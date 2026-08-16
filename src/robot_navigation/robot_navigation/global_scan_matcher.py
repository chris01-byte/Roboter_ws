"""ROS-unabhaengiger globaler LiDAR/Karten-Abgleich.

Die Suche bewertet sowohl die Naehe der Scan-Endpunkte zu Kartenwaenden als
auch den freien Strahlweg. Sie veraendert keinerlei Roboterzustand.
"""

from dataclasses import dataclass
import math
from typing import Tuple

import numpy as np
from scipy.ndimage import distance_transform_edt


# Derselbe konservative Radius wie in beiden realen Nav2-Costmaps. Eine gute
# Scan-Uebereinstimmung darf nie eine Pose freigeben, an die der Roboter laut
# Navigationsgeometrie nicht passt.
ROBOT_CLEARANCE_M = 0.40
ENDPOINT_SIGMA_M = 0.14
COARSE_CELL_STEP = 4
COARSE_YAW_STEP_DEG = 5
COARSE_RAYS = 240
REFINE_RAYS = 720
REFINE_POSITION_M = 0.18
REFINE_YAW_DEG = 7
DISTINCT_POSITION_M = 0.45
DISTINCT_YAW_DEG = 25.0


@dataclass(frozen=True)
class ScanCandidate:
    x_m: float
    y_m: float
    yaw_rad: float
    score: float
    endpoint_within_0_15_m_ratio: float


@dataclass(frozen=True)
class SearchResult:
    candidates: Tuple[ScanCandidate, ...]
    valid_scan_points: int

    @property
    def best(self) -> ScanCandidate:
        if not self.candidates:
            raise ValueError('Suchergebnis enthaelt keine Kandidaten')
        return self.candidates[0]

    @property
    def score_ratio(self) -> float:
        if len(self.candidates) < 2:
            return 0.0
        return self.candidates[0].score / max(self.candidates[1].score, 1e-9)


def select_evenly(points: np.ndarray, maximum: int) -> np.ndarray:
    if points.shape[0] <= maximum:
        return points
    indices = np.linspace(0, points.shape[0] - 1, maximum, dtype=np.int64)
    return points[indices]


def transform_points(
        points: np.ndarray, translation_x: float, translation_y: float,
        yaw_rad: float) -> np.ndarray:
    cosine, sine = math.cos(yaw_rad), math.sin(yaw_rad)
    x = translation_x + cosine * points[:, 0] - sine * points[:, 1]
    y = translation_y + sine * points[:, 0] + cosine * points[:, 1]
    return np.column_stack((x, y))


