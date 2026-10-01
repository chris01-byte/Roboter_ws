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


def self_body_unknown_mask(grid, occupancy, pose, lidar_mount):
    """Only whole unknown cells inside the measured UNPADDED chassis.

    This is a private validity mask, never a raw-map edit or a ray return.
    Mast shadow outside the existing body, padding and occupied cells are
    excluded. The deployed scan handedness requires the measured +90deg TF.
    """
    if (len(pose) != 3 or len(lidar_mount) != 3
            or not all(math.isfinite(v) for v in (*pose, *lidar_mount))):
        raise ValueError('self_body_pose_or_tf_invalid')
    expected = (.245, 0., math.pi/2)
    if (abs(lidar_mount[0]-expected[0]) > .001
            or abs(lidar_mount[1]) > .001
            or abs(math.atan2(math.sin(lidar_mount[2]-expected[2]),
                              math.cos(lidar_mount[2]-expected[2]))) > .001):
        raise ValueError('self_body_lidar_tf_mismatch')
    if occupancy.shape != (grid.info.height, grid.info.width):
        raise ValueError('self_body_grid_mismatch')
    if not math.isfinite(grid.info.resolution) or grid.info.resolution <= 0:
        raise ValueError('self_body_resolution_invalid')
    rows, cols = np.indices(occupancy.shape)
    q=grid.info.origin.orientation
    yaw=math.atan2(2*(q.w*q.z+q.x*q.y),1-2*(q.y*q.y+q.z*q.z))
    res=grid.info.resolution
    lx,ly=(cols+.5)*res,(rows+.5)*res
    dx=grid.info.origin.position.x+math.cos(yaw)*lx-math.sin(yaw)*ly-pose[0]
    dy=grid.info.origin.position.y+math.sin(yaw)*lx+math.cos(yaw)*ly-pose[1]
    x,y=math.cos(pose[2])*dx+math.sin(pose[2])*dy,-math.sin(pose[2])*dx+math.cos(pose[2])*dy
    # Exact projection of the square cell onto body axes. The old half
    # diagonal over-shrank parallel grids and rejected wholly enclosed cells.
    # Every corner must still be inside the physical, unpadded chassis.
    relative = yaw-pose[2]
    reserve=res/2*(abs(math.cos(relative))+abs(math.sin(relative)))
    return ((occupancy < 0) & (-.11+reserve <= x) & (x <= .31-reserve)
            & (abs(y) <= .23-reserve))


def known_safe_mask(occupancy, scope, correlation, origin, yaw, resolution, clearance, self_body=None):
    inside = rasterize_scope(
        scope, context=correlation.context, width=occupancy.shape[1],
        height=occupancy.shape[0], resolution_m=resolution,
        origin_x_m=origin[0], origin_y_m=origin[1], origin_yaw_rad=yaw,
        maximum_cells=1000000)
    known = (occupancy == 0) & inside
    if self_body is not None:
        if self_body.shape != known.shape or self_body.dtype != bool:
            raise ValueError('self_body_mask_invalid')
        # A true obstacle can NEVER be exempted, even inside the body.
        known |= self_body & (occupancy < 0) & inside
    distance = distance_transform_edt(np.pad(known, 1))[1:-1, 1:-1]
    # Include cell-size uncertainty; never seed across an unknown gap.
    safe = known & (distance * resolution >= clearance + resolution / 2)
    return known, safe


