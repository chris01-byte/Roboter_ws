#!/usr/bin/env python3
"""Isolated, device-free process smoke for the WE-M3 portal runtime.

The script starts the real ``ExploreNode`` in a child process and supplies
only synthetic ROS data on scenario-specific topics.  It never publishes a
velocity command, opens a device, or starts a robot launch profile.
"""

import argparse
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import threading
import time

import numpy as np


os.environ.setdefault("ROS_DOMAIN_ID", "195")

import rclpy  # noqa: E402
from geometry_msgs.msg import TransformStamped, Twist  # noqa: E402
from nav2_msgs.action import NavigateToPose  # noqa: E402
from nav_msgs.msg import OccupancyGrid  # noqa: E402
from rclpy.action import (  # noqa: E402
    ActionClient,
    ActionServer,
    CancelResponse,
    GoalResponse,
)
from rclpy.callback_groups import ReentrantCallbackGroup  # noqa: E402
from rclpy.executors import MultiThreadedExecutor  # noqa: E402
from rclpy.node import Node  # noqa: E402
from rclpy.qos import (  # noqa: E402
    DurabilityPolicy,
    HistoryPolicy,
    QoSProfile,
    ReliabilityPolicy,
)
from sensor_msgs.msg import LaserScan  # noqa: E402
from std_msgs.msg import String  # noqa: E402
from tf2_ros import TransformBroadcaster  # noqa: E402

from amadeus_map_identity import (  # noqa: E402
    compact_occupancy_cells,
    map_snapshot_fingerprint,
)
from robot_interfaces.action import ExploreArea  # noqa: E402


WIDTH = 100
MULTIROOM_WIDTH = 155
HEIGHT = 60
RESOLUTION = 0.05
ORIGIN = (0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0)


def _map_cells(revision, *, width=WIDTH, height=HEIGHT,
               multiroom=False, frontier_stage="none",
               frontier_replan=False, blocked_goal_xy=None):
    """Return one device-free map, optionally with staged hall work."""
    occupancy = np.full((height, width), 100, dtype=np.int8)
    if frontier_replan:
        occupancy[5:55, 3:97] = 0
        if frontier_stage in {"both", "first_only"}:
            occupancy[26:34, 38:46] = -1
        if frontier_stage in {"both", "second_only"}:
            occupancy[26:34, 73:81] = -1
        if blocked_goal_xy is not None:
            cell_x = int(float(blocked_goal_xy[0]) / RESOLUTION)
            cell_y = int(float(blocked_goal_xy[1]) / RESOLUTION)
            occupancy[max(0, cell_y - 4):min(height, cell_y + 5),
                      max(0, cell_x - 4):min(width, cell_x + 5)] = 100
    elif multiroom:
        occupancy[5:55, 3:48] = 0
        occupancy[20:40, 52:100] = 0
        occupancy[5:55, 104:149] = 0
        occupancy[27:33, 48:52] = 0
        occupancy[27:33, 100:104] = 0
        if frontier_stage == "visible":
            occupancy[20:27, 76:84] = -1
        elif frontier_stage == "hidden":
            occupancy[20:27, 76:84] = 100
    else:
        occupancy[5:55, 3:48] = 0
        occupancy[5:55, 52:97] = 0
        occupancy[27:33, 48:52] = 0
    occupancy[0, revision % width] = 99
    return occupancy.ravel().tolist()


def _fingerprint(cells, *, width=WIDTH, height=HEIGHT,
                 resolution=RESOLUTION):
    return map_snapshot_fingerprint(
        width=width,
        height=height,
        resolution=float(resolution),
        frame_id="map",
        origin=ORIGIN,
        compact_cells=compact_occupancy_cells(
            cells=cells, cell_count=width * height),
    )


def _map_message(node, revision):
    message = OccupancyGrid()
    message.header.frame_id = "map"
    message.header.stamp = node.get_clock().now().to_msg()
    message.info.width = node.map_width
    message.info.height = node.map_height
    message.info.resolution = RESOLUTION
    message.info.origin.orientation.w = 1.0
    message.data = _map_cells(
        revision,
        width=node.map_width,
        height=node.map_height,
        multiroom=node.multiroom,
        frontier_stage=node.frontier_stage,
        frontier_replan=node.frontier_replan,
        blocked_goal_xy=node.blocked_goal_xy,
    )
    return message


def _map_status(message, revision, *, event="status", saved=None,
                observed_maps=None, duplicate_maps=0):
    stamp_ns = (
        int(message.header.stamp.sec) * 1_000_000_000
        + int(message.header.stamp.nanosec)
    )
    wire_resolution = float(np.float32(message.info.resolution))
    payload = {
        "schema_version": 1,
        "event": event,
        "ok": True,
        "message": "Synthetischer WE-M3/U-Kartenstatus.",
        "time": time.time(),
        "map": {
            "available": True,
            "snapshot_available": True,
            "publisher_count": 1,
            "age_seconds": 0.05,
            "source": "synthetic",
            "summary": {
                "width": message.info.width,
                "height": message.info.height,
                "resolution": wire_resolution,
                "frame_id": "map",
                "origin": {"position": [0.0, 0.0]},
                "source_stamp_ns": stamp_ns,
                "fingerprint": _fingerprint(
                    message.data,
                    width=message.info.width,
                    height=message.info.height,
                    resolution=wire_resolution),
            },
        },
        "pose": {"available": False},
        "storage": {"root": "/not-used", "last_saved": saved},
        "counters": {
            "accepted_maps": revision,
            "observed_maps": revision if observed_maps is None else observed_maps,
            "duplicate_maps": duplicate_maps,
        },
    }
    if event == "save_result":
        payload.update({"command": "save", "saved": saved})
    return payload


def _box_ranges(x_m, y_m, *, yaw_rad=0.0, count=720):
    """Return base-frame rays to a fixed asymmetric rectangular contour."""
    angles = -math.pi + np.arange(count, dtype=np.float64) * (
        2.0 * math.pi / count)
    world_angles = angles + float(yaw_rad)
    dx = np.cos(world_angles)
    dy = np.sin(world_angles)
    candidates = np.full((4, count), np.inf, dtype=np.float64)
    with np.errstate(divide="ignore", invalid="ignore"):
        for index, wall_x in enumerate((-1.0, 9.0)):
            scale = (wall_x - x_m) / dx
            hit_y = y_m + scale * dy
            candidates[index] = np.where(
                (scale > 0.0) & (hit_y >= -1.0) & (hit_y <= 4.0),
                scale,
                np.inf,
            )
        for index, wall_y in enumerate((-1.0, 4.0), start=2):
            scale = (wall_y - y_m) / dy
            hit_x = x_m + scale * dx
            candidates[index] = np.where(
                (scale > 0.0) & (hit_x >= -1.0) & (hit_x <= 6.0),
                scale,
                np.inf,
            )
    return np.min(candidates, axis=0)


