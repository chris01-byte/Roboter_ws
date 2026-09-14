"""Pure single-child lifecycle for revision-bound exploration intentions.

The contract owns identifiers and transitions only.  It contains no metric
pose, path, ROS action, planner, command topic, clock, or motion authority.
"""

from dataclasses import dataclass, replace
from enum import Enum
import hashlib
import re
from typing import Dict, Optional, Tuple

from .exploration_policy import StatefulPolicyAssessment
from .portal_memory import PortalMapContext


_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")


class ChildGoalContractError(ValueError):
    """An intention or child transition is invalid or contradictory."""


class ChildGoalCapacityError(ChildGoalContractError):
    """A configured hard lifecycle bound would be exceeded."""


class ChildGoalState(str, Enum):
    IDLE = "idle"
    ACTIVE = "active"
    CANCEL_REQUESTED = "cancel_requested"


class ChildGoalOutcome(str, Enum):
    SUCCEEDED = "succeeded"
    RETRYABLE_FAILURE = "retryable_failure"
    ABORTED = "aborted"
    CANCELED = "canceled"


class ChildGoalResolutionState(str, Enum):
    COMPLETED = "completed"
    RETRYABLE_FAILURE = "retryable_failure"
    ABORTED = "aborted"
    CANCELED = "canceled"
    INVALIDATED = "invalidated"


