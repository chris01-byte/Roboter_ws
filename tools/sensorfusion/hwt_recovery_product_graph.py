#!/usr/bin/env python3
"""Device-free HWT graph with real Yaw/Guard/Manager/BT/Explorer/Gate.

Run only after sourcing the isolated recovery overlay. The graph uses a
localhost-only ROS domain, synthetic raw HWT/encoder feedback and a Nav2 action
server; it starts no hardware, launch stack or actuator owner. Source, map,
TF and costmap are synthetic ROS messages. Map manager, exact correlation,
portal/frontier feeds and task selection are real product components.

With the isolated underlay and recovery overlay sourced:
  env -u CYCLONEDDS_URI ROS_DOMAIN_ID=225 ROS_LOCALHOST_ONLY=1 \
      python3 tools/sensorfusion/hwt_recovery_product_graph.py
"""

import json
import os
import pathlib
import struct
import signal
import subprocess
import threading
import time

# Reject accidental attachment to the active robot graph. The user's runtime
# uses ROS_DOMAIN_ID=42 and a configured CycloneDDS peer list.
_domain = os.environ.get('ROS_DOMAIN_ID', '')
if (os.environ.get('ROS_LOCALHOST_ONLY') != '1'
        or os.environ.get('CYCLONEDDS_URI')
        or not _domain.isdigit() or not 200 <= int(_domain) <= 230):
    raise SystemExit(
        'Requires isolated ROS_DOMAIN_ID=200..230, ROS_LOCALHOST_ONLY=1 '
        'and CYCLONEDDS_URI unset')

import rclpy
from rclpy.action import ActionServer, CancelResponse
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from rclpy.qos import QoSProfile, DurabilityPolicy
from ament_index_python.packages import (
    get_package_prefix, get_package_share_directory)
from geometry_msgs.msg import Twist, TransformStamped
from nav2_msgs.action import NavigateToPose
from nav_msgs.msg import Odometry, OccupancyGrid
from sensor_msgs.msg import Imu, LaserScan, PointCloud2, PointField
from robot_interfaces.msg import NearFieldStatus
from std_msgs.msg import Bool, String
from tf2_ros import TransformBroadcaster
from explore.explore_node import ExploreNode
from robot_map_manager.robot_map_manager_node import RobotMapManager
from robot_navigation.cmd_vel_mission_gate import CmdVelMissionGate
from robot_state_estimation.hwt601_shadow_node import Hwt601ShadowNode

share = lambda name: pathlib.Path(get_package_share_directory(name))
params = share('explore')/'config/hwt601_recovery_acceptance_params.yaml'
base = share('explore')/'config/explore_params.yaml'
tree = share('explore')/'behavior_trees/navigate_to_pose_no_recovery.xml'
shadow_params = share('robot_state_estimation')/'config/hwt601_shadow.yaml'
logdir = pathlib.Path(os.environ.get('HWT_GRAPH_LOGDIR', '/tmp/we1-hwt-ros-graph-probe'))
logdir.mkdir(exist_ok=True)
commands = [
 ('bt', [str(pathlib.Path(get_package_prefix('bt_orchestrator'))/
              'lib/bt_orchestrator/bt_orchestrator'),'--ros-args',
         '--params-file',str(share('bt_orchestrator')/'config/bt_params.yaml'),
         '-p',f'explore_xml:={share("bt_orchestrator")/"bt_xml/explore.xml"}']),
 ('manager', [str(pathlib.Path(get_package_prefix('mission_manager'))/
                   'lib/mission_manager/mission_manager'),'--ros-args',
              '--params-file',str(share('mission_manager')/'config/mission_catalog.yaml'),
              '-p','enable_real_explore:=true']),
]

