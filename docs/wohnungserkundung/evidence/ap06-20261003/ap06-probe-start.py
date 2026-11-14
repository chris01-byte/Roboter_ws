"""Offline measured-input diagnostic; no planner/action/motion or fresh-source claim."""
import json, sys, copy
from pathlib import Path
from dataclasses import replace
import numpy as np
sys.path.insert(0, '/evidence/ap06-repo/src/explore/test')
from test_metric_frontier import adaptive_fixture
from explore.metric_frontier import footprint_cells
from explore.exploration_scope import AuthorizedExplorationScope
from explore.portal_memory import Point2D
from explore.portal_source_adapter import raw_map_portal_source_from_values
p=Path('/evidence/ap06-runs/product-c-04-profile')
a=np.load(p/'selection-input-1.npz');geometry=json.loads((p/'selection-geometry.json').read_text())
n,inputs=adaptive_fixture()
for index,field,gdata in [(0,'raw',geometry[0]),(5,'cost',geometry[1])]:
 g=inputs[index];g.info.resolution=gdata['resolution'];g.info.width=gdata['width'];g.info.height=gdata['height']
 g.info.origin.position.x,g.info.origin.position.y=gdata['origin'];g.data=a[field].ravel().tolist()
inputs[1]=replace(inputs[1],fingerprint=raw_map_portal_source_from_values(**n._metric_grid_values(inputs[0])).fingerprint)
inputs[2]=tuple(a['pose']);inputs[3]=a['known'].copy();inputs[4]=a['safe'].copy();inputs[6]=a['cost_known'].copy()
n._metric_scope=AuthorizedExplorationScope('scope', inputs[1].context,tuple(Point2D(x,y) for x,y in ((-1.2,-1.4),(4.4,-1.4),(4.4,1.4),(-1.2,1.4))))
n._metric_start_egress_enabled=True;n._metric_egress=None;n._metric_egress_expired=False;n._metric_path_validation='rpp_rollout';n._prealign_handoff_tolerance=.02
out=[]
for d in [.30,.33,.36,.39,.42,.45,.48,.51,.54,.60,.75,1.]:
 route=n._metric_route(inputs,(inputs[2][0]+d,inputs[2][1]),0.)
 missing={}
 for label,g,allowed in [('raw',inputs[0],inputs[3]),('costmap',inputs[5],inputs[6])]:
  rr,cc=footprint_cells(inputs[2][0]+d,inputs[2][1],0.,g,n._world_to_grid,n._metric_bounds,heading_half_angle=.4,center_deviation_m=.15)
  inside=(rr>=0)&(rr<allowed.shape[0])&(cc>=0)&(cc<allowed.shape[1]);r,c=rr[inside],cc[inside];values=np.asarray(g.data).reshape(allowed.shape)[r,c]
  missing[label]=dict(outside=int((~inside).sum()),unknown=int(((values<0)&(~allowed[r,c])).sum()),occupied=int(((values>=0)&(~allowed[r,c])).sum()))
 out.append(dict(forward_distance_m=d,accepted=route is not None,rejection=n._metric_last_route_rejection,goal_missing_cells=missing,route=route))
print(json.dumps(dict(kind='offline_measured_input_only_no_nav2_plan_or_actuation',source_run=p.name,pose=inputs[2],probes=out),indent=2))
# Keep actual cell values/world positions: forbidden inflated cells are not
# automatically physical obstacles. This diagnostic performs no motion.
g=inputs[5];allowed=inputs[6];rr,cc=footprint_cells(.42,0.,0.,g,n._world_to_grid,n._metric_bounds,heading_half_angle=.4,center_deviation_m=.15)
valid=(rr>=0)&(rr<allowed.shape[0])&(cc>=0)&(cc<allowed.shape[1]);rr,cc=rr[valid],cc[valid];bad=~allowed[rr,cc]
print(json.dumps([dict(xy=n._grid_to_world(int(c),int(r),g.info),cost=int(np.asarray(g.data).reshape(allowed.shape)[r,c])) for r,c in zip(rr[bad],cc[bad])]))
