import json
from pathlib import Path
import sys

import pytest


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE_ROOT))

from explore.map_status_adapter import (  # noqa: E402
    MapStatusCorrelationResult,
)
from explore.frontier_task_feed import (  # noqa: E402
    FrontierTaskPolicy,
    frontier_inventory_from_clusters,
)
from explore.portal_memory import (  # noqa: E402
    MemoryCapacityError,
    ObservationDisposition,
    Point2D,
    PortalConfirmationState,
    PortalMapContext,
    PortalMemoryPolicy,
    PortalObservation,
    PortalStructuralEvidence,
    StaleObservationError,
    TraversalDirection,
    TraversalEvent,
)
from explore.portal_plan_adapter import (  # noqa: E402
    PortalPlanAdapterError,
    PortalPlanCandidate,
)
from explore.portal_source_adapter import PortalSourceCorrelation  # noqa: E402
from explore.region_graph import (  # noqa: E402
    RegionGraphCapacityError,
    RegionGraphPolicy,
    RegionSeed,
    RegionTaskState,
    StaleGraphUpdateError,
)
from explore.region_graph_shadow import (  # noqa: E402
    RegionGraphShadowError,
    RegionGraphShadowSession,
)
from explore.region_graph_status import (  # noqa: E402
    ShadowStatusCapacityError,
    ShadowStatusError,
    ShadowStatusPolicy,
    build_shadow_status_json,
)


FINGERPRINT = "a" * 64
CONTEXT = PortalMapContext(
    session_id="session-20260914",
    map_id=f"map-{FINGERPRINT}",
    frame_id="map",
)


def map_status(**changes):
    values = {
        "context": CONTEXT,
        "map_revision": 10,
        "fingerprint": FINGERPRINT,
        "source_stamp_ns": 1_800_000_000_000_000_000,
        "source_map_age_seconds": 0.5,
        "map_changed": True,
        "replayed": False,
    }
    values.update(changes)
    return MapStatusCorrelationResult(**values)


def session(**policies):
    return RegionGraphShadowSession(
        map_status(),
        RegionSeed("start-observation", CONTEXT, 10),
        **policies,
    )


def candidate(**changes):
    values = {
        "observation_id": "portal-plan-0001",
        "context": CONTEXT,
        "map_revision": 10,
        "staging_xy": (1.0, 2.0),
        "target_xy": (1.8, 2.0),
        "uncertainty_m": 0.05,
    }
    values.update(changes)
    return PortalPlanCandidate(**values)


def structural_observation(observation_id, revision, **changes):
    values = {
        "observation_id": observation_id,
        "context": CONTEXT,
        "map_revision": revision,
        "near_side": Point2D(1.0, 2.0),
        "far_side": Point2D(1.8, 2.0),
        "uncertainty_m": 0.02,
        "structural_evidence": PortalStructuralEvidence.QUALIFIED,
    }
    values.update(changes)
    return PortalObservation(**values)


def frontier_inventory(revision, clusters):
    return frontier_inventory_from_clusters(
        PortalSourceCorrelation(
            context=CONTEXT,
            map_revision=revision,
            fingerprint=f"{revision:064x}",
            source_stamp_ns=revision,
        ),
        clusters,
    )


def status_arguments(**changes):
    values = {
        "map_status": map_status(),
        "portal_memory_age_seconds": 0.4,
        "region_graph_age_seconds": 0.3,
    }
    values.update(changes)
    return values


def test_session_starts_one_region_in_exact_context_without_connections():
    shadow = session()

    source = shadow.status_source(**status_arguments(
        portal_memory_age_seconds=None))
    payload = json.loads(build_shadow_status_json(source))

    assert shadow.context == CONTEXT
    assert shadow.start_result.region_id == "region_000001"
    assert payload["context"] == {
        "session_id": CONTEXT.session_id,
        "map_id": CONTEXT.map_id,
        "frame_id": CONTEXT.frame_id,
    }
    assert payload["summary"]["region_count"] == 1
    assert payload["summary"]["connection_count"] == 0
    assert payload["summary"]["portal_count"] == 0
    assert payload["summary"]["confirmed_entry_count"] == 0
    assert payload["regions"][0]["entered"] is True


