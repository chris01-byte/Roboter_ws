from dataclasses import FrozenInstanceError
import json
from pathlib import Path
import sys

import pytest


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE_ROOT))

from explore.map_status_adapter import (  # noqa: E402
    MapEpochChangeRequired,
    MapStatusAdapterError,
    MapStatusCorrelationPolicy,
)
from explore.portal_memory import PortalMemoryPolicy  # noqa: E402
from explore.region_graph import RegionGraphPolicy  # noqa: E402
from explore.region_graph_shadow_lifecycle import (  # noqa: E402
    RegionGraphShadowLifecycle,
    RegionGraphShadowLifecycleError,
    RegionGraphShadowNotReadyError,
    ShadowLifecycleState,
)
from explore.region_graph_status import (  # noqa: E402
    ShadowStatusCapacityError,
    ShadowStatusPolicy,
)


FINGERPRINT_A = "a" * 64
FINGERPRINT_B = "b" * 64


def status_json(**changes):
    values = {
        "available": True,
        "accepted_maps": 3,
        "fingerprint": FINGERPRINT_A,
        "frame_id": "map",
        "source_stamp_ns": 1_799_999_999_500_000_000,
        "age_seconds": 0.25,
        "time": 1_800_000_000.0,
    }
    values.update(changes)
    available = values["available"]
    summary = None
    if available:
        summary = {
            "fingerprint": values["fingerprint"],
            "frame_id": values["frame_id"],
            "source_stamp_ns": values["source_stamp_ns"],
        }
    payload = {
        "schema_version": 1,
        "time": values["time"],
        "map": {
            "available": available,
            "snapshot_available": available,
            "age_seconds": values["age_seconds"] if available else None,
            "summary": summary,
        },
        "counters": {
            "accepted_maps": values["accepted_maps"] if available else 0,
        },
    }
    return json.dumps(payload)


def lifecycle(**changes):
    values = {
        "session_id": "session-20260914",
        "expected_frame_id": "map",
        "start_observation_id": "start-observation",
    }
    values.update(changes)
    return RegionGraphShadowLifecycle(**values)


def accept_status(owner, text=None, *, at=100.0):
    return owner.accept_map_status_json(
        status_json() if text is None else text,
        received_monotonic_seconds=at,
    )


def build_status(owner, *, now=100.0):
    return owner.build_status_json(now_monotonic_seconds=now)


def test_owner_waits_without_inventing_context_or_status():
    owner = lifecycle()

    assert owner.state is ShadowLifecycleState.WAITING_FOR_MAP
    assert owner.context is None
    assert owner.latest_map_status is None
    with pytest.raises(RegionGraphShadowNotReadyError):
        build_status(owner)


def test_unavailable_status_before_first_map_remains_waiting():
    owner = lifecycle()

    for _ in range(2):
        update = accept_status(
            owner, status_json(available=False, accepted_maps=0))
        assert update.state is ShadowLifecycleState.WAITING_FOR_MAP
        assert update.map_status is None
        assert update.session_started is False

    assert owner.context is None
    assert owner.latest_map_status is None


def test_first_complete_status_starts_exactly_one_session():
    owner = lifecycle()

    update = accept_status(owner)
    payload = json.loads(build_status(owner))

    assert update.state is ShadowLifecycleState.ACTIVE
    assert update.session_started is True
    assert update.map_status == owner.latest_map_status
    assert owner.context == update.map_status.context
    assert payload["context"] == {
        "session_id": "session-20260914",
        "map_id": f"map-{FINGERPRINT_A}",
        "frame_id": "map",
    }
    assert payload["source"]["source_map"]["revision"] == 3
    assert payload["source"]["source_map"]["age_seconds"] == 0.25
    assert payload["source"]["portal_memory"]["state"] == "missing"
    assert payload["source"]["region_graph"]["age_seconds"] == 0.0
    assert payload["summary"]["region_count"] == 1


