"""Finite, occluding sensor/plant model; never publishes a map or truth TF.

World geometry is available to sensors and the independent oracle only. The
product receives range returns and encoder/gyro registers, not waypoints.
"""
import math
import numpy as np


def rectangle(x0, x1, y0, y1):
    return np.array([(x0, y0), (x1, y0), (x1, y1), (x0, y1)])


def chassis(pose):
    x, y, yaw = pose
    c, s = math.cos(yaw), math.sin(yaw)
    return np.array([(x+c*a-s*b, y+s*a+c*b)
                     for a, b in ((-.13, -.25), (.33, -.25), (.33, .25), (-.13, .25))])


def polygon_distance(a, b):
    """Separating axes plus exact edge distances, independent of Nav2."""
    separated = False
    for poly in (a, b):
        for edge in np.roll(poly, -1, axis=0)-poly:
            axis = np.array([-edge[1], edge[0]])
            pa, pb = a@axis, b@axis
            separated |= bool(pa.max() < pb.min() or pb.max() < pa.min())
    if not separated:
        return 0.
    distance = math.inf
    for vertices, edges in ((a, b), (b, a)):
        for start, end in zip(edges, np.roll(edges, -1, axis=0)):
            v = end-start
            f = np.clip((vertices-start)@v/(v@v), 0., 1.)
            distance = min(distance, float(np.linalg.norm(vertices-start-f[:, None]*v, axis=1).min()))
    return distance


def chassis_clearance(pose, obstacles):
    """Vectorized independent rectangle SAT/edge oracle for 100-Hz sampling."""
    body, objects = chassis(pose), np.asarray(obstacles)
    c, s = math.cos(pose[2]), math.sin(pose[2])
    axes = np.array([(1., 0.), (0., 1.), (c, s), (-s, c)])
    a, b = body@axes.T, objects@axes.T
    separated = ((b.max(axis=1) < a.min(axis=0)) | (a.max(axis=0) < b.min(axis=1))).any(axis=1)
    distances = np.full(len(objects), math.inf)
    for points, edges in ((np.broadcast_to(body, objects.shape), objects),
                          (objects, np.broadcast_to(body, objects.shape))):
        start, vector = edges, np.roll(edges, -1, axis=1)-edges
        delta = points[:, None, :, :]-start[:, :, None, :]
        fraction = np.clip((delta*vector[:, :, None, :]).sum(axis=-1)/
                           (vector*vector).sum(axis=-1)[:, :, None], 0., 1.)
        distance = np.linalg.norm(delta-fraction[..., None]*vector[:, :, None, :], axis=-1).min(axis=(1, 2))
        distances = np.minimum(distances, distance)
    return float(np.where(separated, distances, 0.).min())