class SyntheticWorld(Node):
    def __init__(self, scenario, persistence_directory=None):
        super().__init__(f"we_m3u_world_{scenario}")
        self.scenario = scenario
        self.multiroom = scenario == "multiroom"
        self.frontier_replan = scenario in {
            "frontier_replan", "frontier_no_source"}
        self.map_width = MULTIROOM_WIDTH if self.multiroom else WIDTH
        self.map_height = HEIGHT
        self.frontier_stage = "both" if self.frontier_replan else "none"
        self.blocked_goal_xy = None
        prefix = f"/we_m3u/{scenario}"
        self.map_topic = f"{prefix}/map"
        self.costmap_topic = f"{prefix}/costmap"
        self.map_status_topic = f"{prefix}/map_status"
        self.shadow_status_topic = f"{prefix}/shadow_status"
        self.explore_status_topic = f"{prefix}/explore_status"
        self.scan_topic = f"{prefix}/scan"
        self.scan_command_topic = f"{prefix}/scan_command"
        self.door_command_topic = f"{prefix}/door_command"
        self.nav_action = f"{prefix}/navigate_to_pose"
        self.latest_shadow = None
        self.latest_explore = None
        self.command_count = 0
        self.nav_goal_count = 0
        self.nav_cancel_count = 0
        self.nav_active_count = 0
        self.nav_max_active_count = 0
        self.nav_targets = []
        self.nav_terminal = []
        self._nav_lock = threading.Lock()
        self.nav_goal_received = threading.Event()
        self.nav_release = threading.Event()
        self.persistence_directory = persistence_directory
        self.last_saved = None
        self.last_map_message = None
        self._qos = QoSProfile(
            history=HistoryPolicy.KEEP_LAST,
            depth=1,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
            reliability=ReliabilityPolicy.RELIABLE,
        )
        self._map_pub = self.create_publisher(
            OccupancyGrid, self.map_topic, self._qos)
        self._costmap_pub = self.create_publisher(
            OccupancyGrid, self.costmap_topic, self._qos)
        self._map_status_pub = self.create_publisher(
            String, self.map_status_topic, self._qos)
        self._scan_pub = self.create_publisher(LaserScan, self.scan_topic, 10)
        self._tf = TransformBroadcaster(self)
        self.create_subscription(
            String, self.shadow_status_topic, self._on_shadow, self._qos)
        self.create_subscription(
            String, self.explore_status_topic, self._on_explore, self._qos)
        self.create_subscription(
            Twist, self.scan_command_topic, self._on_command, 10)
        self.create_subscription(
            Twist, self.door_command_topic, self._on_command, 10)
        self._nav_server = ActionServer(
            self,
            NavigateToPose,
            self.nav_action,
            execute_callback=self._execute_nav,
            goal_callback=self._accept_nav,
            cancel_callback=self._cancel_nav,
            callback_group=ReentrantCallbackGroup(),
        )
        self._explore_client = ActionClient(
            self,
            ExploreArea,
            "/explore_area",
            callback_group=ReentrantCallbackGroup(),
        )

    def _on_shadow(self, message):
        try:
            self.latest_shadow = json.loads(message.data)
        except json.JSONDecodeError:
            self.latest_shadow = {"invalid": True}

    def _on_explore(self, message):
        try:
            self.latest_explore = json.loads(message.data)
        except json.JSONDecodeError:
            self.latest_explore = {"invalid": True}

    def _on_command(self, _message):
        self.command_count += 1

    def _accept_nav(self, request):
        with self._nav_lock:
            self.nav_goal_count += 1
            self.nav_targets.append((
                float(request.pose.pose.position.x),
                float(request.pose.pose.position.y)))
        self.nav_goal_received.set()
        return GoalResponse.ACCEPT

    def _cancel_nav(self, _goal_handle):
        self.nav_cancel_count += 1
        return CancelResponse.ACCEPT

    def _execute_nav(self, goal_handle):
        with self._nav_lock:
            self.nav_active_count += 1
            self.nav_max_active_count = max(
                self.nav_max_active_count, self.nav_active_count)
        try:
            deadline = time.monotonic() + 12.0
            while time.monotonic() < deadline:
                if goal_handle.is_cancel_requested:
                    goal_handle.canceled()
                    self.nav_terminal.append("canceled")
                    return NavigateToPose.Result()
                if self.nav_release.wait(0.02):
                    goal_handle.succeed()
                    self.nav_terminal.append("succeeded")
                    return NavigateToPose.Result()
            goal_handle.abort()
            self.nav_terminal.append("aborted")
            return NavigateToPose.Result()
        finally:
            with self._nav_lock:
                self.nav_active_count -= 1

    def publish_revision(self, revision):
        message = _map_message(self, revision)
        self.last_map_message = message
        status = String(data=json.dumps(_map_status(
            message, revision, saved=self.last_saved)))
        self._map_pub.publish(message)
        self._costmap_pub.publish(message)
        # Exercise both arrival orders and allow the child executor to retain
        # the exact raw sample before the idempotent status replay.
        time.sleep(0.10)
        self._map_status_pub.publish(status)
        time.sleep(0.10)
        self._map_status_pub.publish(status)

    def publish_identical_map_with_new_stamp(self, revision):
        """Publish unchanged occupancy with a new source stamp and status."""
        if self.last_map_message is None:
            raise RuntimeError("Identische Karte braucht eine Ausgangskarte")
        message = _map_message(self, revision)
        message.data = list(self.last_map_message.data)
        self.last_map_message = message
        self._map_pub.publish(message)
        self._costmap_pub.publish(message)
        time.sleep(0.10)
        status = String(data=json.dumps(_map_status(
            message, revision - 1, saved=self.last_saved,
            observed_maps=revision, duplicate_maps=1)))
        self._map_status_pub.publish(status)
        time.sleep(0.10)
        self._map_status_pub.publish(status)

    def publish_save_result(self, revision):
        message = self.last_map_message
        if message is None:
            raise RuntimeError("Speichern braucht eine zuvor publizierte Karte")
        wire_resolution = float(np.float32(message.info.resolution))
        self.last_saved = {
            "name": "wohnung", "version": "20260915T120000Z-we-resume",
            "path": "/synthetic/maps/wohnung/we-resume",
            "saved_at": "2026-09-15T12:00:00Z",
            "width": message.info.width, "height": message.info.height,
            "resolution": wire_resolution, "frame_id": "map",
            "fingerprint": _fingerprint(
                message.data,
                width=message.info.width,
                height=message.info.height,
                resolution=wire_resolution),
            "durability_warning": None,
        }
        self._map_pub.publish(message)
        self._costmap_pub.publish(message)
        time.sleep(0.10)
        self._map_status_pub.publish(String(data=json.dumps(_map_status(
            message, revision, event="save_result", saved=self.last_saved))))

    def publish_pose_scan(
            self, x_m, *, y_m=1.525, yaw_rad=0.0,
            publish_transform=True):
        stamp = self.get_clock().now().to_msg()
        if publish_transform:
            transform = TransformStamped()
            transform.header.frame_id = "map"
            transform.child_frame_id = "base_link"
            transform.header.stamp = stamp
            transform.transform.translation.x = float(x_m)
            transform.transform.translation.y = float(y_m)
            transform.transform.rotation.z = math.sin(float(yaw_rad) / 2.0)
            transform.transform.rotation.w = math.cos(float(yaw_rad) / 2.0)
            self._tf.sendTransform(transform)
            time.sleep(0.025)
        scan = LaserScan()
        scan.header.frame_id = "base_link"
        scan.header.stamp = stamp
        scan.angle_min = -math.pi
        scan.angle_increment = 2.0 * math.pi / 720.0
        scan.angle_max = scan.angle_min + 719 * scan.angle_increment
        scan.range_min = 0.05
        scan.range_max = 8.0
        scan.ranges = _box_ranges(
            float(x_m), float(y_m), yaw_rad=yaw_rad).astype(float).tolist()
        self._scan_pub.publish(scan)

    def wait_for(self, predicate, timeout, description):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if predicate():
                return
            time.sleep(0.05)
        raise RuntimeError(f"Zeitlimit: {description}")

    def wait_for_candidate(self, timeout=12.0):
        def ready():
            extension = (self.latest_explore or {}).get(
                "wohnungserkundung", {})
            candidate = extension.get("goal_candidate", {})
            return (
                candidate.get("state") == "current"
                and candidate.get("kind") == "portal"
                and "dispatch_blocked_reason" not in candidate
            )

        self.wait_for(ready, timeout, "Portalzielkandidat")
        return self.latest_explore["wohnungserkundung"]["goal_candidate"]

    def wait_for_frontier_candidate(self, timeout=12.0):
        def ready():
            extension = (self.latest_explore or {}).get(
                "wohnungserkundung", {})
            candidate = extension.get("goal_candidate", {})
            return (
                candidate.get("state") == "current"
                and "frontier_id" in candidate
                and "dispatch_blocked_reason" not in candidate
            )

        self.wait_for(ready, timeout, "Frontierzielkandidat")
        return self.latest_explore["wohnungserkundung"]["goal_candidate"]

    def send_explore_goal(self, timeout_s=30.0):
        if not self._explore_client.wait_for_server(timeout_sec=8.0):
            raise RuntimeError("ExploreArea-Server fehlt")
        goal = ExploreArea.Goal()
        goal.timeout_s = float(timeout_s)
        future = self._explore_client.send_goal_async(goal)
        self.wait_for(future.done, 5.0, "ExploreArea-Zielannahme")
        handle = future.result()
        if handle is None or not handle.accepted:
            raise RuntimeError("ExploreArea-Ziel wurde nicht angenommen")
        return handle, handle.get_result_async()


