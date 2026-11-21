"""Pure translation from child-goal results into task-policy events.

Navigation success is deliberately only progress evidence.  Frontier task
completion remains owned by later fresh map/task observations.  This module
contains no ROS, Nav2, action, command, clock, or motion access.
"""

from dataclasses import dataclass
from enum import Enum
import hashlib
import re
from typing import Optional, Tuple

from .exploration_child_goal import (
    ChildGoalOutcome,
    ChildGoalResolution,
    ChildGoalResolutionState,
)
from .exploration_policy import (
    ExplorationTaskPolicySession,
    TaskAttempt,
    TaskAttemptOutcome,
    TaskHistorySnapshot,
)
from .portal_memory import PortalMapContext


_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")


class ChildResultPolicyError(ValueError):
    """A child result is inconsistent or cannot be applied safely."""


class ChildResultDispositionState(str, Enum):
    PROGRESSED = "progressed"
    RETRY_SCHEDULED = "retry_scheduled"
    TEMPORARILY_BLOCKED = "temporarily_blocked"
    REEVALUATE = "reevaluate"
    ABORTED = "aborted"
    CANCELED = "canceled"


@dataclass(frozen=True)
class ChildResultPolicy:
    retry_delay_revisions: int = 1

    def __post_init__(self) -> None:
        if (
                isinstance(self.retry_delay_revisions, bool)
                or not isinstance(self.retry_delay_revisions, int)
                or self.retry_delay_revisions <= 0
                or self.retry_delay_revisions > 4096):
            raise ChildResultPolicyError(
                "retry_delay_revisions muss zwischen 1 und 4096 liegen")


@dataclass(frozen=True)
class ChildResultDisposition:
    result_id: str
    intent_id: str
    task_id: str
    map_revision: int
    state: ChildResultDispositionState
    reason: str
    attempt: Optional[TaskAttempt]
    terminates_exploration: bool


def _validate_resolution(resolution: ChildGoalResolution) -> None:
    if not isinstance(resolution, ChildGoalResolution):
        raise ChildResultPolicyError(
            "resolution muss ChildGoalResolution sein")
    if any(
            not isinstance(value, str)
            or _IDENTIFIER.fullmatch(value) is None
            for value in (
                resolution.result_id,
                resolution.intent_id,
                resolution.task_id)):
        raise ChildResultPolicyError(
            "Kindzielresultat enthaelt ungueltige IDs")
    if not isinstance(resolution.context, PortalMapContext):
        raise ChildResultPolicyError(
            "Kindzielresultat enthaelt keinen Kartenkontext")
    if any(
            isinstance(value, bool) or not isinstance(value, int)
            or value < 0
            for value in (
                resolution.intent_map_revision,
                resolution.observed_map_revision)):
        raise ChildResultPolicyError(
            "Kindzielresultat enthaelt ungueltige Revisionen")
    if not isinstance(resolution.reported_outcome, ChildGoalOutcome):
        raise ChildResultPolicyError(
            "Kindzielresultat enthaelt kein gemeldetes Ergebnis")
    if not isinstance(resolution.state, ChildGoalResolutionState):
        raise ChildResultPolicyError(
            "Kindzielresultat enthaelt keinen Aufloesungszustand")
    expected = {
        ChildGoalResolutionState.COMPLETED: ChildGoalOutcome.SUCCEEDED,
        ChildGoalResolutionState.RETRYABLE_FAILURE: (
            ChildGoalOutcome.RETRYABLE_FAILURE),
        ChildGoalResolutionState.TEMPORARILY_BLOCKED: (
            ChildGoalOutcome.LOCAL_BLOCKED),
        ChildGoalResolutionState.ABORTED: ChildGoalOutcome.ABORTED,
        ChildGoalResolutionState.CANCELED: ChildGoalOutcome.CANCELED,
    }
    if (
            resolution.state in expected
            and resolution.reported_outcome is not expected[resolution.state]):
        raise ChildResultPolicyError(
            "Kindzielzustand widerspricht dem gemeldeten Ergebnis")
    if (
            resolution.state is not ChildGoalResolutionState.INVALIDATED
            and resolution.observed_map_revision
            != resolution.intent_map_revision):
        raise ChildResultPolicyError(
            "Nicht invalidiertes Ergebnis muss zur Zielrevision gehoeren")
    if (
            resolution.observed_map_revision < resolution.intent_map_revision
            or not isinstance(resolution.reason, str)
            or not resolution.reason.strip()
            or len(resolution.reason) > 256):
        raise ChildResultPolicyError(
            "Kindzielresultat enthaelt ungueltige Belege")


