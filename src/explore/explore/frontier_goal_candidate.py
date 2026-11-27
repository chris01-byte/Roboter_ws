"""Pure metric goal candidate for one revision-bound frontier intention.

The adapter validates an exact raw-map snapshot and derives one reachable safe
cell plus a heading.  It does not create a ROS pose, send an action, call Nav2,
publish commands, or authorize motion.
"""

from dataclasses import dataclass
import math
from typing import Any, Iterable, Optional, Tuple

from .exploration_child_goal import ExplorationGoalIntent
from .exploration_scope import AuthorizedExplorationScope
from .exploration_policy import TaskAvailabilityState
from .frontier_task_evidence import (
    FrontierTaskEvidenceBatch,
    FrontierTaskEvidenceCapacityError,
    FrontierTaskEvidenceError,
    FrontierTaskEvidencePolicy,
    _geodesic_distances,
    _information_gain_square_m,
    _nearest_mask_cell,
    _traversable_mask,
    _validated_robot_xy,
    _validated_snapshot,
    _world_to_grid,
)
from .frontier_task_feed import FrontierTrackSnapshot
from .portal_source_adapter import PortalSourceCorrelation
from .region_graph import (
    RegionTaskKind,
    RegionTaskSnapshot,
    RegionTaskState,
)


class FrontierGoalCandidateError(ValueError):
    """The selected task cannot produce one trustworthy metric candidate."""


class FrontierGoalCandidateCapacityError(FrontierGoalCandidateError):
    """A hard input or map-search bound would be exceeded."""


@dataclass(frozen=True)
class FrontierGoalCandidate:
    """Numeric map-frame candidate, not a navigation command or permission."""

    intent_id: str
    task_id: str
    region_id: str
    frontier_id: str
    map_revision: int
    frame_id: str
    source_fingerprint: str
    source_stamp_ns: int
    target_x_m: float
    target_y_m: float
    target_yaw_rad: float
    target_row: int
    target_col: int
    frontier_x_m: float
    frontier_y_m: float
    route_length_m: float
    information_gain_square_m: float

    def __post_init__(self) -> None:
        numeric = (
            self.target_x_m,
            self.target_y_m,
            self.target_yaw_rad,
            self.frontier_x_m,
            self.frontier_y_m,
            self.route_length_m,
            self.information_gain_square_m,
        )
        if any(
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(float(value))
                for value in numeric):
            raise FrontierGoalCandidateError(
                "Zielkandidat enthaelt ungueltige metrische Werte")
        if self.route_length_m < 0.0 or self.information_gain_square_m <= 0.0:
            raise FrontierGoalCandidateError(
                "Zielkandidat braucht Route und positiven Informationsgewinn")
        if any(
                isinstance(value, bool) or not isinstance(value, int)
                or value < 0
                for value in (
                    self.map_revision, self.source_stamp_ns,
                    self.target_row, self.target_col)):
            raise FrontierGoalCandidateError(
                "Zielkandidat enthaelt ungueltige Ganzzahlen")


def _grid_to_world(
        row: int, col: int, origin: Tuple[float, ...], yaw: float,
        resolution_m: float) -> Tuple[float, float]:
    local_x = (col + 0.5) * resolution_m
    local_y = (row + 0.5) * resolution_m
    cosine = math.cos(yaw)
    sine = math.sin(yaw)
    return (
        origin[0] + cosine * local_x - sine * local_y,
        origin[1] + sine * local_x + cosine * local_y,
    )


def _matching_scalar_evidence(
        intent: ExplorationGoalIntent,
        evidence: FrontierTaskEvidenceBatch,
        maximum_tasks: int) -> Tuple[float, float]:
    if not isinstance(evidence, FrontierTaskEvidenceBatch):
        raise FrontierGoalCandidateError(
            "evidence muss FrontierTaskEvidenceBatch sein")
    if evidence.source_map_revision != intent.map_revision:
        raise FrontierGoalCandidateError(
            "Skalare Evidenz passt nicht zur Zielrevision")
    if (
            len(evidence.availability) > maximum_tasks
            or len(evidence.utilities) > maximum_tasks):
        raise FrontierGoalCandidateCapacityError(
            "Skalare Evidenz ueberschreitet die Zielgrenze")
    availability = tuple(
        item for item in evidence.availability
        if item.task_id == intent.task_id)
    utility = tuple(
        item for item in evidence.utilities
        if item.task_id == intent.task_id)
    if len(availability) != 1 or len(utility) != 1:
        raise FrontierGoalCandidateError(
            "Ausgewaehlte Aufgabe braucht eindeutige skalare Evidenz")
    selected_availability = availability[0]
    selected_utility = utility[0]
    if (
            selected_availability.context != intent.context
            or selected_availability.map_revision != intent.map_revision
            or selected_availability.state is not TaskAvailabilityState.AVAILABLE
            or selected_utility.context != intent.context
            or selected_utility.map_revision != intent.map_revision):
        raise FrontierGoalCandidateError(
            "Skalare Evidenz ist nicht aktuell und verfuegbar")
    return (
        selected_utility.geodesic_path_length_m,
        selected_utility.information_gain_square_m,
    )


