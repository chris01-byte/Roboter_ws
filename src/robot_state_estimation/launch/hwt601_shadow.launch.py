#!/usr/bin/env python3
"""Start only the isolated HWT601 yaw shadow; no pose, TF or hardware drive."""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    package_share = get_package_share_directory('robot_state_estimation')
    config = os.path.join(package_share, 'config', 'hwt601_shadow.yaml')
    stationary_confirmed = ParameterValue(
        LaunchConfiguration('operator_stationary_confirmed'), value_type=bool)

    return LaunchDescription([
        # Deliberately no default: a live startup calibration needs a fresh,
        # explicit declaration that the chassis is physically stationary.
        DeclareLaunchArgument(
            'operator_stationary_confirmed',
            description=(
                'Set true only while the chassis is physically stationary. '
                'The measured startup bias is frozen afterwards.')),

        Node(
            package='robot_state_estimation',
            executable='hwt601_imu',
            name='hwt601_shadow_reader',
            output='screen',
            parameters=[config, {
                'imu_topic': '/shadow/hwt601/imu/data_raw',
                'status_topic': '/shadow/hwt601/raw_status_json',
                'diagnostics_topic': '/shadow/hwt601/raw_diagnostics',
            }]),
        Node(
            package='robot_state_estimation',
            executable='hwt601_shadow',
            name='hwt601_shadow',
            output='screen',
            parameters=[config, {
                'operator_stationary_confirmed': stationary_confirmed,
            }]),
    ])
