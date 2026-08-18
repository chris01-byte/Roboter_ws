"""Pure helpers for bridging narrow, costmap-disconnected portals.

Nav2 can split two physically connected rooms into separate traversable
components when the inflated doorway is only a few cells wide.  The explorer
must not treat that as a completed room.  This module identifies a bounded
bridge from the robot's current component to a sizeable neighbouring free
component.  Execution remains outside this module and still requires a fresh
LiDAR corridor check, the mission gate, velocity smoothing and collision
monitoring.
"""

from dataclasses import dataclass
import math
from typing import List, Optional, Tuple

import numpy as np
from scipy.ndimage import distance_transform_edt, label


@dataclass(frozen=True)
class PortalBridge:
    """One bounded transition between two traversable costmap components."""

    staging_row: int
    staging_col: int
    target_row: int
    target_col: int
    target_center_row: float
    target_center_col: float
    gap_m: float
    traverse_distance_m: float
    target_area_m2: float
    staging_distance_m: float


@dataclass(frozen=True)
class CorridorCheck:
    """Result of the independent front-LiDAR swept-corridor check."""

    clear: bool
    required_clear_distance_m: float
    nearest_obstacle_m: float
    far_support_points: int


def _nearest_true_cell(
        mask: np.ndarray, row: int, col: int,
        maximum_distance_cells: int) -> Optional[Tuple[int, int]]:
    rows, cols = np.nonzero(mask)
    if rows.size == 0:
        return None
    distances_sq = (rows - row) ** 2 + (cols - col) ** 2
    index = int(np.argmin(distances_sq))
    if distances_sq[index] > maximum_distance_cells ** 2:
        return None
    return int(rows[index]), int(cols[index])


def find_portal_bridges(
        costs: np.ndarray, robot_cell: Tuple[int, int], *,
        resolution_m: float, goal_max_cost: int,
        min_target_area_m2: float, min_gap_m: float, max_gap_m: float,
        exit_margin_m: float, max_traverse_distance_m: float,
        robot_seed_search_m: float = 0.30) -> List[PortalBridge]:
    """Return bounded bridges from the robot component to large neighbours.

    ``costs`` follows ``nav_msgs/OccupancyGrid`` semantics: negative is
    unknown, 99/100 is treated as non-traversable, and endpoints additionally
    have to stay at or below ``goal_max_cost``.  Components use 4-connectivity
    to match the conservative planner-side topology used by the explorer.
    """
    values = (
        resolution_m, min_target_area_m2, min_gap_m, max_gap_m,
        exit_margin_m, max_traverse_distance_m, robot_seed_search_m,
    )
    if not all(math.isfinite(value) and value > 0.0 for value in values):
        raise ValueError('Portalgrenzen muessen endlich und positiv sein')
    if min_gap_m >= max_gap_m:
        raise ValueError('Portal-Mindestluecke muss kleiner als Maximum sein')
    if exit_margin_m >= max_traverse_distance_m:
        raise ValueError('Portal-Auslauf muss unter der Maximalfahrt liegen')
    if not 0 <= goal_max_cost < 99:
        raise ValueError('Portal-Zielkosten muessen zwischen 0 und 98 liegen')
    array = np.asarray(costs, dtype=np.int16)
    if array.ndim != 2 or array.size == 0:
        raise ValueError('Portal-Costmap muss zweidimensional und nichtleer sein')
    robot_row, robot_col = robot_cell
    if not (
            0 <= robot_row < array.shape[0]
            and 0 <= robot_col < array.shape[1]):
        return []

    traversable = (array >= 0) & (array < 99)
    seed = _nearest_true_cell(
        traversable, robot_row, robot_col,
        max(1, int(math.ceil(robot_seed_search_m / resolution_m))))
    if seed is None:
        return []

    # scipy's default 2-D structure is the required 4-neighbour cross.
    labels, component_count = label(traversable)
    start_label = int(labels[seed])
    if start_label <= 0:
        return []
    sizes = np.bincount(labels.ravel())
    start_component = labels == start_label
    safe_start = start_component & (array <= goal_max_cost)
    if not np.any(safe_start):
        return []

    distance_to_start = distance_transform_edt(~start_component)
    distance_to_safe_start, safe_start_indices = distance_transform_edt(
        ~safe_start, return_indices=True)
    bridges: List[PortalBridge] = []
    minimum_target_cells = max(
        1, int(math.ceil(min_target_area_m2 / (resolution_m ** 2))))

    for target_label in range(1, component_count + 1):
        if target_label == start_label or sizes[target_label] < minimum_target_cells:
            continue
        target_component = labels == target_label
        safe_target = target_component & (array <= goal_max_cost)
        if not np.any(safe_target):
            continue
        target_distances = np.where(
            safe_target, distance_to_safe_start, np.inf)
        target_row, target_col = np.unravel_index(
            int(np.argmin(target_distances)), target_distances.shape)
        # ``gap_m`` describes the topological Costmap split itself.  The
        # actual bounded motion is measured between two endpoint cells whose
        # costs are both acceptable to Nav2.
        component_gap_m = float(np.min(
            np.where(target_component, distance_to_start, np.inf))
            * resolution_m)
        gap_m = component_gap_m
        if not min_gap_m <= gap_m <= max_gap_m:
            continue

        # The Nav2 staging endpoint must itself be below the configured goal
        # cost, not merely part of the broad (<99) connected component.
        staging_row = int(safe_start_indices[0, target_row, target_col])
        staging_col = int(safe_start_indices[1, target_row, target_col])
        traverse_cells = float(target_distances[target_row, target_col])
        traverse_distance_m = traverse_cells * resolution_m + exit_margin_m
        if traverse_distance_m > max_traverse_distance_m:
            continue

        target_rows, target_cols = np.nonzero(target_component)
        target_center_row = float(np.mean(target_rows))
        target_center_col = float(np.mean(target_cols))
        staging_distance_m = resolution_m * math.hypot(
            staging_row - robot_row, staging_col - robot_col)
        bridges.append(PortalBridge(
            staging_row=staging_row,
            staging_col=staging_col,
            target_row=int(target_row),
            target_col=int(target_col),
            target_center_row=target_center_row,
            target_center_col=target_center_col,
            gap_m=gap_m,
            traverse_distance_m=float(traverse_distance_m),
            target_area_m2=float(sizes[target_label]) * resolution_m ** 2,
            staging_distance_m=float(staging_distance_m),
        ))

    # Prefer a large new region, then the shortest safe staging/crossing path.
    bridges.sort(key=lambda bridge: (
        -bridge.target_area_m2,
        bridge.staging_distance_m + bridge.traverse_distance_m,
        bridge.gap_m,
    ))
    return bridges


