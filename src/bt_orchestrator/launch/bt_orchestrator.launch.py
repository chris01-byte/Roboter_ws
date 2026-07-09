#!/usr/bin/env python3
# =====================================================================
#  bt_orchestrator.launch.py
#  Startet den BT-Orchestrator (Missions-Action-Server, K1) mit den
#  Parametern aus config/bt_params.yaml und ABSOLUTEN XML-Pfaden (die
#  installierten Baeume), damit beide Missionstypen sicher gefunden werden.
#  Start:  ros2 launch bt_orchestrator bt_orchestrator.launch.py
#
#  Der Node wartet auf ein RunMission-Goal (vom mission_manager). Fuer den
#  reinen Selbsttest: mock_servers/dry_run.launch.py (mit autostart_mission).
# =====================================================================
import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    pkg_share = get_package_share_directory('bt_orchestrator')

    # Zentrale Parameter-Datei (ROS-Namen, Timeouts, Testobjekt)
    params_file = os.path.join(pkg_share, 'config', 'bt_params.yaml')

    # Absolute Pfade zu BEIDEN Baeumen (ueberschreiben die relativen Defaults).
    pnp_xml = os.path.join(pkg_share, 'bt_xml', 'pick_and_place.xml')
    explore_xml = os.path.join(pkg_share, 'bt_xml', 'explore.xml')

    return LaunchDescription([
        Node(
            package='bt_orchestrator',
            executable='bt_orchestrator',
            name='bt_orchestrator',
            output='screen',
            parameters=[params_file, {
                'bt_xml_file': pnp_xml,            # Alias -> pick_and_place_xml
                'pick_and_place_xml': pnp_xml,
                'explore_xml': explore_xml,
            }],
        )
    ])
