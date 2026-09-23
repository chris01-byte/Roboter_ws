#!/usr/bin/env python3
"""Device-free Stage-3 checks with real Nav2, gate and collision monitor.

The only moving base is an in-process differential-drive model. No hardware
or sensor driver is launched. The fixed private DDS domain is mandatory.
``fixed_bypass`` and ``explorer_bypass`` keep the obstacle in place throughout.
``stopped_bypass`` separately probes late detection and remains a failing
acceptance case until safe release from the stop is demonstrated. ``no_exit``
requires a controlled partial result; ``blocked`` checks fail-closed recovery
when the other sensor provides an ambiguous empty original cloud.
"""

import argparse
from contextlib import nullcontext
import json
import math
import os
from pathlib import Path
import signal
import struct
import subprocess
import tempfile
import threading
import time

import numpy as np

os.environ['ROS_DOMAIN_ID'] = '219'
os.environ['WE_SMOKE_DOMAIN_ID'] = '219'

import rclpy  # noqa: E402
from action_msgs.msg import GoalStatusArray  # noqa: E402
from geometry_msgs.msg import (  # noqa: E402
    PolygonStamped, PoseStamped, TransformStamped, Twist,
)
from lifecycle_msgs.srv import GetState  # noqa: E402
from nav2_msgs.action import ComputePathToPose, NavigateToPose  # noqa: E402
from nav_msgs.msg import Odometry, OccupancyGrid, Path as NavPath  # noqa: E402
from rclpy.action import ActionClient  # noqa: E402
from rclpy.executors import MultiThreadedExecutor  # noqa: E402
from sensor_msgs.msg import LaserScan, PointCloud2, PointField  # noqa: E402
from std_msgs.msg import Bool, String  # noqa: E402
from tf2_ros import TransformBroadcaster  # noqa: E402

from wohnungserkundung_process_smoke import (  # noqa: E402
    SyntheticWorld, _box_ranges, _map_message, _map_status,
    _start_explorer, _stop_explorer,
)


OBSTACLE = (2.00, 2.30, 1.325, 1.725)
FIXED_TARGET = (3.30, 1.525)
PADDED_FOOTPRINT = ((0.33, 0.25), (0.33, -0.25),
                    (-0.13, -0.25), (-0.13, 0.25))


def _ray_box_hit(x, y, angle, bounds):
    x0, x1, y0, y1 = bounds
    dx, dy = math.cos(angle), math.sin(angle)
    hits = []
    for edge in (x0, x1):
        distance = (edge - x) / dx if abs(dx) > 1e-10 else -1
        if distance > 0 and y0 <= y + distance * dy <= y1:
            hits.append(distance)
    for edge in (y0, y1):
        distance = (edge - y) / dy if abs(dy) > 1e-10 else -1
        if distance > 0 and x0 <= x + distance * dx <= x1:
            hits.append(distance)
    return min(hits, default=math.inf)


def _footprint_safe(x, y, yaw, obstacle=OBSTACLE):
    """Independent ground truth: polygon/rectangle SAT, not a Nav2 verdict."""
    c, s = math.cos(yaw), math.sin(yaw)
    polygon = [(x + c * px - s * py, y + s * px + c * py)
               for px, py in PADDED_FOOTPRINT]
    if not all(0.15 < px < 4.85 and 0.25 < py < 2.75
               for px, py in polygon):
        return False
    if obstacle is None:
        return True
    x0, x1, y0, y1 = obstacle
    box = ((x0, y0), (x1, y0), (x1, y1), (x0, y1))
    for ax, ay in ((1.0, 0.0), (0.0, 1.0), (c, s), (-s, c)):
        a = [px * ax + py * ay for px, py in polygon]
        b = [px * ax + py * ay for px, py in box]
        if max(a) < min(b) or max(b) < min(a):
            return True
    return False


def _cloud(stamp, points, frame='base_link'):
    message = PointCloud2()
    message.header.stamp = stamp
    message.header.frame_id = frame
    message.height = 1
    message.width = len(points)
    message.fields = [
        PointField(name=name, offset=index * 4,
                   datatype=PointField.FLOAT32, count=1)
        for index, name in enumerate(('x', 'y', 'z'))]
    message.is_bigendian = False
    message.point_step = 12
    message.row_step = 12 * len(points)
    message.is_dense = True
    message.data = b''.join(struct.pack('<fff', *point) for point in points)
    return message


