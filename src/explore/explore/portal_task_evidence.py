"""Pure route and goal evidence for open portal and transit tasks."""

from dataclasses import dataclass, replace
import heapq
import math
from typing import Any, Dict, Iterable, Optional, Tuple

import numpy as np
from scipy.ndimage import distance_transform_edt

from .exploration_child_goal import ExplorationGoalIntent
from .exploration_policy import (
    TaskAvailability,
    TaskAvailabilityState,
    TaskUtilityEvidence,
)
from .exploration_scope import (
    AuthorizedExplorationScope,
    ExplorationScopeError,
    rasterize_scope,
)
from .frontier_task_evidence import (
    FrontierTaskEvidencePolicy,
    FrontierTaskEvidenceCapacityError,
    FrontierTaskEvidenceError,
    _nearest_mask_cell,
    _validated_robot_xy,
    _validated_snapshot,
    _world_to_grid,
    build_frontier_task_evidence,
)
from .frontier_task_feed import FrontierTrackSnapshot
from .frontier_goal_candidate import _grid_to_world
from .portal_memory import (
    PortalConfirmationState,
    PortalMapContext,
    PortalSnapshot,
    TraversalDirection,
)
from .portal_source_adapter import PortalSourceCorrelation
from .region_graph import (
    PortalConnectionSnapshot,
    RegionTaskKind,
    RegionTaskSnapshot,
    RegionTaskState,
)


class PortalTaskEvidenceError(ValueError):
    """Portal task, map, graph and authorized scope are inconsistent."""


class PortalTaskEvidenceCapacityError(PortalTaskEvidenceError):
    """A hard map, task, target or route-search bound was exceeded."""


def _identifier(value: object, name: str) -> str:
    if (
            not isinstance(value, str)
            or not value
            or len(value) > 128
            or not value.isascii()
            or not value[0].isalnum()
            or any(
                not (character.isalnum() or character in "_.:-")
                for character in value)):
        raise PortalTaskEvidenceError(f"{name} ist ungueltig")
    return value


def _validate_goal_fields(value) -> None:
    for name in (
            "task_id", "region_id", "portal_id", "frame_id", "scope_id"):
        _identifier(getattr(value, name), name)
    if not isinstance(value.direction, TraversalDirection):
        raise PortalTaskEvidenceError(
            "direction muss TraversalDirection sein")
    if not isinstance(value.context, PortalMapContext):
        raise PortalTaskEvidenceError(
            "context muss PortalMapContext sein")
    if (
            isinstance(value.map_revision, bool)
            or not isinstance(value.map_revision, int)
            or value.map_revision < 0
            or isinstance(value.source_stamp_ns, bool)
            or not isinstance(value.source_stamp_ns, int)
            or value.source_stamp_ns < 0
            or isinstance(value.target_row, bool)
            or not isinstance(value.target_row, int)
            or value.target_row < 0
            or isinstance(value.target_col, bool)
            or not isinstance(value.target_col, int)
            or value.target_col < 0):
        raise PortalTaskEvidenceError(
            "Portalziel enthaelt ungueltige Ganzzahlen")
    if (
            not isinstance(value.source_fingerprint, str)
            or len(value.source_fingerprint) != 64
            or any(character not in "0123456789abcdef"
                   for character in value.source_fingerprint)):
        raise PortalTaskEvidenceError(
            "source_fingerprint ist ungueltig")
    if (
            not isinstance(value.scope_fingerprint, str)
            or len(value.scope_fingerprint) != 64
            or any(character not in "0123456789abcdef"
                   for character in value.scope_fingerprint)):
        raise PortalTaskEvidenceError(
            "scope_fingerprint ist ungueltig")
    for name in (
            "target_x_m", "target_y_m", "target_yaw_rad",
            "route_length_m"):
        item = getattr(value, name)
        if (
                isinstance(item, bool)
                or not isinstance(item, (int, float))
                or not math.isfinite(float(item))):
            raise PortalTaskEvidenceError(
                f"{name} muss endlich sein")
    if value.route_length_m <= 0.0:
        raise PortalTaskEvidenceError(
            "route_length_m muss positiv sein")
    path = value.path_cells
    if (
            not isinstance(path, tuple)
            or not path
            or any(
                not isinstance(cell, tuple) or len(cell) != 2
                or any(
                    isinstance(coordinate, bool)
                    or not isinstance(coordinate, int)
                    or coordinate < 0
                    for coordinate in cell)
                for cell in path)):
        raise PortalTaskEvidenceError(
            "path_cells muss ein nichtleeres Rasterpfad-Tupel sein")
    if path[-1] != (value.target_row, value.target_col):
        raise PortalTaskEvidenceError(
            "Pfadende widerspricht der Portalzielzelle")
    if any(
            max(abs(second[0] - first[0]), abs(second[1] - first[1])) != 1
            for first, second in zip(path, path[1:])):
        raise PortalTaskEvidenceError(
            "Portalpfad besitzt nicht benachbarte Zellen")


