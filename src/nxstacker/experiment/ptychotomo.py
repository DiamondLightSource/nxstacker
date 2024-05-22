from collections import deque
from contextlib import nullcontext
from types import MappingProxyType

import h5py
import numpy as np

from nxstacker.experiment.tomoexpt import TomoExpt
from nxstacker.io.nxtomo.metadata import MetadataPtycho
from nxstacker.io.ptycho.ptypy import PtyPyFile
from nxstacker.io.ptycho.ptyrex import PtyREXFile
from nxstacker.utils.io import file_has_paths
from nxstacker.utils.logger import create_logger
from nxstacker.utils.model import FixedValue
from nxstacker.utils.parse import quote_iterable, unique_or_raise
from nxstacker.utils.ptychography import (
    phase_shift,
    remove_phase_ramp,
    unwrap_phase,
)


class PtychoTomo(TomoExpt):
    """Represent a ptycho-tomography experiment."""

    name = "ptychography"
    short_name = "ptycho"
    supported_software = MappingProxyType(
        {
            "PtyPy": PtyPyFile,
            "PtyREX": PtyREXFile,
        },
    )
    save_complex = FixedValue()
    save_modulus = FixedValue()
    save_phase = FixedValue()
    remove_ramp = FixedValue()
    median_norm = FixedValue()
    unwrap_phase = FixedValue()
    rescale = FixedValue()

    def __init__(
        self,
        facility,
        proj_dir,
        proj_file,
        nxtomo_dir,
        include_scan,
        include_proj,
        include_angle,
        raw_dir=None,
        *,
        sort_by_angle=False,
        pad_to_max=True,
        compress=False,
        **kwargs,
    ):
        """Initialise the instance.

        Parameters
        ----------
        facility : FacilityInfo, str or None
            the facility. It could be of the class FacilityInfo, which
            already contains the details, or a str, where an instance of
            FacilityInfo is initialised, or None, where the
            corresponding facility is deduced from given directories.
        proj_dir : pathlib.Path, str or None
            the directory where the projections are stored. If it is
            None, the current working directory is used.
        proj_file : str or None
            the projection file with placeholder %(scan) from
            include_scan and %(proj) from include_proj. Default to None.
        nxtomo_dir : pathlib.Path, str or None
            the directory where the NXtomo files will be saved. If it is
            None, the current working directory is used.
        include_scan : str, iterable or None
            the identifiers of scans to include in the NXtomo file. If
            it is a str, it is passed to generate_numbers; if it is an
            iterable, it will convert to a tuple; if it is None, it will
            be an empty tuple.
        include_proj : str, iterable or None
            the identifiers of projections to include in the NXtomo
            file. See "include_scan".
        include_angle : str, iterable or None
            the rotation angles to be included in the NXtomo file. Use
            this with caution as it might suffer from float-point
            precision issue.  See "include_scan".
        raw_dir : pathlib.Path, str or None, optional
            the directory where the raw data are stored. For most of the
            time this can be left as None as the raw directory is
            inferred from the projection files, but it is useful when
            the original raw directory is invalid. Default to None.
        sort_by_angle : bool, optional
            whether to sort the projections by their rotation angles.
            Default to False.
        pad_to_max : bool, optional
            whether to pad the individual projection if it is not at the
            maximum size of the stack. Default to True. If it is False
            and there is inconsistent size, RuntimeError is raised.
        compress : bool, optional
            whether to apply compression (Blosc) to the NXtomo file.
            Default to False.
        kwargs : dict, optional
            options for ptycho-tomography

        """
        super().__init__(
            facility,
            proj_dir,
            proj_file,
            nxtomo_dir,
            include_scan,
            include_proj,
            include_angle,
            raw_dir,
            sort_by_angle=sort_by_angle,
            pad_to_max=pad_to_max,
            compress=compress,
        )

        self._save_complex = kwargs.get("save_complex", False)
        self._save_modulus = kwargs.get("save_modulus", False)
        self._save_phase = kwargs.get("save_phase", True)
        self._remove_ramp = kwargs.get("remove_ramp", False)
        self._median_norm = kwargs.get("median_norm", False)
        self._unwrap_phase = kwargs.get("unwrap_phase", False)
        self._rescale = kwargs.get("rescale", False)

    def find_all_projections(self):
        """Find all projections.

        It goes through files and directories in self.proj_dir, add the
        file to self.projections if they should be included as informed
        by self.include_scan and self.include_proj.
        """
        pty_files = deque()

        if self.proj_from_placeholder:
            file_iter = self.proj_from_placeholder
        else:
            extensions = self._supported_extensions()
            file_iter = self.proj_dir.glob(f"**/*[{','.join(extensions)}]")

        for fp in file_iter:
            # look at the keys of the file to determine its type
            if h5py.is_hdf5(fp):
                if file_has_paths(fp, PtyPyFile.essential_paths):
                    # for PtyPy file, projection number doesn't matter
                    pty_file = PtyPyFile(
                        fp, id_proj=0, verify=False, raw_dir=self.raw_dir
                    )

                    to_include = pty_file.id_scan in self.include_scan

                    if to_include:
                        pty_file.fill_attr()
                        pty_files.append(pty_file)

                elif file_has_paths(fp, PtyREXFile.essential_paths):
                    pty_file = PtyREXFile(
                        fp, verify=False, raw_dir=self.raw_dir
                    )

                    to_include = (
                        pty_file.id_scan in self.include_scan
                        and pty_file.id_proj in self.include_proj
                    )

                    if to_include:
                        pty_file.fill_attr()
                        pty_files.append(pty_file)

        self._projections = self._preliminary_sort(pty_files)

        if self.num_projections == 0:
            msg = f"No valid projection has been found in {self.proj_dir}"
            raise RuntimeError(msg)

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
        msg = (
            "The software that produces the ptychography "
            f"reconstruction files ({self._software}) is not "
            f"supported. Currently it supports {sw}."
        )
        raise TypeError(msg)

    def _check_software_num(self, software):
        if (num_sw := len(software)) == 0:
            sw = quote_iterable(list(self.supported_software.keys()))
            msg = (
                f"No ptychography reconstruction file is found in "
                f"{self.proj_dir}. Supported software: {sw}."
            )
            raise FileNotFoundError(msg)
        if num_sw > 1:
            sw = quote_iterable(list(software))
            msg = (
                f"Currently it only supports operations on "
                "ptychography reconstruction files from a single "
                f"software. These software are found: {sw}."
            )
            raise RuntimeError(msg)

    def extract_projections_details(self):
        """Extract metadata from the projections.

        The metadata is encapsulated in the corresponding subclass of
        NXtomoMetadata. The projections will be filtered by
        self.include_angle as the value of rotation angle is available
        now. They will also be sorted if it is required.
        """
        self._metadata = MetadataPtycho(self._projections, self._facility)
        self._metadata.fetch_metadata()

        # with rotation angles the projection files can be updated and
        # sorted if desired
        self._arrange_by_angle()

    def _arrange_by_angle(self):
        # update id_angle for the projections
        for pty_file, rot_ang in zip(
            self._projections,
            self.metadata.rotation_angle,
            strict=False,
        ):
            pty_file._id_angle = rot_ang

        if self.sort_by_angle:
            self._projections = sorted(
                self._projections,
                key=lambda x: float(x.id_angle),
            )
        # filter angle
        if self._include_angle:
            self._projections = self._filter_angle()

    def _filter_angle(self):
        filtered = deque()
        for pty_file in self._projections:
            if np.any(
                np.abs(pty_file.id_angle - self._include_angle)
                < self.angle_tol,
            ):
                filtered.append(pty_file)
        return list(filtered)

    def stack_projection(self, mode=0, *, reverse=False):
        """Save the stack of projections into NXtomo files.

        Parameters
        ----------
        mode : int, optional
            the object mode from the reconstruction that will be saved
            in NXtomo file. Default to 0.
        reverse : bool, optional
            whether to reverse the order of projections. Default to
            False.

        """
        if reverse:
            self._projections = self._projections[::-1]

        nxtomo_cplx, nxtomo_modl, nxtomo_phas = self._nxtomo_minimal()

        cplx_cm = (
            nullcontext()
            if nxtomo_cplx is None
            else h5py.File(nxtomo_cplx, "r+")
        )
        modl_cm = (
            nullcontext()
            if nxtomo_modl is None
            else h5py.File(nxtomo_modl, "r+")
        )
        phas_cm = (
            nullcontext()
            if nxtomo_phas is None
            else h5py.File(nxtomo_phas, "r+")
        )

        with cplx_cm as f_cplx, modl_cm as f_modl, phas_cm as f_phas:
            for k, pty_file in enumerate(self._projections):
                rot_ang = pty_file.id_angle

                if pty_file.avail_complex:
                    # if complex data is present, use it to get
                    # modulus/phase to reduce latency from I/O
                    ob_cplx = pty_file.object_complex(mode=mode)

                    if f_cplx:
                        complex_ = self._resize_proj(ob_cplx, self.stack_shape)

                        self._save_proj_to_dset(f_cplx, k, complex_, rot_ang)

                    if f_modl:
                        ob_modl = np.abs(ob_cplx)
                        modulus = self._resize_proj(ob_modl, self.stack_shape)

                        self._save_proj_to_dset(f_modl, k, modulus, rot_ang)

                    if f_phas:
                        if self._remove_ramp:
                            ob_cplx = remove_phase_ramp(ob_cplx)
                        if self._median_norm:
                            ob_cplx = phase_shift(
                                ob_cplx,
                                -np.median(np.angle(ob_cplx)),
                            )

                        ob_phas = np.angle(ob_cplx)
                        phase = self._resize_proj(ob_phas, self.stack_shape)
                        if self._unwrap_phase:
                            phase = unwrap_phase(phase)

                        self._save_proj_to_dset(f_phas, k, phase, rot_ang)
                else:
                    # complex not availabe, only save modulus/phase
                    if f_modl:
                        ob_modl = pty_file.object_modulus(mode=mode)
                        modulus = self._resize_proj(ob_modl, self.stack_shape)

                        self._save_proj_to_dset(f_modl, k, modulus, rot_ang)

                    if f_phas:
                        if self._remove_ramp or self._median_norm:
                            # log warning here
                            pass
                        ob_phas = pty_file.object_phase(mode=mode)
                        phase = self._resize_proj(ob_phas, self.stack_shape)
                        if self._unwrap_phase:
                            phase = unwrap_phase(phase)

                        self._save_proj_to_dset(f_phas, k, phase, rot_ang)

        nxtomo_files = []
        if nxtomo_cplx is not None:
            nxtomo_files.append(nxtomo_cplx)
        if nxtomo_modl is not None:
            nxtomo_files.append(nxtomo_modl)
        if nxtomo_phas is not None:
            nxtomo_files.append(nxtomo_phas)
        self._nxtomo_output_files = nxtomo_files

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
            ob_sh = unique_or_raise(
                ob_shapes,
                companion=self._projections,
                label="object shape",
            )

        return (self.num_projections, *ob_sh)

    def _nxtomo_cplx_minimal(self):
        if self._save_complex and all(
            pty_file.avail_complex for pty_file in self._projections
        ):
            prefix = self._nxtomo_file_prefix()
            f_cplx = self._nxtomo_dir / f"{prefix}_complex.nxs"
            cplx_dtype = unique_or_raise(
                [p.object_complex_dtype for p in self._projections],
                companion=self._projections,
                label="object complex dtype",
            )

            nxtomo_cplx = self.create_minimal_nxtomo(
                f_cplx,
                self._stack_shape,
                cplx_dtype,
            )
        else:
            nxtomo_cplx = None

        return nxtomo_cplx

    def _nxtomo_modl_minimal(self):
        if self._save_modulus and all(
            pty_file.avail_modulus for pty_file in self._projections
        ):
            prefix = self._nxtomo_file_prefix()
            f_modl = self._nxtomo_dir / f"{prefix}_modulus.nxs"
            modl_dtype = unique_or_raise(
                [p.object_modulus_dtype for p in self._projections],
                companion=self._projections,
                label="object modulus dtype",
            )

            nxtomo_modl = self.create_minimal_nxtomo(
                f_modl,
                self._stack_shape,
                modl_dtype,
            )
        else:
            nxtomo_modl = None

        return nxtomo_modl

    def _nxtomo_phas_minimal(self):
        if self._save_phase and all(
            pty_file.avail_phase for pty_file in self._projections
        ):
            prefix = self._nxtomo_file_prefix()
            f_phas = self._nxtomo_dir / f"{prefix}_phase.nxs"
            phas_dtype = unique_or_raise(
                [p.object_phase_dtype for p in self._projections],
                companion=self._projections,
                label="object phase dtype",
            )

            nxtomo_phas = self.create_minimal_nxtomo(
                f_phas,
                self._stack_shape,
                phas_dtype,
            )
        else:
            nxtomo_phas = None

        return nxtomo_phas

    def _log_enter_stack_projection(self, level, name):
        st = super()._log_enter_stack_projection(level, name)

        if self.logger is None:
            self._logger = create_logger(level=level, name=name)
        logger = self.logger

        complex_msg = (
            "The complex reconstruction will "
            + "not " * (not self.save_complex)
            + "be saved."
        )
        modulus_msg = (
            "The modulus will "
            + "not " * (not self.save_modulus)
            + "be saved."
        )
        phase_msg = (
            "The phase will " + "not " * (not self.save_phase) + "be saved."
        )
        phase_ramp_msg = "Phase ramp removal is not yet implemented."
        median_norm_msg = (
            "The phase will "
            + "not " * (not self.median_norm)
            + "be shifted by its median."
        )
        unwrap_phase_msg = (
            "The phase will "
            + "not " * (not self.unwrap_phase)
            + "be unwrapped."
        )
        rescale_msg = "Rescale is not yet implemented."
        logger.info(complex_msg)
        logger.info(modulus_msg)
        logger.info(phase_msg)
        if self.save_phase:
            if self.remove_ramp:
                logger.warning(phase_ramp_msg)
            logger.info(median_norm_msg)
            logger.info(unwrap_phase_msg)
        if self.rescale:
            logger.warning(rescale_msg)
        return st
