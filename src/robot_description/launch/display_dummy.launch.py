#!/usr/bin/env python3
# =====================================================================
#  display_dummy.launch.py - WP-0 Dummy-Anzeige
# ---------------------------------------------------------------------
#  Startet:
#    - robot_state_publisher  (publiziert TF aus der URDF)
#    - joint_state_publisher_gui optional (Gelenke per Slider bewegen)
#    - rviz2 optional
#
#  Start:
#    ros2 launch robot_description display_dummy.launch.py
#    ros2 launch robot_description display_dummy.launch.py use_rviz:=true
# =====================================================================
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import Command, LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    use_gui = LaunchConfiguration('use_gui')
    use_rviz = LaunchConfiguration('use_rviz')

    model = PathJoinSubstitution([
        FindPackageShare('robot_description'),
        'urdf',
        'mobile_manipulator_dummy.urdf.xacro'
    ])

    # ParameterValue(value_type=str) ist unter ROS 2 Humble PFLICHT:
    # ohne dies versucht launch, die URDF-XML als YAML zu parsen -> Abbruch.
    robot_description = {
        'robot_description': ParameterValue(Command(['xacro ', model]), value_type=str)
    }

    return LaunchDescription([
        DeclareLaunchArgument(
            'use_gui', default_value='true',
            description='joint_state_publisher_gui starten (Slider fuer Dummy-Gelenke)'),
        DeclareLaunchArgument(
            'use_rviz', default_value='false',
            description='RViz2 direkt mitstarten'),

        Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            name='robot_state_publisher',
            output='screen',
            parameters=[robot_description],
        ),

        Node(
            package='joint_state_publisher_gui',
            executable='joint_state_publisher_gui',
            name='joint_state_publisher_gui',
            condition=IfCondition(use_gui),
            output='screen',
        ),

        Node(
            package='rviz2',
            executable='rviz2',
            name='rviz2',
            condition=IfCondition(use_rviz),
            output='screen',
            arguments=['-f', 'base_link'],
        ),
    ])
