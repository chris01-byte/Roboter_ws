#!/usr/bin/env python3
# =====================================================================
#  robot.launch.py  -  ONBOARD-Start (mobiler Roboter, WP-5 Baustein D)
# ---------------------------------------------------------------------
#  Startet ALLES, was auf dem Roboter selbst laeuft (Echtzeit + Sicherheit).
#  Der KI-Server wird getrennt gestartet (server.launch.py) und ueber ROS 2
#  DDS im selben WLAN + gleicher ROS_DOMAIN_ID automatisch gefunden.
#
#  Start (auf dem Roboter/Jetson):
#    export ROS_DOMAIN_ID=42          # gleicher Wert wie auf dem Server!
#    ros2 launch robot_bringup robot.launch.py
#
#  Netzwerk-/DDS-Hinweise: siehe README.md und config/cyclonedds_profile.xml
# =====================================================================
import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def _include(pkg, launch_file):
    """Bindet die Launch-Datei eines anderen Pakets ein."""
    return IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(get_package_share_directory(pkg), 'launch', launch_file)))


def generate_launch_description():
    bringup = get_package_share_directory('robot_bringup')
    link_params = os.path.join(bringup, 'config', 'link_monitor_params.yaml')

    start_bt = LaunchConfiguration('start_bt')

    return LaunchDescription([
        DeclareLaunchArgument(
            'start_bt', default_value='true',
            description='Behavior-Tree-Missions-Server mitstarten. Default true, '
                        'seit K1: der BT ist ein wartender Action-Server (kein '
                        'Einmal-Laeufer) - der mission_manager braucht ihn erreichbar.'),

        # --- Onboard-Not-Aus-Waechter (K4): publiziert /safety/estop ---
        #     MUSS laufen, sonst haelt der BT jede echte Mission sofort an.
        _include('safety_monitor', 'safety_monitor.launch.py'),

        # --- Basisantrieb (Bus B) ---
        _include('base_hardware', 'base_hardware.launch.py'),

        # --- Reaktive Nahbereichs-Sicherheit (VL53) ---
        _include('vl53_near_field', 'vl53_near_field.launch.py'),

        # --- Autonome Erkundung (WP-5 Ebene 1) ---
        _include('explore', 'explore.launch.py'),

        # --- Bedien-Layer / Missionskoordination ---
        _include('mission_manager', 'mission_manager.launch.py'),

        # --- Server-Erreichbarkeit ueberwachen (WLAN-Fallback) ---
        Node(
            package='robot_bringup',
            executable='link_monitor',
            name='link_monitor',
            output='screen',
            parameters=[link_params],
        ),

        # --- Gesicht fuer das 7-Zoll-Roboter-Display (WP-4 Erweiterung) ---
        #     rosbridge kommt weiterhin aus smartphone_gui.launch.py;
        #     Standalone: ros2 launch robot_face robot_face.launch.py with_rosbridge:=true
        _include('robot_face', 'robot_face.launch.py'),

        # --- Behavior-Tree (optional; startet sonst on demand) ---
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(os.path.join(
                get_package_share_directory('bt_orchestrator'), 'launch',
                'bt_orchestrator.launch.py')),
            condition=IfCondition(start_bt)),

        # =================================================================
        #  PLATZHALTER - folgen, sobald die jeweiligen Stacks integriert sind:
        #    * SLAM (RTAB-Map)        -> liefert /map fuer Nav2 + explore
        #    * Navigation (Nav2)      -> navigate_to_pose, Costmaps
        #      (schon HEUTE virtuell testbar: robot_navigation/nav_test.launch.py)
        #    * Kamera (OAK/depthai)   -> /oak/rgb, /oak/points, Perception
        #    * Manipulation (MoveIt2) -> Arm-/Greifer-Action-Server
        #  Bis dahin lassen sich diese ueber die mock_servers bereitstellen.
        # =================================================================
    ])
