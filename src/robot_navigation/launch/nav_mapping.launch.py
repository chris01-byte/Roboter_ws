#!/usr/bin/env python3
"""Fail-closed LiDAR SLAM + Nav2 + frontier exploration bringup."""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument, IncludeLaunchDescription, LogInfo, TimerAction)
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def _launch_file(package, filename):
    return os.path.join(
        get_package_share_directory(package), 'launch', filename)


def generate_launch_description():
    nav_pkg = get_package_share_directory('robot_navigation')
    params = os.path.join(nav_pkg, 'config', 'nav2_params_real.yaml')
    mapping_collision_params = os.path.join(
        get_package_share_directory('vl53_near_field'), 'config',
        'collision_monitor_mapping_params.yaml')
    default_explore_params = os.path.join(
        get_package_share_directory('explore'), 'config',
        'explore_params.yaml')

    active_drive = LaunchConfiguration('active_drive')
    enable_auto_explore = LaunchConfiguration('enable_auto_explore')
    normalize_scan = LaunchConfiguration('normalize_scan')
    crop = LaunchConfiguration('crop')
    explore_params_overlay = LaunchConfiguration('explore_params_overlay')

    nav_cmd_remap = [('cmd_vel', 'cmd_vel_nav_raw')]
    smoother_cmd_remap = [
        ('cmd_vel', 'cmd_vel_nav'),
        ('cmd_vel_smoothed', 'cmd_vel_smoothed'),
    ]
    nav_nodes = [
        'controller_server', 'planner_server',
        'behavior_server', 'bt_navigator', 'velocity_smoother']

    staged_navigation = TimerAction(
        period=4.0,
        actions=[
            Node(
                package='robot_navigation',
                executable='cmd_vel_mission_gate',
                name='cmd_vel_mission_gate',
                output='screen',
                parameters=[{
                    'require_localization': False,
                    'allow_localization_search': False,
                    'allow_explore_mission': ParameterValue(
                        enable_auto_explore, value_type=bool),
                }],
            ),
            Node(
                package='nav2_controller', executable='controller_server',
                name='controller_server', output='screen',
                parameters=[params], remappings=nav_cmd_remap),
            Node(
                package='nav2_planner', executable='planner_server',
                name='planner_server', output='screen', parameters=[params]),
            # Humble laedt beim Aktivieren des BT-Navigators auch seinen
            # Standardbaum und erwartet deshalb die Recovery-Actions. Der
            # Explorer selbst verwendet einen recovery-freien Baum. Falls
            # dennoch eine Recovery aufgerufen wird, bleibt deren cmd_vel
            # absichtlich von der realen Fahrkette getrennt.
            Node(
                package='nav2_behaviors', executable='behavior_server',
                name='behavior_server', output='screen', parameters=[params],
                remappings=[('cmd_vel', 'cmd_vel_recovery_blocked')]),
            Node(
                package='nav2_bt_navigator', executable='bt_navigator',
                name='bt_navigator', output='screen', parameters=[params]),
            Node(
                package='nav2_velocity_smoother',
                executable='velocity_smoother',
                name='velocity_smoother', output='screen',
                parameters=[params], remappings=smoother_cmd_remap),
            Node(
                package='nav2_lifecycle_manager',
                executable='lifecycle_manager',
                name='lifecycle_manager_navigation', output='screen',
                parameters=[{
                    'autostart': True,
                    'node_names': nav_nodes,
                }]),
        ])

    return LaunchDescription([
        DeclareLaunchArgument(
            'active_drive', default_value='false',
            description='true bestromt die Basis; nur nach Hardwarefreigabe.'),
        DeclareLaunchArgument(
            'enable_auto_explore', default_value='false',
            description='Explizites zweites Opt-in fuer echte Explore-Missionen '
                        'und das cmd_vel-Fahrtor.'),
        DeclareLaunchArgument(
            'normalize_scan', default_value='true',
            description='STL-27L zwingend auf 2160 Strahlen normalisieren.'),
        DeclareLaunchArgument(
            'crop', default_value='true',
            description='Vermessenen Mastsektor im LiDAR maskieren.'),
        DeclareLaunchArgument(
            'explore_params_overlay', default_value=default_explore_params,
            description='Optionales begrenzendes Explorer-Profil.'),

        LogInfo(msg='Automatische Kartierung: OAK bleibt deaktiviert; '
                    'Hinderniskette ist dual-VL53 plus collision_monitor.'),

        # Einziger Besitzer von Basis, LiDAR, /map und map->odom.
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(_launch_file(
                'amadeus_lidar_bringup', 'slam_lidar.launch.py')),
            launch_arguments={
                'active_drive': active_drive,
                'normalize_scan': normalize_scan,
                'crop': crop,
            }.items()),

        # Letzte reaktive Instanz vor /cmd_vel und laufende VL53-Daten.
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(_launch_file(
                'vl53_near_field', 'vl53_near_field.launch.py')),
            launch_arguments={
                'collision_params_file': mapping_collision_params,
            }.items()),

        # Software-BT-Sicht; der hardwired Not-Aus bleibt primaer.
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(_launch_file(
                'safety_monitor', 'safety_monitor.launch.py'))),

        # Explorer und Missionskette starten, bewegen aber ohne beide Opt-ins
        # und frischen Gate-Status keinen Motor.
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(_launch_file(
                'explore', 'explore.launch.py')),
            launch_arguments={
                'explore_params_overlay': explore_params_overlay,
            }.items()),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(_launch_file(
                'bt_orchestrator', 'bt_orchestrator.launch.py'))),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(_launch_file(
                'mission_manager', 'mission_manager.launch.py')),
            launch_arguments={
                'enable_real_explore': enable_auto_explore,
                'enable_real_go_to_room': 'false',
                'require_localization_for_real_go_to_room': 'true',
            }.items()),

        # SLAM und Sensoren erhalten vier Sekunden Vorsprung. Kein map_server,
        # kein AMCL und kein statisches map->odom: slam_toolbox ist alleiniger
        # Karten- und Transform-Eigentuemer.
        staged_navigation,
    ])