class RealNavWorld(SyntheticWorld):
    def __init__(self, obstacle_mode):
        self.real_nav = True
        super().__init__('local_blocked', fake_nav=False)
        self.obstacle_mode = obstacle_mode
        self.diagnostic_bypass = obstacle_mode in (
            'fixed_bypass', 'explorer_bypass', 'stopped_bypass', 'no_exit')
        self.x = 0.0
        self.y = 0.0
        self.yaw = 0.0
        self.last_tick = time.monotonic()
        self.last_cmd_at = 0.0
        self.cmd = Twist()
        self.goal_a = None
        self.obstacle_center = None
        self.obstacle_active = False
        self.mission_active = False
        self.revision = 0
        self.observed_maps = 0
        self.freeze_map = False
        self.map_update_once = False
        self.map_last_at = 0.0
        self.nav_active_max = 0
        self.nav_statuses = []
        self.last_nav_status_list = []
        self.nav_succeeded = False
        self.nav_success_ids = set()
        self.raw_nonzero = 0
        self.output_nonzero = 0
        self.stopped_while_raw = 0
        self.travel_m = 0.0
        self.stop_pose = None
        self.trace = []
        self.plans = []
        self.collision_arcs = []
        self.chain = {name: Twist() for name in ('raw', 'gate', 'smooth')}
        self.geometry_violation = None
        self.planned_geometry_violation = None
        self.reverse_travel_m = 0.0
        self.runtime_footprint = None
        self.obstacle_in_map = self.diagnostic_bypass
        self.obstacle_bounds = (OBSTACLE if obstacle_mode != 'no_exit'
                                else (2.0, 2.3, 0.25, 2.75))
        self.plan_at = 0.0
        self._plan_client = ActionClient(
            self, ComputePathToPose, '/compute_path_to_pose')
        self._nav_map_pub = self.create_publisher(
            OccupancyGrid, '/map', self._qos)
        self._scan_nav_pub = self.create_publisher(
            LaserScan, '/scan_normiert', 10)
        self._mission_pub = self.create_publisher(
            String, '/mission_manager/status_json', 10)
        self._real_estop_pub = self.create_publisher(
            Bool, '/we_stage3/estop', 10)
        self._real_odom_pub = self.create_publisher(
            Odometry, '/odom', 10)
        self._real_vl53 = {
            side: (
                self.create_publisher(
                    PointCloud2, f'/near_field/{side}/points', 10),
                self.create_publisher(
                    PointCloud2, f'/near_field/{side}/points_costmap', 10))
            for side in ('left', 'right')}
        self._real_tf = TransformBroadcaster(self)
        self._nav_client = ActionClient(self, NavigateToPose,
                                        '/navigate_to_pose')
        self.create_subscription(Twist, '/cmd_vel', self._on_real_cmd, 10)
        self.create_subscription(Twist, '/cmd_vel_nav_raw',
                                 self._on_raw_cmd, 10)
        for name, topic in (('raw', '/cmd_vel_nav_raw'),
                            ('gate', '/cmd_vel_nav'),
                            ('smooth', '/cmd_vel_smoothed')):
            self.create_subscription(
                Twist, topic,
                lambda msg, key=name: self.chain.__setitem__(key, msg), 10)
        self.create_subscription(NavPath, '/plan', self._on_plan, 10)
        self.create_subscription(
            NavPath, '/lookahead_collision_arc', self._on_collision_arc, 10)
        self.create_subscription(
            PolygonStamped, '/local_costmap/published_footprint',
            lambda msg: setattr(self, 'runtime_footprint', msg), 10)
        self.create_subscription(
            GoalStatusArray, '/navigate_to_pose/_action/status',
            self._on_nav_status, 10)
        self.create_timer(0.1, self._tick_real)

    def _on_plan(self, message):
        if message.poses:
            self.plan_at = time.monotonic()
            points = [(p.pose.position.x, p.pose.position.y)
                      for p in message.poses]
            self.plans.append(points)
            if self.diagnostic_bypass and self.obstacle_in_map:
                for first, second in zip(points, points[1:]):
                    yaw = math.atan2(second[1] - first[1],
                                     second[0] - first[0])
                    steps = max(1, math.ceil(math.dist(first, second) / 0.01))
                    for fraction in np.linspace(0, 1, steps + 1):
                        x = first[0] + fraction * (second[0] - first[0])
                        y = first[1] + fraction * (second[1] - first[1])
                        if not _footprint_safe(
                                x, y, yaw, self.obstacle_bounds):
                            self.planned_geometry_violation = (x, y, yaw)

    def _on_collision_arc(self, message):
        if message.poses:
            self.collision_arcs.append({
                't': time.monotonic(), 'frame': message.header.frame_id,
                'poses': [[p.pose.position.x, p.pose.position.y,
                           2.0 * math.atan2(p.pose.orientation.z,
                                            p.pose.orientation.w)]
                          for p in message.poses]})

    def _diagnostic_map(self, stamp):
        message = OccupancyGrid()
        message.header.frame_id = 'map'
        message.header.stamp = stamp
        message.info.width, message.info.height = 100, 60
        message.info.resolution = 0.05
        message.info.origin.orientation.w = 1.0
        cells = np.full((60, 100), 100, dtype=np.int8)
        cells[5:55, 3:97] = 0
        if self.obstacle_mode == 'fixed_bypass':
            cells[26:34, 75:83] = -1
        else:
            # Two disjoint information windows exist from the beginning.
            # Only observation of the first pocket changes after its goal.
            if self.frontier_stage != 'second_only':
                cells[26:34, 58:64] = -1
            cells[26:34, 84:90] = -1
        if self.obstacle_in_map:
            cells[26:35, 40:46] = 100
            if self.obstacle_mode == 'no_exit':
                cells[5:55, 40:46] = 100
        # New observation, stable geometry: no fake changing wall pixels.
        message.data = cells.ravel().tolist()
        return message

    def _diagnostic_sensors(self, stamp, px, py):
        """Eight horizontal rays in the real mounts; original may be empty.

        No-hit is deliberately not a measurement-health certificate. This
        fixture supplies visibility, not the missing real sensor validity API.
        """
        for side, lateral in (('left', 0.095), ('right', -0.095)):
            sx = px + 0.290 * math.cos(self.yaw) - lateral * math.sin(self.yaw)
            sy = py + 0.290 * math.sin(self.yaw) + lateral * math.cos(self.yaw)
            points, costmap = [], []
            for angle in np.linspace(-math.pi / 6, math.pi / 6, 8):
                distance = _ray_box_hit(
                    sx, sy, self.yaw + angle, (0.15, 4.85, 0.25, 2.75))
                if self.obstacle_active:
                    distance = min(distance, _ray_box_hit(
                        sx, sy, self.yaw + angle, self.obstacle_bounds))
                if 0.01 <= distance <= 0.50:
                    point = (distance * math.cos(angle),
                             distance * math.sin(angle), 0.0)
                    points.append(point)
                    costmap.append(point)
                else:
                    costmap.append((0.6 * math.cos(angle),
                                    0.6 * math.sin(angle), 0.0))
            original_pub, costmap_pub = self._real_vl53[side]
            frame = f'vl53_{side}_link'
            original_pub.publish(_cloud(stamp, points, frame))
            costmap_pub.publish(_cloud(stamp, costmap, frame))

    @property
    def map_pose(self):
        return (0.85 + self.x, 1.525 + self.y)

    def _publish_passive_telemetry(self):
        # The parent test timer is replaced by _tick_real below.
        return

    def _on_real_cmd(self, message):
        self.cmd = message
        self.last_cmd_at = time.monotonic()
        if abs(message.linear.x) > 0.001 or abs(message.angular.z) > 0.001:
            self.output_nonzero += 1

    def _on_raw_cmd(self, message):
        if abs(message.linear.x) > 0.001 or abs(message.angular.z) > 0.001:
            self.raw_nonzero += 1
            if (self.obstacle_active and
                    abs(self.cmd.linear.x) < 0.001 and
                    abs(self.cmd.angular.z) < 0.001):
                self.stopped_while_raw += 1
                if self.stop_pose is None:
                    self.stop_pose = self.map_pose

    def _on_nav_status(self, message):
        self.last_nav_status_list = message.status_list
        active = sum(entry.status in (1, 2, 3)
                     for entry in message.status_list)
        self.nav_active_max = max(self.nav_active_max, active)
        self.nav_statuses = [entry.status for entry in message.status_list]
        if 4 in self.nav_statuses:
            self.nav_succeeded = True
        self.nav_success_ids.update(
            bytes(entry.goal_info.goal_id.uuid)
            for entry in message.status_list if entry.status == 4)

    def _tick_real(self):
        now = time.monotonic()
        dt = min(0.12, max(0.0, now - self.last_tick))
        self.last_tick = now
        cmd = self.cmd if now - self.last_cmd_at <= 0.25 else Twist()
        previous_pose = (*self.map_pose, self.yaw)
        linear = max(-0.12, min(0.12, float(cmd.linear.x)))
        angular = max(-0.25, min(0.25, float(cmd.angular.z)))
        self.yaw += angular * dt
        delta = linear * dt
        self.x += delta * math.cos(self.yaw)
        self.y += delta * math.sin(self.yaw)
        self.travel_m += abs(delta)
        self.reverse_travel_m += max(0.0, -delta)
        if self.diagnostic_bypass:
            px, py = self.map_pose
            for fraction in np.linspace(0.0, 1.0, 5):
                sample = tuple(first + fraction * (last - first)
                               for first, last in zip(
                                   previous_pose, (px, py, self.yaw)))
                if not _footprint_safe(
                        *sample, self.obstacle_bounds if self.obstacle_active
                        else None):
                    self.geometry_violation = sample
            self.trace.append({
                't': now, 'x': px, 'y': py, 'yaw': self.yaw,
                'output': [linear, angular],
                **{name: [msg.linear.x, msg.angular.z]
                   for name, msg in self.chain.items()}})

        stamp = self.get_clock().now().to_msg()
        transform = TransformStamped()
        transform.header.stamp = stamp
        transform.header.frame_id = 'odom'
        transform.child_frame_id = 'base_link'
        transform.transform.translation.x = self.x
        transform.transform.translation.y = self.y
        transform.transform.rotation.z = math.sin(self.yaw / 2.0)
        transform.transform.rotation.w = math.cos(self.yaw / 2.0)
        self._real_tf.sendTransform(transform)

        odom = Odometry()
        odom.header.stamp = stamp
        odom.header.frame_id = 'odom'
        odom.child_frame_id = 'base_link'
        odom.pose.pose.position.x = self.x
        odom.pose.pose.position.y = self.y
        odom.pose.pose.orientation.z = transform.transform.rotation.z
        odom.pose.pose.orientation.w = transform.transform.rotation.w
        odom.twist.twist.linear.x = linear
        odom.twist.twist.angular.z = angular
        self._real_odom_pub.publish(odom)
        self._real_estop_pub.publish(Bool(data=False))
        self._mission_pub.publish(String(data=json.dumps({
            'state': 'running' if self.mission_active else 'idle',
            'phase': 'Explore' if self.mission_active else 'idle',
            'active_command': ({'type': 'explore'}
                               if self.mission_active else None),
        })))

        px, py = self.map_pose
        scan = LaserScan()
        scan.header.stamp = stamp
        scan.header.frame_id = 'base_link'
        scan.angle_min = -math.pi
        scan.angle_increment = 2.0 * math.pi / 720.0
        scan.angle_max = scan.angle_min + 719 * scan.angle_increment
        scan.range_min = 0.05
        scan.range_max = 8.0
        if self.diagnostic_bypass:
            scan.ranges = [min(
                _ray_box_hit(px, py, self.yaw + angle,
                             (0.15, 4.85, 0.25, 2.75)),
                _ray_box_hit(px, py, self.yaw + angle, self.obstacle_bounds)
                if self.obstacle_active else math.inf)
                for angle in -math.pi + np.arange(720) * scan.angle_increment]
        else:
            scan.ranges = _box_ranges(
                px, py, yaw_rad=self.yaw).astype(float).tolist()
        self._scan_pub.publish(scan)
        self._scan_nav_pub.publish(scan)

        clear = _cloud(stamp, [])
        # Match the real VL53 costmap stream: one range-clearing point for
        # each horizontal column, not one central ray that leaves ghost cells.
        clear_costmap = _cloud(stamp, [
            (0.6, col * 0.025, 0.2) for col in range(-12, 13)])
        left_points = []
        if self.obstacle_active and self.obstacle_center is not None:
            gx, gy = self.obstacle_center
            for dx in (-0.10, 0.0, 0.10):
                for dy in (-0.10, 0.0, 0.10):
                    mx = gx + dx - px
                    my = gy + dy - py
                    bx = mx * math.cos(self.yaw) + my * math.sin(self.yaw)
                    by = -mx * math.sin(self.yaw) + my * math.cos(self.yaw)
                    if 0.03 < math.hypot(bx, by) <= 0.50:
                        left_points.append((bx, by, 0.2))
        if left_points:
            left = _cloud(stamp, left_points)
            left_costmap = left
        else:
            left = clear
            left_costmap = clear_costmap
        if self.diagnostic_bypass:
            self._diagnostic_sensors(stamp, px, py)
        else:
            for side, (original, costmap) in self._real_vl53.items():
                original.publish(left if side == 'left' else clear)
                costmap.publish(
                    left_costmap if side == 'left' else clear_costmap)

        if now - self.map_last_at >= 1.0:
            self.observed_maps += 1
            if self.diagnostic_bypass:
                message = self._diagnostic_map(stamp)
                duplicate = (self.last_map_message is not None
                             and message.data == self.last_map_message.data)
                if not duplicate:
                    self.revision += 1
            elif (not self.freeze_map or self.map_update_once
                    or self.last_map_message is None):
                self.revision += 1
                duplicate = False
                self.map_update_once = False
            else:
                duplicate = True
            if not self.diagnostic_bypass:
                message = _map_message(self, self.revision)
                if duplicate:
                    message.data = list(self.last_map_message.data)
            self.last_map_message = message
            self._map_pub.publish(message)
            self._nav_map_pub.publish(message)
            self._map_status_pub.publish(String(data=json.dumps(
                _map_status(message, self.revision,
                            observed_maps=self.observed_maps,
                            duplicate_maps=self.observed_maps -
                            self.revision))))
            self.map_last_at = now


