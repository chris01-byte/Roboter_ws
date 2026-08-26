#!/usr/bin/env python3
# =====================================================================
#  oak.launch.py  -  OAK-Tiefenkamera am Roboter (depthai_ros_driver)
#  ====================================================================
#  Startet den Treiber MIT der realen Montagepose, so dass er seine
#  komplette TF-Kette direkt unter base_link haengt. Dadurch landen
#  /oak/points und /oak/stereo/... in einem Frame, den Nav2 verwenden
#  kann - ohne separaten static_transform_publisher.
#
#  Start:            ros2 launch robot_bringup oak.launch.py
#  ohne Punktwolke:  ros2 launch robot_bringup oak.launch.py pointcloud:=false
#
#  Topics: /oak/points (PointCloud2), /oak/stereo/image_raw (Tiefe),
#          /oak/rgb/image_raw, /oak/imu/data
#
#  ---------------------------------------------------------------------
#  KAMERAWECHSEL (OAK-D-S2 -> OAK 4 D Pro Wide FF):
#    Das Modell wird vom Geraet AUTOMATISCH erkannt. Zu tun ist nur:
#      1) neue Kamera anstecken
#      2) MONTAGEPOSE unten pruefen/anpassen (andere Bauform = andere Lage)
#      3) ggf. Aufloesungen in config/oak_params.yaml anpassen
#    Sonst nichts - Frames, Kalibrierung und Topics kommen aus dem Geraet.
#  ---------------------------------------------------------------------
# =====================================================================
import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import LoadComposableNodes, Node
from launch_ros.descriptions import ComposableNode

# =====================================================================
#  >>> MONTAGEPOSE DER KAMERA  -  EINZIGE STELLE ZUM AENDERN <<<
#  GEMESSEN 26.07.2026 am aufgebauten Roboter, bezogen auf base_link:
#    base_link: x=0 an der Antriebsrad-Achse, y=0 Mittellinie,
#               z=0 auf 9 cm ueber dem Boden (halbe Chassis-Hoehe).
#    Gemessen wurde: x=150 mm, y=mittig, z=1340 mm ueber BODEN,
#    20 Grad nach vorn/unten geneigt.
#  -> z gegenueber base_link = 1.340 - 0.090 = 1.250 m
#  Diese Werte gehoeren auch in robot_description (URDF) - dort stehen
#  sie fuer RViz/MoveIt, hier fuer den realen TF-Baum des Treibers.
# =====================================================================
CAM_POS_X = '0.15'      # [m] vor der Antriebsrad-Achse
CAM_POS_Y = '0.0'       # [m] mittig
CAM_POS_Z = '1.25'      # [m] ueber base_link (= 1.34 m ueber Boden)
CAM_ROLL = '0.0'        # [rad]
# [NACHGEMESSEN 27.07.2026] Aus der Bodenebene der Punktwolke bestimmt:
# mit 20.0 Grad stieg der gemessene Boden ueber die Entfernung an
# (-0.083 m bei 1.5 m, -0.064 m bei 2.5 m statt konstant -0.090), Steigung
# +1.06 Grad. Daher 18.94 statt 20.0 Grad. Der Effekt ist klein (26 mm auf
# 2.5 m) und war NICHT die Ursache der dicken Hindernisbaender - der Boden
# wird ohnehin korrekt ausgefiltert (66.5 % der Punkte als Boden erkannt).
# Vorbehalt: ein Teil davon kann auch echte Bodenneigung im Raum sein.
CAM_PITCH = '0.3306'    # [rad] = 18.94 Grad nach unten geneigt
CAM_YAW = '0.0'         # [rad] geradeaus nach vorn
PARENT_FRAME = 'base_link'


