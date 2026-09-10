import math
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from hwt601_encoder_dynamic_turn import (  # noqa: E402
    angle_delta, base_healthy, stationary, turn_command)


def healthy_state():
    return dict(
        dry_run=False, allow_rs485=True, rs485_ready=True,
        odometry_source='encoder_position', encoder_feedback_ok=True,
        encoder_initialized=True, encoder_stale=False,
        encoder_config_fault_latched=False, encoder_consecutive_failures=0,
        modbus_read_failures=0, encoder_pair_read_duration_s=0.012,
        meas_v_mps=0.0, meas_w_radps=0.0)


def test_angle_wrap_and_stationary_health():
    assert math.degrees(angle_delta(math.radians(-179), math.radians(179))) \
        == pytest.approx(2.0)
    assert base_healthy(healthy_state(), 0.1)
    assert stationary(healthy_state())


@pytest.mark.parametrize('key,value', [
    ('dry_run', True), ('allow_rs485', False), ('rs485_ready', False),
    ('encoder_feedback_ok', False), ('encoder_stale', True),
    ('encoder_consecutive_failures', 1), ('modbus_read_failures', 1),
    ('encoder_pair_read_duration_s', 0.051),
])
def test_health_fails_closed(key, value):
    state = healthy_state()
    state[key] = value
    assert not base_healthy(state, 0.1)


@pytest.mark.parametrize('direction', (-1, 1))
def test_bounded_command_and_target(direction):
    assert turn_command(1, direction * 5, direction * 5,
                        direction * 5, 0.0, direction) \
        == direction * 0.08
    assert turn_command(4, direction * 17, direction * 17,
                        direction * 17, 0.0, direction) == 0.0


@pytest.mark.parametrize('values', [
    (10.1, 10, 10, 10, 0.0, 1),
    (2, 31, 20, 20, 0.0, 1),
    (2, 5, -3, 5, 0.0, 1),
    (2, 5, 12, 5, 0.0, 1),
    (2, 5, 5, 12, 0.0, 1),
    (2, 5, 5, 5, 0.031, 1),
    (6.1, 1, 1, 1, 0.0, 1),
])
def test_turn_faults(values):
    with pytest.raises(ValueError):
        turn_command(*values)
