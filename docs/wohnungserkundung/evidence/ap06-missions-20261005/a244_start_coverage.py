"""Read-only coverage requirement on A227; no new observed cells or movement."""
from pathlib import Path
import sys,json,math,copy
import numpy as np
sys.path.insert(0,'/evidence/ap06-repo/src/explore/test')
from test_metric_public_cooldown import frozen
from explore.metric_frontier import footprint_poses_clear
n,inputs,p=frozen('ap06_a227_start_selection');result={}
for i,label in [(0,'raw'),(1,'cost')]:
 g=inputs[0 if i==0 else 5];allowed=inputs[3 if i==0 else 6];e=n._metric_egress[i]
 rows,cols=np.indices(allowed.shape);x,y=n._grid_to_world(cols,rows,g.info)
 pose=inputs[2];dx=x-pose[0];dy=y-pose[1];covered=np.zeros(allowed.shape,bool)
 reserve=g.info.resolution/math.sqrt(2)+.01+.02
 left,right,bottom,top=n._metric_bounds
 for angle in pose[2]+np.linspace(-.05,.05,15):
  lx=np.cos(angle)*dx+np.sin(angle)*dy;ly=-np.sin(angle)*dx+np.cos(angle)*dy
  covered |= (left-reserve<=lx)&(lx<=right+reserve)&(bottom-reserve<=ly)&(ly<=top+reserve)
 occupancy=np.asarray(g.data).reshape(allowed.shape)
 missing=covered&(occupancy<0)&~e.unknown
 xy=np.column_stack((x[missing],y[missing]));cells=np.column_stack(np.nonzero(missing))
 result[label]=dict(additional_unobserved_cells_outside_initial_inventory=int(missing.sum()),
   occupied_cells_in_required_envelope=int(np.count_nonzero(covered&(occupancy>=100))),
   required_tracking_m=.02,required_heading_rad=.05,
   missing_cell_centres_bbox_m=[xy.min(axis=0).tolist(),xy.max(axis=0).tolist()] if len(xy) else None,
   complete_tracking_proof=footprint_poses_clear([pose],g,allowed|e.unknown,n._world_to_grid,
       n._metric_bounds,heading_half_angle=.05,center_deviation_m=.02),
   cells=cells.tolist())
 f=copy.deepcopy(e.fixed);virtual=np.where(f.unknown,-1,0)
 measured=(.005430180062437047,-2.1888534984835452e-7,-.00010196898912041717)
 result[label]['straight_pose_on_A227']=f.check_trajectory([(measured[0],0.,0.)],virtual,~f.unknown,n._world_to_grid)
 result[label]['A238_measured_pose_on_separate_A227_inventory']=f.check_trajectory([measured],virtual,~f.unknown,n._world_to_grid)
 result[label]['counterexample_detail']=getattr(f,'last_monotone_failure',None)
print(json.dumps(result,indent=2),flush=True)
