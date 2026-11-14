"""Device-free end-to-end portal task pipeline for WE-M3."""

from pathlib import Path
import math
import sys

import numpy as np

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE_ROOT))

from amadeus_map_identity import (  # noqa: E402
    compact_occupancy_cells,
    map_snapshot_fingerprint,
)
from explore.exploration_child_goal import (  # noqa: E402
    current_goal_intent_from_assessments,
)
from explore.exploration_policy import (  # noqa: E402
    ExplorationTaskPolicySession,
    assess_exploration_policy,
    score_task_utilities,
)
from explore.exploration_scope import AuthorizedExplorationScope  # noqa: E402
from explore.map_status_adapter import MapStatusCorrelationResult  # noqa: E402
from explore.portal_memory import (  # noqa: E402
    Point2D,
    PortalMapContext,
)
from explore.raw_map_portal_adapter import (  # noqa: E402
    correlated_connected_portal_inventory,
)
from explore.portal_source_adapter import PortalSourceCorrelation  # noqa: E402
from explore.portal_task_evidence import (  # noqa: E402
    PortalTaskEvidencePolicy,
    bind_portal_goal_candidate,
    build_portal_task_evidence,
)
from explore.portal_traversal_evidence import (  # noqa: E402
    IndependentMotionSource,
    PortalTraversalPolicy,
)
from explore.portal_traversal_runtime import (  # noqa: E402
    PairedTraversalReading,
    PortalTraversalRuntimeSession,
)
from explore.region_graph import (  # noqa: E402
    RegionSeed,
    RegionTaskKind,
    RegionTaskState,
)
from explore.region_graph_shadow import RegionGraphShadowSession  # noqa: E402


CONTEXT = PortalMapContext("session-pipeline", "map-pipeline", "map")
WIDTH = 100
HEIGHT = 60
RESOLUTION = 0.05
ORIGIN = (0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0)


def map_cells(revision):
    occupancy = np.full((HEIGHT, WIDTH), -1, dtype=np.int8)
    occupancy[5:55, 3:48] = 0
    occupancy[5:55, 52:97] = 0
    occupancy[27:33, 48:52] = 0
    for row in range(10, min(13, 10 + max(0, revision - 7))):
        occupancy[row, 10] = 100
    return occupancy.ravel().tolist()


def fingerprint(revision):
    cells = map_cells(revision)
    return map_snapshot_fingerprint(
        width=WIDTH,
        height=HEIGHT,
        resolution=RESOLUTION,
        frame_id="map",
        origin=ORIGIN,
        compact_cells=compact_occupancy_cells(
            cells=cells, cell_count=WIDTH * HEIGHT),
    )


def map_status(revision):
    return MapStatusCorrelationResult(
        context=CONTEXT,
        map_revision=revision,
        fingerprint=fingerprint(revision),
        source_stamp_ns=1_000_000_000,
        source_map_age_seconds=0.1,
        map_changed=True,
        replayed=False,
    )


def portal_inventory(revision):
    correlation = PortalSourceCorrelation(
        CONTEXT, revision, fingerprint(revision), 1_000_000_000)
    return correlated_connected_portal_inventory(
        correlation,
        width=WIDTH,
        height=HEIGHT,
        resolution=RESOLUTION,
        frame_id="map",
        origin=ORIGIN,
        cells=map_cells(revision),
        source_stamp_ns=1_000_000_000,
        robot_xy=(1.025, 1.525),
        uncertainty_m=0.02,
        analysis_clearance_m=0.20,
        min_target_area_m2=0.40,
        min_gap_m=0.12,
        max_gap_m=0.80,
        exit_margin_m=0.25,
        max_traverse_distance_m=1.00,
    )


