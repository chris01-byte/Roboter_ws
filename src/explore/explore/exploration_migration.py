"""Pure additive migration from WE-M3 results to legacy explorer contracts.

This module changes no ROS interface.  It defines the conservative mapping a
later opt-in runtime adapter must follow while legacy Action and status
consumers remain deployed.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from .exploration_completion import (
    CompletionAssessment,
    ExplorationResultState,
    ReturnResultState,
)
from .exploration_policy import ExplorationPolicyAssessment


WE_STATUS_SCHEMA_VERSION = 1
WE_PASSIVE_STATUS_MAX_BLOCKER_CODES = 128


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
        max_blocker_codes: int = WE_PASSIVE_STATUS_MAX_BLOCKER_CODES) -> dict:
    """Project one passive assessment without implying a terminal result.

    The bounded summary is safe to attach beneath ``wohnungserkundung`` in the
    legacy status document.  It deliberately contains no pose, path, metric
    goal, navigation request, or motion authorization.
    """
    if not isinstance(assessment, ExplorationPolicyAssessment):
        raise ExplorationMigrationError(
            "assessment muss ExplorationPolicyAssessment sein")
    if (
            isinstance(max_blocker_codes, bool)
            or not isinstance(max_blocker_codes, int)
            or max_blocker_codes <= 0):
        raise ExplorationMigrationError(
            "max_blocker_codes muss eine positive Ganzzahl sein")
    blocker_codes = assessment.blocker_codes[:max_blocker_codes]
    return {
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
    }


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
