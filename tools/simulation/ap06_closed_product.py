#!/usr/bin/env python3
"""Actual Mission/BT/Explorer/Nav2/EKF/SLAM with finite simulated devices.

Run ONLY inside an isolated, device-free container, AP06_SIMULATION=1 and a
dedicated ROS_DOMAIN_ID. Device identities here describe memory endpoints;
they do not qualify USB, transport latency, real stopping or physical coverage.
No truth occupancy publisher, truth TF or NavigateToPose goal sender exists.
"""
import argparse
from collections import deque
import functools
import gc
import json
import math
import multiprocessing
import os
from pathlib import Path
import signal
import struct
import subprocess
import sys
import threading
import time
import traceback
from types import SimpleNamespace
from ap06_trace import EventTrace, storage_budget

import numpy as np
import yaml
import rclpy
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from rclpy.serialization import serialize_message
from rclpy.qos import DurabilityPolicy, QoSProfile, qos_profile_sensor_data
from geometry_msgs.msg import TransformStamped, Twist
from lifecycle_msgs.srv import ChangeState, GetState
from action_msgs.msg import GoalStatusArray
from nav_msgs.msg import OccupancyGrid, Path as NavPath
from sensor_msgs.msg import LaserScan, PointCloud2, PointField
from std_msgs.msg import Bool, String
from std_srvs.srv import Trigger
from tf2_msgs.msg import TFMessage
from tf2_ros import StaticTransformBroadcaster
from robot_interfaces.msg import NearFieldStatus
from ament_index_python.packages import get_package_prefix

from ap06_world import World
from explore.portal_source_adapter import raw_map_portal_source_from_values
from ap06_sensors import vl53_producer, oak_cloud
from ap06_isolation import require_isolation


class MemoryESS:
    """Modbus API endpoint, with counters from actual simulated wheel motion."""
    def __init__(self, world, **_kwargs):
        self.world = world
        self.connected = False
        self.registers = {1: {}, 2: {}}
        self.started = {1: False, 2: False}
        self.writes = 0
        self.lock = threading.RLock()
        self.advanced_at = time.monotonic()
        self.last_slow_advance = None

    def advance(self):
        began = time.monotonic()
        with self.lock:
            now = time.monotonic()
            remaining, self.advanced_at = now-self.advanced_at, now
            elapsed = remaining
            steps = 0
            command = self.command()
            # Integrate known, unchanged input over real elapsed time. This
            # never fills missed sensor samples or rewrites their timestamps.
            while remaining > 1e-9:
                step = min(.01, remaining)
                self.world.integrate(command, step)
                remaining -= step
                steps += 1
            ended = time.monotonic()
            if ended-began > .02:
                self.last_slow_advance = dict(begin=began, end=ended,
                    thread_id=threading.get_native_id(), lock_wait_s=now-began,
                    elapsed_s=elapsed, steps=steps, pose=self.world.pose.tolist(),
                    velocity=self.world.velocity.tolist())

    def connect(self):
        self.connected = True
        return True

    def close(self):
        self.connected = False
        self.started = {1: False, 2: False}

    def response(self, words=()):
        return SimpleNamespace(registers=words, isError=lambda: not self.connected)

    def read_holding_registers(self, address, count, device_id):
        self.advance()
        if address == 10 and count == 3:
            counter = round(self.world.motor_positions[device_id-1]) & 0xffffffff
            v, w = self.world.velocity
            speed = (v+(-1 if device_id == 1 else 1)*w*.3845/2)*10/(2*math.pi*.0624)*60
            if device_id == 2:
                speed = -speed
            return self.response([counter >> 16, counter & 0xffff, round(speed) & 0xffff])
        return self.response([{17: 1000, 25: 0, 257: 4000}.get(address+i,
            self.registers[device_id].get(address+i, 0)) for i in range(count)])

    def write_register(self, address, value, device_id):
        if address not in (29, 30, 31, 32, 39):
            raise RuntimeError('undeclared actuator register')
        with self.lock:
            self.advance()
            self.writes += 1
            self.registers[device_id][address] = value
            if address == 39:
                self.started[device_id] = value == 2
        return self.response()

    def command(self):
        speeds = []
        for motor in (1, 2):
            value = self.registers[motor].get(29, 0) if self.started[motor] else 0
            value = value-65536 if value & 32768 else value
            speeds.append(value*2*math.pi*.0624/600 * (1 if motor == 1 else -1))
        return ((speeds[0]+speeds[1])/2, (speeds[1]-speeds[0])/.3845)


def device_parameters(repo):
    """Use the production source contracts at the simulated byte endpoints."""
    common = {
        'base_hardware': yaml.safe_load((repo/'src/base_hardware/config/base_hardware_params.yaml').read_text())['base_hardware'],
        'hwt601_imu': yaml.safe_load((repo/'src/robot_state_estimation/config/hwt601_shadow.yaml').read_text())['hwt601_shadow_reader']}
    common['base_hardware']['ros__parameters'].update(
        dry_run=False, allow_rs485=True, publish_tf=False,
        odom_topic='/fusion/hwt601/wheel_odom_raw', encoder_timing_recovery_enabled=True,
        # The same existing publication mode qualified at the real LAB source.
        # Native DDS can hold a writer's GIL during discovery/backpressure;
        # acquisition must not share that pause. No sample is restamped.
        isolate_feedback_output=True, feedback_output_cpu_affinity=[-1])
    common['hwt601_imu']['ros__parameters'].update(
        development_contract=True, response_timeout_s=.05, sensor_timeout_s=.30,
        isolate_sensor_output=True)
    return common


class MemoryHWT:
    """FC03 byte endpoint; actual transport/CRC/deadline checks stay in use."""
    def __init__(self, world, bus, fault, **_kwargs):
        self.world, self.bus, self.fault = world, bus, fault
        self.is_open = True
        self.buffer = b''
        self.timeout = .05

    def reset_input_buffer(self):
        self.buffer = b''

    def write(self, request):
        from robot_state_estimation.hwt601_protocol import append_crc, build_read_holding_registers
        if request != build_read_holding_registers(80, 52, 6):
            raise RuntimeError('simulation HWT accepts FC03 motion reads only')
        self.bus.advance()
        gyro = round((float(self.world.velocity[1])+.001)/math.radians(400)*32768) & 0xffff
        self.buffer = append_crc(bytes([80, 3, 12])+struct.pack('>6H', 0, 0, 8192, 0, 0, gyro))
        return len(request)

    def read(self, count):
        if time.monotonic() < self.fault['until']:
            time.sleep(self.timeout)
            return b''
        result, self.buffer = self.buffer[:count], self.buffer[count:]
        return result

    def close(self):
        self.is_open = False


