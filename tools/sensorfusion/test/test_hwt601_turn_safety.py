from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import hwt601_drehtest as module  # noqa: E402


def test_noninteractive_run_cannot_consume_piped_motion_markers(monkeypatch):
    monkeypatch.setattr(sys, 'argv', ['hwt601_drehtest.py', '--run',
                                     '--motor-power-off', '--stationary-confirmed'])
    monkeypatch.setattr(sys.stdin, 'isatty', lambda: False)
    with pytest.raises(SystemExit) as error:
        module.main()
    assert error.value.code == 2


def test_test_script_has_no_actuator_or_configuration_path():
    source = Path(module.__file__).read_text()
    assert 'cmd_vel' not in source
    assert 'base_hardware' not in source
    assert 'rclpy' not in source
    assert 'stationary_adaptation_time_constant_s=0.0' in source
    assert 'estimator.update' in source
    assert 'scale_assumption' not in source  # No parameter-update path.
