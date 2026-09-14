"""Canonical content fingerprint for a validated occupancy-map snapshot."""

import hashlib
import math
import struct
from typing import Tuple


_VALID_COMPACT_CELL_BYTES = bytes(range(101)) + b"\xff"
_IDENTITY_TRANSLATION = bytes(range(256))


class MapIdentityError(ValueError):
    """The supplied values cannot form one canonical map identity."""


def _positive_uint32(value: object, name: str) -> int:
    if (
            isinstance(value, bool)
            or not isinstance(value, int)
            or value <= 0
            or value > 0xffffffff):
        raise MapIdentityError(
            f"{name} muss eine positive 32-Bit-Ganzzahl sein")
    return value


def _finite_float(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise MapIdentityError(f"{name} muss eine endliche Zahl sein")
    normalized = float(value)
    if not math.isfinite(normalized):
        raise MapIdentityError(f"{name} muss eine endliche Zahl sein")
    return normalized


def map_snapshot_fingerprint(
        *, width: int, height: int, resolution: float, frame_id: str,
        origin: Tuple[float, float, float, float, float, float, float],
        compact_cells: bytes,
) -> str:
    """Hash one normalized snapshot with the established map-manager layout.

    ``compact_cells`` uses bytes 0..100 for occupancy and 255 for ROS unknown.
    Source timestamps are deliberately not part of the content identity.
    """
    clean_width = _positive_uint32(width, "width")
    clean_height = _positive_uint32(height, "height")
    clean_resolution = _finite_float(resolution, "resolution")
    if clean_resolution <= 0.0:
        raise MapIdentityError("resolution muss positiv sein")
    if (
            not isinstance(frame_id, str)
            or not frame_id
            or frame_id != frame_id.strip()
            or any(ord(character) < 0x20 for character in frame_id)):
        raise MapIdentityError("frame_id ist ungueltig oder nicht normalisiert")
    frame_bytes = frame_id.encode("utf-8")
    if len(frame_bytes) > 0xffff:
        raise MapIdentityError("frame_id ist fuer das Fingerprintformat zu lang")
    if not isinstance(origin, tuple) or len(origin) != 7:
        raise MapIdentityError("origin muss ein unveraenderliches 7-Tupel sein")
    clean_origin = tuple(
        _finite_float(value, f"origin[{index}]")
        for index, value in enumerate(origin)
    )
    if not isinstance(compact_cells, bytes):
        raise MapIdentityError("compact_cells muss bytes sein")
    if len(compact_cells) != clean_width * clean_height:
        raise MapIdentityError("compact_cells hat nicht width * height Werte")
    if compact_cells.translate(
            _IDENTITY_TRANSLATION, _VALID_COMPACT_CELL_BYTES):
        raise MapIdentityError(
            "compact_cells enthaelt Werte ausserhalb 0..100 oder 255")

    digest = hashlib.sha256()
    digest.update(struct.pack(
        "!IId", clean_width, clean_height, clean_resolution))
    digest.update(struct.pack("!H", len(frame_bytes)))
    digest.update(frame_bytes)
    digest.update(struct.pack("!7d", *clean_origin))
    digest.update(compact_cells)
    return digest.hexdigest()
