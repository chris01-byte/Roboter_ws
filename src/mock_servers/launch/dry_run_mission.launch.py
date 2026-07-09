#!/usr/bin/env python3
# =====================================================================
#  dry_run_mission.launch.py  -  ECHTE K1-Kette trocken testen
#  ====================================================================
#  Startet Mock-Server + bt_orchestrator (Action-Server, OHNE Autostart)
#  + mission_manager (Action-Client). Anders als dry_run.launch.py laeuft
#  die Mission hier NICHT von selbst - sie wird wie im Echtbetrieb per
#  command_json ausgeloest:
#
#    ros2 launch mock_servers dry_run_mission.launch.py
#    # zweites Terminal, Auftrag senden:
#    ros2 topic pub --once /mission_manager/command_json std_msgs/msg/String \
#      "{data: '{\"type\":\"pick_and_place\",\"object\":\"Tasse\",\"room\":\"Kueche\",\"target\":\"Tisch\"}'}"
#    # Status beobachten:
#    ros2 topic echo /mission_manager/status_json
#
#  Erwartung: status_json wandert von running (mit echten BT-Phasen wie
#  "NavigateToPose", "ComputeGrasp") nach success. Das ist der Nachweis,
#  dass Auftrag -> mission_manager -> bt_orchestrator -> Mocks WIRKLICH
#  durchlaeuft (Befund K1 geschlossen).
#
#  ACHTUNG: startet einen EIGENEN mission_manager - nicht gleichzeitig mit
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

    mock_params = os.path.join(mock_pkg, 'config', 'mock_params.yaml')
    bt_params = os.path.join(bt_pkg, 'config', 'bt_params.yaml')
    bt_xml = os.path.join(bt_pkg, 'bt_xml', 'pick_and_place.xml')
    explore_xml = os.path.join(bt_pkg, 'bt_xml', 'explore.xml')
    mm_params = os.path.join(mm_pkg, 'config', 'mission_catalog.yaml')

    mock = Node(
        package='mock_servers', executable='mock_servers', name='mock_servers',
        output='screen', parameters=[mock_params],
    )

    # bt_orchestrator als Action-Server (KEIN autostart -> wartet auf Goal).
    bt = Node(
        package='bt_orchestrator', executable='bt_orchestrator', name='bt_orchestrator',
        output='screen',
        parameters=[bt_params, {'bt_xml_file': bt_xml,
                                'pick_and_place_xml': bt_xml,
                                'explore_xml': explore_xml,
                                'autostart_mission': ''}],
    )

    # mission_manager als Action-Client.
    mm = Node(
        package='mission_manager', executable='mission_manager', name='mission_manager',
        output='screen', parameters=[mm_params],
    )

    # BT + mission_manager 3 s spaeter, damit die Mock-Server zuerst stehen.
    delayed = TimerAction(period=3.0, actions=[bt, mm])

    return LaunchDescription([mock, delayed])
