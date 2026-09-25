from dataclasses import replace
import ast
from pathlib import Path
import sys

import pytest


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE_ROOT))

from explore.child_result_policy import (  # noqa: E402
    ChildResultDispositionState,
)
from explore.exploration_child_goal import (  # noqa: E402
    ChildGoalState,
    ExplorationGoalIntent,
)
from explore.exploration_nav_runtime import (  # noqa: E402
    ExplorationNavigationRuntimeError,
    ExplorationNavigationSession,
    NavigationSourceState,
    NavigationStopCause,
)
from explore.frontier_goal_candidate import FrontierGoalCandidate  # noqa: E402
from explore.portal_memory import PortalMapContext  # noqa: E402


CONTEXT = PortalMapContext("session-m3n", "map-m3n", "map")


def _intent(revision=7):
    return ExplorationGoalIntent(
        intent_id=f"intent-{revision}",
        task_id="task-frontier-1",
        region_id="region-1",
        context=CONTEXT,
        map_revision=revision,
    )


def _candidate(revision=7):
    return FrontierGoalCandidate(
        intent_id=f"intent-{revision}",
        task_id="task-frontier-1",
        region_id="region-1",
        frontier_id="frontier-1",
        map_revision=revision,
        frame_id="map",
        source_fingerprint="a" * 64,
        source_stamp_ns=123,
        target_x_m=1.0,
        target_y_m=2.0,
        target_yaw_rad=0.5,
        target_row=20,
        target_col=10,
        frontier_x_m=1.1,
        frontier_y_m=2.1,
        route_length_m=3.0,
        information_gain_square_m=1.5,
    )


def _run(navigation_status="success", *, state=None,
         user_canceled=lambda: False, budget_exhausted=lambda: False,
         navigate=None):
    session = ExplorationNavigationSession(CONTEXT)
    live = {"value": state or NavigationSourceState(CONTEXT, 7, True)}
    calls = []

    def default_navigate(candidate, should_stop):
        calls.append((candidate, should_stop()))
        return navigation_status

    result = session.run(
        _intent(),
        _candidate(),
        navigate or default_navigate,
        lambda: live["value"],
        user_canceled,
        budget_exhausted,
    )
    return session, result, calls, live


def test_success_is_one_progress_disposition_through_injected_owner():
    session, result, calls, _live = _run()

    assert calls == [(_candidate(), False)]
    assert result.navigation_status == "success"
    assert result.stop_cause is NavigationStopCause.NONE
    assert result.disposition.state is ChildResultDispositionState.PROGRESSED
    assert result.disposition.attempt is not None
    assert result.disposition.terminates_exploration is False
    assert session.child_status.state is ChildGoalState.IDLE


@pytest.mark.parametrize("status", ["aborted", "rejected", "timeout"])
def test_bounded_navigation_failures_schedule_retry(status):
    _session, result, _calls, _live = _run(status)

    assert result.navigation_status == status
    assert result.disposition.state is (
        ChildResultDispositionState.RETRY_SCHEDULED)
    assert result.disposition.attempt.retry_not_before_revision == 8


@pytest.mark.parametrize("status", ["cancel_failed", "error", "surprise"])
def test_transport_or_unknown_failures_abort(status):
    _session, result, _calls, _live = _run(status)

    assert result.navigation_status == (
        status if status != "surprise" else "error")
    assert result.disposition.state is ChildResultDispositionState.ABORTED
    assert result.disposition.terminates_exploration is True


def test_map_revision_change_cancels_before_late_success_can_progress():
    live = {"value": NavigationSourceState(CONTEXT, 7, True)}
    stop_values = []

    def navigate(_candidate_value, should_stop):
        live["value"] = NavigationSourceState(CONTEXT, 8, False)
        stop_values.append(should_stop())
        return "success"

    session = ExplorationNavigationSession(CONTEXT)
    result = session.run(
        _intent(), _candidate(), navigate,
        lambda: live["value"], lambda: False, lambda: False)

    assert stop_values == [True]
    assert result.stop_cause is NavigationStopCause.SOURCE_INVALIDATED
    assert result.disposition.state is ChildResultDispositionState.REEVALUATE
    assert result.disposition.attempt is None


