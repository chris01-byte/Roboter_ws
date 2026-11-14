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
        _hwt_guard=SimpleNamespace(health=health, failure=health.motion_failure,
                                   refresh_passive_wheel=lambda: None,
                                   refresh_current_wheel=lambda: None,
                                   refresh_current_imu=lambda: None),
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


def test_source_receive_happens_before_health_lock():
    gate, health, output, status = gate_with_ready_sources()
    observed = []
    def receive():
        assert not health.lock._is_owned()
        observed.append(True)
    gate._hwt_guard.refresh_current_wheel = receive
    gate._hwt_guard.refresh_current_imu = receive
    CmdVelMissionGate._publish(gate)
    assert len(observed) == 2 and output[-1].linear.x == .05


def diagnostic_ack_fixture():
    gate, health, output, status = gate_with_ready_sources()
    now = time.monotonic()
    gate._allow_stage3_diagnostic, gate._stage3_active = True, False
    gate._stage3_active_time = now
    gate._allow_localization_search = False
    gate._stage3_diagnostic_health_authorized = lambda _: True
    gate._stage3_command = Twist()
    gate._stage3_command_time = now
    gate._command = Twist()
    gate._status = dict(state='idle',active_command={})
    gate._hwt_resume_pending, gate._hwt_mission_seen = True, True
    health.statuses['wheel'][0].update(meas_motor_rpm_left=0.,
        meas_motor_rpm_right=0.,meas_v_mps=0.,meas_w_radps=0.,encoder_feedback_age_s=.02)
    health.sample_details['wheel'] = dict(twist=[0.]*6)
    return gate, health


def test_explicit_lab_ack_preserves_fault_budgets_history_and_cannot_replay():
    gate, health = diagnostic_ack_fixture()
    health.recovery_attempts, health.wheel_recovery_attempts = 1, 2
    journal = health.recovery_events
    response = CmdVelMissionGate._acknowledge_diagnostic_hold(gate,None,SimpleNamespace())
    assert response.success and not gate._hwt_resume_pending
    assert gate._hwt_mission_seen and not gate._stage3_active
    assert gate._stage3_command_time is None
    assert (health.recovery_attempts,health.wheel_recovery_attempts) == (1,2)
    assert health.recovery_events is journal


@pytest.mark.parametrize('failure', ['disabled','active','moving','missing_wheel',
    'terminal','estop','old_idle','bad_near','old_activation'])
def test_explicit_lab_ack_still_rejects_real_bad_state(failure):
    gate, health = diagnostic_ack_fixture()
    if failure=='disabled':gate._allow_stage3_diagnostic=False
    elif failure=='active':gate._stage3_active=True
    elif failure=='moving':health.statuses['wheel'][0]['meas_motor_rpm_left']=2.
    elif failure=='missing_wheel':del health.samples['wheel']
    elif failure=='terminal':health.latched_fault='real_terminal_fault'
    elif failure=='estop':gate._estop_clear=False
    elif failure=='old_idle':gate._status_time-=2.
    elif failure=='bad_near':gate._stage3_diagnostic_health_authorized=lambda _:False
    elif failure=='old_activation':gate._stage3_active_time-=1.
    response=CmdVelMissionGate._acknowledge_diagnostic_hold(gate,None,SimpleNamespace())
    assert not response.success and gate._hwt_resume_pending


@pytest.mark.parametrize('failure', [None,'stale_command','active_false',
    'near','estop','tf','wheel','hold'])
def test_idle_manager_does_not_pulse_zero_into_an_authorized_real_diagnostic(failure):
    gate, health, output, _ = gate_with_ready_sources()
    now=time.monotonic()
    gate._allow_stage3_diagnostic=True
    gate._stage3_active=True
    gate._stage3_active_time=gate._stage3_command_time=now
    gate._stage3_diagnostic_health_authorized=lambda _:True
    gate._mission_authorized=lambda *_:False
    gate._search_authorized=lambda _:False
    if failure=='stale_command':gate._stage3_command_time-=2.
    elif failure=='active_false':gate._stage3_active=False
    elif failure=='near':gate._stage3_diagnostic_health_authorized=lambda _:False
    elif failure=='estop':gate._estop_clear=False
    elif failure=='tf':gate._motion_tf_authorized=lambda:False
    elif failure=='wheel':del health.samples['wheel']
    elif failure=='hold':gate._hwt_resume_pending=True
    CmdVelMissionGate._on_status(gate,String(data=json.dumps(dict(state='idle',active_command={}))))
    assert bool(output) is (failure is not None)
    if output:assert output[-1].linear.x==output[-1].angular.z==0.


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
        gate._stage3_active = True
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


def test_real_empty_idle_command_does_not_invent_previous_mission():
    gate, health, output, status = startup_idle_gate()
    CmdVelMissionGate._on_status(gate, String(data=json.dumps({
        'state': 'idle', 'active_command': {}})))
    assert gate._hwt_mission_seen is False
    CmdVelMissionGate._on_explore_status(gate, String(data=json.dumps({
        'state': 'idle', 'phase': 'idle', 'hwt_recovery_sequence': 0})))
    assert gate._hwt_resume_pending is False


@pytest.mark.parametrize('countercase', [None, 'moving_rpm', 'old_feedback', 'missing_twist', 'used_test'])
def test_unused_diagnostic_startup_recovers_only_with_measured_rest(countercase):
    gate, health, output, status = startup_idle_gate()
    gate._status['active_command'] = {}
    gate._allow_stage3_diagnostic = True
    gate._stage3_active = False
    gate._stage3_command = Twist()
    health.statuses['wheel'][0].update(meas_motor_rpm_left=0., meas_motor_rpm_right=0.,
        meas_v_mps=0., meas_w_radps=0., encoder_feedback_age_s=.01)
    health.sample_details['wheel'] = dict(twist=[0.]*6)
    if countercase == 'moving_rpm':health.statuses['wheel'][0]['meas_motor_rpm_left']=1.
    elif countercase == 'old_feedback':health.statuses['wheel'][0]['encoder_feedback_age_s']=.19
    elif countercase == 'missing_twist':health.sample_details['wheel']={}
    elif countercase == 'used_test':gate._hwt_mission_seen=True
    CmdVelMissionGate._on_explore_status(gate, String(data=json.dumps({
        'state': 'idle', 'phase': 'idle', 'hwt_recovery_sequence': 0})))
    assert gate._hwt_resume_pending is (countercase is not None)
    assert all(m.linear.x == 0. for m in output)


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
