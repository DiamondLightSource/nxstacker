from nxstacker.tomojoin import tomojoin

from . import only_dls_file_system


@only_dls_file_system
def test_xrf_i14_from_file_placeholder(tmp_path):
    proj_file = "/dls/i14/data/2024/cm37259-1/processed/i14-%(scan)_xrf.nxs"

    nxtomo_files = tomojoin(
        "xrf",
        proj_file=proj_file,
        nxtomo_dir=str(tmp_path),
        from_scan="274820-275001",
        exclude_scan="274827,274885",
        transition="V-Ka,Pt-La",
    )

    assert len(nxtomo_files) == 2
