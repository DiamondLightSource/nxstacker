"""Class for a tomography experiment.

This module provides:
- TomoExpt: hold attributes/methods common for tomography data
            collection.
"""
from contextlib import suppress
from functools import cached_property
from pathlib import Path

from nxstacker.io.nxtomo.minimal import LINK_DATA, LINK_ROT_ANG, create_minimal


class TomoExpt:
    """Hold attributes/methods common for tomography data collection."""

    angle_tol = 1e-3

    def __init__(self, proj_dir, nxtomo_dir, facility, include_scan,
                 include_proj, include_angle, raw_dir=None):
        """Initialise a tomography experiment."""
        self._facility = facility
        self._facility_id = facility.name

        if proj_dir is None:
            self._proj_dir = Path()
        else:
            self._proj_dir = Path(proj_dir)

        if nxtomo_dir is None:
            self._nxtomo_dir = Path()
        else:
            self._nxtomo_dir = Path(nxtomo_dir)

        if include_scan is None:
            self._include_scan = []
        else:
            self._include_scan = list(include_scan)

        if include_proj is None:
            self._include_proj = []
        else:
            self._include_proj = list(include_proj)

        if include_angle is None:
            self._include_angle = []
        else:
            self._include_angle = list(include_angle)

        self._raw_dir = None
        if raw_dir is not None:
            self._raw_dir = Path(raw_dir)

        self._projections = []
        self._stack_shape = ()
        self.metadata = None
        self.sort_by_angle = False
        self.pad_to_max = True

        # convert the ids to str
        self._include_scan = [str(k) for k in self._include_scan]
        self._include_proj = [str(k) for k in self._include_proj]
        self._include_angle = [str(k) for k in self._include_angle]


    def create_minimal_nxtomo(self, filename, stack_shape, stack_dtype):
        """Create a minimal NXtomo file."""

        md_dict = self.metadata.to_dict()

        # no need to pass rotation_angle
        with suppress(KeyError):
            md_dict.pop("rotation_angle")

        create_minimal(filename, stack_shape, stack_dtype, self._facility,
                       **md_dict)
        return filename

    @property
    def facility(self):
        return self._facility

    @property
    def facility_id(self):
        return self._facility_id

    @property
    def proj_dir(self):
        return self._proj_dir

    @property
    def nxtomo_dir(self):
        return self._nxtomo_dir

    @property
    def include_scan(self):
        return self._include_scan

    @property
    def include_proj(self):
        return self._include_proj

    @property
    def include_angle(self):
        return self._include_angle

    @property
    def projections(self):
        return self._projections

    @property
    def stack_shape(self):
        return self._stack_shape

    @property
    def nxtomo_title(self):
        return self._nxtomo_title

    @property
    def nxtomo_desc(self):
        return self._nxtomo_desc

    @property
    def num_projections(self):
        return len(self._projections)

    @property
    def raw_dir(self):
        return self._raw_dir

    @property
    def id_start(self):
        return self._id_start

    @property
    def id_end(self):
        return self._id_end

    @cached_property
    def proj_dset_path(self):
        return str(LINK_DATA)

    @cached_property
    def rot_ang_dset_path(self):
        return str(LINK_ROT_ANG)
