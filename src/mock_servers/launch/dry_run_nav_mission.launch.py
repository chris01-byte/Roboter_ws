#!/usr/bin/env python3
# =====================================================================
#  dry_run_nav_mission.launch.py  -  Koenigstest: echte Mission + ECHTES Nav2
#  ====================================================================
#  Wie dry_run_mission.launch.py, aber die Navigation macht der ECHTE
#  Nav2-Stack (robot_navigation/nav_test.launch.py: Testkarte + virtuelle
#  Dry-Run-Basis) statt des Mocks. Arm/Greifer/Wahrnehmung bleiben Mocks.
#
#    ros2 launch mock_servers dry_run_nav_mission.launch.py
#    # Auftrag senden (Ablagepose 'Tisch' kommt aus dem Pose-Katalog):
#    ros2 topic pub --once /mission_manager/command_json std_msgs/msg/String \
#      "{data: '{\"type\":\"pick_and_place\",\"object\":\"Tasse\",\"room\":\"Kueche\",\"target\":\"Tisch\"}'}"
#    ros2 topic echo /mission_manager/status_json     # running -> success
#
#  Erwartung: Der Roboter FAEHRT wirklich (Nav2 plant, /odom bewegt sich
#  durch die Testwohnung) - im Log erscheint KEIN "[mock] NavigateToPose".
#
#  ACHTUNG: eigener mission_manager - nicht zugleich mit
#  smartphone_gui.launch.py starten. Voraussetzung: ros-humble-navigation2.
# =====================================================================
import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, TimerAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node


def generate_launch_description():
    mock_pkg = get_package_share_directory('mock_servers')
    bt_pkg = get_package_share_directory('bt_orchestrator')
    mm_pkg = get_package_share_directory('mission_manager')
    nav_pkg = get_package_share_directory('robot_navigation')

    mock_params = os.path.join(mock_pkg, 'config', 'mock_params.yaml')
    bt_params = os.path.join(bt_pkg, 'config', 'bt_params.yaml')
    bt_xml = os.path.join(bt_pkg, 'bt_xml', 'pick_and_place.xml')
    explore_xml = os.path.join(bt_pkg, 'bt_xml', 'explore.xml')
    mm_params = os.path.join(mm_pkg, 'config', 'mission_catalog.yaml')

    # ECHTES Nav2 (Testkarte + virtuelle Basis; enthaelt base_hardware!).
    nav = IncludeLaunchDescription(PythonLaunchDescriptionSource(
        os.path.join(nav_pkg, 'launch', 'nav_test.launch.py')))

    # Mocks OHNE Navigation (sonst zwei Server auf /navigate_to_pose).
    mock = Node(
        package='mock_servers', executable='mock_servers', name='mock_servers',
        output='screen',
        parameters=[mock_params, {'provide_navigation': False}],
    )

    bt = Node(
        package='bt_orchestrator', executable='bt_orchestrator', name='bt_orchestrator',
        output='screen',
        parameters=[bt_params, {'bt_xml_file': bt_xml,
                                'pick_and_place_xml': bt_xml,
                                'explore_xml': explore_xml,
                                'autostart_mission': ''}],
    )

    mm = Node(
        package='mission_manager', executable='mission_manager', name='mission_manager',
        output='screen', parameters=[mm_params],
    )

    # BT + mission_manager etwas spaeter: Nav2-Lifecycle braucht ein paar Sekunden.
    delayed = TimerAction(period=6.0, actions=[bt, mm])

    return LaunchDescription([nav, mock, delayed])
