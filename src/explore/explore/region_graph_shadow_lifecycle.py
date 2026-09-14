"""Pure lifecycle owner for one decoded passive region-graph shadow session.

The owner composes the bounded JSON decoder, map-status correlator, and shadow
session without reading a clock or exposing ROS, portal, navigation, filesystem,
or actuator interfaces.  A map epoch change is deliberately not healed in
place: callers must create a new owner with a new explicit session identifier.
"""

from dataclasses import dataclass
from enum import Enum
import math
from typing import Optional

from .map_status_adapter import (
    MapManagerStatusCorrelator,
    MapStatusCorrelationPolicy,
    MapStatusCorrelationResult,
    MapStatusUnavailableError,
    decode_map_manager_status_json,
)
from .portal_memory import PortalMapContext, PortalMemoryPolicy
from .region_graph import RegionGraphPolicy, RegionSeed
from .region_graph_shadow import RegionGraphShadowSession
from .region_graph_status import ShadowStatusPolicy


class RegionGraphShadowLifecycleError(ValueError):
    """The pure lifecycle boundary was configured or used inconsistently."""


class RegionGraphShadowNotReadyError(RegionGraphShadowLifecycleError):
    """No complete map status has started the owned shadow session yet."""


class ShadowLifecycleState(str, Enum):
    WAITING_FOR_MAP = "waiting_for_map"
    ACTIVE = "active"


@dataclass(frozen=True)
class ShadowLifecycleUpdate:
    state: ShadowLifecycleState
    map_status: Optional[MapStatusCorrelationResult]
    session_started: bool = False


def _monotonic_seconds(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise RegionGraphShadowLifecycleError(
            f"{name} muss eine nichtnegative endliche Zahl sein")
    normalized = float(value)
    if not math.isfinite(normalized) or normalized < 0.0:
        raise RegionGraphShadowLifecycleError(
            f"{name} muss eine nichtnegative endliche Zahl sein")
    return normalized


class RegionGraphShadowLifecycle:
    """Own decoder-to-session state for one explicit map-manager epoch."""

    def __init__(
            self, session_id: str, expected_frame_id: str,
            start_observation_id: str, *,
            map_policy: Optional[MapStatusCorrelationPolicy] = None,
            portal_policy: Optional[PortalMemoryPolicy] = None,
            graph_policy: Optional[RegionGraphPolicy] = None,
            status_policy: Optional[ShadowStatusPolicy] = None) -> None:
        if portal_policy is not None and not isinstance(
                portal_policy, PortalMemoryPolicy):
            raise RegionGraphShadowLifecycleError(
                "portal_policy muss PortalMemoryPolicy sein")
        if graph_policy is not None and not isinstance(
                graph_policy, RegionGraphPolicy):
            raise RegionGraphShadowLifecycleError(
                "graph_policy muss RegionGraphPolicy sein")
        if status_policy is not None and not isinstance(
                status_policy, ShadowStatusPolicy):
            raise RegionGraphShadowLifecycleError(
                "status_policy muss ShadowStatusPolicy sein")
        try:
            pending_context = PortalMapContext(
                session_id=session_id,
                map_id="pending-map-epoch",
                frame_id=expected_frame_id,
            )
            RegionSeed(start_observation_id, pending_context, 0)
            correlator = MapManagerStatusCorrelator(
                session_id,
                expected_frame_id,
                policy=map_policy,
            )
        except ValueError as exc:
            raise RegionGraphShadowLifecycleError(
                "Sitzungs-, Frame- oder Startbeobachtungs-ID ist ungueltig"
            ) from exc

        self._start_observation_id = start_observation_id
        self._portal_policy = portal_policy
        self._graph_policy = graph_policy
        self._status_policy = status_policy
        self._correlator = correlator
        self._session: Optional[RegionGraphShadowSession] = None
        self._latest_map_status: Optional[MapStatusCorrelationResult] = None
        self._last_monotonic_seconds: Optional[float] = None
        self._graph_changed_monotonic_seconds: Optional[float] = None

    @property
    def state(self) -> ShadowLifecycleState:
        if self._session is None:
            return ShadowLifecycleState.WAITING_FOR_MAP
        return ShadowLifecycleState.ACTIVE

    @property
    def context(self) -> Optional[PortalMapContext]:
        if self._session is None:
            return None
        return self._session.context

    @property
    def latest_map_status(self) -> Optional[MapStatusCorrelationResult]:
        return self._latest_map_status

    def accept_map_status_json(
            self, text: str, *,
            received_monotonic_seconds: float) -> ShadowLifecycleUpdate:
        """Decode and accept one status without silently crossing map epochs."""
        sample = decode_map_manager_status_json(text)
        received = self._validate_monotonic_progress(
            received_monotonic_seconds,
            "received_monotonic_seconds",
        )
        try:
            result = self._correlator.accept(sample)
        except MapStatusUnavailableError:
            self._last_monotonic_seconds = received
            return ShadowLifecycleUpdate(
                state=ShadowLifecycleState.WAITING_FOR_MAP,
                map_status=None,
            )

        if self._session is None:
            seed = RegionSeed(
                self._start_observation_id,
                result.context,
                result.map_revision,
            )
            session = RegionGraphShadowSession(
                result,
                seed,
                portal_policy=self._portal_policy,
                graph_policy=self._graph_policy,
                status_policy=self._status_policy,
            )
            self._session = session
            self._latest_map_status = result
            self._last_monotonic_seconds = received
            self._graph_changed_monotonic_seconds = received
            return ShadowLifecycleUpdate(
                state=ShadowLifecycleState.ACTIVE,
                map_status=result,
                session_started=True,
            )

        self._session.status_source(
            result,
            portal_memory_age_seconds=None,
            region_graph_age_seconds=None,
        )
        self._latest_map_status = result
        self._last_monotonic_seconds = received
        return ShadowLifecycleUpdate(
            state=ShadowLifecycleState.ACTIVE,
            map_status=result,
        )

    def build_status_json(self, *, now_monotonic_seconds: float) -> str:
        """Build status only after a complete map initialized the owner."""
        now = self._validate_monotonic_progress(
            now_monotonic_seconds,
            "now_monotonic_seconds",
        )
        if self._session is None or self._latest_map_status is None:
            raise RegionGraphShadowNotReadyError(
                "Schatten-Sitzung wartet noch auf einen Kartensnapshot")
        graph_changed = self._graph_changed_monotonic_seconds
        if graph_changed is None:
            raise RegionGraphShadowLifecycleError(
                "Graphzeitpunkt fehlt trotz aktiver Schatten-Sitzung")
        payload = self._session.build_status_json(
            self._latest_map_status,
            portal_memory_age_seconds=None,
            region_graph_age_seconds=now - graph_changed,
        )
        self._last_monotonic_seconds = now
        return payload

    def _validate_monotonic_progress(
            self, value: object, name: str) -> float:
        normalized = _monotonic_seconds(value, name)
        if (
                self._last_monotonic_seconds is not None
                and normalized < self._last_monotonic_seconds):
            raise RegionGraphShadowLifecycleError(
                f"{name} ist gegenueber dem letzten Eingang ruecklaeufig")
        return normalized
