"""Read-only filter counterprobe on original B73 geometry, all limits intact."""
import b73_selection_probe as frozen
import explore.metric_frontier_runtime as runtime
import time,json
from pathlib import Path
original=runtime.boundary_samples
rows=[]
for index in (4,5,13,14):
 for variant in ('original','current_local_remainder','all_components'):
  n,i,p=frozen.frozen(index)
  def sampled(grid,scope,to_world,minimum,**kwargs):
   if variant=='all_components':minimum=.01
   if variant=='current_local_remainder':
    kwargs['retained_anchors']=(*kwargs.get('retained_anchors',()),i[2][:2])
    kwargs['retained_radius_m']=.8+n._min_goal_dist_m+n._goal_search_m
   return original(grid,scope,to_world,minimum,**kwargs)
  runtime.boundary_samples=sampled;start=time.monotonic();out=dict(index=index,variant=variant)
  try:out['candidates']=[dict(task=c.task_id,goal=[c.x,c.y,c.yaw],points=c.observation_points,native=c.requires_nav2_plan) for c in n._metric_select(i,p,.3)]
  except Exception as e:out['error']=str(e)
  out['seconds']=time.monotonic()-start;out['ranking']=n._frontier_rank_stats;rows.append(out);print(json.dumps(out),flush=True)
  runtime.boundary_samples=original
Path('/evidence/ap06-missions-20261005/b73-small-boundary-probe.json').write_text(json.dumps(rows,indent=2)+'\n')
