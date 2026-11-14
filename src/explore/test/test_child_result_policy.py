from dataclasses import replace
import ast
from pathlib import Path
import sys

import pytest


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE_ROOT))

from explore.child_result_policy import (  # noqa: E402
    ChildResultDispositionState,
    ChildResultPolicy,
    ChildResultPolicyError,
    apply_child_result_to_task_policy,
    disposition_from_child_result,
)
from explore.exploration_child_goal import (  # noqa: E402
    ChildGoalCancellation,
    ChildGoalOutcome,
    ChildGoalResolutionState,
    ChildGoalResult,
    ExplorationChildGoalSession,
    ExplorationGoalIntent,
)
from explore.exploration_policy import (  # noqa: E402
    ExplorationTaskPolicySession,
    TaskAttemptOutcome,
    TaskAvailability,
    TaskAvailabilityState,
)
from explore.portal_memory import PortalMapContext  # noqa: E402
from explore.region_graph import (  # noqa: E402
    RegionGraph,
    RegionSeed,
    RegionTaskKind,
    RegionTaskState,
    RegionTaskUpdate,
)
from explore.region_graph_status import ShadowStatusSource  # noqa: E402


CONTEXT = PortalMapContext("session-m3l", "map-m3l", "map")


def _source(revision=7):
    graph = RegionGraph(CONTEXT)
    region = graph.start(RegionSeed("start", CONTEXT, 0))
    graph.update_task(RegionTaskUpdate(
        update_id="task-open",
        task_id="task-frontier_000001",
        context=CONTEXT,
        map_revision=7,
        region_id=region.region_id,
        kind=RegionTaskKind.FRONTIER,
        subject_id="frontier_000001",
        state=RegionTaskState.OPEN,
    ))
    snapshot = graph.snapshot()
    if revision != snapshot.latest_revision:
        snapshot = replace(snapshot, latest_revision=revision)
    return ShadowStatusSource(
        context=CONTEXT,
        source_map_revision=revision,
        portal_memory_revision=revision,
        graph=snapshot,
        portals=(),
        reachability=(),
        source_map_age_seconds=0.1,
        portal_memory_age_seconds=0.1,
        region_graph_age_seconds=0.1,
    )


def _availability(revision=7):
    return TaskAvailability(
        task_id="task-frontier_000001",
        context=CONTEXT,
        map_revision=revision,
        state=TaskAvailabilityState.AVAILABLE,
        reason="raw_map_route_available",
        recheck_condition="revalidate_before_navigation",
    )


def _policy_session():
    session = ExplorationTaskPolicySession(CONTEXT)
    assessment = session.assess(_source(), (_availability(),))
    assert assessment.selected_task_id == "task-frontier_000001"
    return session


def _resolution(outcome, *, invalidated=False):
    intent = ExplorationGoalIntent(
        intent_id="intent-7-task-frontier_000001",
        task_id="task-frontier_000001",
        region_id="region_000001",
        context=CONTEXT,
        map_revision=7,
    )
    child = ExplorationChildGoalSession(CONTEXT)
    child.start(intent)
    revision = 7
    if invalidated:
        revision = 8
        child.request_cancel(ChildGoalCancellation(
            cancellation_id="cancel-revision-8",
            intent_id=intent.intent_id,
            context=CONTEXT,
            observed_map_revision=revision,
            reason="map_revision_changed",
            invalidates_intent=True,
        ))
    return child.finish(ChildGoalResult(
        result_id=f"result-{outcome.value}",
        intent_id=intent.intent_id,
        context=CONTEXT,
        observed_map_revision=revision,
        outcome=outcome,
        reason=f"child_{outcome.value}",
    ))


def test_success_records_progress_attempt_but_never_completes_task():
    task_policy = _policy_session()
    resolution = _resolution(ChildGoalOutcome.SUCCEEDED)

    disposition, history = apply_child_result_to_task_policy(
        task_policy, resolution)
    replay_disposition, replay_history = apply_child_result_to_task_policy(
        task_policy, replace(resolution, duplicate=True))

    assert disposition.state is ChildResultDispositionState.PROGRESSED
    assert disposition.terminates_exploration is False
    assert disposition.attempt.outcome is TaskAttemptOutcome.PROGRESSED
    assert history.attempt_count == 1
    assert history.completed is False
    assert replay_disposition.attempt == disposition.attempt
    assert replay_history == history
    assert task_policy.history()[0].attempt_count == 1


