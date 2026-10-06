"""B76 original snapshot32, analytical existing cooldown elapsed; readonly geometry."""
import copy,math,time,json,pickle
from pathlib import Path
import b73_selection_probe as source
from explore.metric_frontier import MetricCandidate
from explore.metric_frontier_candidates import visible_boundary_cells
b=Path('/evidence/ap06-missions-20261005');source.root=b/'mission-b-v76-capture';n,inputs,p=source.frozen(32)
original_eligible=p.eligible
p.eligible=lambda key,xy,now,*args,**kw:original_eligible(key,xy,now+31,*args,**kw)
# Analytical time counterprobe only. No stored retry_after or try counters changed.
selected=pickle.loads((source.root/'departure-input-4.pickle').read_bytes())['target']
f=selected.frontier_xy;pose=inputs[2];bearing=math.atan2(selected.y-pose[1],selected.x-pose[0]);distance=math.dist((selected.x,selected.y),pose[:2]);scope=n._metric_scope_mask(inputs);rows=[]
for shift in (0.,.05,-.05,.1,-.1,.15,-.15,.2,-.2,.3,-.3):
 angle=bearing+shift;goal=(pose[0]+distance*math.cos(angle),pose[1]+distance*math.sin(angle));facing=math.atan2(f[1]-goal[1],f[0]-goal[0]);error=abs(math.atan2(math.sin(angle-pose[2]),math.cos(angle-pose[2])))
 for yaw in dict.fromkeys((facing,facing+math.pi/2,facing-math.pi/2,angle)):
  route=n._metric_route(inputs,goal,yaw)
  if route is None:continue
  stop=n._metric_rollout_stop_pose(inputs,route,yaw)
  if not n._metric_scan_geometry_ready((inputs[0],inputs[1],stop,*inputs[3:])):continue
  cells=visible_boundary_cells(inputs[0],scope,stop,n._metric_observation_view());points=tuple(n._grid_to_world(c,r,inputs[0].info) for r,c in sorted(cells) if math.dist(n._grid_to_world(c,r,inputs[0].info),f)<=.8)
  served=[a for key,a in p.attempts.items() if key!=selected.task_id and a.completed and a.tries and math.dist(a.target_xy,stop[:2])<p.radius]
  points=tuple(x for x in points if all(math.dist(x,a.frontier_xy)>.8+p.radius for a in served))
  if not points:continue
  if any(p.identify(f,xy,observation_points=points,create=False)!=selected.task_id for xy in (stop[:2],goal)):continue
  local=n._metric_local_evidence(inputs,p.attempts[selected.task_id].frontier_xy)
  if not all(p.eligible(selected.task_id,xy,time.monotonic(),inputs[1].fingerprint,local,observation_points=points) for xy in (stop[:2],goal)):continue
  length=sum(math.dist(a,c) for a,c in zip(route,route[1:]));cost=n._potential_scale*length-n._gain_scale*len(points)*inputs[0].info.resolution+n._heading_scale*error
  rows.append(dict(shift=shift,goal=[*goal,yaw],stop=stop,points=points,cost=cost,task=selected.task_id,original_points=len(selected.observation_points),original_cost=selected.cost))
print('rows',len(rows),flush=True)
for row in sorted(rows,key=lambda a:a['cost'])[:12]:print(json.dumps(row),flush=True)
(b/'b78-bearing-probe.json').write_text(json.dumps(dict(original_pose=pose,analytical_cooldown_seconds=31,rows=rows),indent=2)+'\n')
