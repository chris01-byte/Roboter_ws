import math
from pathlib import Path
import sys

import numpy as np


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE_ROOT))

from explore.lidar_motion import (  # noqa: E402
    LidarMotionEstimate,
    LidarReferenceMatcher,
    motion_estimate_is_reliable,
    scan_points_in_base,
)


def _line(start, stop, count):
    return np.column_stack((
        np.linspace(start[0], stop[0], count),
        np.linspace(start[1], stop[1], count),
    ))


def _feature_rich_reference():
    return np.vstack((
        _line((-1.5, -1.1), (2.8, -1.1), 240),
        _line((2.8, -1.1), (2.8, 1.8), 180),
        _line((2.8, 1.8), (0.6, 1.8), 130),
        _line((0.6, 1.8), (0.6, 0.45), 90),
        _line((0.6, 0.45), (-0.7, 0.45), 100),
        _line((-0.7, 0.45), (-1.4, 1.35), 80),
    ))


def _scan_seen_from_pose(reference, x_m, y_m, yaw_rad):
    # reference = translation + rotation * current
    delta_x = reference[:, 0] - x_m
    delta_y = reference[:, 1] - y_m
    cosine = math.cos(yaw_rad)
    sine = math.sin(yaw_rad)
    return np.column_stack((
        cosine * delta_x + sine * delta_y,
        -sine * delta_x + cosine * delta_y,
    ))


def test_scan_conversion_uses_measured_laser_mount():
    points = scan_points_in_base(
        [1.0, float('nan')], 0.0, math.pi / 2.0, 0.05, 8.0,
        laser_x_m=0.2, laser_y_m=0.0, laser_yaw_rad=math.pi / 2.0,
        maximum_range_m=4.0)

    assert points.shape == (1, 2)
    assert np.allclose(points[0], (0.2, 1.0), atol=1e-9)


def test_reference_matcher_stays_zero_for_stationary_scan():
    reference = _feature_rich_reference()
    matcher = LidarReferenceMatcher(reference)

    estimate = matcher.estimate(reference.copy(), (0.0, 0.0, 0.0))

    assert abs(estimate.x_m) <= 0.005
    assert abs(estimate.y_m) <= 0.005
    assert abs(estimate.yaw_rad) <= math.radians(0.25)
    assert motion_estimate_is_reliable(
        estimate, max_cost_m=0.08, min_support_ratio=0.45,
        min_distinct_gap_m=0.0005)


def test_reference_matcher_recovers_motion_despite_dropout_and_noise():
    reference = _feature_rich_reference()
    matcher = LidarReferenceMatcher(reference)
    true_pose = (0.50, 0.03, math.radians(6.0))
    current = _scan_seen_from_pose(reference, *true_pose)
    current = current[np.arange(current.shape[0]) % 5 != 0]
    current += np.random.default_rng(18).normal(0.0, 0.003, current.shape)

    estimate = matcher.estimate(
        current, (0.48, 0.025, math.radians(5.8)))

    assert math.isclose(estimate.x_m, true_pose[0], abs_tol=0.01)
    assert math.isclose(estimate.y_m, true_pose[1], abs_tol=0.01)
    assert math.isclose(
        estimate.yaw_rad, true_pose[2], abs_tol=math.radians(0.5))
    assert motion_estimate_is_reliable(
        estimate, max_cost_m=0.08, min_support_ratio=0.45,
        min_distinct_gap_m=0.0005)


def test_match_quality_rejects_weak_or_ambiguous_pose():
    weak = LidarMotionEstimate(
        x_m=0.2, y_m=0.0, yaw_rad=0.0,
        cost_m=0.09, support_ratio=0.30, distinct_cost_m=0.0901)

    assert not motion_estimate_is_reliable(
        weak, max_cost_m=0.08, min_support_ratio=0.45,
        min_distinct_gap_m=0.0005)


def test_unchanged_lidar_cannot_claim_encoder_slip_as_motion():
    reference = _feature_rich_reference()
    matcher = LidarReferenceMatcher(reference)

    estimate = matcher.estimate(reference, (0.0, 0.0, 0.0))

    # A wheel budget may say 1.0 m elsewhere; this independent estimate stays
    # at zero because the room contour did not move around the chassis.
    assert estimate.x_m < 0.01