def test_retryable_failure_records_bounded_revision_delay():
    task_policy = _policy_session()
    resolution = _resolution(ChildGoalOutcome.RETRYABLE_FAILURE)

    disposition, history = apply_child_result_to_task_policy(
        task_policy,
        resolution,
        ChildResultPolicy(retry_delay_revisions=2),
    )

    assert disposition.state is ChildResultDispositionState.RETRY_SCHEDULED
    assert disposition.terminates_exploration is False
    assert disposition.attempt.outcome is TaskAttemptOutcome.RETRYABLE_FAILURE
    assert disposition.attempt.retry_not_before_revision == 9
    assert history.retryable_failure_count == 1
    assert history.completed is False

    deferred = task_policy.assess(_source(8), (_availability(8),))
    assert deferred.selected_task_id is None
    assert deferred.retry_deferred_task_ids == ("task-frontier_000001",)
    eligible = task_policy.assess(_source(9), (_availability(9),))
    assert eligible.selected_task_id == "task-frontier_000001"


def test_local_blockage_defers_task_then_allows_fresh_reassessment():
    task_policy = _policy_session()
    disposition, history = apply_child_result_to_task_policy(
        task_policy, _resolution(ChildGoalOutcome.LOCAL_BLOCKED))

    assert disposition.state is (
        ChildResultDispositionState.TEMPORARILY_BLOCKED)
    assert disposition.terminates_exploration is False
    assert disposition.attempt.retry_not_before_revision == 9
    assert history.retryable_failure_count == 1
    deferred = task_policy.assess(_source(8), (_availability(8),))
    assert deferred.selected_task_id is None
    restored = task_policy.assess(_source(9), (_availability(9),))
    assert restored.selected_task_id == "task-frontier_000001"


def test_invalidated_result_requests_reevaluation_without_attempt():
    task_policy = _policy_session()
    resolution = _resolution(
        ChildGoalOutcome.SUCCEEDED, invalidated=True)
    before = task_policy.history()

    disposition, history = apply_child_result_to_task_policy(
        task_policy, resolution)

    assert resolution.state is ChildGoalResolutionState.INVALIDATED
    assert disposition.state is ChildResultDispositionState.REEVALUATE
    assert disposition.map_revision == 8
    assert disposition.attempt is None
    assert disposition.terminates_exploration is False
    assert history is None
    assert task_policy.history() == before


@pytest.mark.parametrize("outcome,state", [
    (ChildGoalOutcome.ABORTED, ChildResultDispositionState.ABORTED),
    (ChildGoalOutcome.CANCELED, ChildResultDispositionState.CANCELED),
])
def test_abort_and_cancel_terminate_without_task_progress(outcome, state):
    task_policy = _policy_session()
    before = task_policy.history()

    disposition, history = apply_child_result_to_task_policy(
        task_policy, _resolution(outcome))

    assert disposition.state is state
    assert disposition.terminates_exploration is True
    assert disposition.attempt is None
    assert history is None
    assert task_policy.history() == before


def test_result_state_revision_and_context_conflicts_fail_closed():
    success = _resolution(ChildGoalOutcome.SUCCEEDED)
    with pytest.raises(ChildResultPolicyError, match="widerspricht"):
        disposition_from_child_result(replace(
            success,
            state=ChildGoalResolutionState.RETRYABLE_FAILURE,
        ))
    with pytest.raises(ChildResultPolicyError, match="Zielrevision"):
        disposition_from_child_result(replace(
            success,
            observed_map_revision=8,
        ))

    task_policy = _policy_session()
    foreign = PortalMapContext("foreign", "map", "map")
    with pytest.raises(ChildResultPolicyError, match="fremden"):
        apply_child_result_to_task_policy(
            task_policy, replace(success, context=foreign))
    assert task_policy.history()[0].attempt_count == 0


@pytest.mark.parametrize("value", [0, -1, 4097, True, 1.5])
def test_retry_delay_is_positive_and_bounded(value):
    with pytest.raises(ChildResultPolicyError):
        ChildResultPolicy(retry_delay_revisions=value)


def test_module_has_no_ros_nav_action_command_or_motion_imports():
    source = (PACKAGE_ROOT / "explore" / "child_result_policy.py").read_text(
        encoding="utf-8")
    tree = ast.parse(source)
    imported = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    assert not any(name.startswith("rclpy") for name in imported)
    assert not any(name.startswith("nav2") for name in imported)
    assert not any(name.startswith("geometry_msgs") for name in imported)
    assert "ActionClient" not in source
    assert "Twist" not in source
    assert "cmd_vel" not in source