def _parameter_text(world):
    safe_bt = Path(__file__).resolve().parents[2] / (
        "src/explore/behavior_trees/navigate_to_pose_no_recovery.xml")
    parameters = {
        "map_topic": world.map_topic,
        "global_costmap_topic": world.costmap_topic,
        "odom_topic": f"/we_m3u/{world.scenario}/odom_unused",
        "nav_action_name": world.nav_action,
        "status_topic": world.explore_status_topic,
        "visualize": False,
        "behavior_tree": str(safe_bt),
        "initial_scan_enabled": False,
        "portal_crossing_enabled": False,
        "return_to_start": False,
        "replan_period_s": 0.05,
        "goal_timeout_s": 10.0,
        "overall_timeout_s": 60.0 if world.multiroom else 30.0,
        "nav_cancel_timeout_s": 1.5,
        "max_frontier_goals": (
            1 if world.frontier_replan else 8 if world.multiroom else 2),
        "map_timeout_s": 2.0 if world.scenario == "frontier_no_source" else 30.0,
        "scan_command_topic": world.scan_command_topic,
        "door_command_topic": world.door_command_topic,
        "door_lidar_scan_topic": world.scan_topic,
        "door_lidar_motion_mode": True,
        "door_traverse_distance_m": 0.50,
        "door_encoder_wheel_budget_m": 1.0,
        "door_lidar_scan_timeout_s": 0.8,
        "door_lidar_recovery_timeout_s": 2.0,
        "door_lidar_max_range_m": 8.0,
        "door_lidar_min_points": 200,
        "door_lidar_max_cost_m": 0.10,
        "door_lidar_min_support_ratio": 0.40,
        "door_lidar_min_distinct_gap_m": 0.000001,
        "door_lidar_max_step_m": 0.09,
        "door_lidar_max_yaw_step_rad": 0.15,
        "region_graph_shadow_enabled": True,
        "region_graph_shadow_raw_map_enabled": True,
        "region_graph_shadow_raw_map_capacity": 8,
        "region_graph_shadow_connected_portals_enabled": True,
        "region_graph_shadow_frontiers_enabled": True,
        "region_graph_shadow_session_id": f"session-m3u-{world.scenario}",
        "region_graph_shadow_start_observation_id": (
            f"start-m3u-{world.scenario}"),
        "region_graph_shadow_map_status_topic": world.map_status_topic,
        "region_graph_shadow_status_topic": world.shadow_status_topic,
        "wohnungserkundung_policy_enabled": True,
        "wohnungserkundung_navigation_enabled": True,
        "wohnungserkundung_persistence_enabled": (
            world.persistence_directory is not None),
        "wohnungserkundung_persistence_directory": (
            str(world.persistence_directory)
            if world.persistence_directory is not None
            else "/tmp/we-m3u-persistence-disabled"),
        "wohnungserkundung_accessible_scope_verified": True,
        "wohnungserkundung_scope_id": f"scope-m3u-{world.scenario}",
        "wohnungserkundung_scope_polygon_xy": [
            0.0, 0.0,
            7.75 if world.multiroom else 5.0, 0.0,
            7.75 if world.multiroom else 5.0, 3.0,
            0.0, 3.0],
        "wohnungserkundung_evidence_clearance_m": 0.10,
        "wohnungserkundung_scope_clearance_m": 0.10,
        "wohnungserkundung_robot_seed_search_m": 0.20,
        "wohnungserkundung_portal_rear_overhang_m": 0.15,
        "wohnungserkundung_portal_exit_clearance_m": 0.10,
        "wohnungserkundung_portal_target_search_m": 0.20,
        "wohnungserkundung_portal_target_lateral_m": 0.15,
        "wohnungserkundung_portal_path_radius_m": 0.15,
        "wohnungserkundung_portal_monitor_enabled": True,
        "wohnungserkundung_traversal_front_overhang_m": 0.10,
        "wohnungserkundung_traversal_rear_overhang_m": 0.10,
        "wohnungserkundung_traversal_start_clearance_m": 0.10,
        "wohnungserkundung_traversal_exit_clearance_m": 0.10,
        "wohnungserkundung_traversal_max_lateral_deviation_m": 0.20,
        "wohnungserkundung_traversal_max_pose_step_m": 0.09,
        "wohnungserkundung_traversal_max_pose_speed_mps": 2.0,
        "wohnungserkundung_traversal_max_yaw_error_rad": 0.25,
        "wohnungserkundung_traversal_max_yaw_step_rad": 0.15,
        "wohnungserkundung_traversal_max_backward_step_m": 0.03,
        "wohnungserkundung_traversal_max_motion_disagreement_m": 0.10,
        "wohnungserkundung_traversal_max_source_age_s": 30.0,
        "wohnungserkundung_traversal_max_revision_lag": 0,
        "wohnungserkundung_traversal_minimum_pose_samples": 10,
        "wohnungserkundung_traversal_maximum_pose_samples": 64,
        "wohnungserkundung_traversal_max_pose_interval_s": 0.5,
        "wohnungserkundung_traversal_max_scan_rejections": 4,
    }
    return json.dumps({"explore_node": {"ros__parameters": parameters}})


