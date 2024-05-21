"""Class for a tomography experiment.

This module provides:
- TomoExpt: hold attributes/methods common for tomography data
            collection.
"""

import re
from contextlib import suppress
from functools import cached_property
from itertools import chain
from pathlib import Path
from types import MappingProxyType

import numpy as np

from nxstacker.io.nxtomo.minimal import LINK_DATA, LINK_ROT_ANG, create_minimal
from nxstacker.utils.model import (
    Directory,
    ExperimentFacility,
    FilePath,
    FixedValue,
    IdentifierRange,
)


class TomoExpt:
    """Hold attributes/methods common for tomography data collection."""

    name = "tomography"
    short_name = "tomo"
    angle_tol = 1e-3
    supported_software = MappingProxyType({})
    proj_dir = Directory(must_exist=True)
    proj_file = FilePath(undefined_ok=True)
    nxtomo_dir = Directory()
    raw_dir = Directory(undefined_ok=True, must_exist=True)
    facility = ExperimentFacility()
    include_scan = IdentifierRange(int)
    include_proj = IdentifierRange(int)
    include_angle = IdentifierRange(float)
    proj_from_placeholder = FixedValue()
    projections = FixedValue()
    stack_shape = FixedValue()
    sort_by_angle = FixedValue()
    pad_to_max = FixedValue()
    compress = FixedValue()
    metadata = FixedValue()
    nxtomo_output_files = FixedValue()

    def __init__(
        self,
        facility,
        proj_dir,
        proj_file,
        nxtomo_dir,
        include_scan,
        include_proj,
        include_angle,
        raw_dir,
        sort_by_angle,
        pad_to_max,
        compress,
    ):
        """Initialise a tomography experiment."""
        self.proj_dir = proj_dir
        self.proj_file = proj_file
        self.nxtomo_dir = nxtomo_dir
        self.raw_dir = raw_dir

        self.facility = facility

        self.include_scan = include_scan
        self.include_proj = include_proj
        self.include_angle = include_angle
        self.proj_from_placeholder = self._substitute_placeholder_in_proj_dir()

        self.sort_by_angle = sort_by_angle
        self.pad_to_max = pad_to_max
        self.compress = compress

        self.projections = []
        self.stack_shape = ()

        self.metadata = None
        self.nxtomo_output_files = []

    def create_minimal_nxtomo(self, filename, stack_shape, stack_dtype):
        """Create a minimal NXtomo file."""
        md_dict = self.metadata.to_dict()

        # no need to pass rotation_angle
        with suppress(KeyError):
            md_dict.pop("rotation_angle")

        create_minimal(
            filename,
            stack_shape,
            stack_dtype,
            self.facility,
            compress=self.compress,
            **md_dict,
        )
        return filename

    def _nxtomo_file_prefix(self):
        common = f"tomo_{self.short_name}"

        if self.metadata is None:
            return common

        if self.metadata.is_scan_single:
            # use the projection ID when there is only one
            # scan number
            proj_start = self.projections[0].id_proj
            proj_end = self.projections[-1].id_proj
            prefix = (
                f"{common}_{self.metadata.scan_start}_"
                f"{proj_start}_{proj_end}"
            )
        else:
            prefix = (
                f"{common}_{self.metadata.scan_start}_"
                f"{self.metadata.scan_end}"
            )
        return prefix

    def _supported_extensions(self):
        return list(
            chain.from_iterable(
                [
                    file_type.extensions
                    for file_type in self.supported_software.values()
                ],
            ),
        )

    def _substitute_placeholder_in_proj_dir(self):
        if "%(scan)" in str(self.proj_file) or "%(proj)" in str(
            self.proj_file
        ):
            if self.include_scan and self.include_proj:
                scan_substituted = [
                    str(self.proj_file).replace("%(scan)", scan)
                    for scan in self.include_scan
                ]
                proj_files = []
                for scan_sub in scan_substituted:
                    proj_files.extend(
                        [
                            Path(scan_sub.replace("%(proj)", proj))
                            for proj in self.include_proj
                        ]
                    )
            elif self.include_scan and not self.include_proj:
                proj_files = [
                    Path((str(self.proj_file)).replace("%(scan)", scan))
                    for scan in self.include_scan
                ]
            elif not self.include_scan and self.include_proj:
                proj_files = [
                    Path((str(self.proj_file)).replace("%(proj)", proj))
                    for proj in self.include_proj
                ]
            else:
                proj_files = ()

            self._redefine_proj_dir_from_placeholder_in_path()
        else:
            proj_files = self.proj_file

        return proj_files

    def _redefine_proj_dir_from_placeholder_in_path(self):
        # redefine proj_dir if there is valid placeholder
        placeholder = re.compile(r"%\((scan|proj)\)")
        proj_dir = "/"
        for pt in self.proj_file.parts:
            if re.search(placeholder, pt) is None:
                # no valid placeholder, part of proj_dir
                proj_dir += f"{pt}/"
            else:
                # reach the first placeholder
                break
        self._proj_dir = Path(proj_dir).resolve()

    def _save_proj_to_dset(self, fh, proj_index, proj, angle):
        proj_dset = fh[self.proj_dset_path]
        proj_dset[proj_index, :, :] = proj

        rot_ang_dset = fh[self.rot_ang_dset_path]
        rot_ang_dset[proj_index] = angle

    def _resize_proj(self, proj, stack_shape):
        proj_y, proj_x = proj.shape
        stack_y, stack_x = stack_shape[1:]

        if self.pad_to_max and (proj_y < stack_y or proj_x < stack_x):
            # pad to stack shape if the projection is smaller than
            # others
            y_diff = stack_y - proj_y
            top = y_diff // 2
            bottom = top + y_diff % 2

            x_diff = stack_x - proj_x
            left = x_diff // 2
            right = left + x_diff % 2

            final = np.pad(
                proj,
                ((top, bottom), (left, right)),
                mode="symmetric",
            )
        else:
            final = proj

        return final

    def _gather_raw_dir_from_proj_file(self):
        if self.num_projections != 0:
            return list(dict.fromkeys(f.raw_dir for f in self.projections))
        return [""]

    @property
    def num_projections(self):
        """Store the number of total projections."""
        return len(self.projections)

    @cached_property
    def facility_id(self):
        """Store the name of the facility."""
        return self.facility.name

    @cached_property
    def proj_dset_path(self):
        """Store the dataset path for projections in hdf5."""
        return str(LINK_DATA)

    @cached_property
    def rot_ang_dset_path(self):
        """Store the dataset path for rotation angle in hdf5."""
        return str(LINK_ROT_ANG)
