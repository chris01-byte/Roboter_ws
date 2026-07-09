#!/usr/bin/env python3
# =====================================================================
#  dry_run_safety.launch.py  -  Not-Aus-Kette echt testen (K4 + K1)
#  ====================================================================
#  Wie dry_run_mission.launch.py, aber der /safety/estop kommt vom
#  ECHTEN safety_monitor statt vom Mock (mock: publish_estop:=false).
#  So laesst sich der komplette Not-Aus-Pfad trocken durchspielen:
#
#    ros2 launch mock_servers dry_run_safety.launch.py
#    # Mission starten:
#    ros2 topic pub --once /mission_manager/command_json std_msgs/msg/String \
#      "{data: '{\"type\":\"pick_and_place\",\"object\":\"Tasse\",\"room\":\"Kueche\",\"target\":\"Tisch\"}'}"
#    # Waehrend die Mission laeuft, Not-Aus ausloesen:
#    ros2 topic pub --once /safety/estop_request std_msgs/msg/Bool "{data: true}"
#    # -> Mission haelt sofort an (IsEstopClear wird FAILURE); Status geht auf failed.
#    # Wieder freigeben:
#    ros2 topic pub --once /safety/estop_request std_msgs/msg/Bool "{data: false}"
#
#  ACHTUNG: startet einen eigenen mission_manager - nicht zugleich mit
#  smartphone_gui.launch.py verwenden (sonst laeuft der Node doppelt).
# =====================================================================
import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import TimerAction
from launch_ros.actions import Node


def generate_launch_description():
    mock_pkg = get_package_share_directory('mock_servers')
    bt_pkg = get_package_share_directory('bt_orchestrator')
    mm_pkg = get_package_share_directory('mission_manager')
    safety_pkg = get_package_share_directory('safety_monitor')

    mock_params = os.path.join(mock_pkg, 'config', 'mock_params.yaml')
    bt_params = os.path.join(bt_pkg, 'config', 'bt_params.yaml')
    bt_xml = os.path.join(bt_pkg, 'bt_xml', 'pick_and_place.xml')
    explore_xml = os.path.join(bt_pkg, 'bt_xml', 'explore.xml')
    mm_params = os.path.join(mm_pkg, 'config', 'mission_catalog.yaml')
    safety_params = os.path.join(safety_pkg, 'config', 'safety_monitor_params.yaml')

    # Mock OHNE eigenen /safety/estop -> der safety_monitor ist die Quelle.
    mock = Node(
        package='mock_servers', executable='mock_servers', name='mock_servers',
        output='screen', parameters=[mock_params, {'publish_estop': False}],
    )

    # Echter Not-Aus-Waechter (publiziert /safety/estop).
    safety = Node(
        package='safety_monitor', executable='safety_monitor', name='safety_monitor',
        output='screen', parameters=[safety_params],
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

    # BT + mission_manager 3 s spaeter, Mock + safety_monitor zuerst.
    delayed = TimerAction(period=3.0, actions=[bt, mm])

    return LaunchDescription([mock, safety, delayed])
