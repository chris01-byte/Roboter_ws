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
    PortalMemory,
    PortalMemoryError,
    PortalMemoryPolicy,
    PortalObservation,
    StaleObservationError,
)


CONTEXT = PortalMapContext(
    session_id="session-20260914",
    map_id="live-map-epoch-1",
    frame_id="map",
)


def observation(
        observation_id, revision, near=(0.0, 0.0), far=(1.0, 0.0),
        *, context=CONTEXT, uncertainty=0.0):
    return PortalObservation(
        observation_id=observation_id,
        context=context,
        map_revision=revision,
        near_side=Point2D(*near),
        far_side=Point2D(*far),
        uncertainty_m=uncertainty,
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
    assert 0 < policy.max_observations < 100_000
