import math

import pytest

from amadeus_map_identity import MapIdentityError, map_snapshot_fingerprint


def fingerprint(**changes):
    values = {
        "width": 2,
        "height": 2,
        "resolution": 0.05,
        "frame_id": "map",
        "origin": (0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0),
        "compact_cells": bytes((0, 100, 255, 42)),
    }
    values.update(changes)
    return map_snapshot_fingerprint(**values)


def test_known_map_manager_vector_is_byte_exact():
    assert fingerprint() == (
        "cc800c3239900c2716fb3392a18e6a85"
        "b40413ef5a619bba7f02dcc77913b9c8")


def test_equal_normalized_values_are_deterministic():
    assert fingerprint() == fingerprint()


@pytest.mark.parametrize("change", [
    {"width": 0},
    {"width": True},
    {"height": 0x1_0000_0000},
    {"resolution": 0.0},
    {"resolution": math.nan},
    {"resolution": True},
    {"frame_id": ""},
    {"frame_id": " map"},
    {"frame_id": "map\nchild"},
    {"origin": [0.0] * 7},
    {"origin": (0.0,) * 6},
    {"origin": (0.0,) * 6 + (math.inf,)},
    {"compact_cells": bytearray((0, 100, 255, 42))},
    {"compact_cells": bytes((0, 100, 42))},
    {"compact_cells": bytes((0, 100, 254, 42))},
])
def test_noncanonical_input_is_rejected(change):
    with pytest.raises(MapIdentityError):
        fingerprint(**change)


def test_each_content_dimension_changes_the_digest():
    baseline = fingerprint()
    variants = (
        fingerprint(width=1, height=4),
        fingerprint(resolution=0.10),
        fingerprint(frame_id="odom"),
        fingerprint(origin=(1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0)),
        fingerprint(compact_cells=bytes((0, 100, 255, 43))),
    )

    assert all(value != baseline for value in variants)
    assert len(set(variants)) == len(variants)
