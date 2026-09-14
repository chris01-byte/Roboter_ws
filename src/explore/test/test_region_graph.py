from dataclasses import replace
from pathlib import Path
import sys

import pytest


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE_ROOT))

from explore.portal_memory import (  # noqa: E402
    Point2D,
    PortalMapContext,
    PortalMemory,
    PortalObservation,
    PortalSide,
    PortalStructuralEvidence,
    TraversalDirection,
    TraversalEvent,
)
from explore.region_graph import (  # noqa: E402
    PortalLinkDisposition,
    PortalLinkObservation,
    RegionContextMismatchError,
    RegionGraph,
    RegionGraphCapacityError,
    RegionGraphConflictError,
    RegionGraphError,
    RegionGraphPolicy,
    RegionMerge,
    RegionSeed,
    StaleGraphUpdateError,
    UnknownPortalConnectionError,
    UnknownRegionError,
)


CONTEXT = PortalMapContext(
    session_id="session-20260914",
    map_id="live-map-epoch-1",
    frame_id="map",
)


def portal_observation(
        observation_id, revision, near=(0.0, 0.0), far=(1.0, 0.0),
        *, evidence=PortalStructuralEvidence.QUALIFIED,
        context=CONTEXT):
    return PortalObservation(
        observation_id=observation_id,
        context=context,
        map_revision=revision,
        near_side=Point2D(*near),
        far_side=Point2D(*far),
        structural_evidence=evidence,
    )


def confirmed_portal(memory, prefix, first_revision, *, y=0.0):
    created = memory.observe(portal_observation(
        f"{prefix}-1", first_revision,
        near=(0.0, y), far=(1.0, y)))
    memory.observe(portal_observation(
        f"{prefix}-2", first_revision + 1,
        near=(0.01, y), far=(1.01, y)))
    return memory.snapshot(created.portal_id)


def started_graph(*, revision=0, policy=None):
    graph = RegionGraph(CONTEXT, policy)
    start = graph.start(RegionSeed("start-observation", CONTEXT, revision))
    return graph, start.region_id


def link_observation(
        observation_id, revision, portal, region_id, side,
        *, context=CONTEXT):
    return PortalLinkObservation(
        observation_id=observation_id,
        context=context,
        map_revision=revision,
        portal=portal,
        current_region_id=region_id,
        current_side=side,
    )


def traversal(
        event_id, portal_id, revision, direction, *, confirmed=True,
        context=CONTEXT, event_time_ns=100):
    return TraversalEvent(
        event_id=event_id,
        portal_id=portal_id,
        context=context,
        map_revision=revision,
        event_time_ns=event_time_ns,
        direction=direction,
        crossing_confirmed=confirmed,
    )


def three_region_path(*, policy=None):
    memory = PortalMemory(CONTEXT)
    first_portal = confirmed_portal(memory, "door-one", 1, y=0.0)
    second_portal = confirmed_portal(memory, "door-two", 3, y=1.0)
    graph, start_room = started_graph(policy=policy)
    first_link_input = link_observation(
        "link-one", 2, first_portal, start_room, PortalSide.A)
    first_link = graph.observe_portal(first_link_input)
    hall = first_link.opposite_region_id
    first_event = traversal(
        "enter-hall", first_portal.portal_id, 2,
        TraversalDirection.A_TO_B)
    graph.record_traversal(first_event)
    second_link_input = link_observation(
        "link-two", 4, second_portal, hall, PortalSide.A)
    second_link = graph.observe_portal(second_link_input)
    next_room = second_link.opposite_region_id
    second_event = traversal(
        "enter-next-room", second_portal.portal_id, 4,
        TraversalDirection.A_TO_B, event_time_ns=200)
    graph.record_traversal(second_event)
    return {
        "graph": graph,
        "start_room": start_room,
        "hall": hall,
        "next_room": next_room,
        "first_portal": first_portal,
        "second_portal": second_portal,
        "first_link_input": first_link_input,
        "second_link_input": second_link_input,
        "first_event": first_event,
        "second_event": second_event,
    }


