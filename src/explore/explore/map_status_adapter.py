"""Pure decoding and correlation of the robot-map-manager status contract.

The decoder consumes only explicitly supplied JSON text, while the correlator
consumes its validated fields.  Neither subscribes, reads a clock, inspects a
map, or accesses files.  ``accepted_maps`` is treated only as a process-local
revision: a counter reset, frame change, or inconsistent fingerprint transition
requires a new explicit session rather than silently reusing portal or region
state.
"""

from dataclasses import dataclass, replace
import json
import math
import re
from typing import Optional

from .portal_memory import PortalMapContext


_FINGERPRINT = re.compile(r"^[0-9a-f]{64}$")
MAXIMUM_MAP_STATUS_BYTES = 1_048_576
MAXIMUM_MAP_STATUS_DEPTH = 32


class MapStatusAdapterError(ValueError):
    """A map-manager status cannot be used as trustworthy shadow input."""


class MapStatusUnavailableError(MapStatusAdapterError):
    """The status contains no complete current map snapshot."""


class MapEpochChangeRequired(MapStatusAdapterError):
    """The sequence can continue only in a new explicit map context."""


def _unique_json_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise MapStatusAdapterError(
                f"JSON-Feld {key!r} ist mehrfach vorhanden")
        result[key] = value
    return result


def _reject_json_constant(value: str) -> None:
    raise MapStatusAdapterError(
        f"Nicht endliche JSON-Zahl {value!r} ist ungueltig")


def _validate_json_depth(value: object) -> None:
    pending = [(value, 1)]
    while pending:
        current, depth = pending.pop()
        if depth > MAXIMUM_MAP_STATUS_DEPTH:
            raise MapStatusAdapterError(
                "Kartenstatus-JSON ist zu tief verschachtelt")
        if isinstance(current, dict):
            pending.extend(
                (child, depth + 1) for child in current.values())
        elif isinstance(current, list):
            pending.extend((child, depth + 1) for child in current)


def _required(mapping: dict, key: str, path: str) -> object:
    if key not in mapping:
        raise MapStatusAdapterError(
            f"Kartenstatus-JSON enthaelt {path}.{key} nicht")
    return mapping[key]


def _required_object(mapping: dict, key: str, path: str) -> dict:
    value = _required(mapping, key, path)
    if not isinstance(value, dict):
        raise MapStatusAdapterError(
            f"Kartenstatus-JSON erwartet ein Objekt bei {path}.{key}")
    return value