def test_source_stop_remains_latched_when_source_recovers_before_nav2_cancel():
    live = {'state': NavigationSourceState(CONTEXT, 7, True)}

    def navigate(_candidate_value, should_stop):
        live['state'] = NavigationSourceState(CONTEXT, 8, False)
        assert should_stop() is True
        live['state'] = NavigationSourceState(CONTEXT, 9, True)
        return 'canceled'

    result = ExplorationNavigationSession(CONTEXT).run(
        _intent(), _candidate(), navigate, lambda: live['state'],
        lambda: False, lambda: False)

    assert result.navigation_status == 'canceled'
    assert result.stop_cause is NavigationStopCause.SOURCE_INVALIDATED
    assert result.disposition.state is ChildResultDispositionState.REEVALUATE
    assert result.disposition.attempt is None


def test_unconfirmed_cancel_never_replans_even_after_source_stop():
    live = {'state': NavigationSourceState(CONTEXT, 7, True)}

    def navigate(_candidate_value, should_stop):
        live['state'] = NavigationSourceState(CONTEXT, 8, False)
        assert should_stop() is True
        return 'cancel_failed'

    result = ExplorationNavigationSession(CONTEXT).run(
        _intent(), _candidate(), navigate, lambda: live['state'],
        lambda: False, lambda: False)

    assert result.stop_cause is NavigationStopCause.SYSTEM_FAILURE
    assert result.disposition.state is ChildResultDispositionState.ABORTED


def test_newer_exactly_revalidated_source_does_not_cancel_child():
    live = {"value": NavigationSourceState(CONTEXT, 7, True)}
    stop_values = []

    def navigate(_candidate_value, should_stop):
        live["value"] = NavigationSourceState(CONTEXT, 8, True)
        stop_values.append(should_stop())
        return "success"

    session = ExplorationNavigationSession(CONTEXT)
    result = session.run(
        _intent(), _candidate(), navigate,
        lambda: live["value"], lambda: False, lambda: False)

    assert stop_values == [False]
    assert result.stop_cause is NavigationStopCause.NONE
    assert result.disposition.state is ChildResultDispositionState.PROGRESSED


@pytest.mark.parametrize("cancel,budget,cause", [
    (True, False, NavigationStopCause.USER_CANCELED),
    (False, True, NavigationStopCause.BUDGET_EXHAUSTED),
])
def test_external_stop_causes_cancel_without_task_progress(cancel, budget, cause):
    flags = {"cancel": False, "budget": False}

    def navigate(_candidate_value, should_stop):
        flags["cancel"] = cancel
        flags["budget"] = budget
        assert should_stop() is True
        return "canceled"

    session = ExplorationNavigationSession(CONTEXT)
    result = session.run(
        _intent(), _candidate(), navigate,
        lambda: NavigationSourceState(CONTEXT, 7, True),
        lambda: flags["cancel"],
        lambda: flags["budget"],
    )

    assert result.stop_cause is cause
    assert result.disposition.state is ChildResultDispositionState.CANCELED
    assert result.disposition.attempt is None


def test_dispatch_exception_is_terminal_abort_and_closes_child():
    session, result, _calls, _live = _run(
        navigate=lambda *_args: (_ for _ in ()).throw(RuntimeError("fake")))

    assert result.navigation_status == "error"
    assert result.disposition.state is ChildResultDispositionState.ABORTED
    assert session.child_status.state is ChildGoalState.IDLE


def test_proven_local_obstruction_is_bounded_nonterminal_child_result():
    session = ExplorationNavigationSession(CONTEXT)
    result = session.run(
        _intent(), _candidate(), lambda *_args: "aborted",
        lambda: NavigationSourceState(CONTEXT, 7, True),
        lambda: False, lambda: False,
        local_blocked=lambda candidate: candidate == _candidate(),
    )
    assert result.stop_cause is NavigationStopCause.LOCAL_BLOCKED
    assert result.disposition.state is (
        ChildResultDispositionState.TEMPORARILY_BLOCKED)
    assert result.disposition.attempt.retry_not_before_revision == 9
    assert result.disposition.terminates_exploration is False
    assert session.child_status.state is ChildGoalState.IDLE


