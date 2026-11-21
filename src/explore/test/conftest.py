"""Test the built native arithmetic even when colcon starts in the source tree.

The installed runtime imports this extension normally. A source-directory
pytest run otherwise silently selects the optional NumPy fallback and cannot
qualify the installed helper's fixed processing window. Dedicated equivalence
tests still explicitly exercise both implementations and malformed buffers.
"""
import importlib.util
from pathlib import Path
import sysconfig

import pytest


@pytest.fixture(scope='session', autouse=True)
def built_reserved_sweep():
    from ament_index_python.packages import get_package_prefix
    import explore.metric_frontier as geometry

    if geometry._reserved_sweep is not None:
        return geometry._reserved_sweep
    prefix = Path(get_package_prefix('explore'))
    files = list(prefix.rglob('_reserved_sweep'+sysconfig.get_config_var('EXT_SUFFIX')))
    assert len(files) == 1, 'Build explore before qualifying its native processing window'
    spec = importlib.util.spec_from_file_location('explore._reserved_sweep', files[0])
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    geometry._reserved_sweep = module
    return module