@dataclass(frozen=True)
class ChildGoalPolicy:
    max_intents: int = 4096
    max_cancellations: int = 4096
    max_results: int = 4096

    def __post_init__(self) -> None:
        for name in ("max_intents", "max_cancellations", "max_results"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise ChildGoalContractError(
                    f"{name} muss eine positive Ganzzahl sein")


@dataclass(frozen=True)
class ExplorationGoalIntent:
    intent_id: str
    task_id: str
    region_id: str
    context: PortalMapContext
    map_revision: int

    def __post_init__(self) -> None:
        _identifier(self.intent_id, "intent_id")
        _identifier(self.task_id, "task_id")
        _identifier(self.region_id, "region_id")
        if not isinstance(self.context, PortalMapContext):
            raise ChildGoalContractError(
                "context muss PortalMapContext sein")
        _revision(self.map_revision, "map_revision")


@dataclass(frozen=True)
class ChildGoalCancellation:
    cancellation_id: str
    intent_id: str
    context: PortalMapContext
    observed_map_revision: int
    reason: str
    invalidates_intent: bool

    def __post_init__(self) -> None:
        _identifier(self.cancellation_id, "cancellation_id")
        _identifier(self.intent_id, "intent_id")
        if not isinstance(self.context, PortalMapContext):
            raise ChildGoalContractError(
                "context muss PortalMapContext sein")
        _revision(self.observed_map_revision, "observed_map_revision")
        _text(self.reason, "reason")
        if not isinstance(self.invalidates_intent, bool):
            raise ChildGoalContractError(
                "invalidates_intent muss boolesch sein")


@dataclass(frozen=True)
class ChildGoalResult:
    result_id: str
    intent_id: str
    context: PortalMapContext
    observed_map_revision: int
    outcome: ChildGoalOutcome
    reason: str

    def __post_init__(self) -> None:
        _identifier(self.result_id, "result_id")
        _identifier(self.intent_id, "intent_id")
        if not isinstance(self.context, PortalMapContext):
            raise ChildGoalContractError(
                "context muss PortalMapContext sein")
        _revision(self.observed_map_revision, "observed_map_revision")
        if not isinstance(self.outcome, ChildGoalOutcome):
            raise ChildGoalContractError(
                "outcome muss ChildGoalOutcome sein")
        _text(self.reason, "reason")


@dataclass(frozen=True)
class ChildGoalResolution:
    result_id: str
    intent_id: str
    task_id: str
    intent_map_revision: int
    observed_map_revision: int
    reported_outcome: ChildGoalOutcome
    state: ChildGoalResolutionState
    reason: str
    duplicate: bool = False


@dataclass(frozen=True)
class ChildGoalStatus:
    context: PortalMapContext
    state: ChildGoalState
    active_intent: Optional[ExplorationGoalIntent]
    pending_cancellation: Optional[ChildGoalCancellation]
    last_resolution: Optional[ChildGoalResolution]
    intent_count: int
    cancellation_count: int
    result_count: int


def _identifier(value: object, name: str) -> str:
    if not isinstance(value, str) or _IDENTIFIER.fullmatch(value) is None:
        raise ChildGoalContractError(
            f"{name} muss 1 bis 128 sichere ASCII-Zeichen enthalten")
    return value


def _revision(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ChildGoalContractError(
            f"{name} muss eine nichtnegative Ganzzahl sein")
    return value


def _text(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > 256:
        raise ChildGoalContractError(
            f"{name} muss 1 bis 256 Textzeichen enthalten")
    return value


def goal_intent_from_selection(
        assessment: StatefulPolicyAssessment,
) -> Optional[ExplorationGoalIntent]:
    """Derive a deterministic ID-only intent from a current selection."""
    if not isinstance(assessment, StatefulPolicyAssessment):
        raise ChildGoalContractError(
            "assessment muss StatefulPolicyAssessment sein")
    if assessment.completion_allowed:
        raise ChildGoalContractError(
            "Auswahl darf keine Abschlussfreigabe tragen")
    if assessment.selected_task_id is None:
        if assessment.selected_region_id is not None:
            raise ChildGoalContractError(
                "Region ohne ausgewaehlte Aufgabe ist ungueltig")
        return None
    if assessment.selected_region_id is None:
        raise ChildGoalContractError(
            "Ausgewaehlte Aufgabe braucht eine Region")
    if assessment.selected_task_id not in assessment.passive.eligible_task_ids:
        raise ChildGoalContractError(
            "Ausgewaehlte Aufgabe ist nicht geeignet")
    digest = hashlib.sha256()
    digest.update(b"we-goal-intent-v1\0")
    digest.update(assessment.passive.context.session_id.encode("ascii"))
    digest.update(b"\0")
    digest.update(assessment.passive.context.map_id.encode("ascii"))
    digest.update(b"\0")
    digest.update(assessment.passive.context.frame_id.encode("ascii"))
    digest.update(b"\0")
    digest.update(str(
        assessment.passive.source_map_revision).encode("ascii"))
    digest.update(b"\0")
    digest.update(assessment.selected_task_id.encode("ascii"))
    digest.update(b"\0")
    digest.update(assessment.selected_region_id.encode("ascii"))
    return ExplorationGoalIntent(
        intent_id=f"intent-{digest.hexdigest()}",
        task_id=assessment.selected_task_id,
        region_id=assessment.selected_region_id,
        context=assessment.passive.context,
        map_revision=assessment.passive.source_map_revision,
    )


class ExplorationChildGoalSession:
    """Bounded owner that never permits two concurrent child intentions."""

    def __init__(
            self, context: PortalMapContext,
            policy: Optional[ChildGoalPolicy] = None) -> None:
        if not isinstance(context, PortalMapContext):
            raise ChildGoalContractError(
                "context muss PortalMapContext sein")
        selected_policy = policy or ChildGoalPolicy()
        if not isinstance(selected_policy, ChildGoalPolicy):
            raise ChildGoalContractError(
                "policy muss ChildGoalPolicy sein")
        self._context = context
        self._policy = selected_policy
        self._intents: Dict[str, ExplorationGoalIntent] = {}
        self._cancellations: Dict[str, ChildGoalCancellation] = {}
        self._results: Dict[
            str, Tuple[ChildGoalResult, ChildGoalResolution]] = {}
        self._active_intent: Optional[ExplorationGoalIntent] = None
        self._pending_cancellation: Optional[ChildGoalCancellation] = None
        self._last_resolution: Optional[ChildGoalResolution] = None

    @property
    def context(self) -> PortalMapContext:
        return self._context

    def status(self) -> ChildGoalStatus:
        state = ChildGoalState.IDLE
        if self._active_intent is not None:
            state = (
                ChildGoalState.CANCEL_REQUESTED
                if self._pending_cancellation is not None
                else ChildGoalState.ACTIVE)
        return ChildGoalStatus(
            context=self._context,
            state=state,
            active_intent=self._active_intent,
            pending_cancellation=self._pending_cancellation,
            last_resolution=self._last_resolution,
            intent_count=len(self._intents),
            cancellation_count=len(self._cancellations),
            result_count=len(self._results),
        )

    def start(self, intent: ExplorationGoalIntent) -> ChildGoalStatus:
        if not isinstance(intent, ExplorationGoalIntent):
            raise ChildGoalContractError(
                "intent muss ExplorationGoalIntent sein")
        self._require_context(intent.context)
        previous = self._intents.get(intent.intent_id)
        if previous is not None:
            if previous != intent:
                raise ChildGoalContractError(
                    "intent_id wurde widerspruechlich wiederverwendet")
            if self._active_intent != intent:
                raise ChildGoalContractError(
                    "Zielabsicht ist nicht mehr aktiv")
            return self.status()
        if self._active_intent is not None:
            raise ChildGoalContractError(
                "Vor neuer Zielabsicht muss das aktive Kindziel enden")
        if len(self._intents) >= self._policy.max_intents:
            raise ChildGoalCapacityError("Zielabsichtsverlauf ist voll")
        self._intents[intent.intent_id] = intent
        self._active_intent = intent
        self._pending_cancellation = None
        return self.status()

    def request_cancel(
            self, cancellation: ChildGoalCancellation,
    ) -> ChildGoalStatus:
        if not isinstance(cancellation, ChildGoalCancellation):
            raise ChildGoalContractError(
                "cancellation muss ChildGoalCancellation sein")
        self._require_context(cancellation.context)
        previous = self._cancellations.get(
            cancellation.cancellation_id)
        if previous is not None:
            if previous != cancellation:
                raise ChildGoalContractError(
                    "cancellation_id wurde widerspruechlich "
                    "wiederverwendet")
            if (
                    self._active_intent is None
                    or self._active_intent.intent_id != cancellation.intent_id
                    or self._pending_cancellation != cancellation):
                raise ChildGoalContractError(
                    "Cancelanforderung ist nicht mehr ausstehend")
            return self.status()
        active = self._require_active(cancellation.intent_id)
        if cancellation.observed_map_revision < active.map_revision:
            raise ChildGoalContractError(
                "Cancelbeobachtung liegt vor der Zielabsicht")
        if self._pending_cancellation is not None:
            raise ChildGoalContractError(
                "Aktives Kindziel besitzt bereits eine andere "
                "Cancelanforderung")
        if len(self._cancellations) >= self._policy.max_cancellations:
            raise ChildGoalCapacityError("Cancelverlauf ist voll")
        self._cancellations[cancellation.cancellation_id] = cancellation
        self._pending_cancellation = cancellation
        return self.status()

    def finish(self, result: ChildGoalResult) -> ChildGoalResolution:
        if not isinstance(result, ChildGoalResult):
            raise ChildGoalContractError(
                "result muss ChildGoalResult sein")
        self._require_context(result.context)
        previous = self._results.get(result.result_id)
        if previous is not None:
            if previous[0] != result:
                raise ChildGoalContractError(
                    "result_id wurde widerspruechlich wiederverwendet")
            return replace(previous[1], duplicate=True)
        active = self._require_active(result.intent_id)
        if result.observed_map_revision < active.map_revision:
            raise ChildGoalContractError(
                "Kindresultat liegt vor der Zielabsicht")
        if len(self._results) >= self._policy.max_results:
            raise ChildGoalCapacityError("Kindresultatverlauf ist voll")

        cancellation = self._pending_cancellation
        if cancellation is not None and cancellation.invalidates_intent:
            state = ChildGoalResolutionState.INVALIDATED
            reason = cancellation.reason
        else:
            state = {
                ChildGoalOutcome.SUCCEEDED: (
                    ChildGoalResolutionState.COMPLETED),
                ChildGoalOutcome.RETRYABLE_FAILURE: (
                    ChildGoalResolutionState.RETRYABLE_FAILURE),
                ChildGoalOutcome.ABORTED: ChildGoalResolutionState.ABORTED,
                ChildGoalOutcome.CANCELED: ChildGoalResolutionState.CANCELED,
            }[result.outcome]
            reason = result.reason
        resolution = ChildGoalResolution(
            result_id=result.result_id,
            intent_id=active.intent_id,
            task_id=active.task_id,
            intent_map_revision=active.map_revision,
            observed_map_revision=result.observed_map_revision,
            reported_outcome=result.outcome,
            state=state,
            reason=reason,
        )
        self._results[result.result_id] = (result, resolution)
        self._last_resolution = resolution
        self._active_intent = None
        self._pending_cancellation = None
        return resolution

    def _require_context(self, context: PortalMapContext) -> None:
        if context != self._context:
            raise ChildGoalContractError(
                "Kindzielereignis hat einen fremden Kartenkontext")

    def _require_active(self, intent_id: str) -> ExplorationGoalIntent:
        active = self._active_intent
        if active is None or active.intent_id != intent_id:
            raise ChildGoalContractError(
                "Kindzielereignis passt nicht zur aktiven Zielabsicht")
        return active
