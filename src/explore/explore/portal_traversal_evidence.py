"""Pure evidence gate for a fully completed portal traversal.

The validator consumes already measured, map-frame observations.  It never
reads TF, sensors or actions and never commands motion.  Its numeric policy is
explicit because chassis and freshness limits require a separately reviewed
profile; no default here is a hardware measurement.
"""

from dataclasses import dataclass
from enum import Enum
import hashlib
import math
from typing import Optional, Tuple

from .portal_memory import (
    Point2D,
    PortalConfirmationState,
    PortalMapContext,
    PortalSnapshot,
    TraversalDirection,
    TraversalEvent,
)


class PortalTraversalEvidenceError(ValueError):
    """The evidence contract is malformed or internally inconsistent."""


class TraversalExecutionMode(str, Enum):
    REGULAR_NAV2 = "regular_nav2"
    SPECIAL_BRIDGE = "special_bridge"


class IndependentMotionSource(str, Enum):
    FROZEN_RANGE_SCAN = "frozen_range_scan"
    VISUAL_INERTIAL = "visual_inertial"
    WHEEL_ENCODER_ONLY = "wheel_encoder_only"


@dataclass(frozen=True)
class PortalTraversalPolicy:
    """Explicit software thresholds awaiting a frozen target profile."""

    chassis_front_overhang_m: float
    chassis_rear_overhang_m: float
    start_clearance_m: float
    exit_clearance_m: float
    maximum_lateral_deviation_m: float
    maximum_pose_step_m: float
    maximum_pose_speed_mps: float
    maximum_yaw_error_rad: float
    maximum_yaw_step_rad: float
    maximum_backward_step_m: float
    maximum_motion_disagreement_m: float
    maximum_source_age_ns: int
    maximum_revision_lag: int
    minimum_pose_samples: int = 3

    def __post_init__(self) -> None:
        positive = (
            "chassis_front_overhang_m",
            "chassis_rear_overhang_m",
            "start_clearance_m",
            "exit_clearance_m",
            "maximum_lateral_deviation_m",
            "maximum_pose_step_m",
            "maximum_pose_speed_mps",
            "maximum_yaw_error_rad",
            "maximum_yaw_step_rad",
            "maximum_motion_disagreement_m",
        )
        for name in positive:
            value = getattr(self, name)
            if (
                    isinstance(value, bool)
                    or not isinstance(value, (int, float))
                    or not math.isfinite(float(value))
                    or float(value) <= 0.0):
                raise PortalTraversalEvidenceError(
                    f"{name} muss endlich und positiv sein")
        backward = self.maximum_backward_step_m
        if (
                isinstance(backward, bool)
                or not isinstance(backward, (int, float))
                or not math.isfinite(float(backward))
                or float(backward) < 0.0):
            raise PortalTraversalEvidenceError(
                "maximum_backward_step_m muss endlich und nichtnegativ sein")
        if self.maximum_yaw_error_rad >= math.pi / 2.0:
            raise PortalTraversalEvidenceError(
                "maximum_yaw_error_rad muss kleiner als pi/2 sein")
        if self.maximum_yaw_step_rad >= math.pi:
            raise PortalTraversalEvidenceError(
                "maximum_yaw_step_rad muss kleiner als pi sein")
        for name in (
                "maximum_source_age_ns", "maximum_revision_lag",
                "minimum_pose_samples"):
            value = getattr(self, name)
            minimum = 3 if name == "minimum_pose_samples" else 0
            if (
                    isinstance(value, bool)
                    or not isinstance(value, int)
                    or value < minimum):
                raise PortalTraversalEvidenceError(
                    f"{name} ist ungueltig")
        if self.maximum_source_age_ns == 0:
            raise PortalTraversalEvidenceError(
                "maximum_source_age_ns muss positiv sein")


