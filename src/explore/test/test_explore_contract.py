import math
from pathlib import Path
import sys
from types import SimpleNamespace

import numpy as np
from nav_msgs.msg import OccupancyGrid

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE_ROOT))

from explore.explore_node import (  # noqa: E402
    ExploreNode,
    Frontier,
    RotationProgress,
    circular_clearance_mask,
    connected_mask,
    farthest_uncovered_cell,
    stamp_coverage,
)


def _grid(width=80, height=80, resolution=0.05):
    grid = OccupancyGrid()
    grid.header.frame_id = 'map'
    grid.info.width = width
    grid.info.height = height
    grid.info.resolution = resolution
    grid.info.origin.orientation.w = 1.0
    grid.data = [-1] * (width * height)
    return grid


def test_grid_world_conversion_honors_rotated_origin():
    info = SimpleNamespace(
        resolution=1.0,
        origin=SimpleNamespace(
            position=SimpleNamespace(x=10.0, y=20.0),
            orientation=SimpleNamespace(
                x=0.0, y=0.0,
                z=math.sin(math.pi / 4.0),
                w=math.cos(math.pi / 4.0))))
    x, y = ExploreNode._grid_to_world(0, 0, info)
    assert math.isclose(x, 9.5, abs_tol=1e-9)
    assert math.isclose(y, 20.5, abs_tol=1e-9)
    col, row = ExploreNode._world_to_grid(x, y, info)
    assert (col, row) == (0, 0)


def test_frontier_goal_is_inside_known_clear_space():
    node = ExploreNode.__new__(ExploreNode)
    node._approach_dist_m = 0.45
    node._goal_clearance_m = 0.20
    node._goal_search_m = 0.20
    grid = _grid()
    data = np.asarray(grid.data, dtype=np.int16).reshape((80, 80))
    data[15:65, 10:55] = 0
    grid.data = data.ravel().tolist()
    frontier_x, frontier_y = node._grid_to_world(54, 40, grid.info)
    frontier = Frontier((frontier_x, frontier_y), 20)

    goal = node._frontier_approach_goal(
        frontier, robot_xy=(1.0, frontier_y), grid=grid)

    assert goal is not None
    col, row = node._world_to_grid(goal[0], goal[1], grid.info)
    assert data[row, col] == 0
    assert col < 54


def test_rotation_progress_survives_pi_wrap_and_rejects_reverse_motion():
    progress = RotationProgress(math.radians(170.0), direction=1.0)
    step = progress.update(math.radians(-170.0))
    assert math.isclose(step, math.radians(20.0), abs_tol=1e-9)
    assert math.isclose(progress.progress, math.radians(20.0), abs_tol=1e-9)

    step = progress.update(math.radians(-175.0))
    assert math.isclose(step, math.radians(-5.0), abs_tol=1e-9)
    assert math.isclose(
        progress.reverse_progress, math.radians(5.0), abs_tol=1e-9)


def test_frontier_ranking_prefers_forward_candidate_when_distance_matches():
    node = ExploreNode.__new__(ExploreNode)
    node._potential_scale = 3.0
    node._gain_scale = 1.0
    node._heading_scale = 0.75
    node._min_goal_dist_m = 0.30
    node._blacklist = []
    node._blacklist_radius = 0.35
    node._visited_frontier_goals = []
    node._frontier_revisit_radius = 0.60
    node._frontier_approach_goal = lambda frontier, _robot, _grid: (
        frontier.cx, frontier.cy)
    grid = _grid(resolution=0.05)
    forward = Frontier((1.0, 0.0), 10)
    sideways = Frontier((0.0, 1.0), 10)

    ranked = node._rank_frontiers(
        [sideways, forward], (0.0, 0.0), grid, robot_yaw=0.0)

    assert ranked[0] is forward


def test_frontier_ranking_does_not_resubmit_served_goal_neighborhood():
    node = ExploreNode.__new__(ExploreNode)
    node._potential_scale = 3.0
    node._gain_scale = 1.0
    node._heading_scale = 0.0
    node._min_goal_dist_m = 0.30
    node._blacklist = []
    node._blacklist_radius = 0.35
    node._visited_frontier_goals = [(1.0, 0.0)]
    node._frontier_revisit_radius = 0.60
    node._frontier_approach_goal = lambda frontier, _robot, _grid: (
        frontier.cx, frontier.cy)
    grid = _grid(resolution=0.05)
    repeated = Frontier((1.25, 0.0), 20)
    new_region = Frontier((0.0, 1.0), 10)

    ranked = node._rank_frontiers(
        [repeated, new_region], (0.0, 0.0), grid, robot_yaw=0.0)

    assert ranked == [new_region]


def test_circular_clearance_and_component_keep_goals_on_robot_side_of_wall():
    data = np.zeros((30, 50), dtype=np.int16)
    data[:, 25] = 100
    safe = circular_clearance_mask(data, clearance_cells=2)
    reachable = connected_mask(safe, (15, 10))

    assert reachable[15, 10]
    assert not reachable[15, 40]
    assert not np.any(safe[:, 23:28])