@dataclass(frozen=True)
class PortalTaskEvidencePolicy:
    """Explicit software limits; metric values are not hardware acceptance."""

    clearance_m: float
    scope_clearance_m: float
    robot_seed_search_m: float
    chassis_rear_overhang_m: float
    exit_clearance_m: float
    target_search_m: float
    maximum_target_lateral_m: float
    portal_path_radius_m: float
    max_cells: int = 512 * 512
    max_tasks: int = 4096
    max_portals: int = 256
    max_connections: int = 512
    max_target_candidates: int = 256
    max_expanded_cells: int = 512 * 512
    max_path_cells: int = 8192

    def __post_init__(self) -> None:
        for name in (
                "clearance_m", "scope_clearance_m", "robot_seed_search_m",
                "chassis_rear_overhang_m", "exit_clearance_m",
                "target_search_m", "maximum_target_lateral_m",
                "portal_path_radius_m"):
            value = getattr(self, name)
            if (
                    isinstance(value, bool)
                    or not isinstance(value, (int, float))
                    or not math.isfinite(float(value))
                    or float(value) <= 0.0):
                raise PortalTaskEvidenceError(
                    f"{name} muss endlich und positiv sein")
        for name in (
                "max_cells", "max_tasks", "max_portals", "max_connections",
                "max_target_candidates", "max_expanded_cells",
                "max_path_cells"):
            value = getattr(self, name)
            if (
                    isinstance(value, bool)
                    or not isinstance(value, int)
                    or value <= 0):
                raise PortalTaskEvidenceError(
                    f"{name} muss eine positive Ganzzahl sein")


@dataclass(frozen=True)
class PortalGoalProposal:
    task_id: str
    region_id: str
    portal_id: str
    direction: TraversalDirection
    context: PortalMapContext
    map_revision: int
    frame_id: str
    source_fingerprint: str
    source_stamp_ns: int
    scope_id: str
    scope_fingerprint: str
    target_x_m: float
    target_y_m: float
    target_yaw_rad: float
    target_row: int
    target_col: int
    route_length_m: float
    path_cells: Tuple[Tuple[int, int], ...]

    def __post_init__(self) -> None:
        _validate_goal_fields(self)


@dataclass(frozen=True)
class PortalGoalCandidate:
    intent_id: str
    task_id: str
    region_id: str
    portal_id: str
    direction: TraversalDirection
    context: PortalMapContext
    map_revision: int
    frame_id: str
    source_fingerprint: str
    source_stamp_ns: int
    scope_id: str
    scope_fingerprint: str
    target_x_m: float
    target_y_m: float
    target_yaw_rad: float
    target_row: int
    target_col: int
    route_length_m: float
    path_cells: Tuple[Tuple[int, int], ...]

    def __post_init__(self) -> None:
        _identifier(self.intent_id, "intent_id")
        _validate_goal_fields(self)


@dataclass(frozen=True)
class PortalTaskEvidenceBatch:
    source_map_revision: int
    scope_id: str
    availability: Tuple[TaskAvailability, ...]
    utilities: Tuple[TaskUtilityEvidence, ...]
    proposals: Tuple[PortalGoalProposal, ...]
    robot_seed_available: bool


