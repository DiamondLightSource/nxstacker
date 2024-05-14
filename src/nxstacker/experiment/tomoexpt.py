"""Class for a tomography experiment.

This module provides:
- TomoExpt: hold attributes/methods common for tomography data
            collection.
"""

from contextlib import suppress
from functools import cached_property

from nxstacker.io.nxtomo.minimal import LINK_DATA, LINK_ROT_ANG, create_minimal
from nxstacker.utils.model import (
    Directory,
    ExperimentFacility,
    IdentifierRange,
    ReadOnly,
)


class TomoExpt:
    """Hold attributes/methods common for tomography data collection."""

    name = "tomography"
    short_name = "tomo"
    angle_tol = 1e-3
    proj_dir = Directory(must_exist=True)
    nxtomo_dir = Directory()
    raw_dir = Directory(undefined_ok=True, must_exist=True)
    facility = ExperimentFacility()
    include_scan = IdentifierRange(int)
    include_proj = IdentifierRange(int)
    include_angle = IdentifierRange(float)
    projections = ReadOnly()
    stack_shape = ReadOnly()
    sort_by_angle = ReadOnly()
    pad_to_max = ReadOnly()
    compress = ReadOnly()
    metadata = ReadOnly()

    def __init__(
        self,
        facility,
        proj_dir,
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
        self.nxtomo_dir = nxtomo_dir
        self.raw_dir = raw_dir

        self.facility = facility

        self.include_scan = include_scan
        self.include_proj = include_proj
        self.include_angle = include_angle

        self._sort_by_angle = sort_by_angle
        self._pad_to_max = pad_to_max
        self._compress = compress

        self._projections = []
        self._stack_shape = ()

        self._metadata = None

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
