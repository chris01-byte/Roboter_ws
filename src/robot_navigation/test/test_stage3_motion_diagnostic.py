from pathlib import Path
import sys
from types import SimpleNamespace

from geometry_msgs.msg import Twist
import pytest


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE_ROOT))

from robot_navigation.cmd_vel_mission_gate import (  # noqa: E402
    CmdVelMissionGate,
)
from robot_navigation.stage3_motion_diagnostic import (  # noqa: E402
    Stage3MotionDiagnostic,
    ANGULAR_RADPS,
    FOOTPRINT_RADIUS_M,
    LAB_MODE,
    LINEAR_MPS,
    PHASES,
    TEST_DISTANCE_M,
    TEST_TURN_RAD,
    directed_turn_progress,
    disk_in_polygon,
    point_in_polygon,
)


SCOPE = ((-1.0, -1.0), (2.0, -1.0), (2.0, 1.0), (-1.0, 1.0))


def test_stage3_test_is_opt_in_single_sequence_and_not_a_cmd_vel_publisher():
    launch = (PACKAGE_ROOT / 'launch' / 'nav_mapping.launch.py').read_text()
    source = (PACKAGE_ROOT / 'robot_navigation' /
              'stage3_motion_diagnostic.py').read_text()

    assert "'enable_stage3_motion_diagnostic', default_value='false'" in launch
    assert "'lab_external_hardware_halt_attested', default_value='false'" in launch
    assert "'start_stage3_motion_diagnostic', default_value='true'" in launch
    assert 'start_stage3_motion_diagnostic' in launch
    assert "create_service(\n            Trigger, '/stage3_motion_test/start'" in source
    assert "'/cmd_vel_stage3_diagnostic_raw'" in source
    assert "NearFieldStatus, '/near_field/status'" in source
    assert "create_publisher(\n            Twist, '/cmd_vel'" not in source
    assert PHASES == (
        'forward', 'stop_after_forward', 'turn_positive',
        'stop_after_positive', 'turn_negative', 'stop_final')
    assert TEST_DISTANCE_M == 0.25
    assert TEST_TURN_RAD > 0.2617 and TEST_TURN_RAD < 0.2619
    assert LINEAR_MPS == 0.08
    assert ANGULAR_RADPS == 0.10
    assert LAB_MODE == 'stage3_bounded_motion_test'
    assert "'lab_mode': LAB_MODE" in source
    assert 'if not self.external_hardware_halt_attested:' in source
    assert "'external_hardware_halt_attested': (" in source


def test_scope_contains_padded_footprint_and_rejects_edge_crossing():
    assert point_in_polygon(0.0, 0.0, SCOPE)
    assert disk_in_polygon(0.0, 0.0, FOOTPRINT_RADIUS_M, SCOPE)
    assert not disk_in_polygon(1.8, 0.0, FOOTPRINT_RADIUS_M, SCOPE)


def test_positive_and_negative_turns_measure_full_relative_15_degree_steps():
    start_yaw = 0.4
    positive_endpoint = start_yaw + TEST_TURN_RAD
    assert directed_turn_progress(start_yaw, positive_endpoint, 1.0) == pytest.approx(
        TEST_TURN_RAD)
    assert directed_turn_progress(
        positive_endpoint, start_yaw, -1.0) == pytest.approx(TEST_TURN_RAD)
    halfway_back = positive_endpoint - TEST_TURN_RAD / 2.0
    assert directed_turn_progress(
        positive_endpoint, halfway_back, -1.0) < TEST_TURN_RAD
    # A center can remain in the scope while the padded robot footprint exits.
    assert point_in_polygon(1.8, 0.0, SCOPE)
    assert not disk_in_polygon(1.8, 0.0, FOOTPRINT_RADIUS_M, SCOPE)


