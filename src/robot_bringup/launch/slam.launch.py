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
#     RTAB-Map schreibt das visuelle WOERTERBUCH erst beim Herunterfahren in die
#     Datenbank. Fehlt es, ist die Karte geometrisch noch da, aber
#     WIEDERERKENNUNG UND LOKALISIERUNG SIND UNMOEGLICH:
#       "Not found word 1 (dict size=0)"
#       "The dictionary is empty or missing some words from nodes in WM"
#       danach hunderte "Rejected loop closure ... Not enough inliers 0/20"
#     Das laesst sich NICHT reparieren - die Karte muss neu aufgenommen werden.
#
#     SO BEENDEN:  Ctrl-C im Launch-Terminal, oder von aussen
#         kill -INT <PID des ros2-launch-Prozesses>
#     und dann warten, bis der rtabmap-Prozess von selbst verschwunden ist
#     (dauert mit der Kartengroesse an, gemessen 5 s und mehr).
#
#     ZWEI FALLEN, beide am 27.07.2026 real aufgetreten:
#     1) NICHT die Prozessgruppe signalisieren ("kill -INT -<PGID>"). rtabmap
#        bekaeme SIGINT dann doppelt: einmal direkt vom Kernel, einmal
#        weitergereicht von launch. Das erste startet das Speichern, das zweite
#        bricht es ab. Ergebnis: "process has died ... exit code -2", Datenbank
#        mit 831 Knoten und 0 Woertern. SIGKILL ist also nicht die einzige
#        Ursache - ein gut gemeintes SIGINT an die Gruppe reicht schon.
#     2) launch eskaliert nach SIGINT selbsttaetig auf SIGTERM und SIGKILL,
#        nach je 5 s Vorgabe. Das ist knapper als der Speichervorgang. Deshalb
#        beim Start grosszuegige Fristen mitgeben:
#            ros2 launch robot_bringup slam.launch.py \
#                sigterm_timeout:=120 sigkill_timeout:=180 ...
#        (In Humble sind das Launch-Konfigurationen, KEINE ros2-launch-Optionen.)
#
#     KONTROLLE, ob es geklappt hat - muss > 0 sein:
#       sqlite3 ~/.local/share/amadeus/rtabmap.db "SELECT COUNT(*) FROM Word;"
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
        # ACHTUNG bei der Fehlersuche: Mit Grid/3D=false publiziert RTAB-Map KEINE
        # /cloud_ground - die Wolke ist dann leer, obwohl die Bodenerkennung
        # einwandfrei arbeitet. Am 28.07.2026 habe ich das als "erkennt keinen
        # Boden mehr" fehlgedeutet. Zum Pruefen kurzzeitig Grid/3D=true setzen,
        # dann trennen /cloud_ground (bis +0.10 m) und /cloud_obstacles (ab
        # +0.11 m) sauber an der Schwelle.
        'Grid/RayTracing': 'true',           # traegt den Raum bis zum Treffer als FREI ein
        # Reichweite der Kartierung. Stand 2.5, war der Hauptgrund dafuer, dass die
        # Karte vom 27.07. nur 17.7 % Freiflaeche zeigte: Um den Fahrweg entstand
        # ein runder "Sichthorizont" bei 2.5 m statt der eckigen Raumwaende.
        # 4.0 ist gedeckt - die Nav2-Costmap arbeitet laengst mit obstacle_max_range
        # 4.0, und die Messung vom 26.07. ergab im Ring 3-4 m nur 0.1 % der Punkte
        # unter der Filtergrenze (Median +0.82 m) = echte Objekte, kein Bodenrauschen.
        # Der Bodenfehler waechst mit der Entfernung (1.06 Grad Neigung = 26 mm auf
        # 2.5 m, rund 42 mm auf 4 m) und bleibt damit klar unter MaxGroundHeight 0.15.
        'Grid/RangeMax': '4.0',
        # ---- Bodenerkennung: feste Hoehenschwelle, am 28.07.2026 nachgemessen ----
        # Die Rohwolke der OAK liefert sauberen Boden: auf 1-2 m liegen 73.8 % der
        # Punkte auf Bodenhoehe (Median -0.05 m, erwartet -0.09 m), auf 3-4 m nur
        # 8.5 % - dort stehen echte Waende, kein Rauschen. Die Schwelle trennt das
        # nachweislich sauber: /cloud_ground reicht bis +0.10 m, /cloud_obstacles
        # beginnt bei +0.11 m (gemessen mit Grid/3D=true).
        # Vorher stand hier NormalsSegmentation=true mit der Begruendung, eine feste
        # Schwelle scheitere auf 3-4 m am Tiefenrauschen - die Messung stuetzt das
        # nicht. Beide Varianten liefern ein aehnlich volles Raster; die kleine
        # Freiflaeche kommt NICHT von der Bodenerkennung, sondern daher, dass der
        # Roboter zu wenig Strecke macht (RayTracing traegt nur frei ein, wo die
        # Kamera hinsieht - und sie sieht Boden erst ab 1.6 m).
        'Grid/NormalsSegmentation': 'false',
        'Grid/MaxGroundHeight': '0.10',      # Boden liegt bei -0.09 -> 0.19 m Abstand
        'Grid/MaxGroundAngle': '45',         # ohne Wirkung bei NormalsSegmentation=false
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
        # Ohne Vorwissen anfangen. Normalerweise laedt RTAB-Map beim Start die
        # zuletzt gespeicherte Pose - dann steht der Roboter sofort "richtig" in
        # der Karte, ganz ohne etwas wiedererkannt zu haben. Fuer einen ehrlichen
        # Lokalisierungstest muss dieses Vorwissen weg: Der Roboter beginnt am
        # Kartenursprung und muss sich seine Position selbst erarbeiten.
        'RGBD/StartAtOrigin': ParameterValue(
            LaunchConfiguration('start_at_origin'), value_type=str),
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
            'start_at_origin', default_value='false',
            description='true = RTAB-Map startet am Kartenursprung statt an der zuletzt '
                        'gespeicherten Pose. Fuer den ehrlichen Lokalisierungstest '
                        '("kidnapped robot"): nur so muss sich der Roboter seine Position '
                        'wirklich selbst erarbeiten.'),
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