def _start_explorer(world, log_path):
    parameter_file = tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", prefix="we-m3u-", delete=False)
    try:
        parameter_file.write(_parameter_text(world))
        parameter_file.close()
        command = [
            sys.executable,
            "-c",
            "from explore.explore_node import main; main()",
            "--ros-args",
            "--params-file",
            parameter_file.name,
        ]
        log_handle = open(log_path, "w", encoding="utf-8")
        process = subprocess.Popen(
            command,
            cwd=str(Path(__file__).resolve().parents[2]),
            env=os.environ.copy(),
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            text=True,
        )
        return process, log_handle, parameter_file.name
    except Exception:
        Path(parameter_file.name).unlink(missing_ok=True)
        raise


def _stop_explorer(process, log_handle, parameter_path):
    if process.poll() is None:
        process.send_signal(signal.SIGINT)
        try:
            process.wait(timeout=5.0)
        except subprocess.TimeoutExpired:
            process.terminate()
            process.wait(timeout=3.0)
    log_handle.close()
    Path(parameter_path).unlink(missing_ok=True)


def _feed_portal_chain(world):
    world.publish_pose_scan(1.025)
    # One fresh revision after portal-task creation separates the later
    # traversal verdict from the graph mutation that opened the task.
    for revision in (7, 8, 9, 10):
        world.publish_revision(revision)
        time.sleep(1.25)
    return world.wait_for_candidate()


def _run_scenario(executor, scenario, log_directory):
    world = SyntheticWorld(scenario)
    executor.add_node(world)
    log_path = log_directory / f"{scenario}.log"
    process, log_handle, parameter_path = _start_explorer(world, log_path)
    explore_handle = None
    explore_result = None
    try:
        world.wait_for(
            lambda: world._explore_client.wait_for_server(timeout_sec=0.1),
            8.0,
            "Explorer-Prozessstart",
        )
        candidate = _feed_portal_chain(world)
        target_x = float(candidate["target"]["x_m"])
        start_x = max(0.5, target_x - 1.60)
        world.publish_pose_scan(start_x)
        time.sleep(0.15)
        explore_handle, explore_result = world.send_explore_goal()
        world.wait_for(
            world.nav_goal_received.is_set, 8.0, "Fake-Nav2-Kindziel")

        if scenario == "positive":
            end_x = min(4.7, target_x + 0.45)
            distance = end_x - start_x
            steps = max(24, int(math.ceil(distance / 0.04)))
            for index in range(steps + 1):
                x_m = start_x + distance * index / steps
                world.publish_pose_scan(x_m)
                time.sleep(0.055)
            time.sleep(0.25)
            world.nav_release.set()
            world.wait_for(
                lambda: (world.latest_explore or {}).get(
                    "wohnungserkundung", {}).get(
                        "portal_traversal", {}).get("state")
                == "confirmed",
                8.0,
                "bestaetigtes Traversalereignis",
            )
            world.wait_for(
                lambda: (
                    (world.latest_shadow or {}).get(
                        "summary", {}).get("completed_task_count", 0) >= 1
                    and (world.latest_shadow or {}).get(
                        "summary", {}).get("confirmed_entry_count", 0) >= 1
                ),
                5.0,
                "atomare Raum-/Aufgabenfortschreibung",
            )
            # A positive parent result must arise from the production
            # completion window, never from canceling the checker-owned goal.
            for revision in (11, 12, 13, 14, 15, 16):
                world.publish_pose_scan(end_x)
                world.publish_revision(revision)
                if explore_result.done():
                    break
                time.sleep(0.70)
            world.wait_for(
                explore_result.done, 8.0,
                "natuerlicher ExploreArea-Gesamtabschluss")
            action_result = explore_result.result()
            if (
                    action_result is None
                    or action_result.status != 4
                    or not action_result.result.success):
                raise AssertionError(
                    f"kein natuerlicher positiver Abschluss: {action_result}")
            result = {
                "scenario": scenario,
                "portal_traversal": "confirmed",
                "parent_result": "natural_success",
                "completed_task_count": world.latest_shadow["summary"][
                    "completed_task_count"],
                "confirmed_entry_count": world.latest_shadow["summary"][
                    "confirmed_entry_count"],
                "portal_task_state": next(
                    task["state"] for task in world.latest_shadow["tasks"]
                    if task["kind"] == "portal"),
            }
        else:
            for index in range(5):
                world.publish_pose_scan(
                    start_x + 0.01 * index, publish_transform=False)
                time.sleep(0.10)
            world.wait_for(
                lambda: world.nav_cancel_count >= 1,
                6.0,
                "Kindzielabbruch nach Monitorfehler",
            )
            world.wait_for(
                lambda: (world.latest_explore or {}).get(
                    "wohnungserkundung", {}).get(
                        "portal_traversal", {}).get("state")
                == "unconfirmed",
                6.0,
                "unbestaetigter Traversalstatus",
            )
            world.wait_for(explore_result.done, 6.0, "ExploreArea-Fehlergebnis")
            shadow_summary = (world.latest_shadow or {}).get("summary", {})
            result = {
                "scenario": scenario,
                "portal_traversal": "unconfirmed",
                "nav_cancel_count": world.nav_cancel_count,
                "completed_task_count": shadow_summary.get(
                    "completed_task_count", 0),
                "confirmed_entry_count": shadow_summary.get(
                    "confirmed_entry_count", 0),
                "portal_task_state": next(
                    task["state"] for task in world.latest_shadow["tasks"]
                    if task["kind"] == "portal"),
            }

        result.update({
            "nav_goal_count": world.nav_goal_count,
            "command_message_count": world.command_count,
            "child_process_alive": process.poll() is None,
        })
        if result["nav_goal_count"] != 1:
            raise AssertionError(result)
        if result["command_message_count"] != 0:
            raise AssertionError(result)
        if scenario == "positive" and (
                result["completed_task_count"] < 1
                or result["confirmed_entry_count"] < 1
                or result["portal_task_state"] != "completed"):
            raise AssertionError(result)
        if scenario == "fault" and (
                result["confirmed_entry_count"] != 0
                or result["portal_task_state"] != "open"
                or result["nav_cancel_count"] < 1):
            raise AssertionError(result)
        return result
    except Exception as error:
        log_handle.flush()
        try:
            log_tail = Path(log_path).read_text(
                encoding="utf-8", errors="replace")[-4000:]
        except OSError:
            log_tail = "<Log nicht lesbar>"
        diagnostics = json.dumps({
            "process_returncode": process.poll(),
            "latest_shadow": world.latest_shadow,
            "latest_explore": world.latest_explore,
        }, sort_keys=True)
        error = RuntimeError(
            f"WE-M3/U-Szenario fehlgeschlagen: {error}\n"
            f"--- Diagnosen ---\n{diagnostics}\n"
            f"--- Explorer-Log ---\n{log_tail}")
        raise error
    finally:
        _stop_explorer(process, log_handle, parameter_path)
        executor.remove_node(world)
        world.destroy_node()


