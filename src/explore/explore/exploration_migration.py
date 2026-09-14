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


WE_STATUS_SCHEMA_VERSION = 1


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
