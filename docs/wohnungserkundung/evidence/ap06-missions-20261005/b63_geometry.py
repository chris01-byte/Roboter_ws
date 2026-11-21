import sys,math,json,numpy as np
from pathlib import Path
from rclpy.serialization import deserialize_message
from nav_msgs.msg import OccupancyGrid,Path as NavPath
from geometry_msgs.msg import PoseStamped
sys.path.insert(0,'/evidence/ap06-repo/src/explore/test')
from test_metric_frontier import adaptive_fixture
from explore.metric_frontier import known_safe_mask,MetricCandidate,rpp_trajectory,footprint_cells,footprint_poses_clear
from explore.portal_memory import PortalMapContext,Point2D
from explore.portal_source_adapter import PortalSourceCorrelation,raw_map_portal_source_from_values
from explore.exploration_scope import AuthorizedExplorationScope
r=Path('/evidence/ap06-missions-20261005');b=r/'mission-b-v63';d=json.loads((b/'result.json').read_text());m=d['metric'];s=json.loads(Path(m['persistence']['path']).read_text())['state']
n,_=adaptive_fixture();ctx=PortalMapContext(**s['context']);n._metric_scope=AuthorizedExplorationScope(s['scope']['scope_id'],ctx,tuple(Point2D(*xy) for xy in s['scope']['vertices']))
raw=deserialize_message((b/'final_raw_map.cdr').read_bytes(),OccupancyGrid);cost=deserialize_message((b/'final_costmap.cdr').read_bytes(),OccupancyGrid)
a=np.asarray(raw.data).reshape(raw.info.height,raw.info.width);ca=np.asarray(cost.data).reshape(cost.info.height,cost.info.width)
source=raw_map_portal_source_from_values(**n._metric_grid_values(raw));cor=PortalSourceCorrelation(ctx,1,source.fingerprint,source.source_stamp_ns)
known,safe=known_safe_mask(a,n._metric_scope,cor,(raw.info.origin.position.x,raw.info.origin.position.y),0.,raw.info.resolution,.28)
n._metric_path_validation='rpp_rollout';n._prealign_handoff_tolerance=.02;n._metric_start_egress_enabled=False
pose=tuple(m['arrival_check']['pose']);inputs=(raw,cor,pose,known,safe,cost,(ca>=0)&(ca<100));plans=json.loads((r/'b63-recorded-plans.json').read_text());record=plans[-1]
target=MetricCandidate('recorded',*m['arrival_check']['goal'],(0.,0.),(),0.,0.,cor.fingerprint,1)
path=NavPath();path.header.frame_id='map'
for x,y in record['points']:
 p=PoseStamped();p.header.frame_id='map';p.pose.position.x=x;p.pose.position.y=y;p.pose.orientation.w=1.;path.poses.append(p)
path.poses[-1].pose.orientation.z=math.sin(target.yaw/2);path.poses[-1].pose.orientation.w=math.cos(target.yaw/2)
routes=[];original=n._metric_standard_waypoints_clear
n._metric_standard_waypoints_clear=lambda i,route,yaw:(routes.append(route) or original(i,route,yaw))
route=n._metric_validate_nav_plan(inputs,path,target,public_only=True);print('recorded validation',route is not None,n._metric_last_route_rejection,'pose',pose)
trajectory=rpp_trajectory(routes[-1],pose,min(raw.info.resolution,cost.info.resolution),.02,n._metric_bounds,prealign_to_first_leg=True,external_prealignment=False)
print('trajectory poses',len(trajectory),'last',trajectory[-1]);failures=[]
for label,g,allowed in [('raw',raw,known),('cost',cost,inputs[6])]:
 values=np.asarray(g.data).reshape(allowed.shape)
 for index,p in enumerate(trajectory):
  if not footprint_poses_clear([p],g,allowed,n._world_to_grid,n._metric_bounds,heading_half_angle=.05,center_deviation_m=.02):
   rr,cc=footprint_cells(*p,g,n._world_to_grid,n._metric_bounds,heading_half_angle=.05,center_deviation_m=.02)
   inside=(rr>=0)&(rr<allowed.shape[0])&(cc>=0)&(cc<allowed.shape[1]);bad=inside.copy();bad[inside]=~allowed[rr[inside],cc[inside]]
   cells=[dict(cell=[int(row),int(col)],xy=n._grid_to_world(int(col),int(row),g.info),occupancy=int(values[row,col]) if 0<=row<values.shape[0] and 0<=col<values.shape[1] else 'outside') for row,col in zip(rr[bad],cc[bad])]
   item=dict(grid=label,index=index,pose=p,cells=cells);print('first violation',label,index,p,cells[:6]);failures.append(item);break
(r/'b63-path-diagnostic.json').write_text(json.dumps(dict(kind='Recorded real Nav2 path checked against later stationary terminal rasters, not an exact failure snapshot or acceptance',route=routes[-1],trajectory=trajectory,failures=failures),indent=2)+'\n')