def test_unqualified_candidate_changes_memory_but_not_graph_or_entry():
    shadow = session()

    result = shadow.observe_portal_plan(candidate())
    payload = json.loads(shadow.build_status_json(**status_arguments()))

    assert result.disposition is ObservationDisposition.CREATED
    assert payload["summary"]["portal_count"] == 1
    assert payload["summary"]["unresolved_portal_count"] == 1
    assert payload["summary"]["confirmed_portal_count"] == 0
    assert payload["summary"]["region_count"] == 1
    assert payload["summary"]["connection_count"] == 0
    assert payload["summary"]["confirmed_entry_count"] == 0
    assert payload["portals"][0]["confirmation_state"] == (
        PortalConfirmationState.CANDIDATE.value)
    assert payload["portals"][0]["qualified_evidence_count"] == 0
    assert payload["portals"][0]["confirmed_traversal_count"] == 0


def test_exact_candidate_replay_is_idempotent_and_status_is_stable():
    shadow = session()
    first = shadow.observe_portal_plan(candidate())
    status_before = shadow.build_status_json(**status_arguments())

    replay = shadow.observe_portal_plan(candidate())
    status_after = shadow.build_status_json(**status_arguments())

    assert replay.portal_id == first.portal_id
    assert replay.duplicate is True
    assert replay.evidence_added is False
    assert status_after == status_before


def test_structural_events_automatically_create_region_and_tasks():
    shadow = session()

    first = shadow.observe_structural_portal(
        structural_observation("door-structure-10", 10))
    first_payload = json.loads(shadow.build_status_json(**status_arguments()))

    assert first.link is None
    assert first.observation.qualified_evidence_added is True
    assert first_payload["summary"]["region_count"] == 1
    assert first_payload["summary"]["open_task_count"] == 1
    assert first_payload["tasks"] == [{
        "task_id": "task-observe-portal_000001",
        "region_id": "region_000001",
        "kind": "observation",
        "subject_id": "portal_000001",
        "state": "open",
        "created_revision": 10,
        "last_revision": 10,
    }]

    second = shadow.observe_structural_portal(
        structural_observation("door-structure-11", 11))
    payload = json.loads(shadow.build_status_json(**status_arguments(
        map_status=map_status(map_revision=11))))

    assert second.link.opposite_region_id == "region_000002"
    assert payload["summary"]["confirmed_portal_count"] == 1
    assert payload["summary"]["region_count"] == 2
    assert payload["summary"]["connection_count"] == 1
    assert payload["summary"]["open_task_count"] == 1
    assert payload["summary"]["completed_task_count"] == 1
    assert [(task["kind"], task["region_id"], task["state"])
            for task in payload["tasks"]] == [
        ("observation", "region_000001", "completed"),
        ("portal", "region_000002", "open"),
    ]
    assert payload["regions"][1]["seen"] is True
    assert payload["regions"][1]["entered"] is False


def test_validated_traversal_enters_region_and_completes_portal_task():
    shadow = session()
    shadow.observe_structural_portal(
        structural_observation("door-structure-10", 10))
    second = shadow.observe_structural_portal(
        structural_observation("door-structure-11", 11))
    portal_id = second.observation.portal_id

    result = shadow.record_validated_traversal(TraversalEvent(
        event_id="validated-door-crossing-12",
        portal_id=portal_id,
        context=CONTEXT,
        map_revision=12,
        event_time_ns=12_000_000_000,
        direction=TraversalDirection.A_TO_B,
        crossing_confirmed=True,
    ))
    payload = json.loads(shadow.build_status_json(**status_arguments(
        map_status=map_status(map_revision=12))))

    assert result.memory.counted is True
    assert result.graph.entered is True
    assert result.task_update.task.state is RegionTaskState.COMPLETED
    assert payload["summary"]["current_region_id"] == "region_000002"
    assert payload["summary"]["confirmed_entry_count"] == 1
    assert payload["summary"]["open_task_count"] == 0
    assert payload["summary"]["completed_task_count"] == 2
    assert payload["regions"][1]["entered"] is True


