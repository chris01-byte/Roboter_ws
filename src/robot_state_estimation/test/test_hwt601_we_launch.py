"""Resolve launch entities without executing nodes or opening devices."""
import importlib.util
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml
from launch import LaunchContext, LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, OpaqueFunction, TimerAction
from launch.utilities import normalize_to_list_of_substitutions, perform_substitutions
from launch_ros.actions import Node


ROOT = Path(__file__).resolve().parents[3]


def load_launch(relative):
    spec = importlib.util.spec_from_file_location('launch_under_test', ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.get_package_share_directory = lambda pkg: str(ROOT / 'src' / pkg)
    return module


def context(**values):
    ctx = LaunchContext()
    ctx.launch_configurations.update(values)
    return ctx


@pytest.mark.parametrize('active', ['false', 'true'])
def test_hwt_has_exactly_one_bus_and_local_tf_owner(active):
    module = load_launch('src/amadeus_lidar_bringup/launch/slam_lidar_hwt601.launch.py')
    ctx = context(active_drive=active, normalize_scan='true', crop='true',
                  operator_stationary_confirmed='true')
    def enabled_nodes(entities):
        for entity in entities:
            if entity.condition is not None and not entity.condition.evaluate(ctx):
                continue
            if isinstance(entity, Node):
                yield entity
            elif isinstance(entity, TimerAction):
                yield from enabled_nodes(entity.actions)
    nodes = list(enabled_nodes(module.generate_launch_description().entities))
    executables = [n.node_executable if isinstance(n.node_executable, str)
                   else perform_substitutions(ctx, n.node_executable) for n in nodes]
    assert executables.count('ekf_node') == 1
    assert executables.count('async_slam_toolbox_node') == 1
    assert executables.count('lidar_odometry') == 1
    assert executables.count('base_hardware') == (active == 'true')
    assert executables.count('encoder_shadow_reader') == (active == 'false')
    text = (ROOT / 'src/amadeus_lidar_bringup/launch/slam_lidar_hwt601.launch.py').read_text()
    assert "'publish_tf': False" in text
    assert "'odom_topic': '/fusion/hwt601/wheel_odom_raw'" in text
    assert "('odometry/filtered', '/odom')" in text


def test_no_default_or_inferred_stillness_opens_hwt_devices():
    module = load_launch('src/amadeus_lidar_bringup/launch/slam_lidar_hwt601.launch.py')
    entities = module.generate_launch_description().entities
    gate_index = next(i for i, e in enumerate(entities) if isinstance(e, OpaqueFunction))
    assert all(not isinstance(e, (Node, IncludeLaunchDescription, TimerAction))
               for e in entities[:gate_index])
    with pytest.raises(RuntimeError, match='Stillstand'):
        module._require_stationary_confirmation(context(operator_stationary_confirmed='false'))


@pytest.mark.parametrize('value', ['0', '99', '2001', 'x', '100.5'])
def test_hwt_ramp_comparison_rejects_invalid_values_before_devices(value):
    module = load_launch('src/amadeus_lidar_bringup/launch/slam_lidar_hwt601.launch.py')
    with pytest.raises(RuntimeError, match='Anfahrrampe'):
        module._require_stationary_confirmation(context(operator_stationary_confirmed='true', hwt601_accel_ms=value))


@pytest.mark.parametrize('value', ['100', '2000'])
def test_hwt_ramp_comparison_accepts_explicit_values_and_outer_binding(value):
    module = load_launch('src/amadeus_lidar_bringup/launch/slam_lidar_hwt601.launch.py')
    assert module._require_stationary_confirmation(context(operator_stationary_confirmed='true', hwt601_accel_ms=value)) == []
    for relative in ('src/robot_bringup/launch/app_mapping.launch.py', 'src/robot_navigation/launch/nav_mapping.launch.py'):
        text = (ROOT / relative).read_text()
        assert "DeclareLaunchArgument('hwt601_accel_ms', default_value='2000')" in text
        assert "'hwt601_accel_ms': LaunchConfiguration('hwt601_accel_ms')" in text


def test_historical_mapping_profile_not_shadow_ekf_and_no_commands_or_encoder_yaw():
    config = yaml.safe_load((ROOT / 'src/robot_state_estimation/config/ekf_hwt601_mapping.yaml').read_text())
    p = config['hwt601_mapping_ekf']['ros__parameters']
    assert [i for i, v in enumerate(p['odom0_config']) if v] == [6]
    assert [i for i, v in enumerate(p['imu0_config']) if v] == [11]
    assert p['odom0'] == '/fusion/hwt601/wheel_odom_raw'
    assert p['imu0'] == '/shadow/hwt601/imu/yaw_rate'
    assert p['use_control'] is False and p['publish_tf'] is True
    assert p['world_frame'] == 'odom'
    assert 'odom1' not in p
    assert len(p['process_noise_covariance']) == 225


def test_outer_chain_passes_explicit_mode_and_both_consumers_require_inputs():
    outer = (ROOT / 'src/robot_bringup/launch/app_mapping.launch.py').read_text()
    nav = (ROOT / 'src/robot_navigation/launch/nav_mapping.launch.py').read_text()
    explorer = (ROOT / 'src/explore/launch/explore.launch.py').read_text()
    for source in (outer, nav):
        assert "'use_hwt601_odometry', default_value='false'" in source
        assert "'operator_stationary_confirmed', default_value='false'" in source
    assert 'condition=UnlessCondition(use_hwt601_odometry)' in nav
    assert 'condition=IfCondition(use_hwt601_odometry)' in nav
    assert nav.count("'require_hwt601_fusion'") == 2
    assert "'require_hwt601_fusion': ParameterValue(" in explorer


def resolved(value, ctx):
    return perform_substitutions(ctx, normalize_to_list_of_substitutions(value))


def include_location(entity, ctx):
    source = entity.launch_description_source
    # Humble exposes substitution reprs in location until this public method
    # resolves the path. Suppress recursive file loading, never execute nodes.
    with patch.object(source, '_get_launch_description', return_value=LaunchDescription()):
        source.get_launch_description(ctx)
    return source.location


def declared_launch(relative, **overrides):
    entities = load_launch(relative).generate_launch_description().entities
    ctx = context(**overrides)
    for entity in entities:
        if isinstance(entity, DeclareLaunchArgument):
            entity.execute(ctx)  # Configuration only; no node/process execution.
    return entities, ctx


@pytest.mark.parametrize('active, executable', [('true', 'base_hardware'),
                                             ('false', 'encoder_shadow_reader')])
def test_encoder_owner_establishes_baseline_after_stack_startup(active, executable):
    from launch.utilities import type_utils
    entities, ctx = declared_launch(
        'src/amadeus_lidar_bringup/launch/slam_lidar_hwt601.launch.py',
        active_drive=active, operator_stationary_confirmed='true')
    eligible = [e for e in entities if e.condition is None or e.condition.evaluate(ctx)]
    assert not any(isinstance(e, Node) and resolved(e.node_executable, ctx) == executable
                   for e in eligible)
    delayed = [(e, n) for e in eligible if isinstance(e, TimerAction)
               for n in e.actions if isinstance(n, Node)
               and resolved(n.node_executable, ctx) == executable]
    assert len(delayed) == 1
    assert type_utils.perform_typed_substitution(ctx, delayed[0][0].period, float) == 15.


def enabled_launch_owners(entities, ctx):
    owners = []
    for entity in entities:
        if entity.condition is not None and not entity.condition.evaluate(ctx):
            continue
        if isinstance(entity, IncludeLaunchDescription):
            owners.append(('include', include_location(entity, ctx)))
        elif isinstance(entity, Node):
            owners.append(('node', resolved(entity.node_executable, ctx)))
        elif isinstance(entity, TimerAction):
            owners.extend(enabled_launch_owners(entity.actions, ctx))
    return owners


def test_mapping_default_still_starts_one_explorer():
    for relative in ('src/robot_bringup/launch/app_mapping.launch.py',
                     'src/robot_navigation/launch/nav_mapping.launch.py'):
        entities, ctx = declared_launch(relative)
        assert ctx.launch_configurations['start_explorer'] == 'true'
        if relative.startswith('src/robot_navigation/'):
            owners = enabled_launch_owners(entities, ctx)
            assert sum(path.endswith('/explore.launch.py') for _, path in owners) == 1


@pytest.mark.parametrize('active', ['false', 'true'])
@pytest.mark.parametrize('auto', ['false', 'true'])
def test_app_staging_removes_only_explorer_and_preserves_drive_opt_ins(active, auto):
    runs = {}
    for start_explorer in ('false', 'true'):
        outer, ctx = declared_launch('src/robot_bringup/launch/app_mapping.launch.py',
            start_explorer=start_explorer, active_drive=active,
            enable_auto_explore=auto, use_hwt601_odometry='true')
        includes = [entity for entity in outer if isinstance(entity, IncludeLaunchDescription)]
        navigation = next(entity for entity in includes
            if include_location(entity, ctx).endswith('/nav_mapping.launch.py'))
        arguments = {name: resolved(value, ctx) for name, value in navigation.launch_arguments}
        assert arguments['start_explorer'] == start_explorer
        assert arguments['active_drive'] == active
        assert arguments['enable_auto_explore'] == auto
        assert arguments['use_hwt601_odometry'] == 'true'
        inner, inner_ctx = declared_launch('src/robot_navigation/launch/nav_mapping.launch.py', **arguments)
        runs[start_explorer] = (enabled_launch_owners(outer, ctx),
                                enabled_launch_owners(inner, inner_ctx))
    assert runs['false'][0] == runs['true'][0]
    explorer = [owner for owner in runs['true'][1] if owner[1].endswith('/explore.launch.py')]
    assert len(explorer) == 1
    assert runs['false'][1] == [owner for owner in runs['true'][1] if owner not in explorer]
    assert sum(path.endswith('/slam_lidar_hwt601.launch.py') for _, path in runs['false'][1]) == 1
    assert sum(path.endswith('/bt_orchestrator.launch.py') for _, path in runs['false'][1]) == 1
    assert sum(path.endswith('/mission_manager.launch.py') for _, path in runs['false'][1]) == 1
