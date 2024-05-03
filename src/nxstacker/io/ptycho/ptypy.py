import re
from pathlib import Path
from types import MappingProxyType

import h5py
import numpy as np

from nxstacker.utils.io import file_has_paths, top_level_dir
from nxstacker.utils.parse import quote_iterable


class PtyPyFile:

    experiment = "ptychography"
    software = "PtyPy"
    path_names = MappingProxyType({"object": "/content/obj",
                                   "probe": "/content/probe",
                                   "scan_names":  "/content/pars/scans",
                                   })
    essential_paths = tuple(path_names.values())
    extensions = (".ptyr", )

    def __init__(self, file_path, id_scan=None, id_proj=None, *, verify=True):
        self._file_path = Path(file_path)

        if verify and not self.verify_file():
            paths = quote_iterable(self.essential_paths)
            msg = (f"The file {self._file_path} is not a reconstruction "
                   f"from {self.software}. Does the file have all the "
                   f"following path names: {paths}?")
            raise KeyError(msg)

        self._compose_paths()

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

        self._ob_attr()
        self._pr_attr()

    def _retrieve_id_scan(self):
        # get the scan number from the raw file by matching them with
        # some regex
        regexes = (re.compile(r".*-(\d+)\.nxs$"),
                   re.compile(r".*-(\d+)_processed\.nxs$"),
                   )

        for regex in regexes:
            match = re.search(regex, self._raw_file)
            if match is not None:
                # return the first match
                return match.group(1)
        # ideally some fallback here but raise for now
        msg = f"Cannot deduce scan numbers from {self._raw_file}"
        raise RuntimeError(msg)


    def _retrieve_id_proj(self):
        msg = (f"For {self.software} reconstruction file, it cannot get the "
                "projection ID from the file itself. It should be set by "
                "passing value to the argument 'id_proj' when initialising "
                "the instance.")
        raise TypeError(msg)

    def _compose_paths(self):
        with h5py.File(self._file_path, "r") as f:
            scans = list(f[self.path_names["scan_names"]])

            # assume one storage
            scan_name = scans[0]

            self._storage = f"S{scan_name}G00"
            self._object_path = (f"{self.path_names['object']}/"
                                 f"{self._storage}/data")
            self._probe_path = (f"{self.path_names['probe']}/"
                                f"{self._storage}/data")
            self._raw_file_key = (f"{self.path_names['scan_names']}/"
                                  f"{scan_name}/data/intensities/file")
            self._px_sz_key = (f"{self.path_names['object']}/"
                               f"{self._storage}/_psize")

            # get the path of the raw file
            self._raw_file = f[self._raw_file_key][()]

        if isinstance(self._raw_file, bytes):
            self._raw_file = self._raw_file.decode()


    def find_raw_dir(self):
        raw_dir = top_level_dir(self._raw_file)

        if Path(raw_dir).is_dir():
            self._raw_dir =  raw_dir
        else:
            self._raw_dir =  top_level_dir(self._file_path)

    def object_complex(self, mode=0):
        with h5py.File(self._file_path, "r") as f:
            ob = f[self._object_path]

            if mode < (num_modes := ob.shape[0]):
                obj = ob[mode, :, :]
            else:
                mode_str = "mode" + "s"*(num_modes>1)
                msg = (f"The object has {num_modes} {mode_str} and the "
                       f"maximum mode index is {num_modes-1}, but {mode} "
                        "was given.")
                raise IndexError(msg)
        return obj

    def object_modulus(self, mode=0):
        return np.abs(self.object_complex(mode=mode))

    def object_phase(self, mode=0):
        return np.angle(self.object_complex(mode=mode))

    def _ob_attr(self):
        with h5py.File(self._file_path, "r") as f:
            self._object_shape = f[self._object_path].shape
            self._object_complex_dtype = f[self._object_path].dtype
            self._pixel_size = f[self._px_sz_key][()].mean()

        # don't want to perform np.abs and np.angle by reading the
        # actual complex data
        if self._object_complex_dtype == np.complex64:
            self._object_modulus_dtype = np.float32
            self._object_phase_dtype = np.float32
        else:
            self._object_modulus_dtype = np.float64
            self._object_phase_dtype = np.float64

    def probe_complex(self, mode=0):
        with h5py.File(self._file_path, "r") as f:
            pr = f[self._probe_path]

            if mode < (num_modes := pr.shape[0]):
                prb = pr[mode, :, :]
            else:
                mode_str = "mode" + "s"*(num_modes>1)
                msg = (f"The probe has {num_modes} {mode_str} and the "
                       f"maximum mode index is {num_modes-1}, but {mode} "
                        "was given.")
                raise IndexError(msg)
        return prb

    def probe_modulus(self, mode=0):
        return np.abs(self.probe_complex(mode=mode))

    def probe_phase(self, mode=0):
        return np.angle(self.probe_complex(mode=mode))

    def _pr_attr(self):
        with h5py.File(self._file_path, "r") as f:
            self._probe_shape = f[self._probe_path].shape
            self._probe_complex_dtype = f[self._probe_path].dtype

        # don't want to perform np.abs and np.angle by reading the
        # actual complex data
        if self._probe_complex_dtype == np.complex64:
            self._probe_modulus_dtype = np.float32
            self._probe_phase_dtype = np.float32
        else:
            self._probe_modulus_dtype = np.float64
            self._probe_phase_dtype = np.float64

    def verify_file(self):
        return file_has_paths(self._file_path, self.essential_paths)

    @property
    def file_path(self):
        return self._file_path

    @property
    def storage(self):
        return self._storage

    @property
    def object_path(self):
        return self._object_path

    @property
    def probe_path(self):
        return self._probe_path

    @property
    def raw_file(self):
        return self._raw_file

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
        return True

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

