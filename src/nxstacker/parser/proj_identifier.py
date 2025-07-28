import re
from collections import deque
from functools import cached_property
from pathlib import Path

import numpy as np


def generate_numbers(specifier, dtype=int):
    """Generate a list of numbers from specifier.

    The specifier should have the format of <START>[-<END>[:<STEP>]], for
    examples, "10-12" gives [10, 11, 12], "10-14:2" gives [10, 12, 14].

    Parameters
    ----------
    specifier : str
        the specifier for the generation of number
    dtype : type, optional
        the data type of the numbers. Default to int.

    """
    result = []
    segments = specifier.split(",")

    try:
        eps = np.finfo(dtype).eps
    except ValueError:
        eps = 1

    single_num = re.compile(r"^([-]?\d+\.?\d*)$")
    start_end = re.compile(r"^([-]?\d+\.?\d*)-([-]?\d+\.?\d*)$")
    start_end_step = re.compile(
        r"^([-]?\d+\.?\d*)-([-]?\d+\.?\d*):" r"(\d+\.?\d*)$"
    )

    for segment in segments:
        if match := re.search(single_num, segment):
            start = float(match.group(1))
            end = start
            step = 1.0
        elif match := re.search(start_end, segment):
            start = float(match.group(1))
            end = float(match.group(2))
            step = 1.0
        elif match := re.search(start_end_step, segment):
            start = float(match.group(1))
            end = float(match.group(2))
            step = float(match.group(3))
        else:
            msg = (
                f"Invalid specifier {segment}. It should be one of the "
                "followings: <NUMBER>, <START>-<END> or "
                "<START>-<END>:<STEP>."
            )
            raise ValueError(msg)

        result.extend(list(np.arange(start, end + eps, step).astype(dtype)))

    return result


class ProjIdentifier:
    """Specify the identifiers for projections."""

    def __init__(
        self, from_range=None, from_file=None, exclude=None, id_type=str
    ):
        """Initialise the projection identifiers.

        The source can be from a range specified as
        <START>[-<END>[:<STEP>]] and/or a text file. If there is any
        duplicate, it will be removed.

        If the id_type is float-point number, it may suffer from
        precision issue.

        Parameters
        ----------
        from_range : str, optional
            the range specified as <START>[-<END>[:<STEP>]]. Default to
            None.
        from_file : str or pathlib.Path, optional
            the text file with the identifier in a single column.
            Default to None.
        exclude : str, optional
            identifier to be exclude, specified as
            <START>[-<END>[:<STEP>]].
        id_type : type, optional
            the data type of the identifier. Default to str.

        """
        self.from_range = []
        self.from_file = []
        self.exclude = []
        self.identifiers = deque()
        self.id_type = id_type
        self.only_from_file = False

        if from_range is not None:
            self.from_range = self.id_from_range(from_range)

        if from_file is not None:
            self.from_file = self.id_from_file(from_file)

        if exclude is not None:
            self.exclude = generate_numbers(exclude, self.id_type)

        # retain order, a bit inefficient
        merged = list(dict.fromkeys(self.from_range)) + list(
            dict.fromkeys(self.from_file)
        )
        merged = list(dict.fromkeys(merged))
        for entry in merged:
            if entry not in self.exclude:
                self.identifiers.append(entry)

        self.identifiers = tuple(self.identifiers)

        if from_file is not None and from_range is None and exclude is None:
            self.only_from_file = True

    def id_from_range(self, specifier):
        """Return numbers from <START>[-<END>[:<STEP>]]."""
        return generate_numbers(specifier, self.id_type)

    def id_from_file(self, file_path, delimiter=None):
        """Return numbers from a text file.

        Parameters
        ----------
        file_path : str or pathlib.Path
            the text file with the numbers in a single column
        delimiter : str, optional
            the delimiter between columns if there are mutliple columns.
            Default to None, set to space " ".

        """
        if delimiter is None:
            delimiter = " "

        fp = Path(file_path)
        with fp.open() as f:
            # only first column
            ids = [self.id_type(entry.split(delimiter)[0]) for entry in f]
        return ids

    @cached_property
    def num_identifiers(self):
        """Store the number of identifiers."""
        return len(self.identifiers)
