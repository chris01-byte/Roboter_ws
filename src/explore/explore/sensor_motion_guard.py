"""Actual LiDAR-hit check for the padded body's full stationary sweep.

This is an extra rejection check, not evidence of free space. The downstream
collision monitor owns continuous LiDAR/VL53 braking. Invalid rays never grant
observed-map credit; the physical sensor coverage remains an operating limit.
"""
import math

import numpy as np


def scan_sweep_clear(scan, mount, bounds, center_deviation_m=0.):
    ranges = np.asarray(scan['ranges'], dtype=float)
    valid = (np.isfinite(ranges) & (ranges > 0)
             & (ranges >= scan['range_min']) & (ranges <= scan['range_max']))
    if not np.any(valid):
        raise ValueError('sensor_scan_no_valid_returns')
    angles = scan['angle_min'] + np.nonzero(valid)[0] * scan['angle_increment'] + mount[2]
    x = mount[0] + ranges[valid] * np.cos(angles)
    y = mount[1] + ranges[valid] * np.sin(angles)
    radius = math.hypot(max(abs(bounds[0]), abs(bounds[1])),
                        max(abs(bounds[2]), abs(bounds[3]))) + center_deviation_m + .01
    return bool(np.all(x*x + y*y > radius*radius))
