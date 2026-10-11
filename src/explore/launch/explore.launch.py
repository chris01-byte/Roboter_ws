#!/usr/bin/env python3
# =====================================================================
#  explore.launch.py  -  Startet den Frontier-Exploration-Node (WP-5)
# ---------------------------------------------------------------------
#  Start:
#    ros2 launch explore explore.launch.py
#
#  Voraussetzung: Eine Karte wird publiziert (SLAM / RTAB-Map auf map_topic)
#  UND Nav2 laeuft (Action navigate_to_pose). Fuer den Trockentest genuegt
#  ein Map-Publisher + der Nav2-Mock bzw. der echte Nav2-Stack.
#
#  Ausloesen der Erkundung (ohne BT, zum schnellen Test) z.B. mit:
#    ros2 action send_goal /explore_area robot_interfaces/action/ExploreArea \
#         "{timeout_s: 0.0, min_frontier_size_m: 0.0, return_to_start: false}"
# =====================================================================
import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration, PythonExpression
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    pkg = get_package_share_directory('explore')
    params = os.path.join(pkg, 'config', 'explore_params.yaml')
    params_overlay = LaunchConfiguration('explore_params_overlay')
    unknown_space_policy = LaunchConfiguration('unknown_space_policy')
    motion_params = PythonExpression([
        "'", os.path.join(pkg, 'config', 'metric_sensor_guarded_motion_params.yaml'),
        "' if '", unknown_space_policy, "' == 'sensor_guarded' else '",
        os.path.join(pkg, 'config', 'metric_observed_only_motion_params.yaml'), "'"])
    safe_bt = os.path.join(
        pkg, 'behavior_trees', 'navigate_to_pose_no_recovery.xml')

    return LaunchDescription([
        DeclareLaunchArgument('unknown_space_policy', default_value='observed_only',
            choices=['observed_only', 'sensor_guarded']),
        DeclareLaunchArgument('require_hwt601_fusion', default_value='false'),
        DeclareLaunchArgument('hwt601_active_drive', default_value='false'),
        DeclareLaunchArgument('hwt_development_contract', default_value='false'),
        DeclareLaunchArgument(
            'explore_params_overlay', default_value=params,
            description='Optionales zweites Parameterprofil; Standard '
                        'wiederholt die normalen Explorer-Parameter.'),
        Node(
            package='explore',
            executable='explore',
            name='explore_node',
            output='screen',
            parameters=[
                params, params_overlay, motion_params, {
                    'behavior_tree': safe_bt,
                    'require_hwt601_fusion': ParameterValue(
                        LaunchConfiguration('require_hwt601_fusion'), value_type=bool),
                    'hwt601_active_drive': ParameterValue(
                        LaunchConfiguration('hwt601_active_drive'), value_type=bool),
                    'hwt_development_contract': ParameterValue(
                        LaunchConfiguration('hwt_development_contract'), value_type=bool),
                }],
        )
    ])
