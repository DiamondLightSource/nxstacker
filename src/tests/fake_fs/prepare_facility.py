from datetime import datetime, timezone
from pathlib import Path

import h5py
import numpy as np


class PrepareI14:
    """Prepare a standard i14 file structure for testing."""

    def __init__(
        self,
        root,
        start_scan,
        end_scan,
        visit_id=None,
        detector_distance=None,
        sample_name=None,
        rotation_angle=None,
        sample_x_value_set=None,
        sample_y_value_set=None,
    ):
        """Initialise the instance for preparation.

        Parameters
        ----------
        root : str or pathlib.Path
            the root of the visit
        start_scan : int or str
            the starting scan number
        end_scan : int or str
            the ending scan number
        visit_id : str, optional
            the visit ID. Default to None, set to "cm12345-6".
        detector_distance : float, optional
            the sample-to-detector distance. Default to None, set to
            1234.5.
        sample_name : str, optional
            the name of the sample. Default to None, set to "".
        rotation_angle : float, optional
            the rotation angle. Default to None, set to -31.8.
        sample_x_value_set, sample_y_value_set : ndarray
            the x and y value set. Default to ndarray with 21 elements
            for x and 31 elements for y.

        """
        self.start_scan = int(start_scan)
        self.end_scan = int(end_scan)

        if visit_id is None:
            self.visit_id = "cm12345-6"
        else:
            self.visit_id = visit_id

        if detector_distance is None:
            self.detector_distance = 1234.5
        else:
            self.detector_distance = detector_distance

        if sample_name is None:
            self.sample_name = ""
        else:
            self.sample_name = sample_name

        if rotation_angle is None:
            self.rotation_angle = -31.8
        else:
            self.rotation_angle = rotation_angle

        if sample_x_value_set is None:
            self.sample_x_value_set = np.linspace(-14, 14, num=21)
        else:
            self.sample_x_value_set = sample_x_value_set

        if sample_y_value_set is None:
            self.sample_y_value_set = np.linspace(-14, 14, num=31)
        else:
            self.sample_y_value_set = sample_y_value_set

        # create raw data directory
        self.visit = Path(root) / self.visit_id
        self.raw_data_dir = self.visit / "scan"
        self.raw_data_dir.mkdir(parents=True)

        self.raw_files = []
        self.scan_num = []

    def write_dummy_raw(self):
        """Save minimal i14 raw data."""
        for k in range(self.start_scan, self.end_scan + 1):
            fp = self.raw_data_dir / f"i14-{k}.nxs"

            # put dummy data
            with h5py.File(fp, "w") as f:
                # start time
                f["/entry/diamond_scan/start_time"] = datetime.now(
                    timezone.utc
                ).isoformat()

                # file name
                f["file_name"] = str(fp)

                # sample-detector distance
                f["/entry/instrument/detectors/excalibur_z"] = (
                    self.detector_distance
                )
                f["/entry/instrument/detectors/excalibur_z"].attrs["units"] = (
                    "mm"
                )
                f["/entry/instrument/scannables/excalibur_z/value"] = (
                    self.detector_distance
                )
                f["/entry/instrument/scannables/excalibur_z/value"].attrs[
                    "units"
                ] = "mm"

                # sample name
                f["/entry/sample"] = self.sample_name

                # rotation angle
                f["/entry/instrument/sample/sample_rot"] = self.rotation_angle
                f["/entry/instrument/sample/sample_rot"].attrs["units"] = "deg"
                f["/entry/instrument/scannables/stage1/stage1_rotation"] = (
                    self.rotation_angle
                )
                f["/entry/instrument/scannables/stage1/stage1_rotation"].attrs[
                    "units"
                ] = "deg"

                # sample x value set
                f["/entry/instrument/SampleX/value_set"] = (
                    self.sample_x_value_set
                )
                f["/entry/xsp3_addetector/SampleX_value_set"] = (
                    self.sample_x_value_set
                )
                f["/entry/merlin_addetector/SampleX_value_set"] = (
                    self.sample_x_value_set
                )
                f["/entry/eiger_addetector/SampleX_value_set"] = (
                    self.sample_x_value_set
                )
                f["/entry/excalibur_addetector/SampleX_value_set"] = (
                    self.sample_x_value_set
                )

                # sample y value set
                f["/entry/instrument/SampleY/value_set"] = (
                    self.sample_y_value_set
                )
                f["/entry/xsp3_addetector/SampleY_value_set"] = (
                    self.sample_y_value_set
                )
                f["/entry/merlin_addetector/SampleY_value_set"] = (
                    self.sample_y_value_set
                )
                f["/entry/eiger_addetector/SampleY_value_set"] = (
                    self.sample_y_value_set
                )
                f["/entry/excalibur_addetector/SampleY_value_set"] = (
                    self.sample_y_value_set
                )

                # end time
                f["/entry/diamond_scan/end_time"] = datetime.now(
                    timezone.utc
                ).isoformat()

            self.raw_files.append(fp)
            self.scan_num.append(k)


