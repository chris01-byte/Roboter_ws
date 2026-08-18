#!/usr/bin/env python3
# ============================================================================
#  explore_node.py  -  Frontier- und adaptive Flaechenexploration
#  ---------------------------------------------------------------------------
#  ZWECK:
#    Der Roboter erkundet die Wohnung SELBSTSTAENDIG und ZIELGERICHTET -
#    NICHT per Zufallsgenerator. Er nutzt die "Frontier"-Methode:
#      * Eine Frontier ist die Grenze zwischen bekannt-freiem und noch
#        unbekanntem Raum in der SLAM-Karte.
#      * Der Node sucht alle Frontiers, bewertet sie (Kosten/Nutzen) und
#        schickt die beste als Fahrziel an Nav2.
#      * Nach Ende der Frontiers misst er die reale Fahrspur gegen den sicher
#        befahrbaren Freiraum und faehrt adaptive Abdeckungsziele an.
#      * Erst die konfigurierte Fahrspur-Abdeckung bestaetigt den Abschluss.
#    Das ist deterministisch, effizient und vollstaendig. CPU-only, kein CUDA.
#
#  ROLLE IN DER ARCHITEKTUR (Schichten):
#    mission_manager / Behavior-Tree  --Action ExploreArea-->  DIESER NODE
#    DIESER NODE                       --Action navigate_to_pose-->  Nav2
#    Reaktive Sicherheit (collision_monitor, VL53) bleibt UNBERUEHRT aktiv.
#
#  SCHNITTSTELLEN:
#    Action-Server : /explore_area        (robot_interfaces/ExploreArea)
#    Action-Client : navigate_to_pose     (nav2_msgs/NavigateToPose)
#    Subscribe     : <map_topic>          (nav_msgs/OccupancyGrid, SLAM)
#    TF            : <global_frame> -> <robot_base_frame>  (Roboterpose)
#    Publish (opt) : <marker_topic>       (visualization_msgs/MarkerArray)
#    Publish       : /explore/status_json (std_msgs/String, 1 Hz)
#
#  ALLE PARAMETER -> config/explore_params.yaml (nur dort aendern!).
#
#  ABNAHME: Rundblick und vier Frontier-Ziele am 16.08.2026 real gefahren;
#  adaptive Abdeckung und App-Start/Abbruch motorlos integriert.
# ============================================================================

import json
import math
import threading
import time
from collections import deque
from dataclasses import dataclass
from typing import List, Optional, Tuple

import numpy as np

import rclpy
from rclpy.node import Node
from rclpy.action import ActionServer, ActionClient, CancelResponse, GoalResponse
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy

from nav_msgs.msg import OccupancyGrid, Odometry
from geometry_msgs.msg import PoseStamped, Point, Twist
from std_msgs.msg import String
from visualization_msgs.msg import Marker, MarkerArray
from action_msgs.msg import GoalStatus
from nav2_msgs.action import NavigateToPose
from robot_interfaces.action import ExploreArea

import tf2_ros


@dataclass
class CoveragePlan:
    """Momentaufnahme der sicher befahrbaren, real abgefahrenen Flaeche."""

    ratio: float
    reachable_area_m2: float
    covered_area_m2: float
    goal_cell: Optional[Tuple[int, int]]


def circular_clearance_mask(
        data: np.ndarray, clearance_cells: int) -> np.ndarray:
    """Erode known-free space by an isotropic circular clearance radius.

    The previous square window treated a diagonal corner at ``r * sqrt(2)``
    like an obstacle only ``r`` away. On a 3-cm map that disconnected ordinary
    doorways although Nav2's circular global model could pass them. Unknown
    cells and map borders remain blocked; this changes geometry, not safety.
    """
    free = data == 0
    if clearance_cells <= 0:
        return free
    radius = int(clearance_cells)
    height, width = free.shape
    blocked = np.pad(
        ~free, radius, mode='constant', constant_values=True)
    unsafe = np.zeros_like(free, dtype=bool)
    radius_squared = radius * radius
    for drow in range(-radius, radius + 1):
        dcol_max = math.isqrt(radius_squared - drow * drow)
        rows = blocked[
            radius + drow:radius + drow + height, :]
        for dcol in range(-dcol_max, dcol_max + 1):
            unsafe |= rows[
                :, radius + dcol:radius + dcol + width]
    return free & ~unsafe


def connected_mask(mask: np.ndarray, seed: Tuple[int, int]) -> np.ndarray:
    """Return the conservative 4-connected component containing ``seed``."""
    height, width = mask.shape
    row, col = seed
    result = np.zeros_like(mask, dtype=bool)
    if not (0 <= row < height and 0 <= col < width and mask[row, col]):
        return result
    queue = deque([(row, col)])
    result[row, col] = True
    while queue:
        current_row, current_col = queue.popleft()
        for drow, dcol in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            next_row = current_row + drow
            next_col = current_col + dcol
            if (
                    0 <= next_row < height
                    and 0 <= next_col < width
                    and mask[next_row, next_col]
                    and not result[next_row, next_col]):
                result[next_row, next_col] = True
                queue.append((next_row, next_col))
    return result


def nearest_mask_cell(
        mask: np.ndarray, row: int, col: int,
        maximum_distance_cells: int) -> Optional[Tuple[int, int]]:
    """Find the nearest true cell without crossing a topology boundary."""
    rows, cols = np.nonzero(mask)
    if rows.size == 0:
        return None
    distances = (rows - row) ** 2 + (cols - col) ** 2
    index = int(np.argmin(distances))
    if distances[index] > maximum_distance_cells ** 2:
        return None
    return int(rows[index]), int(cols[index])


def stamp_coverage(
        shape: Tuple[int, int], path_cells: List[Tuple[int, int]],
        radius_cells: int) -> np.ndarray:
    """Rasterize the robot's measured path with a circular visit radius."""
    covered = np.zeros(shape, dtype=bool)
    height, width = shape
    radius = max(0, int(radius_cells))
    radius_squared = radius ** 2
    for row, col in path_cells:
        row0 = max(0, row - radius)
        row1 = min(height, row + radius + 1)
        col0 = max(0, col - radius)
        col1 = min(width, col + radius + 1)
        yy, xx = np.ogrid[row0:row1, col0:col1]
        disk = (yy - row) ** 2 + (xx - col) ** 2 <= radius_squared
        covered[row0:row1, col0:col1] |= disk
    return covered


def farthest_uncovered_cell(
        reachable: np.ndarray, covered: np.ndarray,
        excluded: np.ndarray) -> Optional[Tuple[int, int]]:
    """Choose the geodesically farthest safe cell from covered space."""
    candidates = reachable & ~covered & ~excluded
    if not np.any(candidates):
        return None
    distance = np.full(reachable.shape, -1, dtype=np.int32)
    queue = deque()
    for row, col in zip(*np.nonzero(reachable & covered)):
        distance[row, col] = 0
        queue.append((int(row), int(col)))
    if not queue:
        return None
    while queue:
        row, col = queue.popleft()
        next_distance = distance[row, col] + 1
        for drow, dcol in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            next_row, next_col = row + drow, col + dcol
            if (
                    0 <= next_row < reachable.shape[0]
                    and 0 <= next_col < reachable.shape[1]
                    and reachable[next_row, next_col]
                    and distance[next_row, next_col] < 0):
                distance[next_row, next_col] = next_distance
                queue.append((next_row, next_col))
    candidate_rows, candidate_cols = np.nonzero(candidates)
    values = distance[candidate_rows, candidate_cols]
    valid = values >= 0
    if not np.any(valid):
        return None
    candidate_rows = candidate_rows[valid]
    candidate_cols = candidate_cols[valid]
    values = values[valid]
    index = int(np.argmax(values))
    return int(candidate_rows[index]), int(candidate_cols[index])


def normalize_angle(angle: float) -> float:
    """Normalize an angle to [-pi, pi)."""
    return (angle + math.pi) % (2.0 * math.pi) - math.pi


def quaternion_yaw(q) -> float:
    """Return planar yaw for a geometry_msgs compatible quaternion."""
    return math.atan2(
        2.0 * (q.w * q.z + q.x * q.y),
        1.0 - 2.0 * (q.y * q.y + q.z * q.z))


class RotationProgress:
    """Accumulate a full rotation across the +/-pi wraparound."""

    def __init__(self, initial_yaw: float, direction: float = 1.0):
        if direction not in (-1.0, 1.0):
            raise ValueError('Drehrichtung muss -1 oder +1 sein')
        self.previous_yaw = initial_yaw
        self.direction = direction
        self.progress = 0.0
        self.reverse_progress = 0.0

    def update(self, yaw: float) -> float:
        directed_step = self.direction * normalize_angle(
            yaw - self.previous_yaw)
        self.previous_yaw = yaw
        if directed_step >= 0.0:
            self.progress += directed_step
        else:
            self.reverse_progress -= directed_step
        return directed_step


