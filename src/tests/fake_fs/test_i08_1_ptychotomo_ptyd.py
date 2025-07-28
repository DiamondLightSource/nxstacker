import h5py
import numpy as np
import pytest

from nxstacker.tomojoin import tomojoin

from .prepare_facility import PrepareI08_1
from .prepare_proj_file import PreparePtyPyFile


@pytest.fixture
def start_scan():
    return 32145


@pytest.fixture
def end_scan():
    return 32151


@pytest.fixture
def visit_id():
    return "cm69393-1"


@pytest.fixture
def detector_distance():
    return 0.072


@pytest.fixture
def sample_name():
    return "butterfly"


@pytest.fixture
def rotation_angle():
    return -31.8


@pytest.fixture
def sample_x_value_set():
    return np.linspace(-8, 8, num=31)


@pytest.fixture
def sample_y_value_set():
    return np.linspace(-8, 8, num=21)


@pytest.fixture
def x_px_size():
    return 3.21e-6


@pytest.fixture
def y_px_size():
    return 3.21e-6


@pytest.fixture
def scan_list(tmp_path, start_scan, end_scan):
    scan_nr = list(range(start_scan, end_scan + 1))

    with (tmp_path / "scan_list.txt").open("w") as f:
        for nr in scan_nr:
            f.write(f"{nr}\n")

    return tmp_path / "scan_list.txt"


@pytest.fixture
def angle_list(tmp_path, start_scan, end_scan, rotation_angle):
    nscan = end_scan - start_scan + 1

    with (tmp_path / "angle_list.txt").open("w") as f:
        for _ in range(nscan):
            f.write(f"{rotation_angle}\n")

    return tmp_path / "angle_list.txt"


@pytest.fixture
def angle_list_one_more(tmp_path, start_scan, end_scan, rotation_angle):
    nscan = end_scan - start_scan + 2

    with (tmp_path / "angle_list.txt").open("w") as f:
        for _ in range(nscan):
            f.write(f"{rotation_angle}\n")

    return tmp_path / "angle_list.txt"


