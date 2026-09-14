"""Pure session owner for passive portal and region-graph shadow state.

This composition layer owns one bounded portal memory, one bounded provisional
region graph, and one bounded status policy for exactly one explicit map
context derived from the first correlated map-manager result.  Later status
projections accept that result type instead of separately asserted map revision
and age values.  The session accepts only the unqualified portal-plan contract
and deliberately exposes no structural qualification, traversal, goal, ROS,
clock, filesystem, or actuator interface.
"""

from typing import Optional

from .map_status_adapter import MapStatusCorrelationResult
from .portal_memory import (
    ObservationResult,
    PortalMapContext,
    PortalMemory,
    PortalMemoryPolicy,
    StaleObservationError,
)
from .portal_plan_adapter import (
    PortalPlanCandidate,
    normalize_portal_plan_candidate,
)
from .portal_source_adapter import RawMapCorrelationDiagnostics
from .region_graph import (
    RegionGraph,
    RegionGraphPolicy,
    RegionSeed,
    RegionStartResult,
)
from .region_graph_status import (
    ShadowStatusPolicy,
    ShadowStatusSource,
    build_shadow_status_json,
)


class RegionGraphShadowError(ValueError):
    """The passive session boundary was configured inconsistently."""


class RegionGraphShadowSession:
    """Own one passive in-memory shadow session without runtime side effects."""

    def __init__(
            self, initial_map_status: MapStatusCorrelationResult,
            start_seed: RegionSeed, *,
            portal_policy: Optional[PortalMemoryPolicy] = None,
            graph_policy: Optional[RegionGraphPolicy] = None,
            status_policy: Optional[ShadowStatusPolicy] = None) -> None:
        if not isinstance(initial_map_status, MapStatusCorrelationResult):
            raise RegionGraphShadowError(
                "initial_map_status muss MapStatusCorrelationResult sein")
        if initial_map_status.replayed or not initial_map_status.map_changed:
            raise RegionGraphShadowError(
                "Sitzung braucht das erste neue Kartenresultat")
        if not isinstance(start_seed, RegionSeed):
            raise RegionGraphShadowError("start_seed muss RegionSeed sein")
        if start_seed.context != initial_map_status.context:
            raise RegionGraphShadowError(
                "Startregion passt nicht zu Sitzung, Karte und Frame")
        if start_seed.map_revision != initial_map_status.map_revision:
            raise RegionGraphShadowError(
                "Startregion passt nicht zur ersten Kartenrevision")
        if portal_policy is not None and not isinstance(
                portal_policy, PortalMemoryPolicy):
            raise RegionGraphShadowError(
                "portal_policy muss PortalMemoryPolicy sein")
        if graph_policy is not None and not isinstance(
                graph_policy, RegionGraphPolicy):
            raise RegionGraphShadowError(
                "graph_policy muss RegionGraphPolicy sein")
        if status_policy is not None and not isinstance(
                status_policy, ShadowStatusPolicy):
            raise RegionGraphShadowError(
                "status_policy muss ShadowStatusPolicy sein")

        self._context = initial_map_status.context
        self._map_status = initial_map_status
        self._portal_memory = PortalMemory(self._context, portal_policy)
        self._region_graph = RegionGraph(self._context, graph_policy)
        self._status_policy = status_policy or ShadowStatusPolicy()
        self._start_result = self._region_graph.start(start_seed)

    @property
    def context(self) -> PortalMapContext:
        return self._context

    @property
    def start_result(self) -> RegionStartResult:
        return self._start_result

    def observe_portal_plan(
            self, candidate: PortalPlanCandidate) -> ObservationResult:
        """Store one unqualified candidate without touching the region graph."""
        observation = normalize_portal_plan_candidate(
            candidate, self._context)
        if observation.map_revision < self._region_graph.latest_revision:
            raise StaleObservationError(
                "Portalplan stammt aus der Zeit vor der Schatten-Sitzung")
        return self._portal_memory.observe(observation)

    def status_source(
            self, map_status: MapStatusCorrelationResult, *,
            portal_memory_age_seconds: Optional[float],
            region_graph_age_seconds: Optional[float],
            raw_map_correlation: Optional[
                RawMapCorrelationDiagnostics] = None) -> ShadowStatusSource:
        """Accept one correlated map status and return immutable snapshots."""
        source = self._status_source_for(
            map_status,
            portal_memory_age_seconds=portal_memory_age_seconds,
            region_graph_age_seconds=region_graph_age_seconds,
            raw_map_correlation=raw_map_correlation,
        )
        self._map_status = map_status
        return source

    def _status_source_for(
            self, map_status: MapStatusCorrelationResult, *,
            portal_memory_age_seconds: Optional[float],
            region_graph_age_seconds: Optional[float],
            raw_map_correlation: Optional[
                RawMapCorrelationDiagnostics] = None) -> ShadowStatusSource:
        if not isinstance(map_status, MapStatusCorrelationResult):
            raise RegionGraphShadowError(
                "map_status muss MapStatusCorrelationResult sein")
        if map_status.context != self._context:
            raise RegionGraphShadowError(
                "Kartenstatus passt nicht zu Sitzung, Karte und Frame")
        if map_status.map_revision < self._map_status.map_revision:
            raise RegionGraphShadowError(
                "Kartenstatusrevision ist ruecklaeufig")
        return ShadowStatusSource(
            context=self._context,
            source_map_revision=map_status.map_revision,
            portal_memory_revision=self._portal_memory.latest_revision,
            graph=self._region_graph.snapshot(),
            portals=self._portal_memory.snapshots(),
            reachability=self._portal_memory.reachability_snapshots(),
            source_map_age_seconds=map_status.source_map_age_seconds,
            portal_memory_age_seconds=portal_memory_age_seconds,
            region_graph_age_seconds=region_graph_age_seconds,
            raw_map_correlation=raw_map_correlation,
        )

    def build_status_json(
            self, map_status: MapStatusCorrelationResult, *,
            portal_memory_age_seconds: Optional[float],
            region_graph_age_seconds: Optional[float],
            raw_map_correlation: Optional[
                RawMapCorrelationDiagnostics] = None) -> str:
        """Validate and serialize one bounded passive status document."""
        source = self._status_source_for(
            map_status,
            portal_memory_age_seconds=portal_memory_age_seconds,
            region_graph_age_seconds=region_graph_age_seconds,
            raw_map_correlation=raw_map_correlation,
        )
        payload = build_shadow_status_json(source, self._status_policy)
        self._map_status = map_status
        return payload
