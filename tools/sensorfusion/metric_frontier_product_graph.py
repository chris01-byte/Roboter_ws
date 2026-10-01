#!/usr/bin/env python3
"""Device-free metric product graph with real map/mission/BT/HWT/gate nodes.

Strict localhost/domain guard; starts no device, sensor driver or actuator.
The fixture publishes rasters and physical-source messages, never candidates,
regions, portals or task-adapter health. Explorer runs in its product process.
A Nav2 test server supplies action results and bounded synthetic pose changes.

After sourcing the isolated build:
  env -u CYCLONEDDS_URI ROS_DOMAIN_ID=224 ROS_LOCALHOST_ONLY=1 \
      METRIC_GRAPH_CASE=chain python3 tools/sensorfusion/metric_frontier_product_graph.py
Cases: chain, blocked, hold, route, estop, sensor, actuator, pose, map, late,
cancel_failed, budget, empty, filtered, scan, scan_route, mast_start, mast_start_scan, mast_start_full_scan. Logs/results remain local under HWT_GRAPH_LOGDIR.
"""

import json
import math
import os
import pathlib
import struct
import signal
import subprocess
import sys
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
from rclpy.executors import MultiThreadedExecutor, SingleThreadedExecutor
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
params = share('explore')/'config/metric_frontier_params.yaml'
base = share('explore')/'config/explore_params.yaml'
tree = share('explore')/'behavior_trees/navigate_to_pose_no_recovery.xml'
shadow_params = share('robot_state_estimation')/'config/hwt601_shadow.yaml'
logdir = pathlib.Path(os.environ.get('HWT_GRAPH_LOGDIR', '/tmp/amadeus-metric-product-graph'))
logdir.mkdir(parents=True, exist_ok=True)
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

CASE=os.environ.get('METRIC_GRAPH_CASE','chain')
if CASE not in ('chain','blocked','hold','route','estop','sensor','actuator','pose',
                'map','late','cancel_failed','budget','empty','filtered','scan','scan_route','mast_start','mast_start_scan','mast_start_full_scan'):
    raise SystemExit('Unknown METRIC_GRAPH_CASE')

