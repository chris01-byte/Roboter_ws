#!/usr/bin/env python3
# =====================================================================
#  nav_real.launch.py  -  Nav2 auf REALER Hardware (VL53-Umfahrung)
#  ====================================================================
#  Geschlossener Navigationskreis mit ECHTER Basis + VL53-Sensorik:
#    Nav2 plant/regelt -> cmd_vel_nav_raw -> mission_cmd_vel_gate
#    -> cmd_vel_nav -> velocity_smoother
#    -> cmd_vel_smoothed -> collision_monitor -> /cmd_vel -> base_hardware
#    -> Motoren -> gemessene Odometrie (/odom + TF
#    odom->base_link) -> Nav2 sieht die Bewegung. Reale VL53-Hindernisse
#    landen im obstacle_layer beider Costmaps -> Nav2 plant drumherum.
#
#  Lokalisierung: map->odom als statische Identitaet (kein SLAM/AMCL) -
#  reicht fuer Relativ-Ziele in einer leeren Karte.
#
#  Start (GESTUFT!):
#    Stufe 1 (kein Motorstrom, Costmap/Planung pruefen):
#      ros2 launch robot_navigation nav_real.launch.py
#    Stufe 2 (SCHARF, Roboter faehrt - aufgebockt/freie Flaeche, Not-Aus!):
#      ros2 launch robot_navigation nav_real.launch.py active_drive:=true
#
#  Ziel senden:
#    ros2 action send_goal /navigate_to_pose nav2_msgs/action/NavigateToPose \
#      "{pose: {header: {frame_id: map}, pose: {position: {x: 1.0}, \
#       orientation: {w: 1.0}}}}"
#
#  Voraussetzung: ros-humble-navigation2; base_hardware + vl53_near_field gebaut.
# =====================================================================
import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PythonExpression
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    nav_pkg = get_package_share_directory('robot_navigation')
    params = os.path.join(nav_pkg, 'config', 'nav2_params_real.yaml')
    default_map = os.path.join(nav_pkg, 'maps', 'leer.yaml')

    base_pkg = get_package_share_directory('base_hardware')
    base_params = os.path.join(base_pkg, 'config', 'base_hardware_params.yaml')

    vl53_launch = os.path.join(
        get_package_share_directory('vl53_near_field'), 'launch',
        'vl53_near_field.launch.py')

    oak_launch = os.path.join(
        get_package_share_directory('robot_bringup'), 'launch', 'oak.launch.py')

    map_yaml = LaunchConfiguration('map')
    active_drive = LaunchConfiguration('active_drive')
    static_map_odom_x = LaunchConfiguration('static_map_odom_x')
    static_map_odom_y = LaunchConfiguration('static_map_odom_y')
    static_map_odom_yaw = LaunchConfiguration('static_map_odom_yaw')

    # active_drive steuert den Basis-Modus:
    #   false -> dry_run=true,  allow_rs485=false  (Stufe 1, kein Motorstrom)
    #   true  -> dry_run=false, allow_rs485=true   (Stufe 2, scharf)
    dry_run = ParameterValue(
        PythonExpression(["'", active_drive, "' != 'true'"]), value_type=bool)
    allow_rs485 = ParameterValue(
        PythonExpression(["'", active_drive, "' == 'true'"]), value_type=bool)

    nav_nodes = ['controller_server', 'planner_server',
                 'behavior_server', 'bt_navigator', 'velocity_smoother']

    # Nav2-Regler vor dem collision_monitor glaetten. Der Monitor bleibt die
    # letzte Instanz vor /cmd_vel und kann deshalb unverzoegert stoppen.
    nav_cmd_remap = [('cmd_vel', 'cmd_vel_nav_raw')]
    smoother_cmd_remap = [('cmd_vel', 'cmd_vel_nav'),
                          ('cmd_vel_smoothed', 'cmd_vel_smoothed')]

    return LaunchDescription([
        DeclareLaunchArgument('map', default_value=default_map,
                              description='Karten-YAML (Default: leere Karte)'),
        DeclareLaunchArgument(
            'static_map_odom', default_value='true',
            description='Statisches map->odom als Platzhalter-Lokalisierung. ZWINGEND '
                        'false, sobald SLAM (RTAB-Map) oder AMCL laeuft - die sind dann '
                        'die einzige Quelle fuer diesen Transform.'),
        DeclareLaunchArgument(
            'static_map_odom_x', default_value='0.0',
            description='Nur Platzhalter-Lokalisierung: Startpose x im map-Frame.'),
        DeclareLaunchArgument(
            'static_map_odom_y', default_value='0.0',
            description='Nur Platzhalter-Lokalisierung: Startpose y im map-Frame.'),
        DeclareLaunchArgument(
            'static_map_odom_yaw', default_value='0.0',
            description='Nur Platzhalter-Lokalisierung: Startpose yaw [rad].'),
        DeclareLaunchArgument('oak', default_value='true',
                              description='OAK-Tiefenkamera mitstarten (Fernsicht '
                                          'fuer den obstacle_layer).'),
        DeclareLaunchArgument('active_drive', default_value='false',
                              description='true = base_hardware SCHARF (Motoren '
                                          'fahren!). false = dry_run (Stufe-1-Test).'),

        # --- Karte + "Lokalisierung" ---
        Node(package='nav2_map_server', executable='map_server',
             name='map_server', output='screen',
             parameters=[params, {'yaml_filename': map_yaml}]),
        # map->odom als statische Identitaet: nur ein PLATZHALTER, solange weder
        # SLAM noch AMCL laufen. Er behauptet, der Roboter driftet nie - fuer
        # kurze Relativfahrten in leerer Karte vertretbar.
        # ZWINGEND static_map_odom:=false setzen, sobald RTAB-Map oder AMCL
        # laeuft: die publizieren map->odom selbst, und zwei Publisher fuer
        # denselben Transform sind unzulaessig (Lokalisierung springt).
        Node(package='tf2_ros', executable='static_transform_publisher',
             name='tf_map_odom', output='screen',
             condition=IfCondition(LaunchConfiguration('static_map_odom')),
             arguments=[static_map_odom_x, static_map_odom_y, '0',
                        static_map_odom_yaw, '0', '0', 'map', 'odom']),

        # --- Echte Basis: base_hardware (dry_run/scharf via active_drive) ---
        Node(package='base_hardware', executable='base_hardware',
             name='base_hardware', output='screen',
             parameters=[base_params, {
                 'publish_tf': True,
                 'dry_run': dry_run,
                 'allow_rs485': allow_rs485,
             }]),

        # --- VL53-Kette: Punktwolken (obstacle_layer) + collision_monitor (Backstop) ---
        IncludeLaunchDescription(PythonLaunchDescriptionSource(vl53_launch)),

        # --- OAK-Tiefenkamera: Fernsicht fuer den obstacle_layer ---
        #     Optional abschaltbar (oak:=false), z.B. wenn die Kamera fehlt.
        IncludeLaunchDescription(PythonLaunchDescriptionSource(oak_launch),
                                 condition=IfCondition(LaunchConfiguration('oak'))),

        # Fail-closed: Ein verspaetet angenommenes/verwaistes Nav2-Unterziel
        # darf nach terminalem Missionsstatus keine Bewegung mehr ausloesen.
        Node(package='robot_navigation', executable='cmd_vel_mission_gate',
             name='cmd_vel_mission_gate', output='screen'),

        # --- Nav2-Kern (Regler + Behavior -> cmd_vel_nav_raw) ---
        Node(package='nav2_controller', executable='controller_server',
             name='controller_server', output='screen',
             parameters=[params], remappings=nav_cmd_remap),
        Node(package='nav2_planner', executable='planner_server',
             name='planner_server', output='screen', parameters=[params]),
        Node(package='nav2_behaviors', executable='behavior_server',
             name='behavior_server', output='screen',
             parameters=[params], remappings=nav_cmd_remap),
        Node(package='nav2_bt_navigator', executable='bt_navigator',
             name='bt_navigator', output='screen', parameters=[params]),
        Node(package='nav2_velocity_smoother', executable='velocity_smoother',
             name='velocity_smoother', output='screen',
             parameters=[params], remappings=smoother_cmd_remap),

        # --- Lifecycle: erst Karte, dann Navigation ---
        Node(package='nav2_lifecycle_manager', executable='lifecycle_manager',
             name='lifecycle_manager_localization', output='screen',
             parameters=[{'autostart': True, 'node_names': ['map_server']}]),
        Node(package='nav2_lifecycle_manager', executable='lifecycle_manager',
             name='lifecycle_manager_navigation', output='screen',
             parameters=[{'autostart': True, 'node_names': nav_nodes}]),
    ])
