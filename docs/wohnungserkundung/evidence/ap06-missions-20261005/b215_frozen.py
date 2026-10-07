"""Terminal B214 public geometry, actual recorded TF and original complete task history.
This is a geometry component, not the original live failure entry or health proof.
"""
from pathlib import Path
import math,json,pickle,copy,time
import numpy as np
from rclpy.serialization import deserialize_message
from nav_msgs.msg import OccupancyGrid
from sensor_msgs.msg import LaserScan
import b73_selection_probe as fixture
from explore.metric_frontier import MetricTaskPolicy,MetricAttempt,known_safe_mask
from explore.metric_frontier_runtime import MetricInputs
from explore.metric_frontier_candidates import lidar_view
from explore.portal_memory import PortalMapContext,Point2D
from explore.exploration_scope import AuthorizedExplorationScope
from explore.portal_source_adapter import raw_map_portal_source_from_values,PortalSourceCorrelation
root=Path('/evidence/ap06-missions-20261005');case=root/'mission-b-v214'
def frozen():
 fixture.root=root/'mission-b-v126-entry-diagnostic';n,_,_=fixture.frozen(2)
 record=json.loads((root/'b215-terminal-public-source.json').read_text());state=record['checkpoint']['state'];tfs=record['transforms']
 def yaw(t):
  x,y,z,w=t['rotation'];return math.atan2(2*(w*z+x*y),1-2*(y*y+z*z))
 ref=(*tfs['map->odom']['translation'][:2],yaw(tfs['map->odom']));odom=tfs['odom->base_link'];x,y=odom['translation'][:2]
 pose=(ref[0]+math.cos(ref[2])*x-math.sin(ref[2])*y,ref[1]+math.sin(ref[2])*x+math.cos(ref[2])*y,ref[2]+yaw(odom))
 raw=deserialize_message((case/'final_raw_map.cdr').read_bytes(),OccupancyGrid);cost=deserialize_message((case/'final_costmap.cdr').read_bytes(),OccupancyGrid)
 context=PortalMapContext(**state['context']);scope=AuthorizedExplorationScope(state['scope']['scope_id'],context,tuple(Point2D(*p) for p in state['scope']['vertices']))
 source=raw_map_portal_source_from_values(**n._metric_grid_values(raw));assert source.fingerprint==state['fingerprint']
 correlation=PortalSourceCorrelation(context,0,source.fingerprint,source.source_stamp_ns)
 occupancy=np.asarray(raw.data).reshape(raw.info.height,raw.info.width);q=raw.info.origin.orientation;a=math.atan2(2*(q.w*q.z+q.x*q.y),1-2*(q.y*q.y+q.z*q.z));origin=n._metric_grid_values(raw)['origin'];res=raw.info.resolution
 known,safe=known_safe_mask(occupancy,scope,correlation,origin,a,res,n._goal_clearance_m)
 costs=np.asarray(cost.data).reshape(cost.info.height,cost.info.width);cost_known=(costs>=0)&(costs<100)
 rr,cc=np.nonzero(safe);lx,ly=(cc+.5)*res,(rr+.5)*res
 wx,wy=origin[0]+math.cos(a)*lx-math.sin(a)*ly,origin[1]+math.sin(a)*lx+math.cos(a)*ly
 o=cost.info.origin;q=o.orientation;cyaw=math.atan2(2*(q.w*q.z+q.x*q.y),1-2*(q.y*q.y+q.z*q.z));dx,dy=wx-o.position.x,wy-o.position.y
 cx=np.floor((math.cos(cyaw)*dx+math.sin(cyaw)*dy)/cost.info.resolution).astype(int);cy=np.floor((-math.sin(cyaw)*dx+math.cos(cyaw)*dy)/cost.info.resolution).astype(int)
 valid=(cy>=0)&(cy<costs.shape[0])&(cx>=0)&(cx<costs.shape[1]);allowed=np.zeros(valid.shape,bool);allowed[valid]=(costs[cy[valid],cx[valid]]>=0)&(costs[cy[valid],cx[valid]]<=n._frontier_goal_max_cost);safe[rr[~allowed],cc[~allowed]]=False
 n._metric_scope=scope;n._metric_egress=[];n._metric_egress_expired=True;n._metric_body_anchor_expired=True;n._metric_body_reference=lambda:ref;n._metric_input_reference=ref;n._global_costmap=cost;n._global_costmap_received_at=time.monotonic()
 scan=deserialize_message((case/'final_scan.cdr').read_bytes(),LaserScan);template=pickle.loads((root/'mission-b-v126-entry-diagnostic/selection-object-2.pickle').read_bytes());view=lidar_view(dict(ranges=np.asarray(scan.ranges),angle_min=scan.angle_min,angle_increment=scan.angle_increment,range_min=scan.range_min,range_max=scan.range_max,frame_id=scan.header.frame_id,received_at=time.monotonic()),template['mount'],time.monotonic(),n._door_lidar_scan_timeout,n._door_lidar_max_range)
 n._metric_observation_view=lambda:view
 values=MetricInputs((raw,correlation,pose,known,safe,cost,cost_known),ref,None)
 p=state['policy'];policy=MetricTaskPolicy(p['radius'],p['cooldown_s'],p['retry_limit']);policy.next_id=p['next_id'];now=time.monotonic()
 for key,v in p['tasks'].items():
  d=dict(v);d['frontier_xy']=tuple(d['frontier_xy']);d['target_xy']=tuple(d['target_xy']);d['retry_after']=now+d.pop('retry_remaining_s');policy.attempts[key]=MetricAttempt(**d)
 return n,values,policy
