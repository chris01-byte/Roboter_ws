import math
from pathlib import Path
import sys
import threading
import time
from types import SimpleNamespace

import numpy as np
from nav_msgs.msg import OccupancyGrid
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
    validated_shadow_raw_map_capacity,
)
from explore.portal_planning import CorridorCheck, PortalBridge  # noqa: E402
from explore.region_graph_shadow_lifecycle import (  # noqa: E402
    RegionGraphShadowLifecycle,
    RegionGraphShadowNotReadyError,
)
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
    assert parameters['region_graph_shadow_portal_analysis_clearance_m'] == 0.20
    assert parameters['region_graph_shadow_portal_uncertainty_m'] == 0.05
    assert parameters['region_graph_shadow_portal_retry_limit'] == 30
    assert parameters['region_graph_shadow_session_id'] == ''
    assert parameters['region_graph_shadow_start_observation_id'] == ''
    assert parameters['region_graph_shadow_map_status_topic'] == (
        '/robot_map_manager/status_json')
    assert parameters['region_graph_shadow_status_topic'] == (
        '/explore/region_graph/status_json')
    assert parameters['region_graph_shadow_status_topic'] != (
        parameters['status_topic'])
    assert 'PortalPlanCandidate' not in source
    assert '.observe_structural_portal(' in source


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
    node._region_graph_shadow = SimpleNamespace(build_status_json=not_ready)
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
        build_status_json=lambda **kwargs: build_calls.append(kwargs) or '{}')
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
    observation = object()
    observations = []
    node._robot_pose = lambda: (0.1, 0.1, 0.0)

    def build_observations(value, **kwargs):
        assert value is correlation
        assert not node._region_graph_shadow_lock.locked()
        assert kwargs['robot_xy'] == (0.1, 0.1)
        return (observation,)

    def observe(value, **kwargs):
        assert node._region_graph_shadow_lock.locked()
        observations.append((value, kwargs))

    node._region_graph_shadow = SimpleNamespace(
        observe_structural_portal=observe)
    monkeypatch.setattr(
        explore_node_module,
        'correlated_connected_portal_observations',
        build_observations)
    monkeypatch.setattr(explore_node_module.time, 'monotonic', lambda: 50.0)

    node._try_observe_connected_raw_map_portals()
    node._try_observe_connected_raw_map_portals()

    assert observations == [(
        observation, {'observed_monotonic_seconds': 50.0})]
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
    observations = []
    node._robot_pose = lambda: (0.1, 0.1, 0.0)
    node._region_graph_shadow = SimpleNamespace(
        observe_structural_portal=lambda *args, **kwargs: observations.append(
            (args, kwargs)))

    def change_cache(*args, **kwargs):
        node._region_graph_shadow_latest_correlation = SimpleNamespace(
            fingerprint='b' * 64,
            source_stamp_ns=456,
            context=SimpleNamespace(frame_id='map'),
            map_revision=8,
        )
        return (object(),)

    monkeypatch.setattr(
        explore_node_module,
        'correlated_connected_portal_observations',
        change_cache)

    node._try_observe_connected_raw_map_portals()

    assert correlation.map_revision == 7
    assert observations == []
    assert node._region_graph_shadow_processed_correlation is None
