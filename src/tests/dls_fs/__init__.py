from pathlib import Path

import pytest

skip_test = not Path("/dls").is_dir()
reason = "The test is only relevant when it is run in DLS file system."

only_dls_file_system = pytest.mark.skipif(skip_test, reason=reason)
