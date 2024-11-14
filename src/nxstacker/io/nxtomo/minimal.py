import sys
from datetime import datetime
from pathlib import Path

import h5py
import numpy as np

from nxstacker.utils.io import get_version, user_name
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


def create_minimal(
    file_nxtomo,
    stack_shape,
    stack_dtype,
    facility,
    *,
    compression_settings=None,
    title=None,
    sample_description=None,
    detector_distance=None,
    x_pixel_size=None,
    y_pixel_size=None,
    start_time=None,
    end_time=None,
):
    """Create a minimal NXtomo file of a stack of projections.

    Parameters
    ----------
    file_nxtomo : str or pathlib.Path
        the NXtomo file path
    stack_shape : iterable
        the shape of the stack. This should be 3-dimensional.
    stack_dtype : type
        the data type of the stack
    facility : FacilityInfo
        the facility information
    compression_settings : CompressionBlosc or None, optional
        the instance hodling attributes for Blosc compression. Default
        to None, no compression is applied.
    title : str, optional
        title of the file. Default to None, skip saving it.
    sample_description : str, optional
        description of the sample. Default to None, skip saving it.
    detector_distance : float, optional
        sample-to-detector distance. Default to None, skip saving it.
    x_pixel_size, y_pixel_size : float, optional
        x and y pixel size. Default to None, skip saving it.
    start_time, end_time: str, optional
        start and end time in ISO 8601. Default to None, skip saving it.

    """
    stack_shape = tuple(stack_shape)
    if (ndim := len(stack_shape)) != 3:
        msg = f"The stack should be 3-dimensional, but it is {ndim}."
        raise ValueError(msg)

    nframe = stack_shape[0]

    with h5py.File(file_nxtomo, "w") as f:
        _create_entry(f, title=title, start_time=start_time, end_time=end_time)

        _create_instrument(f)

        _create_source(f, facility)

        _create_detector(
            f,
            stack_shape,
            stack_dtype,
            x_pixel_size=x_pixel_size,
            y_pixel_size=y_pixel_size,
            detector_distance=detector_distance,
            compression_settings=compression_settings,
        )

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


def _create_detector(
    root,
    stack_shape,
    stack_dtype,
    x_pixel_size=None,
    y_pixel_size=None,
    detector_distance=None,
    *,
    compression_settings=None,
):
    grp_detector = root.create_group(str(NX_DETECTOR))
    grp_detector.attrs["NX_class"] = "NXdetector"

    if compression_settings is None:
        # no compression
        compression = None
        compression_opts = None
    else:
        # with compression
        compression = compression_settings.compression_id
        compression_opts = compression_settings.comopts
    chunks = (1, stack_shape[1], stack_shape[2])

    grp_detector.create_dataset(
        DATA_DETECTOR,
        shape=stack_shape,
        dtype=stack_dtype,
        chunks=chunks,
        compression=compression,
        compression_opts=compression_opts,
    )

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

    dset_angle = grp_sample.create_dataset(
        ROT_ANGLE, shape=nframe, dtype=float
    )
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
    grp_process[VERSION] = get_version()
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