def footprint_cells(x, y, yaw, grid, world_to_grid, bounds=(-.13, .33, -.25, .25), heading_half_angle=0., heading_samples=None, center_deviation_m=0.):
    """Conservative cell-intersection test of the padded measured rectangle.

    Bounds enclose the actual configured footprint. Cell half diagonals and
    route samples supply raster/interpolation reserve; unknown is never free.
    """
    left, right, bottom, top = bounds
    res = grid.info.resolution
    if not math.isfinite(center_deviation_m) or center_deviation_m < 0:
        raise ValueError("controller_center_deviation_invalid")
    reserve = res / math.sqrt(2) + .01 + center_deviation_m
    radius = math.hypot(max(abs(left), abs(right))+reserve, max(abs(bottom), abs(top))+reserve)
    c0, r0 = world_to_grid(x, y, grid.info)
    n = int(math.ceil(radius / res)) + 2
    angles = yaw + np.linspace(-heading_half_angle, heading_half_angle,
                               heading_samples if heading_samples is not None else
                               1 if heading_half_angle == 0 else 15)
    cosine, sine = np.cos(angles)[:, None, None], np.sin(angles)[:, None, None]
    rows, cols = np.mgrid[r0-n:r0+n+1, c0-n:c0+n+1]
    q = grid.info.origin.orientation
    map_yaw = math.atan2(2*(q.w*q.z+q.x*q.y),1-2*(q.y*q.y+q.z*q.z))
    local_x, local_y = (cols+.5)*res, (rows+.5)*res
    dx = grid.info.origin.position.x+math.cos(map_yaw)*local_x-math.sin(map_yaw)*local_y-x
    dy = grid.info.origin.position.y+math.sin(map_yaw)*local_x+math.cos(map_yaw)*local_y-y
    lx, ly = cosine*dx+sine*dy, -sine*dx+cosine*dy
    touched = ((left-reserve<=lx)&(lx<=right+reserve)&
               (bottom-reserve<=ly)&(ly<=top+reserve))
    touched = np.any(touched, axis=0)
    return rows[touched], cols[touched]


def footprint_clear(x, y, yaw, grid, allowed, world_to_grid, grid_to_world,
                    bounds=(-.13, .33, -.25, .25), heading_half_angle=0., heading_samples=None, center_deviation_m=0.):
    """Use the identical reserved cell set for motion and diagnosis."""
    r, c = footprint_cells(x, y, yaw, grid, world_to_grid, bounds, heading_half_angle, heading_samples, center_deviation_m)
    if np.any((r<0)|(r>=allowed.shape[0])|(c<0)|(c>=allowed.shape[1])):
        return False
    return bool(np.all(allowed[r,c]))



def lookahead_point(point, remaining_route, distance_m):
    """RPP carrot: first polyline intersection with the Euclidean radius.

    Fixed lookahead is a circle radius, not remaining arclength at a corner.
    A route wholly inside the circle uses its actual final point.
    """
    previous=point
    for endpoint in remaining_route:
        if math.dist(point,endpoint)>=distance_m:
            dx,dy=endpoint[0]-previous[0],endpoint[1]-previous[1]
            px,py=previous[0]-point[0],previous[1]-point[1]
            a=dx*dx+dy*dy
            b=2*(px*dx+py*dy)
            c=px*px+py*py-distance_m*distance_m
            fraction=(-b+math.sqrt(max(0.,b*b-4*a*c)))/(2*a)
            return previous[0]+fraction*dx,previous[1]+fraction*dy
        previous=endpoint
    return previous


def _clip_cell(polygon, row, col):
    vertices = list(polygon)
    for axis, bound, sign in ((0,col,1),(0,col+1,-1),(1,row,1),(1,row+1,-1)):
        source, vertices = vertices, []
        if not source:
            break
        previous = source[-1]
        for current in source:
            inside, before = sign*(current[axis]-bound)>=0, sign*(previous[axis]-bound)>=0
            if inside != before:
                f=(bound-previous[axis])/(current[axis]-previous[axis])
                vertices.append(tuple(previous[k]+f*(current[k]-previous[k]) for k in (0,1)))
            if inside:
                vertices.append(current)
            previous=current
    return vertices


def _polygon_area(p):
    return abs(sum(a[0]*b[1]-a[1]*b[0] for a,b in zip(p,p[1:]+p[:1])))/2 if p else 0.


def _polygon_distance(a,b):
    def point_segment(p,x,y):
        dx,dy=y[0]-x[0],y[1]-x[1];d=dx*dx+dy*dy
        f=max(0.,min(1.,((p[0]-x[0])*dx+(p[1]-x[1])*dy)/d)) if d else 0.
        return math.hypot(p[0]-x[0]-f*dx,p[1]-x[1]-f*dy)
    return min(point_segment(p,x,y) for p,polygon in
        [(p,b) for p in a]+[(p,a) for p in b]
        for x,y in zip(polygon,polygon[1:]+polygon[:1]))


