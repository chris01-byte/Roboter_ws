from dataclasses import replace
import json
from pathlib import Path
import sys

import pytest


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE_ROOT))

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
from explore.portal_source_adapter import (  # noqa: E402
    RawMapCorrelationDiagnostics,
)
from explore.region_graph import (  # noqa: E402
    PortalLinkObservation,
    RegionExplorationState,
    RegionExplorationUpdate,
    RegionGraph,
    RegionGraphSnapshot,
    RegionSeed,
    RegionTaskKind,
    RegionTaskState,
    RegionTaskUpdate,
)
from explore.region_graph_status import (  # noqa: E402
    SCHEMA_VERSION,
    ShadowStatusCapacityError,
    ShadowStatusError,
    ShadowStatusPolicy,
    ShadowStatusSource,
    build_shadow_status_json,
)


CONTEXT = PortalMapContext(
    session_id="session-20260914",
    map_id="live-map-epoch-1",
    frame_id="map",
)


def observation(
        observation_id, revision, y,
        evidence=PortalStructuralEvidence.QUALIFIED):
    return PortalObservation(
        observation_id=observation_id,
        context=CONTEXT,
        map_revision=revision,
        near_side=Point2D(0.0, y),
        far_side=Point2D(1.0, y),
        structural_evidence=evidence,
    )


def populated_source():
    memory = PortalMemory(CONTEXT)
    first = memory.observe(observation("door-1", 1, 0.0))
    memory.observe(observation("door-2", 2, 0.0))
    second = memory.observe(observation("opening-1", 3, 5.0))
    memory.observe(observation(
        "opening-2", 4, 5.0,
        PortalStructuralEvidence.CONTRADICTORY))
    memory.update_reachability(ReachabilityUpdate(
        update_id="blocked-a",
        portal_id=first.portal_id,
        side=PortalSide.A,
        context=CONTEXT,
        map_revision=4,
        observed_at_ns=400,
        state=ReachabilityState.TEMPORARILY_BLOCKED,
        reason="fresh_obstacle",
        recheck_condition="next_map_revision",
    ))

    graph = RegionGraph(CONTEXT)
    start = graph.start(RegionSeed("start", CONTEXT, 0))
    link = graph.observe_portal(PortalLinkObservation(
        observation_id="link-door",
        context=CONTEXT,
        map_revision=2,
        portal=memory.snapshot(first.portal_id),
        current_region_id=start.region_id,
        current_side=PortalSide.A,
    ))
    graph.update_task(RegionTaskUpdate(
        update_id="frontier-update",
        task_id="frontier-task",
        context=CONTEXT,
        map_revision=4,
        region_id=start.region_id,
        kind=RegionTaskKind.FRONTIER,
        subject_id="frontier-1",
        state=RegionTaskState.OPEN,
    ))
    graph.update_task(RegionTaskUpdate(
        update_id="observation-update",
        task_id="observation-task",
        context=CONTEXT,
        map_revision=4,
        region_id=link.opposite_region_id,
        kind=RegionTaskKind.OBSERVATION,
        subject_id="observation-1",
        state=RegionTaskState.COMPLETED,
    ))
    graph.update_region_exploration(RegionExplorationUpdate(
        update_id="region-progress",
        context=CONTEXT,
        map_revision=4,
        region_id=start.region_id,
        state=RegionExplorationState.IN_PROGRESS,
        reason="frontier_work_started",
    ))
    assert second.portal_id != first.portal_id
    return ShadowStatusSource(
        context=CONTEXT,
        source_map_revision=5,
        portal_memory_revision=memory.latest_revision,
        graph=graph.snapshot(),
        portals=memory.snapshots(),
        reachability=memory.reachability_snapshots(),
        source_map_age_seconds=0.5,
        portal_memory_age_seconds=0.4,
        region_graph_age_seconds=0.3,
    )


