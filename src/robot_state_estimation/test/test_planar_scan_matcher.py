import math
from pathlib import Path
import sys

import numpy as np


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE_ROOT))

from robot_state_estimation.planar_scan_matcher import (  # noqa: E402
    LidarReferenceMatcher,
    LidarMotionEstimate,
    compose_pose,
    conservative_motion_variances,
    motion_estimate_is_reliable,
    relative_pose,
    scan_points_in_base,
)


def _feature_rich_reference():
    horizontal = np.column_stack((
        np.linspace(-2.0, 2.0, 401),
        np.full(401, 1.3),
    ))
    vertical = np.column_stack((
        np.full(321, -1.4),
        np.linspace(-1.4, 1.3, 321),
    ))
    diagonal_x = np.linspace(0.2, 1.8, 251)
    diagonal = np.column_stack((diagonal_x, -0.8 + 0.3 * diagonal_x))
    return np.vstack((horizontal, vertical, diagonal))


def _scan_seen_from_pose(reference, x_m, y_m, yaw_rad):
    delta = reference - np.asarray((x_m, y_m))
    cosine = math.cos(yaw_rad)
    sine = math.sin(yaw_rad)
    return np.column_stack((
        cosine * delta[:, 0] + sine * delta[:, 1],
        -sine * delta[:, 0] + cosine * delta[:, 1],
    ))


def test_matcher_recovers_motion_without_wheel_prediction():
    reference = _feature_rich_reference()
    matcher = LidarReferenceMatcher(reference)
    true_pose = (0.045, -0.025, math.radians(2.0))
    current = _scan_seen_from_pose(reference, *true_pose)

    estimate = matcher.estimate(current, (0.0, 0.0, 0.0))

    assert math.isclose(estimate.x_m, true_pose[0], abs_tol=0.01)
    assert math.isclose(estimate.y_m, true_pose[1], abs_tol=0.01)
    assert math.isclose(
        estimate.yaw_rad, true_pose[2], abs_tol=math.radians(0.5))
    assert motion_estimate_is_reliable(
        estimate, max_cost_m=0.08, min_support_ratio=0.45,
        min_distinct_gap_m=0.0005)


def test_pose_compose_and_relative_are_inverse_operations():
    first = (1.2, -0.4, math.radians(35.0))
    local = (0.3, -0.1, math.radians(-12.0))

    world = compose_pose(first, local)
    recovered = relative_pose(first, world)

    assert np.allclose(recovered, local, atol=1e-9)


def test_scan_conversion_honours_sensor_mount():
    points = scan_points_in_base(
        [1.0], 0.0, 0.1, 0.05, 8.0,
        laser_x_m=0.2, laser_y_m=-0.1,
        laser_yaw_rad=math.pi / 2.0, maximum_range_m=6.0)

    assert np.allclose(points[0], (0.2, 0.9), atol=1e-9)


def test_scan_residual_is_converted_to_velocity_variance_using_time():
    estimate = LidarMotionEstimate(
        x_m=0.02, y_m=0.0, yaw_rad=0.01,
        cost_m=0.01, support_ratio=0.5, distinct_cost_m=0.02)

    variances = conservative_motion_variances(
        estimate, 0.2,
        minimum_position_m2=0.0004,
        minimum_yaw_rad2=0.0025,
        minimum_linear_velocity_m2ps2=0.0025,
        minimum_angular_velocity_rad2ps2=0.01)

    assert math.isclose(variances.position_m2, 0.0004)
    assert math.isclose(variances.yaw_rad2, 0.0025)
    assert math.isclose(variances.linear_velocity_m2ps2, 0.02)
    assert math.isclose(variances.angular_velocity_rad2ps2, 0.125)
