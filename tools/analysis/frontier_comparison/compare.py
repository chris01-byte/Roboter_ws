#!/usr/bin/env python3
"""AP-04 pinned-core comparison with identical product admission and sensor view.

Synthetic maps only. No mission, Navigator, motor publisher or completion claim.
The upstream probe MUST link the unmodified pinned library; see CMakeLists.txt.
"""
import argparse
import copy
import importlib.util
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import time


def load_fixture(repo):
    sys.path.insert(0,str(repo/'src/explore/test'))
    import test_metric_frontier_candidates as f
    return f


def external_frontiers(probe, n, inputs):
    from explore.explore_node import Frontier
    from explore.metric_frontier_candidates import boundary_inward
    g=inputs[0];q=g.info.origin.orientation
    header=[g.info.width,g.info.height,g.info.resolution,g.info.origin.position.x,
            g.info.origin.position.y,2*math.atan2(q.z,q.w),*inputs[2][:2],3]
    content=' '.join(map(str,header+list(g.data)+list(inputs[5].data)))
    result=subprocess.run([str(probe)],input=content,text=True,capture_output=True,check=True,timeout=5.)
    if result.stdout.strip()=='unsupported_origin_rotation':return [],'unsupported_origin_rotation'
    frontiers=[]
    for row in result.stdout.splitlines():
        x,y,size=row.split();f=Frontier((float(x),float(y)),int(size))
        col,r=n._world_to_grid(f.cx,f.cy,g.info)
        # Same adapter standoff/vehicle proof as corrected own boundary anchors.
        f.approach_direction=boundary_inward(g,r,col)
        frontiers.append(f)
    return frontiers,'ok'


def compare(repo,probe):
    from explore.metric_frontier_candidates import visible_boundary_cells
    f=load_fixture(repo);rows=[]
    for case in ('ring','concave','long','blocked','growth','revisit','no_semantics'):
        n,inputs,scan=f.fixture(case)
        # First establish the unblocked optimum, then block that same actual
        # costmap footprint for ALL cores; never inject a preselected alternative.
        if case=='blocked':
            best=n._metric_candidates(inputs,.3)[0];g=copy.deepcopy(inputs[5])
            import numpy as np
            a=np.asarray(g.data).reshape(g.info.height,g.info.width).copy()
            col,row=n._world_to_grid(best.x,best.y,g.info);a[row-2:row+3,col-2:col+3]=100
            g.data=a.ravel().tolist();inputs[5]=g;inputs[6]=(a>=0)&(a<100);n._global_costmap=g
        previous={}
        for revision in range(1,4) if case in ('growth','revisit') else (1,):
            if revision>1:
                n,inputs,scan=f.fixture(case,revision=revision)
                if case=='revisit' and previous.get('boundary_samples'):
                    # Exact earlier observation pose, with changed map evidence.
                    inputs[2]=tuple(previous['boundary_samples'])
                if case=='growth':
                    # Grow dimensions/shift origin, preserve old world cells.
                    from dataclasses import replace
                    import numpy as np
                    from explore.metric_frontier import known_safe_mask
                    from explore.portal_source_adapter import raw_map_portal_source_from_values
                    pad=revision-1
                    for index in (0,5):
                        g=inputs[index];arr=np.asarray(g.data).reshape(60,90)
                        arr=np.pad(arr,((0,pad),(pad,0)),constant_values=-1)
                        g.info.width=90+pad;g.info.height=60+pad
                        g.info.origin.position.x=-.1*pad;g.data=arr.ravel().tolist()
                    source=raw_map_portal_source_from_values(**n._metric_grid_values(inputs[0]))
                    inputs[1]=replace(inputs[1],fingerprint=source.fingerprint)
                    arr=np.asarray(inputs[0].data).reshape(60+pad,90+pad)
                    inputs[3],inputs[4]=known_safe_mask(arr,n._metric_scope,inputs[1],(-.1*pad,0.),0.,.1,.28)
                    a=np.asarray(inputs[5].data).reshape(60+pad,90+pad);inputs[6]=(a>=0)&(a<100)
            snapshot={'case':case,'revision':revision,'pose':inputs[2],
                      'fingerprint':inputs[1].fingerprint,'cores':{}}
            for mode in ('legacy_centroid','upstream_418e971','boundary_samples'):
                started=time.monotonic();reason='ok'
                if mode=='legacy_centroid':frontiers=n._detect_frontiers(inputs[0],.3)
                elif mode=='upstream_418e971':frontiers,reason=external_frontiers(probe,n,inputs)
                else:frontiers=None
                view=n._metric_observation_view()
                cs=n._metric_candidates(inputs,.3,frontiers=frontiers,view=view)
                sightings=[visible_boundary_cells(inputs[0],f.scope_mask(n,inputs),(c.x,c.y,c.yaw),view) for c in cs]
                union=set().union(*sightings)
                snapshot['cores'][mode]={'reason':reason,'accepted':len(cs),
                    'visible_boundary_union_m':len(union)*inputs[0].info.resolution,
                    'best_single_sight_m':max(map(len,sightings),default=0)*inputs[0].info.resolution,
                    'elapsed_s':time.monotonic()-started,'rejections':n._frontier_rank_stats,
                    'goals':[dict(x=c.x,y=c.y,yaw=c.yaw,frontier=c.frontier_xy,
                                  route_length_m=c.route_length_m,requires_nav2_plan=c.requires_nav2_plan) for c in cs]}
                if cs:previous[mode]=(cs[0].x,cs[0].y,cs[0].yaw)
            rows.append(snapshot)
    # Outcome requirements describe useful coverage, not output point counts.
    for row in rows:
        assert row['cores']['boundary_samples']['accepted'],row
    long=next(row for row in rows if row['case']=='long')['cores']
    assert long['boundary_samples']['visible_boundary_union_m']>2*long['boundary_samples']['best_single_sight_m']
    assert long['boundary_samples']['visible_boundary_union_m']>long['upstream_418e971']['visible_boundary_union_m']
    assert next(row for row in rows if row['case']=='ring')['cores']['legacy_centroid']['accepted']==0
    return rows


if __name__=='__main__':
    assert os.environ.get('ROS_LOCALHOST_ONLY')=='1'
    parser=argparse.ArgumentParser();parser.add_argument('--repo',type=Path,required=True)
    parser.add_argument('--probe',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();result=compare(args.repo,args.probe)
    args.output.write_text(json.dumps(result,indent=2,allow_nan=False))
    print(json.dumps({'snapshots':len(result),'passed':True,'output':str(args.output)}))
