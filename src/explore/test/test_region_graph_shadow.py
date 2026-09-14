import json
from pathlib import Path
import sys

import pytest


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE_ROOT))

from explore.portal_memory import (  # noqa: E402
    MemoryCapacityError,
    ObservationDisposition,
    PortalConfirmationState,
    PortalMapContext,
    PortalMemoryPolicy,
    StaleObservationError,
)
from explore.portal_plan_adapter import (  # noqa: E402
    PortalPlanAdapterError,
    PortalPlanCandidate,
)
from explore.region_graph import RegionGraphPolicy, RegionSeed  # noqa: E402
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


CONTEXT = PortalMapContext(
    session_id="session-20260914",
    map_id="live-map-epoch-1",
    frame_id="map",
)


def session(**policies):
    return RegionGraphShadowSession(
        CONTEXT,
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


def status_arguments(**changes):
    values = {
        "source_map_revision": 10,
        "source_map_age_seconds": 0.5,
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


def test_missing_ages_remain_visible_in_composed_status():
    shadow = session()
    shadow.observe_portal_plan(candidate())

    payload = json.loads(shadow.build_status_json(**status_arguments(
        source_map_age_seconds=None,
        portal_memory_age_seconds=None,
        region_graph_age_seconds=None,
    )))

    assert payload["source"]["stale"] is True
    assert payload["source"]["stale_sources"] == [
        "source_map", "portal_memory", "region_graph"]
    assert all(
        payload["source"][name]["state"] == "missing"
        for name in payload["source"]["stale_sources"])


def test_source_revision_behind_owned_state_fails_closed():
    shadow = session()
    shadow.observe_portal_plan(candidate(map_revision=12))

    with pytest.raises(ShadowStatusError):
        shadow.build_status_json(**status_arguments(
            source_map_revision=11))


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


@pytest.mark.parametrize("change", [
    {"context": "context"},
    {"start_seed": "seed"},
    {"portal_policy": "policy"},
    {"graph_policy": "policy"},
    {"status_policy": "policy"},
])
def test_invalid_session_arguments_fail_closed(change):
    arguments = {
        "context": CONTEXT,
        "start_seed": RegionSeed("start", CONTEXT, 0),
    }
    arguments.update(change)

    with pytest.raises(RegionGraphShadowError):
        RegionGraphShadowSession(**arguments)


def test_foreign_start_context_fails_closed():
    foreign = PortalMapContext("other-session", CONTEXT.map_id, "map")

    with pytest.raises(RegionGraphShadowError):
        RegionGraphShadowSession(
            CONTEXT, RegionSeed("foreign-start", foreign, 0))


def test_policy_objects_are_not_mutated_or_replaced():
    portal_policy = PortalMemoryPolicy(max_observations=2)
    graph_policy = RegionGraphPolicy(max_regions=2)
    status_policy = ShadowStatusPolicy(max_portals=2)
    before = (portal_policy, graph_policy, status_policy)

    shadow = session(
        portal_policy=portal_policy,
        graph_policy=graph_policy,
        status_policy=status_policy,
    )
    shadow.observe_portal_plan(candidate())
    shadow.build_status_json(**status_arguments())

    assert (portal_policy, graph_policy, status_policy) == before


def test_status_source_is_an_immutable_snapshot_not_live_state():
    shadow = session()
    source_before = shadow.status_source(**status_arguments(
        portal_memory_age_seconds=None))

    shadow.observe_portal_plan(candidate())

    assert source_before.portals == ()
    assert shadow.status_source(**status_arguments()).portals != ()


def test_session_has_no_qualification_traversal_or_goal_api():
    shadow = session()

    assert not hasattr(shadow, "qualify_portal")
    assert not hasattr(shadow, "record_traversal")
    assert not hasattr(shadow, "create_goal")