def test_start_room_hall_room_and_return_reuse_the_same_hall_region():
    memory = PortalMemory(CONTEXT)
    first_portal = confirmed_portal(memory, "door-one", 1, y=0.0)
    second_portal = confirmed_portal(memory, "door-two", 3, y=1.0)
    graph, start_room = started_graph()

    first_link = graph.observe_portal(link_observation(
        "link-one", 2, first_portal, start_room, PortalSide.A))
    hall = first_link.opposite_region_id
    graph.record_traversal(traversal(
        "enter-hall", first_portal.portal_id, 2,
        TraversalDirection.A_TO_B))
    second_link = graph.observe_portal(link_observation(
        "link-two", 4, second_portal, hall, PortalSide.A))
    next_room = second_link.opposite_region_id
    graph.record_traversal(traversal(
        "enter-next-room", second_portal.portal_id, 4,
        TraversalDirection.A_TO_B, event_time_ns=200))
    returned = graph.record_traversal(traversal(
        "return-to-hall", second_portal.portal_id, 5,
        TraversalDirection.B_TO_A, event_time_ns=300))

    snapshot = graph.snapshot()
    assert start_room == "region_000001"
    assert hall == "region_000002"
    assert next_room == "region_000003"
    assert returned.target_region_id == hall
    assert returned.current_region_id == hall
    assert len(snapshot.regions) == 3
    assert len(snapshot.connections) == 2
    assert snapshot.confirmed_entry_count == 3
    assert graph.region(hall).entry_count == 2
    assert graph.region(next_room).entered


def test_same_portal_from_opposite_side_matches_without_new_region():
    memory = PortalMemory(CONTEXT)
    portal = confirmed_portal(memory, "door", 1)
    graph, start_room = started_graph()
    created = graph.observe_portal(link_observation(
        "from-a", 2, portal, start_room, PortalSide.A))
    hall = created.opposite_region_id
    graph.record_traversal(traversal(
        "to-hall", portal.portal_id, 2, TraversalDirection.A_TO_B))

    reverse = graph.observe_portal(link_observation(
        "from-b", 3, portal, hall, PortalSide.B))

    assert reverse.disposition is PortalLinkDisposition.MATCHED
    assert reverse.opposite_region_id == start_room
    assert len(graph.snapshot().regions) == 2
    assert len(graph.snapshot().connections) == 1


def test_open_area_without_confirmed_portal_remains_one_region():
    graph, start_room = started_graph(revision=4)
    seed = RegionSeed("start-observation", CONTEXT, 4)

    replay = graph.start(seed)

    assert replay.duplicate
    assert replay.region_id == start_room
    assert graph.current_region_id == start_room
    assert len(graph.snapshot().regions) == 1
    assert graph.snapshot().connections == ()
    with pytest.raises(RegionGraphConflictError):
        graph.start(RegionSeed("invented-second-area", CONTEXT, 4))


@pytest.mark.parametrize(
    "evidence",
    [
        PortalStructuralEvidence.INSUFFICIENT,
        PortalStructuralEvidence.CONTRADICTORY,
    ],
)
def test_candidate_or_uncertain_portal_does_not_create_region(evidence):
    memory = PortalMemory(CONTEXT)
    created = memory.observe(portal_observation(
        "unconfirmed-1", 1, evidence=evidence))
    memory.observe(portal_observation(
        "unconfirmed-2", 2, evidence=evidence))
    portal = memory.snapshot(created.portal_id)
    graph, start_room = started_graph()

    result = graph.observe_portal(link_observation(
        "deferred-link", 2, portal, start_room, PortalSide.A))

    assert result.disposition is PortalLinkDisposition.DEFERRED
    assert result.opposite_region_id is None
    assert len(graph.snapshot().regions) == 1
    assert graph.snapshot().connections == ()


def test_unconfirmed_traversal_changes_neither_entry_nor_current_region():
    memory = PortalMemory(CONTEXT)
    portal = confirmed_portal(memory, "door", 1)
    graph, start_room = started_graph()
    link = graph.observe_portal(link_observation(
        "link", 2, portal, start_room, PortalSide.A))

    result = graph.record_traversal(traversal(
        "incomplete", portal.portal_id, 2,
        TraversalDirection.A_TO_B, confirmed=False))

    assert not result.entered
    assert result.current_region_id == start_room
    assert graph.current_region_id == start_room
    assert not graph.region(link.opposite_region_id).entered
    assert graph.snapshot().confirmed_entry_count == 0