def _cell_intersections(polygon, cells):
    """Batch exact convex clipping; bounded eight-vertex intersections."""
    n=len(cells);vertices=np.zeros((n,12,2));vertices[:,:4]=polygon
    counts=np.full(n,4,dtype=int);j=np.arange(12)[None,:]
    for axis,offset,sign in ((0,0,1),(0,1,-1),(1,0,1),(1,1,-1)):
        bound=cells[:,1-axis]+offset
        previous=vertices[np.arange(n)[:,None],np.where(j==0,counts[:,None]-1,j-1)]
        active=j<counts[:,None]
        inside=sign*(vertices[:,:,axis]-bound[:,None])>=0
        before=sign*(previous[:,:,axis]-bound[:,None])>=0
        cross=active&(inside!=before)
        fraction=np.zeros((n,12))
        np.divide(bound[:,None]-previous[:,:,axis],vertices[:,:,axis]-previous[:,:,axis],
            out=fraction,where=cross)
        intersection=previous+fraction[:,:,None]*(vertices-previous)
        candidates=np.stack((intersection,vertices),axis=2).reshape(n,24,2)
        keep=np.stack((cross,active&inside),axis=2).reshape(n,24)
        indices=np.cumsum(keep,axis=1)-1;rr,cc=np.nonzero(keep)
        vertices=np.zeros((n,12,2));vertices[rr,indices[rr,cc]]=candidates[rr,cc]
        counts=keep.sum(axis=1)
    valid=j<counts[:,None]
    following=vertices[np.arange(n)[:,None],np.where(j+1<counts[:,None],j+1,0)]
    area=np.abs(np.sum(np.where(valid,vertices[:,:,0]*following[:,:,1]
        -vertices[:,:,1]*following[:,:,0],0),axis=1))/2
    return area,vertices,valid


def _cell_distances(polygon,cells):
    square=np.stack((np.stack((cells[:,1],cells[:,0]),axis=1),
        np.stack((cells[:,1]+1,cells[:,0]),axis=1),
        np.stack((cells[:,1]+1,cells[:,0]+1),axis=1),
        np.stack((cells[:,1],cells[:,0]+1),axis=1)),axis=1)
    rectangle=np.broadcast_to(np.asarray(polygon),square.shape)
    def distance(points,edges):
        vector=np.roll(edges,-1,axis=1)-edges
        delta=points[:,:,None,:]-edges[:,None,:,:]
        fraction=np.clip(np.sum(delta*vector[:,None,:,:],axis=3)
            /np.sum(vector*vector,axis=2)[:,None,:],0,1)
        return np.min(np.sum((delta-fraction[:,:,:,None]*vector[:,None,:,:])**2,axis=3),axis=(1,2))
    return np.sqrt(np.minimum(distance(rectangle,square),distance(square,rectangle)))