def front_lidar_corridor_check(
        points_in_base: np.ndarray, *, traverse_distance_m: float,
        corridor_half_width_m: float, front_overhang_m: float,
        minimum_far_support_points: int,
        near_ignore_m: float = 0.05) -> CorridorCheck:
    """Require an observed clear LiDAR strip for the complete swept motion.

    The robot footprint and exit margin are handled by the caller.  This check
    only accepts a corridor if no finite LiDAR endpoint lies inside the swept
    centre strip *and* enough endpoints beyond the required distance prove
    that the front sector is actually observed rather than masked/empty.
    """
    values = (
        traverse_distance_m, corridor_half_width_m,
        front_overhang_m, near_ignore_m,
    )
    if not all(math.isfinite(value) and value > 0.0 for value in values):
        raise ValueError('LiDAR-Korridorgrenzen muessen endlich und positiv sein')
    if minimum_far_support_points <= 0:
        raise ValueError('LiDAR-Korridor braucht positive Fernstuetzung')
    points = np.asarray(points_in_base, dtype=np.float64)
    if points.ndim != 2 or points.shape[1:] != (2,):
        raise ValueError('LiDAR-Korridorpunkte muessen die Form (n, 2) haben')
    points = points[np.all(np.isfinite(points), axis=1)]
    required = traverse_distance_m + front_overhang_m
    centre = points[
        (points[:, 0] > near_ignore_m)
        & (np.abs(points[:, 1]) <= corridor_half_width_m)]
    if centre.shape[0] == 0:
        return CorridorCheck(False, required, float('inf'), 0)
    nearest = float(np.min(centre[:, 0]))
    far_support = int(np.count_nonzero(centre[:, 0] >= required))
    clear = nearest >= required and far_support >= minimum_far_support_points
    return CorridorCheck(clear, required, nearest, far_support)
