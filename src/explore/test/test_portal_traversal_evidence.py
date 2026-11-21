from dataclasses import replace
from pathlib import Path
import math
import sys

import pytest


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE_ROOT))

from explore.portal_memory import (  # noqa: E402
    Point2D,
    PortalConfirmationState,
    PortalMapContext,
    PortalSnapshot,
    TraversalDirection,
)
from explore.portal_traversal_evidence import (  # noqa: E402
    IndependentMotionEvidence,
    IndependentMotionSource,
    PortalTraversalEvidence,
    PortalTraversalEvidenceError,
    PortalTraversalPolicy,
    TraversalExecutionMode,
    TraversalPoseSample,
    assess_portal_traversal,
)


CONTEXT = PortalMapContext("session-m3r", "map-m3r", "map")


def policy(**changes):
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


def portal():
    return PortalSnapshot(
        portal_id="portal_000001",
        side_a=Point2D(0.0, 0.0),
        side_b=Point2D(1.0, 0.0),
        first_revision=8,
        last_revision=9,
        observation_count=2,
        evidence_count=2,
        qualified_evidence_count=2,
        confirmation_state=PortalConfirmationState.CONFIRMED,
        confirmed=True,
        confirmed_traversal_count=0,
    )


def pose(sample_id, revision, stamp_seconds, x, y=0.0, yaw=0.0):
    return TraversalPoseSample(
        sample_id=sample_id,
        context=CONTEXT,
        map_revision=revision,
        stamp_ns=int(stamp_seconds * 1e9),
        x=x,
        y=y,
        yaw=yaw,
    )


def evidence(**changes):
    poses = (
        pose("pose-1", 9, 1.0, -0.50),
        pose("pose-2", 9, 2.0, 0.10),
        pose("pose-3", 10, 3.0, 0.70),
        pose("pose-4", 10, 4.0, 1.50),
    )
    values = {
        "evidence_id": "portal-traversal-m3r",
        "context": CONTEXT,
        "portal": portal(),
        "direction": TraversalDirection.A_TO_B,
        "execution_mode": TraversalExecutionMode.REGULAR_NAV2,
        "execution_succeeded": True,
        "source_map_revision": 10,
        "source_map_stamp_ns": 4_000_000_000,
        "evaluated_at_ns": 4_100_000_000,
        "poses": poses,
        "independent_motion": IndependentMotionEvidence(
            evidence_id="frozen-scan-motion",
            context=CONTEXT,
            map_revision=10,
            start_stamp_ns=poses[0].stamp_ns,
            end_stamp_ns=poses[-1].stamp_ns,
            signed_forward_progress_m=2.0,
            source=IndependentMotionSource.FROZEN_RANGE_SCAN,
        ),
    }
    values.update(changes)
    return PortalTraversalEvidence(**values)


def test_regular_nav2_crossing_requires_and_emits_full_evidence_event():
    first = assess_portal_traversal(evidence(), policy())
    replay = assess_portal_traversal(evidence(), policy())

    assert first.confirmed is True
    assert first.reason == "full_chassis_crossing_confirmed"
    assert first.start_clearance_m == pytest.approx(0.20)
    assert first.exit_clearance_m == pytest.approx(0.20)
    assert first.localized_forward_progress_m == pytest.approx(2.0)
    assert first.traversal_event.crossing_confirmed is True
    assert first.traversal_event.direction is TraversalDirection.A_TO_B
    assert first.traversal_event == replay.traversal_event


def test_special_bridge_uses_the_same_evidence_thresholds():
    regular = assess_portal_traversal(evidence(), policy())
    assessed = assess_portal_traversal(evidence(
        execution_mode=TraversalExecutionMode.SPECIAL_BRIDGE), policy())

    assert assessed.confirmed is True
    assert assessed.execution_mode is TraversalExecutionMode.SPECIAL_BRIDGE
    assert assessed.traversal_event.event_id != (
        regular.traversal_event.event_id)


def test_nav2_success_before_full_chassis_exit_is_not_a_crossing():
    poses = evidence().poses[:-1] + (pose("pose-4", 10, 4.0, 1.25),)
    assessed = assess_portal_traversal(evidence(
        poses=poses,
        independent_motion=replace(
            evidence().independent_motion,
            end_stamp_ns=poses[-1].stamp_ns,
            signed_forward_progress_m=1.75,
        )), policy())

    assert assessed.confirmed is False
    assert assessed.reason == "chassis_exit_not_complete"
    assert assessed.traversal_event is None


def test_nav2_success_without_enough_pose_history_is_not_a_crossing():
    poses = (evidence().poses[0], evidence().poses[-1])
    assessed = assess_portal_traversal(evidence(
        poses=poses,
        independent_motion=replace(
            evidence().independent_motion,
            start_stamp_ns=poses[0].stamp_ns,
            end_stamp_ns=poses[-1].stamp_ns,
        )), policy())

    assert assessed.reason == "insufficient_pose_samples"
    assert assessed.confirmed is False


