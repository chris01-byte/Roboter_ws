#!/usr/bin/env python3
"""AP-03: real Nav2 actions, synthetic world/odom, independent geometry oracle.

No hardware graph, actuator/health mocks or deployment. Run in an isolated ROS
Humble container. Component goals are explicit; only bootstrap uses the actual
Explorer frontier selection. Wall-clock plant, 100-Hz exact unicycle integration,
50-ms first-order motor response; this is NOT a hardware tracking qualification.
"""
import argparse
import copy
import json
import math
import os
import signal
from pathlib import Path
import subprocess
import sys
import threading
import time

import numpy as np
import rclpy
import yaml
from action_msgs.msg import GoalStatus
from geometry_msgs.msg import PoseStamped, TransformStamped, Twist
from lifecycle_msgs.srv import ChangeState
from rcl_interfaces.srv import GetParameters
from nav_msgs.msg import OccupancyGrid, Odometry
from nav2_msgs.action import ComputePathToPose, FollowPath
from rclpy.action import ActionClient
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from rclpy.qos import QoSProfile, DurabilityPolicy, ReliabilityPolicy
from tf2_ros import TransformBroadcaster
from scipy.spatial import cKDTree

from ament_index_python.packages import get_package_prefix
from explore.explore_node import ExploreNode
from explore.metric_frontier import MetricCandidate, MetricTaskPolicy, known_safe_mask, rpp_trajectory, route_departure_point
from explore.exploration_scope import AuthorizedExplorationScope
from explore.portal_memory import Point2D, PortalMapContext
from explore.portal_source_adapter import PortalSourceCorrelation, raw_map_portal_source_from_values
from explore.metric_frontier_runtime import MetricFrontierRuntime


def polygon(pose, padded=True):
    x,y,yaw=pose;c,s=math.cos(yaw),math.sin(yaw)
    bounds=(-.13,.33,-.25,.25) if padded else (-.11,.31,-.23,.23)
    l,r,b,t=bounds
    return np.array([(x+c*a-s*b,y+s*a+c*b) for a,b in ((l,b),(r,b),(r,t),(l,t))])


def clearance(a,b):
    # Independent separating-axis intersection + exact edge/vertex distance.
    for poly in (a,b):
        for edge in np.roll(poly,-1,axis=0)-poly:
            axis=np.array([-edge[1],edge[0]]);pa,pb=a@axis,b@axis
            if pa.max()<pb.min() or pb.max()<pa.min():break
        else:continue
        break
    else:return 0.
    result=float('inf')
    for points,edges in ((a,b),(b,a)):
        for start,end in zip(edges,np.roll(edges,-1,axis=0)):
            v=end-start;f=np.clip((points-start)@v/(v@v),0,1)
            result=min(result,float(np.linalg.norm(points-start-f[:,None]*v,axis=1).min()))
    return result


def rect(x0,x1,y0,y1):return np.array([(x0,y0),(x1,y0),(x1,y1),(x0,y1)])