def test_portal_and_traversal_replays_are_idempotent_after_later_progress():
    memory = PortalMemory(CONTEXT)
    portal = confirmed_portal(memory, "door", 1)
    graph, start_room = started_graph()
    link_input = link_observation(
        "link", 2, portal, start_room, PortalSide.A)
    link = graph.observe_portal(link_input)
    event = traversal(
        "enter", portal.portal_id, 2, TraversalDirection.A_TO_B)
    graph.record_traversal(event)

    link_replay = graph.observe_portal(link_input)
    event_replay = graph.record_traversal(event)

    assert link_replay.duplicate
    assert len(graph.snapshot().regions) == 2
    assert event_replay.duplicate
    assert not event_replay.entered
    assert event_replay.current_region_id == link.opposite_region_id
    assert graph.region(link.opposite_region_id).entry_count == 1


def test_reused_input_ids_with_different_content_fail_closed():
    memory = PortalMemory(CONTEXT)
    portal = confirmed_portal(memory, "door", 1)
    graph, start_room = started_graph()
    link = link_observation(
        "fixed-link", 2, portal, start_room, PortalSide.A)
    graph.observe_portal(link)

    with pytest.raises(RegionGraphConflictError):
        graph.observe_portal(replace(link, current_side=PortalSide.B))

    event = traversal(
        "fixed-event", portal.portal_id, 2,
        TraversalDirection.A_TO_B, confirmed=False)
    graph.record_traversal(event)
    with pytest.raises(RegionGraphConflictError):
        graph.record_traversal(replace(event, crossing_confirmed=True))


def test_unknown_region_portal_and_wrong_current_region_fail_closed():
    memory = PortalMemory(CONTEXT)
    portal = confirmed_portal(memory, "door", 1)
    graph, start_room = started_graph()

    with pytest.raises(UnknownRegionError):
        graph.observe_portal(link_observation(
            "unknown-region", 2, portal, "region_999999", PortalSide.A))
    with pytest.raises(UnknownPortalConnectionError):
        graph.record_traversal(traversal(
            "unknown-portal", "portal_999999", 2,
            TraversalDirection.A_TO_B))

    link = graph.observe_portal(link_observation(
        "valid-link", 2, portal, start_room, PortalSide.A))
    with pytest.raises(RegionGraphConflictError):
        graph.observe_portal(link_observation(
            "wrong-current", 2, portal,
            link.opposite_region_id, PortalSide.B))


def test_context_mismatches_are_rejected_for_all_graph_inputs():
    foreign = PortalMapContext("other-session", CONTEXT.map_id, "map")
    graph = RegionGraph(CONTEXT)

    with pytest.raises(RegionContextMismatchError):
        graph.start(RegionSeed("foreign-start", foreign, 0))

    graph, start_room = started_graph()
    memory = PortalMemory(CONTEXT)
    portal = confirmed_portal(memory, "door", 1)
    with pytest.raises(RegionContextMismatchError):
        graph.observe_portal(link_observation(
            "foreign-link", 2, portal, start_room, PortalSide.A,
            context=foreign))
    with pytest.raises(RegionContextMismatchError):
        graph.record_traversal(traversal(
            "foreign-event", portal.portal_id, 2,
            TraversalDirection.A_TO_B, context=foreign))


def test_stale_updates_and_future_portal_snapshot_are_rejected():
    memory = PortalMemory(CONTEXT)
    portal = confirmed_portal(memory, "door", 3)
    graph, start_room = started_graph(revision=4)

    with pytest.raises(StaleGraphUpdateError):
        graph.observe_portal(link_observation(
            "stale-link", 3, portal, start_room, PortalSide.A))
    future_portal = replace(portal, last_revision=6)
    with pytest.raises(StaleGraphUpdateError):
        graph.observe_portal(link_observation(
            "future-portal", 5, future_portal,
            start_room, PortalSide.A))


def test_inconsistent_portal_confirmation_contract_is_rejected():
    memory = PortalMemory(CONTEXT)
    portal = confirmed_portal(memory, "door", 1)
    graph, start_room = started_graph()

    inconsistent = replace(portal, confirmed=False)

    with pytest.raises(RegionGraphError):
        graph.observe_portal(link_observation(
            "inconsistent", 2, inconsistent,
            start_room, PortalSide.A))