def test_cross_component_event_is_atomic_when_task_revision_is_not_newer():
    shadow = session()
    shadow.observe_structural_portal(
        structural_observation("door-structure-10", 10))
    second = shadow.observe_structural_portal(
        structural_observation("door-structure-11", 11))
    before = shadow.build_status_json(**status_arguments(
        map_status=map_status(map_revision=11)))

    with pytest.raises(StaleGraphUpdateError):
        shadow.record_validated_traversal(TraversalEvent(
            event_id="same-revision-crossing",
            portal_id=second.observation.portal_id,
            context=CONTEXT,
            map_revision=11,
            event_time_ns=11_000_000_000,
            direction=TraversalDirection.A_TO_B,
            crossing_confirmed=True,
        ))

    after = shadow.build_status_json(**status_arguments(
        map_status=map_status(map_revision=11)))
    assert after == before


def test_foreign_context_fails_before_any_session_state_changes():
    shadow = session()
    before = shadow.build_status_json(**status_arguments(
        portal_memory_age_seconds=None))
    foreign = PortalMapContext("other-session", CONTEXT.map_id, "map")

    with pytest.raises(PortalPlanAdapterError):
        shadow.observe_portal_plan(candidate(context=foreign))

    after = shadow.build_status_json(**status_arguments(
        portal_memory_age_seconds=None))
    assert after == before


def test_new_observation_behind_memory_revision_fails_closed():
    shadow = session()
    shadow.observe_portal_plan(candidate(map_revision=12))

    with pytest.raises(StaleObservationError):
        shadow.observe_portal_plan(candidate(
            observation_id="older-plan",
            map_revision=11,
            staging_xy=(3.0, 2.0),
            target_xy=(3.8, 2.0),
        ))


def test_candidate_before_start_revision_fails_without_state_change():
    shadow = session()
    before = shadow.build_status_json(**status_arguments(
        portal_memory_age_seconds=None))

    with pytest.raises(StaleObservationError):
        shadow.observe_portal_plan(candidate(map_revision=9))

    after = shadow.build_status_json(**status_arguments(
        portal_memory_age_seconds=None))
    assert after == before


def test_caller_ages_remain_explicit_and_correlated_map_age_is_copied():
    shadow = session()
    shadow.observe_portal_plan(candidate())

    payload = json.loads(shadow.build_status_json(**status_arguments(
        portal_memory_age_seconds=None,
        region_graph_age_seconds=None,
    )))

    assert payload["source"]["stale"] is True
    assert payload["source"]["stale_sources"] == [
        "portal_memory", "region_graph"]
    assert payload["source"]["source_map"] == {
        "revision": 10,
        "lag_revisions": 0,
        "age_seconds": 0.5,
        "state": "fresh",
    }
    assert payload["source"]["portal_memory"]["state"] == "missing"
    assert payload["source"]["region_graph"]["state"] == "missing"


def test_source_revision_behind_owned_state_fails_closed():
    shadow = session()
    shadow.observe_portal_plan(candidate(map_revision=12))

    with pytest.raises(ShadowStatusError):
        shadow.build_status_json(**status_arguments(
            map_status=map_status(map_revision=11)))


def test_portal_memory_capacity_is_enforced_by_session():
    shadow = session(portal_policy=PortalMemoryPolicy(max_observations=1))
    shadow.observe_portal_plan(candidate())

    with pytest.raises(MemoryCapacityError):
        shadow.observe_portal_plan(candidate(
            observation_id="second-plan",
            staging_xy=(3.0, 2.0),
            target_xy=(3.8, 2.0),
        ))


def test_one_region_graph_capacity_is_not_consumed_by_candidate():
    shadow = session(graph_policy=RegionGraphPolicy(max_regions=1))

    shadow.observe_portal_plan(candidate())
    payload = json.loads(shadow.build_status_json(**status_arguments()))

    assert payload["summary"]["region_count"] == 1
    assert payload["summary"]["connection_count"] == 0


def test_status_capacity_is_enforced_by_session():
    shadow = session(status_policy=ShadowStatusPolicy(
        max_serialized_bytes=64))

    with pytest.raises(ShadowStatusCapacityError):
        shadow.build_status_json(**status_arguments(
            portal_memory_age_seconds=None))


