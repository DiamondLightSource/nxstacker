from pathlib import Path

import h5py
import numpy as np


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

        self.proj_files = []

    def write_dummy_proj(self):
        """Save a minimal dummy PtyPy reconstruction file."""
        rng = np.random.default_rng()

        for sn, rf in zip(self.scan_num, self.raw_files, strict=False):
            fp = self.proj_dir / f"scan_{sn}.ptyr"

            with h5py.File(fp, "w") as f:
                f[
                    f"/content/pars/scans/{self.scan_name}/data/intensities/file"
                ] = str(rf)
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
