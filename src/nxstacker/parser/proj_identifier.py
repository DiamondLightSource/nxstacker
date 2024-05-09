import re
from collections import deque
from pathlib import Path

import numpy as np


def generate_numbers(specifier, dtype=int):
    """
    """
    result = []
    segments = specifier.split(",")

    try:
        eps = np.finfo(dtype).eps
    except ValueError:
        eps = 1

    single_num = re.compile(r"^([-]?\d+\.?\d*)$")
    start_end = re.compile(r"^([-]?\d+\.?\d*)-([-]?\d+\.?\d*)$")
    start_end_step = re.compile(r"^([-]?\d+\.?\d*)-([-]?\d+\.?\d*):"
                                r"(\d+\.?\d*)$")


    for segment in segments:
        if (match := re.search(single_num, segment)):
            start = float(match.group(1))
            end = start
            step = 1.0
        elif (match := re.search(start_end, segment)):
            start = float(match.group(1))
            end = float(match.group(2))
            step = 1.0
        elif (match := re.search(start_end_step, segment)):
            start = float(match.group(1))
            end = float(match.group(2))
            step = float(match.group(3))
        else:
            msg = (f"Invalid specifier {segment}. It should be one of the "
                    "followings: <NUMBER>, <START>-<END> or "
                    "<START>-<END>:<STEP>.")
            raise ValueError(msg)

        result.extend(list(np.arange(start, end+eps, step).astype(dtype)))

    return result


class ProjIdentifier:
    """Specify the identifiers for projections.

    Common identifiers for projections are by scan numbers, projection
    numbers, and rotation angles.

    Attributes
    ----------
    from_range : list
    from_file : list
    exclude : list
    """

    def __init__(self, from_range=None, from_file=None, exclude=None,
                 id_type=str):

        self.from_range = []
        self.from_file = []
        self.exclude = []
        self.identifiers = deque()
        self.id_type = id_type

        if from_range is not None:
            self.from_range = self.id_from_range(from_range)

        if from_file is not None:
            self.from_file = self.id_from_file(from_file)

        if exclude is not None:
            self.exclude = generate_numbers(exclude, self.id_type)

        # retain order, a bit inefficient
        merged = list(dict.fromkeys(self.from_range)) +\
                 list(dict.fromkeys(self.from_file))
        merged = list(dict.fromkeys(merged))
        for entry in merged:
            if entry not in self.exclude:
                self.identifiers.append(entry)

        self.identifiers = tuple(self.identifiers)

    def id_from_range(self, specifier):
        return generate_numbers(specifier, self.id_type)

    def id_from_file(self, file_path):
        fp = Path(file_path)
        with fp.open() as f:
            ids = [self.id_type(entry) for entry in f]
        return ids
