"""Pure, fail-closed WE-M3 exploration-policy contract.

The policy evaluates immutable passive snapshots and externally supplied task
availability evidence.  It does not read a clock, create metric goals, call a
planner, own ROS interfaces, or authorize motion.  In this first WE-M3 step it
can only identify work, waiting states, and completion *candidates*; it can
never report ``complete_accessible``.
"""

from dataclasses import dataclass, field
from enum import Enum
import math
from typing import Dict, Optional, Tuple

from .portal_memory import (
    PortalConfirmationState,
    PortalMapContext,
    ReachabilityState,
)
from .region_graph import (
    RegionExplorationState,
    RegionTaskKind,
    RegionTaskState,
)
from .region_graph_status import (
    ShadowStatusError,
    ShadowStatusPolicy,
    ShadowStatusSource,
    validate_shadow_status_source,
)


class ExplorationPolicyError(ValueError):
    """The passive inputs cannot form one trustworthy policy assessment."""


class ExplorationPolicyCapacityError(ExplorationPolicyError):
    """A configured hard policy bound would be exceeded."""


class TaskAvailabilityState(str, Enum):
    """Externally established status; never a permission to move."""

    AVAILABLE = "available"
    FILTERED = "filtered"
    TEMPORARILY_BLOCKED = "temporarily_blocked"
    UNKNOWN = "unknown"
    EXCLUDED = "excluded"


class PolicyTaskState(str, Enum):
    """Normalized task status in one policy assessment."""

    ELIGIBLE = "eligible"
    FILTERED = "filtered"
    TEMPORARILY_BLOCKED = "temporarily_blocked"
    UNKNOWN = "unknown"
    EXCLUDED = "excluded"
    STALE_EVIDENCE = "stale_evidence"


class PolicyAssessmentState(str, Enum):
    """Non-terminal result of WE-M3/A's passive assessment."""

    WAITING_FOR_FRESH_SOURCES = "waiting_for_fresh_sources"
    READY_WITH_TASKS = "ready_with_tasks"
    WAITING_FOR_TASK_EVIDENCE = "waiting_for_task_evidence"
    PARTIAL_CANDIDATE = "partial_candidate"
    COMPLETION_WINDOW_REQUIRED = "completion_window_required"


@dataclass(frozen=True)
class TaskAvailability:
    """Revision-bound evidence about one open task.

    ``AVAILABLE`` means only that a later selector may consider the task.  It
    is not a goal, path, safety verdict, or drive authorization.
    """

    task_id: str
    context: PortalMapContext
    map_revision: int
    state: TaskAvailabilityState
    reason: str
    recheck_condition: str

    def __post_init__(self) -> None:
        _identifier(self.task_id, "task_id")
        if not isinstance(self.context, PortalMapContext):
            raise ExplorationPolicyError(
                "context muss PortalMapContext sein")
        _revision(self.map_revision, "map_revision")
        if not isinstance(self.state, TaskAvailabilityState):
            raise ExplorationPolicyError(
                "state muss TaskAvailabilityState sein")
        _text(self.reason, "reason")
        _text(self.recheck_condition, "recheck_condition")


@dataclass(frozen=True)
class ExplorationPolicyConfig:
    """Synthetic software bounds, not hardware or acceptance thresholds."""

    source_policy: ShadowStatusPolicy = field(
        default_factory=ShadowStatusPolicy)
    maximum_task_evidence_revision_lag: int = 1
    max_task_availability: int = 4096

    def __post_init__(self) -> None:
        if not isinstance(self.source_policy, ShadowStatusPolicy):
            raise ExplorationPolicyError(
                "source_policy muss ShadowStatusPolicy sein")
        _revision(
            self.maximum_task_evidence_revision_lag,
            "maximum_task_evidence_revision_lag",
        )
        if (
                isinstance(self.max_task_availability, bool)
                or not isinstance(self.max_task_availability, int)
                or self.max_task_availability <= 0):
            raise ExplorationPolicyError(
                "max_task_availability muss eine positive Ganzzahl sein")


@dataclass(frozen=True)
class PolicyTaskAssessment:
    task_id: str
    region_id: str
    kind: RegionTaskKind
    state: PolicyTaskState
    reason: str
    recheck_condition: str
    evidence_revision: Optional[int]
    in_current_region: bool