def test_ptycho_i08_1_with_no_nxs(
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
    scan_list,
    angle_list,
):
    # prepare i08-1 raw data directory structure
    prep_i08_1 = PrepareI08_1(
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
    # do not write the dummy raw files
    for k in range(start_scan, end_scan + 1):
        fp = prep_i08_1.visit / f"processing/{k}.ptyd"
        prep_i08_1.raw_files.append(fp)
        prep_i08_1.scan_num.append(k)

    # prepare projection files from PtyPy
    ptypy_prep = PreparePtyPyFile(
        tmp_path,
        scan_num=prep_i08_1.scan_num,
        raw_files=prep_i08_1.raw_files,
        ob_shape=(sample_y_value_set.size, sample_x_value_set.size),
        x_px_size=x_px_size,
        y_px_size=y_px_size,
        use_nxs=True,
    )
    ptypy_prep.write_dummy_proj()

    # use placeholder
    proj_file = ptypy_prep.proj_dir / "scan_%(scan).ptyr"

    # stack
    nxtomo_files = tomojoin(
        "ptychography",
        proj_file=proj_file,
        nxtomo_dir=str(tmp_path),
        scan_list=scan_list,
        angle_list=angle_list,
        save_phase=True,
        save_modulus=True,
        save_complex=True,
        median_norm=True,
        unwrap_phase=True,
        remove_ramp=True,
        facility="i08-1",
        ignore_metadata_from_raw=True,
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
            np.array([rotation_angle] * num_scans),
        ).all()

    with h5py.File(nxtomo_modl, "r") as f:
        assert f["/entry/data/data"].dtype == np.float32

    with h5py.File(nxtomo_phas, "r") as f:
        assert f["/entry/data/data"].dtype == np.float32


def test_ptycho_i08_1_with_no_nxs_no_ignore_raw(
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
    scan_list,
    angle_list,
):
    # prepare i08-1 raw data directory structure
    prep_i08_1 = PrepareI08_1(
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
    # do not write the dummy raw files
    for k in range(start_scan, end_scan + 1):
        fp = prep_i08_1.visit / f"processing/{k}.ptyd"
        prep_i08_1.raw_files.append(fp)
        prep_i08_1.scan_num.append(k)

    # prepare projection files from PtyPy
    ptypy_prep = PreparePtyPyFile(
        tmp_path,
        scan_num=prep_i08_1.scan_num,
        raw_files=prep_i08_1.raw_files,
        ob_shape=(sample_y_value_set.size, sample_x_value_set.size),
        x_px_size=x_px_size,
        y_px_size=y_px_size,
        use_nxs=True,
    )
    ptypy_prep.write_dummy_proj()

    # use placeholder
    proj_file = ptypy_prep.proj_dir / "scan_%(scan).ptyr"

    # stack
    with pytest.raises(FileNotFoundError):
        _ = tomojoin(
            "ptychography",
            proj_file=proj_file,
            nxtomo_dir=str(tmp_path),
            scan_list=scan_list,
            angle_list=angle_list,
            save_phase=True,
            save_modulus=True,
            save_complex=True,
            median_norm=True,
            unwrap_phase=True,
            remove_ramp=True,
            facility="i08-1",
        )


def test_ptycho_i08_1_with_no_nxs_miss_angle_list(
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
    scan_list,
):
    # prepare i08-1 raw data directory structure
    prep_i08_1 = PrepareI08_1(
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
    # do not write the dummy raw files
    for k in range(start_scan, end_scan + 1):
        fp = prep_i08_1.visit / f"processing/{k}.ptyd"
        prep_i08_1.raw_files.append(fp)
        prep_i08_1.scan_num.append(k)

    # prepare projection files from PtyPy
    ptypy_prep = PreparePtyPyFile(
        tmp_path,
        scan_num=prep_i08_1.scan_num,
        raw_files=prep_i08_1.raw_files,
        ob_shape=(sample_y_value_set.size, sample_x_value_set.size),
        x_px_size=x_px_size,
        y_px_size=y_px_size,
        use_nxs=True,
    )
    ptypy_prep.write_dummy_proj()

    # use placeholder
    proj_file = ptypy_prep.proj_dir / "scan_%(scan).ptyr"

    # stack
    with pytest.raises(RuntimeError):
        _ = tomojoin(
            "ptychography",
            proj_file=proj_file,
            nxtomo_dir=str(tmp_path),
            scan_list=scan_list,
            save_phase=True,
            save_modulus=True,
            save_complex=True,
            median_norm=True,
            unwrap_phase=True,
            remove_ramp=True,
            facility="i08-1",
            ignore_metadata_from_raw=True,
        )


def test_ptycho_i08_1_with_no_nxs_scan_not_match_angle(
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
    scan_list,
    angle_list_one_more,
):
    # prepare i08-1 raw data directory structure
    prep_i08_1 = PrepareI08_1(
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
    # do not write the dummy raw files
    for k in range(start_scan, end_scan + 1):
        fp = prep_i08_1.visit / f"processing/{k}.ptyd"
        prep_i08_1.raw_files.append(fp)
        prep_i08_1.scan_num.append(k)

    # prepare projection files from PtyPy
    ptypy_prep = PreparePtyPyFile(
        tmp_path,
        scan_num=prep_i08_1.scan_num,
        raw_files=prep_i08_1.raw_files,
        ob_shape=(sample_y_value_set.size, sample_x_value_set.size),
        x_px_size=x_px_size,
        y_px_size=y_px_size,
        use_nxs=True,
    )
    ptypy_prep.write_dummy_proj()

    # use placeholder
    proj_file = ptypy_prep.proj_dir / "scan_%(scan).ptyr"

    # stack
    with pytest.raises(RuntimeError):
        _ = tomojoin(
            "ptychography",
            proj_file=proj_file,
            nxtomo_dir=str(tmp_path),
            scan_list=scan_list,
            angle_list=angle_list_one_more,
            save_phase=True,
            save_modulus=True,
            save_complex=True,
            median_norm=True,
            unwrap_phase=True,
            remove_ramp=True,
            facility="i08-1",
            ignore_metadata_from_raw=True,
        )
