"""Pure provisional region graph built from confirmed portal identities.

The graph has no ROS, filesystem, planner, or actuator dependency.  It consumes
already validated portal snapshots and traversal verdicts.  It does not segment
maps, validate motion, generate navigation goals, or grant permission to move.
"""

from dataclasses import dataclass, field, replace
from enum import Enum
from typing import Dict, Optional, Tuple

from .portal_memory import (
    PortalConfirmationState,
    PortalMapContext,
    PortalSide,
    PortalSnapshot,
    TraversalDirection,
    TraversalEvent,
)


class RegionGraphError(ValueError):
    """Base class for rejected graph operations."""


class RegionContextMismatchError(RegionGraphError):
    """An input belongs to another session, map, or frame."""


class RegionGraphConflictError(RegionGraphError):
    """An ID or topological assignment conflicts with accepted history."""


class RegionGraphCapacityError(RegionGraphError):
    """A configured hard graph bound would be exceeded."""


class UnknownRegionError(RegionGraphError):
    """An operation references no known provisional region."""


class UnknownPortalConnectionError(RegionGraphError):
    """A traversal references no accepted portal connection."""


class StaleGraphUpdateError(RegionGraphError):
    """A previously unseen update predates the graph revision."""


def _identifier(value: object, name: str) -> str:
    if not isinstance(value, str) or not value or len(value) > 128:
        raise RegionGraphError(f"{name} muss 1 bis 128 Zeichen enthalten")
    if not value[0].isalnum() or any(
            not (character.isalnum() or character in "_.:-")
            for character in value):
        raise RegionGraphError(f"{name} enthaelt unzulaessige Zeichen")
    if not value.isascii():
        raise RegionGraphError(f"{name} muss ASCII sein")
    return value


def _revision(value: object, name: str = "map_revision") -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise RegionGraphError(f"{name} muss eine nichtnegative Ganzzahl sein")
    return value


