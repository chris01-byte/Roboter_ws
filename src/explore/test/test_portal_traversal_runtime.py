from dataclasses import replace
from pathlib import Path
import math
import sys

import pytest


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE_ROOT))

from explore.exploration_child_goal import ExplorationGoalIntent  # noqa: E402
from explore.exploration_policy import TaskAttemptOutcome  # noqa: E402
from explore.portal_memory import (  # noqa: E402
    Point2D,
    PortalConfirmationState,
    PortalMapContext,
    PortalSnapshot,
    TraversalDirection,
)
from explore.portal_task_evidence import PortalGoalCandidate  # noqa: E402
from explore.portal_traversal_evidence import (  # noqa: E402
    IndependentMotionSource,
    PortalTraversalPolicy,
)
from explore.portal_traversal_runtime import (  # noqa: E402
    PairedTraversalReading,
    PortalTraversalRuntimeError,
    PortalTraversalRuntimePolicy,
    PortalTraversalRuntimeSession,
    retry_attempt_from_portal_outcome,
)


CONTEXT = PortalMapContext("session-m3t", "map-m3t", "map")


def candidate(**changes):
    values = {
        "intent_id": "intent-portal-10",
        "task_id": "task-portal_000001",
        "region_id": "region_000002",
        "portal_id": "portal_000001",
        "direction": TraversalDirection.A_TO_B,
        "context": CONTEXT,
        "map_revision": 10,
        "frame_id": "map",
        "source_fingerprint": "a" * 64,
        "source_stamp_ns": 4_000_000_000,
        "scope_id": "scope-m3t",
        "scope_fingerprint": "b" * 64,
        "target_x_m": 1.5,
        "target_y_m": 0.0,
        "target_yaw_rad": 0.0,
        "target_row": 0,
        "target_col": 15,
        "route_length_m": 2.0,
        "path_cells": tuple((0, column) for column in range(16)),
    }
    values.update(changes)
    return PortalGoalCandidate(**values)


