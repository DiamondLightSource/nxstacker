import re
from pathlib import Path
from types import MappingProxyType

import h5py
import numpy as np

from nxstacker.io.projection import ProjectionFile
from nxstacker.utils.io import is_staging_area, top_level_dir
from nxstacker.utils.model import (
    FixedValue,
)


class PtyREXFile(ProjectionFile):
    """Represent a PtyREX reconstruction file."""

    experiment = "ptychography"
    software = "PtyREX"
    path_names = MappingProxyType(
        {
            "object_modulus": "/entry_1/process_1/output_1/object_modulus",
            "object_phase": "/entry_1/process_1/output_1/object_phase",
            "probe_modulus": "/entry_1/process_1/output_1/probe_modulus",
            "probe_phase": "/entry_1/process_1/output_1/probe_phase",
            "id_proj": "/entry_1/experiment_1/data/data_ID",
            "save_dir": "/entry_1/process_1/common_1/save_dir",
            "pixel_size": "/entry_1/process_1/common_1/dx",
        },
    )
    essential_paths = tuple(path_names.values())
    extensions = (".hdf", ".hdf5", ".h5")
    pad_value_modulus = 1
    pad_value_phase = 0
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
        """Initialise an instance of PtyREX file.

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
        # PtyREX output file has the name hardcoded, with the format
        # <PREFIX>_<SCAN_NUM>_<PROJ_NUM>_<TIMESTAMP>.hdf
        # although nothing prevent people from changing the file name,
        # it is sufficiently reasonable to deduce its scan number from
        # the output file name. In case of failure, raise
        filename = self._file_path.name
        regex = re.compile(r"\w*_(\d+)_\d+_.*\.(?:hdf|hdf5|h5|)")
        match = re.search(regex, filename)
        if match is not None:
            id_scan = match.group(1)
        else:
            msg = (
                "Fail to deduce scan number from the file name "
                "{self._file_path}. It can be set by passing value "
                "to the argument 'id_scan' when initialising "
                "the instance."
            )
            raise RuntimeError(msg)

        return id_scan

    def _retrieve_id_proj(self):
        with h5py.File(self._file_path, "r") as f:
            id_proj = f[self.path_names["id_proj"]][()]

        if isinstance(id_proj, bytes):
            id_proj = id_proj.decode()

        return id_proj

    def _overwrite_raw_dir(self):
        """Overwrite the _raw_dir attribute."""
        # check save_dir first
        with h5py.File(self._file_path, "r") as f:
            save_dir = f[self.path_names["save_dir"]][()]
        if isinstance(save_dir, bytes):
            save_dir = save_dir.decode()

        if is_staging_area(save_dir):
            depth = 8
        else:
            depth = 6

        raw_dir = top_level_dir(save_dir, depth=depth)

        if Path(raw_dir).is_dir():
            self._raw_dir = raw_dir
        else:
            # this is a fallback
            if is_staging_area(self._file_path):
                depth = 8
            else:
                depth = 6
            self._raw_dir = top_level_dir(self._file_path, depth=depth)

    def _pad_extent(self, img, pad_value=0):
        """Return the extent of padding for PtyREX file."""
        is_padded = np.isclose(img, pad_value)

        y_extent = is_padded.all(axis=1)
        top = np.argmin(y_extent)
        bottom = img.shape[0] - np.argmin(y_extent[::-1])

        x_extent = is_padded.all(axis=0)
        left = np.argmin(x_extent)
        right = img.shape[1] - np.argmin(x_extent[::-1])

        return top, bottom, left, right

    def object_complex(self, _):
        """PtyREX file does not save the complex object."""
        msg = (
            "The complex object is not currently saved in reconstruction "
            f"from {self.software}."
        )
        raise TypeError(msg)

    def object_modulus(self, mode=0):
        """Return the object modulus of a particular mode.

        Parameters
        ----------
        mode : int, optional
            the mode of the object modulus to be returned. Default to 0.

        """
        with h5py.File(self._file_path, "r") as f:
            ob_mod = f[self.path_names["object_modulus"]]

            if mode < (num_modes := ob_mod.shape[0]):
                # ignore all other channels
                ob_modulus = ob_mod[mode, 0, 0, 0, 0, :, :]
            else:
                mode_str = "mode" + "s" * (num_modes > 1)
                msg = (
                    f"The object modulus has {num_modes} {mode_str} and "
                    f"the maximum mode index is {num_modes-1}, but {mode} "
                    "was given."
                )
                raise IndexError(msg)

        if self.trim_proj:
            top, bottom, left, right = self._pad_extent(
                ob_modulus,
                self.pad_value_modulus,
            )
            ob_modulus = ob_modulus[top:bottom, left:right]

        return ob_modulus

    def object_phase(self, mode=0):
        """Return the object phase of a particular mode.

        Parameters
        ----------
        mode : int, optional
            the mode of the object phase to be returned. Default to 0.

        """
        with h5py.File(self._file_path, "r") as f:
            ob_ang = f[self.path_names["object_phase"]]

            if mode < (num_modes := ob_ang.shape[0]):
                # ignore all other channels
                ob_phase = ob_ang[mode, 0, 0, 0, 0, :, :]
            else:
                mode_str = "mode" + "s" * (num_modes > 1)
                msg = (
                    f"The object phase has {num_modes} {mode_str} and "
                    f"the maximum mode index is {num_modes-1}, but {mode} "
                    "was given."
                )
                raise IndexError(msg)

        if self.trim_proj:
            top, bottom, left, right = self._pad_extent(
                ob_phase,
                self.pad_value_phase,
            )
            ob_phase = ob_phase[top:bottom, left:right]

        return ob_phase

    def _ob_attr(self):
        pn = self.path_names
        with h5py.File(self._file_path, "r") as f:
            if self.trim_proj:
                self.object_shape = self.object_phase().shape
            else:
                self.object_shape = f[pn["object_modulus"]].shape

            self.object_modulus_dtype = f[pn["object_modulus"]].dtype
            self.object_phase_dtype = f[pn["object_phase"]].dtype
            self.pixel_size = f[pn["pixel_size"]][()].mean()

        if (
            self.object_modulus_dtype == np.float32
            and self.object_phase_dtype == np.float32
        ):
            self.object_complex_dtype = np.complex64
        else:
            self.object_complex_dtype = np.complex128

    def probe_complex(self, _):
        """PtyREX file does not save the complex probe."""
        msg = (
            "The complex probe is not currently saved in reconstruction "
            f"from {self.software}."
        )
        raise TypeError(msg)

    def probe_modulus(self, mode=0):
        """Return the probe modulus of a particular mode.

        Parameters
        ----------
        mode : int, optional
            the mode of the probe modulus to be returned. Default to 0.

        """
        with h5py.File(self._file_path, "r") as f:
            pr_mod = f[self.path_names["probe_modulus"]]

            if mode < (num_modes := pr_mod.shape[0]):
                # ignore all other channels
                pr_modulus = pr_mod[mode, 0, 0, 0, 0, :, :]
            else:
                mode_str = "mode" + "s" * (num_modes > 1)
                msg = (
                    f"The probe modulus has {num_modes} {mode_str} and "
                    f"the maximum mode index is {num_modes-1}, but {mode} "
                    "was given."
                )
                raise IndexError(msg)
        return pr_modulus

    def probe_phase(self, mode=0):
        """Return the probe phase of a particular mode.

        Parameters
        ----------
        mode : int, optional
            the mode of the probe phase to be returned. Default to 0.

        """
        with h5py.File(self._file_path, "r") as f:
            pr_ang = f[self.path_names["probe_phase"]]

            if mode < (num_modes := pr_ang.shape[0]):
                # ignore all other channels
                pr_phase = pr_ang[mode, 0, 0, 0, 0, :, :]
            else:
                mode_str = "mode" + "s" * (num_modes > 1)
                msg = (
                    f"The probe phase has {num_modes} {mode_str} and "
                    f"the maximum mode index is {num_modes-1}, but {mode} "
                    "was given."
                )
                raise IndexError(msg)
        return pr_phase

    def _pr_attr(self):
        pn = self.path_names
        with h5py.File(self._file_path, "r") as f:
            self.probe_shape = f[pn["probe_modulus"]].shape
            self.probe_modulus_dtype = f[pn["probe_modulus"]].dtype
            self.probe_phase_dtype = f[pn["probe_phase"]].dtype

        if (
            self.probe_modulus_dtype == np.float32
            and self.probe_phase_dtype == np.float32
        ):
            self.probe_complex_dtype = np.complex64
        else:
            self.probe_complex_dtype = np.complex128

    @property
    def avail_complex(self):
        """Indicate whether the complex object/probe is available."""
        return False

    @property
    def avail_modulus(self):
        """Indicate whether the modulus of object/probe is available."""
        return True

    @property
    def avail_phase(self):
        """Indicate whether the phase of object/probe is available."""
        return True
