from datetime import datetime, timedelta, tzinfo
from pathlib import Path
from types import MappingProxyType

import xraylib

from nxstacker.parser.proj_identifier import generate_numbers
from nxstacker.utils.facility import choose_facility_info


class UKtz(tzinfo):
    """Time zone in the UK."""

    def utcoffset(self, dt):
        """Determine the offset based on the date and year."""
        if self.is_dst(dt):
            # UTC +1
            return timedelta(hours=1)

        return timedelta()

    def dst(self, dt):
        """Return the DST adjustment."""
        year = dt.year

        # In the UK the clocks go forward 1 hour at 1am on the last
        # Sunday in March, and back 1 hour at 2am on the last Sunday in
        # October.
        last_sunday_march = self._last_sunday(year, 3)
        last_sunday_october = self._last_sunday(year, 10)
        dston = last_sunday_march.replace(hour=1)
        dstoff = last_sunday_october.replace(hour=2)

        if dston <= dt.replace(tzinfo=None) < dstoff:
            # BST
            return timedelta(hours=1)

        # GMT
        return timedelta()

    def tzname(self, dt):
        """Return time zone name as BST or GMT."""
        return "BST" if self.is_dst(dt) else "GMT"

    def is_dst(self, dt):
        """Check if it is DST."""
        return self.dst(dt) != timedelta()

    def _last_sunday(self, year, month):
        """Find the last Sunday of the specified year and month."""
        last_day = 31
        while True:
            try:
                last_sunday = datetime(year, month, last_day)  # noqa: DTZ001
            except ValueError:
                pass
            else:
                if last_sunday.weekday() == 6:
                    return last_sunday

            last_day -= 1


class FixedValue:
    """A descriptor with fixed value.

    For an attribute named "name", it stores the value in "_name" and it
    cannot be changed afterwards, although it is possible to change the
    value of "_name" directly.
    """

    def __set_name__(self, owner, name):
        self.public_name = name
        self.private_name = f"_{name}"

    def __get__(self, instance, owner=None):
        if instance is None:
            return self
        return getattr(instance, self.private_name)

    def __set__(self, instance, value):
        if hasattr(instance, self.private_name):
            msg = f"can't set attribute '{self.public_name}'"
            raise AttributeError(msg)
        setattr(instance, self.private_name, value)


class Directory(FixedValue):
    """Represent a directory."""

    def __init__(self, *, undefined_ok=False, must_exist=False):
        """Initialise the directory descriptor.

        Parameters
        ----------
        undefined_ok : bool, optional
            whether the directory can be None. Default to False.
        must_exist : bool, optional
            whether to check for the existence of directory. Default to
            False, and it will be created if the path is invalid.

        """
        self.undefined_ok = undefined_ok
        self.must_exist = must_exist

    def __set__(self, instance, value):
        if hasattr(instance, self.private_name):
            msg = f"can't set attribute '{self.public_name}'"
            raise AttributeError(msg)

        if value is None and self.undefined_ok:
            dir_ = None
        elif value is None:
            dir_ = Path()
        else:
            if isinstance(value, bytes):
                value = value.decode()
            dir_ = Path(value).resolve()

        self.validate_or_create(dir_)
        setattr(instance, self.private_name, dir_)

    def validate_or_create(self, dir_):
        """Check directory existence and create it if it is necessary.

        Parameters
        ----------
        dir_ : pathlib.Path or None
            the direcotry, or None and validation is skipped.

        """
        # skip validation if it is None
        if dir_ is None:
            return

        if self.must_exist and not dir_.is_dir():
            msg = f"The directory {dir_} does not exist."
            raise ValueError(msg)

        if not dir_.is_dir():
            dir_.mkdir(parents=True, exist_ok=True)


class FilePath(FixedValue):
    """Represent a file path."""

    def __init__(self, *, undefined_ok=False, must_exist=False):
        """Initialise the file path descriptor.

        Parameters
        ----------
        undefined_ok : bool, optional
            whether the file path can be None. Default to False.
        must_exist : bool, optional
            whether to check for the existence of the file. Default to
            False.

        """
        self.undefined_ok = undefined_ok
        self.must_exist = must_exist

    def __set__(self, instance, value):
        if hasattr(instance, self.private_name):
            msg = f"can't set attribute '{self.public_name}'"
            raise AttributeError(msg)

        if value is None and self.undefined_ok:
            fp = None
        elif value is None and not self.undefined_ok:
            msg = (
                "The file path cannot be None, or the flag 'undefined_ok' "
                "can be turned on."
            )
            raise ValueError(msg)
        else:
            if isinstance(value, bytes):
                value = value.decode()
            fp = Path(value).resolve()

        self.validate(fp)
        setattr(instance, self.private_name, fp)

    def validate(self, fp):
        """Check file existence.

        Parameters
        ----------
        fp : pathlib.Path or None
            the file path, or None and validation is skipped.

        """
        # skip validation if it is None
        if fp is None:
            return

        if self.must_exist and not fp.is_file():
            msg = f"The file {fp} does not exist."
            raise ValueError(msg)


