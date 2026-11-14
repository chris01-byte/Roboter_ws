"""Small, wheel-independent planar scan matcher.

The matcher observes room geometry against a frozen local reference.  It is
not a SLAM system and owns no TF.  Its only purpose in this package is to
provide an independent short-term motion measurement for quality supervision.
"""

from dataclasses import dataclass
import math
from typing import Sequence, Tuple

import numpy as np
from scipy.ndimage import distance_transform_edt


@dataclass(frozen=True)
class LidarMotionEstimate:
    x_m: float
    y_m: float
    yaw_rad: float
    cost_m: float
    support_ratio: float
    distinct_cost_m: float

    @property
    def distinct_gap_m(self) -> float:
        return self.distinct_cost_m - self.cost_m


@dataclass(frozen=True)
class LidarMotionVariances:
    position_m2: float
    yaw_rad2: float
    linear_velocity_m2ps2: float
    angular_velocity_rad2ps2: float


def conservative_motion_variances(
        estimate: LidarMotionEstimate, dt_s: float, *,
        minimum_position_m2: float,
        minimum_yaw_rad2: float,
        minimum_linear_velocity_m2ps2: float,
        minimum_angular_velocity_rad2ps2: float) -> LidarMotionVariances:
    """Convert scan residuals into dimensionally valid conservative variances.

    The matcher residual is a distance, so it can seed pose variance but not
    be copied directly into a velocity covariance.  Differencing two poses
    contributes approximately twice the pose variance divided by ``dt**2``.
    Yaw uses a conservative 0.5 m effective geometry lever arm.
    """
    values = (
        estimate.cost_m, estimate.support_ratio, dt_s,
        minimum_position_m2, minimum_yaw_rad2,
        minimum_linear_velocity_m2ps2,
        minimum_angular_velocity_rad2ps2,
    )
    if not all(math.isfinite(value) and value > 0.0 for value in values):
        raise ValueError('LiDAR-Unsicherheiten muessen positiv sein')
    if estimate.support_ratio > 1.0:
        raise ValueError('LiDAR-Unterstuetzung darf eins nicht ueberschreiten')

    position = max(
        minimum_position_m2,
        estimate.cost_m * estimate.cost_m
        / max(estimate.support_ratio, 0.05))
    yaw = max(minimum_yaw_rad2, 4.0 * position)
    inverse_dt_squared = 1.0 / (dt_s * dt_s)
    return LidarMotionVariances(
        position_m2=position,
        yaw_rad2=yaw,
        linear_velocity_m2ps2=max(
            minimum_linear_velocity_m2ps2,
            2.0 * position * inverse_dt_squared),
        angular_velocity_rad2ps2=max(
            minimum_angular_velocity_rad2ps2,
            2.0 * yaw * inverse_dt_squared),
    )


def normalize_angle(angle: float) -> float:
    return math.atan2(math.sin(angle), math.cos(angle))


def compose_pose(
        first: Tuple[float, float, float],
        second: Tuple[float, float, float]) -> Tuple[float, float, float]:
    """Return ``world_T_first * first_T_second`` in planar coordinates."""
    cosine = math.cos(first[2])
    sine = math.sin(first[2])
    return (
        first[0] + cosine * second[0] - sine * second[1],
        first[1] + sine * second[0] + cosine * second[1],
        normalize_angle(first[2] + second[2]),
    )


def relative_pose(
        first: Tuple[float, float, float],
        second: Tuple[float, float, float]) -> Tuple[float, float, float]:
    """Express ``second`` in the coordinate frame of ``first``."""
    dx = second[0] - first[0]
    dy = second[1] - first[1]
    cosine = math.cos(first[2])
    sine = math.sin(first[2])
    return (
        cosine * dx + sine * dy,
        -sine * dx + cosine * dy,
        normalize_angle(second[2] - first[2]),
    )