class World:
    def __init__(self, door_m, start):
        if door_m not in (.68, .80):
            raise ValueError('undeclared door')
        self.start = np.asarray(start, dtype=float)
        self.pose = self.start.copy()
        self.velocity = np.zeros(2)
        self.motor_positions = np.zeros(2)
        self.obstacles = [
            rectangle(-2.85, -2.8, -1.45, 1.45), rectangle(2.8, 2.85, -1.45, 1.45),
            rectangle(-2.85, -.6, -1.45, -1.4), rectangle(-2.85, -.6, 1.4, 1.45),
            rectangle(.6, 2.85, -1.45, -1.4), rectangle(.6, 2.85, 1.4, 1.45),
            rectangle(-.64, -.56, -1.4, -door_m/2), rectangle(-.64, -.56, door_m/2, 1.4),
            rectangle(.56, .64, -1.4, -door_m/2), rectangle(.56, .64, door_m/2, 1.4),
            rectangle(-.6, .6, -.47, -.42), rectangle(-.6, .6, .42, .47),
            # Island requires a detour; the upper alternative is visibly blocked.
            rectangle(1.55, 1.8, -.30, .30), rectangle(1.55, 1.8, .72, 1.4)]
        self.minimum_clearance = math.inf
        self.collision = False
        self.travel = 0.
        self.rear_cleared = False
        self.checked_pose = None

    def local(self, points):
        """Authorized scope coordinates, not a reference map."""
        p = np.asarray(points)-self.start[:2]
        c, s = math.cos(self.start[2]), math.sin(self.start[2])
        return p@np.array([[c, -s], [s, c]])

    def integrate(self, command, dt, tau=.05):
        if not 0. < dt <= .03:
            raise ValueError('missed plant tick must be recorded, not extrapolated')
        if (not np.any(command) and not np.any(self.velocity)
                and self.checked_pose == tuple(self.pose)):
            return  # exact stationary solution; retain already checked geometry
        self.velocity += (np.asarray(command)-self.velocity)*(1-math.exp(-dt/tau))
        v, w = self.velocity
        x, y, yaw = self.pose
        if abs(w) > 1e-9:
            x += v/w*(math.sin(yaw+w*dt)-math.sin(yaw))
            y -= v/w*(math.cos(yaw+w*dt)-math.cos(yaw))
        else:
            x += v*dt*math.cos(yaw)
            y += v*dt*math.sin(yaw)
        self.pose[:] = x, y, math.atan2(math.sin(yaw+w*dt), math.cos(yaw+w*dt))
        self.travel += abs(v)*dt
        # Integer counters represent measured plant rotation, including ramp/tail.
        self.motor_positions += np.array([v-w*.3845/2, -(v+w*.3845/2)])*dt/(2*math.pi*.0624)*10000
        # The declared obstacles are static. Reuse only an exactly identical
        # pose's geometry; still integrate every nonzero velocity/counter tail.
        pose = tuple(self.pose)
        if pose != self.checked_pose:
            self.minimum_clearance = min(self.minimum_clearance,
                chassis_clearance(self.pose, self.obstacles))
            self.collision |= self.minimum_clearance <= 0.
            self.rear_cleared |= bool(chassis(self.pose)[:, 0].min() > .64)
            self.checked_pose = pose

    def raycast(self, origin, angles, maximum=10.):
        """First finite return; occupied edges occlude all further geometry."""
        directions = np.array([np.cos(angles), np.sin(angles)]).T
        result = np.full(len(directions), maximum)
        origin = np.asarray(origin)
        for obstacle in self.obstacles:
            low, high = obstacle.min(axis=0), obstacle.max(axis=0)
            with np.errstate(divide='ignore', invalid='ignore'):
                t0, t1 = (low-origin)/directions, (high-origin)/directions
            parallel = abs(directions) < 1e-12
            outside = ((origin < low) | (origin > high)) & parallel
            lower = np.where(parallel, -np.inf, np.minimum(t0, t1)).max(axis=1)
            upper = np.where(parallel, np.inf, np.maximum(t0, t1)).min(axis=1)
            hit = (upper >= np.maximum(0., lower)) & ~outside.any(axis=1)
            result = np.minimum(result, np.where(hit, np.maximum(0., lower), maximum))
        return result

    def laser(self, beams=720, mask=True):
        yaw = self.pose[2]
        origin = self.pose[:2]+np.array([math.cos(yaw), math.sin(yaw)])*.245
        angles = np.arange(beams)*2*math.pi/beams
        ranges = self.raycast(origin, angles+yaw+math.pi/2)
        if mask:
            # stl27l.yaml: clockwise native 236..304 becomes ROS 56..124;
            # +90-degree mount places this occlusion behind the chassis.
            ranges[(angles >= math.radians(56)) & (angles <= math.radians(124))] = np.nan
        return angles, ranges

    def cone_returns(self, mount, directions, maximum=4.):
        """Finite 3-D first returns from extruded walls, floor and ceiling.

        The 2-D obstacles extend from base-frame floor -0.09 to ceiling 3 m.
        Directions/mount are in base coordinates; no geometry is published.
        No return inside the sensor range is NaN, never a clearing endpoint.
        """
        directions = np.asarray(directions, dtype=float)
        horizontal = np.linalg.norm(directions[:, :2], axis=1)
        yaw = self.pose[2]
        c, s = math.cos(yaw), math.sin(yaw)
        origin = self.pose[:2]+np.array([c*mount[0]-s*mount[1], s*mount[0]+c*mount[1]])
        distances = self.raycast(origin, np.arctan2(directions[:, 1], directions[:, 0])+yaw,
                                 maximum=100.)/horizontal
        z = mount[2]+distances*directions[:, 2]
        distances[(z < -.09) | (z > 3.)] = np.inf
        for height in (-.09, 3.):
            with np.errstate(divide='ignore', invalid='ignore'):
                plane = (height-mount[2])/directions[:, 2]
            distances = np.minimum(distances, np.where(plane > 0., plane, np.inf))
        return np.where(distances <= maximum, distances, np.nan)

    def map_oracle(self, occupancy, resolution, origin):
        """Compare SLAM cells to physical reference, independent of free count.

        Inputs are output observations only. Reference data are never supplied
        to an exploration callback. Map frame starts at the declared base pose.
        """
        a = np.asarray(occupancy)
        ys, xs = np.mgrid[-1.4:1.4:resolution, -2.8:2.8:resolution]
        reference = np.stack((xs.ravel()+resolution/2, ys.ravel()+resolution/2), axis=1)
        accessible = ((reference[:, 0] < -.6) | (reference[:, 0] > .6) | (abs(reference[:, 1]) < .42))
        for o in self.obstacles:
            accessible &= ~((reference >= o.min(axis=0)).all(axis=1) & (reference <= o.max(axis=0)).all(axis=1))
        reference = reference[accessible]
        indices = np.floor((self.local(reference)-np.asarray(origin))/resolution).astype(int)
        in_grid = (indices[:, 0] >= 0) & (indices[:, 0] < a.shape[1]) & (indices[:, 1] >= 0) & (indices[:, 1] < a.shape[0])
        observed = np.zeros(len(reference), dtype=bool)
        observed[in_grid] = a[indices[in_grid, 1], indices[in_grid, 0]] == 0
        row, col = np.nonzero(a >= 65)
        local = np.stack((origin[0]+(col+.5)*resolution, origin[1]+(row+.5)*resolution), axis=1)
        c, s = math.cos(self.start[2]), math.sin(self.start[2])
        points = local@np.array([[c, s], [-s, c]])+self.start[:2]
        distance = np.full(len(points), math.inf)
        for o in self.obstacles:
            for start, end in zip(o, np.roll(o, -1, axis=0)):
                v = end-start
                f = np.clip((points-start)@v/(v@v), 0., 1.)
                distance = np.minimum(distance, np.linalg.norm(points-start-f[:, None]*v, axis=1))
        return {'reference_free_cells': len(reference), 'reference_observed_cells': int(observed.sum()),
                'reference_observed_fraction': float(observed.mean()),
                'maximum_occupied_wall_error_m': float(distance.max()) if len(distance) else None}
