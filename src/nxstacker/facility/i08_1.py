from pathlib import Path

import h5py

from nxstacker.facility.facility import SPECS_DIR, FacilityInfo
from nxstacker.utils.io import dataset_from_first_valid_path


class I08_1(FacilityInfo): # noqa: N801

    name = "i08-1"

    def __init__(self, specs=None):
        super().__init__()

        self.specs = SPECS_DIR / "i08-1.yaml"
        if specs is not None:
            self.specs = Path(specs)

        self.populate_attr()
        self.metadata_file = {"ptychography": self.nxs_file,
                              }

    def nxs_file(self, raw_dir, scan_id):
        nxs_f = Path(f"{raw_dir}/nexus/i08-1-{scan_id}.nxs")
        if nxs_f.exists():
            return nxs_f
        msg = (f"The NeXus file {nxs_f} does not exist. Please "
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
        id_proj : int, optional
            not use by i08-1

        Returns
        -------
        rot_ang : float
            the rotation angle
        """
        rot_f_method = self.metadata_file.get(proj_file.experiment,
                                              self.nxs_file)
        rot_f = rot_f_method(proj_file.raw_dir, proj_file.id_scan)

        with h5py.File(rot_f, "r") as f:
            dset = dataset_from_first_valid_path(f, self.rotation_angle_path)
            rot_ang = dset[()]

        return rot_ang

    def sample_detector_dist(self, _):
        """
        """
        return 0.072
