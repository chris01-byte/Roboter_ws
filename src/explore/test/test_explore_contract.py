import json
import math
from pathlib import Path
import sys
import threading
import time
from types import SimpleNamespace

import numpy as np
from action_msgs.msg import GoalStatus
from builtin_interfaces.msg import Time
from nav_msgs.msg import OccupancyGrid
import pytest
from std_msgs.msg import String
import yaml

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE_ROOT))

from explore.explore_node import (  # noqa: E402
    ExploreNode,
    Frontier,
    PortalPlan,
    RotationProgress,
    circular_clearance_mask,
    connected_mask,
    bounded_heading_increment,
    door_motion_consistency,
    door_steering_command,
    farthest_uncovered_cell,
    grid_line_is_clear,
    odom_freshness_state,
    relative_planar_motion,
    stamp_coverage,
    validated_shadow_connected_portal_feed,
    validated_shadow_frontier_task_feed,
    validated_shadow_raw_map_capacity,
    validated_passive_policy_enabled,
    validated_portal_monitor_enabled,
    validated_we_completion_configuration,
    validated_we_navigation_enabled,
)
from explore.portal_planning import CorridorCheck, PortalBridge  # noqa: E402
from explore.portal_memory import (  # noqa: E402
    Point2D,
    PortalConfirmationState,
    PortalMapContext,
    PortalSnapshot,
    TraversalDirection,
    TraversalEvent,
)
from explore.portal_task_evidence import PortalGoalCandidate  # noqa: E402
from explore.portal_traversal_runtime import (  # noqa: E402
    PortalTraversalRuntimeOutcome,
)
from explore.exploration_child_goal import ExplorationGoalIntent  # noqa: E402
from explore.exploration_policy import PolicyAssessmentState  # noqa: E402
from explore.exploration_completion import (  # noqa: E402
    CompletionAssessment,
    CompletionPolicy,
    ExplorationResultState,
    ReturnResultState,
)
from explore.frontier_task_resolution import (  # noqa: E402
    FrontierTaskResolutionState,
)
from explore.region_graph_shadow_lifecycle import (  # noqa: E402
    RegionGraphShadowLifecycle,
    RegionGraphShadowNotReadyError,
)
from explore.region_graph import RegionTaskKind, RegionTaskState  # noqa: E402
import explore.explore_node as explore_node_module  # noqa: E402


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
    assert frontier.goal_projected is False
    col, row = node._world_to_grid(goal[0], goal[1], grid.info)
    assert data[row, col] == 0
    assert col < 54


def test_frontier_goal_projects_to_robot_connected_safe_component():
    node = ExploreNode.__new__(ExploreNode)
    node._approach_dist_m = 0.20
    node._goal_clearance_m = 0.10
    node._goal_search_m = 0.10
    grid = _grid(width=100, height=60, resolution=0.05)
    data = np.full((60, 100), -1, dtype=np.int16)
    data[10:50, 5:45] = 0
    data[10:50, 55:95] = 0
    grid.data = data.ravel().tolist()
    frontier_x, frontier_y = node._grid_to_world(90, 30, grid.info)
    robot_x, robot_y = node._grid_to_world(10, 30, grid.info)
    frontier = Frontier((frontier_x, frontier_y), 20)

    goal = node._frontier_approach_goal(
        frontier, robot_xy=(robot_x, robot_y), grid=grid)

    assert goal is not None
    assert frontier.goal_projected is True
    goal_col, _goal_row = node._world_to_grid(goal[0], goal[1], grid.info)
    assert goal_col < 45


def test_costmap_projects_goal_to_navfn_start_component():
    node = ExploreNode.__new__(ExploreNode)
    node._global_costmap = _grid(width=100, height=40, resolution=0.05)
    costs = np.zeros((40, 100), dtype=np.int16)
    costs[:, 50] = 99
    node._global_costmap.data = costs.ravel().tolist()
    node._global_costmap_received_at = time.monotonic()
    node._map_timeout_s = 5.0
    node._global_frame = 'map'
    node._frontier_goal_max_cost = 90
    robot_xy = node._grid_to_world(10, 20, node._global_costmap.info)
    proposed_goal = node._grid_to_world(80, 20, node._global_costmap.info)
    desired_goal = node._grid_to_world(85, 20, node._global_costmap.info)

    result = node._costmap_reachable_goal(
        proposed_goal, desired_goal, robot_xy)

    assert result is not None
    (goal_x, goal_y), projected = result
    goal_col, _goal_row = node._world_to_grid(
        goal_x, goal_y, node._global_costmap.info)
    assert projected is True
    assert goal_col == 49


def _forward_stage_node(costmap):
    node = ExploreNode.__new__(ExploreNode)
    node._frontier_forward_stage_max_distance = 0.70
    node._frontier_forward_cone_half_angle = math.radians(20.0)
    node._global_costmap = costmap
    node._global_costmap_received_at = time.monotonic()
    node._map_timeout_s = 5.0
    node._global_frame = 'map'
    node._frontier_goal_max_cost = 90
    node._min_goal_dist_m = 0.30
    node._visited_frontier_goals = []
    node._frontier_revisit_radius = 0.60
    node._blacklist = []
    node._blacklist_radius = 0.35
    return node


def test_forward_costmap_stage_is_bounded_direct_and_in_cone():
    costmap = _grid(width=80, height=40, resolution=0.05)
    costmap.data = [0] * (costmap.info.width * costmap.info.height)
    node = _forward_stage_node(costmap)
    robot_x, robot_y = node._grid_to_world(20, 20, costmap.info)

    stage = node._forward_costmap_stage((robot_x, robot_y, 0.0))

    assert stage is not None
    assert stage.forward_staging is True
    distance = math.hypot(
        stage.goal_x - robot_x, stage.goal_y - robot_y)
    heading = math.atan2(
        stage.goal_y - robot_y, stage.goal_x - robot_x)
    assert 0.65 <= distance <= 0.725
    assert abs(heading) <= math.radians(20.0)


def test_forward_costmap_stage_rejects_blocked_short_component():
    costmap = _grid(width=80, height=40, resolution=0.05)
    costs = np.zeros((40, 80), dtype=np.int16)
    costs[:, 26] = 99
    costmap.data = costs.ravel().tolist()
    node = _forward_stage_node(costmap)
    robot_x, robot_y = node._grid_to_world(20, 20, costmap.info)

    stage = node._forward_costmap_stage((robot_x, robot_y, 0.0))

    assert stage is None


def test_forward_costmap_stage_requires_exact_robot_cell_to_be_traversable():
    costmap = _grid(width=80, height=40, resolution=0.05)
    costs = np.zeros((40, 80), dtype=np.int16)
    costs[20, 20] = 99
    costmap.data = costs.ravel().tolist()
    node = _forward_stage_node(costmap)
    robot_x, robot_y = node._grid_to_world(20, 20, costmap.info)

    stage = node._forward_costmap_stage((robot_x, robot_y, 0.0))

    assert stage is None


def test_grid_line_clear_rejects_single_lethal_cell():
    mask = np.ones((5, 8), dtype=bool)
    assert grid_line_is_clear(mask, (2, 1), (2, 6))
    mask[2, 4] = False
    assert not grid_line_is_clear(mask, (2, 1), (2, 6))


def test_rotation_progress_survives_pi_wrap_and_rejects_reverse_motion():
    progress = RotationProgress(math.radians(170.0), direction=1.0)
    step = progress.update(math.radians(-170.0))
    assert math.isclose(step, math.radians(20.0), abs_tol=1e-9)
    assert math.isclose(progress.progress, math.radians(20.0), abs_tol=1e-9)

    step = progress.update(math.radians(-175.0))
    assert math.isclose(step, math.radians(-5.0), abs_tol=1e-9)
    assert math.isclose(
        progress.reverse_progress, math.radians(5.0), abs_tol=1e-9)


def test_transient_odom_gap_pauses_before_recovery_deadline():
    assert odom_freshness_state(
        now=14.9, received_at=10.0, started_at=5.0,
        freshness_timeout_s=0.8, recovery_timeout_s=5.0) == 'pause'


def test_odom_gap_recovers_only_with_fresh_sample():
    assert odom_freshness_state(
        now=14.9, received_at=14.7, started_at=5.0,
        freshness_timeout_s=0.8, recovery_timeout_s=5.0) == 'fresh'


def test_odom_gap_expires_at_hard_recovery_limit():
    assert odom_freshness_state(
        now=15.1, received_at=10.0, started_at=5.0,
        freshness_timeout_s=0.8, recovery_timeout_s=5.0) == 'expired'


def test_relative_planar_motion_uses_encoder_start_heading():
    forward, lateral, heading = relative_planar_motion(
        (1.0, 2.0), math.pi / 2.0,
        (1.0, 2.9), math.pi / 2.0 + 0.04)

    assert math.isclose(forward, 0.9, abs_tol=1e-9)
    assert math.isclose(lateral, 0.0, abs_tol=1e-9)
    assert math.isclose(heading, 0.04, abs_tol=1e-9)


def test_relative_planar_motion_exposes_lateral_drift():
    forward, lateral, heading = relative_planar_motion(
        (0.0, 0.0), 0.0, (0.6, -0.05), -0.03)

    assert math.isclose(forward, 0.6, abs_tol=1e-9)
    assert math.isclose(lateral, -0.05, abs_tol=1e-9)
    assert math.isclose(heading, -0.03, abs_tol=1e-9)


def test_door_progress_tolerates_bounded_slip_but_rejects_false_success():
    assert door_motion_consistency(0.30, 0.63, 0.45, 0.15) == 'consistent'
    assert door_motion_consistency(0.10, 0.56, 0.45, 0.15) == 'encoder_slip'
    assert door_motion_consistency(0.50, 0.34, 0.45, 0.15) == (
        'localization_jump')
    # Encoderweg allein darf einen noch nicht physisch gefahrenen Zielweg nie
    # als konsistent ausgeben, sobald die begrenzte Schlupfreserve aufgebraucht
    # ist.
    assert door_motion_consistency(0.40, 0.90, 0.45, 0.15) == 'encoder_slip'


def test_door_steering_uses_localized_heading_and_centreline():
    # Positive Kartenabweichung bedeutet links: Kommando muss nach rechts.
    assert door_steering_command(0.08, 0.02, 0.8, 0.8, 0.10) < 0.0
    # Negative Kartenabweichung bedeutet rechts: Kommando muss nach links.
    assert door_steering_command(-0.08, -0.02, 0.8, 0.8, 0.10) > 0.0
    assert door_steering_command(0.30, 0.10, 0.8, 0.8, 0.10) == -0.10


def test_supervised_door_heading_filter_rejects_pose_jump():
    assert math.isclose(
        bounded_heading_increment(0.10, 0.14, 0.17), 0.04,
        abs_tol=1e-9)
    assert bounded_heading_increment(0.10, 0.40, 0.17) is None


def test_frontier_ranking_prefers_forward_candidate_when_distance_matches():
    node = ExploreNode.__new__(ExploreNode)
    node._potential_scale = 3.0
    node._gain_scale = 1.0
    node._heading_scale = 0.75
    node._frontier_forward_cone_half_angle = 0.0
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


def test_frontier_forward_cone_rejects_sideways_candidate():
    node = ExploreNode.__new__(ExploreNode)
    node._potential_scale = 3.0
    node._gain_scale = 1.0
    node._heading_scale = 0.0
    node._frontier_forward_cone_half_angle = math.radians(20.0)
    node._min_goal_dist_m = 0.30
    node._blacklist = []
    node._blacklist_radius = 0.35
    node._visited_frontier_goals = []
    node._frontier_revisit_radius = 0.60
    node._frontier_approach_goal = lambda frontier, _robot, _grid: (
        frontier.cx, frontier.cy)
    grid = _grid(resolution=0.05)
    forward = Frontier((1.0, math.tan(math.radians(10.0))), 10)
    sideways = Frontier((1.0, math.tan(math.radians(30.0))), 100)

    ranked = node._rank_frontiers(
        [sideways, forward], (0.0, 0.0), grid, robot_yaw=0.0)

    assert ranked == [forward]
    assert node._frontiers_rejected_by_heading == 1
    assert node._frontier_rank_stats == {
        'raw': 2,
        'approach_unavailable': 0,
        'too_near': 0,
        'visited': 0,
        'blacklisted': 0,
        'outside_forward_cone': 1,
        'accepted': 1,
        'projected': 0,
    }


