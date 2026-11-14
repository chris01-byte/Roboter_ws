from array import array
import math

import pytest

from amadeus_map_identity import (
    MAXIMUM_OCCUPANCY_CELL_COUNT,
    MapIdentityError,
    compact_occupancy_cells,
    map_snapshot_fingerprint,
)


def test_signed_byte_buffer_is_copied_losslessly_to_immutable_bytes():
    cells = array("b", [0, 100, -1, 42])

    compact = compact_occupancy_cells(cells=cells, cell_count=4)

    assert compact == bytes((0, 100, 255, 42))
    assert isinstance(compact, bytes)


@pytest.mark.parametrize("cells", [
    bytes((0, 100, 255, 42)),
    bytearray((0, 100, 255, 42)),
    array("B", [0, 100, 255, 42]),
])
def test_compact_byte_buffers_preserve_ros_unknown(cells):
    assert compact_occupancy_cells(cells=cells, cell_count=4) == (
        bytes((0, 100, 255, 42)))


def test_generic_iterables_use_strict_signed_value_fallback():
    cells = (value for value in (0, 100, -1, 42))

    assert compact_occupancy_cells(cells=cells, cell_count=4) == (
        bytes((0, 100, 255, 42)))
    assert compact_occupancy_cells(
        cells=array("h", [0, 100, -1, 42]),
        cell_count=4,
    ) == bytes((0, 100, 255, 42))


@pytest.mark.parametrize("cells, cell_count", [
    ([0, 1, 2], 4),
    ([0, 1, 2, 3, 4], 4),
    ([0, 100, -2, 42], 4),
    ([0, 100, 101, 42], 4),
    ([0, 100, True, 42], 4),
    ([0, 100, 1.5, 42], 4),
    ([0, 100, 255, 42], 4),
    (bytes((0, 100, 254, 42)), 4),
    (array("f", [0.0, 1.0]), 2),
    (None, 0),
    ((), -1),
    ((), True),
])
def test_invalid_cell_sources_are_rejected(cells, cell_count):
    with pytest.raises(MapIdentityError):
        compact_occupancy_cells(cells=cells, cell_count=cell_count)


def test_cell_limit_is_shared_and_rejected_before_iteration():
    class MustNotIterate:
        def __iter__(self):
            raise AssertionError("oversized source must not be iterated")

    assert MAXIMUM_OCCUPANCY_CELL_COUNT == 4_000_000
    with pytest.raises(MapIdentityError):
        compact_occupancy_cells(
            cells=MustNotIterate(),
            cell_count=MAXIMUM_OCCUPANCY_CELL_COUNT + 1,
        )


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
