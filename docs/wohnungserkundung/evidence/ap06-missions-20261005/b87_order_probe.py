"""Original coherent B76 pre-third selection; analytical existing cooldown elapsed only."""
import sys,math,time,json,pickle
from pathlib import Path
sys.path.insert(0,'/evidence/ap06-missions-20261005')
import b80_frozen as r
from explore.metric_frontier_candidates import visible_boundary_cells,boundary_samples
n,i,p=r.n,r.inputs,r.policy
old=p.eligible;p.eligible=lambda key,xy,now,*a,**kw:old(key,xy,now+31,*a,**kw)
sel=pickle.load(open('/evidence/ap06-missions-20261005/mission-b-v76-capture/departure-input-4.pickle','rb'))['target']
scope=n._metric_scope_mask(i);rows=[]
for angle in (-math.pi/2,math.pi,0.,math.pi/2):
 for d in (.6,.45,.3,.33):
  goal=(i[2][0]+d*math.cos(angle),i[2][1]+d*math.sin(angle));face=math.atan2(sel.frontier_xy[1]-goal[1],sel.frontier_xy[0]-goal[0])
  for yaw in (face,face+math.pi/2,face-math.pi/2,angle):
   route=n._metric_route(i,goal,yaw)
   if route is None:continue
   stop=n._metric_rollout_stop_pose(i,route,yaw)
   if not n._metric_scan_geometry_ready((i[0],i[1],stop,*i[3:])):continue
   cells=visible_boundary_cells(i[0],scope,stop,n._metric_observation_view())
   pts=tuple(n._grid_to_world(c,r,i[0].info) for r,c in sorted(cells) if math.dist(n._grid_to_world(c,r,i[0].info),sel.frontier_xy)<=.8)
   served=[a for key,a in p.attempts.items() if key!=sel.task_id and a.completed and a.tries and math.dist(a.target_xy,stop[:2])<p.radius]
   pts=tuple(x for x in pts if all(math.dist(x,a.frontier_xy)>.8+p.radius for a in served))
   if not pts:continue
   same=all(p.identify(sel.frontier_xy,xy,observation_points=pts,create=False)==sel.task_id for xy in (stop[:2],goal))
   ev=n._metric_local_evidence(i,p.attempts[sel.task_id].frontier_xy)
   eligible=same and all(p.eligible(sel.task_id,xy,time.monotonic(),i[1].fingerprint,ev,observation_points=pts) for xy in (stop[:2],goal))
   error=abs(math.atan2(math.sin(angle-i[2][2]),math.cos(angle-i[2][2])));length=sum(math.dist(a,b) for a,b in zip(route,route[1:]));cost=n._potential_scale*length-n._gain_scale*len(pts)*i[0].info.resolution+n._heading_scale*error
   rows.append(dict(angle=angle,distance=d,goal=[*goal,yaw],stop=stop,points=pts,cost=cost,eligible=eligible))
print(json.dumps(rows,indent=2),flush=True)
Path('/evidence/ap06-missions-20261005/b87-order-probe.json').write_text(json.dumps(rows,indent=2))
