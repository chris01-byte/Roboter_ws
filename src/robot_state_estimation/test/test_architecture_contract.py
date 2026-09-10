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
        ROOT / 'robot_state_estimation' / 'hwt601_imu_node.py',
        ROOT / 'robot_state_estimation' / 'hwt601_transport.py',
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
    assert '<exec_depend>python3-serial</exec_depend>' in package_xml


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
            'ekf_encoder_imu_reference.yaml',
            'ekf_hwt601_encoder_shadow.yaml',
            'ekf_hwt601_mapping.yaml'):
        data = yaml.safe_load((ROOT / 'config' / filename).read_text())
        assert len(data) == 1
        node = next(iter(data.values()))
        matrix = node['ros__parameters']['process_noise_covariance']

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


def test_hwt601_profiles_are_separate_read_only_and_not_fused_by_default():
    driver = yaml.safe_load(
        (ROOT / 'config' / 'hwt601_driver.yaml').read_text())[
            'hwt601_imu']['ros__parameters']
    adapter = yaml.safe_load(
        (ROOT / 'config' / 'amadeus_hwt601.yaml').read_text())[
            'sensor_adapter']['ros__parameters']
    protocol = (
        ROOT / 'robot_state_estimation' / 'hwt601_protocol.py').read_text()
    node = (ROOT / 'robot_state_estimation' / 'hwt601_imu_node.py').read_text()
    validation = (
        ROOT.parent / 'robot_bringup' / 'launch'
        / 'state_estimation_hwt601_validation.launch.py').read_text()

    assert driver['port'] == '/dev/ttyUSB_HWT601'
    assert driver['port'] != '/dev/ttyUSB_BASE'
    assert driver['device_address'] == 80
    assert driver['poll_rate_hz'] <= 200.0
    assert driver['frame_id'] == 'hwt601_link'
    assert driver['angular_velocity_full_scale_dps'] == 400.0
    assert driver['angular_velocity_variance'] > 0.0
    assert driver['linear_acceleration_variance'] > 0.0
    assert adapter['imu_input'] == '/hwt601/imu/data_raw'
    assert adapter['expected_imu_frame'] == 'hwt601_link'
    assert adapter['use_imu_orientation'] is False
    assert 'READ_HOLDING_REGISTERS = 0x03' in protocol
    assert 'WRITE_SINGLE_REGISTER' not in protocol
    assert 'message.orientation_covariance[0] = -1.0' in node
    assert 'os.path.realpath(self.port) == os.path.realpath(motor_port)' in node
    assert "'start_fusion_adapter', default_value='false'" in validation
    assert "'start_ekf', default_value='false'" in validation
    assert "'start_oak', default_value='false'" in validation
    assert "'dry_run': True" in validation
    assert "'allow_rs485': False" in validation


def test_hwt601_shadow_is_isolated_yaw_only_and_has_no_control_path():
    launch = (ROOT / 'launch' / 'hwt601_shadow.launch.py').read_text()
    source = (
        ROOT / 'robot_state_estimation' / 'hwt601_shadow_node.py').read_text()
    core = (
        ROOT / 'robot_state_estimation' / 'hwt601_shadow_core.py').read_text()
    config = yaml.safe_load(
        (ROOT / 'config' / 'hwt601_shadow.yaml').read_text())
    driver = config['hwt601_shadow_reader']['ros__parameters']
    shadow = config['hwt601_shadow']['ros__parameters']

    forbidden_launch_text = (
        'base_hardware', 'depthai', 'scan_quality_gate', 'lidar_odometry',
        'slam', 'nav2', 'cmd_vel', "'/odom'", "'/map'", "'/tf'",
        '/fusion/imu', '/fusion/wheel_odom',
    )
    assert all(token not in launch for token in forbidden_launch_text)
    assert 'operator_stationary_confirmed' in launch
    assert "default_value='true'" not in launch
    assert "default_value='false'" not in launch
    assert "executable='hwt601_imu'" in launch
    assert "executable='hwt601_shadow'" in launch

    topics = (
        driver['imu_topic'], driver['status_topic'],
        driver['diagnostics_topic'], shadow['imu_input'],
        shadow['imu_output'], shadow['status_topic'],
        shadow['diagnostics_topic'],
    )
    assert all(topic.startswith('/shadow/hwt601/') for topic in topics)
    assert driver['frame_id'] == 'hwt601_link'
    assert shadow['expected_input_frame'] == 'hwt601_link'
    assert shadow['output_frame'] == 'base_link'
    assert shadow['operator_stationary_confirmed'] is False
    assert shadow['angular_velocity_z_variance'] == 5.0e-7
    assert driver['angular_velocity_variance'] == 5.0e-7

    combined = launch + source + core
    assert 'TransformBroadcaster' not in combined
    assert 'create_subscription(\n            Twist' not in combined
    assert 'create_publisher(\n            Odometry' not in combined
    assert 'output.orientation_covariance[0] = -1.0' in source
    assert 'output.linear_acceleration_covariance[0] = -1.0' in source
    assert 'output.angular_velocity.z = result.yaw_rate_radps' in source
    assert 'message.angular_velocity_covariance[8] > 0.0' in source
    assert 'self.core.reject_invalid_message()' in source
    assert "'fusion_ready': False" in source
    assert "'publishes_tf': False" in source
    assert 'SHADOW_OUTPUT_QOS_DEPTH = 200' in source
    assert 'reliability=ReliabilityPolicy.RELIABLE' in source
    assert "'output_qos': 'reliable_keep_last_200'" in source


