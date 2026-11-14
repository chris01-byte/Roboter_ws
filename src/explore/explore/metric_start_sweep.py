"""Continuous straight-start geometry candidate, without motion authority.

This checks a *whole* forward corridor, not a sequence of free point poses.
The padded chassis is enclosed for every heading in an interval and every
translation error in a disk. Exact cell polygons replace the half-cell and
sample-interpolation approximations. Heading bounds are analytic, not sampled.

This is deliberately a read-only qualification component. It does not bind
live sources, prove a controller's error bounds, or replace the active gate.
An admissible result alone must never dispatch an action or velocity command.
"""
from dataclasses import asdict, dataclass
import math

import numpy as np
from shapely.affinity import affine_transform
from shapely.geometry import Polygon, box
from shapely.ops import unary_union


PADDED_BOUNDS = (-.13, .33, -.25, .25)


@dataclass(frozen=True)
class StartSweepResult:
    geometry_admissible: bool
    reason: str
    outside_scope_area_m2: float = 0.
    outside_grid_area_m2: float = 0.
    occupied_area_m2: float = 0.
    new_unknown_area_m2: float = 0.
    initial_unknown_area_m2: float = 0.

    def report(self):
        return dict(asdict(self), motion_authorized=False,
                    qualification='offline_geometry_only')


def _extrema(a, b, half_angle):
    """Exact extrema of a*cos(t)+b*sin(t), -half_angle <= t <= half_angle."""
    candidates = [-half_angle, half_angle]
    stationary = math.atan2(b, a)
    first = math.ceil((-half_angle-stationary)/math.pi)
    last = math.floor((half_angle-stationary)/math.pi)
    candidates.extend(stationary+k*math.pi for k in range(first, last+1))
    values = [a*math.cos(t)+b*math.sin(t) for t in candidates]
    return min(values), max(values)


def enclosing_bounds(bounds, position_error_m, heading_error_rad):
    """An axis-aligned enclosure of every rotated corner plus error disk.

    The disk's projections are bounded by +/- position_error_m. The resulting
    rectangle is conservative at corners but cannot miss an intermediate yaw.
    Coordinates are in the initial robot frame, never raster coordinates.
    """
    values = (*bounds, position_error_m, heading_error_rad)
    if (len(bounds) != 4 or not all(math.isfinite(v) for v in values)
            or bounds[0] >= bounds[1] or bounds[2] >= bounds[3]
            or not 0 <= position_error_m <= 1.
            or not 0 <= heading_error_rad <= math.pi):
        raise ValueError('straight_sweep_invalid_envelope')
    corners = [(x, y) for x in bounds[:2] for y in bounds[2:]]
    xs = [_extrema(x, -y, heading_error_rad) for x, y in corners]
    ys = [_extrema(y, x, heading_error_rad) for x, y in corners]
    return (min(v[0] for v in xs)-position_error_m,
            max(v[1] for v in xs)+position_error_m,
            min(v[0] for v in ys)-position_error_m,
            max(v[1] for v in ys)+position_error_m)


def _body_rectangle(pose, bounds):
    left, right, bottom, top = bounds
    c, s = math.cos(pose[2]), math.sin(pose[2])
    return affine_transform(box(left, bottom, right, top),
                            [c, -s, s, c, pose[0], pose[1]])


def _region(mask, offset_row=0, offset_col=0):
    """Union exact row runs, without filling holes or disconnected cells."""
    edges = np.diff(np.pad(mask.astype(np.int8), ((0, 0), (1, 1))), axis=1)
    rows, starts = np.nonzero(edges == 1)
    end_rows, ends = np.nonzero(edges == -1)
    assert np.array_equal(rows, end_rows)
    return unary_union([box(c0+offset_col, r+offset_row,
                            c1+offset_col, r+1+offset_row)
                        for r, c0, c1 in zip(rows, starts, ends)])


