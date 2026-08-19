#!/usr/bin/env python3
# =====================================================================
#  mission_manager.launch.py - WP-4
# =====================================================================
import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    pkg = get_package_share_directory('mission_manager')
    params = os.path.join(pkg, 'config', 'mission_catalog.yaml')
    safe_room_bt = os.path.join(
        pkg, 'behavior_trees', 'navigate_to_pose_no_recovery.xml')

    return LaunchDescription([
        DeclareLaunchArgument(
            'enable_real_explore',
            default_value='false',
            description='true = Explore-Auftraege an den echten Behavior-Tree '
                        'senden. Nur zusammen mit dem Explore-Fahrtor.'),
        DeclareLaunchArgument(
            'enable_real_go_to_room',
            default_value='false',
            description='true = go_to_room sendet ein echtes Nav2-Ziel. '
                        'Nur nach motorlosem Preflight und Fahrfreigabe.'),
        DeclareLaunchArgument(
            'navigate_to_pose_action',
            default_value='/navigate_to_pose'),
        DeclareLaunchArgument(
            'go_to_room_behavior_tree',
            default_value=safe_room_bt,
            description='Recovery-freier Nav2-Baum fuer die erste Raumfahrt.'),
        DeclareLaunchArgument(
            'require_localization_for_real_go_to_room',
            default_value='true',
            description='Fail-closed: reales Raumziel nur mit frischer '
                        '/localization/ready-Freigabe.'),
        Node(
            package='mission_manager',
            executable='mission_manager',
            name='mission_manager',
            output='screen',
            parameters=[params, {
                'enable_real_explore': ParameterValue(
                    LaunchConfiguration('enable_real_explore'),
                    value_type=bool),
                'enable_real_go_to_room': ParameterValue(
                    LaunchConfiguration('enable_real_go_to_room'),
                    value_type=bool),
                'navigate_to_pose_action': LaunchConfiguration(
                    'navigate_to_pose_action'),
                'go_to_room_behavior_tree': LaunchConfiguration(
                    'go_to_room_behavior_tree'),
                'require_localization_for_real_go_to_room': ParameterValue(
                    LaunchConfiguration(
                        'require_localization_for_real_go_to_room'),
                    value_type=bool),
            }],
        )
    ])