@dataclass(frozen=True)
class ExplorationPolicyAssessment:
    """Explainable passive result with no navigation output."""

    context: PortalMapContext
    source_map_revision: int
    state: PolicyAssessmentState
    current_region_id: Optional[str]
    source_ready: bool
    stale_sources: Tuple[str, ...]
    open_task_ids: Tuple[str, ...]
    current_region_task_ids: Tuple[str, ...]
    other_region_task_ids: Tuple[str, ...]
    eligible_task_ids: Tuple[str, ...]
    task_assessments: Tuple[PolicyTaskAssessment, ...]
    unresolved_portal_ids: Tuple[str, ...]
    unknown_reachability: Tuple[str, ...]
    blocked_reachability: Tuple[str, ...]
    excluded_reachability: Tuple[str, ...]
    unentered_region_ids: Tuple[str, ...]
    incomplete_region_ids: Tuple[str, ...]
    blocker_codes: Tuple[str, ...]
    completion_allowed: bool = False


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
        raise ExplorationPolicyError(
            f"{name} muss 1 bis 128 sichere ASCII-Zeichen enthalten")
    return value


def _revision(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ExplorationPolicyError(
            f"{name} muss eine nichtnegative Ganzzahl sein")
    return value


def _text(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > 256:
        raise ExplorationPolicyError(
            f"{name} muss 1 bis 256 Textzeichen enthalten")
    return value


def _source_is_fresh(
        revision: Optional[int], age_seconds: Optional[float],
        current_revision: int, maximum_revision_lag: int,
        maximum_age_seconds: float) -> bool:
    if revision is None or age_seconds is None:
        return False
    if revision > current_revision:
        raise ExplorationPolicyError(
            "Quellrevision liegt vor der aktuellen Kartenrevision")
    if not math.isfinite(age_seconds) or age_seconds < 0.0:
        raise ExplorationPolicyError("Quellalter ist ungueltig")
    return (
        current_revision - revision <= maximum_revision_lag
        and age_seconds <= maximum_age_seconds
    )


def _stale_sources(
        source: ShadowStatusSource,
        policy: ShadowStatusPolicy) -> Tuple[str, ...]:
    checks = (
        (
            "source_map", source.source_map_revision,
            source.source_map_age_seconds,
            policy.maximum_source_map_age_seconds,
        ),
        (
            "portal_memory", source.portal_memory_revision,
            source.portal_memory_age_seconds,
            policy.maximum_portal_memory_age_seconds,
        ),
        (
            "region_graph", source.graph.latest_revision,
            source.region_graph_age_seconds,
            policy.maximum_region_graph_age_seconds,
        ),
    )
    return tuple(
        name for name, revision, age_seconds, maximum_age_seconds in checks
        if not _source_is_fresh(
            revision,
            age_seconds,
            source.source_map_revision,
            policy.maximum_revision_lag,
            maximum_age_seconds,
        )
    )


def _reachability_key(item: object) -> str:
    return f"{item.portal_id}:{item.side.value}"


def _task_state(
        availability: Optional[TaskAvailability], source_revision: int,
        maximum_lag: int) -> Tuple[PolicyTaskState, str, str, Optional[int]]:
    if availability is None:
        return (
            PolicyTaskState.UNKNOWN,
            "missing_task_availability",
            "supply_revision_bound_task_availability",
            None,
        )
    if availability.map_revision > source_revision:
        raise ExplorationPolicyError(
            "Aufgabenevidenz liegt vor der aktuellen Kartenrevision")
    if source_revision - availability.map_revision > maximum_lag:
        return (
            PolicyTaskState.STALE_EVIDENCE,
            "stale_task_availability",
            "reassess_on_current_map_revision",
            availability.map_revision,
        )
    normalized = {
        TaskAvailabilityState.AVAILABLE: PolicyTaskState.ELIGIBLE,
        TaskAvailabilityState.FILTERED: PolicyTaskState.FILTERED,
        TaskAvailabilityState.TEMPORARILY_BLOCKED: (
            PolicyTaskState.TEMPORARILY_BLOCKED),
        TaskAvailabilityState.UNKNOWN: PolicyTaskState.UNKNOWN,
        TaskAvailabilityState.EXCLUDED: PolicyTaskState.EXCLUDED,
    }[availability.state]
    return (
        normalized,
        availability.reason,
        availability.recheck_condition,
        availability.map_revision,
    )


def assess_exploration_policy(
        source: ShadowStatusSource,
        task_availability: Tuple[TaskAvailability, ...] = (),
        config: Optional[ExplorationPolicyConfig] = None,
) -> ExplorationPolicyAssessment:
    """Assess one snapshot without selecting or creating a navigation goal."""
    selected_config = config or ExplorationPolicyConfig()
    if not isinstance(selected_config, ExplorationPolicyConfig):
        raise ExplorationPolicyError(
            "config muss ExplorationPolicyConfig sein")
    if not isinstance(task_availability, tuple) or any(
            not isinstance(item, TaskAvailability)
            for item in task_availability):
        raise ExplorationPolicyError(
            "task_availability muss ein Tupel aus TaskAvailability sein")
    if len(task_availability) > selected_config.max_task_availability:
        raise ExplorationPolicyCapacityError(
            "Aufgabenevidenz ueberschreitet die Policygrenze")

    try:
        validate_shadow_status_source(source, selected_config.source_policy)
    except ShadowStatusError as exc:
        raise ExplorationPolicyError(str(exc)) from exc

    evidence_ids = [item.task_id for item in task_availability]
    if len(set(evidence_ids)) != len(evidence_ids):
        raise ExplorationPolicyError(
            "Aufgabenevidenz enthaelt doppelte Aufgaben-IDs")
    graph_tasks = {task.task_id: task for task in source.graph.tasks}
    unknown_ids = sorted(set(evidence_ids) - set(graph_tasks))
    if unknown_ids:
        raise ExplorationPolicyError(
            "Aufgabenevidenz verweist auf unbekannte Aufgabe")
    if any(item.context != source.context for item in task_availability):
        raise ExplorationPolicyError(
            "Aufgabenevidenz und Snapshot haben verschiedene Kontexte")
    if any(
            graph_tasks[item.task_id].state is not RegionTaskState.OPEN
            for item in task_availability):
        raise ExplorationPolicyError(
            "Aufgabenevidenz darf nur offene Aufgaben referenzieren")

    availability_by_task = {
        item.task_id: item for item in task_availability}
    open_tasks = tuple(
        task for task in source.graph.tasks
        if task.state is RegionTaskState.OPEN
    )
    current_region_id = source.graph.current_region_id
    assessments = []
    for task in open_tasks:
        state, reason, recheck, evidence_revision = _task_state(
            availability_by_task.get(task.task_id),
            source.source_map_revision,
            selected_config.maximum_task_evidence_revision_lag,
        )
        assessments.append(PolicyTaskAssessment(
            task_id=task.task_id,
            region_id=task.region_id,
            kind=task.kind,
            state=state,
            reason=reason,
            recheck_condition=recheck,
            evidence_revision=evidence_revision,
            in_current_region=(task.region_id == current_region_id),
        ))
    assessments.sort(key=lambda item: item.task_id)

    current_tasks = tuple(sorted(
        item.task_id for item in assessments if item.in_current_region))
    other_tasks = tuple(
        item.task_id for item in sorted(
            (item for item in assessments if not item.in_current_region),
            key=lambda item: (item.region_id, item.task_id),
        )
    )
    eligible_set = {
        item.task_id for item in assessments
        if item.state is PolicyTaskState.ELIGIBLE}
    eligible = tuple(
        task_id for task_id in current_tasks + other_tasks
        if task_id in eligible_set
    )

    stale_sources = _stale_sources(source, selected_config.source_policy)
    unresolved_portals = tuple(sorted(
        portal.portal_id for portal in source.portals
        if portal.confirmation_state is not PortalConfirmationState.CONFIRMED
    ))
    unknown_reachability = tuple(sorted(
        _reachability_key(item) for item in source.reachability
        if item.state is ReachabilityState.UNKNOWN
    ))
    blocked_reachability = tuple(sorted(
        _reachability_key(item) for item in source.reachability
        if item.state is ReachabilityState.TEMPORARILY_BLOCKED
    ))
    excluded_reachability = tuple(sorted(
        _reachability_key(item) for item in source.reachability
        if item.state is ReachabilityState.EXCLUDED
    ))
    unentered_regions = tuple(sorted(
        region.region_id for region in source.graph.regions
        if not region.entered
    ))
    incomplete_regions = tuple(sorted(
        region.region_id for region in source.graph.regions
        if region.exploration_state is not (
            RegionExplorationState.COMPLETE_CANDIDATE)
    ))

    blocker_codes = []
    blocker_codes.extend(
        f"stale_source:{name}" for name in stale_sources)
    blocker_codes.extend(
        f"open_task:{item.task_id}:{item.state.value}"
        for item in assessments)
    blocker_codes.extend(
        f"unresolved_portal:{portal_id}"
        for portal_id in unresolved_portals)
    blocker_codes.extend(
        f"unknown_reachability:{key}" for key in unknown_reachability)
    blocker_codes.extend(
        f"blocked_reachability:{key}" for key in blocked_reachability)
    blocker_codes.extend(
        f"excluded_reachability:{key}" for key in excluded_reachability)
    blocker_codes.extend(
        f"unentered_region:{region_id}" for region_id in unentered_regions)
    blocker_codes.extend(
        f"incomplete_region:{region_id}" for region_id in incomplete_regions)
    if current_region_id is None:
        blocker_codes.append("missing_current_region")

    uncertain_task_evidence = any(
        item.state in (
            PolicyTaskState.UNKNOWN,
            PolicyTaskState.STALE_EVIDENCE,
        )
        for item in assessments
    )
    if stale_sources:
        state = PolicyAssessmentState.WAITING_FOR_FRESH_SOURCES
    elif eligible:
        state = PolicyAssessmentState.READY_WITH_TASKS
    elif assessments and uncertain_task_evidence:
        state = PolicyAssessmentState.WAITING_FOR_TASK_EVIDENCE
    elif assessments or blocker_codes:
        state = PolicyAssessmentState.PARTIAL_CANDIDATE
    else:
        state = PolicyAssessmentState.COMPLETION_WINDOW_REQUIRED

    if not blocker_codes:
        blocker_codes.extend((
            "fresh_observation_window_required",
            "accessible_scope_required",
            "child_navigation_state_required",
        ))

    return ExplorationPolicyAssessment(
        context=source.context,
        source_map_revision=source.source_map_revision,
        state=state,
        current_region_id=current_region_id,
        source_ready=not stale_sources,
        stale_sources=stale_sources,
        open_task_ids=tuple(sorted(
            task.task_id for task in open_tasks)),
        current_region_task_ids=current_tasks,
        other_region_task_ids=other_tasks,
        eligible_task_ids=eligible,
        task_assessments=tuple(assessments),
        unresolved_portal_ids=unresolved_portals,
        unknown_reachability=unknown_reachability,
        blocked_reachability=blocked_reachability,
        excluded_reachability=excluded_reachability,
        unentered_region_ids=unentered_regions,
        incomplete_region_ids=incomplete_regions,
        blocker_codes=tuple(blocker_codes),
        completion_allowed=False,
    )


class TaskAttemptOutcome(str, Enum):
    """External attempt evidence without any motion-success inference."""

    PROGRESSED = "progressed"
    RETRYABLE_FAILURE = "retryable_failure"


@dataclass(frozen=True)
class TaskAttempt:
    attempt_id: str
    task_id: str
    context: PortalMapContext
    map_revision: int
    outcome: TaskAttemptOutcome
    reason: str
    retry_not_before_revision: Optional[int] = None

    def __post_init__(self) -> None:
        _identifier(self.attempt_id, "attempt_id")
        _identifier(self.task_id, "task_id")
        if not isinstance(self.context, PortalMapContext):
            raise ExplorationPolicyError(
                "context muss PortalMapContext sein")
        _revision(self.map_revision, "map_revision")
        if not isinstance(self.outcome, TaskAttemptOutcome):
            raise ExplorationPolicyError(
                "outcome muss TaskAttemptOutcome sein")
        _text(self.reason, "reason")
        if self.outcome is TaskAttemptOutcome.RETRYABLE_FAILURE:
            retry_revision = _revision(
                self.retry_not_before_revision,
                "retry_not_before_revision",
            )
            if retry_revision <= self.map_revision:
                raise ExplorationPolicyError(
                    "Retryrevision muss nach dem Fehlversuch liegen")
        elif self.retry_not_before_revision is not None:
            raise ExplorationPolicyError(
                "Fortschritt darf keine Retryrevision setzen")


@dataclass(frozen=True)
class TaskReactivation:
    reactivation_id: str
    task_id: str
    context: PortalMapContext
    map_revision: int
    reason: str

    def __post_init__(self) -> None:
        _identifier(self.reactivation_id, "reactivation_id")
        _identifier(self.task_id, "task_id")
        if not isinstance(self.context, PortalMapContext):
            raise ExplorationPolicyError(
                "context muss PortalMapContext sein")
        _revision(self.map_revision, "map_revision")
        _text(self.reason, "reason")


@dataclass(frozen=True)
class TaskHistoryPolicy:
    """Bounded revision thresholds, not timing or hardware limits."""

    assessment_config: ExplorationPolicyConfig = field(
        default_factory=ExplorationPolicyConfig)
    maximum_retryable_failures: int = 3
    minimum_region_hold_revisions: int = 2
    starvation_revision_threshold: int = 8
    max_tracked_tasks: int = 4096
    max_attempts: int = 8192
    max_reactivations: int = 4096

    def __post_init__(self) -> None:
        if not isinstance(
                self.assessment_config, ExplorationPolicyConfig):
            raise ExplorationPolicyError(
                "assessment_config muss ExplorationPolicyConfig sein")
        for name in (
                "maximum_retryable_failures",
                "minimum_region_hold_revisions",
                "starvation_revision_threshold",
                "max_tracked_tasks", "max_attempts", "max_reactivations"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise ExplorationPolicyError(
                    f"{name} muss eine positive Ganzzahl sein")


@dataclass(frozen=True)
class TaskHistorySnapshot:
    task_id: str
    region_id: str
    first_seen_revision: int
    last_seen_revision: int
    age_revisions: int
    last_selected_revision: Optional[int]
    selection_count: int
    last_attempt_revision: Optional[int]
    attempt_count: int
    retryable_failure_count: int
    retry_not_before_revision: Optional[int]
    last_attempt_reason: Optional[str]
    last_reactivation_revision: Optional[int]
    completed: bool


@dataclass(frozen=True)
class StatefulPolicyAssessment:
    passive: ExplorationPolicyAssessment
    selected_task_id: Optional[str]
    selected_region_id: Optional[str]
    selection_reason: str
    retry_deferred_task_ids: Tuple[str, ...]
    retry_exhausted_task_ids: Tuple[str, ...]
    utility_scores: Tuple["TaskUtilityScore", ...]
    history: Tuple[TaskHistorySnapshot, ...]
    blocker_codes: Tuple[str, ...]
    completion_allowed: bool = False


@dataclass
class _TaskHistoryState:
    task_id: str
    region_id: str
    first_seen_revision: int
    last_seen_revision: int
    last_selected_revision: Optional[int] = None
    selection_count: int = 0
    last_attempt_revision: Optional[int] = None
    attempt_count: int = 0
    retryable_failure_count: int = 0
    retry_not_before_revision: Optional[int] = None
    last_attempt_reason: Optional[str] = None
    last_reactivation_revision: Optional[int] = None
    completed: bool = False


@dataclass(frozen=True)
class TaskUtilityEvidence:
    """Planner-independent scalar evidence; contains no pose or path."""

    task_id: str
    context: PortalMapContext
    map_revision: int
    geodesic_path_length_m: float
    information_gain_square_m: float

    def __post_init__(self) -> None:
        _identifier(self.task_id, "task_id")
        if not isinstance(self.context, PortalMapContext):
            raise ExplorationPolicyError(
                "context muss PortalMapContext sein")
        _revision(self.map_revision, "map_revision")
        _finite_nonnegative(
            self.geodesic_path_length_m, "geodesic_path_length_m")
        _finite_nonnegative(
            self.information_gain_square_m,
            "information_gain_square_m",
        )


@dataclass(frozen=True)
class TaskScoringPolicy:
    """Visible synthetic normalization and weights for ID-only scoring."""

    route_normalization_m: float = 20.0
    information_normalization_square_m: float = 10.0
    route_weight: float = 0.4
    information_weight: float = 0.6
    max_evidence: int = 4096

    def __post_init__(self) -> None:
        for name in (
                "route_normalization_m",
                "information_normalization_square_m"):
            if _finite_nonnegative(getattr(self, name), name) <= 0.0:
                raise ExplorationPolicyError(f"{name} muss positiv sein")
        for name in ("route_weight", "information_weight"):
            _finite_nonnegative(getattr(self, name), name)
        if self.route_weight + self.information_weight <= 0.0:
            raise ExplorationPolicyError(
                "Mindestens ein Bewertungsgewicht muss positiv sein")
        if (
                isinstance(self.max_evidence, bool)
                or not isinstance(self.max_evidence, int)
                or self.max_evidence <= 0):
            raise ExplorationPolicyError(
                "max_evidence muss eine positive Ganzzahl sein")


@dataclass(frozen=True)
class TaskUtilityScore:
    task_id: str
    geodesic_path_length_m: float
    information_gain_square_m: float
    normalized_route_cost: float
    normalized_information_gain: float
    score: float


def _finite_nonnegative(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ExplorationPolicyError(
            f"{name} muss eine nichtnegative endliche Zahl sein")
    normalized = float(value)
    if not math.isfinite(normalized) or normalized < 0.0:
        raise ExplorationPolicyError(
            f"{name} muss eine nichtnegative endliche Zahl sein")
    return normalized


def score_task_utilities(
        task_ids: Tuple[str, ...],
        evidence: Tuple[TaskUtilityEvidence, ...],
        source_revision: int,
        policy: Optional[TaskScoringPolicy] = None,
) -> Tuple[TaskUtilityScore, ...]:
    """Return canonical bounded scalar scores for exactly the given IDs."""
    selected_policy = policy or TaskScoringPolicy()
    if not isinstance(selected_policy, TaskScoringPolicy):
        raise ExplorationPolicyError("policy muss TaskScoringPolicy sein")
    if not isinstance(task_ids, tuple):
        raise ExplorationPolicyError("task_ids muss ein Tupel sein")
    for task_id in task_ids:
        _identifier(task_id, "task_id")
    if len(set(task_ids)) != len(task_ids):
        raise ExplorationPolicyError("task_ids enthaelt Duplikate")
    if not isinstance(evidence, tuple) or any(
            not isinstance(item, TaskUtilityEvidence) for item in evidence):
        raise ExplorationPolicyError(
            "evidence muss ein Tupel aus TaskUtilityEvidence sein")
    if len(evidence) > selected_policy.max_evidence:
        raise ExplorationPolicyCapacityError(
            "Bewertungsevidenz ueberschreitet die Policygrenze")
    evidence_ids = [item.task_id for item in evidence]
    if len(set(evidence_ids)) != len(evidence_ids):
        raise ExplorationPolicyError(
            "Bewertungsevidenz enthaelt doppelte Aufgaben-IDs")
    if set(evidence_ids) != set(task_ids):
        raise ExplorationPolicyError(
            "Bewertungsevidenz muss den Kandidatenbestand exakt abdecken")
    if any(item.map_revision != source_revision for item in evidence):
        raise ExplorationPolicyError(
            "Bewertungsevidenz gehoert nicht zur aktuellen Kartenrevision")

    total_weight = (
        selected_policy.route_weight + selected_policy.information_weight)
    scores = []
    for item in evidence:
        route = min(
            float(item.geodesic_path_length_m)
            / selected_policy.route_normalization_m,
            1.0,
        )
        information = min(
            float(item.information_gain_square_m)
            / selected_policy.information_normalization_square_m,
            1.0,
        )
        score = (
            selected_policy.route_weight * (1.0 - route)
            + selected_policy.information_weight * information
        ) / total_weight
        scores.append(TaskUtilityScore(
            task_id=item.task_id,
            geodesic_path_length_m=float(item.geodesic_path_length_m),
            information_gain_square_m=float(
                item.information_gain_square_m),
            normalized_route_cost=route,
            normalized_information_gain=information,
            score=score,
        ))
    return tuple(sorted(scores, key=lambda item: item.task_id))


class ExplorationTaskPolicySession:
    """Revision-driven task history and ID-only hierarchical selection."""

    def __init__(
            self, context: PortalMapContext,
            policy: Optional[TaskHistoryPolicy] = None) -> None:
        if not isinstance(context, PortalMapContext):
            raise ExplorationPolicyError(
                "context muss PortalMapContext sein")
        selected_policy = policy or TaskHistoryPolicy()
        if not isinstance(selected_policy, TaskHistoryPolicy):
            raise ExplorationPolicyError(
                "policy muss TaskHistoryPolicy sein")
        self._context = context
        self._policy = selected_policy
        self._tasks: Dict[str, _TaskHistoryState] = {}
        self._attempts: Dict[str, TaskAttempt] = {}
        self._reactivations: Dict[str, TaskReactivation] = {}
        self._last_request = None
        self._last_result: Optional[StatefulPolicyAssessment] = None
        self._latest_assessment_revision: Optional[int] = None
        self._active_region_id: Optional[str] = None
        self._active_region_since_revision: Optional[int] = None

    @property
    def context(self) -> PortalMapContext:
        return self._context

    @property
    def latest_assessment_revision(self) -> Optional[int]:
        return self._latest_assessment_revision

    def history(self) -> Tuple[TaskHistorySnapshot, ...]:
        return tuple(
            self._snapshot(self._tasks[task_id])
            for task_id in sorted(self._tasks)
        )

    def record_attempt(self, attempt: TaskAttempt) -> TaskHistorySnapshot:
        if not isinstance(attempt, TaskAttempt):
            raise ExplorationPolicyError("attempt muss TaskAttempt sein")
        self._require_context(attempt.context)
        previous = self._attempts.get(attempt.attempt_id)
        if previous is not None:
            if previous != attempt:
                raise ExplorationPolicyError(
                    "attempt_id wurde widerspruechlich wiederverwendet")
            return self._snapshot(self._tasks[attempt.task_id])
        task = self._require_task(attempt.task_id)
        self._require_event_revision(attempt.map_revision, task)
        if task.completed:
            raise ExplorationPolicyError(
                "Erledigte Aufgabe darf keinen Versuch erhalten")
        if self._is_retry_deferred(task, attempt.map_revision):
            raise ExplorationPolicyError(
                "Aufgabe ist bis zur Retryrevision zurueckgestellt")
        if (
                task.retryable_failure_count
                >= self._policy.maximum_retryable_failures):
            raise ExplorationPolicyError(
                "Retrybudget ist ohne Reaktivierung erschoepft")
        if len(self._attempts) >= self._policy.max_attempts:
            raise ExplorationPolicyCapacityError(
                "Versuchsverlauf ist voll")

        task.last_attempt_revision = attempt.map_revision
        task.attempt_count += 1
        task.last_attempt_reason = attempt.reason
        if attempt.outcome is TaskAttemptOutcome.RETRYABLE_FAILURE:
            task.retryable_failure_count += 1
            task.retry_not_before_revision = (
                attempt.retry_not_before_revision)
        else:
            task.retry_not_before_revision = None
        self._attempts[attempt.attempt_id] = attempt
        self._clear_assessment_replay()
        return self._snapshot(task)

    def reactivate(
            self, reactivation: TaskReactivation) -> TaskHistorySnapshot:
        if not isinstance(reactivation, TaskReactivation):
            raise ExplorationPolicyError(
                "reactivation muss TaskReactivation sein")
        self._require_context(reactivation.context)
        previous = self._reactivations.get(reactivation.reactivation_id)
        if previous is not None:
            if previous != reactivation:
                raise ExplorationPolicyError(
                    "reactivation_id wurde widerspruechlich wiederverwendet")
            return self._snapshot(self._tasks[reactivation.task_id])
        task = self._require_task(reactivation.task_id)
        self._require_event_revision(reactivation.map_revision, task)
        if task.completed:
            raise ExplorationPolicyError(
                "Erledigte Aufgabe darf nicht reaktiviert werden")
        if len(self._reactivations) >= self._policy.max_reactivations:
            raise ExplorationPolicyCapacityError(
                "Reaktivierungsverlauf ist voll")

        task.retryable_failure_count = 0
        task.retry_not_before_revision = None
        task.last_reactivation_revision = reactivation.map_revision
        self._reactivations[reactivation.reactivation_id] = reactivation
        self._clear_assessment_replay()
        return self._snapshot(task)

    def assess(
            self, source: ShadowStatusSource,
            task_availability: Tuple[TaskAvailability, ...] = (),
            task_utilities: Tuple[TaskUtilityEvidence, ...] = (),
            scoring_policy: Optional[TaskScoringPolicy] = None,
    ) -> StatefulPolicyAssessment:
        if not isinstance(source, ShadowStatusSource):
            raise ExplorationPolicyError(
                "source muss ShadowStatusSource sein")
        self._require_context(source.context)
        revision = source.source_map_revision
        request = (
            source, task_availability, task_utilities, scoring_policy)
        if self._latest_assessment_revision is not None:
            if revision < self._latest_assessment_revision:
                raise ExplorationPolicyError(
                    "Policy-Snapshot ist aelter als der letzte Stand")
            if revision == self._latest_assessment_revision:
                if request != self._last_request or self._last_result is None:
                    raise ExplorationPolicyError(
                        "Kartenrevision wurde widerspruechlich neu bewertet")
                return self._last_result

        passive = assess_exploration_policy(
            source,
            task_availability,
            self._policy.assessment_config,
        )
        self._observe_tasks(source)

        eligible = set(passive.eligible_task_ids)
        retry_deferred = tuple(sorted(
            task_id for task_id in eligible
            if self._is_retry_deferred(self._tasks[task_id], revision)
        ))
        retry_exhausted = tuple(sorted(
            task_id for task_id in eligible
            if self._tasks[task_id].retryable_failure_count
            >= self._policy.maximum_retryable_failures
        ))
        selectable = (
            eligible - set(retry_deferred) - set(retry_exhausted)
            if passive.state is PolicyAssessmentState.READY_WITH_TASKS
            else set()
        )
        utility_scores = ()
        if task_utilities:
            if not isinstance(task_utilities, tuple) or any(
                    not isinstance(item, TaskUtilityEvidence)
                    for item in task_utilities):
                raise ExplorationPolicyError(
                    "task_utilities muss TaskUtilityEvidence enthalten")
            if any(item.context != self._context for item in task_utilities):
                raise ExplorationPolicyError(
                    "Bewertungsevidenz hat einen fremden Kartenkontext")
            utilities_by_task = {
                item.task_id: item for item in task_utilities}
            if len(utilities_by_task) != len(task_utilities):
                raise ExplorationPolicyError(
                    "Bewertungsevidenz enthaelt doppelte Aufgaben-IDs")
            if set(utilities_by_task) != eligible:
                raise ExplorationPolicyError(
                    "Bewertungsevidenz muss den geeigneten Bestand exakt "
                    "abdecken")
            utility_scores = score_task_utilities(
                tuple(sorted(selectable)),
                tuple(
                    utilities_by_task[task_id]
                    for task_id in sorted(selectable)),
                revision,
                scoring_policy,
            )
        elif scoring_policy is not None:
            raise ExplorationPolicyError(
                "scoring_policy ohne Bewertungsevidenz ist ungueltig")
        score_by_task = {
            item.task_id: item.score for item in utility_scores}
        selected_task_id, reason = self._select_task(
            selectable, source, revision, score_by_task)
        selected_region_id = (
            self._tasks[selected_task_id].region_id
            if selected_task_id is not None else None)
        if selected_task_id is not None:
            selected_task = self._tasks[selected_task_id]
            selected_task.last_selected_revision = revision
            selected_task.selection_count += 1
        if selected_region_id is not None and (
                selected_region_id != self._active_region_id):
            self._active_region_id = selected_region_id
            self._active_region_since_revision = revision

        blocker_codes = list(passive.blocker_codes)
        blocker_codes.extend(
            f"retry_deferred:{task_id}" for task_id in retry_deferred)
        blocker_codes.extend(
            f"retry_exhausted:{task_id}" for task_id in retry_exhausted)
        result = StatefulPolicyAssessment(
            passive=passive,
            selected_task_id=selected_task_id,
            selected_region_id=selected_region_id,
            selection_reason=reason,
            retry_deferred_task_ids=retry_deferred,
            retry_exhausted_task_ids=retry_exhausted,
            utility_scores=utility_scores,
            history=self.history(),
            blocker_codes=tuple(blocker_codes),
            completion_allowed=False,
        )
        self._latest_assessment_revision = revision
        self._last_request = request
        self._last_result = result
        return result

    def _observe_tasks(self, source: ShadowStatusSource) -> None:
        new_tasks = [
            task for task in source.graph.tasks
            if task.task_id not in self._tasks]
        if len(self._tasks) + len(new_tasks) > self._policy.max_tracked_tasks:
            raise ExplorationPolicyCapacityError(
                "Aufgabenverlauf ist voll")
        for task in source.graph.tasks:
            state = self._tasks.get(task.task_id)
            if state is None:
                state = _TaskHistoryState(
                    task_id=task.task_id,
                    region_id=task.region_id,
                    first_seen_revision=task.created_revision,
                    last_seen_revision=source.source_map_revision,
                )
                self._tasks[task.task_id] = state
            elif state.region_id != task.region_id:
                state.region_id = task.region_id
            state.last_seen_revision = source.source_map_revision
            state.completed = task.state is RegionTaskState.COMPLETED

    def _select_task(
            self, selectable: set, source: ShadowStatusSource,
            revision: int,
            score_by_task: Dict[str, float],
    ) -> Tuple[Optional[str], str]:
        if not selectable or not source.graph.current_region_id:
            return None, "no_selectable_task"
        ordered = sorted(
            selectable,
            key=lambda task_id: (
                -score_by_task.get(task_id, 0.0),
                self._tasks[task_id].first_seen_revision,
                task_id,
            ),
        )
        if (
                self._active_region_id is not None
                and self._active_region_since_revision is not None
                and revision - self._active_region_since_revision
                < self._policy.minimum_region_hold_revisions):
            held = [
                task_id for task_id in ordered
                if self._tasks[task_id].region_id == self._active_region_id]
            if held:
                return held[0], "region_hysteresis"

        starved = sorted(
            (
                task_id for task_id in ordered
                if revision - (
                    self._tasks[task_id].last_selected_revision
                    if self._tasks[task_id].last_selected_revision is not None
                    else self._tasks[task_id].first_seen_revision)
                >= self._policy.starvation_revision_threshold
            ),
            key=lambda task_id: (
                self._tasks[task_id].last_selected_revision
                if self._tasks[task_id].last_selected_revision is not None
                else self._tasks[task_id].first_seen_revision,
                -score_by_task.get(task_id, 0.0),
                task_id,
            ),
        )
        if starved:
            return starved[0], "starvation_prevention"

        current = [
            task_id for task_id in ordered
            if self._tasks[task_id].region_id
            == source.graph.current_region_id]
        if current:
            return current[0], "current_region"
        return ordered[0], "oldest_available_task"

    def _require_context(self, context: PortalMapContext) -> None:
        if context != self._context:
            raise ExplorationPolicyError(
                "Policy-Ereignis hat einen fremden Kartenkontext")

    def _require_task(self, task_id: str) -> _TaskHistoryState:
        try:
            return self._tasks[task_id]
        except KeyError as exc:
            raise ExplorationPolicyError(
                "Policy-Ereignis verweist auf unbekannte Aufgabe") from exc

    def _require_event_revision(
            self, revision: int, task: _TaskHistoryState) -> None:
        if (
                self._latest_assessment_revision is None
                or revision != self._latest_assessment_revision
                or revision != task.last_seen_revision
                or (
                    task.last_attempt_revision is not None
                    and revision < task.last_attempt_revision)):
            raise ExplorationPolicyError(
                "Policy-Ereignis gehoert nicht zum aktuellen Snapshot")

    def _is_retry_deferred(
            self, task: _TaskHistoryState, revision: int) -> bool:
        return (
            task.retry_not_before_revision is not None
            and revision < task.retry_not_before_revision
        )

    def _clear_assessment_replay(self) -> None:
        self._last_request = None
        self._last_result = None

    @staticmethod
    def _snapshot(task: _TaskHistoryState) -> TaskHistorySnapshot:
        return TaskHistorySnapshot(
            task_id=task.task_id,
            region_id=task.region_id,
            first_seen_revision=task.first_seen_revision,
            last_seen_revision=task.last_seen_revision,
            age_revisions=(
                task.last_seen_revision - task.first_seen_revision),
            last_selected_revision=task.last_selected_revision,
            selection_count=task.selection_count,
            last_attempt_revision=task.last_attempt_revision,
            attempt_count=task.attempt_count,
            retryable_failure_count=task.retryable_failure_count,
            retry_not_before_revision=task.retry_not_before_revision,
            last_attempt_reason=task.last_attempt_reason,
            last_reactivation_revision=task.last_reactivation_revision,
            completed=task.completed,
        )
