from pathlib import Path
import sys

import pytest
import yaml


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE_ROOT))

from robot_navigation.cmd_vel_mission_gate import (  # noqa: E402
    explore_direct_values_valid,
    explore_health_authorized,
    explore_motion_authorized,
    explore_scan_values_valid,
    localization_search_authorized,
    localization_search_values_valid,
    localization_motion_authorized,
    room_motion_authorized,
)


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


def test_mapping_launch_has_single_slam_owner_and_explicit_explore_gate():
    source = (
        PACKAGE_ROOT / 'launch' / 'nav_mapping.launch.py'
    ).read_text(encoding='utf-8')

    assert "'slam_lidar.launch.py'" in source
    assert "'vl53_near_field.launch.py'" in source
    assert "'collision_monitor_mapping_params.yaml'" in source
    assert "'collision_params_file': mapping_collision_params" in source
    assert "'safety_monitor.launch.py'" in source
    assert "'explore.launch.py'" in source
    assert "'enable_auto_explore', default_value='false'" in source
    assert "'allow_explore_mission'" in source
    assert "'enable_real_explore': enable_auto_explore" in source
    assert "'explore_params_overlay': explore_params_overlay" in source
    assert "period=4.0" in source
    assert 'nav2_map_server' not in source
    assert 'nav2_amcl' not in source
    assert 'static_transform_publisher' not in source
    assert "package='nav2_behaviors'" in source
    assert "('cmd_vel', 'cmd_vel_recovery_blocked')" in source


def test_real_smoother_and_controller_limits_are_conservative():
    parameters = yaml.safe_load(
        (PACKAGE_ROOT / 'config' / 'nav2_params_real.yaml').read_text()
    )
    controller_server = parameters['controller_server']['ros__parameters']
    controller = controller_server['FollowPath']
    progress = controller_server['progress_checker']
    smoother = parameters['velocity_smoother']['ros__parameters']

    assert controller['desired_linear_vel'] <= 0.10
    assert controller['rotate_to_heading_angular_vel'] <= 0.20
    # Die Komfortgrenze gehoert in den nachgeschalteten Smoother. Eine zweite
    # gleich niedrige Reglergrenze koppelt die Encoder-Rueckmeldung erneut ein
    # und machte die reale Drehung um eine Groessenordnung zu langsam.
    assert controller['max_angular_accel'] == 2.0
    assert progress['plugin'] == 'nav2_controller::PoseProgressChecker'
    assert progress['required_movement_radius'] == 0.10
    assert progress['required_movement_angle'] == 0.05
    assert progress['movement_time_allowance'] == 30.0
    assert smoother['feedback'] == 'OPEN_LOOP'
    assert smoother['max_velocity'] == [0.12, 0.0, 0.25]
    assert smoother['max_accel'] == [0.12, 0.0, 0.30]
    assert smoother['max_accel'][2] < controller['max_angular_accel']
    assert smoother['velocity_timeout'] <= 0.5
    # Ein gemessener 0,95-s-Aussetzer von map->odom darf die Nav2-Action nicht
    # verwerfen. Die Kommandokette stoppt dank Smoother trotzdem spaetestens
    # nach 0,5 s ohne neue Reglerausgabe.
    assert controller_server['failure_tolerance'] >= 1.5
    assert smoother['velocity_timeout'] < controller_server['failure_tolerance']
    assert parameters['bt_navigator']['ros__parameters'][
        'default_server_timeout'] >= 2000


def test_real_planner_uses_measured_astar_configuration():
    parameters = yaml.safe_load(
        (PACKAGE_ROOT / 'config' / 'nav2_params_real.yaml').read_text()
    )
    planner = parameters['planner_server']['ros__parameters']['GridBased']

    assert planner['plugin'] == 'nav2_navfn_planner/NavfnPlanner'
    assert planner['use_astar'] is True
    assert planner['allow_unknown'] is False


def test_real_footprint_fits_doors_without_hiding_platform_length():
    parameters = yaml.safe_load(
        (PACKAGE_ROOT / 'config' / 'nav2_params_real.yaml').read_text()
    )
    local = parameters['local_costmap']['local_costmap']['ros__parameters']
    global_costmap = parameters['global_costmap']['global_costmap'][
        'ros__parameters']
    footprint = yaml.safe_load(local['footprint'])

    assert footprint == [
        [0.31, 0.23], [0.31, -0.23],
        [-0.11, -0.23], [-0.11, 0.23],
    ]
    assert local['footprint_padding'] == 0.02
    assert 'robot_radius' not in local
    # NavFn prueft keine SE2-Polygone. Sein globales Breitenmodell bleibt
    # deshalb separat und konservativer als die halbe Plattformbreite.
    assert global_costmap['robot_radius'] == 0.28
    assert global_costmap['footprint_padding'] == 0.0

    measured_door_width = 0.68
    padded_platform_width = 0.46 + 2 * local['footprint_padding']
    assert measured_door_width - padded_platform_width == pytest.approx(0.18)
    assert measured_door_width - 2 * global_costmap['robot_radius'] == (
        pytest.approx(0.12))


