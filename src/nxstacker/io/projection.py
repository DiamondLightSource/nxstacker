from types import MappingProxyType

from nxstacker.utils.io import file_has_paths
from nxstacker.utils.model import (
    Directory,
    FilePath,
    FixedValue,
    PositiveNumber,
)
from nxstacker.utils.parse import quote_iterable


class ProjectionFile:
    """Act as the base class of projection file."""

    experiment = "unknown"
    software = "unknown"
    path_names = MappingProxyType({})
    essential_paths = tuple(path_names.values())
    extensions = ()
    file_path = FilePath(must_exist=True)
    raw_dir = Directory(undefined_ok=True, must_exist=True)
    description = FixedValue()
    trim_proj = FixedValue()
    distance = PositiveNumber(float)
    pixel_size = PositiveNumber(float)
    id_scan = FixedValue()
    id_proj = FixedValue()
    id_angle = FixedValue()

    def __init__(
        self,
        file_path,
        *,
        verify=True,
        raw_dir=None,
        description=None,
    ):
        """Initialise an instance of projection file.

        Parameters
        ----------
        file_path : pathlib.Path or str
            the file path of the reconstruction file.
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

        # these needs to be overwritten later
        self.id_scan = None
        self.id_proj = None

        # the rotation angle is not known at this stage
        # this is available from the raw data file and retrieval of it
        # depends on the facility
        self.id_angle = None

        self.raw_dir = raw_dir
        self.description = description
        self.trim_proj = True

    def verify_file(self):
        """Check existence of some essential hdf5 paths."""
        return file_has_paths(self._file_path, self.essential_paths)

    def __str__(self):
        return f"{self.software} file: {self._file_path}"

    def __repr__(self):
        cls_name = type(self).__name__
        id_scan = (
            f", id_scan='{self._id_scan}'" if self._id_scan is not None else ""
        )
        id_proj = (
            f", id_proj='{self._id_proj}'" if self._id_proj is not None else ""
        )
        id_angle = (
            f", id_angle='{self._id_angle}'"
            if self._id_angle is not None
            else ""
        )
        raw_dir = (
            f", raw_dir='{self._raw_dir}'" if self._raw_dir is not None else ""
        )
        description = (
            f", description='{self._description}'"
            if self._description is not None
            else ""
        )
        return (
            f"{cls_name}(file_path='{self._file_path}'"
            f"{id_scan}{id_proj}{id_angle}{raw_dir}{description})"
        )
