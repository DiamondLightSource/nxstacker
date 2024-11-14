from collections import deque
from contextlib import nullcontext
from multiprocessing import Manager, Pool, Process
from types import MappingProxyType

import h5py
import numpy as np

from nxstacker.experiment.tomoexpt import TomoExpt
from nxstacker.io.nxtomo.metadata import MetadataPtycho
from nxstacker.io.ptycho.ptypy import PtyPyFile
from nxstacker.io.ptycho.ptyrex import PtyREXFile
from nxstacker.utils.io import (
    file_has_paths,
    pad2stack,
    save_proj_to_h5,
)
from nxstacker.utils.logger import create_logger
from nxstacker.utils.model import FixedValue
from nxstacker.utils.parse import quote_iterable, unique_or_raise
from nxstacker.utils.ptychography import (
    phase_shift,
    remove_phase_ramp,
    unwrap_phase,
)
from nxstacker.utils.resource import num_cpus


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
        skip_proj_file_check=False,
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
        skip_proj_file_check : bool, optional
            whether to skip the file check when adding an hdf5 to the list
            of projection files. Usually this is true when you are doing a
            typical stacking and sure no other hdf5 files are present in
            proj_dir. Default to False.
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
            skip_proj_file_check=skip_proj_file_check,
        )

        self._save_complex = kwargs.get("save_complex", False)
        self._save_modulus = kwargs.get("save_modulus", False)
        self._save_phase = kwargs.get("save_phase", True)
        self._remove_ramp = kwargs.get("remove_ramp", False)
        self._median_norm = kwargs.get("median_norm", False)
        self._unwrap_phase = kwargs.get("unwrap_phase", False)
        self._rescale = kwargs.get("rescale", False)

    def find_all_projections(self, *, parallel=True):
        """Find all projections.

        It goes through files and directories in self.proj_dir, add the
        file to self.projections if they should be included as informed
        by self.include_scan and self.include_proj.

        Parameters
        ----------
        parallel : bool, optional
            parallelise the finding of projection files. Default to
            True.

        """
        pty_files = deque()

        if self.proj_from_placeholder:
            file_iter = self.proj_from_placeholder
        else:
            extensions = self._supported_extensions()
            file_iter = self.proj_dir.glob(f"**/*[{','.join(extensions)}]")

        # set the flags of whether assuming they are of a specified
        # projection file type and the order to validate file if no such
        # assumption is make
        self._assume_file_order()

        if parallel:
            ncpus = num_cpus()
            with Pool(processes=ncpus) as pool:
                for pty_file in pool.imap_unordered(
                    self._find_proj, file_iter
                ):
                    if pty_file is not None:
                        pty_files.append(pty_file)
        else:
            # serial
            for fp in file_iter:
                pty_file = self._find_proj(fp)
                if pty_file is not None:
                    pty_files.append(pty_file)

        self._projections = self._preliminary_sort(pty_files)

        if self.num_projections == 0:
            msg = f"No valid projection has been found in {self.proj_dir}"
            raise RuntimeError(msg)

    def _assume_file_order(self):
        if self.skip_proj_file_check:
            self._assume_ptypy_file = "PtyPy" in self.facility.ptycho_file_type
            self._assume_ptyrex_file = (
                "PtyREX" in self.facility.ptycho_file_type
            )

            # these are not used
            self._order_paths = ()
            self._order_init = ()
        else:
            self._assume_ptypy_file = False
            self._assume_ptyrex_file = False

            # now it won't skip checking, so give preference to the
            # assumed file type as the ordering of checking impacts the
            # speed
            if "PtyPy" in self.facility.ptycho_file_type:
                self._order_paths = (
                    PtyPyFile.essential_paths,
                    PtyREXFile.essential_paths,
                )
                self._order_init = (
                    self._init_ptypy_file,
                    self._init_ptyrex_file,
                )
            elif "PtyREX" in self.facility.ptycho_file_type:
                self._order_paths = (
                    PtyREXFile.essential_paths,
                    PtyPyFile.essential_paths,
                )
                self._order_init = (
                    self._init_ptyrex_file,
                    self._init_ptypy_file,
                )
            else:
                msg = (
                    "Unsupported ptychography file type "
                    f"'{self.facility.ptycho_file_type}'."
                )
                raise ValueError(msg)

    def _find_proj(self, fp):
        pty_file = None
        to_include = False
        if h5py.is_hdf5(fp):
            if any([self._assume_ptypy_file, self._assume_ptyrex_file]):
                # no check, quicker but less safe
                if self._assume_ptypy_file:
                    pty_file, to_include = self._init_ptypy_file(fp)
                elif self._assume_ptyrex_file:
                    pty_file, to_include = self._init_ptyrex_file(fp)
            else:
                # look at the keys of the file to determine its type
                # from a preferred order as determined by the
                # facility, slower but safer
                for ep, init_method in zip(
                    self._order_paths, self._order_init, strict=False
                ):
                    if file_has_paths(fp, ep):
                        pty_file, to_include = init_method(fp)
                        break

            # fill the attribute of the file if it should be included
            # and return the file, otherwise return None
            if to_include:
                pty_file.fill_attr()
                return pty_file
            return None

        return pty_file

    def _init_ptypy_file(self, fp):
        # for PtyPy file, projection number doesn't matter
        pty_file = PtyPyFile(fp, id_proj=0, verify=False, raw_dir=self.raw_dir)

        to_include = pty_file.id_scan in self.include_scan

        return pty_file, to_include

    def _init_ptyrex_file(self, fp):
        pty_file = PtyREXFile(fp, verify=False, raw_dir=self.raw_dir)

        to_include = (
            pty_file.id_scan in self.include_scan
            and pty_file.id_proj in self.include_proj
        )

        return pty_file, to_include

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

        _ = self.check_missing_projections()

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

        read_cplx = nxtomo_cplx is not None
        read_modl = nxtomo_modl is not None
        read_phas = nxtomo_phas is not None

        # parallelise when more than 50 projections
        parallel = self.num_projections >= 50

        if parallel:
            ncpus = num_cpus()

            # to avoid over-subscribe we set the blosc thread to 1
            # if doing multiprocessing
            if self.compression_settings is not None:
                self.compression_settings.set_nthreads(1)

            with Manager() as manager:
                queue = manager.Queue()

                # initiate the hdf5 writing process
                write_proc = Process(
                    target=self._parallel_cplx_modl_phas,
                    args=(nxtomo_cplx, nxtomo_modl, nxtomo_phas, queue),
                )
                write_proc.start()

                with Pool(ncpus) as pool:
                    tasks = (
                        (
                            k,
                            pty_file,
                            mode,
                            read_cplx,
                            read_modl,
                            read_phas,
                            queue,
                        )
                        for k, pty_file in enumerate(self._projections)
                    )
                    chunk_sz = self.num_projections // ncpus + 1

                    # distribute the reading to a pool of workers
                    # the result is put into a queue when they are read
                    pool.starmap_async(
                        self._read_cplx_modl_phas, tasks, chunksize=chunk_sz
                    )

                    # .join before .close, essential
                    pool.close()
                    pool.join()

                # send termination signal to the queue
                queue.put(None)

                write_proc.join()
        else:
            # serial
            queue = None
            cplx_cm, modl_cm, phas_cm = self._create_cm(
                nxtomo_cplx, nxtomo_modl, nxtomo_phas
            )
            with cplx_cm as f_cplx, modl_cm as f_modl, phas_cm as f_phas:
                for k, pty_file in enumerate(self._projections):
                    proj_pack = self._read_cplx_modl_phas(
                        k,
                        pty_file,
                        mode,
                        read_cplx,
                        read_modl,
                        read_phas,
                        queue,
                    )
                    self._serial_cplx_modl_phas(
                        proj_pack, f_cplx, f_modl, f_phas
                    )

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

    def _create_cm(self, nxtomo_cplx, nxtomo_modl, nxtomo_phas):
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

        return cplx_cm, modl_cm, phas_cm

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

    def _serial_cplx_modl_phas(self, proj_pack, f_cplx, f_modl, f_phas):
        """Write serially."""
        # h5py File objects are available
        k, rot_ang, complex_, modulus, phase = proj_pack
        angle_data = {
            "data": rot_ang,
            "key": self.rot_ang_dset_path,
        }

        self._save_cplx_to_file(k, f_cplx, complex_, angle_data)
        self._save_modl_to_file(k, f_modl, modulus, angle_data)
        self._save_phas_to_file(k, f_phas, phase, angle_data)

    def _parallel_cplx_modl_phas(
        self, nxtomo_cplx, nxtomo_modl, nxtomo_phas, queue
    ):
        """Write in parallel using data from queue."""
        cplx_cm, modl_cm, phas_cm = self._create_cm(
            nxtomo_cplx, nxtomo_modl, nxtomo_phas
        )

        with cplx_cm as f_cplx, modl_cm as f_modl, phas_cm as f_phas:
            while True:
                proj_pack = queue.get()

                # signal to terminate
                if proj_pack is None:
                    break

                # if not terminated, unpack
                k, rot_ang, complex_, modulus, phase = proj_pack
                angle_data = {
                    "data": rot_ang,
                    "key": self.rot_ang_dset_path,
                }

                self._save_cplx_to_file(k, f_cplx, complex_, angle_data)
                self._save_modl_to_file(k, f_modl, modulus, angle_data)
                self._save_phas_to_file(k, f_phas, phase, angle_data)

    def _save_cplx_to_file(self, k, f_cplx, complex_, angle_data):
        if f_cplx and complex_ is not None:
            cplx_data = {
                "data": complex_,
                "key": self.proj_dset_path,
            }
            save_proj_to_h5(
                f_cplx, k, cplx_data, angle_data, self.compression_settings
            )

    def _save_modl_to_file(self, k, f_modl, modulus, angle_data):
        if f_modl and modulus is not None:
            modl_data = {
                "data": modulus,
                "key": self.proj_dset_path,
            }
            save_proj_to_h5(
                f_modl, k, modl_data, angle_data, self.compression_settings
            )

    def _save_phas_to_file(self, k, f_phas, phase, angle_data):
        if f_phas and phase is not None:
            phas_data = {
                "data": phase,
                "key": self.proj_dset_path,
            }
            save_proj_to_h5(
                f_phas, k, phas_data, angle_data, self.compression_settings
            )

    def _read_cplx_modl_phas(
        self, k, pty_file, mode, read_cplx, read_modl, read_phas, queue
    ):
        """Put projections image into a queue or return them."""
        rot_ang = pty_file.id_angle

        complex_ = None
        modulus = None
        phase = None

        if pty_file.avail_complex:
            # if complex data is present, use it to get
            # modulus/phase to reduce latency from i/o
            ob_cplx = pty_file.object_complex(mode=mode)

            if read_cplx:
                if self.pad_to_max:
                    complex_ = pad2stack(ob_cplx, self.stack_shape)
                else:
                    complex_ = ob_cplx

            if read_modl:
                ob_modl = np.abs(ob_cplx)
                if self.pad_to_max:
                    modulus = pad2stack(ob_modl, self.stack_shape)
                else:
                    modulus = ob_modl

            if read_phas:
                if self._remove_ramp:
                    ob_cplx = remove_phase_ramp(ob_cplx)
                if self._median_norm:
                    ob_cplx = phase_shift(
                        ob_cplx,
                        -np.median(np.angle(ob_cplx)),
                    )

                ob_phas = np.angle(ob_cplx)
                if self.pad_to_max:
                    phase = pad2stack(ob_phas, self.stack_shape)
                else:
                    phase = ob_phas

                if self._unwrap_phase:
                    phase = unwrap_phase(phase)

        else:
            # complex not availabe, only save modulus/phase
            if read_modl:
                ob_modl = pty_file.object_modulus(mode=mode)
                if self.pad_to_max:
                    modulus = pad2stack(ob_modl, self.stack_shape)
                else:
                    modulus = ob_modl

            if read_phas:
                if self._remove_ramp or self._median_norm:
                    # log warning here
                    pass
                ob_phas = pty_file.object_phase(mode=mode)
                if self.pad_to_max:
                    phase = pad2stack(ob_phas, self.stack_shape)
                else:
                    phase = ob_phas

                if self._unwrap_phase:
                    phase = unwrap_phase(phase)

        if queue is None:
            # serial
            return k, rot_ang, complex_, modulus, phase

        # parallel, put results in the queue
        queue.put((k, rot_ang, complex_, modulus, phase))
        return None

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
