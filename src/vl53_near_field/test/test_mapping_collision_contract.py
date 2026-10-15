from pathlib import Path

import yaml


PACKAGE_ROOT = Path(__file__).resolve().parents[1]


def _parameters(filename):
    payload = yaml.safe_load(
        (PACKAGE_ROOT / 'config' / filename).read_text(encoding='utf-8'))
    return payload['collision_monitor']['ros__parameters']


def test_mapping_profile_uses_motion_aware_conservative_footprint():
    params = _parameters('collision_monitor_mapping_params.yaml')

    assert params['polygons'] == ['FootprintApproach', 'SlowZone']
    approach = params['FootprintApproach']
    assert approach['type'] == 'polygon'
    assert approach['footprint_topic'] == (
        '/local_costmap/published_footprint')
    assert 'radius' not in approach
    assert approach['action_type'] == 'approach'
    assert approach['time_before_collision'] >= 2.0
    assert 0.0 < approach['simulation_time_step'] <= 0.1
    assert approach['max_points'] <= 1

    slow = params['SlowZone']
    assert slow['action_type'] == 'slowdown'
    assert slow['slowdown_ratio'] == 0.3
    assert params['cmd_vel_in_topic'] == 'cmd_vel_smoothed'
    assert params['cmd_vel_out_topic'] == 'cmd_vel'
    assert params['base_shift_correction'] is False
    assert params['observation_sources'] == ['vl53_left', 'vl53_right']


def test_default_collision_profile_remains_unchanged_for_teleop():
    params = _parameters('collision_monitor_params.yaml')

    assert params['polygons'] == ['StopZone', 'SlowZone']
    assert params['StopZone']['action_type'] == 'stop'


def test_vl53_launch_defaults_to_normal_profile_but_accepts_override():
    source = (
        PACKAGE_ROOT / 'launch' / 'vl53_near_field.launch.py'
    ).read_text(encoding='utf-8')

    assert "'collision_params_file'" in source
    assert "'collision_monitor_params.yaml'" in source
    assert 'parameters=[collision_params, collision_overlay]' in source
    # Without an explicit overlay the same file is loaded again (no change).
    assert "'collision_params_overlay', default_value=collision_params," in source


def test_self_healing_overlay_only_lowers_vl53_height_below_any_valid_point():
    import math

    overlay = yaml.safe_load((PACKAGE_ROOT / 'config' /
                              'collision_monitor_self_healing_overlay.yaml').read_text())
    assert overlay == {'collision_monitor': {'ros__parameters': {
        'vl53_left': {'min_height': -0.02}, 'vl53_right': {'min_height': -0.02}}}}
    mapping = _parameters('collision_monitor_mapping_params.yaml')
    assert mapping['vl53_left']['min_height'] == 0.05     # other modes unchanged
    # Geometry: lowest valid point is the bottom row at the range limit; it must
    # stay above the new limit, and the floor must stay out of range.
    sensor = yaml.safe_load((PACKAGE_ROOT / 'config' / 'vl53_params.yaml').read_text())
    params = next(iter(sensor.values()))['ros__parameters']
    fov, z_max = params['fov_deg'], params['z_max']
    bottom_row = math.radians(-fov/2 + 0.5*fov/8)
    sensor_z_base_link, base_link_above_floor = 0.215, 0.09
    lowest_point = sensor_z_base_link + z_max*math.sin(bottom_row)
    assert -0.02 < lowest_point                  # every valid return counts
    floor_distance = (sensor_z_base_link + base_link_above_floor)/math.sin(-bottom_row)
    assert floor_distance > z_max                # floor never becomes a point


def test_vl53_node_tolerates_a_context_already_stopped_by_sigint():
    source = (
        PACKAGE_ROOT / 'vl53_near_field' / 'vl53_near_field_node.py'
    ).read_text(encoding='utf-8')

    assert 'except (KeyboardInterrupt, ExternalShutdownException):' in source
    assert 'except RuntimeError:' in source
    assert 'if rclpy.ok():\n            raise' in source
    assert 'if rclpy.ok():\n            rclpy.shutdown()' in source
