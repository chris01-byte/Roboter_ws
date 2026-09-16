"""Device-free WE chain: production portal decisions, restart, same hall."""

import math
from pathlib import Path
import sys

import numpy as np
from nav_msgs.msg import OccupancyGrid
from types import SimpleNamespace


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
SHARED_ROOT = Path(__file__).resolve().parents[2] / "amadeus_map_identity"
sys.path.insert(0, str(PACKAGE_ROOT))
sys.path.insert(0, str(SHARED_ROOT))

from explore.exploration_persistence import (  # noqa: E402
    ExplorationStateRepository,
    MapVersionBinding,
)
from explore.exploration_child_goal import (  # noqa: E402
    current_goal_intent_from_assessments,
)
from explore.exploration_nav_runtime import (  # noqa: E402
    ExplorationNavigationSession,
    NavigationSourceState,
)
from explore.exploration_policy import (  # noqa: E402
    ExplorationTaskPolicySession,
    assess_exploration_policy,
)
from explore.exploration_scope import AuthorizedExplorationScope  # noqa: E402
from explore.explore_node import ExploreNode  # noqa: E402
from explore.frontier_goal_candidate import (  # noqa: E402
    build_frontier_goal_candidate,
)
from explore.frontier_task_evidence import (  # noqa: E402
    FrontierTaskEvidencePolicy,
    build_frontier_task_evidence,
)
from explore.frontier_task_feed import frontier_inventory_from_clusters  # noqa: E402
from explore.frontier_task_resolution import (  # noqa: E402
    build_frontier_task_resolution_evidence,
)
from explore.map_status_adapter import MapStatusCorrelationResult  # noqa: E402
from explore.portal_memory import (  # noqa: E402
    Point2D,
    PortalMapContext,
    PortalSide,
    TraversalDirection,
)
from explore.portal_source_adapter import (  # noqa: E402
    PortalSourceCorrelation,
    raw_map_portal_source_from_values,
)
from explore.portal_traversal_evidence import (  # noqa: E402
    IndependentMotionEvidence,
    IndependentMotionSource,
    PortalTraversalEvidence,
    PortalTraversalPolicy,
    TraversalExecutionMode,
    TraversalPoseSample,
    assess_portal_traversal,
)
from explore.portal_task_evidence import (  # noqa: E402
    PortalTaskEvidencePolicy,
    bind_portal_goal_candidate,
    build_portal_task_evidence,
)
from explore.raw_map_portal_adapter import (  # noqa: E402
    correlated_connected_portal_inventory,
)
from explore.region_graph import (  # noqa: E402
    RegionSeed,
    RegionTaskKind,
    RegionTaskState,
)
from explore.region_graph_shadow import RegionGraphShadowSession  # noqa: E402


RESOLUTION = 0.05
ORIGIN = (0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0)
FINGERPRINT = "c" * 64
CONTEXT = PortalMapContext(
    "we-full-chain", f"map-{FINGERPRINT}", "map")


def apartment_map():
    occupancy = np.full((60, 155), 100, dtype=np.int8)
    occupancy[5:55, 3:48] = 0       # Startraum
    occupancy[20:40, 52:100] = 0    # Flur
    occupancy[5:55, 104:149] = 0    # weiteres Zimmer
    occupancy[27:33, 48:52] = 0
    occupancy[27:33, 100:104] = 0
    return occupancy


def map_status(revision):
    return MapStatusCorrelationResult(
        context=CONTEXT, map_revision=revision,
        fingerprint=FINGERPRINT, source_stamp_ns=revision * 1_000_000_000,
        source_map_age_seconds=0.05, map_changed=True, replayed=False)