class World(Node):
    def __init__(self, case):
        super().__init__('ap03_world')
        self.case=case;self.pose=np.array([-.9,0.,0.]);self.command=np.zeros(2);self.velocity=np.zeros(2)
        self.cmd_at=0.;self.moving=False;self.trace=[];self.min_clearance=float('inf');self.reverse=0;self.nonzero_commands=0
        self.obstacles=[rect(-2,-1.96,-2,2),rect(1.96,2,-2,2),rect(-2,2,-2,-1.96),rect(-2,2,1.96,2)]
        if case.startswith('door') or case in ('unknown_outer','rotation_narrow'):
            width=.8 if case=='door80' else .56 if case=='door56' else .68
            self.obstacles += [rect(-.1,.1,-2,-width/2),rect(-.1,.1,width/2,2)]
            if case=='rotation_narrow':self.pose[0]=0.
        elif case=='detour':
            self.obstacles += [rect(-.15,.15,-.8,.25),rect(-2,2,.93,2)]
        elif case in ('bootstrap','blind_start'):
            self.pose=np.array([-.9,0.,0.])
            self.obstacles += [rect(-2,2,-.84,-.8),rect(-2,2,.8,.84)]
        self.grid=OccupancyGrid();g=self.grid;g.header.frame_id='map';g.info.resolution=.02
        g.info.width=g.info.height=200;g.info.origin.position.x=g.info.origin.position.y=-2.;g.info.origin.orientation.w=1.
        rr,cc=np.indices((200,200));self.xx=-2+(cc+.5)*.02;self.yy=-2+(rr+.5)*.02
        self.truth=np.zeros((200,200),np.int8)
        for o in self.obstacles:
            self.truth[(self.xx>=o[:,0].min())&(self.xx<o[:,0].max())&(self.yy>=o[:,1].min())&(self.yy<o[:,1].max())]=100
        self.observed=np.ones((200,200),bool)
        if case=='unknown_outer':self.observed[self.xx>.25]=False
        if case in ('bootstrap','blind_start'):
            # A finite forward depth view and initial body neighbourhood. Rear
            # exterior is deliberately unobserved, so full rotation is unsafe.
            self.observed[:]=False;self.observe()
            if case=='blind_start':self.observed[(self.xx>-.65)&(np.abs(self.yy)<.5)]=False
        qos=QoSProfile(depth=1,durability=DurabilityPolicy.TRANSIENT_LOCAL,reliability=ReliabilityPolicy.RELIABLE)
        self.map_pub=self.create_publisher(OccupancyGrid,'/map',qos)
        self.odom_pub=self.create_publisher(Odometry,'/odom',10);self.tf=TransformBroadcaster(self)
        self.create_subscription(Twist,'/cmd_vel',self.cmd,10)
        self.cost=None;self.create_subscription(OccupancyGrid,'/global_costmap/costmap',lambda msg:setattr(self,'cost',msg),qos)
        self.create_timer(.01,self.tick);self.create_timer(.2,self.publish_map);self.last=time.monotonic();self.publish_map()

    def observe(self):
        if self.case not in ('bootstrap','blind_start'):return
        x,y,yaw=self.pose;dx,dy=self.xx-x,self.yy-y
        # Explicit idealized forward coverage, not an assertion about OAK/VL53.
        forward=np.cos(yaw)*dx+np.sin(yaw)*dy;side=-np.sin(yaw)*dx+np.cos(yaw)*dy
        visible=(forward>=-.2)&(forward<=1.35)&(np.abs(side)<=.85)
        # Independent world-only occlusion: no free cell behind a wall may
        # become observed merely because it lies in the rectangular view.
        for obstacle in self.obstacles:
            with np.errstate(divide='ignore',invalid='ignore'):
                tx=np.stack(((obstacle[:,0].min()-x)/dx,(obstacle[:,0].max()-x)/dx))
                ty=np.stack(((obstacle[:,1].min()-y)/dy,(obstacle[:,1].max()-y)/dy))
            enter=np.maximum(tx.min(axis=0),ty.min(axis=0));leave=np.minimum(tx.max(axis=0),ty.max(axis=0))
            blocked=(np.maximum(enter,0.)<=np.minimum(leave,1.))&(enter<1.-1e-8)
            visible &= ~blocked | (self.truth==100)
        self.observed |= visible

    def publish_map(self):
        self.grid.header.stamp=self.get_clock().now().to_msg()
        self.grid.data=np.where(self.observed,self.truth,-1).ravel().tolist();self.map_pub.publish(self.grid)

    def cmd(self,msg):
        self.command[:]=msg.linear.x,msg.angular.z;self.cmd_at=time.monotonic()
        self.nonzero_commands+=int(abs(msg.linear.x)+abs(msg.angular.z)>1e-9)

    def tick(self):
        now=time.monotonic();dt=min(.025,now-self.last);self.last=now
        desired=self.command if self.moving and now-self.cmd_at<.2 else np.zeros(2)
        self.velocity += (desired-self.velocity)*(1-math.exp(-dt/.05))
        v,w=self.velocity;x,y,yaw=self.pose
        if abs(w)>1e-9:
            self.pose[0]+=v/w*(math.sin(yaw+w*dt)-math.sin(yaw));self.pose[1]-=v/w*(math.cos(yaw+w*dt)-math.cos(yaw))
        else:self.pose[:2]+=v*dt*np.array([math.cos(yaw),math.sin(yaw)])
        self.pose[2]=math.atan2(math.sin(yaw+w*dt),math.cos(yaw+w*dt))
        if self.moving:
            distance=min(clearance(polygon(self.pose),o) for o in self.obstacles)
            self.min_clearance=min(self.min_clearance,distance)
            if distance<=0:raise RuntimeError('independent ground-truth collision')
            self.reverse+=int(v<-.0001);self.trace.append([now,*self.pose,v,w]);self.observe()
        stamp=self.get_clock().now().to_msg();transforms=[]
        for parent,child,px,py,angle in [('map','odom',0.,0.,0.),('odom','base_link',*self.pose)]:
            t=TransformStamped();t.header.stamp=stamp;t.header.frame_id=parent;t.child_frame_id=child
            t.transform.translation.x=float(px);t.transform.translation.y=float(py);t.transform.rotation.z=math.sin(angle/2);t.transform.rotation.w=math.cos(angle/2);transforms.append(t)
        self.tf.sendTransform(transforms)
        o=Odometry();o.header.stamp=stamp;o.header.frame_id='odom';o.child_frame_id='base_link';o.pose.pose.position.x=float(self.pose[0]);o.pose.pose.position.y=float(self.pose[1]);o.pose.pose.orientation=transforms[1].transform.rotation
        o.twist.twist.linear.x=float(v);o.twist.twist.angular.z=float(w);self.odom_pub.publish(o)


