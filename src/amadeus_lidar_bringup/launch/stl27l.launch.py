#!/usr/bin/env python3
# =====================================================================
#  stl27l.launch.py  -  2D-LiDAR STL-27L an Amadeus
#  ====================================================================
#  Startet den Herstellertreiber (ldlidar_stl_ros2, unveraendert) mit den
#  Amadeus-Parametern aus config/stl27l.yaml.
#
#  WICHTIG - DIE MONTAGEPOSE WIRD NICHT GERATEN:
#  Solange publish_static_tf:=false (Vorgabe) ist, wird KEIN
#  base_link -> laser_frame veroeffentlicht. Ein falscher TF ist schlimmer
#  als gar keiner: SLAM und Nav2 wuerden die Messwerte an die falsche Stelle
#  im Raum legen, und der Fehler faellt erst in der fertigen Karte auf.
#  Fuer den isolierten Sensortest (Phase 1) genuegt Fixed Frame = laser_frame
#  in RViz - dafuer braucht es keinen TF.
#  Erst wenn die Werte nach Abschnitt 5.6 des Integrationsplans am echten
#  Roboter GEMESSEN sind, werden sie in config/stl27l.yaml eingetragen und
#  publish_static_tf:=true gesetzt. Besser noch: den Link in die URDF
#  aufnehmen und vom robot_state_publisher senden lassen - dann hier auf
#  false lassen, sonst gibt es zwei Publisher fuer denselben Transform.
#
#  ---------------------------------------------------------------------
#  A) Phase 1 - isolierter Sensortest, ohne TF, ohne SLAM:
#       ros2 launch amadeus_lidar_bringup stl27l.launch.py
#     Danach in RViz: Fixed Frame = laser_frame, LaserScan auf /scan.
#
#  B) Nach der Vermessung, mit statischem TF:
#       ros2 launch amadeus_lidar_bringup stl27l.launch.py publish_static_tf:=true
#
#  C) Diagnose mit ungefiltertem Scan (Winkelmaskierung aus):
#       ros2 launch amadeus_lidar_bringup stl27l.launch.py crop:=false
#  ---------------------------------------------------------------------
#
#  SICHERHEIT: Der STL-27L sitzt auf etwa 80 cm Hoehe. Alles darunter -
#  Tischplatten, Kisten, Hocker, Schwellen - ist fuer ihn UNSICHTBAR. Er
#  ersetzt keinen bodennahen Kollisionsschutz. Der maskierte Mastsektor ist
#  UNBEKANNTER Raum, nicht freier Raum.
# =====================================================================
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, LogInfo
from launch.conditions import IfCondition, UnlessCondition
from launch.substitutions import LaunchConfiguration, PythonExpression
from launch_ros.actions import Node


def generate_launch_description():
    pkg = get_package_share_directory('amadeus_lidar_bringup')
    params = os.path.join(pkg, 'config', 'stl27l.yaml')

    crop = LaunchConfiguration('crop')
    tf_on = LaunchConfiguration('publish_static_tf')

    return LaunchDescription([
        DeclareLaunchArgument(
            'port', default_value='/dev/amadeus_lidar',
            description='Serieller Port. Der stabile udev-Alias, NICHT /dev/ttyUSB0 - '
                        'dort haengt der Motor-RS485-Adapter.'),
        DeclareLaunchArgument(
            'crop', default_value='true',
            description='Winkelmaskierung des vom Mast verdeckten Sektors. Fuer die '
                        'Vermessung (Abschnitt 5.5) auf false setzen.'),
        DeclareLaunchArgument(
            'publish_static_tf', default_value='false',
            description='base_link -> laser_frame senden. NUR true, wenn die Werte in '
                        'config/stl27l.yaml gemessen sind UND der Link nicht schon aus '
                        'der URDF kommt.'),
        # Montagepose, GEMESSEN am 11.08.2026 (Herleitung siehe config/stl27l.yaml).
        # Der yaw ist der kritische Wert: Der Sensornullpunkt zeigt nach RECHTS,
        # nicht nach vorn - ermittelt an einem Rohr genau vor dem Roboter, das im
        # Scan bei +89 Grad erschien.
        DeclareLaunchArgument('tf_x', default_value='0.245',
                              description='[m] Radmitte 275 mm zur Vorderkante minus 30 mm'),
        DeclareLaunchArgument('tf_y', default_value='0.0',
                              description='[m] sitzt mittig'),
        DeclareLaunchArgument('tf_z', default_value='0.660',
                              description='[m] 750 mm ueber Boden minus 90 mm base_link-Hoehe'),
        DeclareLaunchArgument('tf_roll', default_value='0.0'),
        DeclareLaunchArgument('tf_pitch', default_value='0.0'),
        DeclareLaunchArgument('tf_yaw', default_value='-1.5708',
                              description='[rad] -90 Grad, Sensornullpunkt zeigt nach rechts'),

        LogInfo(condition=UnlessCondition(tf_on),
                msg='STL-27L: KEIN base_link->laser_frame (Montagepose noch nicht '
                    'vermessen). Fuer RViz Fixed Frame = laser_frame verwenden.'),
        LogInfo(condition=IfCondition(tf_on),
                msg='STL-27L: statischer TF aktiv - die Werte MUESSEN gemessen sein.'),
        LogInfo(condition=UnlessCondition(crop),
                msg='STL-27L: Winkelmaskierung AUS - der Scan enthaelt Reflexionen des '
                    'eigenen Rumpfs. Nur zur Vermessung, nicht fuer SLAM/Nav2.'),

        Node(
            package='ldlidar_stl_ros2', executable='ldlidar_stl_ros2_node',
            name='amadeus_stl27l', output='screen',
            parameters=[params, {
                'port_name': LaunchConfiguration('port'),
                'enable_angle_crop_func': crop,
            }],
        ),

        Node(
            package='tf2_ros', executable='static_transform_publisher',
            name='stl27l_static_tf', output='screen',
            condition=IfCondition(tf_on),
            arguments=[
                '--x', LaunchConfiguration('tf_x'),
                '--y', LaunchConfiguration('tf_y'),
                '--z', LaunchConfiguration('tf_z'),
                '--roll', LaunchConfiguration('tf_roll'),
                '--pitch', LaunchConfiguration('tf_pitch'),
                '--yaw', LaunchConfiguration('tf_yaw'),
                '--frame-id', 'base_link',
                '--child-frame-id', 'laser_frame',
            ],
        ),
    ])
