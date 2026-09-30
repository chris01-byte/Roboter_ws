"""Metric task policy: no regions, portals, ROS clients or movement authority.

Uses the existing frontier clusters/approach generator supplied by ExploreNode.
Routes are conservative raw-map geodesics intersected with the live costmap,
then checked with the measured asymmetric padded chassis (including turns).
"""
from dataclasses import dataclass, field
import math
import numpy as np
from scipy.ndimage import distance_transform_edt

from .exploration_scope import rasterize_scope
from .frontier_task_evidence import _geodesic_distances


@dataclass(frozen=True)
class MetricCandidate:
    task_id: str
    x: float
    y: float
    yaw: float
    frontier_xy: tuple
    route: tuple
    route_length_m: float
    cost: float
    fingerprint: str
    revision: int


@dataclass
class MetricAttempt:
    frontier_xy: tuple
    target_xy: tuple
    failures: int = 0
    retry_after: float = 0.0
    fingerprint: str = ''
    completed: bool = False
    reason: str = ''


@dataclass
class MetricTaskPolicy:
    """Bounded spatial history; revision/goal UUID changes never erase a try."""
    radius: float
    cooldown_s: float
    retry_limit: int
    attempts: dict = field(default_factory=dict)
    next_id: int = 0

    def identify(self, frontier_xy):
        matches = [(math.dist(a.frontier_xy, frontier_xy), key)
                   for key, a in self.attempts.items()
                   if math.dist(a.frontier_xy, frontier_xy) < self.radius]
        if matches:
            return min(matches)[1]
        if len(self.attempts) >= 512:
            raise ValueError('metric_task_history_capacity_exhausted')
        self.next_id += 1
        key = f'metric-task-{self.next_id}'
        self.attempts[key] = MetricAttempt(frontier_xy, frontier_xy)
        return key

    def eligible(self, task_id, target_xy, now, fingerprint):
        attempt = self.attempts[task_id]
        # Successful observation neighbourhoods remain served for this mission.
        if any(a.completed and math.dist(a.target_xy, target_xy) < self.radius
               for a in self.attempts.values()):
            return False
        return (not attempt.completed and attempt.failures < self.retry_limit
                and (attempt.failures == 0 or
                     (now >= attempt.retry_after and
                      fingerprint != attempt.fingerprint)))

    def record(self, candidate, outcome, now, fingerprint):
        attempt = self.attempts[candidate.task_id]
        attempt.target_xy = (candidate.x, candidate.y)
        attempt.fingerprint = fingerprint
        attempt.reason = outcome
        if outcome == 'observed':
            attempt.completed = True
        else:
            attempt.failures += 1
            attempt.retry_after = now + self.cooldown_s


def route_cells(mask, start, target):
    """Existing no-corner-cutting distance field, with a descending path."""
    h, w = mask.shape
    if any(not (0 <= r < h and 0 <= c < w) or not mask[r, c]
           for r, c in (start, target)):
        return None
    distances = _geodesic_distances(mask, start)
    if not np.isfinite(distances[target]):
        return None
    route = [target]
    while route[-1] != start:
        r, c = route[-1]
        choices = []
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                nr, nc = r + dr, c + dc
                if (not (dr or dc) or not (0 <= nr < h and 0 <= nc < w)
                        or not mask[nr, nc]):
                    continue
                if dr and dc and (not mask[r, nc] or not mask[nr, c]):
                    continue
                if distances[nr, nc] < distances[r, c] - 1e-9:
                    choices.append((distances[nr, nc] + math.hypot(dr, dc), nr, nc))
        if not choices:
            return None
        _, nr, nc = min(choices)
        route.append((nr, nc))
    return tuple(reversed(route))


def known_safe_mask(occupancy, scope, correlation, origin, yaw, resolution, clearance):
    inside = rasterize_scope(
        scope, context=correlation.context, width=occupancy.shape[1],
        height=occupancy.shape[0], resolution_m=resolution,
        origin_x_m=origin[0], origin_y_m=origin[1], origin_yaw_rad=yaw,
        maximum_cells=1000000)
    known = (occupancy == 0) & inside
    distance = distance_transform_edt(np.pad(known, 1))[1:-1, 1:-1]
    # Include cell-size uncertainty; never seed across an unknown gap.
    safe = known & (distance * resolution >= clearance + resolution / 2)
    return known, safe


def footprint_clear(x, y, yaw, grid, allowed, world_to_grid, grid_to_world,
                    bounds=(-.13, .33, -.25, .25)):
    """Conservative cell-intersection test of the padded measured rectangle.

    Bounds enclose the actual configured footprint. Cell half diagonals and
    route samples supply raster/interpolation reserve; unknown is never free.
    """
    left, right, bottom, top = bounds
    res = grid.info.resolution
    radius = math.hypot(max(abs(left), abs(right)), max(abs(bottom), abs(top)))
    c0, r0 = world_to_grid(x, y, grid.info)
    n = int(math.ceil(radius / res)) + 2
    cosine, sine = math.cos(yaw), math.sin(yaw)
    reserve = res / math.sqrt(2) + .01
    rows, cols = np.mgrid[r0-n:r0+n+1, c0-n:c0+n+1]
    q = grid.info.origin.orientation
    map_yaw = math.atan2(2*(q.w*q.z+q.x*q.y),1-2*(q.y*q.y+q.z*q.z))
    local_x, local_y = (cols+.5)*res, (rows+.5)*res
    dx = grid.info.origin.position.x+math.cos(map_yaw)*local_x-math.sin(map_yaw)*local_y-x
    dy = grid.info.origin.position.y+math.sin(map_yaw)*local_x+math.cos(map_yaw)*local_y-y
    lx, ly = cosine*dx+sine*dy, -sine*dx+cosine*dy
    touched = ((left-reserve<=lx)&(lx<=right+reserve)&
               (bottom-reserve<=ly)&(ly<=top+reserve))
    r, c = rows[touched], cols[touched]
    if np.any((r<0)|(r>=allowed.shape[0])|(c<0)|(c>=allowed.shape[1])):
        return False
    return bool(np.all(allowed[r,c]))



def footprint_route_clear(route, initial_yaw, grids, check):
    """Check translations and all required in-place yaw transitions."""
    yaw = initial_yaw
    for index, point in enumerate(route):
        if index + 1 < len(route):
            nxt = route[index + 1]
            target_yaw = math.atan2(nxt[1]-point[1], nxt[0]-point[0])
            delta = math.atan2(math.sin(target_yaw-yaw), math.cos(target_yaw-yaw))
            for step in range(1 + int(math.ceil(abs(delta)/.05))):
                angle = yaw + delta * step / max(1, math.ceil(abs(delta)/.05))
                if not all(check(*point, angle, grid, allowed) for grid, allowed in grids):
                    return False
            yaw = target_yaw
            length = math.dist(point, nxt)
            n = max(1, math.ceil(length / min(g.info.resolution for g, _ in grids) * 2))
            for k in range(n + 1):
                xy = (point[0]+(nxt[0]-point[0])*k/n, point[1]+(nxt[1]-point[1])*k/n)
                if not all(check(*xy, yaw, grid, allowed) for grid, allowed in grids):
                    return False
        elif not all(check(*point, yaw, grid, allowed) for grid, allowed in grids):
            return False
    return True
