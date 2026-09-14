"""Pure lifecycle owner for one decoded passive region-graph shadow session.

The owner composes the bounded JSON decoder, map-status correlator, and shadow
session without reading a clock or exposing ROS, qualified evidence, traversal,
navigation, filesystem, or actuator interfaces.  It accepts only the existing
unqualified portal-plan contract.  A map epoch change is deliberately not healed
in place: callers must create a new owner with a new explicit session identifier.
"""

from dataclasses import dataclass, replace
from enum import Enum
import math
from typing import Optional

from .frontier_task_feed import (
    FrontierInventory,
    FrontierTaskPolicy,
    FrontierTrackSnapshot,
)
from .map_status_adapter import (
    MapManagerStatusCorrelator,
    MapStatusCorrelationPolicy,
    MapStatusCorrelationResult,
    MapStatusUnavailableError,
    decode_map_manager_status_json,
)
from .portal_memory import (
    ObservationResult,
    PortalMapContext,
    PortalMemoryPolicy,
    PortalObservation,
    PortalObservationInventory,
    TraversalEvent,
)
from .portal_plan_adapter import PortalPlanCandidate
from .portal_source_adapter import (
    PortalSourceAdapterError,
    PortalSourceCorrelation,
    RawMapCorrelationDiagnostics,
    RawMapPortalSource,
    RawMapStatusJoiner,
)
from .region_graph import RegionGraphPolicy, RegionSeed
from .region_graph_shadow import (
    RegionGraphShadowSession,
    ShadowFrontierEventResult,
    ShadowPortalEventResult,
    ShadowPortalInventoryResult,
    ShadowTraversalEventResult,
)
from .region_graph_status import (
    ShadowStatusPolicy,
    ShadowStatusSource,
    build_shadow_status_json,
)


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
    raw_map_correlation: Optional[PortalSourceCorrelation] = None


