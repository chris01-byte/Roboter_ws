#!/usr/bin/env python3
# =====================================================================
#  mission_manager.launch.py - WP-4
# =====================================================================
import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    pkg = get_package_share_directory('mission_manager')
    params = os.path.join(pkg, 'config', 'mission_catalog.yaml')

    return LaunchDescription([
        Node(
            package='mission_manager',
            executable='mission_manager',
            name='mission_manager',
            output='screen',
            parameters=[params],
        )
    ])
