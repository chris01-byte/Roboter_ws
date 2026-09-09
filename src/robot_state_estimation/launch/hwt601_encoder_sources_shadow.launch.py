#!/usr/bin/env python3
"""Start only the read-only HWT601 and encoder shadow sources."""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration


def generate_launch_description():
    state_share = get_package_share_directory('robot_state_estimation')
    base_share = get_package_share_directory('base_hardware')
    hwt_launch = os.path.join(
        state_share, 'launch', 'hwt601_shadow.launch.py')
    encoder_launch = os.path.join(
        base_share, 'launch', 'encoder_shadow.launch.py')

    return LaunchDescription([
        # Deliberately required and forwarded to the HWT startup-bias gate.
        # The combined acceptance must additionally prove encoder stillness
        # over the complete settle/calibration window.
        DeclareLaunchArgument(
            'operator_stationary_confirmed',
            description=(
                'Set true only while the chassis is physically stationary. '
                'Encoder evidence must independently confirm this window.')),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(encoder_launch)),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(hwt_launch),
            launch_arguments={
                'operator_stationary_confirmed': LaunchConfiguration(
                    'operator_stationary_confirmed'),
            }.items()),
    ])