def test_frontier_ranking_does_not_resubmit_served_goal_neighborhood():
    node = ExploreNode.__new__(ExploreNode)
    node._potential_scale = 3.0
    node._gain_scale = 1.0
    node._heading_scale = 0.0
    node._frontier_forward_cone_half_angle = 0.0
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


def test_unresolved_frontier_blocks_local_coverage_completion():
    assert ExploreNode._unresolved_frontier_count({
        'approach_unavailable': 1,
        'blacklisted': 2,
        'outside_forward_cone': 0,
        'visited': 5,
        'too_near': 3,
    }) == 3


def test_served_or_close_frontiers_do_not_block_coverage_completion():
    assert ExploreNode._unresolved_frontier_count({
        'approach_unavailable': 0,
        'blacklisted': 0,
        'outside_forward_cone': 0,
        'visited': 5,
        'too_near': 3,
    }) == 0


def _portal_plan(staging_x=0.40, target_x=1.00):
    bridge = PortalBridge(
        staging_row=10, staging_col=20,
        target_row=10, target_col=40,
        target_center_row=10.0, target_center_col=55.0,
        gap_m=0.50, traverse_distance_m=0.85,
        target_area_m2=1.20, staging_distance_m=staging_x)
    return PortalPlan(
        bridge=bridge,
        staging_xy=(staging_x, 0.0),
        target_xy=(target_x, 0.0),
        target_center_xy=(1.50, 0.0),
        midpoint_xy=((staging_x + target_x) / 2.0, 0.0))


def _portal_execution_node(plan):
    node = ExploreNode.__new__(ExploreNode)
    state = {'pose': (0.0, 0.0, 0.0)}
    node._robot_pose = lambda: state['pose']
    node._matching_portal_plan = lambda _reference, _pose: plan
    node._prealign_to_goal = lambda *_args, **_kwargs: (
        'skipped', 0.0, 0.0, 0.0)
    node._min_goal_dist_m = 0.30
    node._goal_timeout_s = 150.0
    node._portal_exit_margin = 0.25
    node._portal_max_traverse_distance = 1.0
    node._prealign_handoff_tolerance = 0.17
    node._portal_max_encoder_budget = 2.0
    node._portal_encoder_budget_factor = 2.2
    node._portal_encoder_budget_margin = 0.20
    node._door_speed = 0.08
    node._door_timeout = 120.0
    node.get_logger = lambda: SimpleNamespace(info=lambda *_args: None)

    def navigate(*_args, **_kwargs):
        state['pose'] = plan.staging_xy + (0.0,)
        return 'success'

    node._navigate_to = navigate
    return node


def test_portal_execution_stages_then_uses_lidar_with_bounded_wheel_budget():
    plan = _portal_plan()
    node = _portal_execution_node(plan)
    node._fresh_front_lidar_corridor = lambda distance: (
        'success', CorridorCheck(True, distance + 0.33, 2.4, 30))
    driven = {}

    def drive(distance, wheel_budget, speed, timeout, stop_requested):
        driven.update(
            distance=distance, wheel_budget=wheel_budget,
            speed=speed, timeout=timeout,
            stop_requested=stop_requested())
        return 'success', distance, distance + 0.1, 0.0, 0.0, 0.01, 0.9, 0

    node._drive_forward_lidar = drive

    status, midpoint = node._execute_portal_plan(plan)

    assert status == 'success'
    assert midpoint == plan.midpoint_xy
    assert math.isclose(driven['distance'], 0.85, abs_tol=1e-9)
    assert math.isclose(driven['wheel_budget'], 2.0, abs_tol=1e-9)
    assert driven['speed'] == 0.08
    assert driven['stop_requested'] is False


def test_portal_execution_never_drives_when_lidar_corridor_is_blocked():
    plan = _portal_plan(staging_x=0.10, target_x=0.60)
    node = _portal_execution_node(plan)
    node._fresh_front_lidar_corridor = lambda distance: (
        'corridor_blocked',
        CorridorCheck(False, distance + 0.33, 0.60, 20))
    node._drive_forward_lidar = lambda *_args, **_kwargs: (_ for _ in ()).throw(
        AssertionError('blocked corridor must not receive a drive command'))

    status, _midpoint = node._execute_portal_plan(plan)

    assert status == 'portal_corridor_blocked'


def _portal_connectivity_node(costs):
    node = ExploreNode.__new__(ExploreNode)
    node._global_costmap = _grid(width=80, height=40, resolution=0.05)
    node._global_costmap.data = costs.ravel().tolist()
    node._global_costmap_received_at = time.monotonic()
    node._map_timeout_s = 5.0
    node._global_frame = 'map'
    node._frontier_goal_max_cost = 90
    node._portal_exit_margin = 0.25
    return node


def test_portal_merge_selects_reachable_goal_beyond_original_target():
    costs = np.zeros((40, 80), dtype=np.int16)
    node = _portal_connectivity_node(costs)
    plan = _portal_plan()

    goal = node._connected_portal_exit_goal(plan, (0.10, 0.10, 0.0))

    assert goal is not None
    assert goal[0] >= plan.target_xy[0] + 0.20


def test_portal_merge_rejects_original_target_in_other_component():
    costs = np.zeros((40, 80), dtype=np.int16)
    costs[:, 12] = 99
    node = _portal_connectivity_node(costs)
    plan = _portal_plan()

    assert node._connected_portal_exit_goal(
        plan, (0.10, 0.10, 0.0)) is None


def test_portal_execution_hands_merged_geometry_back_to_nav2():
    plan = _portal_plan()
    node = _portal_execution_node(plan)
    state = {'pose': (0.0, 0.0, 0.0)}
    node._robot_pose = lambda: state['pose']
    node._matching_portal_plan = lambda *_args: None
    node._connected_portal_exit_goal = lambda *_args: (1.25, 0.0)
    goals = []

    def navigate(x, y, *_args, **_kwargs):
        goals.append((x, y))
        state['pose'] = (x, y, 0.0)
        return 'success'

    node._navigate_to = navigate
    node._drive_forward_lidar = lambda *_args, **_kwargs: (_ for _ in ()).throw(
        AssertionError('connected Costmap route must stay under Nav2'))

    status, midpoint = node._execute_portal_plan(plan)

    assert status == 'connected_success'
    assert midpoint == plan.midpoint_xy
    assert goals == [(1.25, 0.0)]


def test_portal_execution_still_fails_closed_when_geometry_is_unresolved():
    plan = _portal_plan()
    node = _portal_execution_node(plan)
    node._matching_portal_plan = lambda *_args: None
    node._connected_portal_exit_goal = lambda *_args: None

    status, _midpoint = node._execute_portal_plan(plan)

    assert status == 'portal_geometry_changed'


def test_nav_abort_after_measured_progress_allows_staged_replan():
    progress = ExploreNode._staging_progress_m(
        'aborted', (1.0, 2.0), (1.55, 2.02))

    assert progress is not None
    assert progress > 0.55


def test_nav_abort_without_departure_is_not_staging_progress():
    progress = ExploreNode._staging_progress_m(
        'aborted', (1.0, 2.0), (1.02, 2.01))

    assert progress is not None
    assert progress < 0.03


def test_non_aborted_navigation_never_becomes_staging_progress():
    assert ExploreNode._staging_progress_m(
        'timeout', (1.0, 2.0), (1.55, 2.02)) is None


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
    assert 'portal_crossing_enabled: true' in config
    assert 'portal_min_component_area_m2: 0.40' in config
    assert 'portal_max_traverse_distance_m: 1.00' in config
    assert 'portal_max_encoder_budget_m: 2.00' in config
    assert 'portal_lidar_corridor_half_width_m: 0.25' in config
    assert 'portal_front_overhang_m: 0.33' in config
    assert 'portal_stop_after_crossing: false' in config
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


def test_door_profile_uses_lidar_truth_and_encoder_only_as_budget():
    parameters = yaml.safe_load(
        (PACKAGE_ROOT / 'config' / 'door_test_params.yaml').read_text()
    )['explore_node']['ros__parameters']

    assert parameters['max_frontier_goals'] == 1
    assert parameters['max_failed_goals'] == 1
    assert parameters['coverage_enabled'] is False
    assert parameters['overall_timeout_s'] == 180.0
    assert parameters['initial_scan_enabled'] is False
    assert parameters['door_supervised_wheel_budget_mode'] is False
    assert parameters['door_lidar_motion_mode'] is True
    assert parameters['door_traverse_distance_m'] == 0.20
    assert parameters['door_encoder_wheel_budget_m'] == 0.60
    assert parameters['door_max_angular_speed_radps'] == 0.10
    assert parameters['door_max_heading_error_rad'] == 0.26
    assert parameters['door_max_lateral_error_m'] == 0.06

    normal_parameters = yaml.safe_load(
        (PACKAGE_ROOT / 'config' / 'explore_params.yaml').read_text()
    )['explore_node']['ros__parameters']
    assert normal_parameters['frontier_forward_cone_half_angle_rad'] == 0.0
    assert normal_parameters['frontier_forward_stage_max_distance_m'] == 0.0
    assert normal_parameters['door_traverse_distance_m'] == 0.0
    assert normal_parameters['door_supervised_wheel_budget_mode'] is False
    assert normal_parameters['door_lidar_motion_mode'] is False
    assert normal_parameters['door_encoder_wheel_budget_m'] == 0.0
    assert normal_parameters['door_lidar_scan_topic'] == '/scan_normiert'
    assert normal_parameters['door_lidar_scan_timeout_s'] <= 0.5
    assert (
        normal_parameters['door_lidar_recovery_timeout_s']
        > normal_parameters['door_lidar_scan_timeout_s'])
    assert normal_parameters['door_lidar_min_points'] >= 400
    assert normal_parameters['door_lidar_max_cost_m'] <= 0.08
    assert normal_parameters['door_lidar_min_support_ratio'] >= 0.45
    assert normal_parameters['door_command_topic'] == (
        '/cmd_vel_explore_direct_raw')
    assert normal_parameters['door_linear_speed_mps'] <= 0.08
    assert normal_parameters['door_max_angular_speed_radps'] <= 0.05
    assert normal_parameters['door_max_heading_error_rad'] <= 0.17
    assert normal_parameters['door_max_lateral_error_m'] <= 0.08
    assert normal_parameters['door_localization_timeout_s'] <= 0.8
    assert (
        normal_parameters['door_localization_recovery_timeout_s']
        > normal_parameters['door_localization_timeout_s'])
    assert normal_parameters['door_max_encoder_overrun_m'] <= 0.45
    assert normal_parameters['door_max_localization_lead_m'] <= 0.15
    assert normal_parameters['door_no_progress_timeout_s'] <= 12.0
    assert normal_parameters['portal_crossing_enabled'] is True
    assert normal_parameters['portal_min_component_area_m2'] >= 0.40
    assert normal_parameters['portal_min_gap_m'] > 0.0
    assert (
        normal_parameters['portal_max_gap_m']
        > normal_parameters['portal_min_gap_m'])
    assert normal_parameters['portal_max_traverse_distance_m'] <= 1.0
    assert (
        normal_parameters['portal_max_encoder_budget_m']
        > normal_parameters['portal_max_traverse_distance_m'])
    assert normal_parameters['portal_max_encoder_budget_m'] <= 2.0
    assert normal_parameters['portal_lidar_corridor_half_width_m'] >= 0.25
    assert normal_parameters['portal_front_overhang_m'] >= 0.33
    assert normal_parameters['portal_stop_after_crossing'] is False
    assert 0 <= normal_parameters['frontier_goal_max_cost'] < 99
    assert normal_parameters['frontier_stage_min_progress_m'] >= 0.30
    assert (
        normal_parameters['scan_odom_recovery_timeout_s']
        > normal_parameters['scan_odom_timeout_s'])
    assert normal_parameters['scan_odom_recovery_timeout_s'] == 5.0

    launch_source = (
        PACKAGE_ROOT / 'launch' / 'explore.launch.py').read_text()
    assert "'explore_params_overlay'" in launch_source
    assert 'params_overlay' in launch_source

    source = (PACKAGE_ROOT / 'explore' / 'explore_node.py').read_text()
    assert 'self._drive_forward_lidar(' in source
    assert "status = 'wheel_budget_exhausted'" in source
    assert "expected_status = 'success'" in source
    assert 'match_executor.submit(' in source
    assert 'match_executor.shutdown(wait=True, cancel_futures=True)' in source
    assert 'self._drive_forward_odom(' not in source


