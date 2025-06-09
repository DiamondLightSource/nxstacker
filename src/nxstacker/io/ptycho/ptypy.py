import re
from pathlib import Path
from types import MappingProxyType

import h5py
import numpy as np

from nxstacker.io.projection import ProjectionFile
from nxstacker.utils.io import is_staging_area, top_level_dir
from nxstacker.utils.model import (
    FilePath,
    FixedValue,
)


class PtyPyFile(ProjectionFile):
    """Represent a PtyPy reconstruction file."""

    experiment = "ptychography"
    software = "PtyPy"
    path_names = MappingProxyType(
        {
            "object": "/content/obj",
            "probe": "/content/probe",
            "scan_names": "/content/pars/scans",
        },
    )
    essential_paths = tuple(path_names.values())
    extensions = (".ptyr",)
    scan_name = FixedValue()
    storage_name = FixedValue()
    object_path = FixedValue()
    probe_path = FixedValue()
    raw_file_path = FixedValue()
    px_sz_path = FixedValue()
    raw_file = FilePath(must_exist=True)
    object_shape = FixedValue()
    object_complex_dtype = FixedValue()
    object_modulus_dtype = FixedValue()
    object_phase_dtype = FixedValue()
    probe_shape = FixedValue()
    probe_complex_dtype = FixedValue()
    probe_modulus_dtype = FixedValue()
    probe_phase_dtype = FixedValue()

    def __init__(
        self,
        file_path,
        id_scan=None,
        id_proj=None,
        *,
        verify=True,
        raw_dir=None,
        description=None,
    ):
        """Initialise an instance of PtyPy file.

        Parameters
        ----------
        file_path : pathlib.Path or str
            see ProjectionFile
        id_scan : str or None, optional
            the scan identifier of the reconstruction. If it is None, it
            tries to fetch this from the file and its attributes.
            Default to None.
        id_proj : str or None, optional
            the projection identifier of the reconstruction. If it is
            None, it tries to fetch this from the file and its
            attributes. Default to None.
        verify : bool, optional
            see ProjectionFile
        raw_dir : pathlib.Path or str, optional
            see ProjectionFile
        description : str, optional
            see ProjectionFile

        """
        super().__init__(
            file_path, verify=verify, raw_dir=raw_dir, description=description
        )

        self._compose_paths()

        if id_scan is None:
            self._id_scan = self._retrieve_id_scan()
        else:
            self._id_scan = str(id_scan)

        if id_proj is None:
            self._id_proj = self._retrieve_id_proj()
        else:
            self._id_proj = str(id_proj)

    def fill_attr(self):
        """Assign attributes as determined from the file."""
        if self.raw_dir is None:
            self._overwrite_raw_dir()

        self._ob_attr()
        self._pr_attr()

    def _retrieve_id_scan(self):
        # get the scan number from the raw file by matching them with
        # some regex
        regexes = (
            re.compile(r".*-(\d+)\.nxs$"),
            re.compile(r".*-(\d+)_processed\.nxs$"),
            re.compile(r".(\d+)\.ptyd$"),
        )

        for regex in regexes:
            match = re.search(regex, str(self._raw_file))
            if match is not None:
                # return the first match
                return match.group(1)
        # ideally some fallback here but raise for now
        msg = f"Cannot deduce scan numbers from {self._raw_file}"
        raise RuntimeError(msg)

    def _retrieve_id_proj(self):
        msg = (
            f"For {self.software} reconstruction file, it cannot get the "
            "projection ID from the file itself. It should be set by "
            "passing value to the argument 'id_proj' when initialising "
            "the instance."
        )
        raise TypeError(msg)

    def _compose_paths(self):
        with h5py.File(self._file_path, "r") as f:
            scans = list(f[self.path_names["scan_names"]])

            # assume one storage
            self.scan_name = scans[0]

            self.storage_name = f"S{self._scan_name}G00"
            self.object_path = (
                f"{self.path_names['object']}/{self._storage_name}/data"
            )
            self.probe_path = (
                f"{self.path_names['probe']}/{self._storage_name}/data"
            )
            self.raw_file_path = (
                f"{self.path_names['scan_names']}/"
                f"{self._scan_name}/data/intensities/file"
            )
            self.raw_dfile_path = (
                f"{self.path_names['scan_names']}/"
                f"{self._scan_name}/data/dfile"
            )
            self.px_sz_path = (
                f"{self.path_names['object']}/{self._storage_name}/_psize"
            )

            # get the path of the raw file
            try:
                self.raw_file = f[self.raw_file_path][()]
            except:
                self.raw_file = f[self.raw_dfile_path][()]
                
    def _overwrite_raw_dir(self):
        """Overwrite the _raw_dir attribute."""
        if is_staging_area(self._raw_file):
            depth = 8
        else:
            depth = 6

        raw_dir = top_level_dir(self._raw_file, depth=depth)

        if Path(raw_dir).is_dir():
            self._raw_dir = raw_dir
        else:
            # this is a fallback
            if is_staging_area(self._file_path):
                depth = 8
            else:
                depth = 6
            self._raw_dir = top_level_dir(self._file_path, depth=depth)

    def object_complex(self, mode=0):
        """Return the complex object of a particular mode.

        Parameters
        ----------
        mode : int, optional
            the mode of the complex object to be returned. Default to 0.

        """
        with h5py.File(self._file_path, "r") as f:
            ob = f[self._object_path]

            if mode < (num_modes := ob.shape[0]):
                obj = ob[mode, :, :]
            else:
                mode_str = "mode" + "s" * (num_modes > 1)
                msg = (
                    f"The object has {num_modes} {mode_str} and the "
                    f"maximum mode index is {num_modes-1}, but {mode} "
                    "was given."
                )
                raise IndexError(msg)
        return obj

    def object_modulus(self, mode=0):
        """Return the object modulus of a particular mode."""
        return np.abs(self.object_complex(mode=mode))

    def object_phase(self, mode=0):
        """Return the object phase of a particular mode."""
        return np.angle(self.object_complex(mode=mode))

    def _ob_attr(self):
        with h5py.File(self._file_path, "r") as f:
            self.object_shape = f[self._object_path].shape
            self.object_complex_dtype = f[self._object_path].dtype
            self.pixel_size = f[self._px_sz_path][()].mean()

        # don't want to perform np.abs and np.angle by reading the
        # actual complex data
        if self.object_complex_dtype == np.complex64:
            self.object_modulus_dtype = np.float32
            self.object_phase_dtype = np.float32
        else:
            self.object_modulus_dtype = np.float64
            self.object_phase_dtype = np.float64

    def probe_complex(self, mode=0):
        """Return the complex probe of a particular mode.

        Parameters
        ----------
        mode : int, optional
            the mode of the complex probe to be returned. Default to 0.

        """
        with h5py.File(self._file_path, "r") as f:
            pr = f[self._probe_path]

            if mode < (num_modes := pr.shape[0]):
                prb = pr[mode, :, :]
            else:
                mode_str = "mode" + "s" * (num_modes > 1)
                msg = (
                    f"The probe has {num_modes} {mode_str} and the "
                    f"maximum mode index is {num_modes-1}, but {mode} "
                    "was given."
                )
                raise IndexError(msg)
        return prb

    def probe_modulus(self, mode=0):
        """Return the probe modulus of a particular mode."""
        return np.abs(self.probe_complex(mode=mode))

    def probe_phase(self, mode=0):
        """Return the probe phase of a particular mode."""
        return np.angle(self.probe_complex(mode=mode))

    def _pr_attr(self):
        with h5py.File(self._file_path, "r") as f:
            self.probe_shape = f[self._probe_path].shape
            self.probe_complex_dtype = f[self._probe_path].dtype

        # don't want to perform np.abs and np.angle by reading the
        # actual complex data
        if self.probe_complex_dtype == np.complex64:
            self.probe_modulus_dtype = np.float32
            self.probe_phase_dtype = np.float32
        else:
            self.probe_modulus_dtype = np.float64
            self.probe_phase_dtype = np.float64

    @property
    def avail_complex(self):
        """Indicate whether the complex object/probe is available."""
        return True

    @property
    def avail_modulus(self):
        """Indicate whether the modulus of object/probe is available."""
        return True

    @property
    def avail_phase(self):
        """Indicate whether the phase of object/probe is available."""
        return True
