#!/usr/bin/env python3
"""Isolated, device-free process smoke for the WE-M3 portal runtime.

The script starts the real ``ExploreNode`` in a child process and supplies
only synthetic ROS data on scenario-specific topics.  It never publishes a
velocity command, opens a device, or starts a robot launch profile.
"""

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
HEIGHT = 60
RESOLUTION = 0.05
ORIGIN = (0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0)


def _map_cells(revision):
    """Known synthetic rooms: no frontier tasks, one connected doorway."""
    occupancy = np.full((HEIGHT, WIDTH), 100, dtype=np.int8)
    occupancy[5:55, 3:48] = 0
    occupancy[5:55, 52:97] = 0
    occupancy[27:33, 48:52] = 0
    occupancy[0, revision % WIDTH] = 99
    return occupancy.ravel().tolist()


def _fingerprint(cells, resolution=RESOLUTION):
    return map_snapshot_fingerprint(
        width=WIDTH,
        height=HEIGHT,
        resolution=float(resolution),
        frame_id="map",
        origin=ORIGIN,
        compact_cells=compact_occupancy_cells(
            cells=cells, cell_count=WIDTH * HEIGHT),
    )


def _map_message(node, revision):
    message = OccupancyGrid()
    message.header.frame_id = "map"
    message.header.stamp = node.get_clock().now().to_msg()
    message.info.width = WIDTH
    message.info.height = HEIGHT
    message.info.resolution = RESOLUTION
    message.info.origin.orientation.w = 1.0
    message.data = _map_cells(revision)
    return message


def _map_status(message, revision):
    stamp_ns = (
        int(message.header.stamp.sec) * 1_000_000_000
        + int(message.header.stamp.nanosec)
    )
    wire_resolution = float(np.float32(message.info.resolution))
    return {
        "schema_version": 1,
        "event": "status",
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
                "width": WIDTH,
                "height": HEIGHT,
                "resolution": wire_resolution,
                "frame_id": "map",
                "origin": {"position": [0.0, 0.0]},
                "source_stamp_ns": stamp_ns,
                "fingerprint": _fingerprint(
                    message.data, resolution=wire_resolution),
            },
        },
        "pose": {"available": False},
        "storage": {"root": "/not-used"},
        "counters": {"accepted_maps": revision, "duplicate_maps": 0},
    }


def _box_ranges(x_m, y_m, count=720):
    """Return exact rays to a fixed asymmetric rectangular room contour."""
    angles = -math.pi + np.arange(count, dtype=np.float64) * (
        2.0 * math.pi / count)
    dx = np.cos(angles)
    dy = np.sin(angles)
    candidates = np.full((4, count), np.inf, dtype=np.float64)
    with np.errstate(divide="ignore", invalid="ignore"):
        for index, wall_x in enumerate((-1.0, 6.0)):
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
    def __init__(self, scenario):
        super().__init__(f"we_m3u_world_{scenario}")
        self.scenario = scenario
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
        self.nav_goal_received = threading.Event()
        self.nav_release = threading.Event()
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

    def _accept_nav(self, _request):
        self.nav_goal_count += 1
        self.nav_goal_received.set()
        return GoalResponse.ACCEPT

    def _cancel_nav(self, _goal_handle):
        self.nav_cancel_count += 1
        return CancelResponse.ACCEPT

    def _execute_nav(self, goal_handle):
        deadline = time.monotonic() + 12.0
        while time.monotonic() < deadline:
            if goal_handle.is_cancel_requested:
                goal_handle.canceled()
                return NavigateToPose.Result()
            if self.nav_release.wait(0.02):
                goal_handle.succeed()
                return NavigateToPose.Result()
        goal_handle.abort()
        return NavigateToPose.Result()

    def publish_revision(self, revision):
        message = _map_message(self, revision)
        status = String(data=json.dumps(_map_status(message, revision)))
        self._map_pub.publish(message)
        self._costmap_pub.publish(message)
        # Exercise both arrival orders and allow the child executor to retain
        # the exact raw sample before the idempotent status replay.
        time.sleep(0.10)
        self._map_status_pub.publish(status)
        time.sleep(0.10)
        self._map_status_pub.publish(status)

    def publish_pose_scan(self, x_m, *, publish_transform=True):
        stamp = self.get_clock().now().to_msg()
        if publish_transform:
            transform = TransformStamped()
            transform.header.frame_id = "map"
            transform.child_frame_id = "base_link"
            transform.header.stamp = stamp
            transform.transform.translation.x = float(x_m)
            transform.transform.translation.y = 1.525
            transform.transform.rotation.w = 1.0
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
        scan.ranges = _box_ranges(float(x_m), 1.525).astype(float).tolist()
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

    def send_explore_goal(self, timeout_s=15.0):
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
        "overall_timeout_s": 15.0,
        "nav_cancel_timeout_s": 1.5,
        "max_frontier_goals": 2,
        "map_timeout_s": 30.0,
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
        "wohnungserkundung_accessible_scope_verified": True,
        "wohnungserkundung_scope_id": f"scope-m3u-{world.scenario}",
        "wohnungserkundung_scope_polygon_xy": [
            0.0, 0.0, 5.0, 0.0, 5.0, 3.0, 0.0, 3.0],
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
    for revision in (7, 8, 9):
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
            cancel_future = explore_handle.cancel_goal_async()
            world.wait_for(cancel_future.done, 3.0, "ExploreArea-Abbruch")
            result = {
                "scenario": scenario,
                "portal_traversal": "confirmed",
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


def main():
    rclpy.init()
    executor = MultiThreadedExecutor(num_threads=6)
    spin_thread = threading.Thread(target=executor.spin, daemon=True)
    spin_thread.start()
    try:
        with tempfile.TemporaryDirectory(prefix="we-m3u-process-") as path:
            log_directory = Path(path)
            results = [
                _run_scenario(executor, scenario, log_directory)
                for scenario in ("positive", "fault")
            ]
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
