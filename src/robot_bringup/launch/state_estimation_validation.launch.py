#!/usr/bin/env python3
"""Motorless validation stack for the modular state estimator.

This launch hard-codes the base driver to dry-run.  It cannot be turned into a
real drive launch through a launch argument.
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    base_share = get_package_share_directory('base_hardware')
    bringup_share = get_package_share_directory('robot_bringup')
    lidar_share = get_package_share_directory('amadeus_lidar_bringup')
    fusion_share = get_package_share_directory('robot_state_estimation')

    base_params = os.path.join(
        base_share, 'config', 'base_hardware_params.yaml')
    oak_launch = os.path.join(bringup_share, 'launch', 'oak.launch.py')
    lidar_launch = os.path.join(lidar_share, 'launch', 'stl27l.launch.py')
    fusion_launch = os.path.join(fusion_share, 'launch', 'fusion.launch.py')

    return LaunchDescription([
        DeclareLaunchArgument(
            'start_oak', default_value='true',
            description='Start OAK with IMU; point cloud stays disabled.'),
        DeclareLaunchArgument(
            'start_lidar', default_value='false',
            description='Start STL-27L and scan normalization if connected.'),
        DeclareLaunchArgument(
            'start_lidar_reference', default_value='false',
            description='Start optional independent scan-motion monitor.'),
        DeclareLaunchArgument(
            'normalized_scan_divisor', default_value='2'),

        # No launch argument can override these four safety values.
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
            PythonLaunchDescriptionSource(oak_launch),
            condition=IfCondition(LaunchConfiguration('start_oak')),
            launch_arguments={'pointcloud': 'false'}.items()),

        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(lidar_launch),
            condition=IfCondition(LaunchConfiguration('start_lidar')),
            launch_arguments={
                'publish_static_tf': 'true',
                'crop': 'true',
            }.items()),

        Node(
            package='amadeus_lidar_bringup',
            executable='scan_vereinheitlichen',
            name='scan_vereinheitlichen',
            output='screen',
            condition=IfCondition(LaunchConfiguration('start_lidar')),
            parameters=[{
                'eingang': '/scan',
                'ausgang': '/scan_normiert',
                'strahlen': 2160,
                'ausgabe_teiler': ParameterValue(
                    LaunchConfiguration('normalized_scan_divisor'),
                    value_type=int),
            }]),

        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(fusion_launch),
            launch_arguments={
                'start_lidar_reference': LaunchConfiguration(
                    'start_lidar_reference'),
            }.items()),
    ])
