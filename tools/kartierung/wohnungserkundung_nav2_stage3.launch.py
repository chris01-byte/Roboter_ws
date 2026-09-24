#!/usr/bin/env python3
"""Device-free Stage-3 process fixture: real Nav2 and collision monitor.

This launch deliberately starts no hardware, SLAM, or real sensor driver.
The companion process checker owns the synthetic map, TF, odometry and
pointclouds in a private DDS domain. Never use this as a robot launch file.
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    if os.environ.get('ROS_DOMAIN_ID') != '219':
        raise RuntimeError('Stage-3-Pruefstack nur in ROS_DOMAIN_ID=219')

    nav_params = os.path.join(
        get_package_share_directory('robot_navigation'), 'config',
        'nav2_params_real.yaml')
    collision_params = os.path.join(
        get_package_share_directory('vl53_near_field'), 'config',
        'collision_monitor_mapping_params.yaml')
    nav_nodes = [
        'controller_server', 'planner_server', 'behavior_server',
        'bt_navigator', 'velocity_smoother',
    ]

    return LaunchDescription([
        *[Node(
            package='tf2_ros', executable='static_transform_publisher',
            name=f'we_stage3_vl53_{side}', output='screen',
            arguments=['0.290', str(y), '0.215', '0', '0', '0',
                       'base_link', f'vl53_{side}_link'])
          for side, y in (('left', 0.095), ('right', -0.095))],
        Node(
            package='tf2_ros', executable='static_transform_publisher',
            name='we_stage3_map_odom', output='screen',
            arguments=['0.85', '1.525', '0', '0', '0', '0', 'map', 'odom']),
        Node(
            package='robot_navigation', executable='cmd_vel_mission_gate',
            name='cmd_vel_mission_gate', output='screen',
            parameters=[{
                'require_localization': False,
                'allow_localization_search': False,
                'allow_explore_mission': True,
                'estop_topic': '/we_stage3/estop',
            }]),
        Node(
            package='nav2_controller', executable='controller_server',
            name='controller_server', output='screen',
            parameters=[nav_params],
            remappings=[('cmd_vel', 'cmd_vel_nav_raw')]),
        Node(
            package='nav2_planner', executable='planner_server',
            name='planner_server', output='screen',
            parameters=[nav_params]),
        Node(
            package='nav2_behaviors', executable='behavior_server',
            name='behavior_server', output='screen',
            parameters=[nav_params],
            remappings=[('cmd_vel', 'cmd_vel_recovery_blocked')]),
        Node(
            package='nav2_bt_navigator', executable='bt_navigator',
            name='bt_navigator', output='screen',
            parameters=[nav_params]),
        Node(
            package='nav2_velocity_smoother', executable='velocity_smoother',
            name='velocity_smoother', output='screen',
            parameters=[nav_params],
            remappings=[('cmd_vel', 'cmd_vel_nav'),
                        ('cmd_vel_smoothed', 'cmd_vel_smoothed')]),
        Node(
            package='nav2_lifecycle_manager', executable='lifecycle_manager',
            name='lifecycle_manager_navigation', output='screen',
            parameters=[{'autostart': True, 'node_names': nav_nodes}]),
        Node(
            package='nav2_collision_monitor', executable='collision_monitor',
            name='collision_monitor', output='screen',
            parameters=[collision_params]),
        Node(
            package='nav2_lifecycle_manager', executable='lifecycle_manager',
            name='lifecycle_manager_collision', output='screen',
            parameters=[{'autostart': True,
                         'node_names': ['collision_monitor']}]),
    ])