def portal(**changes):
    values = {
        "portal_id": "portal_000001",
        "side_a": Point2D(0.0, 0.0),
        "side_b": Point2D(1.0, 0.0),
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


def evidence_policy(**changes):
    values = {
        "chassis_front_overhang_m": 0.30,
        "chassis_rear_overhang_m": 0.30,
        "start_clearance_m": 0.10,
        "exit_clearance_m": 0.10,
        "maximum_lateral_deviation_m": 0.20,
        "maximum_pose_step_m": 0.85,
        "maximum_pose_speed_mps": 0.90,
        "maximum_yaw_error_rad": 0.25,
        "maximum_yaw_step_rad": 0.20,
        "maximum_backward_step_m": 0.05,
        "maximum_motion_disagreement_m": 0.15,
        "maximum_source_age_ns": 500_000_000,
        "maximum_revision_lag": 1,
        "minimum_pose_samples": 3,
    }
    values.update(changes)
    return PortalTraversalPolicy(**values)


def reading(index, x, *, independent=None, revision=10, source=None):
    return PairedTraversalReading(
        reading_id=f"reading-{index}",
        context=CONTEXT,
        map_revision=revision,
        stamp_ns=index * 1_000_000_000,
        x=x,
        y=0.0,
        yaw=0.0,
        independent_forward_progress_m=(
            x + 0.5 if independent is None else independent),
        independent_source=(
            source or IndependentMotionSource.FROZEN_RANGE_SCAN),
    )


def completed_session():
    session = PortalTraversalRuntimeSession(
        candidate(), portal(), evidence_policy())
    for item in (
            reading(1, -0.5),
            reading(2, 0.1),
            reading(3, 0.7),
            reading(4, 1.5)):
        session.observe(item)
    return session


def test_paired_runtime_builds_exact_m3r_event_and_replays_finish():
    session = completed_session()

    outcome = session.finish(
        execution_succeeded=True, evaluated_at_ns=4_100_000_000)
    replay = session.finish(
        execution_succeeded=True, evaluated_at_ns=4_100_000_000)

    assert outcome.confirmed is True
    assert outcome.reason == "full_chassis_crossing_confirmed"
    assert outcome.sample_count == 4
    assert outcome.assessment.traversal_event.portal_id == "portal_000001"
    assert replay is outcome
    with pytest.raises(PortalTraversalRuntimeError):
        session.observe(reading(5, 1.6))


def test_nav_success_without_full_exit_becomes_retryable_not_progress():
    session = PortalTraversalRuntimeSession(
        candidate(), portal(), evidence_policy())
    for item in (
            reading(1, -0.5),
            reading(2, 0.1),
            reading(3, 0.7),
            reading(4, 1.2)):
        session.observe(item)

    outcome = session.finish(
        execution_succeeded=True, evaluated_at_ns=4_100_000_000)
    intent = ExplorationGoalIntent(
        candidate().intent_id,
        candidate().task_id,
        candidate().region_id,
        CONTEXT,
        10,
    )
    attempt = retry_attempt_from_portal_outcome(intent, outcome)

    assert outcome.confirmed is False
    assert outcome.reason == "chassis_exit_not_complete"
    assert attempt.outcome is TaskAttemptOutcome.RETRYABLE_FAILURE
    assert attempt.reason == (
        "portal_traversal_unconfirmed:chassis_exit_not_complete")
    assert attempt.retry_not_before_revision == 11


def test_execution_failure_can_never_confirm_crossing():
    outcome = completed_session().finish(
        execution_succeeded=False, evaluated_at_ns=4_100_000_000)

    assert outcome.confirmed is False
    assert outcome.reason == "execution_not_successful"


def test_less_than_two_paired_samples_is_explicitly_unassessable():
    session = PortalTraversalRuntimeSession(
        candidate(), portal(), evidence_policy())
    session.observe(reading(1, -0.5))

    outcome = session.finish(
        execution_succeeded=True, evaluated_at_ns=1_100_000_000)

    assert outcome.confirmed is False
    assert outcome.reason == "insufficient_paired_samples"
    assert outcome.assessment is None


def test_runtime_rejects_wrong_context_wheel_only_replay_and_overflow():
    session = PortalTraversalRuntimeSession(
        candidate(), portal(), evidence_policy(),
        PortalTraversalRuntimePolicy(max_samples=3))
    with pytest.raises(PortalTraversalRuntimeError):
        session.observe(replace(
            reading(1, -0.5),
            context=PortalMapContext("other", "map-m3t", "map")))
    with pytest.raises(PortalTraversalRuntimeError):
        session.observe(reading(
            1, -0.5,
            source=IndependentMotionSource.WHEEL_ENCODER_ONLY))
    session.observe(reading(1, -0.5))
    with pytest.raises(PortalTraversalRuntimeError):
        session.observe(reading(1, -0.4))
    session.observe(reading(2, 0.0))
    session.observe(reading(3, 0.5))
    with pytest.raises(PortalTraversalRuntimeError):
        session.observe(reading(4, 1.0))


def test_runtime_rejects_source_switch_and_nonincreasing_time():
    session = PortalTraversalRuntimeSession(
        candidate(), portal(), evidence_policy())
    session.observe(reading(1, -0.5))
    with pytest.raises(PortalTraversalRuntimeError):
        session.observe(replace(
            reading(2, 0.0),
            independent_source=IndependentMotionSource.VISUAL_INERTIAL))
    with pytest.raises(PortalTraversalRuntimeError):
        session.observe(replace(reading(2, 0.0), stamp_ns=1_000_000_000))


def test_runtime_rejects_unbounded_gap_between_paired_samples():
    session = PortalTraversalRuntimeSession(
        candidate(), portal(), evidence_policy(),
        PortalTraversalRuntimePolicy(
            maximum_sample_interval_ns=500_000_000))
    session.observe(reading(1, -0.5))

    with pytest.raises(PortalTraversalRuntimeError):
        session.observe(reading(2, 0.0))


def test_reverse_candidate_uses_same_paired_runtime_contract():
    reverse = candidate(
        direction=TraversalDirection.B_TO_A,
        target_x_m=-0.5,
        target_yaw_rad=math.pi,
    )
    session = PortalTraversalRuntimeSession(
        reverse, portal(), evidence_policy())
    for index, x in enumerate((1.5, 0.9, 0.3, -0.5), start=1):
        session.observe(replace(
            reading(index, x, independent=-(x - 1.5)),
            yaw=math.pi,
        ))

    outcome = session.finish(
        execution_succeeded=True, evaluated_at_ns=4_100_000_000)

    assert outcome.confirmed is True
    assert outcome.assessment.traversal_event.direction is (
        TraversalDirection.B_TO_A)


def test_candidate_portal_revision_and_policy_are_exactly_validated():
    with pytest.raises(PortalTraversalRuntimeError):
        PortalTraversalRuntimeSession(
            candidate(), portal(portal_id="other-portal"), evidence_policy())
    with pytest.raises(PortalTraversalRuntimeError):
        PortalTraversalRuntimeSession(
            candidate(), portal(last_revision=11), evidence_policy())
    with pytest.raises(PortalTraversalRuntimeError):
        PortalTraversalRuntimePolicy(max_samples=2)
