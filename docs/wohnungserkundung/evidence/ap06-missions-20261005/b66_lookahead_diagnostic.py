import json,math
from pathlib import Path
import b66_frozen as f
from explore.metric_frontier import MetricCandidate,rpp_trajectory,footprint_poses_clear,footprint_cells
from nav_msgs.msg import Path as NavPath
from geometry_msgs.msg import PoseStamped
import numpy as np
r=Path('/evidence/ap06-missions-20261005');n,inputs=f.n,f.inputs
records=[]
for label in ('cell-centers-028',):
 data=json.loads((r/('b66-native-plan-probe-'+label)/'native-plans.json').read_text())[0]
 path=NavPath();path.header.frame_id='map'
 for x,y in data['points']:
  p=PoseStamped();p.pose.position.x=x;p.pose.position.y=y;p.pose.orientation.w=1.;path.poses.append(p)
 target=MetricCandidate('probe',*data['goal'],(0.,0.),(),1.,0.,inputs[1].fingerprint,1)
 path.poses[-1].pose.orientation.z=math.sin(target.yaw/2);path.poses[-1].pose.orientation.w=math.cos(target.yaw/2)
 captured=[];original=n._metric_standard_waypoints_clear
 def checked(i,route,yaw,**kw):
  captured.append(route);return original(i,route,yaw,**kw)
 n._metric_standard_waypoints_clear=checked
 valid=n._metric_validate_nav_plan(inputs,path,target,public_only=True)
 n._metric_standard_waypoints_clear=original;route=captured[-1]
 item=dict(label=label,whole_public_valid=valid is not None,rejection=n._metric_last_route_rejection,pose=inputs[2],public_turn_ready=n._metric_public_prealignment_ready(inputs,route),private_start_needed=n._metric_private_start_needed(inputs),path=route,failures=[])
 for distance in (.4,.3,.2,.15):
  aligned=False
  import inspect,explore.metric_frontier as model
  ns=dict(model.__dict__);ns['lookahead']=distance
  ns['route_departure_point']=lambda route,pose,resolution: model.lookahead_point(pose[:2],route[1:],distance)
  exec(inspect.getsource(model.rpp_trajectory).replace('route[index+1:],.4)','route[index+1:],lookahead)'),ns)
  predicted=ns['rpp_trajectory']
  trajectory=predicted(route,inputs[2],inputs[0].info.resolution,.02,n._metric_bounds,prealign_to_first_leg=True,external_prealignment=aligned)
  for index,pose in enumerate(trajectory):
   found=False
   for name,g,allowed in [('raw',inputs[0],inputs[3]),('cost',inputs[5],inputs[6])]:
    if footprint_poses_clear([pose],g,allowed,n._world_to_grid,n._metric_bounds,heading_half_angle=.05,center_deviation_m=.02):continue
    rows,cols=footprint_cells(*pose,g,n._world_to_grid,n._metric_bounds,heading_half_angle=.05,center_deviation_m=.02);inside=(rows>=0)&(rows<allowed.shape[0])&(cols>=0)&(cols<allowed.shape[1]);bad=~inside;bad[inside]|=~allowed[rows[inside],cols[inside]];array=np.asarray(g.data).reshape(allowed.shape)
    cells=[dict(row=int(rr),col=int(cc),xy=n._grid_to_world(int(cc),int(rr),g.info),value=int(array[rr,cc]) if 0<=rr<array.shape[0] and 0<=cc<array.shape[1] else None) for rr,cc in zip(rows[bad],cols[bad])]
    item['failures'].append(dict(diagnostic_lookahead_m=distance,aligned=aligned,index=index,pose=pose,grid=name,cells=cells));found=True;break
   if found:break
  if not found:item['failures'].append(dict(diagnostic_lookahead_m=distance,entire_native_translation_clear=True,stop=trajectory[-1]))
 print({k:v for k,v in item.items() if k!='path'},flush=True);records.append(item)
(r/'b66-diagnostic-lookahead.json').write_text(json.dumps(records,indent=2)+'\n')
