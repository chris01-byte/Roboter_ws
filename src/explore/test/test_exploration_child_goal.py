from dataclasses import replace
import ast
from pathlib import Path
import sys

import pytest


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE_ROOT))

from explore.exploration_child_goal import (  # noqa: E402
    ChildGoalCancellation,
    ChildGoalCapacityError,
    ChildGoalContractError,
    ChildGoalOutcome,
    ChildGoalPolicy,
    ChildGoalResolutionState,
    ChildGoalResult,
    ChildGoalState,
    ExplorationChildGoalSession,
    ExplorationGoalIntent,
    current_goal_intent_from_assessments,
    goal_intent_from_selection,
)
from explore.exploration_policy import (  # noqa: E402
    ExplorationPolicyAssessment,
    PolicyAssessmentState,
    StatefulPolicyAssessment,
)
from explore.portal_memory import PortalMapContext  # noqa: E402


CONTEXT = PortalMapContext("session-m3j", "map-m3j", "map")


def _passive(revision=7, eligible=("task-1",)):
    return ExplorationPolicyAssessment(
        context=CONTEXT,
        source_map_revision=revision,
        state=(PolicyAssessmentState.READY_WITH_TASKS if eligible
               else PolicyAssessmentState.PARTIAL_CANDIDATE),
        current_region_id="region-1",
        source_ready=True,
        stale_sources=(),
        open_task_ids=eligible,
        current_region_task_ids=eligible,
        other_region_task_ids=(),
        eligible_task_ids=eligible,
        task_assessments=(),
        unresolved_portal_ids=(),
        unknown_reachability=(),
        blocked_reachability=(),
        excluded_reachability=(),
        unentered_region_ids=(),
        incomplete_region_ids=("region-1",),
        blocker_codes=tuple(f"open_task:{item}:eligible" for item in eligible),
        completion_allowed=False,
    )


def _assessment(revision=7, task_id="task-1"):
    passive = _passive(
        revision, () if task_id is None else (task_id,))
    return StatefulPolicyAssessment(
        passive=passive,
        selected_task_id=task_id,
        selected_region_id=("region-1" if task_id is not None else None),
        selection_reason=(
            "current_region" if task_id is not None
            else "no_selectable_task"),
        retry_deferred_task_ids=(),
        retry_exhausted_task_ids=(),
        utility_scores=(),
        history=(),
        blocker_codes=passive.blocker_codes,
        completion_allowed=False,
    )


def _intent(revision=7, task_id="task-1"):
    return ExplorationGoalIntent(
        intent_id=f"intent-{revision}-{task_id}",
        task_id=task_id,
        region_id="region-1",
        context=CONTEXT,
        map_revision=revision,
    )


def _cancel(intent, *, revision=8, invalidates=True, suffix="1"):
    return ChildGoalCancellation(
        cancellation_id=f"cancel-{suffix}",
        intent_id=intent.intent_id,
        context=CONTEXT,
        observed_map_revision=revision,
        reason=("map_revision_changed" if invalidates else "user_requested"),
        invalidates_intent=invalidates,
    )


def _result(intent, outcome=ChildGoalOutcome.SUCCEEDED, *,
            revision=7, suffix="1"):
    return ChildGoalResult(
        result_id=f"result-{suffix}",
        intent_id=intent.intent_id,
        context=CONTEXT,
        observed_map_revision=revision,
        outcome=outcome,
        reason=f"child_{outcome.value}",
    )


def test_selection_derives_stable_id_only_intent():
    assessment = _assessment()

    first = goal_intent_from_selection(assessment)
    replay = goal_intent_from_selection(assessment)

    assert replay == first
    assert first.intent_id.startswith("intent-")
    assert first.task_id == "task-1"
    assert first.region_id == "region-1"
    assert first.map_revision == 7
    assert not hasattr(first, "pose")
    assert not hasattr(first, "path")
    assert goal_intent_from_selection(_assessment(task_id=None)) is None


def test_live_assessment_must_still_agree_before_intent_is_current():
    stateful = _assessment()
    assert current_goal_intent_from_assessments(
        stateful.passive, stateful) == goal_intent_from_selection(stateful)

    stale = replace(
        stateful.passive,
        state=PolicyAssessmentState.WAITING_FOR_FRESH_SOURCES,
        source_ready=False,
        stale_sources=("source_map",),
        eligible_task_ids=(),
    )
    assert current_goal_intent_from_assessments(stale, stateful) is None
    deselected = replace(stateful.passive, eligible_task_ids=())
    assert current_goal_intent_from_assessments(deselected, stateful) is None


def test_live_and_stateful_revision_mismatch_fails_closed():
    stateful = _assessment()
    with pytest.raises(ChildGoalContractError, match="passen nicht"):
        current_goal_intent_from_assessments(
            replace(stateful.passive, source_map_revision=8), stateful)


def test_exact_start_replay_is_idempotent_and_competing_child_is_rejected():
    session = ExplorationChildGoalSession(CONTEXT)
    intent = _intent()

    first = session.start(intent)
    replay = session.start(intent)

    assert first.state is ChildGoalState.ACTIVE
    assert replay == first
    assert first.intent_count == 1
    with pytest.raises(ChildGoalContractError, match="aktive Kindziel"):
        session.start(_intent(task_id="task-2"))