@dataclass(frozen=True)
class TransitPurposeAssessment:
    """Why one otherwise safe transit route is, or is not, useful now.

    The transit route itself remains a normal ``PortalGoalProposal``.  This
    object binds it to one distinct task that can be started after entering the
    route's target region.  It is evidence only: after the crossing the normal
    task adapters still re-evaluate the actual next child goal.
    """

    transit_task_id: str
    target_region_id: str
    portal_id: str
    state: TaskAvailabilityState
    reason: str
    recheck_condition: str
    purpose_task_id: Optional[str] = None
    purpose_kind: Optional[RegionTaskKind] = None
    next_portal_id: Optional[str] = None

    def __post_init__(self) -> None:
        _identifier(self.transit_task_id, "transit_task_id")
        _identifier(self.target_region_id, "target_region_id")
        _identifier(self.portal_id, "portal_id")
        if not isinstance(self.state, TaskAvailabilityState):
            raise PortalTaskEvidenceError("Transitbedarf besitzt keinen Zustand")
        if not isinstance(self.reason, str) or not self.reason:
            raise PortalTaskEvidenceError("Transitbedarf besitzt keinen Grund")
        if (
                not isinstance(self.recheck_condition, str)
                or not self.recheck_condition):
            raise PortalTaskEvidenceError(
                "Transitbedarf besitzt keine Neubewertung")
        if self.purpose_task_id is None:
            if self.purpose_kind is not None or self.next_portal_id is not None:
                raise PortalTaskEvidenceError(
                    "Transitbedarf ohne Aufgabe enthaelt Zweckfelder")
        else:
            _identifier(self.purpose_task_id, "purpose_task_id")
            if not isinstance(self.purpose_kind, RegionTaskKind):
                raise PortalTaskEvidenceError(
                    "Transitbedarf besitzt keine Aufgabenart")
            if self.next_portal_id is not None:
                _identifier(self.next_portal_id, "next_portal_id")


@dataclass(frozen=True)
class TransitPurposeEvidenceBatch:
    """Availability replacements for all open transit tasks in one revision."""

    source_map_revision: int
    availability: Tuple[TaskAvailability, ...]
    assessments: Tuple[TransitPurposeAssessment, ...]


def _astar_path(
        traversable: np.ndarray, start: Tuple[int, int],
        goal: Tuple[int, int], *, max_expanded_cells: int,
        max_path_cells: int) -> Optional[Tuple[Tuple[int, int], ...]]:
    height, width = traversable.shape
    queue = [(0.0, 0.0, start)]
    best = {start: 0.0}
    previous: Dict[Tuple[int, int], Tuple[int, int]] = {}
    expanded = 0
    while queue:
        _priority, cost, current = heapq.heappop(queue)
        if cost != best.get(current):
            continue
        expanded += 1
        if expanded > max_expanded_cells:
            raise PortalTaskEvidenceCapacityError(
                "Portal-Routensuche ueberschreitet die Zellgrenze")
        if current == goal:
            path = [current]
            while current != start:
                current = previous[current]
                path.append(current)
                if len(path) > max_path_cells:
                    raise PortalTaskEvidenceCapacityError(
                        "Portalroute ueberschreitet die Pfadgrenze")
            return tuple(reversed(path))
        row, col = current
        for row_delta, col_delta in (
                (-1, -1), (-1, 0), (-1, 1), (0, -1),
                (0, 1), (1, -1), (1, 0), (1, 1)):
            next_row = row + row_delta
            next_col = col + col_delta
            if not (
                    0 <= next_row < height and 0 <= next_col < width
                    and traversable[next_row, next_col]):
                continue
            diagonal = row_delta != 0 and col_delta != 0
            if diagonal and not (
                    traversable[row, next_col]
                    and traversable[next_row, col]):
                continue
            step = math.sqrt(2.0) if diagonal else 1.0
            next_cost = cost + step
            neighbor = (next_row, next_col)
            if next_cost >= best.get(neighbor, math.inf):
                continue
            best[neighbor] = next_cost
            previous[neighbor] = current
            heuristic = math.hypot(
                goal[0] - next_row, goal[1] - next_col)
            heapq.heappush(
                queue, (next_cost + heuristic, next_cost, neighbor))
    return None


