import copy
from dataclasses import FrozenInstanceError
import json
from pathlib import Path
import math
import sys

import pytest


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE_ROOT))

from explore.map_status_adapter import (  # noqa: E402
    MAXIMUM_MAP_STATUS_BYTES,
    MapEpochChangeRequired,
    MapManagerStatusCorrelator,
    MapManagerStatusSample,
    MapStatusAdapterError,
    MapStatusCorrelationPolicy,
    MapStatusUnavailableError,
    decode_map_manager_status_json,
)
from explore.region_graph import RegionSeed  # noqa: E402
from explore.region_graph_shadow import RegionGraphShadowSession  # noqa: E402


FINGERPRINT_A = "a" * 64
FINGERPRINT_B = "b" * 64
FINGERPRINT_C = "c" * 64


def status_payload(*, available=True):
    summary = None
    age_seconds = None
    accepted_maps = 0
    if available:
        summary = {
            "width": 640,
            "height": 480,
            "resolution": 0.03,
            "frame_id": "map",
            "origin": {"position": [0.0, 0.0]},
            "source_stamp_ns": 1_799_999_999_500_000_000,
            "fingerprint": FINGERPRINT_A,
        }
        age_seconds = 0.25
        accepted_maps = 3
    return {
        "schema_version": 1,
        "event": "status",
        "ok": True,
        "message": "Periodischer Kartenstatus.",
        "time": 1_800_000_000.0,
        "map": {
            "available": available,
            "snapshot_available": available,
            "publisher_count": 1,
            "age_seconds": age_seconds,
            "source": "/map",
            "summary": summary,
        },
        "pose": {"available": False},
        "storage": {"root": "/not-consumed"},
        "counters": {
            "accepted_maps": accepted_maps,
            "duplicate_maps": 0,
        },
    }


def sample(**changes):
    values = {
        "schema_version": 1,
        "status_time_seconds": 1_800_000_000.0,
        "map_available": True,
        "snapshot_available": True,
        "accepted_maps": 3,
        "fingerprint": FINGERPRINT_A,
        "frame_id": "map",
        "source_stamp_ns": 1_799_999_999_500_000_000,
        "received_age_seconds": 0.25,
    }
    values.update(changes)
    return MapManagerStatusSample(**values)


def correlator(**changes):
    values = {
        "session_id": "session-20260914",
        "expected_frame_id": "map",
    }
    values.update(changes)
    return MapManagerStatusCorrelator(**values)


def unavailable_sample(**changes):
    values = {
        "schema_version": 1,
        "status_time_seconds": 1_800_000_000.0,
        "map_available": False,
        "snapshot_available": False,
        "accepted_maps": 0,
        "fingerprint": None,
        "frame_id": None,
        "source_stamp_ns": None,
        "received_age_seconds": None,
    }
    values.update(changes)
    return MapManagerStatusSample(**values)


def test_decoder_maps_actual_available_status_envelope_exactly():
    payload = status_payload()

    decoded = decode_map_manager_status_json(json.dumps(payload))

    assert decoded == sample()


def test_decoder_maps_actual_unavailable_status_without_partial_map_data():
    payload = status_payload(available=False)

    decoded = decode_map_manager_status_json(json.dumps(payload))

    assert decoded == unavailable_sample()


def test_decoder_ignores_bounded_irrelevant_status_fields():
    payload = status_payload()
    payload["ok"] = False
    payload["extra"] = {"bounded": [1, 2, {"value": "ignored"}]}
    payload["map"]["summary"]["new_schema_field"] = "ignored"

    decoded = decode_map_manager_status_json(json.dumps(payload))

    assert decoded == sample()


def test_decoded_status_flows_through_correlator_without_invention():
    decoded = decode_map_manager_status_json(json.dumps(status_payload()))

    result = correlator().accept(decoded)

    assert result.map_revision == 3
    assert result.fingerprint == FINGERPRINT_A
    assert result.source_map_age_seconds == 0.25


