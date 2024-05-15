from pathlib import Path

import h5py

from nxstacker.facility.facility import SPECS_DIR, FacilityInfo
from nxstacker.utils.io import dataset_from_first_valid_path
from nxstacker.utils.parse import add_timezone


class I08_1(FacilityInfo):  # noqa: N801
    """Facility information for i08-1."""

    name = "i08-1"

    def __init__(self, specs=None):
        """Initialise the i08-1 facility information.

        Parameters
        ----------
        specs : str or pathlib.Path, optional
            addition YAML specification to the facility. Default to
            None.

        """
        super().__init__()

        self.specs = SPECS_DIR / "i08-1.yaml"
        if specs is not None:
            self.specs = Path(specs)

        self.populate_attr()

    def nxs_file(self, proj_file):
        """Return the path of NeXus file of a given projection file.

        Parameters
        ----------
        proj_file : ProjectionFile
            the projection file

        Returns
        -------
        nxs_f : pathlib.Path
            the path of the NeXus file

        """
        raw_dir = proj_file.raw_dir
        scan_id = proj_file.id_scan

        nxs_f = Path(f"{raw_dir}/nexus/i08-1-{scan_id}.nxs")
        if nxs_f.exists():
            return nxs_f
        msg = (
            f"The NeXus file {nxs_f} does not exist. Please "
            "check the raw data directory and scan ID to see "
            "if they match."
        )
        raise FileNotFoundError(msg)

    def rotation_angle(self, rot_f, _):
        """Retrieve rotation angle.

        The extra argument "_" is unused and acts as a placeholder so
        there is a consistent interface across all FacilityInfo.

        Parameters
        ----------
        rot_f : str or pathlib.Path
            the file from which the rotation angle is retrieved

        Returns
        -------
        rot_ang : float
            the rotation angle, in degree

        """
        with h5py.File(rot_f, "r") as f:
            dset = dataset_from_first_valid_path(f, self.rotation_angle_path)
            rot_ang = dset[()]

        return rot_ang

    def sample_detector_dist(self, _=None):
        """Return the sample-detector distance which is a constant."""
        return 0.072

    def start_time(self, start_time_f, _):
        """Retrieve the start time.

        The extra argument "_" is unused and acts as a placeholder so
        there is a consistent interface across all FacilityInfo.

        Parameters
        ----------
        start_time_f : str or pathlib.Path
            the file from which the start time is retrieved

        Returns
        -------
        start_time_tz : str
            timestamp of the start time, in ISO 8601

        """
        with h5py.File(start_time_f, "r") as f:
            dset = dataset_from_first_valid_path(f, self.start_time_path)
            start_time = dset[()]

        if isinstance(start_time, bytes):
            start_time = start_time.decode()

        start_time_tz = add_timezone(start_time)

        return start_time_tz

    def end_time(self, end_time_f, _):
        """Retrieve the end time.

        The extra argument "_" is unused and acts as a placeholder so
        there is a consistent interface across all FacilityInfo.

        Parameters
        ----------
        end_time_f : str or pathlib.Path
            the file from which the end time is retrieved

        Returns
        -------
        end_time_tz : str
            timestamp of the end time, in ISO 8601

        """
        with h5py.File(end_time_f, "r") as f:
            dset = dataset_from_first_valid_path(f, self.end_time_path)
            end_time = dset[()]

        if isinstance(end_time, bytes):
            end_time = end_time.decode()

        end_time_tz = add_timezone(end_time)

        return end_time_tz
