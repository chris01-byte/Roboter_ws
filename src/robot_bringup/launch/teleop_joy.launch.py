#!/usr/bin/env python3
# =====================================================================
#  teleop_joy.launch.py  -  Handsteuerung per DualShock-Controller
#  ====================================================================
#  Startet joy_node (liest den Controller) und teleop_twist_joy
#  (macht daraus Fahrbefehle).
#
#  GEFAHREN WIRD AUF cmd_vel_smoothed, NICHT auf /cmd_vel:
#  Nur so laeuft die Fahrt durch den nav2_collision_monitor, der vor
#  Hindernissen bremst. Wer direkt auf /cmd_vel steuert, faehrt ohne Notbremse.
#
#  TOTMANNSCHALTER: Ohne gedrueckte L1-Taste wird nichts gesendet. Loslassen
#  heisst anhalten. L1+R1 zusammen ist der Schnellgang.
#
#  Benutzung zusammen mit der Kartierung:
#     Terminal 1:  ros2 launch robot_bringup slam.launch.py active_drive:=true
#     Terminal 2:  ros2 launch robot_bringup teleop_joy.launch.py
#
#  Hinweis: Der collision_monitor schweigt nach einem Stopp (stop_pub_timeout
#  2 s). Dass nach dem Anhalten nichts mehr auf /cmd_vel steht, ist normal.
# =====================================================================
import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    params = os.path.join(
        get_package_share_directory('robot_bringup'), 'config', 'teleop_joy.yaml')

    return LaunchDescription([
        DeclareLaunchArgument(
            'joy_dev', default_value='0',
            description='Nummer des Joystick-Geraets (/dev/input/js<N>).'),
        DeclareLaunchArgument(
            'cmd_topic', default_value='/cmd_vel_smoothed',
            description='Ziel-Topic. Vorgabe geht durch den collision_monitor. '
                        'NUR fuer Notfaelle auf /cmd_vel umstellen - das umgeht '
                        'die Notbremse.'),

        Node(package='joy', executable='joy_node', name='joy_node',
             output='screen',
             parameters=[{
                 'device_id': LaunchConfiguration('joy_dev'),
                 # Ruhelage-Toleranz. 0.10 war zu knapp: Der DualShock liefert in
                 # Neutralstellung keine exakte Null, der Roboter kroch dann
                 # gelegentlich von selbst los (28.07.2026 beobachtet). Mit
                 # abgeschaltetem Totmannschalter ist das besonders unangenehm,
                 # weil nichts anderes mehr die Fahrt unterbindet.
                 'deadzone': 0.20,
                 # Wiederholrate: base_hardware hat einen Fahrbefehl-Watchdog,
                 # ein einmaliger Stickausschlag wuerde sonst verhungern.
                 'autorepeat_rate': 20.0,
             }]),

        Node(package='teleop_twist_joy', executable='teleop_node',
             name='teleop_twist_joy_node', output='screen',
             parameters=[params],
             remappings=[('/cmd_vel', LaunchConfiguration('cmd_topic'))]),
    ])
