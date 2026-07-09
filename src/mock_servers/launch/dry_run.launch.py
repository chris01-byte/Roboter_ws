#!/usr/bin/env python3
# =====================================================================
#  dry_run.launch.py   -  KOMPLETTER Trockentest (ein Befehl)
#  Startet die Mock-Server UND den Behavior-Tree-Orchestrator.
#  Der BT startet 3 s verzoegert, damit die Mock-Server zuerst hochfahren.
#
#  K1: bt_orchestrator ist jetzt ein Missions-Action-Server und wartet
#  normal auf ein Goal. Fuer diesen reinen Trockentest (ohne mission_manager)
#  setzen wir autostart_mission:=pick_and_place -> der BT schickt sich das
#  Goal selbst und laeuft die Mission durch (Log: "Mission beendet mit
#  Status: SUCCESS"). Fuer die ECHTE Kette mission_manager -> BT siehe
#  dry_run_mission.launch.py.
#
#  Start:  ros2 launch mock_servers dry_run.launch.py
#  Danach: Groot2 oeffnen und mit dem laufenden Baum verbinden (Port 1667).
# =====================================================================
import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, TimerAction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    mock_pkg = get_package_share_directory('mock_servers')
    bt_pkg = get_package_share_directory('bt_orchestrator')

    mock_params = os.path.join(mock_pkg, 'config', 'mock_params.yaml')
    bt_params = os.path.join(bt_pkg, 'config', 'bt_params.yaml')
    bt_xml = os.path.join(bt_pkg, 'bt_xml', 'pick_and_place.xml')
    explore_xml = os.path.join(bt_pkg, 'bt_xml', 'explore.xml')

    # object_found:=false -> testet den K5-Guard (Objekt nicht gefunden +
    # kein Offboard -> darf NICHT erkunden). Default true laesst A1 unveraendert.
    object_found = LaunchConfiguration('object_found')

    # 1) Mock-Server sofort starten
    mock = Node(
        package='mock_servers',
        executable='mock_servers',
        name='mock_servers',
        output='screen',
        parameters=[mock_params,
                    {'object_found': ParameterValue(object_found, value_type=bool)}],
    )

    # 2) Behavior-Tree 3 s spaeter (damit die Server-Schnittstellen bereitstehen).
    #    autostart_mission -> BT schickt sich das Goal selbst (Trockentest ohne
    #    mission_manager). Ohne diesen Parameter wartet der BT auf ein Goal.
    bt = Node(
        package='bt_orchestrator',
        executable='bt_orchestrator',
        name='bt_orchestrator',
        output='screen',
        parameters=[bt_params, {'bt_xml_file': bt_xml,
                                'pick_and_place_xml': bt_xml,
                                'explore_xml': explore_xml,
                                'autostart_mission': 'pick_and_place'}],
    )
    bt_delayed = TimerAction(period=3.0, actions=[bt])

    return LaunchDescription([
        DeclareLaunchArgument('object_found', default_value='true'),
        mock, bt_delayed,
    ])
