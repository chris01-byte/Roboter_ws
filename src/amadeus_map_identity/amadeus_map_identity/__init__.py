"""Shared ROS-independent identity helpers for Amadeus map snapshots."""

from .fingerprint import (
    MAXIMUM_OCCUPANCY_CELL_COUNT,
    MapIdentityError,
    compact_occupancy_cells,
    map_snapshot_fingerprint,
)


__all__ = [
    "MAXIMUM_OCCUPANCY_CELL_COUNT",
    "MapIdentityError",
    "compact_occupancy_cells",
    "map_snapshot_fingerprint",
]