def test_region_graph_shadow_is_disabled_and_separate_by_default():
    parameters = yaml.safe_load(
        (PACKAGE_ROOT / 'config' / 'explore_params.yaml').read_text()
    )['explore_node']['ros__parameters']
    source = (PACKAGE_ROOT / 'explore' / 'explore_node.py').read_text()

    assert parameters['region_graph_shadow_enabled'] is False
    assert parameters['region_graph_shadow_raw_map_enabled'] is False
    assert parameters['region_graph_shadow_raw_map_capacity'] == 0
    assert parameters['region_graph_shadow_connected_portals_enabled'] is False
    assert parameters['region_graph_shadow_frontiers_enabled'] is False
    assert parameters['region_graph_shadow_portal_analysis_clearance_m'] == 0.20
    assert parameters['region_graph_shadow_portal_uncertainty_m'] == 0.05
    assert parameters['region_graph_shadow_portal_retry_limit'] == 30
    assert parameters['region_graph_shadow_session_id'] == ''
    assert parameters['region_graph_shadow_start_observation_id'] == ''
    assert parameters['region_graph_shadow_map_status_topic'] == (
        '/robot_map_manager/status_json')
    assert parameters['region_graph_shadow_status_topic'] == (
        '/explore/region_graph/status_json')
    assert parameters['wohnungserkundung_policy_enabled'] is False
    assert parameters['wohnungserkundung_navigation_enabled'] is False
    assert parameters['wohnungserkundung_accessible_scope_verified'] is False
    assert 'wohnungserkundung_scope_polygon_xy' not in parameters
    assert parameters['wohnungserkundung_completion_required_revisions'] == 3
    assert parameters['wohnungserkundung_evidence_clearance_m'] == 0.28
    assert parameters['wohnungserkundung_robot_seed_search_m'] == 0.75
    assert parameters['wohnungserkundung_task_cell_search_m'] == 0.60
    assert parameters['wohnungserkundung_information_radius_m'] == 0.75
    assert parameters['wohnungserkundung_evidence_max_cells'] == 262144
    assert parameters['wohnungserkundung_portal_monitor_enabled'] is False
    assert parameters['wohnungserkundung_traversal_front_overhang_m'] == 0.0
    assert parameters['wohnungserkundung_traversal_rear_overhang_m'] == 0.0
    assert parameters['wohnungserkundung_traversal_max_source_age_s'] == 0.0
    assert parameters['wohnungserkundung_traversal_minimum_pose_samples'] == 3
    assert parameters['wohnungserkundung_traversal_maximum_pose_samples'] == 256
    assert parameters['wohnungserkundung_traversal_max_pose_interval_s'] == 0.0
    assert parameters['region_graph_shadow_status_topic'] != (
        parameters['status_topic'])
    assert 'PortalPlanCandidate' not in source
    assert '.observe_portal_inventory(' in source


def test_passive_policy_requires_explicit_shadow_opt_in():
    assert validated_passive_policy_enabled(False, False) is False
    assert validated_passive_policy_enabled(True, False) is False
    assert validated_passive_policy_enabled(True, True) is True
    for values in ((False, True), (1, True), (True, 1)):
        with pytest.raises(ValueError):
            validated_passive_policy_enabled(*values)


def test_we_navigation_requires_complete_explicit_opt_in_chain():
    assert validated_we_navigation_enabled(
        True, True, True, True, True) is True
    assert validated_we_navigation_enabled(
        True, True, True, True, False) is False
    for values in (
            (False, True, True, True, True),
            (True, False, True, True, True),
            (True, True, False, True, True),
            (True, True, True, False, True),
            (True, True, True, True, 1)):
        with pytest.raises(ValueError):
            validated_we_navigation_enabled(*values)


def test_portal_monitor_requires_navigation_scope_and_independent_lidar():
    assert validated_portal_monitor_enabled(
        True, True, True, True) is True
    assert validated_portal_monitor_enabled(
        True, True, True, False) is False
    for values in (
            (False, True, True, True),
            (True, False, True, True),
            (True, True, False, True),
            (True, True, True, 1)):
        with pytest.raises(ValueError):
            validated_portal_monitor_enabled(*values)


def test_we_completion_requires_explicit_scope_and_positive_window():
    verified, policy = validated_we_completion_configuration(True, 3)
    assert verified is True
    assert policy.required_fresh_observations == 3
    verified, policy = validated_we_completion_configuration(False, 1)
    assert verified is False
    assert policy.required_fresh_observations == 1
    for values in ((1, 3), (False, 0), (False, True)):
        with pytest.raises(ValueError):
            validated_we_completion_configuration(*values)


def test_we_execute_branch_precedes_legacy_frontier_state_mutation():
    node = ExploreNode.__new__(ExploreNode)
    node._wohnungserkundung_navigation_enabled = True
    node._overall_timeout_s = 300.0
    node._min_frontier_m = 0.30
    node._return_to_start_p = False
    sentinel = object()
    handle = SimpleNamespace(request=SimpleNamespace(
        timeout_s=12.0,
        min_frontier_size_m=0.4,
        return_to_start=False,
    ))
    node._execute_wohnungserkundung_navigation = (
        lambda selected_handle, timeout: sentinel if (
            selected_handle is handle and timeout == 12.0
        ) else None)

    assert node._execute_reserved(handle) is sentinel


@pytest.mark.parametrize("state, terminal_method, success, complete", [
    (ExplorationResultState.COMPLETE_ACCESSIBLE, 'succeed', True, True),
    (ExplorationResultState.PARTIAL, 'succeed', False, False),
    (ExplorationResultState.ABORTED, 'abort', False, False),
    (ExplorationResultState.CANCELED, 'canceled', False, False),
])
def test_we_completion_projects_distinct_action_terminals(
        state, terminal_method, success, complete):
    calls = []
    handle = SimpleNamespace(
        succeed=lambda: calls.append('succeed'),
        abort=lambda: calls.append('abort'),
        canceled=lambda: calls.append('canceled'),
    )
    completion = CompletionAssessment(
        state=state,
        reason='test_terminal',
        qualifying_observation_count=2,
        required_observation_count=3,
        blocker_codes=(),
        map_saved=None,
        return_result=ReturnResultState.NOT_REQUESTED,
        terminal=True,
    )
    node = ExploreNode.__new__(ExploreNode)
    node._wohnungserkundung_runtime_lock = threading.Lock()
    node._wohnungserkundung_status_extension = {'schema_version': 1}
    node._coverage_complete = False
    node._map = None

    result = node._finish_wohnungserkundung_completion(
        handle, completion, 4)

    assert calls == [terminal_method]
    assert result.success is success
    assert result.frontiers_visited == 4
    assert node._coverage_complete is complete
    assert node._wohnungserkundung_status_extension[
        'runtime_result']['result_state'] == state.value


def test_we_runtime_budget_returns_successful_action_with_partial_payload(
        monkeypatch):
    calls = []
    clock = iter((10.0, 11.0))
    node = ExploreNode.__new__(ExploreNode)
    node._wohnungserkundung_runtime_lock = threading.Lock()
    node._wohnungserkundung_status_extension = {'schema_version': 1}
    node._wohnungserkundung_policy_snapshot = None
    node._wohnungserkundung_completion_policy = CompletionPolicy()
    node._wohnungserkundung_active_child = None
    node._wohnungserkundung_consumed_intent_id = None
    node._map = None
    node._publish_status = lambda state: calls.append(f'publish:{state}')
    handle = SimpleNamespace(
        is_cancel_requested=False,
        succeed=lambda: calls.append('succeed'),
        abort=lambda: calls.append('abort'),
        canceled=lambda: calls.append('canceled'),
    )
    monkeypatch.setattr(
        explore_node_module.time, 'monotonic', lambda: next(clock))
    monkeypatch.setattr(explore_node_module.rclpy, 'ok', lambda: True)

    result = node._execute_wohnungserkundung_navigation(handle, 0.5)

    assert result.success is False
    assert calls == ['publish:running', 'succeed']
    assert node._wohnungserkundung_completion_assessment.state is (
        ExplorationResultState.PARTIAL)


def test_we_runtime_completes_before_requesting_another_navigation_target(
        monkeypatch):
    calls = []
    completion = CompletionAssessment(
        state=ExplorationResultState.COMPLETE_ACCESSIBLE,
        reason='fresh_observation_window_satisfied',
        qualifying_observation_count=3,
        required_observation_count=3,
        blocker_codes=(),
        map_saved=None,
        return_result=ReturnResultState.NOT_REQUESTED,
        terminal=True,
    )
    node = ExploreNode.__new__(ExploreNode)
    node._wohnungserkundung_runtime_lock = threading.Lock()
    node._wohnungserkundung_status_extension = {'schema_version': 1}
    node._wohnungserkundung_policy_snapshot = object()
    node._wohnungserkundung_completion_policy = CompletionPolicy()
    node._wohnungserkundung_active_child = None
    node._wohnungserkundung_consumed_intent_id = None
    node._map = None
    node._publish_status = lambda state: calls.append(f'publish:{state}')
    node._observe_wohnungserkundung_completion = (
        lambda session, snapshot: (object(), completion))
    node._current_wohnungserkundung_navigation_target = lambda: (
        (_ for _ in ()).throw(
            AssertionError('Nach Vollabschluss darf kein Ziel entstehen')))
    handle = SimpleNamespace(
        is_cancel_requested=False,
        succeed=lambda: calls.append('succeed'),
        abort=lambda: calls.append('abort'),
        canceled=lambda: calls.append('canceled'),
    )
    monkeypatch.setattr(explore_node_module.time, 'monotonic', lambda: 10.0)
    monkeypatch.setattr(explore_node_module.rclpy, 'ok', lambda: True)

    result = node._execute_wohnungserkundung_navigation(handle, 5.0)

    assert result.success is True
    assert calls == ['publish:running', 'succeed']
    assert node._coverage_complete is True


