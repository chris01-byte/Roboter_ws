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
    LegacyActionTerminalState,
    WE_STATUS_SCHEMA_VERSION,
    build_we_status_extension,
    project_completion_for_legacy,
)


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