class Sources(Node):
    def __init__(self):
        super().__init__('we1_synthetic_sources')
        self.map_frame = 'map'
        self.map_ticks = 0
        self.map_variant = False
        self.raw_on = True
        self.moving = False
        self.x = .05
        self.y = .05
        self.yaw = 0.0
        self.stage = 0
        self.blocked_task = False
        self.map_on = True
        self.sensor_on = True
        self.actuator_fault = False
        self.gate_angular = 0.0
        self.route_blocked = False
        self.pose_on = True
        self.estop_active = False
        self.last_raw = time.monotonic()
        self.last_sample_at = time.monotonic()
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
        self.sample_stop=threading.Event()
        self.sample_thread=threading.Thread(target=self.sample_loop,daemon=True)
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
    def sample_loop(self):
        # Publication must not queue behind this observer's ROS subscriptions.
        # Each real-time tick creates a new stamp; missed ticks remain gaps.
        deadline=time.monotonic()
        while not self.sample_stop.is_set():
            self.samples()
            deadline+=.01
            now=time.monotonic()
            if deadline<=now:
                deadline=now+.01
            self.sample_stop.wait(deadline-now)
    def samples(self):
        stamp=self.get_clock().now().to_msg()
        sample_at=time.monotonic()
        sample_dt=sample_at-self.last_sample_at
        self.last_sample_at=sample_at
        if CASE in ('scan','scan_route','mast_start_scan','mast_start_full_scan'):
            self.yaw+=self.gate_angular*sample_dt
        if self.raw_on:
            raw=Imu();raw.header.stamp=stamp;raw.header.frame_id='hwt601_link'
            raw.angular_velocity_covariance[8]=.01
            raw.angular_velocity.x=.001
            raw.angular_velocity.y=-.002
            raw.angular_velocity.z=.0001+self.gate_angular
            self.raw.publish(raw);self.last_raw=time.monotonic()
            self.raw_stamps.append(stamp.sec+stamp.nanosec*1e-9)
        wheel=Odometry();wheel.header.stamp=stamp;wheel.header.frame_id='odom';wheel.child_frame_id='base_link'
        wheel.pose.pose.position.x=self.x
        wheel.pose.pose.position.y=self.y
        wheel.pose.pose.orientation.z=math.sin(self.yaw/2)
        wheel.pose.pose.orientation.w=math.cos(self.yaw/2)
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
            if child=='base_link':
                transform.transform.translation.x=self.x
                transform.transform.translation.y=self.y
                transform.transform.rotation.z=math.sin(self.yaw/2)
                transform.transform.rotation.w=math.cos(self.yaw/2)
            transforms.append(transform)
        if self.pose_on:
            self.tf.sendTransform(transforms)
        grid=self.make_grid(stamp, costmap=True)
        self.costmap.publish(grid)
        grid=self.make_grid(stamp)
        self.map_ticks += 1
        if self.map_on:
            self.map_pub.publish(grid)
        if not self.sensor_on:
            return
        scan=LaserScan()
        scan.header.stamp=stamp
        scan.header.frame_id='laser_frame' if CASE in ('mast_start','mast_start_scan','mast_start_full_scan') else 'base_link'
        scan.angle_min=-3.14159
        scan.angle_increment=6.28318/720
        scan.range_min=.05
        scan.range_max=10.0
        scan.ranges=[3.0]*720
        if CASE in ('mast_start','mast_start_scan','mast_start_full_scan'):
            t=TransformStamped();t.header.stamp=stamp;t.header.frame_id='base_link';t.child_frame_id='laser_frame'
            t.transform.translation.x=.245;t.transform.translation.z=.660
            t.transform.rotation.z=math.sin(math.pi/4);t.transform.rotation.w=math.cos(math.pi/4)
            self.tf.sendTransform(t)
            scan.ranges=[math.nan if math.radians(56)<=scan.angle_min+i*scan.angle_increment<=math.radians(124) else 3.
                         for i in range(720)]
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
                   odometry_source='encoder_position',encoder_feedback_ok=not self.actuator_fault,
                   encoder_stale=False,encoder_config_fault_latched=False,
                   encoder_feedback_age_s=0.0)
        self.raw_status.publish(String(data=json.dumps(raw)))
        self.wheel_status.publish(String(data=json.dumps(wheel)))

    def make_grid(self, stamp, costmap=False):
        grid=OccupancyGrid();grid.header.stamp=stamp;grid.header.frame_id=self.map_frame
        grid.info.width=80;grid.info.height=40;grid.info.resolution=.1
        grid.info.origin.position.x=-1.;grid.info.origin.position.y=-2.
        grid.info.origin.orientation.w=1.
        cutoff=80 if CASE=='empty' else (25,40,55,68)[min(self.stage,3)]
        cells=[]
        for row in range(40):
            for col in range(80):
                value=0 if costmap or col<cutoff else -1
                if row in (0,39) or col in (0,79):value=100
                # A real raster wall with an open 1.6-m connection, no door label.
                if col in (30,31) and not 12<=row<28:value=100
                if CASE in ('blocked','budget') and row in (19,20) and col>=18:value=100
                if CASE in ('mast_start','mast_start_scan','mast_start_full_scan') and not costmap and self.stage==0 and col==10 and row in (19,20):
                    value=-1  # unknown rear mast ray strictly inside initial measured body
                if self.route_blocked:value=100
                if self.blocked_task and 18<=col<=25 and row<19:value=100
                cells.append(value)
        if self.map_variant:cells[-2-int(self.map_variant)%10]=100
        grid.data=cells
        return grid

