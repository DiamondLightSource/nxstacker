from pathlib import Path

import numpy as np
import pytest

from nxstacker.utils.io import is_staging_area, pad2stack, top_level_dir


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


class TestPad2Stack:
    def test_proj_smaller(self):
        proj = np.arange(7 * 8).reshape(7, 8)
        stack_shape = (3, 10, 11)
        padded = pad2stack(proj, stack_shape)

        assert padded.shape == (10, 11)

    def test_proj_equal(self):
        proj = np.arange(10 * 11).reshape(10, 11)
        stack_shape = (3, 10, 11)
        padded = pad2stack(proj, stack_shape)

        assert padded.shape == (10, 11)

    def test_proj_larger(self):
        proj = np.arange(10 * 12).reshape(10, 12)
        stack_shape = (3, 10, 11)

        with pytest.raises(ValueError, match="larger"):
            pad2stack(proj, stack_shape)