def automatic_inventory(occupancy, robot_cell, revision):
    source = raw_map_portal_source_from_values(
        width=occupancy.shape[1], height=occupancy.shape[0],
        resolution=RESOLUTION, frame_id="map", origin=ORIGIN,
        cells=occupancy.ravel(), source_stamp_ns=revision * 1_000_000_000)
    correlation = PortalSourceCorrelation(
        CONTEXT, revision, source.fingerprint, source.source_stamp_ns)
    robot_xy = (
        (robot_cell[1] + 0.5) * RESOLUTION,
        (robot_cell[0] + 0.5) * RESOLUTION,
    )
    return correlated_connected_portal_inventory(
        correlation,
        width=occupancy.shape[1], height=occupancy.shape[0],
        resolution=RESOLUTION, frame_id="map", origin=ORIGIN,
        cells=occupancy.ravel(), source_stamp_ns=source.source_stamp_ns,
        robot_xy=robot_xy, uncertainty_m=0.02,
        analysis_clearance_m=0.20, min_target_area_m2=0.40,
        min_gap_m=0.12, max_gap_m=0.80, exit_margin_m=0.25,
        max_traverse_distance_m=1.00)


def direction_from(side):
    return (
        TraversalDirection.A_TO_B
        if side is PortalSide.A else TraversalDirection.B_TO_A)


def validated_crossing(portal, direction, revision, suffix):
    if direction is TraversalDirection.A_TO_B:
        start, end = portal.side_a, portal.side_b
    else:
        start, end = portal.side_b, portal.side_a
    dx, dy = end.x - start.x, end.y - start.y
    length = math.hypot(dx, dy)
    ux, uy = dx / length, dy / length
    yaw = math.atan2(uy, ux)
    points = tuple(
        (start.x - 0.20 * ux + (length + 0.40) * ux * index / 3,
         start.y - 0.20 * uy + (length + 0.40) * uy * index / 3)
        for index in range(4))
    stamps = tuple((revision * 10 + index) * 1_000_000_000
                   for index in range(4))
    poses = tuple(TraversalPoseSample(
        f"pose-{suffix}-{index}", CONTEXT, revision, stamps[index],
        point[0], point[1], yaw)
        for index, point in enumerate(points))
    motion = IndependentMotionEvidence(
        f"motion-{suffix}", CONTEXT, revision, stamps[0], stamps[-1],
        length + 0.40, IndependentMotionSource.FROZEN_RANGE_SCAN)
    assessed = assess_portal_traversal(PortalTraversalEvidence(
        f"crossing-{suffix}", CONTEXT, portal, direction,
        TraversalExecutionMode.REGULAR_NAV2, True, revision, stamps[-1],
        stamps[-1] + 50_000_000, poses, motion), PortalTraversalPolicy(
            chassis_front_overhang_m=0.05,
            chassis_rear_overhang_m=0.05,
            start_clearance_m=0.05, exit_clearance_m=0.05,
            maximum_lateral_deviation_m=0.05,
            maximum_pose_step_m=0.50, maximum_pose_speed_mps=1.0,
            maximum_yaw_error_rad=0.10, maximum_yaw_step_rad=0.10,
            maximum_backward_step_m=0.01,
            maximum_motion_disagreement_m=0.01,
            maximum_source_age_ns=100_000_000,
            maximum_revision_lag=0, minimum_pose_samples=4))
    assert assessed.confirmed
    return assessed.traversal_event


def observe_twice(shadow, occupancy, robot_cell, first_revision):
    result = None
    for revision in (first_revision, first_revision + 1):
        result = shadow.observe_portal_inventory(
            automatic_inventory(occupancy, robot_cell, revision))
    return result


def add_hall_frontier(shadow, revision):
    """Register remaining automatic work in the current hall region."""
    correlation = PortalSourceCorrelation(
        CONTEXT, revision, FINGERPRINT, revision * 1_000_000_000)
    return shadow.observe_frontier_inventory(frontier_inventory_from_clusters(
        correlation, ((3.75, 1.50, 12),)))