def build_frontier_goal_candidate(
        intent: ExplorationGoalIntent,
        correlation: PortalSourceCorrelation, *,
        width: int, height: int, resolution: float, frame_id: str,
        origin: Tuple[float, float, float, float, float, float, float],
        cells: Iterable[Any], source_stamp_ns: int,
        robot_xy: Optional[Tuple[float, float]],
        task: RegionTaskSnapshot,
        tracks: Tuple[FrontierTrackSnapshot, ...],
        evidence: FrontierTaskEvidenceBatch,
        policy: Optional[FrontierTaskEvidencePolicy] = None,
        scope: Optional[AuthorizedExplorationScope] = None,
        scope_clearance_m: Optional[float] = None,
) -> FrontierGoalCandidate:
    """Derive one exact, reachable map-frame candidate or fail closed."""
    if not isinstance(intent, ExplorationGoalIntent):
        raise FrontierGoalCandidateError(
            "intent muss ExplorationGoalIntent sein")
    if not isinstance(correlation, PortalSourceCorrelation):
        raise FrontierGoalCandidateError(
            "correlation muss PortalSourceCorrelation sein")
    if (
            correlation.context != intent.context
            or correlation.map_revision != intent.map_revision):
        raise FrontierGoalCandidateError(
            "Rohkartenkorrelation passt nicht zur Zielabsicht")
    if not isinstance(task, RegionTaskSnapshot):
        raise FrontierGoalCandidateError(
            "task muss RegionTaskSnapshot sein")
    if (
            task.task_id != intent.task_id
            or task.region_id != intent.region_id
            or task.kind is not RegionTaskKind.FRONTIER
            or task.state is not RegionTaskState.OPEN
            or task.created_revision > intent.map_revision
            or task.last_revision > intent.map_revision):
        raise FrontierGoalCandidateError(
            "Aufgabe passt nicht als offene Frontier zur Zielabsicht")
    if not isinstance(tracks, tuple) or any(
            not isinstance(item, FrontierTrackSnapshot) for item in tracks):
        raise FrontierGoalCandidateError(
            "tracks muss ein Tupel aus FrontierTrackSnapshot sein")

    selected_policy = policy or FrontierTaskEvidencePolicy()
    if not isinstance(selected_policy, FrontierTaskEvidencePolicy):
        raise FrontierGoalCandidateError(
            "policy muss FrontierTaskEvidencePolicy sein")
    if len(tracks) > selected_policy.max_tracks:
        raise FrontierGoalCandidateCapacityError(
            "Frontierbestand ueberschreitet die Zielgrenze")
    track_ids = tuple(item.frontier_id for item in tracks)
    if len(set(track_ids)) != len(track_ids):
        raise FrontierGoalCandidateError(
            "Frontierbestand enthaelt Duplikate")
    matches = tuple(
        item for item in tracks if item.frontier_id == task.subject_id)
    if len(matches) != 1:
        raise FrontierGoalCandidateError(
            "Ausgewaehlte Aufgabe braucht genau einen Frontiertrack")
    track = matches[0]
    if track.last_revision != intent.map_revision:
        raise FrontierGoalCandidateError(
            "Frontiertrack stammt nicht aus der Zielrevision")

    route_length_m, information_gain_square_m = (
        _matching_scalar_evidence(
            intent, evidence, selected_policy.max_tasks))
    try:
        occupancy, resolution_m, clean_origin, map_yaw = _validated_snapshot(
            correlation,
            width=width,
            height=height,
            resolution=resolution,
            frame_id=frame_id,
            origin=origin,
            cells=cells,
            source_stamp_ns=source_stamp_ns,
            max_cells=selected_policy.max_cells,
        )
        normalized_robot_xy = _validated_robot_xy(robot_xy)
    except FrontierTaskEvidenceCapacityError as error:
        raise FrontierGoalCandidateCapacityError(str(error)) from error
    except FrontierTaskEvidenceError as error:
        raise FrontierGoalCandidateError(str(error)) from error
    if normalized_robot_xy is None:
        raise FrontierGoalCandidateError(
            "Zielbildung braucht eine aktuelle Roboterpose")

    try:
        traversable = _traversable_mask(
            occupancy,
            resolution_m,
            correlation,
            clean_origin,
            map_yaw,
            selected_policy,
            scope=scope,
            scope_clearance_m=scope_clearance_m,
        )
    except FrontierTaskEvidenceError as error:
        raise FrontierGoalCandidateError(str(error)) from error
    robot_row, robot_col = _world_to_grid(
        normalized_robot_xy, clean_origin, map_yaw, resolution_m)
    robot_seed = _nearest_mask_cell(
        traversable,
        robot_row,
        robot_col,
        int(math.ceil(
            selected_policy.robot_seed_search_m / resolution_m)),
    )
    if robot_seed is None:
        raise FrontierGoalCandidateError(
            "Roboterpose besitzt keine sichere Startzelle")
    distances = _geodesic_distances(traversable, robot_seed)
    frontier_row, frontier_col = _world_to_grid(
        (track.centroid.x, track.centroid.y),
        clean_origin,
        map_yaw,
        resolution_m,
    )
    target_cell = _nearest_mask_cell(
        traversable,
        frontier_row,
        frontier_col,
        int(math.ceil(
            selected_policy.task_cell_search_m / resolution_m)),
    )
    if target_cell is None or not math.isfinite(distances[target_cell]):
        raise FrontierGoalCandidateError(
            "Frontier besitzt keine erreichbare sichere Zielzelle")
    target_row, target_col = target_cell
    computed_route_length_m = (
        float(distances[target_row, target_col]) * resolution_m)
    if not math.isclose(
            computed_route_length_m, route_length_m,
            rel_tol=1e-9, abs_tol=1e-9):
        raise FrontierGoalCandidateError(
            "Zielzelle widerspricht der skalaren Wegevidenz")
    computed_information_gain_square_m = _information_gain_square_m(
        occupancy,
        frontier_row,
        frontier_col,
        max(1, int(math.ceil(
            selected_policy.information_radius_m / resolution_m))),
        resolution_m,
    )
    if not math.isclose(
            computed_information_gain_square_m,
            information_gain_square_m,
            rel_tol=1e-9, abs_tol=1e-9):
        raise FrontierGoalCandidateError(
            "Frontier widerspricht der skalaren Informationsevidenz")

    target_x_m, target_y_m = _grid_to_world(
        target_row, target_col, clean_origin, map_yaw, resolution_m)
    delta_x = track.centroid.x - target_x_m
    delta_y = track.centroid.y - target_y_m
    if math.hypot(delta_x, delta_y) <= 1e-9:
        delta_x = target_x_m - normalized_robot_xy[0]
        delta_y = target_y_m - normalized_robot_xy[1]
    target_yaw_rad = (
        map_yaw if math.hypot(delta_x, delta_y) <= 1e-9
        else math.atan2(delta_y, delta_x))
    return FrontierGoalCandidate(
        intent_id=intent.intent_id,
        task_id=intent.task_id,
        region_id=intent.region_id,
        frontier_id=track.frontier_id,
        map_revision=intent.map_revision,
        frame_id=frame_id,
        source_fingerprint=correlation.fingerprint,
        source_stamp_ns=source_stamp_ns,
        target_x_m=target_x_m,
        target_y_m=target_y_m,
        target_yaw_rad=target_yaw_rad,
        target_row=target_row,
        target_col=target_col,
        frontier_x_m=track.centroid.x,
        frontier_y_m=track.centroid.y,
        route_length_m=computed_route_length_m,
        information_gain_square_m=computed_information_gain_square_m,
    )


