from pathlib import Path

from nxstacker.utils.parse import as_dls_staging_area


class TestAsDLSStagingArea:
    def test_dls_standard(self):
        input_dir = Path("/dls/i99/data/2047/cm12345-6")
        # if the argument is an absolute path, the previous path is
        # ignored
        staging_dir = Path("/dls/staging") / str(input_dir)[1:]

        assert as_dls_staging_area(input_dir) == staging_dir

    def test_non_dls(self):
        input_dir = Path("/tmp/i99/data/2047/cm12345-6")  # noqa: S108

        assert as_dls_staging_area(input_dir) == input_dir

    def test_already_staging(self):
        input_dir = Path("/dls/staging/dls/i99/data/2047/cm12345-6")

        assert as_dls_staging_area(input_dir) == input_dir