class Frontier:
    """Eine zusammenhaengende Frontier-Region (Grenze frei<->unbekannt)."""
    def __init__(self, centroid_world: Tuple[float, float], size_cells: int):
        self.cx = centroid_world[0]      # Schwerpunkt X in Weltkoordinaten [m]
        self.cy = centroid_world[1]      # Schwerpunkt Y in Weltkoordinaten [m]
        self.size = size_cells           # Anzahl Frontier-Zellen (Nutzen-Mass)
        self.cost = 0.0                  # berechnete Gesamtkosten (kleiner = besser)
        self.goal_x: Optional[float] = None
        self.goal_y: Optional[float] = None


class ExploreNode(Node):
    def __init__(self):
        super().__init__('explore_node')

        # -------------------------------------------------------------------
        #  Parameter (Defaults; per explore_params.yaml ueberschreibbar)
        # -------------------------------------------------------------------
        self._map_topic         = self.declare_parameter('map_topic', '/map').value
        self._global_frame      = self.declare_parameter('global_frame', 'map').value
        self._robot_base_frame  = self.declare_parameter('robot_base_frame', 'base_link').value
        self._nav_action_name   = self.declare_parameter('nav_action_name', 'navigate_to_pose').value
        self._replan_period_s   = float(self.declare_parameter('replan_period_s', 2.0).value)
        self._min_frontier_m    = float(self.declare_parameter('min_frontier_size_m', 0.30).value)
        self._goal_timeout_s    = float(self.declare_parameter('goal_timeout_s', 45.0).value)
        self._overall_timeout_s = float(self.declare_parameter('overall_timeout_s', 0.0).value)
        self._potential_scale   = float(self.declare_parameter('potential_scale', 3.0).value)
        self._gain_scale        = float(self.declare_parameter('gain_scale', 1.0).value)
        self._heading_scale     = float(self.declare_parameter('heading_scale', 0.75).value)
        self._min_goal_dist_m   = float(self.declare_parameter('min_goal_distance_m', 0.30).value)
        self._blacklist_radius  = float(self.declare_parameter('blacklist_radius_m', 0.35).value)
        self._frontier_revisit_radius = float(self.declare_parameter(
            'frontier_revisit_radius_m', 0.60).value)
        self._max_frontier_goals = int(self.declare_parameter(
            'max_frontier_goals', 20).value)
        self._approach_dist_m   = float(self.declare_parameter('frontier_approach_distance_m', 0.45).value)
        self._goal_clearance_m  = float(self.declare_parameter('goal_clearance_m', 0.35).value)
        self._goal_search_m     = float(self.declare_parameter('goal_search_radius_m', 0.30).value)
        self._map_timeout_s     = float(self.declare_parameter('map_timeout_s', 5.0).value)
        self._cancel_timeout_s  = float(self.declare_parameter('nav_cancel_timeout_s', 3.0).value)
        self._max_failed_goals  = int(self.declare_parameter('max_failed_goals', 6).value)
        self._behavior_tree     = str(self.declare_parameter('behavior_tree', '').value).strip()
        self._return_to_start_p = bool(self.declare_parameter('return_to_start', False).value)
        self._visualize         = bool(self.declare_parameter('visualize', True).value)
        self._marker_topic      = self.declare_parameter('marker_topic', '/explore/frontiers').value
        self._odom_topic        = self.declare_parameter('odom_topic', '/odom').value
        self._scan_cmd_topic    = self.declare_parameter(
            'scan_command_topic', '/cmd_vel_explore_scan_raw').value
        self._initial_scan_enabled = bool(self.declare_parameter(
            'initial_scan_enabled', True).value)
        self._initial_scan_angle = float(self.declare_parameter(
            'initial_scan_angle_rad', 2.0 * math.pi).value)
        self._initial_scan_speed = float(self.declare_parameter(
            'initial_scan_angular_speed_radps', 0.12).value)
        self._initial_scan_timeout = float(self.declare_parameter(
            'initial_scan_timeout_s', 210.0).value)
        self._scan_odom_timeout = float(self.declare_parameter(
            'scan_odom_timeout_s', 0.8).value)
        self._scan_no_progress_timeout = float(self.declare_parameter(
            'scan_no_progress_timeout_s', 8.0).value)
        self._scan_progress_window = float(self.declare_parameter(
            'scan_progress_window_rad', 0.03).value)
        self._scan_rate_check_after = float(self.declare_parameter(
            'scan_rate_check_after_s', 15.0).value)
        self._scan_min_average_rate = float(self.declare_parameter(
            'scan_min_average_rate_radps', 0.01).value)
        self._scan_reverse_limit = float(self.declare_parameter(
            'scan_reverse_limit_rad', 0.08).value)
        self._scan_stop_timeout = float(self.declare_parameter(
            'scan_stop_timeout_s', 4.0).value)
        self._scan_stop_tolerance = float(self.declare_parameter(
            'scan_stop_angular_tolerance_radps', 0.02).value)
        self._scan_command_rate = float(self.declare_parameter(
            'scan_command_rate_hz', 20.0).value)
        self._prealign_enabled = bool(self.declare_parameter(
            'prealign_enabled', True).value)
        self._prealign_handoff_tolerance = float(self.declare_parameter(
            'prealign_handoff_tolerance_rad', 0.17).value)
        self._prealign_stop_margin = float(self.declare_parameter(
            'prealign_stop_margin_rad', 0.10).value)
        self._prealign_speed = float(self.declare_parameter(
            'prealign_angular_speed_radps', 0.12).value)
        self._prealign_timeout = float(self.declare_parameter(
            'prealign_timeout_s', 180.0).value)
        self._prealign_rate_check_after = float(self.declare_parameter(
            'prealign_rate_check_after_s', 15.0).value)
        self._prealign_min_average_rate = float(self.declare_parameter(
            'prealign_min_average_rate_radps', 0.01).value)
        self._prealign_settle_s = float(self.declare_parameter(
            'prealign_map_settle_s', 1.0).value)
        self._prealign_max_passes = int(self.declare_parameter(
            'prealign_max_passes', 3).value)
        self._prealign_min_improvement = float(self.declare_parameter(
            'prealign_min_improvement_rad', 0.04).value)
        self._coverage_enabled = bool(self.declare_parameter(
            'coverage_enabled', True).value)
        self._coverage_target_ratio = float(self.declare_parameter(
            'coverage_target_ratio', 0.85).value)
        self._coverage_visit_radius_m = float(self.declare_parameter(
            'coverage_visit_radius_m', 0.65).value)
        self._coverage_clearance_m = float(self.declare_parameter(
            'coverage_clearance_m', 0.40).value)
        self._coverage_min_goal_distance_m = float(self.declare_parameter(
            'coverage_min_goal_distance_m', 0.70).value)
        self._coverage_path_sample_m = float(self.declare_parameter(
            'coverage_path_sample_m', 0.12).value)
        self._coverage_max_interpolation_gap_m = float(self.declare_parameter(
            'coverage_max_interpolation_gap_m', 0.35).value)
        self._coverage_max_goals = int(self.declare_parameter(
            'coverage_max_goals', 14).value)
        self._status_topic = str(self.declare_parameter(
            'status_topic', '/explore/status_json').value)

        # -------------------------------------------------------------------
        #  Laufzeit-Zustand
        # -------------------------------------------------------------------
        self._map: Optional[OccupancyGrid] = None
        self._map_received_at: Optional[float] = None
        self._blacklist: List[Tuple[float, float]] = []   # gescheiterte Ziele (Weltkoord.)
        self._visited_frontier_goals: List[Tuple[float, float]] = []
        self._start_xy: Optional[Tuple[float, float]] = None
        self._active_goal = False
        self._active_goal_lock = threading.Lock()
        self._odom_lock = threading.Lock()
        self._odom_yaw: Optional[float] = None
        self._odom_angular_speed: Optional[float] = None
        self._odom_received_at: Optional[float] = None
        self._coverage_path: List[Tuple[float, float]] = []
        self._coverage_ratio = 0.0
        self._reachable_area_m2 = 0.0
        self._covered_area_m2 = 0.0
        self._coverage_goals_visited = 0
        self._frontiers_visited_status = 0
        self._frontiers_remaining = 0
        self._coverage_complete = False
        self._status_state = 'idle'
        self._status_phase = 'idle'
        self._status_message = 'Explorer bereit; warte auf Erkundungsauftrag.'

        if (
                self._approach_dist_m <= 0.0
                or self._goal_clearance_m <= 0.0
                or self._goal_search_m < 0.0
                or self._map_timeout_s <= 0.0
                or self._cancel_timeout_s <= 0.0
                or self._max_failed_goals <= 0
                or self._frontier_revisit_radius <= self._min_goal_dist_m
                or self._max_frontier_goals <= 0
                or self._heading_scale < 0.0
                or self._initial_scan_angle <= 0.0
                or not 0.0 < self._initial_scan_speed <= 0.15
                or self._initial_scan_timeout <= 0.0
                or self._scan_odom_timeout <= 0.0
                or self._scan_no_progress_timeout <= 0.0
                or self._scan_progress_window <= 0.0
                or self._scan_rate_check_after <= 0.0
                or self._scan_min_average_rate <= 0.0
                or self._scan_reverse_limit <= 0.0
                or self._scan_stop_timeout <= 0.0
                or self._scan_stop_tolerance <= 0.0
                or self._scan_command_rate <= 0.0
                or self._prealign_handoff_tolerance <= 0.0
                or self._prealign_stop_margin <= 0.0
                or self._prealign_stop_margin
                >= self._prealign_handoff_tolerance
                or not 0.0 < self._prealign_speed <= 0.15
                or self._prealign_timeout <= 0.0
                or self._prealign_rate_check_after <= 0.0
                or self._prealign_min_average_rate <= 0.0
                or self._prealign_settle_s < 0.0
                or self._prealign_max_passes <= 0
                or self._prealign_min_improvement <= 0.0
                or self._prealign_min_improvement
                >= self._prealign_handoff_tolerance
                or not 0.0 < self._coverage_target_ratio <= 1.0
                or self._coverage_visit_radius_m <= 0.0
                or self._coverage_clearance_m <= 0.0
                or self._coverage_min_goal_distance_m <= 0.0
                or self._coverage_path_sample_m <= 0.0
                or self._coverage_path_sample_m
                > self._coverage_visit_radius_m
                or self._coverage_max_interpolation_gap_m
                <= self._coverage_path_sample_m
                or self._coverage_max_goals <= 0):
            raise ValueError('Explorer-Sicherheitsgrenzen muessen positiv sein')
        if not self._behavior_tree:
            raise ValueError(
                'behavior_tree ist Pflicht; autonome Navigation ohne '
                'expliziten Recovery-freien Baum ist gesperrt')

        # Reentrant-Group: Map-Callback, Action-Server und Nav-Client duerfen
        # sich NICHT gegenseitig blockieren (der Explore-Loop wartet blockierend
        # auf Nav-Ergebnisse, waehrend weiter Karten hereinkommen muessen).
        self._cb = ReentrantCallbackGroup()

        # -------------------------------------------------------------------
        #  ROS-Schnittstellen
        # -------------------------------------------------------------------
        self._tf_buffer = tf2_ros.Buffer()
        self._tf_listener = tf2_ros.TransformListener(self._tf_buffer, self)

        self.create_subscription(
            OccupancyGrid, self._map_topic, self._on_map, 1, callback_group=self._cb)
        self.create_subscription(
            Odometry, self._odom_topic, self._on_odom, 20,
            callback_group=self._cb)
        self._scan_cmd_pub = self.create_publisher(
            Twist, self._scan_cmd_topic, 10)
        status_qos = QoSProfile(depth=1)
        status_qos.durability = DurabilityPolicy.TRANSIENT_LOCAL
        status_qos.reliability = ReliabilityPolicy.RELIABLE
        self._status_pub = self.create_publisher(
            String, self._status_topic, status_qos)
        self._status_timer = self.create_timer(
            1.0, self._publish_current_status, callback_group=self._cb)

        self._nav_client = ActionClient(
            self, NavigateToPose, self._nav_action_name, callback_group=self._cb)

        if self._visualize:
            self._marker_pub = self.create_publisher(MarkerArray, self._marker_topic, 1)

        self._action_server = ActionServer(
            self, ExploreArea, '/explore_area',
            execute_callback=self._execute,
            goal_callback=self._goal_cb,
            cancel_callback=self._cancel_cb,
            callback_group=self._cb)

        self.get_logger().info(
            f"explore_node bereit. Map='{self._map_topic}', Nav='{self._nav_action_name}'. "
            f"Erkundung starten via Action /explore_area.")
        self._publish_status('idle')

    # ======================= Karten-Eingang =============================
    def _on_map(self, msg: OccupancyGrid):
        self._map = msg
        self._map_received_at = time.monotonic()

    def _on_odom(self, msg: Odometry):
        q = msg.pose.pose.orientation
        values = (
            q.x, q.y, q.z, q.w,
            msg.twist.twist.angular.z,
        )
        if not all(math.isfinite(value) for value in values):
            with self._odom_lock:
                self._odom_yaw = None
                self._odom_angular_speed = None
                self._odom_received_at = None
            self._scan_cmd_pub.publish(Twist())
            return
        with self._odom_lock:
            self._odom_yaw = quaternion_yaw(q)
            self._odom_angular_speed = msg.twist.twist.angular.z
            self._odom_received_at = time.monotonic()

    def _odom_snapshot(self):
        with self._odom_lock:
            return (
                self._odom_yaw,
                self._odom_angular_speed,
                self._odom_received_at,
            )

    # ======================= Roboterpose via TF =========================
    def _robot_pose(self) -> Optional[Tuple[float, float, float]]:
        try:
            t = self._tf_buffer.lookup_transform(
                self._global_frame, self._robot_base_frame, rclpy.time.Time())
            return (
                t.transform.translation.x,
                t.transform.translation.y,
                quaternion_yaw(t.transform.rotation),
            )
        except Exception as exc:  # TransformException u.a.
            self.get_logger().warn(
                f"TF {self._global_frame}->{self._robot_base_frame} fehlt: {exc}",
                throttle_duration_sec=5.0)
            return None

    def _robot_xy(self) -> Optional[Tuple[float, float]]:
        pose = self._robot_pose()
        return None if pose is None else pose[:2]

    # ======================= Reale Flaechenabdeckung ===================
    def _record_coverage_pose(self, robot_xy: Optional[Tuple[float, float]]):
        """Store the measured map-frame path at a bounded spatial interval."""
        if robot_xy is None or not all(math.isfinite(value) for value in robot_xy):
            return
        if not self._coverage_path:
            self._coverage_path.append(robot_xy)
            return
        start_x, start_y = self._coverage_path[-1]
        distance = math.hypot(robot_xy[0] - start_x, robot_xy[1] - start_y)
        if distance < self._coverage_path_sample_m:
            return
        # A SLAM loop closure may move map->odom abruptly although the robot
        # did not drive the straight segment between both map poses. Keep the
        # new sample, but never paint such a transform jump as physical path.
        if distance > self._coverage_max_interpolation_gap_m:
            self._coverage_path.append(robot_xy)
            return
        steps = max(1, int(math.ceil(distance / self._coverage_path_sample_m)))
        for step in range(1, steps + 1):
            fraction = step / steps
            self._coverage_path.append((
                start_x + fraction * (robot_xy[0] - start_x),
                start_y + fraction * (robot_xy[1] - start_y),
            ))

    @staticmethod
    def _exclude_disk(
            mask: np.ndarray, row: int, col: int, radius_cells: int):
        row0 = max(0, row - radius_cells)
        row1 = min(mask.shape[0], row + radius_cells + 1)
        col0 = max(0, col - radius_cells)
        col1 = min(mask.shape[1], col + radius_cells + 1)
        yy, xx = np.ogrid[row0:row1, col0:col1]
        mask[row0:row1, col0:col1] |= (
            (yy - row) ** 2 + (xx - col) ** 2 <= radius_cells ** 2)

    def _coverage_plan(
            self, grid: OccupancyGrid, robot_xy: Tuple[float, float],
            required_goal: Optional[Tuple[float, float]] = None
            ) -> CoveragePlan:
        """Measure driven coverage and select a room-size-adaptive next goal."""
        info = grid.info
        if info.width <= 0 or info.height <= 0 or info.resolution <= 0.0:
            return CoveragePlan(0.0, 0.0, 0.0, None)
        data = np.asarray(grid.data, dtype=np.int16).reshape(
            (info.height, info.width))
        robot_col, robot_row = self._world_to_grid(
            robot_xy[0], robot_xy[1], info)

        free = data == 0
        free_seed = nearest_mask_cell(
            free, robot_row, robot_col,
            max(1, int(math.ceil(0.25 / info.resolution))))
        if free_seed is None:
            return CoveragePlan(0.0, 0.0, 0.0, None)
        same_free_space = connected_mask(free, free_seed)

        clearance_cells = int(math.ceil(
            self._coverage_clearance_m / info.resolution))
        safe = circular_clearance_mask(
            data, clearance_cells) & same_free_space
        safe_seed = nearest_mask_cell(
            safe, robot_row, robot_col,
            max(1, int(math.ceil(
                (self._coverage_clearance_m + 0.25) / info.resolution))))
        if safe_seed is None:
            return CoveragePlan(0.0, 0.0, 0.0, None)
        reachable = connected_mask(safe, safe_seed)
        reachable_cells = int(np.count_nonzero(reachable))
        if reachable_cells == 0:
            return CoveragePlan(0.0, 0.0, 0.0, None)

        path_cells = []
        for path_x, path_y in self._coverage_path:
            path_col, path_row = self._world_to_grid(path_x, path_y, info)
            if 0 <= path_row < info.height and 0 <= path_col < info.width:
                path_cells.append((path_row, path_col))
        if not path_cells:
            path_cells.append((robot_row, robot_col))
        covered = stamp_coverage(
            data.shape, path_cells,
            int(math.ceil(self._coverage_visit_radius_m / info.resolution)))
        covered_reachable = covered & reachable
        covered_cells = int(np.count_nonzero(covered_reachable))
        cell_area = info.resolution ** 2
        ratio = covered_cells / reachable_cells

        if required_goal is not None:
            goal_col, goal_row = self._world_to_grid(
                required_goal[0], required_goal[1], info)
            goal_cell = None
            if (
                    0 <= goal_row < info.height
                    and 0 <= goal_col < info.width
                    and reachable[goal_row, goal_col]
                    and not self._is_blacklisted(
                        required_goal[0], required_goal[1])):
                goal_cell = (goal_row, goal_col)
            return CoveragePlan(
                ratio, reachable_cells * cell_area,
                covered_cells * cell_area, goal_cell)

        excluded = np.zeros_like(reachable, dtype=bool)
        self._exclude_disk(
            excluded, robot_row, robot_col,
            int(math.ceil(
                self._coverage_min_goal_distance_m / info.resolution)))
        for blacklist_x, blacklist_y in self._blacklist:
            blacklist_col, blacklist_row = self._world_to_grid(
                blacklist_x, blacklist_y, info)
            if (
                    0 <= blacklist_row < info.height
                    and 0 <= blacklist_col < info.width):
                self._exclude_disk(
                    excluded, blacklist_row, blacklist_col,
                    int(math.ceil(
                        self._blacklist_radius / info.resolution)))
        goal_cell = farthest_uncovered_cell(
            reachable, covered_reachable, excluded)
        return CoveragePlan(
            ratio, reachable_cells * cell_area,
            covered_cells * cell_area, goal_cell)

    def _apply_coverage_plan(self, plan: CoveragePlan):
        self._coverage_ratio = min(1.0, max(0.0, plan.ratio))
        self._reachable_area_m2 = max(0.0, plan.reachable_area_m2)
        self._covered_area_m2 = max(0.0, plan.covered_area_m2)

    def _publish_status(self, state: str):
        self._status_state = state
        payload = {
            'schema_version': 1,
            'backend_ready': True,
            'state': state,
            'phase': self._status_phase,
            'message': self._status_message,
            'strategy': 'frontier_then_adaptive_coverage',
            'coverage_ratio': self._coverage_ratio,
            'coverage_percent': 100.0 * self._coverage_ratio,
            'target_coverage_percent': 100.0 * self._coverage_target_ratio,
            'reachable_area_m2': self._reachable_area_m2,
            'covered_area_m2': self._covered_area_m2,
            'frontiers_visited': self._frontiers_visited_status,
            'coverage_goals_visited': self._coverage_goals_visited,
            'frontiers_remaining': self._frontiers_remaining,
            'map_ready_to_save': (
                state == 'success' and self._coverage_complete),
            'time': time.time(),
        }
        self._status_pub.publish(String(data=json.dumps(
            payload, ensure_ascii=False, separators=(',', ':'))))

    def _publish_current_status(self):
        self._publish_status(self._status_state)

    # ======================= Frontier-Erkennung =========================
    def _detect_frontiers(self, grid: OccupancyGrid, min_frontier_m: float) -> List[Frontier]:
        """Findet und clustert Frontier-Zellen in der OccupancyGrid.

        Belegung:  -1 = unbekannt, 0 = frei, 100 = belegt.
        Frontier-Zelle = FREI und hat mindestens einen UNBEKANNTEN 4-Nachbarn.
        """
        info = grid.info
        w, h, res = info.width, info.height, info.resolution
        if w == 0 or h == 0 or res <= 0.0:
            return []

        data = np.asarray(grid.data, dtype=np.int16).reshape((h, w))
        free = (data == 0)
        unknown = (data < 0)

        # Unbekannte Nachbarschaft per Array-Verschiebung (schnell, ohne Schleife).
        adj = np.zeros((h, w), dtype=bool)
        adj[1:, :]  |= unknown[:-1, :]   # Nachbar oben unbekannt
        adj[:-1, :] |= unknown[1:, :]    # Nachbar unten unbekannt
        adj[:, 1:]  |= unknown[:, :-1]   # Nachbar links unbekannt
        adj[:, :-1] |= unknown[:, 1:]    # Nachbar rechts unbekannt
        frontier_mask = free & adj

        # Mindestgroesse in Zellen (min_frontier_m als grobe Ausdehnung interpretiert).
        min_cells = max(1, int(round(min_frontier_m / res)))

        # Zusammenhaengende Frontier-Regionen (8-Nachbarschaft) per BFS clustern.
        visited = np.zeros((h, w), dtype=bool)
        ys, xs = np.nonzero(frontier_mask)
        frontiers: List[Frontier] = []
        for sy, sx in zip(ys.tolist(), xs.tolist()):
            if visited[sy, sx]:
                continue
            q = deque([(sy, sx)])
            visited[sy, sx] = True
            comp: List[Tuple[int, int]] = []
            while q:
                cy, cx = q.popleft()
                comp.append((cy, cx))
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        if dy == 0 and dx == 0:
                            continue
                        ny, nx = cy + dy, cx + dx
                        if 0 <= ny < h and 0 <= nx < w and frontier_mask[ny, nx] and not visited[ny, nx]:
                            visited[ny, nx] = True
                            q.append((ny, nx))
            if len(comp) < min_cells:
                continue   # zu kleine Frontier ignorieren (Rauschen)
            mean_row = sum(c[0] for c in comp) / len(comp)
            mean_col = sum(c[1] for c in comp) / len(comp)
            wx, wy = self._grid_to_world(mean_col, mean_row, info)
            frontiers.append(Frontier((wx, wy), len(comp)))
        return frontiers

    @staticmethod
    def _grid_to_world(col: float, row: float, info) -> Tuple[float, float]:
        q = info.origin.orientation
        yaw = math.atan2(
            2.0 * (q.w * q.z + q.x * q.y),
            1.0 - 2.0 * (q.y * q.y + q.z * q.z))
        lx = (col + 0.5) * info.resolution
        ly = (row + 0.5) * info.resolution
        c, s = math.cos(yaw), math.sin(yaw)
        wx = info.origin.position.x + c * lx - s * ly
        wy = info.origin.position.y + s * lx + c * ly
        return wx, wy

    @staticmethod
    def _world_to_grid(x: float, y: float, info) -> Tuple[int, int]:
        q = info.origin.orientation
        yaw = math.atan2(
            2.0 * (q.w * q.z + q.x * q.y),
            1.0 - 2.0 * (q.y * q.y + q.z * q.z))
        dx = x - info.origin.position.x
        dy = y - info.origin.position.y
        c, s = math.cos(yaw), math.sin(yaw)
        lx = c * dx + s * dy
        ly = -s * dx + c * dy
        return int(math.floor(lx / info.resolution)), int(math.floor(ly / info.resolution))

    def _frontier_approach_goal(
            self, frontier: Frontier, robot_xy: Tuple[float, float],
            grid: OccupancyGrid) -> Optional[Tuple[float, float]]:
        """Pick a known-free goal safely inside the frontier boundary."""
        dx = robot_xy[0] - frontier.cx
        dy = robot_xy[1] - frontier.cy
        norm = math.hypot(dx, dy)
        if norm <= 1e-9:
            return None
        desired_x = frontier.cx + self._approach_dist_m * dx / norm
        desired_y = frontier.cy + self._approach_dist_m * dy / norm
        info = grid.info
        data = np.asarray(grid.data, dtype=np.int16).reshape(
            (info.height, info.width))
        center_col, center_row = self._world_to_grid(desired_x, desired_y, info)
        search_cells = int(math.ceil(self._goal_search_m / info.resolution))
        clearance_cells = int(math.ceil(
            self._goal_clearance_m / info.resolution))
        safe_goal_cells = circular_clearance_mask(data, clearance_cells)
        choices = []
        for row in range(center_row - search_cells, center_row + search_cells + 1):
            for col in range(center_col - search_cells, center_col + search_cells + 1):
                if not (0 <= row < info.height and 0 <= col < info.width):
                    continue
                if not safe_goal_cells[row, col]:
                    continue
                wx, wy = self._grid_to_world(col, row, info)
                choices.append((math.hypot(wx - desired_x, wy - desired_y), wx, wy))
        if not choices:
            return None
        _, goal_x, goal_y = min(choices)
        return goal_x, goal_y

    # ======================= Bewertung / Auswahl ========================
    def _rank_frontiers(
            self, frontiers: List[Frontier], robot_xy: Tuple[float, float],
            grid: OccupancyGrid, robot_yaw: Optional[float] = None
            ) -> List[Frontier]:
        rx, ry = robot_xy
        res = grid.info.resolution
        candidates: List[Frontier] = []
        for f in frontiers:
            approach = self._frontier_approach_goal(f, robot_xy, grid)
            if approach is None:
                continue
            f.goal_x, f.goal_y = approach
            dist = math.hypot(f.goal_x - rx, f.goal_y - ry)
            if dist < self._min_goal_dist_m:
                continue   # zu nah (quasi schon erreicht)
            if self._is_visited_frontier_goal(f.goal_x, f.goal_y):
                continue   # dieses lokale Frontier-Umfeld wurde schon bedient
            if self._is_blacklisted(f.cx, f.cy):
                continue   # zuvor gescheitertes Ziel meiden
            # Kosten/Nutzen (Idee wie explore_lite):
            #   naeher  -> guenstiger (potential_scale * Distanz)
            #   groesser-> attraktiver (gain_scale * Frontier-Ausdehnung)
            f.cost = self._potential_scale * dist - self._gain_scale * (f.size * res)
            if robot_yaw is not None:
                goal_heading = math.atan2(f.goal_y - ry, f.goal_x - rx)
                f.cost += self._heading_scale * abs(normalize_angle(
                    goal_heading - robot_yaw))
            candidates.append(f)
        candidates.sort(key=lambda fr: fr.cost)   # kleinste Kosten zuerst
        return candidates

    def _is_blacklisted(self, x: float, y: float) -> bool:
        for bx, by in self._blacklist:
            if math.hypot(x - bx, y - by) < self._blacklist_radius:
                return True
        return False

    def _is_visited_frontier_goal(self, x: float, y: float) -> bool:
        """Reject a local frontier neighborhood already served successfully.

        A still-visible frontier can otherwise remain just outside the
        explorer's minimum distance while Nav2 considers its approach pose
        reached. Re-submitting that pose creates an unbounded sequence of
        immediate successes without driven coverage.
        """
        for visited_x, visited_y in getattr(
                self, '_visited_frontier_goals', []):
            if math.hypot(x - visited_x, y - visited_y) < (
                    self._frontier_revisit_radius):
                return True
        return False

    @staticmethod
    def _progress_percent(grid: OccupancyGrid) -> float:
        data = np.asarray(grid.data, dtype=np.int16)
        known = int(np.count_nonzero(data >= 0))
        return 100.0 * known / max(1, data.size)

    # ======================= Nav2 anfahren ==============================
    def _navigate_to(
            self, x: float, y: float, timeout_s: float,
            stop_requested=lambda: False) -> str:
        """Sendet EIN Fahrziel an Nav2 und wartet (blockierend) auf das Ergebnis.

        Rueckgabe: 'success' | 'aborted' | 'rejected' | 'timeout'
        """
        if not self._nav_client.wait_for_server(timeout_sec=5.0):
            self.get_logger().error("Nav2-Action 'navigate_to_pose' nicht erreichbar")
            return 'rejected'

        ps = PoseStamped()
        ps.header.frame_id = self._global_frame
        ps.header.stamp = self.get_clock().now().to_msg()
        ps.pose.position.x = x
        ps.pose.position.y = y
        rxy = self._robot_xy()
        yaw = math.atan2(y - rxy[1], x - rxy[0]) if rxy else 0.0   # zum Ziel blicken
        ps.pose.orientation.z = math.sin(yaw / 2.0)
        ps.pose.orientation.w = math.cos(yaw / 2.0)

        goal = NavigateToPose.Goal()
        goal.pose = ps
        goal.behavior_tree = self._behavior_tree

        done = threading.Event()
        holder = {'status': None, 'handle': None}

        def _on_result(fut):
            try:
                holder['status'] = fut.result().status
            except Exception:
                holder['status'] = 'error'
            done.set()

        def _on_goal(fut):
            try:
                gh = fut.result()
            except Exception:
                holder['status'] = 'error'
                done.set()
                return
            if not gh.accepted:
                holder['status'] = 'rejected'
                done.set()
                return
            holder['handle'] = gh
            gh.get_result_async().add_done_callback(_on_result)

        self._nav_client.send_goal_async(goal).add_done_callback(_on_goal)

        started = time.monotonic()
        last_path_sample_at = started
        stop_reason = None
        stop_reason_started = None
        cancel_started = None
        while rclpy.ok() and not done.wait(timeout=0.05):
            now = time.monotonic()
            if now - last_path_sample_at >= 0.25:
                self._record_coverage_pose(self._robot_xy())
                last_path_sample_at = now
            if stop_reason is None and stop_requested():
                stop_reason = 'canceled'
                stop_reason_started = now
            if (
                    stop_reason is None and timeout_s > 0.0
                and now - started >= timeout_s):
                stop_reason = 'timeout'
                stop_reason_started = now
            if (
                    stop_reason is not None and holder['handle'] is None
                    and now - stop_reason_started >= self._cancel_timeout_s):
                return 'cancel_failed'
            if stop_reason is not None and holder['handle'] is not None:
                if cancel_started is None:
                    holder['handle'].cancel_goal_async()
                    cancel_started = now
                elif now - cancel_started >= self._cancel_timeout_s:
                    return 'cancel_failed'

        if not done.is_set():
            return 'cancel_failed' if stop_reason is not None else 'aborted'
        self._record_coverage_pose(self._robot_xy())
        if stop_reason is not None:
            return stop_reason
        if holder['status'] == GoalStatus.STATUS_SUCCEEDED:
            return 'success'
        if holder['status'] == GoalStatus.STATUS_CANCELED:
            return 'canceled'
        if holder['status'] == 'rejected':
            return 'rejected'
        return 'aborted'

    # ======================= Initialer LiDAR-Rundblick =================
    def _publish_scan_stop(self):
        self._scan_cmd_pub.publish(Twist())

    def _stop_scan_and_confirm(self) -> str:
        """Command zero until encoder odometry confirms a stable stop."""
        deadline = time.monotonic() + self._scan_stop_timeout
        stable_since = None
        period = 1.0 / self._scan_command_rate
        while rclpy.ok() and time.monotonic() < deadline:
            self._publish_scan_stop()
            yaw, angular_speed, received_at = self._odom_snapshot()
            now = time.monotonic()
            if (
                    yaw is None or angular_speed is None or received_at is None
                    or not 0.0 <= now - received_at <= self._scan_odom_timeout):
                stable_since = None
            elif abs(angular_speed) <= self._scan_stop_tolerance:
                if stable_since is None:
                    stable_since = now
                elif now - stable_since >= 0.5:
                    return 'success'
            else:
                stable_since = None
            time.sleep(period)
        self._publish_scan_stop()
        return 'stop_unconfirmed'

    def _rotate_in_place(
            self, angle_rad: float, speed_radps: float, timeout_s: float,
            stop_requested=lambda: False, *,
            rate_check_after_s: Optional[float] = None,
            min_average_rate_radps: Optional[float] = None,
            ) -> Tuple[str, float]:
        """Rotate by a signed odometry angle with one constant setpoint."""
        target_angle = abs(angle_rad)
        if target_angle <= 1e-9:
            return 'success', 0.0
        rate_check_after = (
            self._scan_rate_check_after
            if rate_check_after_s is None else rate_check_after_s)
        min_average_rate = (
            self._scan_min_average_rate
            if min_average_rate_radps is None else min_average_rate_radps)
        direction = 1.0 if angle_rad > 0.0 else -1.0
        started = time.monotonic()
        period = 1.0 / self._scan_command_rate
        accumulator = None
        progress_checkpoint = 0.0
        progress_checkpoint_at = started
        status = 'aborted'

        try:
            while rclpy.ok():
                now = time.monotonic()
                if stop_requested():
                    status = 'interrupted'
                    break
                if now - started >= timeout_s:
                    status = 'timeout'
                    break

                yaw, _angular_speed, received_at = self._odom_snapshot()
                if (
                        yaw is None or received_at is None
                        or not 0.0 <= now - received_at <= self._scan_odom_timeout):
                    if now - started >= self._scan_odom_timeout:
                        status = 'odom_stale'
                        break
                    self._publish_scan_stop()
                    time.sleep(period)
                    continue

                if accumulator is None:
                    accumulator = RotationProgress(yaw, direction=direction)
                    progress_checkpoint_at = now
                else:
                    accumulator.update(yaw)

                if accumulator.reverse_progress > self._scan_reverse_limit:
                    status = 'wrong_direction'
                    break
                if (
                        accumulator.progress - progress_checkpoint
                        >= self._scan_progress_window):
                    progress_checkpoint = accumulator.progress
                    progress_checkpoint_at = now
                elif now - progress_checkpoint_at >= self._scan_no_progress_timeout:
                    status = 'no_progress'
                    break
                if (
                        now - started >= rate_check_after
                        and accumulator.progress / (now - started)
                        < min_average_rate):
                    status = 'too_slow'
                    break
                if accumulator.progress >= target_angle:
                    status = 'success'
                    break

                command = Twist()
                command.angular.z = direction * speed_radps
                self._scan_cmd_pub.publish(command)
                time.sleep(period)
        finally:
            self._publish_scan_stop()

        achieved = 0.0 if accumulator is None else accumulator.progress
        stop_status = self._stop_scan_and_confirm()
        if stop_status != 'success':
            return stop_status, achieved
        return status, achieved

    def _scan_in_place(self, stop_requested=lambda: False) -> Tuple[str, float]:
        """Perform one odometry-measured, bounded, counter-clockwise scan."""
        return self._rotate_in_place(
            self._initial_scan_angle,
            self._initial_scan_speed,
            self._initial_scan_timeout,
            stop_requested=stop_requested)

    def _prealign_to_goal(
            self, goal_x: float, goal_y: float,
            robot_pose: Tuple[float, float, float],
            stop_requested=lambda: False
            ) -> Tuple[str, float, float, float]:
        """Align in map, measuring each physical turn in odom.

        A large LiDAR turn may update ``map->odom``. Therefore an odometry-only
        success is not sufficient for handing the goal to Nav2: after every
        stopped turn the residual is measured again in the map frame. A
        non-improving correction fails closed instead of letting Nav2 hunt in
        yaw with the slow hardware ramp.
        """
        desired_heading = math.atan2(
            goal_y - robot_pose[1], goal_x - robot_pose[0])
        initial_error = normalize_angle(desired_heading - robot_pose[2])
        if not self._prealign_enabled:
            return 'skipped', 0.0, initial_error, initial_error

        current_error = initial_error
        total_achieved = 0.0
        for pass_number in range(1, self._prealign_max_passes + 1):
            if abs(current_error) <= self._prealign_handoff_tolerance:
                status = 'skipped' if pass_number == 1 else 'success'
                return status, total_achieved, initial_error, current_error

            commanded_angle = math.copysign(
                abs(current_error) - self._prealign_stop_margin,
                current_error)
            status, achieved = self._rotate_in_place(
                commanded_angle,
                self._prealign_speed,
                self._prealign_timeout,
                stop_requested=stop_requested,
                rate_check_after_s=self._prealign_rate_check_after,
                min_average_rate_radps=self._prealign_min_average_rate)
            total_achieved += achieved
            if status != 'success':
                return status, total_achieved, initial_error, current_error

            settle_deadline = time.monotonic() + self._prealign_settle_s
            while time.monotonic() < settle_deadline:
                if stop_requested():
                    return (
                        'interrupted', total_achieved,
                        initial_error, current_error)
                time.sleep(min(0.05, settle_deadline - time.monotonic()))

            measured_pose = self._robot_pose()
            if measured_pose is None:
                return (
                    'map_pose_missing', total_achieved,
                    initial_error, current_error)
            desired_heading = math.atan2(
                goal_y - measured_pose[1], goal_x - measured_pose[0])
            measured_error = normalize_angle(
                desired_heading - measured_pose[2])
            improvement = abs(current_error) - abs(measured_error)
            self.get_logger().info(
                f'Karten-Ausrichtung Durchgang {pass_number}/'
                f'{self._prealign_max_passes}: Restfehler '
                f'{math.degrees(measured_error):+.1f} Grad, Verbesserung '
                f'{math.degrees(improvement):.1f} Grad.')

            if abs(measured_error) <= self._prealign_handoff_tolerance:
                return (
                    'success', total_achieved,
                    initial_error, measured_error)
            if improvement < self._prealign_min_improvement:
                return (
                    'map_no_improvement', total_achieved,
                    initial_error, measured_error)
            current_error = measured_error

        return (
            'map_alignment_failed', total_achieved,
            initial_error, current_error)

    # ======================= Action-Server ==============================
    def _goal_cb(self, goal_request) -> GoalResponse:
        with self._active_goal_lock:
            if self._active_goal:
                self.get_logger().warn(
                    'Explorationsziel abgelehnt: bereits eine Erkundung aktiv.')
                return GoalResponse.REJECT
            self._active_goal = True
        return GoalResponse.ACCEPT

    def _cancel_cb(self, goal_handle) -> CancelResponse:
        return CancelResponse.ACCEPT

    def _execute(self, goal_handle):
        """Run one bounded exploration and own every child Nav2 goal."""
        try:
            result = self._execute_reserved(goal_handle)
            if goal_handle.is_cancel_requested or 'abgebrochen' in result.message:
                state = 'canceled'
                self._status_phase = 'canceled'
            elif result.success and self._coverage_complete:
                state = 'success'
                self._status_phase = 'complete'
            elif result.success:
                state = 'partial'
                self._status_phase = 'partial'
            else:
                state = 'failed'
                self._status_phase = 'failed'
            self._status_message = result.message
            self._publish_status(state)
            return result
        except Exception as exc:
            self._status_phase = 'failed'
            self._status_message = f'Interner Explorer-Fehler: {exc}'
            self._publish_status('failed')
            raise
        finally:
            with self._active_goal_lock:
                self._active_goal = False

    def _map_is_fresh(self) -> bool:
        return (
            self._map is not None
            and self._map_received_at is not None
            and 0.0 <= time.monotonic() - self._map_received_at <= self._map_timeout_s
        )

    def _finish_result(self, result, frontiers_visited):
        result.frontiers_visited = frontiers_visited
        if self._map is not None:
            data = np.asarray(self._map.data, dtype=np.int16)
            free_cells = int(np.count_nonzero(data == 0))
            result.explored_area_m2 = float(free_cells) * (
                self._map.info.resolution ** 2)
        return result

    @staticmethod
    def _classify_frontier_completion(frontiers_present, frontiers_visited):
        """Classify exhaustion without disguising a failed first departure."""
        if not frontiers_present:
            return (
                True,
                'Keine offenen Frontiers mehr - Raum vollstaendig erkundet',
                'complete')
        if frontiers_visited > 0:
            return (
                True,
                'Keine weiteren sicher erreichbaren Frontiers - Erkundung '
                'innerhalb des bekannten Freiraums sauber beendet',
                'safe_complete')
        return (
            False,
            'Frontiers vorhanden, aber kein Ziel mit sicherem Abstand im '
            'bekannten Freiraum erreichbar',
            None)

    def _execute_reserved(self, goal_handle):
        req = goal_handle.request
        overall_timeout = (
            req.timeout_s if req.timeout_s > 0 else self._overall_timeout_s)
        min_frontier_m = (
            req.min_frontier_size_m
            if req.min_frontier_size_m > 0 else self._min_frontier_m)
        return_to_start = req.return_to_start or self._return_to_start_p

        self._blacklist.clear()
        self._visited_frontier_goals.clear()
        self._start_xy = None
        self._coverage_path.clear()
        self._coverage_ratio = 0.0
        self._reachable_area_m2 = 0.0
        self._covered_area_m2 = 0.0
        self._coverage_goals_visited = 0
        self._frontiers_visited_status = 0
        self._frontiers_remaining = 0
        self._coverage_complete = False
        self._status_phase = 'waiting_for_map'
        self._status_message = 'Erkundung gestartet; warte auf SLAM-Karte und Pose.'
        self._publish_status('running')
        frontiers_visited = 0
        failed_goals = 0
        initial_scan_done = not self._initial_scan_enabled
        t_start = time.monotonic()
        result = ExploreArea.Result()
        completion_reason = None

        self.get_logger().info(
            f'Exploration gestartet; Gesamtlimit {overall_timeout:.0f} s.')

        def overall_expired():
            return (
                overall_timeout > 0.0
                and time.monotonic() - t_start >= overall_timeout)

        while rclpy.ok():
            if goal_handle.is_cancel_requested:
                goal_handle.canceled()
                result.success = False
                result.message = 'Erkundung abgebrochen; Nav2-Kindziel beendet'
                self.get_logger().info(result.message)
                return self._finish_result(result, frontiers_visited)

            if overall_expired():
                goal_handle.abort()
                result.success = False
                result.message = (
                    'Zeitlimit erreicht; Zielabdeckung nicht bestaetigt '
                    f'({100.0 * self._coverage_ratio:.0f} %)')
                return self._finish_result(result, frontiers_visited)

            # slam_toolbox publiziert eine unveraenderte Karte im Stillstand
            # nicht periodisch. Der initiale Rundblick darf daher mit einer
            # bereits empfangenen, aber alten Karte bootstrappen. Vor jeder
            # Translation bleibt Kartenfrische zwingend.
            map_ready = self._map is not None and (
                not initial_scan_done or self._map_is_fresh())
            if not map_ready:
                if time.monotonic() - t_start > self._map_timeout_s:
                    goal_handle.abort()
                    result.success = False
                    result.message = 'SLAM-Karte fehlt oder ist veraltet'
                    return self._finish_result(result, frontiers_visited)
                time.sleep(0.1)
                continue

            grid = self._map
            if grid.header.frame_id not in ('', self._global_frame):
                goal_handle.abort()
                result.success = False
                result.message = (
                    f'Kartenframe {grid.header.frame_id!r} passt nicht zu '
                    f'{self._global_frame!r}')
                return self._finish_result(result, frontiers_visited)

            robot_pose = self._robot_pose()
            if robot_pose is None:
                if time.monotonic() - t_start > self._map_timeout_s:
                    goal_handle.abort()
                    result.success = False
                    result.message = 'Roboterpose im Kartenframe fehlt'
                    return self._finish_result(result, frontiers_visited)
                time.sleep(0.1)
                continue
            robot_xy = robot_pose[:2]
            if self._start_xy is None:
                self._start_xy = robot_xy
            self._record_coverage_pose(robot_xy)

            if not initial_scan_done:
                self._status_phase = 'initial_scan'
                self._status_message = (
                    'Kontrollierter 360-Grad-LiDAR-Rundblick läuft.')
                self._publish_status('running')
                self.get_logger().info(
                    'Phase 1/3: kontrollierter 360-Grad-LiDAR-Rundblick.')
                scan_status, achieved = self._scan_in_place(
                    stop_requested=lambda: (
                        goal_handle.is_cancel_requested
                        or overall_expired()
                        or self._map is None))
                if scan_status != 'success':
                    if goal_handle.is_cancel_requested:
                        goal_handle.canceled()
                        result.message = '360-Grad-Rundblick abgebrochen'
                    elif overall_expired():
                        goal_handle.abort()
                        result.success = False
                        result.message = (
                            'Zeitlimit waehrend des Rundblicks erreicht; '
                            'Roboter bestaetigt gestoppt, Karte unvollstaendig')
                    else:
                        goal_handle.abort()
                        result.message = (
                            f'360-Grad-Rundblick fehlgeschlagen: {scan_status}; '
                            f'erreicht {math.degrees(achieved):.1f} Grad')
                    return self._finish_result(result, frontiers_visited)
                initial_scan_done = True
                self.get_logger().info(
                    f'Rundblick vollstaendig: {math.degrees(achieved):.1f} Grad; '
                    'Phase 2/3 startet mit frischer Frontier-Neuplanung.')
                time.sleep(self._replan_period_s)
                continue

            frontiers = self._detect_frontiers(grid, min_frontier_m)
            if self._visualize:
                self._publish_markers(frontiers, grid.header.frame_id)
            candidates = self._rank_frontiers(
                frontiers, robot_xy, grid, robot_yaw=robot_pose[2])
            coverage_plan = self._coverage_plan(grid, robot_xy)
            self._apply_coverage_plan(coverage_plan)
            self._frontiers_remaining = len(candidates)
            self._frontiers_visited_status = frontiers_visited

            coverage_goal = False
            if candidates:
                if frontiers_visited >= self._max_frontier_goals:
                    goal_handle.abort()
                    result.success = False
                    result.message = (
                        'Frontier-Limit ohne Abschluss erreicht '
                        f'({frontiers_visited}/{self._max_frontier_goals}); '
                        'Wiederholungs- oder Kartenfortschritt pruefen')
                    return self._finish_result(result, frontiers_visited)
                best = candidates[0]
                self._status_phase = 'frontier'
                self._status_message = (
                    f'Kartengrenze {frontiers_visited + 1} wird angefahren; '
                    f'{len(candidates)} sichere Kandidaten offen.')
            elif not self._coverage_enabled:
                success, message, reason = self._classify_frontier_completion(
                    bool(frontiers), frontiers_visited)
                result.success = success
                result.message = message
                if not success:
                    goal_handle.abort()
                    return self._finish_result(result, frontiers_visited)
                completion_reason = reason
                self._coverage_complete = success
                break
            elif self._coverage_ratio >= self._coverage_target_ratio:
                self._coverage_complete = True
                result.success = True
                result.message = (
                    'Adaptive Raumerkundung abgeschlossen: '
                    f'{100.0 * self._coverage_ratio:.0f} % der sicher '
                    'befahrbaren Flaeche wurden durch die reale Fahrspur '
                    'abgedeckt')
                completion_reason = 'coverage_complete'
                break
            elif self._coverage_goals_visited >= self._coverage_max_goals:
                goal_handle.abort()
                result.success = False
                result.message = (
                    f'Abdeckungsziel nach {self._coverage_max_goals} '
                    f'Flaechenzielen nicht erreicht '
                    f'({100.0 * self._coverage_ratio:.0f} %)')
                return self._finish_result(result, frontiers_visited)
            elif coverage_plan.goal_cell is None:
                goal_handle.abort()
                result.success = False
                result.message = (
                    'Keine weitere sichere Abdeckungsfahrt moeglich; '
                    f'Ziel {100.0 * self._coverage_target_ratio:.0f} %, '
                    f'erreicht {100.0 * self._coverage_ratio:.0f} %')
                return self._finish_result(result, frontiers_visited)
            else:
                goal_row, goal_col = coverage_plan.goal_cell
                goal_x, goal_y = self._grid_to_world(
                    goal_col, goal_row, grid.info)
                best = Frontier((goal_x, goal_y), 0)
                best.goal_x, best.goal_y = goal_x, goal_y
                coverage_goal = True
                self._status_phase = 'coverage'
                self._status_message = (
                    f'Phase 3/3: Abdeckungsziel '
                    f'{self._coverage_goals_visited + 1} wird angefahren; '
                    f'{100.0 * self._coverage_ratio:.0f} % von '
                    f'{100.0 * self._coverage_target_ratio:.0f} % erreicht.')

            goal_label = 'Abdeckungsziel' if coverage_goal else 'Frontier'
            self._publish_status('running')
            fb = ExploreArea.Feedback()
            fb.explored_percent = 100.0 * self._coverage_ratio
            fb.frontiers_remaining = len(candidates)
            goal_pose = PoseStamped()
            goal_pose.header.frame_id = self._global_frame
            goal_pose.header.stamp = self.get_clock().now().to_msg()
            goal_pose.pose.position.x = best.goal_x
            goal_pose.pose.position.y = best.goal_y
            goal_pose.pose.orientation.w = 1.0
            fb.current_goal = goal_pose
            goal_handle.publish_feedback(fb)

            turn_status, turned, heading_error, residual_error = (
                self._prealign_to_goal(
                best.goal_x, best.goal_y, robot_pose,
                stop_requested=lambda: (
                    goal_handle.is_cancel_requested
                    or overall_expired()
                    or self._map is None)))
            self.get_logger().info(
                f'{goal_label}-Vorausrichtung: Soll '
                f'{math.degrees(heading_error):+.1f} Grad, erreicht '
                f'{math.degrees(turned):.1f} Grad, Karten-Restfehler '
                f'{math.degrees(residual_error):+.1f} Grad, '
                f'Status={turn_status}.')
            if turn_status not in ('success', 'skipped'):
                if goal_handle.is_cancel_requested:
                    goal_handle.canceled()
                    result.success = False
                    result.message = 'Erkundung waehrend Vorausrichtung abgebrochen'
                    return self._finish_result(result, frontiers_visited)
                if overall_expired():
                    goal_handle.abort()
                    result.success = False
                    result.message = (
                        'Zeitlimit waehrend Vorausrichtung erreicht; '
                        'Roboter bestaetigt gestoppt, Karte unvollstaendig')
                    return self._finish_result(result, frontiers_visited)
                if turn_status in (
                        'odom_stale', 'wrong_direction', 'stop_unconfirmed',
                        'interrupted', 'map_pose_missing',
                        'map_no_improvement', 'map_alignment_failed'):
                    goal_handle.abort()
                    result.success = False
                    result.message = (
                        f'Sichere {goal_label}-Vorausrichtung fehlgeschlagen: '
                        f'{turn_status}')
                    return self._finish_result(result, frontiers_visited)
                self._blacklist.append((best.cx, best.cy))
                failed_goals += 1
                self.get_logger().warn(
                    f'{goal_label} wegen Vorausrichtung {turn_status} gesperrt; '
                    f'Fehlversuch {failed_goals}/{self._max_failed_goals}')
                if failed_goals >= self._max_failed_goals:
                    goal_handle.abort()
                    result.success = False
                    result.message = 'Zu viele nicht ausrichtbare Erkundungsziele'
                    return self._finish_result(result, frontiers_visited)
                continue

            # Die Vorausrichtung kann map->odom und den sicheren Anfahrpunkt
            # verschieben. Deshalb wird das Ziel immer neu aus der aktuellen
            # Karte berechnet und anschliessend nochmals im Kartenframe
            # ausgerichtet. Erst danach darf Nav2 eine Translation erhalten.
            refreshed_pose = self._robot_pose()
            refreshed_grid = self._map
            refreshed_goal = None
            if (refreshed_pose is not None and refreshed_grid is not None
                    and self._map_is_fresh()):
                if coverage_goal:
                    refreshed_plan = self._coverage_plan(
                        refreshed_grid, refreshed_pose[:2],
                        required_goal=(best.goal_x, best.goal_y))
                    self._apply_coverage_plan(refreshed_plan)
                    if refreshed_plan.goal_cell is not None:
                        refreshed_goal = (best.goal_x, best.goal_y)
                else:
                    refreshed_goal = self._frontier_approach_goal(
                        best, refreshed_pose[:2], refreshed_grid)
            if refreshed_goal is None:
                self._blacklist.append((best.cx, best.cy))
                failed_goals += 1
                self.get_logger().warn(
                    f'{goal_label} nach Vorausrichtung nicht mehr sicher; '
                    f'Fehlversuch {failed_goals}/{self._max_failed_goals}')
                if failed_goals >= self._max_failed_goals:
                    goal_handle.abort()
                    result.success = False
                    result.message = 'Zu viele nach Messung unsichere Erkundungsziele'
                    return self._finish_result(result, frontiers_visited)
                continue
            best.goal_x, best.goal_y = refreshed_goal

            verify_status, verify_turned, verify_error, verify_residual = (
                self._prealign_to_goal(
                    best.goal_x, best.goal_y, refreshed_pose,
                    stop_requested=lambda: (
                        goal_handle.is_cancel_requested
                        or overall_expired()
                        or self._map is None)))
            self.get_logger().info(
                f'Karten-Uebergabepruefung: Soll '
                f'{math.degrees(verify_error):+.1f} Grad, erreicht '
                f'{math.degrees(verify_turned):.1f} Grad, Restfehler '
                f'{math.degrees(verify_residual):+.1f} Grad, '
                f'Status={verify_status}.')
            if verify_status not in ('success', 'skipped'):
                if goal_handle.is_cancel_requested:
                    goal_handle.canceled()
                    result.success = False
                    result.message = (
                        'Erkundung waehrend Karten-Uebergabe abgebrochen')
                    return self._finish_result(result, frontiers_visited)
                if overall_expired():
                    goal_handle.abort()
                    result.success = False
                    result.message = (
                        'Zeitlimit waehrend Karten-Uebergabe erreicht; '
                        'Roboter bestaetigt gestoppt, Karte unvollstaendig')
                    return self._finish_result(result, frontiers_visited)
                if verify_status in (
                        'odom_stale', 'wrong_direction', 'stop_unconfirmed',
                        'interrupted', 'map_pose_missing',
                        'map_no_improvement', 'map_alignment_failed'):
                    goal_handle.abort()
                    result.success = False
                    result.message = (
                        'Sichere Karten-Uebergabe an Nav2 fehlgeschlagen: '
                        f'{verify_status}')
                    return self._finish_result(result, frontiers_visited)
                self._blacklist.append((best.cx, best.cy))
                failed_goals += 1
                self.get_logger().warn(
                    f'Frontier wegen Karten-Uebergabe {verify_status} '
                    f'gesperrt; Fehlversuch '
                    f'{failed_goals}/{self._max_failed_goals}')
                if failed_goals >= self._max_failed_goals:
                    goal_handle.abort()
                    result.success = False
                    result.message = 'Zu viele nicht ausrichtbare Erkundungsziele'
                    return self._finish_result(result, frontiers_visited)
                continue

            self.get_logger().info(
                f'Fahre zu sicherem {goal_label}; '
                f'Frontier-Groesse={best.size}, offen={len(candidates)}, '
                f'Abdeckung={100.0 * self._coverage_ratio:.1f} %')
            status = self._navigate_to(
                best.goal_x, best.goal_y, self._goal_timeout_s,
                stop_requested=lambda: (
                    goal_handle.is_cancel_requested
                    or overall_expired()
                    or not self._map_is_fresh()))

            if status == 'success':
                if coverage_goal:
                    self._coverage_goals_visited += 1
                else:
                    self._visited_frontier_goals.append(
                        (best.goal_x, best.goal_y))
                    frontiers_visited += 1
                    self._frontiers_visited_status = frontiers_visited
                time.sleep(self._replan_period_s)
                continue

            if status == 'canceled':
                if goal_handle.is_cancel_requested:
                    goal_handle.canceled()
                    result.success = False
                    result.message = 'Erkundung und Nav2-Kindziel abgebrochen'
                elif overall_expired():
                    result.success = False
                    result.message = (
                        'Zeitlimit erreicht; Zielabdeckung nicht bestaetigt '
                        f'({100.0 * self._coverage_ratio:.0f} %)')
                    goal_handle.abort()
                else:
                    goal_handle.abort()
                    result.success = False
                    result.message = 'SLAM-Karte waehrend der Fahrt veraltet'
                return self._finish_result(result, frontiers_visited)

            if status == 'cancel_failed':
                goal_handle.abort()
                result.success = False
                result.message = (
                    'Nav2-Kindziel konnte nicht bestaetigt beendet werden; '
                    'Fahrtor muss blockiert bleiben')
                return self._finish_result(result, frontiers_visited)

            self._blacklist.append((best.cx, best.cy))
            failed_goals += 1
            self.get_logger().warn(
                f'{goal_label} {status}; Fehlversuch '
                f'{failed_goals}/{self._max_failed_goals}')
            if failed_goals >= self._max_failed_goals:
                goal_handle.abort()
                result.success = False
                result.message = 'Zu viele nicht erreichbare Erkundungsziele'
                return self._finish_result(result, frontiers_visited)

        if return_to_start and self._start_xy is not None:
            self.get_logger().info('Kehre zur Startpose zurueck ...')
            status = self._navigate_to(
                self._start_xy[0], self._start_xy[1], self._goal_timeout_s,
                stop_requested=lambda: goal_handle.is_cancel_requested)
            if status != 'success':
                goal_handle.abort()
                result.success = False
                result.message = f'Rueckkehr zur Startpose fehlgeschlagen: {status}'
                return self._finish_result(result, frontiers_visited)

        if completion_reason in {
                'coverage_complete', 'complete', 'safe_complete'}:
            goal_handle.succeed()
        self.get_logger().info(f'Exploration beendet: {result.message}')
        return self._finish_result(result, frontiers_visited)

    # ======================= Visualisierung =============================
    def _publish_markers(self, frontiers: List[Frontier], frame_id: str):
        arr = MarkerArray()
        m = Marker()
        m.header.frame_id = frame_id or self._global_frame
        m.header.stamp = self.get_clock().now().to_msg()
        m.ns = 'frontiers'
        m.id = 0
        m.type = Marker.POINTS
        m.action = Marker.ADD
        m.scale.x = 0.08
        m.scale.y = 0.08
        m.color.r = 0.0
        m.color.g = 0.8
        m.color.b = 1.0
        m.color.a = 1.0
        for f in frontiers:
            p = Point()
            p.x, p.y, p.z = f.cx, f.cy, 0.05
            m.points.append(p)
        arr.markers.append(m)
        self._marker_pub.publish(arr)


def main(args=None):
    rclpy.init(args=args)
    node = ExploreNode()
    # MultiThreadedExecutor: erlaubt, dass der blockierende Explore-Loop
    # laeuft, waehrend Map-Callbacks und Nav-Ergebnisse parallel eintreffen.
    executor = MultiThreadedExecutor()
    executor.add_node(node)
    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
