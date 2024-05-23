import h5py
import numpy as np
import pytest
from nxstacker.tomojoin import tomojoin

from .prepare_facility import PrepareI14
from .prepare_proj_file import PreparePtyPyFile


@pytest.fixture()
def start_scan():
    return 10000


@pytest.fixture()
def end_scan():
    return 10006


@pytest.fixture()
def visit_id():
    return "cm12345-6"


@pytest.fixture()
def detector_distance():
    return 1234.5


@pytest.fixture()
def sample_name():
    return ""


@pytest.fixture()
def rotation_angle():
    return -31.8


@pytest.fixture()
def sample_x_value_set():
    return np.linspace(-14, 14, num=31)


@pytest.fixture()
def sample_y_value_set():
    return np.linspace(-14, 14, num=21)


@pytest.fixture()
def x_px_size():
    return 1.23e-9


@pytest.fixture()
def y_px_size():
    return 1.23e-9


def test_ptycho_i14_from_dir(
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

    # prepare projection files from PtyPy
    ptypy_prep = PreparePtyPyFile(
        tmp_path,
        scan_num=prep_i14.scan_num,
        raw_files=prep_i14.raw_files,
        ob_shape=(sample_y_value_set.size, sample_x_value_set.size),
        x_px_size=x_px_size,
        y_px_size=y_px_size,
    )
    ptypy_prep.write_dummy_proj()

    # stack
    nxtomo_files = tomojoin(
        "ptychography",
        proj_dir=ptypy_prep.proj_dir,
        nxtomo_dir=str(tmp_path),
        from_scan=f"{start_scan}-{end_scan}",
        save_phase=True,
        save_modulus=True,
        save_complex=True,
        median_norm=True,
        unwrap_phase=True,
        remove_ramp=True,
        facility="i14",
    )

    assert len(nxtomo_files) == 3

    nxtomo_cplx = nxtomo_files[0]
    nxtomo_modl = nxtomo_files[1]
    nxtomo_phas = nxtomo_files[2]
    num_scans = end_scan - start_scan + 1

    with h5py.File(nxtomo_cplx, "r") as f:
        assert f["/entry/data/data"].dtype == np.complex64

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

    with h5py.File(nxtomo_modl, "r") as f:
        assert f["/entry/data/data"].dtype == np.float32

    with h5py.File(nxtomo_phas, "r") as f:
        assert f["/entry/data/data"].dtype == np.float32


def test_ptycho_i14_from_file_placeholder(
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

    # prepare projection files from PtyPy
    ptypy_prep = PreparePtyPyFile(
        tmp_path,
        scan_num=prep_i14.scan_num,
        raw_files=prep_i14.raw_files,
        ob_shape=(sample_y_value_set.size, sample_x_value_set.size),
        x_px_size=x_px_size,
        y_px_size=y_px_size,
    )
    ptypy_prep.write_dummy_proj()

    # use placeholder
    proj_file = ptypy_prep.proj_dir / "scan_%(scan).ptyr"

    # stack
    nxtomo_files = tomojoin(
        "ptychography",
        proj_file=proj_file,
        nxtomo_dir=str(tmp_path),
        from_scan=f"{start_scan}-{end_scan}",
        save_phase=True,
        save_modulus=True,
        save_complex=True,
        median_norm=True,
        unwrap_phase=True,
        remove_ramp=True,
        facility="i14",
    )

    assert len(nxtomo_files) == 3

    nxtomo_cplx = nxtomo_files[0]
    nxtomo_modl = nxtomo_files[1]
    nxtomo_phas = nxtomo_files[2]
    num_scans = end_scan - start_scan + 1

    with h5py.File(nxtomo_cplx, "r") as f:
        assert f["/entry/data/data"].dtype == np.complex64

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

    with h5py.File(nxtomo_modl, "r") as f:
        assert f["/entry/data/data"].dtype == np.float32

    with h5py.File(nxtomo_phas, "r") as f:
        assert f["/entry/data/data"].dtype == np.float32
