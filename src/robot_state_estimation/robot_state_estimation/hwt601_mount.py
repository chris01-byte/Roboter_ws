"""Nominal footplate reference only; never invent an internal IMU origin."""

import math


def mount_pose(config):
    if (config['parent_frame'], config['mount_frame']) != (
            'base_link', 'hwt601_mount'):
        raise ValueError('Only base_link -> hwt601_mount is supported')
    if tuple(config[f'sensor_{axis}_direction'] for axis in 'xyz') != (
            'right', 'forward', 'up'):
        raise ValueError('Mounting axes differ from the confirmed installation')
    names = ('housing_center_forward_of_axle_m',
             'housing_center_left_of_centerline_m',
             'footplate_height_above_ground_m',
             'base_link_height_above_ground_m')
    values = [float(config[name]) for name in names]
    if not all(math.isfinite(value) for value in values):
        raise ValueError('Mount dimensions must be finite')
    x, y, foot_z, base_z = values
    if (abs(x) > 0.5 or abs(y) > 0.5
            or not 0 <= foot_z <= 0.5 or not 0 < base_z <= 0.5):
        raise ValueError('Implausible chassis dimensions; check metres vs mm')
    if config.get('fusion_approved') is not False:
        raise ValueError('Footplate geometry is not a fusion approval')
    quaternion = (0.0, 0.0, -math.sqrt(0.5), math.sqrt(0.5))
    return (x, y, foot_z - base_z), quaternion