def test_circular_clearance_does_not_overblock_diagonal_corner():
    data = np.zeros((21, 21), dtype=np.int16)
    data[5, 5] = 100

    safe = circular_clearance_mask(data, clearance_cells=5)

    assert not safe[5, 10]       # exakt 5 Zellen vom Hindernis
    assert safe[10, 10]          # diagonal sqrt(50) > 5 Zellen


def test_measured_clearance_connects_narrowest_doorway():
    data = np.zeros((80, 120), dtype=np.int16)
    data[:, 60] = 100
    data[29:52, 60] = 0          # 0.69 m: Rasterung der gemessenen 0.68-m-Tuer
    safe = circular_clearance_mask(data, clearance_cells=10)  # ceil(0.28/0.03)

    reachable = connected_mask(safe, (40, 20))

    assert reachable[40, 100]


def test_farthest_coverage_goal_expands_away_from_measured_path():
    reachable = np.ones((21, 41), dtype=bool)
    covered = stamp_coverage(
        reachable.shape, [(row, 5) for row in range(21)], radius_cells=3)
    excluded = np.zeros_like(reachable)

    goal = farthest_uncovered_cell(reachable, covered, excluded)

    assert goal is not None
    assert goal[1] == 40


def test_coverage_plan_scales_with_reachable_room_area():
    def configured_node():
        node = ExploreNode.__new__(ExploreNode)
        node._coverage_clearance_m = 0.20
        node._coverage_visit_radius_m = 0.45
        node._coverage_min_goal_distance_m = 0.60
        node._blacklist_radius = 0.35
        node._blacklist = []
        node._coverage_path = [(1.5, 1.5)]
        return node

    small = _grid(width=60, height=60, resolution=0.05)
    small.data = [0] * (small.info.width * small.info.height)
    large = _grid(width=120, height=60, resolution=0.05)
    large.data = [0] * (large.info.width * large.info.height)
    node = configured_node()

    small_plan = node._coverage_plan(small, (1.5, 1.5))
    large_plan = node._coverage_plan(large, (1.5, 1.5))

    assert small_plan.goal_cell is not None
    assert large_plan.goal_cell is not None
    assert large_plan.reachable_area_m2 > small_plan.reachable_area_m2
    assert large_plan.ratio < small_plan.ratio


def test_map_frame_jump_is_not_interpolated_as_driven_path():
    node = ExploreNode.__new__(ExploreNode)
    node._coverage_path = [(0.0, 0.0)]
    node._coverage_path_sample_m = 0.10
    node._coverage_max_interpolation_gap_m = 0.35

    node._record_coverage_pose((1.0, 0.0))

    assert node._coverage_path == [(0.0, 0.0), (1.0, 0.0)]


def test_prealignment_uses_shortest_signed_turn_and_keeps_tolerance():
    node = ExploreNode.__new__(ExploreNode)
    node._prealign_enabled = True
    node._prealign_handoff_tolerance = 0.17
    node._prealign_stop_margin = 0.10
    node._prealign_speed = 0.12
    node._prealign_timeout = 180.0
    node._prealign_rate_check_after = 15.0
    node._prealign_min_average_rate = 0.01
    node._prealign_settle_s = 0.0
    node._prealign_max_passes = 3
    node._prealign_min_improvement = 0.04
    calls = []
    node._rotate_in_place = lambda angle, speed, timeout, **kwargs: (
        calls.append((angle, speed, timeout, kwargs)) or
        ('success', abs(angle)))
    node._robot_pose = lambda: (0.0, 0.0, -math.pi / 2.0 + 0.10)
    node.get_logger = lambda: SimpleNamespace(info=lambda *_args: None)

    status, achieved, error, residual = node._prealign_to_goal(
        0.0, -1.0, (0.0, 0.0, 0.0))

    assert status == 'success'
    assert math.isclose(error, -math.pi / 2.0, abs_tol=1e-9)
    assert math.isclose(calls[0][0], -(math.pi / 2.0 - 0.10), abs_tol=1e-9)
    assert math.isclose(achieved, math.pi / 2.0 - 0.10, abs_tol=1e-9)
    assert math.isclose(residual, -0.10, abs_tol=1e-9)
    assert calls[0][1:3] == (0.12, 180.0)
    assert calls[0][3]['rate_check_after_s'] == 15.0
    assert calls[0][3]['min_average_rate_radps'] == 0.01


def test_prealignment_rechecks_map_frame_and_retries_bounded():
    node = ExploreNode.__new__(ExploreNode)
    node._prealign_enabled = True
    node._prealign_handoff_tolerance = 0.17
    node._prealign_stop_margin = 0.10
    node._prealign_speed = 0.12
    node._prealign_timeout = 180.0
    node._prealign_rate_check_after = 15.0
    node._prealign_min_average_rate = 0.01
    node._prealign_settle_s = 0.0
    node._prealign_max_passes = 3
    node._prealign_min_improvement = 0.04
    map_poses = iter([
        (0.0, 0.0, -0.80),
        (0.0, 0.0, -1.48),
    ])
    node._robot_pose = lambda: next(map_poses)
    commands = []
    node._rotate_in_place = lambda angle, *_args, **_kwargs: (
        commands.append(angle) or ('success', abs(angle)))
    node.get_logger = lambda: SimpleNamespace(info=lambda *_args: None)

    status, _achieved, initial, residual = node._prealign_to_goal(
        0.0, -1.0, (0.0, 0.0, 0.0))

    assert status == 'success'
    assert math.isclose(initial, -math.pi / 2.0, abs_tol=1e-9)
    assert math.isclose(residual, -math.pi / 2.0 + 1.48, abs_tol=1e-9)
    assert len(commands) == 2
    assert commands[0] < 0.0
    assert commands[1] < 0.0