def test_start_room_hall_room_interrupt_restore_and_same_hall(tmp_path):
    occupancy = apartment_map()
    shadow = RegionGraphShadowSession(
        map_status(1), RegionSeed("start", CONTEXT, 1))

    first = observe_twice(shadow, occupancy, (30, 20), 1)
    first_event = next(item for item in first.events if item.link is not None)
    first_portal = shadow.portal_snapshots()[0]
    shadow.record_validated_traversal(validated_crossing(
        first_portal, direction_from(first_event.observation.approach_side),
        3, "start-to-hall"))
    assert shadow.status_source(
        map_status(3), portal_memory_age_seconds=0.0,
        region_graph_age_seconds=0.0).graph.current_region_id == (
            "region_000002")

    add_hall_frontier(shadow, 4)
    second = observe_twice(shadow, occupancy, (30, 75), 5)
    second_event = next(
        item for item in second.events
        if item.link is not None and item.link.portal_id == "portal_000002")
    second_portal = next(
        item for item in shadow.portal_snapshots()
        if item.portal_id == "portal_000002")
    shadow.record_validated_traversal(validated_crossing(
        second_portal,
        direction_from(second_event.observation.approach_side),
        7, "hall-to-room"))
    before = shadow.status_source(
        map_status(7), portal_memory_age_seconds=0.0,
        region_graph_age_seconds=0.0)
    assert before.graph.current_region_id == "region_000003"
    assert any(
        item.kind is RegionTaskKind.TRANSIT
        and item.state is RegionTaskState.OPEN
        for item in before.graph.tasks)

    repository = ExplorationStateRepository(tmp_path / "we")
    binding = MapVersionBinding(
        "wohnung", "20260915T130000Z-full-chain", FINGERPRINT,
        occupancy.shape[1], occupancy.shape[0], RESOLUTION, "map")
    repository.save(binding, shadow.persistent_state())
    loaded = repository.load(binding)
    resumed = RegionGraphShadowSession.restore_persistent_state(
        map_status(0), RegionSeed("restart", CONTEXT, 0), loaded.state)
    after = resumed.status_source(
        map_status(0), portal_memory_age_seconds=0.0,
        region_graph_age_seconds=0.0)
    assert after.graph.current_region_id == "region_000003"
    assert tuple(item.region_id for item in after.graph.regions) == (
        "region_000001", "region_000002", "region_000003")
    persisted_transit = next(
        item for item in after.graph.tasks
        if item.kind is RegionTaskKind.TRANSIT)
    assert persisted_transit.state is RegionTaskState.OPEN

    reverse = observe_twice(resumed, occupancy, (30, 125), 1)
    reverse_event = next(
        item for item in reverse.events
        if item.link is not None and item.link.portal_id == "portal_000002")
    resumed.record_validated_traversal(validated_crossing(
        next(item for item in resumed.portal_snapshots()
             if item.portal_id == "portal_000002"),
        direction_from(reverse_event.observation.approach_side),
        3, "room-to-same-hall"))
    final = resumed.status_source(
        map_status(3), portal_memory_age_seconds=0.0,
        region_graph_age_seconds=0.0)

    assert final.graph.current_region_id == "region_000002"
    assert next(
        item for item in final.graph.regions
        if item.region_id == "region_000002").entry_count == 2
    assert tuple(item.portal_id for item in final.portals) == (
        "portal_000001", "portal_000002")
    assert final.graph.confirmed_entry_count == 3
    assert next(
        item for item in final.graph.tasks
        if item.task_id == persisted_transit.task_id).state is (
            RegionTaskState.COMPLETED)


