#!/usr/bin/env python3
"""Motorless, on-demand HD OAK profile; never run beside oak.launch.py."""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource


def generate_launch_description():
    bringup = get_package_share_directory('robot_bringup')
    semantic = get_package_share_directory('semantic_perception')
    return LaunchDescription([
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(bringup, 'launch', 'oak.launch.py')),
            launch_arguments={
                'params_file': os.path.join(
                    bringup, 'config', 'oak_params_detail.yaml'),
                'semantic_relay_params': os.path.join(
                    semantic, 'config',
                    'semantic_stream_relay_detail_params.yaml'),
                'pointcloud': 'false',
                'semantic_relay': 'true',
                'external_rectifier': 'true',
            }.items(),
        ),
    ])