class FakeNav(Node):
    def __init__(self, sources):
        super().__init__('metric_nav2_test_server')
        self.sources=sources
        self.goals=[];self.canceled=[];self.active=0;self.maximum=0
        self.release=False;self.shutdown_requested=False
        self.pub=self.create_publisher(Twist,'/cmd_vel_nav_raw',10)
        self.server=ActionServer(self,NavigateToPose,'/navigate_to_pose',
            execute_callback=self.execute,
            goal_callback=self.accept,
            cancel_callback=self.cancel,
            callback_group=ReentrantCallbackGroup())
    def accept(self, goal):
        from rclpy.action import GoalResponse
        if CASE=='late':time.sleep(4.)
        return GoalResponse.ACCEPT
    def cancel(self, goal):
        return CancelResponse.REJECT if CASE=='cancel_failed' else CancelResponse.ACCEPT
    def execute(self,goal):
        index=len(self.goals)+1
        target=(goal.request.pose.pose.position.x,goal.request.pose.pose.position.y)
        self.goals.append(dict(index=index,uuid=bytes(goal.goal_id.uuid).hex(),target=target,time=time.monotonic()))
        self.active+=1;self.maximum=max(self.maximum,self.active)
        print('NAV_GOAL',json.dumps(self.goals[-1]),flush=True)
        begun=time.monotonic()
        initial=(self.sources.x,self.sources.y)
        moving_since=None
        try:
            if CASE=='blocked' and index==1:
                time.sleep(.4)
                goal.abort()
                return NavigateToPose.Result()
            while rclpy.ok() and not self.shutdown_requested:
                if goal.is_cancel_requested:
                    self.canceled.append(index);goal.canceled()
                    print('NAV_CANCELED',index,flush=True)
                    return NavigateToPose.Result()
                cmd=Twist();cmd.linear.x=.05
                if CASE=='budget':
                    cmd.linear.x=0.;cmd.angular.z=.03
                    self.sources.yaw+=self.sources.gate_angular*.05
                self.pub.publish(cmd)
                if CASE in ('chain','mast_start','mast_start_scan','mast_start_full_scan') and self.release:
                    if moving_since is None:moving_since=time.monotonic()
                    fraction=min(1.,(time.monotonic()-moving_since)/3.)
                    self.sources.x=initial[0]+(target[0]-initial[0])*fraction
                    self.sources.y=initial[1]+(target[1]-initial[1])*fraction
                    if fraction>=1:
                        self.sources.stage+=1
                        goal.succeed()
                        return NavigateToPose.Result()
                time.sleep(.05)
            goal.abort();return NavigateToPose.Result()
        finally:
            self.pub.publish(Twist())
            self.active-=1


