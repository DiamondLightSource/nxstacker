from pathlib import Path

import h5py
import numpy as np

from nxstacker.facility.facility import SPECS_DIR, FacilityInfo
from nxstacker.utils.io import (
    dataset_from_first_valid_path,
    files_first_exist,
)
from nxstacker.utils.parse import (
    add_timezone,
    as_dls_staging_area,
    quote_iterable,
)


class I14(FacilityInfo):
    """Facility information for i14."""

    name = "i14"

    def __init__(self, specs=None):
        """Initialise the i14 facility information.

        Parameters
        ----------
        specs : str or pathlib.Path, optional
            addition YAML specification to the facility. Default to
            None.

        """
        super().__init__()

        self.specs = SPECS_DIR / "i14.yaml"
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

        standard = Path(f"{raw_dir}/scan/i14-{scan_id}.nxs")

        nxs_candidates = [
            standard,
            as_dls_staging_area(standard),
            Path(f"{raw_dir}/i14-{scan_id}.nxs"),
        ]

        nxs_f = files_first_exist(nxs_candidates)

        if nxs_f is not None:
            return nxs_f

        fs = quote_iterable(list(dict.fromkeys(nxs_candidates)))
        msg = (
            "No valid NeXus file can be found. These are the locations that "
            f"have been tried: {fs}"
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

    def sample_detector_dist(self, dist_f):
        """Retrieve the distance between the sample and detector.

        Parameters
        ----------
        dist_f : str or pathlib.Path
            the file from which the distance is retrieved

        Returns
        -------
        dist : float
            the distance, in m

        """
        with h5py.File(dist_f, "r") as f:
            dset = dataset_from_first_valid_path(
                f, self.detector_distance_path
            )
            dist = dset[()] * 1e-3

        return dist

    def x_pixel_size(self, px_f):
        """Retrieve the x pixel size.

        Parameters
        ----------
        px_f : str or pathlib.Path
            the file from which the x pixel size is retrieved

        Returns
        -------
        x_px_sz : float
            the x pixel size, in m

        """
        with h5py.File(px_f, "r") as f:
            dset = dataset_from_first_valid_path(
                f, self.sample_x_value_set_path
            )
            x_value_set = dset[()]

        x_px_sz = np.diff(x_value_set).mean() * 1e-3

        return x_px_sz

    def y_pixel_size(self, px_f):
        """Retrieve the y pixel size.

        Parameters
        ----------
        px_f : str or pathlib.Path
            the file from which the y pixel size is retrieved

        Returns
        -------
        y_px_sz : float
            the y pixel size, in m

        """
        with h5py.File(px_f, "r") as f:
            dset = dataset_from_first_valid_path(
                f, self.sample_y_value_set_path
            )
            y_value_set = dset[()]

        y_px_sz = np.diff(y_value_set).mean() * 1e-3

        return y_px_sz

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
