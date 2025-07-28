import random
from datetime import datetime
from pathlib import Path

import h5py
import numpy as np

from nxstacker.utils.model import XRFTransitionList


class PreparePtyPyFile:
    """Prepare minimal PtyPy file for testing."""

    def __init__(
        self,
        dest,
        scan_num,
        raw_files,
        ob_shape,
        x_px_size,
        y_px_size,
        scan_name=None,
        *,
        use_nxs=True,
    ):
        """Initialise the instance for preparation.

        Parameters
        ----------
        dest : str or pathlib.Path
            the directory to save the files
        scan_num : list
            the scan number(s) from which they are reconstructed
        raw_files : list
            the raw file(s) from which they are reconstructed
        ob_shape : iterable
            the 2D shape of the object
        x_px_size, y_px_size : float
            the x and y real-space pixel size
        scan_name : str, optional
            the scan name in a PtyPy configuration file. Default to
            None, set to "my_sample".
        use_nxs : str, optional
            if True, the raw file is .nxs instead of .ptyd. Default to
            True.

        """
        self.scan_num = scan_num
        self.raw_files = raw_files
        self.ob_sh = (2, *ob_shape)
        self.x_px_size = x_px_size
        self.y_px_size = y_px_size
        self.pr_sh = (2, 128, 128)

        # create directory to store the files
        self.proj_dir = Path(dest) / "proj_dir"
        self.proj_dir.mkdir(parents=True)

        if scan_name is None:
            self.scan_name = "my_sample"
        else:
            self.scan_name = scan_name
        self.storage = f"S{self.scan_name}G00"

        self.use_nxs = use_nxs
        self.proj_files = []

    def write_dummy_proj(self):
        """Save a minimal dummy PtyPy reconstruction file."""
        rng = np.random.default_rng()

        for sn, rf in zip(self.scan_num, self.raw_files, strict=False):
            fp = self.proj_dir / f"scan_{sn}.ptyr"

            with h5py.File(fp, "w") as f:
                if self.use_nxs:
                    f[
                        f"/content/pars/scans/{self.scan_name}/data/intensities/file"
                    ] = str(rf)
                else:
                    f[f"/content/pars/scans/{self.scan_name}/data/dfile"] = (
                        str(rf.parent.parent / f"processing/{sn}.ptyd")
                    )
                f[f"/content/obj/{self.storage}/data"] = rng.random(
                    self.ob_sh, dtype=np.float32
                ) + 1j * rng.random(self.ob_sh, dtype=np.float32)
                f[f"/content/probe/{self.storage}/data"] = rng.random(
                    self.pr_sh, dtype=np.float32
                ) + 1j * rng.random(self.pr_sh, dtype=np.float32)
                f[f"/content/obj/{self.storage}/_psize"] = (
                    self.y_px_size,
                    self.x_px_size,
                )

            self.proj_files.append(fp)


class PreparePtyREXFile:
    """Prepare minimal PtyREX file for testing."""

    def __init__(
        self,
        dest,
        scan_num,
        proj_num,
        ob_shape,
        x_px_size,
        y_px_size,
        detector_distance,
    ):
        """Initialise the instance for preparation.

        Parameters
        ----------
        dest : str or pathlib.Path
            the directory to save the files
        scan_num : int
            the scan number from which they are reconstructed
        proj_num : list
            the projection number(s) from which they are reconstructed
        raw_files : list
            the raw file(s) from which they are reconstructed
        ob_shape : iterable
            the 2D shape of the object
        x_px_size, y_px_size : float
            the x and y real-space pixel size
        detector_distance : float
            the sample-to-detector distance

        """
        self.scan_num = [scan_num] * len(proj_num)
        self.proj_num = proj_num
        self.ob_sh = (2, 2, 2, 2, 2, *ob_shape)
        self.x_px_size = x_px_size
        self.y_px_size = y_px_size
        self.pr_sh = (2, 2, 2, 2, 2, 128, 128)
        self.detector_distance = detector_distance

        # create directory to store the files
        self.proj_dir = Path(dest) / "proj_dir"
        self.proj_dir.mkdir(parents=True)

        self.proj_files = []
        self.prefix = ""

    def write_dummy_proj(self):
        """Save a minimal dummy PtyREX reconstruction file."""
        rng = np.random.default_rng()

        for sn, pn in zip(self.scan_num, self.proj_num, strict=False):
            ext = random.choice(("hdf", "hdf5", "h5"))  # noqa: S311
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")  # noqa: DTZ005
            fp = self.proj_dir / f"{self.prefix}_{sn}_{pn}_{timestamp}.{ext}"

            with h5py.File(fp, "w") as f:
                f["/entry_1/experiment_1/data/data_ID"] = str(pn)

                f["/entry_1/process_1/common_1/save_dir"] = str(self.proj_dir)

                f["/entry_1/process_1/common_1/dx"] = np.array(
                    [[self.y_px_size, self.x_px_size]]
                )

                f["/entry_1/process_1/output_1/object_modulus"] = rng.random(
                    self.ob_sh, dtype=np.float32
                )
                f["/entry_1/process_1/output_1/object_phase"] = rng.random(
                    self.ob_sh, dtype=np.float32
                )
                f["/entry_1/process_1/output_1/probe_modulus"] = rng.random(
                    self.pr_sh, dtype=np.float32
                )
                f["/entry_1/process_1/output_1/probe_phase"] = rng.random(
                    self.pr_sh, dtype=np.float32
                )

                f["/entry_1/experiment_1/detector/distance"] = (
                    self.detector_distance
                )

            self.proj_files.append(fp)


class PrepareXRFWindowFile:
    """Prepare minimal XRF window file from Python for testing."""

    line_groups = XRFTransitionList()

    def __init__(
        self,
        dest,
        scan_num,
        ob_shape,
        line_groups,
    ):
        """Initialise the instance for preparation.

        Parameters
        ----------
        dest : str or pathlib.Path
            the directory to save the files
        scan_num : list
            the scan number(s) from which they are reconstructed
        ob_shape : iterable
            the 2D shape of the elemental map
        line_groups : list
            the line groups that have been windowed

        """
        self.ob_sh = ob_shape
        self.scan_num = scan_num
        self.line_groups = line_groups

        # create directory to store the files
        self.proj_dir = Path(dest) / "proj_dir"
        self.proj_dir.mkdir(parents=True)

        self.proj_files = []

    def write_dummy_proj(self):
        """Save a minimal dummy XRF window file (i14)."""
        rng = np.random.default_rng()

        for sn in self.scan_num:
            fp = self.proj_dir / f"i14-{sn}_xrf.nxs"

            with h5py.File(fp, "w") as f:
                mca = rng.random((*self.ob_sh, 4096))
                f["/processed/mca/data"] = mca

                result = rng.random(self.ob_sh)
                f["/processed/result/data"] = result

                for lg in self.line_groups:
                    f[f"/processed/{lg}/data"] = rng.random(self.ob_sh)

            self.proj_files.append(fp)
