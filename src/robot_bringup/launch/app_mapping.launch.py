#!/usr/bin/env python3
"""Single-owner mapping stack for app-controlled adaptive exploration."""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, LogInfo
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def _launch_file(package, filename):
    return os.path.join(
        get_package_share_directory(package), 'launch', filename)


def generate_launch_description():
    active_drive = LaunchConfiguration('active_drive')
    enable_auto_explore = LaunchConfiguration('enable_auto_explore')
    normalize_scan = LaunchConfiguration('normalize_scan')
    crop = LaunchConfiguration('crop')
    start_web_gui = LaunchConfiguration('start_web_gui')
    explore_params_overlay = LaunchConfiguration('explore_params_overlay')
    default_explore_params = os.path.join(
        get_package_share_directory('explore'), 'config',
        'explore_params.yaml')

    return LaunchDescription([
        DeclareLaunchArgument(
            'active_drive', default_value='false',
            description='true bestromt die Basis; nur nach Hardwarefreigabe.'),
        DeclareLaunchArgument(
            'enable_auto_explore', default_value='false',
            description='Zweites Opt-in fuer App-Erkundung und Fahrtor.'),
        DeclareLaunchArgument(
            'normalize_scan', default_value='true',
            description='STL-27L auf 2160 Strahlen normalisieren.'),
        DeclareLaunchArgument(
            'crop', default_value='true',
            description='Vermessenen Mastsektor im LiDAR maskieren.'),
        DeclareLaunchArgument(
            'start_web_gui', default_value='true',
            description='Web-Fallback auf Port 8080 mitstarten.'),
        DeclareLaunchArgument(
            'explore_params_overlay', default_value=default_explore_params,
            description='Optionales begrenzendes Explorer-Profil.'),

        LogInfo(msg='App-Kartierung: genau ein SLAM/Nav2-/Missions-Stack; '
                    'Kartenmanager und rosbridge sind integriert.'),

        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(_launch_file(
                'robot_navigation', 'nav_mapping.launch.py')),
            launch_arguments={
                'active_drive': active_drive,
                'enable_auto_explore': enable_auto_explore,
                'normalize_scan': normalize_scan,
                'crop': crop,
                'explore_params_overlay': explore_params_overlay,
            }.items()),

        # Beide Manager sind reine Beobachter/Persistenzschichten. Sie senden
        # weder Nav2-Ziele noch cmd_vel und erzeugen keinen zweiten /map-Owner.
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(_launch_file(
                'robot_map_manager', 'map_manager.launch.py'))),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(_launch_file(
                'semantic_map_manager', 'semantic_map_manager.launch.py'))),

        # Einzige App-Bruecke dieses Launches. robot.launch.py oder
        # smartphone_gui.launch.py duerfen nicht parallel gestartet werden.
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
            arguments=['--host', '0.0.0.0', '--port', '8080'],
            condition=IfCondition(start_web_gui),
        ),
    ])