def _nonnegative_integer(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise MapStatusAdapterError(
            f"{name} muss eine nichtnegative Ganzzahl sein")
    return value


def _nonnegative_finite(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise MapStatusAdapterError(
            f"{name} muss eine nichtnegative endliche Zahl sein")
    normalized = float(value)
    if not math.isfinite(normalized) or normalized < 0.0:
        raise MapStatusAdapterError(
            f"{name} muss eine nichtnegative endliche Zahl sein")
    return normalized


@dataclass(frozen=True)
class MapStatusCorrelationPolicy:
    """Synthetic timestamp tolerance, not a measured runtime threshold."""

    maximum_future_stamp_seconds: float = 0.5

    def __post_init__(self) -> None:
        _nonnegative_finite(
            self.maximum_future_stamp_seconds,
            "maximum_future_stamp_seconds",
        )


@dataclass(frozen=True)
class MapManagerStatusSample:
    """Relevant schema-1 fields from one map-manager status message."""

    schema_version: int
    status_time_seconds: float
    map_available: bool
    snapshot_available: bool
    accepted_maps: int
    observed_maps: int
    fingerprint: Optional[str]
    frame_id: Optional[str]
    source_stamp_ns: Optional[int]
    received_age_seconds: Optional[float]

    def __post_init__(self) -> None:
        if (
                isinstance(self.schema_version, bool)
                or not isinstance(self.schema_version, int)
                or self.schema_version != 1):
            raise MapStatusAdapterError(
                "schema_version muss der unterstuetzte Wert 1 sein")
        _nonnegative_finite(self.status_time_seconds, "status_time_seconds")
        if not isinstance(self.map_available, bool):
            raise MapStatusAdapterError("map_available muss bool sein")
        if not isinstance(self.snapshot_available, bool):
            raise MapStatusAdapterError("snapshot_available muss bool sein")
        if self.map_available is not self.snapshot_available:
            raise MapStatusAdapterError(
                "Karten- und Snapshot-Verfuegbarkeit widersprechen sich")
        accepted_maps = _nonnegative_integer(
            self.accepted_maps, "accepted_maps")
        observed_maps = _nonnegative_integer(
            self.observed_maps, "observed_maps")

        if not self.map_available:
            if accepted_maps != 0 or observed_maps != 0 or any(
                    value is not None for value in (
                    self.fingerprint,
                    self.frame_id,
                    self.source_stamp_ns,
                    self.received_age_seconds)):
                raise MapStatusAdapterError(
                    "Nicht verfuegbarer Kartenstatus enthaelt Kartendaten")
            return

        if accepted_maps <= 0:
            raise MapStatusAdapterError(
                "Verfuegbare Karte braucht einen positiven accepted_maps-Zaehler")
        if observed_maps < accepted_maps:
            raise MapStatusAdapterError(
                "observed_maps darf accepted_maps nicht unterschreiten")
        if (
                not isinstance(self.fingerprint, str)
                or _FINGERPRINT.fullmatch(self.fingerprint) is None):
            raise MapStatusAdapterError(
                "fingerprint muss ein SHA-256-Hexwert sein")
        if (
                not isinstance(self.frame_id, str)
                or not self.frame_id
                or len(self.frame_id) > 128
                or not self.frame_id.isascii()
                or any(
                    not (character.isalnum() or character in "_.:-")
                    for character in self.frame_id)):
            raise MapStatusAdapterError("frame_id ist ungueltig")
        source_stamp_ns = _nonnegative_integer(
            self.source_stamp_ns, "source_stamp_ns")
        received_age_seconds = _nonnegative_finite(
            self.received_age_seconds, "received_age_seconds")
        if received_age_seconds > float(self.status_time_seconds):
            raise MapStatusAdapterError(
                "Empfangsalter liegt vor dem darstellbaren Statuszeitpunkt")
        object.__setattr__(
            self, "source_stamp_ns", source_stamp_ns)
        object.__setattr__(
            self, "received_age_seconds", received_age_seconds)


def decode_map_manager_status_json(text: str) -> MapManagerStatusSample:
    """Decode the relevant fields of one bounded schema-1 status envelope."""
    if not isinstance(text, str):
        raise MapStatusAdapterError(
            "Kartenstatus muss als JSON-Zeichenkette vorliegen")
    try:
        encoded_size = len(text.encode("utf-8"))
    except UnicodeError as exc:
        raise MapStatusAdapterError(
            "Kartenstatus enthaelt kein gueltiges Unicode") from exc
    if encoded_size > MAXIMUM_MAP_STATUS_BYTES:
        raise MapStatusAdapterError(
            "Kartenstatus-JSON ueberschreitet die Eingangsgrenze")
    try:
        payload = json.loads(
            text,
            object_pairs_hook=_unique_json_object,
            parse_constant=_reject_json_constant,
        )
    except MapStatusAdapterError:
        raise
    except (json.JSONDecodeError, UnicodeError, RecursionError, ValueError) as exc:
        raise MapStatusAdapterError(
            "Kartenstatus enthaelt kein gueltiges JSON") from exc
    _validate_json_depth(payload)
    if not isinstance(payload, dict):
        raise MapStatusAdapterError(
            "Kartenstatus-JSON muss ein Objekt sein")

    map_payload = _required_object(payload, "map", "root")
    counters = _required_object(payload, "counters", "root")
    map_available = _required(map_payload, "available", "root.map")
    if not isinstance(map_available, bool):
        raise MapStatusAdapterError(
            "root.map.available muss bool sein")
    summary = _required(map_payload, "summary", "root.map")
    if map_available:
        if not isinstance(summary, dict):
            raise MapStatusAdapterError(
                "Verfuegbare Karte braucht ein summary-Objekt")
        fingerprint = _required(
            summary, "fingerprint", "root.map.summary")
        frame_id = _required(summary, "frame_id", "root.map.summary")
        source_stamp_ns = _required(
            summary, "source_stamp_ns", "root.map.summary")
    else:
        if summary is not None:
            raise MapStatusAdapterError(
                "Nicht verfuegbare Karte braucht summary null")
        fingerprint = None
        frame_id = None
        source_stamp_ns = None

    return MapManagerStatusSample(
        schema_version=_required(payload, "schema_version", "root"),
        status_time_seconds=_required(payload, "time", "root"),
        map_available=map_available,
        snapshot_available=_required(
            map_payload, "snapshot_available", "root.map"),
        accepted_maps=_required(
            counters, "accepted_maps", "root.counters"),
        observed_maps=counters.get(
            "observed_maps",
            _required(counters, "accepted_maps", "root.counters"),
        ),
        fingerprint=fingerprint,
        frame_id=frame_id,
        source_stamp_ns=source_stamp_ns,
        received_age_seconds=_required(
            map_payload, "age_seconds", "root.map"),
    )


@dataclass(frozen=True)
class MapStatusCorrelationResult:
    """Normalized map source for one explicit shadow-session context."""

    context: PortalMapContext
    map_revision: int
    fingerprint: str
    source_stamp_ns: int
    source_map_age_seconds: float
    map_changed: bool
    replayed: bool = False


class MapManagerStatusCorrelator:
    """Correlate a bounded last-value sequence without retaining map data."""

    def __init__(
            self, session_id: str, expected_frame_id: str, *,
            policy: Optional[MapStatusCorrelationPolicy] = None) -> None:
        if policy is not None and not isinstance(
                policy, MapStatusCorrelationPolicy):
            raise MapStatusAdapterError(
                "policy muss MapStatusCorrelationPolicy sein")
        try:
            pending_context = PortalMapContext(
                session_id=session_id,
                map_id="pending-map-epoch",
                frame_id=expected_frame_id,
            )
        except ValueError as exc:
            raise MapStatusAdapterError(
                "Sitzungs-ID oder erwarteter Kartenframe ist ungueltig") from exc
        self._session_id = pending_context.session_id
        self._expected_frame_id = pending_context.frame_id
        self._policy = policy or MapStatusCorrelationPolicy()
        self._context: Optional[PortalMapContext] = None
        self._last_sample: Optional[MapManagerStatusSample] = None
        self._last_result: Optional[MapStatusCorrelationResult] = None

    @property
    def context(self) -> Optional[PortalMapContext]:
        return self._context

    def accept(
            self, sample: MapManagerStatusSample) -> MapStatusCorrelationResult:
        """Accept one consistent status or fail without changing prior state."""
        if not isinstance(sample, MapManagerStatusSample):
            raise MapStatusAdapterError(
                "sample muss MapManagerStatusSample sein")
        if not sample.map_available:
            if self._last_sample is None:
                raise MapStatusUnavailableError(
                    "Kartenmanager hat noch keinen Kartensnapshot")
            raise MapEpochChangeRequired(
                "Kartenstatus wurde nach Initialisierung nicht verfuegbar")
        if sample.frame_id != self._expected_frame_id:
            raise MapEpochChangeRequired(
                "Kartenframe erfordert einen neuen expliziten Kontext")
        self._validate_future_stamp(sample)

        previous = self._last_sample
        if previous is None:
            context = PortalMapContext(
                session_id=self._session_id,
                map_id=f"map-{sample.fingerprint}",
                frame_id=sample.frame_id,
            )
            result = MapStatusCorrelationResult(
                context=context,
                map_revision=sample.observed_maps,
                fingerprint=sample.fingerprint,
                source_stamp_ns=sample.source_stamp_ns,
                source_map_age_seconds=sample.received_age_seconds,
                map_changed=True,
            )
            self._context = context
            self._last_sample = sample
            self._last_result = result
            return result

        if sample == previous:
            return replace(self._last_result, replayed=True, map_changed=False)
        self._validate_sequence(previous, sample)
        map_changed = sample.observed_maps > previous.observed_maps
        result = MapStatusCorrelationResult(
            context=self._context,
            map_revision=sample.observed_maps,
            fingerprint=sample.fingerprint,
            source_stamp_ns=sample.source_stamp_ns,
            source_map_age_seconds=sample.received_age_seconds,
            map_changed=map_changed,
        )
        self._last_sample = sample
        self._last_result = result
        return result

    def _validate_future_stamp(self, sample: MapManagerStatusSample) -> None:
        if sample.source_stamp_ns == 0:
            return
        future_seconds = (
            sample.source_stamp_ns / 1_000_000_000.0
            - sample.status_time_seconds)
        if future_seconds > self._policy.maximum_future_stamp_seconds:
            raise MapStatusAdapterError(
                "Karten-Quellstempel liegt unzulaessig in der Zukunft")

    @staticmethod
    def _validate_sequence(
            previous: MapManagerStatusSample,
            sample: MapManagerStatusSample) -> None:
        if sample.status_time_seconds < previous.status_time_seconds:
            raise MapStatusAdapterError("Kartenstatuszeit ist ruecklaeufig")
        if sample.accepted_maps < previous.accepted_maps:
            raise MapEpochChangeRequired(
                "accepted_maps ist ruecklaeufig; neuer Kontext erforderlich")
        if sample.observed_maps < previous.observed_maps:
            raise MapEpochChangeRequired(
                "observed_maps ist ruecklaeufig; neuer Kontext erforderlich")
        accepted_changed = sample.accepted_maps > previous.accepted_maps
        observed_changed = sample.observed_maps > previous.observed_maps
        fingerprint_changed = sample.fingerprint != previous.fingerprint
        source_stamp_changed = (
            sample.source_stamp_ns != previous.source_stamp_ns)
        if sample.source_stamp_ns < previous.source_stamp_ns:
            raise MapEpochChangeRequired(
                "Karten-Quellstempel ist ruecklaeufig; neuer Kontext erforderlich")
        if accepted_changed is not fingerprint_changed:
            raise MapStatusAdapterError(
                "Fingerprint- und accepted_maps-Verlauf widersprechen sich")
        if observed_changed is not source_stamp_changed:
            raise MapStatusAdapterError(
                "Quellstempel- und observed_maps-Verlauf widersprechen sich")
        if accepted_changed and not observed_changed:
            raise MapStatusAdapterError(
                "Neue Kartengeometrie braucht eine neue Beobachtung")
