from pathlib import Path

import h5py

from nxstacker.facility.facility import SPECS_DIR, FacilityInfo
from nxstacker.utils.io import dataset_from_first_valid_path
from nxstacker.utils.parse import add_timezone


class I08_1(FacilityInfo): # noqa: N801

    name = "i08-1"

    def __init__(self, specs=None):
        super().__init__()

        self.specs = SPECS_DIR / "i08-1.yaml"
        if specs is not None:
            self.specs = Path(specs)

        self.populate_attr()

    def nxs_file(self, proj_file):
        raw_dir = proj_file.raw_dir
        scan_id = proj_file.id_scan

        nxs_f = Path(f"{raw_dir}/nexus/i08-1-{scan_id}.nxs")
        if nxs_f.exists():
            return nxs_f
        msg = (f"The NeXus file {nxs_f} does not exist. Please "
                "check the raw data directory and scan ID to see "
                "if they match.")
        raise FileNotFoundError(msg)

    def rotation_angle(self, rot_f, _):
        """Retrieve rotation angle.

        Parameters
        ----------
        raw_dir : Path
            the raw data directory
        scan_id : str
            the scan ID
        id_proj : int, optional
            not use by i08-1

        Returns
        -------
        rot_ang : float
            the rotation angle
        """
        with h5py.File(rot_f, "r") as f:
            dset = dataset_from_first_valid_path(f, self.rotation_angle_path)
            rot_ang = dset[()]

        return rot_ang

    def sample_detector_dist(self, _=None):
        """
        """
        return 0.072

    def start_time(self, start_time_f, _):
        with h5py.File(start_time_f, "r") as f:
            dset = dataset_from_first_valid_path(f, self.start_time_path)
            start_time = dset[()]

        if isinstance(start_time, bytes):
            start_time = start_time.decode()

        start_time_tz = add_timezone(start_time)

        return start_time_tz

    def end_time(self, end_time_f, _):
        with h5py.File(end_time_f, "r") as f:
            dset = dataset_from_first_valid_path(f, self.end_time_path)
            end_time = dset[()]

        if isinstance(end_time, bytes):
            end_time = end_time.decode()

        end_time_tz = add_timezone(end_time)

        return end_time_tz
