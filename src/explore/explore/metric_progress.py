"""Measured metric progress and bounded completion, without motion authority."""
from dataclasses import dataclass, field
import hashlib
import math

import numpy as np
from scipy.ndimage import label


def local_evidence(grid, anchor, to_world, radius=.8):
    """Local world-cell content; stamps, UUIDs and distant edits grant no retry."""
    data = np.asarray(grid.data).reshape(grid.info.height, grid.info.width)
    # Bounded local projection also survives integer-cell map expansion.
    q = grid.info.origin.orientation
    yaw = math.atan2(2*(q.w*q.z+q.x*q.y), 1-2*(q.y*q.y+q.z*q.z))
    dx, dy = anchor[0]-grid.info.origin.position.x, anchor[1]-grid.info.origin.position.y
    col = (math.cos(yaw)*dx+math.sin(yaw)*dy)/grid.info.resolution
    row = (-math.sin(yaw)*dx+math.cos(yaw)*dy)/grid.info.resolution
    span = math.ceil(radius/grid.info.resolution)+1
    cells = []
    for r in range(max(0, int(row)-span), min(grid.info.height, int(row)+span+1)):
        for c in range(max(0, int(col)-span), min(grid.info.width, int(col)+span+1)):
            xy = to_world(c, r, grid.info)
            if math.dist(xy, anchor) <= radius:
                cells.append((round(xy[0], 8), round(xy[1], 8), int(data[r, c])))
    return hashlib.sha256(repr(sorted(cells)).encode('ascii')).hexdigest()


def reachable_remainder(grid, inside, pose, to_grid):
    """All raw-free connected boundaries, before size/history/geometry filters.

    Unknown behind a wall has no accessible boundary. A narrow connection or
    tiny frontier still counts; inability to plan it must never imply success.
    """
    data = np.asarray(grid.data).reshape(grid.info.height, grid.info.width)
    c, r = to_grid(*pose[:2], grid.info)
    free = (data == 0) & inside
    if not (0 <= r < data.shape[0] and 0 <= c < data.shape[1] and free[r, c]):
        raise ValueError('completion_raw_pose_not_observed_free')
    components, _ = label(free)  # four-connected: no diagonal corner shortcut
    reachable = components == components[r, c]
    unknown = (data < 0) & inside
    adjacent = np.zeros(data.shape, bool)
    adjacent[1:] |= unknown[:-1]
    adjacent[:-1] |= unknown[1:]
    adjacent[:, 1:] |= unknown[:, :-1]
    adjacent[:, :-1] |= unknown[:, 1:]
    return int(np.count_nonzero(reachable & adjacent))


def local_small_remainder(grid, inside, pose, anchor, to_grid, to_world,
                          min_frontier_m, radius=.8):
    """Reachable local boundary omitted by the normal component-size filter.

    Resolving one proposed ray does not finish a spatial task when its actual
    remaining boundary has merely become too small for ordinary sampling.
    Connectivity is proved on the whole raw-free scope, not a cropped disk;
    walls and disconnected islands cannot create an unfinished task here.
    This is work accounting only, never a chassis or motion permission.
    Return None if raw-free connectivity cannot yet be established (including
    private start egress). The caller must retain the task as unfinished.
    """
    data = np.asarray(grid.data).reshape(grid.info.height, grid.info.width)
    free = (data == 0) & inside
    c, r = to_grid(*pose[:2], grid.info)
    if not (0 <= r < data.shape[0] and 0 <= c < data.shape[1] and free[r, c]):
        return None
    connected, _ = label(free)
    unknown = (data < 0) & inside
    adjacent = np.zeros(data.shape, bool)
    adjacent[1:] |= unknown[:-1]
    adjacent[:-1] |= unknown[1:]
    adjacent[:, 1:] |= unknown[:, :-1]
    adjacent[:, :-1] |= unknown[:, 1:]
    components, _ = label(free & adjacent, np.ones((3, 3), int))
    sizes = np.bincount(components.ravel())
    minimum = max(1, round(min_frontier_m / grid.info.resolution))
    omitted = ((components > 0) & (sizes[components] < minimum)
               & (connected == connected[r, c]))
    return sum(math.dist(to_world(int(c), int(r), grid.info), anchor) <= radius
               for r, c in np.argwhere(omitted))


@dataclass
class CompletionWindow:
    duration_s: float = 3.
    minimum_scans: int = 3
    started: float = None
    last_scan: int = None
    samples: int = 0
    context: object = None
    last_time: float = None

    def observe(self, *, now, scan_stamp, context, clear):
        if (not clear or (self.context is not None and self.context != context) or
                (self.last_time is not None and now-self.last_time > .5)):
            self.started, self.last_scan, self.samples = None, None, 0
        self.context = context
        self.last_time = now
        if not clear:
            return False
        if scan_stamp <= 0 or (self.last_scan is not None and scan_stamp <= self.last_scan):
            return False
        if self.started is None:
            self.started = now
        self.last_scan = scan_stamp
        self.samples += 1
        return now-self.started >= self.duration_s and self.samples >= self.minimum_scans


