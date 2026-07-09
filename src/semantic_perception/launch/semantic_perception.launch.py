#!/usr/bin/env python3
# =====================================================================
#  semantic_perception.launch.py  -  Open-Vocabulary-Wahrnehmung (WP-5 B)
# ---------------------------------------------------------------------
#  Start (auf dem KI-Server oder perspektivisch nah an der Kamera):
#    ros2 launch semantic_perception semantic_perception.launch.py
#
#  Standard-Backend ist 'stub' (simuliert). Fuer echte Erkennung das
#  Modell in _detect_with_model() einhaengen und model_backend setzen.
# =====================================================================
import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    pkg = get_package_share_directory('semantic_perception')
    params = os.path.join(pkg, 'config', 'semantic_perception_params.yaml')

    return LaunchDescription([
        Node(
            package='semantic_perception',
            executable='semantic_perception',
            name='semantic_perception',
            output='screen',
            parameters=[params],
        )
    ])
