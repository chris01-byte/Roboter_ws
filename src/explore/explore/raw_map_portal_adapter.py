"""Build passive portal evidence from one exactly correlated raw map.

This module is ROS-free and has no runtime, planner, filesystem or actuator
side effects.  The legacy candidate adapter remains structurally unqualified;
the richer observation adapter qualifies only a topologically separating neck.
"""

import hashlib
import math
import struct
from typing import Any, Iterable, Tuple

import numpy as np
from scipy.ndimage import label

from amadeus_map_identity import (
    MAXIMUM_OCCUPANCY_CELL_COUNT,
    MapIdentityError,
    compact_occupancy_cells,
    map_snapshot_fingerprint,
)

from .portal_memory import (
    Point2D,
    PortalMapContext,
    PortalObservation,
    PortalObservationInventory,
    PortalStructuralEvidence,
)
from .portal_plan_adapter import PortalPlanCandidate
from .portal_planning import find_connected_clearance_portals
from .portal_source_adapter import (
    PortalSourceAdapterError,
    PortalSourceCorrelation,
    RawMapPortalSource,
)


class RawMapPortalCandidateError(ValueError):
    """The exact raw snapshot cannot produce passive portal candidates."""


def _validated_correlation(
        correlation: object) -> PortalSourceCorrelation:
    if not isinstance(correlation, PortalSourceCorrelation):
        raise RawMapPortalCandidateError(
            "correlation muss PortalSourceCorrelation sein")
    if not isinstance(correlation.context, PortalMapContext):
        raise RawMapPortalCandidateError(
            "Korrelation enthaelt keinen gueltigen Kartenkontext")
    if (
            isinstance(correlation.map_revision, bool)
            or not isinstance(correlation.map_revision, int)
            or correlation.map_revision <= 0):
        raise RawMapPortalCandidateError(
            "Korrelation enthaelt keine positive Kartenrevision")
    try:
        RawMapPortalSource(
            fingerprint=correlation.fingerprint,
            source_stamp_ns=correlation.source_stamp_ns,
            frame_id=correlation.context.frame_id,
        )
    except PortalSourceAdapterError as error:
        raise RawMapPortalCandidateError(
            "Korrelation enthaelt keine gueltige Rohkartenidentitaet"
        ) from error
    return correlation


def _validated_planar_origin(
        origin: object) -> Tuple[Tuple[float, ...], float]:
    if not isinstance(origin, tuple) or len(origin) != 7:
        raise RawMapPortalCandidateError(
            "origin muss ein unveraenderliches 7-Tupel sein")
    if any(
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(float(value))
            for value in origin):
        raise RawMapPortalCandidateError("origin muss endlich sein")
    normalized = tuple(float(value) for value in origin)
    position_z, qx, qy, qz, qw = normalized[2:]
    quaternion_norm = math.sqrt(qx * qx + qy * qy + qz * qz + qw * qw)
    if (
            abs(position_z) > 1e-9
            or abs(qx) > 1e-9
            or abs(qy) > 1e-9
            or abs(quaternion_norm - 1.0) > 1e-6):
        raise RawMapPortalCandidateError(
            "Rohkartenursprung muss planar und normiert sein")
    yaw = math.atan2(2.0 * qw * qz, 1.0 - 2.0 * qz * qz)
    return normalized, yaw


def _candidate_id(
        source: RawMapPortalSource, staging_row: int, staging_col: int,
        target_row: int, target_col: int) -> str:
    digest = hashlib.sha256()
    digest.update(b"connected-clearance-v1\0")
    digest.update(bytes.fromhex(source.fingerprint))
    digest.update(struct.pack(
        "!Q4I", source.source_stamp_ns,
        staging_row, staging_col, target_row, target_col))
    return "raw-connected-" + digest.hexdigest()


