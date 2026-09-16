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
from dataclasses import dataclass, replace
import hashlib
from typing import Optional, Tuple

from .frontier_task_feed import (
    FrontierInventory,
    FrontierInventoryResult,
    FrontierTrackSnapshot,
    FrontierTaskPolicy,
    FrontierTaskTracker,
)
from .frontier_task_resolution import (
    FrontierTaskResolutionEvidence,
    FrontierTaskResolutionState,
)
from .map_status_adapter import MapStatusCorrelationResult
from .portal_memory import (
    ObservationResult,
    PortalConfirmationState,
    PortalMapContext,
    PortalMemory,
    PortalMemoryPolicy,
    PortalObservation,
    PortalObservationInventory,
    PortalSnapshot,
    Point2D,
    PortalSide,
    ReachabilitySnapshot,
    ReachabilityState,
    ReachabilityUpdate,
    ReachabilityResult,
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
    RegionGraphSnapshot,
    RegionGraphPolicy,
    RegionExplorationState,
    RegionExplorationUpdate,
    RegionSeed,
    RegionStartResult,
    RegionTaskKind,
    RegionTaskResult,
    RegionTaskState,
    RegionTaskUpdate,
    RegionSnapshot,
    PortalConnectionSnapshot,
    RegionTaskSnapshot,
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
class ShadowPortalInventoryResult:
    """Atomic complete portal-detector outcome for one map revision."""

    inventory_id: str
    map_revision: int
    events: Tuple[ShadowPortalEventResult, ...]
    duplicate: bool = False


@dataclass(frozen=True)
class ShadowTraversalEventResult:
    """Atomic externally validated traversal and task outcome."""

    memory: TraversalResult
    graph: GraphTraversalResult
    task_update: Optional[RegionTaskResult]
    transit_task_update: Optional[RegionTaskResult] = None


@dataclass(frozen=True)
class ShadowFrontierEventResult:
    """Atomic unfiltered frontier inventory and new-task outcome."""

    inventory: FrontierInventoryResult
    task_updates: Tuple[RegionTaskResult, ...]


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
            frontier_policy: Optional[FrontierTaskPolicy] = None,
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
        if frontier_policy is not None and not isinstance(
                frontier_policy, FrontierTaskPolicy):
            raise RegionGraphShadowError(
                "frontier_policy muss FrontierTaskPolicy sein")
        if status_policy is not None and not isinstance(
                status_policy, ShadowStatusPolicy):
            raise RegionGraphShadowError(
                "status_policy muss ShadowStatusPolicy sein")

        selected_portal_policy = portal_policy or PortalMemoryPolicy()
        self._context = initial_map_status.context
        self._map_status = initial_map_status
        self._portal_memory = PortalMemory(
            self._context, selected_portal_policy)
        self._portal_inventory_max_observations = (
            selected_portal_policy.max_inventory_observations)
        self._last_portal_inventory: Optional[
            Tuple[PortalObservationInventory, ShadowPortalInventoryResult]
        ] = None
        self._portal_inventory_revision: Optional[int] = None
        self._frontier_tasks = FrontierTaskTracker(
            self._context, policy=frontier_policy)
        self._region_graph = RegionGraph(self._context, graph_policy)
        self._status_policy = status_policy or ShadowStatusPolicy()
        self._start_result = self._region_graph.start(start_seed)

    @property
    def context(self) -> PortalMapContext:
        return self._context

    @property
    def start_result(self) -> RegionStartResult:
        return self._start_result

    def frontier_tracks(self) -> Tuple[FrontierTrackSnapshot, ...]:
        """Return immutable stable frontier geometry for passive evidence."""
        return self._frontier_tasks.tracks()

    def portal_snapshots(self) -> Tuple[PortalSnapshot, ...]:
        """Return immutable canonical portals for a runtime evidence adapter."""
        return self._portal_memory.snapshots()

    def persistent_state(self) -> dict:
        """Return bounded JSON-ready WE state; no map or manual room data."""
        graph = self._region_graph.snapshot()
        return {
            "state_schema": 1,
            "graph": {
                "current_region_id": graph.current_region_id,
                "regions": [
                    {
                        "region_id": item.region_id,
                        "seen": item.seen,
                        "entered": item.entered,
                        "entry_count": item.entry_count,
                        "portal_ids": list(item.portal_ids),
                        "alias_ids": list(item.alias_ids),
                        "task_ids": list(item.task_ids),
                        "exploration_state": item.exploration_state.value,
                        "exploration_reason": item.exploration_reason,
                        "exploration_revision_present": (
                            item.exploration_revision is not None),
                    } for item in graph.regions
                ],
                "connections": [
                    {
                        "portal_id": item.portal_id,
                        "side_a_region_id": item.side_a_region_id,
                        "side_b_region_id": item.side_b_region_id,
                    } for item in graph.connections
                ],
                "aliases": [list(item) for item in graph.region_aliases],
                "tasks": [
                    {
                        "task_id": item.task_id,
                        "region_id": item.region_id,
                        "kind": item.kind.value,
                        "subject_id": item.subject_id,
                        "state": item.state.value,
                    } for item in graph.tasks
                ],
            },
            "portals": [
                {
                    "portal_id": item.portal_id,
                    "side_a": [item.side_a.x, item.side_a.y],
                    "side_b": [item.side_b.x, item.side_b.y],
                    "observation_count": item.observation_count,
                    "evidence_count": item.evidence_count,
                    "qualified_evidence_count": item.qualified_evidence_count,
                    "confirmation_state": item.confirmation_state.value,
                    "confirmed_traversal_count": (
                        item.confirmed_traversal_count),
                } for item in self._portal_memory.snapshots()
            ],
            "reachability": [
                {
                    "portal_id": item.portal_id,
                    "side": item.side.value,
                    "state": item.state.value,
                    "reason": item.reason,
                    "recheck_condition": item.recheck_condition,
                    "observed_at_ns": item.observed_at_ns,
                    "update_id": item.update_id,
                } for item in self._portal_memory.reachability_snapshots()
            ],
            "frontiers": [
                {
                    "frontier_id": item.frontier_id,
                    "centroid": [item.centroid.x, item.centroid.y],
                    "size_cells": item.size_cells,
                    "observation_count": item.observation_count,
                } for item in self._frontier_tasks.tracks()
            ],
        }

    @classmethod
    def restore_persistent_state(
            cls, initial_map_status: MapStatusCorrelationResult,
            start_seed: RegionSeed, payload: dict, **policies):
        """Validate and restore WE state on the exact verified saved map."""
        if not isinstance(payload, dict) or payload.get("state_schema") != 1:
            raise RegionGraphShadowError(
                "Gespeicherter WE-Zustand besitzt kein bekanntes Schema")
        if set(payload) != {
                "state_schema", "graph", "portals", "reachability",
                "frontiers"}:
            raise RegionGraphShadowError(
                "Gespeicherter WE-Zustand besitzt unerwartete Felder")
        context = initial_map_status.context
        revision = initial_map_status.map_revision
        try:
            portals = tuple(PortalSnapshot(
                portal_id=item["portal_id"],
                side_a=Point2D(*item["side_a"]),
                side_b=Point2D(*item["side_b"]),
                first_revision=revision,
                last_revision=revision,
                observation_count=item["observation_count"],
                evidence_count=item["evidence_count"],
                qualified_evidence_count=item["qualified_evidence_count"],
                confirmation_state=PortalConfirmationState(
                    item["confirmation_state"]),
                confirmed=(item["confirmation_state"] == "confirmed"),
                confirmed_traversal_count=item["confirmed_traversal_count"],
            ) for item in payload["portals"])
            reachability = tuple(ReachabilitySnapshot(
                portal_id=item["portal_id"],
                side=PortalSide(item["side"]),
                state=ReachabilityState(item["state"]),
                reason=item["reason"],
                recheck_condition=item["recheck_condition"],
                map_revision=(
                    None if item["state"] == "unknown" else revision),
                observed_at_ns=item["observed_at_ns"],
                update_id=item["update_id"],
            ) for item in payload["reachability"])
            frontiers = tuple(FrontierTrackSnapshot(
                frontier_id=item["frontier_id"],
                centroid=Point2D(*item["centroid"]),
                size_cells=item["size_cells"],
                first_revision=revision,
                last_revision=revision,
                observation_count=item["observation_count"],
            ) for item in payload["frontiers"])
            graph_payload = payload["graph"]
            regions = tuple(RegionSnapshot(
                region_id=item["region_id"],
                first_revision=revision,
                last_revision=revision,
                seen=item["seen"],
                entered=item["entered"],
                entry_count=item["entry_count"],
                portal_ids=tuple(item["portal_ids"]),
                alias_ids=tuple(item["alias_ids"]),
                task_ids=tuple(item["task_ids"]),
                exploration_state=RegionExplorationState(
                    item["exploration_state"]),
                exploration_reason=item["exploration_reason"],
                exploration_revision=(
                    revision if item["exploration_revision_present"]
                    else None),
            ) for item in graph_payload["regions"])
            connections = tuple(PortalConnectionSnapshot(
                portal_id=item["portal_id"],
                side_a_region_id=item["side_a_region_id"],
                side_b_region_id=item["side_b_region_id"],
                first_revision=revision,
                last_revision=revision,
                internal=(
                    item["side_a_region_id"] == item["side_b_region_id"]),
            ) for item in graph_payload["connections"])
            tasks = tuple(RegionTaskSnapshot(
                task_id=item["task_id"],
                region_id=item["region_id"],
                kind=RegionTaskKind(item["kind"]),
                subject_id=item["subject_id"],
                state=RegionTaskState(item["state"]),
                created_revision=revision,
                last_revision=revision,
            ) for item in graph_payload["tasks"])
            aliases = tuple(tuple(item) for item in graph_payload["aliases"])
            graph = RegionGraphSnapshot(
                context=context,
                latest_revision=revision,
                current_region_id=graph_payload["current_region_id"],
                regions=regions,
                connections=connections,
                confirmed_entry_count=sum(item.entry_count for item in regions),
                region_aliases=aliases,
                tasks=tasks,
                open_task_count=sum(
                    item.state is RegionTaskState.OPEN for item in tasks),
                completed_task_count=sum(
                    item.state is RegionTaskState.COMPLETED for item in tasks),
            )
        except (KeyError, TypeError, ValueError) as error:
            raise RegionGraphShadowError(
                "Gespeicherter WE-Zustand ist ungueltig") from error
        restored = cls(initial_map_status, start_seed, **policies)
        restored._portal_memory = PortalMemory(
            context, policies.get("portal_policy"))
        restored._portal_memory.restore_snapshots(
            portals, reachability, map_revision=revision)
        restored._frontier_tasks = FrontierTaskTracker(
            context, policy=policies.get("frontier_policy"))
        restored._frontier_tasks.restore_tracks(
            frontiers, map_revision=revision)
        restored._region_graph = RegionGraph(
            context, policies.get("graph_policy"))
        restored._region_graph.restore_snapshot(graph, map_revision=revision)
        restored._portal_inventory_revision = revision if portals else None
        restored._last_portal_inventory = None
        restored._start_result = RegionStartResult(
            region_id=graph.current_region_id)
        if set(item.portal_id for item in portals) != set(
                item.portal_id for item in connections):
            raise RegionGraphShadowError(
                "Gespeicherte Portale und Graphverbindungen widersprechen sich")
        frontier_ids = {item.frontier_id for item in frontiers}
        task_frontier_ids = {
            item.subject_id for item in tasks
            if item.kind is RegionTaskKind.FRONTIER}
        if not task_frontier_ids.issubset(frontier_ids):
            raise RegionGraphShadowError(
                "Gespeicherte Frontieraufgabe besitzt keine stabile ID")
        return restored

    def _latest_event_revision(self) -> int:
        revisions = [self._region_graph.latest_revision]
        if self._portal_memory.latest_revision is not None:
            revisions.append(self._portal_memory.latest_revision)
        if self._frontier_tasks.latest_revision is not None:
            revisions.append(self._frontier_tasks.latest_revision)
        return max(revisions)

    def observe_portal_plan(
            self, candidate: PortalPlanCandidate) -> ObservationResult:
        """Store one unqualified candidate without touching the region graph."""
        observation = normalize_portal_plan_candidate(
            candidate, self._context)
        if observation.map_revision < self._latest_event_revision():
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
        if observation.map_revision < self._latest_event_revision():
            raise StaleObservationError(
                "Portalbeobachtung stammt aus einer veralteten Graphrevision")

        memory = deepcopy(self._portal_memory)
        graph = deepcopy(self._region_graph)
        result = self._apply_structural_portal(
            memory, graph, observation)
        self._portal_memory = memory
        self._region_graph = graph
        return result

    def update_portal_reachability(
            self, update: ReachabilityUpdate) -> ReachabilityResult:
        """Store one external side verdict without changing topology."""
        return self._portal_memory.update_reachability(update)

    def _apply_structural_portal(
            self, memory: PortalMemory, graph: RegionGraph,
            observation: PortalObservation) -> ShadowPortalEventResult:
        """Apply one observation to caller-owned candidate state."""
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

        self._advance_regions_from_task_inventory(
            graph,
            tuple(result.task.region_id for result in task_updates),
            observation.map_revision,
            observation.observation_id,
        )
        return ShadowPortalEventResult(
            observation=observed,
            link=link,
            task_updates=tuple(task_updates),
        )

    def observe_portal_inventory(
            self, inventory: PortalObservationInventory,
    ) -> ShadowPortalInventoryResult:
        """Atomically apply and acknowledge one complete detector run."""
        if not isinstance(inventory, PortalObservationInventory):
            raise RegionGraphShadowError(
                "inventory muss PortalObservationInventory sein")
        if inventory.context != self._context:
            raise RegionGraphShadowError(
                "Portalbestand passt nicht zum Schattenkontext")
        previous = self._last_portal_inventory
        if previous is not None and previous[0].inventory_id == (
                inventory.inventory_id):
            if previous[0] != inventory:
                raise RegionGraphShadowError(
                    "Portal-inventory_id wurde widerspruechlich "
                    "wiederverwendet")
            return replace(previous[1], duplicate=True)
        if (
                self._portal_inventory_revision is not None
                and inventory.map_revision
                <= self._portal_inventory_revision):
            raise StaleObservationError(
                "Kartenrevision besitzt bereits einen anderen oder neueren "
                "Portalbestand")
        if inventory.map_revision < self._latest_event_revision():
            raise StaleObservationError(
                "Portalbestand stammt aus einer veralteten Graphrevision")
        if len(inventory.observations) > (
                self._portal_inventory_max_observations):
            raise RegionGraphShadowError(
                "Portalbestand ueberschreitet die Sitzungsgrenze")

        memory = deepcopy(self._portal_memory)
        graph = deepcopy(self._region_graph)
        events = tuple(
            self._apply_structural_portal(memory, graph, observation)
            for observation in inventory.observations
        )
        graph.observe_revision(self._context, inventory.map_revision)
        result = ShadowPortalInventoryResult(
            inventory_id=inventory.inventory_id,
            map_revision=inventory.map_revision,
            events=events,
        )
        self._portal_memory = memory
        self._region_graph = graph
        self._last_portal_inventory = (inventory, result)
        self._portal_inventory_revision = inventory.map_revision
        return result

    def observe_frontier_inventory(
            self, inventory: FrontierInventory) -> ShadowFrontierEventResult:
        """Keep every raw frontier globally visible as a passive task.

        Only newly assigned stable frontier identities create graph tasks.
        Matched or missing clusters never complete, reopen, rank or filter one.
        """
        if not isinstance(inventory, FrontierInventory):
            raise RegionGraphShadowError(
                "inventory muss FrontierInventory sein")
        if inventory.context != self._context:
            raise RegionGraphShadowError(
                "Frontierbestand passt nicht zum Schattenkontext")
        if inventory.map_revision < self._latest_event_revision():
            raise StaleObservationError(
                "Frontierbestand stammt aus einer veralteten Graphrevision")

        tracker = deepcopy(self._frontier_tasks)
        graph = deepcopy(self._region_graph)
        observed = tracker.observe(inventory)
        task_updates = []
        for assignment in observed.assignments:
            if observed.duplicate or not assignment.created:
                continue
            task_updates.append(graph.update_task(RegionTaskUpdate(
                update_id=_derived_id(
                    "frontier-open", inventory.inventory_id,
                    assignment.frontier_id),
                task_id=f"task-{assignment.frontier_id}",
                context=self._context,
                map_revision=inventory.map_revision,
                region_id=graph.current_region_id,
                kind=RegionTaskKind.FRONTIER,
                subject_id=assignment.frontier_id,
                state=RegionTaskState.OPEN,
            )))
        self._advance_regions_from_task_inventory(
            graph,
            tuple(result.task.region_id for result in task_updates),
            inventory.map_revision,
            inventory.inventory_id,
        )
        graph.observe_revision(self._context, inventory.map_revision)
        self._frontier_tasks = tracker
        self._region_graph = graph
        return ShadowFrontierEventResult(
            inventory=observed,
            task_updates=tuple(task_updates),
        )

    def resolve_frontier_task(
            self, evidence: FrontierTaskResolutionEvidence
    ) -> RegionTaskResult:
        """Complete one frontier task only from positive newer map evidence."""
        if not isinstance(evidence, FrontierTaskResolutionEvidence):
            raise RegionGraphShadowError(
                "evidence muss FrontierTaskResolutionEvidence sein")
        if evidence.context != self._context:
            raise RegionGraphShadowError(
                "Frontierabschluss passt nicht zum Schattenkontext")
        if evidence.state is not FrontierTaskResolutionState.RESOLVED:
            raise RegionGraphShadowError(
                "Nur positive Frontierevidenz darf eine Aufgabe erledigen")
        tasks = {task.task_id: task for task in self._region_graph.tasks()}
        task = tasks.get(evidence.task_id)
        if (
                task is None
                or task.region_id != evidence.region_id
                or task.kind is not RegionTaskKind.FRONTIER
                or task.subject_id != evidence.frontier_id):
            raise RegionGraphShadowError(
                "Frontierevidenz passt nicht zur Graphaufgabe")
        graph = deepcopy(self._region_graph)
        result = graph.update_task(RegionTaskUpdate(
            update_id=_derived_id(
                "frontier-complete", evidence.resolution_id),
            task_id=task.task_id,
            context=self._context,
            map_revision=evidence.evidence_map_revision,
            region_id=task.region_id,
            kind=task.kind,
            subject_id=task.subject_id,
            state=RegionTaskState.COMPLETED,
        ))
        self._advance_regions_from_task_inventory(
            graph,
            (task.region_id,),
            evidence.evidence_map_revision,
            evidence.resolution_id,
        )
        self._region_graph = graph
        return result

    def record_validated_traversal(
            self, event: TraversalEvent) -> ShadowTraversalEventResult:
        """Atomically apply an externally validated traversal verdict."""
        if not isinstance(event, TraversalEvent):
            raise RegionGraphShadowError("event muss TraversalEvent sein")
        if event.context != self._context:
            raise RegionGraphShadowError(
                "Durchfahrtsereignis passt nicht zum Schattenkontext")
        if event.map_revision < self._latest_event_revision():
            raise StaleObservationError(
                "Durchfahrtsereignis stammt aus einer veralteten Revision")
        memory = deepcopy(self._portal_memory)
        graph = deepcopy(self._region_graph)
        memory_result = memory.record_traversal(event)
        if event.crossing_confirmed and not memory_result.duplicate:
            for side in (PortalSide.A, PortalSide.B):
                memory.update_reachability(ReachabilityUpdate(
                    update_id=_derived_id(
                        "traversal-open", event.event_id, side.value),
                    portal_id=event.portal_id,
                    side=side,
                    context=self._context,
                    map_revision=event.map_revision,
                    observed_at_ns=event.event_time_ns,
                    state=ReachabilityState.OPEN,
                    reason="validated_full_chassis_traversal",
                    recheck_condition="fresh_route_evidence_required",
                ))
        graph_result = graph.record_traversal(event)
        task_result = None
        transit_task_result = None
        tasks = {task.task_id: task for task in graph.tasks()}
        completed_task = tasks.get(f"task-portal-{event.portal_id}")
        if (
                completed_task is None
                or completed_task.region_id != graph_result.target_region_id
                or completed_task.kind is not RegionTaskKind.PORTAL
                or completed_task.state is not RegionTaskState.OPEN):
            matching_transit_tasks = tuple(
                task for task in tasks.values()
                if (
                    task.region_id == graph_result.target_region_id
                    and task.kind is RegionTaskKind.TRANSIT
                    and task.subject_id == event.portal_id
                    and task.state is RegionTaskState.OPEN))
            completed_task = (
                matching_transit_tasks[0]
                if len(matching_transit_tasks) == 1 else None)
        if graph_result.entered and completed_task is not None:
            task_result = graph.update_task(RegionTaskUpdate(
                update_id=_derived_id("portal-complete", event.event_id),
                task_id=completed_task.task_id,
                context=self._context,
                map_revision=event.map_revision,
                region_id=completed_task.region_id,
                kind=completed_task.kind,
                subject_id=completed_task.subject_id,
                state=RegionTaskState.COMPLETED,
            ))
        if graph_result.entered:
            # A portal task belongs to the region *after* its own crossing,
            # but the work starts on the adjacent side.  Treat that adjacent
            # side as source work here so a room -> hall transit can be
            # created for the hall's next confirmed portal.  Merely open
            # transit tasks never create a return; availability is checked by
            # the later purpose-evidence adapter before this task is selected.
            source_open_work = []
            for task in graph.tasks(state=RegionTaskState.OPEN):
                if (
                        task.kind is RegionTaskKind.FRONTIER
                        and task.region_id == graph_result.source_region_id):
                    source_open_work.append(task)
                elif task.kind is RegionTaskKind.PORTAL:
                    connection = graph.connection(task.subject_id)
                    sides = (
                        connection.side_a_region_id,
                        connection.side_b_region_id)
                    if (
                            task.region_id in sides
                            and graph_result.source_region_id in sides
                            and task.region_id
                            != graph_result.source_region_id):
                        source_open_work.append(task)
            if source_open_work:
                transit_task_result = graph.update_task(RegionTaskUpdate(
                    update_id=_derived_id(
                        "transit-open", event.event_id),
                    task_id=_derived_id(
                        "transit-task", event.portal_id,
                        graph_result.source_region_id, event.event_id),
                    context=self._context,
                    map_revision=event.map_revision,
                    region_id=graph_result.source_region_id,
                    kind=RegionTaskKind.TRANSIT,
                    subject_id=event.portal_id,
                    state=RegionTaskState.OPEN,
                ))
        if task_result is not None:
            self._advance_regions_from_task_inventory(
                graph,
                (task_result.task.region_id,),
                event.map_revision,
                event.event_id,
            )
        self._portal_memory = memory
        self._region_graph = graph
        return ShadowTraversalEventResult(
            memory=memory_result,
            graph=graph_result,
            task_update=task_result,
            transit_task_update=transit_task_result,
        )

    def _advance_regions_from_task_inventory(
            self, graph: RegionGraph, region_ids: Tuple[str, ...],
            map_revision: int, trigger_id: str) -> None:
        """Advance monotone region candidates from explicit task evidence."""
        for region_id in sorted(set(region_ids)):
            region = graph.region(region_id)
            tasks = graph.tasks(region_id)
            if not tasks:
                continue
            open_tasks = tuple(
                task for task in tasks
                if task.state is RegionTaskState.OPEN)
            desired = None
            reason = None
            if region.exploration_state is RegionExplorationState.UNASSESSED:
                desired = RegionExplorationState.IN_PROGRESS
                reason = "task_inventory_became_observable"
            elif (
                    region.exploration_state
                    is RegionExplorationState.IN_PROGRESS
                    and not open_tasks):
                desired = RegionExplorationState.COMPLETE_CANDIDATE
                reason = "all_region_tasks_positively_completed"
            if desired is None:
                continue
            graph.update_region_exploration(RegionExplorationUpdate(
                update_id=_derived_id(
                    "region-task-state", trigger_id, region_id,
                    desired.value),
                context=self._context,
                map_revision=map_revision,
                region_id=region_id,
                state=desired,
                reason=reason,
            ))

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
        portal_revisions = tuple(
            revision for revision in (
                self._portal_inventory_revision,
                self._portal_memory.latest_revision,
            )
            if revision is not None)
        return ShadowStatusSource(
            context=self._context,
            source_map_revision=map_status.map_revision,
            portal_memory_revision=(
                max(portal_revisions) if portal_revisions else None),
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
