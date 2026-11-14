"""Bounded runtime assembly for paired portal-traversal measurements.

The session accepts already paired map poses and slip-resistant motion
readings.  It neither reads sensors nor commands navigation.  A ROS adapter
may feed it while the existing single-child owner is active.
"""

from dataclasses import dataclass
import hashlib
import math
from typing import Optional, Tuple

from .exploration_child_goal import ExplorationGoalIntent
from .exploration_policy import (
    TaskAttempt,
    TaskAttemptOutcome,
)
from .portal_memory import PortalMapContext, PortalSnapshot
from .portal_task_evidence import PortalGoalCandidate
from .portal_traversal_evidence import (
    IndependentMotionEvidence,
    IndependentMotionSource,
    PortalTraversalAssessment,
    PortalTraversalEvidence,
    PortalTraversalPolicy,
    TraversalExecutionMode,
    TraversalPoseSample,
    assess_portal_traversal,
)


class PortalTraversalRuntimeError(ValueError):
    """Runtime input is malformed, inconsistent or exceeds a hard bound."""


@dataclass(frozen=True)
class PortalTraversalRuntimePolicy:
    """Pure accumulation bounds, separate from evidence thresholds."""

    max_samples: int = 256
    maximum_sample_interval_ns: int = 2_000_000_000

    def __post_init__(self) -> None:
        if (
                isinstance(self.max_samples, bool)
                or not isinstance(self.max_samples, int)
                or self.max_samples < 3
                or self.max_samples > 8192):
            raise PortalTraversalRuntimeError(
                "max_samples muss zwischen 3 und 8192 liegen")
        if (
                isinstance(self.maximum_sample_interval_ns, bool)
                or not isinstance(self.maximum_sample_interval_ns, int)
                or self.maximum_sample_interval_ns <= 0):
            raise PortalTraversalRuntimeError(
                "maximum_sample_interval_ns muss positiv sein")


@dataclass(frozen=True)
class PairedTraversalReading:
    """One timestamp shared by map pose and independent displacement."""

    reading_id: str
    context: PortalMapContext
    map_revision: int
    stamp_ns: int
    x: float
    y: float
    yaw: float
    independent_forward_progress_m: float
    independent_source: IndependentMotionSource

    def __post_init__(self) -> None:
        _identifier(self.reading_id, "reading_id")
        if not isinstance(self.context, PortalMapContext):
            raise PortalTraversalRuntimeError(
                "context muss PortalMapContext sein")
        for name in ("map_revision", "stamp_ns"):
            value = getattr(self, name)
            if (
                    isinstance(value, bool)
                    or not isinstance(value, int)
                    or value < 0):
                raise PortalTraversalRuntimeError(
                    f"{name} muss nichtnegativ sein")
        for name in (
                "x", "y", "yaw", "independent_forward_progress_m"):
            value = getattr(self, name)
            if (
                    isinstance(value, bool)
                    or not isinstance(value, (int, float))
                    or not math.isfinite(float(value))):
                raise PortalTraversalRuntimeError(
                    f"{name} muss endlich sein")
        if not isinstance(self.independent_source, IndependentMotionSource):
            raise PortalTraversalRuntimeError(
                "independent_source ist ungueltig")


@dataclass(frozen=True)
class PortalTraversalRuntimeOutcome:
    """Terminal evidence result; absence of assessment is explicit."""

    confirmed: bool
    reason: str
    sample_count: int
    assessment: Optional[PortalTraversalAssessment]


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
        raise PortalTraversalRuntimeError(f"{name} ist ungueltig")
    return value


def _derived_id(prefix: str, *values: str) -> str:
    digest = hashlib.sha256()
    digest.update(prefix.encode("ascii"))
    for value in values:
        digest.update(b"\0")
        digest.update(value.encode("ascii"))
    return f"{prefix}-{digest.hexdigest()}"


