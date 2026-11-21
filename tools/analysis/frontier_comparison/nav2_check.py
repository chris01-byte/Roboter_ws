#!/usr/bin/env python3
"""Plan recorded AP-04 candidate proposals with real NavFn A* and validate paths.

Only ComputePathToPose is used. No controller, mission, Twist or hardware node.
Map/costmap obstacles and unknowns from the comparison become the static planner
map, with the same measured Nav2 profile. Native plans are not route doubles.
"""
import argparse
import copy
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import sys
import threading
import time

import numpy as np
import rclpy
import yaml
from geometry_msgs.msg import TransformStamped
from lifecycle_msgs.srv import ChangeState
from nav_msgs.msg import OccupancyGrid
from nav2_msgs.action import ComputePathToPose
from rclpy.action import ActionClient
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from ament_index_python.packages import get_package_prefix
from rclpy.qos import QoSProfile, DurabilityPolicy, ReliabilityPolicy
from tf2_ros import TransformBroadcaster
from explore.metric_frontier import MetricCandidate, known_safe_mask
from explore.metric_frontier_candidates import visible_boundary_cells
from explore.portal_source_adapter import raw_map_portal_source_from_values
from dataclasses import replace
from compare import load_fixture


def wait(future,timeout=2.):
    deadline=time.monotonic()+timeout
    while not future.done() and time.monotonic()<deadline:time.sleep(.005)
    if not future.done():raise TimeoutError('native planner deadline')
    return future.result()


class MapSource(Node):
    def __init__(self,grid,pose):
        super().__init__('ap04_candidate_map');self.grid=grid;self.pose=pose;self.cost=None
        qos=QoSProfile(depth=1,durability=DurabilityPolicy.TRANSIENT_LOCAL,reliability=ReliabilityPolicy.RELIABLE)
        self.pub=self.create_publisher(OccupancyGrid,'/map',qos);self.tf=TransformBroadcaster(self)
        self.create_subscription(OccupancyGrid,'/global_costmap/costmap',lambda m:setattr(self,'cost',m),qos)
        self.create_timer(.05,self.publish)
    def publish(self):
        self.grid.header.stamp=self.get_clock().now().to_msg();self.pub.publish(self.grid)
        t=TransformStamped();t.header.stamp=self.get_clock().now().to_msg()
        t.header.frame_id='map';t.child_frame_id='base_link'
        t.transform.translation.x=self.pose[0];t.transform.translation.y=self.pose[1]
        t.transform.rotation.z=math.sin(self.pose[2]/2);t.transform.rotation.w=math.cos(self.pose[2]/2)
        self.tf.sendTransform(t)


