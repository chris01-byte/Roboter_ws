"""Pure in-memory identity tracking for normalized portal observations.

This module deliberately has no ROS, Nav2, filesystem, or actuator imports.
Detectors remain responsible for converting grid observations into metric
coordinates in one validated map frame.  The memory only associates those
observations inside one explicit mapping session and map epoch.

All default matching limits are synthetic software starting values.  They are
not measured door, footprint, localization, or hardware tolerances.
"""

from dataclasses import dataclass, field, replace
from enum import Enum
import math
import re
from typing import Dict, Optional, Tuple


_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")


class PortalMemoryError(ValueError):
    """Base class for rejected observations and invalid memory operations."""


class ContextMismatchError(PortalMemoryError):
    """The observation belongs to another session, map, or frame."""


class ObservationConflictError(PortalMemoryError):
    """An observation ID was reused with different content."""


class StaleObservationError(PortalMemoryError):
    """A previously unseen observation predates the accepted map revision."""


class MemoryCapacityError(PortalMemoryError):
    """A configured hard memory bound would be exceeded."""


class UnknownPortalError(PortalMemoryError):
    """An event or state update references no known portal identity."""


class TraversalConflictError(PortalMemoryError):
    """A traversal event ID was reused with different content."""


class ReachabilityConflictError(PortalMemoryError):
    """A reachability update ID was reused with different content."""


def _validate_identifier(value: object, name: str) -> str:
    if not isinstance(value, str) or _IDENTIFIER.fullmatch(value) is None:
        raise PortalMemoryError(
            f"{name} muss 1 bis 128 sichere ASCII-Zeichen enthalten")
    return value