def test_region_connection_and_observation_capacities_fail_without_eviction():
    memory = PortalMemory(CONTEXT)
    first_portal = confirmed_portal(memory, "door-one", 1, y=0.0)
    second_portal = confirmed_portal(memory, "door-two", 3, y=1.0)

    region_limited, start = started_graph(policy=RegionGraphPolicy(
        max_regions=1))
    with pytest.raises(RegionGraphCapacityError):
        region_limited.observe_portal(link_observation(
            "region-limit", 2, first_portal, start, PortalSide.A))
    assert len(region_limited.snapshot().regions) == 1

    connection_limited, start = started_graph(policy=RegionGraphPolicy(
        max_connections=1))
    first = connection_limited.observe_portal(link_observation(
        "first-link", 2, first_portal, start, PortalSide.A))
    connection_limited.record_traversal(traversal(
        "enter-neighbor", first_portal.portal_id, 2,
        TraversalDirection.A_TO_B))
    with pytest.raises(RegionGraphCapacityError):
        connection_limited.observe_portal(link_observation(
            "connection-limit", 4, second_portal,
            first.opposite_region_id, PortalSide.A))
    assert len(connection_limited.snapshot().connections) == 1

    candidate_memory = PortalMemory(CONTEXT)
    candidate_id = candidate_memory.observe(portal_observation(
        "candidate-1", 1,
        evidence=PortalStructuralEvidence.INSUFFICIENT)).portal_id
    candidate = candidate_memory.snapshot(candidate_id)
    observation_limited, start = started_graph(policy=RegionGraphPolicy(
        max_portal_observations=1))
    observation_limited.observe_portal(link_observation(
        "accepted-candidate", 1, candidate, start, PortalSide.A))
    with pytest.raises(RegionGraphCapacityError):
        observation_limited.observe_portal(link_observation(
            "observation-limit", 1, candidate, start, PortalSide.A))


def test_traversal_capacity_is_independent_and_preserves_current_region():
    memory = PortalMemory(CONTEXT)
    portal = confirmed_portal(memory, "door", 1)
    graph, start_room = started_graph(policy=RegionGraphPolicy(
        max_traversal_events=1))
    graph.observe_portal(link_observation(
        "link", 2, portal, start_room, PortalSide.A))
    graph.record_traversal(traversal(
        "attempt-one", portal.portal_id, 2,
        TraversalDirection.A_TO_B, confirmed=False))

    with pytest.raises(RegionGraphCapacityError):
        graph.record_traversal(traversal(
            "attempt-two", portal.portal_id, 2,
            TraversalDirection.A_TO_B, confirmed=False,
            event_time_ns=200))
    assert graph.current_region_id == start_room
    assert graph.snapshot().confirmed_entry_count == 0


@pytest.mark.parametrize(
    "factory",
    [
        lambda: RegionGraphPolicy(max_regions=0),
        lambda: RegionSeed("bad id", CONTEXT, 0),
        lambda: RegionSeed("valid", CONTEXT, True),
    ],
)
def test_invalid_policy_and_seed_fields_are_rejected(factory):
    with pytest.raises(RegionGraphError):
        factory()


def test_loop_closure_merge_rewrites_topology_to_deterministic_region():
    path = three_region_path()
    graph = path["graph"]

    result = graph.merge_regions(RegionMerge(
        merge_id="close-loop",
        context=CONTEXT,
        map_revision=5,
        first_region_id=path["next_room"],
        second_region_id=path["start_room"],
        reason="synthetic_loop_closure",
    ))

    snapshot = graph.snapshot()
    assert result.canonical_region_id == path["start_room"]
    assert result.removed_region_id == path["next_room"]
    assert graph.current_region_id == path["start_room"]
    assert len(snapshot.regions) == 2
    assert len(snapshot.connections) == 2
    first = graph.connection(path["first_portal"].portal_id)
    second = graph.connection(path["second_portal"].portal_id)
    assert (first.side_a_region_id, first.side_b_region_id) == (
        path["start_room"], path["hall"])
    assert (second.side_a_region_id, second.side_b_region_id) == (
        path["hall"], path["start_room"])


