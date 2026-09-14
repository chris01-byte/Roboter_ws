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
from typing import Optional, Tuple

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
