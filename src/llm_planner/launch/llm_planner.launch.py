#!/usr/bin/env python3
# =====================================================================
#  llm_planner.launch.py  -  Startet den LLM-Aufgabenplaner (WP-5 C)
# ---------------------------------------------------------------------
#  Start (auf dem KI-Server):
#    ros2 launch llm_planner llm_planner.launch.py
#
#  Voraussetzung fuer echtes LLM: Ollama laeuft und das Modell ist geladen:
#    ollama serve            # (laeuft meist als Dienst)
#    ollama pull llama3.2
#  Ohne Ollama arbeitet der Node im Regel-Fallback (use_ollama:=false).
# =====================================================================
import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    pkg = get_package_share_directory('llm_planner')
    params = os.path.join(pkg, 'config', 'llm_planner_params.yaml')

    return LaunchDescription([
        Node(
            package='llm_planner',
            executable='llm_planner',
            name='llm_planner',
            output='screen',
            parameters=[params],
        )
    ])
