from dataclasses import replace
import ast
from pathlib import Path
import sys

import pytest


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE_ROOT))

from explore.exploration_policy import (  # noqa: E402
    ExplorationTaskPolicySession,
    ExplorationPolicyCapacityError,
    ExplorationPolicyConfig,
    ExplorationPolicyError,
    PolicyAssessmentState,
    PolicyTaskState,
    TaskAttempt,
    TaskAttemptOutcome,
    TaskAvailability,
    TaskAvailabilityState,
    TaskHistoryPolicy,
    TaskReactivation,
    TaskScoringPolicy,
    TaskUtilityEvidence,
    assess_exploration_policy,
    score_task_utilities,
)
from explore.exploration_completion import (  # noqa: E402
    AccessibleScopeState,
    ChildNavigationState,
    CompletionObservation,
    CompletionPolicy,
    ExplorationCompletionCapacityError,
    ExplorationCompletionError,
    ExplorationCompletionSession,
    ExplorationResultState,
    ReturnResultState,
    TerminationCause,
    completion_from_termination,
)
from explore.portal_memory import (  # noqa: E402
    Point2D,
    PortalMapContext,
    PortalMemory,
    PortalObservation,
    PortalSide,
    PortalStructuralEvidence,
    ReachabilityState,
    ReachabilityUpdate,
)
from explore.region_graph import (  # noqa: E402
    PortalLinkObservation,
    RegionExplorationState,
    RegionExplorationUpdate,
    RegionGraph,
    RegionSeed,
    RegionTaskKind,
    RegionTaskState,
    RegionTaskUpdate,
)
from explore.region_graph_status import (  # noqa: E402
    ShadowStatusPolicy,
    ShadowStatusSource,
)


CONTEXT = PortalMapContext(
    session_id="session-we-m3a",
    map_id="map-epoch-1",
    frame_id="map",
)


def _observation(observation_id, revision):
    return PortalObservation(
        observation_id=observation_id,
        context=CONTEXT,
        map_revision=revision,
        near_side=Point2D(0.0, 0.0),
        far_side=Point2D(1.0, 0.0),
        structural_evidence=PortalStructuralEvidence.QUALIFIED,
    )


def _task_update(task_id, region_id, revision, kind):
    return RegionTaskUpdate(
        update_id=f"update-{task_id}-{revision}",
        task_id=task_id,
        context=CONTEXT,
        map_revision=revision,
        region_id=region_id,
        kind=kind,
        subject_id=f"subject-{task_id}",
        state=RegionTaskState.OPEN,
    )


def _source_with_two_open_tasks():
    memory = PortalMemory(CONTEXT)
    first = memory.observe(_observation("door-r1", 1))
    memory.observe(_observation("door-r2", 2))
    portal = memory.snapshot(first.portal_id)
    for side in (PortalSide.A, PortalSide.B):
        memory.update_reachability(ReachabilityUpdate(
            update_id=f"reach-{side.value}",
            portal_id=portal.portal_id,
            side=side,
            context=CONTEXT,
            map_revision=4,
            observed_at_ns=400 + (side is PortalSide.B),
            state=ReachabilityState.OPEN,
            reason="passive_route_evidence",
            recheck_condition="next_map_revision",
        ))

    graph = RegionGraph(CONTEXT)
    current = graph.start(RegionSeed("start", CONTEXT, 0))
    link = graph.observe_portal(PortalLinkObservation(
        observation_id="link-door",
        context=CONTEXT,
        map_revision=2,
        portal=portal,
        current_region_id=current.region_id,
        current_side=PortalSide.A,
    ))
    graph.update_task(_task_update(
        "z-current", current.region_id, 3, RegionTaskKind.FRONTIER))
    graph.update_task(_task_update(
        "a-other", link.opposite_region_id, 3, RegionTaskKind.PORTAL))
    return ShadowStatusSource(
        context=CONTEXT,
        source_map_revision=4,
        portal_memory_revision=memory.latest_revision,
        graph=graph.snapshot(),
        portals=memory.snapshots(),
        reachability=memory.reachability_snapshots(),
        source_map_age_seconds=0.1,
        portal_memory_age_seconds=0.1,
        region_graph_age_seconds=0.1,
    )


def _availability(task_id, state=TaskAvailabilityState.AVAILABLE,
                  revision=4):
    return TaskAvailability(
        task_id=task_id,
        context=CONTEXT,
        map_revision=revision,
        state=state,
        reason=f"evidence_{state.value}",
        recheck_condition="next_map_revision",
    )


def _advance_source(source, revision, current_region_id=None):
    graph = replace(
        source.graph,
        latest_revision=revision,
        current_region_id=(
            source.graph.current_region_id
            if current_region_id is None else current_region_id),
    )
    return replace(
        source,
        source_map_revision=revision,
        portal_memory_revision=revision,
        graph=graph,
    )


def _all_available(revision):
    return (
        _availability("a-other", revision=revision),
        _availability("z-current", revision=revision),
    )


def _utility(task_id, revision, route_m, information_square_m):
    return TaskUtilityEvidence(
        task_id=task_id,
        context=CONTEXT,
        map_revision=revision,
        geodesic_path_length_m=route_m,
        information_gain_square_m=information_square_m,
    )


def _same_region_source():
    source = _source_with_two_open_tasks()
    current = source.graph.current_region_id
    tasks = tuple(
        replace(task, region_id=current) for task in source.graph.tasks)
    graph = replace(
        source.graph,
        tasks=tasks,
        regions=tuple(
            replace(
                region,
                task_ids=tuple(sorted(
                    task.task_id for task in tasks
                    if task.region_id == region.region_id)),
            )
            for region in source.graph.regions
        ),
    )
    return replace(source, graph=graph)


