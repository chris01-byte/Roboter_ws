"""Single-child navigation runtime over injected existing orchestration.

The module owns lifecycle semantics, not motion.  A caller supplies the one
existing navigation function and a live revision predicate.  There are no ROS
imports, publishers, action clients, devices, or command topics here.
"""

from dataclasses import dataclass
from enum import Enum
import hashlib
from typing import Callable, Optional

from .child_result_policy import (
    ChildResultDisposition,
    disposition_from_child_result,
)
from .exploration_child_goal import (
    ChildGoalCancellation,
    ChildGoalOutcome,
    ChildGoalResult,
    ExplorationChildGoalSession,
    ExplorationGoalIntent,
)
from .frontier_goal_candidate import FrontierGoalCandidate
from .portal_task_evidence import PortalGoalCandidate
from .portal_memory import PortalMapContext


class ExplorationNavigationRuntimeError(ValueError):
    """The child navigation request or live source state is inconsistent."""


class NavigationStopCause(str, Enum):
    NONE = "none"
    SOURCE_INVALIDATED = "source_invalidated"
    LOCAL_BLOCKED = "local_blocked"
    SYSTEM_FAILURE = "system_failure"
    BUDGET_EXHAUSTED = "budget_exhausted"
    USER_CANCELED = "user_canceled"


@dataclass(frozen=True)
class NavigationSourceState:
    context: PortalMapContext
    map_revision: int
    current: bool

    def __post_init__(self) -> None:
        if not isinstance(self.context, PortalMapContext):
            raise ExplorationNavigationRuntimeError(
                "context muss PortalMapContext sein")
        if (
                isinstance(self.map_revision, bool)
                or not isinstance(self.map_revision, int)
                or self.map_revision < 0):
            raise ExplorationNavigationRuntimeError(
                "map_revision muss nichtnegativ sein")
        if not isinstance(self.current, bool):
            raise ExplorationNavigationRuntimeError(
                "current muss boolesch sein")


@dataclass(frozen=True)
class NavigationChildRun:
    navigation_status: str
    stop_cause: NavigationStopCause
    disposition: ChildResultDisposition


def _event_id(prefix: str, intent_id: str) -> str:
    digest = hashlib.sha256()
    digest.update(prefix.encode("ascii"))
    digest.update(b"\0")
    digest.update(intent_id.encode("ascii"))
    return f"{prefix}-{digest.hexdigest()}"