@pytest.mark.parametrize("verdict", [False, None, RuntimeError("fault")])
def test_unproven_abort_never_becomes_local_blockage(verdict):
    def classify(_candidate):
        if isinstance(verdict, Exception):
            raise verdict
        return verdict

    session = ExplorationNavigationSession(CONTEXT)
    result = session.run(
        _intent(), _candidate(), lambda *_args: "aborted",
        lambda: NavigationSourceState(CONTEXT, 7, True),
        lambda: False, lambda: False,
        local_blocked=classify,
    )
    assert result.stop_cause is NavigationStopCause.SYSTEM_FAILURE
    assert result.disposition.state is ChildResultDispositionState.ABORTED
    assert result.disposition.attempt is None
    assert session.child_status.state is ChildGoalState.IDLE


def test_hard_sensor_failure_cancels_child_as_system_failure():
    failed = {'value': False}
    def navigate(_candidate, should_stop):
        failed['value'] = True
        assert should_stop() is True
        return 'canceled'
    result = ExplorationNavigationSession(CONTEXT).run(
        _intent(), _candidate(), navigate,
        lambda: NavigationSourceState(CONTEXT, 7, True),
        lambda: False, lambda: False,
        local_blocked=lambda _candidate: pytest.fail(
            'Sensorfehler ist keine lokale Blockade'),
        safety_failure=lambda: failed['value'],
    )
    assert result.stop_cause is NavigationStopCause.SYSTEM_FAILURE
    assert result.disposition.state is ChildResultDispositionState.ABORTED
    assert result.disposition.terminates_exploration is True


def test_source_invalidation_never_records_local_failure():
    live = {'state': NavigationSourceState(CONTEXT, 7, True)}
    classified = []

    def navigate(_candidate, _should_stop):
        live['state'] = NavigationSourceState(CONTEXT, 8, False)
        return 'aborted'

    session = ExplorationNavigationSession(CONTEXT)
    result = session.run(
        _intent(), _candidate(), navigate, lambda: live['state'],
        lambda: False, lambda: False,
        local_blocked=lambda _candidate: classified.append(True) or True,
    )
    assert result.stop_cause is NavigationStopCause.SOURCE_INVALIDATED
    assert result.disposition.state is ChildResultDispositionState.REEVALUATE
    assert result.disposition.attempt is None
    assert classified == []


@pytest.mark.parametrize("status", ["rejected", "timeout"])
def test_unproven_reject_or_timeout_is_hard_failure_in_we_runtime(status):
    session = ExplorationNavigationSession(CONTEXT)
    result = session.run(
        _intent(), _candidate(), lambda *_args: status,
        lambda: NavigationSourceState(CONTEXT, 7, True),
        lambda: False, lambda: False,
        local_blocked=lambda _candidate: False,
    )
    assert result.stop_cause is NavigationStopCause.SYSTEM_FAILURE
    assert result.disposition.state is ChildResultDispositionState.ABORTED


def test_stale_initial_source_and_candidate_mismatch_never_dispatch():
    calls = []
    session = ExplorationNavigationSession(CONTEXT)
    with pytest.raises(ExplorationNavigationRuntimeError, match="veraltet"):
        session.run(
            _intent(), _candidate(),
            lambda *_args: calls.append(True),
            lambda: NavigationSourceState(CONTEXT, 8, False),
            lambda: False, lambda: False)
    with pytest.raises(ExplorationNavigationRuntimeError, match="passt nicht"):
        session.run(
            _intent(), replace(_candidate(), intent_id="intent-other"),
            lambda *_args: calls.append(True),
            lambda: NavigationSourceState(CONTEXT, 7, True),
            lambda: False, lambda: False)
    assert calls == []


def test_module_has_no_ros_nav_action_command_or_motion_imports():
    source = (PACKAGE_ROOT / "explore" / "exploration_nav_runtime.py").read_text(
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
