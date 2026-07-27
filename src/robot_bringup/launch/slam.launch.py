#!/usr/bin/env python3
# =====================================================================
#  slam.launch.py  -  RTAB-Map (RGB-D) auf dem echten Roboter
#  ====================================================================
#  Baut die Karte aus OAK-Farbbild + Tiefe und der GEMESSENEN Radodometrie.
#  Startet bewusst WEDER Nav2 NOCH einen Fahrbefehl.
#
#  TF-Besitzverhaeltnisse (genau ein Publisher je Transform):
#    RTAB-Map        -> /map  und  TF map -> odom
#    base_hardware   -> /odom und  TF odom -> base_link
#    OAK-Treiber     -> TF base_link -> oak_* (aus der Montagepose)
#    vl53-Launch     -> TF base_link -> vl53_* (hier nicht gestartet)
#  WICHTIG: nav_real.launch.py hat ein statisches map->odom als Platzhalter.
#  Es darf NICHT parallel laufen - dort static_map_odom:=false setzen.
#
#  ---------------------------------------------------------------------
#  A) Stufe 1 - ohne Motorstrom, Roboter steht (Pipelinetest):
#       ros2 launch robot_bringup slam.launch.py
#
#  B) KARTIERFAHRT - scharf, Roboter faehrt (Not-Aus in der Hand!):
#       Terminal 1:  ros2 launch robot_bringup slam.launch.py active_drive:=true
#       Terminal 2:  ros2 run teleop_twist_keyboard teleop_twist_keyboard \
#                      --ros-args -r /cmd_vel:=/cmd_vel_smoothed
#     WICHTIG: auf cmd_vel_smoothed fahren, NICHT auf /cmd_vel. Nur so laeuft
#     die Fahrt durch den collision_monitor, der vor Hindernissen bremst.
#     Langsam fahren (im teleop mit 'x'/'c' die Grenzen senken), Ecken langsam
#     umrunden - schnelle Drehungen brechen die visuelle Wiedererkennung.
#
#  !!! RTAB-MAP IMMER SAUBER BEENDEN !!!
#     Ctrl-C im Launch-Terminal, oder SIGINT an den rtabmap-Prozess, und ihm
#     dann Zeit lassen (gemessen: ~5 s). Er schreibt beim Beenden das visuelle
#     WOERTERBUCH in die Datenbank.
#     Wird er mit SIGKILL (kill -9) abgeschossen, bleibt die Datenbank ohne
#     Woerterbuch zurueck: die Karte ist geometrisch noch da, aber
#     WIEDERERKENNUNG UND LOKALISIERUNG SIND UNMOEGLICH. Symptome beim
#     naechsten Start (real passiert 27.07.2026):
#       "Not found word 1 (dict size=0)"
#       "The dictionary is empty or missing some words from nodes in WM"
#       danach hunderte "Rejected loop closure ... Not enough inliers 0/20"
#     Das laesst sich NICHT reparieren - die Karte muss neu aufgenommen werden.
#
#  C) Karte sichern (waehrend SLAM laeuft):
#       ros2 service call /robot_map_manager/save_map std_srvs/srv/Trigger
#     -> versionierter Ordner unter ~/.local/share/amadeus/maps/
#     Die RTAB-Datenbank (~/.local/share/amadeus/rtabmap.db) ist davon
#     unabhaengig und traegt die Wiedererkennung - sie ersetzt der Snapshot NICHT.
#
#  D) Karte spaeter weiterverwenden statt neu aufnehmen:
#       ros2 launch robot_bringup slam.launch.py delete_db:=false
#       ros2 launch robot_bringup slam.launch.py delete_db:=false localization:=true
#
#  Karte pruefen:  ros2 topic echo /map --once --qos-durability transient_local
#  ---------------------------------------------------------------------
#
#  HINWEIS zur Odometrie: base_hardware liest die Ist-Drehzahl nur, wenn es
#  scharf ist (dry_run=false UND allow_rs485=true). Im Stufe-1-Betrieb steht
#  die Odometrie deshalb still - das ist fuer den bewegungsfreien Aufbau- und
#  Pipelinetest richtig, taugt aber nicht zum Kartieren durch Anschieben.
# =====================================================================
import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition, UnlessCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PythonExpression
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    bringup = get_package_share_directory('robot_bringup')
    oak_launch = os.path.join(bringup, 'launch', 'oak.launch.py')
    slam_cam_params = os.path.join(bringup, 'config', 'oak_params_slam.yaml')

    base_params = os.path.join(
        get_package_share_directory('base_hardware'), 'config',
        'base_hardware_params.yaml')

    map_manager_launch = os.path.join(
        get_package_share_directory('robot_map_manager'), 'launch',
        'map_manager.launch.py')

    vl53_launch = os.path.join(
        get_package_share_directory('vl53_near_field'), 'launch',
        'vl53_near_field.launch.py')

    active_drive = LaunchConfiguration('active_drive')
    dry_run = ParameterValue(
        PythonExpression(["'", active_drive, "' != 'true'"]), value_type=bool)
    allow_rs485 = ParameterValue(
        PythonExpression(["'", active_drive, "' == 'true'"]), value_type=bool)

    # RTAB-Map: RGB-D aus der OAK + Radodometrie als Bewegungsschaetzung.
    rtabmap_params = [{
        'frame_id': 'base_link',
        'odom_frame_id': 'odom',
        'map_frame_id': 'map',
        'subscribe_depth': True,
        'subscribe_rgb': True,
        'subscribe_scan': False,
        # Bild- und Tiefenrate unterscheiden sich (26 vs 11 Hz) -> lose Kopplung
        'approx_sync': True,
        'queue_size': 30,
        'publish_tf': True,          # RTAB-Map besitzt map->odom
        'database_path': os.path.expanduser('~/.local/share/amadeus/rtabmap.db'),
        # Wie oft eine neue Karten-Stuetzstelle entsteht (Hz). Klein halten,
        # der Jetson soll nicht an der Kartierung ersticken.
        'Rtabmap/DetectionRate': '1.0',
        # Ohne Bewegung keine neuen Knoten - verhindert, dass der Stillstand
        # die Datenbank mit identischen Bildern flutet.
        'RGBD/LinearUpdate': '0.05',
        'RGBD/AngularUpdate': '0.05',
        # ---- Belegungsraster ----
        # Erste Fassung erzeugte eine schlechte Karte: 26 % belegt gegen nur
        # 7 % frei, Waende als dicke Baender, Strahlenartefakte. Zwei Ursachen:
        #  1) OHNE Strahlverfolgung wird freier Raum ueberhaupt nicht
        #     eingetragen - nur Treffer. Deshalb kaum Freiflaeche.
        #  2) Boden per fester Hoehenschwelle auszublenden scheitert bei einer
        #     Kamera auf 1.34 m mit 20 Grad Neigung: auf 3-4 m ist das
        #     Tiefenrauschen groesser als die Schwelle, der Boden wurde als
        #     Hindernis markiert.
        'Grid/FromDepth': 'true',
        'Grid/3D': 'false',                  # flaches 2D-Raster (guenstiger, reicht fuer Nav2)
        'Grid/RayTracing': 'true',           # traegt den Raum bis zum Treffer als FREI ein
        'Grid/RangeMax': '2.5',              # nur so weit, wie die Tiefe verlaesslich ist
        'Grid/NormalsSegmentation': 'true',  # Boden ueber Flaechenneigung statt fester Hoehe
        'Grid/MaxGroundAngle': '45',         # bis 45 Grad Neigung gilt als Boden
        'Grid/MaxGroundHeight': '0.15',      # grosszuegig, Normalen entscheiden
        'Grid/MaxObstacleHeight': '1.5',
        'Grid/NoiseFilteringRadius': '0.05',      # vereinzelte Ausreisser verwerfen
        'Grid/NoiseFilteringMinNeighbors': '2',
    }]

    # Nur lokalisieren = Speicher nicht mehr erweitern.
    # RTAB-Map-Parameter sind STRINGS - ohne value_type=str macht launch daraus
    # einen Bool und der Node bricht mit InvalidParameterTypeException ab.
    mem_param = {
        'Mem/IncrementalMemory': ParameterValue(
            PythonExpression(["'false' if '", LaunchConfiguration('localization'),
                              "' == 'true' else 'true'"]),
            value_type=str),
    }

    rtabmap_remaps = [
        ('rgb/image', '/oak/rgb/image_rect'),
        ('rgb/camera_info', '/oak/rgb/camera_info'),
        ('depth/image', '/oak/stereo/image_raw'),
        ('odom', '/odom'),
    ]

    return LaunchDescription([
        DeclareLaunchArgument(
            'active_drive', default_value='false',
            description='true = base_hardware SCHARF (Motoren koennen fahren, und nur '
                        'dann liefert es gemessene Odometrie). false = dry_run.'),
        DeclareLaunchArgument(
            'delete_db', default_value='true',
            description='true = neue Karte (Datenbank loeschen). false = vorhandene '
                        'Karte fortsetzen/relokalisieren.'),
        DeclareLaunchArgument(
            'localization', default_value='false',
            description='true = nur lokalisieren statt kartieren (setzt delete_db:=false '
                        'voraus).'),
        DeclareLaunchArgument(
            'map_manager', default_value='true',
            description='Kartenmanager mitstarten (speichert Karten fuer die App).'),
        DeclareLaunchArgument(
            'safety', default_value='true',
            description='VL53 + collision_monitor mitstarten. Bei active_drive:=true '
                        'ZWINGEND true - sonst faehrt der Roboter ohne Notbremse.'),

        # --- Nahbereichs-Sicherheit: VL53 + collision_monitor ---
        #     Der Monitor ist der einzige Publisher von /cmd_vel: gefahren wird
        #     auf cmd_vel_smoothed, er reicht durch oder bremst.
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(vl53_launch),
            condition=IfCondition(LaunchConfiguration('safety'))),

        # --- Kamera mit dem SLAM-Profil (640x360 fuer Bildmerkmale) ---
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(oak_launch),
            launch_arguments={'params_file': slam_cam_params}.items()),

        # --- Basis: liefert /odom + TF odom->base_link ---
        Node(package='base_hardware', executable='base_hardware',
             name='base_hardware', output='screen',
             parameters=[base_params, {
                 'publish_tf': True,
                 'dry_run': dry_run,
                 'allow_rs485': allow_rs485,
             }]),

        # --- RTAB-Map: einziger Besitzer von /map und map->odom ---
        #     Zwei Varianten, weil '--delete_db_on_start' ein Kommandozeilen-
        #     Argument ist und sich nicht per Substitution ein-/ausschalten laesst.
        Node(package='rtabmap_slam', executable='rtabmap',
             name='rtabmap', output='screen',
             condition=IfCondition(LaunchConfiguration('delete_db')),
             parameters=rtabmap_params + [mem_param],
             remappings=rtabmap_remaps,
             arguments=['--delete_db_on_start']),
        Node(package='rtabmap_slam', executable='rtabmap',
             name='rtabmap', output='screen',
             condition=UnlessCondition(LaunchConfiguration('delete_db')),
             parameters=rtabmap_params + [mem_param],
             remappings=rtabmap_remaps),

        # --- Kartenmanager: speichert /map versioniert fuer die iPhone-App ---
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(map_manager_launch),
            condition=IfCondition(LaunchConfiguration('map_manager'))),
    ])
