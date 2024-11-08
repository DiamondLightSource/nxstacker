import re
import subprocess
from importlib.metadata import PackageNotFoundError, version
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
    try:
        f = h5py.File(file_path, "r")
    except OSError:
        # file cannot be opened
        return False
    else:
        return all(path in f for path in paths)


def top_level_dir(directory, depth=6):
    """Return partial path of a directory with a specific depth.

    E.g. "/first/second/third/fourth" with a depth of 3 will return
    "/first/second" ('/' counts as one depth).

    Parameters
    ----------
    directory : str or pathlib.Path
        the directory which a partial path is to be extracted
    depth : int, optional
        the depth to be returned

    """
    return Path("/".join(Path(directory).parts[:depth])).resolve()


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


def files_first_exist(files):
    """Get the first existing file path from a list of them.

    Parameters
    ----------
    files : iterable
        a collection of file paths. Any None or empty string will be
        skipped.

    Returns
    -------
    the first file path in 'files' that exists. 'None' is returned if
    none of the files exists.

    """
    for fp in list(dict.fromkeys(files)):
        if fp is None or fp == "":
            continue
        if Path(fp).exists():
            return fp
    return None


def user_name():
    """Get the user name as ID or real name from database if possible.

    Returns
    -------
    the name, one of the following: "unknown", login name (from whoami)
    or real name (from pinky)

    """
    try:
        whoami = subprocess.run(
            ["/usr/bin/whoami"], capture_output=True, text=True, check=True
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        # problem with the command "whoami", return "unknown"
        return "unknown"
    else:
        login_name = whoami.stdout.strip("\n")

        try:
            pinky = subprocess.run(
                ["/usr/bin/pinky", "-l", login_name],
                capture_output=True,
                text=True,
                check=True,
            )
        except (FileNotFoundError, subprocess.CalledProcessError):
            # problem with "pinky", return the login name
            return login_name
        else:
            pinky_out = pinky.stdout
            regex = re.compile(r"In real life:(.*)\n")

            if (match := re.search(regex, pinky_out)) is None:
                # fail to parse output from pinky -l
                return login_name

            real_name = match.group(1).strip(" ")
            if real_name == "???":
                # cannot find info from the database
                return login_name

            return real_name


def get_version():
    """Get the version number.

    Returns
    -------
    ver : str
        the version number

    """
    try:
        ver = version("nxstacker")
    except PackageNotFoundError:
        ver = "dev"
    return ver


def is_staging_area(directory):
    """Check if the given directory is a DLS staging area.

    Parameters
    ----------
    directory : str or pathlib.Path
        the directory to be checked

    Returns
    -------
    True or False, indicating whether this is a DLS staging area

    """
    dir_ = Path(directory).resolve()

    try:
        dir_.relative_to("/dls/staging")
    except ValueError:
        return False
    else:
        return True