class Sensors(Node):
    def __init__(self, world, bus, out, masked, beams, *, record_plant=True):
        super().__init__('ap06_simulated_devices')
        self.world, self.bus, self.masked, self.beams = world, bus, masked, beams
        self.last = time.monotonic()
        self.tick_gaps = []
        self.trace = (out/'plant.jsonl').open('w', buffering=1) if record_plant else None
        self.scan_pub = self.create_publisher(LaserScan, '/scan', qos_profile_sensor_data)
        self.left = self.create_publisher(PointCloud2, '/near_field/left/points', 10)
        self.right = self.create_publisher(PointCloud2, '/near_field/right/points', 10)
        self.status = self.create_publisher(NearFieldStatus, '/near_field/status', 10)
        self.left_costmap = self.create_publisher(PointCloud2, '/near_field/left/points_costmap', 10)
        self.right_costmap = self.create_publisher(PointCloud2, '/near_field/right/points_costmap', 10)
        self.oak = self.create_publisher(PointCloud2, '/oak/points', 10)
        self.vl53 = vl53_producer(self, world, dict(pub_left=self.left, pub_right=self.right,
            pub_left_cm=self.left_costmap, pub_right_cm=self.right_costmap, pub_status=self.status))
        qos = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL)
        # Only the model switch endpoint; the genuine SafetyMonitor owns the
        # BT/gate /safety/estop decision and heartbeat.
        self.estop = self.create_publisher(Bool, '/safety/estop_request', qos)
        self.static_tf = StaticTransformBroadcaster(self)
        tf = TransformStamped()
        tf.header.stamp = self.get_clock().now().to_msg()
        tf.header.frame_id, tf.child_frame_id = 'base_link', 'laser_frame'
        tf.transform.translation.x, tf.transform.translation.z = .245, .660
        tf.transform.rotation.z, tf.transform.rotation.w = math.sin(math.pi/4), math.cos(math.pi/4)
        transforms = [tf]
        for frame, x, y, z, pitch in (
                ('vl53_left_link', .290, .095, .215, 0.),
                ('vl53_right_link', .290, -.095, .215, 0.),
                ('ap06_camera_frame', .15, 0., 1.25, .3306)):
            transform = TransformStamped()
            transform.header.stamp = tf.header.stamp
            transform.header.frame_id, transform.child_frame_id = 'base_link', frame
            transform.transform.translation.x, transform.transform.translation.y = x, y
            transform.transform.translation.z = z
            transform.transform.rotation.y, transform.transform.rotation.w = math.sin(pitch/2), math.cos(pitch/2)
            transforms.append(transform)
        self.static_tf.sendTransform(transforms)
        if record_plant:
            self.create_timer(.01, self.tick)
        self.create_timer(.1, self.publish)

    def tick(self):
        now = time.monotonic()
        dt, self.last = now-self.last, now
        if dt > .03:
            self.tick_gaps.append(dt)
        self.bus.advance()
        self.trace.write(json.dumps([now, *self.world.pose.tolist(), *self.world.velocity.tolist()])+'\n')

    def publish(self):
        stamp = getattr(self, '_sensor_stamp', None)
        if stamp is None:
            stamp = self.get_clock().now().to_msg()
        angles, ranges = self.world.laser(mask=self.masked, beams=self.beams)
        scan = LaserScan()
        scan.header.stamp, scan.header.frame_id = stamp, 'laser_frame'
        scan.angle_min, scan.angle_max = 0., float(angles[-1])
        scan.angle_increment, scan.scan_time = float(angles[1]), .1
        scan.range_min, scan.range_max = .05, 10.
        scan.ranges = ranges.astype(np.float32).tolist()
        self.scan_pub.publish(scan)
        self.vl53._tick()
        self.oak.publish(oak_cloud(self.world, stamp))
        self.estop.publish(Bool(data=self.world.collision))


class FaultWindow:
    def __init__(self, value):
        self.value = value

    def __getitem__(self, key):
        if key != 'until':
            raise KeyError(key)
        return self.value.value

    def __setitem__(self, key, value):
        if key != 'until':
            raise KeyError(key)
        self.value.value = value


class DeviceMirror:
    """Read-only oracle telemetry, never supplied to any product callback."""
    def __init__(self, geometry, telemetry):
        self.geometry, self.telemetry = geometry, telemetry

    def snapshot(self):
        return list(self.telemetry[:])

    @property
    def velocity(self):
        return np.array(self.snapshot()[3:5])

    @property
    def collision(self):
        return bool(self.snapshot()[7])

    @property
    def travel(self):
        return self.snapshot()[5]

    @property
    def minimum_clearance(self):
        return self.snapshot()[6]

    @property
    def rear_cleared(self):
        return bool(self.snapshot()[8])

    @property
    def writes(self):
        return int(self.snapshot()[9])

    def local(self, points):
        return self.geometry.local(points)

    def map_oracle(self, *args):
        return self.geometry.map_oracle(*args)


def finite_sensor_process(case, out, masked, beams, telemetry, ready, halt, sensor_cpu=None):
    """Finite rays from an actual fresh plant sample, in their own interpreter.

    Source stamps and the 100-Hz plant remain owned by the device process.
    Expired plant snapshots produce no new sensor frames or healthy heartbeat.
    This worker never integrates the plant, writes registers, or publishes TF
    except the existing fixed sensor mounts.
    """
    require_isolation()
    if sensor_cpu is not None:
        os.sched_setaffinity(0, {sensor_cpu})
    sys.setswitchinterval(.001)
    model = World(case['door_m'], case['start'])
    samples = dict(published=0, withheld_stale_plant=0)
    rclpy.init()
    node = executor = None
    latency = (out/'sensor_executor_latency.jsonl').open('w', buffering=1)
    try:
        class FiniteSensors(Sensors):
            def publish(self):
                snapshot = telemetry[:]
                if not 0 <= time.monotonic()-snapshot[10] <= .03:
                    samples['withheld_stale_plant'] += 1
                    return
                model.pose[:] = snapshot[:3]
                model.velocity[:] = snapshot[3:5]
                model.collision = bool(snapshot[7])
                acquisition = rclpy.time.Time(seconds=int(snapshot[11]),
                    nanoseconds=int(snapshot[12]), clock_type=self.get_clock().clock_type)
                self._sensor_stamp = acquisition.to_msg()
                self.vl53.get_clock = lambda: SimpleNamespace(now=lambda: acquisition)
                samples['published'] += 1
                super().publish()
        node = FiniteSensors(model, None, out, masked, beams, record_plant=False)
        executor = SingleThreadedExecutor(); executor.add_node(node)
        ready.set()
        while not halt.is_set():
            began, cpu = time.monotonic(), time.process_time()
            executor.spin_once(timeout_sec=.02)
            ended = time.monotonic()
            if ended-began > .05:
                latency.write(json.dumps(dict(begin=began, end=ended,
                    duration_s=ended-began, process_cpu_s=time.process_time()-cpu))+'\n')
    finally:
        if executor is not None:
            executor.shutdown(timeout_sec=1.)
        if node is not None:
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
        latency.close()
        (out/'sensor_result.json').write_text(json.dumps(dict(samples,
            actual_cpu_affinity=sorted(os.sched_getaffinity(0)),
            separate_process=True, writes_registers=False, plant_integration=False), indent=2)+'\n')


