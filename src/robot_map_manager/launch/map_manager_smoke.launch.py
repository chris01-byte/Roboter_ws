#!/usr/bin/env python3
"""Fahrbewegungsfreier Smoke-Test mit statischer Testwohnung."""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    manager_share = get_package_share_directory("robot_map_manager")
    navigation_share = get_package_share_directory("robot_navigation")
    manager_parameters = os.path.join(
        manager_share,
        "config",
        "robot_map_manager.yaml",
    )
    default_map = os.path.join(
        navigation_share,
        "maps",
        "testwohnung.yaml",
    )

    map_yaml = LaunchConfiguration("map")
    start_rosbridge = LaunchConfiguration("start_rosbridge")
    rosbridge_address = LaunchConfiguration("rosbridge_address")

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "map",
                default_value=default_map,
                description="Statische Karten-YAML für den Smoke-Test.",
            ),
            DeclareLaunchArgument(
                "start_rosbridge",
                default_value="false",
                description="rosbridge nur bei Bedarf lokal auf Port 9090 starten.",
            ),
            DeclareLaunchArgument(
                "rosbridge_address",
                default_value="127.0.0.1",
                description="Bind-Adresse des optionalen rosbridge.",
            ),
            Node(
                package="nav2_map_server",
                executable="map_server",
                name="map_manager_smoke_map_server",
                output="screen",
                parameters=[{"yaml_filename": map_yaml}],
            ),
            Node(
                package="nav2_lifecycle_manager",
                executable="lifecycle_manager",
                name="map_manager_smoke_lifecycle",
                output="screen",
                parameters=[
                    {
                        "autostart": True,
                        "node_names": ["map_manager_smoke_map_server"],
                    }
                ],
            ),
            # Nur eine unveränderliche Testtransformation; keine Odometrie,
            # Navigation, cmd_vel-Publisher oder Motor-Hardware wird gestartet.
            Node(
                package="tf2_ros",
                executable="static_transform_publisher",
                name="map_manager_smoke_tf",
                output="screen",
                arguments=[
                    "0",
                    "0",
                    "0",
                    "0",
                    "0",
                    "0",
                    "map",
                    "base_link",
                ],
            ),
            Node(
                package="robot_map_manager",
                executable="robot_map_manager",
                name="robot_map_manager",
                output="screen",
                parameters=[manager_parameters],
            ),
            Node(
                package="rosbridge_server",
                executable="rosbridge_websocket",
                name="map_manager_smoke_rosbridge",
                output="screen",
                parameters=[{"port": 9090, "address": rosbridge_address}],
                condition=IfCondition(start_rosbridge),
            ),
        ]
    )
