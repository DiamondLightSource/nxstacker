import re
from pathlib import Path
from types import MappingProxyType

import h5py
import numpy as np

from nxstacker.utils.io import file_has_paths, top_level_dir
from nxstacker.utils.parse import quote_iterable


class PtyREXFile:

    experiment = "ptychography"
    software = "PtyREX"
    path_names = MappingProxyType(
            {"object_modulus": "/entry_1/process_1/output_1/object_modulus",
             "object_phase": "/entry_1/process_1/output_1/object_phase",
             "probe_modulus": "/entry_1/process_1/output_1/probe_modulus",
             "probe_phase": "/entry_1/process_1/output_1/probe_phase",
             "id_proj": "/entry_1/experiment_1/data/data_ID",
             "save_dir": "/entry_1/process_1/common_1/save_dir",
             "pixel_size": "/entry_1/process_1/common_1/dx",
             })
    essential_paths = tuple(path_names.values())
    extensions = (".hdf", ".hdf5", ".h5")

    def __init__(self, file_path, id_scan=None, id_proj=None, *, verify=True):
        self._file_path = Path(file_path)

        if verify and not self.verify_file():
            paths = quote_iterable(self.essential_paths)
            msg = (f"The file {self._file_path} is not a reconstruction "
                   f"from {self.software}. Does the file have all the "
                   f"following path names: {paths}?")
            raise KeyError(msg)

        if id_scan is None:
            self._id_scan = self._retrieve_id_scan()
        else:
            self._id_scan = str(id_scan)

        if id_proj is None:
            self._id_proj = self._retrieve_id_proj()
        else:
            self._id_proj = str(id_proj)

        # these are not known at this stage
        self._id_angle = None
        self._distance = None
        self._pixel_size = None
        self.description = None

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
            msg = ("Fail to deduce scan number from the file name "
                    "{self._file_path}. It can be set by passing value "
                    "to the argument 'id_scan' when initialising "
                    "the instance.")
            raise RuntimeError(msg)

        return id_scan

    def _retrieve_id_proj(self):
        with h5py.File(self._file_path, "r") as f:
            id_proj = f[self.path_names["id_proj"]][()]

        if isinstance(id_proj, bytes):
            id_proj = id_proj.decode()

        return id_proj

    def find_raw_dir(self):
        # check save_dir first
        with h5py.File(self._file_path, "r") as f:
            save_dir = f[self.path_names["save_dir"]][()]
        if isinstance(save_dir, bytes):
            save_dir = save_dir.decode()

        raw_dir = top_level_dir(save_dir)

        if Path(raw_dir).is_dir():
            self._raw_dir = raw_dir
        else:
            self._raw_dir = top_level_dir(self._file_path)

    def object_complex(self, _):
        msg = ("The complex object is not currently saved in reconstruction "
               f"from {self.software}.")
        raise TypeError(msg)

    def object_modulus(self, mode=0):
        with h5py.File(self._file_path, "r") as f:
            ob_mod = f[self.path_names["object_modulus"]]

            if mode < (num_modes := ob_mod.shape[0]):
                # ignore all other channels
                ob_modulus = ob_mod[mode, 0, 0, 0, 0, :, :]
            else:
                mode_str = "mode" + "s"*(num_modes>1)
                msg = (f"The object modulus has {num_modes} {mode_str} and "
                       f"the maximum mode index is {num_modes-1}, but {mode} "
                        "was given.")
                raise IndexError(msg)
        return ob_modulus

    def object_phase(self, mode=0):
        with h5py.File(self._file_path, "r") as f:
            ob_ang = f[self.path_names["object_phase"]]

            if mode < (num_modes := ob_ang.shape[0]):
                # ignore all other channels
                ob_phase = ob_ang[mode, 0, 0, 0, 0, :, :]
            else:
                mode_str = "mode" + "s"*(num_modes>1)
                msg = (f"The object phase has {num_modes} {mode_str} and "
                       f"the maximum mode index is {num_modes-1}, but {mode} "
                        "was given.")
                raise IndexError(msg)
        return ob_phase

    def _ob_attr(self):
        pn = self.path_names
        with h5py.File(self._file_path, "r") as f:
            self._object_shape = f[pn["object_modulus"]].shape
            self._object_modulus_dtype = f[pn["object_modulus"]].dtype
            self._object_phase_dtype = f[pn["object_phase"]].dtype
            self._pixel_size = f[pn["pixel_size"]][()].mean()

        if (self._object_modulus_dtype == np.float32 and
            self._object_phase_dtype == np.float32):
            self._object_complex_dtype = np.complex64
        else:
            self._object_complex_dtype = np.complex128

    def probe_complex(self, _):
        msg = ("The complex probe is not currently saved in reconstruction "
               f"from {self.software}.")
        raise TypeError(msg)

    def probe_modulus(self, mode=0):
        with h5py.File(self._file_path, "r") as f:
            pr_mod = f[self.path_names["probe_modulus"]]

            if mode < (num_modes := pr_mod.shape[0]):
                # ignore all other channels
                pr_modulus = pr_mod[mode, 0, 0, 0, 0, :, :]
            else:
                mode_str = "mode" + "s"*(num_modes>1)
                msg = (f"The probe modulus has {num_modes} {mode_str} and "
                       f"the maximum mode index is {num_modes-1}, but {mode} "
                        "was given.")
                raise IndexError(msg)
        return pr_modulus

    def probe_phase(self, mode=0):
        with h5py.File(self._file_path, "r") as f:
            pr_ang = f[self.path_names["probe_phase"]]

            if mode < (num_modes := pr_ang.shape[0]):
                # ignore all other channels
                pr_phase = pr_ang[mode, 0, 0, 0, 0, :, :]
            else:
                mode_str = "mode" + "s"*(num_modes>1)
                msg = (f"The probe phase has {num_modes} {mode_str} and "
                       f"the maximum mode index is {num_modes-1}, but {mode} "
                        "was given.")
                raise IndexError(msg)
        return pr_phase

    def _pr_attr(self):
        pn = self.path_names
        with h5py.File(self._file_path, "r") as f:
            self._probe_shape = f[pn["probe_modulus"]].shape
            self._probe_modulus_dtype = f[pn["probe_modulus"]].dtype
            self._probe_phase_dtype = f[pn["probe_phase"]].dtype

        if (self._probe_modulus_dtype == np.float32 and
            self._probe_phase_dtype == np.float32):
            self._probe_complex_dtype = np.complex64
        else:
            self._probe_complex_dtype = np.complex128

    def verify_file(self):
        return file_has_paths(self._file_path, self.essential_paths)

    @property
    def file_path(self):
        return self._file_path

    @property
    def raw_dir(self):
        return self._raw_dir

    @property
    def object_shape(self):
        return self._object_shape

    @property
    def object_complex_dtype(self):
        return self._object_complex_dtype

    @property
    def object_modulus_dtype(self):
        return self._object_modulus_dtype

    @property
    def object_phase_dtype(self):
        return self._object_phase_dtype

    @property
    def probe_shape(self):
        return self._probe_shape

    @property
    def probe_complex_dtype(self):
        return self._probe_complex_dtype

    @property
    def probe_modulus_dtype(self):
        return self._probe_modulus_dtype

    @property
    def probe_phase_dtype(self):
        return self._probe_phase_dtype

    @property
    def id_scan(self):
        if self._id_scan is None:
            self._id_scan = self._retrieve_id_scan()
        return self._id_scan

    @property
    def id_proj(self):
        if self._id_proj is None:
            self._id_proj = self._retrieve_id_proj()
        return self._id_proj

    @property
    def id_angle(self):
        return self._id_angle

    @id_angle.setter
    def id_angle(self, angle):
        self._id_angle = angle

    @property
    def distance(self):
        return self._distance

    @distance.setter
    def distance(self, dist):
        self._distance = dist

    @property
    def pixel_size(self):
        return self._pixel_size

    @pixel_size.setter
    def pixel_size(self, px_sz):
        self._pixel_size = px_sz

    @property
    def avail_complex(self):
        return False

    @property
    def avail_modulus(self):
        return True

    @property
    def avail_phase(self):
        return True

    def __str__(self):
        return f"{self.software} file: {self._file_path}"

    def __repr__(self):
        cls_name = type(self).__name__
        id_angle = (f"id_angle={self._id_angle}" if self._id_angle is not None
                    else "")
        return (f"{cls_name}(file_path='{self._file_path}',"
                f"id_scan='{self._id_scan}',"
                f"id_proj='{self._id_proj}'{id_angle})")
