"""Stateless boundary proposals and first-hit LiDAR visibility, no task policy.

A component centroid need not lie on its boundary. Keep actual free boundary
cells instead, with spatially separated samples of long/concave components.
The caller still proves the complete chassis route on raw map and costmap.
"""
from dataclasses import dataclass
import math
import numpy as np
from scipy.ndimage import label, find_objects


@dataclass(frozen=True)
class BoundarySample:
    xy: tuple
    size: int
    inward: tuple


def boundary_samples(grid, scope_mask, to_world, min_frontier_m,
                     spacing_m=.8, limit=128):
    data = np.asarray(grid.data).reshape(grid.info.height, grid.info.width)
    unknown = data < 0
    adjacent = np.zeros(data.shape, bool)
    adjacent[1:] |= unknown[:-1]
    adjacent[:-1] |= unknown[1:]
    adjacent[:, 1:] |= unknown[:, :-1]
    adjacent[:, :-1] |= unknown[:, 1:]
    # Scope never changes unknown into free. Only anchors inside it are used.
    boundary = (data == 0) & adjacent & scope_mask
    components, _ = label(boundary, np.ones((3, 3), int))
    minimum = max(1, round(min_frontier_m / grid.info.resolution))
    samples = []
    for component, bounds in enumerate(find_objects(components), 1):
        cells = np.argwhere(components[bounds] == component)
        cells += (bounds[0].start, bounds[1].start)
        if len(cells) < minimum:
            continue
        groups = {}
        for row, col in cells:
            tile = (int(row * grid.info.resolution / spacing_m),
                    int(col * grid.info.resolution / spacing_m))
            groups.setdefault(tile, []).append((int(row), int(col)))
        for tile, points in sorted(groups.items()):
            center = ((tile[0]+.5)*spacing_m/grid.info.resolution,
                      (tile[1]+.5)*spacing_m/grid.info.resolution)
            row, col = min(points, key=lambda p: (math.dist(p, center), p))
            samples.append(BoundarySample(to_world(col, row, grid.info), len(points),
                                          boundary_inward(grid, row, col, data=data)))
            if len(samples) > limit:
                raise ValueError('frontier_candidate_capacity_exhausted')
    # Fail closed, explicitly: truncation cannot silently erase remaining work.
    return samples


def boundary_inward(grid, row, col, *, data=None):
    """World normal toward observed free space, for free OR unknown anchors."""
    if data is None:
        data = np.asarray(grid.data).reshape(grid.info.height, grid.info.width)
    dx = dy = 0.
    unknown_anchor = data[row, col] < 0
    for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        r, c = row+dr, col+dc
        if 0 <= r < data.shape[0] and 0 <= c < data.shape[1]:
            if unknown_anchor and data[r, c] == 0:
                dx += dc; dy += dr
            elif not unknown_anchor and data[r, c] < 0:
                dx -= dc; dy -= dr
    norm = math.hypot(dx, dy)
    if norm == 0:
        return None
    q = grid.info.origin.orientation
    yaw = math.atan2(2*(q.w*q.z+q.x*q.y),1-2*(q.y*q.y+q.z*q.z))
    return ((math.cos(yaw)*dx-math.sin(yaw)*dy)/norm,
            (math.sin(yaw)*dx+math.cos(yaw)*dy)/norm)


@dataclass(frozen=True)
class LidarView:
    mount: tuple
    angles: np.ndarray
    range_m: float
    minimum_range_m: float = 0.


