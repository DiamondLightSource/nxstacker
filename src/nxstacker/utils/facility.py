import os
import re
from pathlib import Path

from nxstacker.facility import I08_1, I13_1, I14


def choose_facility_info(facility, dirs=None):
    """Choose the facility information instance.

    Parameters
    ----------
    facility : str or None
        a string that indicates the facility, e.g. "i14", "i08-1",
        "i13-1".
    dirs : list, optional
        a list of directories to help deciding the facility if the above
        argument is None. Default to None.

    Returns
    -------
    facility_info : FacilityInfo
        the facility information instance

    """
    if facility is None:
        facility = deduce_from_directory(dirs)
        return choose_facility_info(facility)

    match str(facility).lower():
        case "i14":
            facility_info = I14()
        case "i13-1" | "i13":
            facility_info = I13_1()
        case "i08-1" | "j08":
            facility_info = I08_1()
        case _:
            msg = f"The facility '{facility}' is not currently supported."
            raise ValueError(msg)

    return facility_info


def deduce_from_directory(dirs=None):
    """Deduce facility from a list of directories.

    Parameters
    ----------
    dirs : list
        the list of directories from which the facility is deduced. The
        current working directory will be appended to the provided list.
        Default to None, and set to the current working directory.

    Returns
    -------
    a string that indicates the facility

    """
    pattern = re.compile(r"[ibempkx]\d\d(?:-\d)?(?!\d+)")

    # first check if the env var BEAMLINE is set
    if (facility := os.environ.get("BEAMLINE")) is not None:
        return facility.lower()

    # otherwise see if it can be extracted from a list of directory
    # paths, the order of the directories matters as it will immediately
    # return the match once it is found
    if dirs is None:
        dirs = [Path.cwd()]
    else:
        dirs = [*list(dirs), Path.cwd()]

    for dir_ in dirs:
        if (
            dir_ is not None
            and (facility := re.search(pattern, str(dir_))) is not None
        ):
            return facility.group()

    msg = "Failure in deducing the facility, please provide it explicitly."
    raise ValueError(msg)
