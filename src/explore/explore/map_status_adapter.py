"""Pure correlation of the existing robot-map-manager status contract.

The adapter consumes explicit, already parsed fields.  It does not subscribe,
parse JSON, read a clock, inspect a map, or access files.  ``accepted_maps`` is
treated only as a process-local revision: a counter reset, frame change, or
inconsistent fingerprint transition requires a new explicit session rather
than silently reusing portal or region state.
"""

from dataclasses import dataclass, replace
import math
import re
from typing import Optional

from .portal_memory import PortalMapContext


_FINGERPRINT = re.compile(r"^[0-9a-f]{64}$")


class MapStatusAdapterError(ValueError):
    """A map-manager status cannot be used as trustworthy shadow input."""


class MapStatusUnavailableError(MapStatusAdapterError):
    """The status contains no complete current map snapshot."""


class MapEpochChangeRequired(MapStatusAdapterError):
    """The sequence can continue only in a new explicit map context."""


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

        if not self.map_available:
            if accepted_maps != 0 or any(value is not None for value in (
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
                map_revision=sample.accepted_maps,
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
        map_changed = sample.accepted_maps > previous.accepted_maps
        result = MapStatusCorrelationResult(
            context=self._context,
            map_revision=sample.accepted_maps,
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
        counter_changed = sample.accepted_maps > previous.accepted_maps
        fingerprint_changed = sample.fingerprint != previous.fingerprint
        if counter_changed is not fingerprint_changed:
            raise MapStatusAdapterError(
                "Fingerprint- und accepted_maps-Verlauf widersprechen sich")
        if (
                not counter_changed
                and sample.source_stamp_ns != previous.source_stamp_ns):
            raise MapStatusAdapterError(
                "Quellstempel wechselte ohne neue akzeptierte Karte")
        if sample.source_stamp_ns < previous.source_stamp_ns:
            raise MapEpochChangeRequired(
                "Karten-Quellstempel ist ruecklaeufig; neuer Kontext erforderlich")