def wait(future,timeout=15):
    deadline=time.monotonic()+timeout
    while not future.done() and time.monotonic()<deadline:time.sleep(.01)
    if not future.done():raise TimeoutError('ROS future')
    return future.result()


def fixture(world, model):
    n=ExploreNode.__new__(ExploreNode);g=copy.deepcopy(world.grid);a=np.asarray(g.data).reshape(200,200)
    context=PortalMapContext('ap03','world','map')
    fp=raw_map_portal_source_from_values(**MetricFrontierRuntime._metric_grid_values(g)).fingerprint
    c=PortalSourceCorrelation(context,1,fp,g.header.stamp.sec*10**9+g.header.stamp.nanosec)
    scope=AuthorizedExplorationScope('synthetic',context,tuple(Point2D(x,y) for x,y in ((-1.95,-1.95),(1.95,-1.95),(1.95,1.95),(-1.95,1.95))))
    values=dict(_metric_scope=scope,_metric_path_validation=model,_metric_bounds=(-.13,.33,-.25,.25),_metric_start_strategy='adaptive',_global_frame='map',_goal_clearance_m=.28,_frontier_goal_max_cost=90,_goal_search_m=.3,_approach_dist_m=.6,_min_goal_dist_m=.3,_frontier_forward_cone_half_angle=0.,_potential_scale=3.,_gain_scale=1.,_heading_scale=.75,_visualize=False,_wohnungserkundung_evidence_max_cells=1000000,_metric_nav_path=None,_prealign_enabled=True,_prealign_handoff_tolerance=.02,_prealign_stop_margin=.01,_prealign_speed=.12,_prealign_timeout=30.,_prealign_rate_check_after=15.,_prealign_min_average_rate=.01,_prealign_settle_s=.1,_prealign_max_passes=3,_prealign_min_improvement=.005)
    for k,v in values.items():setattr(n,k,v)
    known,safe=known_safe_mask(a,scope,c,(-2.,-2.),0.,.02,.28)
    cost=world.cost or g;costs=np.asarray(cost.data).reshape(cost.info.height,cost.info.width)
    return n,[g,c,tuple(world.pose),known,safe,cost,(costs>=0)&(costs<100)]


