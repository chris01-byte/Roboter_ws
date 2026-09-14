"""Pure scalar evidence for revision-bound passive frontier tasks.

The adapter verifies one raw occupancy snapshot against the exact shadow
correlation, associates open graph tasks with stable frontier tracks and emits
only availability plus scalar route/information evidence.  It emits no pose,
path, goal, planner request, ROS interface, or motion authorization.
"""

from dataclasses import dataclass
import math
from typing import Any, Iterable, Optional, Tuple

import numpy as np
from scipy.ndimage import distance_transform_edt
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import dijkstra

from amadeus_map_identity import (
    MAXIMUM_OCCUPANCY_CELL_COUNT,
    MapIdentityError,
    compact_occupancy_cells,
    map_snapshot_fingerprint,
)

from .exploration_policy import (
    TaskAvailability,
    TaskAvailabilityState,
    TaskUtilityEvidence,
)
from .frontier_task_feed import FrontierTrackSnapshot
from .portal_source_adapter import (
    PortalSourceAdapterError,
    PortalSourceCorrelation,
    RawMapPortalSource,
)
from .region_graph import (
    RegionTaskKind,
    RegionTaskSnapshot,
    RegionTaskState,
)


class FrontierTaskEvidenceError(ValueError):
    """The exact map and passive task inventory are inconsistent."""


class FrontierTaskEvidenceCapacityError(FrontierTaskEvidenceError):
    """A configured hard input or search bound would be exceeded."""


DEFAULT_FRONTIER_EVIDENCE_MAX_CELLS = 512 * 512


