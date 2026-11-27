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
    RegionExplorationState,
    RegionExplorationUpdate,
    RegionGraph,
    RegionGraphCapacityError,
    RegionGraphConflictError,
    RegionGraphError,
    RegionGraphPolicy,
    RegionMerge,
    RegionPortalEnd,
    RegionSeed,
    RegionSplit,
    RegionSplitTarget,
    RegionTaskKind,
    RegionTaskState,
    RegionTaskUpdate,
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


def task_update(
        update_id, task_id, revision, region_id, kind, subject_id, state,
        *, context=CONTEXT):
    return RegionTaskUpdate(
        update_id=update_id,
        task_id=task_id,
        context=context,
        map_revision=revision,
        region_id=region_id,
        kind=kind,
        subject_id=subject_id,
        state=state,
    )


def exploration_update(
        update_id, revision, region_id, state,
        *, reason="synthetic_progress", context=CONTEXT):
    return RegionExplorationUpdate(
        update_id=update_id,
        context=context,
        map_revision=revision,
        region_id=region_id,
        state=state,
        reason=reason,
    )


def region_split(
        split_id, revision, source_region_id,
        retained_portal_ends, created_portal_ends,
        retained_task_ids, created_task_ids, state_target,
        *, context=CONTEXT, reason="synthetic_partition"):
    return RegionSplit(
        split_id=split_id,
        context=context,
        map_revision=revision,
        source_region_id=source_region_id,
        retained_portal_ends=tuple(retained_portal_ends),
        created_portal_ends=tuple(created_portal_ends),
        retained_task_ids=tuple(retained_task_ids),
        created_task_ids=tuple(created_task_ids),
        state_target=state_target,
        reason=reason,
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


def test_complete_source_revision_advances_without_graph_mutation():
    graph, start_region = started_graph()

    assert graph.observe_revision(CONTEXT, 3) is True
    assert graph.observe_revision(CONTEXT, 3) is False

    snapshot = graph.snapshot()
    assert snapshot.latest_revision == 3
    assert snapshot.regions[0].region_id == start_region
    assert snapshot.regions[0].last_revision == 0
    assert snapshot.tasks == ()
    with pytest.raises(StaleGraphUpdateError):
        graph.observe_revision(CONTEXT, 2)
    with pytest.raises(RegionContextMismatchError):
        graph.observe_revision(replace(CONTEXT, map_id="other-map"), 4)


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


def test_region_exploration_progress_is_separate_and_ordered():
    graph, region_id = started_graph()
    initial = graph.region(region_id)

    in_progress = graph.update_region_exploration(exploration_update(
        "progress", 1, region_id, RegionExplorationState.IN_PROGRESS,
        reason="frontier_work_started"))
    complete_candidate = graph.update_region_exploration(exploration_update(
        "candidate", 2, region_id,
        RegionExplorationState.COMPLETE_CANDIDATE,
        reason="no_open_tasks_in_current_snapshot"))

    assert initial.seen and initial.entered
    assert initial.exploration_state is RegionExplorationState.UNASSESSED
    assert initial.exploration_reason is None
    assert initial.exploration_revision is None
    assert in_progress.state_changed
    assert in_progress.region.exploration_state is (
        RegionExplorationState.IN_PROGRESS)
    assert complete_candidate.state_changed
    assert complete_candidate.region.exploration_state is (
        RegionExplorationState.COMPLETE_CANDIDATE)
    assert complete_candidate.region.exploration_revision == 2
    assert graph.current_region_id == region_id


def test_region_exploration_cannot_skip_or_reopen_candidate():
    graph, region_id = started_graph()
    with pytest.raises(RegionGraphConflictError):
        graph.update_region_exploration(exploration_update(
            "skip", 1, region_id,
            RegionExplorationState.COMPLETE_CANDIDATE))

    graph.update_region_exploration(exploration_update(
        "progress", 1, region_id, RegionExplorationState.IN_PROGRESS))
    graph.update_region_exploration(exploration_update(
        "candidate", 2, region_id,
        RegionExplorationState.COMPLETE_CANDIDATE))
    before = graph.region(region_id)
    with pytest.raises(RegionGraphConflictError):
        graph.update_region_exploration(exploration_update(
            "reopen", 3, region_id, RegionExplorationState.IN_PROGRESS))

    assert graph.region(region_id) == before


def test_region_exploration_replay_is_idempotent_after_merge():
    path = three_region_path()
    update = exploration_update(
        "stable-progress", 4, path["next_room"],
        RegionExplorationState.IN_PROGRESS)
    path["graph"].update_region_exploration(update)
    merged = path["graph"].merge_regions(RegionMerge(
        "merge-progress", CONTEXT, 5,
        path["start_room"], path["next_room"], "synthetic_loop"))

    replay = path["graph"].update_region_exploration(update)

    assert replay.duplicate
    assert replay.region.region_id == merged.canonical_region_id
    assert replay.region.exploration_state is (
        RegionExplorationState.UNASSESSED)
    assert replay.region.exploration_reason == "region_merge_conservative"
    assert replay.region.exploration_revision == 5


def test_region_split_requires_reassessment_of_both_results():
    path = split_ready_path()
    graph = path["graph"]
    graph.update_region_exploration(exploration_update(
        "progress", 5, path["start_room"],
        RegionExplorationState.IN_PROGRESS))
    graph.update_region_exploration(exploration_update(
        "candidate", 6, path["start_room"],
        RegionExplorationState.COMPLETE_CANDIDATE))

    result = graph.split_region(path["split"])

    for region_id in (
            result.retained_region_id, result.created_region_id):
        region = graph.region(region_id)
        assert region.exploration_state is RegionExplorationState.UNASSESSED
        assert region.exploration_reason == (
            "region_split_requires_reassessment")
        assert region.exploration_revision == 6


def test_region_exploration_update_capacity_is_atomic():
    graph, region_id = started_graph(policy=RegionGraphPolicy(
        max_region_exploration_updates=1))
    graph.update_region_exploration(exploration_update(
        "first", 1, region_id, RegionExplorationState.IN_PROGRESS))
    before = graph.region(region_id)

    with pytest.raises(RegionGraphCapacityError):
        graph.update_region_exploration(exploration_update(
            "over-capacity", 2, region_id,
            RegionExplorationState.COMPLETE_CANDIDATE))

    assert graph.region(region_id) == before


def test_region_exploration_identity_context_and_revision_fail_closed():
    graph, region_id = started_graph()
    original = exploration_update(
        "stable-update", 1, region_id,
        RegionExplorationState.IN_PROGRESS)
    graph.update_region_exploration(original)
    before = graph.snapshot()

    with pytest.raises(RegionGraphConflictError):
        graph.update_region_exploration(replace(
            original, reason="conflicting_reason"))
    with pytest.raises(RegionContextMismatchError):
        graph.update_region_exploration(exploration_update(
            "foreign", 2, region_id,
            RegionExplorationState.IN_PROGRESS,
            context=PortalMapContext("other", CONTEXT.map_id, "map")))
    with pytest.raises(StaleGraphUpdateError):
        graph.update_region_exploration(exploration_update(
            "stale", 0, region_id,
            RegionExplorationState.IN_PROGRESS))
    with pytest.raises(UnknownRegionError):
        graph.update_region_exploration(exploration_update(
            "unknown", 2, "region_999999",
            RegionExplorationState.IN_PROGRESS))

    assert graph.snapshot() == before


@pytest.mark.parametrize("factory", [
    lambda: RegionGraphPolicy(max_region_exploration_updates=0),
    lambda: RegionExplorationUpdate(
        "bad id", CONTEXT, 1, "region_000001",
        RegionExplorationState.IN_PROGRESS, "reason"),
    lambda: RegionExplorationUpdate(
        "update", CONTEXT, True, "region_000001",
        RegionExplorationState.IN_PROGRESS, "reason"),
    lambda: RegionExplorationUpdate(
        "update", CONTEXT, 1, "region_000001", "in_progress", "reason"),
    lambda: RegionExplorationUpdate(
        "update", CONTEXT, 1, "region_000001",
        RegionExplorationState.IN_PROGRESS, " "),
])
def test_invalid_region_exploration_fields_are_rejected(factory):
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


def test_task_kinds_are_passive_stable_references_in_deterministic_order():
    graph, region_id = started_graph()
    graph.update_task(task_update(
        "update-frontier", "task-frontier", 1, region_id,
        RegionTaskKind.FRONTIER, "frontier-17", RegionTaskState.OPEN))
    graph.update_task(task_update(
        "update-portal", "task-portal", 2, region_id,
        RegionTaskKind.PORTAL, "portal_000001", RegionTaskState.OPEN))
    graph.update_task(task_update(
        "update-observation", "task-observation", 3, region_id,
        RegionTaskKind.OBSERVATION, "observation-9", RegionTaskState.OPEN))

    tasks = graph.tasks()

    assert tuple(task.task_id for task in tasks) == (
        "task-frontier", "task-observation", "task-portal")
    assert all(task.region_id == region_id for task in tasks)
    assert graph.region(region_id).task_ids == (
        "task-frontier", "task-observation", "task-portal")
    assert graph.snapshot().open_task_count == 3
    assert graph.snapshot().completed_task_count == 0


def test_open_task_can_complete_once_without_execution_side_effects():
    graph, region_id = started_graph()
    created = graph.update_task(task_update(
        "create", "task-1", 1, region_id,
        RegionTaskKind.FRONTIER, "frontier-1", RegionTaskState.OPEN))
    completed = graph.update_task(task_update(
        "complete", "task-1", 2, region_id,
        RegionTaskKind.FRONTIER, "frontier-1", RegionTaskState.COMPLETED))

    assert created.created
    assert not created.state_changed
    assert not completed.created
    assert completed.state_changed
    assert completed.task.state is RegionTaskState.COMPLETED
    assert completed.task.created_revision == 1
    assert completed.task.last_revision == 2
    assert graph.snapshot().open_task_count == 0
    assert graph.snapshot().completed_task_count == 1
    assert graph.current_region_id == region_id


def test_newer_same_state_update_preserves_identity_and_reports_no_change():
    graph, region_id = started_graph()
    graph.update_task(task_update(
        "create", "task-1", 1, region_id,
        RegionTaskKind.OBSERVATION, "observation-1", RegionTaskState.OPEN))

    refreshed = graph.update_task(task_update(
        "refresh", "task-1", 2, region_id,
        RegionTaskKind.OBSERVATION, "observation-1", RegionTaskState.OPEN))

    assert not refreshed.created
    assert not refreshed.state_changed
    assert refreshed.task.task_id == "task-1"
    assert refreshed.task.last_revision == 2
    assert len(graph.tasks()) == 1


def test_merge_preserves_open_and_completed_tasks_without_loss():
    path = three_region_path()
    graph = path["graph"]
    graph.update_task(task_update(
        "open-update", "open-task", 4, path["next_room"],
        RegionTaskKind.PORTAL, path["second_portal"].portal_id,
        RegionTaskState.OPEN))
    graph.update_task(task_update(
        "done-update", "done-task", 4, path["start_room"],
        RegionTaskKind.FRONTIER, "frontier-complete",
        RegionTaskState.COMPLETED))

    graph.merge_regions(RegionMerge(
        "merge-with-tasks", CONTEXT, 5,
        path["next_room"], path["start_room"], "synthetic_loop"))

    assert tuple(task.task_id for task in graph.tasks()) == (
        "done-task", "open-task")
    assert all(
        task.region_id == path["start_room"] for task in graph.tasks())
    assert graph.region(path["start_room"]).task_ids == (
        "done-task", "open-task")
    assert graph.snapshot().open_task_count == 1
    assert graph.snapshot().completed_task_count == 1


def test_task_update_replay_after_merge_returns_current_canonical_region():
    path = three_region_path()
    graph = path["graph"]
    original = task_update(
        "stable-update", "task-1", 4, path["next_room"],
        RegionTaskKind.OBSERVATION, "observation-1", RegionTaskState.OPEN)
    graph.update_task(original)
    graph.merge_regions(RegionMerge(
        "merge-before-replay", CONTEXT, 5,
        path["next_room"], path["start_room"], "synthetic_loop"))
    before = graph.snapshot()

    replay = graph.update_task(original)

    assert replay.duplicate
    assert not replay.created
    assert not replay.state_changed
    assert replay.task.region_id == path["start_room"]
    assert graph.snapshot() == before


def test_historical_alias_can_complete_task_after_merge():
    path = three_region_path()
    graph = path["graph"]
    graph.update_task(task_update(
        "create-before-merge", "task-1", 4, path["next_room"],
        RegionTaskKind.PORTAL, path["second_portal"].portal_id,
        RegionTaskState.OPEN))
    graph.merge_regions(RegionMerge(
        "merge-before-complete", CONTEXT, 5,
        path["next_room"], path["start_room"], "synthetic_loop"))

    completed = graph.update_task(task_update(
        "complete-by-alias", "task-1", 6, path["next_room"],
        RegionTaskKind.PORTAL, path["second_portal"].portal_id,
        RegionTaskState.COMPLETED))

    assert completed.state_changed
    assert completed.task.region_id == path["start_room"]
    assert graph.tasks(path["next_room"]) == graph.tasks(path["start_room"])


@pytest.mark.parametrize(
    "field,value",
    [
        ("kind", RegionTaskKind.PORTAL),
        ("subject_id", "another-subject"),
    ],
)
def test_existing_task_identity_fields_cannot_change(field, value):
    graph, region_id = started_graph()
    graph.update_task(task_update(
        "create", "task-1", 1, region_id,
        RegionTaskKind.FRONTIER, "frontier-1", RegionTaskState.OPEN))
    changed = task_update(
        "changed", "task-1", 2, region_id,
        RegionTaskKind.FRONTIER, "frontier-1", RegionTaskState.OPEN)

    with pytest.raises(RegionGraphConflictError):
        graph.update_task(replace(changed, **{field: value}))
    assert len(graph.tasks()) == 1


def test_existing_task_cannot_move_to_unrelated_region():
    path = three_region_path()
    graph = path["graph"]
    graph.update_task(task_update(
        "create", "task-1", 4, path["start_room"],
        RegionTaskKind.FRONTIER, "frontier-1", RegionTaskState.OPEN))

    with pytest.raises(RegionGraphConflictError):
        graph.update_task(task_update(
            "move", "task-1", 5, path["hall"],
            RegionTaskKind.FRONTIER, "frontier-1", RegionTaskState.OPEN))
    assert graph.task("task-1").region_id == path["start_room"]


def test_completed_task_cannot_reopen_in_reference_only_scope():
    graph, region_id = started_graph()
    graph.update_task(task_update(
        "created-done", "task-1", 1, region_id,
        RegionTaskKind.FRONTIER, "frontier-1", RegionTaskState.COMPLETED))

    with pytest.raises(RegionGraphConflictError):
        graph.update_task(task_update(
            "reopen", "task-1", 2, region_id,
            RegionTaskKind.FRONTIER, "frontier-1", RegionTaskState.OPEN))
    assert graph.task("task-1").state is RegionTaskState.COMPLETED


def test_task_update_id_reuse_and_stale_revision_fail_closed():
    graph, region_id = started_graph()
    original = task_update(
        "fixed-update", "task-1", 2, region_id,
        RegionTaskKind.FRONTIER, "frontier-1", RegionTaskState.OPEN)
    graph.update_task(original)

    with pytest.raises(RegionGraphConflictError):
        graph.update_task(replace(original, subject_id="frontier-2"))
    with pytest.raises(StaleGraphUpdateError):
        graph.update_task(task_update(
            "same-revision", "task-1", 2, region_id,
            RegionTaskKind.FRONTIER, "frontier-1", RegionTaskState.COMPLETED))
    assert graph.task("task-1").state is RegionTaskState.OPEN


def test_task_context_and_unknown_region_fail_closed():
    graph, region_id = started_graph()
    foreign = PortalMapContext("other-session", CONTEXT.map_id, "map")

    with pytest.raises(RegionContextMismatchError):
        graph.update_task(task_update(
            "foreign", "task-1", 1, region_id,
            RegionTaskKind.FRONTIER, "frontier-1", RegionTaskState.OPEN,
            context=foreign))
    with pytest.raises(UnknownRegionError):
        graph.update_task(task_update(
            "unknown-region", "task-1", 1, "region_999999",
            RegionTaskKind.FRONTIER, "frontier-1", RegionTaskState.OPEN))
    assert graph.tasks() == ()


def test_task_and_update_capacities_are_independent_and_atomic():
    task_limited, region_id = started_graph(policy=RegionGraphPolicy(
        max_tasks=1))
    task_limited.update_task(task_update(
        "first-update", "task-1", 1, region_id,
        RegionTaskKind.FRONTIER, "frontier-1", RegionTaskState.OPEN))
    with pytest.raises(RegionGraphCapacityError):
        task_limited.update_task(task_update(
            "second-update", "task-2", 2, region_id,
            RegionTaskKind.PORTAL, "portal_000001", RegionTaskState.OPEN))
    assert tuple(task.task_id for task in task_limited.tasks()) == ("task-1",)

    update_limited, region_id = started_graph(policy=RegionGraphPolicy(
        max_task_updates=1))
    update_limited.update_task(task_update(
        "first-update", "task-1", 1, region_id,
        RegionTaskKind.FRONTIER, "frontier-1", RegionTaskState.OPEN))
    with pytest.raises(RegionGraphCapacityError):
        update_limited.update_task(task_update(
            "complete-update", "task-1", 2, region_id,
            RegionTaskKind.FRONTIER, "frontier-1",
            RegionTaskState.COMPLETED))
    assert update_limited.task("task-1").state is RegionTaskState.OPEN


def test_task_filters_do_not_change_inventory():
    graph, region_id = started_graph()
    graph.update_task(task_update(
        "frontier-update", "frontier-task", 1, region_id,
        RegionTaskKind.FRONTIER, "frontier-1", RegionTaskState.OPEN))
    graph.update_task(task_update(
        "portal-update", "portal-task", 2, region_id,
        RegionTaskKind.PORTAL, "portal_000001", RegionTaskState.COMPLETED))

    assert tuple(task.task_id for task in graph.tasks(
        kind=RegionTaskKind.FRONTIER)) == ("frontier-task",)
    assert tuple(task.task_id for task in graph.tasks(
        state=RegionTaskState.COMPLETED)) == ("portal-task",)
    assert len(graph.tasks()) == 2
    with pytest.raises(RegionGraphError):
        graph.tasks(kind="frontier")
    with pytest.raises(RegionGraphError):
        graph.tasks(state="open")


@pytest.mark.parametrize(
    "factory",
    [
        lambda: RegionGraphPolicy(max_tasks=0),
        lambda: RegionGraphPolicy(max_task_updates=0),
        lambda: RegionTaskUpdate(
            "bad id", "task-1", CONTEXT, 1, "region_000001",
            RegionTaskKind.FRONTIER, "frontier-1", RegionTaskState.OPEN),
        lambda: RegionTaskUpdate(
            "update", "task-1", CONTEXT, True, "region_000001",
            RegionTaskKind.FRONTIER, "frontier-1", RegionTaskState.OPEN),
        lambda: RegionTaskUpdate(
            "update", "task-1", CONTEXT, 1, "region_000001",
            "frontier", "frontier-1", RegionTaskState.OPEN),
        lambda: RegionTaskUpdate(
            "update", "task-1", CONTEXT, 1, "region_000001",
            RegionTaskKind.FRONTIER, "frontier-1", "open"),
    ],
)
def test_invalid_task_policy_and_fields_are_rejected(factory):
    with pytest.raises(RegionGraphError):
        factory()


def split_ready_path(*, policy=None):
    path = three_region_path(policy=policy)
    graph = path["graph"]
    graph.update_task(task_update(
        "task-retained-update", "task-retained", 4, path["start_room"],
        RegionTaskKind.FRONTIER, "frontier-retained", RegionTaskState.OPEN))
    graph.update_task(task_update(
        "task-created-update", "task-created", 4, path["next_room"],
        RegionTaskKind.PORTAL, path["second_portal"].portal_id,
        RegionTaskState.COMPLETED))
    graph.merge_regions(RegionMerge(
        "merge-before-split", CONTEXT, 5,
        path["next_room"], path["start_room"], "synthetic_loop"))
    path["split"] = region_split(
        "stable-split", 6, path["next_room"],
        (RegionPortalEnd(path["first_portal"].portal_id, PortalSide.A),),
        (RegionPortalEnd(path["second_portal"].portal_id, PortalSide.B),),
        ("task-retained",), ("task-created",),
        RegionSplitTarget.CREATED,
    )
    return path


def test_explicit_split_partitions_portal_ends_tasks_and_whole_state():
    path = split_ready_path()
    graph = path["graph"]
    before_entry_count = graph.snapshot().confirmed_entry_count

    result = graph.split_region(path["split"])

    retained = graph.region(result.retained_region_id)
    created = graph.region(result.created_region_id)
    first_connection = graph.connection(path["first_portal"].portal_id)
    second_connection = graph.connection(path["second_portal"].portal_id)
    assert result.retained_region_id == path["start_room"]
    assert result.created_region_id == "region_000004"
    assert result.state_region_id == result.created_region_id
    assert first_connection.side_a_region_id == result.retained_region_id
    assert second_connection.side_b_region_id == result.created_region_id
    assert retained.portal_ids == (path["first_portal"].portal_id,)
    assert created.portal_ids == (path["second_portal"].portal_id,)
    assert retained.task_ids == ("task-retained",)
    assert created.task_ids == ("task-created",)
    assert graph.task("task-retained").region_id == result.retained_region_id
    assert graph.task("task-created").region_id == result.created_region_id
    assert not retained.seen and not retained.entered
    assert retained.entry_count == 0
    assert created.seen and created.entered
    assert created.entry_count == 1
    assert graph.current_region_id == result.created_region_id
    assert graph.snapshot().confirmed_entry_count == before_entry_count


def test_split_of_noncurrent_region_keeps_current_and_retains_state():
    path = three_region_path()
    graph = path["graph"]
    split = region_split(
        "split-hall", 5, path["hall"],
        (RegionPortalEnd(path["first_portal"].portal_id, PortalSide.B),),
        (RegionPortalEnd(path["second_portal"].portal_id, PortalSide.A),),
        (), (), RegionSplitTarget.RETAINED,
    )

    result = graph.split_region(split)

    assert graph.current_region_id == path["next_room"]
    assert result.state_region_id == path["hall"]
    assert graph.region(path["hall"]).entered
    assert graph.region(path["hall"]).entry_count == 1
    assert not graph.region(result.created_region_id).entered
    assert graph.snapshot().confirmed_entry_count == 2


def test_split_replay_is_idempotent():
    path = split_ready_path()
    graph = path["graph"]
    accepted = graph.split_region(path["split"])
    before = graph.snapshot()
    reordered = replace(
        path["split"],
        retained_task_ids=tuple(reversed(path["split"].retained_task_ids)),
        created_task_ids=tuple(reversed(path["split"].created_task_ids)),
    )

    replay = graph.split_region(reordered)

    assert replay.duplicate
    assert replay.retained_region_id == accepted.retained_region_id
    assert replay.created_region_id == accepted.created_region_id
    assert graph.snapshot() == before
    with pytest.raises(RegionGraphConflictError):
        graph.split_region(replace(path["split"], reason="other_reason"))


def test_split_assignment_order_is_canonicalized():
    split = region_split(
        "ordered-split", 1, "region_000001",
        (
            RegionPortalEnd("portal-z", PortalSide.B),
            RegionPortalEnd("portal-a", PortalSide.A),
        ),
        (), ("task-z", "task-a"), (), RegionSplitTarget.RETAINED,
    )

    assert split.retained_portal_ends == (
        RegionPortalEnd("portal-a", PortalSide.A),
        RegionPortalEnd("portal-z", PortalSide.B),
    )
    assert split.retained_task_ids == ("task-a", "task-z")


def test_split_can_assign_both_ends_of_internal_portal_separately():
    memory = PortalMemory(CONTEXT)
    portal = confirmed_portal(memory, "internal-door", 1)
    graph, start_room = started_graph()
    link = graph.observe_portal(link_observation(
        "internal-link", 2, portal, start_room, PortalSide.A))
    graph.merge_regions(RegionMerge(
        "make-internal", CONTEXT, 3,
        start_room, link.opposite_region_id, "synthetic_open_area"))
    assert graph.connection(portal.portal_id).internal

    result = graph.split_region(region_split(
        "restore-boundary", 4, start_room,
        (RegionPortalEnd(portal.portal_id, PortalSide.A),),
        (RegionPortalEnd(portal.portal_id, PortalSide.B),),
        (), (), RegionSplitTarget.RETAINED,
    ))

    connection = graph.connection(portal.portal_id)
    assert not connection.internal
    assert connection.side_a_region_id == result.retained_region_id
    assert connection.side_b_region_id == result.created_region_id
    assert graph.region(result.retained_region_id).portal_ids == (
        portal.portal_id,)
    assert graph.region(result.created_region_id).portal_ids == (
        portal.portal_id,)


def test_historical_alias_stays_with_retained_region_after_split():
    path = split_ready_path()
    graph = path["graph"]

    result = graph.split_region(path["split"])

    assert graph.resolve_region_id(path["next_room"]) == result.retained_region_id
    assert path["next_room"] in graph.region(
        result.retained_region_id).alias_ids
    assert graph.resolve_region_id(result.created_region_id) == (
        result.created_region_id)


def test_portal_and_traversal_replays_follow_split_end_assignments():
    path = split_ready_path()
    graph = path["graph"]
    result = graph.split_region(path["split"])

    first_link = graph.observe_portal(path["first_link_input"])
    second_link = graph.observe_portal(path["second_link_input"])
    first_crossing = graph.record_traversal(path["first_event"])
    second_crossing = graph.record_traversal(path["second_event"])

    assert first_link.duplicate and second_link.duplicate
    assert first_link.current_region_id == result.retained_region_id
    assert first_link.opposite_region_id == path["hall"]
    assert second_link.current_region_id == path["hall"]
    assert second_link.opposite_region_id == result.created_region_id
    assert first_crossing.duplicate and second_crossing.duplicate
    assert first_crossing.source_region_id == result.retained_region_id
    assert first_crossing.target_region_id == path["hall"]
    assert second_crossing.source_region_id == path["hall"]
    assert second_crossing.target_region_id == result.created_region_id


def test_task_replay_follows_split_while_old_source_cannot_move_task():
    path = split_ready_path()
    graph = path["graph"]
    result = graph.split_region(path["split"])
    original = task_update(
        "task-created-update", "task-created", 4, path["next_room"],
        RegionTaskKind.PORTAL, path["second_portal"].portal_id,
        RegionTaskState.COMPLETED)

    replay = graph.update_task(original)

    assert replay.duplicate
    assert replay.task.region_id == result.created_region_id
    with pytest.raises(RegionGraphConflictError):
        graph.update_task(task_update(
            "wrong-region-update", "task-created", 7, path["next_room"],
            RegionTaskKind.PORTAL, path["second_portal"].portal_id,
            RegionTaskState.COMPLETED))


@pytest.mark.parametrize(
    "change",
    [
        {"retained_portal_ends": ()},
        {"created_portal_ends": ()},
        {"created_portal_ends": (
            RegionPortalEnd("portal_000001", PortalSide.A),)},
        {"retained_portal_ends": (
            RegionPortalEnd("portal_unknown", PortalSide.A),)},
        {"retained_task_ids": ()},
        {"created_task_ids": ()},
        {"created_task_ids": ("task-retained",)},
        {"retained_task_ids": ("task-unknown",)},
    ],
)
def test_incomplete_duplicate_or_unknown_split_assignments_are_atomic(change):
    path = split_ready_path()
    graph = path["graph"]
    before = graph.snapshot()

    with pytest.raises(RegionGraphConflictError):
        graph.split_region(replace(path["split"], **change))

    assert graph.snapshot() == before


def test_split_context_unknown_source_and_stale_revision_are_atomic():
    path = split_ready_path()
    graph = path["graph"]
    before = graph.snapshot()
    foreign = PortalMapContext("other-session", CONTEXT.map_id, "map")

    with pytest.raises(RegionContextMismatchError):
        graph.split_region(replace(path["split"], context=foreign))
    with pytest.raises(UnknownRegionError):
        graph.split_region(replace(
            path["split"], split_id="unknown-source",
            source_region_id="region_999999"))
    with pytest.raises(StaleGraphUpdateError):
        graph.split_region(replace(
            path["split"], split_id="stale-split", map_revision=4))
    assert graph.snapshot() == before


def test_split_region_and_history_capacities_fail_atomically():
    graph, region_id = started_graph(policy=RegionGraphPolicy(max_regions=1))
    capacity_split = region_split(
        "no-room", 1, region_id, (), (), (), (),
        RegionSplitTarget.RETAINED)
    before = graph.snapshot()
    with pytest.raises(RegionGraphCapacityError):
        graph.split_region(capacity_split)
    assert graph.snapshot() == before

    path = split_ready_path(policy=RegionGraphPolicy(max_region_splits=1))
    graph = path["graph"]
    accepted = graph.split_region(path["split"])
    before = graph.snapshot()
    with pytest.raises(RegionGraphCapacityError):
        graph.split_region(region_split(
            "over-history", 7, accepted.created_region_id,
            (RegionPortalEnd(path["second_portal"].portal_id, PortalSide.B),),
            (), (), ("task-created",), RegionSplitTarget.RETAINED))
    assert graph.snapshot() == before


def test_merge_after_split_restores_one_region_without_reference_loss():
    path = split_ready_path()
    graph = path["graph"]
    split_result = graph.split_region(path["split"])

    merge_result = graph.merge_regions(RegionMerge(
        "merge-after-split", CONTEXT, 7,
        split_result.retained_region_id, split_result.created_region_id,
        "synthetic_reconciliation"))
    replay = graph.split_region(path["split"])

    assert merge_result.canonical_region_id == path["start_room"]
    assert graph.region(path["start_room"]).task_ids == (
        "task-created", "task-retained")
    assert graph.region(path["start_room"]).portal_ids == (
        path["first_portal"].portal_id, path["second_portal"].portal_id)
    assert replay.duplicate
    assert replay.retained_region_id == replay.created_region_id
    assert replay.state_region_id == path["start_room"]


@pytest.mark.parametrize(
    "factory",
    [
        lambda: RegionGraphPolicy(max_region_splits=0),
        lambda: RegionPortalEnd("bad id", PortalSide.A),
        lambda: RegionPortalEnd("portal_000001", "A"),
        lambda: RegionSplit(
            "split", CONTEXT, 1, "region_000001", [], (), (), (),
            RegionSplitTarget.RETAINED, "reason"),
        lambda: RegionSplit(
            "split", CONTEXT, 1, "region_000001",
            (RegionPortalEnd("portal_000001", PortalSide.A),) * 2,
            (), (), (), RegionSplitTarget.RETAINED, "reason"),
        lambda: RegionSplit(
            "split", CONTEXT, 1, "region_000001", (), (),
            ("task-1", "task-1"), (), RegionSplitTarget.RETAINED, "reason"),
        lambda: RegionSplit(
            "split", CONTEXT, 1, "region_000001", (), (), (), (),
            "retained", "reason"),
        lambda: RegionSplit(
            "split", CONTEXT, True, "region_000001", (), (), (), (),
            RegionSplitTarget.RETAINED, "reason"),
        lambda: RegionSplit(
            "split", CONTEXT, 1, "region_000001", (), (), (), (),
            RegionSplitTarget.RETAINED, " "),
    ],
)
def test_invalid_split_policy_and_fields_are_rejected(factory):
    with pytest.raises(RegionGraphError):
        factory()