class MapScorer:
    """Vorberechnete Distanzfelder und vektorisierte Posenbewertung."""

    def __init__(
            self, grid: np.ndarray, resolution: float, origin_x: float,
            origin_y: float, origin_yaw: float = 0.0):
        array = np.asarray(grid, dtype=np.int16)
        if array.ndim != 2 or array.size == 0:
            raise ValueError('Karte muss ein nichtleeres zweidimensionales Feld sein')
        if not math.isfinite(resolution) or resolution <= 0.0:
            raise ValueError('Kartenaufloesung muss endlich und positiv sein')
        if not all(math.isfinite(value) for value in (
                origin_x, origin_y, origin_yaw)):
            raise ValueError('Kartenursprung muss endlich sein')
        self.grid = array
        self.height, self.width = array.shape
        self.resolution = float(resolution)
        self.occupied = self.grid >= 65
        if not np.any(self.occupied):
            raise ValueError('Karte enthaelt keine belegten Zellen')
        self.wall_distance = distance_transform_edt(
            ~self.occupied) * self.resolution
        traversable = self.grid == 0
        self.clearance = distance_transform_edt(traversable) * self.resolution
        self.origin_x = float(origin_x)
        self.origin_y = float(origin_y)
        self.origin_yaw = float(origin_yaw)
        self.origin_cos = math.cos(self.origin_yaw)
        self.origin_sin = math.sin(self.origin_yaw)

    def grid_centers_to_world(self, rows, columns):
        local_x = (columns + 0.5) * self.resolution
        local_y = (rows + 0.5) * self.resolution
        x = (self.origin_x + self.origin_cos * local_x
             - self.origin_sin * local_y)
        y = (self.origin_y + self.origin_sin * local_x
             + self.origin_cos * local_y)
        return x, y

    def world_to_grid_arrays(self, x, y):
        delta_x = x - self.origin_x
        delta_y = y - self.origin_y
        local_x = self.origin_cos * delta_x + self.origin_sin * delta_y
        local_y = -self.origin_sin * delta_x + self.origin_cos * delta_y
        columns = np.floor(local_x / self.resolution).astype(np.int32)
        rows = np.floor(local_y / self.resolution).astype(np.int32)
        inside = (
            (columns >= 0) & (columns < self.width)
            & (rows >= 0) & (rows < self.height))
        return rows, columns, inside

    def candidate_positions(self):
        valid = (
            (self.grid == 0)
            & (self.clearance >= ROBOT_CLEARANCE_M))
        rows, columns = np.nonzero(valid)
        coarse = (
            (rows % COARSE_CELL_STEP == COARSE_CELL_STEP // 2)
            & (columns % COARSE_CELL_STEP == COARSE_CELL_STEP // 2))
        return self.grid_centers_to_world(rows[coarse], columns[coarse])

    def valid_base_poses(self, x, y):
        rows, columns, inside = self.world_to_grid_arrays(x, y)
        valid = np.zeros_like(inside, dtype=bool)
        valid[inside] = (
            (self.grid[rows[inside], columns[inside]] == 0)
            & (self.clearance[rows[inside], columns[inside]]
               >= ROBOT_CLEARANCE_M))
        return valid

    def score(
            self, pose_x: np.ndarray, pose_y: np.ndarray,
            pose_yaw: np.ndarray, endpoint_points: np.ndarray,
            ray_points: np.ndarray, chunk_size: int = 256):
        scores = np.full(pose_x.shape[0], -1.0, dtype=np.float64)
        endpoint_ratios = np.zeros(pose_x.shape[0], dtype=np.float64)
        threshold = math.exp(-0.5 * (0.15 / ENDPOINT_SIGMA_M) ** 2)
        for start in range(0, pose_x.shape[0], chunk_size):
            stop = min(start + chunk_size, pose_x.shape[0])
            x = pose_x[start:stop, None]
            y = pose_y[start:stop, None]
            cosine = np.cos(pose_yaw[start:stop])[:, None]
            sine = np.sin(pose_yaw[start:stop])[:, None]

            end_x = (
                x + cosine * endpoint_points[:, 0]
                - sine * endpoint_points[:, 1])
            end_y = (
                y + sine * endpoint_points[:, 0]
                + cosine * endpoint_points[:, 1])
            rows, columns, inside = self.world_to_grid_arrays(end_x, end_y)
            likelihood = np.zeros_like(end_x)
            likelihood[inside] = np.exp(
                -0.5 * (
                    self.wall_distance[rows[inside], columns[inside]]
                    / ENDPOINT_SIGMA_M) ** 2)
            endpoint_score = np.mean(likelihood, axis=1)
            endpoint_ratios[start:stop] = np.mean(
                likelihood >= threshold, axis=1)

            ray_x = (
                x + cosine * ray_points[:, 0]
                - sine * ray_points[:, 1])
            ray_y = (
                y + sine * ray_points[:, 0]
                + cosine * ray_points[:, 1])
            ray_rows, ray_columns, ray_inside = self.world_to_grid_arrays(
                ray_x, ray_y)
            sampled_values = np.full(ray_x.shape, 100, dtype=np.int16)
            sampled_values[ray_inside] = self.grid[
                ray_rows[ray_inside], ray_columns[ray_inside]]
            free_score = np.zeros_like(ray_x)
            free_score[sampled_values == 0] = 1.0
            free_score[sampled_values < 0] = 0.35
            scores[start:stop] = (
                0.78 * endpoint_score + 0.22 * np.mean(free_score, axis=1))
        return scores, endpoint_ratios


def build_ray_samples(
        laser_points: np.ndarray, laser_translation_x: float,
        laser_translation_y: float, laser_yaw_rad: float,
        maximum_beams: int) -> np.ndarray:
    selected = select_evenly(laser_points, maximum_beams)
    fractions = np.asarray((0.2, 0.4, 0.6, 0.8), dtype=np.float64)
    sampled = (selected[:, None, :] * fractions[None, :, None]).reshape(-1, 2)
    return transform_points(
        sampled, laser_translation_x, laser_translation_y, laser_yaw_rad)


def angular_difference(first: float, second: float) -> float:
    return abs(math.atan2(math.sin(first - second), math.cos(first - second)))


def _distinct_best(pose_x, pose_y, pose_yaw, scores, count):
    selected = []
    for index in np.argsort(scores)[::-1]:
        if scores[index] < 0.0:
            continue
        candidate = (
            float(pose_x[index]), float(pose_y[index]),
            float(pose_yaw[index]), float(scores[index]), int(index))
        if all(
            math.hypot(candidate[0] - previous[0],
                       candidate[1] - previous[1]) >= DISTINCT_POSITION_M
            or angular_difference(candidate[2], previous[2])
            >= math.radians(DISTINCT_YAW_DEG)
            for previous in selected
        ):
            selected.append(candidate)
            if len(selected) >= count:
                break
    return selected


def search_global_pose(
        scorer: MapScorer, laser_points: np.ndarray, *,
        laser_translation_x: float, laser_translation_y: float,
        laser_yaw_rad: float) -> SearchResult:
    """Sucht hierarchisch freie Kartenpositionen und alle Blickrichtungen."""
    points = np.asarray(laser_points, dtype=np.float64)
    if points.ndim != 2 or points.shape[1:] != (2,):
        raise ValueError('Laserpunkte muessen die Form (n, 2) haben')
    if points.shape[0] < 50 or not np.all(np.isfinite(points)):
        raise ValueError('Zu wenige oder ungueltige Laserpunkte')

    coarse_laser = select_evenly(points, COARSE_RAYS)
    coarse_endpoints = transform_points(
        coarse_laser, laser_translation_x, laser_translation_y,
        laser_yaw_rad)
    coarse_rays = build_ray_samples(
        points, laser_translation_x, laser_translation_y, laser_yaw_rad, 48)
    positions_x, positions_y = scorer.candidate_positions()
    if positions_x.size == 0:
        raise RuntimeError('Karte enthaelt keine Position mit Roboterfreiraum')
    yaws = np.radians(np.arange(-180, 180, COARSE_YAW_STEP_DEG))
    pose_x = np.repeat(positions_x, yaws.size)
    pose_y = np.repeat(positions_y, yaws.size)
    pose_yaw = np.tile(yaws, positions_x.size)
    coarse_scores, _ = scorer.score(
        pose_x, pose_y, pose_yaw, coarse_endpoints, coarse_rays)
    seeds = _distinct_best(pose_x, pose_y, pose_yaw, coarse_scores, 12)
    if not seeds:
        raise RuntimeError('Keine zulaessige grobe Scan-Hypothese gefunden')

    refined_x = []
    refined_y = []
    refined_yaw = []
    position_offsets = np.arange(
        -REFINE_POSITION_M, REFINE_POSITION_M + 0.001, scorer.resolution)
    yaw_offsets = np.radians(np.arange(-REFINE_YAW_DEG, REFINE_YAW_DEG + 1))
    for seed_x, seed_y, seed_yaw, _, _ in seeds:
        offset_x, offset_y, offset_yaw = np.meshgrid(
            position_offsets, position_offsets, yaw_offsets, indexing='ij')
        refined_x.append((seed_x + offset_x).ravel())
        refined_y.append((seed_y + offset_y).ravel())
        refined_yaw.append((seed_yaw + offset_yaw).ravel())
    pose_x = np.concatenate(refined_x)
    pose_y = np.concatenate(refined_y)
    pose_yaw = np.concatenate(refined_yaw)
    valid = scorer.valid_base_poses(pose_x, pose_y)
    pose_x, pose_y, pose_yaw = pose_x[valid], pose_y[valid], pose_yaw[valid]

    refine_laser = select_evenly(points, REFINE_RAYS)
    refine_endpoints = transform_points(
        refine_laser, laser_translation_x, laser_translation_y,
        laser_yaw_rad)
    refine_rays = build_ray_samples(
        points, laser_translation_x, laser_translation_y, laser_yaw_rad, 120)
    refined_scores, endpoint_ratios = scorer.score(
        pose_x, pose_y, pose_yaw, refine_endpoints, refine_rays,
        chunk_size=128)
    best = _distinct_best(pose_x, pose_y, pose_yaw, refined_scores, 8)
    candidates = tuple(
        ScanCandidate(
            x_m=x,
            y_m=y,
            yaw_rad=math.atan2(math.sin(yaw), math.cos(yaw)),
            score=score,
            endpoint_within_0_15_m_ratio=float(endpoint_ratios[index]))
        for x, y, yaw, score, index in best
    )
    if len(candidates) < 2:
        raise RuntimeError('Keine zwei unterscheidbaren Scan-Hypothesen gefunden')
    return SearchResult(
        candidates=candidates, valid_scan_points=int(points.shape[0]))


def result_is_accepted(
        result: SearchResult, *, minimum_score: float,
        minimum_endpoint_ratio: float, minimum_score_ratio: float):
    """Fail-closed Qualitaetsgrenze fuer das globale Suchergebnis."""
    best = result.best
    reasons = []
    if best.score < minimum_score:
        reasons.append(
            f'Gesamtscore {best.score:.3f} < {minimum_score:.3f}')
    if best.endpoint_within_0_15_m_ratio < minimum_endpoint_ratio:
        reasons.append(
            'Wandtrefferquote '
            f'{best.endpoint_within_0_15_m_ratio:.3f} '
            f'< {minimum_endpoint_ratio:.3f}')
    if result.score_ratio < minimum_score_ratio:
        reasons.append(
            f'Bestenabstand {result.score_ratio:.3f} '
            f'< {minimum_score_ratio:.3f}')
    return not reasons, reasons