@dataclass(frozen=True)
class FrontierTaskEvidencePolicy:
    """Synthetic software start values; not measured hardware limits."""

    clearance_m: float = 0.28
    robot_seed_search_m: float = 0.75
    task_cell_search_m: float = 0.60
    information_radius_m: float = 0.75
    max_tasks: int = 4096
    max_tracks: int = 4096
    max_cells: int = DEFAULT_FRONTIER_EVIDENCE_MAX_CELLS

    def __post_init__(self) -> None:
        for name in (
                "clearance_m", "robot_seed_search_m",
                "task_cell_search_m", "information_radius_m"):
            value = _finite_nonnegative(getattr(self, name), name)
            if value <= 0.0:
                raise FrontierTaskEvidenceError(f"{name} muss positiv sein")
            object.__setattr__(self, name, value)
        for name in ("max_tasks", "max_tracks", "max_cells"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise FrontierTaskEvidenceError(
                    f"{name} muss eine positive Ganzzahl sein")
        if self.max_cells > MAXIMUM_OCCUPANCY_CELL_COUNT:
            raise FrontierTaskEvidenceError(
                "max_cells darf die gemeinsame Kartengrenze nicht erhoehen")


@dataclass(frozen=True)
class FrontierTaskEvidenceBatch:
    """Complete evidence outcome for every open task in one revision."""

    source_map_revision: int
    availability: Tuple[TaskAvailability, ...]
    utilities: Tuple[TaskUtilityEvidence, ...]
    robot_seed_available: bool
    current_frontier_track_count: int


def _finite_nonnegative(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise FrontierTaskEvidenceError(
            f"{name} muss eine nichtnegative endliche Zahl sein")
    normalized = float(value)
    if not math.isfinite(normalized) or normalized < 0.0:
        raise FrontierTaskEvidenceError(
            f"{name} muss eine nichtnegative endliche Zahl sein")
    return normalized


def _validated_origin(origin: object) -> Tuple[Tuple[float, ...], float]:
    if not isinstance(origin, tuple) or len(origin) != 7:
        raise FrontierTaskEvidenceError(
            "origin muss ein unveraenderliches 7-Tupel sein")
    if any(
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(float(value))
            for value in origin):
        raise FrontierTaskEvidenceError("origin muss endlich sein")
    normalized = tuple(float(value) for value in origin)
    position_z, qx, qy, qz, qw = normalized[2:]
    quaternion_norm = math.sqrt(qx * qx + qy * qy + qz * qz + qw * qw)
    if (
            abs(position_z) > 1e-9
            or abs(qx) > 1e-9
            or abs(qy) > 1e-9
            or abs(quaternion_norm - 1.0) > 1e-6):
        raise FrontierTaskEvidenceError(
            "Rohkartenursprung muss planar und normiert sein")
    yaw = math.atan2(2.0 * qw * qz, 1.0 - 2.0 * qz * qz)
    return normalized, yaw


def _validated_snapshot(
        correlation: object, *, width: object, height: object,
        resolution: object, frame_id: object, origin: object,
        cells: Iterable[Any], source_stamp_ns: object,
        max_cells: int) -> Tuple[np.ndarray, float, Tuple[float, ...], float]:
    if not isinstance(correlation, PortalSourceCorrelation):
        raise FrontierTaskEvidenceError(
            "correlation muss PortalSourceCorrelation sein")
    if (
            isinstance(width, bool) or not isinstance(width, int)
            or isinstance(height, bool) or not isinstance(height, int)
            or width <= 0 or height <= 0
            or width * height > max_cells):
        raise FrontierTaskEvidenceCapacityError(
            "Kartendimensionen sind ungueltig oder zu gross")
    resolution_m = _finite_nonnegative(resolution, "resolution")
    if resolution_m <= 0.0:
        raise FrontierTaskEvidenceError("resolution muss positiv sein")
    clean_origin, yaw = _validated_origin(origin)
    try:
        compact_cells = compact_occupancy_cells(
            cells=cells, cell_count=width * height)
        fingerprint = map_snapshot_fingerprint(
            width=width,
            height=height,
            resolution=resolution_m,
            frame_id=frame_id,
            origin=clean_origin,
            compact_cells=compact_cells,
        )
        source = RawMapPortalSource(
            fingerprint=fingerprint,
            source_stamp_ns=source_stamp_ns,
            frame_id=frame_id,
        )
    except (MapIdentityError, PortalSourceAdapterError) as error:
        raise FrontierTaskEvidenceError(
            "Rohkartensnapshot ist nicht kanonisch") from error
    if (
            source.fingerprint != correlation.fingerprint
            or source.source_stamp_ns != correlation.source_stamp_ns
            or source.frame_id != correlation.context.frame_id):
        raise FrontierTaskEvidenceError(
            "Rohkartensnapshot passt nicht zur Korrelation")
    unsigned = np.frombuffer(compact_cells, dtype=np.uint8)
    occupancy = unsigned.astype(np.int16).reshape((height, width))
    occupancy[occupancy == 255] = -1
    return occupancy, resolution_m, clean_origin, yaw


def _world_to_grid(
        xy: Tuple[float, float], origin: Tuple[float, ...], yaw: float,
        resolution_m: float) -> Tuple[int, int]:
    dx = float(xy[0]) - origin[0]
    dy = float(xy[1]) - origin[1]
    cosine = math.cos(yaw)
    sine = math.sin(yaw)
    col = math.floor((cosine * dx + sine * dy) / resolution_m)
    row = math.floor((-sine * dx + cosine * dy) / resolution_m)
    return row, col


def _validated_robot_xy(
        robot_xy: Optional[Tuple[float, float]]) -> Optional[Tuple[float, float]]:
    if robot_xy is None:
        return None
    if (
            not isinstance(robot_xy, tuple) or len(robot_xy) != 2
            or any(
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(float(value))
                for value in robot_xy)):
        raise FrontierTaskEvidenceError(
            "robot_xy muss None oder ein endliches unveraenderliches XY-Paar sein")
    return float(robot_xy[0]), float(robot_xy[1])


def _nearest_mask_cell(
        mask: np.ndarray, row: int, col: int,
        maximum_distance_cells: int) -> Optional[Tuple[int, int]]:
    row0 = max(0, row - maximum_distance_cells)
    row1 = min(mask.shape[0], row + maximum_distance_cells + 1)
    col0 = max(0, col - maximum_distance_cells)
    col1 = min(mask.shape[1], col + maximum_distance_cells + 1)
    if row0 >= row1 or col0 >= col1:
        return None
    rows, cols = np.nonzero(mask[row0:row1, col0:col1])
    if rows.size == 0:
        return None
    rows = rows + row0
    cols = cols + col0
    distances = (rows - row) ** 2 + (cols - col) ** 2
    within = distances <= maximum_distance_cells ** 2
    if not np.any(within):
        return None
    candidates = sorted(
        (int(distances[index]), int(rows[index]), int(cols[index]))
        for index in np.nonzero(within)[0])
    _, selected_row, selected_col = candidates[0]
    return selected_row, selected_col


def _geodesic_distances(
        traversable: np.ndarray,
        seed: Tuple[int, int]) -> np.ndarray:
    """Return sparse 8-neighbour distances without diagonal corner cutting."""
    height, width = traversable.shape
    cell_ids = np.arange(
        height * width, dtype=np.int32).reshape((height, width))

    horizontal = traversable[:, :-1] & traversable[:, 1:]
    vertical = traversable[:-1, :] & traversable[1:, :]
    diagonal_right = (
        traversable[:-1, :-1]
        & traversable[1:, 1:]
        & traversable[:-1, 1:]
        & traversable[1:, :-1]
    )
    diagonal_left = (
        traversable[:-1, 1:]
        & traversable[1:, :-1]
        & traversable[:-1, :-1]
        & traversable[1:, 1:]
    )
    rows = np.concatenate((
        cell_ids[:, :-1][horizontal],
        cell_ids[:-1, :][vertical],
        cell_ids[:-1, :-1][diagonal_right],
        cell_ids[:-1, 1:][diagonal_left],
    ))
    columns = np.concatenate((
        cell_ids[:, 1:][horizontal],
        cell_ids[1:, :][vertical],
        cell_ids[1:, 1:][diagonal_right],
        cell_ids[1:, :-1][diagonal_left],
    ))
    orthogonal_count = int(np.count_nonzero(horizontal)) + int(
        np.count_nonzero(vertical))
    weights = np.concatenate((
        np.ones(orthogonal_count, dtype=np.float64),
        np.full(
            rows.size - orthogonal_count,
            math.sqrt(2.0),
            dtype=np.float64,
        ),
    ))
    graph = coo_matrix(
        (weights, (rows, columns)),
        shape=(height * width, height * width),
    ).tocsr()
    seed_index = seed[0] * width + seed[1]
    distances = dijkstra(
        graph, directed=False, indices=seed_index, return_predecessors=False)
    return distances.reshape((height, width))


def _information_gain_square_m(
        occupancy: np.ndarray, row: int, col: int,
        radius_cells: int, resolution_m: float) -> float:
    row0 = max(0, row - radius_cells)
    row1 = min(occupancy.shape[0], row + radius_cells + 1)
    col0 = max(0, col - radius_cells)
    col1 = min(occupancy.shape[1], col + radius_cells + 1)
    yy, xx = np.ogrid[row0:row1, col0:col1]
    disk = (yy - row) ** 2 + (xx - col) ** 2 <= radius_cells ** 2
    unknown = occupancy[row0:row1, col0:col1] < 0
    return float(np.count_nonzero(unknown & disk)) * resolution_m ** 2


def build_frontier_task_evidence(
        correlation: PortalSourceCorrelation, *,
        width: int, height: int, resolution: float, frame_id: str,
        origin: Tuple[float, float, float, float, float, float, float],
        cells: Iterable[Any], source_stamp_ns: int,
        robot_xy: Optional[Tuple[float, float]],
        tasks: Tuple[RegionTaskSnapshot, ...],
        tracks: Tuple[FrontierTrackSnapshot, ...],
        policy: Optional[FrontierTaskEvidencePolicy] = None,
) -> FrontierTaskEvidenceBatch:
    """Build complete scalar evidence for all open tasks in one map revision."""
    selected_policy = policy or FrontierTaskEvidencePolicy()
    if not isinstance(selected_policy, FrontierTaskEvidencePolicy):
        raise FrontierTaskEvidenceError(
            "policy muss FrontierTaskEvidencePolicy sein")
    occupancy, resolution_m, clean_origin, yaw = _validated_snapshot(
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
    if not isinstance(tasks, tuple) or any(
            not isinstance(task, RegionTaskSnapshot) for task in tasks):
        raise FrontierTaskEvidenceError(
            "tasks muss ein Tupel aus RegionTaskSnapshot sein")
    if not isinstance(tracks, tuple) or any(
            not isinstance(track, FrontierTrackSnapshot) for track in tracks):
        raise FrontierTaskEvidenceError(
            "tracks muss ein Tupel aus FrontierTrackSnapshot sein")
    if len(tasks) > selected_policy.max_tasks:
        raise FrontierTaskEvidenceCapacityError(
            "Aufgabenbestand ueberschreitet die Evidenzgrenze")
    if len(tracks) > selected_policy.max_tracks:
        raise FrontierTaskEvidenceCapacityError(
            "Frontierbestand ueberschreitet die Evidenzgrenze")
    task_ids = [task.task_id for task in tasks]
    track_ids = [track.frontier_id for track in tracks]
    if len(set(task_ids)) != len(task_ids):
        raise FrontierTaskEvidenceError("Aufgabenbestand enthaelt Duplikate")
    if len(set(track_ids)) != len(track_ids):
        raise FrontierTaskEvidenceError("Frontierbestand enthaelt Duplikate")
    if any(task.state is not RegionTaskState.OPEN for task in tasks):
        raise FrontierTaskEvidenceError(
            "Evidenzadapter akzeptiert nur offene Aufgaben")
    if any(
            task.created_revision > correlation.map_revision
            or task.last_revision > correlation.map_revision
            for task in tasks):
        raise FrontierTaskEvidenceError(
            "Aufgabe liegt vor der aktuellen Kartenrevision")
    if any(track.last_revision > correlation.map_revision for track in tracks):
        raise FrontierTaskEvidenceError(
            "Frontiertrack liegt vor der aktuellen Kartenrevision")

    safe_free = occupancy == 0
    clearance_cells = selected_policy.clearance_m / resolution_m
    padded = np.pad(safe_free, 1, mode="constant", constant_values=False)
    clearance = distance_transform_edt(padded)[1:-1, 1:-1]
    traversable = safe_free & (clearance >= clearance_cells)
    robot_seed = None
    distances = np.full(occupancy.shape, np.inf, dtype=np.float64)
    if normalized_robot_xy is not None:
        robot_row, robot_col = _world_to_grid(
            normalized_robot_xy, clean_origin, yaw, resolution_m)
        robot_seed = _nearest_mask_cell(
            traversable,
            robot_row,
            robot_col,
            int(math.ceil(
                selected_policy.robot_seed_search_m / resolution_m)),
        )
        if robot_seed is not None:
            distances = _geodesic_distances(traversable, robot_seed)

    tracks_by_id = {track.frontier_id: track for track in tracks}
    task_search_cells = int(math.ceil(
        selected_policy.task_cell_search_m / resolution_m))
    information_radius_cells = max(1, int(math.ceil(
        selected_policy.information_radius_m / resolution_m)))
    availability = []
    utilities = []
    for task in sorted(tasks, key=lambda item: item.task_id):
        state = TaskAvailabilityState.UNKNOWN
        reason = "unsupported_task_kind"
        recheck = "supply_task_specific_evidence"
        utility = None
        if task.kind is RegionTaskKind.FRONTIER:
            track = tracks_by_id.get(task.subject_id)
            if track is None:
                reason = "missing_frontier_track"
                recheck = "observe_complete_frontier_inventory"
            elif track.last_revision != correlation.map_revision:
                reason = "frontier_not_observed_in_current_revision"
                recheck = "observe_frontier_on_current_map_revision"
            elif normalized_robot_xy is None:
                reason = "missing_robot_pose"
                recheck = "supply_current_map_frame_robot_pose"
            elif robot_seed is None:
                state = TaskAvailabilityState.TEMPORARILY_BLOCKED
                reason = "robot_outside_safe_free_space"
                recheck = "reassess_after_pose_or_map_update"
            else:
                frontier_row, frontier_col = _world_to_grid(
                    (track.centroid.x, track.centroid.y),
                    clean_origin,
                    yaw,
                    resolution_m,
                )
                target_cell = _nearest_mask_cell(
                    traversable,
                    frontier_row,
                    frontier_col,
                    task_search_cells,
                )
                if (
                        target_cell is None
                        or not math.isfinite(distances[target_cell])):
                    state = TaskAvailabilityState.TEMPORARILY_BLOCKED
                    reason = "no_current_raw_map_route"
                    recheck = "reassess_after_map_revision"
                else:
                    target_row, target_col = target_cell
                    information = _information_gain_square_m(
                        occupancy,
                        frontier_row,
                        frontier_col,
                        information_radius_cells,
                        resolution_m,
                    )
                    if information <= 0.0:
                        state = TaskAvailabilityState.FILTERED
                        reason = "no_current_information_gain"
                        recheck = "reassess_after_map_revision"
                    else:
                        state = TaskAvailabilityState.AVAILABLE
                        reason = "raw_map_geodesic_and_information_available"
                        recheck = "revalidate_before_navigation"
                        utility = TaskUtilityEvidence(
                            task_id=task.task_id,
                            context=correlation.context,
                            map_revision=correlation.map_revision,
                            geodesic_path_length_m=(
                                float(distances[target_row, target_col])
                                * resolution_m),
                            information_gain_square_m=information,
                        )
        availability.append(TaskAvailability(
            task_id=task.task_id,
            context=correlation.context,
            map_revision=correlation.map_revision,
            state=state,
            reason=reason,
            recheck_condition=recheck,
        ))
        if utility is not None:
            utilities.append(utility)

    return FrontierTaskEvidenceBatch(
        source_map_revision=correlation.map_revision,
        availability=tuple(availability),
        utilities=tuple(utilities),
        robot_seed_available=robot_seed is not None,
        current_frontier_track_count=sum(
            track.last_revision == correlation.map_revision
            for track in tracks),
    )
