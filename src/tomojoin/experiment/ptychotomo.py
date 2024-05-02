import time
from collections import deque
from contextlib import nullcontext
from itertools import chain
from types import MappingProxyType

import h5py
import numpy as np
from tomojoin.experiment.tomoexpt import TomoExpt

from tomojoin.io.nxtomo.minimal import LINK_DATA, LINK_ROT_ANG
from tomojoin.io.ptycho.ptypy import PtyPyFile
from tomojoin.io.ptycho.ptyrex import PtyREXFile
from tomojoin.utils.io import file_has_paths
from tomojoin.utils.parse import quote_iterable, unique_or_raise


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
                        pty_file.find_raw_dir()
                        pty_files.append(pty_file)

                elif file_has_paths(fp, PtyREXFile.essential_paths):
                    pty_file = PtyREXFile(fp, verify=False)

                    to_include = (pty_file.id_scan in self.include_scan and
                                  pty_file.id_proj in self.include_proj)

                    if to_include:
                        pty_file.find_raw_dir()
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

    def extract_projections_details(self, *, sort_by_angle=False):


        for pty_file in self._projections:


            rot_ang = self._facility.rotation_angle(pty_file)
            distance = self._facility.sample_detector_dist(pty_file)

            # fill information after raw dir is known


            # update the correpsonding file
            pty_file.id_angle = rot_ang
            pty_file.distance = distance

        if sort_by_angle:
            self._projections = sorted(self._projections,
                                       key=lambda x: float(x.id_angle))

        # filter angle
        if self._include_angle:
            self._projections = self._filter_angle()


        # set global metadata from values in different projections
        self._sample_detector_distance = np.mean([f.distance for f in
                                                 self._projections])

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
                if pty_file.avail_complex:
                    # if complex is accessible, use it to get
                    # modulus/phase to reduce latency from I/O
                    ob_cplx = pty_file.object_complex(mode=mode)
                    rot_ang = pty_file.id_angle

                    if f_cplx:
                        f_cplx[str(LINK_DATA)][k, :, :] = ob_cplx
                        f_cplx[str(LINK_ROT_ANG)][k] = rot_ang

                    if f_modl:
                        f_modl[str(LINK_DATA)][k, :, :] = np.abs(ob_cplx)
                        f_modl[str(LINK_ROT_ANG)][k] = rot_ang

                    if f_phas:
                        f_phas[str(LINK_DATA)][k, :, :] = np.angle(ob_cplx)
                        f_phas[str(LINK_ROT_ANG)][k] = rot_ang
                else:
                    # complex not availabe, only save modulus/phase
                    if f_modl:
                        ob_modl = pty_file.object_modulus(mode=mode)
                        f_modl[str(LINK_DATA)][k, :, :] = ob_modl
                        f_modl[str(LINK_ROT_ANG)][k] = rot_ang

                    if f_phas:
                        ob_phas = pty_file.object_phase(mode=mode)
                        f_phas[str(LINK_DATA)][k, :, :] = ob_phas
                        f_phas[str(LINK_ROT_ANG)][k] = rot_ang


    def _nxtomo_minimal(self):
        self._stack_shape = self._decide_stack_shape()

        cplx = self._nxtomo_cplx_minimal()
        modl = self._nxtomo_modl_minimal()
        phas = self._nxtomo_phas_minimal()

        return cplx, modl, phas

    def _decide_stack_shape(self):

        # determine homogeneity
        ob_sh = unique_or_raise([p.object_shape for p in self._projections],
                                companion=self._projections,
                                label="object shape")
        # ignore mode channel
        return (self.num_projections, *ob_sh[1:])

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
                                                     self._nxtomo_title,
                                                     self._nxtomo_desc)
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
                                                     self._nxtomo_title,
                                                     self._nxtomo_desc)
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
                                                     self._nxtomo_title,
                                                     self._nxtomo_desc)
        else:
            nxtomo_phas = None

        return nxtomo_phas