from collections import deque
from types import MappingProxyType

import h5py
import numpy as np

from nxstacker.experiment.tomoexpt import TomoExpt
from nxstacker.io.nxtomo.metadata import MetadataXRF
from nxstacker.io.xrf.python_processing import XRFWindowFile
from nxstacker.utils.io import (
    file_has_paths,
    pad2stack,
    save_proj_to_h5,
)
from nxstacker.utils.logger import create_logger
from nxstacker.utils.model import XRFTransitionList
from nxstacker.utils.parse import quote_iterable, unique_or_raise


class XRFTomo(TomoExpt):
    """Represent a XRF-tomography experiment."""

    name = "x-ray fluorescence"
    short_name = "xrf"
    supported_software = MappingProxyType(
        {
            "window": XRFWindowFile,
        },
    )
    transition = XRFTransitionList()

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
        ignore_raw=False,
        **kwargs,
    ):
        """Initialise the instance."""
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
            ignore_raw=ignore_raw,
        )

        self.transition = kwargs.get("transition")

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
            if h5py.is_hdf5(fp):  # noqa: SIM102
                if file_has_paths(fp, XRFWindowFile.essential_paths):
                    # projection number doesn't matter
                    pty_file = XRFWindowFile(
                        fp, id_proj=0, verify=False, raw_dir=self.raw_dir
                    )

                    to_include = pty_file.id_scan in self.include_scan

                    if to_include:
                        pty_file.fill_attr()
                        pty_files.append(pty_file)

        self._projections = self._preliminary_sort(pty_files)

        if self.num_projections == 0:
            msg = f"No valid projection has been found in {self.proj_dir}"
            raise RuntimeError(msg)

    def _preliminary_sort(self, files):
        return sorted(files, key=lambda x: int(x.id_scan))

    def extract_projections_details(self):
        """Extract metadata from the projections.

        The metadata is encapsulated in the corresponding subclass of
        NXtomoMetadata. The projections will be filtered by
        self.include_angle as the value of rotation angle is available
        now. They will also be sorted if it is required.
        """
        self._metadata = MetadataXRF(self._projections, self._facility)
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

    def stack_projection(self, *, reverse=False):
        """Save the stack of projections into NXtomo files.

        Parameters
        ----------
        reverse : bool, optional
            whether to reverse the order of projections. Default to
            False.

        """
        if reverse:
            self._projections = self._projections[::-1]

        nxtomo_flist, stack_shapes = self._nxtomo_minimal()

        for nxtomo_fp, st_sh, transition in zip(
            nxtomo_flist, stack_shapes, self.transition, strict=False
        ):
            with h5py.File(nxtomo_fp, "r+") as f:
                for k, pty_file in enumerate(self._projections):
                    rot_ang = pty_file.id_angle
                    el_map = pty_file.elemental_map(transition)

                    el_map = pad2stack(el_map, st_sh)
                    el_data = {
                        "data": el_map,
                        "key": self.proj_dset_path,
                    }
                    angle_data = {
                        "data": rot_ang,
                        "key": self.rot_ang_dset_path,
                    }
                    save_proj_to_h5(f, k, el_data, angle_data)

        self._nxtomo_output_files = nxtomo_flist

    def _nxtomo_minimal(self):
        nxtomo_flist = []
        stack_shapes = []
        for t in self.transition:
            stack_shape, stack_dtype = self._decide_stack_attr(t)

            prefix = self._nxtomo_file_prefix()
            f_trans = self._nxtomo_dir / f"{prefix}_{t}.nxs"

            nxtomo_fp = self.create_minimal_nxtomo(
                f_trans,
                stack_shape,
                stack_dtype,
            )

            nxtomo_flist.append(nxtomo_fp)
            stack_shapes.append(stack_shape)

        return nxtomo_flist, stack_shapes

    def _decide_stack_attr(self, transition):
        map_attr = [
            p.elemental_map_attr(transition) for p in self._projections
        ]
        map_shapes = [attr[0] for attr in map_attr]
        map_dtype = [attr[1] for attr in map_attr]

        if self.pad_to_max:
            # determine maximum y and x sizes if pad to max
            y_sh = [sh[0] for sh in map_shapes]
            x_sh = [sh[1] for sh in map_shapes]
            map_sh = (max(y_sh), max(x_sh))
        else:
            map_sh = unique_or_raise(
                map_shapes,
                companion=self._projections,
                label="elemental map shape",
            )

        stack_shape = (self.num_projections, *map_sh)
        stack_dtype = unique_or_raise(
            map_dtype, companion=self._projections, label="elemental map dtype"
        )

        return stack_shape, stack_dtype

    def _log_enter_stack_projection(self, level, name):
        st = super()._log_enter_stack_projection(level, name)

        if self.logger is None:
            self._logger = create_logger(level=level, name=name)
        logger = self.logger

        lg = quote_iterable(self.transition)
        logger.info(
            "The following line group"
            + "s" * (len(self.transition) > 1)
            + f" will be saved: {lg}."
        )
        return st