def lidar_view(scan, mount, now, timeout, maximum_range_m):
    if (scan is None or mount is None
            or not 0 <= now-scan['received_at'] <= timeout):
        raise ValueError('candidate_lidar_missing_stale_or_tf_missing')
    values = (*mount, scan['angle_min'], scan['angle_increment'],
              scan['range_min'], scan['range_max'], maximum_range_m)
    ranges = np.asarray(scan['ranges'])
    if (not all(math.isfinite(v) for v in values) or not len(ranges)
            or len(ranges) > 4096 or scan['angle_increment'] == 0
            or not 0 <= scan['range_min'] < scan['range_max']
            or maximum_range_m <= 0):
        raise ValueError('candidate_lidar_geometry_invalid')
    # NaN/zero/masked/out-of-range bins grant no sight, including the mast.
    valid = (np.isfinite(ranges) & (ranges >= scan['range_min'])
             & (ranges <= scan['range_max']) & (ranges > 0))
    if not np.any(valid):
        raise ValueError('candidate_lidar_no_valid_rays')
    angles = scan['angle_min'] + np.nonzero(valid)[0]*scan['angle_increment']
    return LidarView(tuple(mount), angles, min(scan['range_max'], maximum_range_m), scan['range_min'])


def visible_boundary_cells(grid, scope_mask, pose, view):
    """Potential first unknown hits, bounded by measured sight and known walls.

    Unknown terminates a ray; cells beyond it are never credited. Half-cell
    steps with the neighbouring cell at diagonal crossings prevent corner
    peeking. This predicts opportunity; it is not an observed-gain receipt.
    """
    info = grid.info
    data = np.asarray(grid.data).reshape(info.height, info.width)
    q = info.origin.orientation
    origin_yaw = math.atan2(2*(q.w*q.z+q.x*q.y), 1-2*(q.y*q.y+q.z*q.z))
    c, s = math.cos(pose[2]), math.sin(pose[2])
    x = pose[0]+c*view.mount[0]-s*view.mount[1]
    y = pose[1]+s*view.mount[0]+c*view.mount[1]
    co, si = math.cos(origin_yaw), math.sin(origin_yaw)
    dx, dy = x-info.origin.position.x, y-info.origin.position.y
    x, y = co*dx+si*dy, -si*dx+co*dy
    if (2*view.range_m/info.resolution > 8192
            or len(view.angles)*(math.ceil(2*view.range_m/info.resolution)+1) > 2000000):
        raise ValueError('candidate_visibility_capacity_exhausted')
    distances = np.arange(0, view.range_m+1e-9, info.resolution/2)
    angles = view.angles+pose[2]+view.mount[2]-origin_yaw
    cols = np.floor((x+np.cos(angles[:, None])*distances)/info.resolution).astype(int)
    rows = np.floor((y+np.sin(angles[:, None])*distances)/info.resolution).astype(int)
    inside = (rows >= 0) & (rows < info.height) & (cols >= 0) & (cols < info.width)
    rr, cc = np.clip(rows, 0, info.height-1), np.clip(cols, 0, info.width-1)
    permitted = inside & scope_mask[rr, cc]
    costs = data[rr, cc]
    stopped = ~permitted | (costs != 0)
    # A diagonal cell transition crosses both side cells; either blocked side
    # ends sight. Include unknown sides conservatively as a stop, without gain.
    diagonal = (rows[:, 1:] != rows[:, :-1]) & (cols[:, 1:] != cols[:, :-1])
    side_clear = ((data[rr[:, :-1], cc[:, 1:]] == 0)
                  & (data[rr[:, 1:], cc[:, :-1]] == 0)
                  & scope_mask[rr[:, :-1], cc[:, 1:]]
                  & scope_mask[rr[:, 1:], cc[:, :-1]])
    stopped[:, 1:] |= diagonal & ~side_clear
    first = np.argmax(stopped, axis=1)
    rays = np.arange(len(angles))
    hits = (np.any(stopped, axis=1) & permitted[rays, first] & (costs[rays, first] < 0)
            & (costs[:, 0] == 0) & (distances[first] >= view.minimum_range_m))
    # Side-cell occlusion has no visible diagonal unknown endpoint.
    hits &= ~(np.pad(diagonal & ~side_clear, ((0, 0), (1, 0)))[rays, first])
    return frozenset(zip(rows[rays[hits], first[hits]].tolist(),
                         cols[rays[hits], first[hits]].tolist()))