@dataclass(frozen=True)
class ShadowLifecycleStatus:
    """One source snapshot and its byte-bounded canonical projection."""

    source: ShadowStatusSource
    serialized: str


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
            frontier_policy: Optional[FrontierTaskPolicy] = None,
            graph_policy: Optional[RegionGraphPolicy] = None,
            status_policy: Optional[ShadowStatusPolicy] = None,
            raw_map_capacity: Optional[int] = None) -> None:
        if portal_policy is not None and not isinstance(
                portal_policy, PortalMemoryPolicy):
            raise RegionGraphShadowLifecycleError(
                "portal_policy muss PortalMemoryPolicy sein")
        if graph_policy is not None and not isinstance(
                graph_policy, RegionGraphPolicy):
            raise RegionGraphShadowLifecycleError(
                "graph_policy muss RegionGraphPolicy sein")
        if frontier_policy is not None and not isinstance(
                frontier_policy, FrontierTaskPolicy):
            raise RegionGraphShadowLifecycleError(
                "frontier_policy muss FrontierTaskPolicy sein")
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
        try:
            raw_map_joiner = (
                None
                if raw_map_capacity is None
                else RawMapStatusJoiner(capacity=raw_map_capacity)
            )
        except PortalSourceAdapterError as exc:
            raise RegionGraphShadowLifecycleError(
                "raw_map_capacity muss eine positive Ganzzahl sein"
            ) from exc

        self._start_observation_id = start_observation_id
        self._portal_policy = portal_policy
        self._frontier_policy = frontier_policy
        self._graph_policy = graph_policy
        self._status_policy = status_policy or ShadowStatusPolicy()
        self._correlator = correlator
        self._raw_map_joiner = raw_map_joiner
        self._session: Optional[RegionGraphShadowSession] = None
        self._latest_map_status: Optional[MapStatusCorrelationResult] = None
        self._last_monotonic_seconds: Optional[float] = None
        self._map_status_received_monotonic_seconds: Optional[float] = None
        self._graph_changed_monotonic_seconds: Optional[float] = None
        self._portal_changed_monotonic_seconds: Optional[float] = None

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

    def frontier_tracks(self) -> tuple[FrontierTrackSnapshot, ...]:
        """Expose immutable track snapshots only after session creation."""
        if self._session is None:
            raise RegionGraphShadowNotReadyError(
                "Frontiertracks warten noch auf eine Schatten-Sitzung")
        return self._session.frontier_tracks()

    @property
    def raw_map_diagnostics(self) -> RawMapCorrelationDiagnostics:
        joiner = self._raw_map_joiner
        if joiner is None:
            return RawMapCorrelationDiagnostics(
                enabled=False,
                capacity=0,
                source_observations=0,
                unique_sources=0,
                duplicate_sources=0,
                pending_sources=0,
                evicted_sources=0,
                emitted_correlations=0,
                last_emitted_revision=None,
            )
        return joiner.diagnostics

    def accept_raw_map_source(
            self, source: RawMapPortalSource, *,
            received_monotonic_seconds: float) -> ShadowLifecycleUpdate:
        """Offer one immutable raw-map identity to the optional joiner."""
        joiner = self._raw_map_joiner
        if joiner is None:
            raise RegionGraphShadowLifecycleError(
                "Rohkartenkorrelation ist nicht aktiviert")
        received = self._validate_monotonic_progress(
            received_monotonic_seconds,
            "received_monotonic_seconds",
        )
        try:
            correlation = joiner.observe_source(source)
        except PortalSourceAdapterError as exc:
            raise RegionGraphShadowLifecycleError(
                "Rohkartenquelle ist fuer den Schatten ungueltig") from exc
        self._last_monotonic_seconds = received
        return ShadowLifecycleUpdate(
            state=self.state,
            map_status=self._latest_map_status,
            raw_map_correlation=correlation,
        )

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

        raw_map_correlation = None
        if self._raw_map_joiner is not None:
            try:
                raw_map_correlation = self._raw_map_joiner.observe_status(
                    result)
            except PortalSourceAdapterError as exc:
                raise RegionGraphShadowLifecycleError(
                    "Kartenstatus widerspricht der Rohkartenkorrelation"
                ) from exc

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
                frontier_policy=self._frontier_policy,
                graph_policy=self._graph_policy,
                status_policy=self._status_policy,
            )
            self._session = session
            self._latest_map_status = result
            self._last_monotonic_seconds = received
            self._map_status_received_monotonic_seconds = received
            self._graph_changed_monotonic_seconds = received
            return ShadowLifecycleUpdate(
                state=ShadowLifecycleState.ACTIVE,
                map_status=result,
                session_started=True,
                raw_map_correlation=raw_map_correlation,
            )

        self._session.status_source(
            result,
            portal_memory_age_seconds=None,
            region_graph_age_seconds=None,
        )
        self._latest_map_status = result
        self._last_monotonic_seconds = received
        if not result.replayed:
            self._map_status_received_monotonic_seconds = received
        return ShadowLifecycleUpdate(
            state=ShadowLifecycleState.ACTIVE,
            map_status=result,
            raw_map_correlation=raw_map_correlation,
        )

    def observe_portal_plan(
            self, candidate: PortalPlanCandidate, *,
            observed_monotonic_seconds: float) -> ObservationResult:
        """Accept one unqualified portal plan in the active map context."""
        if self._session is None or self._latest_map_status is None:
            raise RegionGraphShadowNotReadyError(
                "Portalplan wartet noch auf eine Schatten-Sitzung")
        observed = self._validate_monotonic_progress(
            observed_monotonic_seconds,
            "observed_monotonic_seconds",
        )
        if not isinstance(candidate, PortalPlanCandidate):
            raise RegionGraphShadowLifecycleError(
                "candidate muss PortalPlanCandidate sein")
        if candidate.context != self._session.context:
            raise RegionGraphShadowLifecycleError(
                "Portalplan passt nicht zum aktiven Kartenkontext")
        if candidate.map_revision > self._latest_map_status.map_revision:
            raise RegionGraphShadowLifecycleError(
                "Portalplan liegt vor dem aktuellen Kartenstatus")

        result = self._session.observe_portal_plan(candidate)
        self._last_monotonic_seconds = observed
        if not result.duplicate:
            self._portal_changed_monotonic_seconds = observed
        return result

    def observe_structural_portal(
            self, observation: PortalObservation, *,
            observed_monotonic_seconds: float) -> ShadowPortalEventResult:
        """Apply exact-map structural evidence to passive graph and tasks."""
        if self._session is None or self._latest_map_status is None:
            raise RegionGraphShadowNotReadyError(
                "Portalbeobachtung wartet noch auf eine Schatten-Sitzung")
        observed = self._validate_monotonic_progress(
            observed_monotonic_seconds,
            "observed_monotonic_seconds",
        )
        if not isinstance(observation, PortalObservation):
            raise RegionGraphShadowLifecycleError(
                "observation muss PortalObservation sein")
        if observation.context != self._session.context:
            raise RegionGraphShadowLifecycleError(
                "Portalbeobachtung passt nicht zum aktiven Kartenkontext")
        if observation.map_revision > self._latest_map_status.map_revision:
            raise RegionGraphShadowLifecycleError(
                "Portalbeobachtung liegt vor dem aktuellen Kartenstatus")
        result = self._session.observe_structural_portal(observation)
        self._last_monotonic_seconds = observed
        if not result.observation.duplicate:
            self._portal_changed_monotonic_seconds = observed
        if result.link is not None or result.task_updates:
            self._graph_changed_monotonic_seconds = observed
        return result

    def observe_portal_inventory(
            self, inventory: PortalObservationInventory, *,
            observed_monotonic_seconds: float,
    ) -> ShadowPortalInventoryResult:
        """Apply one complete exact-map detector outcome atomically."""
        if self._session is None or self._latest_map_status is None:
            raise RegionGraphShadowNotReadyError(
                "Portalbestand wartet noch auf eine Schatten-Sitzung")
        observed = self._validate_monotonic_progress(
            observed_monotonic_seconds,
            "observed_monotonic_seconds",
        )
        if not isinstance(inventory, PortalObservationInventory):
            raise RegionGraphShadowLifecycleError(
                "inventory muss PortalObservationInventory sein")
        if inventory.context != self._session.context:
            raise RegionGraphShadowLifecycleError(
                "Portalbestand passt nicht zum aktiven Kartenkontext")
        if inventory.map_revision > self._latest_map_status.map_revision:
            raise RegionGraphShadowLifecycleError(
                "Portalbestand liegt vor dem aktuellen Kartenstatus")
        result = self._session.observe_portal_inventory(inventory)
        self._last_monotonic_seconds = observed
        if not result.duplicate:
            self._portal_changed_monotonic_seconds = observed
        if any(event.link is not None or event.task_updates
               for event in result.events):
            self._graph_changed_monotonic_seconds = observed
        return result

    def record_validated_traversal(
            self, event: TraversalEvent, *,
            observed_monotonic_seconds: float) -> ShadowTraversalEventResult:
        """Apply one externally validated event without inferring movement."""
        if self._session is None or self._latest_map_status is None:
            raise RegionGraphShadowNotReadyError(
                "Durchfahrt wartet noch auf eine Schatten-Sitzung")
        observed = self._validate_monotonic_progress(
            observed_monotonic_seconds,
            "observed_monotonic_seconds",
        )
        if not isinstance(event, TraversalEvent):
            raise RegionGraphShadowLifecycleError(
                "event muss TraversalEvent sein")
        if event.context != self._session.context:
            raise RegionGraphShadowLifecycleError(
                "Durchfahrt passt nicht zum aktiven Kartenkontext")
        if event.map_revision > self._latest_map_status.map_revision:
            raise RegionGraphShadowLifecycleError(
                "Durchfahrt liegt vor dem aktuellen Kartenstatus")
        result = self._session.record_validated_traversal(event)
        self._last_monotonic_seconds = observed
        if not result.memory.duplicate:
            self._portal_changed_monotonic_seconds = observed
        if not result.graph.duplicate or result.task_update is not None:
            self._graph_changed_monotonic_seconds = observed
        return result

    def observe_frontier_inventory(
            self, inventory: FrontierInventory, *,
            observed_monotonic_seconds: float) -> ShadowFrontierEventResult:
        """Apply one complete unfiltered frontier inventory passively."""
        if self._session is None or self._latest_map_status is None:
            raise RegionGraphShadowNotReadyError(
                "Frontierbestand wartet noch auf eine Schatten-Sitzung")
        observed = self._validate_monotonic_progress(
            observed_monotonic_seconds,
            "observed_monotonic_seconds",
        )
        if not isinstance(inventory, FrontierInventory):
            raise RegionGraphShadowLifecycleError(
                "inventory muss FrontierInventory sein")
        if inventory.context != self._session.context:
            raise RegionGraphShadowLifecycleError(
                "Frontierbestand passt nicht zum aktiven Kartenkontext")
        if inventory.map_revision > self._latest_map_status.map_revision:
            raise RegionGraphShadowLifecycleError(
                "Frontierbestand liegt vor dem aktuellen Kartenstatus")
        result = self._session.observe_frontier_inventory(inventory)
        self._last_monotonic_seconds = observed
        if result.task_updates:
            self._graph_changed_monotonic_seconds = observed
        return result

    def build_status(self, *, now_monotonic_seconds: float) -> ShadowLifecycleStatus:
        """Build one atomic typed snapshot and its canonical JSON projection."""
        now = self._validate_monotonic_progress(
            now_monotonic_seconds,
            "now_monotonic_seconds",
        )
        if self._session is None or self._latest_map_status is None:
            raise RegionGraphShadowNotReadyError(
                "Schatten-Sitzung wartet noch auf einen Kartensnapshot")
        map_status_received = self._map_status_received_monotonic_seconds
        if map_status_received is None:
            raise RegionGraphShadowLifecycleError(
                "Karten-Empfangszeit fehlt trotz aktiver Schatten-Sitzung")
        graph_changed = self._graph_changed_monotonic_seconds
        if graph_changed is None:
            raise RegionGraphShadowLifecycleError(
                "Graphzeitpunkt fehlt trotz aktiver Schatten-Sitzung")
        portal_age = None
        if self._portal_changed_monotonic_seconds is not None:
            portal_age = now - self._portal_changed_monotonic_seconds
        current_map_status = replace(
            self._latest_map_status,
            source_map_age_seconds=(
                self._latest_map_status.source_map_age_seconds
                + now - map_status_received),
        )
        source = self._session.status_source(
            current_map_status,
            portal_memory_age_seconds=portal_age,
            region_graph_age_seconds=now - graph_changed,
            raw_map_correlation=(
                None
                if self._raw_map_joiner is None
                else self.raw_map_diagnostics
            ),
        )
        payload = build_shadow_status_json(source, self._status_policy)
        self._last_monotonic_seconds = now
        return ShadowLifecycleStatus(source=source, serialized=payload)

    def build_status_json(self, *, now_monotonic_seconds: float) -> str:
        """Build status only after a complete map initialized the owner."""
        return self.build_status(
            now_monotonic_seconds=now_monotonic_seconds).serialized

    def _validate_monotonic_progress(
            self, value: object, name: str) -> float:
        normalized = _monotonic_seconds(value, name)
        if (
                self._last_monotonic_seconds is not None
                and normalized < self._last_monotonic_seconds):
            raise RegionGraphShadowLifecycleError(
                f"{name} ist gegenueber dem letzten Eingang ruecklaeufig")
        return normalized