@pytest.mark.parametrize("path", [
    ("schema_version",),
    ("time",),
    ("map",),
    ("map", "available"),
    ("map", "snapshot_available"),
    ("map", "age_seconds"),
    ("map", "summary"),
    ("map", "summary", "fingerprint"),
    ("map", "summary", "frame_id"),
    ("map", "summary", "source_stamp_ns"),
    ("counters",),
    ("counters", "accepted_maps"),
])
def test_decoder_rejects_each_missing_required_path(path):
    payload = copy.deepcopy(status_payload())
    parent = payload
    for element in path[:-1]:
        parent = parent[element]
    del parent[path[-1]]

    with pytest.raises(MapStatusAdapterError):
        decode_map_manager_status_json(json.dumps(payload))


@pytest.mark.parametrize(("path", "value"), [
    (("schema_version",), "1"),
    (("time",), "1800000000"),
    (("map", "available"), 1),
    (("map", "snapshot_available"), 1),
    (("map", "age_seconds"), "0.25"),
    (("map", "summary", "fingerprint"), FINGERPRINT_A.upper()),
    (("map", "summary", "frame_id"), "bad frame"),
    (("map", "summary", "source_stamp_ns"), 1.5),
    (("counters", "accepted_maps"), 3.0),
])
def test_decoder_does_not_coerce_required_field_types(path, value):
    payload = copy.deepcopy(status_payload())
    parent = payload
    for element in path[:-1]:
        parent = parent[element]
    parent[path[-1]] = value

    with pytest.raises(MapStatusAdapterError):
        decode_map_manager_status_json(json.dumps(payload))


@pytest.mark.parametrize(("path", "value"), [
    (("map",), []),
    (("counters",), None),
    (("map", "summary"), []),
])
def test_decoder_rejects_wrong_intermediate_structures(path, value):
    payload = copy.deepcopy(status_payload())
    parent = payload
    for element in path[:-1]:
        parent = parent[element]
    parent[path[-1]] = value

    with pytest.raises(MapStatusAdapterError):
        decode_map_manager_status_json(json.dumps(payload))


def test_decoder_rejects_summary_when_map_is_unavailable():
    payload = status_payload(available=False)
    payload["map"]["summary"] = {}

    with pytest.raises(MapStatusAdapterError):
        decode_map_manager_status_json(json.dumps(payload))


@pytest.mark.parametrize("text", [
    "",
    "not-json",
    "[]",
    '{"value":NaN}',
    '{"schema_version":1,"schema_version":1}',
    "{\"open\":",
])
def test_decoder_rejects_invalid_or_ambiguous_json(text):
    with pytest.raises(MapStatusAdapterError):
        decode_map_manager_status_json(text)


@pytest.mark.parametrize("value", [None, b"{}", 1, {}])
def test_decoder_requires_a_text_input(value):
    with pytest.raises(MapStatusAdapterError):
        decode_map_manager_status_json(value)


def test_decoder_rejects_invalid_unicode_before_json_parsing():
    with pytest.raises(MapStatusAdapterError):
        decode_map_manager_status_json("\ud800")


def test_decoder_rejects_oversized_input_before_json_parsing():
    text = " " * (MAXIMUM_MAP_STATUS_BYTES + 1)

    with pytest.raises(MapStatusAdapterError):
        decode_map_manager_status_json(text)


def test_decoder_rejects_excessive_nesting_in_irrelevant_fields():
    text = '{"nested":' * 40 + "null" + "}" * 40

    with pytest.raises(MapStatusAdapterError):
        decode_map_manager_status_json(text)


def test_first_complete_status_creates_explicit_context_and_revision():
    adapter = correlator()

    result = adapter.accept(sample())

    assert result.context.session_id == "session-20260914"
    assert result.context.map_id == f"map-{FINGERPRINT_A}"
    assert result.context.frame_id == "map"
    assert result.map_revision == 3
    assert result.fingerprint == FINGERPRINT_A
    assert result.source_stamp_ns == 1_799_999_999_500_000_000
    assert result.source_map_age_seconds == 0.25
    assert result.map_changed is True
    assert result.replayed is False
    assert adapter.context == result.context