class PortalTraversalRuntimeSession:
    """Accumulate one candidate's bounded paired measurement sequence."""

    def __init__(
            self,
            candidate: PortalGoalCandidate,
            portal: PortalSnapshot,
            evidence_policy: PortalTraversalPolicy,
            runtime_policy: Optional[PortalTraversalRuntimePolicy] = None,
    ) -> None:
        if not isinstance(candidate, PortalGoalCandidate):
            raise PortalTraversalRuntimeError(
                "candidate muss PortalGoalCandidate sein")
        if not isinstance(portal, PortalSnapshot):
            raise PortalTraversalRuntimeError(
                "portal muss PortalSnapshot sein")
        if not isinstance(evidence_policy, PortalTraversalPolicy):
            raise PortalTraversalRuntimeError(
                "evidence_policy muss PortalTraversalPolicy sein")
        selected_runtime = runtime_policy or PortalTraversalRuntimePolicy()
        if not isinstance(selected_runtime, PortalTraversalRuntimePolicy):
            raise PortalTraversalRuntimeError(
                "runtime_policy muss PortalTraversalRuntimePolicy sein")
        if (
                portal.portal_id != candidate.portal_id
                or portal.last_revision > candidate.map_revision):
            raise PortalTraversalRuntimeError(
                "Portalbestand passt nicht zum Zielkandidaten")
        self._candidate = candidate
        self._portal = portal
        self._evidence_policy = evidence_policy
        self._runtime_policy = selected_runtime
        self._readings: Tuple[PairedTraversalReading, ...] = ()
        self._finished = False
        self._outcome = None

    @property
    def candidate(self) -> PortalGoalCandidate:
        return self._candidate

    @property
    def sample_count(self) -> int:
        return len(self._readings)

    def observe(self, reading: PairedTraversalReading) -> None:
        """Append one exact paired reading, rejecting replay and overflow."""
        if self._finished:
            raise PortalTraversalRuntimeError(
                "abgeschlossene Traversierung nimmt keine Messung an")
        if not isinstance(reading, PairedTraversalReading):
            raise PortalTraversalRuntimeError(
                "reading muss PairedTraversalReading sein")
        if (
                reading.context != self._candidate.context
                or reading.map_revision > self._candidate.map_revision):
            raise PortalTraversalRuntimeError(
                "Messung passt nicht zum Zielkontext")
        if reading.independent_source is (
                IndependentMotionSource.WHEEL_ENCODER_ONLY):
            raise PortalTraversalRuntimeError(
                "reine Radencoder sind keine unabhaengige Messung")
        if self._readings:
            previous = self._readings[-1]
            if reading.reading_id == previous.reading_id:
                raise PortalTraversalRuntimeError(
                    "aufeinanderfolgende Messungen duerfen kein Replay sein")
            if reading.stamp_ns <= previous.stamp_ns:
                raise PortalTraversalRuntimeError(
                    "Messzeit muss streng steigen")
            if reading.stamp_ns - previous.stamp_ns > (
                    self._runtime_policy.maximum_sample_interval_ns):
                raise PortalTraversalRuntimeError(
                    "Messabstand ueberschreitet die Laufzeitgrenze")
            if reading.independent_source is not (
                    previous.independent_source):
                raise PortalTraversalRuntimeError(
                    "unabhaengige Quelle darf im Lauf nicht wechseln")
        if len(self._readings) >= self._runtime_policy.max_samples:
            raise PortalTraversalRuntimeError(
                "Portalmonitor ueberschreitet die Messgrenze")
        self._readings += (reading,)

    def finish(
            self, *, execution_succeeded: bool,
            evaluated_at_ns: int,
    ) -> PortalTraversalRuntimeOutcome:
        """Build and evaluate the exact M3/R evidence once."""
        if self._finished:
            return self._outcome
        if not isinstance(execution_succeeded, bool):
            raise PortalTraversalRuntimeError(
                "execution_succeeded muss boolesch sein")
        if (
                isinstance(evaluated_at_ns, bool)
                or not isinstance(evaluated_at_ns, int)
                or evaluated_at_ns < 0):
            raise PortalTraversalRuntimeError(
                "evaluated_at_ns muss nichtnegativ sein")
        self._finished = True
        if len(self._readings) < 2:
            self._outcome = PortalTraversalRuntimeOutcome(
                confirmed=False,
                reason="insufficient_paired_samples",
                sample_count=len(self._readings),
                assessment=None,
            )
            return self._outcome

        first = self._readings[0]
        last = self._readings[-1]
        poses = tuple(
            TraversalPoseSample(
                sample_id=_derived_id(
                    "portal-pose", self._candidate.intent_id,
                    reading.reading_id),
                context=reading.context,
                map_revision=reading.map_revision,
                stamp_ns=reading.stamp_ns,
                x=reading.x,
                y=reading.y,
                yaw=reading.yaw,
            )
            for reading in self._readings
        )
        motion = IndependentMotionEvidence(
            evidence_id=_derived_id(
                "portal-motion", self._candidate.intent_id,
                first.reading_id, last.reading_id),
            context=self._candidate.context,
            map_revision=max(
                reading.map_revision for reading in self._readings),
            start_stamp_ns=first.stamp_ns,
            end_stamp_ns=last.stamp_ns,
            signed_forward_progress_m=(
                last.independent_forward_progress_m
                - first.independent_forward_progress_m),
            source=first.independent_source,
        )
        evidence = PortalTraversalEvidence(
            evidence_id=_derived_id(
                "portal-runtime", self._candidate.intent_id),
            context=self._candidate.context,
            portal=self._portal,
            direction=self._candidate.direction,
            execution_mode=TraversalExecutionMode.REGULAR_NAV2,
            execution_succeeded=execution_succeeded,
            source_map_revision=self._candidate.map_revision,
            source_map_stamp_ns=self._candidate.source_stamp_ns,
            evaluated_at_ns=evaluated_at_ns,
            poses=poses,
            independent_motion=motion,
        )
        assessment = assess_portal_traversal(
            evidence, self._evidence_policy)
        self._outcome = PortalTraversalRuntimeOutcome(
            confirmed=assessment.confirmed,
            reason=assessment.reason,
            sample_count=len(poses),
            assessment=assessment,
        )
        return self._outcome


