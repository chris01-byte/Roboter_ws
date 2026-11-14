"""Actual current finite endpoint occlusion, no truth input or map mutation."""
import b73_selection_probe as frozen
import numpy as np,copy,math,time,json
import explore.metric_frontier_runtime as runtime
from pathlib import Path
original=runtime.visible_boundary_cells
rows=[]
for index in (4,5,13,14):
 n,i,p=frozen.frozen(index)
 record=frozen.pickle.loads((frozen.root/('selection-object-'+str(index)+'.pickle')).read_bytes())
 scan=record['scan'];mount=record['mount'];pose=i[2];grid=i[0]
 ranges=np.asarray(scan['ranges']);angles=scan['angle_min']+np.arange(len(ranges))*scan['angle_increment']
 valid=np.isfinite(ranges)&(ranges>0)&(ranges>=scan['range_min'])&(ranges<scan['range_max'])
 c,s=math.cos(pose[2]),math.sin(pose[2]);origin=(pose[0]+c*mount[0]-s*mount[1],pose[1]+s*mount[0]+c*mount[1])
 xy=np.column_stack((origin[0]+ranges[valid]*np.cos(angles[valid]+pose[2]+mount[2]),origin[1]+ranges[valid]*np.sin(angles[valid]+pose[2]+mount[2])))
 blocked=copy.deepcopy(grid);array=np.asarray(grid.data).reshape(grid.info.height,grid.info.width).copy();changed=set()
 for x,y in xy:
  col,row=n._world_to_grid(x,y,grid.info)
  if 0<=row<grid.info.height and 0<=col<grid.info.width and array[row,col]==0:
   array[row,col]=100;changed.add((row,col))
 blocked.data=array.ravel().tolist()
 def sight(g,scope,pose,view):
  assert g is grid
  return original(blocked,scope,pose,view)
 runtime.visible_boundary_cells=sight;start=time.monotonic();out=dict(index=index,finite_current_occluder_cells=len(changed))
 try:
  candidates=n._metric_select(i,p,.3);out['candidates']=[dict(task=c.task_id,goal=[c.x,c.y,c.yaw],points=c.observation_points,native=c.requires_nav2_plan) for c in candidates]
 except Exception as e:out['error']=str(e)
 out['seconds']=time.monotonic()-start;out['ranking']=n._frontier_rank_stats;rows.append(out);print(json.dumps(out),flush=True)
 runtime.visible_boundary_cells=original
Path('/evidence/ap06-missions-20261005/b73-endpoint-probe.json').write_text(json.dumps(rows,indent=2)+'\n')