def test_serialization_failure_does_not_accept_new_map_revision():
    shadow = session(status_policy=ShadowStatusPolicy(
        max_serialized_bytes=64))

    with pytest.raises(ShadowStatusCapacityError):
        shadow.build_status_json(**status_arguments(
            map_status=map_status(map_revision=12, fingerprint="b" * 64),
            portal_memory_age_seconds=None))

    source = shadow.status_source(
        map_status(map_revision=11, fingerprint="c" * 64),
        portal_memory_age_seconds=None,
        region_graph_age_seconds=None,
    )
    assert source.source_map_revision == 11


@pytest.mark.parametrize("change", [
    {"initial_map_status": "map-status"},
    {"start_seed": "seed"},
    {"portal_policy": "policy"},
    {"graph_policy": "policy"},
    {"status_policy": "policy"},
])
def test_invalid_session_arguments_fail_closed(change):
    arguments = {
        "initial_map_status": map_status(),
        "start_seed": RegionSeed("start", CONTEXT, 10),
    }
    arguments.update(change)

    with pytest.raises(RegionGraphShadowError):
        RegionGraphShadowSession(**arguments)


def test_foreign_start_context_fails_closed():
    foreign = PortalMapContext("other-session", CONTEXT.map_id, "map")

    with pytest.raises(RegionGraphShadowError):
        RegionGraphShadowSession(
            map_status(), RegionSeed("foreign-start", foreign, 10))


def test_start_revision_must_match_first_map_result():
    with pytest.raises(RegionGraphShadowError):
        RegionGraphShadowSession(
            map_status(), RegionSeed("late-start", CONTEXT, 11))


@pytest.mark.parametrize("initial", [
    map_status(map_changed=False),
    map_status(replayed=True),
])
def test_session_requires_first_new_map_result(initial):
    with pytest.raises(RegionGraphShadowError):
        RegionGraphShadowSession(
            initial, RegionSeed("start", CONTEXT, 10))


def test_map_growth_updates_revision_and_copies_source_age():
    shadow = session()
    grown = map_status(
        map_revision=12,
        fingerprint="b" * 64,
        source_stamp_ns=1_800_000_001_000_000_000,
        source_map_age_seconds=0.125,
    )

    source = shadow.status_source(
        grown,
        portal_memory_age_seconds=None,
        region_graph_age_seconds=0.25,
    )

    assert source.context == CONTEXT
    assert source.source_map_revision == 12
    assert source.source_map_age_seconds == 0.125
    assert source.portal_memory_age_seconds is None
    assert source.region_graph_age_seconds == 0.25


def test_same_revision_periodic_status_can_refresh_correlated_map_age():
    shadow = session()
    periodic = map_status(
        source_map_age_seconds=0.25,
        map_changed=False,
    )

    source = shadow.status_source(
        periodic,
        portal_memory_age_seconds=0.75,
        region_graph_age_seconds=1.0,
    )

    assert source.source_map_revision == 10
    assert source.source_map_age_seconds == 0.25
    assert source.portal_memory_age_seconds == 0.75
    assert source.region_graph_age_seconds == 1.0


def test_exact_correlated_status_replay_is_accepted():
    shadow = session()
    replay = map_status(map_changed=False, replayed=True)

    source = shadow.status_source(
        replay,
        portal_memory_age_seconds=None,
        region_graph_age_seconds=None,
    )

    assert source.source_map_revision == 10
    assert source.source_map_age_seconds == 0.5


def test_foreign_map_status_fails_without_changing_latest_revision():
    shadow = session()
    current = map_status(map_revision=12, fingerprint="b" * 64)
    shadow.status_source(
        current,
        portal_memory_age_seconds=None,
        region_graph_age_seconds=None,
    )
    foreign = PortalMapContext("other-session", CONTEXT.map_id, "map")

    with pytest.raises(RegionGraphShadowError):
        shadow.status_source(
            map_status(context=foreign, map_revision=13),
            portal_memory_age_seconds=None,
            region_graph_age_seconds=None,
        )

    with pytest.raises(RegionGraphShadowError):
        shadow.status_source(
            map_status(map_revision=11),
            portal_memory_age_seconds=None,
            region_graph_age_seconds=None,
        )


