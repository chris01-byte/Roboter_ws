import math
from pathlib import Path
import sys

import pytest


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE_ROOT))

from explore.portal_memory import (  # noqa: E402
    ContextMismatchError,
    MemoryCapacityError,
    ObservationConflictError,
    ObservationDisposition,
    Point2D,
    PortalMapContext,
    PortalConfirmationState,
    PortalMemory,
    PortalMemoryError,
    PortalMemoryPolicy,
    PortalObservation,
    PortalObservationInventory,
    PortalSide,
    PortalStructuralEvidence,
    ReachabilityConflictError,
    ReachabilityState,
    ReachabilityUpdate,
    StaleObservationError,
    TraversalConflictError,
    TraversalDirection,
    TraversalEvent,
    UnknownPortalError,
)


CONTEXT = PortalMapContext(
    session_id="session-20260914",
    map_id="live-map-epoch-1",
    frame_id="map",
)


def observation(
        observation_id, revision, near=(0.0, 0.0), far=(1.0, 0.0),
        *, context=CONTEXT, uncertainty=0.0,
        evidence=PortalStructuralEvidence.QUALIFIED):
    return PortalObservation(
        observation_id=observation_id,
        context=context,
        map_revision=revision,
        near_side=Point2D(*near),
        far_side=Point2D(*far),
        uncertainty_m=uncertainty,
        structural_evidence=evidence,
    )


def memory_with_portal(*, policy=None, revision=1):
    memory = PortalMemory(CONTEXT, policy)
    portal_id = memory.observe(observation("portal-source", revision)).portal_id
    return memory, portal_id


def traversal(
        event_id, portal_id, revision=1, *, event_time_ns=100,
        direction=TraversalDirection.A_TO_B, confirmed=True,
        context=CONTEXT):
    return TraversalEvent(
        event_id=event_id,
        portal_id=portal_id,
        context=context,
        map_revision=revision,
        event_time_ns=event_time_ns,
        direction=direction,
        crossing_confirmed=confirmed,
    )


def reachability(
        update_id, portal_id, revision, observed_at_ns, state, *,
        side=PortalSide.A, reason="synthetic_check",
        recheck_condition="on_fresh_map", context=CONTEXT):
    return ReachabilityUpdate(
        update_id=update_id,
        portal_id=portal_id,
        side=side,
        context=context,
        map_revision=revision,
        observed_at_ns=observed_at_ns,
        state=state,
        reason=reason,
        recheck_condition=recheck_condition,
    )


def test_same_portal_from_opposite_side_keeps_id_and_swaps_approach_side():
    memory = PortalMemory(CONTEXT)

    first = memory.observe(observation("obs-1", 1))
    reverse = memory.observe(observation(
        "obs-2", 2, near=(1.02, 0.01), far=(0.01, -0.01)))

    assert first.disposition is ObservationDisposition.CREATED
    assert reverse.disposition is ObservationDisposition.MATCHED
    assert reverse.portal_id == first.portal_id
    assert first.approach_side == "A"
    assert reverse.approach_side == "B"
    snapshot = memory.snapshot(first.portal_id)
    assert snapshot.evidence_count == 2
    assert snapshot.observation_count == 2
    assert snapshot.confirmed


def test_duplicate_observation_is_idempotent_and_conflicting_reuse_fails():
    memory = PortalMemory(CONTEXT)
    original = observation("stable-observation", 4)

    accepted = memory.observe(original)
    replay = memory.observe(original)

    assert replay.portal_id == accepted.portal_id
    assert replay.duplicate
    assert not replay.evidence_added
    assert memory.snapshot(accepted.portal_id).observation_count == 1
    with pytest.raises(ObservationConflictError):
        memory.observe(observation(
            "stable-observation", 4, near=(0.02, 0.0), far=(1.02, 0.0)))


def test_same_map_revision_does_not_count_as_independent_evidence():
    memory = PortalMemory(CONTEXT)
    created = memory.observe(observation("obs-a", 7))

    repeated_map = memory.observe(observation(
        "obs-b", 7, near=(0.01, 0.0), far=(1.01, 0.0)))

    assert repeated_map.portal_id == created.portal_id
    assert not repeated_map.evidence_added
    snapshot = memory.snapshot(created.portal_id)
    assert snapshot.observation_count == 2
    assert snapshot.evidence_count == 1
    assert not snapshot.confirmed


