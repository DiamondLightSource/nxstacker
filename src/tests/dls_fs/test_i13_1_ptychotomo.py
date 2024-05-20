from nxstacker.tomojoin import tomojoin

from . import only_dls_file_system


@only_dls_file_system
def test_ptycho_i13_1_step_proj(tmp_path):
    proj_dir = "/dls/i13-1/data/2024/cm37257-1/processing/kuda/384979"

    nxtomo_files = tomojoin(
        "ptychography",
        proj_dir=proj_dir,
        nxtomo_dir=str(tmp_path),
        from_scan="384979",
        from_proj="0-1000:100",
        save_phase=True,
        save_modulus=False,
        save_complex=False,
        median_norm=True,
        unwrap_phase=True,
        remove_ramp=True,
        compress=True,
    )

    assert len(nxtomo_files) == 1
