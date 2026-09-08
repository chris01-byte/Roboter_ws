"""Opt-in footplate TF inspection, without sensor, base, EKF or OAK nodes."""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
import yaml

from robot_state_estimation.hwt601_mount import mount_pose


def _mount(context):
    filename = LaunchConfiguration('config').perform(context)
    with open(filename, encoding='utf-8') as source:
        config = yaml.safe_load(source)
    translation, rotation = mount_pose(config)
    arguments = []
    for name, value in zip(('x', 'y', 'z', 'qx', 'qy', 'qz', 'qw'),
                           (*translation, *rotation)):
        arguments.extend([f'--{name}', str(value)])
    arguments.extend(['--frame-id', config['parent_frame'],
                      '--child-frame-id', config['mount_frame']])
    return [Node(package='tf2_ros', executable='static_transform_publisher',
                 name='hwt601_mount_reference', output='screen',
                 arguments=arguments)]


def generate_launch_description():
    share = get_package_share_directory('robot_state_estimation')
    return LaunchDescription([
        DeclareLaunchArgument('config', default_value=os.path.join(
            share, 'config', 'hwt601_mount.yaml')),
        OpaqueFunction(function=_mount),
    ])
