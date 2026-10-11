"""Evaluate actual launch parameter choices; no executables or devices started."""
from pathlib import Path
import runpy

import pytest
import yaml
from launch import LaunchContext
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.utilities import normalize_to_list_of_substitutions, perform_substitutions
from launch_ros.actions import Node
from launch_ros.utilities import evaluate_parameters


REPO = Path(__file__).resolve().parents[3]


def value(context, substitution):
    return perform_substitutions(context, normalize_to_list_of_substitutions(substitution))


def description(monkeypatch, package, filename, context):
    import ament_index_python.packages
    monkeypatch.setattr(ament_index_python.packages, 'get_package_share_directory',
                        lambda name: str(REPO/'src'/name))
    result = runpy.run_path(str(REPO/'src'/package/'launch'/filename))['generate_launch_description']()
    for action in result.entities:
        if isinstance(action, DeclareLaunchArgument):
            action.execute(context)
    return result


@pytest.mark.parametrize('policy', ['observed_only', 'sensor_guarded'])
def test_one_mapping_policy_matches_explorer_planner_and_final_brake(monkeypatch, policy):
    context = LaunchContext()
    context.launch_configurations['unknown_space_policy'] = policy
    mapping = description(monkeypatch, 'robot_navigation', 'nav_mapping.launch.py', context)
    nodes = [child for action in mapping.entities for child in getattr(action, 'actions', ())
             if isinstance(child, Node)]
    planner = next(node for node in nodes if 'planner_server' in str(node._Node__node_name))
    planner_files = evaluate_parameters(context, planner._Node__parameters)
    native = yaml.safe_load(planner_files[-1].read_text())
    assert native['planner_server']['ros__parameters']['GridBased']['allow_unknown'] is (policy == 'sensor_guarded')
    controller = next(node for node in nodes if 'controller_server' in str(node._Node__node_name))
    assert evaluate_parameters(context, controller._Node__parameters) == planner_files

    includes = [dict(action.launch_arguments) for action in mapping.entities
                if isinstance(action, IncludeLaunchDescription)]
    collision = next(args for args in includes if 'collision_params_file' in args)
    collision_file = Path(value(context, collision['collision_params_file']))
    brake = yaml.safe_load(collision_file.read_text())['collision_monitor']['ros__parameters']
    assert ('lidar' in brake['observation_sources']) is (policy == 'sensor_guarded')
    assert {'vl53_left', 'vl53_right'} <= set(brake['observation_sources'])
    assert brake['cmd_vel_in_topic'] == 'cmd_vel_smoothed' and brake['cmd_vel_out_topic'] == 'cmd_vel'
    assert brake['FootprintApproach']['time_before_collision'] == 2.
    if policy == 'sensor_guarded':
        assert brake['lidar']['topic'] == '/scan_normiert'
        assert brake['FootprintApproach']['max_points'] == 1
        for owner in ('local_costmap', 'global_costmap'):
            layer = native[owner][owner]['ros__parameters']
            assert 'obstacle_layer' in layer['plugins'] and 'lidar_obstacle_layer' in layer['plugins']
            assert layer['lidar_obstacle_layer']['lidar']['topic'] == '/scan_normiert'
            assert 'observation_sources' not in layer.get('obstacle_layer', {})

    explorer_args = next(args for args in includes if 'unknown_space_policy' in args)
    assert value(context, explorer_args['unknown_space_policy']) == policy
    expected_mode='lab_slots' if policy=='sensor_guarded' else 'continuous'
    assert value(context, explorer_args['execution_mode']) == expected_mode
    exploration = description(monkeypatch, 'explore', 'explore.launch.py', context)
    node = next(action for action in exploration.entities if isinstance(action, Node))
    files = evaluate_parameters(context, node._Node__parameters)
    motion = yaml.safe_load(files[2].read_text())['explore_node']['ros__parameters']
    assert motion['metric_unknown_space_policy'] == policy
    slots = yaml.safe_load(files[3].read_text())['explore_node']['ros__parameters']
    assert slots['metric_execution_mode']==expected_mode
    if policy == 'sensor_guarded':
        assert motion['metric_start_strategy'] == 'sensor_scan_first'
        assert not motion['metric_self_body_enabled'] and not motion['metric_start_egress_enabled']
        assert 'metric_session_id' not in motion and 'metric_scope_map_fingerprint' not in motion


def test_app_forwards_motion_policy_without_enabling_drive(monkeypatch):
    context = LaunchContext()
    app = description(monkeypatch, 'robot_bringup', 'app_mapping.launch.py', context)
    args = next(dict(action.launch_arguments) for action in app.entities
                if isinstance(action, IncludeLaunchDescription)
                and 'unknown_space_policy' in dict(action.launch_arguments))
    assert value(context, args['unknown_space_policy']) == 'sensor_guarded'
    assert value(context, args['execution_mode']) == 'lab_slots'
    assert value(context, args['active_drive']) == 'false'
    assert value(context, args['enable_auto_explore']) == 'false'


def test_explicit_continuous_fallback_is_forwarded_and_keeps_sensor_brakes(monkeypatch):
    context=LaunchContext()
    context.launch_configurations.update(unknown_space_policy='sensor_guarded',execution_mode='continuous')
    app=description(monkeypatch,'robot_bringup','app_mapping.launch.py',context)
    args=next(dict(action.launch_arguments) for action in app.entities
              if isinstance(action,IncludeLaunchDescription)
              and 'execution_mode' in dict(action.launch_arguments))
    assert value(context,args['execution_mode'])=='continuous'
    exploration=description(monkeypatch,'explore','explore.launch.py',context)
    node=next(action for action in exploration.entities if isinstance(action,Node))
    files=evaluate_parameters(context,node._Node__parameters)
    assert yaml.safe_load(files[2].read_text())['explore_node']['ros__parameters']['metric_unknown_space_policy']=='sensor_guarded'
    assert yaml.safe_load(files[3].read_text())['explore_node']['ros__parameters']['metric_execution_mode']=='continuous'