def test_revision_rollback_fails_without_changing_latest_revision():
    shadow = session()
    current = map_status(map_revision=12, fingerprint="b" * 64)
    shadow.status_source(
        current,
        portal_memory_age_seconds=None,
        region_graph_age_seconds=None,
    )

    for _ in range(2):
        with pytest.raises(RegionGraphShadowError):
            shadow.status_source(
                map_status(map_revision=11),
                portal_memory_age_seconds=None,
                region_graph_age_seconds=None,
            )


def test_status_requires_typed_map_result():
    shadow = session()

    with pytest.raises(RegionGraphShadowError):
        shadow.status_source(
            "map-status",
            portal_memory_age_seconds=None,
            region_graph_age_seconds=None,
        )


def test_frontier_inventory_creates_global_open_tasks_without_filtering():
    shadow = session(frontier_policy=FrontierTaskPolicy(
        association_radius_m=0.60))

    first = shadow.observe_frontier_inventory(frontier_inventory(
        10, [(1.0, 1.0, 8), (3.0, 1.0, 12)]))
    missing = shadow.observe_frontier_inventory(frontier_inventory(11, []))
    matched = shadow.observe_frontier_inventory(frontier_inventory(
        12, [(1.2, 1.0, 9)]))
    source = shadow.status_source(
        map_status(map_revision=12, fingerprint=f"{12:064x}"),
        portal_memory_age_seconds=None,
        region_graph_age_seconds=0.0,
    )

    assert len(first.task_updates) == 2
    assert missing.task_updates == ()
    assert matched.task_updates == ()
    assert matched.inventory.assignments[0].frontier_id == "frontier_000001"
    assert tuple(task.subject_id for task in source.graph.tasks) == (
        "frontier_000001", "frontier_000002")
    assert all(task.state is RegionTaskState.OPEN for task in source.graph.tasks)
    assert all(
        task.region_id == source.graph.current_region_id
        for task in source.graph.tasks)


def test_frontier_replay_and_graph_capacity_failure_are_atomic():
    shadow = session(graph_policy=RegionGraphPolicy(max_tasks=1))
    first_inventory = frontier_inventory(10, [(1.0, 1.0, 8)])
    first = shadow.observe_frontier_inventory(first_inventory)
    replay = shadow.observe_frontier_inventory(first_inventory)
    before = shadow.status_source(
        map_status(), portal_memory_age_seconds=None,
        region_graph_age_seconds=0.0)

    with pytest.raises(RegionGraphCapacityError, match="Aufgabenspeicher ist voll"):
        shadow.observe_frontier_inventory(frontier_inventory(
            11, [(1.0, 1.0, 8), (3.0, 1.0, 8)]))

    after = shadow.status_source(
        map_status(), portal_memory_age_seconds=None,
        region_graph_age_seconds=0.0)
    assert first.task_updates[0].created is True
    assert replay.inventory.duplicate is True
    assert replay.task_updates == ()
    assert after == before


def test_policy_objects_are_not_mutated_or_replaced():
    portal_policy = PortalMemoryPolicy(max_observations=2)
    frontier_policy = FrontierTaskPolicy(max_frontiers=2)
    graph_policy = RegionGraphPolicy(max_regions=2)
    status_policy = ShadowStatusPolicy(max_portals=2)
    before = (portal_policy, frontier_policy, graph_policy, status_policy)

    shadow = session(
        portal_policy=portal_policy,
        frontier_policy=frontier_policy,
        graph_policy=graph_policy,
        status_policy=status_policy,
    )
    shadow.observe_portal_plan(candidate())
    shadow.build_status_json(**status_arguments())

    assert (
        portal_policy, frontier_policy, graph_policy, status_policy) == before


def test_status_source_is_an_immutable_snapshot_not_live_state():
    shadow = session()
    source_before = shadow.status_source(**status_arguments(
        portal_memory_age_seconds=None))

    shadow.observe_portal_plan(candidate())

    assert source_before.portals == ()
    assert shadow.status_source(**status_arguments()).portals != ()


def test_session_has_explicit_evidence_apis_but_no_inference_or_goal_api():
    shadow = session()

    assert not hasattr(shadow, "qualify_portal")
    assert hasattr(shadow, "observe_structural_portal")
    assert hasattr(shadow, "observe_frontier_inventory")
    assert hasattr(shadow, "record_validated_traversal")
    assert not hasattr(shadow, "record_traversal")
    assert not hasattr(shadow, "create_goal")
