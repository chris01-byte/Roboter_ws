#!/usr/bin/env python3
# =====================================================================
#  smartphone_gui.launch.py - WP-4 Komplettstart
# ---------------------------------------------------------------------
#  Startet:
#    - mission_manager
#    - rosbridge_websocket (Port 9090)
#    - statischen Webserver fuer die Smartphone-PWA (Port 8080)
#
#  Start:
#    ros2 launch smartphone_gui smartphone_gui.launch.py
#
#  Smartphone:
#    http://JETSON-IP:8080
# =====================================================================
import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    gui_port = LaunchConfiguration('gui_port')

    mission_pkg = get_package_share_directory('mission_manager')
    mission_params = os.path.join(mission_pkg, 'config', 'mission_catalog.yaml')

    return LaunchDescription([
        DeclareLaunchArgument('gui_port', default_value='8080'),

        Node(
            package='mission_manager',
            executable='mission_manager',
            name='mission_manager',
            output='screen',
            parameters=[mission_params],
        ),

        Node(
            package='rosbridge_server',
            executable='rosbridge_websocket',
            name='rosbridge_websocket',
            output='screen',
            parameters=[{'port': 9090, 'address': '0.0.0.0'}],
        ),

        Node(
            package='smartphone_gui',
            executable='serve_gui',
            name='smartphone_gui_server',
            output='screen',
            arguments=['--host', '0.0.0.0', '--port', gui_port],
        ),
    ])