def _fresh_single_region_source(*, complete):
    graph = RegionGraph(CONTEXT)
    start = graph.start(RegionSeed("start", CONTEXT, 0))
    if complete:
        graph.update_region_exploration(RegionExplorationUpdate(
            update_id="start-region",
            context=CONTEXT,
            map_revision=1,
            region_id=start.region_id,
            state=RegionExplorationState.IN_PROGRESS,
            reason="region_assessment_started",
        ))
        graph.update_region_exploration(RegionExplorationUpdate(
            update_id="complete-region",
            context=CONTEXT,
            map_revision=2,
            region_id=start.region_id,
            state=RegionExplorationState.COMPLETE_CANDIDATE,
            reason="no_open_tasks_in_region",
        ))
    source_revision = 2 if complete else 1
    return ShadowStatusSource(
        context=CONTEXT,
        source_map_revision=source_revision,
        portal_memory_revision=source_revision,
        graph=graph.snapshot(),
        portals=(),
        reachability=(),
        source_map_age_seconds=0.1,
        portal_memory_age_seconds=0.1,
        region_graph_age_seconds=0.1,
    )


def test_current_region_tasks_are_grouped_first_without_creating_a_goal():
    source = _source_with_two_open_tasks()
    result = assess_exploration_policy(source, (
        _availability("a-other"),
        _availability("z-current"),
    ))

    assert result.state is PolicyAssessmentState.READY_WITH_TASKS
    assert result.open_task_ids == ("a-other", "z-current")
    assert result.current_region_task_ids == ("z-current",)
    assert result.other_region_task_ids == ("a-other",)
    assert result.eligible_task_ids == ("z-current", "a-other")
    assert result.completion_allowed is False
    assert not hasattr(result, "goal")
    assert not hasattr(result, "pose")


def test_result_is_deterministic_under_evidence_order_and_does_not_mutate_input():
    source = _source_with_two_open_tasks()
    evidence = (_availability("a-other"), _availability("z-current"))
    before_source = repr(source)
    before_evidence = repr(evidence)

    first = assess_exploration_policy(source, evidence)
    second = assess_exploration_policy(source, tuple(reversed(evidence)))

    assert first == second
    assert repr(source) == before_source
    assert repr(evidence) == before_evidence


@pytest.mark.parametrize("availability_state, expected_state", [
    (TaskAvailabilityState.FILTERED, PolicyTaskState.FILTERED),
    (
        TaskAvailabilityState.TEMPORARILY_BLOCKED,
        PolicyTaskState.TEMPORARILY_BLOCKED,
    ),
    (TaskAvailabilityState.EXCLUDED, PolicyTaskState.EXCLUDED),
])
def test_filtered_blocked_and_excluded_tasks_remain_visible_and_block_completion(
        availability_state, expected_state):
    source = _source_with_two_open_tasks()
    result = assess_exploration_policy(source, (
        _availability("a-other", availability_state),
        _availability("z-current", availability_state),
    ))

    assert result.state is PolicyAssessmentState.PARTIAL_CANDIDATE
    assert result.open_task_ids == ("a-other", "z-current")
    assert result.eligible_task_ids == ()
    assert {item.state for item in result.task_assessments} == {
        expected_state}
    assert result.completion_allowed is False
    assert any(
        code.startswith("open_task:a-other:")
        for code in result.blocker_codes)


def test_missing_availability_is_unknown_and_cannot_disappear_by_filtering():
    result = assess_exploration_policy(
        _source_with_two_open_tasks(),
        (_availability("z-current"),),
    )

    assert result.state is PolicyAssessmentState.READY_WITH_TASKS
    missing = next(
        item for item in result.task_assessments
        if item.task_id == "a-other")
    assert missing.state is PolicyTaskState.UNKNOWN
    assert missing.reason == "missing_task_availability"
    assert "open_task:a-other:unknown" in result.blocker_codes
    assert result.completion_allowed is False


def test_only_missing_or_stale_task_evidence_requires_reassessment():
    source = _source_with_two_open_tasks()
    missing = assess_exploration_policy(source)
    stale = assess_exploration_policy(source, (
        _availability("a-other", revision=2),
        _availability("z-current", revision=2),
    ))

    assert missing.state is PolicyAssessmentState.WAITING_FOR_TASK_EVIDENCE
    assert stale.state is PolicyAssessmentState.WAITING_FOR_TASK_EVIDENCE
    assert {item.state for item in stale.task_assessments} == {
        PolicyTaskState.STALE_EVIDENCE}


@pytest.mark.parametrize("field", [
    "source_map_age_seconds",
    "portal_memory_age_seconds",
    "region_graph_age_seconds",
])
def test_stale_or_missing_passive_source_takes_precedence(field):
    source = replace(_source_with_two_open_tasks(), **{field: None})
    result = assess_exploration_policy(source, (
        _availability("a-other"),
        _availability("z-current"),
    ))

    assert result.state is PolicyAssessmentState.WAITING_FOR_FRESH_SOURCES
    assert result.source_ready is False
    assert result.stale_sources
    assert result.completion_allowed is False