def _complete_portal_navigation(
        world, candidate, *, entry_count, label, source_x=None):
    """Feed bounded scan/TF evidence for the currently selected portal goal."""
    target_x = float(candidate["target"]["x_m"])
    yaw_rad = float(candidate["target"]["yaw_rad"])
    if source_x is None:
        start_x = target_x - 1.60
    else:
        start_x = float(source_x)
    sign = 1.0 if target_x >= start_x else -1.0
    end_x = target_x + sign * 0.45
    world.publish_pose_scan(start_x, yaw_rad=yaw_rad)
    time.sleep(0.15)
    distance = end_x - start_x
    steps = max(24, int(math.ceil(abs(distance) / 0.04)))
    for index in range(steps + 1):
        world.publish_pose_scan(
            start_x + distance * index / steps, yaw_rad=yaw_rad)
        # The productive monitor samples at 20 Hz.  Keep each synthetic pose
        # long enough for that real callback cadence to observe every bounded
        # 4 cm step; otherwise host scheduling can manufacture a >9 cm jump
        # that the production contract must rightly reject.
        time.sleep(0.10)
    time.sleep(0.25)
    world.nav_release.set()
    world.wait_for(
        lambda: (
            (world.latest_explore or {}).get(
                "wohnungserkundung", {}).get(
                    "portal_traversal", {}).get("state") == "confirmed"
            and (world.latest_shadow or {}).get(
                "summary", {}).get("confirmed_entry_count", 0)
            >= entry_count
        ),
        8.0,
        f"bestaetigte Durchfahrt {label}",
    )
    world.nav_release.clear()


def _next_map_revision(world):
    source = (world.latest_shadow or {}).get("source", {})
    return int(source.get("map_revision", 0)) + 1


