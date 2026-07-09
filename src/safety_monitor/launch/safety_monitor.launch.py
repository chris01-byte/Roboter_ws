#!/usr/bin/env python3
# =====================================================================
#  safety_monitor.launch.py  -  Onboard-Not-Aus-Waechter (K4)
# ---------------------------------------------------------------------
#  Start:  ros2 launch safety_monitor safety_monitor.launch.py
#  Wird normalerweise von robot_bringup/robot.launch.py mitgestartet.
#
#  Not-Aus testen (zweites Terminal):
#    ros2 topic pub --once /safety/estop_request std_msgs/msg/Bool "{data: true}"
#    ros2 topic echo /safety/estop        # -> data: true
#    ros2 topic pub --once /safety/estop_request std_msgs/msg/Bool "{data: false}"
# =====================================================================
import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    pkg = get_package_share_directory('safety_monitor')
    params = os.path.join(pkg, 'config', 'safety_monitor_params.yaml')

    return LaunchDescription([
        Node(
            package='safety_monitor',
            executable='safety_monitor',
            name='safety_monitor',
            output='screen',
            parameters=[params],
        )
    ])
