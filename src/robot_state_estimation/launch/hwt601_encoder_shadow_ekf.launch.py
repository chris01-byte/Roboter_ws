#!/usr/bin/env python3
"""Start only the passive HWT601/encoder shadow EKF."""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    package_share = get_package_share_directory('robot_state_estimation')
    config = os.path.join(
        package_share, 'config', 'ekf_hwt601_encoder_shadow.yaml')
    use_sim_time = ParameterValue(
        LaunchConfiguration('use_sim_time'), value_type=bool)

    return LaunchDescription([
        DeclareLaunchArgument('use_sim_time', default_value='false'),
        Node(
            package='robot_localization',
            executable='ekf_node',
            name='hwt601_encoder_shadow_ekf',
            output='screen',
            parameters=[config, {'use_sim_time': use_sim_time}],
            remappings=[
                ('odometry/filtered', '/shadow/hwt601/odom'),
                ('/diagnostics', '/shadow/hwt601/diagnostics/ekf'),
                # robot_localization advertises a TF endpoint even with
                # publish_tf=false.  Keep that endpoint out
                # of the production TF graph and observable in this sandbox.
                ('/tf', '/shadow/hwt601/tf_unused'),
                ('/tf_static', '/shadow/hwt601/tf_static_unused'),
                ('set_pose', '/shadow/hwt601/set_pose'),
                ('toggle_filter_processing',
                 '/shadow/hwt601/toggle_filter_processing'),
            ],
        ),
    ])
