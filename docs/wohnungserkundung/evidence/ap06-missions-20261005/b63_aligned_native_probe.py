import math,json
from pathlib import Path
import b63_frozen as f
from explore.metric_frontier import rpp_trajectory,footprint_poses_clear,lookahead_point,MetricCandidate
from explore.metric_frontier_runtime import MetricFrontierRuntime
from nav_msgs.msg import Path as NavPath
from geometry_msgs.msg import PoseStamped
r=Path('/evidence/ap06-missions-20261005')
for label in ['true','false','cell-centers-028','cell-centers-0325']:
 record=json.loads((r/('b63-native-plan-probe-'+label)/'native-plans.json').read_text())[0];n,inputs=f.n,f.inputs;pose=inputs[2];path=NavPath();path.header.frame_id='map'
 for x,y in record['points']:
  p=PoseStamped();p.header.frame_id='map';p.pose.position.x=x;p.pose.position.y=y;p.pose.orientation.w=1.;path.poses.append(p)
 target=MetricCandidate('probe',*record['goal'],(0.,0.),(),1.,0.,inputs[1].fingerprint,1)
 path.poses[-1].pose.orientation.z=math.sin(target.yaw/2);path.poses[-1].pose.orientation.w=math.cos(target.yaw/2)
 routes=[];n._metric_standard_waypoints_clear=lambda i,route,yaw:(routes.append(route) or MetricFrontierRuntime._metric_standard_waypoints_clear(n,i,route,yaw))
 n._metric_validate_nav_plan(inputs,path,target,public_only=True);route=routes[-1];leg=lookahead_point(pose[:2],route[1:],.4);angle=math.atan2(leg[1]-pose[1],leg[0]-pose[0]);error=math.atan2(math.sin(angle-pose[2]),math.cos(angle-pose[2]));count=max(1,math.ceil(abs(error)/.01));turn=[(pose[0],pose[1],pose[2]+error*i/count) for i in range(count+1)]
 goodturn=all(footprint_poses_clear(turn,g,allowed,n._world_to_grid,n._metric_bounds,heading_half_angle=.05,center_deviation_m=.02) for g,allowed in ((inputs[0],inputs[3]),(inputs[5],inputs[6])))
 for offset in [0.,-.02,.02]:
  varied=(inputs[0],inputs[1],(*pose[:2],angle+offset),*inputs[3:]);valid=MetricFrontierRuntime._metric_standard_waypoints_clear(n,varied,route,target.yaw)
  print(label,'angle',angle,'turn',goodturn,'offset',offset,'entire_public_motion',valid is not None,'rejection',n._metric_last_route_rejection,flush=True)