def test_hwt601_shadow_wrapper_requires_stillness_and_free_ports():
    wrapper = (
        ROOT.parents[1] / 'tools' / 'sensorfusion'
        / 'start_hwt601_shadow.sh').read_text()

    assert 'AMADEUS_HWT601_STILLSTAND' in wrapper
    assert '!= "JA"' in wrapper
    assert 'check_port_free /dev/ttyUSB_HWT601' in wrapper
    assert 'check_port_free /dev/ttyUSB_BASE' in wrapper
    assert 'status} -ne 1 || -n "${output}"' in wrapper
    assert 'NetworkInterface name="lo"' in wrapper
    assert 'RMW_IMPLEMENTATION=rmw_cyclonedds_cpp' in wrapper
    assert 'operator_stationary_confirmed:=true' in wrapper
    assert 'ros2 node list --no-daemon 2>&1' in wrapper
    assert 'ros2 node list --no-daemon 2>/dev/null || true' not in wrapper
    assert 'base_hardware' not in wrapper
    assert '/cmd_vel' not in wrapper


def test_hwt601_encoder_shadow_ekf_selects_only_measured_vx_and_yaw_rates():
    data = yaml.safe_load(
        (ROOT / 'config' / 'ekf_hwt601_encoder_shadow.yaml').read_text())
    assert set(data) == {'hwt601_encoder_shadow_ekf'}
    params = data['hwt601_encoder_shadow_ekf']['ros__parameters']

    assert params['two_d_mode'] is True
    assert params['publish_tf'] is False
    assert params['use_control'] is False
    assert params['world_frame'] == 'odom'
    assert params['base_link_frame'] == 'base_link'
    assert params['odom0'] == '/shadow/hwt601/wheel_odom_raw'
    assert params['imu0'] == '/shadow/hwt601/imu/yaw_rate'

    wheel = params['odom0_config']
    imu = params['imu0_config']
    assert len(wheel) == 15
    assert len(imu) == 15
    assert [index for index, enabled in enumerate(wheel) if enabled] == [6, 11]
    assert [index for index, enabled in enumerate(imu) if enabled] == [11]
    assert wheel[7] is False  # No fictional lateral-velocity measurement.

    sensor_keys = {
        key for key in params
        if key.startswith(('odom', 'imu', 'pose', 'twist', 'accel'))
        and key[-1:].isdigit()
    }
    assert sensor_keys == {'odom0', 'imu0'}


def test_hwt601_mapping_ekf_promotes_only_encoder_vx_and_hwt_yaw():
    data = yaml.safe_load(
        (ROOT / 'config' / 'ekf_hwt601_mapping.yaml').read_text())
    assert set(data) == {'hwt601_mapping_ekf'}
    params = data['hwt601_mapping_ekf']['ros__parameters']

    assert params['publish_tf'] is True
    assert params['world_frame'] == 'odom'
    assert params['use_control'] is False
    assert params['odom0'] == '/fusion/hwt601/wheel_odom_raw'
    assert params['imu0'] == '/shadow/hwt601/imu/yaw_rate'
    assert [
        index for index, enabled in enumerate(params['odom0_config'])
        if enabled] == [6]
    assert [
        index for index, enabled in enumerate(params['imu0_config'])
        if enabled] == [11]
    assert not any(
        key.startswith(('odom1', 'imu1', 'pose', 'twist', 'accel'))
        for key in params)


