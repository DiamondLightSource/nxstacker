from pathlib import Path

import h5py


def file_has_paths(file_path, paths):
    """Check if an HDF5 file contains a sequence of paths.

    Parameters
    ----------
    file_path : str/pathlib.Path
        the path of the file to be checked
    paths : list
        the sequence of paths to be checked for the presence in file_path

    Returns
    -------
    True or False, indicating whether it contains all the paths or not
    """
    with h5py.File(file_path, "r") as f:
        for path in paths:
            if path not in f:
                return False
    return True

def top_level_dir(directory, level=6):
    return Path("/".join(Path(directory).parts[:level]))

def dataset_from_first_valid_path(hdf5_file, paths):
    """Get the dataset from the file with the first valid path.

    Parameters
    ----------
    hdf5_file : h5py.File
        the opened instance of an HDF5 file
    paths : iterable
        a sequence of paths to be tried

    Returns
    -------
    dataset : h5py.Dataset
        the stored dataset from the first valid path, None if no dataset
        is retrieved after trying all the paths
    """
    dataset = None
    for path in paths:
        if path in hdf5_file:
            dataset = hdf5_file[path]
            break
    return dataset

