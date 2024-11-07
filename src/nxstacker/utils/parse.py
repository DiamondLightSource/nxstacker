from datetime import datetime, timezone
from pathlib import Path

from nxstacker.parser.proj_identifier import ProjIdentifier


def quote_iterable(iterable):
    """Produce quoted and comma-delimited string from an iterable.

    It converts, e.g. ["abc", "def", "ghi"] to
    "'abc', 'def' and 'ghi'". These are more friendly for stdout or
    stderr.

    Parameters
    ----------
    iterable : any iterable
        the iterable to be processed.

    Returns
    -------
    comma : str
        the quoted and comma-delimited string

    """
    if len(iterable) == 1:
        return f"'{next(iter(iterable))}'"

    quoted = [f"'{entry}'" for entry in iterable]
    comma = ", ".join(quoted[:-1])
    comma += f" and {quoted[-1]}"

    return comma


def unique_or_raise(iterable, companion=None, label="item", reference=None):
    """Return unique item or raise when encounters inhomogeneous item.

    Parameters
    ----------
    iterable : any iterable
        the iterable which uniquenes is to be checked.
    companion : any iterable, optional
        the iterable relates to the iterable which uniqueness is to be
        checked.  It must have the same length with the iterable above.
        This is for more relevant error message. Default to None, set to
        the same iterable above.
    label : str, optional
        the name of the item. This is for more descriptive error
        message. Default to "item".
    reference : Any, optional
        the reference to check uniqueness against. Default to None, set
        to the first item of the iterable.

    Returns
    -------
    the unique item

    """
    if companion is None:
        companion = iterable

    if len(iterable) != len(companion):
        msg = (
            "The companion must have the same length with the actual "
            "iterable."
        )
        raise ValueError(msg)

    seen = set()
    for k, item in enumerate(iterable):
        if reference is None:
            reference = item

        seen.add(item)
        if len(seen) > 1:
            msg = (
                f"Inhomogenous {label} for {companion[k]}. "
                f"This has {item} but the reference is {reference}."
            )
            raise RuntimeError(msg)

    return seen.pop()


def add_timezone(time_isoformat):
    """Add time zone information to an ISO 8601 time format.

    Parameters
    ----------
    time_isoformat : str
        a time format following ISO 8601

    Returns
    -------
    tz_iso : str
        the same time format with time zone information

    """
    time_from_iso = datetime.fromisoformat(time_isoformat)
    time_with_tz = time_from_iso.astimezone(timezone.utc)
    tz_iso = time_with_tz.isoformat()

    return tz_iso


def parse_identifier(
    from_string=None, file_list=None, exclude=None, id_type=int
):
    """Parse identifier specification as a tuple.

    Parameters
    ----------
    from_string : str, optional
        the string specification of the identifier with the format
        <START>[-<END>[:<STEP>]].  Default to None.
    file_list : str, optional
        the text file with single-column identifiers. Default to None.
    exclude : str, optional
        the identifier to be excluded, in the format
        <START>[-<END>[:<STEP>]].  Default to None.
    id_type : type, optional
        the data type of the identifier. Default to int.

    Returns
    -------
    to_include : tuple
        the identifiers to be included

    """
    pi = ProjIdentifier(from_string, file_list, exclude, id_type=id_type)
    to_include = pi.identifiers

    return to_include


def as_dls_staging_area(visit):
    """Return the DLS staging area from a visit.

    Parameters
    ----------
    visit : str or pathlib.Path
        the visit path

    Returns
    -------
    the corresponding staging area for a visit, e.g. if the visit is
    "/dls/xxx/data/2024" then it will return
    "/dls/staging/dls/xxx/data/2024". It will return the original path
    if the visit is not a DLS visit (not starting as "/dls") or already
    a staging area for a visit.

    """
    visit = Path(visit).resolve()

    try:
        without_dls = visit.relative_to("/dls")
    except ValueError:
        return visit
    else:
        staging = Path.joinpath(Path("/dls/staging"), without_dls)
        return staging