def run(args):
    f=load_fixture(args.repo)
    rows=[row for row in json.loads(args.comparison.read_text()) if row['case']==args.case]
    out=args.output/args.case;out.mkdir(parents=True,exist_ok=True)
    config=yaml.safe_load((args.repo/'src/robot_navigation/config/nav2_params_real.yaml').read_text())
    config={key:config[key] for key in ('planner_server','global_costmap')}
    p=config['global_costmap']['global_costmap']['ros__parameters']
    p.update(plugins=['static_layer','inflation_layer'],track_unknown_space=True,
             rolling_window=False,always_send_full_costmap=True,resolution=.1,
             global_frame='map',update_frequency=20.,publish_frequency=10.)
    p['static_layer']={'plugin':'nav2_costmap_2d::StaticLayer','map_subscribe_transient_local':True,'subscribe_to_updates':False}
    params=out/'params.yaml';params.write_text(yaml.safe_dump(config))
    n,inputs,scan=f.fixture(args.case);rclpy.init();node=MapSource(inputs[0],inputs[2])
    executor=MultiThreadedExecutor(num_threads=3);executor.add_node(node)
    thread=threading.Thread(target=executor.spin,daemon=True);thread.start()
    stream=(out/'planner.log').open('w')
    executable=Path(get_package_prefix('nav2_planner'))/'lib/nav2_planner/planner_server'
    proc=subprocess.Popen([str(executable),'--ros-args','--params-file',str(params)],stdout=stream,stderr=subprocess.STDOUT)
    results=[]
    try:
        lifecycle=node.create_client(ChangeState,'/planner_server/change_state')
        assert lifecycle.wait_for_service(timeout_sec=20)
        for transition in (1,3):
            request=ChangeState.Request();request.transition.id=transition
            assert wait(lifecycle.call_async(request),30).success
        client=ActionClient(node,ComputePathToPose,'/compute_path_to_pose')
        assert client.wait_for_server(timeout_sec=5)
        for row in rows:
            n,inputs,scan=f.fixture(args.case,revision=row['revision'])
            if args.case=='blocked':
                best=n._metric_candidates(inputs,.3)[0];g=copy.deepcopy(inputs[5])
                arr=np.asarray(g.data).reshape(60,90).copy();col,r=n._world_to_grid(best.x,best.y,g.info)
                arr[r-2:r+3,col-2:col+3]=100;g.data=arr.ravel().tolist()
                inputs[5]=g;inputs[6]=(arr>=0)&(arr<100);n._global_costmap=g
            if args.case=='growth' and row['revision']>1:
                pad=row['revision']-1
                for index in (0,5):
                    g=inputs[index];arr=np.asarray(g.data).reshape(60,90)
                    arr=np.pad(arr,((0,pad),(pad,0)),constant_values=-1)
                    g.info.width=90+pad;g.info.height=60+pad;g.info.origin.position.x=-.1*pad;g.data=arr.ravel().tolist()
                source=raw_map_portal_source_from_values(**n._metric_grid_values(inputs[0]))
                inputs[1]=replace(inputs[1],fingerprint=source.fingerprint)
                arr=np.asarray(inputs[0].data).reshape(60+pad,90+pad)
                inputs[3],inputs[4]=known_safe_mask(arr,n._metric_scope,inputs[1],(-.1*pad,0.),0.,.1,.28)
                a=np.asarray(inputs[5].data).reshape(60+pad,90+pad);inputs[6]=(a>=0)&(a<100)
            inputs[2]=tuple(row['pose'])
            assert inputs[1].fingerprint==row['fingerprint']
            planning_grid=copy.deepcopy(inputs[0]);a=np.asarray(inputs[5].data)
            raw=np.asarray(planning_grid.data);raw[(a==100)&(raw>=0)]=100;planning_grid.data=raw.tolist()
            node.grid=planning_grid;node.pose=inputs[2];node.cost=None
            deadline=time.monotonic()+3
            # Wait for this exact map generation/geometry in the real static layer.
            while time.monotonic()<deadline:
                cost=node.cost
                if cost is not None and cost.info.width==planning_grid.info.width and cost.info.height==planning_grid.info.height:
                    cm=np.asarray(cost.data);unknown=raw<0
                    if (np.all(cm[unknown]!=0) and not np.any(cm[raw==0]<0)
                            and np.all(cm[raw==100]>=99)):break
                time.sleep(.02)
            else:raise TimeoutError('native costmap current map not received')
            for mode,record in row['cores'].items():
                attempts=[]
                for index,c in enumerate(record['goals']):
                    goal=ComputePathToPose.Goal();goal.planner_id='GridBased';goal.use_start=True
                    for stamped,xy,yaw in ((goal.start,inputs[2][:2],inputs[2][2]),(goal.goal,(c['x'],c['y']),c['yaw'])):
                        stamped.header.frame_id='map';stamped.header.stamp=node.get_clock().now().to_msg()
                        stamped.pose.position.x=float(xy[0]);stamped.pose.position.y=float(xy[1])
                        stamped.pose.orientation.z=math.sin(yaw/2);stamped.pose.orientation.w=math.cos(yaw/2)
                    started=time.monotonic();handle=wait(client.send_goal_async(goal));assert handle.accepted
                    response=wait(handle.get_result_async(),max(.001,2.-(time.monotonic()-started)))
                    target=MetricCandidate('candidate',c['x'],c['y'],c['yaw'],tuple(c['frontier']),(),c['route_length_m'],0.,inputs[1].fingerprint,row['revision'])
                    valid=response.status==4 and n._metric_validate_nav_plan(inputs,response.result.path,target) is not None
                    attempt=dict(index=index,planner_status=response.status,full_path_valid=valid,
                                 rejection=n._metric_last_route_rejection if response.status==4 else 'nav2_plan_failed',elapsed_s=time.monotonic()-started)
                    attempts.append(attempt)
                    points=[(p.pose.position.x,p.pose.position.y) for p in response.result.path.poses]
                    (out/f'revision-{row["revision"]}-{mode}-{index}-path.json').write_text(json.dumps(points))
                valid_goals=[goal for goal,attempt in zip(record['goals'],attempts) if attempt['full_path_valid']]
                view=n._metric_observation_view()
                sights=[visible_boundary_cells(inputs[0],f.scope_mask(n,inputs),(goal['x'],goal['y'],goal['yaw']),view) for goal in valid_goals]
                result=dict(case=args.case,revision=row['revision'],core=mode,attempts=attempts,
                            planable=sum(a['full_path_valid'] for a in attempts),
                            native_valid_boundary_union_m=len(set().union(*sights))*.1,
                            best_single_sight_m=max(map(len,sights),default=0)*.1)
                if args.case=='long' and mode=='boundary_samples':
                    assert result['native_valid_boundary_union_m']>2*result['best_single_sight_m']
                results.append(result)
                if mode=='boundary_samples':assert result['planable']>0,result
        return results
    finally:
        # Signal the native executable directly; no wrapper, launch or process group.
        proc.send_signal(signal.SIGINT)
        try:proc.wait(timeout=5)
        except subprocess.TimeoutExpired:proc.kill();proc.wait()
        stream.close();executor.shutdown();node.destroy_node();rclpy.shutdown();thread.join(timeout=2)
        (out/'results.json').write_text(json.dumps(results,indent=2,allow_nan=False))


if __name__=='__main__':
    assert os.environ.get('ROS_LOCALHOST_ONLY')=='1'
    parser=argparse.ArgumentParser();parser.add_argument('--repo',type=Path,required=True)
    parser.add_argument('--comparison',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--case',choices=['ring','concave','long','blocked','growth','revisit','no_semantics'])
    args=parser.parse_args()
    if args.case:print(json.dumps(run(args)))
    else:
        for index,case in enumerate(['ring','concave','long','blocked','growth','revisit','no_semantics']):
            subprocess.run([sys.executable,__file__,'--repo',str(args.repo),'--comparison',str(args.comparison),
                '--output',str(args.output),'--case',case],env=dict(os.environ,ROS_DOMAIN_ID=str(220+index)),check=True)