def device_process(case, out, device_file, masked, beams, fault_value, telemetry, ready, halt,
                   source_cpu=None, sensor_cpu=None, sensor_worker=finite_sensor_process):
    """Own physical plant and original sources in a separate Python process.

    ROS graph construction/service serialization in the mission supervisor
    must not hold the encoder/gyro producers' interpreter lock. Source periods,
    clocks, deadlines, frames, plant integration and checks remain original.
    Shared memory carries only passive oracle telemetry and fault injection.
    """
    require_isolation()
    initialization_affinity = sorted(os.sched_getaffinity(0))
    worker_cpus = set(initialization_affinity)-{source_cpu}
    if sensor_cpu is not None and sensor_cpu != source_cpu:
        worker_cpus.add(sensor_cpu)
    if source_cpu is not None and worker_cpus:
        os.sched_setaffinity(0, worker_cpus)
    sys.setswitchinterval(.001)
    model = World(case['door_m'], case['start'])
    fault = FaultWindow(fault_value)
    from base_hardware import base_hardware_node as base_module
    from robot_state_estimation import hwt601_imu_node as raw_module
    from robot_state_estimation.hwt601_transport import Hwt601SerialTransport
    bus = MemoryESS(model)
    base_module.ModbusSerialClient = lambda **kw: bus
    class SimulatedBase(base_module.BaseHardware):
        def _connect_modbus(self):
            def aliases(port):
                if port != '/dev/ttyUSB_BASE':
                    raise RuntimeError('wrong memory bus alias')
                return 'memory://ap06/base'
            def identity(port):
                if port != 'memory://ap06/base':
                    raise RuntimeError('wrong memory bus identity')
            self.encoder_owner_aliases, self.encoder_owner_usb = aliases, identity
            super()._connect_modbus()
    raw_module.Hwt601SerialTransport = functools.partial(Hwt601SerialTransport,
        serial_factory=lambda **kw: MemoryHWT(model, bus, fault, **kw))
    stopped = threading.Event()
    threads, executors, nodes = [], [], []
    latency_log = (out/'device_executor_latency.jsonl').open('w',buffering=1)
    gc_begin = {}
    def gc_timing(phase, info):
        generation = info['generation']
        if phase == 'start':
            gc_begin[generation] = time.monotonic()
        elif generation in gc_begin:
            ended = time.monotonic(); began = gc_begin.pop(generation)
            if ended-began > .05:
                latency_log.write(json.dumps(dict(node='python_gc',begin=began,end=ended,
                    duration_s=ended-began,generation=generation,collected=info['collected']))+'\n')
    gc.callbacks.append(gc_timing)
    def interrupt(_signum, _frame):
        halt.set()
    signal.signal(signal.SIGINT, interrupt)
    signal.signal(signal.SIGTERM, interrupt)
    context = multiprocessing.get_context('spawn')
    sensor_ready = context.Event()
    sensor_device = context.Process(target=sensor_worker, args=(case, out, masked, beams,
        telemetry, sensor_ready, halt, sensor_cpu), name='ap06-finite-sensors')
    rclpy.init(args=['--ros-args', '--params-file', str(device_file)])
    try:
        # Spawn independent sources before the first live encoder baseline.
        # ARM vfork/exec can suspend every parent thread for hundreds of ms;
        # doing this after starting the acquisition executors created a real,
        # unbridgeable wheel gap. No clock, sample or limit is rewritten.
        sensor_device.start()
        if not sensor_ready.wait(20.):
            raise RuntimeError('independent finite sensor process readiness')
        class RecordedPlant(Node):
            def __init__(self):
                super().__init__('ap06_simulated_plant')
                self.last = time.monotonic(); self.tick_gaps = []
                self.trace = (out/'plant.jsonl').open('w', buffering=1)
                self.create_timer(.01, self.tick)
            def tick(self):
                now = time.monotonic(); dt, self.last = now-self.last, now
                if dt > .03:
                    self.tick_gaps.append(dt)
                with bus.lock:
                    bus.advance()
                    stamp = self.get_clock().now().to_msg()
                    state = [*model.pose.tolist(), *model.velocity.tolist(), model.travel,
                             model.minimum_clearance, float(model.collision),
                             float(model.rear_cleared), float(bus.writes), time.monotonic(),
                             float(stamp.sec), float(stamp.nanosec)]
                telemetry[:] = state
                self.trace.write(json.dumps([now, *state[:5]])+'\n')
        sensors = RecordedPlant()
        raw_node = raw_module.Hwt601ImuNode()
        base_node = SimulatedBase()
        nodes = [sensors, raw_node, base_node]
        # Spawned DDS/sensor workers and native DDS threads must inherit the
        # other available CPUs, not the single acquisition CPU. Pin the owner
        # and its subsequent acquisition threads before timers run. Early
        # pinning also placed every writer on that CPU. Remove this measured
        # coupling; remaining discovery/load gaps must still fail their gates.
        output_affinities = {
            'encoder': sorted(os.sched_getaffinity(base_node.feedback_output.pid)),
            'imu': (sorted(os.sched_getaffinity(raw_node._sensor_output.pid))
                    if raw_node._sensor_output is not None else None)}
        if source_cpu is not None:
            os.sched_setaffinity(0, {source_cpu})
        for node in nodes:
            ex = SingleThreadedExecutor(); ex.add_node(node); executors.append(ex)
            def loop(ex=ex, name=node.get_name()):
                try:
                    while not stopped.is_set():
                        began = time.monotonic(); process_began=time.process_time(); thread_began=time.thread_time()
                        ex.spin_once(timeout_sec=.05)
                        ended = time.monotonic()
                        if ended-began > .1:
                            latency_log.write(json.dumps(dict(node=name,begin=began,end=ended,
                                duration_s=ended-began,process_cpu_s=time.process_time()-process_began,
                                thread_cpu_s=time.thread_time()-thread_began,
                                last_slow_advance=bus.last_slow_advance))+'\n')
                except Exception:
                    traceback.print_exc(); halt.set()
            thread = threading.Thread(target=loop, daemon=True)
            threads.append(thread); thread.start()
        ready.set()
        while not halt.wait(.05):
            if not sensor_device.is_alive():
                raise RuntimeError('independent finite sensor process exited')
    finally:
        if 'base_node' in locals():
            base_node._stop_both_motors(force=True)
            deadline = time.monotonic()+1.
            while max(abs(model.velocity)) >= .005 and time.monotonic() < deadline:
                time.sleep(.01)
        stopped.set()
        halt.set()
        if sensor_device.pid is not None:
            sensor_device.join(3.)
            if sensor_device.is_alive():
                sensor_device.terminate(); sensor_device.join(2.)
        for thread in threads:
            thread.join(2.)
        for ex in executors:
            ex.shutdown(timeout_sec=1.)
        for node in reversed(nodes):
            node.destroy_node()
        gc.callbacks.remove(gc_timing)
        latency_log.close()
        if 'sensors' in locals():
            sensors.trace.close()
            (out/'device_result.json').write_text(json.dumps(dict(
                plant_tick_gaps=sensors.tick_gaps, simulated_register_writes=bus.writes,
                initialization_cpu_affinity=initialization_affinity,
                passive_worker_cpu_affinity=sorted(worker_cpus),
                publication_cpu_affinities=locals().get('output_affinities'),
                source_periods_unchanged=True, separate_source_process=True,
                separate_finite_sensor_process=True,
                finite_sensor_process_exitcode=sensor_device.exitcode,
                actual_cpu_affinity=sorted(os.sched_getaffinity(0))), indent=2)+'\n')
        if rclpy.ok():
            rclpy.shutdown()