def _run_multiroom_scenario(executor, log_directory, persistence_directory):
    """Production chain with restart: room -> hall -> room -> same hall."""
    world = SyntheticWorld("multiroom", persistence_directory)
    executor.add_node(world)
    processes = []

    def identity_snapshot():
        status = world.latest_shadow
        return {
            "portal_ids": sorted(p["portal_id"] for p in status["portals"]),
            "region_ids": sorted(r["region_id"] for r in status["regions"]),
            "current_region_id": status["summary"]["current_region_id"],
            "portal_traversal_counts": {
                p["portal_id"]: p["confirmed_traversal_count"]
                for p in status["portals"]},
        }

    def start(label):
        started = _start_explorer(
            world, log_directory / f"multiroom-{label}.log")
        processes.append(started)
        return started

    current = start("before")
    try:
        world.wait_for(
            lambda: world._explore_client.wait_for_server(timeout_sec=0.1),
            8.0,
            "Mehrraum-Explorer-Prozessstart",
        )
        first_candidate = _feed_portal_chain(world)
        handle, result_future = world.send_explore_goal(timeout_s=58.0)
        world.wait_for(
            lambda: world.nav_goal_count >= 1,
            8.0,
            "erstes Mehrraum-Kindziel",
        )
        _complete_portal_navigation(
            world, first_candidate, entry_count=1, label="Startraum-Flur")
        hall_region_id = world.latest_shadow["summary"]["current_region_id"]

        # The raw detector itself first creates the remaining hall frontier.
        # Removing its unknown cells later makes that task unavailable without
        # completing it; therefore the independently discovered second portal
        # is selected next and the return task is genuinely required.
        world.frontier_stage = "visible"
        # The raw frontier feed has no motion authority.  A map-frame pose
        # outside safe free space intentionally prevents a child candidate in
        # this one observation while still retaining the task for later work.
        world.publish_pose_scan(3.75, y_m=0.10)
        for revision in (11, 12):
            world.publish_revision(revision)
            time.sleep(0.55)
        world.wait_for(
            lambda: any(
                task.get("kind") == "frontier"
                and task.get("state") == "open"
                for task in (world.latest_shadow or {}).get("tasks", [])
            ),
            6.0,
            "automatisch gebildete Flur-Frontieraufgabe",
        )
        world.frontier_stage = "hidden"
        world.publish_pose_scan(3.90)

        def second_task_ready():
            return any(
                task.get("kind") == "portal"
                and task.get("state") == "open"
                and task.get("task_id") != first_candidate.get("task_id")
                for task in (world.latest_shadow or {}).get("tasks", []))
        for revision in range(13, 18):
            world.publish_revision(revision)
            time.sleep(0.35)
            if second_task_ready():
                break
        world.wait_for(second_task_ready, 2.0,
                       "zweite versionsgebundene Portalaufgabe")
        world.publish_revision(_next_map_revision(world))

        def second_portal_ready():
            candidate = (world.latest_explore or {}).get(
                "wohnungserkundung", {}).get("goal_candidate", {})
            return (
                candidate.get("state") == "current"
                and candidate.get("kind") == "portal"
                and candidate.get("task_id") != first_candidate.get("task_id")
                and "dispatch_blocked_reason" not in candidate
            )

        world.wait_for(second_portal_ready, 10.0, "zweites Portalziel")
        second_candidate = world.latest_explore[
            "wohnungserkundung"]["goal_candidate"]
        world.publish_pose_scan(3.90)
        world.wait_for(
            lambda: world.nav_goal_count >= 2,
            8.0,
            "zweites Mehrraum-Kindziel",
        )
        _complete_portal_navigation(
            world, second_candidate, entry_count=2, label="Flur-Zimmer",
            source_x=3.90)

        world.wait_for(
            lambda: any(
                task.get("kind") == "transit"
                and task.get("state") == "open"
                for task in (world.latest_shadow or {}).get("tasks", [])
            ),
            6.0,
            "versionsgebundene Rueckkehr-Aufgabe",
        )
        transit_task = next(
            task for task in world.latest_shadow["tasks"]
            if task.get("kind") == "transit"
            and task.get("state") == "open")
        before_restart = identity_snapshot()

        # The parent is interrupted deliberately after the destination room
        # has been entered.  The manager-backed save must retain its still
        # open return task, but neither loading nor the missing fresh pose may
        # dispatch a child goal.
        interrupted = handle.cancel_goal_async()
        world.wait_for(interrupted.done, 4.0, "Mehrraum-Unterbrechung")
        world.wait_for(result_future.done, 5.0,
                       "unterbrochenes Mehrraum-Elternergebnis")
        save_revision = int(world.latest_shadow["source"]["map_revision"])
        world.publish_save_result(save_revision)
        world.wait_for(
            lambda: bool(list(Path(persistence_directory).rglob(
                "state-*.json"))),
            5.0, "atomare Mehrraum-Zustandsspeicherung")
        _stop_explorer(*current)

        world.nav_goal_received.clear()
        world.nav_release.clear()
        goals_before_restart = world.nav_goal_count
        world.latest_shadow = None
        world.latest_explore = None
        current = start("after")
        world.wait_for(
            lambda: world._explore_client.wait_for_server(timeout_sec=0.1),
            8.0, "Mehrraum-Explorer-Neustart")
        time.sleep(1.5)
        if world.nav_goal_count != goals_before_restart:
            raise AssertionError("Mehrraumladen startete unerlaubt Navigation")

        # The retained hall frontier becomes observable again before the
        # return is considered.  It is the concrete purpose of the transit;
        # the remote frontier itself still cannot dispatch directly from this
        # room because the production policy requires the portal monitor.
        world.frontier_stage = "visible"
        # The forward endpoint lies past the portal exit.  A bounded Nav2
        # approach inside the entered room re-establishes the independent
        # monitor's source-side precondition before the return is selected.
        world.publish_pose_scan(6.50, yaw_rad=math.pi)
        # A traversal itself does not manufacture a raw-map update.  Supply a
        # newer unchanged-map revision before evaluating the return target so
        # the production freshness contract remains in force.
        world.publish_revision(_next_map_revision(world))

        def transit_ready():
            candidate = (world.latest_explore or {}).get(
                "wohnungserkundung", {}).get("goal_candidate", {})
            return (
                candidate.get("state") == "current"
                and candidate.get("task_id") == transit_task["task_id"]
                and candidate.get("kind") == "portal"
                and candidate.get("transit_purpose", {}).get(
                    "target_region_id") == hall_region_id
                and candidate.get("transit_purpose", {}).get("task_id")
                and "dispatch_blocked_reason" not in candidate
            )

        world.wait_for(transit_ready, 10.0, "automatisch gewaehltes Rueckportal")
        after_restart = identity_snapshot()
        if after_restart != before_restart:
            raise AssertionError({"before_restart": before_restart,
                                  "after_restart": after_restart})
        if world.nav_goal_count != goals_before_restart:
            raise AssertionError("Neue Quellen ohne Auftrag starteten Navigation")
        transit_candidate = world.latest_explore[
            "wohnungserkundung"]["goal_candidate"]
        if transit_candidate["task_id"] != transit_task["task_id"]:
            raise AssertionError("Rueckkehr-Aufgaben-ID ging beim Neustart verloren")
        if transit_candidate["portal_id"] != second_candidate["portal_id"]:
            raise AssertionError("Rueckweg verwendet nicht dieselbe Portal-ID")
        world.publish_pose_scan(6.50, yaw_rad=float(
            transit_candidate["target"]["yaw_rad"]))
        _resumed_handle, resumed_result = world.send_explore_goal(timeout_s=58.0)
        world.wait_for(
            lambda: world.nav_goal_count >= 3,
            8.0,
            "Rueckkehr-Kindziel",
        )
        _complete_portal_navigation(
            world, transit_candidate, entry_count=3, label="Zimmer-Flur",
            source_x=6.50)
        world.wait_for(
            lambda: any(
                task.get("task_id") == transit_task["task_id"]
                and task.get("state") == "completed"
                for task in (world.latest_shadow or {}).get("tasks", [])
            ),
            5.0,
            "abgeschlossene Rueckkehr-Aufgabe",
        )
        after_return = identity_snapshot()
        if after_return["current_region_id"] != hall_region_id:
            raise AssertionError("Rueckweg erzeugte eine andere Flurregion")
        for key in ("portal_ids", "region_ids"):
            if after_return[key] != before_restart[key]:
                raise AssertionError("Rueckweg erzeugte neue Portal-/Regions-IDs")
        return_portal = transit_candidate["portal_id"]
        if after_return["portal_traversal_counts"][return_portal] != (
                before_restart["portal_traversal_counts"][return_portal] + 1):
            raise AssertionError("Rueckweg besitzt kein neues Traversierungsereignis")

        # The same persisted frontier is now local and therefore eligible.
        # Its Nav2 success is resolved only by the newer all-free raw map.
        # Keep a real non-zero approach distance to the selected frontier.
        # Placing the fake robot directly on its staged approach would rightly
        # make the production Nav2-costmap gate withhold that no-op goal.
        world.publish_pose_scan(3.00)
        world.publish_revision(_next_map_revision(world))
        frontier_candidate = world.wait_for_frontier_candidate()
        world.wait_for(
            lambda: world.nav_goal_count >= 4,
            8.0,
            "Flur-Frontier-Kindziel",
        )
        world.nav_release.set()
        world.wait_for(
            lambda: (world.latest_explore or {}).get(
                "wohnungserkundung", {}).get(
                    "frontier_resolution", {}).get("state")
            == "waiting_for_new_map",
            5.0,
            "positive Frontiernavigation",
        )
        world.nav_release.clear()
        world.frontier_stage = "none"
        # Keep the synthetic source alive until the unchanged production
        # observation window completes. Five publications can be coalesced
        # into only two policy observations on a loaded review machine.
        completion_deadline = time.monotonic() + 12.0
        revision = _next_map_revision(world)
        while not resumed_result.done() and time.monotonic() < completion_deadline:
            world.publish_pose_scan(float(frontier_candidate["target"]["x_m"]))
            world.publish_revision(revision)
            revision += 1
            if resumed_result.done():
                break
            time.sleep(0.70)
        world.wait_for(
            resumed_result.done,
            10.0,
            "natuerlicher Mehrraum-Gesamtabschluss",
        )
        action_result = resumed_result.result()
        if (
                action_result is None
                or action_result.status != 4
                or not action_result.result.success):
            raise AssertionError(
                f"kein natuerlicher Mehrraumabschluss: {action_result}")
        task_by_id = {
            task["task_id"]: task
            for task in world.latest_shadow["tasks"]}
        result = {
            "scenario": "multiroom",
            "chain": "start_room-hall-room-same_hall",
            "interruption": "explicit_cancel_after_destination_room",
            "saved_versions": len(list(Path(persistence_directory).rglob(
                "state-*.json"))),
            "load_started_navigation": False,
            "continuation_order": "new_explicit_explore_area_goal",
            "parent_result": "natural_success",
            "before_restart": before_restart,
            "after_restart": after_restart,
            "after_return": after_return,
            "transit_task_id": transit_task["task_id"],
            "transit_task_state_before_restart": transit_task["state"],
            "frontier_task_id": frontier_candidate["task_id"],
            "confirmed_entry_count": world.latest_shadow["summary"][
                "confirmed_entry_count"],
            "nav_goal_count": world.nav_goal_count,
            "command_message_count": world.command_count,
            "transit_task_state": task_by_id[transit_task["task_id"]]["state"],
            "frontier_task_state": task_by_id[frontier_candidate["task_id"]][
                "state"],
            "child_process_alive": current[0].poll() is None,
        }
        if (
                result["confirmed_entry_count"] < 3
                or result["nav_goal_count"] != 4
                or result["command_message_count"] != 0
                or result["saved_versions"] < 1
                or result["transit_task_state"] != "completed"
                or result["frontier_task_state"] != "completed"):
            raise AssertionError(result)
        return result
    except Exception as error:
        current[1].flush()
        try:
            log_tail = Path(current[1].name).read_text(
                encoding="utf-8", errors="replace")[-6000:]
        except OSError:
            log_tail = "<Log nicht lesbar>"
        diagnostics = json.dumps({
            "process_returncode": current[0].poll(),
            "latest_shadow": world.latest_shadow,
            "latest_explore": world.latest_explore,
        }, sort_keys=True)
        raise RuntimeError(
            f"WE-Mehrraumszenario fehlgeschlagen: {error}\n"
            f"--- Diagnosen ---\n{diagnostics}\n"
            f"--- Explorer-Log ---\n{log_tail}") from error
    finally:
        for process, log_handle, parameter_path in processes:
            if process.poll() is None:
                _stop_explorer(process, log_handle, parameter_path)
        executor.remove_node(world)
        world.destroy_node()