def test_we_runtime_applies_new_positive_frontier_resolution(monkeypatch):
    candidate = SimpleNamespace(
        map_revision=7,
        task_id='task-frontier_000001',
    )
    disposition = object()
    pending = (candidate, disposition)
    correlation = SimpleNamespace(map_revision=8)
    raw_source = object()
    raw_map = SimpleNamespace(
        info=SimpleNamespace(
            width=2,
            height=2,
            resolution=0.1,
            origin=SimpleNamespace(
                position=SimpleNamespace(x=0.0, y=0.0, z=0.0),
                orientation=SimpleNamespace(
                    x=0.0, y=0.0, z=0.0, w=1.0),
            ),
        ),
        header=SimpleNamespace(
            frame_id='map',
            stamp=SimpleNamespace(sec=1, nanosec=2),
        ),
        data=[0, 0, 0, 0],
    )
    tracks = (object(),)
    evidence = SimpleNamespace(
        state=FrontierTaskResolutionState.RESOLVED,
        resolved=True,
        reason='resolved',
        task_id='task-frontier_000001',
        goal_map_revision=7,
        evidence_map_revision=8,
        checked_information_cells=4,
        unknown_information_cells=0,
    )
    applied = []
    node = ExploreNode.__new__(ExploreNode)
    node._wohnungserkundung_policy_enabled = True
    node._wohnungserkundung_runtime_lock = threading.Lock()
    node._wohnungserkundung_pending_frontier_resolution = pending
    node._wohnungserkundung_frontier_resolution_status = {
        'state': 'waiting_for_new_map'}
    node._wohnungserkundung_evidence_policy = object()
    node._region_graph_shadow_lock = threading.Lock()
    node._region_graph_shadow_fault = None
    node._region_graph_shadow_latest_raw_map = raw_map
    node._region_graph_shadow_latest_raw_source = raw_source
    node._region_graph_shadow_latest_correlation = correlation
    node._region_graph_shadow_frontier_processed_correlation = ('key',)
    node._shadow_correlation_key = lambda value: (
        ('key',) if value is correlation else None)
    node._shadow_source_matches_correlation = (
        lambda source, selected: source is raw_source and selected is correlation)
    node._region_graph_shadow = SimpleNamespace(
        frontier_tracks=lambda: tracks,
        resolve_frontier_task=lambda selected, **kwargs: (
            applied.append((selected, kwargs))),
    )
    node._fault_region_graph_shadow = lambda *args: (
        (_ for _ in ()).throw(AssertionError('kein Schattenfehler erwartet')))

    def build(selected_candidate, selected_disposition,
              selected_correlation, **kwargs):
        assert selected_candidate is candidate
        assert selected_disposition is disposition
        assert selected_correlation is correlation
        assert kwargs['tracks'] is tracks
        assert kwargs['cells'] == raw_map.data
        return evidence

    monkeypatch.setattr(
        explore_node_module,
        'build_frontier_task_resolution_evidence',
        build,
    )
    monkeypatch.setattr(explore_node_module.time, 'monotonic', lambda: 11.0)

    node._try_resolve_successful_wohnungserkundung_frontier()

    assert applied == [(evidence, {'observed_monotonic_seconds': 11.0})]
    assert node._wohnungserkundung_pending_frontier_resolution is None
    assert node._wohnungserkundung_frontier_resolution_status == {
        'state': 'resolved',
        'reason': 'resolved',
        'task_id': 'task-frontier_000001',
        'goal_map_revision': 7,
        'evidence_map_revision': 8,
        'checked_information_cells': 4,
        'unknown_information_cells': 0,
    }


def test_exact_unconsumed_we_target_is_withheld_after_revision_change():
    context = PortalMapContext('session-m3n', 'map-m3n', 'map')
    intent = SimpleNamespace(
        intent_id='intent-1', context=context, map_revision=7)
    candidate = SimpleNamespace(
        source_fingerprint='a' * 64,
        source_stamp_ns=123,
        frame_id='map',
    )
    node = ExploreNode.__new__(ExploreNode)
    node._region_graph_shadow_lock = threading.Lock()
    node._region_graph_shadow_latest_correlation = SimpleNamespace(
        context=context,
        map_revision=7,
        fingerprint='a' * 64,
        source_stamp_ns=123,
    )
    node._wohnungserkundung_runtime_lock = threading.Lock()
    node._wohnungserkundung_navigation_snapshot = (intent, candidate)
    node._wohnungserkundung_consumed_intent_id = None

    assert node._current_wohnungserkundung_navigation_target() == (
        intent, candidate)
    node._region_graph_shadow_latest_correlation = SimpleNamespace(
        context=context,
        map_revision=8,
        fingerprint='b' * 64,
        source_stamp_ns=456,
    )
    assert node._current_wohnungserkundung_navigation_target() is None
    node._region_graph_shadow_latest_correlation = SimpleNamespace(
        context=context,
        map_revision=7,
        fingerprint='a' * 64,
        source_stamp_ns=123,
    )
    node._wohnungserkundung_consumed_intent_id = 'intent-1'
    assert node._current_wohnungserkundung_navigation_target() is None


def test_existing_nav_client_receives_explicit_we_candidate_yaw():
    sent = []

    class ImmediateFuture:
        def __init__(self, value):
            self._value = value

        def result(self):
            return self._value

        def add_done_callback(self, callback):
            callback(self)
            return self

    result_future = ImmediateFuture(SimpleNamespace(
        status=GoalStatus.STATUS_SUCCEEDED))
    nav_handle = SimpleNamespace(
        accepted=True,
        get_result_async=lambda: result_future,
    )
    node = ExploreNode.__new__(ExploreNode)
    node._nav_client = SimpleNamespace(
        wait_for_server=lambda timeout_sec: timeout_sec == 5.0,
        send_goal_async=lambda goal: (
            sent.append(goal) or ImmediateFuture(nav_handle)),
    )
    node._global_frame = 'map'
    node._behavior_tree = '/fake/no_recovery.xml'
    node._cancel_timeout_s = 1.0
    node._robot_xy = lambda: (0.0, 0.0)
    node._record_coverage_pose = lambda _pose: None
    node.get_clock = lambda: SimpleNamespace(
        now=lambda: SimpleNamespace(
            to_msg=lambda: Time(sec=1, nanosec=2)))

    status = node._navigate_to(
        1.0, 2.0, 10.0, goal_yaw=math.pi / 2.0)

    assert status == 'success'
    assert len(sent) == 1
    assert sent[0].behavior_tree == '/fake/no_recovery.xml'
    assert math.isclose(
        sent[0].pose.pose.orientation.z,
        math.sin(math.pi / 4.0), abs_tol=1e-9)
    assert math.isclose(
        sent[0].pose.pose.orientation.w,
        math.cos(math.pi / 4.0), abs_tol=1e-9)


def test_existing_nav_client_calls_portal_progress_observer():
    observations = []

    class ImmediateFuture:
        def __init__(self, value):
            self._value = value

        def result(self):
            return self._value

        def add_done_callback(self, callback):
            callback(self)
            return self

    result_future = ImmediateFuture(SimpleNamespace(
        status=GoalStatus.STATUS_SUCCEEDED))
    nav_handle = SimpleNamespace(
        accepted=True,
        get_result_async=lambda: result_future,
    )
    node = ExploreNode.__new__(ExploreNode)
    node._nav_client = SimpleNamespace(
        wait_for_server=lambda timeout_sec: timeout_sec == 5.0,
        send_goal_async=lambda goal: ImmediateFuture(nav_handle),
    )
    node._global_frame = 'map'
    node._behavior_tree = '/fake/no_recovery.xml'
    node._cancel_timeout_s = 1.0
    node._robot_xy = lambda: (0.0, 0.0)
    node._record_coverage_pose = lambda _pose: None
    node.get_clock = lambda: SimpleNamespace(
        now=lambda: SimpleNamespace(
            to_msg=lambda: Time(sec=1, nanosec=2)))

    status = node._navigate_to(
        1.0,
        0.0,
        10.0,
        goal_yaw=0.0,
        progress_observer=lambda: observations.append(True) or True,
    )

    assert status == 'success'
    assert observations == [True, True]


def _portal_runtime_candidate():
    return PortalGoalCandidate(
        intent_id='intent-portal-8',
        task_id='task-portal_000001',
        region_id='region_000002',
        portal_id='portal_000001',
        direction=TraversalDirection.A_TO_B,
        context=PortalMapContext('session-node', 'map-node', 'map'),
        map_revision=8,
        frame_id='map',
        source_fingerprint='a' * 64,
        source_stamp_ns=8_000_000_000,
        scope_id='scope-node',
        scope_fingerprint='b' * 64,
        target_x_m=1.5,
        target_y_m=0.0,
        target_yaw_rad=0.0,
        target_row=0,
        target_col=2,
        route_length_m=2.0,
        path_cells=((0, 0), (0, 1), (0, 2)),
    )


def _portal_runtime_snapshot():
    return PortalSnapshot(
        portal_id='portal_000001',
        side_a=Point2D(0.0, 0.0),
        side_b=Point2D(1.0, 0.0),
        first_revision=6,
        last_revision=7,
        observation_count=2,
        evidence_count=2,
        qualified_evidence_count=2,
        confirmation_state=PortalConfirmationState.CONFIRMED,
        confirmed=True,
        confirmed_traversal_count=0,
    )


def _portal_runtime_node(monkeypatch, outcome):
    candidate = _portal_runtime_candidate()
    intent = ExplorationGoalIntent(
        intent_id=candidate.intent_id,
        task_id=candidate.task_id,
        region_id=candidate.region_id,
        context=candidate.context,
        map_revision=candidate.map_revision,
    )
    portal = _portal_runtime_snapshot()
    attempts = []
    traversal_events = []
    observations = []
    monitor = SimpleNamespace(
        observe=lambda: observations.append(True) or True,
        finish=lambda **kwargs: outcome,
    )
    node = ExploreNode.__new__(ExploreNode)
    node._wohnungserkundung_runtime_lock = threading.Lock()
    node._region_graph_shadow_lock = threading.Lock()
    node._wohnungserkundung_active_child = None
    node._wohnungserkundung_accessible_scope_verified = True
    node._wohnungserkundung_portal_monitor_factory = (
        lambda selected, current: monitor
        if selected is candidate and current is portal else None)
    node._wohnungserkundung_task_policy_session = SimpleNamespace(
        record_attempt=attempts.append)
    node._region_graph_shadow = SimpleNamespace(
        portal_snapshots=lambda: (portal,),
        record_validated_traversal=lambda event, **_kwargs: (
            traversal_events.append(event)
            or SimpleNamespace(graph=SimpleNamespace(entered=True))),
    )
    node._goal_timeout_s = 10.0
    node.get_clock = lambda: SimpleNamespace(
        now=lambda: SimpleNamespace(nanoseconds=9))

    def navigate(*args, **kwargs):
        assert kwargs['progress_observer'] is monitor.observe
        assert kwargs['progress_observer']() is True
        return 'success'

    node._navigate_to = navigate
    run = SimpleNamespace(
        navigation_status='success',
        disposition=SimpleNamespace(attempt=object()),
    )

    class NavigationSession:
        def run(self, selected_intent, selected_candidate, navigate_child,
                source_state, user_canceled, budget_exhausted):
            assert selected_intent is intent
            assert selected_candidate is candidate
            assert navigate_child(candidate, lambda: False) == 'success'
            return run

    result = node._run_wohnungserkundung_child(
        NavigationSession(),
        intent,
        candidate,
        SimpleNamespace(is_cancel_requested=False),
        lambda: False,
    )
    return (
        node, intent, candidate, run, attempts, traversal_events,
        observations, result)


def test_confirmed_portal_runtime_records_event_without_progress_attempt(
        monkeypatch):
    event = TraversalEvent(
        event_id='runtime-event-8',
        portal_id='portal_000001',
        context=_portal_runtime_candidate().context,
        map_revision=8,
        event_time_ns=8,
        direction=TraversalDirection.A_TO_B,
        crossing_confirmed=True,
    )
    outcome = PortalTraversalRuntimeOutcome(
        confirmed=True,
        reason='full_chassis_crossing_confirmed',
        sample_count=4,
        assessment=SimpleNamespace(traversal_event=event),
    )

    (node, intent, _candidate, run, attempts, traversal_events,
     observations, result) = _portal_runtime_node(monkeypatch, outcome)

    assert result == (run, outcome)
    assert attempts == []
    assert traversal_events == [event]
    assert observations == [True]
    assert node._wohnungserkundung_consumed_intent_id == intent.intent_id
    assert node._wohnungserkundung_active_child is None
    assert node._wohnungserkundung_portal_traversal_status['state'] == (
        'confirmed')


def test_unconfirmed_portal_runtime_records_retry_instead_of_event(
        monkeypatch):
    outcome = PortalTraversalRuntimeOutcome(
        confirmed=False,
        reason='chassis_exit_not_complete',
        sample_count=4,
        assessment=None,
    )

    (node, _intent, _candidate, _run, attempts, traversal_events,
     _observations, _result) = _portal_runtime_node(monkeypatch, outcome)

    assert traversal_events == []
    assert len(attempts) == 1
    assert attempts[0].outcome.value == 'retryable_failure'
    assert attempts[0].reason == (
        'portal_traversal_unconfirmed:chassis_exit_not_complete')
    assert attempts[0].retry_not_before_revision == 9
    assert node._wohnungserkundung_portal_traversal_status['state'] == (
        'unconfirmed')