def revalidate_active_frontier_goal_candidate(
        intent: ExplorationGoalIntent,
        candidate: FrontierGoalCandidate,
        correlation: PortalSourceCorrelation, *,
        width: int, height: int, resolution: float, frame_id: str,
        origin: Tuple[float, float, float, float, float, float, float],
        cells: Iterable[Any], source_stamp_ns: int,
        robot_xy: Optional[Tuple[float, float]],
        policy: Optional[FrontierTaskEvidencePolicy] = None,
        scope: Optional[AuthorizedExplorationScope] = None,
        scope_clearance_m: Optional[float] = None,
) -> float:
    """Revalidate one already dispatched fixed target on a newer raw map.

    Frontier centroids and their preferred safe cells legitimately move while
    SLAM grows.  That must not replace an active Nav2 goal merely because a
    newer candidate would be a few cells away.  Continuation is nevertheless
    fail-closed: the *original metric target* must still be inside the
    authorized scope, obstacle-clear, and geodesically reachable from the
    current robot pose on the exact correlated raw-map revision.

    The returned value is the freshly measured route length in metres.  This
    helper does not dispatch, adjust, or authorize a different goal.
    """
    if not isinstance(intent, ExplorationGoalIntent):
        raise FrontierGoalCandidateError(
            "intent muss ExplorationGoalIntent sein")
    if not isinstance(candidate, FrontierGoalCandidate):
        raise FrontierGoalCandidateError(
            "candidate muss FrontierGoalCandidate sein")
    if (
            candidate.intent_id != intent.intent_id
            or candidate.task_id != intent.task_id
            or candidate.region_id != intent.region_id
            or candidate.map_revision != intent.map_revision
            or candidate.frame_id != intent.context.frame_id):
        raise FrontierGoalCandidateError(
            "Aktiver Zielkandidat passt nicht zur Zielabsicht")
    if (
            not isinstance(correlation, PortalSourceCorrelation)
            or correlation.context != intent.context
            or correlation.map_revision < intent.map_revision):
        raise FrontierGoalCandidateError(
            "Aktive Zielpruefung braucht denselben neueren Kartenkontext")

    selected_policy = policy or FrontierTaskEvidencePolicy()
    if not isinstance(selected_policy, FrontierTaskEvidencePolicy):
        raise FrontierGoalCandidateError(
            "policy muss FrontierTaskEvidencePolicy sein")
    try:
        occupancy, resolution_m, clean_origin, map_yaw = _validated_snapshot(
            correlation,
            width=width,
            height=height,
            resolution=resolution,
            frame_id=frame_id,
            origin=origin,
            cells=cells,
            source_stamp_ns=source_stamp_ns,
            max_cells=selected_policy.max_cells,
        )
        normalized_robot_xy = _validated_robot_xy(robot_xy)
        traversable = _traversable_mask(
            occupancy,
            resolution_m,
            correlation,
            clean_origin,
            map_yaw,
            selected_policy,
            scope=scope,
            scope_clearance_m=scope_clearance_m,
        )
    except FrontierTaskEvidenceCapacityError as error:
        raise FrontierGoalCandidateCapacityError(str(error)) from error
    except FrontierTaskEvidenceError as error:
        raise FrontierGoalCandidateError(str(error)) from error
    if normalized_robot_xy is None:
        raise FrontierGoalCandidateError(
            "Aktive Zielpruefung braucht eine aktuelle Roboterpose")

    robot_row, robot_col = _world_to_grid(
        normalized_robot_xy, clean_origin, map_yaw, resolution_m)
    robot_seed = _nearest_mask_cell(
        traversable,
        robot_row,
        robot_col,
        int(math.ceil(
            selected_policy.robot_seed_search_m / resolution_m)),
    )
    if robot_seed is None:
        raise FrontierGoalCandidateError(
            "Roboterpose besitzt keine sichere Startzelle")

    target_row, target_col = _world_to_grid(
        (candidate.target_x_m, candidate.target_y_m),
        clean_origin,
        map_yaw,
        resolution_m,
    )
    if (
            target_row < 0
            or target_col < 0
            or target_row >= traversable.shape[0]
            or target_col >= traversable.shape[1]
            or not bool(traversable[target_row, target_col])):
        raise FrontierGoalCandidateError(
            "Aktives Ziel ist nicht mehr als sichere Zielzelle belegt")
    distances = _geodesic_distances(traversable, robot_seed)
    distance_cells = float(distances[target_row, target_col])
    if not math.isfinite(distance_cells):
        raise FrontierGoalCandidateError(
            "Aktives Ziel ist auf der aktuellen Rohkarte nicht erreichbar")
    return distance_cells * resolution_m