def test_small_metric_geometry_change_matches_within_synthetic_policy():
    policy = PortalMemoryPolicy(
        max_endpoint_distance_m=0.12,
        max_midpoint_distance_m=0.08,
    )
    memory = PortalMemory(CONTEXT, policy)
    created = memory.observe(observation("growth-1", 1))

    changed = memory.observe(observation(
        "growth-2", 2, near=(0.05, 0.02), far=(1.06, 0.01)))

    assert changed.portal_id == created.portal_id
    assert len(memory.snapshots()) == 1


def test_two_nearby_parallel_doors_remain_separate():
    policy = PortalMemoryPolicy(
        max_endpoint_distance_m=0.16,
        max_midpoint_distance_m=0.16,
        ambiguity_margin_m=0.01,
    )
    memory = PortalMemory(CONTEXT, policy)

    first = memory.observe(observation("door-1", 1))
    second = memory.observe(observation(
        "door-2", 2, near=(0.0, 0.24), far=(1.0, 0.24)))

    assert first.portal_id != second.portal_id
    assert len(memory.snapshots()) == 2


def test_equidistant_observation_is_ambiguous_and_changes_no_portal():
    policy = PortalMemoryPolicy(
        max_endpoint_distance_m=0.16,
        max_midpoint_distance_m=0.16,
        ambiguity_margin_m=0.01,
    )
    memory = PortalMemory(CONTEXT, policy)
    first = memory.observe(observation("door-1", 1))
    second = memory.observe(observation(
        "door-2", 2, near=(0.0, 0.24), far=(1.0, 0.24)))
    before = memory.snapshots()

    ambiguous = memory.observe(observation(
        "between", 3, near=(0.0, 0.12), far=(1.0, 0.12)))

    assert ambiguous.disposition is ObservationDisposition.AMBIGUOUS
    assert ambiguous.portal_id is None
    assert ambiguous.approach_side is None
    assert ambiguous.candidate_ids == (first.portal_id, second.portal_id)
    assert memory.snapshots() == before


@pytest.mark.parametrize(
    "other_context",
    [
        PortalMapContext("another-session", CONTEXT.map_id, CONTEXT.frame_id),
        PortalMapContext(CONTEXT.session_id, "another-map", CONTEXT.frame_id),
        PortalMapContext(CONTEXT.session_id, CONTEXT.map_id, "map-corrected"),
    ],
)
def test_session_map_and_frame_mismatches_fail_closed(other_context):
    memory = PortalMemory(CONTEXT)

    with pytest.raises(ContextMismatchError):
        memory.observe(observation("foreign", 1, context=other_context))
    assert memory.snapshots() == ()
    assert memory.latest_revision is None


def test_unseen_stale_revision_is_rejected_but_known_replay_stays_idempotent():
    memory = PortalMemory(CONTEXT)
    first_observation = observation("first", 3)
    memory.observe(first_observation)
    memory.observe(observation("newer", 5, near=(0.01, 0.0), far=(1.01, 0.0)))

    assert memory.observe(first_observation).duplicate
    with pytest.raises(StaleObservationError):
        memory.observe(observation("late-new-id", 4))


@pytest.mark.parametrize(
    "near,far,uncertainty",
    [
        ((math.nan, 0.0), (1.0, 0.0), 0.0),
        ((0.0, 0.0), (math.inf, 0.0), 0.0),
        ((0.0, 0.0), (0.0, 0.0), 0.0),
        ((0.0, 0.0), (1.0, 0.0), math.nan),
        ((0.0, 0.0), (1.0, 0.0), -0.01),
    ],
)
def test_invalid_geometry_and_uncertainty_are_rejected(near, far, uncertainty):
    with pytest.raises(PortalMemoryError):
        observation("invalid", 1, near=near, far=far, uncertainty=uncertainty)