class PrepareI08_1:  # noqa: N801
    """Prepare a standard i08-1 file structure for testing."""

    def __init__(
        self,
        root,
        start_scan,
        end_scan,
        visit_id=None,
        detector_distance=None,
        sample_name=None,
        rotation_angle=None,
        sample_x_value_set=None,
        sample_y_value_set=None,
    ):
        """Initialise the instance for preparation.

        Parameters
        ----------
        root : str or pathlib.Path
            the root of the visit
        start_scan : int or str
            the starting scan number
        end_scan : int or str
            the ending scan number
        visit_id : str, optional
            the visit ID. Default to None, set to "cm12345-6".
        detector_distance : float, optional
            the sample-to-detector distance. Default to None, set to
            1234.5.
        sample_name : str, optional
            the name of the sample. Default to None, set to "".
        rotation_angle : float, optional
            the rotation angle. Default to None, set to -31.8.
        sample_x_value_set, sample_y_value_set : ndarray
            the x and y value set. Default to ndarray with 21 elements
            for x and 31 elements for y.

        """
        self.start_scan = int(start_scan)
        self.end_scan = int(end_scan)

        if visit_id is None:
            self.visit_id = "cm12345-6"
        else:
            self.visit_id = visit_id

        if detector_distance is None:
            self.detector_distance = 1234.5
        else:
            self.detector_distance = detector_distance

        if sample_name is None:
            self.sample_name = ""
        else:
            self.sample_name = sample_name

        if rotation_angle is None:
            self.rotation_angle = -31.8
        else:
            self.rotation_angle = rotation_angle

        if sample_x_value_set is None:
            self.sample_x_value_set = np.linspace(-14, 14, num=21)
        else:
            self.sample_x_value_set = sample_x_value_set

        if sample_y_value_set is None:
            self.sample_y_value_set = np.linspace(-14, 14, num=31)
        else:
            self.sample_y_value_set = sample_y_value_set

        # create raw data directory
        self.visit = Path(root) / self.visit_id
        self.raw_data_dir = self.visit / "nexus"
        self.raw_data_dir.mkdir(parents=True)

        self.raw_files = []
        self.scan_num = []

    def write_dummy_raw(self):
        """Save minimal i08-1 raw data."""
        for k in range(self.start_scan, self.end_scan + 1):
            fp = self.raw_data_dir / f"i08-1-{k}.nxs"

            # put dummy data
            with h5py.File(fp, "w") as f:
                # start time
                f["/entry/diamond_scan/start_time"] = datetime.now(
                    timezone.utc
                ).isoformat()

                # file name
                f["file_name"] = str(fp)

                # sample name
                f["/entry/sample/name"] = self.sample_name

                # rotation angle
                f["/entry/instrument/sample_rotation/value"] = (
                    self.rotation_angle
                )
                f["/entry/instrument/sample_rotation/value"].attrs["units"] = (
                    "deg"
                )

                # end time
                f["/entry/diamond_scan/end_time"] = datetime.now(
                    timezone.utc
                ).isoformat()

            self.raw_files.append(fp)
            self.scan_num.append(k)


