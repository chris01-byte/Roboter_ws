"""Continuous padded chassis coverage for the existing fixed LAB diagnostic.

This is scope coverage, not evidence that an unknown raster cell is free and
not a replacement for the Explorer's map/egress proof. The existing sensor,
gate, collision and hardware protections still own motion authorization.
"""
import math

from shapely.affinity import affine_transform
from shapely.geometry import Polygon, box
from shapely.ops import unary_union

PADDED_BOUNDS = (-.13, .33, -.25, .25)
# Constant-speed upper bound: .8 s pose age + .25 s watchdog + .4 s drive
# brake ramp + .15 s scheduling allowance. Deceleration is not credited.
STOP_HORIZON_S = 1.6


def _extrema(a, b, lo, hi):
    angles = [lo, hi]
    stationary = math.atan2(b, a)
    angles += [stationary+k*math.pi for k in range(
        math.ceil((lo-stationary)/math.pi),
        math.floor((hi-stationary)/math.pi)+1)]
    values = [a*math.cos(t)+b*math.sin(t) for t in angles]
    return min(values), max(values)


def _rotated_bounds(lo, hi):
    corners = [(x, y) for x in PADDED_BOUNDS[:2] for y in PADDED_BOUNDS[2:]]
    xs = [_extrema(x, -y, lo, hi) for x, y in corners]
    ys = [_extrema(y, x, lo, hi) for x, y in corners]
    return min(v[0] for v in xs), max(v[1] for v in xs), min(v[0] for v in ys), max(v[1] for v in ys)


def _world(rectangle, pose):
    c, s = math.cos(pose[2]), math.sin(pose[2])
    return affine_transform(rectangle, [c, -s, s, c, pose[0], pose[1]])


def _covered(geometry, polygon):
    if (len(polygon) < 3 or any(len(p) != 2 or not all(math.isfinite(v) for v in p)
                                for p in polygon)):
        return False
    scope = Polygon(polygon)
    return (scope.is_valid and not scope.is_empty and scope.area > 0
            and geometry.difference(scope).area <= 1e-12)


def stop_sweep_in_scope(pose, vx, wz, polygon, *, observed_motion=False):
    """Enclose all body positions until a constant-speed worst-case stop.

    Translation is enclosed by the extrema of the instantaneous heading;
    these bounds also cover varying speed during deceleration. Both the
    commanded and measured residual velocities must be checked by the caller.
    Commands retain their strict forward/.08/.10 limits. Observed residual
    motion is signed (including encoder quantization during in-place turns)
    and bounded by the existing Base .30/.80 limits. This never authorizes a
    reverse/faster command; the complete measured stop envelope must still fit.
    """
    if (len(pose) != 3 or not all(math.isfinite(v) for v in (*pose, vx, wz))
            or (abs(vx) > .30+1e-9 or abs(wz) > .80+1e-9
                if observed_motion else vx < 0 or vx > .08+1e-9 or abs(wz) > .10+1e-9)):
        return False
    lo, hi = sorted((0., wz*STOP_HORIZON_S))
    rear, front, right, left = _rotated_bounds(lo, hi)
    dx = _extrema(1., 0., lo, hi)
    dy = _extrema(0., 1., lo, hi)
    distance = vx*STOP_HORIZON_S
    xs, ys = (0., distance*dx[0], distance*dx[1]), (0., distance*dy[0], distance*dy[1])
    envelope = box(rear+min(xs), right+min(ys), front+max(xs), left+max(ys))
    return _covered(_world(envelope, pose), polygon)


def fixed_sequence_in_scope(pose, polygon, *, distance=.25):
    """Whole .25 m forward / +15 / -15 sequence, including stop overruns.

    The start contains no hypothetical in-place turn. At the forward endpoint
    the continuous angular enclosure includes the existing 5-degree limit
    and constant-speed stop travel in both directions. No waypoint sampling.
    """
    if (len(pose) != 3 or not all(math.isfinite(v) for v in (*pose, distance))
            or not 0. <= distance <= .25):
        return False
    if (len(polygon) < 3 or any(len(p) != 2 or not all(math.isfinite(v) for v in p)
                                for p in polygon)):
        return False
    scope = Polygon(polygon)
    if not scope.is_valid or scope.is_empty or scope.area <= 0:
        return False
    overrun = .08*STOP_HORIZON_S
    straight = box(-.13, -.25, .33+distance+overrun, .25)
    angle = math.radians(20.)+.10*STOP_HORIZON_S
    if scope.equals(scope.convex_hull):
        # A convex polygon is the intersection of its edge half-planes.
        # Test the exact continuous support of every padded corner, including
        # all intermediate angular extrema and the full translation overrun.
        # A single axis-aligned box combines extrema from different headings
        # and falsely rejects rotated starts. Neither padding nor stop travel
        # is reduced here. Concave scopes retain the enclosing-union fallback.
        c, s = math.cos(pose[2]), math.sin(pose[2])
        vertices = [(c*(x-pose[0])+s*(y-pose[1]),
                     -s*(x-pose[0])+c*(y-pose[1])) for x, y in scope.exterior.coords]
        if not scope.exterior.is_ccw:
            vertices.reverse()
        if not _covered(_world(straight, pose), polygon):
            return False
        for (ax, ay), (bx, by) in zip(vertices, vertices[1:]):
            dx, dy = bx-ax, by-ay
            translation = min(-dy*distance, -dy*(distance+overrun))
            for x in PADDED_BOUNDS[:2]:
                for y in PADDED_BOUNDS[2:]:
                    support = _extrema(dx*y-dy*x, dx*x+dy*y, -angle, angle)[0]
                    if support+translation+dy*ax-dx*ay < -1e-12:
                        return False
        return True
    rear, front, right, left = _rotated_bounds(-angle, angle)
    turns = box(distance+rear, right, distance+overrun+front, left)
    return _covered(_world(unary_union((straight, turns)), pose), polygon)


def forward_sequence_in_scope(pose, polygon, *, distance=.25):
    """The separately selected .25-m acceleration/braking measurement only."""
    if (len(pose) != 3 or not all(math.isfinite(v) for v in (*pose, distance))
            or not .05 <= distance <= .25):
        return False
    return _covered(_world(box(-.13, -.25, .33+distance+.08*STOP_HORIZON_S, .25), pose), polygon)


def wheel_pose_in_bound_scope(current, initial_wheel, initial_map):
    """Keep the reviewed physical LAB area anchored through SLAM corrections.

    Initial map pose belongs to the same stationary scope measurement. Wheel
    pose is real position-feedback odometry, not commanded RPM or an invented
    transform. The anchor is immutable for one diagnostic process/session.
    """
    if not all(len(p) == 3 and all(math.isfinite(v) for v in p)
               for p in (current, initial_wheel, initial_map)):
        raise ValueError('invalid fixed wheel/scope reference')
    angle = initial_map[2]-initial_wheel[2]
    dx, dy = current[0]-initial_wheel[0], current[1]-initial_wheel[1]
    c, s = math.cos(angle), math.sin(angle)
    return (initial_map[0]+c*dx-s*dy, initial_map[1]+s*dx+c*dy,
            initial_map[2]+current[2]-initial_wheel[2])