def test_uncertainty_has_a_hard_bound():
    memory = PortalMemory(
        CONTEXT, PortalMemoryPolicy(maximum_uncertainty_m=0.05))

    with pytest.raises(PortalMemoryError):
        memory.observe(observation("too-uncertain", 1, uncertainty=0.051))


def test_portal_and_observation_capacities_fail_without_eviction():
    portal_limited = PortalMemory(
        CONTEXT,
        PortalMemoryPolicy(
            max_endpoint_distance_m=0.10,
            max_midpoint_distance_m=0.10,
            max_portals=1,
        ),
    )
    portal_limited.observe(observation("first-door", 1))
    with pytest.raises(MemoryCapacityError):
        portal_limited.observe(observation(
            "second-door", 2, near=(0.0, 1.0), far=(1.0, 1.0)))
    assert len(portal_limited.snapshots()) == 1

    observation_limited = PortalMemory(
        CONTEXT, PortalMemoryPolicy(max_observations=1))
    original = observation("only-observation", 1)
    result = observation_limited.observe(original)
    assert observation_limited.observe(original).duplicate
    with pytest.raises(MemoryCapacityError):
        observation_limited.observe(observation(
            "one-too-many", 2, near=(0.01, 0.0), far=(1.01, 0.0)))
    assert observation_limited.snapshot(result.portal_id).observation_count == 1


def test_grid_origin_and_resolution_are_accepted_only_after_metric_normalization():
    def metric_point(origin, resolution, cell):
        return (
            origin[0] + resolution * cell[0],
            origin[1] + resolution * cell[1],
        )

    memory = PortalMemory(
        CONTEXT,
        PortalMemoryPolicy(
            max_endpoint_distance_m=0.10,
            max_midpoint_distance_m=0.10,
        ),
    )
    first = memory.observe(observation(
        "grid-a", 1,
        near=metric_point((0.0, 0.0), 0.10, (10, 10)),
        far=metric_point((0.0, 0.0), 0.10, (20, 10)),
    ))
    equivalent = memory.observe(observation(
        "grid-b", 2,
        near=metric_point((-1.0, -1.0), 0.05, (40, 40)),
        far=metric_point((-1.0, -1.0), 0.05, (60, 40)),
    ))
    shifted = memory.observe(observation(
        "grid-c", 3,
        near=metric_point((-0.5, -1.0), 0.05, (40, 40)),
        far=metric_point((-0.5, -1.0), 0.05, (60, 40)),
    ))

    assert equivalent.portal_id == first.portal_id
    assert shifted.portal_id != first.portal_id
    assert len(memory.snapshots()) == 2


def test_axis_rotation_beyond_policy_does_not_reuse_identity():
    memory = PortalMemory(
        CONTEXT,
        PortalMemoryPolicy(max_axis_angle_rad=math.radians(10.0)),
    )
    first = memory.observe(observation("horizontal", 1))
    rotated = memory.observe(observation(
        "diagonal", 2,
        near=(0.5 - math.sqrt(0.5) / 2.0, -math.sqrt(0.5) / 2.0),
        far=(0.5 + math.sqrt(0.5) / 2.0, math.sqrt(0.5) / 2.0),
    ))

    assert rotated.portal_id != first.portal_id


def test_default_policy_is_explicitly_bounded_and_ids_are_deterministic():
    policy = PortalMemoryPolicy()
    memory = PortalMemory(CONTEXT, policy)

    first = memory.observe(observation("one", 1))
    second = memory.observe(observation(
        "two", 2, near=(0.0, 1.0), far=(1.0, 1.0)))

    assert first.portal_id == "portal_000001"
    assert second.portal_id == "portal_000002"
    assert 0 < policy.max_portals < 10_000
    assert 0 < policy.max_inventory_observations < 10_000
    assert 0 < policy.max_observations < 100_000


def test_portal_inventory_requires_one_context_revision_and_unique_ids():
    first = observation("inventory-a", 3)
    foreign = observation(
        "inventory-b", 3,
        context=PortalMapContext("other", "map", "map"))

    with pytest.raises(PortalMemoryError, match="Kontext und Revision"):
        PortalObservationInventory(
            "portal-inventory-" + "a" * 64,
            CONTEXT,
            3,
            (first, foreign),
        )
    with pytest.raises(PortalMemoryError, match="doppelte"):
        PortalObservationInventory(
            "portal-inventory-" + "a" * 64,
            CONTEXT,
            3,
            (first, first),
        )


