"""Correlate one raw-map portal source without inventing map provenance.

The adapter accepts only an already computed identity of the exact raw
``OccupancyGrid`` used by a passive detector.  It does not hash ROS messages,
read a clock, inspect a costmap, invoke a detector, or mutate shadow state.
Nav2 master-costmap timestamps are deliberately not accepted as raw-map
identity because they describe costmap publication rather than map lineage.
"""

from dataclasses import dataclass
import math
import re

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