def test_return_transit_is_auto_selected_with_exact_portal_evidence():
    """A remaining hall task creates one safe, selectable return crossing."""
    occupancy = apartment_map()
    shadow = RegionGraphShadowSession(
        map_status(1), RegionSeed("start", CONTEXT, 1))
    first = observe_twice(shadow, occupancy, (30, 20), 1)
    first_event = next(item for item in first.events if item.link is not None)
    first_portal = shadow.portal_snapshots()[0]
    shadow.record_validated_traversal(validated_crossing(
        first_portal, direction_from(first_event.observation.approach_side),
        3, "return-start-to-hall"))
    add_hall_frontier(shadow, 4)

    second = observe_twice(shadow, occupancy, (30, 75), 5)
    second_event = next(
        item for item in second.events
        if item.link is not None and item.link.portal_id == "portal_000002")
    second_portal = next(
        item for item in shadow.portal_snapshots()
        if item.portal_id == "portal_000002")
    forward_direction = direction_from(second_event.observation.approach_side)
    applied = shadow.record_validated_traversal(validated_crossing(
        second_portal, forward_direction, 7, "return-hall-to-room"))
    transit = applied.transit_task_update
    assert transit is not None
    assert transit.created is True
    assert transit.task.kind is RegionTaskKind.TRANSIT
    assert transit.task.region_id == "region_000002"
    assert transit.task.subject_id == second_portal.portal_id

    source = shadow.status_source(
        map_status(8), portal_memory_age_seconds=0.0,
        region_graph_age_seconds=0.0)
    raw_source = raw_map_portal_source_from_values(
        width=occupancy.shape[1], height=occupancy.shape[0],
        resolution=RESOLUTION, frame_id="map", origin=ORIGIN,
        cells=occupancy.ravel(), source_stamp_ns=8_000_000_000)
    correlation = PortalSourceCorrelation(
        CONTEXT, 8, raw_source.fingerprint, raw_source.source_stamp_ns)
    scope = AuthorizedExplorationScope(
        "scope-return-transit", CONTEXT, (
            Point2D(0.10, 0.10), Point2D(7.65, 0.10),
            Point2D(7.65, 2.90), Point2D(0.10, 2.90),
        ))
    route_policy = PortalTaskEvidencePolicy(
        clearance_m=0.10, scope_clearance_m=0.10,
        robot_seed_search_m=0.20, chassis_rear_overhang_m=0.20,
        exit_clearance_m=0.10, target_search_m=0.20,
        maximum_target_lateral_m=0.15, portal_path_radius_m=0.15)
    evidence = build_portal_task_evidence(
        correlation, width=occupancy.shape[1], height=occupancy.shape[0],
        resolution=RESOLUTION, frame_id="map", origin=ORIGIN,
        cells=occupancy.ravel(), source_stamp_ns=raw_source.source_stamp_ns,
        robot_xy=(6.275, 1.525),
        current_region_id=source.graph.current_region_id,
        tasks=tuple(task for task in source.graph.tasks
                    if task.kind is RegionTaskKind.TRANSIT
                    and task.state is RegionTaskState.OPEN),
        portals=source.portals, connections=source.graph.connections,
        scope=scope, policy=route_policy)
    passive = assess_exploration_policy(source, evidence.availability)
    stateful = ExplorationTaskPolicySession(CONTEXT).assess(
        source, evidence.availability, evidence.utilities)
    intent = current_goal_intent_from_assessments(passive, stateful)
    assert intent is not None
    assert intent.task_id == transit.task.task_id
    proposal = next(
        item for item in evidence.proposals if item.task_id == intent.task_id)
    candidate = bind_portal_goal_candidate(intent, proposal)
    expected_return = (
        TraversalDirection.B_TO_A
        if forward_direction is TraversalDirection.A_TO_B
        else TraversalDirection.A_TO_B)
    assert candidate.portal_id == second_portal.portal_id
    assert candidate.direction is expected_return

    returned = shadow.record_validated_traversal(validated_crossing(
        second_portal, candidate.direction, 9, "return-room-to-hall"))
    assert returned.task_update is not None
    assert returned.task_update.task.task_id == transit.task.task_id
    assert returned.task_update.task.state is RegionTaskState.COMPLETED
    assert returned.transit_task_update is None
    final = shadow.status_source(
        map_status(9), portal_memory_age_seconds=0.0,
        region_graph_age_seconds=0.0)
    hall = next(item for item in final.graph.regions
                if item.region_id == "region_000002")
    assert hall.entry_count == 2


