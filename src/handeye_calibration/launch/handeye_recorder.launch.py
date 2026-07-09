#!/usr/bin/env python3
# =====================================================================
#  handeye_recorder.launch.py  -  Messpaar-Aufnahme (Konzept-Stufe D)
# ---------------------------------------------------------------------
#  Startet den Recorder mit config/handeye_params.yaml.
#
#  WICHTIG: Im Vordergrund-Terminal starten (Tastatur-Bedienung!):
#    ros2 launch handeye_calibration handeye_recorder.launch.py
#
#  Voraussetzungen (siehe KONZEPT_KALIBRIERUNG_OAK_ARM.md, Stufen A-C):
#    - /joint_states + robot_state_publisher (TF base_link -> tool0)
#    - OAK-Treiber mit Bild + CameraInfo
#    - ChArUco-Board starr am Flansch
# =====================================================================
import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    pkg = get_package_share_directory('handeye_calibration')
    params = os.path.join(pkg, 'config', 'handeye_params.yaml')

    return LaunchDescription([
        Node(
            package='handeye_calibration',
            executable='handeye_recorder',
            name='handeye_recorder',
            output='screen',
            emulate_tty=True,          # damit print()-Ausgaben sofort sichtbar sind
            parameters=[params],
        )
    ])
