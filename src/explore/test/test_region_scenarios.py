"""Combined synthetic geometry-to-graph scenarios for WE-M2.

Detector geometry, structural qualification and traversal confirmation are
deliberately separate fixture inputs.  This test never derives either truth
verdict from a geometric candidate or a planner result.
"""

from pathlib import Path
import math
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
    RegionMerge,
    RegionPortalEnd,
    RegionSeed,
    RegionSplit,
    RegionSplitTarget,
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


def _open_living_area_map():
    occupancy = np.full((60, 100), -1, dtype=np.int16)
    occupancy[5:55, 3:97] = 0
    return occupancy


def _l_hall_map():
    occupancy = np.full((90, 120), -1, dtype=np.int16)
    occupancy[5:45, 3:43] = 0
    occupancy[18:32, 47:85] = 0
    occupancy[18:65, 71:85] = 0
    occupancy[69:86, 40:110] = 0
    occupancy[22:28, 43:47] = 0
    occupancy[65:69, 76:82] = 0
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


def _transformed_observation(
        observation_id, revision, bridge, *, origin, yaw):
    cosine = math.cos(yaw)
    sine = math.sin(yaw)

    def metric_point(row, col):
        local_x = col * RESOLUTION_M
        local_y = row * RESOLUTION_M
        return Point2D(
            origin[0] + cosine * local_x - sine * local_y,
            origin[1] + sine * local_x + cosine * local_y,
        )

    return PortalObservation(
        observation_id=observation_id,
        context=CONTEXT,
        map_revision=revision,
        near_side=metric_point(bridge.staging_row, bridge.staging_col),
        far_side=metric_point(bridge.target_row, bridge.target_col),
        structural_evidence=PortalStructuralEvidence.QUALIFIED,
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


def test_open_living_area_creates_no_portal_region_or_task():
    memory = PortalMemory(CONTEXT)
    graph = RegionGraph(CONTEXT)
    start_room = graph.start(
        RegionSeed("open-area-start", CONTEXT, 0)).region_id

    assert _portals_from(_open_living_area_map(), (30, 20)) == []
    assert memory.snapshots() == ()

    snapshot = graph.snapshot()
    assert tuple(region.region_id for region in snapshot.regions) == (
        start_room,)
    assert snapshot.connections == ()
    assert snapshot.tasks == ()
    assert snapshot.confirmed_entry_count == 0


def test_furniture_neck_stays_uncertain_and_does_not_split_region():
    occupancy = _open_living_area_map()
    # A large synthetic furniture island leaves two routes inside one room.
    # Its upper route resembles a neck after analysis erosion, but the fixture
    # explicitly supplies contradictory structural truth.
    occupancy[12:48, 45:55] = -1
    bridge, = _portals_from(occupancy, (30, 20))
    memory = PortalMemory(CONTEXT)
    graph = RegionGraph(CONTEXT)
    start_room = graph.start(
        RegionSeed("furniture-start", CONTEXT, 0)).region_id

    observed = memory.observe(_observation(
        "furniture-neck", 1, bridge,
        PortalStructuralEvidence.CONTRADICTORY))
    portal = memory.snapshot(observed.portal_id)
    assert portal.confirmation_state is PortalConfirmationState.UNCERTAIN
    assert not portal.confirmed

    deferred = graph.observe_portal(_link(
        "furniture-neck-link", 1, portal,
        start_room, observed.approach_side))
    assert deferred.disposition is PortalLinkDisposition.DEFERRED
    assert deferred.opposite_region_id is None

    snapshot = graph.snapshot()
    assert tuple(region.region_id for region in snapshot.regions) == (
        start_room,)
    assert snapshot.connections == ()
    assert snapshot.tasks == ()
    assert snapshot.confirmed_entry_count == 0


def test_l_hall_loop_merge_reuses_start_region_and_keeps_two_portals():
    occupancy = _l_hall_map()
    # These two free cells are on different arms of the same L-shaped hall.
    assert occupancy[25, 60] == 0
    assert occupancy[50, 78] == 0
    memory = PortalMemory(CONTEXT)
    graph = RegionGraph(CONTEXT)
    start_room = graph.start(
        RegionSeed("loop-start", CONTEXT, 0)).region_id
    assert start_room == "region_000001"

    first_bridge, = _portals_from(occupancy, (25, 20))
    memory.observe(_observation(
        "loop-door-one-qualified-1", 1, first_bridge))
    first_observed = memory.observe(_observation(
        "loop-door-one-qualified-2", 2, first_bridge))
    first_portal_id = first_observed.portal_id
    assert first_portal_id == "portal_000001"
    assert first_observed.approach_side is PortalSide.A
    first_link = graph.observe_portal(_link(
        "loop-door-one-link", 2, memory.snapshot(first_portal_id),
        start_room, first_observed.approach_side))
    hall = first_link.opposite_region_id
    assert hall == "region_000002"
    enter_hall = _traversal(
        "loop-enter-hall", first_portal_id, 3,
        _direction_from(first_observed.approach_side), confirmed=True)
    memory.record_traversal(enter_hall)
    graph.record_traversal(enter_hall)

    hall_bridges = _portals_from(occupancy, (25, 60))
    assert len(hall_bridges) == 2
    second_bridge, = (
        bridge for bridge in hall_bridges
        if bridge.target_center_row > 70.0)
    memory.observe(_observation(
        "loop-door-two-qualified-1", 4, second_bridge))
    second_observed = memory.observe(_observation(
        "loop-door-two-qualified-2", 5, second_bridge))
    second_portal_id = second_observed.portal_id
    assert second_portal_id == "portal_000002"
    assert second_observed.approach_side is PortalSide.A
    second_link = graph.observe_portal(_link(
        "loop-door-two-link", 5, memory.snapshot(second_portal_id),
        hall, second_observed.approach_side))
    provisional_return_region = second_link.opposite_region_id
    assert provisional_return_region == "region_000003"
    enter_provisional_region = _traversal(
        "loop-enter-provisional-region", second_portal_id, 6,
        _direction_from(second_observed.approach_side), confirmed=True)
    memory.record_traversal(enter_provisional_region)
    graph.record_traversal(enter_provisional_region)
    assert tuple(region.region_id for region in graph.snapshot().regions) == (
        "region_000001", "region_000002", "region_000003")

    merged = graph.merge_regions(RegionMerge(
        merge_id="explicit-loop-truth",
        context=CONTEXT,
        map_revision=7,
        first_region_id=provisional_return_region,
        second_region_id=start_room,
        reason="fixture_supplied_loop_closure",
    ))
    assert merged.canonical_region_id == start_room
    assert merged.removed_region_id == provisional_return_region
    assert graph.current_region_id == start_room

    return_to_hall = _traversal(
        "loop-return-to-hall", second_portal_id, 8,
        TraversalDirection.B_TO_A, confirmed=True)
    memory.record_traversal(return_to_hall)
    returned = graph.record_traversal(return_to_hall)

    snapshot = graph.snapshot()
    assert returned.target_region_id == hall
    assert returned.current_region_id == hall
    assert tuple(portal.portal_id for portal in memory.snapshots()) == (
        "portal_000001", "portal_000002")
    assert tuple(region.region_id for region in snapshot.regions) == (
        start_room, hall)
    assert snapshot.region_aliases == (
        (provisional_return_region, start_room),)
    assert len(snapshot.connections) == 2
    assert {
        frozenset((connection.side_a_region_id,
                   connection.side_b_region_id))
        for connection in snapshot.connections
    } == {frozenset((start_room, hall))}
    assert snapshot.confirmed_entry_count == 3
    assert graph.region(hall).entry_count == 2


def test_map_growth_rotation_and_correction_keep_ids_and_tasks_explicit():
    occupancy = _room_hall_room_map()
    original = occupancy.copy()
    base_bridge, = _portals_from(occupancy, (30, 20))

    grown = np.pad(
        occupancy, ((10, 0), (20, 0)),
        mode="constant", constant_values=-1)
    grown_original = grown.copy()
    grown_bridge, = _portals_from(grown, (40, 40))

    rotated = np.rot90(occupancy)
    rotated_original = rotated.copy()
    rotated_robot = (occupancy.shape[1] - 1 - 20, 30)
    rotated_bridge, = _portals_from(rotated, rotated_robot)

    base_observation = _transformed_observation(
        "map-base", 1, base_bridge, origin=(0.0, 0.0), yaw=0.0)
    grown_observation = _transformed_observation(
        "map-grown", 2, grown_bridge,
        origin=(-20 * RESOLUTION_M, -10 * RESOLUTION_M), yaw=0.0)
    rotated_observation = _transformed_observation(
        "map-rotated", 3, rotated_bridge,
        origin=((occupancy.shape[1] - 1) * RESOLUTION_M, 0.0),
        yaw=math.pi / 2.0)
    np.testing.assert_allclose(
        (base_observation.near_side.x, base_observation.near_side.y,
         base_observation.far_side.x, base_observation.far_side.y),
        (grown_observation.near_side.x, grown_observation.near_side.y,
         grown_observation.far_side.x, grown_observation.far_side.y))
    np.testing.assert_allclose(
        (base_observation.near_side.x, base_observation.near_side.y,
         base_observation.far_side.x, base_observation.far_side.y),
        (rotated_observation.near_side.x, rotated_observation.near_side.y,
         rotated_observation.far_side.x, rotated_observation.far_side.y),
        atol=1e-12)

    memory = PortalMemory(CONTEXT)
    base_result = memory.observe(base_observation)
    grown_result = memory.observe(grown_observation)
    rotated_result = memory.observe(rotated_observation)
    portal_id = base_result.portal_id
    assert portal_id == "portal_000001"
    assert grown_result.portal_id == portal_id
    assert rotated_result.portal_id == portal_id
    assert memory.snapshot(portal_id).confirmation_state is (
        PortalConfirmationState.CONFIRMED)

    graph = RegionGraph(CONTEXT)
    start_room = graph.start(
        RegionSeed("map-change-start", CONTEXT, 0)).region_id
    linked = graph.observe_portal(_link(
        "map-change-link", 3, memory.snapshot(portal_id),
        start_room, rotated_result.approach_side))
    hall = linked.opposite_region_id
    assert start_room == "region_000001"
    assert hall == "region_000002"
    graph.update_task(RegionTaskUpdate(
        update_id="map-change-task-create",
        task_id="task-map-change",
        context=CONTEXT,
        map_revision=3,
        region_id=hall,
        kind=RegionTaskKind.PORTAL,
        subject_id=portal_id,
        state=RegionTaskState.OPEN,
    ))
    enter_hall = _traversal(
        "map-change-enter-hall", portal_id, 4,
        _direction_from(rotated_result.approach_side), confirmed=True)
    memory.record_traversal(enter_hall)
    graph.record_traversal(enter_hall)
    assert graph.current_region_id == hall
    assert graph.task("task-map-change").region_id == hall

    graph.merge_regions(RegionMerge(
        merge_id="map-correction-merge",
        context=CONTEXT,
        map_revision=5,
        first_region_id=start_room,
        second_region_id=hall,
        reason="fixture_supplied_map_overlap",
    ))
    assert graph.current_region_id == start_room
    assert graph.task("task-map-change").region_id == start_room

    corrected = graph.split_region(RegionSplit(
        split_id="map-correction-split",
        context=CONTEXT,
        map_revision=6,
        source_region_id=start_room,
        retained_portal_ends=(RegionPortalEnd(portal_id, PortalSide.A),),
        created_portal_ends=(RegionPortalEnd(portal_id, PortalSide.B),),
        retained_task_ids=(),
        created_task_ids=("task-map-change",),
        state_target=RegionSplitTarget.CREATED,
        reason="fixture_supplied_corrected_boundary",
    ))

    snapshot = graph.snapshot()
    assert corrected.retained_region_id == start_room
    assert corrected.created_region_id == "region_000003"
    assert graph.current_region_id == corrected.created_region_id
    assert graph.resolve_region_id(hall) == start_room
    assert snapshot.region_aliases == ((hall, start_room),)
    assert tuple(region.region_id for region in snapshot.regions) == (
        start_room, corrected.created_region_id)
    assert graph.task("task-map-change").region_id == (
        corrected.created_region_id)
    assert graph.task("task-map-change").state is RegionTaskState.OPEN
    connection = graph.connection(portal_id)
    assert connection.side_a_region_id == start_room
    assert connection.side_b_region_id == corrected.created_region_id
    assert tuple(portal.portal_id for portal in memory.snapshots()) == (
        portal_id,)
    assert np.array_equal(occupancy, original)
    assert np.array_equal(grown, grown_original)
    assert np.array_equal(rotated, rotated_original)