def test_removed_id_resolves_as_alias_and_combines_region_state():
    path = three_region_path()
    graph = path["graph"]
    before_entries = graph.snapshot().confirmed_entry_count
    graph.merge_regions(RegionMerge(
        "merge-state", CONTEXT, 5,
        path["next_room"], path["start_room"], "synthetic_overlap"))

    canonical = graph.region(path["start_room"])
    through_alias = graph.region(path["next_room"])

    assert graph.resolve_region_id(path["next_room"]) == path["start_room"]
    assert through_alias == canonical
    assert path["next_room"] in canonical.alias_ids
    assert canonical.seen
    assert canonical.entered
    assert canonical.entry_count == 1
    assert set(canonical.portal_ids) == {
        path["first_portal"].portal_id,
        path["second_portal"].portal_id,
    }
    assert graph.snapshot().confirmed_entry_count == before_entries
    assert graph.snapshot().region_aliases == (
        (path["next_room"], path["start_room"]),)


def test_old_portal_and_traversal_replays_resolve_alias_without_mutation():
    path = three_region_path()
    graph = path["graph"]
    graph.merge_regions(RegionMerge(
        "merge-replay", CONTEXT, 5,
        path["start_room"], path["next_room"], "synthetic_loop"))
    before = graph.snapshot()

    link_replay = graph.observe_portal(path["second_link_input"])
    event_replay = graph.record_traversal(path["second_event"])

    assert link_replay.duplicate
    assert link_replay.current_region_id == path["hall"]
    assert link_replay.opposite_region_id == path["start_room"]
    assert event_replay.duplicate
    assert not event_replay.entered
    assert event_replay.source_region_id == path["hall"]
    assert event_replay.target_region_id == path["start_room"]
    assert event_replay.current_region_id == path["start_room"]
    assert graph.snapshot() == before


def test_historical_alias_is_accepted_for_new_opposite_side_observation():
    path = three_region_path()
    graph = path["graph"]
    graph.merge_regions(RegionMerge(
        "merge-alias-input", CONTEXT, 5,
        path["next_room"], path["start_room"], "synthetic_loop"))

    observed = graph.observe_portal(link_observation(
        "after-merge-from-old-id", 6, path["second_portal"],
        path["next_room"], PortalSide.B))

    assert observed.disposition is PortalLinkDisposition.MATCHED
    assert observed.current_region_id == path["start_room"]
    assert observed.opposite_region_id == path["hall"]
    assert len(graph.snapshot().regions) == 2


def test_traversal_after_loop_merge_uses_rewritten_connection():
    path = three_region_path()
    graph = path["graph"]
    graph.merge_regions(RegionMerge(
        "merge-before-return", CONTEXT, 5,
        path["next_room"], path["start_room"], "synthetic_loop"))

    returned = graph.record_traversal(traversal(
        "return-after-merge", path["second_portal"].portal_id, 6,
        TraversalDirection.B_TO_A, event_time_ns=300))

    assert returned.source_region_id == path["start_room"]
    assert returned.target_region_id == path["hall"]
    assert returned.current_region_id == path["hall"]
    assert graph.region(path["hall"]).entry_count == 2


def test_merge_is_idempotent_and_conflicting_id_reuse_fails_closed():
    path = three_region_path()
    graph = path["graph"]
    merge = RegionMerge(
        "stable-merge", CONTEXT, 5,
        path["next_room"], path["start_room"], "synthetic_loop")

    accepted = graph.merge_regions(merge)
    replay = graph.merge_regions(merge)

    assert not accepted.duplicate
    assert replay.duplicate
    assert replay.canonical_region_id == accepted.canonical_region_id
    assert len(graph.snapshot().regions) == 2
    with pytest.raises(RegionGraphConflictError):
        graph.merge_regions(replace(merge, reason="different_reason"))


def test_self_merge_and_already_aliased_merge_are_rejected():
    path = three_region_path()
    graph = path["graph"]
    with pytest.raises(RegionGraphConflictError):
        graph.merge_regions(RegionMerge(
            "self-merge", CONTEXT, 5,
            path["hall"], path["hall"], "invalid_self_merge"))

    graph.merge_regions(RegionMerge(
        "valid-merge", CONTEXT, 5,
        path["next_room"], path["start_room"], "synthetic_loop"))
    with pytest.raises(RegionGraphConflictError):
        graph.merge_regions(RegionMerge(
            "already-one", CONTEXT, 6,
            path["next_room"], path["start_room"], "duplicate_relation"))