def _attempt_id(resolution: ChildGoalResolution) -> str:
    digest = hashlib.sha256()
    digest.update(b"we-task-attempt-v1\0")
    digest.update(resolution.result_id.encode("ascii"))
    digest.update(b"\0")
    digest.update(resolution.intent_id.encode("ascii"))
    digest.update(b"\0")
    digest.update(resolution.task_id.encode("ascii"))
    digest.update(b"\0")
    digest.update(str(resolution.intent_map_revision).encode("ascii"))
    return f"attempt-{digest.hexdigest()}"


def disposition_from_child_result(
        resolution: ChildGoalResolution,
        policy: Optional[ChildResultPolicy] = None,
) -> ChildResultDisposition:
    """Map one validated terminal child result without mutating task state."""
    _validate_resolution(resolution)
    selected_policy = policy or ChildResultPolicy()
    if not isinstance(selected_policy, ChildResultPolicy):
        raise ChildResultPolicyError(
            "policy muss ChildResultPolicy sein")

    attempt = None
    terminates = False
    if resolution.state is ChildGoalResolutionState.COMPLETED:
        state = ChildResultDispositionState.PROGRESSED
        reason = "child_goal_reached_reobserve_frontier"
        attempt = TaskAttempt(
            attempt_id=_attempt_id(resolution),
            task_id=resolution.task_id,
            context=resolution.context,
            map_revision=resolution.intent_map_revision,
            outcome=TaskAttemptOutcome.PROGRESSED,
            reason=reason,
        )
    elif resolution.state is ChildGoalResolutionState.RETRYABLE_FAILURE:
        state = ChildResultDispositionState.RETRY_SCHEDULED
        reason = "child_goal_retryable_failure"
        attempt = TaskAttempt(
            attempt_id=_attempt_id(resolution),
            task_id=resolution.task_id,
            context=resolution.context,
            map_revision=resolution.intent_map_revision,
            outcome=TaskAttemptOutcome.RETRYABLE_FAILURE,
            reason=reason,
            retry_not_before_revision=(
                resolution.intent_map_revision
                + selected_policy.retry_delay_revisions),
        )
    elif resolution.state is ChildGoalResolutionState.TEMPORARILY_BLOCKED:
        state = ChildResultDispositionState.TEMPORARILY_BLOCKED
        reason = "child_goal_local_blocked"
        attempt = TaskAttempt(
            attempt_id=_attempt_id(resolution),
            task_id=resolution.task_id,
            context=resolution.context,
            map_revision=resolution.intent_map_revision,
            outcome=TaskAttemptOutcome.RETRYABLE_FAILURE,
            reason=reason,
            retry_not_before_revision=(
                resolution.intent_map_revision
                + max(2, selected_policy.retry_delay_revisions)),
        )
    elif resolution.state is ChildGoalResolutionState.INVALIDATED:
        state = ChildResultDispositionState.REEVALUATE
        reason = "map_revision_invalidated_child_goal"
    elif resolution.state is ChildGoalResolutionState.ABORTED:
        state = ChildResultDispositionState.ABORTED
        reason = "child_goal_system_abort"
        terminates = True
    else:
        state = ChildResultDispositionState.CANCELED
        reason = "child_goal_canceled"
        terminates = True

    return ChildResultDisposition(
        result_id=resolution.result_id,
        intent_id=resolution.intent_id,
        task_id=resolution.task_id,
        map_revision=resolution.observed_map_revision,
        state=state,
        reason=reason,
        attempt=attempt,
        terminates_exploration=terminates,
    )


def apply_child_result_to_task_policy(
        session: ExplorationTaskPolicySession,
        resolution: ChildGoalResolution,
        policy: Optional[ChildResultPolicy] = None,
) -> Tuple[ChildResultDisposition, Optional[TaskHistorySnapshot]]:
    """Apply only attempt-producing dispositions to the existing owner."""
    if not isinstance(session, ExplorationTaskPolicySession):
        raise ChildResultPolicyError(
            "session muss ExplorationTaskPolicySession sein")
    if not isinstance(resolution, ChildGoalResolution):
        raise ChildResultPolicyError(
            "resolution muss ChildGoalResolution sein")
    if session.context != resolution.context:
        raise ChildResultPolicyError(
            "Policy-Sitzung hat einen fremden Kartenkontext")
    disposition = disposition_from_child_result(
        resolution, policy)
    history = (
        session.record_attempt(disposition.attempt)
        if disposition.attempt is not None else None)
    return disposition, history
