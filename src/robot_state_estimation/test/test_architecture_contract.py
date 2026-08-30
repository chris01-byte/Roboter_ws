from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


def test_ekf_has_single_local_tf_owner_and_no_command_prediction():
    data = yaml.safe_load(
        (ROOT / 'config' / 'ekf_encoder_imu.yaml').read_text())
    params = data['ekf_filter_node']['ros__parameters']

    assert params['world_frame'] == 'odom'
    assert params['odom_frame'] == 'odom'
    assert params['base_link_frame'] == 'base_link'
    assert params['publish_tf'] is True
    assert params['two_d_mode'] is True
    assert params['use_control'] is False
    assert params['odom0'] == '/fusion/wheel_odom'
    assert params['imu0'] == '/fusion/imu'

    wheel = params['odom0_config']
    imu = params['imu0_config']
    assert len(wheel) == 15
    assert len(imu) == 15
    assert [index for index, enabled in enumerate(wheel) if enabled] == [6, 7, 11]
    assert [index for index, enabled in enumerate(imu) if enabled] == [11]


def test_launch_and_nodes_have_no_actuator_topic():
    sources = [
        ROOT / 'launch' / 'fusion.launch.py',
        ROOT / 'robot_state_estimation' / 'sensor_adapter_node.py',
        ROOT / 'robot_state_estimation' / 'scan_quality_gate_node.py',
        ROOT / 'robot_state_estimation' / 'lidar_odometry_node.py',
    ]
    text = '\n'.join(path.read_text() for path in sources)

    assert 'base_hardware' not in text
    assert 'cmd_vel' not in text
    assert 'allow_rs485' not in text
    assert "executable='ekf_node'" in text
    assert "default_value='false'" in text


def test_amadeus_profile_is_fail_closed_for_scan_quality():
    data = yaml.safe_load((ROOT / 'config' / 'amadeus.yaml').read_text())
    adapter = data['sensor_adapter']['ros__parameters']
    gate = data['scan_quality_gate']['ros__parameters']

    assert adapter['wheel_odom_input'] == '/wheel/odom_raw'
    assert adapter['imu_input'] == '/oak/imu/data'
    assert adapter['require_imu'] is True
    assert adapter['require_reference_odom'] is False
    assert gate['scan_input'] == '/scan_normiert'
    assert gate['scan_output'] == '/scan_qualitaet'
    assert gate['fail_closed'] is True


def test_amadeus_gyro_bias_profile_handles_warmup_drift_fail_closed():
    data = yaml.safe_load((ROOT / 'config' / 'amadeus.yaml').read_text())
    adapter = data['sensor_adapter']['ros__parameters']
    source = (
        ROOT / 'robot_state_estimation' / 'sensor_adapter_node.py').read_text()

    assert adapter['gyro_bias_initial_settle_s'] >= 10.0
    assert adapter['gyro_bias_calibration_s'] >= 5.0
    assert adapter['gyro_bias_minimum_samples'] >= 1000
    assert adapter['gyro_bias_stationary_adaptation_time_constant_s'] == 5.0
    assert adapter['gyro_bias_maximum_stationary_residual_radps'] <= 0.001
    assert adapter['gyro_bias_stationary_angular_threshold_radps'] <= 0.005
    assert 'and bias_ready' in source
    assert 'not bias.calibrated or not bias.stable' in source


def test_package_declares_standard_filter_dependency():
    package_xml = (ROOT / 'package.xml').read_text()

    assert '<exec_depend>robot_localization</exec_depend>' in package_xml
    assert '<depend>diagnostic_msgs</depend>' in package_xml


def test_reference_profile_adds_independent_twist_without_map_pose():
    data = yaml.safe_load(
        (ROOT / 'config' / 'ekf_encoder_imu_reference.yaml').read_text())
    params = data['ekf_filter_node']['ros__parameters']

    assert params['odom1'] == '/fusion/reference_odom'
    assert [
        index for index, enabled in enumerate(params['odom1_config'])
        if enabled] == [6, 11]
    assert params['world_frame'] == 'odom'
    assert params['use_control'] is False


def test_process_noise_matrices_are_complete_homogeneous_ros_arrays():
    for filename in (
            'ekf_encoder_imu.yaml',
            'ekf_encoder_imu_reference.yaml'):
        data = yaml.safe_load((ROOT / 'config' / filename).read_text())
        matrix = data['ekf_filter_node']['ros__parameters'][
            'process_noise_covariance']

        # ROS 2 parameters require a homogeneous array.  A single integer 0
        # among floats makes robot_localization reject the complete YAML file.
        assert len(matrix) == 15 * 15
        assert all(type(value) is float for value in matrix)
        assert all(matrix[index * 15 + index] > 0.0 for index in range(15))


def test_amadeus_validation_launch_is_hard_coded_motorless():
    launch_file = (
        ROOT.parent / 'robot_bringup' / 'launch'
        / 'state_estimation_validation.launch.py')
    text = launch_file.read_text()

    assert "'dry_run': True" in text
    assert "'allow_rs485': False" in text
    assert "'publish_tf': False" in text
    assert "'odom_topic': '/wheel/odom_raw'" in text
    assert "'active_drive'" not in text
