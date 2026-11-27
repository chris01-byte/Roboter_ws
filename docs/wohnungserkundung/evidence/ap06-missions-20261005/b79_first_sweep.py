"""Exact original B73 frame and original native paths; locate unchanged predicate."""
from pathlib import Path
import sys,copy,json,numpy as np
sys.path.insert(0,'/evidence/ap06-repo/src/explore/test')
from test_metric_departure import path
from explore.metric_frontier import MetricCandidate,footprint_cells,footprint_clear
import explore.metric_frontier_runtime as runtime
import b73_local_frozen as recorded
n,inputs,p=recorded.n,recorded.inputs,recorded.policy
original=runtime.footprint_poses_clear
rows=[]
for variant in ('hybrid-controller-r06',):
 probes=json.loads((Path('/evidence/ap06-missions-20261005')/('b79-native-probe-'+variant)/'native-plans.json').read_text())
 calls=[]
 def diagnosed(poses,grid,allowed,to_grid,bounds,**kw):
  ok=original(poses,grid,allowed,to_grid,bounds,**kw)
  if not ok:
   for k,pose in enumerate(poses):
    rr,cc=footprint_cells(*pose,grid,to_grid,bounds,kw.get('heading_half_angle',0),center_deviation_m=kw.get('center_deviation_m',0))
    invalid=[]
    for r,c in zip(rr,cc):
     if not (0<=r<allowed.shape[0] and 0<=c<allowed.shape[1]) or not allowed[r,c]:
      invalid.append(dict(row=int(r),col=int(c),world=n._grid_to_world(int(c),int(r),grid.info),value=None if not (0<=r<allowed.shape[0] and 0<=c<allowed.shape[1]) else int(grid.data[r*grid.info.width+c])))
    if invalid:
     calls.append(dict(grid='raw' if grid is inputs[0] else 'cost',count=len(poses),index=k,pose=pose,forbidden=invalid));break
  return ok
 runtime.footprint_poses_clear=diagnosed
 target=MetricCandidate('original-probe',*probes[1]['goal'],(1.304999970830977,.13499999698251486),(),1.,0.,inputs[1].fingerprint,1)
 route=n._metric_validate_nav_plan(inputs,path(probes[1]),target,public_only=True)
 rows.append(dict(variant=variant,valid=route is not None,rejection=n._metric_last_route_rejection,checks=calls))
 print(json.dumps(rows[-1]),flush=True)
 runtime.footprint_poses_clear=original
Path('/evidence/ap06-missions-20261005/b79-first-sweep.json').write_text(json.dumps(rows,indent=2)+'\n')
