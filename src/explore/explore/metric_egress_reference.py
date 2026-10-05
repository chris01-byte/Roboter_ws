"""Project the first escape inventory; never recapture it on a SLAM update.

The capture raster is immutable in odometry space. Current unknown cells must
be wholly covered by its retained cells. Observations retire intersecting
capture cells conservatively, so resampling cannot resurrect an exemption.
"""
import copy
import math
import numpy as np

from .metric_frontier import StartEgressEvidence, _cell_intersections


def transform_poses(poses, source, target):
    """source/target are planar map->odom transforms at the pose's TF time."""
    poses = np.asarray(poses, dtype=float)
    angle = target[2] - source[2]
    dx, dy = poses[:, 0] - source[0], poses[:, 1] - source[1]
    ox = math.cos(source[2])*dx + math.sin(source[2])*dy
    oy = -math.sin(source[2])*dx + math.cos(source[2])*dy
    return np.column_stack((target[0] + math.cos(target[2])*ox - math.sin(target[2])*oy,
        target[1] + math.sin(target[2])*ox + math.cos(target[2])*oy, poses[:, 2] + angle))


def grid_points(points, source_grid, source_reference, target_grid, target_reference):
    """Continuous cell corners, with no rounding of the physical inventory."""
    points = np.asarray(points, dtype=float)
    o = source_grid.info.origin
    q = o.orientation
    yaw = math.atan2(2*q.w*q.z, 1-2*q.z*q.z)
    x, y = points[:, 0]*source_grid.info.resolution, points[:, 1]*source_grid.info.resolution
    world = np.column_stack((o.position.x + math.cos(yaw)*x - math.sin(yaw)*y,
        o.position.y + math.sin(yaw)*x + math.cos(yaw)*y, np.zeros(len(points))))
    world = transform_poses(world, source_reference, target_reference)
    o = target_grid.info.origin
    q = o.orientation
    yaw = math.atan2(2*q.w*q.z, 1-2*q.z*q.z)
    dx, dy = world[:, 0]-o.position.x, world[:, 1]-o.position.y
    return np.column_stack(((math.cos(yaw)*dx + math.sin(yaw)*dy)/target_grid.info.resolution,
        (-math.sin(yaw)*dx + math.cos(yaw)*dy)/target_grid.info.resolution))


def intersecting_cells(polygon, shape):
    # Tiny floating-point edge noise is not an additional raster allowance.
    low = np.floor(np.min(polygon, axis=0)+1e-9).astype(int)
    high = np.ceil(np.max(polygon, axis=0)-1e-9).astype(int)
    if low[0] < 0 or low[1] < 0 or high[0] > shape[1] or high[1] > shape[0]:
        return None
    rr, cc = np.meshgrid(np.arange(low[1], high[1]), np.arange(low[0], high[0]), indexing='ij')
    cells = np.column_stack((rr.ravel(), cc.ravel()))
    if not len(cells):
        return cells
    areas = _cell_intersections(np.asarray(polygon), cells)[0]
    return cells[areas > 1e-9]


def square(row, col):
    return ((col, row), (col+1, row), (col+1, row+1), (col, row+1))


