from dataclasses import replace
from pathlib import Path
import sys

import pytest


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE_ROOT))

from amadeus_map_identity import (  # noqa: E402
    compact_occupancy_cells,
    map_snapshot_fingerprint,
)
from explore.exploration_child_goal import ExplorationGoalIntent  # noqa: E402
from explore.exploration_policy import TaskAvailabilityState  # noqa: E402
from explore.exploration_scope import AuthorizedExplorationScope  # noqa: E402
from explore.portal_memory import (  # noqa: E402
    Point2D,
    PortalConfirmationState,
    PortalMapContext,
    PortalSnapshot,
    TraversalDirection,
)
from explore.portal_source_adapter import PortalSourceCorrelation  # noqa: E402
from explore.portal_task_evidence import (  # noqa: E402
    PortalTaskEvidenceCapacityError,
    PortalTaskEvidenceError,
    PortalTaskEvidencePolicy,
    bind_portal_goal_candidate,
    build_portal_task_evidence,
)
from explore.region_graph import (  # noqa: E402
    PortalConnectionSnapshot,
    RegionTaskKind,
    RegionTaskSnapshot,
    RegionTaskState,
)


CONTEXT = PortalMapContext("session-m3s", "map-m3s", "map")
STAMP_NS = 1_800_000_000_000_000_000


def map_data(*, cells=None, width=30, height=20):
    resolution = 0.1
    values = list(cells or [0] * (width * height))
    origin = (0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0)
    compact = compact_occupancy_cells(
        cells=values, cell_count=width * height)
    fingerprint = map_snapshot_fingerprint(
        width=width,
        height=height,
        resolution=resolution,
        frame_id="map",
        origin=origin,
        compact_cells=compact,
    )
    return {
        "correlation": PortalSourceCorrelation(
            CONTEXT, 10, fingerprint, STAMP_NS),
        "width": width,
        "height": height,
        "resolution": resolution,
        "frame_id": "map",
        "origin": origin,
        "cells": values,
        "source_stamp_ns": STAMP_NS,
    }


def portal(**changes):
    values = {
        "portal_id": "portal_000001",
        "side_a": Point2D(1.0, 1.0),
        "side_b": Point2D(1.2, 1.0),
        "first_revision": 8,
        "last_revision": 9,
        "observation_count": 2,
        "evidence_count": 2,
        "qualified_evidence_count": 2,
        "confirmation_state": PortalConfirmationState.CONFIRMED,
        "confirmed": True,
        "confirmed_traversal_count": 0,
    }
    values.update(changes)
    return PortalSnapshot(**values)


def task(**changes):
    values = {
        "task_id": "task-portal_000001-side-B",
        "region_id": "region_000002",
        "kind": RegionTaskKind.PORTAL,
        "subject_id": "portal_000001",
        "state": RegionTaskState.OPEN,
        "created_revision": 9,
        "last_revision": 9,
    }
    values.update(changes)
    return RegionTaskSnapshot(**values)


def connection(**changes):
    values = {
        "portal_id": "portal_000001",
        "side_a_region_id": "region_000001",
        "side_b_region_id": "region_000002",
        "first_revision": 9,
        "last_revision": 9,
        "internal": False,
    }
    values.update(changes)
    return PortalConnectionSnapshot(**values)


def scope(**changes):
    values = {
        "scope_id": "scope-m3s",
        "context": CONTEXT,
        "vertices": (
            Point2D(0.0, 0.0), Point2D(3.0, 0.0),
            Point2D(3.0, 2.0), Point2D(0.0, 2.0),
        ),
    }
    values.update(changes)
    return AuthorizedExplorationScope(**values)


def policy(**changes):
    values = {
        "clearance_m": 0.10,
        "scope_clearance_m": 0.10,
        "robot_seed_search_m": 0.20,
        "chassis_rear_overhang_m": 0.20,
        "exit_clearance_m": 0.10,
        "target_search_m": 0.20,
        "maximum_target_lateral_m": 0.15,
        "portal_path_radius_m": 0.15,
    }
    values.update(changes)
    return PortalTaskEvidencePolicy(**values)


def build(**changes):
    arguments = {
        **map_data(),
        "robot_xy": (0.5, 1.05),
        "current_region_id": "region_000001",
        "tasks": (task(),),
        "portals": (portal(),),
        "connections": (connection(),),
        "scope": scope(),
        "policy": policy(),
    }
    arguments.update(changes)
    return build_portal_task_evidence(**arguments)


def test_open_portal_task_gets_scoped_route_and_zero_claimed_information():
    batch = build()

    assert batch.availability[0].state is TaskAvailabilityState.AVAILABLE
    assert batch.utilities[0].information_gain_square_m == 0.0
    proposal = batch.proposals[0]
    assert proposal.direction is TraversalDirection.A_TO_B
    assert proposal.target_x_m >= 1.5
    assert proposal.scope_id == "scope-m3s"
    assert len(proposal.scope_fingerprint) == 64
    assert proposal.context == CONTEXT
    assert proposal.route_length_m > 0.0
    assert proposal.path_cells[-1] == (
        proposal.target_row, proposal.target_col)
    assert all(0 <= row < 20 and 0 <= col < 30
               for row, col in proposal.path_cells)