def test_gate_rejects_reverse_and_over_limit_diagnostic_inputs():
    gate = CmdVelMissionGate.__new__(CmdVelMissionGate)
    gate._explore_direct_max_linear = 0.08
    gate._explore_direct_max_angular = 0.10
    class Logger:
        def error(self, _message):
            pass
    gate._publisher = SimpleNamespace(publish=lambda message: None)
    gate._logger = Logger()
    gate._on_stage3_diagnostic_command(Twist())
    assert gate._stage3_command_time is not None
    for linear, angular in ((-0.001, 0.0), (0.081, 0.0), (0.0, 0.101)):
        command = Twist()
        command.linear.x = linear
        command.angular.z = angular
        gate._on_stage3_diagnostic_command(command)
        assert gate._stage3_command_time is None


def test_diagnostic_deactivation_immediately_publishes_zero():
    published = []
    gate = CmdVelMissionGate.__new__(CmdVelMissionGate)
    gate._publisher = SimpleNamespace(publish=published.append)
    gate._on_stage3_diagnostic_active(SimpleNamespace(data=False))
    assert gate._stage3_active is False
    assert gate._stage3_command_time is None
    assert len(published) == 1
    assert published[0].linear.x == 0.0
    assert published[0].angular.z == 0.0


def test_diagnostic_inputs_are_explicitly_routed_before_gate():
    launch = (PACKAGE_ROOT / 'launch' / 'nav_mapping.launch.py').read_text()
    gate = (PACKAGE_ROOT / 'robot_navigation' /
            'cmd_vel_mission_gate.py').read_text()
    assert "'allow_stage3_motion_diagnostic': ParameterValue(" in launch
    assert "'/cmd_vel_stage3_diagnostic_raw'" in gate
    assert "self._stage3_diagnostic_health_authorized(now)" in gate
    assert "mode = 'stage3_diagnostic'" in gate
    assert "('cmd_vel_smoothed', 'cmd_vel_smoothed')" in launch
    assert "'cmd_vel_recovery_blocked'" in launch


def test_operator_stop_deactivates_existing_diagnostic_without_new_child():
    node = Stage3MotionDiagnostic.__new__(Stage3MotionDiagnostic)
    node._state = 'forward'
    finished = []
    node._finish = lambda state, reason: finished.append((state, reason))
    response = node._stop(None, SimpleNamespace())
    assert response.success is True
    assert finished == [('aborted', 'Expliziter Diagnoseabbruch')]


def test_next_turn_at_start_boundary_is_stopped_before_publication():
    node = Stage3MotionDiagnostic.__new__(Stage3MotionDiagnostic)
    node.scope_polygon = ((-.13, -.9), (2., -.9), (2., .7), (-.13, .7))
    node._scope_pose = lambda: (0., 0., 0.)
    finished = []
    node._finish = lambda state, reason: finished.append((state, reason))
    node._publish_command(0., .1)
    assert finished and finished[0][0] == 'aborted'


@pytest.mark.parametrize('measured_rpm,age,expected', [(0., .02, True), (2., .02, False), (0., .19, False)])
def test_stop_uses_real_base_status_field_names_and_measured_rpm(measured_rpm, age, expected):
    node = Stage3MotionDiagnostic.__new__(Stage3MotionDiagnostic)
    node._latest = dict(base=dict(meas_motor_rpm_left=measured_rpm, meas_motor_rpm_right=0.,
                                 encoder_feedback_ok=True, encoder_stale=False,
                                 encoder_feedback_age_s=age), odom=dict(vx=0., wz=0.))
    for name in ('gate_out', 'smoother_out', 'collision_monitor_out'):
        node._latest[name] = dict(vx=0., wz=0.)
    # Collision monitor legitimately stops repeating zero after two seconds.
    node._fresh = lambda name, timeout: name != 'collision_monitor_out'
    assert node._stationary() is expected


