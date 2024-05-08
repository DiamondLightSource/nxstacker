import time
from collections import deque
from contextlib import nullcontext
from itertools import chain
from types import MappingProxyType

import h5py
import numpy as np

from nxstacker.experiment.tomoexpt import TomoExpt
from nxstacker.io.nxtomo.metadata import MetadataPtycho
from nxstacker.io.ptycho.ptypy import PtyPyFile
from nxstacker.io.ptycho.ptyrex import PtyREXFile
from nxstacker.utils.io import file_has_paths
from nxstacker.utils.parse import quote_iterable, unique_or_raise
from nxstacker.utils.ptychography import unwrap_phase


class PtychoTomo(TomoExpt):

    name = "ptychography"
    short_name = "ptycho"
    supported_software = MappingProxyType({"PtyPy": PtyPyFile,
                                           "PtyREX": PtyREXFile,
                                           })

    def __init__(self, proj_dir, nxtomo_dir, facility, include_scan,
                 include_proj, include_angle, raw_dir=None, **kwargs):

        super().__init__(proj_dir, nxtomo_dir, facility, include_scan,
                         include_proj, include_angle, raw_dir)

        self._save_complex = kwargs.get("save_complex", False)
        self._save_modulus = kwargs.get("save_modulus", False)
        self._save_phase = kwargs.get("save_phase", True)
        self._remove_ramp = kwargs.get("remove_ramp", False)
        self._normalise = kwargs.get("normalise", False)
        self._unwrap_phase = kwargs.get("unwrap_phase", False)
        self._rescale = kwargs.get("rescale", False)

    def find_all_projections(self):

        pty_files = deque()

        st = time.perf_counter()
        extensions = self._supported_extensions()
        for fp in self.proj_dir.glob(f"**/*[{','.join(extensions)}]"):
            # look at the keys of the file to determine its type
            if h5py.is_hdf5(fp):
                if file_has_paths(fp, PtyPyFile.essential_paths):
                    # for PtyPy file, projection number doesn't matter
                    pty_file = PtyPyFile(fp, id_proj=0, verify=False)

                    to_include = pty_file.id_scan in self.include_scan

                    if to_include:
                        pty_file.fill_attr()
                        pty_files.append(pty_file)

                elif file_has_paths(fp, PtyREXFile.essential_paths):
                    pty_file = PtyREXFile(fp, verify=False)

                    to_include = (pty_file.id_scan in self.include_scan and
                                  pty_file.id_proj in self.include_proj)

                    if to_include:
                        pty_file.fill_attr()
                        pty_files.append(pty_file)

        print(f"{time.perf_counter() - st} s")

        self._projections = self._preliminary_sort(pty_files)

    def _supported_extensions(self):
        return list(chain.from_iterable([file_type.extensions for file_type in
                                         self.supported_software.values()]))

    def _preliminary_sort(self, files):
        software = {file.software for file in files}
        self._check_software_num(software)

        self._software = next(iter(software))

        if self._software == PtyPyFile.software:
            # for PtyPy, sort by scan id
            return sorted(files, key=lambda x: int(x.id_scan))
        if self._software == PtyREXFile.software:
            # for PtyREX, sort by proj id
            return sorted(files, key=lambda x: int(x.id_proj))

        sw = quote_iterable(list(self.supported_software.keys()))
        msg = ("The software that produces the ptychography "
               f"reconstruction files ({self._software}) is not "
               f"supported. Currently it supports {sw}.")
        raise TypeError(msg)

    def _check_software_num(self, software):
        if (num_sw := len(software)) == 0:
            sw = quote_iterable(list(self.supported_software.keys()))
            msg = (f"No ptychography reconstruction file is found in "
                   f"{self.proj_dir}. Supported software: {sw}.")
            raise FileNotFoundError(msg)
        if num_sw > 1:
            sw = quote_iterable(list(software))
            msg = (f"Currently it only supports operations on "
                    "ptychography reconstruction files from a single "
                   f"software. These software are found: {sw}.")
            raise RuntimeError(msg)

    def extract_projections_details(self):

        self.metadata = MetadataPtycho(self._projections, self._facility)
        self.metadata.fetch_metadata()

        # with rotation angles the projection files can be updated and
        # sorted if desired
        self._arrange_by_angle()

    def _arrange_by_angle(self):
        # update id_angle for the projections
        for pty_file, rot_ang in zip(self._projections,
                                     self.metadata.rotation_angle,
                                     strict=False):
            pty_file.id_angle = rot_ang

        if self.sort_by_angle:
            self._projections = sorted(self._projections,
                                       key=lambda x: float(x.id_angle))
        # filter angle
        if self._include_angle:
            self._projections = self._filter_angle()

    def _filter_angle(self):
        filtered = deque()
        for pty_file in self._projections:
            if np.any(np.abs(pty_file.id_angle - self._include_angle)
                      < self.angle_tol):
                filtered.append(pty_file)
        return list(filtered)

    def stack_projection(self, mode=0, *, reverse=False):

        if reverse:
            self._projections = self._projections[::-1]

        nxtomo_cplx, nxtomo_modl, nxtomo_phas = self._nxtomo_minimal()

        cplx_cm = (nullcontext() if nxtomo_cplx is None else
                   h5py.File(nxtomo_cplx, "r+"))
        modl_cm = (nullcontext() if nxtomo_modl is None else
                   h5py.File(nxtomo_modl, "r+"))
        phas_cm = (nullcontext() if nxtomo_phas is None else
                   h5py.File(nxtomo_phas, "r+"))

        with cplx_cm as f_cplx, modl_cm as f_modl, phas_cm as f_phas:
            for k, pty_file in enumerate(self._projections):
                rot_ang = pty_file.id_angle

                if pty_file.avail_complex:
                    # if complex data is present, use it to get
                    # modulus/phase to reduce latency from I/O
                    ob_cplx = pty_file.object_complex(mode=mode)

                    if f_cplx:
                        complex_ = self._resize_proj(ob_cplx)

                        self._save_proj_to_dset(f_cplx, k, complex_, rot_ang)

                    if f_modl:
                        ob_modl = np.abs(ob_cplx)
                        modulus = self._resize_proj(ob_modl)

                        self._save_proj_to_dset(f_modl, k, modulus, rot_ang)

                    if f_phas:
                        ob_phas = np.angle(ob_cplx)
                        phase = self._resize_proj(ob_phas)
                        if self._unwrap_phase:
                            phase = unwrap_phase(phase)

                        self._save_proj_to_dset(f_phas, k, phase, rot_ang)
                else:
                    # complex not availabe, only save modulus/phase
                    if f_modl:
                        ob_modl = pty_file.object_modulus(mode=mode)
                        modulus = self._resize_proj(ob_modl)

                        self._save_proj_to_dset(f_modl, k, modulus, rot_ang)

                    if f_phas:
                        ob_phas = pty_file.object_phase(mode=mode)
                        phase = self._resize_proj(ob_phas)
                        if self._unwrap_phase:
                            phase = unwrap_phase(phase)

                        self._save_proj_to_dset(f_phas, k, phase, rot_ang)

    def _nxtomo_minimal(self):
        self._stack_shape = self._decide_stack_shape()

        cplx = self._nxtomo_cplx_minimal()
        modl = self._nxtomo_modl_minimal()
        phas = self._nxtomo_phas_minimal()

        return cplx, modl, phas

    def _decide_stack_shape(self):
        # assume last 2 dimensions are the actual object shape
        # (excluding modes and other channels)
        ob_shapes = [p.object_shape[-2:] for p in self._projections]

        if self.pad_to_max:
            # determine maximum y and x sizes if pad to max
            y_sh = [sh[0] for sh in ob_shapes]
            x_sh = [sh[1] for sh in ob_shapes]
            ob_sh = (max(y_sh), max(x_sh))
        else:
            ob_sh = unique_or_raise(ob_shapes, companion=self._projections,
                                    label="object shape")

        return (self.num_projections, *ob_sh)

    def _nxtomo_cplx_minimal(self):
        if self._save_complex and all(pty_file.avail_complex for pty_file in
                                      self._projections):
            f_cplx = self._nxtomo_dir / "complex.nxs"
            cplx_dtype = unique_or_raise([p.object_complex_dtype
                                          for p in self._projections],
                                         companion=self._projections,
                                         label="object complex dtype")

            nxtomo_cplx = self.create_minimal_nxtomo(f_cplx,
                                                     self._stack_shape,
                                                     cplx_dtype,
                                                     )
        else:
            nxtomo_cplx = None

        return nxtomo_cplx

    def _nxtomo_modl_minimal(self):
        if self._save_modulus and all(pty_file.avail_modulus for pty_file in
                                      self._projections):
            f_modl = self._nxtomo_dir / "modulus.nxs"
            modl_dtype = unique_or_raise([p.object_modulus_dtype
                                          for p in self._projections],
                                         companion=self._projections,
                                         label="object modulus dtype")

            nxtomo_modl = self.create_minimal_nxtomo(f_modl,
                                                     self._stack_shape,
                                                     modl_dtype,
                                                     )
        else:
            nxtomo_modl = None

        return nxtomo_modl

    def _nxtomo_phas_minimal(self):
        if self._save_phase and all(pty_file.avail_phase for pty_file in
                                      self._projections):
            f_phas = self._nxtomo_dir / "phase.nxs"
            phas_dtype = unique_or_raise([p.object_phase_dtype
                                          for p in self._projections],
                                         companion=self._projections,
                                         label="object phase dtype")

            nxtomo_phas = self.create_minimal_nxtomo(f_phas,
                                                     self._stack_shape,
                                                     phas_dtype,
                                                     )
        else:
            nxtomo_phas = None

        return nxtomo_phas

    def _save_proj_to_dset(self, fh, proj_index, proj, angle):
        proj_dset = fh[self.proj_dset_path]
        proj_dset[proj_index, :, :] = proj

        rot_ang_dset = fh[self.rot_ang_dset_path]
        rot_ang_dset[proj_index] = angle

    def _resize_proj(self, proj):
        proj_y, proj_x = proj.shape
        stack_y, stack_x = self._stack_shape[1:]

        if self.pad_to_max and (proj_y < stack_y or proj_x < stack_x):
            # pad to stack shape if the projection is smaller than
            # others
            y_diff = stack_y - proj_y
            top = y_diff // 2
            bottom = top + y_diff % 2

            x_diff = stack_x - proj_x
            left = x_diff // 2
            right = left + x_diff % 2

            final = np.pad(proj, ((top, bottom), (left, right)),
                           mode="symmetric")
        else:
            final = proj

        return final
