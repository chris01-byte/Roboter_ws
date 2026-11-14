"""Original zero-gain arrivals: original vs reserved predicted view points.
Pure component comparisons; no mission counters, source health or motion.
"""
import copy,pickle,json,sys,time,math
from pathlib import Path
sys.path.insert(0,'/evidence/ap06-repo/src/explore/test')
from test_metric_frontier import adaptive_fixture
from explore.metric_frontier_candidates import lidar_view,visible_boundary_cells
from explore.metric_frontier_runtime import MetricInputs
from explore.metric_progress import ObservationBaseline,measured_gain,observation_complete
r=Path('/evidence/ap06-missions-20261005/mission-b-v73-capture')
def load(name):return pickle.loads((r/name).read_bytes())
out=[]
for dep,before_index,after_index in ((3,4,5),(4,13,14)):
 before=load('selection-object-'+str(before_index)+'.pickle');after=load('selection-object-'+str(after_index)+'.pickle');d=load('departure-input-'+str(dep)+'.pickle')
 n,_=adaptive_fixture()
 for k,v in before['attributes'].items():setattr(n,k,copy.deepcopy(v))
 n._metric_egress=copy.deepcopy(before['evidence']);n._metric_scope=before['scope'];n._metric_body_reference=lambda:before['reference'];n._global_costmap=d['inputs'][5];n._metric_status={}
 inputs=MetricInputs(d['inputs'],d['reference'],d['physical_motion']);target=d['target']
 stop=n._metric_rollout_stop_pose(inputs,d['route'],target.yaw,native_plan=True)
 view=lidar_view(before['scan'],before['mount'],before['captured_monotonic'],n._door_lidar_scan_timeout,n._door_lidar_max_range)
 grid=before['inputs'][0];cor=before['inputs'][1];scope=n._metric_scope_mask(before['inputs'])
 q=grid.info.origin.orientation;angle=math.atan2(2*q.w*q.z,1-2*q.z*q.z)
 scans=before['scan'];stamp=scans['key'][0]*10**9+scans['key'][1]
 union=set();details=[]
 for dx,dy,dyaw in ((0,0,0),(.02,0,0),(-.02,0,0),(0,.02,0),(0,-.02,0),(0,0,.05),(0,0,-.05)):
  potential=tuple(n._grid_to_world(c,r0,grid.info) for r0,c in visible_boundary_cells(grid,scope,(stop[0]+dx,stop[1]+dy,stop[2]+dyaw),view) if math.dist(n._grid_to_world(c,r0,grid.info),target.frontier_xy)<=.8)
  union.update(potential);details.append([dx,dy,dyaw,len(potential)])
 results={}
 for name,points in [('original',target.observation_points),('reserved_union',tuple(sorted(union)))]:
  baseline=ObservationBaseline(cor.context,cor.source_stamp_ns,stamp,grid.info.resolution,angle,points)
  gained=measured_gain(baseline,after['inputs'][0],after['inputs'][1],after['inputs'][2],after['scan'],after['mount'],n._world_to_grid,n._grid_to_world,4.)
  states=[]
  for xy in points:
   c0,r0=n._world_to_grid(*xy,after['inputs'][0].info);states.append([list(xy),int(after['inputs'][0].data[r0*after['inputs'][0].info.width+c0])])
  results[name]=dict(points=points,gained=sorted(gained),complete=observation_complete(baseline,after['inputs'][0],after['inputs'][1],n._world_to_grid,n._grid_to_world),final_states=states)
 out.append(dict(departure=dep,task=target.task_id,goal=[target.x,target.y,target.yaw],predicted=stop,actual=after['inputs'][2],before_stamp=cor.source_stamp_ns,departure_stamp=d['inputs'][1].source_stamp_ns,after_stamp=after['inputs'][1].source_stamp_ns,potential_samples=details,comparison=results))
print(json.dumps(out,indent=2),flush=True)
Path('/evidence/ap06-missions-20261005/b73-gain-probe.json').write_text(json.dumps(out,indent=2)+'\n')
