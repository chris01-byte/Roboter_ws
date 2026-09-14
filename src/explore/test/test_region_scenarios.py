"""Combined synthetic geometry-to-graph scenarios for WE-M2.

Detector geometry, structural qualification and traversal confirmation are
deliberately separate fixture inputs.  This test never derives either truth
verdict from a geometric candidate or a planner result.
"""

from pathlib import Path
import sys

import numpy as np


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE_ROOT))

from explore.portal_memory import (  # noqa: E402
    Point2D,
    PortalConfirmationState,
    PortalMapContext,
    PortalMemory,
    PortalObservation,
    PortalSide,
    PortalStructuralEvidence,
    TraversalDirection,
    TraversalEvent,
)
from explore.portal_planning import (  # noqa: E402
    PortalBridge,
    find_connected_clearance_portals,
)
from explore.region_graph import (  # noqa: E402
    PortalLinkDisposition,
    PortalLinkObservation,
    RegionGraph,
    RegionSeed,
    RegionTaskKind,
    RegionTaskState,
    RegionTaskUpdate,
)


CONTEXT = PortalMapContext(
    session_id="we-m2aj-session",
    map_id="synthetic-apartment-1",
    frame_id="map",
)
RESOLUTION_M = 0.05


def _room_hall_room_map():
    occupancy = np.full((60, 155), -1, dtype=np.int16)
    occupancy[5:55, 3:48] = 0
    occupancy[20:40, 52:100] = 0
    occupancy[5:55, 104:149] = 0
    occupancy[27:33, 48:52] = 0
    occupancy[27:33, 100:104] = 0
    return occupancy


def _portals_from(occupancy, robot_cell):
    return find_connected_clearance_portals(
        occupancy,
        robot_cell,
        resolution_m=RESOLUTION_M,
        analysis_clearance_m=0.20,
        min_target_area_m2=0.40,
        min_gap_m=0.12,
        max_gap_m=0.80,
        exit_margin_m=0.25,
        max_traverse_distance_m=1.00,
    )


def _observation(
        observation_id, revision, bridge,
        evidence=PortalStructuralEvidence.QUALIFIED):
    assert isinstance(bridge, PortalBridge)
    return PortalObservation(
        observation_id=observation_id,
        context=CONTEXT,
        map_revision=revision,
        near_side=Point2D(
            bridge.staging_col * RESOLUTION_M,
            bridge.staging_row * RESOLUTION_M,
        ),
        far_side=Point2D(
            bridge.target_col * RESOLUTION_M,
            bridge.target_row * RESOLUTION_M,
        ),
        structural_evidence=evidence,
    )


def _link(observation_id, revision, portal, region_id, side):
    return PortalLinkObservation(
        observation_id=observation_id,
        context=CONTEXT,
        map_revision=revision,
        portal=portal,
        current_region_id=region_id,
        current_side=side,
    )


def _direction_from(side):
    if side is PortalSide.A:
        return TraversalDirection.A_TO_B
    return TraversalDirection.B_TO_A


def _traversal(
        event_id, portal_id, revision, direction, *, confirmed):
    return TraversalEvent(
        event_id=event_id,
        portal_id=portal_id,
        context=CONTEXT,
        map_revision=revision,
        event_time_ns=revision * 1_000_000_000,
        direction=direction,
        crossing_confirmed=confirmed,
    )