@dataclass(frozen=True)
class TraversalPoseSample:
    sample_id: str
    context: PortalMapContext
    map_revision: int
    stamp_ns: int
    x: float
    y: float
    yaw: float

    def __post_init__(self) -> None:
        _identifier(self.sample_id, "sample_id")
        _context(self.context)
        _nonnegative_integer(self.map_revision, "map_revision")
        _nonnegative_integer(self.stamp_ns, "stamp_ns")
        for name in ("x", "y", "yaw"):
            value = getattr(self, name)
            if (
                    isinstance(value, bool)
                    or not isinstance(value, (int, float))
                    or not math.isfinite(float(value))):
                raise PortalTraversalEvidenceError(
                    f"{name} muss endlich sein")


@dataclass(frozen=True)
class IndependentMotionEvidence:
    evidence_id: str
    context: PortalMapContext
    map_revision: int
    start_stamp_ns: int
    end_stamp_ns: int
    signed_forward_progress_m: float
    source: IndependentMotionSource

    def __post_init__(self) -> None:
        _identifier(self.evidence_id, "evidence_id")
        _context(self.context)
        _nonnegative_integer(self.map_revision, "map_revision")
        _nonnegative_integer(self.start_stamp_ns, "start_stamp_ns")
        _nonnegative_integer(self.end_stamp_ns, "end_stamp_ns")
        if self.end_stamp_ns <= self.start_stamp_ns:
            raise PortalTraversalEvidenceError(
                "Bewegungszeitfenster muss positiv sein")
        progress = self.signed_forward_progress_m
        if (
                isinstance(progress, bool)
                or not isinstance(progress, (int, float))
                or not math.isfinite(float(progress))):
            raise PortalTraversalEvidenceError(
                "signed_forward_progress_m muss endlich sein")
        if not isinstance(self.source, IndependentMotionSource):
            raise PortalTraversalEvidenceError(
                "source muss IndependentMotionSource sein")


@dataclass(frozen=True)
class PortalTraversalEvidence:
    evidence_id: str
    context: PortalMapContext
    portal: PortalSnapshot
    direction: TraversalDirection
    execution_mode: TraversalExecutionMode
    execution_succeeded: bool
    source_map_revision: int
    source_map_stamp_ns: int
    evaluated_at_ns: int
    poses: Tuple[TraversalPoseSample, ...]
    independent_motion: IndependentMotionEvidence

    def __post_init__(self) -> None:
        _identifier(self.evidence_id, "evidence_id")
        _context(self.context)
        if not isinstance(self.portal, PortalSnapshot):
            raise PortalTraversalEvidenceError(
                "portal muss PortalSnapshot sein")
        if not isinstance(self.direction, TraversalDirection):
            raise PortalTraversalEvidenceError(
                "direction muss TraversalDirection sein")
        if not isinstance(self.execution_mode, TraversalExecutionMode):
            raise PortalTraversalEvidenceError(
                "execution_mode muss TraversalExecutionMode sein")
        if not isinstance(self.execution_succeeded, bool):
            raise PortalTraversalEvidenceError(
                "execution_succeeded muss bool sein")
        _nonnegative_integer(self.source_map_revision, "source_map_revision")
        _nonnegative_integer(self.source_map_stamp_ns, "source_map_stamp_ns")
        _nonnegative_integer(self.evaluated_at_ns, "evaluated_at_ns")
        if not isinstance(self.poses, tuple) or any(
                not isinstance(item, TraversalPoseSample)
                for item in self.poses):
            raise PortalTraversalEvidenceError(
                "poses muss ein Tupel aus TraversalPoseSample sein")
        if not isinstance(self.independent_motion, IndependentMotionEvidence):
            raise PortalTraversalEvidenceError(
                "independent_motion muss IndependentMotionEvidence sein")


@dataclass(frozen=True)
class PortalTraversalAssessment:
    evidence_id: str
    confirmed: bool
    reason: str
    execution_mode: TraversalExecutionMode
    direction: TraversalDirection
    localized_forward_progress_m: float
    independent_forward_progress_m: float
    start_clearance_m: float
    exit_clearance_m: float
    maximum_lateral_deviation_m: float
    traversal_event: Optional[TraversalEvent] = None


