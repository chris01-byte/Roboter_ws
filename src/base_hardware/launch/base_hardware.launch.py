#!/usr/bin/env python3
# =====================================================================
#  base_hardware.launch.py
# ---------------------------------------------------------------------
#  Startet den Basis-Hardware-Node. Standard: Dry-run, keine RS485-Ausgabe.
#
#  Start:
#    ros2 launch base_hardware base_hardware.launch.py
#
#  Optional mit TF fuer Standalone-RViz-Test:
#    ros2 launch base_hardware base_hardware.launch.py publish_tf:=true
# =====================================================================
import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    publish_tf = LaunchConfiguration('publish_tf')
    pkg = get_package_share_directory('base_hardware')
    params = os.path.join(pkg, 'config', 'base_hardware_params.yaml')

    return LaunchDescription([
        DeclareLaunchArgument(
            'publish_tf', default_value='false',
            description='Nur fuer Standalone-Test: base_hardware soll odom->base_link TF publizieren'),

        Node(
            package='base_hardware',
            executable='base_hardware',
            name='base_hardware',
            output='screen',
            parameters=[params, {'publish_tf': ParameterValue(publish_tf, value_type=bool)}],
        )
    ])
