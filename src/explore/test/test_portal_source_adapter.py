from dataclasses import FrozenInstanceError, replace
import math
from pathlib import Path
import sys

import pytest


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE_ROOT))

from explore.map_status_adapter import (  # noqa: E402
    MapStatusCorrelationResult,
)
from explore.portal_memory import PortalMapContext  # noqa: E402
from explore.portal_source_adapter import (  # noqa: E402
    PortalSourceAdapterError,
    RawMapPortalSource,
    correlate_raw_map_portal_source,
    raw_map_portal_source_from_values,
)


FINGERPRINT = "a" * 64
CONTEXT = PortalMapContext(
    "session-20260914", "map-initial-fingerprint", "map")


def source(**changes):
    values = {
        "fingerprint": FINGERPRINT,
        "source_stamp_ns": 1_799_999_999_500_000_000,
        "frame_id": "map",
    }
    values.update(changes)
    return RawMapPortalSource(**values)


def map_status(**changes):
    values = {
        "context": CONTEXT,
        "map_revision": 12,
        "fingerprint": FINGERPRINT,
        "source_stamp_ns": 1_799_999_999_500_000_000,
        "source_map_age_seconds": 0.25,
        "map_changed": True,
        "replayed": False,
    }
    values.update(changes)
    return MapStatusCorrelationResult(**values)


def source_from_values(**changes):
    values = {
        "width": 2,
        "height": 2,
        "resolution": 0.05,
        "frame_id": "map",
        "origin": (0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0),
        "compact_cells": bytes((0, 100, 255, 42)),
        "source_stamp_ns": 123,
    }
    values.update(changes)
    return raw_map_portal_source_from_values(**values)


def test_normalized_values_use_the_shared_known_fingerprint_vector():
    raw_source = source_from_values()

    assert raw_source.fingerprint == (
        "cc800c3239900c2716fb3392a18e6a85"
        "b40413ef5a619bba7f02dcc77913b9c8")
    assert raw_source.source_stamp_ns == 123
    assert raw_source.frame_id == "map"


def test_source_stamp_is_carried_but_not_part_of_content_fingerprint():
    first = source_from_values(source_stamp_ns=1)
    second = source_from_values(source_stamp_ns=999)

    assert first.fingerprint == second.fingerprint
    assert first.source_stamp_ns == 1
    assert second.source_stamp_ns == 999


@pytest.mark.parametrize("changes", [
    {"width": 0},
    {"origin": (0.0,) * 6},
    {"compact_cells": bytes((0, 100, 254, 42))},
    {"source_stamp_ns": -1},
])
def test_noncanonical_values_do_not_create_a_portal_source(changes):
    with pytest.raises(PortalSourceAdapterError):
        source_from_values(**changes)


def test_exact_current_raw_map_identity_releases_context_and_revision():
    result = correlate_raw_map_portal_source(source(), map_status())

    assert result.context is CONTEXT
    assert result.map_revision == 12
    assert result.fingerprint == FINGERPRINT
    assert result.source_stamp_ns == 1_799_999_999_500_000_000


def test_exact_zero_stamp_is_preserved_without_arrival_time_invention():
    result = correlate_raw_map_portal_source(
        source(source_stamp_ns=0),
        map_status(source_stamp_ns=0),
    )

    assert result.source_stamp_ns == 0
    assert result.map_revision == 12


@pytest.mark.parametrize("changes", [
    {"fingerprint": "b" * 64},
    {"source_stamp_ns": 1_799_999_999_500_000_001},
    {"frame_id": "odom"},
])
def test_any_identity_mismatch_fails_closed(changes):
    with pytest.raises(PortalSourceAdapterError):
        correlate_raw_map_portal_source(source(**changes), map_status())


def test_older_raw_snapshot_is_not_assigned_the_latest_revision():
    previous_source = source(fingerprint="b" * 64, source_stamp_ns=10)
    latest_status = map_status(map_revision=13)

    with pytest.raises(PortalSourceAdapterError):
        correlate_raw_map_portal_source(previous_source, latest_status)


@pytest.mark.parametrize("changes", [
    {"fingerprint": "A" * 64},
    {"fingerprint": "a" * 63},
    {"source_stamp_ns": -1},
    {"source_stamp_ns": True},
    {"frame_id": ""},
    {"frame_id": "bad frame"},
    {"frame_id": "mäp"},
])
def test_invalid_raw_map_identity_is_rejected(changes):
    with pytest.raises(PortalSourceAdapterError):
        source(**changes)


@pytest.mark.parametrize("changes", [
    {"context": "map"},
    {"map_revision": 0},
    {"map_revision": True},
    {"fingerprint": "A" * 64},
    {"source_stamp_ns": -1},
    {"source_map_age_seconds": math.nan},
    {"source_map_age_seconds": True},
    {"map_changed": 1},
    {"replayed": 0},
])
def test_forged_invalid_map_status_is_rejected(changes):
    with pytest.raises(PortalSourceAdapterError):
        correlate_raw_map_portal_source(source(), map_status(**changes))


def test_wrong_public_argument_types_are_rejected():
    with pytest.raises(PortalSourceAdapterError):
        correlate_raw_map_portal_source("raw-map", map_status())
    with pytest.raises(PortalSourceAdapterError):
        correlate_raw_map_portal_source(source(), "map-status")


def test_inputs_and_result_are_immutable():
    raw_source = source()
    result = correlate_raw_map_portal_source(raw_source, map_status())

    with pytest.raises(FrozenInstanceError):
        raw_source.frame_id = "odom"
    with pytest.raises(FrozenInstanceError):
        result.map_revision = 13


def test_replay_flag_does_not_replace_exact_identity_requirement():
    status = replace(map_status(), replayed=True, map_changed=False)

    assert correlate_raw_map_portal_source(source(), status).map_revision == 12
    with pytest.raises(PortalSourceAdapterError):
        correlate_raw_map_portal_source(
            source(source_stamp_ns=10), status)
