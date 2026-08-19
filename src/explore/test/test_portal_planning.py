from pathlib import Path
import math
import sys

import numpy as np


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE_ROOT))

from explore.portal_planning import (  # noqa: E402
    find_portal_bridges,
    front_lidar_corridor_check,
)


def _two_rooms(*, resolution=0.05, gap_cells=8, target_rows=30):
    costs = np.full((40, 80), -1, dtype=np.int16)
    costs[5:35, 3:28] = 0
    target_start = 28 + gap_cells
    costs[5:5 + target_rows, target_start:75] = 0
    return costs, target_start


def _bridges(costs, **overrides):
    arguments = {
        'resolution_m': 0.05,
        'goal_max_cost': 90,
        'min_target_area_m2': 0.40,
        'min_gap_m': 0.12,
        'max_gap_m': 0.80,
        'exit_margin_m': 0.25,
        'max_traverse_distance_m': 1.00,
    }
    arguments.update(overrides)
    return find_portal_bridges(costs, (20, 10), **arguments)


def test_finds_bounded_bridge_between_two_large_components():
    costs, target_start = _two_rooms(gap_cells=8)

    bridges = _bridges(costs)

    assert len(bridges) == 1
    bridge = bridges[0]
    assert bridge.staging_col == 27
    assert bridge.target_col == target_start
    assert math.isclose(bridge.gap_m, 0.45, abs_tol=1e-9)
    assert math.isclose(bridge.traverse_distance_m, 0.70, abs_tol=1e-9)
    assert bridge.target_area_m2 > 1.0
    assert bridge.staging_distance_m > 0.8


def test_bridge_endpoints_must_both_have_acceptable_nav2_cost():
    costs, target_start = _two_rooms(gap_cells=3)
    costs[:, 26:28] = 95
    costs[:, target_start:target_start + 2] = 95

    bridge = _bridges(costs)[0]

    assert costs[bridge.staging_row, bridge.staging_col] <= 90
    assert costs[bridge.target_row, bridge.target_col] <= 90
    assert bridge.staging_col == 25
    assert bridge.target_col == target_start + 2


def test_rejects_target_component_that_is_too_small():
    costs, _target_start = _two_rooms(gap_cells=5, target_rows=2)

    assert _bridges(costs) == []


def test_rejects_component_beyond_maximum_gap():
    costs, _target_start = _two_rooms(gap_cells=18)

    assert _bridges(costs) == []


def test_rejects_bridge_when_safe_endpoints_make_motion_too_long():
    costs, target_start = _two_rooms(gap_cells=4)
    costs[:, 20:28] = 95
    costs[:, target_start:target_start + 8] = 95

    assert _bridges(costs, max_traverse_distance_m=0.80) == []


def _corridor_points(distance=2.0, count=30):
    return np.column_stack((
        np.full(count, distance),
        np.linspace(-0.24, 0.24, count),
    ))


def test_lidar_accepts_observed_clear_swept_corridor():
    result = front_lidar_corridor_check(
        _corridor_points(), traverse_distance_m=0.70,
        corridor_half_width_m=0.25, front_overhang_m=0.33,
        minimum_far_support_points=12)

    assert result.clear
    assert math.isclose(result.required_clear_distance_m, 1.03)
    assert result.far_support_points == 30


def test_lidar_rejects_central_obstacle_even_with_far_support():
    points = np.vstack((_corridor_points(), [[0.82, 0.05]]))

    result = front_lidar_corridor_check(
        points, traverse_distance_m=0.70,
        corridor_half_width_m=0.25, front_overhang_m=0.33,
        minimum_far_support_points=12)

    assert not result.clear
    assert math.isclose(result.nearest_obstacle_m, 0.82)


def test_lidar_rejects_unobserved_or_masked_corridor():
    points = np.column_stack((
        np.full(40, 2.0), np.linspace(0.30, 0.60, 40)))

    result = front_lidar_corridor_check(
        points, traverse_distance_m=0.70,
        corridor_half_width_m=0.25, front_overhang_m=0.33,
        minimum_far_support_points=12)

    assert not result.clear
    assert result.far_support_points == 0