def _path_uses_portal(
        path: Tuple[Tuple[int, int], ...], *,
        side_a, side_b, origin, map_yaw, resolution_m,
        radius_m: float) -> bool:
    axis_x = side_b.x - side_a.x
    axis_y = side_b.y - side_a.y
    length = math.hypot(axis_x, axis_y)
    if length <= 1e-9:
        return False
    unit_x = axis_x / length
    unit_y = axis_y / length
    samples = []
    for row, col in path:
        x, y = _grid_to_world(row, col, origin, map_yaw, resolution_m)
        relative_x = x - side_a.x
        relative_y = y - side_a.y
        projection = relative_x * unit_x + relative_y * unit_y
        lateral = abs(-relative_x * unit_y + relative_y * unit_x)
        samples.append((projection, lateral))
    midpoint = 0.5 * length
    for first, second in zip(samples, samples[1:]):
        if (
                min(first[0], second[0]) - 1e-9 <= midpoint
                <= max(first[0], second[0]) + 1e-9
                and max(first[1], second[1]) <= radius_m):
            return True
    return False


def _portal_direction(
        task: RegionTaskSnapshot, connection: PortalConnectionSnapshot,
        current_region_id: str) -> Optional[TraversalDirection]:
    if (
            connection.side_a_region_id == current_region_id
            and connection.side_b_region_id == task.region_id):
        return TraversalDirection.A_TO_B
    if (
            connection.side_b_region_id == current_region_id
            and connection.side_a_region_id == task.region_id):
        return TraversalDirection.B_TO_A
    return None


