#!/usr/bin/env python3
# =====================================================================
#  robot_face.launch.py  -  Gesichts-Controller + Webserver
# ---------------------------------------------------------------------
#  Startet:
#    - face_controller  (Ereignisse -> /face/state_json)
#    - serve_face       (statische Web-App, Port 8081)
#    - optional rosbridge_websocket (Port 9090), falls er nicht schon
#      laeuft (smartphone_gui.launch.py startet ihn normalerweise):
#        ros2 launch robot_face robot_face.launch.py with_rosbridge:=true
#
#  Anzeige am 7-Zoll-Display des Jetson: Chromium im Kiosk-Modus auf
#  http://localhost:8081 (Einrichtung siehe README).
# =====================================================================
import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    pkg = get_package_share_directory('robot_face')
    params = os.path.join(pkg, 'config', 'face_params.yaml')

    face_port = LaunchConfiguration('face_port')
    with_rosbridge = LaunchConfiguration('with_rosbridge')

    return LaunchDescription([
        DeclareLaunchArgument('face_port', default_value='8081'),
        DeclareLaunchArgument(
            'with_rosbridge', default_value='false',
            description='rosbridge mitstarten (nur wenn er nicht schon '
                        'von smartphone_gui.launch.py kommt).'),

        Node(
            package='robot_face',
            executable='face_controller',
            name='face_controller',
            output='screen',
            parameters=[params],
        ),

        Node(
            package='robot_face',
            executable='serve_face',
            name='robot_face_server',
            output='screen',
            arguments=['--host', '0.0.0.0', '--port', face_port],
        ),

        Node(
            package='rosbridge_server',
            executable='rosbridge_websocket',
            name='rosbridge_websocket',
            output='screen',
            parameters=[{'port': 9090, 'address': '0.0.0.0'}],
            condition=IfCondition(with_rosbridge),
        ),
    ])