def test_description_uses_measured_asymmetric_chassis_geometry():
    description = (
        PACKAGE_ROOT.parent / 'robot_description' / 'urdf' /
        'mobile_manipulator_dummy.urdf.xacro'
    ).read_text()

    assert 'name="base_length" value="0.38"' in description
    assert 'name="base_width"  value="0.46"' in description
    assert 'name="base_center_x" value="0.08"' in description
    assert 'origin xyz="${base_center_x} 0 0"' in description
    assert 'name="vl53_x"          value="0.290"' in description


def test_mapping_collision_monitor_uses_local_nav2_footprint():
    config = yaml.safe_load(
        (
            PACKAGE_ROOT.parent / 'vl53_near_field' / 'config' /
            'collision_monitor_mapping_params.yaml'
        ).read_text()
    )
    approach = config['collision_monitor']['ros__parameters'][
        'FootprintApproach']

    assert approach['type'] == 'polygon'
    assert approach['footprint_topic'] == (
        '/local_costmap/published_footprint')
    assert 'radius' not in approach
    assert approach['action_type'] == 'approach'


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


def test_explore_gate_requires_explicit_opt_in_phase_and_fresh_sensors():
    running = {
        'state': 'running',
        'phase': 'Explore',
        'active_command': {'type': 'explore'},
    }
    assert not explore_motion_authorized(running, False)
    assert explore_motion_authorized(running, True)
    assert not explore_motion_authorized({**running, 'phase': 'gestartet'}, True)
    assert not explore_motion_authorized(
        {**running, 'active_command': {'type': 'go_to_room'}}, True)

    assert explore_health_authorized(
        True, 9.0, 9.8, 9.8, 9.8, 9.8, 10.0, 5.0, 0.8, 0.8)
    assert not explore_health_authorized(
        False, 9.0, 9.8, 9.8, 9.8, 9.8, 10.0, 5.0, 0.8, 0.8)
    assert not explore_health_authorized(
        True, 9.0, 9.0, 9.8, 9.8, 9.8, 10.0, 5.0, 0.8, 0.8)
    assert explore_health_authorized(
        True, 1.0, 9.8, 9.8, 9.8, 9.8, 10.0, 5.0, 0.8, 0.8,
        allow_stale_map_for_scan=True)
    assert not explore_health_authorized(
        True, 9.0, 9.8, None, 9.8, 9.8, 10.0, 5.0, 0.8, 0.8)


def test_explore_scan_input_is_rotation_only_and_bounded():
    assert explore_scan_values_valid(
        (0.0, 0.0, 0.0, 0.0, 0.0, 0.12), 0.15)
    assert explore_scan_values_valid(
        (0.0, 0.0, 0.0, 0.0, 0.0, 0.0), 0.15)
    assert not explore_scan_values_valid(
        (0.01, 0.0, 0.0, 0.0, 0.0, 0.12), 0.15)
    assert not explore_scan_values_valid(
        (0.0, 0.0, 0.0, 0.0, 0.0, 0.151), 0.15)
    assert not explore_scan_values_valid(
        (0.0, 0.0, 0.0, 0.0, 0.0, float('nan')), 0.15)

    source = (PACKAGE_ROOT / 'robot_navigation' /
              'cmd_vel_mission_gate.py').read_text(encoding='utf-8')
    assert "'/cmd_vel_explore_scan_raw'" in source
    assert 'self._on_explore_scan_command' in source


def test_explore_direct_input_is_forward_only_and_tightly_bounded():
    assert explore_direct_values_valid(
        (0.08, 0.0, 0.0, 0.0, 0.0, 0.10), 0.08, 0.10)
    assert explore_direct_values_valid(
        (0.0, 0.0, 0.0, 0.0, 0.0, 0.0), 0.08, 0.10)
    assert not explore_direct_values_valid(
        (-0.01, 0.0, 0.0, 0.0, 0.0, 0.0), 0.08, 0.10)
    assert not explore_direct_values_valid(
        (0.081, 0.0, 0.0, 0.0, 0.0, 0.0), 0.08, 0.10)
    assert not explore_direct_values_valid(
        (0.08, 0.0, 0.0, 0.0, 0.0, 0.101), 0.08, 0.10)
    assert not explore_direct_values_valid(
        (float('nan'), 0.0, 0.0, 0.0, 0.0, 0.0), 0.08, 0.10)

    source = (PACKAGE_ROOT / 'robot_navigation' /
              'cmd_vel_mission_gate.py').read_text(encoding='utf-8')
    assert "'/cmd_vel_explore_direct_raw'" in source
    assert 'self._on_explore_direct_command' in source