def empty_source():
    memory = PortalMemory(CONTEXT)
    graph = RegionGraph(CONTEXT)
    return ShadowStatusSource(
        context=CONTEXT,
        source_map_revision=0,
        portal_memory_revision=memory.latest_revision,
        graph=graph.snapshot(),
        portals=memory.snapshots(),
        reachability=memory.reachability_snapshots(),
        source_map_age_seconds=0.0,
    )


def test_shadow_status_is_versioned_passive_complete_and_geometry_free():
    serialized = build_shadow_status_json(populated_source())
    payload = json.loads(serialized)

    assert payload["schema_version"] == SCHEMA_VERSION == 1
    assert payload["mode"] == "shadow"
    assert payload["passive"] is True
    assert "raw_map_correlation" not in payload
    assert payload["context"] == {
        "session_id": CONTEXT.session_id,
        "map_id": CONTEXT.map_id,
        "frame_id": CONTEXT.frame_id,
    }
    assert payload["source"]["stale"] is False
    assert payload["source"]["stale_sources"] == []
    assert payload["source"]["source_map"] == {
        "age_seconds": 0.5,
        "lag_revisions": 0,
        "revision": 5,
        "state": "fresh",
    }
    assert payload["summary"] == {
        "blocked_reachability_side_count": 1,
        "completed_task_count": 1,
        "confirmed_entry_count": 0,
        "confirmed_portal_count": 1,
        "connection_count": 1,
        "current_region_id": "region_000001",
        "open_task_count": 1,
        "portal_count": 2,
        "region_count": 2,
        "uncertain_portal_count": 1,
        "unknown_reachability_side_count": 3,
        "unresolved_portal_count": 1,
    }
    assert [item["task_id"] for item in payload["tasks"]] == [
        "frontier-task", "observation-task"]
    assert [item["portal_id"] for item in payload["portals"]] == [
        "portal_000001", "portal_000002"]
    assert payload["regions"][0]["exploration"] == {
        "state": "in_progress",
        "reason": "frontier_work_started",
        "revision": 4,
    }
    assert payload["regions"][1]["exploration"] == {
        "state": "unassessed",
        "reason": None,
        "revision": None,
    }
    assert '"side_a"' not in serialized
    assert '"side_b"' not in serialized
    assert '"x"' not in serialized
    assert '"y"' not in serialized


def test_optional_raw_map_diagnostics_are_bounded_and_geometry_free():
    diagnostics = RawMapCorrelationDiagnostics(
        enabled=True,
        capacity=4,
        source_observations=7,
        unique_sources=5,
        duplicate_sources=2,
        pending_sources=1,
        evicted_sources=1,
        emitted_correlations=3,
        last_emitted_revision=5,
    )

    payload = json.loads(build_shadow_status_json(replace(
        populated_source(), raw_map_correlation=diagnostics)))

    assert payload["schema_version"] == 1
    assert payload["raw_map_correlation"] == {
        "enabled": True,
        "state": "evicted",
        "capacity": 4,
        "source_observations": 7,
        "unique_sources": 5,
        "duplicate_sources": 2,
        "pending_sources": 1,
        "evicted_sources": 1,
        "emitted_correlations": 3,
        "last_emitted_revision": 5,
    }
    serialized_block = json.dumps(payload["raw_map_correlation"])
    assert "fingerprint" not in serialized_block
    assert "frame" not in serialized_block
    assert "cells" not in serialized_block


def test_disabled_or_wrong_raw_map_diagnostics_cannot_be_projected():
    disabled = RawMapCorrelationDiagnostics(
        enabled=False,
        capacity=0,
        source_observations=0,
        unique_sources=0,
        duplicate_sources=0,
        pending_sources=0,
        evicted_sources=0,
        emitted_correlations=0,
        last_emitted_revision=None,
    )
    with pytest.raises(ShadowStatusError):
        replace(populated_source(), raw_map_correlation=disabled)
    with pytest.raises(ShadowStatusError):
        replace(populated_source(), raw_map_correlation="enabled")


