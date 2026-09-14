"""Pure additive migration from WE-M3 results to legacy explorer contracts.

This module changes no ROS interface.  It defines the conservative mapping a
later opt-in runtime adapter must follow while legacy Action and status
consumers remain deployed.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Tuple

from .exploration_completion import (
    CompletionAssessment,
    ExplorationResultState,
    ReturnResultState,
)
from .exploration_policy import (
    ExplorationPolicyAssessment,
    PolicyAssessmentState,
    StatefulPolicyAssessment,
    TaskUtilityScore,
)


WE_STATUS_SCHEMA_VERSION = 1
WE_PASSIVE_STATUS_MAX_BLOCKER_CODES = 128
WE_PASSIVE_STATUS_MAX_TASK_EVIDENCE = 128
WE_PASSIVE_STATUS_MAX_UTILITY_SCORES = 128
WE_PASSIVE_STATUS_MAX_HISTORY = 128
WE_PASSIVE_STATUS_MAX_RETRY_TASKS = 128


class ExplorationMigrationError(ValueError):
    pass


class LegacyActionTerminalState(str, Enum):
    NONE = "none"
    SUCCEEDED = "succeeded"
    ABORTED = "aborted"
    CANCELED = "canceled"


@dataclass(frozen=True)
class LegacyCompletionProjection:
    legacy_status_state: str
    legacy_action_terminal: LegacyActionTerminalState
    legacy_action_success: Optional[bool]
    we_result_state: ExplorationResultState
    reason: str
    map_saved: Optional[bool]
    return_result: ReturnResultState


def project_completion_for_legacy(
        completion: CompletionAssessment) -> LegacyCompletionProjection:
    """Map one WE result without ever weakening legacy success semantics."""
    if not isinstance(completion, CompletionAssessment):
        raise ExplorationMigrationError(
            "completion muss CompletionAssessment sein")
    mapping = {
        ExplorationResultState.IN_PROGRESS: (
            "running", LegacyActionTerminalState.NONE, None),
        ExplorationResultState.COMPLETE_ACCESSIBLE: (
            "success", LegacyActionTerminalState.SUCCEEDED, True),
        ExplorationResultState.PARTIAL: (
            "partial", LegacyActionTerminalState.SUCCEEDED, False),
        ExplorationResultState.ABORTED: (
            "failed", LegacyActionTerminalState.ABORTED, False),
        ExplorationResultState.CANCELED: (
            "canceled", LegacyActionTerminalState.CANCELED, False),
    }
    status, terminal, success = mapping[completion.state]
    return LegacyCompletionProjection(
        legacy_status_state=status,
        legacy_action_terminal=terminal,
        legacy_action_success=success,
        we_result_state=completion.state,
        reason=completion.reason,
        map_saved=completion.map_saved,
        return_result=completion.return_result,
    )


def build_we_status_extension(completion: CompletionAssessment) -> dict:
    """Build the versioned nested object later added to legacy schema 1."""
    projection = project_completion_for_legacy(completion)
    return {
        "schema_version": WE_STATUS_SCHEMA_VERSION,
        "result_state": projection.we_result_state.value,
        "reason": projection.reason,
        "terminal": completion.terminal,
        "qualifying_observation_count": (
            completion.qualifying_observation_count),
        "required_observation_count": completion.required_observation_count,
        "blocker_codes": list(completion.blocker_codes),
        "map_saved": projection.map_saved,
        "return_result": projection.return_result.value,
    }


def build_passive_we_status_extension(
        assessment: ExplorationPolicyAssessment, *,
        utility_scores: Tuple[TaskUtilityScore, ...] = (),
        stateful: Optional[StatefulPolicyAssessment] = None,
        max_blocker_codes: int = WE_PASSIVE_STATUS_MAX_BLOCKER_CODES,
        max_task_evidence: int = WE_PASSIVE_STATUS_MAX_TASK_EVIDENCE,
        max_utility_scores: int = WE_PASSIVE_STATUS_MAX_UTILITY_SCORES,
        max_history: int = WE_PASSIVE_STATUS_MAX_HISTORY,
        max_retry_tasks: int = WE_PASSIVE_STATUS_MAX_RETRY_TASKS,
) -> dict:
    """Project one passive assessment without implying a terminal result.

    The bounded summary is safe to attach beneath ``wohnungserkundung`` in the
    legacy status document.  It deliberately contains no pose, path, metric
    goal, navigation request, or motion authorization.
    """
    if not isinstance(assessment, ExplorationPolicyAssessment):
        raise ExplorationMigrationError(
            "assessment muss ExplorationPolicyAssessment sein")
    for name, value in (
            ("max_blocker_codes", max_blocker_codes),
            ("max_task_evidence", max_task_evidence),
            ("max_utility_scores", max_utility_scores),
            ("max_history", max_history),
            ("max_retry_tasks", max_retry_tasks)):
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise ExplorationMigrationError(
                f"{name} muss eine positive Ganzzahl sein")
    if not isinstance(utility_scores, tuple) or any(
            not isinstance(item, TaskUtilityScore)
            for item in utility_scores):
        raise ExplorationMigrationError(
            "utility_scores muss ein Tupel aus TaskUtilityScore sein")
    utility_ids = [item.task_id for item in utility_scores]
    if len(set(utility_ids)) != len(utility_ids):
        raise ExplorationMigrationError(
            "utility_scores enthaelt doppelte Aufgaben-IDs")
    if set(utility_ids) != set(assessment.eligible_task_ids):
        raise ExplorationMigrationError(
            "utility_scores muss geeignete Aufgaben exakt abdecken")
    if stateful is not None:
        if not isinstance(stateful, StatefulPolicyAssessment):
            raise ExplorationMigrationError(
                "stateful muss StatefulPolicyAssessment sein")
        if (
                stateful.passive.context != assessment.context
                or stateful.passive.source_map_revision
                != assessment.source_map_revision):
            raise ExplorationMigrationError(
                "stateful und passive Bewertung passen nicht zusammen")
        history_ids = [item.task_id for item in stateful.history]
        if len(set(history_ids)) != len(history_ids):
            raise ExplorationMigrationError(
                "stateful.history enthaelt doppelte Aufgaben-IDs")
    blocker_codes = assessment.blocker_codes[:max_blocker_codes]
    task_evidence = assessment.task_assessments[:max_task_evidence]
    bounded_scores = tuple(sorted(
        utility_scores, key=lambda item: item.task_id
    ))[:max_utility_scores]
    extension = {
        "schema_version": WE_STATUS_SCHEMA_VERSION,
        "mode": "passive_shadow",
        "result_state": ExplorationResultState.IN_PROGRESS.value,
        "terminal": False,
        "policy_state": assessment.state.value,
        "completion_allowed": False,
        "source": {
            "session_id": assessment.context.session_id,
            "map_id": assessment.context.map_id,
            "frame_id": assessment.context.frame_id,
            "map_revision": assessment.source_map_revision,
            "ready": assessment.source_ready,
            "stale_sources": list(assessment.stale_sources),
        },
        "current_region_id": assessment.current_region_id,
        "counts": {
            "open_tasks": len(assessment.open_task_ids),
            "current_region_tasks": len(
                assessment.current_region_task_ids),
            "other_region_tasks": len(assessment.other_region_task_ids),
            "eligible_tasks": len(assessment.eligible_task_ids),
            "unresolved_portals": len(assessment.unresolved_portal_ids),
            "unknown_reachability": len(
                assessment.unknown_reachability),
            "blocked_reachability": len(
                assessment.blocked_reachability),
            "excluded_reachability": len(
                assessment.excluded_reachability),
            "unentered_regions": len(assessment.unentered_region_ids),
            "incomplete_regions": len(assessment.incomplete_region_ids),
        },
        "blocker_count": len(assessment.blocker_codes),
        "blocker_codes": list(blocker_codes),
        "blocker_codes_truncated": (
            len(blocker_codes) < len(assessment.blocker_codes)),
        "task_evidence_count": len(assessment.task_assessments),
        "task_evidence": [
            {
                "task_id": item.task_id,
                "region_id": item.region_id,
                "kind": item.kind.value,
                "state": item.state.value,
                "reason": item.reason,
                "recheck_condition": item.recheck_condition,
                "evidence_revision": item.evidence_revision,
                "in_current_region": item.in_current_region,
            }
            for item in task_evidence
        ],
        "task_evidence_truncated": (
            len(task_evidence) < len(assessment.task_assessments)),
        "utility_score_count": len(utility_scores),
        "utility_scores": [
            {
                "task_id": item.task_id,
                "geodesic_path_length_m": item.geodesic_path_length_m,
                "information_gain_square_m": (
                    item.information_gain_square_m),
                "normalized_route_cost": item.normalized_route_cost,
                "normalized_information_gain": (
                    item.normalized_information_gain),
                "score": item.score,
            }
            for item in bounded_scores
        ],
        "utility_scores_truncated": (
            len(bounded_scores) < len(utility_scores)),
    }
    if stateful is not None:
        current_selection = (
            assessment.state is PolicyAssessmentState.READY_WITH_TASKS
            and stateful.selected_task_id is not None
            and stateful.selected_task_id in assessment.eligible_task_ids
        )
        selected_task_id = (
            stateful.selected_task_id if current_selection else None)
        selected_region_id = (
            stateful.selected_region_id if current_selection else None)
        selection_reason = (
            stateful.selection_reason if current_selection
            else (
                stateful.selection_reason
                if stateful.selected_task_id is None
                else "withheld_by_current_passive_policy"
            )
        )
        deferred = stateful.retry_deferred_task_ids[:max_retry_tasks]
        exhausted = stateful.retry_exhausted_task_ids[:max_retry_tasks]
        history = stateful.history[:max_history]
        extension["selection"] = {
            "assessment_revision": (
                stateful.passive.source_map_revision),
            "task_id": selected_task_id,
            "region_id": selected_region_id,
            "reason": selection_reason,
            "current": current_selection,
        }
        extension["retry_deferred_count"] = len(
            stateful.retry_deferred_task_ids)
        extension["retry_deferred_task_ids"] = list(deferred)
        extension["retry_deferred_truncated"] = (
            len(deferred) < len(stateful.retry_deferred_task_ids))
        extension["retry_exhausted_count"] = len(
            stateful.retry_exhausted_task_ids)
        extension["retry_exhausted_task_ids"] = list(exhausted)
        extension["retry_exhausted_truncated"] = (
            len(exhausted) < len(stateful.retry_exhausted_task_ids))
        extension["history_count"] = len(stateful.history)
        extension["history"] = [
            {
                "task_id": item.task_id,
                "region_id": item.region_id,
                "first_seen_revision": item.first_seen_revision,
                "last_seen_revision": item.last_seen_revision,
                "age_revisions": item.age_revisions,
                "last_selected_revision": item.last_selected_revision,
                "selection_count": item.selection_count,
                "last_attempt_revision": item.last_attempt_revision,
                "attempt_count": item.attempt_count,
                "retryable_failure_count": (
                    item.retryable_failure_count),
                "retry_not_before_revision": (
                    item.retry_not_before_revision),
                "last_attempt_reason": item.last_attempt_reason,
                "last_reactivation_revision": (
                    item.last_reactivation_revision),
                "completed": item.completed,
            }
            for item in history
        ]
        extension["history_truncated"] = (
            len(history) < len(stateful.history))
    return extension


def build_unavailable_we_status_extension(reason: str) -> dict:
    """Expose a fail-closed passive adapter state before a source exists."""
    if not isinstance(reason, str) or not reason or len(reason) > 128:
        raise ExplorationMigrationError(
            "reason muss 1 bis 128 Textzeichen enthalten")
    return {
        "schema_version": WE_STATUS_SCHEMA_VERSION,
        "mode": "passive_shadow",
        "result_state": ExplorationResultState.IN_PROGRESS.value,
        "terminal": False,
        "policy_state": "unavailable",
        "completion_allowed": False,
        "reason": reason,
        "blocker_count": 1,
        "blocker_codes": [reason],
        "blocker_codes_truncated": False,
    }
