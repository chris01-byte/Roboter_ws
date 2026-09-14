"""Shared ROS-independent identity helpers for Amadeus map snapshots."""

from .fingerprint import MapIdentityError, map_snapshot_fingerprint


__all__ = ["MapIdentityError", "map_snapshot_fingerprint"]
