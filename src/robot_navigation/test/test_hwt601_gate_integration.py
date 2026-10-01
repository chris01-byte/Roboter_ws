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


def startup_idle_gate():
    gate, health, output, status = gate_with_ready_sources()
    gate._hwt_mission_seen = False
    gate._allow_localization_search = False
    gate._allow_stage3_diagnostic = False
    gate._hwt_resume_pending = True
    gate._status = {'state': 'idle', 'active_command': None}
    gate._command = Twist()
    gate._mission_authorized = lambda status, now: False
    health.motion_failure()
    return gate, health, output, status


def test_recovered_pre_mission_gap_does_not_wait_for_nonexistent_resume():
    gate, health, output, status = startup_idle_gate()
    CmdVelMissionGate._on_explore_status(gate, String(data=json.dumps({
        'state': 'idle', 'phase': 'idle', 'hwt_recovery_sequence': 0})))
    assert gate._hwt_resume_pending is False
    CmdVelMissionGate._publish(gate)
    assert json.loads(status[-1].data)['hwt_motion_ready'] is True
    assert output[-1].linear.x == 0.0
    assert gate._mode == 'blocked'  # an actual mission is still required


@pytest.mark.parametrize('countercase', [
    'previous_mission', 'stale_manager', 'active_command', 'nonzero_command',
    'localization_search', 'diagnostic', 'hold', 'hard_fault', 'hold_sequence',
])
def test_idle_status_cannot_release_a_mission_hold_or_unhealthy_source(countercase):
    gate, health, output, status = startup_idle_gate()
    if countercase == 'previous_mission':
        gate._hwt_mission_seen = True
    elif countercase == 'stale_manager':
        gate._status_time -= 2.0
    elif countercase == 'active_command':
        gate._status['active_command'] = {'type': 'explore'}
    elif countercase == 'nonzero_command':
        gate._command.linear.x = .05
    elif countercase == 'localization_search':
        gate._allow_localization_search = True
    elif countercase == 'diagnostic':
        gate._allow_stage3_diagnostic = True
    elif countercase == 'hold':
        health.recovery_state = 'HOLD'
    elif countercase == 'hard_fault':
        health.recovery_state = 'TERMINAL_FAULT'
        health.latched_fault = 'invalid_raw'
    elif countercase == 'hold_sequence':
        gate._hwt_hold_sequence = 1
    CmdVelMissionGate._on_explore_status(gate, String(data=json.dumps({
        'state': 'idle', 'phase': 'idle', 'hwt_recovery_sequence': 0})))
    assert gate._hwt_resume_pending is True


def test_mission_seen_is_not_forgotten_after_idle():
    gate, health, output, status = startup_idle_gate()
    CmdVelMissionGate._on_status(gate, String(data=json.dumps({
        'state': 'running', 'active_command': {'type': 'explore'}})))
    CmdVelMissionGate._on_status(gate, String(data=json.dumps({
        'state': 'idle', 'active_command': None})))
    assert gate._hwt_mission_seen is True


def test_blocked_diagnostic_publisher_cannot_delay_stop_decision():
    import threading
    from robot_state_estimation.hwt601_fusion_guard import DeferredJsonPublisher
    gate,health,output,status=gate_with_ready_sources()
    entered,release=threading.Event(),threading.Event()
    class BlockedOutput:
        def publish(self,message):
            entered.set();release.wait(2.);status.append(message)
    worker=DeferredJsonPublisher(BlockedOutput())
    gate._hwt_status_worker=worker;gate._hwt_diagnostic_next=0.;gate._hwt_diagnostic_event=-1
    try:
        CmdVelMissionGate._publish(gate)
        assert entered.wait(1.) and output[-1].linear.x==.05
        del health.samples['wheel']
        # The diagnostic publisher remains blocked. The existing command
        # decision still returns and publishes STOP synchronously.
        CmdVelMissionGate._publish(gate)
        assert not release.is_set()
        assert output[-1].linear.x==0. and health.recovery_state=='TERMINAL_FAULT'
        assert health.fault_snapshot()['source_checks'][2]['first_rejecting_predicate']=='missing_message'
    finally:
        release.set();worker.close()
