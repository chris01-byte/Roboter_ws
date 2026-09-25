"""Resolve launch entities without executing nodes or opening devices."""
import importlib.util
from pathlib import Path

import pytest
import yaml
from launch import LaunchContext
from launch.actions import IncludeLaunchDescription, OpaqueFunction
from launch.utilities import perform_substitutions
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
    nodes = [e for e in module.generate_launch_description().entities
             if isinstance(e, Node) and (e.condition is None or e.condition.evaluate(ctx))]
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
    assert all(not isinstance(e, (Node, IncludeLaunchDescription)) for e in entities[:gate_index])
    with pytest.raises(RuntimeError, match='Stillstand'):
        module._require_stationary_confirmation(context(operator_stationary_confirmed='false'))


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