def build_portal_task_evidence(
        correlation: PortalSourceCorrelation, *,
        width: int, height: int, resolution: float, frame_id: str,
        origin: Tuple[float, float, float, float, float, float, float],
        cells: Iterable[Any], source_stamp_ns: int,
        robot_xy: Optional[Tuple[float, float]],
        current_region_id: str,
        tasks: Tuple[RegionTaskSnapshot, ...],
        portals: Tuple[PortalSnapshot, ...],
        connections: Tuple[PortalConnectionSnapshot, ...],
        scope: AuthorizedExplorationScope,
        policy: PortalTaskEvidencePolicy,
) -> PortalTaskEvidenceBatch:
    """Build complete availability, utility and scoped routes for portals."""
    if not isinstance(policy, PortalTaskEvidencePolicy):
        raise PortalTaskEvidenceError(
            "policy muss PortalTaskEvidencePolicy sein")
    if not isinstance(current_region_id, str) or not current_region_id:
        raise PortalTaskEvidenceError(
            "current_region_id ist ungueltig")
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
            max_cells=policy.max_cells,
        )
        normalized_robot_xy = _validated_robot_xy(robot_xy)
        scope_mask = rasterize_scope(
            scope,
            context=correlation.context,
            width=width,
            height=height,
            resolution_m=resolution_m,
            origin_x_m=clean_origin[0],
            origin_y_m=clean_origin[1],
            origin_yaw_rad=map_yaw,
            maximum_cells=policy.max_cells,
        )
    except FrontierTaskEvidenceCapacityError as error:
        raise PortalTaskEvidenceCapacityError(str(error)) from error
    except (FrontierTaskEvidenceError, ExplorationScopeError) as error:
        raise PortalTaskEvidenceError(str(error)) from error
    for values, expected, maximum, name in (
            (tasks, RegionTaskSnapshot, policy.max_tasks, "tasks"),
            (portals, PortalSnapshot, policy.max_portals, "portals"),
            (connections, PortalConnectionSnapshot,
             policy.max_connections, "connections")):
        if (
                not isinstance(values, tuple)
                or len(values) > maximum
                or any(not isinstance(value, expected) for value in values)):
            raise PortalTaskEvidenceCapacityError(
                f"{name} ist ungueltig oder ueberschreitet die Grenze")
    if any(
            task.kind not in (
                RegionTaskKind.PORTAL, RegionTaskKind.TRANSIT)
            or task.state is not RegionTaskState.OPEN
            for task in tasks):
        raise PortalTaskEvidenceError(
            "Portaladapter akzeptiert nur offene Portal- oder Transitaufgaben")
    if len({task.task_id for task in tasks}) != len(tasks):
        raise PortalTaskEvidenceError(
            "Portal- oder Transitaufgaben enthalten doppelte IDs")
    if len({item.portal_id for item in portals}) != len(portals):
        raise PortalTaskEvidenceError("Portalbestand enthaelt doppelte IDs")
    if len({item.portal_id for item in connections}) != len(connections):
        raise PortalTaskEvidenceError(
            "Verbindungsbestand enthaelt doppelte Portal-IDs")
    if any(
            task.created_revision > correlation.map_revision
            or task.last_revision > correlation.map_revision
            for task in tasks):
        raise PortalTaskEvidenceError(
            "Portalaufgabe liegt vor der aktuellen Kartenrevision")
    if any(
            item.last_revision > correlation.map_revision
            for item in (*portals, *connections)):
        raise PortalTaskEvidenceError(
            "Portal- oder Verbindungsstand liegt vor der Karte")

    safe_free = occupancy == 0
    clearance_cells = policy.clearance_m / resolution_m
    padded = np.pad(safe_free, 1, mode="constant", constant_values=False)
    clearance = distance_transform_edt(padded)[1:-1, 1:-1]
    padded_scope = np.pad(
        scope_mask, 1, mode="constant", constant_values=False)
    scope_clearance = distance_transform_edt(padded_scope)[1:-1, 1:-1]
    traversable = (
        safe_free
        & (clearance >= clearance_cells)
        & scope_mask
        & (scope_clearance
           >= policy.scope_clearance_m / resolution_m)
    )
    robot_seed = None
    if normalized_robot_xy is not None:
        robot_row, robot_col = _world_to_grid(
            normalized_robot_xy, clean_origin, map_yaw, resolution_m)
        robot_seed = _nearest_mask_cell(
            traversable,
            robot_row,
            robot_col,
            int(math.ceil(policy.robot_seed_search_m / resolution_m)),
        )

    portals_by_id = {item.portal_id: item for item in portals}
    connections_by_id = {item.portal_id: item for item in connections}
    availability = []
    utilities = []
    proposals = []
    for task in sorted(tasks, key=lambda item: item.task_id):
        state = TaskAvailabilityState.UNKNOWN
        reason = "portal_graph_evidence_missing"
        recheck = "observe_confirmed_portal_and_connection"
        proposal = None
        portal = portals_by_id.get(task.subject_id)
        connection = connections_by_id.get(task.subject_id)
        if task.last_revision >= correlation.map_revision:
            reason = "portal_task_requires_newer_map_revision"
            recheck = "reassess_after_new_map_revision"
        elif portal is None or connection is None:
            pass
        elif (
                not portal.confirmed
                or portal.confirmation_state
                is not PortalConfirmationState.CONFIRMED):
            reason = "portal_not_confirmed"
            recheck = "observe_qualified_portal_revision"
        elif connection.internal:
            state = TaskAvailabilityState.FILTERED
            reason = "portal_connection_is_internal"
            recheck = "reconcile_region_tasks"
        elif normalized_robot_xy is None:
            reason = "missing_robot_pose"
            recheck = "supply_current_map_frame_robot_pose"
        elif robot_seed is None:
            state = TaskAvailabilityState.TEMPORARILY_BLOCKED
            reason = "robot_outside_scoped_safe_free_space"
            recheck = "reassess_after_pose_map_or_scope_update"
        else:
            direction = _portal_direction(
                task, connection, current_region_id)
            if direction is None:
                reason = "portal_task_not_adjacent_to_current_region"
                recheck = "enter_adjacent_region_or_reconcile_graph"
            else:
                side_a = portal.side_a
                side_b = portal.side_b
                axis_x = side_b.x - side_a.x
                axis_y = side_b.y - side_a.y
                span = math.hypot(axis_x, axis_y)
                if span <= 1e-9:
                    reason = "portal_axis_degenerate"
                    recheck = "observe_qualified_portal_geometry"
                else:
                    axis_x /= span
                    axis_y /= span
                    end = side_b
                    if direction is TraversalDirection.B_TO_A:
                        axis_x = -axis_x
                        axis_y = -axis_y
                        end = side_a
                    required_exit = (
                        policy.chassis_rear_overhang_m
                        + policy.exit_clearance_m)
                    desired_xy = (
                        end.x + required_exit * axis_x,
                        end.y + required_exit * axis_y,
                    )
                    desired_row, desired_col = _world_to_grid(
                        desired_xy, clean_origin, map_yaw, resolution_m)
                    radius_cells = int(math.ceil(
                        policy.target_search_m / resolution_m))
                    target_options = []
                    for row in range(
                            max(0, desired_row - radius_cells),
                            min(height, desired_row + radius_cells + 1)):
                        for col in range(
                                max(0, desired_col - radius_cells),
                                min(width, desired_col + radius_cells + 1)):
                            if not traversable[row, col]:
                                continue
                            x, y = _grid_to_world(
                                row, col, clean_origin, map_yaw,
                                resolution_m)
                            end_x = x - end.x
                            end_y = y - end.y
                            forward = end_x * axis_x + end_y * axis_y
                            lateral = abs(-end_x * axis_y + end_y * axis_x)
                            if (
                                    forward + 1e-9 < required_exit
                                    or lateral
                                    > policy.maximum_target_lateral_m):
                                continue
                            distance = math.hypot(
                                x - desired_xy[0], y - desired_xy[1])
                            if distance <= policy.target_search_m + 1e-9:
                                target_options.append(
                                    (distance, row, col, x, y))
                    target_options.sort()
                    if len(target_options) > policy.max_target_candidates:
                        target_options = target_options[
                            :policy.max_target_candidates]
                    selected = None
                    route_m = None
                    for _distance, row, col, x, y in target_options:
                        path = _astar_path(
                            traversable,
                            robot_seed,
                            (row, col),
                            max_expanded_cells=policy.max_expanded_cells,
                            max_path_cells=policy.max_path_cells,
                        )
                        if path is None or not _path_uses_portal(
                                path,
                                side_a=side_a,
                                side_b=side_b,
                                origin=clean_origin,
                                map_yaw=map_yaw,
                                resolution_m=resolution_m,
                                radius_m=policy.portal_path_radius_m):
                            continue
                        route_m = sum(
                            resolution_m * math.hypot(
                                second[0] - first[0],
                                second[1] - first[1])
                            for first, second in zip(path, path[1:]))
                        selected = (row, col, x, y, path)
                        break
                    if selected is None:
                        state = TaskAvailabilityState.TEMPORARILY_BLOCKED
                        reason = "no_scoped_route_through_selected_portal"
                        recheck = "reassess_after_map_or_scope_revision"
                    else:
                        row, col, x, y, path = selected
                        state = TaskAvailabilityState.AVAILABLE
                        reason = "scoped_raw_map_portal_route_available"
                        recheck = "revalidate_before_navigation"
                        proposal = PortalGoalProposal(
                            task_id=task.task_id,
                            region_id=task.region_id,
                            portal_id=portal.portal_id,
                            direction=direction,
                            context=correlation.context,
                            map_revision=correlation.map_revision,
                            frame_id=correlation.context.frame_id,
                            source_fingerprint=correlation.fingerprint,
                            source_stamp_ns=correlation.source_stamp_ns,
                            scope_id=scope.scope_id,
                            scope_fingerprint=scope.fingerprint,
                            target_x_m=x,
                            target_y_m=y,
                            target_yaw_rad=math.atan2(axis_y, axis_x),
                            target_row=row,
                            target_col=col,
                            route_length_m=float(route_m),
                            path_cells=path,
                        )
                        utilities.append(TaskUtilityEvidence(
                            task_id=task.task_id,
                            context=correlation.context,
                            map_revision=correlation.map_revision,
                            geodesic_path_length_m=float(route_m),
                            information_gain_square_m=0.0,
                        ))
        availability.append(TaskAvailability(
            task_id=task.task_id,
            context=correlation.context,
            map_revision=correlation.map_revision,
            state=state,
            reason=reason,
            recheck_condition=recheck,
        ))
        if proposal is not None:
            proposals.append(proposal)
    return PortalTaskEvidenceBatch(
        source_map_revision=correlation.map_revision,
        scope_id=scope.scope_id,
        availability=tuple(availability),
        utilities=tuple(utilities),
        proposals=tuple(proposals),
        robot_seed_available=robot_seed is not None,
    )