class ReferencedStartEgress:
    """Current raster view of a fixed first inventory and its monotone history."""
    def __init__(self, evidence, reference):
        self.fixed = evidence
        self.fixed.grid = copy.deepcopy(evidence.grid)
        self.reference = tuple(reference)
        self.current_reference = self.reference
        self.grid = evidence.grid
        self.unknown = evidence.unknown.copy()
        self.scope_mask = evidence.scope_mask.copy()
        self.generation = 0
        self._projection_key = None

    @property
    def valid(self):
        return self.fixed.valid

    @valid.setter
    def valid(self, value):
        self.fixed.valid = value

    @property
    def reason(self):
        return self.fixed.reason

    @reason.setter
    def reason(self, value):
        self.fixed.reason = value

    @property
    def pose(self):
        return self.fixed.pose

    @property
    def bounds(self):
        return self.fixed.bounds

    @property
    def initial_polygon(self):
        return self.fixed.initial_polygon

    @property
    def remaining_area(self):
        return self.fixed.remaining_area

    @property
    def departed_distance(self):
        return self.fixed.departed_distance

    def refresh(self, grid, occupancy, inside, reference):
        self.grid, self.current_reference = grid, tuple(reference)
        self.scope_mask = inside.copy()
        if not self.valid:
            self.unknown = np.zeros_like(inside)
            return
        o = grid.info.origin
        key = (grid.header.frame_id, grid.info.resolution, occupancy.shape,
            o.position.x, o.position.y, o.orientation.z, o.orientation.w,
            tuple(reference), occupancy.tobytes(), inside.tobytes(), self.fixed.unknown.tobytes())
        if key == self._projection_key:
            return  # geometry only; pose/health/monotone commit are still checked
        retained = self.fixed.unknown
        axes = grid_points(((0.,0.),(1.,0.),(0.,1.)), grid, self.current_reference,
                           self.fixed.grid, self.reference)
        offset = np.rint(axes[0]).astype(int)
        aligned = (np.max(np.abs(axes[0]-offset)) <= 1e-9
            and np.max(np.abs(axes[1:]-axes[0]-np.eye(2))) <= 1e-9)
        if aligned:
            # Exact physical lattice: integer index translation, not nearest
            # neighbour resampling. Width/origin growth does not move cells.
            dc, dr = offset
            r0, c0 = max(0,-dr), max(0,-dc)
            r1, c1 = min(occupancy.shape[0],retained.shape[0]-dr), min(occupancy.shape[1],retained.shape[1]-dc)
            projected = np.zeros_like(inside)
            remaining = np.zeros_like(retained)
            if r1 > r0 and c1 > c0:
                source = (slice(r0+dr,r1+dr),slice(c0+dc,c1+dc))
                target = (slice(r0,r1),slice(c0,c1))
                remaining[source] = retained[source] & (occupancy[target] < 0)
                projected[target] = remaining[source] & inside[target]
            self.fixed.unknown = remaining
            self.unknown = projected
            self.generation += 1
            self._projection_key = (*key[:-1], remaining.tobytes())
            return
        # Any newly observed part retires the entire old cell. This is a
        # conservative loss of authority, never a fresh unknown-space claim.
        for row, col in zip(*np.nonzero(retained)):
            polygon = grid_points(square(row, col), self.fixed.grid, self.reference,
                                  grid, self.current_reference)
            cells = intersecting_cells(polygon, occupancy.shape)
            if cells is None or not len(cells) or np.any(occupancy[cells[:, 0], cells[:, 1]] >= 0):
                retained[row, col] = False
        projected = np.zeros(occupancy.shape, dtype=bool)
        rr, cc = np.nonzero(retained)
        if len(rr):
            envelope = grid_points(((cc.min(), rr.min()), (cc.max()+1, rr.min()),
                (cc.max()+1, rr.max()+1), (cc.min(), rr.max()+1)), self.fixed.grid,
                self.reference, grid, self.current_reference)
            low = np.maximum(0, np.floor(envelope.min(axis=0)).astype(int))
            high = np.minimum((occupancy.shape[1], occupancy.shape[0]),
                              np.ceil(envelope.max(axis=0)).astype(int))
            for row in range(low[1], high[1]):
                for col in range(low[0], high[0]):
                    if occupancy[row, col] >= 0 or not inside[row, col]:
                        continue
                    polygon = grid_points(square(row, col), grid, self.current_reference,
                                          self.fixed.grid, self.reference)
                    cells = intersecting_cells(polygon, retained.shape)
                    if cells is not None and len(cells) and np.all(retained[cells[:, 0], cells[:, 1]]):
                        projected[row, col] = True
        self.unknown = projected
        self.generation += 1
        self._projection_key = (*key[:-1], retained.tobytes())

    def check_trajectory(self, poses, occupancy, allowed, world_to_grid, commit=False):
        if not self.valid:
            return False, self.reason
        if occupancy.shape != self.unknown.shape or allowed.shape != self.unknown.shape:
            self.valid = False
            self.reason = 'start_egress_raster_mismatch'
            return False, self.reason
        poses = np.asarray(poses, dtype=float)
        if poses.ndim != 2 or poses.shape[1] != 3 or not np.all(np.isfinite(poses)):
            return False, 'start_egress_pose_invalid'
        # Fresh complete contour on both actual rasters. Only the exact
        # projection above can excuse a current unknown cell, never occupancy.
        fresh = StartEgressEvidence(self.grid, self.pose, self.bounds,
            np.zeros_like(self.unknown), (), True, scope_mask=self.scope_mask)
        valid, reason = fresh.check_trajectory(poses, occupancy,
            allowed | (self.unknown & (occupancy < 0)), world_to_grid)
        if not valid:
            return False, reason
        # Areas/distances retain their original keys, polygon, reserves and
        # committed values. A SLAM correction is not physical reverse travel.
        fixed_poses = transform_poses(poses, self.current_reference, self.reference)
        virtual = np.where(self.fixed.unknown, -1, 0)
        return self.fixed.check_trajectory(fixed_poses, virtual, ~self.fixed.unknown,
                                          world_to_grid, commit=commit)
