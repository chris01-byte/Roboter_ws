#!/usr/bin/env python3
# =====================================================================
#  vl53_near_field.launch.py   (WP-1b)
#  Startet:
#    1) vl53_near_field            (Sensoren -> PointCloud2 + Status)
#    2) zwei statische TFs         (Montagepose der Sensoren - PLATZHALTER!)
#    3) nav2_collision_monitor     (reaktive Stop-/Slowdown-Zonen)
#    4) lifecycle_manager          (aktiviert den collision_monitor)
#
#  Start:  ros2 launch vl53_near_field vl53_near_field.launch.py
#
#  HINWEIS: In der Produktion gehoeren collision_monitor + Lifecycle in dein
#  zentrales Nav2-Bringup. Hier sind sie der Bequemlichkeit halber dabei,
#  damit WP-1b eigenstaendig testbar ist.
# =====================================================================
import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    pkg = get_package_share_directory('vl53_near_field')
    vl53_params = os.path.join(pkg, 'config', 'vl53_params.yaml')
    collision_params = os.path.join(pkg, 'config', 'collision_monitor_params.yaml')

    # 1) VL53-Node
    vl53_node = Node(
        package='vl53_near_field',
        executable='vl53_near_field',
        name='vl53_near_field',
        output='screen',
        parameters=[vl53_params],
    )

    # 2) Statische Transforms base_link -> vl53_*_link
    #    Arg-Reihenfolge: x y z yaw pitch roll parent child   (Winkel in rad)
    #    GEMESSEN 24.07.2026 am aufgebauten Roboter:
    #    - x=0.29 m vor der Antriebsrad-Achse (base_link x=0)
    #    - y=+/-0.095 m von der Mittellinie (links +, rechts -)
    #    - z=0.215 m ueber base_link (= 0.305 m ueber Boden minus 0.09 m base_link-Hoehe)
    #    - yaw=pitch=roll=0: beide schauen gerade nach vorn (kein Winkelversatz)
    #
    #    ABSCHALTBAR (publish_sensor_tf:=false): Dieselben Frames stehen auch in
    #    der URDF (robot_description). Sobald ein robot_state_publisher mit der
    #    URDF laeuft, wuerden ZWEI Quellen denselben Transform publizieren - das
    #    ist unzulaessig. Dann diese hier abschalten. Solange kein
    #    robot_state_publisher laeuft (aktueller Stand von robot.launch.py und
    #    nav_real.launch.py), sind sie die einzige Quelle und muessen an bleiben.
    publish_sensor_tf = LaunchConfiguration('publish_sensor_tf')
    tf_left = Node(
        package='tf2_ros', executable='static_transform_publisher',
        name='tf_vl53_left', output='screen',
        condition=IfCondition(publish_sensor_tf),
        arguments=['0.29', '0.095', '0.215', '0', '0', '0', 'base_link', 'vl53_left_link'],
    )
    tf_right = Node(
        package='tf2_ros', executable='static_transform_publisher',
        name='tf_vl53_right', output='screen',
        condition=IfCondition(publish_sensor_tf),
        arguments=['0.29', '-0.095', '0.215', '0', '0', '0', 'base_link', 'vl53_right_link'],
    )

    # 3) Reaktive Hindernisvermeidung (Lifecycle-Node)
    collision_monitor = Node(
        package='nav2_collision_monitor', executable='collision_monitor',
        name='collision_monitor', output='screen',
        parameters=[collision_params],
    )

    # 4) Lifecycle-Manager aktiviert den collision_monitor automatisch
    lifecycle_mgr = Node(
        package='nav2_lifecycle_manager', executable='lifecycle_manager',
        name='lifecycle_manager_collision', output='screen',
        parameters=[{'autostart': True, 'node_names': ['collision_monitor']}],
    )

    return LaunchDescription([
        DeclareLaunchArgument(
            'publish_sensor_tf', default_value='true',
            description='Statische TFs base_link->vl53_*_link publizieren. Auf false '
                        'setzen, sobald ein robot_state_publisher dieselben Frames aus '
                        'der URDF liefert - sonst zwei Publisher fuer denselben TF.'),
        vl53_node, tf_left, tf_right, collision_monitor, lifecycle_mgr])
