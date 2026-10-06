import sys,time,math,json,copy
from pathlib import Path
sys.path.insert(0,'/evidence/ap06-repo/src/explore/test')
import profile_a51 as r
from explore.metric_frontier_candidates import boundary_samples
from explore.metric_frontier import MetricTaskPolicy
from explore.explore_node import Frontier
mask=r.n._metric_scope_mask(r.inputs)
p=MetricTaskPolicy(.6,30.,2)
p.attempts['metric-task-4']=copy.deepcopy(r.policy.attempts['metric-task-4']);p.next_id=4
# Explicit diagnostic history: only actual completed first task retained.
# Later maps/pose remain later, no contemporaneous mission acceptance claim.
for sample in boundary_samples(r.raw,mask,r.n._grid_to_world,.3):
 f=Frontier(sample.xy,sample.size)
 side=r.n._metric_robot_side_observation(r.inputs,f,p,mask,time.monotonic())
 if side:
  print('SIDE',json.dumps(dict(frontier=sample.xy,goal=[side.x,side.y,side.yaw],route=side.route,points=side.observation_points)),flush=True)
print('SELECT',[(c.x,c.y,c.yaw,c.requires_nav2_plan) for c in r.n._metric_select(r.inputs,p,.3)],r.n._frontier_rank_stats,flush=True)
