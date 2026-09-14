"""Correlate one raw-map portal source without inventing map provenance.

The correlator accepts only an identity of the exact raw ``OccupancyGrid`` used
by a passive detector.  The pure factory normalizes explicit message fields but
does not import ROS.  Neither path reads a clock, inspects a costmap, invokes a
detector, or mutates shadow state.  Nav2 master-costmap timestamps are
deliberately not accepted as raw-map identity because they describe costmap
publication rather than map lineage.
"""

from collections import OrderedDict
from dataclasses import dataclass
import math
import re
from typing import Any, Iterable, Optional, Tuple

from amadeus_map_identity import (
    MapIdentityError,
    compact_occupancy_cells,
    map_snapshot_fingerprint,
)

from .map_status_adapter import MapStatusCorrelationResult
from .portal_memory import PortalMapContext


_FINGERPRINT = re.compile(r"^[0-9a-f]{64}$")


class PortalSourceAdapterError(ValueError):
    """A portal source cannot be tied to the current raw-map revision."""


def _fingerprint(value: object, name: str) -> str:
    if not isinstance(value, str) or _FINGERPRINT.fullmatch(value) is None:
        raise PortalSourceAdapterError(
            f"{name} muss ein kleingeschriebener SHA-256-Hexwert sein")
    return value


