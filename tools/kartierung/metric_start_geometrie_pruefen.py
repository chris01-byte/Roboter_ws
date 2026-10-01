#!/usr/bin/env python3
"""Offline trace of stored start grids through the existing metric geometry.

No ROS graph, publishers, map edits or motion. Snapshot directory contains
passive-binding.json, passive-map.cdr, passive-global_costmap-costmap.cdr and
product-profile.yaml. Detailed cells/coordinates must stay outside Git.
"""
import argparse
import json
import math
from pathlib import Path
import time

import numpy as np
import yaml
from nav_msgs.msg import OccupancyGrid
from rclpy.serialization import deserialize_message
from scipy.ndimage import distance_transform_edt
from explore.explore_node import ExploreNode
from explore.metric_frontier import (self_body_unknown_mask, known_safe_mask,
    footprint_cells, footprint_clear, MetricTaskPolicy)
from explore.exploration_scope import AuthorizedExplorationScope
from explore.map_status_adapter import MapManagerStatusCorrelator, decode_map_manager_status_json
from explore.portal_memory import Point2D


def clipped_area(polygon, row, col):
    """Exact polygon/cell intersection in raster coordinates (cell area = 1)."""
    vertices=list(polygon)
    for axis, bound, sign in [(0,col,1),(0,col+1,-1),(1,row,1),(1,row+1,-1)]:
        source=vertices;vertices=[]
        if not source:break
        previous=source[-1]
        for current in source:
            inside=sign*(current[axis]-bound)>=0
            before=sign*(previous[axis]-bound)>=0
            if inside!=before:
                fraction=(bound-previous[axis])/(current[axis]-previous[axis])
                vertices.append(tuple(previous[k]+fraction*(current[k]-previous[k]) for k in (0,1)))
            if inside:vertices.append(current)
            previous=current
    if len(vertices)<3:return 0.
    return abs(sum(a[0]*b[1]-a[1]*b[0] for a,b in zip(vertices,vertices[1:]+vertices[:1])))/2


def physical_polygon_in_grid(grid, pose, bounds):
    left,right,bottom,top=bounds
    q=grid.info.origin.orientation;angle=math.atan2(2*q.w*q.z,1-2*q.z*q.z)
    origin=grid.info.origin.position;res=grid.info.resolution;out=[]
    for x,y in [(left,bottom),(right,bottom),(right,top),(left,top)]:
        wx=pose[0]+math.cos(pose[2])*x-math.sin(pose[2])*y-origin.x
        wy=pose[1]+math.sin(pose[2])*x+math.cos(pose[2])*y-origin.y
        out.append(((math.cos(angle)*wx+math.sin(angle)*wy)/res,
                    (-math.sin(angle)*wx+math.cos(angle)*wy)/res))
    return out


def classify(grid, occupancy, known, pose):
    body=physical_polygon_in_grid(grid,pose,(-.11,.31,-.23,.23))
    padded=physical_polygon_in_grid(grid,pose,(-.13,.33,-.25,.25))
    result={}
    for name,angles in [('initial_contour',[pose[2]]),('initial_scan',pose[2]+np.linspace(0.,2*math.pi,127))]:
        touched=set();first=None
        for yaw in angles:
            rows,cols=footprint_cells(*pose[:2],yaw,grid,ExploreNode._world_to_grid)
            cells=set(zip(map(int,rows),map(int,cols)));touched.update(cells)
            if first is None and not footprint_clear(*pose[:2],yaw,grid,known,ExploreNode._world_to_grid,ExploreNode._grid_to_world):
                first=float(yaw)
        counts={};missing=[];outside_area=0.
        for row,col in sorted(touched):
            if not(0<=row<occupancy.shape[0] and 0<=col<occupancy.shape[1]):
                counts['outside_grid']=counts.get('outside_grid',0)+1;continue
            value=int(occupancy[row,col]);body_area=clipped_area(body,row,col);padding_area=clipped_area(padded,row,col)
            if body_area>=1-1e-8:region='whole_body'
            elif body_area>1e-8:region='partial_body_cell'
            elif padding_area>1e-8:region='padding_cell'
            else:region='reserve_or_additional_swing'
            evidence='unknown' if value<0 else 'observed_free' if value==0 else 'inflation' if value<100 else 'obstacle'
            category=region+':'+evidence;counts[category]=counts.get(category,0)+1
            if not known[row,col]:
                outside_area+=(1-body_area)*grid.info.resolution**2
                xy=ExploreNode._grid_to_world(col,row,grid.info)
                missing.append(dict(row=row,col=col,original_value=value,region=region,
                                    world_center=list(xy),body_overlap_fraction=body_area))
        result[name]=dict(clear=first is None,first_rejected_yaw_rad=first,
            touched_cells=len(touched),classes=counts,rejected_cells=missing,
            missing_outside_physical_body_cell_area_m2=outside_area,
            area_definition='sum of rejected reserved raster cells minus exact initial body overlap; conservative required observation area')
    return result


