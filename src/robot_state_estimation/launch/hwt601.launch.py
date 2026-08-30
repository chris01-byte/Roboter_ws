#!/usr/bin/env python3
"""Start only the passive HWT601 reader; no TF, camera or actuator path."""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterFile


def generate_launch_description():
    package_share = get_package_share_directory('robot_state_estimation')
    default_config = os.path.join(
        package_share, 'config', 'hwt601_driver.yaml')

    return LaunchDescription([
        DeclareLaunchArgument(
            'config', default_value=default_config,
            description='Read-only HWT601 serial and scaling profile.'),
        Node(
            package='robot_state_estimation',
            executable='hwt601_imu',
            name='hwt601_imu',
            output='screen',
            parameters=[ParameterFile(
                LaunchConfiguration('config'), allow_substs=True)]),
    ])