def test_evolving_raw_map_forms_selects_and_resolves_frontier_automatically():
    occupancy = np.full((40, 40), 100, dtype=np.int8)
    occupancy[5:35, 5:35] = 0
    occupancy[15:20, 25:30] = -1
    context = PortalMapContext("we-frontier-chain", "map-frontier", "map")

    def inputs(cells, revision):
        source = raw_map_portal_source_from_values(
            width=40, height=40, resolution=RESOLUTION, frame_id="map",
            origin=ORIGIN, cells=cells.ravel(),
            source_stamp_ns=revision * 1_000_000_000)
        correlation = PortalSourceCorrelation(
            context, revision, source.fingerprint, source.source_stamp_ns)
        return source, correlation

    source, correlation = inputs(occupancy, 1)
    initial = MapStatusCorrelationResult(
        context, 1, source.fingerprint, source.source_stamp_ns,
        0.05, True, False)
    shadow = RegionGraphShadowSession(
        initial, RegionSeed("frontier-start", context, 1))
    grid = OccupancyGrid()
    grid.info.width = grid.info.height = 40
    grid.info.resolution = RESOLUTION
    grid.info.origin.orientation.w = 1.0
    grid.data = occupancy.ravel().tolist()
    detector = SimpleNamespace(_grid_to_world=ExploreNode._grid_to_world)
    frontiers = ExploreNode._detect_frontiers(detector, grid, 0.20)
    assert len(frontiers) == 1
    shadow.observe_portal_inventory(correlated_connected_portal_inventory(
        correlation, width=40, height=40, resolution=RESOLUTION,
        frame_id="map", origin=ORIGIN, cells=occupancy.ravel(),
        source_stamp_ns=source.source_stamp_ns, robot_xy=(0.5, 0.5),
        uncertainty_m=0.02, analysis_clearance_m=0.20,
        min_target_area_m2=0.40, min_gap_m=0.12, max_gap_m=0.80,
        exit_margin_m=0.25, max_traverse_distance_m=1.00))
    shadow.observe_frontier_inventory(frontier_inventory_from_clusters(
        correlation, ((item.cx, item.cy, item.size) for item in frontiers)))
    status = shadow.status_source(
        initial, portal_memory_age_seconds=0.0,
        region_graph_age_seconds=0.0)
    policy = FrontierTaskEvidencePolicy(
        clearance_m=0.05, robot_seed_search_m=0.20,
        task_cell_search_m=0.30, information_radius_m=0.30)
    evidence = build_frontier_task_evidence(
        correlation, width=40, height=40, resolution=RESOLUTION,
        frame_id="map", origin=ORIGIN, cells=occupancy.ravel(),
        source_stamp_ns=source.source_stamp_ns, robot_xy=(0.5, 0.5),
        tasks=tuple(item for item in status.graph.tasks
                    if item.state.value == "open"),
        tracks=shadow.frontier_tracks(), policy=policy)
    passive = assess_exploration_policy(status, evidence.availability)
    stateful = ExplorationTaskPolicySession(context).assess(
        status, evidence.availability, evidence.utilities)
    intent = current_goal_intent_from_assessments(passive, stateful)
    assert intent is not None
    task = next(item for item in status.graph.tasks
                if item.task_id == intent.task_id)
    candidate = build_frontier_goal_candidate(
        intent, correlation, width=40, height=40, resolution=RESOLUTION,
        frame_id="map", origin=ORIGIN, cells=occupancy.ravel(),
        source_stamp_ns=source.source_stamp_ns, robot_xy=(0.5, 0.5),
        task=task, tracks=shadow.frontier_tracks(), evidence=evidence,
        policy=policy)
    run = ExplorationNavigationSession(context).run(
        intent, candidate, lambda _candidate, stop: (
            "canceled" if stop() else "success"),
        lambda: NavigationSourceState(context, 1, True),
        lambda: False, lambda: False)
    assert run.navigation_status == "success"

    complete = occupancy.copy()
    complete[15:20, 25:30] = 0
    source2, correlation2 = inputs(complete, 2)
    grid.data = complete.ravel().tolist()
    assert ExploreNode._detect_frontiers(detector, grid, 0.20) == []
    shadow.observe_portal_inventory(correlated_connected_portal_inventory(
        correlation2, width=40, height=40, resolution=RESOLUTION,
        frame_id="map", origin=ORIGIN, cells=complete.ravel(),
        source_stamp_ns=source2.source_stamp_ns, robot_xy=(0.5, 0.5),
        uncertainty_m=0.02, analysis_clearance_m=0.20,
        min_target_area_m2=0.40, min_gap_m=0.12, max_gap_m=0.80,
        exit_margin_m=0.25, max_traverse_distance_m=1.00))
    shadow.observe_frontier_inventory(frontier_inventory_from_clusters(
        correlation2, ()))
    resolution = build_frontier_task_resolution_evidence(
        candidate, run.disposition, correlation2,
        width=40, height=40, resolution=RESOLUTION, frame_id="map",
        origin=ORIGIN, cells=complete.ravel(),
        source_stamp_ns=source2.source_stamp_ns,
        tracks=shadow.frontier_tracks(), policy=policy)
    resolved = shadow.resolve_frontier_task(resolution)
    assert resolved.task.state.value == "completed"