def _run_resume_scenario(executor, log_directory, persistence_directory):
    """Interrupt, save, restart, wait for pose/order, then finish naturally."""
    world = SyntheticWorld("resume", persistence_directory)
    executor.add_node(world)
    processes = []

    def start(label):
        started = _start_explorer(world, log_directory / f"resume-{label}.log")
        processes.append(started)
        return started

    first = start("before")
    try:
        world.wait_for(
            lambda: world._explore_client.wait_for_server(timeout_sec=0.1),
            8.0, "erster Explorer-Prozessstart")
        candidate = _feed_portal_chain(world)
        target_x = float(candidate["target"]["x_m"])
        start_x = max(0.5, target_x - 1.60)
        world.publish_pose_scan(start_x)
        first_handle, first_result = world.send_explore_goal()
        world.wait_for(world.nav_goal_received.is_set, 8.0, "erstes Kindziel")
        canceled = first_handle.cancel_goal_async()
        world.wait_for(canceled.done, 4.0, "explizite Unterbrechung")
        world.wait_for(first_result.done, 5.0, "unterbrochenes Elternergebnis")
        world.publish_save_result(10)
        world.wait_for(
            lambda: bool(list(Path(persistence_directory).rglob(
                "state-*.json"))),
            5.0, "atomare WE-Zustandsspeicherung")
        _stop_explorer(*first)

        world.nav_goal_received.clear()
        world.nav_release.clear()
        goals_before_restart = world.nav_goal_count
        start("after")
        world.wait_for(
            lambda: world._explore_client.wait_for_server(timeout_sec=0.1),
            8.0, "zweiter Explorer-Prozessstart")
        # The transient save status loads state, but neither load nor a missing
        # pose creates a child goal.  A new explicit ExploreArea goal follows.
        time.sleep(1.5)
        if world.nav_goal_count != goals_before_restart:
            raise AssertionError("Laden startete unerlaubt ein Navigationsziel")
        world.publish_pose_scan(start_x)
        world.publish_revision(11)
        resumed_candidate = world.wait_for_candidate()
        if resumed_candidate.get("task_id") != candidate.get("task_id"):
            raise AssertionError("Restaufgaben-ID ging beim Neustart verloren")
        resumed_handle, resumed_result = world.send_explore_goal()
        world.wait_for(world.nav_goal_received.is_set, 8.0, "fortgesetztes Kindziel")
        end_x = min(4.7, target_x + 0.45)
        distance = end_x - start_x
        steps = max(24, int(math.ceil(distance / 0.04)))
        for index in range(steps + 1):
            world.publish_pose_scan(start_x + distance * index / steps)
            time.sleep(0.055)
        world.nav_release.set()
        world.wait_for(
            lambda: (world.latest_explore or {}).get(
                "wohnungserkundung", {}).get(
                    "portal_traversal", {}).get("state") == "confirmed",
            8.0, "fortgesetzte bestaetigte Durchfahrt")
        for revision in range(12, 20):
            world.publish_pose_scan(end_x)
            world.publish_revision(revision)
            if resumed_result.done():
                break
            time.sleep(0.70)
        world.wait_for(
            resumed_result.done, 8.0, "natuerlicher Abschluss nach Neustart")
        action_result = resumed_result.result()
        if (
                action_result is None or action_result.status != 4
                or not action_result.result.success):
            raise AssertionError(
                f"Fortsetzung endete nicht erfolgreich: {action_result}")
        return {
            "scenario": "resume",
            "interruption": "explicit_cancel",
            "saved_versions": len(list(Path(persistence_directory).rglob(
                "state-*.json"))),
            "load_started_navigation": False,
            "pose_revalidated": True,
            "continuation_order": "new_explicit_explore_area_goal",
            "task_id_preserved": resumed_candidate["task_id"],
            "parent_result": "natural_success",
            "nav_goal_count": world.nav_goal_count,
            "command_message_count": world.command_count,
        }
    finally:
        for process, handle, parameter in processes:
            if process.poll() is None:
                _stop_explorer(process, handle, parameter)
        executor.remove_node(world)
        world.destroy_node()


def _run_frontier_replan_scenario(executor, log_directory):
    """Prove that a stopped stale child is followed by real new work."""
    world = SyntheticWorld("frontier_replan")
    executor.add_node(world)
    log_path = log_directory / "frontier_replan.log"
    process, log_handle, parameter_path = _start_explorer(world, log_path)
    try:
        world.wait_for(
            lambda: world._explore_client.wait_for_server(timeout_sec=0.1),
            8.0, "Frontier-Explorer-Prozessstart")
        world.publish_pose_scan(0.85)
        for revision in range(1, 7):
            world.publish_revision(revision)
            try:
                first = world.wait_for_frontier_candidate(timeout=1.0)
                break
            except RuntimeError:
                continue
        else:
            raise RuntimeError("Kein erster Frontierzielkandidat")
        first_task = first["task_id"]
        first_target = (
            float(first["target"]["x_m"]),
            float(first["target"]["y_m"]))
        handle, parent_result = world.send_explore_goal(timeout_s=30.0)
        world.wait_for(lambda: world.nav_goal_count == 1, 8.0,
                       "laufendes Frontierziel A")
        if world.nav_targets[0] != first_target:
            raise AssertionError("Nav2-Ziel A weicht vom Policyziel ab")

        # A changed content revision retains the safe fixed metric target.
        world.publish_revision(7)
        world.wait_for(
            lambda: (world.latest_shadow or {}).get(
                "source", {}).get("map_revision", 0) >= 7,
            5.0, "neue Karten-/Policybewertung bei gueltigem Ziel")
        time.sleep(1.5)
        if world.nav_goal_count != 1 or world.nav_cancel_count != 0:
            raise AssertionError("Gueltiges Ziel wurde unnoetig ersetzt")

        # A byte-identical occupancy grid with a new timestamp is likewise
        # no reason to cancel an in-flight child.
        world.publish_identical_map_with_new_stamp(8)
        time.sleep(1.5)
        if world.nav_goal_count != 1 or world.nav_cancel_count != 0:
            raise AssertionError("Zeitstempelduplikat ersetzte Ziel A")

        # Remove A's unknown pocket and place a real occupied cell block on
        # its fixed metric destination. B's unknown pocket stays available.
        world.frontier_stage = (
            "second_only" if first_target[0] < 3.0 else "first_only")
        world.blocked_goal_xy = first_target
        world.publish_revision(9)
        world.wait_for(lambda: world.nav_cancel_count == 1, 7.0,
                       "sicherer Nav2-Abbruch von Ziel A")
        world.wait_for(lambda: world.nav_terminal == ["canceled"], 4.0,
                       "bestaetigter terminaler A-Abbruch")
        if parent_result.done():
            raise AssertionError("Elternauftrag brach nach A-Abbruch ab")

        # A fresh policy revision must select and dispatch the other
        # independently detected frontier without an external goal request.
        for revision in range(10, 16):
            world.publish_revision(revision)
            if world.nav_goal_count >= 2:
                break
            time.sleep(0.35)
        world.wait_for(lambda: world.nav_goal_count == 2, 8.0,
                       "automatisch versendetes Frontierziel B")
        second = world.wait_for_frontier_candidate(timeout=5.0)
        if second["task_id"] == first_task:
            raise AssertionError("Replan waehlt erneut das blockierte Ziel A")
        second_target = (
            float(second["target"]["x_m"]),
            float(second["target"]["y_m"]))
        if world.nav_targets[1] != second_target:
            raise AssertionError("Nav2-Ziel B weicht vom Policyziel ab")
        if world.nav_max_active_count != 1 or world.nav_active_count != 1:
            raise AssertionError("Konkurrierende Nav2-Kindziele")
        if parent_result.done():
            raise AssertionError("Elternauftrag endete vor Ziel B")

        world.nav_release.set()
        world.wait_for(lambda: world.nav_terminal == [
            "canceled", "succeeded"], 5.0, "erfolgreiches Ziel B")
        world.nav_release.clear()
        if parent_result.done():
            raise AssertionError("Elternauftrag stoppte unmittelbar nach B")
        world.frontier_stage = "none"
        for revision in range(16, 23):
            world.publish_pose_scan(second_target[0], y_m=second_target[1])
            world.publish_revision(revision)
            if any(
                    task.get("task_id") == second["task_id"]
                    and task.get("state") == "completed"
                    for task in (world.latest_shadow or {}).get("tasks", [])):
                break
            time.sleep(0.5)
        world.wait_for(
            lambda: any(
                task.get("task_id") == second["task_id"]
                and task.get("state") == "completed"
                for task in (world.latest_shadow or {}).get("tasks", [])),
            7.0, "belegter Frontierfortschritt nach Ziel B")
        if world.nav_goal_count != 2 or world.nav_max_active_count != 1:
            raise AssertionError("Replan erzeugte eine Zielschleife")
        if world.command_count:
            raise AssertionError("Prozesspruefer erzeugte Fahrbefehle")
        result = {
            "scenario": "frontier_replan",
            "first_task_id": first_task,
            "second_task_id": second["task_id"],
            "nav_terminal": list(world.nav_terminal),
            "nav_goal_count": world.nav_goal_count,
            "nav_cancel_count": world.nav_cancel_count,
            "nav_max_active_count": world.nav_max_active_count,
            "second_task_state": "completed",
            "parent_continued_after_second_child": not parent_result.done(),
            "command_message_count": world.command_count,
        }
        if not result["parent_continued_after_second_child"]:
            raise AssertionError(result)
        canceled = handle.cancel_goal_async()
        world.wait_for(canceled.done, 4.0, "Pruefer-Abbruch nach Nachweis")
        world.wait_for(parent_result.done, 5.0, "beendeter Prueferauftrag")
        return result
    except Exception as error:
        log_handle.flush()
        try:
            log_tail = log_path.read_text(
                encoding="utf-8", errors="replace")[-6000:]
        except OSError:
            log_tail = "<Log nicht lesbar>"
        diagnostics = json.dumps({
            "process_returncode": process.poll(),
            "nav_goals": world.nav_goal_count,
            "nav_cancels": world.nav_cancel_count,
            "nav_terminal": world.nav_terminal,
            "nav_targets": world.nav_targets,
            "latest_shadow_summary": (world.latest_shadow or {}).get(
                "summary"),
            "latest_shadow_tasks": (world.latest_shadow or {}).get(
                "tasks"),
            "latest_explore": world.latest_explore,
        }, sort_keys=True)
        raise RuntimeError(
            f"WE-Frontier-Replan fehlgeschlagen: {error}\n"
            f"--- Diagnosen ---\n{diagnostics}\n"
            f"--- Explorer-Log ---\n{log_tail}") from error
    finally:
        _stop_explorer(process, log_handle, parameter_path)
        executor.remove_node(world)
        world.destroy_node()