class ExplorationNavigationSession:
    """Execute at most one child at a time through an injected Nav2 owner."""

    _KNOWN_STATUSES = {
        "success", "aborted", "rejected", "timeout", "canceled",
        "cancel_failed", "error",
    }

    def __init__(self, context: PortalMapContext) -> None:
        if not isinstance(context, PortalMapContext):
            raise ExplorationNavigationRuntimeError(
                "context muss PortalMapContext sein")
        self._context = context
        self._children = ExplorationChildGoalSession(context)

    @property
    def context(self) -> PortalMapContext:
        return self._context

    @property
    def child_status(self):
        return self._children.status()

    def run(
            self,
            intent: ExplorationGoalIntent,
            candidate,
            navigate: Callable[[object, Callable[[], bool]], str],
            source_state: Callable[[], NavigationSourceState],
            user_canceled: Callable[[], bool],
            budget_exhausted: Callable[[], bool],
            local_blocked: Optional[Callable[[object], bool]] = None,
    ) -> NavigationChildRun:
        if not isinstance(intent, ExplorationGoalIntent):
            raise ExplorationNavigationRuntimeError(
                "intent muss ExplorationGoalIntent sein")
        if not isinstance(candidate, (FrontierGoalCandidate, PortalGoalCandidate)):
            raise ExplorationNavigationRuntimeError(
                "candidate muss ein unterstuetzter Zielkandidat sein")
        if (
                intent.context != self._context
                or candidate.intent_id != intent.intent_id
                or candidate.task_id != intent.task_id
                or candidate.region_id != intent.region_id
                or candidate.map_revision != intent.map_revision
                or candidate.frame_id != intent.context.frame_id):
            raise ExplorationNavigationRuntimeError(
                "Zielkandidat passt nicht zur aktiven Zielabsicht")
        for callback, name in (
                (navigate, "navigate"),
                (source_state, "source_state"),
                (user_canceled, "user_canceled"),
                (budget_exhausted, "budget_exhausted")):
            if not callable(callback):
                raise ExplorationNavigationRuntimeError(
                    f"{name} muss aufrufbar sein")
        if local_blocked is not None and not callable(local_blocked):
            raise ExplorationNavigationRuntimeError(
                "local_blocked muss aufrufbar sein")

        initial_source = source_state()
        self._validate_source(initial_source, intent)
        if not initial_source.current:
            raise ExplorationNavigationRuntimeError(
                "Zielquelle ist bereits vor Versand veraltet")
        if user_canceled() or budget_exhausted():
            raise ExplorationNavigationRuntimeError(
                "Kindziel darf nach Stopanforderung nicht starten")
        self._children.start(intent)

        def should_stop() -> bool:
            return (
                user_canceled()
                or budget_exhausted()
                or not self._current_source(source_state(), intent)
            )

        try:
            navigation_status = navigate(candidate, should_stop)
        except Exception:
            navigation_status = "error"
        if navigation_status not in self._KNOWN_STATUSES:
            navigation_status = "error"
        final_source = source_state()
        if not isinstance(final_source, NavigationSourceState):
            raise ExplorationNavigationRuntimeError(
                "source_state muss NavigationSourceState liefern")

        stop_cause = NavigationStopCause.NONE
        invalidates = False
        if user_canceled():
            stop_cause = NavigationStopCause.USER_CANCELED
        elif budget_exhausted():
            stop_cause = NavigationStopCause.BUDGET_EXHAUSTED
        elif not self._current_source(final_source, intent):
            stop_cause = NavigationStopCause.SOURCE_INVALIDATED
            invalidates = True
        elif (navigation_status in {"aborted", "timeout", "rejected"}
              and local_blocked is not None):
            # Humble NavigateToPose exposes no detailed abort code.  Only a
            # caller with positive, fresh obstruction evidence may downgrade
            # this terminal action to ordinary local blockage.  Missing or
            # faulty evidence remains a system failure, never a recovery cue.
            try:
                obstruction_proven = (
                    navigation_status != "rejected"
                    and local_blocked(candidate) is True)
            except Exception:
                obstruction_proven = False
            stop_cause = (
                NavigationStopCause.LOCAL_BLOCKED if obstruction_proven
                else NavigationStopCause.SYSTEM_FAILURE)

        if stop_cause is not NavigationStopCause.NONE:
            cancellation = ChildGoalCancellation(
                cancellation_id=_event_id("cancel", intent.intent_id),
                intent_id=intent.intent_id,
                context=self._context,
                observed_map_revision=max(
                    intent.map_revision, final_source.map_revision),
                reason=stop_cause.value,
                invalidates_intent=invalidates,
            )
            self._children.request_cancel(cancellation)

        outcome = {
            "success": ChildGoalOutcome.SUCCEEDED,
            "aborted": ChildGoalOutcome.RETRYABLE_FAILURE,
            "rejected": ChildGoalOutcome.RETRYABLE_FAILURE,
            "timeout": ChildGoalOutcome.RETRYABLE_FAILURE,
            "canceled": ChildGoalOutcome.CANCELED,
            "cancel_failed": ChildGoalOutcome.ABORTED,
            "error": ChildGoalOutcome.ABORTED,
        }[navigation_status]
        if stop_cause in {
                NavigationStopCause.USER_CANCELED,
                NavigationStopCause.BUDGET_EXHAUSTED}:
            outcome = ChildGoalOutcome.CANCELED
        elif stop_cause is NavigationStopCause.LOCAL_BLOCKED:
            outcome = ChildGoalOutcome.LOCAL_BLOCKED
        elif stop_cause is NavigationStopCause.SYSTEM_FAILURE:
            outcome = ChildGoalOutcome.ABORTED
        result = ChildGoalResult(
            result_id=_event_id("result", intent.intent_id),
            intent_id=intent.intent_id,
            context=self._context,
            observed_map_revision=(
                max(intent.map_revision, final_source.map_revision)
                if invalidates else intent.map_revision),
            outcome=outcome,
            reason=f"navigation_{navigation_status}",
        )
        resolution = self._children.finish(result)
        return NavigationChildRun(
            navigation_status=navigation_status,
            stop_cause=stop_cause,
            disposition=disposition_from_child_result(resolution),
        )

    def _validate_source(
            self, source: NavigationSourceState,
            intent: ExplorationGoalIntent) -> None:
        if not isinstance(source, NavigationSourceState):
            raise ExplorationNavigationRuntimeError(
                "source_state muss NavigationSourceState liefern")
        if source.context != intent.context:
            raise ExplorationNavigationRuntimeError(
                "Zielquelle wechselte den Kartenkontext")

    @staticmethod
    def _current_source(
            source: NavigationSourceState,
            intent: ExplorationGoalIntent) -> bool:
        return (
            source.current
            and source.context == intent.context
            and source.map_revision >= intent.map_revision)