def test_portal_monitor_adapter_uses_fresh_retained_scan(monkeypatch):
    node = ExploreNode.__new__(ExploreNode)
    node._door_lidar_scan_timeout = 0.5
    node._door_lidar_max_range = 4.0
    node._door_lidar_min_points = 200
    node._door_lidar_scan_snapshot = lambda: {
        'ranges': np.ones(240, dtype=np.float64),
        'angle_min': -1.2,
        'angle_increment': 0.01,
        'range_min': 0.1,
        'range_max': 8.0,
        'frame_id': 'laser',
        'key': (7, 8, 240),
        'received_at': 10.0,
    }
    node._door_lidar_mount = lambda frame: (
        (0.1, 0.0, 0.0) if frame == 'laser' else None)
    monkeypatch.setattr(explore_node_module.time, 'monotonic', lambda: 10.1)

    sample = node._wohnungserkundung_frozen_scan_sample()

    assert sample.sample_id == 'we-scan-7-8-240'
    assert sample.stamp_ns == 7_000_000_008
    assert sample.points.shape == (240, 2)
    assert sample.points.flags.writeable is False


def test_portal_monitor_adapter_reads_map_pose_at_exact_scan_time():
    candidate = _portal_runtime_candidate()
    correlation = SimpleNamespace(
        context=candidate.context,
        map_revision=candidate.map_revision,
        fingerprint=candidate.source_fingerprint,
        source_stamp_ns=candidate.source_stamp_ns,
    )
    requested_times = []
    transform = SimpleNamespace(transform=SimpleNamespace(
        translation=SimpleNamespace(x=0.25, y=-0.1),
        rotation=SimpleNamespace(x=0.0, y=0.0, z=0.0, w=1.0),
    ))
    node = ExploreNode.__new__(ExploreNode)
    node._region_graph_shadow_lock = threading.Lock()
    node._region_graph_shadow_latest_correlation = correlation
    node._global_frame = 'map'
    node._robot_base_frame = 'base_link'
    node._tf_buffer = SimpleNamespace(
        lookup_transform=lambda target, source, stamp: (
            requested_times.append((target, source, stamp.nanoseconds))
            or transform))

    pose = node._wohnungserkundung_exact_time_pose(
        candidate, 7_000_000_008)

    assert requested_times == [('map', 'base_link', 7_000_000_008)]
    assert pose.context == candidate.context
    assert pose.map_revision == candidate.map_revision
    assert pose.stamp_ns == 7_000_000_008
    assert (pose.x, pose.y, pose.yaw) == (0.25, -0.1, 0.0)


def test_disabled_region_graph_shadow_creates_no_interface():
    node = ExploreNode.__new__(ExploreNode)
    node._region_graph_shadow_enabled = False
    node.create_publisher = lambda *args, **kwargs: (_ for _ in ()).throw(
        AssertionError('Publisher darf deaktiviert nicht entstehen'))
    node.create_subscription = lambda *args, **kwargs: (_ for _ in ()).throw(
        AssertionError('Subscription darf deaktiviert nicht entstehen'))
    node.create_timer = lambda *args, **kwargs: (_ for _ in ()).throw(
        AssertionError('Timer darf deaktiviert nicht entstehen'))

    node._initialize_region_graph_shadow()

    assert not hasattr(node, '_region_graph_shadow')


def test_enabled_region_graph_shadow_owns_exact_ros_interfaces(monkeypatch):
    lifecycle_calls = []
    interface_calls = []

    class FakeLifecycle:
        def __init__(self, *args, **kwargs):
            lifecycle_calls.append((args, kwargs))

    node = ExploreNode.__new__(ExploreNode)
    node._region_graph_shadow_enabled = True
    node._region_graph_shadow_raw_map_join_capacity = None
    node._region_graph_shadow_session_id = 'session-7'
    node._region_graph_shadow_start_observation_id = 'start-7'
    node._region_graph_shadow_map_status_topic = (
        '/robot_map_manager/status_json')
    node._region_graph_shadow_status_topic = (
        '/explore/region_graph/status_json')
    node._global_frame = 'map'
    node._cb = object()
    node.create_publisher = lambda *args, **kwargs: interface_calls.append(
        ('publisher', args, kwargs)) or object()
    node.create_subscription = lambda *args, **kwargs: interface_calls.append(
        ('subscription', args, kwargs)) or object()
    node.create_timer = lambda *args, **kwargs: interface_calls.append(
        ('timer', args, kwargs)) or object()
    monkeypatch.setattr(
        explore_node_module, 'RegionGraphShadowLifecycle', FakeLifecycle)

    node._initialize_region_graph_shadow()

    assert lifecycle_calls == [(('session-7', 'map', 'start-7'), {})]
    assert [call[0] for call in interface_calls] == [
        'publisher', 'subscription', 'timer']
    publisher_qos = interface_calls[0][1][2]
    subscription_qos = interface_calls[1][1][3]
    assert publisher_qos.history.name == 'KEEP_LAST'
    assert publisher_qos.depth == 1
    assert publisher_qos.durability.name == 'TRANSIENT_LOCAL'
    assert publisher_qos.reliability.name == 'RELIABLE'
    assert subscription_qos is publisher_qos
    assert interface_calls[1][2]['callback_group'] is node._cb
    assert interface_calls[2][1][0] == 1.0
    assert interface_calls[2][2]['callback_group'] is node._cb
    assert isinstance(node._region_graph_shadow_lock, type(threading.Lock()))
    assert node._region_graph_shadow_fault is None


def test_shadow_raw_map_configuration_requires_double_opt_in_and_capacity():
    assert validated_shadow_raw_map_capacity(False, False, 0) is None
    assert validated_shadow_raw_map_capacity(True, False, 0) is None
    assert validated_shadow_raw_map_capacity(True, True, 3) == 3
    for values in (
            (False, True, 3),
            (True, True, 0),
            (True, False, 3),
            (1, True, 3),
            (True, 1, 3),
            (True, True, True),
            (True, True, -1)):
        try:
            validated_shadow_raw_map_capacity(*values)
        except ValueError:
            pass
        else:
            raise AssertionError(f'Ungueltige Konfiguration akzeptiert: {values}')


def test_enabled_shadow_passes_only_explicit_raw_map_capacity(monkeypatch):
    lifecycle_calls = []

    class FakeLifecycle:
        def __init__(self, *args, **kwargs):
            lifecycle_calls.append((args, kwargs))

    node = ExploreNode.__new__(ExploreNode)
    node._region_graph_shadow_enabled = True
    node._region_graph_shadow_raw_map_join_capacity = 3
    node._region_graph_shadow_session_id = 'session-raw'
    node._region_graph_shadow_start_observation_id = 'start-raw'
    node._region_graph_shadow_map_status_topic = '/map-status'
    node._region_graph_shadow_status_topic = '/shadow-status'
    node._global_frame = 'map'
    node._cb = object()
    node.create_publisher = lambda *args, **kwargs: object()
    node.create_subscription = lambda *args, **kwargs: object()
    node.create_timer = lambda *args, **kwargs: object()
    monkeypatch.setattr(
        explore_node_module, 'RegionGraphShadowLifecycle', FakeLifecycle)

    node._initialize_region_graph_shadow()

    assert lifecycle_calls == [(
        ('session-raw', 'map', 'start-raw'),
        {'raw_map_capacity': 3},
    )]


def test_enabled_frontier_feed_passes_existing_revisit_radius(monkeypatch):
    lifecycle_calls = []

    class FakeLifecycle:
        def __init__(self, *args, **kwargs):
            lifecycle_calls.append((args, kwargs))

    node = ExploreNode.__new__(ExploreNode)
    node._region_graph_shadow_enabled = True
    node._region_graph_shadow_raw_map_join_capacity = 2
    node._region_graph_shadow_frontier_task_feed = True
    node._region_graph_shadow_connected_portal_feed = False
    node._region_graph_shadow_raw_event_feed = True
    node._frontier_revisit_radius = 0.75
    node._region_graph_shadow_session_id = 'session-frontier'
    node._region_graph_shadow_start_observation_id = 'start-frontier'
    node._region_graph_shadow_map_status_topic = '/map-status'
    node._region_graph_shadow_status_topic = '/shadow-status'
    node._global_frame = 'map'
    node._cb = object()
    node.create_publisher = lambda *args, **kwargs: object()
    node.create_subscription = lambda *args, **kwargs: object()
    node.create_timer = lambda *args, **kwargs: object()
    monkeypatch.setattr(
        explore_node_module, 'RegionGraphShadowLifecycle', FakeLifecycle)

    node._initialize_region_graph_shadow()

    args, kwargs = lifecycle_calls[0]
    assert args == ('session-frontier', 'map', 'start-frontier')
    assert kwargs['raw_map_capacity'] == 2
    assert kwargs['frontier_policy'].association_radius_m == 0.75
    assert hasattr(node, '_region_graph_shadow_frontier_processed_correlation')
    assert not hasattr(node, '_region_graph_shadow_processed_correlation')


def test_region_graph_map_callback_passes_one_monotonic_timestamp(monkeypatch):
    accepted = []
    clock_calls = []
    correlation = object()
    node = ExploreNode.__new__(ExploreNode)
    node._region_graph_shadow_lock = threading.Lock()
    node._region_graph_shadow_fault = None
    node._region_graph_shadow_connected_portal_feed = True
    node._region_graph_shadow_latest_correlation = None
    node._region_graph_shadow_portal_retry_count = 3
    node._region_graph_shadow = SimpleNamespace(
        accept_map_status_json=lambda text, **kwargs: accepted.append(
            (text, kwargs)) or SimpleNamespace(
                raw_map_correlation=correlation))
    monkeypatch.setattr(
        explore_node_module.time,
        'monotonic',
        lambda: clock_calls.append(True) or 42.5,
    )

    node._on_region_graph_map_status(SimpleNamespace(data='{"schema": 1}'))

    assert accepted == [(
        '{"schema": 1}', {'received_monotonic_seconds': 42.5})]
    assert len(clock_calls) == 1
    assert node._region_graph_shadow_fault is None
    assert node._region_graph_shadow_latest_correlation is correlation
    assert node._region_graph_shadow_portal_retry_count == 0


def test_disabled_raw_map_shadow_preserves_map_without_factory(monkeypatch):
    node = ExploreNode.__new__(ExploreNode)
    node._region_graph_shadow_raw_map_enabled = False
    message = _grid(width=2, height=2)
    monkeypatch.setattr(explore_node_module.time, 'monotonic', lambda: 7.0)
    monkeypatch.setattr(
        explore_node_module,
        'raw_map_portal_source_from_values',
        lambda **kwargs: (_ for _ in ()).throw(
            AssertionError('Deaktivierter Pfad darf keinen Digest bilden')),
    )

    node._on_map(message)

    assert node._map is message
    assert node._map_received_at == 7.0


def test_enabled_raw_map_snapshot_is_built_outside_and_joined_inside_lock(
        monkeypatch):
    factory_calls = []
    lifecycle_calls = []
    clock_values = iter((10.0, 11.0))
    lock = threading.Lock()
    source = object()
    correlation = object()
    message = _grid(width=2, height=2, resolution=0.1)
    message.header.frame_id = ' map '
    message.header.stamp.sec = 12
    message.header.stamp.nanosec = 34
    message.info.origin.position.x = 1.5

    def build_source(**kwargs):
        assert not lock.locked()
        assert node._map is message
        assert node._map_received_at == 10.0
        factory_calls.append(kwargs)
        return source

    def accept_source(value, **kwargs):
        assert lock.locked()
        lifecycle_calls.append((value, kwargs))
        return SimpleNamespace(raw_map_correlation=correlation)

    node = ExploreNode.__new__(ExploreNode)
    node._region_graph_shadow_raw_map_enabled = True
    node._region_graph_shadow_lock = lock
    node._region_graph_shadow_fault = None
    node._region_graph_shadow_connected_portal_feed = True
    node._region_graph_shadow_latest_raw_map = None
    node._region_graph_shadow_latest_raw_source = None
    node._region_graph_shadow_latest_correlation = None
    node._region_graph_shadow_portal_retry_count = 4
    node._region_graph_shadow = SimpleNamespace(
        accept_raw_map_source=accept_source)
    monkeypatch.setattr(
        explore_node_module.time, 'monotonic', lambda: next(clock_values))
    monkeypatch.setattr(
        explore_node_module, 'raw_map_portal_source_from_values', build_source)

    node._on_map(message)

    assert factory_calls == [{
        'width': 2,
        'height': 2,
        'resolution': 0.1,
        'frame_id': 'map',
        'origin': (1.5, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0),
        'cells': message.data,
        'source_stamp_ns': 12_000_000_034,
    }]
    assert lifecycle_calls == [(
        source, {'received_monotonic_seconds': 11.0})]
    assert node._region_graph_shadow_fault is None
    assert node._region_graph_shadow_latest_raw_map is message
    assert node._region_graph_shadow_latest_raw_source is source
    assert node._region_graph_shadow_latest_correlation is correlation
    assert node._region_graph_shadow_portal_retry_count == 0