def test_exact_map_to_portal_event_to_region_task_completion():
    shadow = RegionGraphShadowSession(
        map_status(7), RegionSeed("pipeline-start", CONTEXT, 7))
    first_inventory = shadow.observe_portal_inventory(portal_inventory(8))
    second_inventory = shadow.observe_portal_inventory(portal_inventory(9))
    assert len(first_inventory.events) == 1
    assert second_inventory.events[0].link is not None

    correlation = PortalSourceCorrelation(
        CONTEXT, 10, fingerprint(10), 1_000_000_000)
    source = shadow.status_source(
        map_status(10),
        portal_memory_age_seconds=0.1,
        region_graph_age_seconds=0.1,
    )
    portal_tasks = tuple(
        task for task in source.graph.tasks
        if task.kind is RegionTaskKind.PORTAL
        and task.state is RegionTaskState.OPEN)
    assert len(portal_tasks) == 1
    scope = AuthorizedExplorationScope(
        "scope-pipeline",
        CONTEXT,
        (
            Point2D(0.0, 0.0), Point2D(5.0, 0.0),
            Point2D(5.0, 3.0), Point2D(0.0, 3.0),
        ),
    )
    route_policy = PortalTaskEvidencePolicy(
        clearance_m=0.1,
        scope_clearance_m=0.1,
        robot_seed_search_m=0.2,
        chassis_rear_overhang_m=0.2,
        exit_clearance_m=0.1,
        target_search_m=0.2,
        maximum_target_lateral_m=0.15,
        portal_path_radius_m=0.15,
    )
    evidence = build_portal_task_evidence(
        correlation,
        width=WIDTH,
        height=HEIGHT,
        resolution=RESOLUTION,
        frame_id="map",
        origin=ORIGIN,
        cells=map_cells(10),
        source_stamp_ns=1_000_000_000,
        robot_xy=(1.025, 1.525),
        current_region_id=source.graph.current_region_id,
        tasks=portal_tasks,
        portals=source.portals,
        connections=source.graph.connections,
        scope=scope,
        policy=route_policy,
    )
    passive = assess_exploration_policy(source, evidence.availability)
    scores = score_task_utilities(
        passive.eligible_task_ids, evidence.utilities, 10)
    stateful = ExplorationTaskPolicySession(CONTEXT).assess(
        source, evidence.availability, evidence.utilities)
    intent = current_goal_intent_from_assessments(passive, stateful)
    assert scores[0].task_id == portal_tasks[0].task_id
    assert intent.task_id == portal_tasks[0].task_id
    candidate = bind_portal_goal_candidate(intent, evidence.proposals[0])
    assert candidate.scope_fingerprint == scope.fingerprint

    traversal = PortalTraversalRuntimeSession(
        candidate,
        source.portals[0],
        PortalTraversalPolicy(
            chassis_front_overhang_m=0.2,
            chassis_rear_overhang_m=0.2,
            start_clearance_m=0.1,
            exit_clearance_m=0.1,
            maximum_lateral_deviation_m=0.15,
            maximum_pose_step_m=0.5,
            maximum_pose_speed_mps=0.6,
            maximum_yaw_error_rad=0.2,
            maximum_yaw_step_rad=0.2,
            maximum_backward_step_m=0.02,
            maximum_motion_disagreement_m=0.1,
            maximum_source_age_ns=5_000_000_000,
            maximum_revision_lag=1,
            minimum_pose_samples=4,
        ),
    )
    portal = source.portals[0]
    axis_x = portal.side_b.x - portal.side_a.x
    axis_y = portal.side_b.y - portal.side_a.y
    axis_length = math.hypot(axis_x, axis_y)
    axis_x /= axis_length
    axis_y /= axis_length
    start_x = portal.side_a.x - 0.4 * axis_x
    start_y = portal.side_a.y - 0.4 * axis_y
    end_x = portal.side_b.x + 0.4 * axis_x
    end_y = portal.side_b.y + 0.4 * axis_y
    travel = math.hypot(end_x - start_x, end_y - start_y)
    for index, fraction in enumerate((0.0, 0.33, 0.66, 1.0), start=2):
        traversal.observe(PairedTraversalReading(
            reading_id=f"pipeline-reading-{index}",
            context=CONTEXT,
            map_revision=10,
            stamp_ns=index * 1_000_000_000,
            x=start_x + fraction * (end_x - start_x),
            y=start_y + fraction * (end_y - start_y),
            yaw=math.atan2(axis_y, axis_x),
            independent_forward_progress_m=fraction * travel,
            independent_source=IndependentMotionSource.FROZEN_RANGE_SCAN,
        ))
    outcome = traversal.finish(
        execution_succeeded=True, evaluated_at_ns=5_100_000_000)
    assert outcome.confirmed is True

    applied = shadow.record_validated_traversal(
        outcome.assessment.traversal_event)
    final_source = shadow.status_source(
        map_status(10),
        portal_memory_age_seconds=0.1,
        region_graph_age_seconds=0.1,
    )

    assert applied.graph.entered is True
    assert applied.task_update.task.state is RegionTaskState.COMPLETED
    assert final_source.graph.current_region_id == portal_tasks[0].region_id
    final_task = tuple(
        task for task in final_source.graph.tasks
        if task.task_id == portal_tasks[0].task_id)[0]
    assert final_task.state is RegionTaskState.COMPLETED