def scan_points_in_base(
        ranges: Sequence[float], angle_min: float, angle_increment: float,
        range_min: float, range_max: float, *, laser_x_m: float,
        laser_y_m: float, laser_yaw_rad: float,
        maximum_range_m: float) -> np.ndarray:
    values = (
        angle_min, angle_increment, range_min, range_max,
        laser_x_m, laser_y_m, laser_yaw_rad, maximum_range_m,
    )
    if not all(math.isfinite(value) for value in values):
        raise ValueError('LiDAR-Geometrie muss endlich sein')
    if angle_increment <= 0.0 or maximum_range_m <= 0.0:
        raise ValueError('LiDAR-Winkel und Reichweite muessen positiv sein')
    array = np.asarray(ranges, dtype=np.float64)
    if array.ndim != 1 or array.size == 0:
        raise ValueError('LiDAR-Profil muss eindimensional und nichtleer sein')
    angles = angle_min + np.arange(array.size) * angle_increment
    valid = (
        np.isfinite(array)
        & (array >= max(0.0, range_min))
        & (array <= min(range_max, maximum_range_m)))
    laser_x = array[valid] * np.cos(angles[valid])
    laser_y = array[valid] * np.sin(angles[valid])
    cosine = math.cos(laser_yaw_rad)
    sine = math.sin(laser_yaw_rad)
    return np.column_stack((
        laser_x_m + cosine * laser_x - sine * laser_y,
        laser_y_m + sine * laser_x + cosine * laser_y,
    ))


def motion_estimate_is_reliable(
        estimate: LidarMotionEstimate, *, max_cost_m: float,
        min_support_ratio: float, min_distinct_gap_m: float) -> bool:
    limits = (max_cost_m, min_support_ratio, min_distinct_gap_m)
    values = (
        estimate.x_m, estimate.y_m, estimate.yaw_rad, estimate.cost_m,
        estimate.support_ratio, estimate.distinct_cost_m,
    )
    if not all(math.isfinite(value) for value in (*limits, *values)):
        return False
    if (
            max_cost_m <= 0.0
            or not 0.0 < min_support_ratio <= 1.0
            or min_distinct_gap_m <= 0.0):
        return False
    return (
        estimate.cost_m <= max_cost_m
        and estimate.support_ratio >= min_support_ratio
        and estimate.distinct_gap_m >= min_distinct_gap_m)