def test_invalid_raw_map_faults_only_shadow_after_preserving_map(monkeypatch):
    errors = []
    factory_calls = []
    node = ExploreNode.__new__(ExploreNode)
    node._region_graph_shadow_raw_map_enabled = True
    node._region_graph_shadow_lock = threading.Lock()
    node._region_graph_shadow_fault = None
    node._region_graph_shadow = SimpleNamespace(
        accept_raw_map_source=lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError('Ungueltige Quelle darf den Besitzer nicht erreichen')))
    node.get_logger = lambda: SimpleNamespace(error=errors.append)
    monkeypatch.setattr(explore_node_module.time, 'monotonic', lambda: 8.0)

    def reject_source(**kwargs):
        factory_calls.append(kwargs)
        raise ValueError('invalid cells')

    monkeypatch.setattr(
        explore_node_module, 'raw_map_portal_source_from_values', reject_source)
    first = _grid(width=2, height=2)
    second = _grid(width=3, height=1)

    node._on_map(first)
    node._on_map(second)

    assert node._map is second
    assert node._map_received_at == 8.0
    assert len(factory_calls) == 1
    assert len(errors) == 1
    assert 'Rohkarte: ValueError: invalid cells' in (
        node._region_graph_shadow_fault)


def test_raw_map_lifecycle_error_faults_only_shadow(monkeypatch):
    errors = []
    message = _grid(width=1, height=1)
    node = ExploreNode.__new__(ExploreNode)
    node._region_graph_shadow_raw_map_enabled = True
    node._region_graph_shadow_lock = threading.Lock()
    node._region_graph_shadow_fault = None
    node._region_graph_shadow = SimpleNamespace(
        accept_raw_map_source=lambda *args, **kwargs: (_ for _ in ()).throw(
            ValueError('join rejected')))
    node.get_logger = lambda: SimpleNamespace(error=errors.append)
    times = iter((20.0, 21.0))
    monkeypatch.setattr(
        explore_node_module.time, 'monotonic', lambda: next(times))
    monkeypatch.setattr(
        explore_node_module,
        'raw_map_portal_source_from_values',
        lambda **kwargs: object(),
    )

    node._on_map(message)

    assert node._map is message
    assert node._map_received_at == 20.0
    assert len(errors) == 1
    assert 'Rohkarte: ValueError: join rejected' in (
        node._region_graph_shadow_fault)


def test_raw_map_callback_reaches_real_pure_lifecycle(monkeypatch):
    node = ExploreNode.__new__(ExploreNode)
    node._region_graph_shadow_raw_map_enabled = True
    node._region_graph_shadow_lock = threading.Lock()
    node._region_graph_shadow_fault = None
    node._region_graph_shadow = RegionGraphShadowLifecycle(
        'session-runtime-contract',
        'map',
        'start-runtime-contract',
        raw_map_capacity=2,
    )
    times = iter((30.0, 31.0))
    monkeypatch.setattr(
        explore_node_module.time, 'monotonic', lambda: next(times))

    node._on_map(_grid(width=2, height=2))

    diagnostics = node._region_graph_shadow.raw_map_diagnostics
    assert diagnostics.source_observations == 1
    assert diagnostics.pending_sources == 1
    assert diagnostics.emitted_correlations == 0
    assert node._region_graph_shadow_fault is None


def test_region_graph_map_error_permanently_faults_only_shadow(monkeypatch):
    lifecycle_calls = []
    clock_calls = []
    errors = []

    def reject(*args, **kwargs):
        lifecycle_calls.append((args, kwargs))
        raise ValueError('epoch changed')

    node = ExploreNode.__new__(ExploreNode)
    node._region_graph_shadow_lock = threading.Lock()
    node._region_graph_shadow_fault = None
    node._region_graph_shadow = SimpleNamespace(
        accept_map_status_json=reject)
    node.get_logger = lambda: SimpleNamespace(error=errors.append)
    monkeypatch.setattr(
        explore_node_module.time,
        'monotonic',
        lambda: clock_calls.append(True) or 8.0,
    )
    message = SimpleNamespace(data='invalid')

    node._on_region_graph_map_status(message)
    node._on_region_graph_map_status(message)

    assert len(lifecycle_calls) == 1
    assert len(clock_calls) == 1
    assert len(errors) == 1
    assert 'ValueError: epoch changed' in node._region_graph_shadow_fault


def test_region_graph_status_waits_without_fault_or_publication(monkeypatch):
    publications = []
    clock_calls = []

    def not_ready(**kwargs):
        raise RegionGraphShadowNotReadyError('waiting')

    node = ExploreNode.__new__(ExploreNode)
    node._region_graph_shadow_lock = threading.Lock()
    node._region_graph_shadow_fault = None
    node._region_graph_shadow = SimpleNamespace(build_status=not_ready)
    node._region_graph_shadow_pub = SimpleNamespace(
        publish=publications.append)
    monkeypatch.setattr(
        explore_node_module.time,
        'monotonic',
        lambda: clock_calls.append(True) or 9.0,
    )

    node._publish_region_graph_shadow_status()

    assert len(clock_calls) == 1
    assert publications == []
    assert node._region_graph_shadow_fault is None


def test_region_graph_status_publishes_one_string_per_tick(monkeypatch):
    build_calls = []
    publications = []
    clock_calls = []
    node = ExploreNode.__new__(ExploreNode)
    node._region_graph_shadow_lock = threading.Lock()
    node._region_graph_shadow_fault = None
    node._region_graph_shadow = SimpleNamespace(
        build_status=lambda **kwargs: build_calls.append(kwargs) or (
            SimpleNamespace(serialized='{}', source=object())))
    node._region_graph_shadow_pub = SimpleNamespace(
        publish=publications.append)
    monkeypatch.setattr(
        explore_node_module.time,
        'monotonic',
        lambda: clock_calls.append(True) or 11.0,
    )

    node._publish_region_graph_shadow_status()

    assert build_calls == [{'now_monotonic_seconds': 11.0}]
    assert len(clock_calls) == 1
    assert len(publications) == 1
    assert isinstance(publications[0], String)
    assert publications[0].data == '{}'


def test_passive_policy_assesses_snapshot_without_changing_shadow_output(
        monkeypatch):
    assessment = SimpleNamespace(
        eligible_task_ids=(),
        state=PolicyAssessmentState.WAITING_FOR_FRESH_SOURCES,
    )
    source = SimpleNamespace(
        source_map_revision=7,
        context=SimpleNamespace(frame_id='map'),
    )
    stateful = object()
    extension = {"schema_version": 1, "mode": "passive_shadow"}
    publications = []
    assessed = []
    node = ExploreNode.__new__(ExploreNode)
    node._region_graph_shadow_lock = threading.Lock()
    node._region_graph_shadow_fault = None
    node._region_graph_shadow = SimpleNamespace(
        build_status=lambda **kwargs: SimpleNamespace(
            serialized='{"shadow":true}', source=source))
    node._region_graph_shadow_pub = SimpleNamespace(
        publish=publications.append)
    node._wohnungserkundung_policy_enabled = True
    node._wohnungserkundung_policy_fault = None
    node._wohnungserkundung_runtime_lock = threading.Lock()
    node._wohnungserkundung_navigation_snapshot = None
    node._wohnungserkundung_active_child = None
    node._wohnungserkundung_consumed_intent_id = None
    node._wohnungserkundung_stateful_assessment = None
    node._wohnungserkundung_task_policy_session = SimpleNamespace(
        latest_assessment_revision=None,
        assess=lambda selected_source, selected_availability,
        selected_utilities: stateful if (
            selected_source is source
            and selected_availability == ()
            and selected_utilities == ()
        ) else None,
    )

    def assess_outside_shadow_lock(value, task_availability):
        assert not node._region_graph_shadow_lock.locked()
        assert task_availability == ()
        assessed.append(value)
        return assessment

    monkeypatch.setattr(
        explore_node_module, 'assess_exploration_policy',
        assess_outside_shadow_lock)
    monkeypatch.setattr(
        explore_node_module, 'build_passive_we_status_extension',
        lambda value, **kwargs: (
            extension if value is assessment and kwargs == {
                'utility_scores': (), 'stateful': stateful} else None))
    monkeypatch.setattr(
        explore_node_module, 'score_task_utilities',
        lambda task_ids, evidence, revision: () if (
            task_ids == () and evidence == () and revision == 7
        ) else (_ for _ in ()).throw(AssertionError('unerwartete Bewertung')))
    monkeypatch.setattr(explore_node_module.time, 'monotonic', lambda: 11.0)

    node._publish_region_graph_shadow_status()

    assert assessed == [source]
    assert node._wohnungserkundung_status_extension is extension
    assert node._wohnungserkundung_policy_fault is None
    assert len(publications) == 1
    assert publications[0].data == '{"shadow":true}'