def test_periodic_same_map_updates_age_without_starting_another_session():
    owner = lifecycle()
    first = accept_status(owner)

    update = accept_status(owner, status_json(
        time=1_800_000_001.0,
        age_seconds=1.25,
    ), at=101.0)
    payload = json.loads(build_status(owner, now=101.5))

    assert update.session_started is False
    assert update.map_status.context == first.map_status.context
    assert update.map_status.map_revision == 3
    assert update.map_status.map_changed is False
    assert payload["source"]["source_map"]["age_seconds"] == 1.25
    assert payload["source"]["region_graph"]["age_seconds"] == 1.5
    assert payload["summary"]["region_count"] == 1


def test_map_growth_advances_owned_revision_in_same_context():
    owner = lifecycle()
    context = accept_status(owner).map_status.context

    update = accept_status(owner, status_json(
        time=1_800_000_001.0,
        accepted_maps=4,
        fingerprint=FINGERPRINT_B,
        source_stamp_ns=1_800_000_000_500_000_000,
        age_seconds=0.2,
    ), at=101.0)
    payload = json.loads(build_status(owner, now=102.0))

    assert update.map_status.context == context
    assert update.map_status.map_revision == 4
    assert update.map_status.map_changed is True
    assert payload["source"]["map_revision"] == 4
    assert payload["source"]["region_graph"]["age_seconds"] == 2.0


def test_exact_replay_is_forwarded_without_starting_another_session():
    owner = lifecycle()
    accept_status(owner)

    replay = accept_status(owner, at=101.0)

    assert replay.session_started is False
    assert replay.map_status.replayed is True
    assert replay.map_status.map_revision == 3


def test_counter_rollback_requires_new_owner_without_mutating_active_state():
    owner = lifecycle()
    first = accept_status(owner)

    with pytest.raises(MapEpochChangeRequired):
        accept_status(owner, status_json(
            time=1_800_000_001.0,
            accepted_maps=2,
            fingerprint=FINGERPRINT_B,
        ), at=101.0)

    assert owner.state is ShadowLifecycleState.ACTIVE
    assert owner.context == first.map_status.context
    assert owner.latest_map_status == first.map_status
    assert accept_status(owner, at=100.5).map_status.replayed is True


def test_frame_change_requires_new_owner_without_mutating_active_state():
    owner = lifecycle()
    first = accept_status(owner)

    with pytest.raises(MapEpochChangeRequired):
        accept_status(owner, status_json(
            time=1_800_000_001.0,
            accepted_maps=4,
            fingerprint=FINGERPRINT_B,
            frame_id="map-corrected",
        ), at=101.0)

    assert owner.context == first.map_status.context
    assert owner.latest_map_status == first.map_status


def test_unavailable_status_after_start_requires_new_owner():
    owner = lifecycle()
    first = accept_status(owner)

    with pytest.raises(MapEpochChangeRequired):
        accept_status(owner, status_json(
            available=False,
            accepted_maps=0,
            time=1_800_000_001.0,
        ), at=101.0)

    assert owner.latest_map_status == first.map_status


def test_invalid_json_never_changes_waiting_or_active_state():
    waiting = lifecycle()
    with pytest.raises(MapStatusAdapterError):
        accept_status(waiting, "not-json")
    assert waiting.state is ShadowLifecycleState.WAITING_FOR_MAP

    active = lifecycle()
    first = accept_status(active)
    with pytest.raises(MapStatusAdapterError):
        accept_status(active, "not-json", at=101.0)
    assert active.latest_map_status == first.map_status


def test_received_time_rollback_fails_without_mutating_map_state():
    owner = lifecycle()
    first = accept_status(owner, at=100.0)

    with pytest.raises(RegionGraphShadowLifecycleError):
        accept_status(owner, status_json(
            time=1_800_000_001.0,
            age_seconds=1.25,
        ), at=99.0)

    assert owner.latest_map_status == first.map_status
    assert accept_status(owner, at=100.0).map_status.replayed is True


def test_waiting_status_participates_in_monotonic_order():
    owner = lifecycle()
    accept_status(
        owner,
        status_json(available=False, accepted_maps=0),
        at=100.0,
    )

    with pytest.raises(RegionGraphShadowLifecycleError):
        accept_status(owner, at=99.0)

    assert owner.state is ShadowLifecycleState.WAITING_FOR_MAP
    assert accept_status(owner, at=100.0).session_started is True