def correlated_connected_portal_candidates(
        correlation: PortalSourceCorrelation, *,
        width: int, height: int, resolution: float, frame_id: str,
        origin: Tuple[float, float, float, float, float, float, float],
        cells: Iterable[Any], source_stamp_ns: int,
        robot_xy: Tuple[float, float], uncertainty_m: float,
        analysis_clearance_m: float, min_target_area_m2: float,
        min_gap_m: float, max_gap_m: float, exit_margin_m: float,
        max_traverse_distance_m: float,
        robot_seed_search_m: float = 0.75,
) -> Tuple[PortalPlanCandidate, ...]:
    """Return deterministic unqualified candidates for an exact raw map."""
    proven = _validated_correlation(correlation)
    if (
            isinstance(width, bool) or not isinstance(width, int)
            or isinstance(height, bool) or not isinstance(height, int)
            or width <= 0 or height <= 0
            or width * height > MAXIMUM_OCCUPANCY_CELL_COUNT):
        raise RawMapPortalCandidateError(
            "Kartendimensionen sind ungueltig oder zu gross")
    clean_origin, yaw = _validated_planar_origin(origin)
    try:
        compact_cells = compact_occupancy_cells(
            cells=cells, cell_count=width * height)
        fingerprint = map_snapshot_fingerprint(
            width=width,
            height=height,
            resolution=resolution,
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
        raise RawMapPortalCandidateError(
            "Rohkartensnapshot ist nicht kanonisch") from error
    if (
            source.fingerprint != proven.fingerprint
            or source.source_stamp_ns != proven.source_stamp_ns
            or source.frame_id != proven.context.frame_id):
        raise RawMapPortalCandidateError(
            "Verwendeter Rohkartensnapshot passt nicht zur Korrelation")
    if (
            not isinstance(robot_xy, tuple) or len(robot_xy) != 2
            or any(
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(float(value))
                for value in robot_xy)):
        raise RawMapPortalCandidateError(
            "robot_xy muss ein endliches unveraenderliches XY-Paar sein")
    if (
            isinstance(uncertainty_m, bool)
            or not isinstance(uncertainty_m, (int, float))
            or not math.isfinite(float(uncertainty_m))
            or uncertainty_m < 0.0):
        raise RawMapPortalCandidateError(
            "uncertainty_m muss endlich und nichtnegativ sein")

    resolution_m = float(resolution)
    cosine = math.cos(yaw)
    sine = math.sin(yaw)
    dx = float(robot_xy[0]) - clean_origin[0]
    dy = float(robot_xy[1]) - clean_origin[1]
    robot_col = math.floor((cosine * dx + sine * dy) / resolution_m)
    robot_row = math.floor((-sine * dx + cosine * dy) / resolution_m)

    unsigned = np.frombuffer(compact_cells, dtype=np.uint8)
    occupancy = unsigned.astype(np.int16).reshape((height, width))
    occupancy[occupancy == 255] = -1
    try:
        bridges = find_connected_clearance_portals(
            occupancy,
            (robot_row, robot_col),
            resolution_m=resolution_m,
            analysis_clearance_m=analysis_clearance_m,
            min_target_area_m2=min_target_area_m2,
            min_gap_m=min_gap_m,
            max_gap_m=max_gap_m,
            exit_margin_m=exit_margin_m,
            max_traverse_distance_m=max_traverse_distance_m,
            robot_seed_search_m=robot_seed_search_m,
        )
    except ValueError as error:
        raise RawMapPortalCandidateError(
            "Grenzen oder Raster des verbundenen Detektors sind ungueltig"
        ) from error

    def grid_to_world(row: int, col: int) -> Tuple[float, float]:
        local_x = (col + 0.5) * resolution_m
        local_y = (row + 0.5) * resolution_m
        return (
            clean_origin[0] + cosine * local_x - sine * local_y,
            clean_origin[1] + sine * local_x + cosine * local_y,
        )

    return tuple(
        PortalPlanCandidate(
            observation_id=_candidate_id(
                source,
                bridge.staging_row,
                bridge.staging_col,
                bridge.target_row,
                bridge.target_col,
            ),
            context=proven.context,
            map_revision=proven.map_revision,
            staging_xy=grid_to_world(
                bridge.staging_row, bridge.staging_col),
            target_xy=grid_to_world(
                bridge.target_row, bridge.target_col),
            uncertainty_m=float(uncertainty_m),
        )
        for bridge in bridges
    )


def _separator_evidence(
        occupancy: np.ndarray, *, robot_cell: Tuple[int, int],
        staging_cell: Tuple[int, int], target_cell: Tuple[int, int],
        resolution_m: float, analysis_clearance_m: float,
        minimum_region_area_m2: float) -> PortalStructuralEvidence:
    """Qualify only a neck whose local removal separates two large areas.

    This topological check cannot identify physical wall material.  It only
    proves that the detected neck is a separator in this exact measured-free
    raster.  Independent map revisions remain mandatory in ``PortalMemory``.
    """
    measured_free = occupancy == 0
    height, width = measured_free.shape
    robot_row, robot_col = robot_cell
    if not (
            0 <= robot_row < height and 0 <= robot_col < width
            and measured_free[robot_row, robot_col]):
        return PortalStructuralEvidence.INSUFFICIENT

    staging_row, staging_col = staging_cell
    target_row, target_col = target_cell
    axis_row = float(target_row - staging_row)
    axis_col = float(target_col - staging_col)
    axis_length = math.hypot(axis_row, axis_col)
    if axis_length <= 1e-9:
        return PortalStructuralEvidence.INSUFFICIENT
    unit_row = axis_row / axis_length
    unit_col = axis_col / axis_length
    probe_offset = int(math.ceil(
        analysis_clearance_m / resolution_m)) + 2
    far_row = int(round(target_row + probe_offset * unit_row))
    far_col = int(round(target_col + probe_offset * unit_col))
    if not (
            0 <= far_row < height and 0 <= far_col < width
            and measured_free[far_row, far_col]):
        return PortalStructuralEvidence.INSUFFICIENT

    rows, cols = np.ogrid[:height, :width]
    midpoint_row = 0.5 * (staging_row + target_row)
    midpoint_col = 0.5 * (staging_col + target_col)
    cut = (
        np.hypot(rows - midpoint_row, cols - midpoint_col) * resolution_m
        <= analysis_clearance_m)
    remaining = measured_free & ~cut
    components, _component_count = label(remaining)
    source_label = int(components[robot_row, robot_col])
    target_label = int(components[far_row, far_col])
    if source_label <= 0 or target_label <= 0 or source_label == target_label:
        return PortalStructuralEvidence.INSUFFICIENT
    minimum_cells = max(
        1, int(math.ceil(minimum_region_area_m2 / resolution_m ** 2)))
    sizes = np.bincount(components.ravel())
    if (
            sizes[source_label] < minimum_cells
            or sizes[target_label] < minimum_cells):
        return PortalStructuralEvidence.INSUFFICIENT
    return PortalStructuralEvidence.QUALIFIED


def correlated_connected_portal_observations(
        correlation: PortalSourceCorrelation, **arguments,
) -> Tuple[PortalObservation, ...]:
    """Build exact-map observations with conservative separator evidence.

    The underlying detector, fingerprint validation and candidate IDs are
    unchanged.  A candidate is structurally qualified only when removing a
    clearance-sized disk around its neck disconnects the robot side from a
    sufficiently large far side in the same exact measured-free raster.
    """
    candidates = correlated_connected_portal_candidates(
        correlation, **arguments)
    if not candidates:
        return ()

    width = arguments["width"]
    height = arguments["height"]
    resolution_m = float(arguments["resolution"])
    origin, yaw = _validated_planar_origin(arguments["origin"])
    try:
        compact_cells = compact_occupancy_cells(
            cells=arguments["cells"], cell_count=width * height)
    except MapIdentityError as error:
        raise RawMapPortalCandidateError(
            "Rohkartenzellen sind fuer Strukturevidenz ungueltig") from error
    occupancy = np.frombuffer(
        compact_cells, dtype=np.uint8).astype(np.int16).reshape(
            (height, width))
    occupancy[occupancy == 255] = -1
    cosine = math.cos(yaw)
    sine = math.sin(yaw)

    def world_to_grid(point: Tuple[float, float]) -> Tuple[int, int]:
        dx = point[0] - origin[0]
        dy = point[1] - origin[1]
        col = (cosine * dx + sine * dy) / resolution_m - 0.5
        row = (-sine * dx + cosine * dy) / resolution_m - 0.5
        return int(round(row)), int(round(col))

    robot_xy = arguments["robot_xy"]
    robot_dx = float(robot_xy[0]) - origin[0]
    robot_dy = float(robot_xy[1]) - origin[1]
    robot_cell = (
        math.floor((-sine * robot_dx + cosine * robot_dy) / resolution_m),
        math.floor((cosine * robot_dx + sine * robot_dy) / resolution_m),
    )
    observations = []
    for candidate in candidates:
        evidence = _separator_evidence(
            occupancy,
            robot_cell=robot_cell,
            staging_cell=world_to_grid(candidate.staging_xy),
            target_cell=world_to_grid(candidate.target_xy),
            resolution_m=resolution_m,
            analysis_clearance_m=float(arguments["analysis_clearance_m"]),
            minimum_region_area_m2=float(arguments["min_target_area_m2"]),
        )
        observations.append(PortalObservation(
            observation_id=candidate.observation_id,
            context=candidate.context,
            map_revision=candidate.map_revision,
            near_side=Point2D(*candidate.staging_xy),
            far_side=Point2D(*candidate.target_xy),
            uncertainty_m=candidate.uncertainty_m,
            structural_evidence=evidence,
        ))
    return tuple(observations)


def correlated_connected_portal_inventory(
        correlation: PortalSourceCorrelation, *,
        maximum_observations: int = 256, **arguments,
) -> PortalObservationInventory:
    """Return one explicit complete detector outcome, including empty.

    Construction succeeds only after the exact-map detector call succeeds.
    A missing object therefore remains distinct from a valid empty inventory.
    """
    if (
            isinstance(maximum_observations, bool)
            or not isinstance(maximum_observations, int)
            or maximum_observations <= 0):
        raise RawMapPortalCandidateError(
            "maximum_observations muss eine positive Ganzzahl sein")
    observations = tuple(sorted(
        correlated_connected_portal_observations(
            correlation, **arguments),
        key=lambda item: item.observation_id,
    ))
    if len(observations) > maximum_observations:
        raise RawMapPortalCandidateError(
            "Portalbestand ueberschreitet maximum_observations")

    digest = hashlib.sha256()
    digest.update(b"we-portal-inventory-v1\0")
    digest.update(correlation.context.session_id.encode("ascii"))
    digest.update(b"\0")
    digest.update(correlation.context.map_id.encode("ascii"))
    digest.update(b"\0")
    digest.update(correlation.context.frame_id.encode("ascii"))
    digest.update(b"\0")
    digest.update(str(correlation.map_revision).encode("ascii"))
    digest.update(b"\0")
    digest.update(correlation.fingerprint.encode("ascii"))
    digest.update(b"\0")
    digest.update(str(correlation.source_stamp_ns).encode("ascii"))
    for observation in observations:
        digest.update(b"\0")
        digest.update(observation.observation_id.encode("ascii"))
    return PortalObservationInventory(
        inventory_id=f"portal-inventory-{digest.hexdigest()}",
        context=correlation.context,
        map_revision=correlation.map_revision,
        observations=observations,
    )
