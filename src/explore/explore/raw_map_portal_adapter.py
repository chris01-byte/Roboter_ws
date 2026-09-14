"""Build passive portal candidates from one exactly correlated raw map.

This module is ROS-free and has no runtime, planner, filesystem or actuator
side effects.  Its candidates remain structurally unqualified.
"""

import hashlib
import math
import struct
from typing import Any, Iterable, Tuple

import numpy as np

from amadeus_map_identity import (
    MAXIMUM_OCCUPANCY_CELL_COUNT,
    MapIdentityError,
    compact_occupancy_cells,
    map_snapshot_fingerprint,
)

from .portal_memory import PortalMapContext
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
