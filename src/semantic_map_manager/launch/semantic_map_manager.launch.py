#!/usr/bin/env python3
"""Startet nur den semantischen Kartenmanager; keinerlei Aktoren/Nav2."""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    package_share = get_package_share_directory("semantic_map_manager")
    parameters = os.path.join(
        package_share,
        "config",
        "semantic_map_manager.yaml",
    )
    return LaunchDescription(
        [
            Node(
                package="semantic_map_manager",
                executable="semantic_map_manager",
                name="semantic_map_manager",
                output="screen",
                parameters=[parameters],
            )
        ]
    )