def test_serialized_limit_includes_optional_raw_map_diagnostics():
    source = populated_source()
    base = build_shadow_status_json(source)
    diagnostics = RawMapCorrelationDiagnostics(
        enabled=True,
        capacity=1,
        source_observations=0,
        unique_sources=0,
        duplicate_sources=0,
        pending_sources=0,
        evicted_sources=0,
        emitted_correlations=0,
        last_emitted_revision=None,
    )
    exact_base_limit = len(base.encode("utf-8"))

    assert build_shadow_status_json(
        source,
        ShadowStatusPolicy(max_serialized_bytes=exact_base_limit),
    ) == base
    with pytest.raises(ShadowStatusCapacityError):
        build_shadow_status_json(
            replace(source, raw_map_correlation=diagnostics),
            ShadowStatusPolicy(max_serialized_bytes=exact_base_limit),
        )


def test_projection_is_byte_deterministic_for_reordered_snapshots():
    source = populated_source()
    reordered_graph = replace(
        source.graph,
        regions=tuple(reversed(source.graph.regions)),
        connections=tuple(reversed(source.graph.connections)),
        tasks=tuple(reversed(source.graph.tasks)),
        region_aliases=tuple(reversed(source.graph.region_aliases)),
    )
    reordered = replace(
        source,
        graph=reordered_graph,
        portals=tuple(reversed(source.portals)),
        reachability=tuple(reversed(source.reachability)),
    )

    assert build_shadow_status_json(reordered) == (
        build_shadow_status_json(source))


def test_revision_lag_marks_each_stale_source_explicitly():
    source = replace(populated_source(), source_map_revision=7)

    payload = json.loads(build_shadow_status_json(source))

    assert payload["source"]["stale"] is True
    assert payload["source"]["stale_sources"] == [
        "portal_memory", "region_graph"]
    assert payload["source"]["portal_memory"] == {
        "age_seconds": 0.4, "lag_revisions": 3,
        "revision": 4, "state": "stale"}
    assert payload["source"]["region_graph"] == {
        "age_seconds": 0.3, "lag_revisions": 3,
        "revision": 4, "state": "stale"}


def test_policy_can_tighten_revision_freshness_without_changing_input():
    source = populated_source()
    before = source

    payload = json.loads(build_shadow_status_json(
        source, ShadowStatusPolicy(maximum_revision_lag=0)))

    assert payload["source"]["stale"] is True
    assert source == before


def test_empty_sources_are_missing_not_fresh_or_complete():
    payload = json.loads(build_shadow_status_json(empty_source()))

    assert payload["source"]["stale"] is True
    assert payload["source"]["stale_sources"] == [
        "portal_memory", "region_graph"]
    assert payload["source"]["source_map"]["state"] == "fresh"
    assert payload["source"]["portal_memory"]["state"] == "missing"
    assert payload["source"]["region_graph"]["state"] == "missing"
    assert payload["summary"]["portal_count"] == 0
    assert payload["summary"]["region_count"] == 0
    assert payload["summary"]["open_task_count"] == 0


def test_equal_revisions_do_not_hide_frozen_sources():
    source = replace(
        populated_source(),
        source_map_revision=4,
        source_map_age_seconds=10.0,
        portal_memory_age_seconds=10.0,
        region_graph_age_seconds=10.0,
    )
    policy = ShadowStatusPolicy(
        maximum_source_map_age_seconds=1.0,
        maximum_portal_memory_age_seconds=1.0,
        maximum_region_graph_age_seconds=1.0,
    )

    payload = json.loads(build_shadow_status_json(source, policy))

    assert payload["source"]["stale"] is True
    assert payload["source"]["stale_sources"] == [
        "source_map", "portal_memory", "region_graph"]
    for name in payload["source"]["stale_sources"]:
        assert payload["source"][name]["lag_revisions"] == 0
        assert payload["source"][name]["age_seconds"] == 10.0
        assert payload["source"][name]["state"] == "stale"


