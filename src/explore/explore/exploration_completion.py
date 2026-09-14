"""Pure WE-M3 completion state machine over passive policy assessments.

No clock, ROS interface, planner, goal, command, filesystem, or device is used.
Terminal exploration state, map-save evidence, and return result stay separate.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional, Tuple

from .exploration_policy import (
    PolicyAssessmentState,
    StatefulPolicyAssessment,
)
from .portal_memory import PortalMapContext


class ExplorationCompletionError(ValueError):
    pass


class ExplorationCompletionCapacityError(ExplorationCompletionError):
    pass


class AccessibleScopeState(str, Enum):
    VERIFIED = "verified"
    UNVERIFIED = "unverified"


class ChildNavigationState(str, Enum):
    IDLE = "idle"
    ACTIVE = "active"
    UNKNOWN = "unknown"


class TerminationCause(str, Enum):
    NONE = "none"
    BUDGET_EXHAUSTED = "budget_exhausted"
    SYSTEM_FAILURE = "system_failure"
    USER_CANCELED = "user_canceled"


class ExplorationResultState(str, Enum):
    IN_PROGRESS = "in_progress"
    COMPLETE_ACCESSIBLE = "complete_accessible"
    PARTIAL = "partial"
    ABORTED = "aborted"
    CANCELED = "canceled"


class ReturnResultState(str, Enum):
    NOT_REQUESTED = "not_requested"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELED = "canceled"


@dataclass(frozen=True)
class CompletionPolicy:
    required_fresh_observations: int = 3
    max_observations: int = 4096

    def __post_init__(self) -> None:
        for name in ("required_fresh_observations", "max_observations"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise ExplorationCompletionError(
                    f"{name} muss eine positive Ganzzahl sein")


@dataclass(frozen=True)
class CompletionObservation:
    observation_id: str
    context: PortalMapContext
    map_revision: int
    assessment: StatefulPolicyAssessment
    accessible_scope: AccessibleScopeState
    child_navigation: ChildNavigationState
    termination: TerminationCause
    reason: str
    map_saved: Optional[bool] = None
    return_result: ReturnResultState = ReturnResultState.NOT_REQUESTED

    def __post_init__(self) -> None:
        _identifier(self.observation_id, "observation_id")
        if not isinstance(self.context, PortalMapContext):
            raise ExplorationCompletionError(
                "context muss PortalMapContext sein")
        _revision(self.map_revision)
        if not isinstance(self.assessment, StatefulPolicyAssessment):
            raise ExplorationCompletionError(
                "assessment muss StatefulPolicyAssessment sein")
        if not isinstance(self.accessible_scope, AccessibleScopeState):
            raise ExplorationCompletionError(
                "accessible_scope ist ungueltig")
        if not isinstance(self.child_navigation, ChildNavigationState):
            raise ExplorationCompletionError(
                "child_navigation ist ungueltig")
        if not isinstance(self.termination, TerminationCause):
            raise ExplorationCompletionError("termination ist ungueltig")
        if not isinstance(self.reason, str) or not self.reason.strip() or len(
                self.reason) > 256:
            raise ExplorationCompletionError("reason ist ungueltig")
        if self.map_saved is not None and not isinstance(self.map_saved, bool):
            raise ExplorationCompletionError("map_saved ist ungueltig")
        if not isinstance(self.return_result, ReturnResultState):
            raise ExplorationCompletionError("return_result ist ungueltig")


@dataclass(frozen=True)
class CompletionAssessment:
    state: ExplorationResultState
    reason: str
    qualifying_observation_count: int
    required_observation_count: int
    blocker_codes: Tuple[str, ...]
    map_saved: Optional[bool]
    return_result: ReturnResultState
    terminal: bool


def _identifier(value: object, name: str) -> str:
    if (
            not isinstance(value, str) or not value or len(value) > 128
            or not value.isascii() or not value[0].isalnum()
            or any(not (char.isalnum() or char in "_.:-") for char in value)):
        raise ExplorationCompletionError(f"{name} ist ungueltig")
    return value


def _revision(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ExplorationCompletionError("map_revision ist ungueltig")
    return value


class ExplorationCompletionSession:
    """Require consecutive fresh qualified revisions before completion."""

    def __init__(
            self, context: PortalMapContext,
            policy: Optional[CompletionPolicy] = None) -> None:
        if not isinstance(context, PortalMapContext):
            raise ExplorationCompletionError("context ist ungueltig")
        selected = policy or CompletionPolicy()
        if not isinstance(selected, CompletionPolicy):
            raise ExplorationCompletionError("policy ist ungueltig")
        self._context = context
        self._policy = selected
        self._observations: Dict[str, Tuple[CompletionObservation,
                                            CompletionAssessment]] = {}
        self._latest_revision: Optional[int] = None
        self._qualifying_count = 0
        self._terminal: Optional[CompletionAssessment] = None

    def observe(self, item: CompletionObservation) -> CompletionAssessment:
        if not isinstance(item, CompletionObservation):
            raise ExplorationCompletionError(
                "item muss CompletionObservation sein")
        if item.context != self._context:
            raise ExplorationCompletionError("fremder Kartenkontext")
        previous = self._observations.get(item.observation_id)
        if previous is not None:
            if previous[0] != item:
                raise ExplorationCompletionError(
                    "observation_id wurde widerspruechlich wiederverwendet")
            return previous[1]
        if self._terminal is not None:
            raise ExplorationCompletionError(
                "Terminaler Abschlusszustand ist unveraenderlich")
        if len(self._observations) >= self._policy.max_observations:
            raise ExplorationCompletionCapacityError(
                "Abschlussbeobachtungsverlauf ist voll")
        if self._latest_revision is not None and item.map_revision <= (
                self._latest_revision):
            raise ExplorationCompletionError(
                "Abschlussbeobachtung ist nicht inhaltlich neu")
        passive = item.assessment.passive
        if (
                passive.context != item.context
                or passive.source_map_revision != item.map_revision):
            raise ExplorationCompletionError(
                "Policybewertung und Abschlussbeobachtung sind nicht korreliert")

        if item.termination is TerminationCause.BUDGET_EXHAUSTED:
            result = self._result(
                ExplorationResultState.PARTIAL, item.reason, (), item, True)
        elif item.termination is TerminationCause.SYSTEM_FAILURE:
            result = self._result(
                ExplorationResultState.ABORTED, item.reason, (), item, True)
        elif item.termination is TerminationCause.USER_CANCELED:
            result = self._result(
                ExplorationResultState.CANCELED, item.reason, (), item, True)
        else:
            blockers = self._completion_blockers(item)
            if blockers:
                self._qualifying_count = 0
                result = self._result(
                    ExplorationResultState.IN_PROGRESS,
                    "completion_blocked", blockers, item, False)
            else:
                self._qualifying_count += 1
                complete = self._qualifying_count >= (
                    self._policy.required_fresh_observations)
                result = self._result(
                    ExplorationResultState.COMPLETE_ACCESSIBLE
                    if complete else ExplorationResultState.IN_PROGRESS,
                    "fresh_observation_window_satisfied"
                    if complete else "fresh_observation_window_pending",
                    (), item, complete)

        self._latest_revision = item.map_revision
        self._observations[item.observation_id] = (item, result)
        if result.terminal:
            self._terminal = result
        return result

    def _completion_blockers(
            self, item: CompletionObservation) -> Tuple[str, ...]:
        assessment = item.assessment
        passive = assessment.passive
        blockers = []
        if passive.state is not PolicyAssessmentState.COMPLETION_WINDOW_REQUIRED:
            blockers.append("policy_not_quiescent")
        if assessment.retry_deferred_task_ids:
            blockers.append("retry_deferred_tasks")
        if assessment.retry_exhausted_task_ids:
            blockers.append("retry_exhausted_tasks")
        if item.accessible_scope is not AccessibleScopeState.VERIFIED:
            blockers.append("accessible_scope_unverified")
        if item.child_navigation is ChildNavigationState.ACTIVE:
            blockers.append("child_navigation_active")
        elif item.child_navigation is ChildNavigationState.UNKNOWN:
            blockers.append("child_navigation_unknown")
        return tuple(blockers)

    def _result(
            self, state: ExplorationResultState, reason: str,
            blockers: Tuple[str, ...], item: CompletionObservation,
            terminal: bool) -> CompletionAssessment:
        return CompletionAssessment(
            state=state,
            reason=reason,
            qualifying_observation_count=self._qualifying_count,
            required_observation_count=(
                self._policy.required_fresh_observations),
            blocker_codes=blockers,
            map_saved=item.map_saved,
            return_result=item.return_result,
            terminal=terminal,
        )
