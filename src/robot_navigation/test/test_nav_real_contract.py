from pathlib import Path
import sys

import yaml


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE_ROOT))

from robot_navigation.cmd_vel_mission_gate import room_motion_authorized  # noqa: E402


def test_real_command_chain_contains_smoother_before_collision_monitor():
    launch_source = (PACKAGE_ROOT / 'launch' / 'nav_real.launch.py').read_text()

    assert "nav_cmd_remap = [('cmd_vel', 'cmd_vel_nav_raw')]" in launch_source
    assert "executable='cmd_vel_mission_gate'" in launch_source
    assert "package='nav2_velocity_smoother'" in launch_source
    assert "('cmd_vel', 'cmd_vel_nav')" in launch_source
    assert "('cmd_vel_smoothed', 'cmd_vel_smoothed')" in launch_source
    assert "'velocity_smoother'" in launch_source
    assert "'static_map_odom_x'" in launch_source
    assert "'static_map_odom_y'" in launch_source
    assert "'static_map_odom_yaw'" in launch_source


def test_real_smoother_and_controller_limits_are_conservative():
    parameters = yaml.safe_load(
        (PACKAGE_ROOT / 'config' / 'nav2_params_real.yaml').read_text()
    )
    controller = parameters['controller_server']['ros__parameters']['FollowPath']
    progress = parameters['controller_server']['ros__parameters'][
        'progress_checker']
    smoother = parameters['velocity_smoother']['ros__parameters']

    assert controller['desired_linear_vel'] <= 0.10
    assert controller['rotate_to_heading_angular_vel'] <= 0.20
    assert controller['max_angular_accel'] <= 0.30
    assert progress['required_movement_radius'] == 0.10
    assert progress['movement_time_allowance'] >= 20.0
    assert smoother['feedback'] == 'OPEN_LOOP'
    assert smoother['max_velocity'] == [0.12, 0.0, 0.25]
    assert smoother['max_accel'] == [0.12, 0.0, 0.30]
    assert smoother['velocity_timeout'] <= 0.5
    assert parameters['bt_navigator']['ros__parameters'][
        'default_server_timeout'] >= 2000


def test_mission_gate_is_fail_closed():
    running = {
        'state': 'running',
        'phase': 'fahre_zum_raum',
        'active_command': {'type': 'go_to_room', 'room': 'Arbeitszimmer'},
    }
    assert room_motion_authorized(running)

    for state in ('failed', 'canceled', 'success', 'completed'):
        assert not room_motion_authorized({**running, 'state': state})
    assert not room_motion_authorized({**running, 'active_command': None})
    assert not room_motion_authorized({
        **running, 'active_command': {'type': 'explore'}})
    assert not room_motion_authorized(None)


def test_mission_gate_tolerates_shutdown_context_race():
    source = (PACKAGE_ROOT / 'robot_navigation' /
              'cmd_vel_mission_gate.py').read_text(encoding='utf-8')
    assert 'except RCLError:' in source
