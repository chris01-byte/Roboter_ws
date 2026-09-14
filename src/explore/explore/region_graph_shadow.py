"""Pure session owner for passive portal and region-graph shadow state.

This composition layer owns one bounded portal memory, one bounded provisional
region graph, and one bounded status policy for exactly one explicit map
context.  It accepts only the unqualified portal-plan contract and deliberately
exposes no structural qualification, traversal, goal, ROS, clock, filesystem,
or actuator interface.
"""

from typing import Optional

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
            self, context: PortalMapContext, start_seed: RegionSeed, *,
            portal_policy: Optional[PortalMemoryPolicy] = None,
            graph_policy: Optional[RegionGraphPolicy] = None,
            status_policy: Optional[ShadowStatusPolicy] = None) -> None:
        if not isinstance(context, PortalMapContext):
            raise RegionGraphShadowError(
                "context muss PortalMapContext sein")
        if not isinstance(start_seed, RegionSeed):
            raise RegionGraphShadowError("start_seed muss RegionSeed sein")
        if start_seed.context != context:
            raise RegionGraphShadowError(
                "Startregion passt nicht zu Sitzung, Karte und Frame")
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

        self._context = context
        self._portal_memory = PortalMemory(context, portal_policy)
        self._region_graph = RegionGraph(context, graph_policy)
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
            self, *, source_map_revision: int,
            source_map_age_seconds: Optional[float],
            portal_memory_age_seconds: Optional[float],
            region_graph_age_seconds: Optional[float]) -> ShadowStatusSource:
        """Return immutable snapshots using only caller-supplied freshness."""
        return ShadowStatusSource(
            context=self._context,
            source_map_revision=source_map_revision,
            portal_memory_revision=self._portal_memory.latest_revision,
            graph=self._region_graph.snapshot(),
            portals=self._portal_memory.snapshots(),
            reachability=self._portal_memory.reachability_snapshots(),
            source_map_age_seconds=source_map_age_seconds,
            portal_memory_age_seconds=portal_memory_age_seconds,
            region_graph_age_seconds=region_graph_age_seconds,
        )

    def build_status_json(
            self, *, source_map_revision: int,
            source_map_age_seconds: Optional[float],
            portal_memory_age_seconds: Optional[float],
            region_graph_age_seconds: Optional[float]) -> str:
        """Validate and serialize one bounded passive status document."""
        source = self.status_source(
            source_map_revision=source_map_revision,
            source_map_age_seconds=source_map_age_seconds,
            portal_memory_age_seconds=portal_memory_age_seconds,
            region_graph_age_seconds=region_graph_age_seconds,
        )
        return build_shadow_status_json(source, self._status_policy)
