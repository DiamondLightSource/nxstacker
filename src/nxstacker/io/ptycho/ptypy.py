import re
from pathlib import Path
from types import MappingProxyType

import h5py
import numpy as np

from nxstacker.utils.io import file_has_paths, top_level_dir
from nxstacker.utils.model import (
    Directory,
    FilePath,
    FixedValue,
    PositiveNumber,
)
from nxstacker.utils.parse import quote_iterable


class PtyPyFile:
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
    file_path = FilePath(must_exist=True)
    scan_name = FixedValue()
    storage_name = FixedValue()
    object_path = FixedValue()
    probe_path = FixedValue()
    raw_file_path = FixedValue()
    px_sz_path = FixedValue()
    raw_file = FilePath(must_exist=True)
    id_scan = FixedValue()
    id_proj = FixedValue()
    id_angle = FixedValue()
    distance = PositiveNumber(float)
    pixel_size = PositiveNumber(float)
    description = FixedValue()
    trim_proj = FixedValue()
    raw_dir = Directory(undefined_ok=True, must_exist=True)
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
            the file path of the reconstruction file.
        id_scan : str or None, optional
            the scan identifier of the reconstruction. If it is None, it
            tries to fetch this from the file and its attributes.
            Default to None.
        id_proj : str or None, optional
            the projection identifier of the reconstruction. If it is
            None, it tries to fetch this from the file and its
            attributes. Default to None.
        verify : bool, optional
            whether to verify the reconstruction file contains a minimum
            set of keys specific to the software from it is produced.
            Default to True.
        raw_dir : pathlib.Path or str, optional
            the directory that stores the raw data of this
            reconstruction.  Default to None, and it will be deduced
            from the attributes of the reconstruction file.
        description : str, optional
            a meaningful description about the sample of the
            reconstruction. Default to None.

        """
        self.file_path = file_path

        if verify and not self.verify_file():
            paths = quote_iterable(self.essential_paths)
            msg = (
                f"The file {self._file_path} is not a reconstruction "
                f"from {self.software}. Does the file have all the "
                f"following path names: {paths}?"
            )
            raise KeyError(msg)

        self._compose_paths()

        if id_scan is None:
            self.id_scan = self._retrieve_id_scan()
        else:
            self.id_scan = str(id_scan)

        if id_proj is None:
            self.id_proj = self._retrieve_id_proj()
        else:
            self.id_proj = str(id_proj)

        # the rotation angle is not known at this stage
        # this is available from the raw data file and retrieval of it
        # depends on the facility
        self.id_angle = None

        self.raw_dir = raw_dir
        self.description = description
        self.trim_proj = True

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
            self.px_sz_path = (
                f"{self.path_names['object']}/{self._storage_name}/_psize"
            )

            # get the path of the raw file
            self.raw_file = f[self._raw_file_path][()]

    def _overwrite_raw_dir(self):
        """Overwrite the _raw_dir attribute."""
        raw_dir = top_level_dir(self._raw_file)

        if Path(raw_dir).is_dir():
            self._raw_dir = raw_dir
        else:
            self._raw_dir = top_level_dir(self._file_path)

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

    def verify_file(self):
        """Check existence of some essential hdf5 paths."""
        return file_has_paths(self._file_path, self.essential_paths)

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

    def __str__(self):
        return f"{self.software} file: {self._file_path}"

    def __repr__(self):
        cls_name = type(self).__name__
        id_angle = (
            f"id_angle={self._id_angle}" if self._id_angle is not None else ""
        )
        return (
            f"{cls_name}(file_path='{self._file_path}',"
            f"id_scan='{self._id_scan}',"
            f"id_proj='{self._id_proj}'{id_angle})"
        )