def parameters(repo,out):
    config=yaml.safe_load((repo/'src/robot_navigation/config/nav2_params_real.yaml').read_text())
    selected={name:config[name] for name in ('planner_server','controller_server','global_costmap','local_costmap')}
    # Same actual planner/controller geometry. Static synthetic observations
    # replace physical sensor transports; no unknown-space clearing plugins.
    for name in ('global_costmap','local_costmap'):
        p=selected[name][name]['ros__parameters'];p.update(plugins=['static_layer','inflation_layer'],track_unknown_space=True,always_send_full_costmap=True,rolling_window=False,resolution=.02,global_frame='map',update_frequency=20.,publish_frequency=10.)
        p['static_layer']={'plugin':'nav2_costmap_2d::StaticLayer','map_subscribe_transient_local':True,'subscribe_to_updates':False}
    out.write_text(yaml.safe_dump(selected))


def run(case,args):
    out=args.output/case;out.mkdir(parents=True,exist_ok=True);params=out/'params.yaml';parameters(args.repo,params)
    rclpy.init();world=World(case);executor=MultiThreadedExecutor(num_threads=4);executor.add_node(world)
    thread=threading.Thread(target=executor.spin,daemon=True);thread.start();processes=[];streams=[]
    result={'case':case,'ros_domain_id':int(os.environ['ROS_DOMAIN_ID']),'model':'wall-clock unicycle + 50ms first-order response','hardware_qualified':False,'planner':'nav2_navfn_planner/NavfnPlanner','controller':'nav2_regulated_pure_pursuit_controller::RegulatedPurePursuitController'}
    try:
        for package,executable in [('nav2_planner','planner_server'),('nav2_controller','controller_server')]:
            stream=(out/(executable+'.log')).open('w');streams.append(stream)
            processes.append(subprocess.Popen([str(Path(get_package_prefix(package))/'lib'/package/executable),'--ros-args','--params-file',str(params)],stdout=stream,stderr=subprocess.STDOUT,start_new_session=True))
        for name in ('planner_server','controller_server'):
            client=world.create_client(ChangeState,'/'+name+'/change_state');assert client.wait_for_service(timeout_sec=20),name
            for state in (1,3):
                req=ChangeState.Request();req.transition.id=state;assert wait(client.call_async(req),30).success,(name,state)
        time.sleep(1.)
        n,inputs=fixture(world,'rpp_rollout');before=int(np.count_nonzero(world.observed));target=(.9,0.);yaw=0.
        n._metric_controller_params=world.create_client(GetParameters,'/controller_server/get_parameters')
        n._metric_status={}
        assert n._metric_controller_contract(lambda:False),'actual controller parameter contract'
        result['controller_parameter_contract']=True
        if case=='rotation_narrow':target=(0.,0.);yaw=math.pi/2
        if case=='door68_stop':target=(0.,0.)
        if case in ('bootstrap','blind_start'):
            decision,candidates=n._metric_start_decision(inputs,MetricTaskPolicy(.6,30.,2),.3,True)
            result['bootstrap_decision']=decision;result['candidate_count']=len(candidates)
            if case=='blind_start':
                assert decision['selected_motion']=='wait' and not candidates
                result['passed']=True;return result
            assert decision['selected_motion']=='observation_goal' and candidates
            target=(candidates[0].x,candidates[0].y);yaw=candidates[0].yaw
            result['selected_goal']=target
        result['own_route_accepted']=n._metric_route(inputs,target,yaw) is not None
        old,old_inputs=fixture(world,'conservative');result['previous_envelope_accepted']=old._metric_route(old_inputs,target,yaw) is not None
        planner=ActionClient(world,ComputePathToPose,'/compute_path_to_pose');assert planner.wait_for_server(timeout_sec=5)
        goal=ComputePathToPose.Goal();goal.planner_id='GridBased';goal.use_start=True
        for pose,xy in ((goal.start,world.pose[:2]),(goal.goal,target)):
            pose.header.frame_id='map';pose.header.stamp=world.get_clock().now().to_msg();pose.pose.position.x=float(xy[0]);pose.pose.position.y=float(xy[1]);pose.pose.orientation.w=1.
        goal.goal.pose.orientation.z=math.sin(yaw/2);goal.goal.pose.orientation.w=math.cos(yaw/2)
        handle=wait(planner.send_goal_async(goal));assert handle.accepted
        planned=wait(handle.get_result_async(),30);result['planner_status']=planned.status
        if case=='unknown_outer':
            assert planned.status!=GoalStatus.STATUS_SUCCEEDED
            assert n._metric_nav2_proposal(inputs,target,yaw) is None
            assert world.nonzero_commands==0;result['nonzero_commands']=0
            result['passed']=True;return result
        if case in ('door56','rotation_narrow'):
            assert n._metric_waypoints_clear(inputs,(tuple(world.pose[:2]),target),yaw) is None
            result['geometry_rejection']=n._metric_last_route_rejection
            if planned.status==GoalStatus.STATUS_SUCCEEDED:
                candidate=MetricCandidate('negative',*target,yaw,target,(),1.,0.,inputs[1].fingerprint,1)
                assert n._metric_validate_nav_plan(inputs,planned.result.path,candidate) is None
            # A failed full-body proof must prevent the child action. Testing
            # this gate does not claim NavFn's point model validates rotation.
            assert world.nonzero_commands==0;result['nonzero_commands']=0
            result['follow_path_sent']=False;result['passed']=True;return result
        assert planned.status==GoalStatus.STATUS_SUCCEEDED
        path=planned.result.path;points=[(p.pose.position.x,p.pose.position.y) for p in path.poses]
        result['path_length_m']=sum(math.dist(a,b) for a,b in zip(points,points[1:]));(out/'path.json').write_text(json.dumps(points))
        candidate=MetricCandidate('component',*target,yaw,target,tuple(points),result['path_length_m'],0.,inputs[1].fingerprint,1)
        route=n._metric_validate_nav_plan(inputs,path,candidate)
        result['geometry_rejection']=n._metric_last_route_rejection
        assert route is not None,result
        if case=='door68':
            # The same passage has no room for an arbitrary full turn.
            spin_inputs=list(inputs);spin_inputs[2]=(0.,0.,0.)
            decision,_=n._metric_start_decision(spin_inputs,MetricTaskPolicy(.6,30.,2),.3,True)
            assert not decision['scan_admissible'];result['narrow_rotation_rejected']=True
        # Actual Explorer alignment algorithm; its world transport emits only
        # synthetic twists and returns measured synthetic odometry. Full
        # hardware/HWT/mission gates are outside this component experiment.
        pub=world.create_publisher(Twist,'/cmd_vel',10)
        def rotate(angle,speed,timeout,**kwargs):
            start=float(world.pose[2]);deadline=time.monotonic()+timeout
            while time.monotonic()<deadline:
                achieved=math.atan2(math.sin(world.pose[2]-start),math.cos(world.pose[2]-start))
                if abs(achieved)>=abs(angle):break
                msg=Twist();msg.angular.z=math.copysign(speed,angle);pub.publish(msg);time.sleep(.01)
            pub.publish(Twist());time.sleep(.25)
            achieved=math.atan2(math.sin(world.pose[2]-start),math.cos(world.pose[2]-start))
            return ('success' if abs(achieved)>=abs(angle) else 'timeout'),achieved
        n._rotate_in_place=rotate;n._robot_pose=lambda:tuple(world.pose);n.get_logger=world.get_logger
        world.moving=True
        alignment=n._prealign_to_goal(*route_departure_point(route,tuple(world.pose),.02),tuple(world.pose))
        assert alignment[0] in ('success','skipped'),alignment
        result['alignment']=alignment
        if world.trace:np.savetxt(out/'alignment.csv',np.asarray(world.trace),delimiter=',')
        world.trace=[]
        expected=np.asarray(rpp_trajectory(route,tuple(world.pose),.02,.02,prealign_to_first_leg=True))
        # RPP switches to goal yaw once inside the actual 0.15-m disk. The
        # independent product goal proof covers that entire disk separately.
        delta=math.atan2(math.sin(yaw-expected[-1,2]),math.cos(yaw-expected[-1,2]))
        expected=np.vstack((expected,[(expected[-1,0],expected[-1,1],expected[-1,2]+a)
            for a in np.linspace(0.,delta,max(2,math.ceil(abs(delta)/.01)))]))
        follower=ActionClient(world,FollowPath,'/follow_path');assert follower.wait_for_server(timeout_sec=5)
        follow=FollowPath.Goal();follow.path=path;follow.controller_id='FollowPath';follow.goal_checker_id='general_goal_checker'
        world.moving=True;fh=wait(follower.send_goal_async(follow));assert fh.accepted
        finished=wait(fh.get_result_async(),100);world.moving=False;time.sleep(.3)
        result['controller_status']=finished.status;assert finished.status==GoalStatus.STATUS_SUCCEEDED
        trace=np.asarray(world.trace);assert len(trace)>10
        distances,indices=cKDTree(expected[:,:2]).query(trace[:,1:3]);angles=np.arctan2(np.sin(trace[:,3]-expected[indices,2]),np.cos(trace[:,3]-expected[indices,2]))
        # During a stationary turn multiple reference yaws share one XY;
        # compare each sample to all nearby reference poses in SE(2).
        heading_errors=[]
        tree=cKDTree(expected[:,:2])
        for sample in trace:
            choices=tree.query_ball_point(sample[1:3],.02)
            # A missing tube neighbour is recorded separately; retain finite
            # diagnostics so even a failed test always writes valid evidence.
            heading_errors.append(min(abs(math.atan2(math.sin(sample[3]-expected[i,2]),math.cos(sample[3]-expected[i,2]))) for i in choices) if choices else math.pi)
        result.update(tracking_position_max_m=float(distances.max()),tracking_heading_max_rad=max(heading_errors),padded_footprint_clearance_min_m=world.min_clearance,reverse_samples=world.reverse,final_pose=world.pose.tolist(),observed_area_gain_m2=(int(np.count_nonzero(world.observed))-before)*.02**2)
        np.savetxt(out/'trace.csv',trace,delimiter=',',header='monotonic,x,y,yaw,v,w')
        assert result['tracking_position_max_m']<=.02 and result['tracking_heading_max_rad']<=.05,result
        assert world.min_clearance>0 and world.reverse==0
        assert math.dist(world.pose[:2],target)<=.16
        if case=='bootstrap':assert result['observed_area_gain_m2']>0
        result['passed']=True;return result
    finally:
        for process in processes:
            if process.poll() is None:
                process.send_signal(signal.SIGINT)
                try:process.wait(timeout=4)
                except subprocess.TimeoutExpired:
                    process.terminate()
                    try:process.wait(timeout=2)
                    except subprocess.TimeoutExpired:process.kill();process.wait()
        for stream in streams:stream.close()
        executor.shutdown();world.destroy_node();rclpy.shutdown();thread.join(timeout=2)
        (out/'result.json').write_text(json.dumps(result,indent=2,allow_nan=False))


def main():
    assert os.environ.get('ROS_LOCALHOST_ONLY')=='1'
    assert 200<=int(os.environ.get('ROS_DOMAIN_ID','0'))<=230
    parser=argparse.ArgumentParser();parser.add_argument('--repo',type=Path,default=Path('/repo'));parser.add_argument('--output',type=Path,required=True);parser.add_argument('--case',choices=['door68','door80','door68_stop','detour','door56','rotation_narrow','unknown_outer','bootstrap','blind_start'])
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    if args.case:
        print(json.dumps(run(args.case,args)),flush=True)
        return
    # Separate ROS contexts/processes/domains prevent a removed lifecycle
    # service's DDS discovery cache from answering the next case's readiness
    # test before its new server has appeared. Never retry a failed case.
    for index,case in enumerate(['door68','door80','door68_stop','detour','door56','rotation_narrow','unknown_outer','bootstrap','blind_start']):
        env=dict(os.environ,ROS_DOMAIN_ID=str(210+index))
        subprocess.run([sys.executable,__file__,'--repo',str(args.repo),'--output',str(args.output),'--case',case],env=env,check=True)


if __name__=='__main__':main()