@dataclass
class StartEgressEvidence:
    """Fixed initial unknown inventory, usable only by a checked escape sweep.

    No cell becomes known. Every new footprint/cell intersection must stay
    within its INITIAL reserved intersection, shrink monotonically, and not
    approach an abandoned cell. Occupied/out-of-scope space is never exempt.
    """
    grid: object
    pose: tuple
    bounds: tuple
    unknown: np.ndarray
    initial_polygon: tuple
    valid: bool
    reason: str = ''
    remaining_area: dict = field(default_factory=dict)
    departed_distance: dict = field(default_factory=dict)
    scope_mask: object = None

    @classmethod
    def capture(cls, grid, occupancy, allowed, inside, pose, bounds, world_to_grid):
        r,c=footprint_cells(*pose,grid,world_to_grid,bounds)
        valid=np.all((r>=0)&(r<allowed.shape[0])&(c>=0)&(c<allowed.shape[1]))
        unknown=np.zeros_like(allowed)
        reason='start_egress_outside_grid'
        if valid:
            bad=~allowed[r,c]
            valid=bool(np.all(inside[r,c]&(~bad|(occupancy[r,c]<0))))
            reason='start_egress_obstacle_or_scope'
            if valid:
                original=(occupancy[r,c]<0)&inside[r,c]
                unknown[r[original],c[original]]=True
        result=cls(grid,pose,bounds,unknown,(),bool(valid),'' if valid else reason)
        result.scope_mask=inside.copy()
        result.initial_polygon=tuple(result.polygon(pose))
        return result

    def polygon(self, pose):
        g=self.grid;res=g.info.resolution;reserve=res/math.sqrt(2)+.01
        left,right,bottom,top=self.bounds
        q=g.info.origin.orientation;angle=math.atan2(2*q.w*q.z,1-2*q.z*q.z)
        origin=g.info.origin.position;out=[]
        for x,y in ((left-reserve,bottom-reserve),(right+reserve,bottom-reserve),
                    (right+reserve,top+reserve),(left-reserve,top+reserve)):
            dx=pose[0]+math.cos(pose[2])*x-math.sin(pose[2])*y-origin.x
            dy=pose[1]+math.sin(pose[2])*x+math.cos(pose[2])*y-origin.y
            out.append(((math.cos(angle)*dx+math.sin(angle)*dy)/res,
                        (-math.sin(angle)*dx+math.cos(angle)*dy)/res))
        return out

    def initial_subset(self, vertices):
        # Convex initial rectangle: no later unknown intersection may grow
        # into an initially unoccupied portion of the same raster cell.
        p=self.initial_polygon
        return all((b[0]-a[0])*(v[1]-a[1])-(b[1]-a[1])*(v[0]-a[0])>=-1e-8
            for a,b in zip(p,p[1:]+p[:1]) for v in vertices)

    def check_trajectory(self, poses, occupancy, allowed, world_to_grid, commit=False):
        if not self.valid:return False,self.reason
        poses=np.asarray(poses,dtype=float)
        if poses.ndim!=2 or poses.shape[1]!=3 or not np.all(np.isfinite(poses)):
            return False,'start_egress_pose_invalid'
        cells=np.column_stack(np.nonzero(self.unknown & (occupancy<0)))
        keys=[tuple(k) for k in cells]
        initial=np.asarray(self.initial_polygon)
        initial_areas=_cell_intersections(initial,cells)[0] if len(cells) else np.empty(0)
        previous_area=np.asarray([self.remaining_area.get(k,a) for k,a in zip(keys,initial_areas)])
        previous_distance=np.asarray([self.departed_distance.get(k,0.) for k in keys])
        forbidden=(~allowed|~self.scope_mask)&(~self.unknown|(occupancy>=0))
        last=None
        def contains(polygons,points):
            result=np.ones((len(polygons),len(points)),dtype=bool)
            for edge in range(4):
                a=polygons[:,edge];b=polygons[:,(edge+1)%4]
                cross=(b[:,0]-a[:,0])[:,None]*(points[None,:,1]-a[:,None,1]) \
                    -(b[:,1]-a[:,1])[:,None]*(points[None,:,0]-a[:,None,0])
                result &= cross>=0
            return result
        batch=max(1,min(32,4096//max(1,len(cells))))
        for begin in range(0,len(poses),batch):
            chunk=poses[begin:begin+batch]
            polygons=np.asarray([self.polygon(tuple(p)) for p in chunk])
            # The original cell-centre reserve already encloses the full
            # chassis. Reject a reserved corner beyond the grid boundary.
            if (np.any(polygons[:,:,0]<-.5) or np.any(polygons[:,:,1]<-.5)
                    or np.any(polygons[:,:,0]>allowed.shape[1]-.5)
                    or np.any(polygons[:,:,1]>allowed.shape[0]-.5)):
                return False,'start_egress_outside_grid'
            c0=max(0,int(math.floor(polygons[:,:,0].min())))
            c1=min(allowed.shape[1],int(math.ceil(polygons[:,:,0].max()))+1)
            r0=max(0,int(math.floor(polygons[:,:,1].min())))
            r1=min(allowed.shape[0],int(math.ceil(polygons[:,:,1].max()))+1)
            rr,cc=np.nonzero(forbidden[r0:r1,c0:c1])
            points=np.column_stack((cc+c0+.5,rr+r0+.5))
            if np.any(contains(polygons,points)):
                return False,'start_egress_new_unknown_or_obstacle'
            if len(cells):
                touched=contains(polygons,cells[:,::-1]+.5).any(axis=1)
                previous=np.vstack((chunk[0] if last is None else last,chunk[:-1]))
                turn=np.arctan2(np.sin(chunk[:,2]-previous[:,2]),np.cos(chunk[:,2]-previous[:,2]))
                if np.any(touched & (np.linalg.norm(chunk[:,:2]-previous[:,:2],axis=1)<1e-9)
                          & (np.abs(turn)>1e-9)):
                    return False,'start_egress_in_place_turn'
                tiled_cells=np.tile(cells,(len(chunk),1))
                tiled_polygons=np.repeat(polygons,len(cells),axis=0)
                areas,vertices,valid=_cell_intersections(tiled_polygons,tiled_cells)
                subset=np.ones(len(areas),dtype=bool)
                for a,b in zip(initial,np.roll(initial,-1,axis=0)):
                    cross=(b[0]-a[0])*(vertices[:,:,1]-a[1])-(b[1]-a[1])*(vertices[:,:,0]-a[0])
                    subset &= np.all(~valid|(cross>=-1e-8),axis=1)
                areas=areas.reshape(len(chunk),len(cells))
                difference=areas-np.vstack((previous_area,areas[:-1]))
                if np.any(difference>1e-8) or not np.all(subset):
                    return False,'start_egress_reentry_or_added_cell_area'
                distances=np.where(areas.ravel()>1e-10,0.,
                    _cell_distances(tiled_polygons,tiled_cells)).reshape(areas.shape)
                difference=distances-np.vstack((previous_distance,distances[:-1]))
                if np.any(difference < -1e-8):
                    return False,'start_egress_approaches_unknown'
                previous_area=areas[-1];previous_distance=distances[-1]
            last=chunk[-1]
        if commit:
            self.remaining_area=dict(zip(keys,previous_area))
            self.departed_distance=dict(zip(keys,previous_distance))
        return True,None


def rpp_trajectory(route, pose, resolution, prealign_tolerance=.17,
                   bounds=(-.13,.33,-.25,.25)):
    """Roll out installed RPP's forward geometric law, with original reserves.

    A real plan is mandatory before execution. Fixed .4 m interpolated carrot,
    .35 rad rotate threshold, .15 m goal position tolerance; no reverse motion.
    Quarter-cell/<=5-mm translations and <=.01-rad turns bound the continuous
    inter-sample sweep inside the existing .01-m interpolation reserve.
    """
    step=min(.005,resolution/4);out=[tuple(pose)];x,y,yaw=pose
    reserve=resolution/math.sqrt(2)+.01
    radius=math.hypot(max(abs(bounds[0]),abs(bounds[1]))+reserve,
        max(abs(bounds[2]),abs(bounds[3]))+reserve)
    turn_step=min(.01,.004/radius)
    if len(route)<2:return out
    # Explorer's real prealignment points at the goal, before RPP takes over.
    initial=math.atan2(route[-1][1]-y,route[-1][0]-x)
    error=math.atan2(math.sin(initial-yaw),math.cos(initial-yaw))
    if abs(error)>prealign_tolerance:
        n=max(1,math.ceil(abs(error)/turn_step))
        out.extend((x,y,yaw+error*i/n) for i in range(1,n+1));yaw=initial
    length=sum(math.dist(a,b) for a,b in zip(route,route[1:]));index=0
    minimum_step=min(step,.004/(1+radius*2*math.sin(.35)/.15))
    for _ in range(min(20000,max(200,int(4*(length+1)/minimum_step)))):
        if math.dist((x,y),route[-1])<=.15:return out
        projections=[]
        for i in range(index,len(route)-1):
            a,b=route[i:i+2];dx,dy=b[0]-a[0],b[1]-a[1];d=dx*dx+dy*dy
            if d<1e-12:continue
            f=max(0.,min(1.,((x-a[0])*dx+(y-a[1])*dy)/d))
            p=a[0]+f*dx,a[1]+f*dy
            projections.append((math.dist((x,y),p),i))
        if not projections:raise ValueError('start_egress_plan_disconnected')
        index=min(projections)[1]
        carrot=lookahead_point((x,y),route[index+1:],.4)
        dx,dy=carrot[0]-x,carrot[1]-y
        error=math.atan2(math.sin(math.atan2(dy,dx)-yaw),math.cos(math.atan2(dy,dx)-yaw))
        if abs(error)>.35:
            yaw+=math.copysign(min(abs(error),turn_step),error);out.append((x,y,yaw));continue
        squared=dx*dx+dy*dy
        curvature=2*(-math.sin(yaw)*dx+math.cos(yaw)*dy)/squared if squared>1e-12 else 0.
        # Bound translation PLUS the reserved corner's angular travel to
        # <=4 mm per chord, including high curvature near goal tolerance.
        arc_step=min(step,.004/(1+radius*abs(curvature)))
        if abs(curvature)<1e-10:
            x+=arc_step*math.cos(yaw);y+=arc_step*math.sin(yaw)
        else:
            next_yaw=yaw+arc_step*curvature
            x+=(math.sin(next_yaw)-math.sin(yaw))/curvature
            y-=(math.cos(next_yaw)-math.cos(yaw))/curvature;yaw=next_yaw
        out.append((x,y,yaw))
    raise ValueError('start_egress_controller_rollout_unbounded')


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
