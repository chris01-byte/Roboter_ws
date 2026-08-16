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
from launch_ros.actions import Node


def generate_launch_description():
    pkg = get_package_share_directory('explore')
    params = os.path.join(pkg, 'config', 'explore_params.yaml')
    safe_bt = os.path.join(
        pkg, 'behavior_trees', 'navigate_to_pose_no_recovery.xml')

    return LaunchDescription([
        Node(
            package='explore',
            executable='explore',
            name='explore_node',
            output='screen',
            parameters=[params, {'behavior_tree': safe_bt}],
        )
    ])