def test_periodic_same_map_status_keeps_revision_and_context():
    adapter = correlator()
    first = adapter.accept(sample())

    periodic = adapter.accept(sample(
        status_time_seconds=1_800_000_001.0,
        received_age_seconds=1.25,
    ))

    assert periodic.context == first.context
    assert periodic.map_revision == first.map_revision == 3
    assert periodic.fingerprint == first.fingerprint
    assert periodic.source_map_age_seconds == 1.25
    assert periodic.map_changed is False
    assert periodic.replayed is False


def test_exact_status_replay_is_idempotent():
    adapter = correlator()
    first = adapter.accept(sample())

    replay = adapter.accept(sample())

    assert replay.context == first.context
    assert replay.map_revision == first.map_revision
    assert replay.replayed is True
    assert replay.map_changed is False


def test_changed_fingerprint_with_increased_counter_is_normal_map_growth():
    adapter = correlator()
    first = adapter.accept(sample())

    grown = adapter.accept(sample(
        status_time_seconds=1_800_000_001.0,
        accepted_maps=4,
        fingerprint=FINGERPRINT_B,
        source_stamp_ns=1_800_000_000_500_000_000,
        received_age_seconds=0.2,
    ))

    assert grown.context == first.context
    assert grown.map_revision == 4
    assert grown.fingerprint == FINGERPRINT_B
    assert grown.map_changed is True


def test_skipped_status_messages_allow_counter_jump_with_new_fingerprint():
    adapter = correlator()
    context = adapter.accept(sample()).context

    jumped = adapter.accept(sample(
        status_time_seconds=1_800_000_005.0,
        accepted_maps=9,
        fingerprint=FINGERPRINT_C,
        source_stamp_ns=1_800_000_004_500_000_000,
        received_age_seconds=0.1,
    ))

    assert jumped.context == context
    assert jumped.map_revision == 9
    assert jumped.map_changed is True


@pytest.mark.parametrize("second", [
    {"status_time_seconds": 1_800_000_001.0, "accepted_maps": 4},
    {"status_time_seconds": 1_800_000_001.0,
     "fingerprint": FINGERPRINT_B},
])
def test_fingerprint_and_counter_must_change_together(second):
    adapter = correlator()
    adapter.accept(sample())

    with pytest.raises(MapStatusAdapterError):
        adapter.accept(sample(**second))


def test_counter_rollback_requires_new_epoch_without_mutating_context():
    adapter = correlator()
    first = adapter.accept(sample())

    with pytest.raises(MapEpochChangeRequired):
        adapter.accept(sample(
            status_time_seconds=1_800_000_001.0,
            accepted_maps=2,
            fingerprint=FINGERPRINT_B,
        ))

    assert adapter.context == first.context
    assert adapter.accept(sample()).replayed is True


def test_frame_change_requires_new_epoch():
    adapter = correlator()
    adapter.accept(sample())

    with pytest.raises(MapEpochChangeRequired):
        adapter.accept(sample(
            status_time_seconds=1_800_000_001.0,
            accepted_maps=4,
            fingerprint=FINGERPRINT_B,
            frame_id="map_corrected",
        ))


def test_source_stamp_rollback_requires_new_epoch():
    adapter = correlator()
    adapter.accept(sample())

    with pytest.raises(MapEpochChangeRequired):
        adapter.accept(sample(
            status_time_seconds=1_800_000_001.0,
            accepted_maps=4,
            fingerprint=FINGERPRINT_B,
            source_stamp_ns=1_799_999_999_000_000_000,
        ))


def test_source_stamp_change_without_new_map_fails_closed():
    adapter = correlator()
    adapter.accept(sample())

    with pytest.raises(MapStatusAdapterError):
        adapter.accept(sample(
            status_time_seconds=1_800_000_001.0,
            source_stamp_ns=1_800_000_000_000_000_000,
            received_age_seconds=0.2,
        ))