def test_hwt601_mapping_launch_has_exactly_one_local_and_global_tf_owner():
    launch = (
        ROOT.parent / 'amadeus_lidar_bringup' / 'launch' /
        'slam_lidar_hwt601.launch.py').read_text()
    package_xml = (
        ROOT.parent / 'amadeus_lidar_bringup' / 'package.xml').read_text()

    assert launch.count("executable='base_hardware'") == 1
    assert "'odom_topic': '/fusion/hwt601/wheel_odom_raw'" in launch
    assert "'publish_tf': False" in launch
    assert launch.count("executable='ekf_node'") == 1
    assert "name='hwt601_mapping_ekf'" in launch
    assert "('odometry/filtered', '/odom')" in launch
    assert launch.count("executable='async_slam_toolbox_node'") == 1
    assert "'hwt601_shadow.launch.py'" in launch
    assert "'operator_stationary_confirmed'" in launch
    assert "executable='lidar_odometry'" in launch
    assert "'odom_output': '/shadow/hwt601/lidar_odom'" in launch
    assert "'status_topic': '/shadow/hwt601/lidar_status_json'" in launch
    assert '<exec_depend>robot_state_estimation</exec_depend>' in package_xml
    assert '<exec_depend>robot_localization</exec_depend>' in package_xml


def test_hwt601_encoder_shadow_ekf_launch_is_one_isolated_filter():
    launch = (
        ROOT / 'launch' / 'hwt601_encoder_shadow_ekf.launch.py').read_text()

    assert launch.count('Node(') == 1
    assert "package='robot_localization'" in launch
    assert "executable='ekf_node'" in launch
    assert "name='hwt601_encoder_shadow_ekf'" in launch
    assert "'config', 'ekf_hwt601_encoder_shadow.yaml'" in launch
    assert "('odometry/filtered', '/shadow/hwt601/odom')" in launch
    assert "('/diagnostics', '/shadow/hwt601/diagnostics/ekf')" in launch
    assert "('/tf', '/shadow/hwt601/tf_unused')" in launch
    assert "('/tf_static', '/shadow/hwt601/tf_static_unused')" in launch
    assert "('set_pose', '/shadow/hwt601/set_pose')" in launch
    assert "'/shadow/hwt601/toggle_filter_processing'" in launch
    assert "DeclareLaunchArgument('config'" not in launch
    assert 'IncludeLaunchDescription' not in launch
    assert 'ExecuteProcess' not in launch
    assert all(topic not in launch for topic in (
        "('/odom',", "('/map',"))

    forbidden = (
        'base_hardware', 'hwt601_imu', 'hwt601_shadow', 'sensor_adapter',
        'depthai', 'oak', 'lidar', 'scan', 'slam', 'nav2', 'cmd_vel',
        'TransformBroadcaster',
    )
    assert all(token not in launch for token in forbidden)


def test_hwt601_encoder_sources_launch_contains_only_read_only_sources():
    launch = (
        ROOT / 'launch'
        / 'hwt601_encoder_sources_shadow.launch.py').read_text()
    package_xml = (ROOT / 'package.xml').read_text()

    assert "'launch', 'hwt601_shadow.launch.py'" in launch
    assert "'launch', 'encoder_shadow.launch.py'" in launch
    assert 'operator_stationary_confirmed' in launch
    assert "default_value='true'" not in launch
    assert "default_value='false'" not in launch
    assert "'operator_stationary_confirmed': LaunchConfiguration(" in launch
    assert "executable='base_hardware'" not in launch
    assert 'hwt601_encoder_shadow_ekf.launch.py' not in launch
    assert 'ekf_node' not in launch
    assert 'cmd_vel' not in launch
    assert "'/odom'" not in launch
    assert "'/tf'" not in launch
    assert '<exec_depend>base_hardware</exec_depend>' in package_xml