class Observer(Node):
    def __init__(self, out):
        super().__init__('ap06_independent_observer')
        self.map = None
        self.costmap = None
        self.last_scan = None
        self.create_subscription(LaserScan, '/scan_normiert',
            lambda msg: setattr(self, 'last_scan', msg), qos_profile_sensor_data)
        # Full payloads remain byte-for-byte in the lossless JSONL journal.
        # Streaming avoids exhausting map-save reserve with temporary raw logs.
        # Acceptance only needs latest
        # status views; retaining every diagnostic object grows through 900 s.
        self.phases, self.manager, self.fusion = (deque(maxlen=8) for _ in range(3))
        self.fusion_at = []
        self.action_active, self.action_maximum, self.command_values = {}, {}, {}
        self.tf_children = set()
        self.transforms = {}
        self.tf_recorded_at = {}
        self.out = out
        self.command = self.create_publisher(String, '/mission_manager/command_json', 10)
        self.events = EventTrace(out/'events.jsonl')
        qos = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL)
        self.create_subscription(OccupancyGrid, '/map', lambda msg: setattr(self, 'map', msg), qos)
        self.create_subscription(OccupancyGrid, '/global_costmap/costmap',
                                 lambda msg: setattr(self, 'costmap', msg), qos)
        def plan_callback(msg, topic='/plan'):
            self.events.write(json.dumps({'at': time.monotonic(), 'topic': topic,
                'frame': msg.header.frame_id,
                'stamp': [msg.header.stamp.sec, msg.header.stamp.nanosec],
                'latest_tf': [self.tf_values(t) for t in self.transforms.values()],
                'points': [[p.pose.position.x, p.pose.position.y] for p in msg.poses]})+'\n')
            self.events.flush()
        self.create_subscription(NavPath, '/plan', plan_callback, 10)
        self.create_subscription(NavPath, '/received_global_plan',
                                 functools.partial(plan_callback, topic='/received_global_plan'), 10)
        for topic, dest in (('/explore/status_json', self.phases),
                            ('/mission_manager/status_json', self.manager),
                            ('/fusion/hwt601/status_json', self.fusion)):
            def callback(msg, topic=topic, dest=dest):
                data = json.loads(msg.data)
                dest.append(data)
                if dest is self.fusion:
                    self.fusion_at.append((time.monotonic(),
                        {'recovery_state': data.get('recovery_state')}))
                self.events.write(json.dumps({'at': time.monotonic(), 'topic': topic, 'data': data})+'\n')
                self.events.flush()
            self.create_subscription(String, topic, callback, qos if dest is self.manager else 10)
        def base_state(msg):
            self.events.write(json.dumps({'at':time.monotonic(),
                'topic':'/base_hardware/state_json','data':json.loads(msg.data)})+'\n')
            self.events.flush()
        self.create_subscription(String,'/base_hardware/state_json',base_state,10)
        self.create_subscription(TFMessage, '/tf', self.on_tf, 100)
        for topic in ('/navigate_to_pose/_action/status', '/explore_area/_action/status'):
            def status_callback(msg, topic=topic):
                active = [[int(value) for value in s.goal_info.goal_id.uuid]
                          for s in msg.status_list if s.status in (1, 2, 3)]
                self.action_active[topic] = active
                self.action_maximum[topic] = max(len(active), self.action_maximum.get(topic, 0))
                self.events.write(json.dumps({'at': time.monotonic(), 'topic': topic, 'active': active})+'\n')
                self.events.flush()
            self.create_subscription(GoalStatusArray, topic, status_callback, qos)
        for topic in ('/cmd_vel_nav_raw', '/cmd_vel_nav', '/cmd_vel_smoothed', '/cmd_vel'):
            def velocity_callback(msg, topic=topic):
                self.command_values[topic] = (msg.linear.x, msg.angular.z)
            self.create_subscription(Twist, topic, velocity_callback, 100)

    @staticmethod
    def tf_values(transform):
        return dict(parent=transform.header.frame_id, child=transform.child_frame_id,
                    stamp=[transform.header.stamp.sec, transform.header.stamp.nanosec],
                    translation=[transform.transform.translation.x,
                                 transform.transform.translation.y,
                                 transform.transform.translation.z],
                    rotation=[transform.transform.rotation.x,
                              transform.transform.rotation.y,
                              transform.transform.rotation.z,
                              transform.transform.rotation.w])

    def on_tf(self, msg):
        now = time.monotonic()
        for transform in msg.transforms:
            pair = (transform.header.frame_id, transform.child_frame_id)
            self.tf_children.add(pair)
            self.transforms[pair] = transform
            if now-self.tf_recorded_at.get(pair, 0.) >= 1.:
                self.events.write(json.dumps(dict(at=now, topic='/tf',
                    transform=self.tf_values(transform)))+'\n')
                self.tf_recorded_at[pair] = now

    def owners(self):
        endpoints = {tuple(int(v) for v in e.endpoint_gid): e.node_name
                     for e in self.get_publishers_info_by_topic('/tf')}
        provenance = {}
        path = self.out/'tf_probe.log'
        if path.exists():
            for line in path.read_text().splitlines():
                if line.startswith('{'):
                    event = json.loads(line)
                    provenance.setdefault(event['parent']+'->'+event['child'], set()).add(tuple(event['gid']))
        return {pair: [endpoints.get(gid, 'unresolved_publisher') for gid in sorted(gids)]
                for pair, gids in provenance.items()}

    def metric(self):
        return self.phases[-1].get('metric_exploration', {}) if self.phases else {}


def transition_lifecycle(change_client, state_client, transition, timeout=30.):
    """Send one transition and prove its actual state within one original budget.

    Fast DDS service discovery can precede response-reader matching. A lost
    acknowledgement must not cause a duplicate non-idempotent transition.
    GetState is a read-only original server query, never an inferred state.
    """
    deadline = time.monotonic()+timeout
    def state():
        future = state_client.call_async(GetState.Request())
        until = min(deadline, time.monotonic()+1.)
        while not future.done() and time.monotonic() < until:
            time.sleep(.02)
        if not future.done():
            state_client.remove_pending_request(future)
            return None
        return future.result().current_state.id
    expected_before, expected_after = (1, 2) if transition == 1 else (2, 3)
    current = None
    while current is None and time.monotonic() < deadline:
        current = state()
    if current != expected_before:
        raise RuntimeError(f'lifecycle precondition {current}, expected {expected_before}')
    request = ChangeState.Request(); request.transition.id = transition
    future = change_client.call_async(request)
    while time.monotonic() < deadline:
        if future.done() and not future.result().success:
            raise RuntimeError('actual lifecycle transition rejected')
        current = state()
        if current == expected_after:
            acknowledged = future.done() and future.result().success
            if not future.done():
                change_client.remove_pending_request(future)
            return dict(transition=transition, actual_state=current, acknowledgement_received=bool(acknowledged))
        time.sleep(.02)
    raise TimeoutError('actual lifecycle transition state not confirmed')


def params(repo, out, unknown_space_policy='observed_only'):
    if unknown_space_policy not in ('observed_only', 'sensor_guarded'):
        raise ValueError('Unknown unknown_space_policy')
    p = yaml.safe_load((repo/'src/robot_navigation/config/nav2_params_real.yaml').read_text())
    if unknown_space_policy == 'sensor_guarded':
        def merge(target, overlay):
            for key, value in overlay.items():
                if isinstance(value, dict):
                    merge(target.setdefault(key, {}), value)
                else:
                    target[key] = value
        merge(p, yaml.safe_load((repo/'src/robot_navigation/config/nav2_sensor_guarded_mapping_params.yaml').read_text()))
    tree = str(repo/'src/explore/behavior_trees/navigate_to_pose_no_recovery.xml')
    p['bt_navigator']['ros__parameters']['default_nav_to_pose_bt_xml'] = tree
    p['bt_navigator']['ros__parameters']['default_nav_through_poses_bt_xml'] = str(
        repo/'tools/simulation/navigate_through_poses_no_recovery.xml')
    # Keep the actual static/obstacle/inflation layers and local rolling odom
    # frame. Omitting the obstacle layer also omits native footprint handling.
    p['hwt601_mapping_ekf'] = yaml.safe_load((repo/'src/robot_state_estimation/config/ekf_hwt601_mapping.yaml').read_text())['hwt601_mapping_ekf']
    p['slam_toolbox'] = yaml.safe_load((repo/'src/amadeus_lidar_bringup/config/slam_toolbox_amadeus.yaml').read_text())['slam_toolbox']
    p['slam_toolbox']['ros__parameters']['scan_topic'] = '/scan_normiert'
    collision_profile = ('collision_monitor_sensor_guarded_mapping_params.yaml'
                         if unknown_space_policy == 'sensor_guarded' else 'collision_monitor_mapping_params.yaml')
    p.update(yaml.safe_load((repo/'src/vl53_near_field/config'/collision_profile).read_text()))
    destination = out/'native_params.yaml'
    destination.write_text(yaml.safe_dump(p))
    return destination


