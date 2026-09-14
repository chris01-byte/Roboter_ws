import math
from pathlib import Path
import sys

import pytest


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE_ROOT))

from explore.portal_memory import (  # noqa: E402
    ObservationDisposition,
    PortalConfirmationState,
    PortalMapContext,
    PortalMemory,
    PortalStructuralEvidence,
)
from explore.portal_plan_adapter import (  # noqa: E402
    PortalPlanAdapterError,
    PortalPlanCandidate,
    normalize_portal_plan_candidate,
)


CONTEXT = PortalMapContext(
    session_id="session-20260914",
    map_id="live-map-epoch-1",
    frame_id="map",
)


def candidate(**changes):
    values = {
        "observation_id": "portal-plan-0001",
        "context": CONTEXT,
        "map_revision": 12,
        "staging_xy": (1.0, 2.0),
        "target_xy": (1.8, 2.0),
        "uncertainty_m": 0.05,
    }
    values.update(changes)
    return PortalPlanCandidate(**values)


def test_normalizes_explicit_geometry_without_qualification_or_motion():
    observation = normalize_portal_plan_candidate(candidate(), CONTEXT)

    assert observation.observation_id == "portal-plan-0001"
    assert observation.context == CONTEXT
    assert observation.map_revision == 12
    assert (observation.near_side.x, observation.near_side.y) == (1.0, 2.0)
    assert (observation.far_side.x, observation.far_side.y) == (1.8, 2.0)
    assert observation.uncertainty_m == 0.05
    assert observation.structural_evidence is (
        PortalStructuralEvidence.INSUFFICIENT)


def test_direction_is_preserved_for_opposite_side_observation():
    reversed_plan = candidate(
        observation_id="portal-plan-reverse",
        map_revision=13,
        staging_xy=(1.8, 2.0),
        target_xy=(1.0, 2.0),
    )

    observation = normalize_portal_plan_candidate(reversed_plan, CONTEXT)

    assert (observation.near_side.x, observation.near_side.y) == (1.8, 2.0)
    assert (observation.far_side.x, observation.far_side.y) == (1.0, 2.0)


def test_exact_replay_is_deterministic_and_memory_counts_it_once():
    memory = PortalMemory(CONTEXT)
    first_observation = normalize_portal_plan_candidate(candidate(), CONTEXT)
    replay_observation = normalize_portal_plan_candidate(candidate(), CONTEXT)

    first = memory.observe(first_observation)
    replay = memory.observe(replay_observation)

    assert first_observation == replay_observation
    assert first.disposition is ObservationDisposition.CREATED
    assert replay.portal_id == first.portal_id
    assert replay.duplicate is True
    assert replay.evidence_added is False
    snapshot = memory.snapshot(first.portal_id)
    assert snapshot.observation_count == 1
    assert snapshot.qualified_evidence_count == 0
    assert snapshot.confirmation_state is PortalConfirmationState.CANDIDATE
    assert snapshot.confirmed_traversal_count == 0


def test_multiple_revisions_remain_unqualified_candidates():
    memory = PortalMemory(CONTEXT)
    first = memory.observe(normalize_portal_plan_candidate(
        candidate(), CONTEXT))
    second = memory.observe(normalize_portal_plan_candidate(
        candidate(
            observation_id="portal-plan-0002",
            map_revision=13,
            staging_xy=(1.01, 2.0),
            target_xy=(1.81, 2.0),
        ),
        CONTEXT,
    ))

    assert second.disposition is ObservationDisposition.MATCHED
    assert second.portal_id == first.portal_id
    snapshot = memory.snapshot(first.portal_id)
    assert snapshot.evidence_count == 2
    assert snapshot.qualified_evidence_count == 0
    assert snapshot.confirmation_state is PortalConfirmationState.CANDIDATE
    assert snapshot.confirmed is False
    assert snapshot.confirmed_traversal_count == 0


@pytest.mark.parametrize("changed_context", [
    PortalMapContext("other-session", CONTEXT.map_id, CONTEXT.frame_id),
    PortalMapContext(CONTEXT.session_id, "other-map", CONTEXT.frame_id),
    PortalMapContext(CONTEXT.session_id, CONTEXT.map_id, "other-frame"),
])
def test_foreign_session_map_or_frame_fails_closed(changed_context):
    with pytest.raises(PortalPlanAdapterError):
        normalize_portal_plan_candidate(
            candidate(context=changed_context), CONTEXT)


@pytest.mark.parametrize("change", [
    {"observation_id": ""},
    {"observation_id": "not safe"},
    {"map_revision": None},
    {"map_revision": True},
    {"map_revision": -1},
    {"staging_xy": [1.0, 2.0]},
    {"staging_xy": (1.0,)},
    {"staging_xy": (math.nan, 2.0)},
    {"target_xy": (math.inf, 2.0)},
    {"target_xy": (1.0, 2.0)},
    {"uncertainty_m": -0.01},
    {"uncertainty_m": math.nan},
    {"uncertainty_m": math.inf},
    {"uncertainty_m": True},
])
def test_invalid_or_degenerate_inputs_fail_closed(change):
    with pytest.raises(PortalPlanAdapterError):
        normalize_portal_plan_candidate(candidate(**change), CONTEXT)


def test_wrong_public_argument_types_fail_closed():
    with pytest.raises(PortalPlanAdapterError):
        normalize_portal_plan_candidate("candidate", CONTEXT)
    with pytest.raises(PortalPlanAdapterError):
        normalize_portal_plan_candidate(candidate(), "context")


def test_candidate_is_immutable():
    plan = candidate()

    with pytest.raises(AttributeError):
        plan.map_revision = 13