def analyze(directory):
    binding=json.loads((directory/'passive-binding.json').read_text())
    profile=yaml.safe_load((directory/'product-profile.yaml').read_text())['explore_node']['ros__parameters']
    raw=deserialize_message((directory/'passive-map.cdr').read_bytes(),OccupancyGrid)
    cost=deserialize_message((directory/'passive-global_costmap-costmap.cdr').read_bytes(),OccupancyGrid)
    occupancy=np.array(raw.data).reshape(raw.info.height,raw.info.width)
    costs=np.array(cost.data).reshape(cost.info.height,cost.info.width)
    p=binding['pose'];pose=(p['x'],p['y'],p['yaw'])
    correlation=MapManagerStatusCorrelator(profile['metric_session_id'],'map').accept(
        decode_map_manager_status_json(json.dumps(binding['map_status'])))
    poly=binding['polygon'];scope=AuthorizedExplorationScope(profile['wohnungserkundung_scope_id'],correlation.context,
        tuple(Point2D(*poly[k:k+2]) for k in range(0,len(poly),2)))
    body=self_body_unknown_mask(raw,occupancy,pose,(.245,0.,math.pi/2))
    q=raw.info.origin.orientation;angle=math.atan2(2*q.w*q.z,1-2*q.z*q.z)
    known,safe=known_safe_mask(occupancy,scope,correlation,(raw.info.origin.position.x,raw.info.origin.position.y),angle,raw.info.resolution,.28,body)
    n=ExploreNode.__new__(ExploreNode)
    n._metric_scope=scope;n._wohnungserkundung_evidence_max_cells=1000000
    # Offline evaluation context, not sensor restamping or a live readiness claim.
    for key,value in dict(_global_costmap=cost,_global_costmap_received_at=time.monotonic(),
        _map_timeout_s=1e6,_global_frame='map',_frontier_goal_max_cost=90,
        _goal_clearance_m=.28,_goal_search_m=.3,_approach_dist_m=.45,
        _metric_bounds=(-.13,.33,-.25,.25),_metric_start_strategy='adaptive',
        _metric_start_egress_enabled=True,_metric_egress=None,_metric_egress_expired=False,
        _metric_body_anchor_expired=False,_min_goal_dist_m=.3,
        _frontier_forward_cone_half_angle=0.,_potential_scale=3.,_gain_scale=1.,_heading_scale=.75,_visualize=False).items():setattr(n,key,value)
    for row,col in zip(*np.nonzero(safe)):
        xy=n._grid_to_world(col,row,raw.info);cx,cy=n._world_to_grid(*xy,cost.info)
        if not(0<=cy<costs.shape[0] and 0<=cx<costs.shape[1] and 0<=costs[cy,cx]<=90):safe[row,col]=False
    cost_known=(costs>=0)&(costs<100)
    candidates=n._metric_select((raw,correlation,pose,known,safe,cost,cost_known),MetricTaskPolicy(.6,30.,2),.3)
    start_decision, adaptive_candidates=n._metric_start_decision(
        (raw,correlation,pose,known,safe,cost,cost_known),MetricTaskPolicy(.6,30.,2),.3,True)
    col,row=n._world_to_grid(*pose[:2],raw.info)
    raw_trace=classify(raw,occupancy,known,pose);cost_trace=classify(cost,costs,cost_known,pose)
    return dict(offline_only=True,source_binding_wall_s=binding['wall_s'],
        map_stamp_ns=raw.header.stamp.sec*10**9+raw.header.stamp.nanosec,
        raw_fingerprint=correlation.fingerprint,pose=pose,
        physical_bounds=[-.11,.31,-.23,.23],padded_bounds=[-.13,.33,-.25,.25],
        reserve_m=raw.info.resolution/math.sqrt(2)+.01,
        raw_start_value=int(occupancy[row,col]),private_start_known=bool(known[row,col]),
        private_body_cells=int(body.sum()),safe_start=bool(safe[row,col]),
        start_clearance_m=float(distance_transform_edt(np.pad(known,1))[row+1,col+1]*raw.info.resolution),
        required_clearance_m=.28+raw.info.resolution/2,
        first_product_rejection=start_decision['first_rejecting_predicate'],
        adaptive_start_decision=start_decision,adaptive_candidates=len(adaptive_candidates),
        raw=raw_trace,costmap=cost_trace,candidates=len(candidates),selection=n._frontier_rank_stats,
        observation='Offline replay only: fixed initial unknown inventory, shrinking movement-specific overlap, no added unknown area or approach/reentry. Full-spin and goal tolerance checks remain strict; real ComputePath and current sources are separately required. Static NaN rays remain NaN.')


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('snapshot',type=Path);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    target=args.output.resolve()
    if any((parent/'.git').exists() for parent in (target.parent,*target.parents)):
        raise SystemExit('Private real geometry output must be outside a Git checkout')
    report=analyze(args.snapshot.resolve());target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(report,indent=2))
    print(json.dumps({k:report[k] for k in ('offline_only','private_body_cells','safe_start','first_product_rejection','candidates')}))


if __name__=='__main__':main()