def test_status_time_advances_global_monotonic_order():
    owner = lifecycle()
    accept_status(owner, at=100.0)
    build_status(owner, now=102.0)

    with pytest.raises(RegionGraphShadowLifecycleError):
        accept_status(owner, at=101.0)

    assert owner.latest_map_status.map_revision == 3


def test_not_ready_status_failure_does_not_advance_monotonic_order():
    owner = lifecycle()

    with pytest.raises(RegionGraphShadowNotReadyError):
        build_status(owner, now=100.0)

    assert accept_status(owner, at=50.0).session_started is True


@pytest.mark.parametrize("invalid", [-1.0, float("nan"), float("inf"), True, "1"])
def test_invalid_received_monotonic_time_fails_closed(invalid):
    owner = lifecycle()

    with pytest.raises(RegionGraphShadowLifecycleError):
        accept_status(owner, at=invalid)

    assert owner.state is ShadowLifecycleState.WAITING_FOR_MAP


@pytest.mark.parametrize("invalid", [-1.0, float("nan"), float("inf"), True, "1"])
def test_invalid_status_monotonic_time_fails_closed(invalid):
    owner = lifecycle()
    accept_status(owner)

    with pytest.raises(RegionGraphShadowLifecycleError):
        build_status(owner, now=invalid)

    assert owner.latest_map_status.map_revision == 3


def test_new_explicit_owner_changes_context_after_epoch_failure():
    first = lifecycle(session_id="session-before")
    old_context = accept_status(first).map_status.context

    restarted = lifecycle(session_id="session-after")
    new_context = accept_status(
        restarted, status_json(accepted_maps=1)).map_status.context

    assert new_context != old_context
    assert new_context.map_id == old_context.map_id


def test_map_policy_is_applied_without_reading_a_clock():
    owner = lifecycle(map_policy=MapStatusCorrelationPolicy(
        maximum_future_stamp_seconds=0.1))

    with pytest.raises(MapStatusAdapterError):
        accept_status(owner, status_json(
            source_stamp_ns=1_800_000_000_200_000_000))
    assert owner.state is ShadowLifecycleState.WAITING_FOR_MAP


def test_status_capacity_policy_is_preserved_by_owner():
    owner = lifecycle(status_policy=ShadowStatusPolicy(
        max_serialized_bytes=64))
    accept_status(owner)

    with pytest.raises(ShadowStatusCapacityError):
        build_status(owner)

    assert accept_status(owner, at=100.5).map_status.replayed is True


@pytest.mark.parametrize("changes", [
    {"session_id": ""},
    {"expected_frame_id": "bad frame"},
    {"start_observation_id": ""},
    {"map_policy": "policy"},
    {"portal_policy": "policy"},
    {"graph_policy": "policy"},
    {"status_policy": "policy"},
])
def test_invalid_owner_configuration_fails_before_input(changes):
    with pytest.raises(RegionGraphShadowLifecycleError):
        lifecycle(**changes)


def test_valid_policy_objects_are_not_mutated_or_replaced():
    map_policy = MapStatusCorrelationPolicy()
    portal_policy = PortalMemoryPolicy(max_observations=2)
    graph_policy = RegionGraphPolicy(max_regions=2)
    status_policy = ShadowStatusPolicy(max_regions=2)
    before = (map_policy, portal_policy, graph_policy, status_policy)

    owner = lifecycle(
        map_policy=map_policy,
        portal_policy=portal_policy,
        graph_policy=graph_policy,
        status_policy=status_policy,
    )
    accept_status(owner)
    build_status(owner)

    assert (map_policy, portal_policy, graph_policy, status_policy) == before


def test_update_is_immutable_and_owner_has_no_reset_or_portal_api():
    owner = lifecycle()
    update = accept_status(owner)

    with pytest.raises(FrozenInstanceError):
        update.session_started = False
    assert not hasattr(owner, "reset")
    assert not hasattr(owner, "observe_portal_plan")
    assert not hasattr(owner, "qualify_portal")
    assert not hasattr(owner, "record_traversal")
