import sys
from contextlib import suppress
from datetime import datetime
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

import h5py
import numpy as np
from hdf5plugin import Blosc

from nxstacker.utils.io import user_name
from nxstacker.utils.model import UKtz

ENTRY = "entry"
DEF = "definition"
TITLE = "title"
START_TIME = "start_time"
END_TIME = "end_time"
INSTRUMENT = "instrument"
SOURCE = "SOURCE"
SOURCE_TYPE = "type"
SOURCE_NAME = "name"
SOURCE_SHORT_NAME = "short_name"
SOURCE_PROBE = "probe"
DETECTOR = "detector"
DATA_DETECTOR = "data"
IMAGE_KEY = "image_key"
X_PX_SZ = "x_pixel_size"
Y_PX_SZ = "y_pixel_size"
DIST = "distance"
SAMPLE = "sample"
SAMPLE_NAME = "name"
ROT_ANGLE = "rotation_angle"
DATA_ENTRY = "data"
PROCESS = "process"
VERSION = "version"
PROGRAM = "program"
DATE = "date"
SEQ_IDX = "sequence_index"
NOTE = "NOTE"

NX_ENTRY = Path(f"/{ENTRY}")
NX_INSTRUMENT = NX_ENTRY / INSTRUMENT
NX_SOURCE = NX_INSTRUMENT / SOURCE
NX_DETECTOR = NX_INSTRUMENT / DETECTOR
NX_SAMPLE = NX_ENTRY / SAMPLE
NX_DATA = NX_ENTRY / DATA_ENTRY
NX_PROCESS = NX_ENTRY / PROCESS
LINK_DATA = NX_DETECTOR / DATA_DETECTOR
LINK_ROT_ANG = NX_SAMPLE / ROT_ANGLE
LINK_IMAGE_KEY = NX_DETECTOR / IMAGE_KEY


def create_minimal(file_nxtomo, stack_shape, stack_dtype, facility, *,
                   compress=False, title=None, sample_description=None,
                   detector_distance=None, x_pixel_size=None,
                   y_pixel_size=None, start_time=None, end_time=None):
    """Create a minimal NXtomo file for a stack of projections.
    """

    stack_shape = tuple(stack_shape)
    nframe = stack_shape[0]

    with h5py.File(file_nxtomo, "w") as f:

        _create_entry(f, title=title, start_time=start_time, end_time=end_time)

        _create_instrument(f)

        _create_source(f, facility)

        _create_detector(f, stack_shape, stack_dtype,
                         x_pixel_size=x_pixel_size,
                         y_pixel_size=y_pixel_size,
                         detector_distance=detector_distance,
                         compress=compress)

        _create_sample(f, nframe, sample_description=sample_description)

        _create_process(f)

        # link data
        _link_data(f)

def _create_entry(root, title=None, start_time=None, end_time=None):
    grp_entry = root.create_group(str(NX_ENTRY))
    grp_entry.attrs["NX_class"] = "NXentry"
    grp_entry.attrs["default"] = DATA_ENTRY

    grp_entry[DEF] = "NXtomo"

    if title is not None:
        grp_entry[TITLE] = str(title)
    if start_time is not None:
        grp_entry[START_TIME] = str(start_time)
    if end_time is not None:
        grp_entry[END_TIME] = str(end_time)

    return grp_entry


def _create_instrument(root):
    grp_instrument = root.create_group(str(NX_INSTRUMENT))
    grp_instrument.attrs["NX_class"] = "NXinstrument"

    return grp_instrument

def _create_source(root, facility):
    grp_source = root.create_group(str(NX_SOURCE))
    grp_source.attrs["NX_class"] = "NXsource"

    grp_source[SOURCE_TYPE] = str(facility.source_type)
    grp_source[SOURCE_NAME] = str(facility.source_name)
    short = facility.source_name_short
    grp_source[SOURCE_NAME].attrs[SOURCE_SHORT_NAME] = str(short)
    grp_source[SOURCE_PROBE] = str(facility.source_probe)

    return grp_source

def _create_detector(root, stack_shape, stack_dtype, x_pixel_size=None,
                     y_pixel_size=None, detector_distance=None, *,
                     compress=False):
    grp_detector = root.create_group(str(NX_DETECTOR))
    grp_detector.attrs["NX_class"] = "NXdetector"

    if compress:
        compression_filter = Blosc("zstd", 9, Blosc.BITSHUFFLE)
        compression = compression_filter.filter_id
        compression_opts = compression_filter.filter_options
    else:
        compression = None
        compression_opts = None
    chunks = (1, stack_shape[1], stack_shape[2])

    grp_detector.create_dataset(DATA_DETECTOR, shape=stack_shape,
                                dtype=stack_dtype, chunks=chunks,
                                compression=compression,
                                compression_opts=compression_opts)

    grp_detector[IMAGE_KEY] = np.zeros(stack_shape[0], dtype=int)

    if x_pixel_size is not None:
        grp_detector[X_PX_SZ] = x_pixel_size
        grp_detector[X_PX_SZ].attrs["units"] = "m"

    if y_pixel_size is not None:
        grp_detector[Y_PX_SZ] = y_pixel_size
        grp_detector[Y_PX_SZ].attrs["units"] = "m"

    if detector_distance is not None:
        grp_detector[DIST] = detector_distance
        grp_detector[DIST].attrs["units"] = "m"

def _create_sample(root, nframe, sample_description=None):
    grp_sample = root.create_group(str(NX_SAMPLE))
    grp_sample.attrs["NX_class"] = "NXsample"

    if sample_description is not None:
        grp_sample[SAMPLE_NAME] = str(sample_description)

    dset_angle = grp_sample.create_dataset(ROT_ANGLE,
                                           shape=nframe,
                                           dtype=float)
    dset_angle.attrs["units"] = "degrees"

def _link_data(root):
    grp_data = root.create_group(str(NX_DATA))
    grp_data.attrs["NX_class"] = "NXdata"
    grp_data.attrs["signal"] = DATA_DETECTOR

    grp_data[DATA_DETECTOR] = h5py.SoftLink(str(LINK_DATA))
    grp_data[ROT_ANGLE] = h5py.SoftLink(str(LINK_ROT_ANG))
    grp_data[IMAGE_KEY] = h5py.SoftLink(str(LINK_IMAGE_KEY))

def _create_process(root):
    grp_process = root.create_group(str(NX_PROCESS))
    grp_process.attrs["NX_class"] = "NXprocess"

    grp_process[PROGRAM] = "nxstacker"
    with suppress(PackageNotFoundError):
        grp_process[VERSION] = version("nxstacker")
    grp_process[DATE] = (now := datetime.now(UKtz()).isoformat())
    grp_process[SEQ_IDX] = 1

    grp_note = grp_process.create_group(NOTE)
    grp_note.attrs["NX_class"] = "NXnote"
    grp_note["data"] = " ".join(sys.argv)
    grp_note["type"] = "text/plain"
    grp_note[SEQ_IDX] = 1
    grp_note["author"] = user_name()
    grp_note["description"] = "the command used to produce this file"
    grp_note["date"] = now
