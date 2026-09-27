"""Exercise the real gate decision with other existing gates independently ready."""
import json
import math
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import pytest
from geometry_msgs.msg import Twist
from std_msgs.msg import String

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'robot_state_estimation' / 'test'))
sys.path.insert(0, str(ROOT / 'robot_navigation'))
from test_hwt601_fusion_health import ready_health
from robot_navigation.cmd_vel_mission_gate import CmdVelMissionGate
from robot_navigation.cmd_vel_mission_gate import explore_motion_authorized


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
        _hwt_resume_pending=False, _hwt_hold_sequence=None,
        _hwt_seen_sequence=0, _hwt_resume_at=None, _allow_explore=True,
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
    if missing == 'wheel':
        assert missing in health.latched_fault
    else:
        assert health.recovery_state == 'HOLD'
        assert health.latched_fault is None
    published = json.loads(status[-1].data)
    assert missing in published['reason']
    assert published['first_fault']['aggregate_reason'] == published['reason']
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


def test_gate_needs_new_explorer_hold_resume_and_new_velocity_command():
    gate, health, output, _status = gate_with_ready_sources()
    gate._status = {
        'state': 'running', 'phase': 'Explore',
        'active_command': {'type': 'explore'}}
    CmdVelMissionGate._publish(gate)
    assert output[-1].linear.x > 0.0
    del health.samples['raw']
    CmdVelMissionGate._publish(gate)
    assert output[-1].linear.x == 0.0
    assert gate._hwt_resume_pending is True
    resumed = String(data=json.dumps({
        'phase': 'we_hwt_resumed', 'hwt_recovery_sequence': 1}))
    CmdVelMissionGate._on_explore_status(gate, resumed)
    assert gate._hwt_resume_pending is True
    now = time.monotonic()
    for name in ('raw', 'yaw', 'wheel'):
        health.sample(name, now, now, now)
        health.status(name, health.statuses[name][0], now)
    health.recovery_state = 'HEALTHY'
    health._hold_since = None
    hold = String(data=json.dumps({
        'phase': 'we_hwt_hold', 'hwt_recovery_sequence': 1}))
    CmdVelMissionGate._on_explore_status(gate, hold)
    CmdVelMissionGate._on_explore_status(gate, resumed)
    CmdVelMissionGate._publish(gate)
    assert gate._hwt_resume_pending is False
    assert output[-1].linear.x == 0.0  # old Nav2 command cannot replay
    gate._command_time = time.monotonic()
    CmdVelMissionGate._publish(gate)
    assert output[-1].linear.x > 0.0
    CmdVelMissionGate._on_explore_status(gate, String(data=json.dumps({
        'phase': 'we_hwt_recovery_validation', 'hwt_recovery_sequence': 1})))
    CmdVelMissionGate._publish(gate)
    assert output[-1].linear.x == 0.0
    assert gate._hwt_resume_pending is True
    CmdVelMissionGate._on_explore_status(gate, resumed)
    CmdVelMissionGate._publish(gate)
    assert output[-1].linear.x == 0.0
    gate._command_time = time.monotonic()
    CmdVelMissionGate._publish(gate)
    assert output[-1].linear.x > 0.0