def _identifier(value: object, name: str) -> str:
    if (
            not isinstance(value, str)
            or not value
            or len(value) > 128
            or not value.isascii()
            or not value[0].isalnum()
            or any(
                not (character.isalnum() or character in "_.:-")
                for character in value)):
        raise PortalTraversalEvidenceError(f"{name} ist ungueltig")
    return value


def _context(value: object) -> PortalMapContext:
    if not isinstance(value, PortalMapContext):
        raise PortalTraversalEvidenceError(
            "context muss PortalMapContext sein")
    return value


def _nonnegative_integer(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise PortalTraversalEvidenceError(
            f"{name} muss eine nichtnegative Ganzzahl sein")
    return value


def _angle_difference(first: float, second: float) -> float:
    return math.atan2(math.sin(first - second), math.cos(first - second))


def _rejected(
        evidence: PortalTraversalEvidence, reason: str, *,
        localized_progress: float = 0.0,
        start_clearance: float = 0.0,
        exit_clearance: float = 0.0,
        lateral_deviation: float = 0.0) -> PortalTraversalAssessment:
    return PortalTraversalAssessment(
        evidence_id=evidence.evidence_id,
        confirmed=False,
        reason=reason,
        execution_mode=evidence.execution_mode,
        direction=evidence.direction,
        localized_forward_progress_m=localized_progress,
        independent_forward_progress_m=(
            evidence.independent_motion.signed_forward_progress_m),
        start_clearance_m=start_clearance,
        exit_clearance_m=exit_clearance,
        maximum_lateral_deviation_m=lateral_deviation,
    )


def assess_portal_traversal(
        evidence: PortalTraversalEvidence,
        policy: PortalTraversalPolicy) -> PortalTraversalAssessment:
    """Confirm only mutually consistent, fresh, full-chassis evidence."""
    if not isinstance(evidence, PortalTraversalEvidence):
        raise PortalTraversalEvidenceError(
            "evidence muss PortalTraversalEvidence sein")
    if not isinstance(policy, PortalTraversalPolicy):
        raise PortalTraversalEvidenceError(
            "policy muss PortalTraversalPolicy sein")
    if (
            evidence.portal.confirmed is not True
            or evidence.portal.confirmation_state
            is not PortalConfirmationState.CONFIRMED):
        return _rejected(evidence, "portal_not_confirmed")
    if evidence.portal.last_revision > evidence.source_map_revision:
        return _rejected(evidence, "portal_revision_ahead_of_source_map")
    if evidence.evaluated_at_ns < evidence.source_map_stamp_ns:
        return _rejected(evidence, "source_map_stamp_in_future")
    if (
            evidence.evaluated_at_ns - evidence.source_map_stamp_ns
            > policy.maximum_source_age_ns):
        return _rejected(evidence, "source_map_stale")
    if not evidence.execution_succeeded:
        return _rejected(evidence, "execution_not_successful")

    poses = evidence.poses
    if len(poses) < policy.minimum_pose_samples:
        return _rejected(evidence, "insufficient_pose_samples")
    motion = evidence.independent_motion
    if any(sample.context != evidence.context for sample in poses):
        return _rejected(evidence, "pose_context_mismatch")
    if motion.context != evidence.context:
        return _rejected(evidence, "motion_context_mismatch")
    if motion.source is IndependentMotionSource.WHEEL_ENCODER_ONLY:
        return _rejected(evidence, "motion_source_not_slip_resistant")
    if (
            motion.start_stamp_ns != poses[0].stamp_ns
            or motion.end_stamp_ns != poses[-1].stamp_ns):
        return _rejected(evidence, "motion_window_mismatch")
    if evidence.evaluated_at_ns < poses[-1].stamp_ns:
        return _rejected(evidence, "pose_stamp_in_future")
    if (
            evidence.evaluated_at_ns - poses[-1].stamp_ns
            > policy.maximum_source_age_ns):
        return _rejected(evidence, "pose_source_stale")

    revisions = tuple(sample.map_revision for sample in poses) + (
        motion.map_revision,)
    if any(revision > evidence.source_map_revision for revision in revisions):
        return _rejected(evidence, "evidence_revision_ahead_of_source_map")
    if any(
            evidence.source_map_revision - revision
            > policy.maximum_revision_lag
            for revision in revisions):
        return _rejected(evidence, "evidence_revision_stale")
    if any(
            second.map_revision < first.map_revision
            for first, second in zip(poses, poses[1:])):
        return _rejected(evidence, "pose_revision_regressed")
    if any(
            second.stamp_ns <= first.stamp_ns
            for first, second in zip(poses, poses[1:])):
        return _rejected(evidence, "pose_time_not_strictly_increasing")

    side_a = evidence.portal.side_a
    side_b = evidence.portal.side_b
    if not isinstance(side_a, Point2D) or not isinstance(side_b, Point2D):
        raise PortalTraversalEvidenceError(
            "Portalgeometrie muss zwei Point2D-Seiten besitzen")
    axis_x = side_b.x - side_a.x
    axis_y = side_b.y - side_a.y
    portal_span = math.hypot(axis_x, axis_y)
    if portal_span <= 1e-9:
        return _rejected(evidence, "portal_axis_degenerate")
    axis_x /= portal_span
    axis_y /= portal_span
    start_anchor = side_a
    end_anchor = side_b
    expected_yaw = math.atan2(axis_y, axis_x)
    if evidence.direction is TraversalDirection.B_TO_A:
        axis_x = -axis_x
        axis_y = -axis_y
        start_anchor = side_b
        end_anchor = side_a
        expected_yaw = math.atan2(axis_y, axis_x)

    projections = []
    lateral_deviations = []
    for sample in poses:
        relative_x = sample.x - start_anchor.x
        relative_y = sample.y - start_anchor.y
        projections.append(relative_x * axis_x + relative_y * axis_y)
        lateral_deviations.append(abs(
            -relative_x * axis_y + relative_y * axis_x))
        if abs(_angle_difference(sample.yaw, expected_yaw)) > (
                policy.maximum_yaw_error_rad):
            return _rejected(
                evidence, "pose_heading_not_portal_directed",
                lateral_deviation=max(lateral_deviations))

    maximum_lateral = max(lateral_deviations)
    localized_progress = projections[-1] - projections[0]
    start_clearance = (
        -projections[0] - policy.chassis_front_overhang_m)
    end_projection = (
        (poses[-1].x - end_anchor.x) * axis_x
        + (poses[-1].y - end_anchor.y) * axis_y)
    exit_clearance = end_projection - policy.chassis_rear_overhang_m
    if maximum_lateral > policy.maximum_lateral_deviation_m:
        return _rejected(
            evidence, "pose_left_portal_corridor",
            localized_progress=localized_progress,
            start_clearance=start_clearance,
            exit_clearance=exit_clearance,
            lateral_deviation=maximum_lateral)
    if start_clearance < policy.start_clearance_m:
        return _rejected(
            evidence, "chassis_not_fully_before_portal",
            localized_progress=localized_progress,
            start_clearance=start_clearance,
            exit_clearance=exit_clearance,
            lateral_deviation=maximum_lateral)
    if exit_clearance < policy.exit_clearance_m:
        return _rejected(
            evidence, "chassis_exit_not_complete",
            localized_progress=localized_progress,
            start_clearance=start_clearance,
            exit_clearance=exit_clearance,
            lateral_deviation=maximum_lateral)

    for first, second, first_projection, second_projection in zip(
            poses, poses[1:], projections, projections[1:]):
        elapsed_seconds = (second.stamp_ns - first.stamp_ns) / 1e9
        step = math.hypot(second.x - first.x, second.y - first.y)
        if step > policy.maximum_pose_step_m:
            return _rejected(
                evidence, "pose_step_exceeds_jump_limit",
                localized_progress=localized_progress,
                start_clearance=start_clearance,
                exit_clearance=exit_clearance,
                lateral_deviation=maximum_lateral)
        if step / elapsed_seconds > policy.maximum_pose_speed_mps:
            return _rejected(
                evidence, "pose_speed_exceeds_limit",
                localized_progress=localized_progress,
                start_clearance=start_clearance,
                exit_clearance=exit_clearance,
                lateral_deviation=maximum_lateral)
        if abs(_angle_difference(second.yaw, first.yaw)) > (
                policy.maximum_yaw_step_rad):
            return _rejected(
                evidence, "pose_yaw_step_exceeds_jump_limit",
                localized_progress=localized_progress,
                start_clearance=start_clearance,
                exit_clearance=exit_clearance,
                lateral_deviation=maximum_lateral)
        if second_projection - first_projection < (
                -policy.maximum_backward_step_m):
            return _rejected(
                evidence, "pose_progress_reversed",
                localized_progress=localized_progress,
                start_clearance=start_clearance,
                exit_clearance=exit_clearance,
                lateral_deviation=maximum_lateral)

    independent_progress = motion.signed_forward_progress_m
    if independent_progress <= 0.0:
        return _rejected(
            evidence, "independent_motion_not_forward",
            localized_progress=localized_progress,
            start_clearance=start_clearance,
            exit_clearance=exit_clearance,
            lateral_deviation=maximum_lateral)
    if abs(independent_progress - localized_progress) > (
            policy.maximum_motion_disagreement_m):
        return _rejected(
            evidence, "localized_and_independent_motion_disagree",
            localized_progress=localized_progress,
            start_clearance=start_clearance,
            exit_clearance=exit_clearance,
            lateral_deviation=maximum_lateral)

    digest = hashlib.sha256()
    digest.update(b"we-portal-traversal-v1\0")
    for value in (
            evidence.evidence_id,
            evidence.context.session_id,
            evidence.context.map_id,
            evidence.context.frame_id,
            evidence.portal.portal_id,
            evidence.direction.value,
            evidence.execution_mode.value,
            str(evidence.execution_succeeded),
            str(evidence.source_map_revision),
            str(evidence.source_map_stamp_ns),
            motion.evidence_id,
            str(motion.map_revision),
            str(motion.start_stamp_ns),
            str(motion.end_stamp_ns),
            float(motion.signed_forward_progress_m).hex(),
            motion.source.value):
        digest.update(value.encode("ascii"))
        digest.update(b"\0")
    for sample in poses:
        for value in (
                sample.sample_id,
                str(sample.map_revision),
                str(sample.stamp_ns),
                float(sample.x).hex(),
                float(sample.y).hex(),
                float(sample.yaw).hex()):
            digest.update(value.encode("ascii"))
            digest.update(b"\0")
    event = TraversalEvent(
        event_id=f"auto-traversal-{digest.hexdigest()}",
        portal_id=evidence.portal.portal_id,
        context=evidence.context,
        map_revision=evidence.source_map_revision,
        event_time_ns=poses[-1].stamp_ns,
        direction=evidence.direction,
        crossing_confirmed=True,
    )
    return PortalTraversalAssessment(
        evidence_id=evidence.evidence_id,
        confirmed=True,
        reason="full_chassis_crossing_confirmed",
        execution_mode=evidence.execution_mode,
        direction=evidence.direction,
        localized_forward_progress_m=localized_progress,
        independent_forward_progress_m=independent_progress,
        start_clearance_m=start_clearance,
        exit_clearance_m=exit_clearance,
        maximum_lateral_deviation_m=maximum_lateral,
        traversal_event=event,
    )
