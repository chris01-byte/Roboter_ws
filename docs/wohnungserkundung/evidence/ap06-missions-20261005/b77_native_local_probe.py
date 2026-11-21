import os,sys,time,math,json,numpy as np
from pathlib import Path
from dataclasses import replace
from rclpy.serialization import deserialize_message
from nav_msgs.msg import OccupancyGrid
sys.path.insert(0,'/evidence/ap06-repo/src/explore/test')
from test_metric_frontier import adaptive_fixture
from explore.metric_frontier import known_safe_mask,rpp_trajectory
from explore.portal_memory import Point2D
from explore.portal_source_adapter import PortalSourceCorrelation,raw_map_portal_source_from_values
import b73_local_frozen as recorded
n,inputs,policy=recorded.n,recorded.inputs,recorded.policy
raw,c,pose,known,safe,cost,cost_known=inputs
scope=n._metric_scope
import copy,threading,subprocess,yaml,rclpy
from ament_index_python.packages import get_package_prefix
from geometry_msgs.msg import TransformStamped
from rclpy.node import Node
from rclpy.qos import QoSProfile,DurabilityPolicy
from rclpy.executors import MultiThreadedExecutor
from rclpy.action import ActionClient
from rcl_interfaces.srv import GetParameters
from lifecycle_msgs.srv import ChangeState
from nav2_msgs.action import ComputePathToPose
from tf2_ros import TransformBroadcaster
from explore.metric_frontier import MetricCandidate
from explore.metric_frontier_runtime import MetricInputs
sys.path.insert(0,'/evidence/ap06-repo/tools/simulation')
from ap03_nav2_closed_loop import parameters,wait
os.sched_setaffinity(0,{3})
out=Path('/evidence/ap06-missions-20261005/b77-native-local-probe');out=out.with_name(out.name+'-'+os.environ.get('AP06_PROBE_VARIANT','original'));out.mkdir(exist_ok=True)
import yaml
p=yaml.safe_load((Path('/evidence/ap06-missions-20261005/mission-b-v73-capture/native_params.yaml')).read_text())
p['planner_server']['ros__parameters']['GridBased']['use_astar']=os.environ.get('AP06_PROBE_ASTAR','true')=='true'
p['global_costmap']['global_costmap']['ros__parameters']['robot_radius']=float(os.environ.get('AP06_PROBE_RADIUS','.28'))
(out/'params.yaml').write_text(yaml.safe_dump(p))
rclpy.init();ros=Node('ap06_readonly_recorded_departure_probe');pub=ros.create_publisher(OccupancyGrid,'/map',QoSProfile(depth=1,durability=DurabilityPolicy.TRANSIENT_LOCAL));tf=TransformBroadcaster(ros)
# Original coherent B73 selection14 snapshot; native readonly query only.
def publish():
 raw.header.stamp=ros.get_clock().now().to_msg();pub.publish(raw)
 ts=[]
 for parent,child,xy,a in [('map','odom',(0.,0.),0.),('odom','base_link',inputs[2][:2],inputs[2][2])]:
  t=TransformStamped();t.header.stamp=raw.header.stamp;t.header.frame_id=parent;t.child_frame_id=child;t.transform.translation.x=xy[0];t.transform.translation.y=xy[1];t.transform.rotation.z=math.sin(a/2);t.transform.rotation.w=math.cos(a/2);ts.append(t)
 tf.sendTransform(ts)
ros.create_timer(.05,publish);ex=MultiThreadedExecutor(num_threads=4);ex.add_node(ros);thread=threading.Thread(target=ex.spin,daemon=True);thread.start();processes=[];streams=[]
try:
 for package,name in [('nav2_planner','planner_server'),('nav2_controller','controller_server')]:
  f=(out/(name+'.log')).open('w');streams.append(f);processes.append(subprocess.Popen([str(Path(get_package_prefix(package))/'lib'/package/name),'--ros-args','--params-file',str(out/'params.yaml')],stdout=f,stderr=subprocess.STDOUT))
 for name in ('planner_server','controller_server'):
  client=ros.create_client(ChangeState,'/'+name+'/change_state');assert client.wait_for_service(timeout_sec=20)
  for st in (1,3):
   req=ChangeState.Request();req.transition.id=st;assert wait(client.call_async(req),30).success
 time.sleep(1)
 n._metric_path_validation='rpp_rollout';n._global_costmap=cost;n._metric_scope=scope;n._prealign_handoff_tolerance=.02;n._metric_controller_params=ros.create_client(GetParameters,'/controller_server/get_parameters');n._metric_planner=ActionClient(ros,ComputePathToPose,'/compute_path_to_pose');n._metric_status={};n._metric_lock=threading.RLock();n._metric_work_context=lambda:('recorded-component',);n._metric_work_is_current=lambda c:c==('recorded-component',);n.get_clock=ros.get_clock;n._metric_active=None;n._metric_plan_after_ns=None
 calls=[];request_plan=n._metric_request_nav_plan
 def record_plan(target,stop_requested,**kwargs):
  path,error=request_plan(target,stop_requested,**kwargs)
  calls.append(dict(start_pose=kwargs.get('start_pose'),goal=[target.x,target.y,target.yaw],error=error,points=[] if path is None else [[p.pose.position.x,p.pose.position.y] for p in path.poses]))
  return path,error
 n._metric_request_nav_plan=record_plan
 results=[]
 from explore.explore_node import Frontier
 choices=[(1.9049999574199319,-.4949999889358878,0.)]
 for x,y,yaw in choices:
  xy=(x,y)
  target=MetricCandidate('probe',*xy,yaw,(1.304999970830977,.13499999698251486),(),1.,0.,c.fingerprint,1)
  path,error=n._metric_request_nav_plan(target,lambda:False)
  route=None if path is None else n._metric_validate_nav_plan(inputs,path,target,public_only=True)
  item=dict(goal=[*xy,yaw],arrival_plan_valid=route is not None,arrival_rejection=error if path is None else n._metric_last_route_rejection,kind='Original B73 after-fourth-observation selection14 raw/cost rasters, recorded map pose, native CPP read-only query; no motion or whole acceptance')
  if route is not None:
   projected=n._metric_rollout_stop_pose(inputs,route,target.yaw,native_plan=True)
   item.update(projected_stop=projected,path_endpoint=route[-1],stop_goal_distance=math.dist(projected[:2],xy),scan_ready=n._metric_scan_geometry_ready((inputs[0],inputs[1],projected,*inputs[3:])))
   item['departure_valid']=n._metric_departure_plan_ready(inputs,route,target,lambda:False)
  item['astar']=os.environ.get('AP06_PROBE_ASTAR','true');print(item,flush=True);results.append(item)
  # keep all measured alternatives
 (out/'result.json').write_text(json.dumps(results,indent=2));(out/'native-plans.json').write_text(json.dumps(calls,indent=2))
finally:
 for proc in processes:
  if proc.poll() is None:proc.send_signal(2)
 for proc in processes:
  try:proc.wait(timeout=5)
  except subprocess.TimeoutExpired:proc.kill();proc.wait()
 ex.shutdown(timeout_sec=3);thread.join(timeout=3);ros.destroy_node();rclpy.shutdown()
 for f in streams:f.close()