def run(args):
    isolation = require_isolation()
    concept_deferred_departure = getattr(args, 'concept_defer_departure', False)
    if concept_deferred_departure:
        from ap06_departure_probe import validate_experiment_options
        validate_experiment_options(args)
    # Heavy geometry belongs to the supervisor, not spawned device sources.
    from explore.metric_frontier_runtime import MetricFrontierRuntime
    manifest_path = args.manifest
    manifest = json.loads(manifest_path.read_text())
    unknown_space_policy = getattr(args, 'unknown_space_policy', 'observed_only')
    execution_mode = getattr(args, 'execution_mode', 'continuous')
    if execution_mode == 'lab_slots' and unknown_space_policy != 'sensor_guarded':
        raise ValueError('lab_slots requires sensor_guarded')
    cases = manifest['positive']+manifest['negative']
    case = next(c for c in cases if c['id'] == args.case)
    out = args.output
    out.mkdir(parents=True, exist_ok=False)
    (out/'manifest.json').write_bytes(manifest_path.read_bytes())
    result = {'case': case, 'passed': False, 'hardware_qualified': False, 'isolation': isolation,
              'unknown_space_policy': unknown_space_policy,
        'execution_mode': execution_mode,
              'manifest_compatible': not (args.ideal_lidar or args.profile_selection or args.capture_decisions or args.capture_geometry or args.diagnostic_beams or concept_deferred_departure),
              'concept_deferred_departure': concept_deferred_departure,
              'actual_lidar_beams': args.diagnostic_beams or manifest['sensor']['lidar_beams'],
              'sensor_profile': 'native_mast_mask' if not args.ideal_lidar else 'ideal_full_360',
              'reference_geometry_provided_to_product': False, 'truth_map_publisher': False,
              'truth_tf_publisher': False, 'manual_navigation_goals': 0}
    storage = storage_budget(out)
    (out/'storage_preflight.json').write_text(json.dumps(storage, indent=2)+'\n')
    if not storage['ready']:
        result['error'] = 'insufficient mission evidence/map-save storage: '+json.dumps(storage)
        (out/'result.json').write_text(json.dumps(result, indent=2)+'\n')
        print(json.dumps(result), flush=True)
        return 1
    processes, streams, nodes, executors, threads = [], [], [], [], []
    stop = threading.Event()
    original_affinity = os.sched_getaffinity(0)
    allowed_cpus = sorted(original_affinity)
    source_cpu = allowed_cpus[-1] if len(allowed_cpus) >= 4 else None
    sensor_cpu = allowed_cpus[-2] if source_cpu is not None else None
    graph_cpus = allowed_cpus[:min(3, len(allowed_cpus)-2)] if source_cpu is not None else allowed_cpus
    # The six-core ARM host has one CPU outside the original graph/source/
    # sensor allocation. Keep sources and native graph unchanged and put the
    # Python Explorer there. Scheduling grants no time or geometry exemption.
    spare_cpus = [cpu for cpu in allowed_cpus
                  if cpu not in (*graph_cpus, source_cpu, sensor_cpu)]
    explorer_cpu = spare_cpus[0] if spare_cpus else None
    result['cpu_allocation'] = dict(available=allowed_cpus, graph=graph_cpus,
                                  source=source_cpu, sensors=sensor_cpu,
                                  explorer=explorer_cpu)
    def start(name, command):
        if name == 'explorer' and explorer_cpu is not None:
            command = ['taskset', '-c', str(explorer_cpu), *command]
        with (out/'commands.jsonl').open('a') as commands:
            commands.write(json.dumps({'name': name, 'argv': command})+'\n')
        stream = (out/(name+'.log')).open('w')
        streams.append(stream)
        processes.append((name, subprocess.Popen(command, stdout=stream, stderr=subprocess.STDOUT)))
    def spin(node):
        ex = SingleThreadedExecutor()
        ex.add_node(node)
        executors.append(ex)
        nodes.append(node)
        def loop():
            try:
                while not stop.is_set():
                    ex.spin_once(timeout_sec=.05)
            except Exception:
                traceback.print_exc()
                stop.set()
        thread = threading.Thread(target=loop, daemon=True)
        threads.append(thread)
        thread.start()
    def wait(predicate, timeout, label):
        until = time.monotonic()+timeout
        while time.monotonic() < until:
            if predicate():
                return
            failed = [(name, proc.poll()) for name, proc in processes if proc.poll() is not None]
            if failed or stop.is_set():
                raise RuntimeError(f'{label}: process/executor failure {failed}')
            time.sleep(.02)
        raise TimeoutError(label)
    def py(module):
        return [sys.executable, '-c', f'from {module} import main; main()']
    def executable(package, name):
        return str(Path(get_package_prefix(package))/'lib'/package/name)
    native = params(args.repo, out, unknown_space_policy)
    fault = {'until': 0.}
    model = World(case['door_m'], case['start'])
    try:
        sys.setswitchinterval(.001)
        # Transport injection only: production nodes calculate their own health.
        # Construct supervisor independently of the plant/source interpreter.
        common = device_parameters(args.repo)
        device_file = out/'device_params.yaml'
        device_file.write_text(yaml.safe_dump(common))
        context = multiprocessing.get_context('spawn')
        telemetry = context.Array('d', [*case['start'], 0., 0., 0., math.inf, 0., 0., 0., 0., 0., 0.])
        fault_value = context.Value('d', 0.)
        fault = FaultWindow(fault_value)
        device_ready, device_halt = context.Event(), context.Event()
        devices = context.Process(target=device_process, args=(case, out, device_file,
            not args.ideal_lidar, result['actual_lidar_beams'], fault_value, telemetry,
            device_ready, device_halt, source_cpu, sensor_cpu), name='ap06-original-devices')
        if source_cpu is not None:
            os.sched_setaffinity(0, graph_cpus)
        devices.start()
        wait(device_ready.is_set, manifest['budgets']['startup_s'], 'independent original device process')
        model = DeviceMirror(model, telemetry)
        bus = model
        rclpy.init(args=['--ros-args', '--params-file', str(device_file)])
        observer = Observer(out)
        lifecycle_clients = {name:observer.create_client(ChangeState,'/'+name+'/change_state')
            for name in ('planner_server','controller_server','bt_navigator',
                         'velocity_smoother','collision_monitor')}
        lifecycle_states = {name:observer.create_client(GetState,'/'+name+'/get_state')
            for name in lifecycle_clients}
        save_client = observer.create_client(Trigger,'/robot_map_manager/save_map')
        spin(observer)
        result['source_initialization_order'] = 'independent_spawned_device_process'
        result['prefixes'] = {p: get_package_prefix(p) for p in (
            'explore', 'mission_manager', 'bt_orchestrator', 'robot_navigation', 'robot_state_estimation',
            'base_hardware', 'robot_map_manager', 'robot_localization', 'slam_toolbox',
            'nav2_bt_navigator', 'nav2_controller', 'nav2_planner', 'nav2_velocity_smoother',
            'nav2_collision_monitor', 'vl53_near_field', 'safety_monitor', 'amadeus_lidar_bringup')}
        start('tf_probe', [str(args.tf_probe)])
        start('scan_normalizer', py('amadeus_lidar_bringup.scan_vereinheitlichen')+[
            '--ros-args', '-p', 'strahlen:='+str(result['actual_lidar_beams'])])
        start('safety', py('safety_monitor.safety_monitor_node')+['--ros-args',
            '--params-file', str(args.repo/'src/safety_monitor/config/safety_monitor_params.yaml')])
        start('shadow', py('robot_state_estimation.hwt601_shadow_node')+['--ros-args',
            '--params-file', str(args.repo/'src/robot_state_estimation/config/hwt601_shadow.yaml'),
            '-p', 'operator_stationary_confirmed:=true'])
        start('ekf', [executable('robot_localization', 'ekf_node'), '--ros-args',
            '-r', '__node:=hwt601_mapping_ekf', '-r', '/odometry/filtered:=/odom', '--params-file', str(native)])
        start('slam', [executable('slam_toolbox', 'sync_slam_toolbox_node'), '--ros-args', '--params-file', str(native)])
        start('maps', py('robot_map_manager.robot_map_manager_node')+['--ros-args', '-p', f'storage_directory:={out}/maps'])
        wait(lambda: observer.map is not None, 30., 'SLAM initial actual map')
        fingerprint = raw_map_portal_source_from_values(**MetricFrontierRuntime._metric_grid_values(observer.map)).fingerprint
        scope = model.local([[-2.8, -1.4], [2.8, -1.4], [2.8, 1.4], [-2.8, 1.4]]).ravel().tolist()
        result['initial_map'] = {'fingerprint': fingerprint, 'width': observer.map.info.width, 'height': observer.map.info.height}
        shared = ['--ros-args', '-p', 'require_hwt601_fusion:=true', '-p', 'hwt601_active_drive:=true',
                  '-p', 'hwt_development_contract:=true', '-p', 'allow_explore_mission:=true', '-p', 'require_localization:=false']
        start('gate', py('robot_navigation.cmd_vel_mission_gate')+shared)
        for package, executable, name, remaps in (
            ('nav2_planner', 'planner_server', 'planner_server', []),
            ('nav2_controller', 'controller_server', 'controller_server', ['-r', 'cmd_vel:=cmd_vel_nav_raw']),
            ('nav2_bt_navigator', 'bt_navigator', 'bt_navigator', []),
            ('nav2_velocity_smoother', 'velocity_smoother', 'velocity_smoother', ['-r', 'cmd_vel:=cmd_vel_nav']),
            ('nav2_collision_monitor', 'collision_monitor', 'collision_monitor', [])):
            start(name, [str(Path(get_package_prefix(package))/'lib'/package/executable),
                         '--ros-args', '--params-file', str(native), *remaps])
        for name in ('planner_server', 'controller_server', 'bt_navigator', 'velocity_smoother', 'collision_monitor'):
            client = lifecycle_clients[name]
            if not client.wait_for_service(timeout_sec=20.):
                raise TimeoutError(name+' lifecycle service')
            state_client = lifecycle_states[name]
            if not state_client.wait_for_service(timeout_sec=20.):
                raise TimeoutError(name+' actual lifecycle state service')
            for state in (1, 3):
                proof = transition_lifecycle(client, state_client, state, 30.)
                result.setdefault('lifecycle_states', {}).setdefault(name, []).append(proof)
        explorer = ['--ros-args', '--params-file', str(args.repo/'src/explore/config/explore_params.yaml'),
            '--params-file', str(args.repo/'src/explore/config/metric_frontier_params.yaml'),
            '--params-file', str(args.repo/'src/explore/config/metric_frontier_simulation_params.yaml'),
            '-p', f'metric_session_id:=ap06-{args.case}', '-p', f'metric_scope_map_fingerprint:={fingerprint}',
            '-p', 'wohnungserkundung_accessible_scope_verified:=true', '-p', 'wohnungserkundung_scope_id:=ap06-two-rooms',
            '-p', 'wohnungserkundung_scope_polygon_xy:='+json.dumps(scope),
            '-p', 'region_graph_shadow_enabled:=false', '-p', 'goal_timeout_s:=150.0',
            '-p', 'overall_timeout_s:=900.0', '-p', 'max_frontier_goals:=20', '-p', 'max_failed_goals:=3',
            '-p', f'behavior_tree:={args.repo}/src/explore/behavior_trees/navigate_to_pose_no_recovery.xml',
            '-p', f'wohnungserkundung_persistence_directory:={out}/checkpoints']+shared[1:]
        explorer_command = py('explore.explore_node')
        if unknown_space_policy == 'sensor_guarded':
            explorer += ['--params-file', str(args.repo/'src/explore/config/metric_sensor_guarded_motion_params.yaml')]
        if execution_mode == 'lab_slots':
            explorer += ['--params-file', str(args.repo/'src/explore/config/metric_lab_slot_params.yaml')]
        if concept_deferred_departure:
            code = ('import sys; '
                f'sys.path.insert(0, {str(args.repo/"tools/simulation")!r}); '
                'from ap06_departure_probe import install_departure_probe; '
                f'install_departure_probe({str(out/"departure_assessments.jsonl")!r}); '
                'from explore.explore_node import main; main()')
            explorer_command = [sys.executable, '-c', code]
        if args.profile_selection or args.capture_decisions:
            # Diagnostic wrapper only; original decisions and deadline stay.
            code = (
                'import cProfile,json,numpy as np,pickle,time; from explore.metric_frontier_runtime import MetricFrontierRuntime as R; '
                'from explore.metric_checkpoint import policy_state; '
                'original=R._metric_select; counter=[0]\n'
                f'profile_enabled={not args.capture_decisions!r}\n'
                'def profiled(self,*a,**kw):\n'
                ' p=cProfile.Profile() if profile_enabled else None; counter[0]+=1\n'
                ' if counter[0]>32: return original(self,*a,**kw)\n'
                ' inputs=a[0]\n'
                ' policy=a[1]\n'
                ' scan=self._door_lidar_scan_snapshot()\n'
                ' attributes={k:getattr(self,k,None) for k in ('
                '"_metric_start_egress_enabled","_metric_egress_expired","_metric_body_anchor_expired",'
                '"_metric_egress_identity","_prealign_handoff_tolerance","_goal_clearance_m",'
                '"_frontier_goal_max_cost","_goal_search_m","_min_goal_dist_m","_approach_dist_m",'
                '"_metric_bounds","_map_timeout_s","_frontier_forward_cone_half_angle",'
                '"_potential_scale","_gain_scale","_heading_scale","_metric_start_strategy",'
                '"_metric_candidate_source","_metric_path_validation","_global_frame",'
                '"_wohnungserkundung_evidence_max_cells","_door_lidar_scan_timeout","_door_lidar_max_range")}\n'
                ' record=dict(kind="Own synthetic diagnostic selection inputs; no live health or mission receipt",'
                'inputs=list(inputs),reference=getattr(inputs,"map_odom_reference",None),'
                'physical_motion=getattr(inputs,"physical_motion",None),'
                'evidence=getattr(self,"_metric_egress",None),scope=self._metric_scope,'
                'policy=None if policy is None else policy_state(policy,time.monotonic()),'
                'scan=scan,mount=self._door_lidar_mount(scan["frame_id"]),'
                'captured_monotonic=time.monotonic(),attributes=attributes)\n'
                f' with open({str(out)!r}+"/selection-object-"+str(counter[0])+".pickle","wb") as f: pickle.dump(record,f)\n'
                f' np.savez_compressed({str(out)!r}+"/selection-input-"+str(counter[0])+".npz",'
                ' raw=np.asarray(inputs[0].data).reshape(inputs[3].shape),known=inputs[3],safe=inputs[4],'
                ' cost=np.asarray(inputs[5].data).reshape(inputs[6].shape),cost_known=inputs[6],pose=inputs[2])\n'
                ' geometry=[{"resolution":g.info.resolution,"origin":[g.info.origin.position.x,g.info.origin.position.y],'
                '"width":g.info.width,"height":g.info.height} for g in (inputs[0],inputs[5])]\n'
                f' open({str(out)!r}+"/selection-geometry.json","w").write(json.dumps(geometry))\n'
                ' try: return p.runcall(original,self,*a,**kw) if p is not None else original(self,*a,**kw)\n'
                ' finally:\n'
                f'  if p is not None: p.dump_stats({str(out)!r}+"/selection-"+str(counter[0])+".prof")\n'
                '  inputs=a[0]\n'
                '  state={"body_anchor_expired":getattr(self,"_metric_body_anchor_expired",None),'
                '"egress_expired":getattr(self,"_metric_egress_expired",None),'
                '"egress":[{"valid":e.valid,"reason":e.reason,"unknown_cells":int(e.unknown.sum())}'
                ' for e in (getattr(self,"_metric_egress",None) or ())],'
                '"first_body_grid":getattr(self,"_metric_body_grid_identity",None),'
                '"first_egress_grid":getattr(self,"_metric_egress_identity",None),'
                '"current_grids":[self._metric_grid_geometry(g) for g in (inputs[0],inputs[5])]}\n'
                f'  open({str(out)!r}+"/selection-state.json","w").write(json.dumps(state,default=str,indent=2))\n'
                'R._metric_select=profiled\n'
                'departure=R._metric_departure_plan_ready; departure_count=[0]\n'
                'def recorded_departure(self,inputs,route,target,stopped):\n'
                ' departure_count[0]+=1; index=departure_count[0]\n'
                ' if index>16: return departure(self,inputs,route,target,stopped)\n'
                ' record=dict(kind="Own synthetic diagnostic bound native departure inputs; no health or acceptance",'
                'inputs=list(inputs),reference=getattr(inputs,"map_odom_reference",None),'
                'physical_motion=getattr(inputs,"physical_motion",None),route=route,target=target,'
                'scope=self._metric_scope,body_bounds=self._metric_bounds,'
                'controller_contract=dict(self._metric_status.get("controller_geometry_contract",{})),'
                'ranking=dict(self._metric_status.get("ranking",{})))\n'
                f' with open({str(out)!r}+"/departure-input-"+str(index)+".pickle","wb") as f: pickle.dump(record,f)\n'
                ' result=departure(self,inputs,route,target,stopped)\n'
                ' state=dict(result=result,rejection=self._metric_status.get("departure_plan_rejection"),'
                'native_sight=self._metric_status.get("native_stop_observation"))\n'
                f' open({str(out)!r}+"/departure-result-"+str(index)+".json","w").write(json.dumps(state,default=str,indent=2))\n'
                ' return result\n'
                'R._metric_departure_plan_ready=recorded_departure\n'
                'from explore.explore_node import main; main()')
            explorer_command = [sys.executable, '-c', code]
        if args.capture_geometry:
            # Passive diagnostic snapshots; never a manifest acceptance run.
            code = (
                'import json,numpy as np; from explore.metric_frontier_runtime import MetricFrontierRuntime as R; '
                'original=R._metric_prepare_egress; seen=set()\n'
                'def captured(self,inputs):\n'
                ' result=original(self,inputs)\n'
                ' evidence=getattr(self,"_metric_egress",None) or ()\n'
                ' reasons=tuple(e.reason for e in evidence if not e.valid)\n'
                ' key=reasons or ("initial",)\n'
                ' if key not in seen and len(seen)<16:\n'
                '  seen.add(key); name="geometry-"+str(len(seen))\n'
                '  arrays=dict(raw=np.asarray(inputs[0].data).reshape(inputs[3].shape),known=inputs[3],safe=inputs[4],'
                'cost=np.asarray(inputs[5].data).reshape(inputs[6].shape),cost_known=inputs[6],pose=inputs[2])\n'
                '  for i,e in enumerate(evidence):\n'
                '   arrays["original_"+str(i)]=np.asarray(e.fixed.grid.data).reshape(e.fixed.unknown.shape)\n'
                '   arrays["retained_"+str(i)]=e.fixed.unknown;arrays["projected_"+str(i)]=e.unknown\n'
                f'  np.savez_compressed({str(out)!r}+"/"+name+".npz",**arrays)\n'
                '  geometry=lambda g:dict(resolution=g.info.resolution,origin=[g.info.origin.position.x,g.info.origin.position.y],'
                'shape=[g.info.height,g.info.width])\n'
                '  state=dict(reasons=reasons,reference=getattr(inputs,"map_odom_reference",None),'
                'current=[geometry(inputs[i]) for i in (0,5)],'
                'initial=[geometry(e.fixed.grid) for e in evidence],'
                'commits=[getattr(e.fixed,"last_commit_pose",None) for e in evidence],'
                'details=[getattr(e.fixed,"last_monotone_failure",None) for e in evidence])\n'
                f'  open({str(out)!r}+"/"+name+".json","w").write(json.dumps(state,indent=2))\n'
                ' return result\n'
                'R._metric_prepare_egress=captured\nfrom explore.explore_node import main; main()')
            explorer_command = [sys.executable, '-c', code]
        start('explorer', explorer_command+explorer)
        start('bt', [str(Path(get_package_prefix('bt_orchestrator'))/'lib/bt_orchestrator/bt_orchestrator'), '--ros-args',
            '--params-file', str(args.repo/'src/bt_orchestrator/config/bt_params.yaml'),
            '-p', f'explore_xml:={args.repo}/src/bt_orchestrator/bt_xml/explore.xml'])
        start('manager', py('mission_manager.mission_manager_node')+['--ros-args',
            '--params-file', str(args.repo/'src/mission_manager/config/mission_catalog.yaml'), '-p', 'enable_real_explore:=true'])
        wait(lambda: observer.metric().get('scope_bound') is True and observer.fusion and
            observer.fusion[-1].get('sources_ready') is True, manifest['budgets']['startup_s'], 'real scope and HWT readiness')
        result['tf_owners'] = observer.owners()
        wait(lambda: observer.command.get_subscription_count() > 0, 10., 'mission command subscriber')
        initial_cells = np.array(observer.map.data)
        observer.command.publish(String(data='{"type":"explore"}'))
        begun = time.monotonic(); injected = False; injection_at = None
        next_progress = begun
        until = begun+manifest['budgets']['mission_s']+15.
        while time.monotonic() < until:
            if time.monotonic() >= next_progress:
                progress = dict(at=time.monotonic(), metric=observer.metric(),
                    manager=observer.manager[-1] if observer.manager else {},
                    travel_m=model.travel, rear_cleared=model.rear_cleared)
                temporary = out/'progress.tmp.json'
                temporary.write_text(json.dumps(progress)+'\n')
                temporary.replace(out/'progress.json')
                next_progress = time.monotonic()+5.
            if model.collision:
                raise RuntimeError('independent padded chassis collision')
            if stop.is_set() or not devices.is_alive():
                raise RuntimeError('executor or source process stopped')
            failed = [(name, proc.poll()) for name, proc in processes if proc.poll() is not None]
            if failed:
                raise RuntimeError('runtime process failure '+str(failed))
            if (case.get('inject') and model.travel > .02 and abs(model.velocity[0]) > .005
                    and not injected):
                injected = True
                injection_at = time.monotonic()
                result['injection_at_s'] = injection_at-begun
                if case['inject'] == 'cancel_after_first_motion':
                    observer.command.publish(String(data='{"type":"cancel"}'))
                else:
                    # A real >300-ms raw-source gap, rather than a still-fresh
                    # 120-ms poll fault that cannot exercise this HOLD contract.
                    fault['until'] = injection_at+.45
                    result['injected_gyro_gap_s'] = .45
            status = observer.metric()
            if status.get('state') in ('success', 'failed', 'blocked', 'canceled'):
                break
            time.sleep(.1)
        wait(lambda: observer.manager and observer.manager[-1].get('state') in
             ('success', 'failed', 'canceled'), 5., 'Mission Manager actual terminal result')
        terminal_at = time.monotonic()
        wait(lambda: max(abs(model.velocity)) < .005, manifest['budgets']['stop_s'], 'actual plant standstill')
        wait(lambda: not any(observer.action_active.values()), manifest['budgets']['cancel_s'],
             'actual action children terminal')
        result['action_maximum_active'] = observer.action_maximum
        result['action_active_at_terminal'] = observer.action_active
        result['command_values_at_terminal'] = observer.command_values
        if args.save_partial:
            client = save_client
            if not client.wait_for_service(timeout_sec=5.):
                raise TimeoutError('actual Map Manager save service')
            future = client.call_async(Trigger.Request())
            wait(future.done, 10., 'actual SLAM map save')
            response = future.result()
            result['map_save'] = {'success': response.success, 'message': response.message}
            if not response.success:
                raise RuntimeError('actual map save rejected: '+response.message)
            # A saved raw map is distinct from a bound Explorer checkpoint.
            wait(lambda: observer.metric().get('persistence', {}).get('state') in ('saved', 'unavailable'),
                 5., 'Explorer exact saved-map checkpoint result')
            result['checkpoint_after_save'] = observer.metric().get('persistence')
        grid = observer.map
        # Passive original messages for offline diagnosis. These are the last
        # independently received samples, not a simultaneous failure snapshot
        # and never an input to the product or an observation receipt.
        for label, message in (('raw_map', grid), ('costmap', observer.costmap),
                               ('scan', observer.last_scan)):
            if message is not None:
                (out/('final_'+label+'.cdr')).write_bytes(serialize_message(message))
        actual_map = np.array(grid.data).reshape(grid.info.height, grid.info.width)
        np.save(out/'final_slam_map.npy', actual_map)
        (out/'final_slam_map_geometry.json').write_text(json.dumps({
            'resolution': grid.info.resolution, 'origin': [grid.info.origin.position.x, grid.info.origin.position.y],
            'frame': grid.header.frame_id}))
        if observer.costmap is not None:
            cost = observer.costmap
            np.save(out/'final_global_costmap.npy',
                    np.array(cost.data).reshape(cost.info.height, cost.info.width))
            (out/'final_global_costmap_geometry.json').write_text(json.dumps({
                'resolution': cost.info.resolution,
                'origin': [cost.info.origin.position.x, cost.info.origin.position.y],
                'frame': cost.header.frame_id}))
        oracle = model.map_oracle(actual_map, grid.info.resolution,
                                 (grid.info.origin.position.x, grid.info.origin.position.y))
        owners = observer.owners()
        plant_samples = [json.loads(line) for line in (out/'plant.jsonl').read_text().splitlines()]
        result.update(metric=observer.metric(), manager=observer.manager[-1], map_oracle=oracle, tf_owners=owners,
                      travel_m=model.travel, minimum_padded_clearance_m=model.minimum_clearance,
                      rear_cleared=model.rear_cleared, plant_tick_gaps=[b[0]-a[0] for a,b in zip(plant_samples,plant_samples[1:]) if b[0]-a[0] > .03],
                      map_growth=bool(len(observer.map.data) != len(initial_cells) or
                          not np.array_equal(np.array(observer.map.data), initial_cells)), simulated_register_writes=bus.writes)
        if case.get('inject'):
            def standstill_after(at):
                return next((row[0]-at for row in plant_samples
                             if row[0] >= at and max(abs(row[4]), abs(row[5])) < .005), None)
            stopped_after = standstill_after(injection_at) if injected else None
            result['injection_to_terminal_s'] = terminal_at-injection_at if injected else None
            result['injection_to_standstill_s'] = stopped_after
            result['passed'] = bool(injected and observer.metric().get('state') != 'success'
                                    and max(abs(model.velocity)) < .005
                                    and observer.manager[-1].get('state') == 'canceled'
                                    and terminal_at-injection_at <= manifest['budgets']['cancel_s']
                                    and stopped_after is not None and stopped_after <= manifest['budgets']['stop_s']
                                    and case['inject'] == 'cancel_after_first_motion')
            if case['inject'] == 'gyro_gap_after_first_motion':
                held_at = next((at for at, s in observer.fusion_at if injected and at >= injection_at
                                and s.get('recovery_state') == 'HOLD'), None)
                hold_stop = standstill_after(held_at) if held_at is not None else None
                result['hold_to_standstill_s'] = hold_stop
                result['hold_resume_qualified'] = False  # this case checks HOLD/stop only
                result['passed'] = bool(held_at is not None and hold_stop is not None
                    and hold_stop <= manifest['budgets']['stop_s']
                    and observer.metric().get('state') != 'success' and max(abs(model.velocity)) < .005)
        else:
            result['passed'] = bool(observer.metric().get('state') == 'success' and model.rear_cleared
                and observer.manager[-1].get('state') == 'success'
                and result['map_growth'] and observer.metric().get('arrivals', 0) >= 3
                and observer.metric().get('observations', 0) >= 3
                and observer.action_maximum.get('/navigate_to_pose/_action/status', 0) == 1
                and len(observer.command_values) == 4
                and owners.get('map->odom') == ['slam_toolbox']
                and owners.get('odom->base_link') == ['hwt601_mapping_ekf']
                and oracle['reference_observed_fraction'] >= manifest['acceptance']['min_reference_observed_fraction']
                and oracle['maximum_occupied_wall_error_m'] is not None
                and oracle['maximum_occupied_wall_error_m'] <= manifest['acceptance']['max_map_truth_error_m'])
        result['passed'] = bool(result['passed']
            and observer.action_maximum.get('/navigate_to_pose/_action/status', 0) <= 1
            and not any(observer.action_active.values())
            and all(abs(v) < 1e-9 for values in observer.command_values.values() for v in values))
        if not result['passed']:
            raise RuntimeError('AP06 acceptance not met: '+str(observer.metric().get('reason', observer.metric().get('state'))))
    except Exception as exc:
        result['error'] = str(exc)
        traceback.print_exc()
    finally:
        if rclpy.ok() and 'observer' in locals():
            observer.command.publish(String(data='{"type":"cancel"}'))
            time.sleep(.5)
        # Signal each direct process once; never signal process groups.
        for name, proc in reversed(processes):
            if proc.poll() is None:
                proc.send_signal(signal.SIGINT)
                try:
                    proc.wait(timeout=4.)
                except subprocess.TimeoutExpired:
                    proc.terminate()
                    try:
                        proc.wait(timeout=2.)
                    except subprocess.TimeoutExpired:
                        proc.kill(); proc.wait()
        stop.set()
        for thread in threads:
            thread.join(2.)
        for ex in executors:
            ex.shutdown(timeout_sec=1.)
        for node in reversed(nodes):
            node.destroy_node()
        if 'observer' in locals():
            observer.events.close()
        if 'devices' in locals():
            device_halt.set()
            devices.join(5.)
            if devices.is_alive():
                devices.terminate(); devices.join(2.)
                if devices.is_alive():
                    devices.kill(); devices.join()
            result['device_process_exitcode'] = devices.exitcode
        if rclpy.ok():
            rclpy.shutdown()
        for stream in streams:
            stream.close()
        os.sched_setaffinity(0, original_affinity)
        (out/'result.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    print(json.dumps({k: result[k] for k in ('case', 'passed', 'error', 'travel_m', 'map_oracle') if k in result}, allow_nan=False), flush=True)
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--case', required=True)
    parser.add_argument('--unknown-space-policy', choices=('observed_only', 'sensor_guarded'),
                        default='observed_only', help='product motion policy; same worlds/sensors/acceptance')
    parser.add_argument('--execution-mode', choices=('continuous', 'lab_slots'), default='continuous',
                        help='existing continuous workflow or explicitly qualified LAB slots')
    parser.add_argument('--tf-probe', type=Path, required=True)
    parser.add_argument('--manifest', type=Path,
                        default=Path(__file__).with_name('ap06_product_scenarios.json'))
    parser.add_argument('--capture-geometry',action='store_true',help='diagnostic actual proof snapshots; no manifest acceptance')
    parser.add_argument('--profile-selection', action='store_true', help='diagnostic overhead; not a qualification run')
    parser.add_argument('--capture-decisions', action='store_true', help='bounded input snapshots without call profiling; not a qualification run')
    parser.add_argument('--ideal-lidar', action='store_true', help='separate ideal sensor diagnostic, not native-mask qualification')
    parser.add_argument('--concept-defer-departure', action='store_true',
                        help='simulation-only logged future-departure ablation; requires --ideal-lidar, never qualification')
    parser.add_argument('--diagnostic-beams', type=int, choices=(720, 2160),
                        help='explicit density diagnostic; never qualifies the declared manifest')
    parser.add_argument('--save-partial', action='store_true', help='save actual synthetic SLAM map after terminal result')
    sys.exit(run(parser.parse_args()))