def test_room_hall_room_and_return_keep_truth_and_identity_separate():
    occupancy = _room_hall_room_map()
    memory = PortalMemory(CONTEXT)
    graph = RegionGraph(CONTEXT)
    start_room = graph.start(
        RegionSeed("start-room", CONTEXT, 0)).region_id
    assert start_room == "region_000001"

    first_bridge, = _portals_from(occupancy, (30, 20))
    geometric = memory.observe(_observation(
        "door-one-geometric", 1, first_bridge,
        PortalStructuralEvidence.INSUFFICIENT))
    first_portal_id = geometric.portal_id
    assert first_portal_id == "portal_000001"
    assert memory.snapshot(first_portal_id).confirmation_state is (
        PortalConfirmationState.CANDIDATE)

    deferred = graph.observe_portal(_link(
        "door-one-deferred", 1, memory.snapshot(first_portal_id),
        start_room, geometric.approach_side))
    assert deferred.disposition is PortalLinkDisposition.DEFERRED
    assert deferred.opposite_region_id is None
    assert len(graph.snapshot().regions) == 1

    first_qualified = memory.observe(_observation(
        "door-one-qualified-1", 2, first_bridge))
    first_confirmed = memory.observe(_observation(
        "door-one-qualified-2", 3, first_bridge))
    assert first_qualified.portal_id == first_portal_id
    assert first_confirmed.portal_id == first_portal_id
    assert memory.snapshot(first_portal_id).confirmation_state is (
        PortalConfirmationState.CONFIRMED)

    first_link = graph.observe_portal(_link(
        "door-one-confirmed", 3, memory.snapshot(first_portal_id),
        start_room, first_confirmed.approach_side))
    hall = first_link.opposite_region_id
    assert hall == "region_000002"
    assert graph.region(hall).seen
    assert not graph.region(hall).entered

    unconfirmed_entry = _traversal(
        "door-one-unconfirmed-crossing", first_portal_id, 3,
        _direction_from(first_confirmed.approach_side), confirmed=False)
    memory.record_traversal(unconfirmed_entry)
    rejected_entry = graph.record_traversal(unconfirmed_entry)
    assert not rejected_entry.entered
    assert graph.current_region_id == start_room

    enter_hall = _traversal(
        "enter-hall", first_portal_id, 4,
        _direction_from(first_confirmed.approach_side), confirmed=True)
    memory.record_traversal(enter_hall)
    accepted_entry = graph.record_traversal(enter_hall)
    assert accepted_entry.entered
    assert graph.current_region_id == hall

    hall_bridges = _portals_from(occupancy, (30, 75))
    assert len(hall_bridges) == 2
    second_bridge, = (
        bridge for bridge in hall_bridges
        if bridge.target_center_col > 100.0)
    second_created = memory.observe(_observation(
        "door-two-qualified-1", 5, second_bridge))
    second_confirmed = memory.observe(_observation(
        "door-two-qualified-2", 6, second_bridge))
    second_portal_id = second_created.portal_id
    assert second_portal_id == "portal_000002"
    assert second_confirmed.portal_id == second_portal_id

    second_link = graph.observe_portal(_link(
        "door-two-confirmed", 6, memory.snapshot(second_portal_id),
        hall, second_confirmed.approach_side))
    next_room = second_link.opposite_region_id
    assert next_room == "region_000003"
    assert graph.region(next_room).seen
    assert not graph.region(next_room).entered

    graph.update_task(RegionTaskUpdate(
        update_id="observe-next-room-task",
        task_id="task-portal-000002",
        context=CONTEXT,
        map_revision=6,
        region_id=next_room,
        kind=RegionTaskKind.PORTAL,
        subject_id=second_portal_id,
        state=RegionTaskState.OPEN,
    ))
    enter_next_room = _traversal(
        "enter-next-room", second_portal_id, 7,
        _direction_from(second_confirmed.approach_side), confirmed=True)
    memory.record_traversal(enter_next_room)
    graph.record_traversal(enter_next_room)
    graph.update_task(RegionTaskUpdate(
        update_id="complete-next-room-task",
        task_id="task-portal-000002",
        context=CONTEXT,
        map_revision=7,
        region_id=next_room,
        kind=RegionTaskKind.PORTAL,
        subject_id=second_portal_id,
        state=RegionTaskState.COMPLETED,
    ))

    reverse_bridge, = _portals_from(occupancy, (30, 125))
    reverse = memory.observe(_observation(
        "door-two-from-room", 8, reverse_bridge))
    assert reverse.portal_id == second_portal_id
    assert reverse.approach_side is PortalSide.B
    reverse_link = graph.observe_portal(_link(
        "door-two-reverse-link", 8, memory.snapshot(second_portal_id),
        next_room, reverse.approach_side))
    assert reverse_link.disposition is PortalLinkDisposition.MATCHED
    assert reverse_link.opposite_region_id == hall

    return_to_hall = _traversal(
        "return-to-hall", second_portal_id, 9,
        _direction_from(reverse.approach_side), confirmed=True)
    memory.record_traversal(return_to_hall)
    returned = graph.record_traversal(return_to_hall)

    snapshot = graph.snapshot()
    assert returned.target_region_id == hall
    assert returned.current_region_id == hall
    assert tuple(portal.portal_id for portal in memory.snapshots()) == (
        "portal_000001", "portal_000002")
    assert tuple(region.region_id for region in snapshot.regions) == (
        "region_000001", "region_000002", "region_000003")
    assert tuple(connection.portal_id for connection in snapshot.connections) == (
        "portal_000001", "portal_000002")
    assert snapshot.region_aliases == ()
    assert snapshot.confirmed_entry_count == 3
    assert graph.region(hall).entry_count == 2
    assert graph.region(next_room).entered
    assert tuple(task.task_id for task in snapshot.tasks) == (
        "task-portal-000002",)
    assert snapshot.tasks[0].region_id == next_room
    assert snapshot.tasks[0].state is RegionTaskState.COMPLETED