def test_prealignment_fails_closed_when_map_error_does_not_improve():
    node = ExploreNode.__new__(ExploreNode)
    node._prealign_enabled = True
    node._prealign_handoff_tolerance = 0.17
    node._prealign_stop_margin = 0.10
    node._prealign_speed = 0.12
    node._prealign_timeout = 180.0
    node._prealign_rate_check_after = 15.0
    node._prealign_min_average_rate = 0.01
    node._prealign_settle_s = 0.0
    node._prealign_max_passes = 3
    node._prealign_min_improvement = 0.04
    node._robot_pose = lambda: (0.0, 0.0, 0.0)
    commands = []
    node._rotate_in_place = lambda angle, *_args, **_kwargs: (
        commands.append(angle) or ('success', abs(angle)))
    node.get_logger = lambda: SimpleNamespace(info=lambda *_args: None)

    status, _achieved, initial, residual = node._prealign_to_goal(
        0.0, -1.0, (0.0, 0.0, 0.0))

    assert status == 'map_no_improvement'
    assert math.isclose(initial, -math.pi / 2.0, abs_tol=1e-9)
    assert math.isclose(residual, initial, abs_tol=1e-9)
    assert len(commands) == 1


def test_frontier_completion_is_success_after_safe_progress():
    success, message, reason = ExploreNode._classify_frontier_completion(
        frontiers_present=True, frontiers_visited=4)

    assert success is True
    assert 'Keine weiteren sicher erreichbaren Frontiers' in message
    assert reason == 'safe_complete'


def test_frontier_completion_still_fails_when_robot_never_departed():
    success, message, reason = ExploreNode._classify_frontier_completion(
        frontiers_present=True, frontiers_visited=0)

    assert success is False
    assert 'kein Ziel mit sicherem Abstand' in message
    assert reason is None


def test_frontier_completion_without_open_edges_is_complete():
    success, message, reason = ExploreNode._classify_frontier_completion(
        frontiers_present=False, frontiers_visited=0)

    assert success is True
    assert 'Keine offenen Frontiers mehr' in message
    assert reason == 'complete'


def test_real_defaults_are_bounded_and_navigation_has_no_recovery():
    config = (PACKAGE_ROOT / 'config' / 'explore_params.yaml').read_text()
    tree = (
        PACKAGE_ROOT / 'behavior_trees' /
        'navigate_to_pose_no_recovery.xml').read_text()
    source = (PACKAGE_ROOT / 'explore' / 'explore_node.py').read_text()

    assert 'goal_timeout_s: 150.0' in config
    assert 'overall_timeout_s: 1200.0' in config
    assert 'max_failed_goals: 6' in config
    assert 'frontier_revisit_radius_m: 0.60' in config
    assert 'max_frontier_goals: 20' in config
    assert 'initial_scan_enabled: true' in config
    assert 'initial_scan_angular_speed_radps: 0.12' in config
    assert 'scan_no_progress_timeout_s: 8.0' in config
    assert 'initial_scan_timeout_s: 210.0' in config
    assert 'scan_rate_check_after_s: 15.0' in config
    assert 'scan_min_average_rate_radps: 0.01' in config
    assert 'prealign_enabled: true' in config
    assert 'prealign_handoff_tolerance_rad: 0.17' in config
    assert 'prealign_max_passes: 3' in config
    assert 'prealign_angular_speed_radps: 0.12' in config
    assert 'prealign_timeout_s: 180.0' in config
    assert 'prealign_rate_check_after_s: 15.0' in config
    assert 'prealign_min_average_rate_radps: 0.01' in config
    assert 'coverage_enabled: true' in config
    assert 'coverage_target_ratio: 0.85' in config
    assert 'goal_clearance_m: 0.28' in config
    assert 'coverage_clearance_m: 0.28' in config
    assert 'coverage_max_interpolation_gap_m: 0.35' in config
    assert 'coverage_max_goals: 14' in config
    assert "'/explore/status_json'" in source
    assert '<ComputePathToPose' in tree
    assert '<FollowPath' in tree
    assert '<BackUp' not in tree
    assert '<Spin' not in tree
    assert '<ClearEntireCostmap' not in tree
    assert "return 'cancel_failed'" in source
    assert 'goal.behavior_tree = self._behavior_tree' in source
    assert 'RotationProgress' in source
    assert 'self._stop_scan_and_confirm()' in source
    assert 'self._prealign_to_goal(' in source