def test_empty_fresh_complete_candidate_still_requires_later_completion_contract():
    result = assess_exploration_policy(
        _fresh_single_region_source(complete=True))

    assert result.state is PolicyAssessmentState.COMPLETION_WINDOW_REQUIRED
    assert result.open_task_ids == ()
    assert result.blocker_codes == (
        "fresh_observation_window_required",
        "accessible_scope_required",
        "child_navigation_state_required",
    )
    assert result.completion_allowed is False


def test_empty_but_unassessed_region_is_only_a_partial_candidate():
    result = assess_exploration_policy(
        _fresh_single_region_source(complete=False))

    assert result.state is PolicyAssessmentState.PARTIAL_CANDIDATE
    assert result.incomplete_region_ids == ("region_000001",)
    assert result.completion_allowed is False


def test_unresolved_structure_and_reachability_are_explainable_blockers():
    source = _source_with_two_open_tasks()
    changed_reachability = tuple(
        replace(
            item,
            state=(ReachabilityState.UNKNOWN
                   if item.side is PortalSide.A
                   else ReachabilityState.TEMPORARILY_BLOCKED),
            reason="needs_recheck",
        )
        for item in source.reachability
    )
    changed_portals = (
        replace(
            source.portals[0],
            confirmation_state=source.portals[0].confirmation_state.UNCERTAIN,
            confirmed=False,
        ),
    )
    source = replace(
        source,
        portals=changed_portals,
        reachability=changed_reachability,
    )
    result = assess_exploration_policy(source)

    assert result.unresolved_portal_ids == ("portal_000001",)
    assert result.unknown_reachability == ("portal_000001:A",)
    assert result.blocked_reachability == ("portal_000001:B",)
    assert result.completion_allowed is False


def test_foreign_duplicate_unknown_and_completed_task_evidence_are_rejected():
    source = _source_with_two_open_tasks()
    foreign_context = PortalMapContext("other-session", "map", "map")
    foreign = replace(_availability("a-other"), context=foreign_context)
    unknown = replace(_availability("a-other"), task_id="not-in-graph")

    with pytest.raises(ExplorationPolicyError, match="doppelte"):
        assess_exploration_policy(source, (
            _availability("a-other"), _availability("a-other")))
    with pytest.raises(ExplorationPolicyError, match="unbekannte"):
        assess_exploration_policy(source, (unknown,))
    with pytest.raises(ExplorationPolicyError, match="Kontexte"):
        assess_exploration_policy(source, (foreign,))

    completed_task = replace(
        source.graph.tasks[0], state=RegionTaskState.COMPLETED)
    other_task = source.graph.tasks[1]
    completed_graph = replace(
        source.graph,
        tasks=(completed_task, other_task),
        open_task_count=1,
        completed_task_count=1,
        regions=tuple(
            replace(
                region,
                task_ids=tuple(
                    task.task_id for task in (completed_task, other_task)
                    if task.region_id == region.region_id),
            )
            for region in source.graph.regions
        ),
    )
    completed_source = replace(source, graph=completed_graph)
    with pytest.raises(ExplorationPolicyError, match="nur offene"):
        assess_exploration_policy(
            completed_source, (_availability(completed_task.task_id),))


def test_capacity_is_hard_and_checked_before_assessment():
    config = ExplorationPolicyConfig(max_task_availability=1)
    with pytest.raises(ExplorationPolicyCapacityError):
        assess_exploration_policy(
            _source_with_two_open_tasks(),
            (_availability("a-other"), _availability("z-current")),
            config,
        )


def test_future_revision_and_invalid_identifier_fail_closed():
    source = _source_with_two_open_tasks()
    future = replace(_availability("a-other"), map_revision=5)
    with pytest.raises(ExplorationPolicyError, match="vor der aktuellen"):
        assess_exploration_policy(source, (future,))
    with pytest.raises(ExplorationPolicyError):
        replace(_availability("a-other"), task_id="bad id")