def test_inconsistent_portal_confirmation_is_not_accepted():
    candidate = replace(
        portal(), confirmation_state=PortalConfirmationState.CANDIDATE)

    assessed = assess_portal_traversal(evidence(portal=candidate), policy())

    assert assessed.reason == "portal_not_confirmed"
    assert assessed.confirmed is False


def test_wheel_encoder_only_evidence_cannot_hide_chassis_slip():
    motion = replace(
        evidence().independent_motion,
        source=IndependentMotionSource.WHEEL_ENCODER_ONLY)

    assessed = assess_portal_traversal(evidence(
        independent_motion=motion), policy())

    assert assessed.reason == "motion_source_not_slip_resistant"
    assert assessed.confirmed is False


def test_tf_position_jump_is_rejected_even_when_endpoints_look_valid():
    poses = (
        pose("pose-1", 9, 1.0, -0.50),
        pose("pose-2", 9, 2.0, -0.40),
        pose("pose-3", 10, 3.0, 1.40),
        pose("pose-4", 10, 4.0, 1.50),
    )
    assessed = assess_portal_traversal(evidence(
        poses=poses,
        independent_motion=replace(
            evidence().independent_motion,
            start_stamp_ns=poses[0].stamp_ns,
            end_stamp_ns=poses[-1].stamp_ns,
        )), policy())

    assert assessed.reason == "pose_step_exceeds_jump_limit"
    assert assessed.confirmed is False


def test_tf_displacement_must_agree_with_independent_motion():
    assessed = assess_portal_traversal(evidence(
        independent_motion=replace(
            evidence().independent_motion,
            signed_forward_progress_m=0.20,
        )), policy())

    assert assessed.reason == "localized_and_independent_motion_disagree"
    assert assessed.confirmed is False


def test_opposite_heading_does_not_confirm_requested_direction():
    poses = tuple(replace(item, yaw=math.pi) for item in evidence().poses)
    assessed = assess_portal_traversal(evidence(poses=poses), policy())

    assert assessed.reason == "pose_heading_not_portal_directed"
    assert assessed.confirmed is False


def test_canonical_reverse_direction_can_be_confirmed_separately():
    poses = (
        pose("pose-1", 9, 1.0, 1.50, yaw=math.pi),
        pose("pose-2", 9, 2.0, 0.90, yaw=math.pi),
        pose("pose-3", 10, 3.0, 0.30, yaw=math.pi),
        pose("pose-4", 10, 4.0, -0.50, yaw=math.pi),
    )
    assessed = assess_portal_traversal(evidence(
        direction=TraversalDirection.B_TO_A,
        poses=poses,
        independent_motion=replace(
            evidence().independent_motion,
            start_stamp_ns=poses[0].stamp_ns,
            end_stamp_ns=poses[-1].stamp_ns,
        )), policy())

    assert assessed.confirmed is True
    assert assessed.traversal_event.direction is TraversalDirection.B_TO_A


@pytest.mark.parametrize(("changed", "reason"), [
    ({"execution_succeeded": False}, "execution_not_successful"),
    ({"evaluated_at_ns": 4_600_000_001}, "source_map_stale"),
    ({"source_map_revision": 8}, "portal_revision_ahead_of_source_map"),
])
def test_failed_or_stale_execution_never_confirms(changed, reason):
    assessed = assess_portal_traversal(evidence(**changed), policy())

    assert assessed.reason == reason
    assert assessed.confirmed is False


def test_lateral_departure_and_backward_progress_are_rejected():
    lateral = list(evidence().poses)
    lateral[2] = replace(lateral[2], y=0.21)
    lateral_result = assess_portal_traversal(evidence(
        poses=tuple(lateral)), policy())

    backward = list(evidence().poses)
    backward[2] = replace(backward[2], x=0.0)
    backward_result = assess_portal_traversal(evidence(
        poses=tuple(backward)), policy(maximum_pose_step_m=1.0))

    assert lateral_result.reason == "pose_left_portal_corridor"
    assert backward_result.reason == "pose_progress_reversed"


def test_context_revision_and_motion_window_must_match_exactly():
    foreign = replace(CONTEXT, session_id="other-session")
    context_result = assess_portal_traversal(evidence(
        poses=(replace(evidence().poses[0], context=foreign),)
        + evidence().poses[1:]), policy())
    revision_result = assess_portal_traversal(evidence(
        independent_motion=replace(
            evidence().independent_motion, map_revision=8)), policy())
    window_result = assess_portal_traversal(evidence(
        independent_motion=replace(
            evidence().independent_motion, end_stamp_ns=3_999_999_999)),
        policy())

    assert context_result.reason == "pose_context_mismatch"
    assert revision_result.reason == "evidence_revision_stale"
    assert window_result.reason == "motion_window_mismatch"


@pytest.mark.parametrize("changes", [
    {"maximum_source_age_ns": 0},
    {"maximum_revision_lag": -1},
    {"minimum_pose_samples": 2},
    {"maximum_backward_step_m": -0.1},
    {"maximum_yaw_error_rad": math.pi / 2.0},
])
def test_invalid_policy_is_rejected(changes):
    with pytest.raises(PortalTraversalEvidenceError):
        policy(**changes)