def bound_map_node():
    node = Stage3MotionDiagnostic.__new__(Stage3MotionDiagnostic)
    node._wheel_scope_bound, node.session_id = True, 'actual-lab-session'
    node._scope_map_epoch_id = 'map-'+'a'*64
    node._latest = dict(
        map_status=dict(ok=True, map=dict(age_seconds=.1, summary=dict(
            frame_id='map', fingerprint='a'*64))),
        region_status=dict(context=dict(session_id='actual-lab-session',
            map_id='map-'+'a'*64, frame_id='map'), source=dict(
            stale=True, stale_sources=['portal_memory', 'region_graph'],
            map_revision=12, source_map=dict(state='fresh', age_seconds=.5,
                revision=12, lag_revisions=0))))
    return node


def test_fixed_lab_map_binding_uses_fresh_real_map_without_portal_inventory():
    node = bound_map_node()
    assert node._scope_map_binding() == 'a'*64
    # Legacy mode still requires its original whole-region source contract.
    node._wheel_scope_bound = False
    assert node._scope_map_binding() is None


def test_immutable_lab_epoch_survives_real_map_growth_without_scope_shift():
    node = bound_map_node()
    node._latest['map_status']['map']['summary']['fingerprint'] = 'b'*64
    assert node._scope_map_binding() == 'b'*64
    assert node._scope_map_epoch_id == 'map-'+'a'*64


@pytest.mark.parametrize('field,value', [('state','stale'), ('age_seconds',2.01),
    ('age_seconds',float('nan')), ('age_seconds',True), ('revision',11),
    ('revision',True), ('lag_revisions',1)])
def test_fixed_lab_still_rejects_bad_or_old_actual_map_source(field, value):
    node = bound_map_node()
    node._latest['region_status']['source']['source_map'][field] = value
    assert node._scope_map_binding() is None


@pytest.mark.parametrize('field,value', [('session_id','other-session'),
    ('map_id','map-'+'b'*64), ('frame_id','odom')])
def test_fixed_lab_still_rejects_wrong_map_context(field, value):
    node = bound_map_node()
    node._latest['region_status']['context'][field] = value
    assert node._scope_map_binding() is None


@pytest.mark.parametrize('state,started,active', [('idle',False,False),
    ('forward',True,True), ('stop_final',True,True), ('complete',True,False),
    ('aborted',True,False)])
def test_zero_publication_never_invents_idle_test_activation(state, started, active):
    node = Stage3MotionDiagnostic.__new__(Stage3MotionDiagnostic)
    node._state, node._test_started_once = state, started
    flags, commands = [], []
    node._active_pub = SimpleNamespace(publish=flags.append)
    node._command_pub = SimpleNamespace(publish=commands.append)
    node._publish_command()
    assert [m.data for m in flags] == [active]
    assert commands[0].linear.x == commands[0].angular.z == 0.


def test_explicit_translation_probe_finishes_at_measured_stop_without_turn():
    import time
    node = Stage3MotionDiagnostic.__new__(Stage3MotionDiagnostic)
    node.forward_stop_only = True
    node._state = 'stop_after_forward'
    node._phase_started = time.monotonic()-.8
    node._stop_stable_since = time.monotonic()-.8
    node._latest = {}
    node._last_nonzero_requested = False
    node._health_failure = lambda: None
    node._scope_pose = lambda: (.25, 0., 0.)
    node._scope_map_binding = lambda **kw: 'actual-test-epoch'
    node._stationary = lambda: True
    events = []
    node._publish_command = lambda *args: events.append(('command', args))
    node._finish = lambda *args: events.append(('finish', args))
    node._enter = lambda *args: events.append(('enter', args))
    node._tick()
    assert events == [('command', ()), ('finish', ('complete', 'Feste Translation und Stillstand bestaetigt'))]


def test_probe_selection_reduces_only_the_actual_executed_sweep():
    node = Stage3MotionDiagnostic.__new__(Stage3MotionDiagnostic)
    node.scope_polygon = ((-1., -1.), (2., -1.), (2., .5), (-1., .5))
    assert not node._sequence_in_scope((0., 0., .36))
    node.forward_stop_only = True
    node.measurement_distance_m = .25
    assert node._sequence_in_scope((0., 0., .36))
    node.forward_stop_only = False
    node.negative_turn_only = True
    assert node._sequence_in_scope((0., 0., .36))