@pytest.mark.parametrize("kind", (
    RegionTaskKind.PORTAL,
    RegionTaskKind.TRANSIT,
))
def test_task_created_on_current_map_waits_for_a_newer_revision(kind):
    current = build(tasks=(task(kind=kind, last_revision=10),))

    assert current.availability[0].state is TaskAvailabilityState.UNKNOWN
    assert current.availability[0].reason == (
        "portal_task_requires_newer_map_revision")
    assert current.proposals == ()
    assert current.utilities == ()


def test_reverse_portal_task_uses_canonical_b_to_a_direction():
    reverse_task = task(
        task_id="task-portal_000001-side-A",
        region_id="region_000001")
    reverse = build(
        robot_xy=(1.7, 1.05),
        current_region_id="region_000002",
        tasks=(reverse_task,))

    proposal = reverse.proposals[0]
    assert proposal.direction is TraversalDirection.B_TO_A
    assert proposal.target_x_m <= 0.7


def test_selected_proposal_binds_to_exact_child_intent():
    proposal = build().proposals[0]
    intent = ExplorationGoalIntent(
        "intent-portal-10",
        proposal.task_id,
        proposal.region_id,
        CONTEXT,
        10,
    )

    candidate = bind_portal_goal_candidate(intent, proposal)

    assert candidate.intent_id == intent.intent_id
    assert candidate.path_cells == proposal.path_cells
    with pytest.raises(PortalTaskEvidenceError):
        bind_portal_goal_candidate(
            replace(intent, map_revision=11), proposal)
    with pytest.raises(PortalTaskEvidenceError):
        bind_portal_goal_candidate(
            replace(intent, context=replace(
                CONTEXT, session_id="other-session")), proposal)


@pytest.mark.parametrize("kind", (RegionTaskKind.PORTAL, RegionTaskKind.TRANSIT))
def test_scope_excluding_far_side_blocks_goal_and_path(kind):
    restricted = scope(vertices=(
        Point2D(0.0, 0.0), Point2D(1.3, 0.0),
        Point2D(1.3, 2.0), Point2D(0.0, 2.0),
    ))

    batch = build(scope=restricted, tasks=(task(kind=kind),))

    assert batch.availability[0].state is (
        TaskAvailabilityState.TEMPORARILY_BLOCKED)
    assert batch.availability[0].reason == (
        "no_scoped_route_through_selected_portal")
    assert batch.proposals == ()


@pytest.mark.parametrize("kind", (RegionTaskKind.PORTAL, RegionTaskKind.TRANSIT))
def test_wall_without_selected_portal_route_blocks_task(kind):
    data = map_data()
    cells = list(data["cells"])
    for row in range(data["height"]):
        cells[row * data["width"] + 11] = 100
    blocked = map_data(cells=cells)

    batch = build(**blocked, tasks=(task(kind=kind),))

    assert batch.availability[0].state is (
        TaskAvailabilityState.TEMPORARILY_BLOCKED)
    assert batch.proposals == ()


@pytest.mark.parametrize("kind", (RegionTaskKind.PORTAL, RegionTaskKind.TRANSIT))
@pytest.mark.parametrize(("changes", "reason"), [
    ({"portals": ()}, "portal_graph_evidence_missing"),
    ({"connections": ()}, "portal_graph_evidence_missing"),
    ({"portals": (portal(confirmed=False),)}, "portal_not_confirmed"),
    ({"connections": (connection(internal=True),)},
     "portal_connection_is_internal"),
    ({"robot_xy": None}, "missing_robot_pose"),
    ({"current_region_id": "region_000099"},
     "portal_task_not_adjacent_to_current_region"),
])
def test_missing_or_nontraversable_portal_evidence_is_explicit(changes, reason, kind):
    batch = build(**changes, tasks=(task(kind=kind),))

    assert batch.availability[0].reason == reason
    assert batch.proposals == ()


def test_wrong_scope_context_and_map_capacity_fail_closed():
    with pytest.raises(PortalTaskEvidenceError):
        build(scope=scope(context=replace(CONTEXT, map_id="other-map")))
    with pytest.raises(PortalTaskEvidenceCapacityError):
        build(policy=policy(max_cells=100))


def test_only_open_portal_tasks_are_accepted():
    with pytest.raises(PortalTaskEvidenceError):
        build(tasks=(task(kind=RegionTaskKind.FRONTIER),))
    with pytest.raises(PortalTaskEvidenceError):
        build(tasks=(task(state=RegionTaskState.COMPLETED),))
    with pytest.raises(PortalTaskEvidenceError):
        build(tasks=(task(last_revision=11),))


def test_goal_value_objects_reject_forged_nonadjacent_path():
    proposal = build().proposals[0]

    with pytest.raises(PortalTaskEvidenceError):
        replace(proposal, path_cells=(proposal.path_cells[0],
                                      proposal.path_cells[-1]))
