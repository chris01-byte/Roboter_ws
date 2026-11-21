import time,json,copy
import profile_a52 as r
import explore.metric_frontier_runtime as module
from explore.metric_frontier import MetricTaskPolicy
from explore.explore_node import Frontier
mask=r.n._metric_scope_mask(r.inputs);f=Frontier((1.304999970830977,.13499999698251486),1)
metrics={'visibility_calls':0,'visibility_s':0.,'route_calls':0,'route_s':0.}
view=module.visible_boundary_cells;route=r.n._metric_route
calls=[]
def measured_view(*args,**kwargs):
 began=time.monotonic();result=view(*args,**kwargs);metrics['visibility_calls']+=1;metrics['visibility_s']+=time.monotonic()-began;return result
def measured_route(*args,**kwargs):
 began=time.monotonic();result=route(*args,**kwargs);metrics['route_calls']+=1;metrics['route_s']+=time.monotonic()-began;calls.append(dict(goal=args[1],yaw=args[2],valid=result is not None));return result
module.visible_boundary_cells=measured_view;r.n._metric_route=measured_route
p=MetricTaskPolicy(.6,30.,2);p.attempts['metric-task-4']=copy.deepcopy(r.policy.attempts['metric-task-4']);p.next_id=4
began=time.monotonic();candidate=r.n._metric_robot_side_observation(r.inputs,f,p,mask,began)
print('MEASURED',json.dumps(dict(metrics=metrics,elapsed_s=time.monotonic()-began,candidate=None if candidate is None else [candidate.x,candidate.y,candidate.yaw],calls=calls)),flush=True)
