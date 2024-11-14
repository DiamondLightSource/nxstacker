import h5py
import numpy as np
import pytest

from nxstacker.tomojoin import tomojoin

from .prepare_facility import PrepareI14
from .prepare_proj_file import PrepareXRFWindowFile


@pytest.fixture
def start_scan():
    return 10000


@pytest.fixture
def end_scan():
    return 10006


@pytest.fixture
def visit_id():
    return "cm12345-6"


@pytest.fixture
def detector_distance():
    return 1234.5


@pytest.fixture
def sample_name():
    return ""


@pytest.fixture
def rotation_angle():
    return -31.8


@pytest.fixture
def sample_x_value_set():
    return np.linspace(-14, 14, num=31)


@pytest.fixture
def sample_y_value_set():
    return np.linspace(-14, 14, num=21)


@pytest.fixture
def x_px_size(sample_x_value_set):
    # in m
    return np.diff(sample_x_value_set).mean() * 1e-3


@pytest.fixture
def y_px_size(sample_y_value_set):
    # in m
    return np.diff(sample_y_value_set).mean() * 1e-3


@pytest.fixture
def line_groups():
    return "W-La,Pt-La,Ni-Ka"


def test_xrf_i14_from_file_placeholder(
    tmp_path,
    start_scan,
    end_scan,
    visit_id,
    detector_distance,
    sample_name,
    rotation_angle,
    sample_x_value_set,
    sample_y_value_set,
    x_px_size,
    y_px_size,
    line_groups,
):
    # prepare i14 raw data directory structure
    prep_i14 = PrepareI14(
        tmp_path,
        start_scan,
        end_scan,
        visit_id=visit_id,
        detector_distance=detector_distance,
        sample_name=sample_name,
        rotation_angle=rotation_angle,
        sample_x_value_set=sample_x_value_set,
        sample_y_value_set=sample_y_value_set,
    )
    prep_i14.write_dummy_raw()

    # prepare projection files from XRF window by Python (i14)
    xrf_i14_prep = PrepareXRFWindowFile(
        tmp_path,
        scan_num=prep_i14.scan_num,
        ob_shape=(sample_y_value_set.size, sample_x_value_set.size),
        line_groups=line_groups,
    )
    xrf_i14_prep.write_dummy_proj()

    # use placeholder
    proj_file = xrf_i14_prep.proj_dir / "i14-%(scan)_xrf.nxs"

    # stack
    nxtomo_files = tomojoin(
        "xrf",
        proj_file=proj_file,
        nxtomo_dir=str(tmp_path),
        from_scan=f"{start_scan}-{end_scan}",
        exclude_scan=f"{start_scan}",
        transition=line_groups,
        facility="i14",
        raw_dir=prep_i14.visit,  # hard to deduce in testing
    )

    assert len(nxtomo_files) == 3

    num_scans = end_scan - start_scan  # excluded one

    for nxtomo_f in nxtomo_files:
        with h5py.File(nxtomo_f, "r") as f:
            assert f["/entry/data/data"].dtype == np.float64

            assert f["/entry/data/rotation_angle"].size == num_scans
            assert f["/entry/data/image_key"].size == num_scans
            assert f["/entry/data/data"].shape == (
                num_scans,
                sample_y_value_set.size,
                sample_x_value_set.size,
            )

            # now in m
            assert np.isclose(
                f["/entry/instrument/detector/distance"][()],
                detector_distance * 1e-3,
            )

            assert np.isclose(
                f["/entry/instrument/detector/x_pixel_size"][()], x_px_size
            )
            assert np.isclose(
                f["/entry/instrument/detector/y_pixel_size"][()], y_px_size
            )

            # all the same for testing
            assert np.isclose(
                f["/entry/data/rotation_angle"][()],
                np.array([rotation_angle] * num_scans),
            ).all()
