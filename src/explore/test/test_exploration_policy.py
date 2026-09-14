from dataclasses import replace
import ast
from pathlib import Path
import sys

import pytest


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE_ROOT))

from explore.exploration_policy import (  # noqa: E402
    ExplorationPolicyCapacityError,
    ExplorationPolicyConfig,
    ExplorationPolicyError,
    PolicyAssessmentState,
    PolicyTaskState,
    TaskAvailability,
    TaskAvailabilityState,
    assess_exploration_policy,
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