def test_passive_runtime_builds_frontier_evidence_outside_shadow_lock(
        monkeypatch):
    raw_map = SimpleNamespace(
        info=SimpleNamespace(
            width=2,
            height=2,
            resolution=0.1,
            origin=SimpleNamespace(
                position=SimpleNamespace(x=0.0, y=0.0, z=0.0),
                orientation=SimpleNamespace(
                    x=0.0, y=0.0, z=0.0, w=1.0),
            ),
        ),
        header=SimpleNamespace(
            frame_id='map',
            stamp=SimpleNamespace(sec=1, nanosec=2),
        ),
        data=[0, 0, 0, -1],
    )
    task = SimpleNamespace(
        task_id='task-1', state=RegionTaskState.OPEN)
    source = SimpleNamespace(
        context=SimpleNamespace(frame_id='map'),
        source_map_revision=7,
        graph=SimpleNamespace(tasks=(task,)),
    )
    correlation = SimpleNamespace(
        map_revision=7,
        context=source.context,
        fingerprint='a' * 64,
        source_stamp_ns=1000000002,
    )
    raw_source = object()
    tracks = (object(),)
    availability = (object(),)
    utilities = (object(),)
    scores = (object(),)
    assessment = SimpleNamespace(
        eligible_task_ids=('task-1',),
        state=PolicyAssessmentState.READY_WITH_TASKS,
    )
    stateful = object()
    intent = SimpleNamespace(intent_id='intent-1', task_id='task-1')
    candidate = object()
    evidence = SimpleNamespace(
        source_map_revision=7,
        availability=availability,
        utilities=utilities,
        robot_seed_available=True,
        current_frontier_track_count=1,
    )
    publications = []
    evidence_builds = []
    stateful_builds = []
    node = ExploreNode.__new__(ExploreNode)
    node._region_graph_shadow_lock = threading.Lock()
    node._region_graph_shadow_fault = None
    node._region_graph_shadow_frontier_task_feed = True
    node._region_graph_shadow_latest_raw_map = raw_map
    node._region_graph_shadow_latest_correlation = correlation
    node._region_graph_shadow_latest_raw_source = raw_source
    node._region_graph_shadow = SimpleNamespace(
        build_status=lambda **kwargs: SimpleNamespace(
            serialized='{"shadow":true}', source=source),
        frontier_tracks=lambda: tracks,
    )
    node._region_graph_shadow_pub = SimpleNamespace(
        publish=publications.append)
    node._wohnungserkundung_policy_enabled = True
    node._wohnungserkundung_policy_fault = None
    node._wohnungserkundung_runtime_lock = threading.Lock()
    node._wohnungserkundung_navigation_snapshot = None
    node._wohnungserkundung_active_child = None
    node._wohnungserkundung_consumed_intent_id = None
    node._wohnungserkundung_evidence_policy = object()
    node._wohnungserkundung_evidence_cache_key = None
    node._wohnungserkundung_evidence_cache = None
    node._wohnungserkundung_goal_cache_key = None
    node._wohnungserkundung_goal_cache = None
    node._wohnungserkundung_stateful_assessment = None

    class FakeTaskPolicySession:
        latest_assessment_revision = None

        def assess(
                self, selected_source, selected_availability,
                selected_utilities):
            assert selected_source is source
            assert selected_availability is availability
            assert selected_utilities is utilities
            stateful_builds.append(selected_source)
            self.latest_assessment_revision = 7
            return stateful

    node._wohnungserkundung_task_policy_session = FakeTaskPolicySession()
    node._try_observe_correlated_raw_map_frontiers = lambda: None
    node._try_observe_connected_raw_map_portals = lambda: None
    node._shadow_source_matches_correlation = (
        lambda selected_source, selected_correlation: (
            selected_source is raw_source
            and selected_correlation is correlation))

    def build_evidence(*args, **kwargs):
        assert not node._region_graph_shadow_lock.locked()
        evidence_builds.append((args, kwargs))
        assert args == (correlation,)
        assert kwargs['robot_xy'] == (1.0, 2.0)
        assert kwargs['tasks'] == (task,)
        assert kwargs['tracks'] == tracks
        return evidence

    node._robot_pose = lambda: (1.0, 2.0, 0.0)
    node._world_to_grid = lambda x, y, info: (10, 20)
    monkeypatch.setattr(
        explore_node_module, 'build_frontier_task_evidence', build_evidence)
    monkeypatch.setattr(
        explore_node_module, 'assess_exploration_policy',
        lambda selected_source, selected_availability: assessment if (
            selected_source is source
            and selected_availability is availability
        ) else None)
    monkeypatch.setattr(
        explore_node_module, 'score_task_utilities',
        lambda task_ids, selected_utilities, revision: scores if (
            task_ids == ('task-1',)
            and selected_utilities is utilities
            and revision == 7
        ) else None)
    monkeypatch.setattr(
        explore_node_module, 'build_passive_we_status_extension',
        lambda selected_assessment, **kwargs: {'schema_version': 1} if (
            selected_assessment is assessment
            and kwargs == {
                'utility_scores': scores,
                'stateful': stateful,
            }
        ) else None)
    monkeypatch.setattr(
        explore_node_module, 'current_goal_intent_from_assessments',
        lambda selected_assessment, selected_stateful: intent if (
            selected_assessment is assessment
            and selected_stateful is stateful
        ) else None)
    goal_builds = []

    def build_goal(selected_intent, selected_correlation, **kwargs):
        assert not node._region_graph_shadow_lock.locked()
        assert selected_intent is intent
        assert selected_correlation is correlation
        assert kwargs['task'] is task
        assert kwargs['tracks'] is tracks
        assert kwargs['evidence'] is evidence
        assert kwargs['robot_xy'] == (1.0, 2.0)
        goal_builds.append((selected_intent, selected_correlation))
        return candidate

    monkeypatch.setattr(
        explore_node_module, 'build_frontier_goal_candidate', build_goal)
    monkeypatch.setattr(
        explore_node_module, 'build_goal_candidate_status',
        lambda value: {'state': 'current'} if value is candidate else None)
    monkeypatch.setattr(explore_node_module.time, 'monotonic', lambda: 11.0)

    node._publish_region_graph_shadow_status()
    node._publish_region_graph_shadow_status()

    assert node._wohnungserkundung_status_extension == {
        'schema_version': 1,
        'task_evidence_source': {
            'state': 'current',
            'map_revision': 7,
            'robot_seed_available': True,
            'current_frontier_track_count': 1,
            'availability_count': 1,
            'utility_count': 1,
        },
        'goal_candidate': {
            'state': 'current',
        },
    }
    assert len(evidence_builds) == 1
    assert len(goal_builds) == 1
    assert stateful_builds == [source]
    assert len(publications) == 2
    assert all(message.data == '{"shadow":true}' for message in publications)


def test_passive_runtime_previews_scoped_portal_without_dispatch(monkeypatch):
    raw_map = SimpleNamespace(
        info=SimpleNamespace(
            width=4,
            height=3,
            resolution=0.1,
            origin=SimpleNamespace(
                position=SimpleNamespace(x=0.0, y=0.0, z=0.0),
                orientation=SimpleNamespace(
                    x=0.0, y=0.0, z=0.0, w=1.0),
            ),
        ),
        header=SimpleNamespace(
            frame_id='map',
            stamp=SimpleNamespace(sec=2, nanosec=3),
        ),
        data=[0] * 12,
    )
    context = PortalMapContext('session-node', 'map-node', 'map')
    portal_task = SimpleNamespace(
        task_id='task-portal-1',
        region_id='region-2',
        kind=RegionTaskKind.PORTAL,
        state=RegionTaskState.OPEN,
    )
    graph = SimpleNamespace(
        tasks=(portal_task,),
        current_region_id='region-1',
        connections=(object(),),
    )
    source = SimpleNamespace(
        context=context,
        source_map_revision=8,
        graph=graph,
        portals=(object(),),
    )
    correlation = SimpleNamespace(
        map_revision=8,
        context=context,
        fingerprint='b' * 64,
        source_stamp_ns=2000000003,
    )
    raw_source = object()
    portal_availability = SimpleNamespace(task_id=portal_task.task_id)
    portal_utility = SimpleNamespace(task_id=portal_task.task_id)
    proposal = SimpleNamespace(task_id=portal_task.task_id)
    portal_evidence = SimpleNamespace(
        availability=(portal_availability,),
        utilities=(portal_utility,),
        proposals=(proposal,),
    )
    frontier_evidence = SimpleNamespace(
        source_map_revision=8,
        availability=(),
        utilities=(),
        robot_seed_available=True,
        current_frontier_track_count=0,
    )
    assessment = SimpleNamespace(
        eligible_task_ids=(portal_task.task_id,),
        state=PolicyAssessmentState.READY_WITH_TASKS,
    )
    stateful = object()
    intent = SimpleNamespace(
        intent_id='intent-portal-1', task_id=portal_task.task_id)
    candidate = object()
    publications = []
    portal_builds = []

    node = ExploreNode.__new__(ExploreNode)
    node._region_graph_shadow_lock = threading.Lock()
    node._region_graph_shadow_fault = None
    node._region_graph_shadow_frontier_task_feed = True
    node._region_graph_shadow_latest_raw_map = raw_map
    node._region_graph_shadow_latest_correlation = correlation
    node._region_graph_shadow_latest_raw_source = raw_source
    node._region_graph_shadow = SimpleNamespace(
        build_status=lambda **kwargs: SimpleNamespace(
            serialized='{"shadow":true}', source=source),
        frontier_tracks=lambda: (),
    )
    node._region_graph_shadow_pub = SimpleNamespace(
        publish=publications.append)
    node._wohnungserkundung_policy_enabled = True
    node._wohnungserkundung_policy_fault = None
    node._wohnungserkundung_runtime_lock = threading.Lock()
    node._wohnungserkundung_navigation_snapshot = None
    node._wohnungserkundung_active_child = None
    node._wohnungserkundung_consumed_intent_id = None
    node._wohnungserkundung_evidence_policy = object()
    node._wohnungserkundung_portal_evidence_policy = object()
    node._wohnungserkundung_scope_id = 'scope-node'
    node._wohnungserkundung_scope_vertices = (
        Point2D(0.0, 0.0), Point2D(1.0, 0.0),
        Point2D(1.0, 1.0), Point2D(0.0, 1.0),
    )
    node._wohnungserkundung_evidence_cache_key = None
    node._wohnungserkundung_evidence_cache = None
    node._wohnungserkundung_goal_cache_key = None
    node._wohnungserkundung_goal_cache = None
    node._wohnungserkundung_stateful_assessment = None
    node._try_observe_correlated_raw_map_frontiers = lambda: None
    node._try_resolve_successful_wohnungserkundung_frontier = lambda: None
    node._try_observe_connected_raw_map_portals = lambda: None
    node._shadow_source_matches_correlation = lambda left, right: (
        left is raw_source and right is correlation)
    node._robot_pose = lambda: (0.1, 0.1, 0.0)
    node._world_to_grid = lambda x, y, info: (1, 1)

    class FakeTaskPolicySession:
        latest_assessment_revision = None

        def assess(self, selected_source, availability, utilities):
            assert selected_source is source
            assert availability == (portal_availability,)
            assert utilities == (portal_utility,)
            self.latest_assessment_revision = 8
            return stateful

    node._wohnungserkundung_task_policy_session = FakeTaskPolicySession()

    monkeypatch.setattr(
        explore_node_module,
        'build_frontier_task_evidence',
        lambda *args, **kwargs: frontier_evidence,
    )

    def build_portal(*args, **kwargs):
        assert not node._region_graph_shadow_lock.locked()
        assert args == (correlation,)
        assert kwargs['tasks'] == (portal_task,)
        assert kwargs['portals'] is source.portals
        assert kwargs['connections'] is graph.connections
        assert kwargs['scope'].scope_id == 'scope-node'
        assert kwargs['scope'].context == context
        portal_builds.append(kwargs)
        return portal_evidence

    monkeypatch.setattr(
        explore_node_module, 'build_portal_task_evidence', build_portal)
    monkeypatch.setattr(
        explore_node_module,
        'assess_exploration_policy',
        lambda selected_source, availability: assessment
        if selected_source is source
        and availability == (portal_availability,) else None,
    )
    monkeypatch.setattr(
        explore_node_module,
        'score_task_utilities',
        lambda task_ids, utilities, revision: ()
        if task_ids == (portal_task.task_id,)
        and utilities == (portal_utility,)
        and revision == 8 else None,
    )
    monkeypatch.setattr(
        explore_node_module,
        'build_passive_we_status_extension',
        lambda *args, **kwargs: {'schema_version': 1},
    )
    monkeypatch.setattr(
        explore_node_module,
        'current_goal_intent_from_assessments',
        lambda *args: intent,
    )
    monkeypatch.setattr(
        explore_node_module,
        'bind_portal_goal_candidate',
        lambda selected_intent, selected_proposal: candidate
        if selected_intent is intent and selected_proposal is proposal
        else None,
    )
    monkeypatch.setattr(
        explore_node_module,
        'build_goal_candidate_status',
        lambda selected: {'state': 'current'}
        if selected is candidate else None,
    )

    node._publish_region_graph_shadow_status()

    assert len(portal_builds) == 1
    assert node._wohnungserkundung_navigation_snapshot is None
    assert node._wohnungserkundung_status_extension == {
        'schema_version': 1,
        'task_evidence_source': {
            'state': 'current',
            'map_revision': 8,
            'robot_seed_available': True,
            'current_frontier_track_count': 0,
            'availability_count': 1,
            'utility_count': 1,
            'portal_scope_state': 'current',
        },
        'goal_candidate': {
            'state': 'current',
            'dispatch_blocked_reason': (
                'portal_traversal_monitor_unavailable'),
        },
    }
    assert len(publications) == 1

    node._wohnungserkundung_portal_monitor_factory = object()
    node._wohnungserkundung_accessible_scope_verified = True
    node._publish_region_graph_shadow_status()

    assert node._wohnungserkundung_navigation_snapshot == (intent, candidate)
    assert 'dispatch_blocked_reason' not in (
        node._wohnungserkundung_status_extension['goal_candidate'])
    assert len(publications) == 2


def _status_node(policy_enabled):
    node = ExploreNode.__new__(ExploreNode)
    node._status_phase = 'idle'
    node._status_message = 'ready'
    node._coverage_ratio = 0.0
    node._coverage_target_ratio = 0.85
    node._reachable_area_m2 = 0.0
    node._covered_area_m2 = 0.0
    node._frontiers_visited_status = 0
    node._frontier_stages_completed = 0
    node._portal_crossings = 0
    node._portals_remaining = 0
    node._unresolved_frontiers = 0
    node._coverage_goals_visited = 0
    node._frontiers_remaining = 0
    node._frontier_rank_stats = {}
    node._coverage_complete = False
    node._wohnungserkundung_policy_enabled = policy_enabled
    node._status_pub = SimpleNamespace(publish=lambda message: None)
    return node


