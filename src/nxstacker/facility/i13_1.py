from datetime import datetime, timezone
from pathlib import Path

import h5py

from nxstacker.facility.facility import SPECS_DIR, FacilityInfo
from nxstacker.utils.io import dataset_from_first_valid_path


class I13_1(FacilityInfo): # noqa: N801

    name = "i13-1"

    def __init__(self, specs=None):
        super().__init__()

        self.specs = SPECS_DIR / "i13-1.yaml"
        if specs is not None:
            self.specs = Path(specs)

        self.populate_attr()

    def nxs_file(self, proj_file):
        raw_dir = proj_file.raw_dir
        scan_id = proj_file.id_scan

        nxs_f = Path(f"{raw_dir}/raw/{scan_id}.nxs")
        if nxs_f.exists():
            return nxs_f
        msg = (f"The NeXus file {nxs_f} does not exist. Please "
                "check the raw data directory and scan ID to see "
                "if they match.")
        raise FileNotFoundError(msg)

    def pty_tomo_file(self, proj_file):
        raw_dir = proj_file.raw_dir
        scan_id = proj_file.id_scan

        pty_tomo_f = Path(f"{raw_dir}/raw/{scan_id}/raw/pty_tomo.h5")
        if pty_tomo_f.exists():
            return pty_tomo_f
        msg = (f"The pty_tomo file {pty_tomo_f} does not exist. Please "
                "check the raw data directory and scan ID to see "
                "if they match.")
        raise FileNotFoundError(msg)

    def position_file(self, proj_file):
        raw_dir = proj_file.raw_dir
        scan_id = proj_file.id_scan

        pos_f = Path(f"{raw_dir}/raw/{scan_id}/raw/positions_0.h5")
        if pos_f.exists():
            return pos_f
        msg = (f"The position file {pos_f} does not exist. Please "
                "check the raw data directory and scan ID to see "
                "if they match.")
        raise FileNotFoundError(msg)

    def rotation_angle(self, rot_f, proj_file=None):
        """Retrieve rotation angle.

        Parameters
        ----------
        raw_dir : Path
            the raw data directory
        scan_id : str
            the scan ID
        id_proj : int
            the projection ID.

        Returns
        -------
        rot_ang : float
            the rotation angle
        """
        if proj_file is None:
            msg = (f"{self.name} requires a projection file to determine the "
                    "rotation angle")
            raise ValueError(msg)

        with h5py.File(rot_f, "r") as f:
            dset = dataset_from_first_valid_path(f, self.rotation_angle_path)
            rot_ang = dset[int(proj_file.id_proj), :, 0].mean()

        return rot_ang

    def sample_detector_dist(self, dist_f):
        """
        """
        with h5py.File(dist_f, "r") as f:
            dset = dataset_from_first_valid_path(f,
                                                 self.detector_distance_path)
            dist = dset[()]
            if dist_f.suffix == ".nxs":
                # assume .nxs recorded with mm
                dist *= 1e-3
        return dist

    def _tot_num_proj(self, proj_file):
        pty_tomo_f = self.pty_tomo_file(proj_file)

        with h5py.File(pty_tomo_f, "r") as f:
            num_projs = f["/data/frames"].shape[0]

        return num_projs

    def start_time(self, start_time_f, proj_file):
        """Get the start time.

        The timestamp here lacks behind for 20 years, but adding 365*20
        will not work because of leap years. The current workaround is
        fine for most cases, but not for overnight scan performed on a
        29/2 for example.

        The solution is of course to have the timestamp saved correctly.

        Parameters
        ----------
        start_time_f : pathlib.Path
            the file used to get the start time
        proj_file : ProjectionFile
            the ptychography projection file

        Returns
        -------
        start_time_tz : str
            the start time in ISO 8601 format with time zone
        """
        num_projs = self._tot_num_proj(proj_file)

        with h5py.File(start_time_f, "r") as f:
            dset = dataset_from_first_valid_path(f, self.start_time_path)

            size = dset.shape[0]
            stride = size // num_projs
            offset = int(proj_file.id_proj) * stride
            start_time = dset[offset, 0, 0]

        # YY-MM-DD from file modification time
        # hh-mm-ss from the timestamp
        start_datetime = datetime.fromtimestamp(start_time,
                                                tz=timezone.utc)
        file_mtime = datetime.fromtimestamp(start_time_f.stat().st_mtime,
                                            tz=timezone.utc)
        start_time_tz = start_datetime.replace(year=file_mtime.year,
                                               month=file_mtime.month,
                                               day=file_mtime.day).isoformat()

        return start_time_tz

    def end_time(self, end_time_f, proj_file):
        """Get the end time.

        The timestamp here lacks behind for 20 years, but adding 365*20
        will not work because of leap years. The current workaround is
        fine for most cases, but not for overnight scan performed on a
        29/2 for example.

        The solution is of course to have the timestamp saved correctly.

        Parameters
        ----------
        end_time_f : pathlib.Path
            the file used to get the end time

        Returns
        -------
        end_time_tz : str
            the end time in ISO 8601 format with time zone
        """
        num_projs = self._tot_num_proj(proj_file)

        with h5py.File(end_time_f, "r") as f:
            dset = dataset_from_first_valid_path(f, self.end_time_path)

            size = dset.shape[0]
            stride = size // num_projs
            offset = (int(proj_file.id_proj) + 1) * stride - 1
            end_time = dset[offset, 0, 0]

        # YY-MM-DD from file modification time
        # hh-mm-ss from the timestamp
        end_datetime = datetime.fromtimestamp(end_time,
                                              tz=timezone.utc)
        file_mtime = datetime.fromtimestamp(end_time_f.stat().st_mtime,
                                            tz=timezone.utc)
        end_time_tz = end_datetime.replace(year=file_mtime.year,
                                           month=file_mtime.month,
                                           day=file_mtime.day).isoformat()

        return end_time_tz
