import re
from types import MappingProxyType

import h5py

from nxstacker.io.projection import ProjectionFile
from nxstacker.utils.io import top_level_dir


class XRFWindowFile(ProjectionFile):
    """Represent a XRF window file from Python processing."""

    experiment = "xrf"
    software = "python processing"
    path_names = MappingProxyType(
        {
            "mca": "/processed/mca/data",
            "result": "/processed/result/data",
            "processed": "/processed",
        },
    )
    essential_paths = tuple(path_names.values())
    extensions = (".nxs",)

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
        """Initialise an instance of XRF windowed file.

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

    def _retrieve_id_scan(self):
        # get the scan number from the raw file by matching them with
        # some regex
        regexes = (
            re.compile(r".*-(\d+)_xrf\.nxs$"),
            re.compile(r".*-(\d+)_processed\.nxs$"),
            re.compile(r".*-(\d+)\.nxs$"),
        )

        for regex in regexes:
            match = re.search(regex, str(self._file_path))
            if match is not None:
                # return the first match
                return match.group(1)
        # ideally some fallback here but raise for now
        msg = f"Cannot deduce scan numbers from {self._file_path}"
        raise RuntimeError(msg)

    def _retrieve_id_proj(self):
        msg = (
            f"For {self.software} reconstruction file, it cannot get the "
            "projection ID from the file itself. It should be set by "
            "passing value to the argument 'id_proj' when initialising "
            "the instance."
        )
        raise TypeError(msg)

    def fill_attr(self):
        """Assign attributes as determined from the file."""
        if self.raw_dir is None:
            self._overwrite_raw_dir()

    def _overwrite_raw_dir(self):
        """Overwrite the _raw_dir attribute."""
        self._raw_dir = top_level_dir(self._file_path)

    def elemental_map(self, transition):
        """Return the correpsonding elemental map.

        Parameters
        ----------
        transition : str
            the transition with the format <ELEMENT>-<EDGE>

        Returns
        -------
        elemental_map : ndarray
            the elemental map of 'transition'

        """
        path = f"{self.path_names['processed']}/{transition}/data"
        with h5py.File(self._file_path, "r") as f:
            try:
                dset = f[path]
            except KeyError:
                msg = f"The elemental map of '{transition}' does not exist."
                raise KeyError(msg) from None
            else:
                elemental_map = dset[()]

        return elemental_map

    def elemental_map_attr(self, transition):
        """Return the shape and dtype of the correpsonding elemental map.

        Parameters
        ----------
        transition : str
            the transition with the format <ELEMENT>-<EDGE>

        Returns
        -------
        shape : tuple
            the shape of the elemental map
        dtype : type
            the data type of the elemental map

        """
        path = f"{self.path_names['processed']}/{transition}/data"
        with h5py.File(self._file_path, "r") as f:
            try:
                dset = f[path]
            except KeyError:
                msg = f"The elemental map of '{transition}' does not exist."
                raise KeyError(msg) from None
            else:
                shape = dset.shape
                dtype = dset.dtype

        return shape, dtype