def test_revision_invalidation_downgrades_late_success_and_allows_next_goal():
    session = ExplorationChildGoalSession(CONTEXT)
    intent = _intent()
    session.start(intent)
    cancel = _cancel(intent)

    pending = session.request_cancel(cancel)
    replay = session.request_cancel(cancel)
    resolution = session.finish(_result(
        intent, ChildGoalOutcome.SUCCEEDED, revision=8))

    assert pending.state is ChildGoalState.CANCEL_REQUESTED
    assert replay == pending
    assert resolution.reported_outcome is ChildGoalOutcome.SUCCEEDED
    assert resolution.state is ChildGoalResolutionState.INVALIDATED
    assert resolution.reason == "map_revision_changed"
    assert session.status().state is ChildGoalState.IDLE
    assert session.start(_intent(revision=8)).state is ChildGoalState.ACTIVE


@pytest.mark.parametrize("outcome,expected", [
    (ChildGoalOutcome.SUCCEEDED, ChildGoalResolutionState.COMPLETED),
    (
        ChildGoalOutcome.RETRYABLE_FAILURE,
        ChildGoalResolutionState.RETRYABLE_FAILURE,
    ),
    (ChildGoalOutcome.ABORTED, ChildGoalResolutionState.ABORTED),
    (ChildGoalOutcome.CANCELED, ChildGoalResolutionState.CANCELED),
])
def test_terminal_outcomes_remain_distinct(outcome, expected):
    session = ExplorationChildGoalSession(CONTEXT)
    intent = _intent()
    session.start(intent)

    result = session.finish(_result(intent, outcome))

    assert result.state is expected
    assert session.status().last_resolution == result


def test_noninvalidating_cancel_preserves_canceled_result():
    session = ExplorationChildGoalSession(CONTEXT)
    intent = _intent()
    session.start(intent)
    session.request_cancel(_cancel(
        intent, revision=7, invalidates=False))

    result = session.finish(_result(
        intent, ChildGoalOutcome.CANCELED, revision=7))

    assert result.state is ChildGoalResolutionState.CANCELED
    assert result.reason == "child_canceled"


def test_result_replay_is_idempotent_but_conflict_fails():
    session = ExplorationChildGoalSession(CONTEXT)
    intent = _intent()
    result = _result(intent)
    session.start(intent)
    first = session.finish(result)

    replay = session.finish(result)

    assert replay == replace(first, duplicate=True)
    with pytest.raises(ChildGoalContractError, match="widerspruechlich"):
        session.finish(replace(result, reason="different"))


def test_terminal_start_and_cancel_replays_cannot_mask_current_state():
    session = ExplorationChildGoalSession(CONTEXT)
    first_intent = _intent()
    first_cancel = _cancel(first_intent)
    session.start(first_intent)
    session.request_cancel(first_cancel)
    session.finish(_result(
        first_intent, ChildGoalOutcome.CANCELED, revision=8))

    with pytest.raises(ChildGoalContractError, match="nicht mehr aktiv"):
        session.start(first_intent)
    with pytest.raises(ChildGoalContractError, match="nicht mehr ausstehend"):
        session.request_cancel(first_cancel)

    second_intent = _intent(revision=8)
    session.start(second_intent)
    with pytest.raises(ChildGoalContractError, match="nicht mehr aktiv"):
        session.start(first_intent)
    with pytest.raises(ChildGoalContractError, match="nicht mehr ausstehend"):
        session.request_cancel(first_cancel)
    assert session.status().active_intent == second_intent


def test_stale_foreign_and_wrong_intent_events_fail_closed():
    session = ExplorationChildGoalSession(CONTEXT)
    intent = _intent()
    session.start(intent)
    foreign = PortalMapContext("foreign", "map", "map")

    with pytest.raises(ChildGoalContractError, match="vor der Zielabsicht"):
        session.request_cancel(_cancel(intent, revision=6))
    with pytest.raises(ChildGoalContractError, match="fremden"):
        session.finish(replace(_result(intent), context=foreign))
    with pytest.raises(ChildGoalContractError, match="aktiven"):
        session.finish(replace(
            _result(intent), intent_id="intent-other"))
    assert session.status().state is ChildGoalState.ACTIVE


def test_capacity_is_checked_before_mutation():
    session = ExplorationChildGoalSession(
        CONTEXT, ChildGoalPolicy(max_intents=1))
    first = _intent()
    session.start(first)
    session.finish(_result(first))

    with pytest.raises(ChildGoalCapacityError):
        session.start(_intent(revision=8))

    assert session.status().state is ChildGoalState.IDLE
    assert session.status().intent_count == 1


def test_module_has_no_ros_navigation_motion_or_pose_imports():
    source = (PACKAGE_ROOT / "explore" / "exploration_child_goal.py").read_text(
        encoding="utf-8")
    tree = ast.parse(source)
    imports = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    assert not any(name.startswith("rclpy") for name in imports)
    assert not any(name.startswith("nav2") for name in imports)
    assert not any(name.startswith("geometry_msgs") for name in imports)
    assert "Twist" not in source
    assert "PoseStamped" not in source
