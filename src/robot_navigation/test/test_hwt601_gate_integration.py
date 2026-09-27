"""Exercise the real gate decision with other existing gates independently ready."""
import json
import math
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import pytest
from geometry_msgs.msg import Twist

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'robot_state_estimation' / 'test'))
sys.path.insert(0, str(ROOT / 'robot_navigation'))
from test_hwt601_fusion_health import ready_health
from robot_navigation.cmd_vel_mission_gate import CmdVelMissionGate


def gate_with_ready_sources():
    now = time.monotonic()
    health = ready_health(now=now)
    output, status = [], []
    command = Twist()
    command.linear.x = 0.05
    gate = SimpleNamespace(
        _hwt_guard=SimpleNamespace(health=health, failure=health.motion_failure),
        _hwt_status_pub=SimpleNamespace(publish=status.append),
        _estop_clear=True, _estop_time=now, _estop_timeout=1.0,
        _motion_tf_authorized=lambda: True,
        _mission_authorized=lambda status, now: True,
        _status={}, _status_time=now, _status_timeout=1.0,
        _require_localization=False, _localization_ready=True,
        _localization_time=now, _localization_timeout=1.0,
        _command=command, _command_time=now, _command_timeout=0.25,
        _search_authorized=lambda now: False, _publisher=SimpleNamespace(publish=output.append),
        _mode='blocked', get_logger=lambda: SimpleNamespace(warn=lambda msg: None),
    )
    return gate, health, output, status


@pytest.mark.parametrize('missing', ['raw', 'yaw', 'wheel'])
def test_gate_stops_even_with_current_fused_odom_and_other_sources(missing):
    gate, health, output, status = gate_with_ready_sources()
    CmdVelMissionGate._publish(gate)
    assert output[-1].linear.x == 0.05
    del health.samples[missing]
    CmdVelMissionGate._publish(gate)
    assert output[-1].linear.x == 0.0
    assert gate._mode == 'blocked'
    assert missing in health.latched_fault
    published = json.loads(status[-1].data)
    assert published['reason'] == health.latched_fault
    assert published['first_fault']['aggregate_reason'] == health.latched_fault
    assert published['first_fault']['observer'] == 'unspecified'
    assert missing + '_sample_missing_stale_or_invalid' in (
        published['first_fault']['violations'])


def test_gate_stops_with_nonfinite_raw_status_and_publishes_valid_json():
    gate, health, output, status = gate_with_ready_sources()
    CmdVelMissionGate._publish(gate)
    assert output[-1].linear.x == 0.05
    health.statuses['raw'][0]['age_s'] = math.nan
    CmdVelMissionGate._publish(gate)
    assert output[-1].linear.x == 0.0
    parsed = json.loads(status[-1].data,
                        parse_constant=lambda value: pytest.fail(value))
    assert parsed['reason'] == 'raw_driver_not_ready'
    assert parsed['first_fault']['raw_status']['age_s'] == {
        'nonfinite_float': 'nan'}
