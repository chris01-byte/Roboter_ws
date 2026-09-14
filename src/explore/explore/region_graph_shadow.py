"""Pure session owner for passive portal and region-graph shadow state.

This composition layer owns one bounded portal memory, one bounded provisional
region graph, and one bounded status policy for exactly one explicit map
context derived from the first correlated map-manager result.  Later status
projections accept that result type instead of separately asserted map revision
and age values.  Exact-map structural observations may update topology and
passive tasks atomically.  Traversal remains an externally validated input;
this owner never infers motion or creates goals.
"""

from copy import deepcopy
from dataclasses import dataclass
import hashlib
from typing import Optional, Tuple

from .map_status_adapter import MapStatusCorrelationResult
from .portal_memory import (
    ObservationResult,
    PortalConfirmationState,
    PortalMapContext,
    PortalMemory,
    PortalMemoryPolicy,
    PortalObservation,
    StaleObservationError,
    TraversalEvent,
    TraversalResult,
)
from .portal_plan_adapter import (
    PortalPlanCandidate,
    normalize_portal_plan_candidate,
)
from .portal_source_adapter import RawMapCorrelationDiagnostics
from .region_graph import (
    GraphTraversalResult,
    PortalLinkObservation,
    PortalLinkResult,
    RegionGraph,
    RegionGraphPolicy,
    RegionSeed,
    RegionStartResult,
    RegionTaskKind,
    RegionTaskResult,
    RegionTaskState,
    RegionTaskUpdate,
)
from .region_graph_status import (
    ShadowStatusPolicy,
    ShadowStatusSource,
    build_shadow_status_json,
)


class RegionGraphShadowError(ValueError):
    """The passive session boundary was configured inconsistently."""


@dataclass(frozen=True)
class ShadowPortalEventResult:
    """Atomic portal-memory, topology and passive-task outcome."""

    observation: ObservationResult
    link: Optional[PortalLinkResult]
    task_updates: Tuple[RegionTaskResult, ...]


@dataclass(frozen=True)
class ShadowTraversalEventResult:
    """Atomic externally validated traversal and task outcome."""

    memory: TraversalResult
    graph: GraphTraversalResult
    task_update: Optional[RegionTaskResult]


def _derived_id(kind: str, *values: str) -> str:
    digest = hashlib.sha256()
    digest.update(b"we-shadow-event-v1\0")
    digest.update(kind.encode("ascii"))
    for value in values:
        digest.update(b"\0")
        digest.update(value.encode("ascii"))
    return f"auto-{kind}-{digest.hexdigest()}"


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

    def observe_structural_portal(
            self, observation: PortalObservation) -> ShadowPortalEventResult:
        """Atomically turn exact-map evidence into topology and tasks.

        Unconfirmed portals create one observation task in the current region.
        A confirmed portal completes that task, creates a provisional opposite
        region and opens one portal task there.  No goal or traversal is
        inferred.
        """
        if not isinstance(observation, PortalObservation):
            raise RegionGraphShadowError(
                "observation muss PortalObservation sein")
        if observation.context != self._context:
            raise RegionGraphShadowError(
                "Portalbeobachtung passt nicht zum Schattenkontext")
        if observation.map_revision < self._region_graph.latest_revision:
            raise StaleObservationError(
                "Portalbeobachtung stammt aus einer veralteten Graphrevision")

        memory = deepcopy(self._portal_memory)
        graph = deepcopy(self._region_graph)
        observed = memory.observe(observation)
        link = None
        task_updates = []
        if observed.portal_id is not None:
            portal = memory.snapshot(observed.portal_id)
            observation_task_id = f"task-observe-{portal.portal_id}"
            tasks = {task.task_id: task for task in graph.tasks()}
            if portal.confirmation_state is not PortalConfirmationState.CONFIRMED:
                if observation_task_id not in tasks:
                    task_updates.append(graph.update_task(RegionTaskUpdate(
                        update_id=_derived_id(
                            "observe-open", observation.observation_id),
                        task_id=observation_task_id,
                        context=self._context,
                        map_revision=observation.map_revision,
                        region_id=graph.current_region_id,
                        kind=RegionTaskKind.OBSERVATION,
                        subject_id=portal.portal_id,
                        state=RegionTaskState.OPEN,
                    )))
            else:
                link = graph.observe_portal(PortalLinkObservation(
                    observation_id=_derived_id(
                        "portal-link", observation.observation_id),
                    context=self._context,
                    map_revision=observation.map_revision,
                    portal=portal,
                    current_region_id=graph.current_region_id,
                    current_side=observed.approach_side,
                ))
                observation_task = tasks.get(observation_task_id)
                if (
                        observation_task is not None
                        and observation_task.state is RegionTaskState.OPEN):
                    task_updates.append(graph.update_task(RegionTaskUpdate(
                        update_id=_derived_id(
                            "observe-complete", observation.observation_id),
                        task_id=observation_task_id,
                        context=self._context,
                        map_revision=observation.map_revision,
                        region_id=observation_task.region_id,
                        kind=observation_task.kind,
                        subject_id=observation_task.subject_id,
                        state=RegionTaskState.COMPLETED,
                    )))
                portal_task_id = f"task-portal-{portal.portal_id}"
                if (
                        link.opposite_region_id is not None
                        and portal_task_id not in tasks):
                    task_updates.append(graph.update_task(RegionTaskUpdate(
                        update_id=_derived_id(
                            "portal-open", observation.observation_id),
                        task_id=portal_task_id,
                        context=self._context,
                        map_revision=observation.map_revision,
                        region_id=link.opposite_region_id,
                        kind=RegionTaskKind.PORTAL,
                        subject_id=portal.portal_id,
                        state=RegionTaskState.OPEN,
                    )))

        self._portal_memory = memory
        self._region_graph = graph
        return ShadowPortalEventResult(
            observation=observed,
            link=link,
            task_updates=tuple(task_updates),
        )

    def record_validated_traversal(
            self, event: TraversalEvent) -> ShadowTraversalEventResult:
        """Atomically apply an externally validated traversal verdict."""
        if not isinstance(event, TraversalEvent):
            raise RegionGraphShadowError("event muss TraversalEvent sein")
        if event.context != self._context:
            raise RegionGraphShadowError(
                "Durchfahrtsereignis passt nicht zum Schattenkontext")
        memory = deepcopy(self._portal_memory)
        graph = deepcopy(self._region_graph)
        memory_result = memory.record_traversal(event)
        graph_result = graph.record_traversal(event)
        task_result = None
        portal_task_id = f"task-portal-{event.portal_id}"
        tasks = {task.task_id: task for task in graph.tasks()}
        portal_task = tasks.get(portal_task_id)
        if (
                graph_result.entered
                and portal_task is not None
                and portal_task.state is RegionTaskState.OPEN):
            task_result = graph.update_task(RegionTaskUpdate(
                update_id=_derived_id("portal-complete", event.event_id),
                task_id=portal_task.task_id,
                context=self._context,
                map_revision=event.map_revision,
                region_id=portal_task.region_id,
                kind=portal_task.kind,
                subject_id=portal_task.subject_id,
                state=RegionTaskState.COMPLETED,
            ))
        self._portal_memory = memory
        self._region_graph = graph
        return ShadowTraversalEventResult(
            memory=memory_result,
            graph=graph_result,
            task_update=task_result,
        )

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
