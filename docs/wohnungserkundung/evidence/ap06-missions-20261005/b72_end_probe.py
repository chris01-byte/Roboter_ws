"""B72 last received synthetic rasters and preserved checkpoint history.
Not a simultaneous failing selection snapshot; component performance only.
"""
import sys,json,time,cProfile,pstats
from pathlib import Path
from dataclasses import replace
import numpy as np
sys.path.insert(0,'/evidence/ap06-repo/src/explore/test')
from test_metric_public_cooldown import frozen
from rclpy.serialization import deserialize_message
from nav_msgs.msg import OccupancyGrid
from sensor_msgs.msg import LaserScan
from explore.metric_frontier import MetricTaskPolicy,MetricAttempt,known_safe_mask
from explore.metric_frontier_runtime import MetricInputs
from explore.metric_frontier_candidates import lidar_view
from explore.portal_memory import PortalMapContext,Point2D
from explore.portal_source_adapter import PortalSourceCorrelation,raw_map_portal_source_from_values
from explore.exploration_scope import AuthorizedExplorationScope
r=Path('/evidence/ap06-missions-20261005/mission-b-v72')
result=json.loads((r/'result.json').read_text());saved=json.loads((r/'saved-checkpoint-evidence.json').read_text())['state']
n,_,_=frozen('ap06_b70_after_observation')
grid=deserialize_message((r/'final_raw_map.cdr').read_bytes(),OccupancyGrid)
cost=deserialize_message((r/'final_costmap.cdr').read_bytes(),OccupancyGrid)
scan=deserialize_message((r/'final_scan.cdr').read_bytes(),LaserScan)
ctx=PortalMapContext(**saved['context']);source=raw_map_portal_source_from_values(**n._metric_grid_values(grid));cor=PortalSourceCorrelation(ctx,1,source.fingerprint,source.source_stamp_ns)
n._metric_scope=AuthorizedExplorationScope(saved['scope']['scope_id'],ctx,tuple(Point2D(*xy) for xy in saved['scope']['vertices']))
q=grid.info.origin.orientation;import math
yaw=math.atan2(2*q.w*q.z,1-2*q.z*q.z);v=n._metric_grid_values(grid)
known,safe=known_safe_mask(np.asarray(grid.data).reshape(grid.info.height,grid.info.width),n._metric_scope,cor,v['origin'],yaw,grid.info.resolution,n._goal_clearance_m)
cost_data=np.asarray(cost.data).reshape(cost.info.height,cost.info.width)
cost_known=(cost_data>=0)&(cost_data<100)
for row,col in zip(*np.nonzero(safe)):
 xy=n._grid_to_world(col,row,grid.info);c,r0=n._world_to_grid(*xy,cost.info)
 if not (0<=r0<cost.info.height and 0<=c<cost.info.width and 0<=cost_data[r0,c]<=n._frontier_goal_max_cost):safe[row,col]=False
state=result['metric']['decision_snapshot']['encoder_state'];pose=(state['x'],state['y'],state['yaw'])
ref=tuple(result['metric']['start_reference']['current'])
inputs=MetricInputs((grid,cor,pose,known,safe,cost,cost_known),ref)
n._metric_egress_expired=True;n._metric_egress=None;n._metric_body_anchor_expired=True;n._global_costmap=cost;n._metric_status={}
now=time.monotonic();snap=dict(received_at=now,ranges=np.asarray(scan.ranges),angle_min=scan.angle_min,angle_increment=scan.angle_increment,range_min=scan.range_min,range_max=scan.range_max)
mount=(.245,0.,math.pi/2);view=lidar_view(snap,mount,now,.5,4.);n._metric_observation_view=lambda:view
p=saved['policy'];policy=MetricTaskPolicy(p['radius'],p['cooldown_s'],p['retry_limit']);policy.next_id=p['next_id']
for k,a in p['tasks'].items():
 d=dict(a);d['retry_after']=now+d.pop('retry_remaining_s');d['frontier_xy']=tuple(d['frontier_xy']);d['target_xy']=tuple(d['target_xy']);policy.attempts[k]=MetricAttempt(**d)
if __name__=='__main__':
 calls={};original=n._metric_route
 def counted(i,target,yaw=None):
  key=(tuple(target),yaw);calls[key]=calls.get(key,0)+1
  return original(i,target,yaw)
 n._metric_route=counted
 profiler=cProfile.Profile();start=time.monotonic();out={}
 try:out['candidates']=profiler.runcall(n._metric_select,inputs,policy,.3)
 except Exception as e:out['error']=str(e)
 out['route_calls']=sum(calls.values());out['route_unique']=len(calls);out['most_repeated_routes']=sorted(calls.values(),reverse=True)[:20];out['seconds']=time.monotonic()-start;out['ranking']=n._frontier_rank_stats
 print(json.dumps(out,default=str,indent=2),flush=True);profiler.dump_stats('/evidence/ap06-missions-20261005/b72-end-selection.prof');pstats.Stats(profiler).sort_stats('cumulative').print_stats(30)