def test_repeated_furniture_bottleneck_evidence_never_confirms_a_portal():
    memory = PortalMemory(CONTEXT)
    created = memory.observe(observation(
        "furniture-1", 1,
        evidence=PortalStructuralEvidence.INSUFFICIENT))
    memory.observe(observation(
        "furniture-2", 2, near=(0.01, 0.0), far=(1.01, 0.0),
        evidence=PortalStructuralEvidence.INSUFFICIENT))
    memory.observe(observation(
        "furniture-3", 3, near=(-0.01, 0.0), far=(0.99, 0.0),
        evidence=PortalStructuralEvidence.INSUFFICIENT))

    snapshot = memory.snapshot(created.portal_id)
    assert snapshot.evidence_count == 3
    assert snapshot.qualified_evidence_count == 0
    assert snapshot.confirmation_state is PortalConfirmationState.CANDIDATE
    assert not snapshot.confirmed


def test_missing_structural_evidence_defaults_fail_closed_to_candidate():
    memory = PortalMemory(CONTEXT)
    raw_observation = PortalObservation(
        observation_id="no-structural-verdict",
        context=CONTEXT,
        map_revision=1,
        near_side=Point2D(0.0, 0.0),
        far_side=Point2D(1.0, 0.0),
    )

    result = memory.observe(raw_observation)
    snapshot = memory.snapshot(result.portal_id)

    assert not result.qualified_evidence_added
    assert snapshot.confirmation_state is PortalConfirmationState.CANDIDATE
    assert not snapshot.confirmed


def test_contradictory_evidence_marks_uncertain_until_newer_qualification():
    memory = PortalMemory(CONTEXT)
    created = memory.observe(observation("qualified-1", 1))
    memory.observe(observation("qualified-2", 2))
    assert memory.snapshot(created.portal_id).confirmed

    contradiction = memory.observe(observation(
        "contradiction", 3,
        evidence=PortalStructuralEvidence.CONTRADICTORY))
    uncertain = memory.snapshot(created.portal_id)

    assert contradiction.evidence_added
    assert not contradiction.qualified_evidence_added
    assert uncertain.confirmation_state is PortalConfirmationState.UNCERTAIN
    assert not uncertain.confirmed

    memory.observe(observation(
        "missing-after-conflict", 4,
        evidence=PortalStructuralEvidence.INSUFFICIENT))
    assert memory.snapshot(
        created.portal_id).confirmation_state is PortalConfirmationState.UNCERTAIN

    recovered = memory.observe(observation("qualified-again", 5))
    assert recovered.qualified_evidence_added
    assert memory.snapshot(
        created.portal_id).confirmation_state is PortalConfirmationState.CONFIRMED


def test_qualified_repeats_of_one_revision_count_only_once():
    memory = PortalMemory(CONTEXT)
    created = memory.observe(observation("same-revision-1", 7))
    repeated = memory.observe(observation(
        "same-revision-2", 7, near=(0.01, 0.0), far=(1.01, 0.0)))

    snapshot = memory.snapshot(created.portal_id)

    assert not repeated.evidence_added
    assert not repeated.qualified_evidence_added
    assert snapshot.evidence_count == 1
    assert snapshot.qualified_evidence_count == 1
    assert snapshot.confirmation_state is PortalConfirmationState.CANDIDATE


def test_lost_structural_visibility_preserves_confirmed_identity():
    memory = PortalMemory(CONTEXT)
    created = memory.observe(observation("visible-1", 1))
    memory.observe(observation("visible-2", 2))
    before = memory.snapshot(created.portal_id)

    lost = memory.observe(observation(
        "not-visible-enough", 3, near=(0.02, 0.0), far=(1.02, 0.0),
        evidence=PortalStructuralEvidence.INSUFFICIENT))
    after = memory.snapshot(created.portal_id)

    assert before.confirmed
    assert lost.portal_id == created.portal_id
    assert not lost.qualified_evidence_added
    assert after.portal_id == before.portal_id
    assert after.confirmation_state is PortalConfirmationState.CONFIRMED