def test_unknown_context_and_stale_merge_leave_graph_unchanged():
    path = three_region_path()
    graph = path["graph"]
    before = graph.snapshot()
    foreign = PortalMapContext("other-session", CONTEXT.map_id, "map")

    with pytest.raises(UnknownRegionError):
        graph.merge_regions(RegionMerge(
            "unknown", CONTEXT, 5,
            path["start_room"], "region_999999", "unknown_region"))
    with pytest.raises(RegionContextMismatchError):
        graph.merge_regions(RegionMerge(
            "foreign", foreign, 5,
            path["start_room"], path["hall"], "foreign_context"))
    with pytest.raises(StaleGraphUpdateError):
        graph.merge_regions(RegionMerge(
            "stale", CONTEXT, 3,
            path["start_room"], path["hall"], "stale_revision"))
    assert graph.snapshot() == before


def test_merge_capacity_fails_without_partial_rewrite():
    path = three_region_path(policy=RegionGraphPolicy(max_region_merges=1))
    graph = path["graph"]
    graph.merge_regions(RegionMerge(
        "first-merge", CONTEXT, 5,
        path["next_room"], path["start_room"], "synthetic_loop"))
    before = graph.snapshot()

    with pytest.raises(RegionGraphCapacityError):
        graph.merge_regions(RegionMerge(
            "over-limit", CONTEXT, 6,
            path["start_room"], path["hall"], "capacity_check"))
    assert graph.snapshot() == before


def test_merge_of_adjacent_regions_retains_internal_portal_without_new_entry():
    memory = PortalMemory(CONTEXT)
    portal = confirmed_portal(memory, "door", 1)
    graph, start_room = started_graph()
    link = graph.observe_portal(link_observation(
        "link", 2, portal, start_room, PortalSide.A))
    graph.merge_regions(RegionMerge(
        "merge-adjacent", CONTEXT, 3,
        start_room, link.opposite_region_id, "synthetic_open_area"))

    connection = graph.connection(portal.portal_id)
    crossing = graph.record_traversal(traversal(
        "internal-crossing", portal.portal_id, 3,
        TraversalDirection.A_TO_B))

    assert connection.internal
    assert connection.side_a_region_id == connection.side_b_region_id
    assert not crossing.entered
    assert crossing.source_region_id == crossing.target_region_id == start_room
    assert graph.current_region_id == start_room
    assert graph.snapshot().confirmed_entry_count == 0


def test_successive_merges_flatten_all_historical_aliases():
    path = three_region_path()
    graph = path["graph"]
    first = graph.merge_regions(RegionMerge(
        "merge-room-hall", CONTEXT, 5,
        path["next_room"], path["hall"], "synthetic_correction"))
    assert first.canonical_region_id == path["hall"]

    second = graph.merge_regions(RegionMerge(
        "merge-with-start", CONTEXT, 6,
        path["hall"], path["start_room"], "synthetic_open_area"))

    assert second.canonical_region_id == path["start_room"]
    assert graph.resolve_region_id(path["hall"]) == path["start_room"]
    assert graph.resolve_region_id(path["next_room"]) == path["start_room"]
    assert graph.snapshot().region_aliases == (
        (path["hall"], path["start_room"]),
        (path["next_room"], path["start_room"]),
    )
    assert graph.region(path["start_room"]).alias_ids == (
        path["hall"], path["next_room"])


@pytest.mark.parametrize(
    "factory",
    [
        lambda: RegionGraphPolicy(max_region_merges=0),
        lambda: RegionMerge(
            "bad id", CONTEXT, 1,
            "region_000001", "region_000002", "reason"),
        lambda: RegionMerge(
            "valid", CONTEXT, True,
            "region_000001", "region_000002", "reason"),
        lambda: RegionMerge(
            "valid", CONTEXT, 1,
            "region_000001", "region_000002", " "),
    ],
)
def test_invalid_merge_policy_and_fields_are_rejected(factory):
    with pytest.raises(RegionGraphError):
        factory()
