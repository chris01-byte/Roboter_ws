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
    assert approach['type'] == 'circle'
    assert approach['action_type'] == 'approach'
    assert approach['radius'] == 0.40
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
    assert 'parameters=[collision_params]' in source