def test_required_localization_gate_is_fail_closed_and_monotonic():
    assert localization_motion_authorized(True, True, 10.0, 10.9, 1.0)
    assert not localization_motion_authorized(True, True, 10.0, 11.01, 1.0)
    assert not localization_motion_authorized(True, False, 10.0, 10.1, 1.0)
    assert not localization_motion_authorized(True, True, None, 10.1, 1.0)
    assert not localization_motion_authorized(True, True, 11.0, 10.1, 1.0)
    assert localization_motion_authorized(False, False, None, 99.0, 1.0)


def test_localization_search_is_bounded_fresh_and_one_shot():
    valid = (0.0, 0.0, 0.0, 0.0, 0.0, 0.15)
    assert localization_search_values_valid(valid, 0.04, 0.15)
    assert localization_search_values_valid(
        (0.04, 0.0, 0.0, 0.0, 0.0, 0.0), 0.04, 0.15)
    assert not localization_search_values_valid(
        (-0.01, 0.0, 0.0, 0.0, 0.0, 0.15), 0.04, 0.15)
    assert not localization_search_values_valid(
        (0.041, 0.0, 0.0, 0.0, 0.0, 0.0), 0.04, 0.15)
    assert not localization_search_values_valid(
        (0.0, 0.0, 0.0, 0.0, 0.0, 0.151), 0.04, 0.15)
    assert localization_search_authorized(
        True, False, False, 10.0, 10.1, 10.1, 10.15, 0.2, 10.2,
        1.0, 0.25, 0.5, 110.0, 0.35)
    assert not localization_search_authorized(
        True, True, True, 10.0, 10.1, 10.1, 10.15, 0.2, 10.2,
        1.0, 0.25, 0.5, 110.0, 0.35)
    assert not localization_search_authorized(
        True, False, True, 10.0, 10.1, 10.1, 10.15, 0.2, 10.2,
        1.0, 0.25, 0.5, 110.0, 0.35)
    assert not localization_search_authorized(
        True, False, False, 10.0, 10.1, 10.1, 10.15, 0.36, 10.2,
        1.0, 0.25, 0.5, 110.0, 0.35)


def test_global_localization_launch_has_one_explicit_map_to_odom_owner():
    source = (
        PACKAGE_ROOT / 'launch' / 'nav_localized.launch.py'
    ).read_text(encoding='utf-8')
    assert "DeclareLaunchArgument(\n            'map'," in source
    assert "'static_map_odom': 'false'" in source
    assert "'require_localization': 'true'" in source
    assert "package='nav2_amcl'" in source
    assert "executable='localization_guard'" in source
    assert "executable='global_scan_localizer'" in source
    assert "'require_global_scan_match'" in source
    assert "executable='static_transform_publisher'" not in source
    assert "'/scan_normiert'" in source
    assert "'allow_localization_search': 'true'" in source

    guard_source = (
        PACKAGE_ROOT / 'robot_navigation' / 'localization_guard.py'
    ).read_text(encoding='utf-8')
    assert 'global_initialization_fingerprint' in guard_source
    assert 'global_scan_match' in guard_source
    assert "self._global_state = 'scan_matching'" in guard_source
    assert '/reinitialize_global_localization' not in guard_source
    assert 'call_async(Empty.Request())' not in guard_source
    assert 'TimerAction(period=4.0' in source
    assert 'TimerAction(period=7.0' in source

    matcher_source = (
        PACKAGE_ROOT / 'robot_navigation' / 'global_scan_localizer.py'
    ).read_text(encoding='utf-8')
    assert "self.declare_parameter('required_consistent_matches', 2)" in matcher_source

    start_helper = (
        PACKAGE_ROOT.parents[1] / 'tools' / 'kartierung' /
        'start_lidar_lokalisierung.sh'
    ).read_text(encoding='utf-8')
    assert 'karte_fuer_nav2_pruefen.py' in start_helper

    search_helper = (
        PACKAGE_ROOT.parents[1] / 'tools' / 'kartierung' /
        'amcl_lokalisierungsdrehung.py'
    ).read_text(encoding='utf-8')
    assert "'/request_nomotion_update'" in search_helper
    assert 'node.publish_for(stop, 2.0)' in search_helper
    assert 'request_nomotion_updates(node, args.nomotion_updates)' in search_helper


def test_amcl_never_assumes_or_restores_an_initial_pose():
    parameters = yaml.safe_load(
        (PACKAGE_ROOT / 'config' / 'nav2_params_real.yaml').read_text()
    )
    amcl = parameters['amcl']['ros__parameters']
    assert amcl['base_frame_id'] == 'base_link'
    assert amcl['global_frame_id'] == 'map'
    assert amcl['odom_frame_id'] == 'odom'
    assert amcl['scan_topic'] == '/scan_normiert'
    assert amcl['set_initial_pose'] is False
    assert amcl['always_reset_initial_pose'] is True
    assert amcl['tf_broadcast'] is True


def test_mission_gate_tolerates_shutdown_context_race():
    source = (PACKAGE_ROOT / 'robot_navigation' /
              'cmd_vel_mission_gate.py').read_text(encoding='utf-8')
    assert 'except RCLError:' in source
