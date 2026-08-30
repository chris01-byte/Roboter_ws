#!/usr/bin/env python3
"""Start only passive state estimation components; never starts hardware."""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    package_share = get_package_share_directory('robot_state_estimation')
    default_adapter = os.path.join(
        package_share, 'config', 'amadeus.yaml')
    default_ekf = os.path.join(
        package_share, 'config', 'ekf_encoder_imu.yaml')

    use_sim_time = ParameterValue(
        LaunchConfiguration('use_sim_time'), value_type=bool)

    return LaunchDescription([
        DeclareLaunchArgument(
            'adapter_config', default_value=default_adapter,
            description='Robot profile for adapters and quality limits.'),
        DeclareLaunchArgument(
            'ekf_config', default_value=default_ekf,
            description='robot_localization input selection and filter profile.'),
        DeclareLaunchArgument(
            'start_ekf', default_value='true',
            description='Start the passive robot_localization EKF.'),
        DeclareLaunchArgument(
            'start_scan_gate', default_value='true',
            description='Filter non-planar scans using the IMU.'),
        DeclareLaunchArgument(
            'start_lidar_reference', default_value='false',
            description=(
                'Start independent LiDAR motion monitoring. It is not fused '
                'directly into the first EKF profile.')),
        DeclareLaunchArgument(
            'use_sim_time', default_value='false'),
        DeclareLaunchArgument(
            'fused_odom_topic', default_value='/odom',
            description='Continuous local odometry consumed by SLAM/Nav2.'),

        Node(
            package='robot_state_estimation',
            executable='sensor_adapter',
            name='sensor_adapter',
            output='screen',
            parameters=[
                LaunchConfiguration('adapter_config'),
                {'use_sim_time': use_sim_time},
            ]),

        Node(
            package='robot_state_estimation',
            executable='scan_quality_gate',
            name='scan_quality_gate',
            output='screen',
            condition=IfCondition(LaunchConfiguration('start_scan_gate')),
            parameters=[
                LaunchConfiguration('adapter_config'),
                {'use_sim_time': use_sim_time},
            ]),

        Node(
            package='robot_localization',
            executable='ekf_node',
            name='ekf_filter_node',
            output='screen',
            condition=IfCondition(LaunchConfiguration('start_ekf')),
            parameters=[
                LaunchConfiguration('ekf_config'),
                {'use_sim_time': use_sim_time},
            ],
            remappings=[
                ('odometry/filtered', LaunchConfiguration('fused_odom_topic')),
            ]),

        Node(
            package='robot_state_estimation',
            executable='lidar_odometry',
            name='lidar_odometry',
            output='screen',
            condition=IfCondition(
                LaunchConfiguration('start_lidar_reference')),
            parameters=[
                LaunchConfiguration('adapter_config'),
                {'use_sim_time': use_sim_time},
            ]),
    ])