def _stop_launch(process):
    if process.poll() is None:
        process.send_signal(signal.SIGINT)
        try:
            process.wait(timeout=12.0)
        except subprocess.TimeoutExpired:
            process.terminate()
            process.wait(timeout=5.0)


def _target(world, xy):
    target = PoseStamped()
    target.header.frame_id = 'map'
    target.header.stamp = world.get_clock().now().to_msg()
    target.pose.position.x, target.pose.position.y = xy
    target.pose.orientation.w = 1.0
    return target


def _run_diagnostic(world):
    """Fixed, reviewable comparison; retain failure evidence outside Git."""
    directory = Path(tempfile.mkdtemp(prefix='we-stage3-bypass-'))
    print(f'EVIDENCE_DIRECTORY={directory}', flush=True)
    nav_log = (directory / 'nav2.log').open('w', encoding='utf-8')
    process = subprocess.Popen(
        ['ros2', 'launch', str(Path(__file__).with_name(
            'wohnungserkundung_nav2_stage3.launch.py'))],
        stdout=nav_log, stderr=subprocess.STDOUT, env=os.environ.copy())
    explorer = None
    handle = None
    result = None
    outcome = {'mode': world.obstacle_mode, 'fixed_target': FIXED_TARGET,
               'obstacle': world.obstacle_bounds, 'obstacle_removed': False}
    world.obstacle_active = world.obstacle_mode != 'stopped_bypass'
    world.obstacle_in_map = world.obstacle_active
    try:
        for name in ('planner_server', 'controller_server', 'bt_navigator',
                     'velocity_smoother', 'collision_monitor'):
            client = world.create_client(GetState, f'/{name}/get_state')
            world.wait_for(lambda: client.wait_for_service(timeout_sec=0.1),
                           25.0, f'{name} Lifecycle erreichbar')
            deadline = time.monotonic() + 25.0
            while time.monotonic() < deadline:
                state = client.call_async(GetState.Request())
                world.wait_for(state.done, 3.0, f'{name} Lifecycle-Antwort')
                if state.result().current_state.id == 3:
                    break
                time.sleep(0.2)
            else:
                outcome['failure_layer'] = f'fixture_lifecycle:{name}'
                raise AssertionError(f'{name} nicht aktiv')
            world.destroy_client(client)
        world.wait_for(lambda: world.runtime_footprint is not None,
                       5.0, 'tatsaechlich gepaddeter Footprint')
        footprint = world.runtime_footprint
        actual = sorted((point.x, point.y)
                        for point in footprint.polygon.points)
        if (footprint.header.frame_id != 'odom'
                or len(actual) != 4
                or any(math.dist(first, second) > 1e-6 for first, second
                       in zip(actual, sorted(PADDED_FOOTPRINT)))):
            outcome['failure_layer'] = 'fixture_footprint_mismatch'
            raise AssertionError(
                'Pruefkontur entspricht nicht dem Live-Footprint')
        outcome['runtime_padded_footprint'] = actual
        world.wait_for(lambda: world._plan_client.wait_for_server(
            timeout_sec=0.1), 25.0, 'NavFn bereit')
        target_xy = FIXED_TARGET
        if world.obstacle_mode not in ('fixed_bypass', 'no_exit'):
            explorer, explorer_log, params = _start_explorer(
                world, directory / 'explorer.log')
            candidate = world.wait_for_frontier_candidate(timeout=30.0)
            first_task = candidate['task_id']
            outcome['automatic_target'] = candidate['target']
            target_xy = (candidate['target']['x_m'],
                         candidate['target']['y_m'])
        goal = ComputePathToPose.Goal()
        goal.goal = _target(world, target_xy)
        goal.planner_id = 'GridBased'
        sent = world._plan_client.send_goal_async(goal)
        world.wait_for(sent.done, 5.0, 'Planannahme')
        plan_result = sent.result().get_result_async()
        world.wait_for(plan_result.done, 8.0, 'initialer NavFn-Pfad')
        path = plan_result.result().result.path
        outcome['planner_status'] = plan_result.result().status
        outcome['plan_points'] = len(path.poses)
        if world.obstacle_mode == 'no_exit':
            if plan_result.result().status != 6 or path.poses:
                raise AssertionError(
                    'Planer muss unloesbare Barriere ablehnen')
            explorer, explorer_log, params = _start_explorer(
                world, directory / 'explorer.log')
            world.wait_for(lambda: world._explore_client.wait_for_server(
                timeout_sec=0.1), 15.0, 'Explorer bereit')
            world.wait_for(lambda: world.latest_shadow is not None,
                           10.0, 'Quellenbewertung bereit')
            world.mission_active = True
            handle, result = world.send_explore_goal(timeout_s=10.0)
            world.wait_for(result.done, 18.0, 'kontrollierter Teilabschluss')
            if world.travel_m > 0.001 or world.nav_active_max > 0:
                raise AssertionError('Bewegung trotz unloesbarer Barriere')
            if 'Teilstand' not in result.result().result.message:
                raise AssertionError('Kein erklaerter Teilabschluss')
            outcome.update(passed=True, controlled_standstill=True,
                           travel_m=world.travel_m,
                           nav_active_max=world.nav_active_max,
                           parent_status=result.result().status,
                           parent_message=result.result().result.message)
            return
        if plan_result.result().status != 4 or len(path.poses) < 2:
            outcome['failure_layer'] = 'planner_no_path'
            raise AssertionError('Kein zulaessiger NavFn-Pfad')
        points = [(p.pose.position.x, p.pose.position.y) for p in path.poses]
        outcome['planned_lateral_excursion_m'] = max(
            abs(y - 1.525) for _, y in points)
        unsafe = []
        for first, second in zip(points, points[1:]):
            yaw = math.atan2(second[1] - first[1], second[0] - first[0])
            steps = max(1, math.ceil(math.dist(first, second) / 0.01))
            for fraction in np.linspace(0, 1, steps + 1):
                x = first[0] + fraction * (second[0] - first[0])
                y = first[1] + fraction * (second[1] - first[1])
                if not _footprint_safe(x, y, yaw,
                                       world.obstacle_bounds
                                       if world.obstacle_active else None):
                    unsafe.append((x, y, yaw))
        outcome['planned_footprint_violations'] = len(unsafe)
        if unsafe:
            outcome['failure_layer'] = 'planner_polygon_clearance'
            outcome['first_unsafe_plan_pose'] = unsafe[0]
            raise AssertionError('Plan hat keinen sicheren Polygon-Sweep')

        if world.obstacle_mode == 'fixed_bypass':
            goal = NavigateToPose.Goal()
            goal.pose = _target(world, FIXED_TARGET)
            goal.behavior_tree = str(Path(__file__).resolve().parents[2] /
                                     'src/explore/behavior_trees/'
                                     'navigate_to_pose_no_recovery.xml')
            world.mission_active = True
            world.wait_for(lambda: world._nav_client.wait_for_server(
                timeout_sec=0.1), 10.0, 'Nav2 bereit')
            sent = world._nav_client.send_goal_async(goal)
            world.wait_for(sent.done, 5.0, 'festes Diagnoseziel angenommen')
            handle = sent.result()
            if not handle.accepted:
                raise AssertionError('Nav2 lehnt Diagnoseziel ab')
            result = handle.get_result_async()
        else:
            world.mission_active = True
            handle, result = world.send_explore_goal(timeout_s=170.0)

        started = time.monotonic()
        stopped_at = None
        stopped_pose = None
        obstacle_at = None
        while time.monotonic() - started < 120.0:
            if (world.geometry_violation or world.travel_m > 6.0
                    or world.reverse_travel_m > 0.001):
                raise AssertionError('Geometrie-/Fahrwegbudget verletzt')
            if world.obstacle_mode == 'fixed_bypass' and result.done():
                outcome['nav_status'] = result.result().status
                if outcome['nav_status'] != 4:
                    raise AssertionError('Nav2 beendet Umfahrung ohne Erfolg')
                break
            if world.obstacle_mode != 'fixed_bypass' and world.nav_succeeded:
                break
            if world.obstacle_mode == 'stopped_bypass':
                if not world.obstacle_active and world.map_pose[0] >= 1.20:
                    world.obstacle_active = True
                    obstacle_at = time.monotonic()
                nav_log.flush()
                log = (directory / 'nav2.log').read_text(errors='replace')
                if obstacle_at and 'detected collision ahead' in log:
                    world.obstacle_in_map = True
                    if stopped_at is None:
                        stopped_at = time.monotonic()
                        stopped_pose = world.map_pose
                if result.done():
                    outcome['parent_message'] = result.result().result.message
                    raise AssertionError('Mission nach Hindernisstopp beendet')
            time.sleep(0.1)
        else:
            raise AssertionError('Umfahrt erreicht Zeitbudget')
        if world.obstacle_mode != 'fixed_bypass':
            if world.obstacle_mode == 'stopped_bypass':
                if stopped_at is None:
                    raise AssertionError('Kein notwendiger Stopp gemessen')
                outcome.update(controller_stop_detected=True,
                               stopped_pose=stopped_pose,
                               resumed_after_stop=True)
            world.frontier_stage = 'second_only'
            world.map_update_once = True
            world.wait_for(lambda: any(
                item.get('task_id') == first_task
                and item.get('state') == 'completed'
                for item in (world.latest_shadow or {}).get('tasks', [])),
                15.0, 'Rohkartenfortschritt nach Umfahrung')
            world.wait_for(lambda: len({
                tuple(entry.goal_info.goal_id.uuid)
                for entry in world.last_nav_status_list}) >= 2,
                15.0, 'Explorer startet Folgeauftrag')
            travel_at_first_success = world.travel_m
            world.wait_for(
                lambda: (len(world.nav_success_ids) >= 2
                         or world.geometry_violation is not None),
                60.0, 'Folgeziel erfolgreich verarbeitet')
            if (world.geometry_violation or world.travel_m > 6.0
                    or world.reverse_travel_m > 0.001
                    or world.travel_m - travel_at_first_success < 0.15):
                raise AssertionError('Keine sichere Bewegung zum Folgeziel')
            if result.done():
                raise AssertionError('Elternmission vor Folgearbeit beendet')
            outcome.update(automatic_frontier_completed=True,
                           same_parent_continues=True,
                           next_goal_succeeded=True,
                           next_goal_travel_m=(
                               world.travel_m - travel_at_first_success))
        outcome.update(
            passed=True, nav_active_max=world.nav_active_max,
            travel_m=world.travel_m,
            actual_lateral_excursion_m=max(
                abs(point['y'] - 1.525) for point in world.trace),
            final_pose=(*world.map_pose, world.yaw))
        if world.planned_geometry_violation:
            outcome['first_unsafe_plan_pose'] = (
                world.planned_geometry_violation)
            raise AssertionError('Nav2-Folgepfad verletzt Footprint-Geometrie')
        outcome['all_planned_footprints_safe'] = True
        outcome['reverse_travel_m'] = world.reverse_travel_m
        if world.nav_active_max > 1:
            raise AssertionError('Konkurrierende Nav2-Ziele')
    except Exception:
        outcome['passed'] = False
        nav_log.flush()
        log = (directory / 'nav2.log').read_text(errors='replace')
        outcome.setdefault('failure_layer', (
            'controller_collision' if 'detected collision' in log
            else 'controller_or_downstream'))
        outcome['controller_collision_count'] = log.count('detected collision')
        outcome['final_pose'] = (*world.map_pose, world.yaw)
        outcome['last_commands'] = world.trace[-1] if world.trace else None
        outcome['last_explore'] = world.latest_explore
        outcome['last_shadow'] = world.latest_shadow
        print(log[-4500:], flush=True)
        raise
    finally:
        world.mission_active = False
        if handle is not None and result is not None and not result.done():
            canceled = handle.cancel_goal_async()
            world.wait_for(canceled.done, 5.0, 'Testabbruch')
            world.wait_for(result.done, 8.0, 'terminaler Testabbruch')
        if explorer is not None:
            _stop_explorer(explorer, explorer_log, params)
        _stop_launch(process)
        nav_log.close()
        (directory / 'trace.json').write_text(json.dumps(world.trace))
        (directory / 'plans.json').write_text(json.dumps(world.plans))
        (directory / 'collision_arcs.json').write_text(
            json.dumps(world.collision_arcs))
        (directory / 'result.json').write_text(json.dumps(outcome, indent=2))
        print(json.dumps({key: value for key, value in outcome.items()
                          if key not in ('last_explore', 'last_shadow')},
                         sort_keys=True), flush=True)


