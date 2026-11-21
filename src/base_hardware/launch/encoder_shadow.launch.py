#!/usr/bin/env python3
"""Startet ausschliesslich den strikt lesenden Encoder-Shadow-Node."""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    package_share = get_package_share_directory('base_hardware')
    parameters = os.path.join(package_share, 'config', 'encoder_shadow.yaml')

    return LaunchDescription([
        Node(
            package='base_hardware',
            executable='encoder_shadow_reader',
            name='hwt601_encoder_shadow_reader',
            output='screen',
            parameters=[parameters],
            respawn=False,
        ),
    ])
