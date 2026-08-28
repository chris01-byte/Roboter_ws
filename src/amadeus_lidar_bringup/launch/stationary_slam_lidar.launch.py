#!/usr/bin/env python3
"""Manuelle 2D-Kartierung nur aus bestaetigten Stillstands-Scans."""

import os
import math

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    IncludeLaunchDescription,
    LogInfo,
    OpaqueFunction,
)
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PythonExpression
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def _slam_actions(context, *, slam_params):
    """Erzeugt SLAM erst nach validierter Auswertung der Fortsetzungspose."""
    map_file_name = LaunchConfiguration('map_file_name').perform(
        context).strip()
    overrides = {'scan_topic': '/scan_stillstand'}

    if map_file_name:
        missing = [
            suffix for suffix in ('.posegraph', '.data')
            if not os.path.isfile(map_file_name + suffix)
        ]
        if missing:
            raise RuntimeError(
                'Posegraph unvollstaendig: Erwartet werden '
                + ', '.join(map_file_name + suffix for suffix in missing))
        try:
            start_pose = [
                float(LaunchConfiguration(name).perform(context))
                for name in ('map_start_x', 'map_start_y', 'map_start_yaw')
            ]
        except ValueError as error:
            raise RuntimeError(
                'map_start_x/y/yaw muessen Zahlen sein') from error
        if not all(math.isfinite(value) for value in start_pose):
            raise RuntimeError('Fortsetzungspose muss endlich sein')
        overrides.update({
            'map_file_name': map_file_name,
            'map_start_pose': start_pose,
        })
        mode_message = (
            'Vorhandener Posegraph wird an der vorgegebenen, zuvor '
            'verifizierten Startpose fortgesetzt.')
    else:
        mode_message = 'Neuer leerer Posegraph wird angelegt.'

    return [
        LogInfo(msg=mode_message),
        Node(
            package='slam_toolbox',
            executable='async_slam_toolbox_node',
            name='slam_toolbox',
            output='screen',
            parameters=[slam_params, overrides]),
    ]


