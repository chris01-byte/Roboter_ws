#!/usr/bin/env python3
"""Device-free Stage-3 checks with real Nav2, gate and collision monitor.

The only moving base is an in-process differential-drive model. No hardware
or sensor driver is launched. The fixed private DDS domain is mandatory.
``disappear`` and ``blocked`` are passing checks; ``bypass`` is a deliberate
open acceptance probe and exits nonzero while no safe detour is demonstrated.
"""

import argparse
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

os.environ['ROS_DOMAIN_ID'] = '219'
os.environ['WE_SMOKE_DOMAIN_ID'] = '219'

import rclpy  # noqa: E402
from action_msgs.msg import GoalStatusArray  # noqa: E402
from geometry_msgs.msg import TransformStamped, Twist  # noqa: E402
from nav2_msgs.action import NavigateToPose  # noqa: E402
from nav_msgs.msg import Odometry, OccupancyGrid  # noqa: E402
from rclpy.action import ActionClient  # noqa: E402
from rclpy.executors import MultiThreadedExecutor  # noqa: E402
from sensor_msgs.msg import LaserScan, PointCloud2, PointField  # noqa: E402
from std_msgs.msg import Bool, String  # noqa: E402
from tf2_ros import TransformBroadcaster  # noqa: E402

from wohnungserkundung_process_smoke import (  # noqa: E402
    SyntheticWorld, _box_ranges, _map_message, _map_status,
    _start_explorer, _stop_explorer,
)


def _cloud(stamp, points):
    message = PointCloud2()
    message.header.stamp = stamp
    message.header.frame_id = 'base_link'
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
        self.nav_succeeded = False
        self.raw_nonzero = 0
        self.output_nonzero = 0
        self.stopped_while_raw = 0
        self.travel_m = 0.0
        self.stop_pose = None
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
        self.create_subscription(
            GoalStatusArray, '/navigate_to_pose/_action/status',
            self._on_nav_status, 10)
        self.create_timer(0.1, self._tick_real)

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
        active = sum(entry.status in (1, 2, 3)
                     for entry in message.status_list)
        self.nav_active_max = max(self.nav_active_max, active)
        self.nav_statuses = [entry.status for entry in message.status_list]
        if 4 in self.nav_statuses:
            self.nav_succeeded = True

    def _tick_real(self):
        now = time.monotonic()
        dt = min(0.12, max(0.0, now - self.last_tick))
        self.last_tick = now
        cmd = self.cmd if now - self.last_cmd_at <= 0.25 else Twist()
        linear = max(-0.12, min(0.12, float(cmd.linear.x)))
        angular = max(-0.25, min(0.25, float(cmd.angular.z)))
        self.yaw += angular * dt
        delta = linear * dt
        self.x += delta * math.cos(self.yaw)
        self.y += delta * math.sin(self.yaw)
        self.travel_m += abs(delta)

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
        scan.ranges = _box_ranges(
            px, py, yaw_rad=self.yaw).astype(float).tolist()
        self._scan_pub.publish(scan)
        self._scan_nav_pub.publish(scan)

        clear = _cloud(stamp, [(0.0, 0.0, 0.0)])
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
        for side, (original, costmap) in self._real_vl53.items():
            original.publish(left if side == 'left' else clear)
            costmap.publish(left_costmap if side == 'left' else clear_costmap)

        if now - self.map_last_at >= 1.0:
            self.observed_maps += 1
            if (not self.freeze_map or self.map_update_once
                    or self.last_map_message is None):
                self.revision += 1
                duplicate = False
                self.map_update_once = False
            else:
                duplicate = True
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


def _run_case(world):
    launch_path = Path(__file__).with_name(
        'wohnungserkundung_nav2_stage3.launch.py')
    with tempfile.TemporaryDirectory(prefix='we-stage3-nav2-') as directory:
        directory = Path(directory)
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
            travel_before_clear = world.travel_m
            if world.obstacle_mode == 'blocked':
                def nav_failures():
                    nav_log.flush()
                    return (directory / 'nav2.log').read_text(
                        encoding='utf-8', errors='replace').count(
                            'Goal failed')

                world.wait_for(lambda: nav_failures() >= 1, 12.0,
                               'Nav2-Abbruch am dauerhaft blockierten A')
                world.wait_for(
                    lambda: (world.latest_explore or {}).get('phase')
                    == 'we_local_blocked_waiting_alternative',
                    8.0, 'A als lokale Blockade zurueckgestellt')
                world.wait_for(
                    lambda: (directory / 'nav2.log').read_text(
                        encoding='utf-8', errors='replace').count(
                            'Begin navigating from current location') >= 2,
                    12.0, 'Alternative B automatisch gestartet')
                world.wait_for(lambda: nav_failures() >= 2, 15.0,
                               'zweites Ziel bei weiter bestehender Blockade')
                time.sleep(0.6)
                if (parent_result.done() or world.nav_active_max > 1
                        or world.travel_m - travel_before_clear > 0.025):
                    raise AssertionError(
                        'Blockade beendete Mission, konkurrierte oder '
                        'fuhr weiter')
                print(json.dumps({
                    'obstacle_mode': 'blocked',
                    'nav_active_max': world.nav_active_max,
                    'nav_failures': nav_failures(),
                    'parent_done_after_second_failure': parent_result.done(),
                    'latest_phase': (world.latest_explore or {}).get('phase'),
                    'travel_m': round(world.travel_m, 3),
                }, sort_keys=True))
                if not parent_result.done():
                    canceled = handle.cancel_goal_async()
                    world.wait_for(canceled.done, 5.0, 'Diagnosemissionsende')
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
    parser.add_argument('--mode', choices=('disappear', 'bypass', 'blocked'),
                        default='disappear')
    args = parser.parse_args()
    rclpy.init()
    executor = MultiThreadedExecutor(num_threads=8)
    world = RealNavWorld(args.mode)
    executor.add_node(world)
    spin_thread = threading.Thread(target=executor.spin, daemon=True)
    spin_thread.start()
    try:
        _run_case(world)
    finally:
        executor.remove_node(world)
        world.destroy_node()
        executor.shutdown(timeout_sec=3.0)
        if rclpy.ok():
            rclpy.shutdown()
        spin_thread.join(timeout=3.0)


if __name__ == '__main__':
    main()
