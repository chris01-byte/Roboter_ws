#!/usr/bin/env python3
# =====================================================================
#  slam_lidar.launch.py  -  2D-Kartierung mit dem STL-27L
#  ====================================================================
#  Startet genau das, was fuer eine LiDAR-Karte noetig ist:
#    base_hardware   -> /odom und TF odom->base_link (gemessene Raddrehzahl)
#    STL-27L         -> /scan und TF base_link->laser_frame
#    slam_toolbox    -> /map und TF map->odom
#
#  BEWUSST NICHT DABEI: OAK-Kamera und RTAB-Map. Beide wuerden mit
#  slam_toolbox um map->odom konkurrieren, und der Integrationsplan verlangt
#  zuerst eine reine LiDAR-Baseline, bevor eine Fusion geplant wird.
#  Ebenfalls nicht dabei: die VL53-Kette. Wer sie als Notbremse will, startet
#  vl53_near_field.launch.py separat und faehrt ueber cmd_vel_smoothed.
#
#  ---------------------------------------------------------------------
#  A) Aufbau pruefen, ohne Motorstrom:
#       source /opt/ros/humble/setup.bash
#       source ~/amadeus_slam_toolbox_ws/install/setup.bash
#       source ~/roboter_ws/install/local_setup.bash
#       ros2 launch amadeus_lidar_bringup slam_lidar.launch.py
#     -> /scan, /map und der TF-Baum lassen sich pruefen, der Roboter steht.
#        Die Odometrie steht dabei still: base_hardware liest die Ist-Drehzahl
#        nur im scharfen Betrieb.
#
#  B) KARTIERFAHRT - Motoren bestromt, Not-Aus in der Hand:
#       Terminal 1: source /opt/ros/humble/setup.bash
#                   source ~/amadeus_slam_toolbox_ws/install/setup.bash
#                   source ~/roboter_ws/install/local_setup.bash
#                   ros2 launch amadeus_lidar_bringup slam_lidar.launch.py \
#                     active_drive:=true
#       Terminal 2: ros2 launch robot_bringup teleop_joy.launch.py \
#                     cmd_topic:=/cmd_vel
#     Langsam fahren, Ecken langsam umrunden.
#
#  C) Karte speichern (waehrend SLAM laeuft):
#       ros2 run nav2_map_server map_saver_cli -f ~/maps/amadeus_lidar_JJJJMMTT
#  ---------------------------------------------------------------------
#
#  SICHERHEITSGRENZEN DES SENSORS:
#  Die Scanebene liegt auf 75 cm. Alles darunter ist unsichtbar - Tischplatten,
#  Kisten, Hocker, Schwellen, Kabel. Der maskierte Mastsektor (236-304 Grad)
#  ist UNBEKANNTER Raum, nicht freier Raum: nach hinten hat der Roboter mit
#  diesem Sensor keinerlei Wahrnehmung.
# =====================================================================
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, LogInfo
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PythonExpression
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    lidar_pkg = get_package_share_directory('amadeus_lidar_bringup')
    slam_params = os.path.join(lidar_pkg, 'config', 'slam_toolbox_amadeus.yaml')
    lidar_launch = os.path.join(lidar_pkg, 'launch', 'stl27l.launch.py')

    base_params = os.path.join(
        get_package_share_directory('base_hardware'), 'config',
        'base_hardware_params.yaml')

    active_drive = LaunchConfiguration('active_drive')
    dry_run = ParameterValue(
        PythonExpression(["'", active_drive, "' != 'true'"]), value_type=bool)
    allow_rs485 = ParameterValue(
        PythonExpression(["'", active_drive, "' == 'true'"]), value_type=bool)

    # Karto verwirft jeden Scan, dessen Strahlenzahl von der des ersten
    # verarbeiteten Scans abweicht. Der STL-27L schwankt zwischen 2146 und
    # 2176 Strahlen, deshalb laeuft normalerweise der Vereinheitlicher davor.
    normalize_scan = LaunchConfiguration('normalize_scan')
    scan_topic = ParameterValue(
        PythonExpression(
            ["'/scan_normiert' if '", normalize_scan, "' == 'true' "
             "else '/scan'"]),
        value_type=str)

    return LaunchDescription([
        DeclareLaunchArgument(
            'active_drive', default_value='false',
            description='true = base_hardware SCHARF. Nur dann liefert es die '
                        'gemessene Odometrie, die slam_toolbox braucht.'),
        DeclareLaunchArgument(
            'normalize_scan', default_value='true',
            description='true = /scan wird auf eine feste Strahlenzahl '
                        'umgesetzt und slam_toolbox hoert auf /scan_normiert. '
                        'Auf false nur zum Gegenmessen: dann verwirft Karto '
                        'rund drei Viertel aller Scans.'),
        DeclareLaunchArgument(
            'crop', default_value='true',
            description='Winkelmaskierung des Mastsektors. Zur Fehlersuche auf false: '
                        'Der Treiber setzt maskierte Strahlen auf 0, und wenn ein '
                        'Verbraucher range_min als 0 ansieht, gelten sie als gueltige '
                        'Messung "Hindernis in 0 m" statt als ungueltig.'),

        LogInfo(condition=IfCondition(active_drive),
                msg='ACHTUNG: Motoren werden bestromt. Not-Aus bereithalten.'),

        # --- LiDAR mit vermessener Montagepose ---
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(lidar_launch),
            launch_arguments={'publish_static_tf': 'true',
                              'crop': LaunchConfiguration('crop')}.items()),

        # --- Basis: /odom + TF odom->base_link ---
        Node(package='base_hardware', executable='base_hardware',
             name='base_hardware', output='screen',
             parameters=[base_params, {
                 'publish_tf': True,
                 'dry_run': dry_run,
                 'allow_rs485': allow_rs485,
             }]),

        # --- Scans auf feste Strahlenzahl bringen ---
        # GEMESSEN 12.08.2026: Der STL-27L liefert 19 verschiedene
        # Strahlenzahlen (2146..2176); die haeufigste deckt nur 25.7 % ab.
        # Karto merkt sich die Zahl des ersten Scans und verwirft alle
        # abweichenden lautlos auf stdout. Ohne diesen Knoten kommt nur rund
        # ein Viertel der Scans in der Karte an.
        Node(package='amadeus_lidar_bringup',
             executable='scan_vereinheitlichen',
             name='scan_vereinheitlichen', output='screen',
             condition=IfCondition(normalize_scan),
             parameters=[{'eingang': '/scan',
                          'ausgang': '/scan_normiert',
                          'strahlen': 2160}]),

        # --- slam_toolbox: einziger Besitzer von /map und map->odom ---
        # ROS 2 Humble braucht den gepinnten Backport aus
        # docs/SLAM_TOOLBOX_ROTATION_FIX.md. Vor dem Launch dessen Overlay
        # sourcen; sonst werden reine Drehungen weiterhin vor Karto verworfen.
        Node(package='slam_toolbox', executable='async_slam_toolbox_node',
             name='slam_toolbox', output='screen',
             parameters=[slam_params, {'scan_topic': scan_topic}]),
    ])