def test_missing_age_is_visible_even_when_revision_is_current():
    source = replace(
        populated_source(),
        source_map_age_seconds=None,
        portal_memory_age_seconds=None,
        region_graph_age_seconds=None,
    )

    payload = json.loads(build_shadow_status_json(source))

    assert payload["source"]["stale_sources"] == [
        "source_map", "portal_memory", "region_graph"]
    assert payload["source"]["source_map"]["state"] == "missing"
    assert payload["source"]["portal_memory"]["state"] == "missing"
    assert payload["source"]["region_graph"]["state"] == "missing"


def test_each_age_limit_is_evaluated_independently():
    source = replace(
        populated_source(),
        source_map_age_seconds=1.1,
        portal_memory_age_seconds=1.2,
        region_graph_age_seconds=1.3,
    )
    policy = ShadowStatusPolicy(
        maximum_source_map_age_seconds=1.0,
        maximum_portal_memory_age_seconds=1.2,
        maximum_region_graph_age_seconds=1.4,
    )

    payload = json.loads(build_shadow_status_json(source, policy))

    assert payload["source"]["source_map"]["state"] == "stale"
    assert payload["source"]["portal_memory"]["state"] == "fresh"
    assert payload["source"]["region_graph"]["state"] == "fresh"
    assert payload["source"]["stale_sources"] == ["source_map"]


@pytest.mark.parametrize("field,value", [
    ("source_map_age_seconds", -0.1),
    ("source_map_age_seconds", float("nan")),
    ("portal_memory_age_seconds", float("inf")),
    ("region_graph_age_seconds", True),
])
def test_invalid_or_backward_age_fails_closed(field, value):
    with pytest.raises(ShadowStatusError):
        replace(populated_source(), **{field: value})


def test_age_without_component_revision_fails_closed():
    source = replace(
        empty_source(),
        portal_memory_age_seconds=0.0,
        region_graph_age_seconds=0.0,
    )

    with pytest.raises(ShadowStatusError):
        build_shadow_status_json(source)


@pytest.mark.parametrize("change", [
    {"portal_memory_revision": 6},
    {"graph": replace(populated_source().graph, latest_revision=6)},
    {"graph": replace(populated_source().graph, latest_revision=True)},
])
def test_source_revision_behind_a_component_fails_closed(change):
    with pytest.raises(ShadowStatusError):
        build_shadow_status_json(replace(populated_source(), **change))


def test_context_mismatch_fails_closed():
    source = populated_source()
    foreign = PortalMapContext("other-session", CONTEXT.map_id, "map")

    with pytest.raises(ShadowStatusError):
        build_shadow_status_json(replace(
            source, graph=replace(source.graph, context=foreign)))


def test_nonempty_portals_require_explicit_memory_revision():
    with pytest.raises(ShadowStatusError):
        build_shadow_status_json(replace(
            populated_source(), portal_memory_revision=None))


@pytest.mark.parametrize("reachability_factory", [
    lambda source: source.reachability[:-1],
    lambda source: source.reachability + (source.reachability[0],),
    lambda source: (
        replace(source.reachability[0], portal_id="portal_unknown"),
    ) + source.reachability[1:],
    lambda source: (
        replace(source.reachability[0], observed_at_ns=None),
    ) + source.reachability[1:],
])
def test_incomplete_or_inconsistent_reachability_fails_closed(
        reachability_factory):
    source = populated_source()
    with pytest.raises(ShadowStatusError):
        build_shadow_status_json(replace(
            source, reachability=reachability_factory(source)))