def _run_frontier_no_source_scenario(executor, log_directory):
    """An invalidated child waits fail-closed, bounded by mission time."""
    world = SyntheticWorld("frontier_no_source")
    executor.add_node(world)
    log_path = log_directory / "frontier_no_source.log"
    process, log_handle, parameter_path = _start_explorer(world, log_path)
    try:
        world.wait_for(
            lambda: world._explore_client.wait_for_server(timeout_sec=0.1),
            8.0, "Frontier-Explorer-Prozessstart ohne Folgequelle")
        world.publish_pose_scan(0.85)
        for revision in range(1, 7):
            world.publish_revision(revision)
            try:
                candidate = world.wait_for_frontier_candidate(timeout=1.0)
                break
            except RuntimeError:
                continue
        else:
            raise RuntimeError("Kein erster Frontierzielkandidat")
        first_target = (
            float(candidate["target"]["x_m"]),
            float(candidate["target"]["y_m"]))
        _handle, parent_result = world.send_explore_goal(timeout_s=10.0)
        world.wait_for(lambda: world.nav_goal_count == 1, 8.0,
                       "laufendes Frontierziel ohne Folgequelle")
        world.frontier_stage = "none"
        world.blocked_goal_xy = first_target
        world.publish_revision(7)
        world.wait_for(lambda: world.nav_terminal == ["canceled"], 7.0,
                       "sicheres Stoppen ohne Folgequelle")
        world.wait_for(
            lambda: "source_map" in (world.latest_explore or {}).get(
                "wohnungserkundung", {}).get(
                    "source", {}).get("stale_sources", []),
            5.0, "unfrische Kartenquelle")
        if world.nav_goal_count != 1 or parent_result.done():
            raise AssertionError("Ohne Quelle wurde gefahren oder abgebrochen")
        world.wait_for(parent_result.done, 10.0,
                       "Begrenzung durch Gesamtmissionsbudget")
        action_result = parent_result.result()
        if action_result is None or action_result.status != 4:
            raise AssertionError(
                f"Kein kontrollierter Teilabschluss: {action_result}")
        if world.nav_goal_count != 1 or world.nav_cancel_count != 1:
            raise AssertionError("Ohne Quelle wurde ein weiteres Ziel gesendet")
        if world.nav_max_active_count != 1 or world.command_count:
            raise AssertionError("Konkurrierendes Ziel oder Fahrbefehl")
        return {
            "scenario": "frontier_no_source",
            "nav_goal_count": world.nav_goal_count,
            "nav_cancel_count": world.nav_cancel_count,
            "nav_terminal": list(world.nav_terminal),
            "nav_max_active_count": world.nav_max_active_count,
            "parent_result": "budget_bounded_partial",
            "command_message_count": world.command_count,
        }
    finally:
        _stop_explorer(process, log_handle, parameter_path)
        executor.remove_node(world)
        world.destroy_node()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--scenario", choices=("all", "frontier_replan", "frontier_no_source"),
        default="all")
    args = parser.parse_args()
    rclpy.init()
    executor = MultiThreadedExecutor(num_threads=6)
    spin_thread = threading.Thread(target=executor.spin, daemon=True)
    spin_thread.start()
    try:
        with tempfile.TemporaryDirectory(prefix="we-m3u-process-") as path:
            log_directory = Path(path)
            results = []
            if args.scenario == "all":
                results.extend(
                    _run_scenario(executor, scenario, log_directory)
                    for scenario in ("positive", "fault"))
                results.append(_run_multiroom_scenario(
                    executor, log_directory,
                    log_directory / "we-multiroom-state"))
                results.append(_run_resume_scenario(
                    executor, log_directory, log_directory / "we-state"))
            if args.scenario in {"all", "frontier_replan"}:
                results.append(_run_frontier_replan_scenario(
                    executor, log_directory))
            if args.scenario in {"all", "frontier_no_source"}:
                results.append(_run_frontier_no_source_scenario(
                    executor, log_directory))
        print(json.dumps({
            "ros_domain_id": os.environ["ROS_DOMAIN_ID"],
            "scenarios": results,
        }, sort_keys=True))
    finally:
        executor.shutdown(timeout_sec=3.0)
        if rclpy.ok():
            rclpy.shutdown()
        spin_thread.join(timeout=3.0)


if __name__ == "__main__":
    main()
