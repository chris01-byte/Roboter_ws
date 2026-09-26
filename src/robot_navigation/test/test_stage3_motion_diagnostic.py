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
    ANGULAR_RADPS,
    FOOTPRINT_RADIUS_M,
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
    assert 'IfCondition(enable_stage3_motion_diagnostic)' in launch
    assert "create_service(\n            Trigger, '/stage3_motion_test/start'" in source
    assert "'/cmd_vel_stage3_diagnostic_raw'" in source
    assert "create_publisher(\n            Twist, '/cmd_vel'" not in source
    assert PHASES == (
        'forward', 'stop_after_forward', 'turn_positive',
        'stop_after_positive', 'turn_negative', 'stop_final')
    assert TEST_DISTANCE_M == 0.25
    assert TEST_TURN_RAD > 0.2617 and TEST_TURN_RAD < 0.2619
    assert LINEAR_MPS == 0.08
    assert ANGULAR_RADPS == 0.10


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
