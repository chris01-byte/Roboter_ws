#!/usr/bin/env python3
# =====================================================================
#  mock_servers.launch.py
#  Startet NUR die Mock-Server (ohne den Behavior-Tree).
#  Nuetzlich, wenn du den BT separat starten willst.
#  Start:  ros2 launch mock_servers mock_servers.launch.py
# =====================================================================
import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    pkg = get_package_share_directory('mock_servers')
    params = os.path.join(pkg, 'config', 'mock_params.yaml')

    return LaunchDescription([
        Node(
            package='mock_servers',
            executable='mock_servers',
            name='mock_servers',
            output='screen',
            parameters=[params],
        )
    ])