def generate_launch_description():
    bringup = get_package_share_directory('robot_bringup')
    params = os.path.join(bringup, 'config', 'oak_params.yaml')
    semantic_perception = get_package_share_directory('semantic_perception')
    relay_params = os.path.join(
        semantic_perception, 'config', 'semantic_stream_relay_params.yaml')
    depthai = get_package_share_directory('depthai_ros_driver')

    pointcloud = LaunchConfiguration('pointcloud')
    semantic_relay = LaunchConfiguration('semantic_relay')
    external_rectifier = LaunchConfiguration('external_rectifier')

    # Gemeinsame Argumente fuer beide Treiber-Launches
    common = {
        'params_file': LaunchConfiguration('params_file'),
        'parent_frame': LaunchConfiguration('parent_frame'),
        'cam_pos_x': LaunchConfiguration('cam_pos_x'),
        'cam_pos_y': LaunchConfiguration('cam_pos_y'),
        'cam_pos_z': LaunchConfiguration('cam_pos_z'),
        'cam_roll': LaunchConfiguration('cam_roll'),
        'cam_pitch': LaunchConfiguration('cam_pitch'),
        'cam_yaw': LaunchConfiguration('cam_yaw'),
        # Der eingebaute Rectifier teilt sonst den single-threaded Container
        # mit dem OAK-Treiber. Entzerrung laeuft unten separat und ohne die im
        # Dauertest ebenfalls ausgefallene image_transport-CameraSubscriber-
        # Zeitstempelsynchronisierung.
        'rectify_rgb': 'false',
    }

    return LaunchDescription([
        DeclareLaunchArgument('params_file', default_value=params),
        DeclareLaunchArgument('pointcloud', default_value='true',
                              description='true = mit /oak/points (fuer Nav2-Costmap)'),
        DeclareLaunchArgument(
            'semantic_relay', default_value='true',
            description='Komprimierten 2-Hz-RGB-D-Strom fuer den KI-Server starten.'),
        DeclareLaunchArgument(
            'semantic_relay_params', default_value=relay_params),
        DeclareLaunchArgument(
            'external_rectifier', default_value='true',
            description='RGB in einem getrennten Prozess entzerren.'),
        DeclareLaunchArgument('parent_frame', default_value=PARENT_FRAME),
        DeclareLaunchArgument('cam_pos_x', default_value=CAM_POS_X),
        DeclareLaunchArgument('cam_pos_y', default_value=CAM_POS_Y),
        DeclareLaunchArgument('cam_pos_z', default_value=CAM_POS_Z),
        DeclareLaunchArgument('cam_roll', default_value=CAM_ROLL),
        DeclareLaunchArgument('cam_pitch', default_value=CAM_PITCH),
        DeclareLaunchArgument('cam_yaw', default_value=CAM_YAW),

        # --- Treiber (Bilder, Tiefe, IMU, TF) ---
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(depthai, 'launch', 'camera.launch.py')),
            launch_arguments=common.items()),

        # Eigener Prozess: CameraInfo ist eine stabile Kalibrierung und muss
        # nicht fuer jedes Bild einen identischen Zeitstempel tragen. Der
        # Standard-image_proc-CameraSubscriber verlor im Realtest nach rund
        # acht Minuten dauerhaft nur seinen RGB-Eingang, obwohl image_raw mit
        # 10,0 Hz weiterlief. Dieser Node verwendet deshalb zwei unabhaengige
        # Best-Effort/KEEP_LAST(1)-Subscriptions.
        Node(
            package='robot_bringup',
            executable='oak_rectifier',
            name='oak_rectifier',
            output='screen',
            condition=IfCondition(external_rectifier),
        ),

        # Der KI-Server abonniert niemals die unkomprimierten OAK-Topics.
        # Das lokale Relay verwirft alte Frames statt per Reliable-DDS
        # Rueckstau bis in image_proc/DepthAI zu erzeugen.
        Node(
            package='semantic_perception',
            executable='semantic_stream_relay',
            name='semantic_stream_relay',
            output='screen',
            condition=IfCondition(semantic_relay),
            parameters=[LaunchConfiguration('semantic_relay_params')],
        ),

        # --- Punktwolke fuer die Nav2-Costmap ---
        # BEWUSST PointCloudXyz (nur Tiefe + camera_info), NICHT das
        # PointCloudXyzi aus depthai's pointcloud.launch.py: jenes braucht
        # zusaetzlich /oak/right/image_rect als Intensitaetsbild. Dieses Bild
        # haengt an der MONO-Aufloesung und skaliert NICHT mit der ISP-Groesse
        # von RGB/Tiefe mit - bei 320x180 Tiefe und 1280x720 Intensitaet
        # rekonstruiert es voellig falsche 3D-Punkte (getestet 26.07.2026:
        # Punkte 5 m seitlich bei 2 m Tiefe). Farbe/Intensitaet braucht eine
        # Costmap ohnehin nicht - so ist es entkoppelt, leichter und spart
        # USB-Bandbreite.
        LoadComposableNodes(
            target_container='oak_container',
            condition=IfCondition(pointcloud),
            composable_node_descriptions=[
                ComposableNode(
                    package='depth_image_proc',
                    plugin='depth_image_proc::PointCloudXyzNode',
                    name='oak_point_cloud_xyz',
                    remappings=[
                        ('image_rect', 'oak/stereo/image_raw'),
                        ('camera_info', 'oak/stereo/camera_info'),
                        ('points', 'oak/points'),
                    ]),
            ]),
    ])
