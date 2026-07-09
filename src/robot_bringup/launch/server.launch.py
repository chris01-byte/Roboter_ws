#!/usr/bin/env python3
# =====================================================================
#  server.launch.py  -  OFFBOARD-Start (KI-Server, WP-5 Bausteine B/C)
# ---------------------------------------------------------------------
#  Startet die rechenintensiven KI-Nodes auf dem stationaeren Server
#  (Ubuntu 22.04 / ROS 2 Humble, RTX 3090). Der Roboter findet diese
#  Nodes automatisch ueber ROS 2 DDS (gleiches WLAN + ROS_DOMAIN_ID).
#
#  Start (auf dem Server):
#    export ROS_DOMAIN_ID=42          # gleicher Wert wie auf dem Roboter!
#    ros2 launch robot_bringup server.launch.py
#
#  Enthaelt:
#    - llm_planner          (Sprache -> Missionsauftrag)   [Baustein C]
#    - semantic_perception  (Open-Vocabulary-Erkennung)    [Baustein B]
# =====================================================================
import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource


def _include(pkg, launch_file):
    return IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(get_package_share_directory(pkg), 'launch', launch_file)))


def generate_launch_description():
    return LaunchDescription([
        # --- Sprach-/Aufgabenplaner (LLM) ---
        _include('llm_planner', 'llm_planner.launch.py'),

        # --- Semantische Wahrnehmung (Open-Vocabulary) ---
        _include('semantic_perception', 'semantic_perception.launch.py'),
    ])
