import h5py
import numpy as np
import pytest
from nxstacker.parser.proj_identifier import ProjIdentifier
from nxstacker.tomojoin import tomojoin

from .prepare_facility import PrepareI13_1
from .prepare_proj_file import PreparePtyREXFile


@pytest.fixture()
def scan():
    return 384979


@pytest.fixture()
def start_proj():
    return 0


@pytest.fixture()
def end_proj():
    return 6


@pytest.fixture()
def visit_id():
    return "cm96854-1"


@pytest.fixture()
def detector_distance():
    return 4.75


@pytest.fixture()
def sample_name():
    return "coherence"


@pytest.fixture()
def rotation_angle():
    return -31.8


@pytest.fixture()
def sample_x_value_set():
    return np.linspace(-13, 13, num=31)


@pytest.fixture()
def sample_y_value_set():
    return np.linspace(-13, 13, num=21)


@pytest.fixture()
def x_px_size():
    return 3.21e-6


@pytest.fixture()
def y_px_size():
    return 3.21e-6


def test_ptycho_i13_1_step_proj(
    tmp_path,
    scan,
    start_proj,
    end_proj,
    visit_id,
    detector_distance,
    sample_name,
    rotation_angle,
    sample_x_value_set,
    sample_y_value_set,
    x_px_size,
    y_px_size,
):
    # prepare i13-1 raw data directory structure
    prep_i13_1 = PrepareI13_1(
        tmp_path,
        scan,
        start_proj,
        end_proj,
        visit_id=visit_id,
        detector_distance=detector_distance,
        sample_name=sample_name,
        rotation_angle=rotation_angle,
        sample_x_value_set=sample_x_value_set,
        sample_y_value_set=sample_y_value_set,
    )
    prep_i13_1.write_dummy_raw()

    # prepare projection files from PtyREX
    ptyrex_prep = PreparePtyREXFile(
        tmp_path,
        scan_num=scan,
        proj_num=prep_i13_1.projs,
        ob_shape=(sample_y_value_set.size * 2, sample_x_value_set.size * 2),
        x_px_size=x_px_size,
        y_px_size=y_px_size,
        detector_distance=detector_distance,
    )
    ptyrex_prep.write_dummy_proj()

    # stack
    nxtomo_files = tomojoin(
        "ptychography",
        proj_dir=ptyrex_prep.proj_dir,
        nxtomo_dir=str(tmp_path),
        from_scan=str(scan),
        from_proj=f"{start_proj}-{end_proj}:2",
        save_phase=True,
        save_modulus=False,
        save_complex=False,
        median_norm=True,
        unwrap_phase=True,
        remove_ramp=True,
        facility="i13-1",
        raw_dir=prep_i13_1.visit,  # hard to deduce in testing
    )

    assert len(nxtomo_files) == 1

    nxtomo_phas = nxtomo_files[0]
    num_projs = ProjIdentifier(f"{start_proj}-{end_proj}:2").num_identifiers

    with h5py.File(nxtomo_phas, "r") as f:
        assert f["/entry/data/data"].dtype == np.float32

        assert f["/entry/data/rotation_angle"].size == num_projs
        assert f["/entry/data/image_key"].size == num_projs
        assert f["/entry/data/data"].shape == (
            num_projs,
            sample_y_value_set.size * 2,
            sample_x_value_set.size * 2,
        )

        # in m
        assert np.isclose(
            f["/entry/instrument/detector/distance"][()],
            detector_distance,
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
            np.array([rotation_angle] * num_projs),
        ).all()
