"""B70 finite synthetic local geometry survey, component only."""
exec(open('/evidence/ap06-missions-20261005/b71_selection_probe.py').read().split('results=[]')[0])
from explore.metric_frontier_candidates import visible_boundary_cells
from explore.explore_node import Frontier
n,_=adaptive_fixture()
for key,value in record['attributes'].items():setattr(n,key,copy.deepcopy(value))
n._metric_egress=copy.deepcopy(record['evidence']);n._metric_scope=record['scope'];n._metric_body_reference=lambda:record['reference'];n._metric_nav_path=None;n._metric_status={};n._visualize=False
view=lidar_view(record['scan'],record['mount'],record['captured_monotonic'],n._door_lidar_scan_timeout,n._door_lidar_max_range);n._metric_observation_view=lambda:view
inputs=MetricInputs(copy.deepcopy(record['inputs']),record['reference'],record['physical_motion']);n._global_costmap=inputs[5];n._metric_prepare_egress(inputs);inputs=n._metric_public_inputs(inputs)
p=record['policy'];policy=MetricTaskPolicy(p['radius'],p['cooldown_s'],p['retry_limit']);policy.next_id=p['next_id'];now=time.monotonic()
for key,stored in p['tasks'].items():
 fields=dict(stored);fields['retry_after']=now+fields.pop('retry_remaining_s')-31;policy.attempts[key]=MetricAttempt(**fields)
policy.attempts['metric-task-4'].completed=False;policy.attempts['metric-task-4'].reason='partially_observed'
import math
mask=n._metric_scope_mask(inputs);hits=[];rejections={};pose=inputs[2];anchor=policy.attempts['metric-task-4'].frontier_xy
for distance in (.3,.45,.6):
 for j in range(16):
  heading=j*math.pi/8;xy=(pose[0]+distance*math.cos(heading),pose[1]+distance*math.sin(heading));facing=math.atan2(anchor[1]-xy[1],anchor[0]-xy[0])
  for yaw in (facing,facing+math.pi/2,facing-math.pi/2,heading):
   route=n._metric_route(inputs,xy,yaw)
   if route is None:
    reason=n._metric_last_route_rejection;rejections[reason]=rejections.get(reason,0)+1;continue
   stop=n._metric_rollout_stop_pose(inputs,route,yaw);visible=visible_boundary_cells(inputs[0],mask,stop,view)
   points=tuple(n._grid_to_world(c,r,inputs[0].info) for r,c in sorted(visible) if math.dist(n._grid_to_world(c,r,inputs[0].info),anchor)<=.8)
   key=policy.identify(anchor,stop[:2],observation_points=points);local=n._metric_local_evidence(inputs,policy.attempts[key].frontier_xy)
   eligible=policy.eligible(key,stop[:2],time.monotonic(),inputs[1].fingerprint,local,observation_points=points)
   hits.append(dict(goal=[*xy,yaw],stop=stop,task=key,points=points,eligible=eligible))
print(json.dumps(dict(pose=pose,rejections=rejections,valid=hits),indent=2))
Path('/evidence/ap06-missions-20261005/b71-local-geometry.json').write_text(json.dumps(dict(pose=pose,rejections=rejections,valid=hits),indent=2))
