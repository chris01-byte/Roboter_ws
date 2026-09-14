from pathlib import Path
import sys

import pytest


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PACKAGE_ROOT.parents[1]
sys.path.insert(0, str(PACKAGE_ROOT))

from explore.exploration_completion import (  # noqa: E402
    CompletionAssessment,
    ExplorationResultState,
    ReturnResultState,
)
from explore.exploration_migration import (  # noqa: E402
    ExplorationMigrationError,
    LegacyActionTerminalState,
    WE_PASSIVE_STATUS_MAX_BLOCKER_CODES,
    WE_STATUS_SCHEMA_VERSION,
    build_passive_we_status_extension,
    build_unavailable_we_status_extension,
    build_we_status_extension,
    project_completion_for_legacy,
)
from explore.exploration_policy import (  # noqa: E402
    ExplorationPolicyAssessment,
    PolicyAssessmentState,
)
from explore.portal_memory import PortalMapContext  # noqa: E402


def _completion(state):
    return CompletionAssessment(
        state=state,
        reason=f"reason_{state.value}",
        qualifying_observation_count=3 if state is (
            ExplorationResultState.COMPLETE_ACCESSIBLE) else 0,
        required_observation_count=3,
        blocker_codes=() if state is not (
            ExplorationResultState.IN_PROGRESS) else ("open_tasks",),
        map_saved=False,
        return_result=ReturnResultState.FAILED,
        terminal=state is not ExplorationResultState.IN_PROGRESS,
    )


@pytest.mark.parametrize("state,status,terminal,success", [
    (
        ExplorationResultState.IN_PROGRESS,
        "running", LegacyActionTerminalState.NONE, None,
    ),
    (
        ExplorationResultState.COMPLETE_ACCESSIBLE,
        "success", LegacyActionTerminalState.SUCCEEDED, True,
    ),
    (
        ExplorationResultState.PARTIAL,
        "partial", LegacyActionTerminalState.SUCCEEDED, False,
    ),
    (
        ExplorationResultState.ABORTED,
        "failed", LegacyActionTerminalState.ABORTED, False,
    ),
    (
        ExplorationResultState.CANCELED,
        "canceled", LegacyActionTerminalState.CANCELED, False,
    ),
])
def test_legacy_mapping_only_reports_full_completion_as_success(
        state, status, terminal, success):
    result = project_completion_for_legacy(_completion(state))
    assert result.legacy_status_state == status
    assert result.legacy_action_terminal is terminal
    assert result.legacy_action_success is success
    assert result.we_result_state is state
    assert result.map_saved is False
    assert result.return_result is ReturnResultState.FAILED


def test_nested_status_extension_is_versioned_and_keeps_results_separate():
    extension = build_we_status_extension(
        _completion(ExplorationResultState.COMPLETE_ACCESSIBLE))
    assert extension == {
        "schema_version": WE_STATUS_SCHEMA_VERSION,
        "result_state": "complete_accessible",
        "reason": "reason_complete_accessible",
        "terminal": True,
        "qualifying_observation_count": 3,
        "required_observation_count": 3,
        "blocker_codes": [],
        "map_saved": False,
        "return_result": "failed",
    }


def _passive_assessment(blocker_codes=("open_task:task-1:unknown",)):
    return ExplorationPolicyAssessment(
        context=PortalMapContext("session-1", "map-1", "map"),
        source_map_revision=7,
        state=PolicyAssessmentState.WAITING_FOR_TASK_EVIDENCE,
        current_region_id="region-1",
        source_ready=True,
        stale_sources=(),
        open_task_ids=("task-1",),
        current_region_task_ids=("task-1",),
        other_region_task_ids=(),
        eligible_task_ids=(),
        task_assessments=(),
        unresolved_portal_ids=("portal-1",),
        unknown_reachability=("portal-1:a",),
        blocked_reachability=(),
        excluded_reachability=(),
        unentered_region_ids=("region-2",),
        incomplete_region_ids=("region-1", "region-2"),
        blocker_codes=blocker_codes,
        completion_allowed=False,
    )


