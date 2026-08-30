#!/usr/bin/env python3
"""Motorless HWT601 validation; OAK and EKF are opt-in comparison stages."""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    base_share = get_package_share_directory('base_hardware')
    bringup_share = get_package_share_directory('robot_bringup')
    fusion_share = get_package_share_directory('robot_state_estimation')

    base_params = os.path.join(
        base_share, 'config', 'base_hardware_params.yaml')
    oak_launch = os.path.join(bringup_share, 'launch', 'oak.launch.py')
    hwt_launch = os.path.join(fusion_share, 'launch', 'hwt601.launch.py')
    fusion_launch = os.path.join(fusion_share, 'launch', 'fusion.launch.py')
    hwt_adapter = os.path.join(
        fusion_share, 'config', 'amadeus_hwt601.yaml')

    return LaunchDescription([
        DeclareLaunchArgument(
            'start_oak', default_value='false',
            description='Optionally start OAK for a time-limited comparison.'),
        DeclareLaunchArgument(
            'start_fusion_adapter', default_value='false',
            description='Run HWT validation/bias adapter after raw checks pass.'),
        DeclareLaunchArgument(
            'start_ekf', default_value='false',
            description=(
                'Opt in only after scale, signs and static TF were accepted.')),
        DeclareLaunchArgument(
            'start_scan_gate', default_value='false',
            description='Opt in only after the measured static TF exists.'),

        # No launch argument can enable the motor RS485 path.
        Node(
            package='base_hardware',
            executable='base_hardware',
            name='base_hardware',
            output='screen',
            parameters=[base_params, {
                'odom_topic': '/wheel/odom_raw',
                'publish_tf': False,
                'dry_run': True,
                'allow_rs485': False,
            }]),

        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(hwt_launch)),

        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(oak_launch),
            condition=IfCondition(LaunchConfiguration('start_oak')),
            launch_arguments={'pointcloud': 'false'}.items()),

        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(fusion_launch),
            condition=IfCondition(
                LaunchConfiguration('start_fusion_adapter')),
            launch_arguments={
                'adapter_config': hwt_adapter,
                'start_ekf': LaunchConfiguration('start_ekf'),
                'start_scan_gate': LaunchConfiguration('start_scan_gate'),
                'start_lidar_reference': 'false',
            }.items()),
    ])