def _portal_entry_region(
        task: RegionTaskSnapshot,
        connection: Optional[PortalConnectionSnapshot]) -> Optional[str]:
    """Return the side from which ``task`` can start its portal crossing."""
    if task.kind is not RegionTaskKind.PORTAL or connection is None:
        return None
    if connection.side_a_region_id == task.region_id:
        return connection.side_b_region_id
    if connection.side_b_region_id == task.region_id:
        return connection.side_a_region_id
    return None


def build_transit_purpose_evidence(
        correlation: PortalSourceCorrelation, *,
        width: int, height: int, resolution: float, frame_id: str,
        origin: Tuple[float, float, float, float, float, float, float],
        cells: Iterable[Any], source_stamp_ns: int,
        tasks: Tuple[RegionTaskSnapshot, ...],
        portals: Tuple[PortalSnapshot, ...],
        connections: Tuple[PortalConnectionSnapshot, ...],
        tracks: Tuple[FrontierTrackSnapshot, ...],
        scope: AuthorizedExplorationScope,
        frontier_policy: FrontierTaskEvidencePolicy,
        portal_policy: PortalTaskEvidencePolicy,
        transit_evidence: PortalTaskEvidenceBatch,
) -> TransitPurposeEvidenceBatch:
    """Bind each selectable transit to fresh work after its exact crossing.

    A transit proposal proves the first portal route from the robot's current
    pose.  Its proposal endpoint is then used only as a *virtual* pose to
    evaluate work that starts in the target region: a local frontier or the
    next confirmed portal.  This reuses the existing route/evidence adapters;
    it neither creates a graph path nor grants a later goal.  If no such work
    is currently evidenced, the transit is held back while its graph task and
    all blocked work remain visible for a later fresh reassessment.
    """
    if not isinstance(correlation, PortalSourceCorrelation):
        raise PortalTaskEvidenceError("Transitbedarf braucht Kartenkorrelation")
    if not isinstance(transit_evidence, PortalTaskEvidenceBatch):
        raise PortalTaskEvidenceError("Transitbedarf braucht Portalevidenz")
    if transit_evidence.source_map_revision != correlation.map_revision:
        raise PortalTaskEvidenceError(
            "Transitbedarf und Portalevidenz haben verschiedene Revisionen")
    if not isinstance(tasks, tuple) or any(
            not isinstance(task, RegionTaskSnapshot) for task in tasks):
        raise PortalTaskEvidenceError("Transitbedarf braucht Aufgabenbestand")
    if not isinstance(tracks, tuple) or any(
            not isinstance(track, FrontierTrackSnapshot) for track in tracks):
        raise PortalTaskEvidenceError("Transitbedarf braucht Frontierbestand")
    if not isinstance(frontier_policy, FrontierTaskEvidencePolicy):
        raise PortalTaskEvidenceError("Transitbedarf braucht Frontierpolicy")
    if not isinstance(portal_policy, PortalTaskEvidencePolicy):
        raise PortalTaskEvidenceError("Transitbedarf braucht Portalpolicy")
    if len({task.task_id for task in tasks}) != len(tasks):
        raise PortalTaskEvidenceError("Transitbedarf besitzt doppelte Aufgaben")
    if len({item.portal_id for item in connections}) != len(connections):
        raise PortalTaskEvidenceError("Transitbedarf besitzt doppelte Verbindungen")

    open_tasks = tuple(
        task for task in tasks if task.state is RegionTaskState.OPEN)
    transit_tasks = tuple(
        task for task in open_tasks if task.kind is RegionTaskKind.TRANSIT)
    availability_by_task = {
        item.task_id: item for item in transit_evidence.availability}
    proposal_by_task = {
        item.task_id: item for item in transit_evidence.proposals}
    connection_by_portal = {
        item.portal_id: item for item in connections}
    replacements = []
    assessments = []

    for transit in sorted(transit_tasks, key=lambda item: item.task_id):
        route_availability = availability_by_task.get(transit.task_id)
        if route_availability is None:
            route_availability = TaskAvailability(
                task_id=transit.task_id,
                context=correlation.context,
                map_revision=correlation.map_revision,
                state=TaskAvailabilityState.UNKNOWN,
                reason="missing_transit_route_evidence",
                recheck_condition="build_exact_portal_route_evidence",
            )
        proposal = proposal_by_task.get(transit.task_id)
        if route_availability.state is not TaskAvailabilityState.AVAILABLE:
            replacements.append(route_availability)
            assessments.append(TransitPurposeAssessment(
                transit_task_id=transit.task_id,
                target_region_id=transit.region_id,
                portal_id=transit.subject_id,
                state=route_availability.state,
                reason=route_availability.reason,
                recheck_condition=route_availability.recheck_condition,
            ))
            continue
        if proposal is None:
            raise PortalTaskEvidenceError(
                "Verfuegbarer Transit besitzt keine exakte Portalroute")
        if (
                proposal.region_id != transit.region_id
                or proposal.portal_id != transit.subject_id):
            raise PortalTaskEvidenceError(
                "Transitroute passt nicht zur Graphaufgabe")

        target_frontiers = tuple(
            task for task in open_tasks
            if (
                task.kind is RegionTaskKind.FRONTIER
                and task.region_id == transit.region_id))
        target_portals = tuple(
            task for task in open_tasks
            if (
                task.kind is RegionTaskKind.PORTAL
                and _portal_entry_region(
                    task, connection_by_portal.get(task.subject_id))
                == transit.region_id))
        virtual_frontiers = build_frontier_task_evidence(
            correlation,
            width=width,
            height=height,
            resolution=resolution,
            frame_id=frame_id,
            origin=origin,
            cells=cells,
            source_stamp_ns=source_stamp_ns,
            robot_xy=(proposal.target_x_m, proposal.target_y_m),
            tasks=target_frontiers,
            tracks=tracks,
            policy=frontier_policy,
        )
        virtual_portals = build_portal_task_evidence(
            correlation,
            width=width,
            height=height,
            resolution=resolution,
            frame_id=frame_id,
            origin=origin,
            cells=cells,
            source_stamp_ns=source_stamp_ns,
            robot_xy=(proposal.target_x_m, proposal.target_y_m),
            current_region_id=transit.region_id,
            tasks=target_portals,
            portals=portals,
            connections=connections,
            scope=scope,
            policy=portal_policy,
        )
        purpose_availability = {
            item.task_id: item
            for item in (
                virtual_frontiers.availability + virtual_portals.availability)
        }
        purpose_tasks = tuple(
            task for task in (*target_frontiers, *target_portals)
            if purpose_availability[task.task_id].state
            is TaskAvailabilityState.AVAILABLE)
        if not purpose_tasks:
            held = replace(
                route_availability,
                state=TaskAvailabilityState.TEMPORARILY_BLOCKED,
                reason="transit_no_available_purpose_in_target_region",
                recheck_condition=(
                    "reassess_target_region_work_on_fresh_map_revision"),
            )
            replacements.append(held)
            assessments.append(TransitPurposeAssessment(
                transit_task_id=transit.task_id,
                target_region_id=transit.region_id,
                portal_id=transit.subject_id,
                state=held.state,
                reason=held.reason,
                recheck_condition=held.recheck_condition,
            ))
            continue
        purpose = sorted(purpose_tasks, key=lambda item: item.task_id)[0]
        ready = replace(
            route_availability,
            reason="transit_purpose_available_after_crossing",
            recheck_condition=(
                "revalidate_transit_purpose_before_and_after_crossing"),
        )
        replacements.append(ready)
        assessments.append(TransitPurposeAssessment(
            transit_task_id=transit.task_id,
            target_region_id=transit.region_id,
            portal_id=transit.subject_id,
            state=ready.state,
            reason=ready.reason,
            recheck_condition=ready.recheck_condition,
            purpose_task_id=purpose.task_id,
            purpose_kind=purpose.kind,
            next_portal_id=(
                purpose.subject_id
                if purpose.kind is RegionTaskKind.PORTAL else None),
        ))
    return TransitPurposeEvidenceBatch(
        source_map_revision=correlation.map_revision,
        availability=tuple(replacements),
        assessments=tuple(assessments),
    )


def bind_portal_goal_candidate(
        intent: ExplorationGoalIntent,
        proposal: PortalGoalProposal) -> PortalGoalCandidate:
    """Bind one selected task route to the current child-goal intention."""
    if not isinstance(intent, ExplorationGoalIntent):
        raise PortalTaskEvidenceError(
            "intent muss ExplorationGoalIntent sein")
    if not isinstance(proposal, PortalGoalProposal):
        raise PortalTaskEvidenceError(
            "proposal muss PortalGoalProposal sein")
    if (
            intent.task_id != proposal.task_id
            or intent.region_id != proposal.region_id
            or intent.map_revision != proposal.map_revision
            or intent.context != proposal.context
            or intent.context.frame_id != proposal.frame_id):
        raise PortalTaskEvidenceError(
            "Portalroute passt nicht zur Zielabsicht")
    return PortalGoalCandidate(
        intent_id=intent.intent_id,
        **{
            field: getattr(proposal, field)
            for field in proposal.__dataclass_fields__
        },
    )
