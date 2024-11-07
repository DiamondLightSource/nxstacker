from pathlib import Path

from nxstacker.utils.io import is_staging_area, top_level_dir


class TestTopLevelDir:
    def test_default_depth(self):
        input_dir = Path("/dls/i99/data/2047/cm12345-1/raw/nexus/")

        assert top_level_dir(input_dir) == Path(
            "/dls/i99/data/2047/cm12345-1/"
        )

    def test_depth_for_staging(self):
        input_dir = Path("/dls/staging/dls/i99/data/2047/cm12345-1/raw/nexus/")

        assert top_level_dir(input_dir, depth=8) == Path(
            "/dls/staging/dls/i99/data/2047/cm12345-1/"
        )


class TestIsStagingArea:
    def test_is_staging(self):
        input_dir = Path("/dls/staging/dls/i99/data/2047/cm12345-1")

        assert is_staging_area(input_dir)

    def test_not_staging(self):
        input_dir = Path("/dls/i99/data/2047/cm12345-1")

        assert not is_staging_area(input_dir)

    def test_not_staging_non_dls(self):
        input_dir = Path("/abc/dls/staging/dls/i99/data/2047/cm12345-1")

        assert not is_staging_area(input_dir)
