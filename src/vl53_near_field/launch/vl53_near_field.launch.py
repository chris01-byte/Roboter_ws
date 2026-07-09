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
    #    !!! PLATZHALTER-WERTE !!! Bitte an die reale Montage anpassen:
    #    - Sensoren leicht NACH INNEN gedreht, damit sich die FOV mittig trifft.
    #    - linker Sensor (+y) dreht nach rechts/innen  -> yaw negativ
    #    - rechter Sensor (-y) dreht nach links/innen   -> yaw positiv
    tf_left = Node(
        package='tf2_ros', executable='static_transform_publisher',
        name='tf_vl53_left', output='screen',
        arguments=['0.20', '0.10', '0.10', '-0.35', '0', '0', 'base_link', 'vl53_left_link'],
    )
    tf_right = Node(
        package='tf2_ros', executable='static_transform_publisher',
        name='tf_vl53_right', output='screen',
        arguments=['0.20', '-0.10', '0.10', '0.35', '0', '0', 'base_link', 'vl53_right_link'],
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

    return LaunchDescription([vl53_node, tf_left, tf_right, collision_monitor, lifecycle_mgr])