def test_legacy_status_is_unchanged_when_passive_policy_is_disabled(
        monkeypatch):
    publications = []
    node = _status_node(False)
    node._status_pub.publish = publications.append
    monkeypatch.setattr(explore_node_module.time, 'time', lambda: 42.0)

    node._publish_status('idle')

    payload = json.loads(publications[0].data)
    assert 'wohnungserkundung' not in payload
    assert payload['time'] == 42.0


def test_enabled_passive_policy_adds_only_nested_status_extension(
        monkeypatch):
    publications = []
    node = _status_node(True)
    node._wohnungserkundung_status_extension = {
        'schema_version': 1,
        'mode': 'passive_shadow',
        'completion_allowed': False,
    }
    node._status_pub.publish = publications.append
    monkeypatch.setattr(explore_node_module.time, 'time', lambda: 42.0)

    node._publish_status('idle')

    payload = json.loads(publications[0].data)
    assert payload['wohnungserkundung'] == (
        node._wohnungserkundung_status_extension)
    del payload['wohnungserkundung']
    assert payload == json.loads(json.dumps({
        'schema_version': 1,
        'backend_ready': True,
        'state': 'idle',
        'phase': 'idle',
        'message': 'ready',
        'strategy': 'frontier_portal_then_adaptive_coverage',
        'coverage_ratio': 0.0,
        'coverage_percent': 0.0,
        'target_coverage_percent': 85.0,
        'reachable_area_m2': 0.0,
        'covered_area_m2': 0.0,
        'frontiers_visited': 0,
        'frontier_stages_completed': 0,
        'portal_crossings': 0,
        'portals_remaining': 0,
        'unresolved_frontiers': 0,
        'coverage_goals_visited': 0,
        'frontiers_remaining': 0,
        'frontier_ranking': {},
        'map_ready_to_save': False,
        'time': 42.0,
    }))


def test_connected_portal_feed_requires_all_three_opt_ins():
    assert validated_shadow_connected_portal_feed(
        True, True, True, 2, 0.20, 0.05, 30)
    assert not validated_shadow_connected_portal_feed(
        True, True, False, 2, 0.20, 0.05, 30)
    for values in (
            (False, True, True, 2, 0.20, 0.05, 30),
            (True, False, True, 2, 0.20, 0.05, 30),
            (True, True, True, 0, 0.20, 0.05, 30),
            (True, True, True, 2, 0.0, 0.05, 30),
            (True, True, True, 2, 0.20, 0.11, 30),
            (True, True, True, 2, 0.20, 0.05, 0),
            (True, True, 1, 2, 0.20, 0.05, 30)):
        try:
            validated_shadow_connected_portal_feed(*values)
        except ValueError:
            pass
        else:
            raise AssertionError(f'Ungueltiger Portalfeed akzeptiert: {values}')


def test_frontier_task_feed_requires_shadow_and_raw_map_but_not_portals():
    assert validated_shadow_frontier_task_feed(True, True, True, 2)
    assert not validated_shadow_frontier_task_feed(True, True, False, 2)
    for values in (
            (False, True, True, 2),
            (True, False, True, 2),
            (True, True, True, 0),
            (True, True, 1, 2)):
        try:
            validated_shadow_frontier_task_feed(*values)
        except ValueError:
            pass
        else:
            raise AssertionError(
                f'Ungueltiger Frontierfeed akzeptiert: {values}')


def test_frontier_feed_uses_raw_clusters_before_rank_or_blacklist(monkeypatch):
    correlation = SimpleNamespace(
        fingerprint='a' * 64,
        source_stamp_ns=123,
        context=SimpleNamespace(frame_id='map'),
        map_revision=7,
    )
    source = SimpleNamespace(
        fingerprint='a' * 64,
        source_stamp_ns=123,
        frame_id='map',
    )
    first = Frontier((1.0, 2.0), 8)
    second = Frontier((3.0, 4.0), 12)
    inventory = object()
    lifecycle_calls = []
    node = ExploreNode.__new__(ExploreNode)
    node._region_graph_shadow_frontier_task_feed = True
    node._region_graph_shadow_lock = threading.Lock()
    node._region_graph_shadow_fault = None
    node._region_graph_shadow_latest_raw_map = _grid(width=2, height=2)
    node._region_graph_shadow_latest_raw_source = source
    node._region_graph_shadow_latest_correlation = correlation
    node._region_graph_shadow_frontier_processed_correlation = None
    node._min_frontier_m = 0.30
    node._blacklist = [(1.0, 2.0)]
    node._detect_frontiers = lambda message, minimum: (
        [first, second]
        if message is node._region_graph_shadow_latest_raw_map
        and minimum == 0.30
        else (_ for _ in ()).throw(AssertionError('Falscher Detektoraufruf')))
    node._rank_frontiers = lambda *args, **kwargs: (_ for _ in ()).throw(
        AssertionError('Passive Zufuehrung darf nicht ranken'))
    node._region_graph_shadow = SimpleNamespace(
        observe_frontier_inventory=lambda value, **kwargs: lifecycle_calls.append(
            (value, kwargs)))

    def build_inventory(value, clusters):
        assert value is correlation
        assert not node._region_graph_shadow_lock.locked()
        assert tuple(clusters) == ((1.0, 2.0, 8), (3.0, 4.0, 12))
        return inventory

    monkeypatch.setattr(
        explore_node_module, 'frontier_inventory_from_clusters',
        build_inventory)
    monkeypatch.setattr(explore_node_module.time, 'monotonic', lambda: 50.0)

    node._try_observe_correlated_raw_map_frontiers()
    node._try_observe_correlated_raw_map_frontiers()

    assert lifecycle_calls == [(
        inventory, {'observed_monotonic_seconds': 50.0})]
    assert node._region_graph_shadow_frontier_processed_correlation == (
        'a' * 64, 123, 'map', 7)


def test_frontier_feed_discards_result_when_exact_cache_changes(monkeypatch):
    node = ExploreNode.__new__(ExploreNode)
    node._region_graph_shadow_frontier_task_feed = True
    node._region_graph_shadow_lock = threading.Lock()
    node._region_graph_shadow_fault = None
    node._region_graph_shadow_latest_raw_map = _grid(width=2, height=2)
    node._region_graph_shadow_latest_raw_source = SimpleNamespace(
        fingerprint='a' * 64, source_stamp_ns=123, frame_id='map')
    original = SimpleNamespace(
        fingerprint='a' * 64, source_stamp_ns=123,
        context=SimpleNamespace(frame_id='map'), map_revision=7)
    node._region_graph_shadow_latest_correlation = original
    node._region_graph_shadow_frontier_processed_correlation = None
    node._min_frontier_m = 0.30
    node._detect_frontiers = lambda *args: []
    calls = []
    node._region_graph_shadow = SimpleNamespace(
        observe_frontier_inventory=lambda *args, **kwargs: calls.append(
            (args, kwargs)))

    def change_cache(*args, **kwargs):
        node._region_graph_shadow_latest_correlation = SimpleNamespace(
            fingerprint='b' * 64, source_stamp_ns=456,
            context=SimpleNamespace(frame_id='map'), map_revision=8)
        return object()

    monkeypatch.setattr(
        explore_node_module, 'frontier_inventory_from_clusters', change_cache)

    node._try_observe_correlated_raw_map_frontiers()

    assert original.map_revision == 7
    assert calls == []
    assert node._region_graph_shadow_frontier_processed_correlation is None


def _portal_feed_node():
    correlation = SimpleNamespace(
        fingerprint='a' * 64,
        source_stamp_ns=123,
        context=SimpleNamespace(frame_id='map'),
        map_revision=7,
    )
    source = SimpleNamespace(
        fingerprint='a' * 64,
        source_stamp_ns=123,
        frame_id='map',
    )
    node = ExploreNode.__new__(ExploreNode)
    node._region_graph_shadow_connected_portal_feed = True
    node._region_graph_shadow_lock = threading.Lock()
    node._region_graph_shadow_fault = None
    node._region_graph_shadow_latest_raw_map = _grid(width=2, height=2)
    node._region_graph_shadow_latest_raw_source = source
    node._region_graph_shadow_latest_correlation = correlation
    node._region_graph_shadow_processed_correlation = None
    node._region_graph_shadow_portal_retry_count = 0
    node._region_graph_shadow_portal_retry_limit = 2
    node._region_graph_shadow_portal_uncertainty = 0.05
    node._region_graph_shadow_portal_analysis_clearance = 0.20
    node._portal_min_component_area = 0.40
    node._portal_min_gap = 0.12
    node._portal_max_gap = 0.80
    node._portal_exit_margin = 0.25
    node._portal_max_traverse_distance = 1.00
    return node, source, correlation


def test_disabled_connected_portal_feed_has_zero_runtime_work():
    node = ExploreNode.__new__(ExploreNode)
    node._region_graph_shadow_connected_portal_feed = False
    node._robot_pose = lambda: (_ for _ in ()).throw(
        AssertionError('Deaktivierter Portalfeed darf keine Pose lesen'))

    node._try_observe_connected_raw_map_portals()


def test_exact_connected_portal_feed_computes_outside_and_mutates_inside_lock(
        monkeypatch):
    node, _source, correlation = _portal_feed_node()
    inventory = object()
    inventories = []
    node._robot_pose = lambda: (0.1, 0.1, 0.0)

    def build_inventory(value, **kwargs):
        assert value is correlation
        assert not node._region_graph_shadow_lock.locked()
        assert kwargs['robot_xy'] == (0.1, 0.1)
        return inventory

    def observe(value, **kwargs):
        assert node._region_graph_shadow_lock.locked()
        inventories.append((value, kwargs))

    node._region_graph_shadow = SimpleNamespace(
        observe_portal_inventory=observe)
    monkeypatch.setattr(
        explore_node_module,
        'correlated_connected_portal_inventory',
        build_inventory)
    monkeypatch.setattr(explore_node_module.time, 'monotonic', lambda: 50.0)

    node._try_observe_connected_raw_map_portals()
    node._try_observe_connected_raw_map_portals()

    assert inventories == [(
        inventory, {'observed_monotonic_seconds': 50.0})]
    assert node._region_graph_shadow_processed_correlation == (
        'a' * 64, 123, 'map', 7)
    assert node._region_graph_shadow_portal_retry_count == 0


def test_missing_pose_faults_only_shadow_after_bounded_retry():
    errors = []
    node, _source, _correlation = _portal_feed_node()
    node._robot_pose = lambda: None
    node.get_logger = lambda: SimpleNamespace(error=errors.append)

    node._try_observe_connected_raw_map_portals()
    assert node._region_graph_shadow_fault is None
    node._try_observe_connected_raw_map_portals()

    assert len(errors) == 1
    assert 'Roboterpose fehlt nach begrenztem Retry' in (
        node._region_graph_shadow_fault)


def test_cache_change_during_detection_discards_candidates(monkeypatch):
    node, _source, correlation = _portal_feed_node()
    inventories = []
    node._robot_pose = lambda: (0.1, 0.1, 0.0)
    node._region_graph_shadow = SimpleNamespace(
        observe_portal_inventory=lambda *args, **kwargs: inventories.append(
            (args, kwargs)))

    def change_cache(*args, **kwargs):
        node._region_graph_shadow_latest_correlation = SimpleNamespace(
            fingerprint='b' * 64,
            source_stamp_ns=456,
            context=SimpleNamespace(frame_id='map'),
            map_revision=8,
        )
        return object()

    monkeypatch.setattr(
        explore_node_module,
        'correlated_connected_portal_inventory',
        change_cache)

    node._try_observe_connected_raw_map_portals()

    assert correlation.map_revision == 7
    assert inventories == []
    assert node._region_graph_shadow_processed_correlation is None