def _text(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > 256:
        raise RegionGraphError(
            f"{name} muss 1 bis 256 Textzeichen enthalten")
    return value


@dataclass(frozen=True)
class RegionGraphPolicy:
    """Hard in-memory bounds, not physical apartment limits."""

    max_regions: int = 256
    max_connections: int = 512
    max_portal_observations: int = 4096
    max_traversal_events: int = 4096
    max_region_merges: int = 1024
    max_region_splits: int = 1024
    max_tasks: int = 4096
    max_task_updates: int = 8192
    max_region_exploration_updates: int = 8192

    def __post_init__(self) -> None:
        for name in (
                "max_regions", "max_connections",
                "max_portal_observations", "max_traversal_events",
                "max_region_merges", "max_region_splits",
                "max_tasks", "max_task_updates",
                "max_region_exploration_updates"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise RegionGraphError(f"{name} muss eine positive Ganzzahl sein")


@dataclass(frozen=True)
class RegionSeed:
    """Explicit start-region observation for one graph context."""

    seed_id: str
    context: PortalMapContext
    map_revision: int

    def __post_init__(self) -> None:
        _identifier(self.seed_id, "seed_id")
        if not isinstance(self.context, PortalMapContext):
            raise RegionGraphError("context muss PortalMapContext sein")
        _revision(self.map_revision)


@dataclass(frozen=True)
class RegionStartResult:
    region_id: str
    duplicate: bool = False


@dataclass(frozen=True)
class PortalLinkObservation:
    """Topological view of one portal from a known current region."""

    observation_id: str
    context: PortalMapContext
    map_revision: int
    portal: PortalSnapshot
    current_region_id: str
    current_side: PortalSide

    def __post_init__(self) -> None:
        _identifier(self.observation_id, "observation_id")
        if not isinstance(self.context, PortalMapContext):
            raise RegionGraphError("context muss PortalMapContext sein")
        _revision(self.map_revision)
        if not isinstance(self.portal, PortalSnapshot):
            raise RegionGraphError("portal muss PortalSnapshot sein")
        _identifier(self.current_region_id, "current_region_id")
        if not isinstance(self.current_side, PortalSide):
            raise RegionGraphError("current_side muss PortalSide sein")


class PortalLinkDisposition(str, Enum):
    CREATED = "created"
    MATCHED = "matched"
    DEFERRED = "deferred"


class RegionExplorationState(str, Enum):
    """Passive regional progress, never a whole-apartment completion result."""

    UNASSESSED = "unassessed"
    IN_PROGRESS = "in_progress"
    COMPLETE_CANDIDATE = "complete_candidate"


@dataclass(frozen=True)
class PortalLinkResult:
    disposition: PortalLinkDisposition
    portal_id: str
    current_region_id: str
    opposite_region_id: Optional[str]
    duplicate: bool = False


@dataclass(frozen=True)
class RegionSnapshot:
    region_id: str
    first_revision: int
    last_revision: int
    seen: bool
    entered: bool
    entry_count: int
    portal_ids: Tuple[str, ...]
    alias_ids: Tuple[str, ...]
    task_ids: Tuple[str, ...]
    exploration_state: RegionExplorationState
    exploration_reason: Optional[str]
    exploration_revision: Optional[int]


@dataclass(frozen=True)
class RegionExplorationUpdate:
    """One explicit regional progress statement without completion authority."""

    update_id: str
    context: PortalMapContext
    map_revision: int
    region_id: str
    state: RegionExplorationState
    reason: str

    def __post_init__(self) -> None:
        _identifier(self.update_id, "update_id")
        if not isinstance(self.context, PortalMapContext):
            raise RegionGraphError("context muss PortalMapContext sein")
        _revision(self.map_revision)
        _identifier(self.region_id, "region_id")
        if not isinstance(self.state, RegionExplorationState):
            raise RegionGraphError(
                "state muss RegionExplorationState sein")
        _text(self.reason, "reason")


@dataclass(frozen=True)
class RegionExplorationResult:
    region: RegionSnapshot
    state_changed: bool
    duplicate: bool = False


@dataclass(frozen=True)
class PortalConnectionSnapshot:
    portal_id: str
    side_a_region_id: str
    side_b_region_id: str
    first_revision: int
    last_revision: int
    internal: bool


@dataclass(frozen=True)
class GraphTraversalResult:
    event_id: str
    portal_id: str
    source_region_id: str
    target_region_id: str
    entered: bool
    current_region_id: str
    duplicate: bool = False


@dataclass(frozen=True)
class RegionGraphSnapshot:
    context: PortalMapContext
    latest_revision: Optional[int]
    current_region_id: Optional[str]
    regions: Tuple[RegionSnapshot, ...]
    connections: Tuple[PortalConnectionSnapshot, ...]
    confirmed_entry_count: int
    region_aliases: Tuple[Tuple[str, str], ...]
    tasks: Tuple["RegionTaskSnapshot", ...]
    open_task_count: int
    completed_task_count: int


@dataclass(frozen=True)
class RegionMerge:
    """Explicit external decision to unify two provisional regions."""

    merge_id: str
    context: PortalMapContext
    map_revision: int
    first_region_id: str
    second_region_id: str
    reason: str

    def __post_init__(self) -> None:
        _identifier(self.merge_id, "merge_id")
        if not isinstance(self.context, PortalMapContext):
            raise RegionGraphError("context muss PortalMapContext sein")
        _revision(self.map_revision)
        _identifier(self.first_region_id, "first_region_id")
        _identifier(self.second_region_id, "second_region_id")
        _text(self.reason, "reason")


@dataclass(frozen=True)
class RegionMergeResult:
    merge_id: str
    canonical_region_id: str
    removed_region_id: str
    duplicate: bool = False


@dataclass(frozen=True)
class RegionPortalEnd:
    """One concrete side of a portal connection assigned during a split."""

    portal_id: str
    side: PortalSide

    def __post_init__(self) -> None:
        _identifier(self.portal_id, "portal_id")
        if not isinstance(self.side, PortalSide):
            raise RegionGraphError("side muss PortalSide sein")


class RegionSplitTarget(str, Enum):
    RETAINED = "retained"
    CREATED = "created"


@dataclass(frozen=True)
class RegionSplit:
    """Explicit complete partition of one provisional region."""

    split_id: str
    context: PortalMapContext
    map_revision: int
    source_region_id: str
    retained_portal_ends: Tuple[RegionPortalEnd, ...]
    created_portal_ends: Tuple[RegionPortalEnd, ...]
    retained_task_ids: Tuple[str, ...]
    created_task_ids: Tuple[str, ...]
    state_target: RegionSplitTarget
    reason: str

    def __post_init__(self) -> None:
        _identifier(self.split_id, "split_id")
        if not isinstance(self.context, PortalMapContext):
            raise RegionGraphError("context muss PortalMapContext sein")
        _revision(self.map_revision)
        _identifier(self.source_region_id, "source_region_id")
        for name in ("retained_portal_ends", "created_portal_ends"):
            value = getattr(self, name)
            if not isinstance(value, tuple) or any(
                    not isinstance(item, RegionPortalEnd) for item in value):
                raise RegionGraphError(
                    f"{name} muss ein Tupel aus RegionPortalEnd sein")
            ordered = tuple(sorted(
                value, key=lambda item: (item.portal_id, item.side.value)))
            if len(set(ordered)) != len(ordered):
                raise RegionGraphError(f"{name} enthaelt Duplikate")
            object.__setattr__(self, name, ordered)
        for name in ("retained_task_ids", "created_task_ids"):
            value = getattr(self, name)
            if not isinstance(value, tuple):
                raise RegionGraphError(f"{name} muss ein Tupel sein")
            for task_id in value:
                _identifier(task_id, f"{name}-Eintrag")
            ordered = tuple(sorted(value))
            if len(set(ordered)) != len(ordered):
                raise RegionGraphError(f"{name} enthaelt Duplikate")
            object.__setattr__(self, name, ordered)
        if not isinstance(self.state_target, RegionSplitTarget):
            raise RegionGraphError("state_target muss RegionSplitTarget sein")
        _text(self.reason, "reason")


@dataclass(frozen=True)
class RegionSplitResult:
    split_id: str
    retained_region_id: str
    created_region_id: str
    state_region_id: str
    duplicate: bool = False


class RegionTaskKind(str, Enum):
    FRONTIER = "frontier"
    PORTAL = "portal"
    OBSERVATION = "observation"


class RegionTaskState(str, Enum):
    OPEN = "open"
    COMPLETED = "completed"


@dataclass(frozen=True)
class RegionTaskUpdate:
    """Idempotent passive task-reference update without execution semantics."""

    update_id: str
    task_id: str
    context: PortalMapContext
    map_revision: int
    region_id: str
    kind: RegionTaskKind
    subject_id: str
    state: RegionTaskState

    def __post_init__(self) -> None:
        _identifier(self.update_id, "update_id")
        _identifier(self.task_id, "task_id")
        if not isinstance(self.context, PortalMapContext):
            raise RegionGraphError("context muss PortalMapContext sein")
        _revision(self.map_revision)
        _identifier(self.region_id, "region_id")
        if not isinstance(self.kind, RegionTaskKind):
            raise RegionGraphError("kind muss RegionTaskKind sein")
        _identifier(self.subject_id, "subject_id")
        if not isinstance(self.state, RegionTaskState):
            raise RegionGraphError("state muss RegionTaskState sein")


@dataclass(frozen=True)
class RegionTaskSnapshot:
    task_id: str
    region_id: str
    kind: RegionTaskKind
    subject_id: str
    state: RegionTaskState
    created_revision: int
    last_revision: int


@dataclass(frozen=True)
class RegionTaskResult:
    task: RegionTaskSnapshot
    created: bool
    state_changed: bool
    duplicate: bool = False


@dataclass
class _RegionState:
    region_id: str
    first_revision: int
    last_revision: int
    seen: bool
    entered: bool
    entry_count: int = 0
    portal_ids: set[str] = field(default_factory=set)
    alias_ids: set[str] = field(default_factory=set)
    task_ids: set[str] = field(default_factory=set)
    exploration_state: RegionExplorationState = (
        RegionExplorationState.UNASSESSED)
    exploration_reason: Optional[str] = None
    exploration_revision: Optional[int] = None


@dataclass
class _ConnectionState:
    portal_id: str
    side_a_region_id: str
    side_b_region_id: str
    first_revision: int
    last_revision: int


@dataclass
class _TaskState:
    task_id: str
    region_id: str
    kind: RegionTaskKind
    subject_id: str
    state: RegionTaskState
    created_revision: int
    last_revision: int


class RegionGraph:
    """Bounded provisional topology for one immutable map context."""

    def __init__(
            self, context: PortalMapContext,
            policy: Optional[RegionGraphPolicy] = None) -> None:
        if not isinstance(context, PortalMapContext):
            raise RegionGraphError("context muss PortalMapContext sein")
        self._context = context
        self._policy = policy or RegionGraphPolicy()
        if not isinstance(self._policy, RegionGraphPolicy):
            raise RegionGraphError("policy muss RegionGraphPolicy sein")
        self._regions: Dict[str, _RegionState] = {}
        self._connections: Dict[str, _ConnectionState] = {}
        self._portal_observations: Dict[
            str, Tuple[PortalLinkObservation, PortalLinkResult]] = {}
        self._traversal_events: Dict[
            str, Tuple[TraversalEvent, GraphTraversalResult]] = {}
        self._region_merges: Dict[
            str, Tuple[RegionMerge, RegionMergeResult]] = {}
        self._region_splits: Dict[
            str, Tuple[RegionSplit, RegionSplitResult]] = {}
        self._region_aliases: Dict[str, str] = {}
        self._tasks: Dict[str, _TaskState] = {}
        self._task_updates: Dict[
            str, Tuple[RegionTaskUpdate, RegionTaskResult]] = {}
        self._region_exploration_updates: Dict[
            str, Tuple[
                RegionExplorationUpdate, RegionExplorationResult]] = {}
        self._start_seed: Optional[RegionSeed] = None
        self._start_result: Optional[RegionStartResult] = None
        self._current_region_id: Optional[str] = None
        self._next_region_number = 1
        self._latest_revision = -1

    @property
    def context(self) -> PortalMapContext:
        return self._context

    @property
    def current_region_id(self) -> Optional[str]:
        return self._current_region_id

    @property
    def latest_revision(self) -> Optional[int]:
        return None if self._latest_revision < 0 else self._latest_revision

    def start(self, seed: RegionSeed) -> RegionStartResult:
        """Create exactly one entered start region, idempotently."""
        if not isinstance(seed, RegionSeed):
            raise RegionGraphError("seed muss RegionSeed sein")
        self._require_context(seed.context)
        if self._start_seed is not None:
            if self._start_seed != seed:
                raise RegionGraphConflictError(
                    "Startregion wurde mit anderem Inhalt erneut gesetzt")
            return replace(self._start_result, duplicate=True)
        self._require_current_revision(seed.map_revision)
        if len(self._regions) >= self._policy.max_regions:
            raise RegionGraphCapacityError("Regionsspeicher ist voll")

        region = self._new_region(
            revision=seed.map_revision, seen=True, entered=True)
        self._regions[region.region_id] = region
        self._current_region_id = region.region_id
        self._latest_revision = seed.map_revision
        self._start_seed = seed
        self._start_result = RegionStartResult(region_id=region.region_id)
        return self._start_result

    def observe_portal(
            self, observation: PortalLinkObservation) -> PortalLinkResult:
        """Associate a confirmed portal or defer uncertain evidence."""
        if not isinstance(observation, PortalLinkObservation):
            raise RegionGraphError(
                "observation muss PortalLinkObservation sein")
        self._require_context(observation.context)

        previous = self._portal_observations.get(observation.observation_id)
        if previous is not None:
            previous_observation, previous_result = previous
            if previous_observation != observation:
                raise RegionGraphConflictError(
                    "observation_id wurde widerspruechlich wiederverwendet")
            connection = self._connections.get(previous_result.portal_id)
            if (
                    connection is not None
                    and previous_result.opposite_region_id is not None):
                current_region_id = self._region_on_side(
                    connection, previous_observation.current_side)
                opposite_region_id = self._region_on_side(
                    connection,
                    self._opposite_side(previous_observation.current_side),
                )
            else:
                current_region_id = self.resolve_region_id(
                    previous_result.current_region_id)
                opposite_region_id = (
                    None if previous_result.opposite_region_id is None
                    else self.resolve_region_id(
                        previous_result.opposite_region_id))
            return replace(
                previous_result,
                current_region_id=current_region_id,
                opposite_region_id=opposite_region_id,
                duplicate=True,
            )

        current_region = self._require_region(observation.current_region_id)
        if self._current_region_id != current_region.region_id:
            raise RegionGraphConflictError(
                "Portalbeobachtung stammt nicht aus der aktuellen Region")
        self._require_current_revision(observation.map_revision)
        self._validate_portal_snapshot(observation)
        if (
                len(self._portal_observations)
                >= self._policy.max_portal_observations):
            raise RegionGraphCapacityError("Portalbeobachtungsspeicher ist voll")

        portal = observation.portal
        if portal.confirmation_state is not PortalConfirmationState.CONFIRMED:
            result = PortalLinkResult(
                disposition=PortalLinkDisposition.DEFERRED,
                portal_id=portal.portal_id,
                current_region_id=current_region.region_id,
                opposite_region_id=None,
            )
        else:
            connection = self._connections.get(portal.portal_id)
            if connection is None:
                if len(self._connections) >= self._policy.max_connections:
                    raise RegionGraphCapacityError("Verbindungsspeicher ist voll")
                if len(self._regions) >= self._policy.max_regions:
                    raise RegionGraphCapacityError("Regionsspeicher ist voll")
                opposite_region = self._new_region(
                    revision=observation.map_revision,
                    seen=True,
                    entered=False,
                )
                connection = self._new_connection(
                    portal_id=portal.portal_id,
                    current_region_id=current_region.region_id,
                    current_side=observation.current_side,
                    opposite_region_id=opposite_region.region_id,
                    revision=observation.map_revision,
                )
                self._regions[opposite_region.region_id] = opposite_region
                self._connections[portal.portal_id] = connection
                current_region.portal_ids.add(portal.portal_id)
                opposite_region.portal_ids.add(portal.portal_id)
                result = PortalLinkResult(
                    disposition=PortalLinkDisposition.CREATED,
                    portal_id=portal.portal_id,
                    current_region_id=current_region.region_id,
                    opposite_region_id=opposite_region.region_id,
                )
            else:
                assigned_region_id = self._region_on_side(
                    connection, observation.current_side)
                if assigned_region_id != current_region.region_id:
                    raise RegionGraphConflictError(
                        "Portalseite widerspricht der bestehenden Region")
                connection.last_revision = max(
                    connection.last_revision, observation.map_revision)
                opposite_region_id = self._region_on_side(
                    connection, self._opposite_side(observation.current_side))
                opposite_region = self._require_region(opposite_region_id)
                opposite_region.last_revision = max(
                    opposite_region.last_revision, observation.map_revision)
                result = PortalLinkResult(
                    disposition=PortalLinkDisposition.MATCHED,
                    portal_id=portal.portal_id,
                    current_region_id=current_region.region_id,
                    opposite_region_id=opposite_region.region_id,
                )
            current_region.last_revision = max(
                current_region.last_revision, observation.map_revision)

        self._portal_observations[observation.observation_id] = (
            observation, result)
        self._latest_revision = max(
            self._latest_revision, observation.map_revision)
        return result

    def record_traversal(self, event: TraversalEvent) -> GraphTraversalResult:
        """Apply an external traversal verdict without validating motion."""
        if not isinstance(event, TraversalEvent):
            raise RegionGraphError("event muss TraversalEvent sein")
        self._require_context(event.context)

        previous = self._traversal_events.get(event.event_id)
        if previous is not None:
            previous_event, previous_result = previous
            if previous_event != event:
                raise RegionGraphConflictError(
                    "event_id wurde widerspruechlich wiederverwendet")
            connection = self._connections.get(previous_event.portal_id)
            if connection is None:
                raise UnknownPortalConnectionError(
                    f"Unbekannte Portalverbindung: {previous_event.portal_id}")
            source_region_id, target_region_id = self._traversal_regions(
                connection, previous_event.direction)
            return replace(
                previous_result,
                source_region_id=source_region_id,
                target_region_id=target_region_id,
                entered=False,
                current_region_id=self._current_region_id,
                duplicate=True,
            )

        connection = self._connections.get(event.portal_id)
        if connection is None:
            raise UnknownPortalConnectionError(
                f"Unbekannte Portalverbindung: {event.portal_id}")
        self._require_current_revision(event.map_revision)
        if len(self._traversal_events) >= self._policy.max_traversal_events:
            raise RegionGraphCapacityError("Durchfahrtsverlauf ist voll")

        source_region_id, target_region_id = self._traversal_regions(
            connection, event.direction)
        if self._current_region_id != source_region_id:
            raise RegionGraphConflictError(
                "Durchfahrtsrichtung beginnt nicht in der aktuellen Region")

        entered = (
            event.crossing_confirmed
            and source_region_id != target_region_id)
        if entered:
            source = self._require_region(source_region_id)
            target = self._require_region(target_region_id)
            source.last_revision = max(source.last_revision, event.map_revision)
            target.last_revision = max(target.last_revision, event.map_revision)
            target.seen = True
            target.entered = True
            target.entry_count += 1
            self._current_region_id = target_region_id

        result = GraphTraversalResult(
            event_id=event.event_id,
            portal_id=event.portal_id,
            source_region_id=source_region_id,
            target_region_id=target_region_id,
            entered=entered,
            current_region_id=self._current_region_id,
        )
        self._traversal_events[event.event_id] = (event, result)
        self._latest_revision = max(self._latest_revision, event.map_revision)
        return result

    def update_task(self, update: RegionTaskUpdate) -> RegionTaskResult:
        """Create or complete one passive task reference idempotently."""
        if not isinstance(update, RegionTaskUpdate):
            raise RegionGraphError("update muss RegionTaskUpdate sein")
        self._require_context(update.context)

        previous = self._task_updates.get(update.update_id)
        if previous is not None:
            previous_update, previous_result = previous
            if previous_update != update:
                raise RegionGraphConflictError(
                    "update_id wurde widerspruechlich wiederverwendet")
            return RegionTaskResult(
                task=self.task(previous_update.task_id),
                created=False,
                state_changed=False,
                duplicate=True,
            )

        region = self._require_region(update.region_id)
        self._require_current_revision(update.map_revision)
        if len(self._task_updates) >= self._policy.max_task_updates:
            raise RegionGraphCapacityError("Aufgabenaktualisierungsverlauf ist voll")

        state = self._tasks.get(update.task_id)
        if state is None:
            if len(self._tasks) >= self._policy.max_tasks:
                raise RegionGraphCapacityError("Aufgabenspeicher ist voll")
            state = _TaskState(
                task_id=update.task_id,
                region_id=region.region_id,
                kind=update.kind,
                subject_id=update.subject_id,
                state=update.state,
                created_revision=update.map_revision,
                last_revision=update.map_revision,
            )
            self._tasks[state.task_id] = state
            region.task_ids.add(state.task_id)
            created = True
            state_changed = False
        else:
            if (
                    state.kind is not update.kind
                    or state.subject_id != update.subject_id
                    or state.region_id != region.region_id):
                raise RegionGraphConflictError(
                    "Aufgabenidentitaet, Subjekt oder Region widerspricht")
            if update.map_revision <= state.last_revision:
                raise StaleGraphUpdateError(
                    "Aufgabenaktualisierung ist nicht neuer als der Zustand")
            if (
                    state.state is RegionTaskState.COMPLETED
                    and update.state is RegionTaskState.OPEN):
                raise RegionGraphConflictError(
                    "Abgeschlossene Aufgabe darf hier nicht reaktiviert werden")
            created = False
            state_changed = state.state is not update.state
            state.state = update.state
            state.last_revision = update.map_revision

        result = RegionTaskResult(
            task=self._task_snapshot(state),
            created=created,
            state_changed=state_changed,
        )
        self._task_updates[update.update_id] = (update, result)
        region.last_revision = max(region.last_revision, update.map_revision)
        self._latest_revision = max(
            self._latest_revision, update.map_revision)
        return result

    def update_region_exploration(
            self,
            update: RegionExplorationUpdate,
    ) -> RegionExplorationResult:
        """Advance one passive regional state without declaring completion."""
        if not isinstance(update, RegionExplorationUpdate):
            raise RegionGraphError(
                "update muss RegionExplorationUpdate sein")
        self._require_context(update.context)

        previous = self._region_exploration_updates.get(update.update_id)
        if previous is not None:
            previous_update, _previous_result = previous
            if previous_update != update:
                raise RegionGraphConflictError(
                    "update_id wurde widerspruechlich wiederverwendet")
            return RegionExplorationResult(
                region=self.region(previous_update.region_id),
                state_changed=False,
                duplicate=True,
            )

        region = self._require_region(update.region_id)
        self._require_current_revision(update.map_revision)
        if (
                len(self._region_exploration_updates)
                >= self._policy.max_region_exploration_updates):
            raise RegionGraphCapacityError(
                "Regionsstatus-Aktualisierungsverlauf ist voll")
        if (
                region.exploration_revision is not None
                and update.map_revision <= region.exploration_revision):
            raise StaleGraphUpdateError(
                "Regionsstatus-Aktualisierung ist nicht neuer als der Zustand")

        allowed = {
            RegionExplorationState.UNASSESSED: {
                RegionExplorationState.UNASSESSED,
                RegionExplorationState.IN_PROGRESS,
            },
            RegionExplorationState.IN_PROGRESS: {
                RegionExplorationState.IN_PROGRESS,
                RegionExplorationState.COMPLETE_CANDIDATE,
            },
            RegionExplorationState.COMPLETE_CANDIDATE: {
                RegionExplorationState.COMPLETE_CANDIDATE,
            },
        }
        if update.state not in allowed[region.exploration_state]:
            raise RegionGraphConflictError(
                "Regionsstatus darf keine Stufe ueberspringen oder zurueckfallen")

        state_changed = region.exploration_state is not update.state
        region.exploration_state = update.state
        region.exploration_reason = update.reason
        region.exploration_revision = update.map_revision
        region.last_revision = max(region.last_revision, update.map_revision)
        self._latest_revision = max(
            self._latest_revision, update.map_revision)
        result = RegionExplorationResult(
            region=self._region_snapshot(region),
            state_changed=state_changed,
        )
        self._region_exploration_updates[update.update_id] = (update, result)
        return result

    def merge_regions(self, merge: RegionMerge) -> RegionMergeResult:
        """Apply one explicit merge and preserve all old region references."""
        if not isinstance(merge, RegionMerge):
            raise RegionGraphError("merge muss RegionMerge sein")
        self._require_context(merge.context)

        previous = self._region_merges.get(merge.merge_id)
        if previous is not None:
            previous_merge, previous_result = previous
            if previous_merge != merge:
                raise RegionGraphConflictError(
                    "merge_id wurde widerspruechlich wiederverwendet")
            return replace(
                previous_result,
                canonical_region_id=self.resolve_region_id(
                    previous_result.canonical_region_id),
                duplicate=True,
            )

        first_id = self.resolve_region_id(merge.first_region_id)
        second_id = self.resolve_region_id(merge.second_region_id)
        if first_id == second_id:
            raise RegionGraphConflictError(
                "Region kann nicht mit sich selbst vereinigt werden")
        self._require_current_revision(merge.map_revision)
        if len(self._region_merges) >= self._policy.max_region_merges:
            raise RegionGraphCapacityError("Regionsvereinigungsverlauf ist voll")

        canonical_id, removed_id = sorted((first_id, second_id))
        canonical = self._regions[canonical_id]
        removed = self._regions[removed_id]
        canonical.first_revision = min(
            canonical.first_revision, removed.first_revision)
        canonical.last_revision = max(
            canonical.last_revision, removed.last_revision,
            merge.map_revision)
        canonical.seen = canonical.seen or removed.seen
        canonical.entered = canonical.entered or removed.entered
        canonical.entry_count += removed.entry_count
        if canonical.exploration_state is not removed.exploration_state:
            exploration_order = (
                RegionExplorationState.UNASSESSED,
                RegionExplorationState.IN_PROGRESS,
                RegionExplorationState.COMPLETE_CANDIDATE,
            )
            canonical.exploration_state = min(
                canonical.exploration_state,
                removed.exploration_state,
                key=exploration_order.index,
            )
            canonical.exploration_reason = "region_merge_conservative"
            canonical.exploration_revision = merge.map_revision
        canonical.portal_ids.update(removed.portal_ids)
        canonical.alias_ids.update(removed.alias_ids)
        canonical.alias_ids.add(removed_id)
        canonical.task_ids.update(removed.task_ids)

        for connection in self._connections.values():
            if connection.side_a_region_id == removed_id:
                connection.side_a_region_id = canonical_id
            if connection.side_b_region_id == removed_id:
                connection.side_b_region_id = canonical_id
            if (
                    connection.side_a_region_id == canonical_id
                    or connection.side_b_region_id == canonical_id):
                connection.last_revision = max(
                    connection.last_revision, merge.map_revision)

        for alias_id, target_id in tuple(self._region_aliases.items()):
            if target_id == removed_id:
                self._region_aliases[alias_id] = canonical_id
        self._region_aliases[removed_id] = canonical_id
        for task in self._tasks.values():
            if task.region_id == removed_id:
                task.region_id = canonical_id
        del self._regions[removed_id]
        if self._current_region_id == removed_id:
            self._current_region_id = canonical_id

        result = RegionMergeResult(
            merge_id=merge.merge_id,
            canonical_region_id=canonical_id,
            removed_region_id=removed_id,
        )
        self._region_merges[merge.merge_id] = (merge, result)
        self._latest_revision = max(
            self._latest_revision, merge.map_revision)
        return result

    def split_region(self, split: RegionSplit) -> RegionSplitResult:
        """Apply one explicit, complete partition without inferring geometry."""
        if not isinstance(split, RegionSplit):
            raise RegionGraphError("split muss RegionSplit sein")
        self._require_context(split.context)

        previous = self._region_splits.get(split.split_id)
        if previous is not None:
            previous_split, previous_result = previous
            if previous_split != split:
                raise RegionGraphConflictError(
                    "split_id wurde widerspruechlich wiederverwendet")
            return replace(
                previous_result,
                retained_region_id=self.resolve_region_id(
                    previous_result.retained_region_id),
                created_region_id=self.resolve_region_id(
                    previous_result.created_region_id),
                state_region_id=self.resolve_region_id(
                    previous_result.state_region_id),
                duplicate=True,
            )

        source = self._require_region(split.source_region_id)
        self._require_current_revision(split.map_revision)
        if len(self._region_splits) >= self._policy.max_region_splits:
            raise RegionGraphCapacityError("Regionsteilungsverlauf ist voll")
        if len(self._regions) >= self._policy.max_regions:
            raise RegionGraphCapacityError("Regionsspeicher ist voll")

        expected_portal_ends = self._portal_ends(source.region_id)
        retained_portal_ends = set(split.retained_portal_ends)
        created_portal_ends = set(split.created_portal_ends)
        if retained_portal_ends & created_portal_ends:
            raise RegionGraphConflictError(
                "Portalende wurde beiden Ergebnisregionen zugewiesen")
        if retained_portal_ends | created_portal_ends != expected_portal_ends:
            raise RegionGraphConflictError(
                "Portalenden sind nicht vollstaendig und exakt zugewiesen")

        expected_task_ids = set(source.task_ids)
        retained_task_ids = set(split.retained_task_ids)
        created_task_ids = set(split.created_task_ids)
        if retained_task_ids & created_task_ids:
            raise RegionGraphConflictError(
                "Aufgabe wurde beiden Ergebnisregionen zugewiesen")
        if retained_task_ids | created_task_ids != expected_task_ids:
            raise RegionGraphConflictError(
                "Aufgaben sind nicht vollstaendig und exakt zugewiesen")

        created = self._new_region(
            revision=split.map_revision, seen=False, entered=False)
        source.last_revision = max(
            source.last_revision, split.map_revision)
        if split.state_target is RegionSplitTarget.CREATED:
            created.seen = source.seen
            created.entered = source.entered
            created.entry_count = source.entry_count
            source.seen = False
            source.entered = False
            source.entry_count = 0
            state_region = created
        else:
            state_region = source

        # A geometry split changes the assessed scope of both resulting
        # regions. Neither child may inherit a completion candidate silently.
        for region in (source, created):
            region.exploration_state = RegionExplorationState.UNASSESSED
            region.exploration_reason = "region_split_requires_reassessment"
            region.exploration_revision = split.map_revision

        source.portal_ids = {
            portal_end.portal_id for portal_end in retained_portal_ends}
        created.portal_ids = {
            portal_end.portal_id for portal_end in created_portal_ends}
        source.task_ids = retained_task_ids
        created.task_ids = created_task_ids

        for portal_end in created_portal_ends:
            connection = self._connections[portal_end.portal_id]
            if portal_end.side is PortalSide.A:
                connection.side_a_region_id = created.region_id
            else:
                connection.side_b_region_id = created.region_id
            connection.last_revision = max(
                connection.last_revision, split.map_revision)
        for portal_end in retained_portal_ends:
            connection = self._connections[portal_end.portal_id]
            connection.last_revision = max(
                connection.last_revision, split.map_revision)
        for task_id in created_task_ids:
            self._tasks[task_id].region_id = created.region_id

        self._regions[created.region_id] = created
        if self._current_region_id == source.region_id:
            self._current_region_id = state_region.region_id

        result = RegionSplitResult(
            split_id=split.split_id,
            retained_region_id=source.region_id,
            created_region_id=created.region_id,
            state_region_id=state_region.region_id,
        )
        self._region_splits[split.split_id] = (split, result)
        self._latest_revision = max(
            self._latest_revision, split.map_revision)
        return result

    def region(self, region_id: str) -> RegionSnapshot:
        return self._region_snapshot(self._require_region(region_id))

    def task(self, task_id: str) -> RegionTaskSnapshot:
        _identifier(task_id, "task_id")
        try:
            state = self._tasks[task_id]
        except KeyError as exc:
            raise RegionGraphError(f"Unbekannte Aufgabe: {task_id}") from exc
        return self._task_snapshot(state)

    def tasks(
            self, region_id: Optional[str] = None,
            *, kind: Optional[RegionTaskKind] = None,
            state: Optional[RegionTaskState] = None,
    ) -> Tuple[RegionTaskSnapshot, ...]:
        """Return deterministic passive references with optional exact filters."""
        canonical_region_id = None
        if region_id is not None:
            canonical_region_id = self.resolve_region_id(region_id)
        if kind is not None and not isinstance(kind, RegionTaskKind):
            raise RegionGraphError("kind muss RegionTaskKind sein")
        if state is not None and not isinstance(state, RegionTaskState):
            raise RegionGraphError("state muss RegionTaskState sein")
        return tuple(
            self._task_snapshot(task)
            for task in sorted(
                self._tasks.values(), key=lambda item: item.task_id)
            if (
                canonical_region_id is None
                or task.region_id == canonical_region_id)
            and (kind is None or task.kind is kind)
            and (state is None or task.state is state)
        )

    def resolve_region_id(self, region_id: str) -> str:
        """Resolve a canonical region or any retained historical alias."""
        _identifier(region_id, "region_id")
        if region_id in self._regions:
            return region_id
        try:
            canonical_id = self._region_aliases[region_id]
        except KeyError as exc:
            raise UnknownRegionError(
                f"Unbekannte Region: {region_id}") from exc
        if canonical_id not in self._regions:
            raise RegionGraphConflictError(
                "Regionsalias verweist nicht auf eine kanonische Region")
        return canonical_id

    def connection(self, portal_id: str) -> PortalConnectionSnapshot:
        _identifier(portal_id, "portal_id")
        try:
            state = self._connections[portal_id]
        except KeyError as exc:
            raise UnknownPortalConnectionError(
                f"Unbekannte Portalverbindung: {portal_id}") from exc
        return self._connection_snapshot(state)

    def snapshot(self) -> RegionGraphSnapshot:
        return RegionGraphSnapshot(
            context=self._context,
            latest_revision=self.latest_revision,
            current_region_id=self._current_region_id,
            regions=tuple(
                self._region_snapshot(self._regions[region_id])
                for region_id in sorted(self._regions)),
            connections=tuple(
                self._connection_snapshot(self._connections[portal_id])
                for portal_id in sorted(self._connections)),
            confirmed_entry_count=sum(
                region.entry_count for region in self._regions.values()),
            region_aliases=tuple(sorted(self._region_aliases.items())),
            tasks=self.tasks(),
            open_task_count=sum(
                task.state is RegionTaskState.OPEN
                for task in self._tasks.values()),
            completed_task_count=sum(
                task.state is RegionTaskState.COMPLETED
                for task in self._tasks.values()),
        )

    def _new_region(
            self, revision: int, *, seen: bool, entered: bool) -> _RegionState:
        region_id = f"region_{self._next_region_number:06d}"
        self._next_region_number += 1
        return _RegionState(
            region_id=region_id,
            first_revision=revision,
            last_revision=revision,
            seen=seen,
            entered=entered,
        )

    @staticmethod
    def _new_connection(
            portal_id: str, current_region_id: str,
            current_side: PortalSide, opposite_region_id: str,
            revision: int) -> _ConnectionState:
        if current_side is PortalSide.A:
            side_a_region_id = current_region_id
            side_b_region_id = opposite_region_id
        else:
            side_a_region_id = opposite_region_id
            side_b_region_id = current_region_id
        return _ConnectionState(
            portal_id=portal_id,
            side_a_region_id=side_a_region_id,
            side_b_region_id=side_b_region_id,
            first_revision=revision,
            last_revision=revision,
        )

    @staticmethod
    def _region_on_side(
            connection: _ConnectionState, side: PortalSide) -> str:
        if side is PortalSide.A:
            return connection.side_a_region_id
        return connection.side_b_region_id

    @staticmethod
    def _opposite_side(side: PortalSide) -> PortalSide:
        if side is PortalSide.A:
            return PortalSide.B
        return PortalSide.A

    @staticmethod
    def _traversal_regions(
            connection: _ConnectionState,
            direction: TraversalDirection) -> Tuple[str, str]:
        if direction is TraversalDirection.A_TO_B:
            return (
                connection.side_a_region_id,
                connection.side_b_region_id,
            )
        return (
            connection.side_b_region_id,
            connection.side_a_region_id,
        )

    def _validate_portal_snapshot(
            self, observation: PortalLinkObservation) -> None:
        portal = observation.portal
        _identifier(portal.portal_id, "portal_id")
        if not isinstance(
                portal.confirmation_state, PortalConfirmationState):
            raise RegionGraphError(
                "portal.confirmation_state ist ungueltig")
        expected_confirmed = (
            portal.confirmation_state is PortalConfirmationState.CONFIRMED)
        if portal.confirmed is not expected_confirmed:
            raise RegionGraphError(
                "Portalstatus und confirmed widersprechen sich")
        if portal.last_revision > observation.map_revision:
            raise StaleGraphUpdateError(
                "Portalstand stammt aus einer zukuenftigen Revision")

    def _require_context(self, context: PortalMapContext) -> None:
        if context != self._context:
            raise RegionContextMismatchError(
                "Eingabe passt nicht zu Sitzung, Karte und Frame")

    def _require_current_revision(self, revision: int) -> None:
        if revision < self._latest_revision:
            raise StaleGraphUpdateError(
                "Eingabe stammt aus einer veralteten Kartenrevision")

    def _require_region(self, region_id: str) -> _RegionState:
        return self._regions[self.resolve_region_id(region_id)]

    def _portal_ends(self, region_id: str) -> set[RegionPortalEnd]:
        portal_ends = set()
        for connection in self._connections.values():
            if connection.side_a_region_id == region_id:
                portal_ends.add(RegionPortalEnd(
                    connection.portal_id, PortalSide.A))
            if connection.side_b_region_id == region_id:
                portal_ends.add(RegionPortalEnd(
                    connection.portal_id, PortalSide.B))
        return portal_ends

    @staticmethod
    def _region_snapshot(state: _RegionState) -> RegionSnapshot:
        return RegionSnapshot(
            region_id=state.region_id,
            first_revision=state.first_revision,
            last_revision=state.last_revision,
            seen=state.seen,
            entered=state.entered,
            entry_count=state.entry_count,
            portal_ids=tuple(sorted(state.portal_ids)),
            alias_ids=tuple(sorted(state.alias_ids)),
            task_ids=tuple(sorted(state.task_ids)),
            exploration_state=state.exploration_state,
            exploration_reason=state.exploration_reason,
            exploration_revision=state.exploration_revision,
        )

    @staticmethod
    def _task_snapshot(state: _TaskState) -> RegionTaskSnapshot:
        return RegionTaskSnapshot(
            task_id=state.task_id,
            region_id=state.region_id,
            kind=state.kind,
            subject_id=state.subject_id,
            state=state.state,
            created_revision=state.created_revision,
            last_revision=state.last_revision,
        )

    @staticmethod
    def _connection_snapshot(
            state: _ConnectionState) -> PortalConnectionSnapshot:
        return PortalConnectionSnapshot(
            portal_id=state.portal_id,
            side_a_region_id=state.side_a_region_id,
            side_b_region_id=state.side_b_region_id,
            first_revision=state.first_revision,
            last_revision=state.last_revision,
            internal=(
                state.side_a_region_id == state.side_b_region_id),
        )