class IdentifierRange(FixedValue):
    """Represent a range of projection identifiers."""

    def __init__(self, num_type=int):
        """Initialise the identifier's range descriptor.

        Parameters
        ----------
        num_type : type,, optional
            the data type of the identifier. Default to int. This is
            used when the range is generated. They will be converted to
            str at the end.

        """
        self.num_type = num_type

    def __set__(self, instance, value):
        if hasattr(instance, self.private_name):
            msg = f"can't set attribute '{self.public_name}'"
            raise AttributeError(msg)

        if value is None:
            id_rng = ()
        elif isinstance(value, str):
            id_rng = generate_numbers(value, dtype=self.num_type)
        else:
            id_rng = tuple(value)

        id_rng_as_str = tuple(str(k) for k in id_rng)
        setattr(instance, self.private_name, id_rng_as_str)


class ExperimentFacility(FixedValue):
    """Represent a facility info in an experiment."""

    def __set__(self, instance, value):
        if hasattr(instance, self.private_name):
            msg = f"can't set attribute '{self.public_name}'"
            raise AttributeError(msg)

        if value is None or isinstance(value, str):
            # these are all directories which can help deducing facility
            # in case they are not defined
            associated_dir = [
                instance.__dict__.get("_proj_dir"),
                instance.__dict__.get("_nxtomo_dir"),
                instance.__dict__.get("_raw_dir"),
            ]

            facility = choose_facility_info(value, dirs=associated_dir)
        else:
            facility = value

        setattr(instance, self.private_name, facility)


class PositiveNumber(FixedValue):
    """Represent a positive number."""

    def __init__(self, num_type=int):
        """Initialise the positive number descriptor.

        Parameters
        ----------
        num_type : type,, optional
            the data type of the number. Default to int.

        """
        self.num_type = num_type

    def __set__(self, instance, value):
        if hasattr(instance, self.private_name):
            msg = f"can't set attribute '{self.public_name}'"
            raise AttributeError(msg)

        num = self.num_type(value)
        if num < 0:
            msg = (
                f"The attribute '{self.public_name}' cannot be "
                f"negative ({num})."
            )
            raise ValueError(msg)

        setattr(instance, self.private_name, num)


class XRFTransitionList(FixedValue):
    """Represent a list of XRF transition."""

    IUPAC = MappingProxyType(
        {
            "Ka": (xraylib.KL3_LINE, "Ka"),
            "Kb": (xraylib.KM3_LINE, "Kb"),
            "La": (xraylib.L3M5_LINE, "La"),
            "Lb": (xraylib.L2M4_LINE, "Lb"),
            "M": (xraylib.M5N7_LINE, "M"),
        }
    )

    def __set__(self, instance, value):
        if hasattr(instance, self.private_name):
            msg = f"can't set attribute '{self.public_name}'"
            raise AttributeError(msg)

        if not value:
            if value is None:
                problem = f"{type(None).__name__}"
            else:
                problem = value
            msg = f"The transition list cannot be '{problem}'."
            raise ValueError(msg)

        # value is a comma-delimited string of transitions
        line_groups = value.split(",")
        for lg in line_groups:
            self.validate(lg)

        setattr(instance, self.private_name, line_groups)

    def validate(self, line_group):
        """Validate the line group."""
        invalid_element = False
        invalid_transition = False
        if line_group.endswith(","):
            msg = (
                "Please remove the trailing comma when specifying the "
                "transition"
            )
            raise ValueError(msg)

        try:
            element, transition = line_group.split("-")
        except ValueError:
            msg = f"The line group {line_group} is invalid."
            raise ValueError(msg) from None

        # check element
        try:
            xraylib.SymbolToAtomicNumber(element)
        except ValueError:
            invalid_element = True

        # check transition
        if transition not in self.IUPAC:
            invalid_transition = True

        # fine
        if not invalid_element and not invalid_transition:
            return

        if invalid_element and invalid_transition:
            msg = (
                f"The element '{element}' and transition '{transition}' "
                "are invalid."
            )
        elif invalid_element:
            msg = f"The element '{element}' is invalid."
        elif invalid_transition:
            msg = f"The transition '{transition}' is invalid."
        raise ValueError(msg)
