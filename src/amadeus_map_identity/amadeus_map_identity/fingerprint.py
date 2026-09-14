"""Canonical content fingerprint for a validated occupancy-map snapshot."""

import hashlib
import math
import struct
from typing import Any, Iterable, Tuple


_VALID_COMPACT_CELL_BYTES = bytes(range(101)) + b"\xff"
_IDENTITY_TRANSLATION = bytes(range(256))
MAXIMUM_OCCUPANCY_CELL_COUNT = 4_000_000


class MapIdentityError(ValueError):
    """The supplied values cannot form one canonical map identity."""


def compact_occupancy_cells(
        *, cells: Iterable[Any], cell_count: int,
) -> bytes:
    """Return canonical uint8 bytes for one ROS int8 occupancy raster.

    Occupancy values 0..100 are preserved and ROS unknown (-1) becomes 255.
    One-dimensional contiguous byte buffers use a C-level copy and validation;
    other iterables use the strict element-by-element fallback.
    """
    if (
            isinstance(cell_count, bool)
            or not isinstance(cell_count, int)
            or cell_count < 0
            or cell_count > MAXIMUM_OCCUPANCY_CELL_COUNT):
        raise MapIdentityError(
            "cell_count muss zwischen 0 und "
            f"{MAXIMUM_OCCUPANCY_CELL_COUNT} liegen")

    try:
        view = memoryview(cells)
    except TypeError:
        view = None

    if (
            view is not None
            and view.ndim == 1
            and view.itemsize == 1
            and view.c_contiguous
            and view.format in {"b", "B", "c"}):
        compact = view.cast("B").tobytes()
        if len(compact) != cell_count:
            raise MapIdentityError(
                f"Karte erwartet {cell_count} Zellwerte, enthält aber "
                f"{len(compact)}.")
        invalid = compact.translate(
            _IDENTITY_TRANSLATION, _VALID_COMPACT_CELL_BYTES)
        if invalid:
            raw_value = invalid[0]
            signed_value = raw_value if raw_value < 128 else raw_value - 256
            raise MapIdentityError(
                f"Kartenwert {signed_value!r} liegt nicht als Ganzzahl "
                "zwischen -1 und 100 vor.")
        return compact

    compact_cells = bytearray()
    try:
        iterator = iter(cells)
    except TypeError as error:
        raise MapIdentityError("Kartendaten müssen iterierbar sein.") from error
    try:
        for index, value in enumerate(iterator):
            if index >= cell_count:
                raise MapIdentityError(
                    f"Karte erwartet {cell_count} Zellwerte, enthält aber mehr.")
            if (
                    isinstance(value, bool)
                    or not isinstance(value, int)
                    or value < -1
                    or value > 100):
                raise MapIdentityError(
                    f"Kartenwert {value!r} an Position {index} liegt nicht "
                    "als Ganzzahl zwischen -1 und 100 vor.")
            compact_cells.append(255 if value == -1 else value)
    except MapIdentityError:
        raise
    except (TypeError, ValueError, NotImplementedError, OverflowError) as error:
        raise MapIdentityError(
            "Kartendaten können nicht kanonisch gelesen werden.") from error
    if len(compact_cells) != cell_count:
        raise MapIdentityError(
            f"Karte erwartet {cell_count} Zellwerte, enthält aber "
            f"{len(compact_cells)}.")
    return bytes(compact_cells)


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
