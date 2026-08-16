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
    node._frontier_approach_goal = lambda frontier, _robot, _grid: (
        frontier.cx, frontier.cy)
    grid = _grid(resolution=0.05)
    forward = Frontier((1.0, 0.0), 10)
    sideways = Frontier((0.0, 1.0), 10)

    ranked = node._rank_frontiers(
        [sideways, forward], (0.0, 0.0), grid, robot_yaw=0.0)

    assert ranked[0] is forward


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

    assert 'overall_timeout_s: 600.0' in config
    assert 'max_failed_goals: 6' in config
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