def test_room_centroid_motion_is_not_part_of_portal_identity_input():
    memory = PortalMemory(CONTEXT)
    synthetic_room_centroid_before = (2.0, 1.0)
    synthetic_room_centroid_after = (3.5, -0.5)

    first = memory.observe(observation("centroid-independent-1", 1))
    second = memory.observe(observation(
        "centroid-independent-2", 2,
        near=(0.03, 0.01), far=(1.03, -0.01)))

    assert synthetic_room_centroid_before != synthetic_room_centroid_after
    assert second.portal_id == first.portal_id
    assert memory.snapshot(first.portal_id).confirmed


def test_detected_portals_observations_and_crossings_remain_separate_counts():
    memory = PortalMemory(CONTEXT)
    first = memory.observe(observation("door-a-1", 1))
    memory.observe(observation("door-a-2", 2))
    second = memory.observe(observation(
        "door-b-1", 3, near=(0.0, 1.0), far=(1.0, 1.0)))
    memory.record_traversal(traversal(
        "only-crossing", first.portal_id, revision=3))

    snapshots = memory.snapshots()

    assert len(snapshots) == 2
    assert sum(item.observation_count for item in snapshots) == 3
    assert memory.confirmed_traversal_count() == 1
    assert memory.confirmed_traversal_count(second.portal_id) == 0


def test_invalid_structural_evidence_type_is_rejected():
    with pytest.raises(PortalMemoryError):
        observation("invalid-evidence", 1, evidence="qualified")


def test_confirmed_traversal_is_counted_exactly_once_on_replay():
    memory, portal_id = memory_with_portal()
    event = traversal("crossing-1", portal_id)

    accepted = memory.record_traversal(event)
    replay = memory.record_traversal(event)

    assert accepted.counted
    assert not accepted.duplicate
    assert replay.duplicate
    assert not replay.counted
    assert replay.portal_traversal_count == 1
    assert memory.confirmed_traversal_count(portal_id) == 1
    assert memory.snapshot(portal_id).confirmed_traversal_count == 1
    assert memory.traversal_events() == (event,)


def test_unconfirmed_event_stays_in_history_but_is_not_a_crossing():
    memory, portal_id = memory_with_portal()

    rejected = memory.record_traversal(traversal(
        "incomplete", portal_id, confirmed=False))
    confirmed = memory.record_traversal(traversal(
        "complete", portal_id, revision=2, event_time_ns=200))

    assert not rejected.counted
    assert not rejected.crossing_confirmed
    assert confirmed.counted
    assert memory.confirmed_traversal_count() == 1
    assert len(memory.traversal_events()) == 2
    assert memory.traversal_events(confirmed_only=True) == (
        traversal("complete", portal_id, revision=2, event_time_ns=200),)


def test_opposite_directions_are_distinct_events_for_the_same_portal():
    memory, portal_id = memory_with_portal()
    outward_event = traversal(
        "outward", portal_id, direction=TraversalDirection.A_TO_B)

    outward = memory.record_traversal(outward_event)
    returning = memory.record_traversal(traversal(
        "returning", portal_id, revision=2, event_time_ns=200,
        direction=TraversalDirection.B_TO_A))
    replay = memory.record_traversal(outward_event)

    assert outward.portal_id == returning.portal_id == portal_id
    assert outward.direction is TraversalDirection.A_TO_B
    assert returning.direction is TraversalDirection.B_TO_A
    assert replay.duplicate
    assert not replay.counted
    assert replay.portal_traversal_count == 2
    assert memory.confirmed_traversal_count(portal_id) == 2


