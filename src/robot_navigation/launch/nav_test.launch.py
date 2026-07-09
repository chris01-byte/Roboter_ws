#!/usr/bin/env python3
# =====================================================================
#  nav_test.launch.py  -  ECHTER Nav2-Stack ohne Hardware
#  ====================================================================
#  Geschlossener Navigationskreis mit virtueller Basis:
#    Nav2 plant/regelt -> /cmd_vel -> base_hardware (Dry-Run) integriert
#    zu /odom + TF odom->base_link -> Nav2 sieht die Bewegung -> Ziel.
#  Lokalisierung: map->odom als statische Identitaet (Dry-Run-Odometrie
#  ist fehlerfrei). Mit SLAM/AMCL ersetzt deren TF spaeter diese Zeile.
#
#  Start:   ros2 launch robot_navigation nav_test.launch.py
#  Test:    ros2 action send_goal /navigate_to_pose nav2_msgs/action/NavigateToPose \
#             "{pose: {header: {frame_id: map}, pose: {position: {x: 1.5}, orientation: {w: 1.0}}}}"
#  RViz:    Karte 'testwohnung' (12x10 m): Wohnzimmer links, Flur rechts
#           unten, Kueche rechts oben; Roboterstart (0,0) im Wohnzimmer.
#
#  Voraussetzung (einmalig): sudo apt install ros-humble-navigation2
# =====================================================================
import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    pkg = get_package_share_directory('robot_navigation')
    params = os.path.join(pkg, 'config', 'nav2_params.yaml')
    default_map = os.path.join(pkg, 'maps', 'testwohnung.yaml')
    map_yaml = LaunchConfiguration('map')

    base_launch = os.path.join(
        get_package_share_directory('base_hardware'), 'launch',
        'base_hardware.launch.py')

    nav_nodes = ['controller_server', 'planner_server',
                 'behavior_server', 'bt_navigator']

    return LaunchDescription([
        DeclareLaunchArgument('map', default_value=default_map,
                              description='Karten-YAML (Default: Testwohnung)'),

        # --- Karte + "Lokalisierung" (statische Identitaet, s. Kopf) ---
        Node(package='nav2_map_server', executable='map_server',
             name='map_server', output='screen',
             parameters=[params, {'yaml_filename': map_yaml}]),
        Node(package='tf2_ros', executable='static_transform_publisher',
             name='tf_map_odom', output='screen',
             arguments=['0', '0', '0', '0', '0', '0', 'map', 'odom']),

        # --- Virtuelle Basis: Dry-Run + TF odom->base_link ---
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(base_launch),
            launch_arguments={'publish_tf': 'true'}.items()),

        # --- Nav2-Kern ---
        Node(package='nav2_controller', executable='controller_server',
             name='controller_server', output='screen', parameters=[params]),
        Node(package='nav2_planner', executable='planner_server',
             name='planner_server', output='screen', parameters=[params]),
        Node(package='nav2_behaviors', executable='behavior_server',
             name='behavior_server', output='screen', parameters=[params]),
        Node(package='nav2_bt_navigator', executable='bt_navigator',
             name='bt_navigator', output='screen', parameters=[params]),

        # --- Lifecycle: erst Karte, dann Navigation aktivieren ---
        Node(package='nav2_lifecycle_manager', executable='lifecycle_manager',
             name='lifecycle_manager_localization', output='screen',
             parameters=[{'autostart': True, 'node_names': ['map_server']}]),
        Node(package='nav2_lifecycle_manager', executable='lifecycle_manager',
             name='lifecycle_manager_navigation', output='screen',
             parameters=[{'autostart': True, 'node_names': nav_nodes}]),
    ])