def _stamp(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise PortalSourceAdapterError(
            f"{name} muss eine nichtnegative Ganzzahl sein")
    return value


def _revision(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise PortalSourceAdapterError(
            "map_revision muss eine positive Ganzzahl sein")
    return value


def _frame(value: object, name: str) -> str:
    if (
            not isinstance(value, str)
            or not value
            or len(value) > 128
            or not value.isascii()
            or any(
                not (character.isalnum() or character in "_.:-")
                for character in value)):
        raise PortalSourceAdapterError(f"{name} ist ungueltig")
    return value


@dataclass(frozen=True)
class RawMapPortalSource:
    """Identity of the exact raw map snapshot used by a passive detector."""

    fingerprint: str
    source_stamp_ns: int
    frame_id: str

    def __post_init__(self) -> None:
        _fingerprint(self.fingerprint, "fingerprint")
        _stamp(self.source_stamp_ns, "source_stamp_ns")
        _frame(self.frame_id, "frame_id")


@dataclass(frozen=True)
class PortalSourceCorrelation:
    """Map context and revision proven for one exact raw-map identity."""

    context: PortalMapContext
    map_revision: int
    fingerprint: str
    source_stamp_ns: int


class RawMapStatusJoiner:
    """Join asynchronous raw identities and manager status without map data."""

    def __init__(self, *, capacity: int) -> None:
        if (
                isinstance(capacity, bool)
                or not isinstance(capacity, int)
                or capacity <= 0):
            raise PortalSourceAdapterError(
                "capacity muss eine positive Ganzzahl sein")
        self._capacity = capacity
        self._sources: OrderedDict[
            tuple[str, int, str], RawMapPortalSource
        ] = OrderedDict()
        self._current_status: Optional[MapStatusCorrelationResult] = None
        self._last_emitted_key: Optional[tuple[object, ...]] = None
        self._evicted_sources = 0

    @property
    def capacity(self) -> int:
        return self._capacity

    @property
    def pending_source_count(self) -> int:
        return len(self._sources)

    @property
    def evicted_source_count(self) -> int:
        return self._evicted_sources

    @property
    def current_status(self) -> Optional[MapStatusCorrelationResult]:
        return self._current_status

    def observe_source(
            self, source: RawMapPortalSource,
    ) -> Optional[PortalSourceCorrelation]:
        """Retain one unique identity and try the current manager status."""
        if not isinstance(source, RawMapPortalSource):
            raise PortalSourceAdapterError(
                "source muss RawMapPortalSource sein")
        source_key = self._source_key(source)
        if source_key not in self._sources:
            if len(self._sources) == self._capacity:
                self._sources.popitem(last=False)
                self._evicted_sources += 1
            self._sources[source_key] = source
        return self._match_current()

    def observe_status(
            self, status: MapStatusCorrelationResult,
    ) -> Optional[PortalSourceCorrelation]:
        """Retain one valid current status and retry all pending identities."""
        if not isinstance(status, MapStatusCorrelationResult):
            raise PortalSourceAdapterError(
                "status muss MapStatusCorrelationResult sein")
        _validate_map_status(status)
        self._validate_status_transition(status)
        self._current_status = status
        return self._match_current()

    @staticmethod
    def _source_key(source: RawMapPortalSource) -> tuple[str, int, str]:
        return (source.fingerprint, source.source_stamp_ns, source.frame_id)

    @staticmethod
    def _status_identity(
            status: MapStatusCorrelationResult,
    ) -> tuple[str, int, str]:
        return (
            status.fingerprint,
            status.source_stamp_ns,
            status.context.frame_id,
        )

    def _validate_status_transition(
            self, status: MapStatusCorrelationResult) -> None:
        previous = self._current_status
        if previous is None:
            return
        if status.context != previous.context:
            raise PortalSourceAdapterError(
                "Kartenstatus wechselte den expliziten Kontext")
        if status.map_revision < previous.map_revision:
            raise PortalSourceAdapterError(
                "Kartenstatusrevision ist ruecklaeufig")
        same_revision = status.map_revision == previous.map_revision
        same_identity = self._status_identity(status) == (
            self._status_identity(previous))
        if same_revision != same_identity:
            raise PortalSourceAdapterError(
                "Kartenstatusrevision und Rohkartenidentitaet widersprechen sich")
        if same_revision and status.map_changed:
            raise PortalSourceAdapterError(
                "Unveraenderte Kartenrevision ist als geaendert markiert")
        if not same_revision and not status.map_changed:
            raise PortalSourceAdapterError(
                "Neue Kartenrevision ist nicht als geaendert markiert")
        if status.replayed and not same_revision:
            raise PortalSourceAdapterError(
                "Neue Kartenrevision darf kein Replay sein")

    def _match_current(self) -> Optional[PortalSourceCorrelation]:
        status = self._current_status
        if status is None:
            return None
        status_identity = self._status_identity(status)
        matching_source = self._sources.get(status_identity)
        if matching_source is None:
            return None
        emission_key = status_identity + (status.map_revision,)
        if emission_key == self._last_emitted_key:
            del self._sources[status_identity]
            return None
        result = correlate_raw_map_portal_source(matching_source, status)
        self._last_emitted_key = emission_key
        del self._sources[status_identity]
        return result


def raw_map_portal_source_from_values(
        *, width: int, height: int, resolution: float, frame_id: str,
        origin: Tuple[float, float, float, float, float, float, float],
        cells: Iterable[Any], source_stamp_ns: int,
) -> RawMapPortalSource:
    """Build identity from raw cells using the shared normalization/digest."""
    try:
        if (
                isinstance(width, bool)
                or not isinstance(width, int)
                or width <= 0
                or width > 0xffffffff
                or isinstance(height, bool)
                or not isinstance(height, int)
                or height <= 0
                or height > 0xffffffff):
            raise MapIdentityError(
                "Kartendimensionen muessen positive 32-Bit-Werte sein")
        compact_cells = compact_occupancy_cells(
            cells=cells,
            cell_count=width * height,
        )
        fingerprint = map_snapshot_fingerprint(
            width=width,
            height=height,
            resolution=resolution,
            frame_id=frame_id,
            origin=origin,
            compact_cells=compact_cells,
        )
        return RawMapPortalSource(
            fingerprint=fingerprint,
            source_stamp_ns=source_stamp_ns,
            frame_id=frame_id,
        )
    except (MapIdentityError, PortalSourceAdapterError) as error:
        raise PortalSourceAdapterError(
            "Rohkartenwerte bilden keine kanonische Portalquelle") from error


def _validate_map_status(status: MapStatusCorrelationResult) -> None:
    if not isinstance(status.context, PortalMapContext):
        raise PortalSourceAdapterError(
            "Kartenstatus enthaelt keinen gueltigen Kontext")
    _revision(status.map_revision)
    _fingerprint(status.fingerprint, "status.fingerprint")
    _stamp(status.source_stamp_ns, "status.source_stamp_ns")
    if (
            isinstance(status.source_map_age_seconds, bool)
            or not isinstance(status.source_map_age_seconds, (int, float))
            or not math.isfinite(float(status.source_map_age_seconds))
            or status.source_map_age_seconds < 0.0):
        raise PortalSourceAdapterError(
            "Kartenstatus enthaelt kein gueltiges Quellenalter")
    if not isinstance(status.map_changed, bool):
        raise PortalSourceAdapterError(
            "Kartenstatus enthaelt kein gueltiges Aenderungskennzeichen")
    if not isinstance(status.replayed, bool):
        raise PortalSourceAdapterError(
            "Kartenstatus enthaelt kein gueltiges Replaykennzeichen")
    if status.replayed and status.map_changed:
        raise PortalSourceAdapterError(
            "Kartenstatus kann nicht Replay und Aenderung zugleich sein")


def correlate_raw_map_portal_source(
        source: RawMapPortalSource,
        current_map_status: MapStatusCorrelationResult,
) -> PortalSourceCorrelation:
    """Return context/revision only for one exact current raw-map match."""
    if not isinstance(source, RawMapPortalSource):
        raise PortalSourceAdapterError(
            "source muss RawMapPortalSource sein")
    if not isinstance(current_map_status, MapStatusCorrelationResult):
        raise PortalSourceAdapterError(
            "current_map_status muss MapStatusCorrelationResult sein")
    _validate_map_status(current_map_status)

    if source.frame_id != current_map_status.context.frame_id:
        raise PortalSourceAdapterError(
            "Rohkartenframe passt nicht zum aktiven Kartenkontext")
    if source.fingerprint != current_map_status.fingerprint:
        raise PortalSourceAdapterError(
            "Rohkartenfingerprint ist nicht der aktuelle Kartenmanagerstand")
    if source.source_stamp_ns != current_map_status.source_stamp_ns:
        raise PortalSourceAdapterError(
            "Rohkartenstempel ist nicht der aktuelle Kartenmanagerstand")

    return PortalSourceCorrelation(
        context=current_map_status.context,
        map_revision=current_map_status.map_revision,
        fingerprint=source.fingerprint,
        source_stamp_ns=source.source_stamp_ns,
    )