def test_future_source_stamp_fails_without_reading_a_clock():
    adapter = correlator(policy=MapStatusCorrelationPolicy(
        maximum_future_stamp_seconds=0.1))

    with pytest.raises(MapStatusAdapterError):
        adapter.accept(sample(
            source_stamp_ns=1_800_000_000_200_000_000))


def test_zero_source_stamp_remains_explicitly_supported():
    result = correlator().accept(sample(source_stamp_ns=0))

    assert result.source_stamp_ns == 0


def test_unavailable_status_is_missing_then_requires_new_epoch():
    adapter = correlator()

    with pytest.raises(MapStatusUnavailableError):
        adapter.accept(unavailable_sample())

    adapter.accept(sample())
    with pytest.raises(MapEpochChangeRequired):
        adapter.accept(unavailable_sample(
            status_time_seconds=1_800_000_001.0))


def test_new_explicit_session_changes_context_after_manager_restart():
    first = correlator(session_id="session-before").accept(sample())
    restarted = correlator(session_id="session-after").accept(sample(
        accepted_maps=1))

    assert restarted.context != first.context
    assert restarted.context.map_id == first.context.map_id
    assert restarted.map_revision == 1


def test_result_initializes_passive_shadow_session_without_invention():
    result = correlator().accept(sample())

    shadow = RegionGraphShadowSession(
        result,
        RegionSeed("start", result.context, result.map_revision),
    )
    payload = shadow.build_status_json(
        result,
        portal_memory_age_seconds=None,
        region_graph_age_seconds=0.0,
    )

    assert f'"map_id":"map-{FINGERPRINT_A}"' in payload
    assert '"source_map":{"age_seconds":0.25' in payload


@pytest.mark.parametrize("change", [
    {"schema_version": 2},
    {"schema_version": True},
    {"status_time_seconds": -0.1},
    {"status_time_seconds": math.nan},
    {"map_available": 1},
    {"snapshot_available": 1},
    {"snapshot_available": False},
    {"accepted_maps": 0},
    {"accepted_maps": True},
    {"fingerprint": "A" * 64},
    {"fingerprint": "a" * 63},
    {"frame_id": ""},
    {"frame_id": "map with space"},
    {"source_stamp_ns": -1},
    {"source_stamp_ns": True},
    {"received_age_seconds": -0.1},
    {"received_age_seconds": math.nan},
    {"received_age_seconds": math.inf},
    {"received_age_seconds": 1_800_000_001.0},
])
def test_invalid_available_status_fields_fail_closed(change):
    with pytest.raises(MapStatusAdapterError):
        sample(**change)


@pytest.mark.parametrize("change", [
    {"map_available": True},
    {"accepted_maps": 1},
    {"fingerprint": FINGERPRINT_A},
    {"frame_id": "map"},
    {"source_stamp_ns": 0},
    {"received_age_seconds": 0.0},
])
def test_unavailable_status_cannot_carry_partial_map_fields(change):
    with pytest.raises(MapStatusAdapterError):
        unavailable_sample(**change)


def test_status_time_must_not_run_backwards():
    adapter = correlator()
    adapter.accept(sample())

    with pytest.raises(MapStatusAdapterError):
        adapter.accept(sample(status_time_seconds=1_799_999_999.0))


@pytest.mark.parametrize("factory", [
    lambda: MapStatusCorrelationPolicy(maximum_future_stamp_seconds=-0.1),
    lambda: MapStatusCorrelationPolicy(maximum_future_stamp_seconds=math.nan),
    lambda: correlator(session_id=""),
    lambda: correlator(expected_frame_id="bad frame"),
    lambda: correlator(policy="policy"),
])
def test_invalid_policy_or_correlator_arguments_fail_closed(factory):
    with pytest.raises(MapStatusAdapterError):
        factory()


def test_wrong_sample_type_fails_closed():
    with pytest.raises(MapStatusAdapterError):
        correlator().accept(None)


def test_result_is_immutable():
    result = correlator().accept(sample())

    with pytest.raises(FrozenInstanceError):
        result.map_revision = 4