class Sources(Node):
    def __init__(self):
        super().__init__('we1_synthetic_sources')
        self.map_frame = 'map'
        self.map_ticks = 0
        self.raw_on = True
        self.moving = True
        self.gate_angular = 0.0
        self.route_blocked = False
        self.pose_on = True
        self.estop_active = False
        self.last_raw = time.monotonic()
        self.raw_stamps=[]
        self.cmd = self.create_publisher(String,'/mission_manager/command_json',10)
        qos=QoSProfile(depth=1);qos.durability=DurabilityPolicy.TRANSIENT_LOCAL
        self.estop = self.create_publisher(Bool,'/safety/estop',qos)
        self.raw = self.create_publisher(Imu,'/shadow/hwt601/imu/data_raw',10)
        self.wheel = self.create_publisher(Odometry,'/fusion/hwt601/wheel_odom_raw',10)
        self.odom = self.create_publisher(Odometry,'/odom',10)
        self.costmap = self.create_publisher(OccupancyGrid,'/global_costmap/costmap',10)
        self.map_pub = self.create_publisher(OccupancyGrid,'/map',qos)
        self.scan = self.create_publisher(LaserScan,'/scan_normiert',10)
        self.left = self.create_publisher(PointCloud2,'/near_field/left/points',10)
        self.right = self.create_publisher(PointCloud2,'/near_field/right/points',10)
        self.near_status = self.create_publisher(NearFieldStatus,'/near_field/status',10)
        self.tf = TransformBroadcaster(self)
        self.raw_status = self.create_publisher(String,'/shadow/hwt601/raw_status_json',10)
        self.yaw_statuses=[]
        self.yaw_samples=[]
        self.create_subscription(String,'/shadow/hwt601/status_json',
            lambda m:self.yaw_statuses.append(json.loads(m.data)),10)
        self.create_subscription(Imu,'/shadow/hwt601/imu/yaw_rate',
            lambda m:self.yaw_samples.append(
                m.header.stamp.sec+m.header.stamp.nanosec*1e-9),10)
        self.wheel_status = self.create_publisher(String,'/base_hardware/state_json',10)
        self.create_timer(.01,self.samples)
        self.create_timer(.2,self.statuses)
        self.create_timer(.1,lambda:self.estop.publish(Bool(data=self.estop_active)))
        self.create_timer(.2,self.publish_pose_and_costmap)
        self.phases=[]; self.manager=[]; self.out=[]; self.gate_status=[]
        self.create_subscription(String,'/explore/status_json',lambda m:self.phases.append(json.loads(m.data)),10)
        self.create_subscription(String,'/mission_manager/status_json',lambda m:self.manager.append(json.loads(m.data)),10)
        self.create_subscription(String,'/fusion/hwt601/status_json',lambda m:self.gate_status.append(json.loads(m.data)),10)
        self.create_subscription(Twist,'/cmd_vel_nav',self.on_gate_output,10)
    def on_gate_output(self,m):
        self.gate_angular=m.angular.z
        self.out.append((time.monotonic(),m.linear.x,m.angular.z))
    def samples(self):
        stamp=self.get_clock().now().to_msg()
        if self.raw_on:
            raw=Imu();raw.header.stamp=stamp;raw.header.frame_id='hwt601_link'
            raw.angular_velocity_covariance[8]=.01
            raw.angular_velocity.x=.001
            raw.angular_velocity.y=-.002
            raw.angular_velocity.z=.0001
            self.raw.publish(raw);self.last_raw=time.monotonic()
            self.raw_stamps.append(stamp.sec+stamp.nanosec*1e-9)
        wheel=Odometry();wheel.header.stamp=stamp;wheel.header.frame_id='odom';wheel.child_frame_id='base_link'
        wheel.pose.pose.orientation.w=1.0
        wheel.twist.covariance[0]=.01;wheel.twist.twist.linear.x=.03 if self.moving else 0.0
        wheel.twist.twist.angular.z=self.gate_angular
        self.wheel.publish(wheel);self.odom.publish(wheel)
    def publish_pose_and_costmap(self):
        stamp = self.get_clock().now().to_msg()
        transforms=[]
        for parent,child in (('map','odom'),('odom','base_link')):
            transform=TransformStamped()
            transform.header.stamp=stamp
            transform.header.frame_id=parent
            transform.child_frame_id=child
            transform.transform.rotation.w=1.0
            transforms.append(transform)
        if self.pose_on:
            self.tf.sendTransform(transforms)
        grid=OccupancyGrid()
        grid.header.stamp=stamp
        grid.header.frame_id='map'
        grid.info.width=40
        grid.info.height=30
        grid.info.resolution=.1
        grid.info.origin.position.x=-1.0
        grid.info.origin.position.y=-1.0
        grid.info.origin.orientation.w=1.0
        grid.data=[100 if self.route_blocked else 0]*1200
        self.costmap.publish(grid)
        # One open room with a straight frontier, no invented task/portal.
        grid.data=[0 if col < 25 else -1 for row in range(30) for col in range(40)]
        grid.header.frame_id=self.map_frame
        self.map_ticks += 1
        if self.map_ticks % 5 == 1:
            self.map_pub.publish(grid)
        scan=LaserScan()
        scan.header.stamp=stamp
        scan.header.frame_id='base_link'
        scan.angle_min=-3.14159
        scan.angle_increment=6.28318/720
        scan.range_min=.05
        scan.range_max=10.0
        scan.ranges=[3.0]*720
        self.scan.publish(scan)
        field_names=('x','y','z')
        for pub in (self.left,self.right):
            cloud=PointCloud2()
            cloud.header.stamp=stamp
            cloud.header.frame_id='base_link'
            cloud.height=1
            cloud.width=1
            cloud.fields=[PointField(name=name,offset=4*i,datatype=7,count=1)
                          for i,name in enumerate(field_names)]
            cloud.point_step=12
            cloud.row_step=12
            cloud.data=struct.pack('<fff',1.0,0.0,0.0)
            pub.publish(cloud)
        near=NearFieldStatus()
        near.header.stamp=stamp
        near.header.frame_id='base_link'
        near.left_quality=NearFieldStatus.QUALITY_VALID_FAR
        near.right_quality=NearFieldStatus.QUALITY_VALID_FAR
        near.left_observed_columns=255
        near.right_observed_columns=255
        near.left_frame_healthy=True
        near.right_frame_healthy=True
        self.near_status.publish(near)
    def statuses(self):
        raw=dict(ready=True,raw_data_ready=True,port='/dev/ttyUSB_HWT601',
                 sensor_write_commands=False,consecutive_errors=0,age_s=0.0,
                 state='bereit',reconnects=0)
        wheel=dict(dry_run=False,allow_rs485=True,rs485_ready=True,
                   odometry_source='encoder_position',encoder_feedback_ok=True,
                   encoder_stale=False,encoder_config_fault_latched=False,
                   encoder_feedback_age_s=0.0)
        self.raw_status.publish(String(data=json.dumps(raw)))
        self.wheel_status.publish(String(data=json.dumps(wheel)))