def run():
    ps=[];executors=[];threads=[];nodes=[]
    spin_stop=threading.Event()
    old_switch=sys.getswitchinterval()
    sys.setswitchinterval(.001)
    try:
        for name,command in commands:
            log=open(logdir/f'{name}.log','w')
            ps.append((subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT),log))
        # Generate only the map binding. Task candidates are produced by the
        # actual frontier/metric policy from this same input grid at runtime.
        from explore.portal_source_adapter import raw_map_portal_source_from_values
        from explore.metric_frontier_runtime import MetricFrontierRuntime
        rclpy.init()
        probe=Sources()
        initial=probe.make_grid(probe.get_clock().now().to_msg())
        from rclpy.serialization import serialize_message, deserialize_message
        initial=deserialize_message(serialize_message(initial),OccupancyGrid)
        binding=raw_map_portal_source_from_values(**MetricFrontierRuntime._metric_grid_values(initial)).fingerprint
        probe.destroy_node();rclpy.shutdown()
        # mast_start_scan uses the existing 0.3-rad software fixture sweep.
        # Full 360-degree footprint admission is unchanged in the runtime.
        # mast_start_full_scan also exercises a full-duration 2*pi revolution.
        explorer_args=['--ros-args','--params-file',str(base),'--params-file',str(params),
            '--params-file',str(shadow_params),'-p','operator_stationary_confirmed:=true',
            '-p',f'behavior_tree:={tree}','-p','require_hwt601_fusion:=true',
            '-p',f'metric_self_body_enabled:={str(CASE in ("mast_start","mast_start_scan","mast_start_full_scan")).lower()}',
            '-p','hwt601_active_drive:=true','-p','allow_explore_mission:=true',
            '-p','require_localization:=false','-p',f'initial_scan_enabled:={"true" if CASE in ("scan","scan_route","mast_start_scan","mast_start_full_scan") else "false"}',
            '-p',f'initial_scan_angle_rad:={2*math.pi if CASE=="mast_start_full_scan" else .3}',
            '-p',f'initial_scan_timeout_s:={210.0 if CASE=="mast_start_full_scan" else 28.0}',
            '-p',f'prealign_enabled:={"true" if CASE in ("scan","scan_route","mast_start_scan","mast_start_full_scan") else "false"}','-p','region_graph_shadow_enabled:=false',
            '-p','metric_session_id:=synthetic-metric-20260930',
            '-p',f'metric_scope_map_fingerprint:={binding}',
            '-p','wohnungserkundung_accessible_scope_verified:=true',
            '-p','wohnungserkundung_scope_id:=synthetic-metric-scope',
            '-p','wohnungserkundung_scope_polygon_xy:=[-0.8,-1.8,6.8,-1.8,6.8,1.8,-0.8,1.8]',
            '-p','goal_timeout_s:=12.0','-p',f'overall_timeout_s:={4.0 if CASE in ("empty","filtered") else 240.0 if CASE=="mast_start_full_scan" else 60.0}',
            '-p',f'min_frontier_size_m:={1000.0 if CASE=="filtered" else .3}',
            '-p','replan_period_s:=0.2','-p',f'storage_directory:={logdir / "synthetic-maps"}']
        log=open(logdir/'explorer.log','w')
        ps.append((subprocess.Popen([sys.executable,'-c','from explore.explore_node import main; main()',*explorer_args],stdout=log,stderr=subprocess.STDOUT),log))
        rclpy.init(args=explorer_args)
        gate=CmdVelMissionGate();shadow=Hwt601ShadowNode()
        sources=Sources();nav=FakeNav(sources);maps=RobotMapManager()
        nodes=[gate,shadow,sources,nav,maps]
        for group in ((nav,maps),(gate,),(shadow,),(sources,)):
            ex=MultiThreadedExecutor(num_threads=4) if len(group)>1 else SingleThreadedExecutor()
            for node in group:ex.add_node(node)
            def spin(executor=ex):
                while not spin_stop.is_set():
                    executor.spin_once(timeout_sec=.1)
            thread=threading.Thread(target=spin,daemon=True);thread.start()
            executors.append(ex);threads.append(thread)
        sources.sample_thread.start()
        def wait(predicate,seconds=6):
            deadline=time.monotonic()+seconds
            while time.monotonic()<deadline:
                if predicate():return True
                time.sleep(.05)
            return False
        print('RESOLVED',json.dumps({n:get_package_prefix(n) for n in
              ('explore','robot_navigation','robot_state_estimation','bt_orchestrator','mission_manager','robot_map_manager')}),flush=True)
        assert wait(lambda:sources.yaw_statuses and sources.yaw_statuses[-1].get('ready') is True,40),'yaw startup'
        assert wait(lambda:gate._hwt_guard.health.motion_failure() is None),'HWT startup'
        assert wait(lambda:sources.cmd.get_subscription_count()>0),'manager missing'
        def metric():
            return sources.phases[-1].get('metric_exploration',{}) if sources.phases else {}
        assert wait(lambda:metric().get('scope_bound')),'map/scope join'
        assert metric().get('source_fault') is None,metric()
        sources.cmd.publish(String(data='{"type":"explore"}'))
        if CASE=='late':
            assert wait(lambda:metric().get('child_terminal') is False,6)
            sources.cmd.publish(String(data='{"type":"cancel"}'))
        if CASE=='scan_route':
            assert wait(lambda:any(m.get('phase')=='we_initial_scan' for m in sources.phases),4),'scan not begun'
            sources.route_blocked=True
            assert wait(lambda:metric().get('state')=='failed',4),'unsafe scan did not stop'
            assert metric().get('first_rejecting_predicate')=='scan_footprint_invalid'
            assert not nav.goals,'unsafe scan dispatched child'
        elif CASE in ('empty','filtered'):
            assert wait(lambda:metric().get('state')=='partial',7),'empty selection not classified'
            assert not nav.goals,'filtered/empty map dispatched a child'
            assert metric().get('metric_completion_candidate',False)==(CASE=='empty')
        else:
            assert wait(lambda:len(nav.goals)>=1,220 if CASE=='mast_start_full_scan' else 44 if CASE in ('scan','scan_route','mast_start_scan') else 10),('first autonomous child missing',sources.phases[-2:])
        if CASE in ('scan','mast_start_scan','mast_start_full_scan'):
            assert any(m.get('phase')=='we_initial_scan' for m in sources.phases),'initial scan not exercised'
            assert abs(math.atan2(math.sin(sources.yaw),math.cos(sources.yaw)))<.15,'prealignment did not restore approach heading'
            if CASE=='mast_start_full_scan':
                assert sources.yaw>6.,'full initial product revolution missing'
        if CASE in ('chain','mast_start','mast_start_scan','mast_start_full_scan'):
            optional=sources.create_publisher(String,'/explore/region_graph/status_json',10)
            optional.publish(String(data='{"current_region":"foreign","ready":false}'))
            if CASE=='chain':sources.map_variant=1
            time.sleep(2.)
            assert len(nav.goals)==1 and not nav.canceled,'harmless map updates canceled child'
            nav.release=True
            assert wait(lambda:len(nav.goals)>=3,15),'three map-derived children missing'
            assert wait(lambda:sources.phases[-1].get('frontiers_visited',0)>=3,8),'three observations not reached'
            assert len({tuple(g['target']) for g in nav.goals[:3]})==3
            assert nav.goals[1]['target'][0]>2.1,'open connection not crossed'
        elif CASE=='blocked':
            assert wait(lambda:len(nav.goals)>=2,10),'alternative autonomous goal missing'
            assert nav.goals[0]['target']!=nav.goals[1]['target']
            assert metric()['chain'][0]['decision']=='task_unreached_cause_unproven'
        elif CASE=='route':
            sources.route_blocked=True
            assert wait(lambda:nav.canceled),'invalid route retained child'
            time.sleep(1.)
            assert len(nav.goals)==1
        elif CASE in ('estop','sensor','actuator','pose','map','cancel_failed','late'):
            if CASE=='estop':sources.estop_active=True
            if CASE=='sensor':sources.sensor_on=False
            if CASE=='actuator':sources.actuator_fault=True
            if CASE=='pose':sources.pose_on=False
            if CASE=='map':sources.map_on=False
            if CASE in ('cancel_failed','late'):sources.cmd.publish(String(data='{"type":"cancel"}'))
            assert wait(lambda:any(m.get('state') in ('failed','canceled') for m in sources.manager[-5:]),10),'hard case not terminal'
            time.sleep(.7)
            assert len(nav.goals)==1,'automatic restart after hard case'
        elif CASE=='budget':
            assert wait(lambda:len(nav.goals)>=2,16),'timeout did not permit healthy alternative/reevaluation'
        elif CASE=='hold':
            sources.raw_on=False;time.sleep(.261);sources.raw_on=True
            assert wait(lambda:nav.canceled),'HOLD child not terminal'
            assert wait(lambda:any(m.get('phase')=='we_hwt_hold' for m in sources.phases))
            # Repeated fault and moving odometry must retain the original deadline.
            deadline=sources.phases[-1].get('hwt_hold_deadline_monotonic')
            sources.moving=True
            recovered_after=time.time()+.4
            assert wait(lambda:sources.yaw_samples and sources.yaw_samples[-1]>=recovered_after
                        and 0<=time.time()-sources.yaw_samples[-1]<.12,5),'first gap did not restore fresh yaw'
            sources.raw_on=False;time.sleep(.261);sources.raw_on=True
            time.sleep(1.4)
            assert len(nav.goals)==1 and sources.phases[-1].get('hwt_hold_deadline_monotonic')==deadline
            sources.moving=False
            assert wait(lambda:len(nav.goals)>=2,5),'HWT resume child missing'
            assert nav.goals[0]['target']==nav.goals[1]['target']
            assert sources.gate_status[-1].get('resume_sequence',0)>=1
        sources.cmd.publish(String(data='{"type":"cancel"}'))
        assert wait(lambda:sources.manager[-1].get('state') in ('canceled','failed'),6),'parent not terminal'
        assert wait(lambda:sources.phases[-1].get('state') in ('canceled','failed','partial'),4),'explorer not terminal'
        if CASE!='cancel_failed':
            assert wait(lambda:nav.active==0,6),'final child not terminal'
        assert nav.maximum==(0 if CASE in ('empty','filtered','scan_route') else 1),'simultaneous children'
        assert wait(lambda:all(abs(v)<1e-9 and abs(w)<1e-9 for _,v,w in sources.out[-8:]),3),'gate did not stop'
        if CASE in ('chain','blocked','hold','budget','mast_start','mast_start_scan','mast_start_full_scan'):
            running=[m for m in sources.manager if m.get('state')=='running']
            assert len({m.get('active_command',{}).get('request_id') for m in running})==1,'parent mission changed'
        assert all(m.get('map_ready_to_save') is False for m in sources.phases)
        summary=dict(result='PASS',case=CASE,goals=nav.goals,canceled=nav.canceled,
                     maximum_active_children=nav.maximum,metric=metric(),
                     source_observation=dict(yaw=sources.yaw,raw_samples=len(sources.raw_stamps),
                        maximum_raw_gap_s=max((b-a for a,b in zip(sources.raw_stamps,sources.raw_stamps[1:])),default=0.)),
                     no_semantic_task_owner=True,save_permission=False)
        (logdir/'result.json').write_text(json.dumps(summary,indent=2,default=str))
        print(json.dumps(summary,default=str),flush=True)
    except Exception:
        if 'sources' in locals():
            failure_metric = metric() if 'metric' in locals() else (sources.phases[-1].get('metric_exploration',{}) if sources.phases else {})
            (logdir/'failure.json').write_text(json.dumps(dict(explorer=sources.phases[-8:],
                manager=sources.manager[-8:],metric=failure_metric,map_fault=failure_metric.get('source_fault'),
                yaw_status_tail=sources.yaw_statuses[-4:],gate_status_tail=sources.gate_status[-2:],
                source_observation=dict(yaw=sources.yaw,raw_samples=len(sources.raw_stamps),
                    maximum_raw_gap_s=max((b-a for a,b in zip(sources.raw_stamps,sources.raw_stamps[1:])),default=0.))),indent=2,default=str))
        raise
    finally:
        if 'sources' in locals():
            sources.cmd.publish(String(data='{"type":"cancel"}'))
            end=time.monotonic()+5.
            while sources.manager and sources.manager[-1].get('state')=='running' and time.monotonic()<end:time.sleep(.05)
            if 'nav' in locals():nav.shutdown_requested=True
            time.sleep(.1)
            sources.sample_stop.set();sources.sample_thread.join(timeout=2)
        spin_stop.set()
        for ex in executors:ex.wake()
        for thread in threads:thread.join(timeout=3)
        for ex in executors:ex.shutdown(timeout_sec=2)
        for node in nodes:node.destroy_node()
        if rclpy.ok():rclpy.shutdown()
        for process,log in ps:
            if process.poll() is None:process.send_signal(signal.SIGINT)
        for process,log in ps:
            try:process.wait(timeout=5)
            except subprocess.TimeoutExpired:process.terminate();process.wait(timeout=5)
            log.close()
        sys.setswitchinterval(old_switch)

if __name__=='__main__':run()