def generate_launch_description():
    lidar_pkg = get_package_share_directory('amadeus_lidar_bringup')
    slam_params = os.path.join(
        lidar_pkg, 'config', 'slam_toolbox_amadeus.yaml')
    gate_params = os.path.join(
        lidar_pkg, 'config', 'stationary_scan_gate.yaml')
    lidar_launch = os.path.join(
        lidar_pkg, 'launch', 'stl27l.launch.py')
    base_params = os.path.join(
        get_package_share_directory('base_hardware'),
        'config', 'base_hardware_params.yaml')

    active_drive = LaunchConfiguration('active_drive')
    manual_teleop = LaunchConfiguration('manual_teleop')
    teleop_enabled = IfCondition(PythonExpression([
        "'", active_drive, "' == 'true' and '", manual_teleop,
        "' == 'true'",
    ]))
    normalize_scan = LaunchConfiguration('normalize_scan')
    source_scan_topic = ParameterValue(
        PythonExpression(
            ["'/scan_normiert' if '", normalize_scan, "' == 'true' "
             "else '/scan'"]),
        value_type=str)
    dry_run = ParameterValue(
        PythonExpression(["'", active_drive, "' != 'true'"]),
        value_type=bool)
    allow_rs485 = ParameterValue(
        PythonExpression(["'", active_drive, "' == 'true'"]),
        value_type=bool)

    return LaunchDescription([
        DeclareLaunchArgument(
            'active_drive', default_value='false',
            description='true bestromt die Basis; nur nach neuer Freigabe.'),
        DeclareLaunchArgument(
            'normalize_scan', default_value='true',
            description='STL-27L auf feste 2160 Strahlen normalisieren.'),
        DeclareLaunchArgument(
            'crop', default_value='true',
            description='Vermessenen Mastsektor maskieren.'),
        DeclareLaunchArgument(
            'manual_teleop', default_value='false',
            description='Controller direkt auf /cmd_vel starten. Dieser '
                        'Sondermodus besitzt absichtlich keine VL53-Kette.'),
        DeclareLaunchArgument(
            'joy_dev', default_value='0',
            description='Nummer des Joystick-Geraets /dev/input/js<N>.'),
        DeclareLaunchArgument(
            'map_file_name', default_value='',
            description='Optionaler Posegraph-Stamm ohne .posegraph/.data.'),
        DeclareLaunchArgument(
            'map_start_x', default_value='0.0',
            description='Verifizierte Startpose im fortgesetzten Graph [m].'),
        DeclareLaunchArgument(
            'map_start_y', default_value='0.0',
            description='Verifizierte Startpose im fortgesetzten Graph [m].'),
        DeclareLaunchArgument(
            'map_start_yaw', default_value='0.0',
            description='Verifizierte Startausrichtung im Graph [rad].'),
        DeclareLaunchArgument(
            'stationary_gate_params', default_value=gate_params,
            description='Parameter der Stillstandsfreigabe.'),

        # Vor allen Hardwareprozessen auswerten: Ein unvollstaendiger
        # Fortsetzungsgraph darf auch bei active_drive:=true nichts starten.
        OpaqueFunction(
            function=_slam_actions,
            kwargs={'slam_params': slam_params}),

        LogInfo(msg='STILLSTANDSKARTIERUNG: Nur /scan_stillstand erreicht '
                    'slam_toolbox; bewegte Scans bleiben gesperrt.'),
        LogInfo(condition=IfCondition(active_drive),
                msg='ACHTUNG: Motoren werden bestromt. Not-Aus bereithalten.'),
        LogInfo(condition=teleop_enabled,
                msg='ACHTUNG: Controller geht direkt auf /cmd_vel; keine '
                    'VL53-Notbremse in diesem Sondermodus.'),

        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(lidar_launch),
            launch_arguments={
                'publish_static_tf': 'true',
                'crop': LaunchConfiguration('crop'),
            }.items()),

        Node(
            package='base_hardware',
            executable='base_hardware',
            name='base_hardware',
            output='screen',
            parameters=[base_params, {
                'publish_tf': True,
                'dry_run': dry_run,
                'allow_rs485': allow_rs485,
            }]),

        Node(
            package='amadeus_lidar_bringup',
            executable='scan_vereinheitlichen',
            name='scan_vereinheitlichen',
            output='screen',
            condition=IfCondition(normalize_scan),
            parameters=[{
                'eingang': '/scan',
                'ausgang': '/scan_normiert',
                'strahlen': 2160,
            }]),

        Node(
            package='amadeus_lidar_bringup',
            executable='stationary_scan_gate',
            name='stationary_scan_gate',
            output='screen',
            parameters=[LaunchConfiguration('stationary_gate_params'), {
                'input_scan_topic': source_scan_topic,
                'output_scan_topic': '/scan_stillstand',
            }]),

        Node(
            package='joy', executable='joy_node', name='joy_node',
            output='screen', condition=teleop_enabled,
            parameters=[{
                'device_id': ParameterValue(
                    LaunchConfiguration('joy_dev'), value_type=int),
                'deadzone': 0.20,
                'autorepeat_rate': 20.0,
            }]),
        Node(
            package='teleop_twist_joy', executable='teleop_node',
            name='teleop_twist_joy_node', output='screen',
            condition=teleop_enabled,
            parameters=[{
                'axis_linear.x': 7,
                'axis_angular.yaw': 6,
                'scale_linear.x': 0.08,
                'scale_angular.yaw': 0.30,
                'scale_linear_turbo.x': 0.10,
                'scale_angular_turbo.yaw': 0.40,
                'enable_button': 4,
                'enable_turbo_button': 5,
                'require_enable_button': False,
                'publish_stamped_twist': False,
            }],
            remappings=[('/cmd_vel', '/cmd_vel')]),
    ])
