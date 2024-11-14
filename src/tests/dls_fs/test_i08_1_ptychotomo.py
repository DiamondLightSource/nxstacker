import pytest

from nxstacker.tomojoin import tomojoin

from . import only_dls_file_system


@pytest.fixture
def scan_list(tmp_path):
    scan_nr = [
        32080,
        32082,
        32085,
        32087,
        32095,
        32097,
        32102,
        32104,
        32108,
        32112,
        32116,
        32120,
        32129,
        32135,
        32139,
        32145,
        32149,
        32153,
        32157,
        32165,
        32167,
        32172,
        32174,
        32180,
        32182,
        32187,
        32189,
        32195,
        32197,
        32199,
        32201,
        32209,
        32211,
        32215,
        32217,
        32221,
        32223,
        32230,
        32232,
        32238,
        32240,
        32246,
        32250,
    ]

    with (tmp_path / "scan_list.txt").open("w") as f:
        for nr in scan_nr:
            f.write(f"{nr}\n")

    return tmp_path / "scan_list.txt"


@only_dls_file_system
def test_ptycho_i08_1_from_scan_list(scan_list, tmp_path):
    proj_file = (
        "/dls/i08-1/data/2023/mg32984-3/processing/benedikt/tilt1_sub1/"
        "scan_%(scan)/scan_%(scan).ptyr"
    )

    nxtomo_files = tomojoin(
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
    )

    assert len(nxtomo_files) == 3
