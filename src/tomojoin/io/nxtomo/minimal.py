from pathlib import Path

import h5py
import numpy as np

ENTRY = "entry"
DEF = "definition"
TITLE = "title"
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

NX_ENTRY = Path(f"/{ENTRY}")
NX_INSTRUMENT = NX_ENTRY / INSTRUMENT
NX_SOURCE = NX_INSTRUMENT / SOURCE
NX_DETECTOR = NX_INSTRUMENT / DETECTOR
NX_SAMPLE = NX_ENTRY / SAMPLE
NX_DATA = NX_ENTRY / DATA_ENTRY
LINK_DATA = NX_DETECTOR / DATA_DETECTOR
LINK_ROT_ANG = NX_SAMPLE / ROT_ANGLE
LINK_IMAGE_KEY = NX_DETECTOR / IMAGE_KEY


def create_minimal(file_nxtomo, stack_shape, stack_dtype, dist, facility,
                   title=None, sample_desc=None):
    """Create a minimal NXtomo file for a stack of projections.
    """

    stack_shape = tuple(stack_shape)
    nframe = stack_shape[0]

    # check if exists

    with h5py.File(file_nxtomo, "w") as f:

        _create_entry(f, title=title)

        _create_instrument(f)

        _create_source(f, facility)

        _create_detector(f, dist, stack_shape, stack_dtype)

        _create_sample(f, nframe, sample_desc)

        # link data
        _link_data(f)

def _create_entry(root, title=None):
    grp_entry = root.create_group(str(NX_ENTRY))
    grp_entry.attrs["NX_class"] = "NXentry"
    grp_entry.attrs["default"] = DATA_ENTRY

    grp_entry[DEF] = "NXtomo"

    if title is not None:
        grp_entry[TITLE] = str(title)

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

def _create_detector(root, dist, stack_shape, stack_dtype):
    grp_detector = root.create_group(str(NX_DETECTOR))
    grp_detector.attrs["NX_class"] = "NXdetector"

    grp_detector.create_dataset(DATA_DETECTOR, shape=stack_shape,
                                dtype=stack_dtype)

    grp_detector[IMAGE_KEY] = np.zeros(stack_shape[0], dtype=int)

    # x_pixel_size from facility
    # y_pixel_size
    # distance
    grp_detector[X_PX_SZ] = 1.0
    grp_detector[X_PX_SZ].attrs["units"] = "m"
    grp_detector[Y_PX_SZ] = 1.0
    grp_detector[Y_PX_SZ].attrs["units"] = "m"
    grp_detector[DIST] = dist
    grp_detector[DIST].attrs["units"] = "m"

def _create_sample(root, nframe, sample_desc):
    grp_sample = root.create_group(str(NX_SAMPLE))
    grp_sample.attrs["NX_class"] = "NXsample"

    grp_sample[SAMPLE_NAME] = str(sample_desc)
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