def check_straight_start(*, occupancy, resolution_m, origin, scope_vertices,
                         pose, distance_m, position_error_m, heading_error_rad,
                         initial_unknown, bounds=PADDED_BOUNDS,
                         free_max_value=0):
    """Check a bounded forward sweep on one immutable, already bound snapshot.

    ``initial_unknown`` is the caller's fixed initial inventory, not permission
    to recapture unknown on later maps. Even true cells excuse only their exact
    overlap with the initial padded body, NEVER an entire boundary cell or the
    added tracking envelope. Current occupied cells are never exempt.

    Raw maps require free_max_value=0; a costmap may explicitly allow its
    declared inflation threshold. Both rasters must independently pass. This
    geometry-only candidate accepts no curve, reverse motion, or map update.
    The caller must retain current source, TF, frame, scope and ledger binding.
    """
    occupancy = np.asarray(occupancy)
    initial_unknown = np.asarray(initial_unknown)
    if (occupancy.ndim != 2 or not occupancy.size or occupancy.size > 1000000
            or not np.issubdtype(occupancy.dtype, np.integer)
            or np.any((occupancy < -1) | (occupancy > 100))
            or initial_unknown.shape != occupancy.shape
            or initial_unknown.dtype != np.dtype(bool)):
        raise ValueError('straight_sweep_invalid_raster')
    if (len(origin) != 3 or len(pose) != 3
            or not all(math.isfinite(v) for v in (*origin, *pose,
                                                resolution_m, distance_m))
            or not 0 < resolution_m <= 1. or not 0 <= distance_m <= .5
            or isinstance(free_max_value, bool)
            or not isinstance(free_max_value, int)
            or not 0 <= free_max_value < 100):
        raise ValueError('straight_sweep_invalid_geometry')
    vertices = np.asarray(scope_vertices, dtype=float)
    if (vertices.ndim != 2 or vertices.shape[1] != 2 or len(vertices) < 3
            or not np.all(np.isfinite(vertices))):
        raise ValueError('straight_sweep_invalid_scope')
    scope = Polygon(vertices)
    if not scope.is_valid or scope.is_empty or scope.area <= 0:
        raise ValueError('straight_sweep_invalid_scope')
    enclosed = enclosing_bounds(bounds, position_error_m, heading_error_rad)
    # Minkowski sum of a constant envelope with the complete forward segment.
    sweep = _body_rectangle(pose, (enclosed[0], enclosed[1]+distance_m,
                                   enclosed[2], enclosed[3]))
    initial = _body_rectangle(pose, bounds)
    outside_scope = sweep.difference(scope).area
    # World -> grid affine transform; map rotations do not rotate the robot
    # twice and cell edges, rather than cell centres, remain authoritative.
    c, s = math.cos(origin[2]), math.sin(origin[2])
    transform = [c/resolution_m, s/resolution_m, -s/resolution_m, c/resolution_m,
                 (-c*origin[0]-s*origin[1])/resolution_m,
                 (s*origin[0]-c*origin[1])/resolution_m]
    grid_sweep = affine_transform(sweep, transform)
    grid_initial = affine_transform(initial, transform)
    height, width = occupancy.shape
    outside_grid = grid_sweep.difference(box(0, 0, width, height)).area*resolution_m**2
    x0, y0, x1, y1 = grid_sweep.bounds
    c0, c1 = max(0, min(width, math.floor(x0))), max(0, min(width, math.ceil(x1)))
    r0, r1 = max(0, min(height, math.floor(y0))), max(0, min(height, math.ceil(y1)))
    values = occupancy[r0:r1, c0:c1]
    unknown = _region(values < 0, r0, c0)
    occupied = _region(values > free_max_value, r0, c0)
    retained = _region(initial_unknown[r0:r1, c0:c1] & (values < 0), r0, c0)
    excused = retained.intersection(grid_initial)
    occupied_area = grid_sweep.intersection(occupied).area*resolution_m**2
    unknown_area = grid_sweep.intersection(unknown).difference(excused).area*resolution_m**2
    # Floating arithmetic tolerance (1e-12 m²), not a cell/clearance allowance.
    reason = next((name for name, area in (
        ('straight_sweep_outside_scope', outside_scope),
        ('straight_sweep_outside_grid', outside_grid),
        ('straight_sweep_occupied', occupied_area),
        ('straight_sweep_new_unknown', unknown_area)) if area > 1e-12), '')
    return StartSweepResult(not reason, reason, outside_scope, outside_grid,
                            occupied_area, unknown_area, excused.area*resolution_m**2)
