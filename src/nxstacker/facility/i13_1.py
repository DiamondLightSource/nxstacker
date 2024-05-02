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
        self.metadata_file = {"ptychography": self.nxs_file,
                              }

    def nxs_file(self, raw_dir, scan_id):
        nxs_f = Path(f"{raw_dir}/raw/{scan_id}.nxs")
        if nxs_f.exists():
            return nxs_f
        msg = (f"The NeXus file {nxs_f} does not exist. Please "
                "check the raw data directory and scan ID to see "
                "if they match.")
        raise FileNotFoundError(msg)

    def pty_tomo_file(self, raw_dir, scan_id):
        pty_tomo_f = Path(f"{raw_dir}/raw/{scan_id}/raw/pty_tomo.h5")
        if pty_tomo_f.exists():
            return pty_tomo_f
        msg = (f"The pty_tomo file {pty_tomo_f} does not exist. Please "
                "check the raw data directory and scan ID to see "
                "if they match.")
        raise FileNotFoundError(msg)

    def rotation_angle(self, proj_file):
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
        metadata_file = {"ptychography": self.pty_tomo_file}
        # raise KeyError for experiment that is not supported
        rot_f_method = metadata_file[proj_file.experiment]
        rot_f = rot_f_method(proj_file.raw_dir, proj_file.id_scan)

        with h5py.File(rot_f, "r") as f:
            dset = dataset_from_first_valid_path(f, self.rotation_angle_path)
            rot_ang = dset[int(proj_file.id_proj), :, 0].mean()

        return rot_ang

    def sample_detector_dist(self, proj_file):
        """
        """
        # try the output file path first
        try:
            with h5py.File(proj_file.file_path, "r") as f:
                dset = dataset_from_first_valid_path(
                        f, self.detector_distance_path)
                dist = dset[()]
        except (FileNotFoundError, TypeError):
            # fail, go to the .nxs file
            dist_f_method = self.metadata_file.get(proj_file.experiment,
                                                   self.nxs_file)
            dist_f = dist_f_method(proj_file.raw_dir, proj_file.id_scan)

            with h5py.File(dist_f, "r") as f:
                dset = dataset_from_first_valid_path(
                        f, self.detector_distance_path)
                dist = dset[()]

        return dist