def test_passive_status_extension_is_bounded_and_never_terminal():
    blockers = tuple(
        f"open_task:task-{index}:unknown"
        for index in range(WE_PASSIVE_STATUS_MAX_BLOCKER_CODES + 2))
    extension = build_passive_we_status_extension(
        _passive_assessment(blockers))

    assert extension["schema_version"] == WE_STATUS_SCHEMA_VERSION
    assert extension["mode"] == "passive_shadow"
    assert extension["result_state"] == "in_progress"
    assert extension["terminal"] is False
    assert extension["completion_allowed"] is False
    assert extension["policy_state"] == "waiting_for_task_evidence"
    assert extension["source"] == {
        "session_id": "session-1",
        "map_id": "map-1",
        "frame_id": "map",
        "map_revision": 7,
        "ready": True,
        "stale_sources": [],
    }
    assert extension["counts"] == {
        "open_tasks": 1,
        "current_region_tasks": 1,
        "other_region_tasks": 0,
        "eligible_tasks": 0,
        "unresolved_portals": 1,
        "unknown_reachability": 1,
        "blocked_reachability": 0,
        "excluded_reachability": 0,
        "unentered_regions": 1,
        "incomplete_regions": 2,
    }
    assert extension["blocker_count"] == len(blockers)
    assert len(extension["blocker_codes"]) == (
        WE_PASSIVE_STATUS_MAX_BLOCKER_CODES)
    assert extension["blocker_codes_truncated"] is True


def test_unavailable_passive_status_is_explicitly_fail_closed():
    extension = build_unavailable_we_status_extension(
        "waiting_for_shadow_snapshot")

    assert extension == {
        "schema_version": WE_STATUS_SCHEMA_VERSION,
        "mode": "passive_shadow",
        "result_state": "in_progress",
        "terminal": False,
        "policy_state": "unavailable",
        "completion_allowed": False,
        "reason": "waiting_for_shadow_snapshot",
        "blocker_count": 1,
        "blocker_codes": ["waiting_for_shadow_snapshot"],
        "blocker_codes_truncated": False,
    }


@pytest.mark.parametrize("value", [None, "assessment", 1])
def test_passive_status_rejects_non_assessments(value):
    with pytest.raises(ExplorationMigrationError):
        build_passive_we_status_extension(value)


def test_explore_area_abi_is_unchanged_during_additive_migration():
    action = (REPOSITORY_ROOT / "src" / "robot_interfaces" / "action"
              / "ExploreArea.action").read_text(encoding="utf-8")
    lines = action.splitlines()
    separators = [index for index, line in enumerate(lines) if line == "---"]
    result_fields = [
        line.split("#", 1)[0].strip()
        for line in lines[separators[0] + 1:separators[1]]
        if line.split("#", 1)[0].strip()
    ]
    assert result_fields == [
        "bool success",
        "string message",
        "int32 frontiers_visited",
        "float32 explored_area_m2",
    ]


def test_bt_is_the_only_production_result_consumer_and_requires_legacy_success():
    header = (REPOSITORY_ROOT / "src" / "bt_orchestrator" / "include"
              / "bt_orchestrator" / "nodes" / "exploration_nodes.hpp")
    source = header.read_text(encoding="utf-8")
    assert "wr.result->success" in source
    assert "ResultCode::SUCCEEDED" in source
    production_hits = []
    for path in (REPOSITORY_ROOT / "src").rglob("*"):
        if not path.is_file() or path.suffix not in {".py", ".cpp", ".hpp"}:
            continue
        if "test" in path.parts or "mock_servers" in path.parts:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if "robot_interfaces::action::ExploreArea" in text:
            production_hits.append(path.relative_to(REPOSITORY_ROOT).as_posix())
    assert production_hits == [
        "src/bt_orchestrator/include/bt_orchestrator/nodes/exploration_nodes.hpp"]


def test_status_consumers_keep_legacy_schema_and_ignore_additive_we_object():
    swift = (REPOSITORY_ROOT / "ios" / "Robotersteuerung"
             / "Robotersteuerung" / "Models"
             / "RobotModels.swift").read_text(encoding="utf-8")
    web = (REPOSITORY_ROOT / "src" / "smartphone_gui" / "web"
           / "app.js").read_text(encoding="utf-8")
    assert "schemaVersion == 1" in swift
    assert 'case mapReadyToSave = "map_ready_to_save"' in swift
    assert "status.schema_version !== 1" in web
    assert "status.map_ready_to_save === true" in web
    assert "wohnungserkundung" not in swift
    assert "wohnungserkundung" not in web