def test_traversal_id_conflict_unknown_portal_and_context_fail_closed():
    memory, portal_id = memory_with_portal()
    original = traversal("fixed-event", portal_id)
    memory.record_traversal(original)

    with pytest.raises(TraversalConflictError):
        memory.record_traversal(traversal(
            "fixed-event", portal_id,
            direction=TraversalDirection.B_TO_A))
    with pytest.raises(UnknownPortalError):
        memory.record_traversal(traversal(
            "unknown", "portal_999999"))
    foreign = PortalMapContext("other-session", CONTEXT.map_id, "map")
    with pytest.raises(ContextMismatchError):
        memory.record_traversal(traversal(
            "foreign", portal_id, context=foreign))
    assert memory.confirmed_traversal_count(portal_id) == 1


def test_stale_new_traversal_is_rejected_but_known_replay_remains_valid():
    memory, portal_id = memory_with_portal(revision=3)
    accepted = traversal("at-current-revision", portal_id, revision=3)
    memory.record_traversal(accepted)
    memory.update_reachability(reachability(
        "newer-state", portal_id, 5, 500, ReachabilityState.OPEN))

    assert memory.record_traversal(accepted).duplicate
    with pytest.raises(StaleObservationError):
        memory.record_traversal(traversal(
            "late-event", portal_id, revision=4, event_time_ns=400))


@pytest.mark.parametrize(
    "overrides",
    [
        {"event_time_ns": -1},
        {"revision": True},
        {"direction": "a_to_b"},
        {"confirmed": 1},
    ],
)
def test_invalid_traversal_fields_are_rejected(overrides):
    _memory, portal_id = memory_with_portal()

    with pytest.raises(PortalMemoryError):
        traversal("invalid-event", portal_id, **overrides)


def test_unassessed_reachability_is_explicitly_unknown_on_both_sides():
    memory, portal_id = memory_with_portal()

    snapshots = memory.reachability_snapshots()

    assert len(snapshots) == 2
    assert {snapshot.side for snapshot in snapshots} == {
        PortalSide.A, PortalSide.B}
    assert all(snapshot.state is ReachabilityState.UNKNOWN
               for snapshot in snapshots)
    assert all(snapshot.update_id is None for snapshot in snapshots)


def test_lost_visibility_marks_unknown_without_deleting_portal_or_history():
    memory, portal_id = memory_with_portal()
    before = memory.snapshot(portal_id)

    result = memory.update_reachability(reachability(
        "lost-view", portal_id, 2, 200, ReachabilityState.UNKNOWN,
        reason="portal_not_currently_visible",
        recheck_condition="on_fresh_portal_observation"))

    assert result.snapshot.state is ReachabilityState.UNKNOWN
    assert memory.snapshot(portal_id).portal_id == before.portal_id
    assert memory.snapshot(portal_id).observation_count == before.observation_count
    assert len(memory.reachability_history(portal_id)) == 1


def test_temporarily_blocked_can_be_reopened_by_newer_external_check():
    memory, portal_id = memory_with_portal()
    blocked = reachability(
        "blocked", portal_id, 2, 200,
        ReachabilityState.TEMPORARILY_BLOCKED,
        reason="synthetic_obstacle",
        recheck_condition="after_costmap_change")
    reopened = reachability(
        "reopened", portal_id, 3, 300, ReachabilityState.OPEN,
        reason="fresh_external_path_check",
        recheck_condition="on_next_map_revision")

    memory.update_reachability(blocked)
    result = memory.update_reachability(reopened)

    assert result.snapshot.state is ReachabilityState.OPEN
    assert memory.reachability_history(portal_id) == (blocked, reopened)
    assert memory.confirmed_traversal_count(portal_id) == 0


def test_reachability_is_side_specific_and_does_not_forbid_return_history():
    memory, portal_id = memory_with_portal()
    memory.update_reachability(reachability(
        "excluded-a", portal_id, 2, 200, ReachabilityState.EXCLUDED,
        side=PortalSide.A, reason="outside_synthetic_scope",
        recheck_condition="on_scope_change"))
    memory.update_reachability(reachability(
        "open-b", portal_id, 2, 201, ReachabilityState.OPEN,
        side=PortalSide.B, reason="fresh_external_path_check",
        recheck_condition="on_next_map_revision"))

    crossing = memory.record_traversal(traversal(
        "observed-return", portal_id, revision=2, event_time_ns=300,
        direction=TraversalDirection.B_TO_A))

    assert memory.reachability_snapshot(
        portal_id, PortalSide.A).state is ReachabilityState.EXCLUDED
    assert memory.reachability_snapshot(
        portal_id, PortalSide.B).state is ReachabilityState.OPEN
    assert crossing.counted


