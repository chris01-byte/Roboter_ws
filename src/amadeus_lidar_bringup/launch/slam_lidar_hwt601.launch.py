#!/usr/bin/env python3
"""Opt-in LiDAR mapping A/B path with HWT601 yaw and encoder translation."""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, LogInfo
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PythonExpression
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    lidar_share = get_package_share_directory('amadeus_lidar_bringup')
    state_share = get_package_share_directory('robot_state_estimation')
    base_params = os.path.join(
        get_package_share_directory('base_hardware'), 'config',
        'base_hardware_params.yaml')
    slam_params = os.path.join(
        lidar_share, 'config', 'slam_toolbox_amadeus.yaml')
    hwt_ekf_params = os.path.join(
        state_share, 'config', 'ekf_hwt601_mapping.yaml')
    hwt_observer_params = os.path.join(
        state_share, 'config', 'amadeus_hwt601.yaml')

    active_drive = LaunchConfiguration('active_drive')
    normalize_scan = LaunchConfiguration('normalize_scan')
    dry_run = ParameterValue(
        PythonExpression(["'", active_drive, "' != 'true'"]),
        value_type=bool)
    allow_rs485 = ParameterValue(
        PythonExpression(["'", active_drive, "' == 'true'"]),
        value_type=bool)
    scan_topic = ParameterValue(
        PythonExpression(
            ["'/scan_normiert' if '", normalize_scan, "' == 'true' "
             "else '/scan'"]),
        value_type=str)

    return LaunchDescription([
        DeclareLaunchArgument(
            'active_drive', default_value='false',
            description='true bestromt die Basis; nur nach Hardwarefreigabe.'),
        DeclareLaunchArgument(
            'operator_stationary_confirmed', default_value='false',
            description='Muss fuer die HWT-Startkalibrierung explizit true sein.'),
        DeclareLaunchArgument(
            'normalize_scan', default_value='true'),
        DeclareLaunchArgument(
            'crop', default_value='true'),

        LogInfo(condition=IfCondition(active_drive),
                msg='ACHTUNG: HWT-Karten-A/B mit bestromten Motoren; Not-Aus bereithalten.'),
        LogInfo(msg='HWT-Karten-A/B: Encoder liefert nur vx, HWT601 nur Gier; '
                    'EKF besitzt /odom und odom->base_link; LiDAR-Matcher beobachtet nur.'),

        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(os.path.join(
                lidar_share, 'launch', 'stl27l.launch.py')),
            launch_arguments={
                'publish_static_tf': 'true',
                'crop': LaunchConfiguration('crop'),
            }.items()),

        # Einzige Verbindung zum Antrieb. Im HWT-Modus darf die Basis weder
        # /odom noch TF besitzen, sondern gibt nur ihre gemessenen Encoder aus.
        Node(
            package='base_hardware', executable='base_hardware',
            name='base_hardware', output='screen',
            parameters=[base_params, {
                'odom_topic': '/fusion/hwt601/wheel_odom_raw',
                'publish_tf': False,
                'dry_run': dry_run,
                'allow_rs485': allow_rs485,
            }]),

        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(os.path.join(
                state_share, 'launch', 'hwt601_shadow.launch.py')),
            launch_arguments={
                'operator_stationary_confirmed': LaunchConfiguration(
                    'operator_stationary_confirmed'),
            }.items()),

        Node(
            package='robot_localization', executable='ekf_node',
            name='hwt601_mapping_ekf', output='screen',
            parameters=[hwt_ekf_params],
            remappings=[('odometry/filtered', '/odom')]),

        Node(
            package='amadeus_lidar_bringup',
            executable='scan_vereinheitlichen',
            name='scan_vereinheitlichen', output='screen',
            condition=IfCondition(normalize_scan),
            parameters=[{
                'eingang': '/scan',
                'ausgang': '/scan_normiert',
                'strahlen': 2160,
            }]),

        # Radunabhaengige Kontrollmessung. Kein TF und bewusst kein EKF-Input
        # im ersten Kartenversuch, damit die Ursache einer Abweichung sichtbar
        # bleibt statt von einer zweiten Korrektur verdeckt zu werden.
        Node(
            package='robot_state_estimation', executable='lidar_odometry',
            name='hwt601_lidar_observer', output='screen',
            parameters=[hwt_observer_params, {
                'scan_input': scan_topic,
                'odom_output': '/shadow/hwt601/lidar_odom',
                'status_topic': '/shadow/hwt601/lidar_status_json',
            }]),

        # Einziger Besitzer von /map und map -> odom.
        Node(
            package='slam_toolbox', executable='async_slam_toolbox_node',
            name='slam_toolbox', output='screen',
            parameters=[slam_params, {'scan_topic': scan_topic}]),
    ])
