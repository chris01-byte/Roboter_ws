#!/usr/bin/env python3
"""Reale Nav2-Kette mit globaler AMCL-Lokalisierung auf einer gespeicherten Karte."""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    IncludeLaunchDescription,
    LogInfo,
    TimerAction,
)
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    navigation_share = get_package_share_directory('robot_navigation')
    navigation_params = os.path.join(
        navigation_share, 'config', 'nav2_params_real.yaml')
    nav_real_launch = os.path.join(
        navigation_share, 'launch', 'nav_real.launch.py')
    lidar_launch = os.path.join(
        get_package_share_directory('amadeus_lidar_bringup'),
        'launch', 'stl27l.launch.py')

    map_yaml = LaunchConfiguration('map')
    active_drive = LaunchConfiguration('active_drive')
    oak = LaunchConfiguration('oak')

    return LaunchDescription([
        # Kein Default: Eine versehentlich geladene Test-/Leerkarte waere fuer
        # globale Lokalisierung gefaehrlicher als ein klarer Startabbruch.
        DeclareLaunchArgument(
            'map',
            description='Absoluter Pfad zur bestaetigten, lokal gespeicherten '
                        'map.yaml. Echte Kartendaten gehoeren nicht ins Repo.'),
        DeclareLaunchArgument(
            'active_drive', default_value='false',
            description='false = motorloser Preflight. true = RS485 scharf; '
                        'nur mit freier Flaeche und Not-Aus.'),
        DeclareLaunchArgument(
            'oak', default_value='true',
            description='OAK-Punktwolke fuer die Nav2-Costmaps mitstarten.'),
        DeclareLaunchArgument(
            'auto_global_localization', default_value='true',
            description='Kartenfesten Vollscan nach bestaetigter Karte und '
                        'frischem LiDAR automatisch starten.'),
        DeclareLaunchArgument(
            'require_global_scan_match', default_value='true',
            description='Fail-closed Vollscan/Karten-Abgleich vor der ersten '
                        'Lokalisierungsfreigabe.'),

        LogInfo(
            msg='AMCL-Start ohne bekannte Pose: Fahrtor bleibt bis zur '
                'Lokalisierungsfreigabe geschlossen.'),
        LogInfo(
            condition=IfCondition(active_drive),
            msg='ACHTUNG: Basis ist scharf. Noch keine Fahrt ohne freie '
                'Flaeche und erreichbaren Not-Aus.'),

        # Der bewaehrte reale Navigationspfad bleibt unveraendert. Nur sein
        # Platzhalter-TF wird ausgeschaltet und das zweite Fahrtor aktiviert.
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(nav_real_launch),
            launch_arguments={
                'map': map_yaml,
                'active_drive': active_drive,
                'oak': oak,
                'static_map_odom': 'false',
                'require_localization': 'true',
                'allow_localization_search': 'true',
            }.items()),

        # AMCL lokalisiert mit demselben vermessenen STL-27L-Pfad wie die
        # Kartierung. Die feste Strahlenzahl verhindert den bereits belegten
        # wechselnden 2145..2176-Strahlen-Eingang.
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(lidar_launch),
            launch_arguments={
                'publish_static_tf': 'true',
                'crop': 'true',
            }.items()),
        Node(
            package='amadeus_lidar_bringup',
            executable='scan_vereinheitlichen',
            name='scan_vereinheitlichen',
            output='screen',
            parameters=[{
                'eingang': '/scan',
                'ausgang': '/scan_normiert',
                'strahlen': 2160,
            }]),

        # Einziger Besitzer von map->odom. Kein slam_toolbox, kein RTAB-Map
        # und kein statischer Platzhalter duerfen parallel laufen.
        # Die 22 Prozesse gleichzeitig zu konfigurieren erzeugte auf dem
        # Jetson sporadische Fast-DDS-Service-Timeouts. Karte, Basis und LiDAR
        # bekommen zuerst ein festes Startfenster; AMCL startet danach allein.
        TimerAction(period=4.0, actions=[
            Node(
                package='nav2_amcl', executable='amcl', name='amcl',
                output='screen', parameters=[navigation_params]),
            Node(
                package='nav2_lifecycle_manager', executable='lifecycle_manager',
                name='lifecycle_manager_amcl', output='screen',
                parameters=[{'autostart': True, 'node_names': ['amcl']}]),
        ]),

        # Der Guard startet erst nach dem AMCL-Aktivierungsfenster. Sollte
        # AMCL trotzdem fehlen/inaktiv bleiben, bleibt die Fahrt fail-closed.
        TimerAction(period=7.0, actions=[
            Node(
                package='robot_navigation', executable='localization_guard',
                name='localization_guard', output='screen',
                parameters=[{
                    'auto_global_localization': ParameterValue(
                        LaunchConfiguration('auto_global_localization'),
                        value_type=bool),
                    'require_global_scan_match': ParameterValue(
                        LaunchConfiguration('require_global_scan_match'),
                        value_type=bool),
                }]),
        # Unabhaengige Wahrheitspruefung: Ein selbstsicheres AMCL-Ergebnis
        # reicht nicht. Der Vollscan muss die aktuelle Karte eindeutig treffen
        # und setzt erst dann /initialpose fuer genau diesen Startzyklus. Der
        # native AMCL-Global-Reset wird bewusst nicht aufgerufen: In Humble
        # ist sein Dienst bereits vor dem internen Kartenempfang erreichbar.
            Node(
                package='robot_navigation', executable='global_scan_localizer',
                name='global_scan_localizer', output='screen'),
        ]),
    ])