class FakeNav(Node):
    def __init__(self):
        super().__init__('we1_nav2_test_server')
        self.goals=[];self.canceled=[];self.active=0;self.maximum=0
        self.pub=self.create_publisher(Twist,'/cmd_vel_nav_raw',10)
        self.server=ActionServer(self,NavigateToPose,'/navigate_to_pose',
            execute_callback=self.execute,cancel_callback=lambda goal:CancelResponse.ACCEPT,
            callback_group=ReentrantCallbackGroup())
    def execute(self,goal):
        index=len(self.goals)+1;self.goals.append((index,goal.goal_id,time.monotonic()))
        self.active+=1;self.maximum=max(self.maximum,self.active)
        print('NAV_GOAL',index,flush=True)
        try:
            while rclpy.ok():
                if goal.is_cancel_requested:
                    self.canceled.append(index);goal.canceled()
                    print('NAV_CANCELED',index,flush=True)
                    return NavigateToPose.Result()
                cmd=Twist();cmd.linear.x=.05;self.pub.publish(cmd)
                time.sleep(.05)
            goal.abort();return NavigateToPose.Result()
        finally:self.active-=1

ps=[];executor=None;thread=None
try:
    for name,command in commands:
        log=open(logdir/f'{name}.log','w')
        ps.append((name,subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,env=os.environ.copy()),log))
    rclpy.init(args=['--ros-args','--params-file',str(base),'--params-file',str(params),
                     '--params-file',str(shadow_params),
                     '-p','operator_stationary_confirmed:=true',
                     '-p',f'behavior_tree:={tree}','-p','require_hwt601_fusion:=true',
                     '-p','hwt601_active_drive:=true','-p','allow_explore_mission:=true',
                     '-p','require_localization:=false',
                     '-p','initial_scan_enabled:=false',
                     '-p','portal_crossing_enabled:=false',
                     '-p','coverage_enabled:=false',
                     '-p','wohnungserkundung_accessible_scope_verified:=true',
                     '-p','wohnungserkundung_scope_id:=synthetic-graph-only',
                     '-p','wohnungserkundung_scope_polygon_xy:=[-0.9,-0.9,3.5,-0.9,3.5,3.5,-0.9,3.5]',
                     '-p',f'storage_directory:={logdir / "synthetic-maps"}'])
    explorer=ExploreNode();gate=CmdVelMissionGate();shadow=Hwt601ShadowNode();sources=Sources();nav=FakeNav();maps=RobotMapManager()
    original_route=explorer._wohnungserkundung_resume_path_ready
    original_still=explorer._wohnungserkundung_hwt_standstill_confirmed
    last=[None,None]
    route_history=[]
    def route_probe():
        value=original_route()
        if value!=last[0]:print('ROUTE',value,flush=True);last[0]=value;route_history.append(value)
        return value
    def still_probe():
        value=original_still()
        if value!=last[1]:print('STILL',value,sources.moving,flush=True);last[1]=value
        return value
    explorer._wohnungserkundung_resume_path_ready=route_probe
    explorer._wohnungserkundung_hwt_standstill_confirmed=still_probe
    executor=MultiThreadedExecutor(num_threads=8)
    for node in (explorer,gate,shadow,sources,nav,maps):executor.add_node(node)
    thread=threading.Thread(target=executor.spin,daemon=True);thread.start()
    def wait_for(predicate,timeout):
        end=time.monotonic()+timeout
        while time.monotonic()<end:
            if predicate():return True
            time.sleep(.05)
        return False
    print('RESOLVED', json.dumps({name:get_package_prefix(name) for name in
        ('explore','robot_state_estimation','robot_navigation','mission_manager','bt_orchestrator','robot_map_manager')}),flush=True)
    assert wait_for(lambda:{'bt_orchestrator','mission_manager'}.issubset(
        set(sources.get_node_names())),10), 'product nodes unavailable'
    assert wait_for(lambda:sources.yaw_statuses and
                    sources.yaw_statuses[-1].get('ready') is True,40), 'real yaw bias startup failed'
    startup_bias=sources.yaw_statuses[-1]['bias']['radps_xyz']
    assert wait_for(lambda:explorer._hwt_guard.health.motion_failure() is None,5), 'HWT startup failed'
    assert wait_for(lambda:sources.cmd.get_subscription_count()>0,5), 'command route unavailable'
    assert wait_for(lambda:explorer._wohnungserkundung_navigation_snapshot is not None,10), 'real policy candidate missing'
    first_task=explorer._wohnungserkundung_navigation_snapshot[0].task_id
    first_revision=explorer._region_graph_shadow_latest_correlation.map_revision
    time.sleep(3.)
    assert explorer._region_graph_shadow_latest_correlation.map_revision > first_revision
    assert explorer._wohnungserkundung_navigation_snapshot is not None, 'unchanged map blocked selection'
    if os.environ.get('HWT_GRAPH_CASE')=='foreign':
        sources.map_frame='foreign_map'
        assert wait_for(lambda:explorer._region_graph_shadow_fault is not None,3)
        assert explorer._current_wohnungserkundung_navigation_target() is None, 'foreign map retained an actionable old candidate'
        sources.cmd.publish(String(data='{"type":"explore"}'))
        time.sleep(3.)
        assert len(nav.goals)==0, 'foreign map dispatched a child'
        print(json.dumps({'result':'PASS','case':'foreign','no_child':True}),flush=True)
        raise SystemExit(0)
    # Stop the actual detector feed: a current map alone is not evidence of
    # an empty portal inventory. Restore it only through real processing.
    explorer._region_graph_shadow_connected_portal_feed=False
    time.sleep(3.)
    assert explorer._wohnungserkundung_navigation_snapshot is None, 'missing portal feed allowed a goal'
    explorer._region_graph_shadow_connected_portal_feed=True
    assert wait_for(lambda:explorer._wohnungserkundung_navigation_snapshot is not None,4)
    sources.route_blocked=True
    assert wait_for(lambda:explorer._wohnungserkundung_navigation_snapshot is None,3), 'invalid route allowed a goal'
    sources.route_blocked=False
    assert wait_for(lambda:explorer._wohnungserkundung_navigation_snapshot is not None,4)
    sources.cmd.publish(String(data='{"type":"explore"}'))
    assert wait_for(lambda:len(nav.goals)>=1,8), 'first Nav2 child missing'
    first_id=nav.goals[0][1]
    assert any(m.get('state')=='running' and
               m.get('active_command',{}).get('type')=='explore'
               for m in sources.manager), 'parent command not active'
    mode=os.environ.get('HWT_GRAPH_CASE','recovery')
    if mode in ('permanent','estop'):
        if mode=='permanent':
            sources.raw_on=False
            assert wait_for(lambda:explorer._hwt_guard.health.recovery_state=='TERMINAL_FAULT',8)
        else:
            sources.estop_active=True
        assert wait_for(lambda:1 in nav.canceled,3), 'old child not terminal'
        assert wait_for(lambda:sources.manager[-1].get('state') in ('canceled','failed'),3)
        sources.raw_on=True
        sources.estop_active=False
        time.sleep(1.5)
        assert len(nav.goals)==1 and nav.active==0
        assert all(abs(v)<1e-9 and abs(w)<1e-9 for _,v,w in sources.out[-10:])
        print(json.dumps({'result':'PASS','case':mode,'no_auto_restart':True,
                          'old_child_terminal':True,'real_map_policy_chain':True}),flush=True)
        raise SystemExit(0)
    assert mode=='recovery'
    time.sleep(.2)
    sources.route_blocked=True
    sources.raw_on=False
    time.sleep(.02)
    raw_before=sources.raw_stamps[-1]
    raw_count=len(sources.raw_stamps)
    resume_at=sources.last_raw+.255
    while time.monotonic()<resume_at:
        time.sleep(min(.005,resume_at-time.monotonic()))
    sources.raw_on=True
    assert wait_for(lambda:len(sources.raw_stamps)>raw_count,1), 'raw stream did not return'
    raw_gap_s=sources.raw_stamps[raw_count]-raw_before
    assert .25<=raw_gap_s<=.30, f'wrong raw gap {raw_gap_s}'
    assert wait_for(lambda:any(m.get('phase')=='we_hwt_hold'
                               for m in sources.phases),2), 'Explorer HOLD missing'
    assert wait_for(lambda:1 in nav.canceled,2), 'old child not terminal'
    assert wait_for(lambda:any(s.get('recovery_state')=='HOLD' and
                               s.get('hwt_motion_ready') is False
                               for s in sources.gate_status),2), 'gate HOLD missing'
    blocked_since=time.monotonic()
    assert wait_for(lambda:shadow._rejected>=1,2), 'real yaw did not reject the gap boundary'
    assert wait_for(lambda:explorer._hwt_guard.health.recovery_state=='RECOVERY_VALIDATION',2), 'first validation missing'
    # A second 261-ms gap during validation must return to HOLD without
    # reactivating the terminal old child or resetting the recovery budget.
    sources.raw_on=False
    time.sleep(.261)
    sources.raw_on=True
    assert wait_for(lambda:sum(e['state']=='HOLD' for e in
        explorer._hwt_guard.health.recovery_events)>=2,2), 'repeated gap did not re-enter HOLD'
    assert len(nav.goals)==1 and nav.maximum==1, 'old child reactivated during repeated gap'
    assert wait_for(lambda:explorer._hwt_guard.health.recovery_state=='HEALTHY',3), 'source not recovered'
    assert shadow.core.fault_reason is None, 'real yaw hard-latched'
    assert shadow.core.bias.bias_radps==tuple(startup_bias), 'startup bias changed'
    assert shadow.core.bias.adaptation_samples==0, 'bias adapted during mission'
    assert max(b-a for a,b in zip(sources.yaw_samples,sources.yaw_samples[1:]))>.25, 'yaw gap missing'
    assert len(nav.goals)==1 and nav.maximum==1, 'new child while odom moving'
    assert not any(m.get('phase')=='we_hwt_resumed' for m in sources.phases), 'resumed while moving'
    assert any(m.get('state')=='running' and
               m.get('active_command',{}).get('type')=='explore'
               for m in sources.manager[-5:]), 'parent mission lost during HOLD'
    time.sleep(.3)
    sources.moving=False
    assert wait_for(lambda:last[1] is True,2), 'stillstand not confirmed'
    assert wait_for(lambda:False in route_history,1), 'blocked route did not prevent resume'
    sources.pose_on=False
    time.sleep(1.6)
    assert len(nav.goals)==1, 'new child while map pose stale'
    sources.pose_on=True
    sources.route_blocked=False
    assert wait_for(lambda:len(nav.goals)>=2,3), 'new child missing after standstill'
    second_id=nav.goals[1][1]
    assert explorer._wohnungserkundung_navigation_snapshot[0].task_id==first_task
    assert any(m.get('hwt_first_fault') for m in sources.phases), 'Explorer snapshot missing'
    assert first_id!=second_id and nav.maximum==1 and nav.canceled[0]==1
    assert last==[True,True], 'route or stillstand not checked'
    assert explorer._hwt_gate_resume_ack_sequence>=1, 'gate ACK missing'
    assert all(abs(v)<1e-9 for t,v,_ in sources.out
               if blocked_since+.1<=t<nav.goals[1][2]), 'motion before new child'
    assert wait_for(lambda:any(t>nav.goals[1][2] and v>0
                               for t,v,_ in sources.out),2), 'new cmd not passed'
    assert any(m.get('phase')=='we_hwt_resumed' for m in sources.phases)
    sources.cmd.publish(String(data='{"type":"cancel"}'))
    assert wait_for(lambda:2 in nav.canceled,3), 'second child cancel missing'
    assert wait_for(lambda:any(m.get('state') in ('canceled','failed')
                               for m in sources.manager[-5:]),3), 'parent cancel missing'
    print(json.dumps({
        'result':'PASS', 'profile':str(params), 'fault':'raw_sample_stale',
        'raw_gap_s':raw_gap_s, 'old_child_terminal':nav.canceled[0]==1,
        'same_task':first_task, 'recovery_new_child_count':1,
        'max_active_children':nav.maximum, 'stillstand_and_route_checked':last,
        'gate_ack_sequence':explorer._hwt_gate_resume_ack_sequence,
        'parent_preserved':True, 'old_command_blocked':True,
        'real_map_policy_chain':True, 'unchanged_map_selection':True,
        'missing_feed_blocks':True, 'invalid_route_blocks':True,
        'user_cancel_terminal':True,
        'real_yaw_shadow':True, 'frozen_bias':startup_bias,
        'repeated_gap_during_validation':True,
    },sort_keys=True),flush=True)

except Exception:
    import traceback
    traceback.print_exc()
    raise
finally:
    if executor and 'sources' in locals() and rclpy.ok():
        try:
            sources.cmd.publish(String(data='{"type":"cancel"}'))
            time.sleep(.3)
        except Exception:
            pass
    if executor:executor.shutdown(timeout_sec=2)
    if thread:thread.join(timeout=2)
    if rclpy.ok():rclpy.shutdown()
    for name,p,log in ps:
        if p.poll() is None:p.send_signal(signal.SIGINT)
    for name,p,log in ps:
        try:p.wait(timeout=5)
        except subprocess.TimeoutExpired:p.terminate();p.wait(timeout=5)
        log.close()
    for name,_,_ in ps:
        contents=(logdir/f'{name}.log').read_text(errors='replace')
        print(name,[v for v in contents.splitlines() if 'ERROR' in v or 'Mission' in v][-5:],flush=True)