def _finite_nonnegative(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise PortalMemoryError(f"{name} muss eine endliche Zahl sein")
    result = float(value)
    if not math.isfinite(result) or result < 0.0:
        raise PortalMemoryError(f"{name} muss endlich und nichtnegativ sein")
    return result


def _finite_number(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise PortalMemoryError(f"{name} muss eine endliche Zahl sein")
    result = float(value)
    if not math.isfinite(result):
        raise PortalMemoryError(f"{name} muss eine endliche Zahl sein")
    return result


def _nonnegative_integer(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise PortalMemoryError(f"{name} muss eine nichtnegative Ganzzahl sein")
    return value


def _bounded_text(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > 256:
        raise PortalMemoryError(
            f"{name} muss 1 bis 256 Textzeichen enthalten")
    return value


@dataclass(frozen=True)
class Point2D:
    """One finite metric point in the observation's declared map frame."""

    x: float
    y: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "x", _finite_number(self.x, "point.x"))
        object.__setattr__(self, "y", _finite_number(self.y, "point.y"))


@dataclass(frozen=True)
class PortalMapContext:
    """Identity boundary for one mapping session and one map epoch."""

    session_id: str
    map_id: str
    frame_id: str

    def __post_init__(self) -> None:
        _validate_identifier(self.session_id, "session_id")
        _validate_identifier(self.map_id, "map_id")
        _validate_identifier(self.frame_id, "frame_id")


@dataclass(frozen=True)
class PortalObservation:
    """A detector-neutral metric observation of one directed passage axis.

    ``near_side`` is the side from which this observation approached the
    portal; ``far_side`` is the opposite side.  Observing the same opening in
    the other direction therefore swaps the two points.
    """

    observation_id: str
    context: PortalMapContext
    map_revision: int
    near_side: Point2D
    far_side: Point2D
    uncertainty_m: float = 0.0

    def __post_init__(self) -> None:
        _validate_identifier(self.observation_id, "observation_id")
        if not isinstance(self.context, PortalMapContext):
            raise PortalMemoryError("context muss PortalMapContext sein")
        _nonnegative_integer(self.map_revision, "map_revision")
        if not isinstance(self.near_side, Point2D):
            raise PortalMemoryError("near_side muss Point2D sein")
        if not isinstance(self.far_side, Point2D):
            raise PortalMemoryError("far_side muss Point2D sein")
        if _distance(self.near_side, self.far_side) <= 1e-9:
            raise PortalMemoryError("Portalachse braucht zwei getrennte Seiten")
        object.__setattr__(self, "uncertainty_m", _finite_nonnegative(
            self.uncertainty_m, "uncertainty_m"))


@dataclass(frozen=True)
class PortalMemoryPolicy:
    """Synthetic, bounded matching policy; not a hardware calibration."""

    max_endpoint_distance_m: float = 0.20
    max_midpoint_distance_m: float = 0.15
    max_axis_angle_rad: float = math.radians(25.0)
    ambiguity_margin_m: float = 0.03
    maximum_uncertainty_m: float = 0.10
    confirmation_revisions: int = 2
    max_portals: int = 256
    max_observations: int = 4096
    max_traversal_events: int = 4096
    max_reachability_updates: int = 4096

    def __post_init__(self) -> None:
        positive_names = (
            "max_endpoint_distance_m",
            "max_midpoint_distance_m",
            "max_axis_angle_rad",
            "ambiguity_margin_m",
            "maximum_uncertainty_m",
        )
        for name in positive_names:
            value = _finite_nonnegative(getattr(self, name), name)
            if value <= 0.0:
                raise PortalMemoryError(f"{name} muss groesser als null sein")
            object.__setattr__(self, name, value)
        if self.max_axis_angle_rad >= math.pi / 2.0:
            raise PortalMemoryError(
                "max_axis_angle_rad muss kleiner als pi/2 sein")
        for name in (
                "confirmation_revisions", "max_portals",
                "max_observations", "max_traversal_events",
                "max_reachability_updates"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise PortalMemoryError(f"{name} muss eine positive Ganzzahl sein")


class ObservationDisposition(str, Enum):
    CREATED = "created"
    MATCHED = "matched"
    AMBIGUOUS = "ambiguous"


class PortalSide(str, Enum):
    A = "A"
    B = "B"


class TraversalDirection(str, Enum):
    A_TO_B = "a_to_b"
    B_TO_A = "b_to_a"


class ReachabilityState(str, Enum):
    OPEN = "open"
    TEMPORARILY_BLOCKED = "temporarily_blocked"
    UNKNOWN = "unknown"
    EXCLUDED = "excluded"


@dataclass(frozen=True)
class ObservationResult:
    """Outcome of one observation without any movement implication."""

    disposition: ObservationDisposition
    portal_id: Optional[str]
    approach_side: Optional[PortalSide]
    candidate_ids: Tuple[str, ...] = ()
    evidence_added: bool = False
    duplicate: bool = False


@dataclass(frozen=True)
class PortalSnapshot:
    """Read-only public state of one candidate or confirmed portal."""

    portal_id: str
    side_a: Point2D
    side_b: Point2D
    first_revision: int
    last_revision: int
    observation_count: int
    evidence_count: int
    confirmed: bool
    confirmed_traversal_count: int


@dataclass(frozen=True)
class TraversalEvent:
    """Immutable result of an externally validated crossing check.

    This class does not inspect poses, footprints, encoders, or sensors.  The
    caller must set ``crossing_confirmed`` only after that separate validation.
    """

    event_id: str
    portal_id: str
    context: PortalMapContext
    map_revision: int
    event_time_ns: int
    direction: TraversalDirection
    crossing_confirmed: bool

    def __post_init__(self) -> None:
        _validate_identifier(self.event_id, "event_id")
        _validate_identifier(self.portal_id, "portal_id")
        if not isinstance(self.context, PortalMapContext):
            raise PortalMemoryError("context muss PortalMapContext sein")
        _nonnegative_integer(self.map_revision, "map_revision")
        _nonnegative_integer(self.event_time_ns, "event_time_ns")
        if not isinstance(self.direction, TraversalDirection):
            raise PortalMemoryError("direction muss TraversalDirection sein")
        if not isinstance(self.crossing_confirmed, bool):
            raise PortalMemoryError("crossing_confirmed muss bool sein")


@dataclass(frozen=True)
class TraversalResult:
    """Idempotent accounting result for one traversal event."""

    event_id: str
    portal_id: str
    direction: TraversalDirection
    crossing_confirmed: bool
    counted: bool
    duplicate: bool
    portal_traversal_count: int


@dataclass(frozen=True)
class ReachabilityUpdate:
    """One externally evaluated, side-specific reachability state."""

    update_id: str
    portal_id: str
    side: PortalSide
    context: PortalMapContext
    map_revision: int
    observed_at_ns: int
    state: ReachabilityState
    reason: str
    recheck_condition: str

    def __post_init__(self) -> None:
        _validate_identifier(self.update_id, "update_id")
        _validate_identifier(self.portal_id, "portal_id")
        if not isinstance(self.side, PortalSide):
            raise PortalMemoryError("side muss PortalSide sein")
        if not isinstance(self.context, PortalMapContext):
            raise PortalMemoryError("context muss PortalMapContext sein")
        _nonnegative_integer(self.map_revision, "map_revision")
        _nonnegative_integer(self.observed_at_ns, "observed_at_ns")
        if not isinstance(self.state, ReachabilityState):
            raise PortalMemoryError("state muss ReachabilityState sein")
        _bounded_text(self.reason, "reason")
        _bounded_text(self.recheck_condition, "recheck_condition")


@dataclass(frozen=True)
class ReachabilitySnapshot:
    """Current reachability of one portal side, separate from history."""

    portal_id: str
    side: PortalSide
    state: ReachabilityState
    reason: str
    recheck_condition: str
    map_revision: Optional[int]
    observed_at_ns: Optional[int]
    update_id: Optional[str]


@dataclass(frozen=True)
class ReachabilityResult:
    snapshot: ReachabilitySnapshot
    duplicate: bool


@dataclass
class _PortalState:
    portal_id: str
    side_a: Point2D
    side_b: Point2D
    anchor_uncertainty_m: float
    first_revision: int
    last_revision: int
    observation_count: int = 1
    evidence_revisions: set[int] = field(default_factory=set)
    confirmed_traversal_count: int = 0


@dataclass(frozen=True)
class _Candidate:
    portal_id: str
    approach_side: PortalSide
    score_m: float


def _distance(first: Point2D, second: Point2D) -> float:
    return math.hypot(first.x - second.x, first.y - second.y)


def _midpoint(first: Point2D, second: Point2D) -> Point2D:
    return Point2D(0.5 * (first.x + second.x), 0.5 * (first.y + second.y))


def _axis_angle(
        first_a: Point2D, first_b: Point2D,
        second_a: Point2D, second_b: Point2D) -> float:
    first_x = first_b.x - first_a.x
    first_y = first_b.y - first_a.y
    second_x = second_b.x - second_a.x
    second_y = second_b.y - second_a.y
    denominator = math.hypot(first_x, first_y) * math.hypot(
        second_x, second_y)
    if denominator <= 1e-12:
        return math.inf
    cosine = abs((first_x * second_x + first_y * second_y) / denominator)
    return math.acos(min(1.0, max(0.0, cosine)))


class PortalMemory:
    """Bounded identity memory for one immutable context boundary."""

    def __init__(
            self, context: PortalMapContext,
            policy: Optional[PortalMemoryPolicy] = None) -> None:
        if not isinstance(context, PortalMapContext):
            raise PortalMemoryError("context muss PortalMapContext sein")
        self._context = context
        self._policy = policy or PortalMemoryPolicy()
        if not isinstance(self._policy, PortalMemoryPolicy):
            raise PortalMemoryError("policy muss PortalMemoryPolicy sein")
        self._portals: Dict[str, _PortalState] = {}
        self._observations: Dict[
            str, Tuple[PortalObservation, ObservationResult]] = {}
        self._traversal_events: Dict[
            str, Tuple[TraversalEvent, TraversalResult]] = {}
        self._reachability_updates: Dict[str, ReachabilityUpdate] = {}
        self._current_reachability: Dict[
            Tuple[str, PortalSide], ReachabilityUpdate] = {}
        self._next_portal_number = 1
        self._latest_revision = -1

    @property
    def context(self) -> PortalMapContext:
        return self._context

    @property
    def latest_revision(self) -> Optional[int]:
        return None if self._latest_revision < 0 else self._latest_revision

    def snapshots(self) -> Tuple[PortalSnapshot, ...]:
        """Return deterministic, immutable portal state in ID order."""
        return tuple(
            self._snapshot(self._portals[portal_id])
            for portal_id in sorted(self._portals)
        )

    def snapshot(self, portal_id: str) -> PortalSnapshot:
        return self._snapshot(self._require_portal(portal_id))

    def confirmed_traversal_count(self, portal_id: Optional[str] = None) -> int:
        """Return confirmed crossings, independently from detected portals."""
        if portal_id is None:
            return sum(
                state.confirmed_traversal_count
                for state in self._portals.values())
        return self._require_portal(portal_id).confirmed_traversal_count

    def traversal_events(
            self, portal_id: Optional[str] = None,
            *, confirmed_only: bool = False) -> Tuple[TraversalEvent, ...]:
        """Return immutable traversal history in accepted event order."""
        if portal_id is not None:
            self._require_portal(portal_id)
        return tuple(
            event
            for event, _result in self._traversal_events.values()
            if (portal_id is None or event.portal_id == portal_id)
            and (not confirmed_only or event.crossing_confirmed)
        )

    def reachability_snapshot(
            self, portal_id: str, side: PortalSide) -> ReachabilitySnapshot:
        """Return current state; absence is explicit UNKNOWN, never OPEN."""
        self._require_portal(portal_id)
        if not isinstance(side, PortalSide):
            raise PortalMemoryError("side muss PortalSide sein")
        update = self._current_reachability.get((portal_id, side))
        if update is None:
            return ReachabilitySnapshot(
                portal_id=portal_id,
                side=side,
                state=ReachabilityState.UNKNOWN,
                reason="not_evaluated",
                recheck_condition="fresh_external_evaluation",
                map_revision=None,
                observed_at_ns=None,
                update_id=None,
            )
        return self._reachability_snapshot(update)

    def reachability_snapshots(self) -> Tuple[ReachabilitySnapshot, ...]:
        """Return both sides for every portal in deterministic order."""
        return tuple(
            self.reachability_snapshot(portal_id, side)
            for portal_id in sorted(self._portals)
            for side in (PortalSide.A, PortalSide.B)
        )

    def reachability_history(
            self, portal_id: Optional[str] = None,
            side: Optional[PortalSide] = None) -> Tuple[ReachabilityUpdate, ...]:
        """Return accepted state updates without collapsing their history."""
        if portal_id is not None:
            self._require_portal(portal_id)
        if side is not None and not isinstance(side, PortalSide):
            raise PortalMemoryError("side muss PortalSide sein")
        return tuple(
            update for update in self._reachability_updates.values()
            if (portal_id is None or update.portal_id == portal_id)
            and (side is None or update.side is side)
        )

    def observe(self, observation: PortalObservation) -> ObservationResult:
        """Associate one observation or report explicit ambiguity.

        Duplicate IDs are replayed without evidence changes.  Reusing an ID
        with different content, crossing the context boundary, going back to
        an older revision, or exceeding a hard capacity fails closed.
        """
        if not isinstance(observation, PortalObservation):
            raise PortalMemoryError("observation muss PortalObservation sein")
        if observation.context != self._context:
            raise ContextMismatchError(
                "Beobachtung passt nicht zu Sitzung, Karte und Frame")
        if observation.uncertainty_m > self._policy.maximum_uncertainty_m:
            raise PortalMemoryError(
                "Beobachtungsunsicherheit ueberschreitet das Softwarelimit")

        previous = self._observations.get(observation.observation_id)
        if previous is not None:
            previous_observation, previous_result = previous
            if previous_observation != observation:
                raise ObservationConflictError(
                    "observation_id wurde mit anderem Inhalt wiederverwendet")
            return replace(
                previous_result, duplicate=True, evidence_added=False)

        if observation.map_revision < self._latest_revision:
            raise StaleObservationError(
                "Neue Beobachtung stammt aus einer veralteten Kartenrevision")
        if len(self._observations) >= self._policy.max_observations:
            raise MemoryCapacityError("Beobachtungsspeicher ist voll")

        candidates = sorted(
            self._matching_candidates(observation),
            key=lambda candidate: (candidate.score_m, candidate.portal_id),
        )
        if (
                len(candidates) >= 2
                and candidates[1].score_m - candidates[0].score_m
                <= self._policy.ambiguity_margin_m):
            result = ObservationResult(
                disposition=ObservationDisposition.AMBIGUOUS,
                portal_id=None,
                approach_side=None,
                candidate_ids=tuple(candidate.portal_id for candidate in candidates),
            )
        elif candidates:
            candidate = candidates[0]
            state = self._portals[candidate.portal_id]
            evidence_added = observation.map_revision not in state.evidence_revisions
            state.evidence_revisions.add(observation.map_revision)
            state.last_revision = max(
                state.last_revision, observation.map_revision)
            state.observation_count += 1
            result = ObservationResult(
                disposition=ObservationDisposition.MATCHED,
                portal_id=state.portal_id,
                approach_side=candidate.approach_side,
                evidence_added=evidence_added,
            )
        else:
            if len(self._portals) >= self._policy.max_portals:
                raise MemoryCapacityError("Portalspeicher ist voll")
            state, approach_side = self._create_portal(observation)
            self._portals[state.portal_id] = state
            result = ObservationResult(
                disposition=ObservationDisposition.CREATED,
                portal_id=state.portal_id,
                approach_side=approach_side,
                evidence_added=True,
            )

        self._observations[observation.observation_id] = (observation, result)
        self._latest_revision = max(
            self._latest_revision, observation.map_revision)
        return result

    def record_traversal(self, event: TraversalEvent) -> TraversalResult:
        """Record one immutable external crossing verdict exactly once."""
        if not isinstance(event, TraversalEvent):
            raise PortalMemoryError("event muss TraversalEvent sein")
        self._require_context(event.context)

        previous = self._traversal_events.get(event.event_id)
        if previous is not None:
            previous_event, previous_result = previous
            if previous_event != event:
                raise TraversalConflictError(
                    "event_id wurde mit anderem Inhalt wiederverwendet")
            current_count = self._require_portal(
                previous_event.portal_id).confirmed_traversal_count
            return replace(
                previous_result,
                duplicate=True,
                counted=False,
                portal_traversal_count=current_count,
            )

        state = self._require_portal(event.portal_id)
        self._require_current_revision(event.map_revision)
        if len(self._traversal_events) >= self._policy.max_traversal_events:
            raise MemoryCapacityError("Durchfahrtsereignisspeicher ist voll")

        counted = event.crossing_confirmed
        if counted:
            state.confirmed_traversal_count += 1
        result = TraversalResult(
            event_id=event.event_id,
            portal_id=event.portal_id,
            direction=event.direction,
            crossing_confirmed=event.crossing_confirmed,
            counted=counted,
            duplicate=False,
            portal_traversal_count=state.confirmed_traversal_count,
        )
        self._traversal_events[event.event_id] = (event, result)
        self._latest_revision = max(self._latest_revision, event.map_revision)
        return result

    def update_reachability(
            self, update: ReachabilityUpdate) -> ReachabilityResult:
        """Apply a newer side-specific state without changing portal history."""
        if not isinstance(update, ReachabilityUpdate):
            raise PortalMemoryError("update muss ReachabilityUpdate sein")
        self._require_context(update.context)

        previous = self._reachability_updates.get(update.update_id)
        if previous is not None:
            if previous != update:
                raise ReachabilityConflictError(
                    "update_id wurde mit anderem Inhalt wiederverwendet")
            return ReachabilityResult(
                snapshot=self.reachability_snapshot(
                    previous.portal_id, previous.side),
                duplicate=True,
            )

        self._require_portal(update.portal_id)
        self._require_current_revision(update.map_revision)
        current = self._current_reachability.get(
            (update.portal_id, update.side))
        if current is not None and (
                update.map_revision, update.observed_at_ns
        ) <= (current.map_revision, current.observed_at_ns):
            raise StaleObservationError(
                "Erreichbarkeitsstand ist nicht neuer als der aktuelle Stand")
        if (
                len(self._reachability_updates)
                >= self._policy.max_reachability_updates):
            raise MemoryCapacityError("Erreichbarkeitsverlauf ist voll")

        self._reachability_updates[update.update_id] = update
        self._current_reachability[(update.portal_id, update.side)] = update
        self._latest_revision = max(self._latest_revision, update.map_revision)
        return ReachabilityResult(
            snapshot=self._reachability_snapshot(update),
            duplicate=False,
        )

    def _create_portal(
            self, observation: PortalObservation,
    ) -> Tuple[_PortalState, PortalSide]:
        portal_id = f"portal_{self._next_portal_number:06d}"
        self._next_portal_number += 1
        near_key = (observation.near_side.x, observation.near_side.y)
        far_key = (observation.far_side.x, observation.far_side.y)
        if near_key <= far_key:
            side_a = observation.near_side
            side_b = observation.far_side
            approach_side = PortalSide.A
        else:
            side_a = observation.far_side
            side_b = observation.near_side
            approach_side = PortalSide.B
        return _PortalState(
            portal_id=portal_id,
            side_a=side_a,
            side_b=side_b,
            anchor_uncertainty_m=observation.uncertainty_m,
            first_revision=observation.map_revision,
            last_revision=observation.map_revision,
            evidence_revisions={observation.map_revision},
        ), approach_side

    def _matching_candidates(
            self, observation: PortalObservation) -> Tuple[_Candidate, ...]:
        candidates = []
        observation_midpoint = _midpoint(
            observation.near_side, observation.far_side)
        for state in self._portals.values():
            if _axis_angle(
                    observation.near_side, observation.far_side,
                    state.side_a, state.side_b,
            ) > self._policy.max_axis_angle_rad:
                continue
            direct = (
                _distance(observation.near_side, state.side_a),
                _distance(observation.far_side, state.side_b),
            )
            reversed_assignment = (
                _distance(observation.near_side, state.side_b),
                _distance(observation.far_side, state.side_a),
            )
            if sum(direct) <= sum(reversed_assignment):
                endpoint_distances = direct
                approach_side = PortalSide.A
            else:
                endpoint_distances = reversed_assignment
                approach_side = PortalSide.B
            uncertainty = (
                observation.uncertainty_m + state.anchor_uncertainty_m)
            if max(endpoint_distances) > (
                    self._policy.max_endpoint_distance_m + uncertainty):
                continue
            midpoint_distance = _distance(
                observation_midpoint, _midpoint(state.side_a, state.side_b))
            if midpoint_distance > (
                    self._policy.max_midpoint_distance_m + uncertainty):
                continue
            candidates.append(_Candidate(
                portal_id=state.portal_id,
                approach_side=approach_side,
                score_m=max(endpoint_distances) + midpoint_distance,
            ))
        return tuple(candidates)

    def _snapshot(self, state: _PortalState) -> PortalSnapshot:
        evidence_count = len(state.evidence_revisions)
        return PortalSnapshot(
            portal_id=state.portal_id,
            side_a=state.side_a,
            side_b=state.side_b,
            first_revision=state.first_revision,
            last_revision=state.last_revision,
            observation_count=state.observation_count,
            evidence_count=evidence_count,
            confirmed=(
                evidence_count >= self._policy.confirmation_revisions),
            confirmed_traversal_count=state.confirmed_traversal_count,
        )

    def _require_context(self, context: PortalMapContext) -> None:
        if context != self._context:
            raise ContextMismatchError(
                "Ereignis passt nicht zu Sitzung, Karte und Frame")

    def _require_current_revision(self, map_revision: int) -> None:
        if map_revision < self._latest_revision:
            raise StaleObservationError(
                "Ereignis stammt aus einer veralteten Kartenrevision")

    def _require_portal(self, portal_id: str) -> _PortalState:
        _validate_identifier(portal_id, "portal_id")
        try:
            return self._portals[portal_id]
        except KeyError as exc:
            raise UnknownPortalError(
                f"Unbekannte Portal-ID: {portal_id}") from exc

    @staticmethod
    def _reachability_snapshot(
            update: ReachabilityUpdate) -> ReachabilitySnapshot:
        return ReachabilitySnapshot(
            portal_id=update.portal_id,
            side=update.side,
            state=update.state,
            reason=update.reason,
            recheck_condition=update.recheck_condition,
            map_revision=update.map_revision,
            observed_at_ns=update.observed_at_ns,
            update_id=update.update_id,
        )