def test_unknown_connection_portal_or_region_fails_closed():
    source = populated_source()
    connection = source.graph.connections[0]

    with pytest.raises(ShadowStatusError):
        build_shadow_status_json(replace(
            source,
            graph=replace(source.graph, connections=(
                replace(connection, portal_id="portal_unknown"),))))
    with pytest.raises(ShadowStatusError):
        build_shadow_status_json(replace(
            source,
            graph=replace(source.graph, connections=(
                replace(connection, side_a_region_id="region_unknown"),))))


@pytest.mark.parametrize("graph_factory", [
    lambda graph: replace(graph, open_task_count=0),
    lambda graph: replace(
        graph, tasks=graph.tasks + (graph.tasks[0],)),
    lambda graph: replace(
        graph, tasks=(
            replace(graph.tasks[0], region_id="region_unknown"),
        ) + graph.tasks[1:]),
    lambda graph: replace(
        graph, regions=(
            replace(graph.regions[0], task_ids=()),
        ) + graph.regions[1:]),
    lambda graph: replace(graph, confirmed_entry_count=1),
])
def test_inconsistent_task_region_or_entry_inventory_fails_closed(
        graph_factory):
    source = populated_source()
    with pytest.raises(ShadowStatusError):
        build_shadow_status_json(replace(
            source, graph=graph_factory(source.graph)))


@pytest.mark.parametrize("region_factory", [
    lambda region: replace(region, exploration_state="in_progress"),
    lambda region: replace(
        region,
        exploration_state=RegionExplorationState.COMPLETE_CANDIDATE,
        exploration_reason=None,
        exploration_revision=None,
    ),
    lambda region: replace(region, exploration_reason=None),
    lambda region: replace(region, exploration_reason=" "),
    lambda region: replace(
        region, exploration_revision=region.last_revision + 1),
])
def test_invalid_region_exploration_status_fails_closed(region_factory):
    source = populated_source()
    changed = region_factory(source.graph.regions[0])
    with pytest.raises(ShadowStatusError):
        build_shadow_status_json(replace(
            source,
            graph=replace(
                source.graph,
                regions=(changed,) + source.graph.regions[1:],
            ),
        ))


@pytest.mark.parametrize("policy", [
    ShadowStatusPolicy(max_portals=1),
    ShadowStatusPolicy(max_regions=1),
    ShadowStatusPolicy(max_tasks=1),
    ShadowStatusPolicy(max_reachability_sides=3),
])
def test_inventory_capacity_limits_fail_closed(policy):
    with pytest.raises(ShadowStatusCapacityError):
        build_shadow_status_json(populated_source(), policy)


def test_serialized_byte_limit_fails_closed():
    with pytest.raises(ShadowStatusCapacityError):
        build_shadow_status_json(
            populated_source(), ShadowStatusPolicy(max_serialized_bytes=64))


@pytest.mark.parametrize("factory", [
    lambda: ShadowStatusPolicy(maximum_revision_lag=-1),
    lambda: ShadowStatusPolicy(maximum_source_map_age_seconds=-1.0),
    lambda: ShadowStatusPolicy(maximum_portal_memory_age_seconds=float("nan")),
    lambda: ShadowStatusPolicy(maximum_region_graph_age_seconds=float("inf")),
    lambda: ShadowStatusPolicy(max_serialized_bytes=0),
    lambda: ShadowStatusSource(
        CONTEXT, True, None, empty_source().graph, (), ()),
    lambda: ShadowStatusSource(
        CONTEXT, 0, None, RegionGraphSnapshot, (), ()),
    lambda: ShadowStatusSource(
        CONTEXT, 0, None, empty_source().graph, [], ()),
])
def test_invalid_policy_and_source_fields_are_rejected(factory):
    with pytest.raises(ShadowStatusError):
        factory()


def test_wrong_public_argument_types_are_rejected():
    with pytest.raises(ShadowStatusError):
        build_shadow_status_json("source")
    with pytest.raises(ShadowStatusError):
        build_shadow_status_json(populated_source(), policy="policy")
