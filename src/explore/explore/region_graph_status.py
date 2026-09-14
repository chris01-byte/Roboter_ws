"""Deterministic passive status projection for portal and region snapshots.

This module has no ROS, filesystem, planner, or actuator dependency.  It does
not create goals, infer freshness from wall time, or expose metric apartment
geometry.  Callers must supply one explicit current map revision.
Freshness additionally requires explicit monotonic ages supplied by the caller;
the projection never reads a clock itself.
"""

from dataclasses import dataclass
import json
import math
from typing import Optional, Tuple

from .portal_memory import (
    PortalConfirmationState,
    PortalMapContext,
    PortalSide,
    PortalSnapshot,
    ReachabilitySnapshot,
    ReachabilityState,
)
from .portal_source_adapter import RawMapCorrelationDiagnostics
from .region_graph import (
    RegionExplorationState,
    RegionGraphSnapshot,
    RegionTaskKind,
    RegionTaskState,
)


SCHEMA_VERSION = 1


class ShadowStatusError(ValueError):
    """The supplied snapshots cannot form one trustworthy passive status."""


class ShadowStatusCapacityError(ShadowStatusError):
    """A configured projection or serialized-output bound would be exceeded."""


def _revision(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ShadowStatusError(
            f"{name} muss eine nichtnegative Ganzzahl sein")
    return value


def _optional_revision(value: object, name: str) -> Optional[int]:
    if value is None:
        return None
    return _revision(value, name)


def _optional_age_seconds(value: object, name: str) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ShadowStatusError(
            f"{name} muss eine nichtnegative endliche Zahl sein")
    normalized = float(value)
    if not math.isfinite(normalized) or normalized < 0.0:
        raise ShadowStatusError(
            f"{name} muss eine nichtnegative endliche Zahl sein")
    return normalized


def _maximum_age_seconds(value: object, name: str) -> float:
    normalized = _optional_age_seconds(value, name)
    if normalized is None:
        raise ShadowStatusError(
            f"{name} muss eine nichtnegative endliche Zahl sein")
    return normalized


@dataclass(frozen=True)
class ShadowStatusPolicy:
    """Hard bounds and synthetic revision/age freshness start values."""

    maximum_revision_lag: int = 1
    maximum_source_map_age_seconds: float = 2.0
    maximum_portal_memory_age_seconds: float = 2.0
    maximum_region_graph_age_seconds: float = 2.0
    max_portals: int = 256
    max_regions: int = 256
    max_connections: int = 512
    max_tasks: int = 4096
    max_reachability_sides: int = 512
    max_serialized_bytes: int = 1048576

    def __post_init__(self) -> None:
        _revision(self.maximum_revision_lag, "maximum_revision_lag")
        for name in (
                "maximum_source_map_age_seconds",
                "maximum_portal_memory_age_seconds",
                "maximum_region_graph_age_seconds"):
            _maximum_age_seconds(getattr(self, name), name)
        for name in (
                "max_portals", "max_regions", "max_connections",
                "max_tasks", "max_reachability_sides",
                "max_serialized_bytes"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise ShadowStatusError(
                    f"{name} muss eine positive Ganzzahl sein")


@dataclass(frozen=True)
class ShadowStatusSource:
    """Immutable inputs asserted to belong to one portal/map context."""

    context: PortalMapContext
    source_map_revision: int
    portal_memory_revision: Optional[int]
    graph: RegionGraphSnapshot
    portals: Tuple[PortalSnapshot, ...]
    reachability: Tuple[ReachabilitySnapshot, ...]
    source_map_age_seconds: Optional[float] = None
    portal_memory_age_seconds: Optional[float] = None
    region_graph_age_seconds: Optional[float] = None
    raw_map_correlation: Optional[RawMapCorrelationDiagnostics] = None

    def __post_init__(self) -> None:
        if not isinstance(self.context, PortalMapContext):
            raise ShadowStatusError("context muss PortalMapContext sein")
        _revision(self.source_map_revision, "source_map_revision")
        _optional_revision(
            self.portal_memory_revision, "portal_memory_revision")
        _optional_age_seconds(
            self.source_map_age_seconds, "source_map_age_seconds")
        _optional_age_seconds(
            self.portal_memory_age_seconds, "portal_memory_age_seconds")
        _optional_age_seconds(
            self.region_graph_age_seconds, "region_graph_age_seconds")
        if (
                self.raw_map_correlation is not None
                and not isinstance(
                    self.raw_map_correlation,
                    RawMapCorrelationDiagnostics)):
            raise ShadowStatusError(
                "raw_map_correlation muss Rohkartendiagnose sein")
        if (
                self.raw_map_correlation is not None
                and not self.raw_map_correlation.enabled):
            raise ShadowStatusError(
                "Deaktivierte Rohkartendiagnose darf nicht projiziert werden")
        if not isinstance(self.graph, RegionGraphSnapshot):
            raise ShadowStatusError("graph muss RegionGraphSnapshot sein")
        if not isinstance(self.portals, tuple) or any(
                not isinstance(item, PortalSnapshot) for item in self.portals):
            raise ShadowStatusError(
                "portals muss ein Tupel aus PortalSnapshot sein")
        if not isinstance(self.reachability, tuple) or any(
                not isinstance(item, ReachabilitySnapshot)
                for item in self.reachability):
            raise ShadowStatusError(
                "reachability muss ein Tupel aus ReachabilitySnapshot sein")


def _source_freshness(
        accepted_revision: Optional[int], source_map_revision: int,
        maximum_revision_lag: int, age_seconds: Optional[float],
        maximum_age_seconds: float) -> dict:
    if accepted_revision is None:
        if age_seconds is not None:
            raise ShadowStatusError(
                "Quellalter ohne zugehoerige Revision ist ungueltig")
        return {
            "revision": None,
            "lag_revisions": None,
            "age_seconds": None,
            "state": "missing",
        }
    if accepted_revision > source_map_revision:
        raise ShadowStatusError(
            "Quellrevision liegt vor der angegebenen aktuellen Kartenrevision")
    lag = source_map_revision - accepted_revision
    normalized_age = _optional_age_seconds(age_seconds, "source age_seconds")
    if normalized_age is None:
        state = "missing"
    elif (
            lag > maximum_revision_lag
            or normalized_age > maximum_age_seconds):
        state = "stale"
    else:
        state = "fresh"
    return {
        "revision": accepted_revision,
        "lag_revisions": lag,
        "age_seconds": normalized_age,
        "state": state,
    }


def _check_capacity(name: str, count: int, maximum: int) -> None:
    if count > maximum:
        raise ShadowStatusCapacityError(
            f"{name} ueberschreitet die Projektionsgrenze")


def _validate_source(
        source: ShadowStatusSource, policy: ShadowStatusPolicy) -> None:
    graph = source.graph
    _optional_revision(graph.latest_revision, "graph.latest_revision")
    if graph.context != source.context:
        raise ShadowStatusError(
            "Portal- und Regionsstatus haben verschiedene Kontexte")

    _check_capacity("Portale", len(source.portals), policy.max_portals)
    _check_capacity("Regionen", len(graph.regions), policy.max_regions)
    _check_capacity(
        "Verbindungen", len(graph.connections), policy.max_connections)
    _check_capacity("Aufgaben", len(graph.tasks), policy.max_tasks)
    _check_capacity(
        "Erreichbarkeitsseiten", len(source.reachability),
        policy.max_reachability_sides)

    portal_ids = [portal.portal_id for portal in source.portals]
    if len(set(portal_ids)) != len(portal_ids):
        raise ShadowStatusError("Portalstatus enthaelt doppelte IDs")
    portal_id_set = set(portal_ids)
    if source.portal_memory_revision is None and (
            source.portals or source.reachability):
        raise ShadowStatusError(
            "Portalbestand ohne Portalgedaechtnisrevision ist ungueltig")
    portal_revision = source.portal_memory_revision
    if portal_revision is not None:
        for portal in source.portals:
            if not isinstance(
                    portal.confirmation_state, PortalConfirmationState):
                raise ShadowStatusError("Portalbestaetigungsstatus ist ungueltig")
            if (
                    not isinstance(portal.confirmed, bool)
                    or portal.confirmed is not (
                        portal.confirmation_state
                        is PortalConfirmationState.CONFIRMED)):
                raise ShadowStatusError(
                    "Portalstatus und confirmed widersprechen sich")
            if portal.first_revision > portal.last_revision:
                raise ShadowStatusError("Portalrevisionen sind widerspruechlich")
            if portal.last_revision > portal_revision:
                raise ShadowStatusError(
                    "Portalstand liegt vor der Portalgedaechtnisrevision")

    reachability_keys = []
    for side_status in source.reachability:
        if not isinstance(side_status.side, PortalSide):
            raise ShadowStatusError("Erreichbarkeitsseite ist ungueltig")
        if not isinstance(side_status.state, ReachabilityState):
            raise ShadowStatusError("Erreichbarkeitszustand ist ungueltig")
        if side_status.portal_id not in portal_id_set:
            raise ShadowStatusError(
                "Erreichbarkeit verweist auf ein unbekanntes Portal")
        if (
                side_status.map_revision is not None
                and portal_revision is not None
                and side_status.map_revision > portal_revision):
            raise ShadowStatusError(
                "Erreichbarkeit liegt vor der Portalgedaechtnisrevision")
        revision_fields_present = (
            side_status.map_revision is not None,
            side_status.observed_at_ns is not None,
            side_status.update_id is not None,
        )
        if any(revision_fields_present) and not all(revision_fields_present):
            raise ShadowStatusError(
                "Erreichbarkeitsrevision ist unvollstaendig")
        reachability_keys.append((side_status.portal_id, side_status.side))
    if len(set(reachability_keys)) != len(reachability_keys):
        raise ShadowStatusError(
            "Erreichbarkeitsstatus enthaelt doppelte Portalseiten")
    expected_reachability = {
        (portal_id, side)
        for portal_id in portal_id_set
        for side in (PortalSide.A, PortalSide.B)
    }
    if set(reachability_keys) != expected_reachability:
        raise ShadowStatusError(
            "Erreichbarkeitsstatus ist nicht fuer alle Portalseiten vollstaendig")

    region_ids = [region.region_id for region in graph.regions]
    if len(set(region_ids)) != len(region_ids):
        raise ShadowStatusError("Regionsstatus enthaelt doppelte IDs")
    region_id_set = set(region_ids)
    if (
            graph.current_region_id is not None
            and graph.current_region_id not in region_id_set):
        raise ShadowStatusError("Aktuelle Region fehlt im Regionsbestand")
    if graph.latest_revision is None and (
            graph.regions or graph.connections or graph.tasks):
        raise ShadowStatusError("Graphbestand ohne Graphrevision ist ungueltig")
    if graph.latest_revision is not None:
        for region in graph.regions:
            if (
                    region.first_revision > region.last_revision
                    or region.last_revision > graph.latest_revision):
                raise ShadowStatusError("Regionsrevisionen sind widerspruechlich")
            if not isinstance(
                    region.exploration_state, RegionExplorationState):
                raise ShadowStatusError(
                    "Regions-Erkundungsstatus ist ungueltig")
            exploration_metadata = (
                region.exploration_reason,
                region.exploration_revision,
            )
            if all(value is None for value in exploration_metadata):
                if region.exploration_state is not (
                        RegionExplorationState.UNASSESSED):
                    raise ShadowStatusError(
                        "Regions-Erkundungsstatus fehlt die Revision")
            elif any(value is None for value in exploration_metadata):
                raise ShadowStatusError(
                    "Regions-Erkundungsstatus ist unvollstaendig")
            else:
                if (
                        not isinstance(region.exploration_reason, str)
                        or not region.exploration_reason.strip()
                        or len(region.exploration_reason) > 256):
                    raise ShadowStatusError(
                        "Regions-Erkundungsgrund ist ungueltig")
                exploration_revision = _revision(
                    region.exploration_revision,
                    "region.exploration_revision",
                )
                if not (
                        region.first_revision <= exploration_revision
                        <= region.last_revision):
                    raise ShadowStatusError(
                        "Regions-Erkundungsrevision ist widerspruechlich")

    connection_ids = [
        connection.portal_id for connection in graph.connections]
    if len(set(connection_ids)) != len(connection_ids):
        raise ShadowStatusError("Verbindungsstatus enthaelt doppelte Portal-IDs")
    if not set(connection_ids).issubset(portal_id_set):
        raise ShadowStatusError("Verbindung verweist auf unbekanntes Portal")
    for connection in graph.connections:
        if (
                connection.first_revision > connection.last_revision
                or graph.latest_revision is None
                or connection.last_revision > graph.latest_revision):
            raise ShadowStatusError(
                "Verbindungsrevisionen sind widerspruechlich")
        if (
                connection.side_a_region_id not in region_id_set
                or connection.side_b_region_id not in region_id_set):
            raise ShadowStatusError("Verbindung verweist auf unbekannte Region")
        if connection.internal is not (
                connection.side_a_region_id == connection.side_b_region_id):
            raise ShadowStatusError(
                "Interner Verbindungsstatus widerspricht den Endpunkten")

    task_ids = [task.task_id for task in graph.tasks]
    if len(set(task_ids)) != len(task_ids):
        raise ShadowStatusError("Aufgabenstatus enthaelt doppelte IDs")
    for task in graph.tasks:
        if (
                not isinstance(task.kind, RegionTaskKind)
                or not isinstance(task.state, RegionTaskState)
                or task.created_revision > task.last_revision
                or graph.latest_revision is None
                or task.last_revision > graph.latest_revision):
            raise ShadowStatusError("Aufgabenstatus ist widerspruechlich")
        if task.region_id not in region_id_set:
            raise ShadowStatusError("Aufgabe verweist auf unbekannte Region")
    open_count = sum(
        task.state is RegionTaskState.OPEN for task in graph.tasks)
    completed_count = sum(
        task.state is RegionTaskState.COMPLETED for task in graph.tasks)
    if (
            open_count != graph.open_task_count
            or completed_count != graph.completed_task_count
            or open_count + completed_count != len(graph.tasks)):
        raise ShadowStatusError("Aufgabenzaehler widersprechen dem Bestand")
    if graph.confirmed_entry_count != sum(
            region.entry_count for region in graph.regions):
        raise ShadowStatusError("Eintrittszaehler widersprechen dem Bestand")

    alias_ids = [alias_id for alias_id, _target in graph.region_aliases]
    if len(set(alias_ids)) != len(alias_ids):
        raise ShadowStatusError("Regionsalias ist mehrfach belegt")
    if any(
            alias_id in region_id_set or target_id not in region_id_set
            for alias_id, target_id in graph.region_aliases):
        raise ShadowStatusError("Regionsalias verweist nicht eindeutig")

    tasks_by_region = {
        region_id: {
            task.task_id for task in graph.tasks
            if task.region_id == region_id}
        for region_id in region_id_set
    }
    connections_by_region = {
        region_id: {
            connection.portal_id for connection in graph.connections
            if region_id in (
                connection.side_a_region_id, connection.side_b_region_id)}
        for region_id in region_id_set
    }
    for region in graph.regions:
        if set(region.task_ids) != tasks_by_region[region.region_id]:
            raise ShadowStatusError(
                "Regions-Aufgabenreferenzen sind nicht vollstaendig")
        if set(region.portal_ids) != connections_by_region[region.region_id]:
            raise ShadowStatusError(
                "Regions-Portalreferenzen sind nicht vollstaendig")


def build_shadow_status_json(
        source: ShadowStatusSource,
        policy: Optional[ShadowStatusPolicy] = None) -> str:
    """Build one bounded canonical JSON document without publishing it."""
    if not isinstance(source, ShadowStatusSource):
        raise ShadowStatusError("source muss ShadowStatusSource sein")
    selected_policy = policy or ShadowStatusPolicy()
    if not isinstance(selected_policy, ShadowStatusPolicy):
        raise ShadowStatusError("policy muss ShadowStatusPolicy sein")
    _validate_source(source, selected_policy)

    portal_freshness = _source_freshness(
        source.portal_memory_revision,
        source.source_map_revision,
        selected_policy.maximum_revision_lag,
        source.portal_memory_age_seconds,
        selected_policy.maximum_portal_memory_age_seconds,
    )
    graph_freshness = _source_freshness(
        source.graph.latest_revision,
        source.source_map_revision,
        selected_policy.maximum_revision_lag,
        source.region_graph_age_seconds,
        selected_policy.maximum_region_graph_age_seconds,
    )
    map_freshness = _source_freshness(
        source.source_map_revision,
        source.source_map_revision,
        selected_policy.maximum_revision_lag,
        source.source_map_age_seconds,
        selected_policy.maximum_source_map_age_seconds,
    )
    stale_sources = tuple(
        name for name, status in (
            ("source_map", map_freshness),
            ("portal_memory", portal_freshness),
            ("region_graph", graph_freshness),
        )
        if status["state"] != "fresh"
    )

    reachability_by_portal = {
        portal_id: {
            item.side.value: item
            for item in source.reachability
            if item.portal_id == portal_id
        }
        for portal_id in (portal.portal_id for portal in source.portals)
    }
    portals = []
    for portal in sorted(source.portals, key=lambda item: item.portal_id):
        side_statuses = reachability_by_portal[portal.portal_id]
        portals.append({
            "portal_id": portal.portal_id,
            "confirmation_state": portal.confirmation_state.value,
            "first_revision": portal.first_revision,
            "last_revision": portal.last_revision,
            "observation_count": portal.observation_count,
            "qualified_evidence_count": portal.qualified_evidence_count,
            "confirmed_traversal_count": portal.confirmed_traversal_count,
            "reachability": [
                {
                    "side": side.value,
                    "state": side_statuses[side.value].state.value,
                    "reason": side_statuses[side.value].reason,
                    "recheck_condition": (
                        side_statuses[side.value].recheck_condition),
                    "map_revision": side_statuses[side.value].map_revision,
                    "observed_at_ns": side_statuses[side.value].observed_at_ns,
                }
                for side in (PortalSide.A, PortalSide.B)
            ],
        })

    graph = source.graph
    payload = {
        "schema_version": SCHEMA_VERSION,
        "mode": "shadow",
        "passive": True,
        "context": {
            "session_id": source.context.session_id,
            "map_id": source.context.map_id,
            "frame_id": source.context.frame_id,
        },
        "source": {
            "map_revision": source.source_map_revision,
            "source_map": map_freshness,
            "portal_memory": portal_freshness,
            "region_graph": graph_freshness,
            "stale": bool(stale_sources),
            "stale_sources": list(stale_sources),
        },
        "summary": {
            "current_region_id": graph.current_region_id,
            "region_count": len(graph.regions),
            "connection_count": len(graph.connections),
            "portal_count": len(source.portals),
            "confirmed_portal_count": sum(
                portal.confirmation_state is PortalConfirmationState.CONFIRMED
                for portal in source.portals),
            "unresolved_portal_count": sum(
                portal.confirmation_state is not PortalConfirmationState.CONFIRMED
                for portal in source.portals),
            "uncertain_portal_count": sum(
                portal.confirmation_state is PortalConfirmationState.UNCERTAIN
                for portal in source.portals),
            "confirmed_entry_count": graph.confirmed_entry_count,
            "open_task_count": graph.open_task_count,
            "completed_task_count": graph.completed_task_count,
            "unknown_reachability_side_count": sum(
                item.state is ReachabilityState.UNKNOWN
                for item in source.reachability),
            "blocked_reachability_side_count": sum(
                item.state is ReachabilityState.TEMPORARILY_BLOCKED
                for item in source.reachability),
        },
        "portals": portals,
        "regions": [
            {
                "region_id": region.region_id,
                "first_revision": region.first_revision,
                "last_revision": region.last_revision,
                "seen": region.seen,
                "entered": region.entered,
                "entry_count": region.entry_count,
                "exploration": {
                    "state": region.exploration_state.value,
                    "reason": region.exploration_reason,
                    "revision": region.exploration_revision,
                },
                "portal_ids": list(region.portal_ids),
                "alias_ids": list(region.alias_ids),
                "task_ids": list(region.task_ids),
            }
            for region in sorted(graph.regions, key=lambda item: item.region_id)
        ],
        "connections": [
            {
                "portal_id": connection.portal_id,
                "side_a_region_id": connection.side_a_region_id,
                "side_b_region_id": connection.side_b_region_id,
                "first_revision": connection.first_revision,
                "last_revision": connection.last_revision,
                "internal": connection.internal,
            }
            for connection in sorted(
                graph.connections, key=lambda item: item.portal_id)
        ],
        "tasks": [
            {
                "task_id": task.task_id,
                "region_id": task.region_id,
                "kind": task.kind.value,
                "subject_id": task.subject_id,
                "state": task.state.value,
                "created_revision": task.created_revision,
                "last_revision": task.last_revision,
            }
            for task in sorted(graph.tasks, key=lambda item: item.task_id)
        ],
        "region_aliases": [
            {"alias_id": alias_id, "canonical_region_id": canonical_id}
            for alias_id, canonical_id in sorted(graph.region_aliases)
        ],
    }
    raw_diagnostics = source.raw_map_correlation
    if raw_diagnostics is not None:
        payload["raw_map_correlation"] = {
            "enabled": True,
            "state": raw_diagnostics.state,
            "capacity": raw_diagnostics.capacity,
            "source_observations": raw_diagnostics.source_observations,
            "unique_sources": raw_diagnostics.unique_sources,
            "duplicate_sources": raw_diagnostics.duplicate_sources,
            "pending_sources": raw_diagnostics.pending_sources,
            "evicted_sources": raw_diagnostics.evicted_sources,
            "emitted_correlations": raw_diagnostics.emitted_correlations,
            "last_emitted_revision": (
                raw_diagnostics.last_emitted_revision),
        }
    serialized = json.dumps(
        payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    if len(serialized.encode("utf-8")) > selected_policy.max_serialized_bytes:
        raise ShadowStatusCapacityError(
            "Serialisierter Schattenstatus ueberschreitet die Bytegrenze")
    return serialized