class PrepareI13_1:  # noqa: N801
    """Prepare a standard i13-1 file structure for testing."""

    def __init__(
        self,
        root,
        scan,
        start_proj,
        end_proj,
        visit_id=None,
        detector_distance=None,
        sample_name=None,
        rotation_angle=None,
        sample_x_value_set=None,
        sample_y_value_set=None,
    ):
        """Initialise the instance for preparation.

        Parameters
        ----------
        root : str or pathlib.Path
            the root of the visit
        scan : int or str
            the scan number
        start_proj : int or str
            the starting projection number
        end_proj : int or str
            the ending projection number
        visit_id : str, optional
            the visit ID. Default to None, set to "cm12345-6".
        detector_distance : float, optional
            the sample-to-detector distance. Default to None, set to
            1234.5.
        sample_name : str, optional
            the name of the sample. Default to None, set to "".
        rotation_angle : float, optional
            the rotation angle. Default to None, set to -31.8.
        sample_x_value_set, sample_y_value_set : ndarray
            the x and y value set. Default to ndarray with 21 elements
            for x and 31 elements for y.

        """
        self.scan = int(scan)
        self.start_proj = int(start_proj)
        self.end_proj = int(end_proj)
        self.projs = list(range(self.start_proj, self.end_proj + 1))

        if visit_id is None:
            self.visit_id = "cm12345-6"
        else:
            self.visit_id = visit_id

        if detector_distance is None:
            self.detector_distance = 1234.5
        else:
            self.detector_distance = detector_distance

        if sample_name is None:
            self.sample_name = "undefined"
        else:
            self.sample_name = sample_name

        if rotation_angle is None:
            self.rotation_angle = -31.8
        else:
            self.rotation_angle = rotation_angle

        if sample_x_value_set is None:
            self.sample_x_value_set = np.linspace(-14, 14, num=21)
        else:
            self.sample_x_value_set = sample_x_value_set

        if sample_y_value_set is None:
            self.sample_y_value_set = np.linspace(-14, 14, num=31)
        else:
            self.sample_y_value_set = sample_y_value_set

        # create raw data directory
        self.visit = Path(root) / self.visit_id
        self.raw_data_dir = self.visit / f"raw/{self.scan}/raw"
        self.raw_data_dir.mkdir(parents=True)

        self.nxs_f = None
        self.pos_f = None
        self.pty_tomo_f = None

    def write_dummy_raw(self):
        """Save minimal i13-1 raw data."""
        rng = np.random.default_rng()

        # save NeXus
        nxs_dir = self.raw_data_dir.parent.parent
        nxs_fp = nxs_dir / f"{self.scan}.nxs"

        with h5py.File(nxs_fp, "w") as f:
            f["/entry1/title"] = self.sample_name
            f["/entry1/experiment_identifier"] = self.visit_id
            f["/entry1/entry_identifier"] = self.scan
            # in mm here
            f["/entry1/before_scan/t2/t2_z"] = self.detector_distance * 1000

        # save pty_tomo
        pty_tomo_fp = self.raw_data_dir / "pty_tomo.h5"
        xy_size = self.sample_x_value_set.size * self.sample_y_value_set.size
        nproj = len(self.projs)
        data_scan = rng.random((nproj, xy_size, 4))
        data_scan[:, :, 0] = self.rotation_angle
        # use much smaller frame size for test data, not (514, 1030)
        data_frames = rng.random((nproj, xy_size, 5, 10))
        with h5py.File(pty_tomo_fp, "w") as f:
            f["/data/scan"] = data_scan
            f["/data/frames"] = data_frames

        # save position_0
        pos_fp = self.raw_data_dir / "positions_0.h5"
        # just some random time
        timestamp = np.empty((nproj * xy_size, 1, 1))
        timestamp[:] = datetime.now().timestamp()  # noqa: DTZ005
        with h5py.File(pos_fp, "w") as f:
            f["/entry/instrument/NDAttributes/NDArrayTimeStamp"] = timestamp

        self.nxs_f = nxs_fp
        self.pty_tomo_f = pty_tomo_fp
        self.pos_f = pos_fp