def retry_attempt_from_portal_outcome(
        intent: ExplorationGoalIntent,
        outcome: PortalTraversalRuntimeOutcome,
        *, retry_delay_revisions: int = 1,
) -> TaskAttempt:
    """Turn missing crossing truth into a bounded retry, never progress."""
    if not isinstance(intent, ExplorationGoalIntent):
        raise PortalTraversalRuntimeError(
            "intent muss ExplorationGoalIntent sein")
    if not isinstance(outcome, PortalTraversalRuntimeOutcome):
        raise PortalTraversalRuntimeError(
            "outcome muss PortalTraversalRuntimeOutcome sein")
    if outcome.confirmed:
        raise PortalTraversalRuntimeError(
            "bestaetigte Querung darf kein Retry werden")
    if (
            isinstance(retry_delay_revisions, bool)
            or not isinstance(retry_delay_revisions, int)
            or retry_delay_revisions <= 0
            or retry_delay_revisions > 4096):
        raise PortalTraversalRuntimeError(
            "retry_delay_revisions ist ungueltig")
    return TaskAttempt(
        attempt_id=_derived_id(
            "portal-retry", intent.intent_id, outcome.reason),
        task_id=intent.task_id,
        context=intent.context,
        map_revision=intent.map_revision,
        outcome=TaskAttemptOutcome.RETRYABLE_FAILURE,
        reason=f"portal_traversal_unconfirmed:{outcome.reason}",
        retry_not_before_revision=(
            intent.map_revision + retry_delay_revisions),
    )
