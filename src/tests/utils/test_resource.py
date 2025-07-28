from unittest.mock import patch

from nxstacker.utils.resource import num_cpus


class TestNumCpus:
    @patch("nxstacker.utils.resource.os")
    def test_below_capped(self, mock_os):
        mock_os.sched_getaffinity.return_value = list(range(5))

        assert num_cpus() == 5

    @patch("nxstacker.utils.resource.os")
    def test_above_capped(self, mock_os):
        mock_os.sched_getaffinity.return_value = list(range(96))

        assert num_cpus() == 8

    @patch("nxstacker.utils.resource.os")
    def test_custom_caps(self, mock_os):
        mock_os.sched_getaffinity.return_value = list(range(8))

        assert num_cpus(capped_at=4) == 4

    @patch("nxstacker.utils.resource.os")
    def test_capped_at_zero(self, mock_os):
        mock_os.sched_getaffinity.return_value = list(range(8))

        assert num_cpus(capped_at=0) == 1
