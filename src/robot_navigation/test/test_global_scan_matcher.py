import math
from pathlib import Path
import sys

import numpy as np


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE_ROOT))

from robot_navigation.global_scan_matcher import (  # noqa: E402
    MapScorer,
    ScanCandidate,
    SearchResult,
    build_ray_samples,
    result_is_accepted,
)


def test_wall_and_free_ray_score_separates_correct_from_wrong_pose():
    resolution = 0.05
    grid = np.zeros((100, 120), dtype=np.int16)
    grid[10, 10:111] = 100
    grid[90, 10:111] = 100
    grid[10:91, 10] = 100
    grid[10:91, 110] = 100
    # Asymmetrische Innenwand verhindert eine reine Rechteckmehrdeutigkeit.
    grid[25:55, 82] = 100
    scorer = MapScorer(grid, resolution, 0.0, 0.0)

    wall_points = []
    for column in range(10, 111, 2):
        wall_points.extend(((
            (column + 0.5) * resolution, (10 + 0.5) * resolution),
            ((column + 0.5) * resolution, (90 + 0.5) * resolution)))
    for row in range(12, 90, 2):
        wall_points.extend(((
            (10 + 0.5) * resolution, (row + 0.5) * resolution),
            ((110 + 0.5) * resolution, (row + 0.5) * resolution)))
    world_endpoints = np.asarray(wall_points, dtype=np.float64)
    true_x, true_y, true_yaw = 2.0, 2.2, math.radians(17.0)
    cosine, sine = math.cos(true_yaw), math.sin(true_yaw)
    delta = world_endpoints - np.asarray((true_x, true_y))
    base_points = np.column_stack((
        cosine * delta[:, 0] + sine * delta[:, 1],
        -sine * delta[:, 0] + cosine * delta[:, 1]))
    rays = build_ray_samples(base_points, 0.0, 0.0, 0.0, 120)

    scores, ratios = scorer.score(
        np.asarray((true_x, 3.1)),
        np.asarray((true_y, 1.0)),
        np.asarray((true_yaw, math.radians(-70.0))),
        base_points, rays)
    assert scores[0] > 0.95
    assert ratios[0] > 0.98
    assert scores[0] > scores[1] + 0.35
    assert ratios[0] > ratios[1] + 0.50


def test_result_requires_absolute_quality_and_a_distinct_winner():
    result = SearchResult(candidates=(
        ScanCandidate(1.2, -1.1, 0.7, 0.98, 0.99),
        ScanCandidate(0.5, 0.4, -2.1, 0.76, 0.72),
    ), valid_scan_points=1668)
    accepted, reasons = result_is_accepted(
        result, minimum_score=0.85, minimum_endpoint_ratio=0.85,
        minimum_score_ratio=1.15)
    assert accepted, reasons

    ambiguous = SearchResult(candidates=(
        ScanCandidate(1.2, -1.1, 0.7, 0.98, 0.99),
        ScanCandidate(2.2, 0.4, -2.1, 0.90, 0.92),
    ), valid_scan_points=1668)
    accepted, reasons = result_is_accepted(
        ambiguous, minimum_score=0.85, minimum_endpoint_ratio=0.85,
        minimum_score_ratio=1.15)
    assert not accepted
    assert any('Bestenabstand' in reason for reason in reasons)