def test_policy_module_has_no_ros_navigation_process_or_device_imports():
    source_path = PACKAGE_ROOT / "explore" / "exploration_policy.py"
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    imported_roots = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_roots.update(
                alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_roots.add(node.module.split(".")[0])

    assert imported_roots.isdisjoint({
        "action_msgs", "geometry_msgs", "nav2_msgs", "rclpy",
        "serial", "subprocess",
    })


def test_source_projection_policy_bounds_are_reused():
    source = _source_with_two_open_tasks()
    config = ExplorationPolicyConfig(source_policy=ShadowStatusPolicy(
        max_tasks=1))

    with pytest.raises(ExplorationPolicyError, match="Aufgaben"):
        assess_exploration_policy(source, config=config)


def test_stateful_session_selects_only_an_id_and_tracks_first_seen_revision():
    source = _source_with_two_open_tasks()
    session = ExplorationTaskPolicySession(CONTEXT)

    result = session.assess(source, _all_available(4))

    assert result.selected_task_id == "z-current"
    assert result.selected_region_id == source.graph.current_region_id
    assert result.selection_reason == "current_region"
    assert result.completion_allowed is False
    assert [item.task_id for item in result.history] == [
        "a-other", "z-current"]
    assert {item.first_seen_revision for item in result.history} == {3}
    selected = next(
        item for item in result.history if item.task_id == "z-current")
    assert selected.age_revisions == 1
    assert selected.last_selected_revision == 4
    assert selected.selection_count == 1
    assert not hasattr(result, "goal")
    assert not hasattr(result, "pose")


def test_stateful_session_never_selects_from_stale_sources():
    source = replace(
        _source_with_two_open_tasks(), source_map_age_seconds=None)
    session = ExplorationTaskPolicySession(CONTEXT)

    result = session.assess(source, _all_available(4))

    assert result.passive.state is (
        PolicyAssessmentState.WAITING_FOR_FRESH_SOURCES)
    assert result.selected_task_id is None
    assert result.selected_region_id is None
    assert result.selection_reason == "no_selectable_task"


def test_exact_assessment_replay_is_idempotent_and_conflict_is_rejected():
    source = _source_with_two_open_tasks()
    evidence = _all_available(4)
    session = ExplorationTaskPolicySession(CONTEXT)
    first = session.assess(source, evidence)

    assert session.assess(source, evidence) is first
    with pytest.raises(ExplorationPolicyError, match="widerspruechlich"):
        session.assess(source, tuple(reversed(evidence)))


def test_region_hysteresis_prevents_immediate_switch_but_then_releases():
    source = _source_with_two_open_tasks()
    session = ExplorationTaskPolicySession(CONTEXT)
    first = session.assess(source, _all_available(4))
    other_region = next(
        region.region_id for region in source.graph.regions
        if region.region_id != first.selected_region_id)

    held = session.assess(
        _advance_source(source, 5, other_region), _all_available(5))
    released = session.assess(
        _advance_source(source, 6, other_region), _all_available(6))

    assert held.selected_task_id == "z-current"
    assert held.selection_reason == "region_hysteresis"
    assert released.selected_task_id == "a-other"
    assert released.selection_reason == "current_region"


def test_old_remote_region_task_preempts_current_region_to_avoid_starvation():
    source = _advance_source(_source_with_two_open_tasks(), 12)
    session = ExplorationTaskPolicySession(CONTEXT)

    result = session.assess(source, _all_available(12))

    assert result.selected_task_id == "a-other"
    assert result.selection_reason == "starvation_prevention"


def test_starvation_rotation_still_honors_the_region_hold_window():
    source = _advance_source(_source_with_two_open_tasks(), 12)
    session = ExplorationTaskPolicySession(CONTEXT)
    first = session.assess(source, _all_available(12))
    held = session.assess(
        _advance_source(source, 13), _all_available(13))
    rotated = session.assess(
        _advance_source(source, 14), _all_available(14))

    assert first.selected_task_id == "a-other"
    assert held.selected_task_id == "a-other"
    assert held.selection_reason == "region_hysteresis"
    assert rotated.selected_task_id == "z-current"
    assert rotated.selection_reason == "starvation_prevention"


def test_active_available_task_is_retained_across_new_map_revisions():
    source = _source_with_two_open_tasks()
    session = ExplorationTaskPolicySession(CONTEXT)
    first = session.assess(source, _all_available(4))

    retained = session.assess(
        _advance_source(source, 20),
        _all_available(20),
        preferred_task_id=first.selected_task_id,
    )

    assert retained.selected_task_id == first.selected_task_id
    assert retained.selection_reason == "active_task_continuity"


def test_active_task_preference_never_revives_unavailable_task():
    source = _source_with_two_open_tasks()
    session = ExplorationTaskPolicySession(CONTEXT)
    first = session.assess(source, _all_available(4))
    other_task_id = next(
        task_id for task_id in ("a-other", "z-current")
        if task_id != first.selected_task_id)

    switched = session.assess(
        _advance_source(source, 20),
        (_availability(other_task_id, revision=20),),
        preferred_task_id=first.selected_task_id,
    )

    assert switched.selected_task_id == other_task_id
    assert switched.selection_reason != "active_task_continuity"


def test_retry_failure_defers_then_releases_task_by_explicit_revision():
    source = _source_with_two_open_tasks()
    session = ExplorationTaskPolicySession(CONTEXT)
    session.assess(source, _all_available(4))
    snapshot = session.record_attempt(TaskAttempt(
        attempt_id="attempt-1",
        task_id="z-current",
        context=CONTEXT,
        map_revision=4,
        outcome=TaskAttemptOutcome.RETRYABLE_FAILURE,
        reason="planner_temporarily_unavailable",
        retry_not_before_revision=6,
    ))

    deferred = session.assess(
        _advance_source(source, 5),
        (_availability("z-current", revision=5),),
    )
    released = session.assess(
        _advance_source(source, 6),
        (_availability("z-current", revision=6),),
    )

    assert snapshot.attempt_count == 1
    assert snapshot.retryable_failure_count == 1
    assert deferred.selected_task_id is None
    assert deferred.retry_deferred_task_ids == ("z-current",)
    assert "retry_deferred:z-current" in deferred.blocker_codes
    assert released.selected_task_id == "z-current"


def test_retry_filter_accepts_complete_eligible_utility_evidence():
    source = _source_with_two_open_tasks()
    session = ExplorationTaskPolicySession(CONTEXT)
    utilities = (
        _utility("a-other", 4, 1.0, 9.0),
        _utility("z-current", 4, 10.0, 1.0),
    )
    first = session.assess(source, _all_available(4), utilities)
    session.record_attempt(TaskAttempt(
        "attempt-score-retry",
        first.selected_task_id,
        CONTEXT,
        4,
        TaskAttemptOutcome.RETRYABLE_FAILURE,
        "temporary",
        6,
    ))

    result = session.assess(
        _advance_source(source, 5),
        _all_available(5),
        tuple(replace(item, map_revision=5) for item in utilities),
    )

    assert result.retry_deferred_task_ids == (first.selected_task_id,)
    assert first.selected_task_id not in {
        item.task_id for item in result.utility_scores}
    assert result.selected_task_id != first.selected_task_id


def test_retry_budget_exhaustion_requires_explicit_reactivation():
    policy = TaskHistoryPolicy(maximum_retryable_failures=2)
    source = _source_with_two_open_tasks()
    session = ExplorationTaskPolicySession(CONTEXT, policy)
    session.assess(source, (_availability("z-current"),))
    session.record_attempt(TaskAttempt(
        "attempt-1", "z-current", CONTEXT, 4,
        TaskAttemptOutcome.RETRYABLE_FAILURE, "first_failure", 5))
    session.assess(
        _advance_source(source, 5),
        (_availability("z-current", revision=5),))
    session.record_attempt(TaskAttempt(
        "attempt-2", "z-current", CONTEXT, 5,
        TaskAttemptOutcome.RETRYABLE_FAILURE, "second_failure", 6))

    exhausted = session.assess(
        _advance_source(source, 6),
        (_availability("z-current", revision=6),))
    assert exhausted.selected_task_id is None
    assert exhausted.retry_exhausted_task_ids == ("z-current",)

    reactivated = session.reactivate(TaskReactivation(
        "reactivate-1", "z-current", CONTEXT, 6,
        "new_map_evidence"))
    resumed = session.assess(
        _advance_source(source, 7),
        (_availability("z-current", revision=7),))
    assert reactivated.retryable_failure_count == 0
    assert reactivated.last_reactivation_revision == 6
    assert resumed.selected_task_id == "z-current"


def test_attempt_and_reactivation_replays_are_idempotent_but_conflicts_fail():
    source = _source_with_two_open_tasks()
    session = ExplorationTaskPolicySession(CONTEXT)
    session.assess(source, _all_available(4))
    attempt = TaskAttempt(
        "attempt-1", "z-current", CONTEXT, 4,
        TaskAttemptOutcome.RETRYABLE_FAILURE, "temporary", 5)
    first = session.record_attempt(attempt)
    replay = session.record_attempt(attempt)
    assert first == replay
    with pytest.raises(ExplorationPolicyError, match="widerspruechlich"):
        session.record_attempt(replace(attempt, reason="different"))

    reactivation = TaskReactivation(
        "reactivate-1", "z-current", CONTEXT, 4, "fresh_evidence")
    first_reactivation = session.reactivate(reactivation)
    assert session.reactivate(reactivation) == first_reactivation
    with pytest.raises(ExplorationPolicyError, match="widerspruechlich"):
        session.reactivate(replace(reactivation, reason="different"))


def test_progress_clears_retry_delay_without_claiming_task_completion():
    source = _source_with_two_open_tasks()
    session = ExplorationTaskPolicySession(CONTEXT)
    session.assess(source, _all_available(4))
    session.record_attempt(TaskAttempt(
        "failure", "z-current", CONTEXT, 4,
        TaskAttemptOutcome.RETRYABLE_FAILURE, "temporary", 6))
    with pytest.raises(ExplorationPolicyError, match="Retryrevision"):
        session.record_attempt(TaskAttempt(
            "early-progress", "z-current", CONTEXT, 4,
            TaskAttemptOutcome.PROGRESSED, "too_early"))
    session.assess(
        _advance_source(source, 6),
        (_availability("z-current", revision=6),))
    progress = session.record_attempt(TaskAttempt(
        "progress", "z-current", CONTEXT, 6,
        TaskAttemptOutcome.PROGRESSED, "new_observation"))

    assert progress.attempt_count == 2
    assert progress.retry_not_before_revision is None
    assert progress.completed is False


def test_revalidated_attempt_binds_child_result_to_current_snapshot():
    source = _source_with_two_open_tasks()
    session = ExplorationTaskPolicySession(CONTEXT)
    first = session.assess(source, _all_available(4))
    session.assess(
        _advance_source(source, 20),
        _all_available(20),
        preferred_task_id=first.selected_task_id,
    )

    progress = session.record_revalidated_attempt(TaskAttempt(
        "revalidated-progress", first.selected_task_id, CONTEXT, 4,
        TaskAttemptOutcome.PROGRESSED, "child_goal_reached"), 20)

    assert progress.last_attempt_revision == 20
    assert progress.attempt_count == 1
    assert progress.completed is False


def test_revalidated_retry_preserves_revision_delay_and_fails_stale():
    source = _source_with_two_open_tasks()
    session = ExplorationTaskPolicySession(CONTEXT)
    session.assess(source, _all_available(4))
    session.assess(_advance_source(source, 20), _all_available(20))
    attempt = TaskAttempt(
        "revalidated-retry", "z-current", CONTEXT, 4,
        TaskAttemptOutcome.RETRYABLE_FAILURE, "temporary", 6)

    snapshot = session.record_revalidated_attempt(attempt, 20)

    assert snapshot.last_attempt_revision == 20
    assert snapshot.retry_not_before_revision == 22
    with pytest.raises(ExplorationPolicyError, match="aktuellen"):
        session.record_revalidated_attempt(
            replace(attempt, attempt_id="stale-revalidation"), 19)


def test_completed_graph_task_is_retained_as_completed_history_not_selected():
    source = _source_with_two_open_tasks()
    session = ExplorationTaskPolicySession(CONTEXT)
    session.assess(source, _all_available(4))
    completed = replace(
        source.graph.tasks[1],
        state=RegionTaskState.COMPLETED,
        last_revision=5,
    )
    open_task = source.graph.tasks[0]
    graph = replace(
        source.graph,
        latest_revision=5,
        tasks=(open_task, completed),
        open_task_count=1,
        completed_task_count=1,
        regions=tuple(
            replace(
                region,
                last_revision=max(region.last_revision, 5)
                if completed.task_id in region.task_ids
                else region.last_revision,
            )
            for region in source.graph.regions
        ),
    )
    updated = replace(
        source,
        source_map_revision=5,
        portal_memory_revision=5,
        graph=graph,
    )

    result = session.assess(
        updated, (_availability(open_task.task_id, revision=5),))

    completed_history = next(
        item for item in result.history if item.task_id == completed.task_id)
    assert completed_history.completed is True
    assert completed.task_id not in result.passive.open_task_ids
    assert result.selected_task_id == open_task.task_id


def test_history_capacity_and_foreign_or_stale_events_fail_closed():
    source = _source_with_two_open_tasks()
    limited = ExplorationTaskPolicySession(
        CONTEXT, TaskHistoryPolicy(max_tracked_tasks=1))
    with pytest.raises(ExplorationPolicyCapacityError):
        limited.assess(source, _all_available(4))

    session = ExplorationTaskPolicySession(CONTEXT)
    session.assess(source, _all_available(4))
    foreign = PortalMapContext("foreign", "map", "map")
    with pytest.raises(ExplorationPolicyError, match="fremden"):
        session.record_attempt(TaskAttempt(
            "foreign", "z-current", foreign, 4,
            TaskAttemptOutcome.PROGRESSED, "invalid_context"))
    with pytest.raises(ExplorationPolicyError, match="unbekannte"):
        session.record_attempt(TaskAttempt(
            "unknown", "unknown-task", CONTEXT, 4,
            TaskAttemptOutcome.PROGRESSED, "missing_task"))
    with pytest.raises(ExplorationPolicyError, match="aktuellen"):
        session.record_attempt(TaskAttempt(
            "old", "z-current", CONTEXT, 3,
            TaskAttemptOutcome.PROGRESSED, "stale_attempt"))


def test_retry_and_history_policy_inputs_are_strict():
    with pytest.raises(ExplorationPolicyError):
        TaskAttempt(
            "bad-retry", "task", CONTEXT, 4,
            TaskAttemptOutcome.RETRYABLE_FAILURE, "temporary", 4)
    with pytest.raises(ExplorationPolicyError):
        TaskAttempt(
            "bad-progress", "task", CONTEXT, 4,
            TaskAttemptOutcome.PROGRESSED, "progress", 5)
    with pytest.raises(ExplorationPolicyError):
        TaskHistoryPolicy(maximum_retryable_failures=0)


def test_scalar_utility_is_normalized_with_explicit_units_and_weights():
    scores = score_task_utilities(
        ("a-other", "z-current"),
        (
            _utility("z-current", 4, 10.0, 5.0),
            _utility("a-other", 4, 40.0, 20.0),
        ),
        4,
    )

    assert [item.task_id for item in scores] == ["a-other", "z-current"]
    capped, middle = scores
    assert capped.normalized_route_cost == 1.0
    assert capped.normalized_information_gain == 1.0
    assert capped.score == pytest.approx(0.6)
    assert middle.normalized_route_cost == 0.5
    assert middle.normalized_information_gain == 0.5
    assert middle.score == pytest.approx(0.5)


def test_utility_refines_selection_only_within_the_hierarchical_candidate_set():
    source = _same_region_source()
    session = ExplorationTaskPolicySession(CONTEXT)
    result = session.assess(
        source,
        _all_available(4),
        (
            _utility("a-other", 4, 2.0, 9.0),
            _utility("z-current", 4, 15.0, 1.0),
        ),
    )

    assert result.selected_task_id == "a-other"
    assert result.selection_reason == "current_region"
    assert [item.task_id for item in result.utility_scores] == [
        "a-other", "z-current"]
    assert result.completion_allowed is False
    assert not hasattr(result, "goal")
    assert not hasattr(result, "path")


def test_equal_utility_uses_stable_task_id_tie_break():
    source = _same_region_source()
    session = ExplorationTaskPolicySession(CONTEXT)
    result = session.assess(
        source,
        _all_available(4),
        (
            _utility("z-current", 4, 5.0, 5.0),
            _utility("a-other", 4, 5.0, 5.0),
        ),
    )
    assert result.selected_task_id == "a-other"


def test_custom_weights_are_visible_and_change_the_id_order():
    source = _same_region_source()
    evidence = (
        _utility("a-other", 4, 18.0, 9.0),
        _utility("z-current", 4, 2.0, 1.0),
    )
    route_only = TaskScoringPolicy(
        route_weight=1.0, information_weight=0.0)
    information_only = TaskScoringPolicy(
        route_weight=0.0, information_weight=1.0)

    route_result = ExplorationTaskPolicySession(CONTEXT).assess(
        source, _all_available(4), evidence, route_only)
    information_result = ExplorationTaskPolicySession(CONTEXT).assess(
        source, _all_available(4), evidence, information_only)

    assert route_result.selected_task_id == "z-current"
    assert information_result.selected_task_id == "a-other"


def test_utility_must_exactly_cover_selectable_ids_at_current_revision():
    source = _same_region_source()
    session = ExplorationTaskPolicySession(CONTEXT)
    with pytest.raises(ExplorationPolicyError, match="exakt abdecken"):
        session.assess(
            source,
            _all_available(4),
            (_utility("a-other", 4, 1.0, 1.0),),
        )
    with pytest.raises(ExplorationPolicyError, match="aktuellen"):
        ExplorationTaskPolicySession(CONTEXT).assess(
            source,
            _all_available(4),
            (
                _utility("a-other", 3, 1.0, 1.0),
                _utility("z-current", 3, 1.0, 1.0),
            ),
        )


def test_duplicate_foreign_nonfinite_and_unpaired_scoring_inputs_fail_closed():
    source = _same_region_source()
    duplicate = _utility("a-other", 4, 1.0, 1.0)
    with pytest.raises(ExplorationPolicyError, match="doppelte"):
        score_task_utilities(
            ("a-other",), (duplicate, duplicate), 4)
    foreign = replace(
        duplicate,
        context=PortalMapContext("foreign", "map", "map"),
    )
    with pytest.raises(ExplorationPolicyError, match="fremden"):
        ExplorationTaskPolicySession(CONTEXT).assess(
            source,
            _all_available(4),
            (foreign, _utility("z-current", 4, 1.0, 1.0)),
        )
    with pytest.raises(ExplorationPolicyError):
        _utility("bad", 4, float("nan"), 1.0)
    with pytest.raises(ExplorationPolicyError, match="ohne"):
        ExplorationTaskPolicySession(CONTEXT).assess(
            source, _all_available(4), scoring_policy=TaskScoringPolicy())


def test_scoring_capacity_and_configuration_are_strict():
    evidence = (
        _utility("a-other", 4, 1.0, 1.0),
        _utility("z-current", 4, 1.0, 1.0),
    )
    with pytest.raises(ExplorationPolicyCapacityError):
        score_task_utilities(
            ("a-other", "z-current"), evidence, 4,
            TaskScoringPolicy(max_evidence=1),
        )
    with pytest.raises(ExplorationPolicyError):
        TaskScoringPolicy(route_normalization_m=0.0)
    with pytest.raises(ExplorationPolicyError):
        TaskScoringPolicy(route_weight=0.0, information_weight=0.0)


def _completion_observation(
        observation_id, revision, assessment, *,
        scope=AccessibleScopeState.VERIFIED,
        child=ChildNavigationState.IDLE,
        termination=TerminationCause.NONE,
        map_saved=None,
        return_result=ReturnResultState.NOT_REQUESTED):
    return CompletionObservation(
        observation_id=observation_id,
        context=CONTEXT,
        map_revision=revision,
        assessment=assessment,
        accessible_scope=scope,
        child_navigation=child,
        termination=termination,
        reason=f"reason_{termination.value}",
        map_saved=map_saved,
        return_result=return_result,
    )


def _completion_assessments(revisions):
    policy_session = ExplorationTaskPolicySession(CONTEXT)
    base = _fresh_single_region_source(complete=True)
    return tuple(
        policy_session.assess(_advance_source(base, revision))
        for revision in revisions
    )


def test_three_fresh_qualified_revisions_are_required_for_complete_accessible():
    assessments = _completion_assessments((2, 3, 4))
    session = ExplorationCompletionSession(CONTEXT)
    results = tuple(
        session.observe(_completion_observation(
            f"complete-{revision}", revision, assessment))
        for revision, assessment in zip((2, 3, 4), assessments)
    )

    assert [item.state for item in results] == [
        ExplorationResultState.IN_PROGRESS,
        ExplorationResultState.IN_PROGRESS,
        ExplorationResultState.COMPLETE_ACCESSIBLE,
    ]
    assert results[-1].qualifying_observation_count == 3
    assert results[-1].terminal is True


@pytest.mark.parametrize("scope, child, blocker", [
    (
        AccessibleScopeState.UNVERIFIED,
        ChildNavigationState.IDLE,
        "accessible_scope_unverified",
    ),
    (
        AccessibleScopeState.VERIFIED,
        ChildNavigationState.ACTIVE,
        "child_navigation_active",
    ),
    (
        AccessibleScopeState.VERIFIED,
        ChildNavigationState.UNKNOWN,
        "child_navigation_unknown",
    ),
])
def test_scope_and_child_navigation_fail_closed(scope, child, blocker):
    assessment = _completion_assessments((2,))[0]
    result = ExplorationCompletionSession(CONTEXT).observe(
        _completion_observation(
            "blocked", 2, assessment, scope=scope, child=child))

    assert result.state is ExplorationResultState.IN_PROGRESS
    assert result.blocker_codes == (blocker,)
    assert result.qualifying_observation_count == 0


def test_blocked_revision_resets_the_consecutive_fresh_window():
    assessments = _completion_assessments((2, 3, 4))
    session = ExplorationCompletionSession(
        CONTEXT, CompletionPolicy(required_fresh_observations=2))
    first = session.observe(_completion_observation(
        "first", 2, assessments[0]))
    blocked = session.observe(_completion_observation(
        "blocked", 3, assessments[1], child=ChildNavigationState.ACTIVE))
    resumed = session.observe(_completion_observation(
        "resumed", 4, assessments[2]))

    assert first.qualifying_observation_count == 1
    assert blocked.qualifying_observation_count == 0
    assert resumed.qualifying_observation_count == 1
    assert resumed.state is ExplorationResultState.IN_PROGRESS


def test_open_or_only_filtered_tasks_cannot_start_completion_window():
    source = _source_with_two_open_tasks()
    policy_session = ExplorationTaskPolicySession(CONTEXT)
    filtered = policy_session.assess(source, (
        _availability("a-other", TaskAvailabilityState.FILTERED),
        _availability("z-current", TaskAvailabilityState.FILTERED),
    ))
    result = ExplorationCompletionSession(CONTEXT).observe(
        _completion_observation("filtered", 4, filtered))

    assert result.state is ExplorationResultState.IN_PROGRESS
    assert result.blocker_codes == ("policy_not_quiescent",)
    assert result.qualifying_observation_count == 0


@pytest.mark.parametrize("cause, expected", [
    (TerminationCause.BUDGET_EXHAUSTED, ExplorationResultState.PARTIAL),
    (TerminationCause.SYSTEM_FAILURE, ExplorationResultState.ABORTED),
    (TerminationCause.USER_CANCELED, ExplorationResultState.CANCELED),
])
def test_terminal_causes_remain_distinct(cause, expected):
    assessment = _completion_assessments((2,))[0]
    result = ExplorationCompletionSession(CONTEXT).observe(
        _completion_observation(
            f"terminal-{cause.value}", 2, assessment,
            termination=cause))

    assert result.state is expected
    assert result.terminal is True


@pytest.mark.parametrize("cause, expected", [
    (TerminationCause.BUDGET_EXHAUSTED, ExplorationResultState.PARTIAL),
    (TerminationCause.SYSTEM_FAILURE, ExplorationResultState.ABORTED),
    (TerminationCause.USER_CANCELED, ExplorationResultState.CANCELED),
])
def test_external_termination_needs_no_invented_map_revision(cause, expected):
    result = completion_from_termination(
        cause,
        "external_runtime_stop",
        qualifying_observation_count=2,
        policy=CompletionPolicy(required_fresh_observations=3),
    )

    assert result.state is expected
    assert result.qualifying_observation_count == 2
    assert result.required_observation_count == 3
    assert result.terminal is True


def test_session_termination_preserves_progress_and_is_idempotent():
    assessment = _completion_assessments((2,))[0]
    session = ExplorationCompletionSession(CONTEXT)
    session.observe(_completion_observation("pending", 2, assessment))

    first = session.terminate(
        TerminationCause.BUDGET_EXHAUSTED,
        "budget",
        map_saved=False,
        return_result=ReturnResultState.FAILED,
    )

    assert session.latest_revision == 2
    assert session.qualifying_observation_count == 1
    assert first.qualifying_observation_count == 1
    assert session.terminate(
        TerminationCause.BUDGET_EXHAUSTED,
        "budget",
        map_saved=False,
        return_result=ReturnResultState.FAILED,
    ) is first
    with pytest.raises(ExplorationCompletionError, match="widerspruechlich"):
        session.terminate(TerminationCause.SYSTEM_FAILURE, "other")
    with pytest.raises(ExplorationCompletionError, match="unveraenderlich"):
        session.observe(replace(
            _completion_observation("later", 3, assessment),
            assessment=replace(
                assessment,
                passive=replace(assessment.passive, source_map_revision=3))))


def test_external_termination_validation_fails_closed():
    for invalid in (TerminationCause.NONE, "budget_exhausted", None):
        with pytest.raises(ExplorationCompletionError):
            completion_from_termination(invalid, "stop")
    with pytest.raises(ExplorationCompletionError):
        completion_from_termination(
            TerminationCause.SYSTEM_FAILURE,
            "stop",
            qualifying_observation_count=True,
        )


def test_map_save_and_return_result_do_not_change_exploration_success():
    assessments = _completion_assessments((2, 3, 4))
    session = ExplorationCompletionSession(CONTEXT)
    for revision, assessment in zip((2, 3), assessments[:2]):
        session.observe(_completion_observation(
            f"pending-{revision}", revision, assessment))
    result = session.observe(_completion_observation(
        "complete", 4, assessments[2],
        map_saved=False,
        return_result=ReturnResultState.FAILED,
    ))

    assert result.state is ExplorationResultState.COMPLETE_ACCESSIBLE
    assert result.map_saved is False
    assert result.return_result is ReturnResultState.FAILED


def test_completion_replay_is_idempotent_and_terminal_is_immutable():
    assessments = _completion_assessments((2, 3))
    session = ExplorationCompletionSession(
        CONTEXT, CompletionPolicy(required_fresh_observations=1))
    observation = _completion_observation("done", 2, assessments[0])
    first = session.observe(observation)
    assert session.observe(observation) is first
    with pytest.raises(ExplorationCompletionError, match="unveraenderlich"):
        session.observe(_completion_observation(
            "later", 3, assessments[1]))


def test_completion_rejects_uncorrelated_replay_and_capacity_overflow():
    assessments = _completion_assessments((2, 3))
    uncorrelated = _completion_observation("bad", 3, assessments[0])
    with pytest.raises(ExplorationCompletionError, match="korreliert"):
        ExplorationCompletionSession(CONTEXT).observe(uncorrelated)

    session = ExplorationCompletionSession(
        CONTEXT, CompletionPolicy(
            required_fresh_observations=3, max_observations=1))
    first = _completion_observation("first", 2, assessments[0])
    session.observe(first)
    with pytest.raises(ExplorationCompletionCapacityError):
        session.observe(_completion_observation(
            "second", 3, assessments[1]))
    with pytest.raises(ExplorationCompletionError, match="widerspruechlich"):
        session.observe(replace(first, reason="different"))


def test_completion_module_has_no_ros_navigation_process_or_device_imports():
    source_path = PACKAGE_ROOT / "explore" / "exploration_completion.py"
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    imported_roots = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_roots.update(
                alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_roots.add(node.module.split(".")[0])
    assert imported_roots.isdisjoint({
        "action_msgs", "geometry_msgs", "nav2_msgs", "rclpy",
        "serial", "subprocess",
    })