class LidarReferenceMatcher:
    """Match successive scans against one frozen local distance field."""

    def __init__(
            self, reference_points: np.ndarray, *, resolution_m: float = 0.015,
            field_margin_m: float = 0.90, maximum_points: int = 600,
            clipped_distance_m: float = 0.20,
            support_distance_m: float = 0.06):
        values = (
            resolution_m, field_margin_m, clipped_distance_m,
            support_distance_m,
        )
        if not all(math.isfinite(value) and value > 0.0 for value in values):
            raise ValueError('Scanmatcher-Grenzen muessen positiv sein')
        if maximum_points < 200:
            raise ValueError('Scanmatcher braucht mindestens 200 Stuetzpunkte')
        points = self._validated_points(reference_points, maximum_points)
        if points.shape[0] < 200:
            raise ValueError('Referenzscan enthaelt zu wenige Punkte')
        self._resolution = float(resolution_m)
        self._maximum_points = int(maximum_points)
        self._clipped_distance = float(clipped_distance_m)
        self._support_distance = float(support_distance_m)
        self._outside_distance = max(0.30, self._clipped_distance)
        self._origin_x = float(np.min(points[:, 0]) - field_margin_m)
        self._origin_y = float(np.min(points[:, 1]) - field_margin_m)
        maximum_x = float(np.max(points[:, 0]) + field_margin_m)
        maximum_y = float(np.max(points[:, 1]) + field_margin_m)
        self._width = int(math.ceil(
            (maximum_x - self._origin_x) / self._resolution)) + 1
        self._height = int(math.ceil(
            (maximum_y - self._origin_y) / self._resolution)) + 1
        occupied = np.zeros((self._height, self._width), dtype=bool)
        columns, rows = self._grid_indices(points)
        occupied[rows, columns] = True
        self._distance_field = (
            distance_transform_edt(~occupied) * self._resolution)

    @staticmethod
    def _validated_points(points: np.ndarray, maximum: int) -> np.ndarray:
        array = np.asarray(points, dtype=np.float64)
        if array.ndim != 2 or array.shape[1:] != (2,):
            raise ValueError('Scanpunkte muessen die Form (n, 2) haben')
        array = array[np.all(np.isfinite(array), axis=1)]
        if array.shape[0] > maximum:
            indices = np.linspace(
                0, array.shape[0] - 1, maximum, dtype=np.int64)
            array = array[indices]
        return array

    def _grid_indices(self, points: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        columns = np.rint(
            (points[:, 0] - self._origin_x) / self._resolution).astype(np.int32)
        rows = np.rint(
            (points[:, 1] - self._origin_y) / self._resolution).astype(np.int32)
        return columns, rows

    @staticmethod
    def _candidate_grid(
            center: Tuple[float, float, float], *,
            translation_span_m: float, translation_step_m: float,
            yaw_span_rad: float, yaw_step_rad: float) -> np.ndarray:
        x_values = np.arange(
            -translation_span_m, translation_span_m + 1e-12,
            translation_step_m) + center[0]
        y_values = np.arange(
            -translation_span_m, translation_span_m + 1e-12,
            translation_step_m) + center[1]
        yaw_values = np.arange(
            -yaw_span_rad, yaw_span_rad + 1e-12,
            yaw_step_rad) + center[2]
        return np.asarray(
            np.meshgrid(x_values, y_values, yaw_values, indexing='ij')
        ).reshape(3, -1).T

    def _scores(
        self, points: np.ndarray, candidates: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray]:
        costs = np.empty(candidates.shape[0], dtype=np.float64)
        supports = np.empty(candidates.shape[0], dtype=np.float64)
        for start in range(0, candidates.shape[0], 128):
            stop = min(start + 128, candidates.shape[0])
            chunk = candidates[start:stop]
            cosine = np.cos(chunk[:, 2, None])
            sine = np.sin(chunk[:, 2, None])
            x = (
                chunk[:, 0, None]
                + cosine * points[None, :, 0]
                - sine * points[None, :, 1])
            y = (
                chunk[:, 1, None]
                + sine * points[None, :, 0]
                + cosine * points[None, :, 1])
            columns = np.rint(
                (x - self._origin_x) / self._resolution).astype(np.int32)
            rows = np.rint(
                (y - self._origin_y) / self._resolution).astype(np.int32)
            inside = (
                (columns >= 0) & (columns < self._width)
                & (rows >= 0) & (rows < self._height))
            distances = np.full(
                x.shape, self._outside_distance, dtype=np.float32)
            indices = np.nonzero(inside)
            distances[indices] = self._distance_field[
                rows[indices], columns[indices]]
            costs[start:stop] = np.mean(
                np.minimum(distances, self._clipped_distance), axis=1)
            supports[start:stop] = np.mean(
                distances <= self._support_distance, axis=1)
        return costs, supports

    @staticmethod
    def _pose(candidate: np.ndarray) -> Tuple[float, float, float]:
        return (
            float(candidate[0]), float(candidate[1]),
            normalize_angle(float(candidate[2])))

    def estimate(
        self, current_points: np.ndarray,
        previous_pose: Tuple[float, float, float]
    ) -> LidarMotionEstimate:
        if not all(math.isfinite(value) for value in previous_pose):
            raise ValueError('Vorherige LiDAR-Pose muss endlich sein')
        points = self._validated_points(current_points, self._maximum_points)
        if points.shape[0] < 200:
            raise ValueError('Aktueller Scan enthaelt zu wenige Punkte')

        coarse = self._candidate_grid(
            previous_pose,
            translation_span_m=0.06,
            translation_step_m=0.02,
            yaw_span_rad=math.radians(3.0),
            yaw_step_rad=math.radians(1.0))
        coarse_costs, _ = self._scores(points, coarse)
        coarse_best = coarse[int(np.argmin(coarse_costs))]

        position_separation = np.hypot(
            coarse[:, 0] - coarse_best[0],
            coarse[:, 1] - coarse_best[1])
        yaw_separation = np.abs(np.arctan2(
            np.sin(coarse[:, 2] - coarse_best[2]),
            np.cos(coarse[:, 2] - coarse_best[2])))
        distinct = (
            (position_separation >= 0.04)
            | (yaw_separation >= math.radians(1.5)))
        distinct_cost = (
            float(np.min(coarse_costs[distinct]))
            if np.any(distinct) else float('inf'))

        refine = self._candidate_grid(
            self._pose(coarse_best),
            translation_span_m=0.02,
            translation_step_m=0.005,
            yaw_span_rad=math.radians(0.75),
            yaw_step_rad=math.radians(0.25))
        refine_costs, refine_supports = self._scores(points, refine)
        best_index = int(np.argmin(refine_costs))
        x_m, y_m, yaw_rad = self._pose(refine[best_index])
        return LidarMotionEstimate(
            x_m=x_m,
            y_m=y_m,
            yaw_rad=yaw_rad,
            cost_m=float(refine_costs[best_index]),
            support_ratio=float(refine_supports[best_index]),
            distinct_cost_m=distinct_cost,
        )