@dataclass(frozen=True)
class ObservationBaseline:
    context: object
    source_stamp: int
    scan_stamp: int
    resolution: float
    grid_yaw: float
    points: tuple


def observation_complete(baseline, grid, correlation, to_grid, to_world):
    """All original finite points resolved, never a new-gain receipt.

    A few genuine new cells are progress without necessarily finishing the
    selected view. Unknown, cropped or fractionally regridded points remain
    unresolved; a newer occupied cell is resolved evidence too.
    """
    q = grid.info.origin.orientation
    yaw = math.atan2(2*(q.w*q.z+q.x*q.y), 1-2*(q.y*q.y+q.z*q.z))
    if (not baseline.points or correlation.context != baseline.context or
            correlation.source_stamp_ns <= baseline.source_stamp or
            grid.info.resolution != baseline.resolution or
            abs(math.atan2(math.sin(yaw-baseline.grid_yaw),math.cos(yaw-baseline.grid_yaw)))>1e-8):
        return False
    data = np.asarray(grid.data).reshape(grid.info.height,grid.info.width)
    for xy in baseline.points:
        col,row = to_grid(*xy,grid.info)
        if (not (0<=row<data.shape[0] and 0<=col<data.shape[1]) or
                data[row,col]<0 or math.dist(xy,to_world(col,row,grid.info))>1e-7):
            return False
    return True


def measured_gain(baseline, grid, correlation, pose, scan, mount, to_grid, to_world, maximum_range_m=4.):
    """Unknown-to-observed change, seen by a newer finite actual LiDAR ray.

    Counts only aligned world cells and unobstructed, in-range current rays.
    A growing free-cell count, a changed fingerprint or arrival alone is not
    evidence. The caller verifies source/pose/scan freshness before this call.
    """
    stamp = scan['key'][0]*10**9 + scan['key'][1]
    q = grid.info.origin.orientation
    yaw = math.atan2(2*(q.w*q.z+q.x*q.y), 1-2*(q.y*q.y+q.z*q.z))
    if (correlation.context != baseline.context or
            correlation.source_stamp_ns <= baseline.source_stamp or
            stamp <= baseline.scan_stamp or grid.info.resolution != baseline.resolution or
            abs(math.atan2(math.sin(yaw-baseline.grid_yaw), math.cos(yaw-baseline.grid_yaw))) > 1e-8):
        return frozenset()
    data = np.asarray(grid.data).reshape(grid.info.height, grid.info.width)
    cp, sp = math.cos(pose[2]), math.sin(pose[2])
    origin = (pose[0]+cp*mount[0]-sp*mount[1], pose[1]+sp*mount[0]+cp*mount[1])
    ranges = np.asarray(scan['ranges'])
    gain = set()
    for xy in baseline.points:
        col, row = to_grid(*xy, grid.info)
        if not (0 <= row < data.shape[0] and 0 <= col < data.shape[1]):
            continue
        if data[row, col] < 0 or math.dist(xy, to_world(col, row, grid.info)) > 1e-7:
            continue  # fractional SLAM regridding is not a cell observation
        distance = math.dist(origin, xy)
        if distance > min(maximum_range_m, scan['range_max']):
            continue
        angle = math.atan2(xy[1]-origin[1], xy[0]-origin[0])-pose[2]-mount[2]
        # Full-circle and limited-sector scans both retain their real bins.
        candidates = [round((angle+turn*2*math.pi-scan['angle_min'])/scan['angle_increment'])
                      for turn in (-1, 0, 1)]
        bins = [i for i in candidates if 0 <= i < len(ranges)]
        if not any(math.isfinite(ranges[i]) and ranges[i] > 0 and
                   scan['range_min'] <= ranges[i] <= scan['range_max'] and
                   scan['range_min'] <= distance <= ranges[i]+grid.info.resolution/2 and
                   (data[row, col] == 0 or abs(distance-ranges[i]) <= grid.info.resolution/2) and
                   abs(angle+round((scan['angle_min']+i*scan['angle_increment']-angle)/(2*math.pi))*2*math.pi-
                       (scan['angle_min']+i*scan['angle_increment']))*max(distance, grid.info.resolution) <= grid.info.resolution/2
                   for i in bins):
            continue
        # Supercover: endpoints and both side cells at every diagonal crossing.
        previous = None
        clear = True
        for t in np.linspace(0, 1, max(2, math.ceil(distance/(grid.info.resolution/2))+1)):
            c, r = to_grid(origin[0]+t*(xy[0]-origin[0]), origin[1]+t*(xy[1]-origin[1]), grid.info)
            cells = [(r, c)]
            if previous is not None and previous[0] != r and previous[1] != c:
                cells += [(previous[0], c), (r, previous[1])]
            if any(not (0 <= rr < data.shape[0] and 0 <= cc < data.shape[1]) or
                   ((rr, cc) != (row, col) and data[rr, cc] != 0) for rr, cc in cells):
                clear = False
                break
            previous = (r, c)
        if clear:
            gain.add(xy)
    return frozenset(gain)