def test_reachability_replay_is_idempotent_and_does_not_restore_old_state():
    memory, portal_id = memory_with_portal()
    old = reachability(
        "state-1", portal_id, 2, 200,
        ReachabilityState.TEMPORARILY_BLOCKED)
    new = reachability(
        "state-2", portal_id, 3, 300, ReachabilityState.OPEN)
    memory.update_reachability(old)
    memory.update_reachability(new)

    replay = memory.update_reachability(old)

    assert replay.duplicate
    assert replay.snapshot.update_id == "state-2"
    assert replay.snapshot.state is ReachabilityState.OPEN
    assert memory.reachability_history(portal_id) == (old, new)
    with pytest.raises(ReachabilityConflictError):
        memory.update_reachability(reachability(
            "state-1", portal_id, 2, 200, ReachabilityState.UNKNOWN))


def test_stale_or_nonadvancing_reachability_update_is_rejected():
    memory, portal_id = memory_with_portal(revision=3)
    current = reachability(
        "current", portal_id, 3, 300, ReachabilityState.OPEN)
    memory.update_reachability(current)

    with pytest.raises(StaleObservationError):
        memory.update_reachability(reachability(
            "old-revision", portal_id, 2, 400, ReachabilityState.UNKNOWN))
    with pytest.raises(StaleObservationError):
        memory.update_reachability(reachability(
            "same-instant", portal_id, 3, 300,
            ReachabilityState.TEMPORARILY_BLOCKED))
    assert memory.reachability_snapshot(
        portal_id, PortalSide.A).state is ReachabilityState.OPEN


def test_reachability_unknown_portal_and_context_fail_closed():
    memory, portal_id = memory_with_portal()
    foreign = PortalMapContext("other-session", CONTEXT.map_id, "map")

    with pytest.raises(UnknownPortalError):
        memory.update_reachability(reachability(
            "unknown-portal", "portal_999999", 1, 100,
            ReachabilityState.OPEN))
    with pytest.raises(ContextMismatchError):
        memory.update_reachability(reachability(
            "foreign", portal_id, 1, 100, ReachabilityState.OPEN,
            context=foreign))
    assert memory.reachability_history() == ()


@pytest.mark.parametrize(
    "overrides",
    [
        {"observed_at_ns": -1},
        {"revision": True},
        {"side": "A"},
        {"state": "open"},
        {"reason": ""},
        {"recheck_condition": " "},
    ],
)
def test_invalid_reachability_fields_are_rejected(overrides):
    _memory, portal_id = memory_with_portal()
    values = {
        "update_id": "invalid-state",
        "portal_id": portal_id,
        "revision": 1,
        "observed_at_ns": 100,
        "state": ReachabilityState.OPEN,
    }
    values.update(overrides)

    with pytest.raises(PortalMemoryError):
        reachability(**values)


def test_event_and_reachability_history_have_independent_hard_caps():
    event_memory, event_portal = memory_with_portal(policy=PortalMemoryPolicy(
        max_traversal_events=1))
    event_memory.record_traversal(traversal(
        "event-1", event_portal, confirmed=False))
    with pytest.raises(MemoryCapacityError):
        event_memory.record_traversal(traversal(
            "event-2", event_portal, event_time_ns=200, confirmed=False))

    state_memory, state_portal = memory_with_portal(policy=PortalMemoryPolicy(
        max_reachability_updates=1))
    state_memory.update_reachability(reachability(
        "state-1", state_portal, 1, 100, ReachabilityState.UNKNOWN))
    with pytest.raises(MemoryCapacityError):
        state_memory.update_reachability(reachability(
            "state-2", state_portal, 1, 200, ReachabilityState.OPEN))

    assert event_memory.confirmed_traversal_count(event_portal) == 0
    assert len(state_memory.reachability_history(state_portal)) == 1
