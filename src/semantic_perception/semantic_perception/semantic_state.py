"""Fail-closed state helpers for map-bound semantic observations."""

from __future__ import annotations

from dataclasses import dataclass
import json
import math
import re
from typing import Any


_FINGERPRINT = re.compile(r'^[0-9a-f]{64}$')


class SemanticStateError(ValueError):
    """Raised when an external semantic/localization state is invalid."""


@dataclass(frozen=True)
class LocalizationStatus:
    ready: bool
    state: str
    reasons: tuple[str, ...]
    map_fingerprint: str | None
    global_initialization: str
    backend_time: float


def parse_localization_status(value: str) -> LocalizationStatus:
    """Parse the bounded subset required before publishing a map pose."""
    if not isinstance(value, str) or len(value.encode('utf-8')) > 64_000:
        raise SemanticStateError('Lokalisierungsstatus fehlt oder ist zu gross')
    try:
        payload: Any = json.loads(value)
    except (TypeError, ValueError) as exc:
        raise SemanticStateError('Lokalisierungsstatus ist kein JSON') from exc
    if not isinstance(payload, dict) or payload.get('schema_version') != 1:
        raise SemanticStateError('Lokalisierungsstatus hat ein falsches Schema')

    ready = payload.get('ready')
    state = payload.get('state')
    initialization = payload.get('global_initialization')
    reasons = payload.get('reasons')
    backend_time = payload.get('time')
    fingerprint = payload.get('map_fingerprint')
    if not isinstance(ready, bool):
        raise SemanticStateError('Lokalisierungsfreigabe ist ungueltig')
    if not isinstance(state, str) or not state.strip() or len(state) > 64:
        raise SemanticStateError('Lokalisierungszustand ist ungueltig')
    if (
            not isinstance(initialization, str) or
            not initialization.strip() or len(initialization) > 64):
        raise SemanticStateError('Globalinitialisierung ist ungueltig')
    if not isinstance(reasons, list) or len(reasons) > 64:
        raise SemanticStateError('Lokalisierungsgruende sind ungueltig')
    clean_reasons = []
    for reason in reasons:
        if not isinstance(reason, str) or len(reason) > 512:
            raise SemanticStateError('Lokalisierungsgrund ist ungueltig')
        clean_reasons.append(reason)
    if (
            isinstance(backend_time, bool) or
            not isinstance(backend_time, (int, float)) or
            not math.isfinite(float(backend_time)) or backend_time <= 0.0):
        raise SemanticStateError('Lokalisierungszeit ist ungueltig')
    if fingerprint is not None and (
            not isinstance(fingerprint, str) or
            _FINGERPRINT.fullmatch(fingerprint) is None):
        raise SemanticStateError('Kartenfingerabdruck ist ungueltig')
    if ready and (
            state != 'localized' or initialization != 'completed' or
            fingerprint is None):
        raise SemanticStateError(
            'Freigegebene Lokalisierung ist nicht vollstaendig gebunden')
    return LocalizationStatus(
        ready=ready,
        state=state,
        reasons=tuple(clean_reasons),
        map_fingerprint=fingerprint,
        global_initialization=initialization,
        backend_time=float(backend_time),
    )


def localization_is_live(
        status: LocalizationStatus | None, *, received_s: float,
        now_s: float, progress_count: int, maximum_age_s: float) -> bool:
    """Require a fresh ready status and two advancing backend heartbeats."""
    if maximum_age_s <= 0.0:
        raise SemanticStateError('Lokalisierungs-Zeitgrenze ist ungueltig')
    return bool(
        status is not None and status.ready and progress_count >= 2 and
        received_s > 0.0 and 0.0 <= now_s - received_s <= maximum_age_s
    )


def bounded_object_status(
        *, frame_id: str, map_fingerprint: str | None, now: float,
        ready: bool, memory: dict[str, dict[str, Any]], maximum_objects: int,
        memory_ttl_s: float) -> dict[str, Any]:
    """Build the app-facing object map without leaking ROS message objects."""
    if not isinstance(frame_id, str) or not frame_id.strip():
        raise SemanticStateError('Objektkarten-Frame fehlt')
    if map_fingerprint is not None and _FINGERPRINT.fullmatch(
            map_fingerprint) is None:
        raise SemanticStateError('Objektkarten-Fingerabdruck ist ungueltig')
    if maximum_objects < 1:
        raise SemanticStateError('Objektlimit ist ungueltig')
    objects = []
    for entry in memory.values():
        if entry.get('map_fingerprint') != map_fingerprint:
            continue
        last_seen = float(entry.get('last_seen_time', 0.0))
        age = max(0.0, now - last_seen)
        if memory_ttl_s > 0.0 and age > memory_ttl_s:
            continue
        pose = entry.get('pose')
        if pose is None:
            continue
        position = pose.pose.position
        values = (
            float(position.x), float(position.y), float(position.z),
            float(entry.get('conf', 0.0)), last_seen,
        )
        if not all(math.isfinite(item) for item in values):
            continue
        objects.append({
            'name': str(entry.get('name', ''))[:80],
            'confidence': values[3],
            'position': {'x': values[0], 'y': values[1], 'z': values[2]},
            'last_seen_time': last_seen,
            'age_s': age,
        })
    objects.sort(key=lambda item: (-item['confidence'], item['name']))
    return {
        'schema_version': 1,
        'ready': bool(ready),
        'frame_id': frame_id.strip(),
        'map_fingerprint': map_fingerprint,
        'time': float(now),
        'objects': objects[:maximum_objects],
    }
