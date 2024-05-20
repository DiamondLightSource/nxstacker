from nxstacker.tomojoin import tomojoin

from . import only_dls_file_system


@only_dls_file_system
def test_ptycho_i14_from_dir(tmp_path):
    proj_dir = (
        "/dls/i14/data/2024/cm37259-1/processed/ptychography_ptypy/"
        "known_probe_epie_eiger"
    )

    nxtomo_files = tomojoin(
        "ptychography",
        proj_dir=proj_dir,
        nxtomo_dir=str(tmp_path),
        from_scan="275019-275199",
        save_phase=True,
        save_modulus=True,
        save_complex=True,
        median_norm=True,
        unwrap_phase=True,
        remove_ramp=True,
    )

    assert len(nxtomo_files) == 3


@only_dls_file_system
def test_ptycho_i14_from_file_placeholder(tmp_path):
    proj_file = (
        "/dls/i14/data/2024/cm37259-1/processed/ptychography_ptypy/"
        "known_probe_epie_eiger/scan_%(scan)/scan_%(scan).ptyr"
    )

    nxtomo_files = tomojoin(
        "ptychography",
        proj_file=proj_file,
        nxtomo_dir=str(tmp_path),
        from_scan="275019-275199",
        save_phase=True,
        save_modulus=True,
        save_complex=True,
        median_norm=True,
        unwrap_phase=True,
        remove_ramp=True,
    )

    assert len(nxtomo_files) == 3
