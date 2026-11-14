"""Frozen all-distance first-hit rule from 4def089; parity oracle only."""
import math
import numpy as np

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