def _run_case(world):
    launch_path = Path(__file__).with_name(
        'wohnungserkundung_nav2_stage3.launch.py')
    with nullcontext(tempfile.mkdtemp(prefix='we-stage3-nav2-')) as directory:
        directory = Path(directory)
        print(f'EVIDENCE_DIRECTORY={directory}', flush=True)
        nav_log = (directory / 'nav2.log').open('w', encoding='utf-8')
        nav_process = subprocess.Popen(
            ['ros2', 'launch', str(launch_path)],
            stdout=nav_log, stderr=subprocess.STDOUT, env=os.environ.copy())
        explorer_process = None
        try:
            world.wait_for(
                lambda: world._nav_client.wait_for_server(timeout_sec=0.1),
                25.0, 'echter Nav2-Navigator')
            explorer_process, explorer_log, explorer_params = _start_explorer(
                world, directory / 'explorer.log')
            world.wait_for_frontier_candidate(timeout=20.0)
            first = world.wait_for_frontier_candidate()
            first_task = first['task_id']
            world.freeze_map = True
            world.goal_a = (
                float(first['target']['x_m']),
                float(first['target']['y_m']))
            world.obstacle_center = (
                world.goal_a if world.obstacle_mode in ('disappear', 'blocked')
                else (1.65, 1.55))
            world.mission_active = True
            handle, parent_result = world.send_explore_goal(timeout_s=170.0)
            world.wait_for(
                lambda: world.raw_nonzero > 5, 30.0,
                'echte Nav2-Kommandos fuer Ziel A')
            world.wait_for(
                lambda: math.dist(
                    world.map_pose, world.obstacle_center) < 0.55,
                65.0, 'virtuelle Annaeherung an Hindernis')
            world.obstacle_active = True

            def collision_seen():
                nav_log.flush()
                return 'detected collision ahead' in (
                    directory / 'nav2.log').read_text(
                        encoding='utf-8', errors='replace')

            world.wait_for(collision_seen, 4.0,
                           'echter Controller-Hindernisstopp')
            stop_start = world.map_pose
            time.sleep(0.65)
            stop_end = world.map_pose
            if math.dist(stop_start, stop_end) > 0.025:
                raise AssertionError(
                    'Hindernis bewirkte keinen belegten sicheren Stopp')
            if world.obstacle_mode == 'legacy_probe':
                gx, gy = world.obstacle_center
                bounds = (gx - 0.1, gx + 0.1, gy - 0.1, gy + 0.1)
                evidence = {
                    'mode': 'legacy_probe', 'goal_a': world.goal_a,
                    'obstacle': bounds,
                    'goal_footprint_safe': _footprint_safe(
                        *world.goal_a, first['target']['yaw_rad'], bounds),
                    'controller_collision_detected': True,
                    'stopped_pose': world.map_pose,
                    'blocked_pose_change_m': math.dist(stop_start, stop_end),
                    'plan_count': len(world.plans),
                    'last_plan': world.plans[-1] if world.plans else [],
                }
                (directory / 'legacy_result.json').write_text(
                    json.dumps(evidence, indent=2))
                print(json.dumps({key: value for key, value in evidence.items()
                                  if key != 'last_plan'}), flush=True)
                canceled = handle.cancel_goal_async()
                world.wait_for(canceled.done, 5.0, 'Diagnoseabbruch')
                world.wait_for(parent_result.done, 8.0, 'Diagnoseende')
                return
            travel_before_clear = world.travel_m
            if world.obstacle_mode == 'blocked':
                world.wait_for(parent_result.done, 12.0,
                               'Fail-closed bei unklarer Messgueltigkeit')
                nav_log.flush()
                dispatched = (directory / 'nav2.log').read_text(
                    encoding='utf-8', errors='replace').count(
                        'Begin navigating from current location')
                if (world.nav_active_max > 1
                        or world.travel_m - travel_before_clear > 0.025
                        or dispatched != 1
                        or parent_result.result().status != 6):
                    raise AssertionError(
                        'Unklare Sensorik darf keine Recovery erlauben')
                print(json.dumps({
                    'obstacle_mode': 'blocked',
                    'nav_active_max': world.nav_active_max,
                    'nav_goal_count': dispatched,
                    'right_sensor': 'fresh_empty_measurement_unknown',
                    'parent_status': parent_result.result().status,
                    'no_unsafe_recovery': True,
                    'movement_after_stop_m': (
                        world.travel_m - travel_before_clear),
                }, sort_keys=True))
                return
            if world.obstacle_mode == 'disappear':
                world.obstacle_active = False
            world.wait_for(
                lambda: world.nav_succeeded,
                35.0 if world.obstacle_mode == 'disappear' else 65.0,
                'Ziel A nach Hindernis sicher erreicht')
            nav_log.flush()
            first_goal_count = (directory / 'nav2.log').read_text(
                encoding='utf-8', errors='replace').count(
                    'Begin navigating from current location')
            if first_goal_count != 1:
                raise AssertionError(
                    'Ziel A wurde vor Erfolg unnoetig ersetzt')
            world.frontier_stage = 'second_only'
            world.map_update_once = True
            world.wait_for(
                lambda: world.travel_m > travel_before_clear + 0.25, 25.0,
                'sichere virtuelle Bewegung nach freiem Pfad')
            world.wait_for(
                lambda: any(
                    entry.get('task_id') == first_task
                    and entry.get('state') == 'completed'
                    for entry in (world.latest_shadow or {}).get('tasks', [])),
                12.0, 'A durch neue Rohkarte als erkundet belegt')
            world.wait_for(
                lambda: (world.latest_explore or {}).get(
                    'wohnungserkundung', {}).get('goal_candidate', {}).get(
                        'task_id') not in (None, first_task),
                12.0, 'neue Aufgabe B nach Erkundungsfortschritt')
            second_task = world.latest_explore["wohnungserkundung"][
                "goal_candidate"]["task_id"]

            def second_nav_started():
                nav_log.flush()
                return (directory / 'nav2.log').read_text(
                    encoding='utf-8', errors='replace').count(
                        'Begin navigating from current location') >= 2

            world.wait_for(second_nav_started, 15.0,
                           'naechstes Frontierziel automatisch gestartet')
            if world.nav_active_max > 1 or parent_result.done():
                raise AssertionError('Kindzielkonkurrenz oder Missionsabbruch')
            result = {
                'obstacle_mode': world.obstacle_mode,
                'nav_active_max': world.nav_active_max,
                'raw_nonzero': world.raw_nonzero,
                'output_nonzero': world.output_nonzero,
                'stopped_while_raw': world.stopped_while_raw,
                'blocked_pose_change_m': round(
                    math.dist(stop_start, stop_end), 4),
                'controller_collision_detected': True,
                'goal_a_succeeded_after_clear': world.nav_succeeded,
                'goal_a_task_completed': True,
                'next_nav_goal_started': True,
                'next_task_distinct': second_task != first_task,
                'travel_m': round(world.travel_m, 3),
                'travel_after_clear_m': round(
                    world.travel_m - travel_before_clear, 3),
                'stop_pose': world.stop_pose,
                'parent_continued': not parent_result.done(),
            }
            canceled = handle.cancel_goal_async()
            world.wait_for(canceled.done, 5.0, 'Testmissionsende')
            world.wait_for(parent_result.done, 8.0, 'Testmissionsresultat')
            print(json.dumps(result, sort_keys=True))
        except Exception:
            nav_log.flush()
            print('NAV2 LOG TAIL:', (directory / 'nav2.log').read_text(
                encoding='utf-8', errors='replace')[-7000:])
            if explorer_process is not None:
                explorer_log.flush()
                print('EXPLORER LOG TAIL:', (
                    directory / 'explorer.log').read_text(
                        encoding='utf-8', errors='replace')[-7000:])
            raise
        finally:
            world.mission_active = False
            if explorer_process is not None:
                _stop_explorer(
                    explorer_process, explorer_log, explorer_params)
            _stop_launch(nav_process)
            nav_log.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=(
        'disappear', 'bypass', 'blocked', 'legacy_probe',
        'fixed_bypass', 'explorer_bypass',
        'stopped_bypass', 'no_exit'),
                        default='disappear')
    args = parser.parse_args()
    rclpy.init()
    executor = MultiThreadedExecutor(num_threads=8)
    world = RealNavWorld(args.mode)
    executor.add_node(world)
    spin_thread = threading.Thread(target=executor.spin, daemon=True)
    spin_thread.start()
    try:
        if world.diagnostic_bypass:
            _run_diagnostic(world)
        else:
            _run_case(world)
    finally:
        # Drain callbacks before destroying their publishers/action clients.
        # Destroying the node while spin is active races pending callbacks.
        executor.shutdown(timeout_sec=3.0)
        spin_thread.join(timeout=3.0)
        executor.remove_node(world)
        world.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
