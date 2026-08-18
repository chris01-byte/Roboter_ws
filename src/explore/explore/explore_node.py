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
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import List, Optional, Tuple

import numpy as np

import rclpy
from rclpy.node import Node
from rclpy.action import ActionServer, ActionClient, CancelResponse, GoalResponse
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from rclpy.qos import (
    DurabilityPolicy, QoSProfile, ReliabilityPolicy,
    qos_profile_sensor_data,
)

from nav_msgs.msg import OccupancyGrid, Odometry
from geometry_msgs.msg import PoseStamped, Point, Twist
from sensor_msgs.msg import LaserScan
from std_msgs.msg import String
from visualization_msgs.msg import Marker, MarkerArray
from action_msgs.msg import GoalStatus
from nav2_msgs.action import NavigateToPose
from robot_interfaces.action import ExploreArea

from explore.lidar_motion import (
    LidarReferenceMatcher,
    motion_estimate_is_reliable,
    scan_points_in_base,
)
from explore.portal_planning import (
    CorridorCheck,
    PortalBridge,
    find_portal_bridges,
    front_lidar_corridor_check,
)

import tf2_ros


@dataclass
class CoveragePlan:
    """Momentaufnahme der sicher befahrbaren, real abgefahrenen Flaeche."""

    ratio: float
    reachable_area_m2: float
    covered_area_m2: float
    goal_cell: Optional[Tuple[int, int]]


@dataclass(frozen=True)
class PortalPlan:
    """Costmap bridge converted to stable map-frame coordinates."""

    bridge: PortalBridge
    staging_xy: Tuple[float, float]
    target_xy: Tuple[float, float]
    target_center_xy: Tuple[float, float]
    midpoint_xy: Tuple[float, float]


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


def grid_line_is_clear(
        mask: np.ndarray, start: Tuple[int, int],
        end: Tuple[int, int]) -> bool:
    """Return whether every Bresenham cell from ``start`` to ``end`` is true."""
    row0, col0 = start
    row1, col1 = end
    height, width = mask.shape
    dcol = abs(col1 - col0)
    drow = -abs(row1 - row0)
    step_col = 1 if col0 < col1 else -1
    step_row = 1 if row0 < row1 else -1
    error = dcol + drow
    while True:
        if not (
                0 <= row0 < height and 0 <= col0 < width
                and mask[row0, col0]):
            return False
        if row0 == row1 and col0 == col1:
            return True
        doubled_error = 2 * error
        if doubled_error >= drow:
            error += drow
            col0 += step_col
        if doubled_error <= dcol:
            error += dcol
            row0 += step_row


def odom_freshness_state(
        now: float, received_at: Optional[float], started_at: float,
        freshness_timeout_s: float, recovery_timeout_s: float,
        sample_valid: bool = True) -> str:
    """Classify encoder odometry as ``fresh``, ``pause`` or ``expired``.

    ``pause`` is deliberately distinct from ``fresh``: callers must command
    zero while waiting for a transient DDS/callback gap to recover. The larger
    recovery limit therefore never authorizes blind motion.
    """
    if not sample_valid or received_at is None:
        return (
            'pause'
            if 0.0 <= now - started_at <= recovery_timeout_s
            else 'expired')
    age = now - received_at
    if age < 0.0:
        return 'expired'
    if age <= freshness_timeout_s:
        return 'fresh'
    if age <= recovery_timeout_s:
        return 'pause'
    return 'expired'


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


def relative_planar_motion(
        start_xy: Tuple[float, float], start_yaw: float,
        current_xy: Tuple[float, float], current_yaw: float
        ) -> Tuple[float, float, float]:
    """Return forward, lateral and heading error in the start frame."""
    values = (*start_xy, start_yaw, *current_xy, current_yaw)
    if not all(math.isfinite(value) for value in values):
        raise ValueError('Odometriewerte muessen endlich sein')
    dx = current_xy[0] - start_xy[0]
    dy = current_xy[1] - start_xy[1]
    c = math.cos(start_yaw)
    s = math.sin(start_yaw)
    forward = c * dx + s * dy
    lateral = -s * dx + c * dy
    heading_error = normalize_angle(current_yaw - start_yaw)
    return forward, lateral, heading_error


def door_motion_consistency(
        localized_progress_m: float, encoder_progress_m: float,
        max_encoder_overrun_m: float, max_localization_lead_m: float) -> str:
    """Compare a map-frame estimate with wheel rotation conservatively.

    This comparison is only suitable when the map-frame estimate has an
    independent motion source.  slam_toolbox driven by the same wheel odometry
    is *not* independent on a slipping threshold and must use the explicitly
    supervised wheel-budget mode below instead.
    """
    values = (
        localized_progress_m, encoder_progress_m,
        max_encoder_overrun_m, max_localization_lead_m,
    )
    if (
            not all(math.isfinite(value) for value in values)
            or max_encoder_overrun_m <= 0.0
            or max_localization_lead_m <= 0.0):
        return 'invalid'
    if encoder_progress_m - localized_progress_m > max_encoder_overrun_m:
        return 'encoder_slip'
    if localized_progress_m - encoder_progress_m > max_localization_lead_m:
        return 'localization_jump'
    return 'consistent'


def bounded_heading_increment(
        previous_yaw_rad: float, current_yaw_rad: float,
        max_step_rad: float) -> Optional[float]:
    """Return a small heading increment, or ``None`` for a pose jump."""
    values = (previous_yaw_rad, current_yaw_rad, max_step_rad)
    if not all(math.isfinite(value) for value in values) or max_step_rad <= 0.0:
        raise ValueError('Tuer-Winkelfilter verlangt endliche positive Werte')
    increment = normalize_angle(current_yaw_rad - previous_yaw_rad)
    return increment if abs(increment) <= max_step_rad else None


def door_steering_command(
        heading_error_rad: float, lateral_error_m: float,
        heading_kp: float, lateral_kp: float,
        max_angular_speed_radps: float) -> float:
    """Return a bounded correction towards the LiDAR start centreline."""
    values = (
        heading_error_rad, lateral_error_m, heading_kp, lateral_kp,
        max_angular_speed_radps,
    )
    if not all(math.isfinite(value) for value in values):
        raise ValueError('Tuerregelwerte muessen endlich sein')
    if heading_kp <= 0.0 or lateral_kp < 0.0 or max_angular_speed_radps <= 0.0:
        raise ValueError('Tuerreglergrenzen muessen positiv sein')
    correction = -(
        heading_kp * heading_error_rad + lateral_kp * lateral_error_m)
    return max(
        -max_angular_speed_radps,
        min(max_angular_speed_radps, correction))


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
        self.goal_projected = False      # erreichbare Zwischenetappe vor Frontier
        self.forward_staging = False     # begrenzte direkte Etappe im Tuerprofil


class ExploreNode(Node):
    def __init__(self):
        super().__init__('explore_node')

        # -------------------------------------------------------------------
        #  Parameter (Defaults; per explore_params.yaml ueberschreibbar)
        # -------------------------------------------------------------------
        self._map_topic         = self.declare_parameter('map_topic', '/map').value
        self._global_costmap_topic = self.declare_parameter(
            'global_costmap_topic', '/global_costmap/costmap').value
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
        self._frontier_forward_cone_half_angle = float(self.declare_parameter(
            'frontier_forward_cone_half_angle_rad', 0.0).value)
        self._frontier_goal_max_cost = int(self.declare_parameter(
            'frontier_goal_max_cost', 90).value)
        self._frontier_forward_stage_max_distance = float(
            self.declare_parameter(
                'frontier_forward_stage_max_distance_m', 0.0).value)
        self._frontier_stage_min_progress_m = float(self.declare_parameter(
            'frontier_stage_min_progress_m', 0.30).value)
        self._min_goal_dist_m   = float(self.declare_parameter('min_goal_distance_m', 0.30).value)
        self._blacklist_radius  = float(self.declare_parameter('blacklist_radius_m', 0.35).value)
        self._frontier_revisit_radius = float(self.declare_parameter(
            'frontier_revisit_radius_m', 0.60).value)
        self._max_frontier_goals = int(self.declare_parameter(
            'max_frontier_goals', 20).value)
        self._approach_dist_m   = float(self.declare_parameter('frontier_approach_distance_m', 0.45).value)
        self._goal_clearance_m  = float(self.declare_parameter('goal_clearance_m', 0.28).value)
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
        self._scan_odom_recovery_timeout = float(self.declare_parameter(
            'scan_odom_recovery_timeout_s', 5.0).value)
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
        self._door_distance = float(self.declare_parameter(
            'door_traverse_distance_m', 0.0).value)
        self._door_supervised_wheel_budget_mode = bool(self.declare_parameter(
            'door_supervised_wheel_budget_mode', False).value)
        self._door_lidar_motion_mode = bool(self.declare_parameter(
            'door_lidar_motion_mode', False).value)
        self._door_encoder_wheel_budget = float(self.declare_parameter(
            'door_encoder_wheel_budget_m', 0.0).value)
        self._door_lidar_scan_topic = str(self.declare_parameter(
            'door_lidar_scan_topic', '/scan_normiert').value)
        self._door_lidar_scan_timeout = float(self.declare_parameter(
            'door_lidar_scan_timeout_s', 0.5).value)
        self._door_lidar_recovery_timeout = float(self.declare_parameter(
            'door_lidar_recovery_timeout_s', 2.0).value)
        self._door_lidar_max_range = float(self.declare_parameter(
            'door_lidar_max_range_m', 4.0).value)
        self._door_lidar_min_points = int(self.declare_parameter(
            'door_lidar_min_points', 400).value)
        self._door_lidar_max_cost = float(self.declare_parameter(
            'door_lidar_max_cost_m', 0.08).value)
        self._door_lidar_min_support = float(self.declare_parameter(
            'door_lidar_min_support_ratio', 0.45).value)
        self._door_lidar_min_distinct_gap = float(self.declare_parameter(
            'door_lidar_min_distinct_gap_m', 0.0005).value)
        self._door_lidar_max_step = float(self.declare_parameter(
            'door_lidar_max_step_m', 0.08).value)
        self._door_lidar_max_yaw_step = float(self.declare_parameter(
            'door_lidar_max_yaw_step_rad', 0.12).value)
        self._door_cmd_topic = str(self.declare_parameter(
            'door_command_topic', '/cmd_vel_explore_direct_raw').value)
        self._door_speed = float(self.declare_parameter(
            'door_linear_speed_mps', 0.08).value)
        self._door_heading_kp = float(self.declare_parameter(
            'door_heading_kp', 0.8).value)
        self._door_lateral_kp = float(self.declare_parameter(
            'door_lateral_kp', 0.8).value)
        self._door_max_angular = float(self.declare_parameter(
            'door_max_angular_speed_radps', 0.05).value)
        self._door_max_heading_error = float(self.declare_parameter(
            'door_max_heading_error_rad', 0.17).value)
        self._door_max_lateral_error = float(self.declare_parameter(
            'door_max_lateral_error_m', 0.08).value)
        self._door_timeout = float(self.declare_parameter(
            'door_timeout_s', 120.0).value)
        self._door_no_progress_timeout = float(self.declare_parameter(
            'door_no_progress_timeout_s', 12.0).value)
        self._door_progress_window = float(self.declare_parameter(
            'door_progress_window_m', 0.02).value)
        self._door_reverse_limit = float(self.declare_parameter(
            'door_reverse_limit_m', 0.03).value)
        self._door_stop_linear_tolerance = float(self.declare_parameter(
            'door_stop_linear_tolerance_mps', 0.01).value)
        self._door_pose_timeout = float(self.declare_parameter(
            'door_localization_timeout_s', 0.8).value)
        self._door_pose_recovery_timeout = float(self.declare_parameter(
            'door_localization_recovery_timeout_s', 3.0).value)
        self._door_max_encoder_overrun = float(self.declare_parameter(
            'door_max_encoder_overrun_m', 0.45).value)
        self._door_max_localization_lead = float(self.declare_parameter(
            'door_max_localization_lead_m', 0.15).value)
        self._door_max_localized_step = float(self.declare_parameter(
            'door_max_localized_step_m', 0.12).value)
        self._door_max_localized_yaw_step = float(self.declare_parameter(
            'door_max_localized_yaw_step_rad', 0.17).value)
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
        self._portal_enabled = bool(self.declare_parameter(
            'portal_crossing_enabled', True).value)
        self._portal_min_component_area = float(self.declare_parameter(
            'portal_min_component_area_m2', 0.40).value)
        self._portal_min_gap = float(self.declare_parameter(
            'portal_min_gap_m', 0.12).value)
        self._portal_max_gap = float(self.declare_parameter(
            'portal_max_gap_m', 0.80).value)
        self._portal_exit_margin = float(self.declare_parameter(
            'portal_exit_margin_m', 0.25).value)
        self._portal_max_traverse_distance = float(self.declare_parameter(
            'portal_max_traverse_distance_m', 1.00).value)
        self._portal_encoder_budget_factor = float(self.declare_parameter(
            'portal_encoder_budget_factor', 2.2).value)
        self._portal_encoder_budget_margin = float(self.declare_parameter(
            'portal_encoder_budget_margin_m', 0.20).value)
        self._portal_max_encoder_budget = float(self.declare_parameter(
            'portal_max_encoder_budget_m', 2.00).value)
        self._portal_corridor_half_width = float(self.declare_parameter(
            'portal_lidar_corridor_half_width_m', 0.25).value)
        self._portal_front_overhang = float(self.declare_parameter(
            'portal_front_overhang_m', 0.33).value)
        self._portal_lidar_min_far_points = int(self.declare_parameter(
            'portal_lidar_min_far_points', 12).value)
        self._portal_max_crossings = int(self.declare_parameter(
            'portal_max_crossings', 8).value)
        self._portal_stop_after_crossing = bool(self.declare_parameter(
            'portal_stop_after_crossing', False).value)
        self._portal_revisit_radius = float(self.declare_parameter(
            'portal_revisit_radius_m', 0.60).value)
        self._coverage_enabled = bool(self.declare_parameter(
            'coverage_enabled', True).value)
        self._coverage_target_ratio = float(self.declare_parameter(
            'coverage_target_ratio', 0.85).value)
        self._coverage_visit_radius_m = float(self.declare_parameter(
            'coverage_visit_radius_m', 0.65).value)
        self._coverage_clearance_m = float(self.declare_parameter(
            'coverage_clearance_m', 0.28).value)
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
        self._global_costmap: Optional[OccupancyGrid] = None
        self._global_costmap_received_at: Optional[float] = None
        self._blacklist: List[Tuple[float, float]] = []   # gescheiterte Ziele (Weltkoord.)
        self._visited_frontier_goals: List[Tuple[float, ...]] = []
        self._start_xy: Optional[Tuple[float, float]] = None
        self._active_goal = False
        self._active_goal_lock = threading.Lock()
        self._odom_lock = threading.Lock()
        self._door_scan_lock = threading.Lock()
        self._door_scan_sample = None
        self._odom_yaw: Optional[float] = None
        self._odom_linear_speed: Optional[float] = None
        self._odom_angular_speed: Optional[float] = None
        self._odom_xy: Optional[Tuple[float, float]] = None
        self._odom_received_at: Optional[float] = None
        self._coverage_path: List[Tuple[float, float]] = []
        self._coverage_ratio = 0.0
        self._reachable_area_m2 = 0.0
        self._covered_area_m2 = 0.0
        self._coverage_goals_visited = 0
        self._frontiers_visited_status = 0
        self._frontier_stages_completed = 0
        self._frontiers_remaining = 0
        self._frontier_rank_stats = {}
        self._visited_portals: List[Tuple[float, float]] = []
        self._portal_crossings = 0
        self._portals_remaining = 0
        self._unresolved_frontiers = 0
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
                or not 0.0 <= self._frontier_forward_cone_half_angle <= math.pi
                or not 0 <= self._frontier_goal_max_cost < 99
                or self._frontier_forward_stage_max_distance < 0.0
                or (
                    0.0 < self._frontier_forward_stage_max_distance
                    < self._min_goal_dist_m)
                or self._frontier_stage_min_progress_m <= 0.0
                or self._initial_scan_angle <= 0.0
                or not 0.0 < self._initial_scan_speed <= 0.15
                or self._initial_scan_timeout <= 0.0
                or self._scan_odom_timeout <= 0.0
                or self._scan_odom_recovery_timeout
                <= self._scan_odom_timeout
                or self._scan_no_progress_timeout <= 0.0
                or self._scan_progress_window <= 0.0
                or self._scan_rate_check_after <= 0.0
                or self._scan_min_average_rate <= 0.0
                or self._scan_reverse_limit <= 0.0
                or self._scan_stop_timeout <= 0.0
                or self._scan_stop_tolerance <= 0.0
                or self._scan_command_rate <= 0.0
                or not 0.0 <= self._door_distance <= 1.0
                or (
                    self._door_supervised_wheel_budget_mode
                    and self._door_distance <= 0.0)
                or (
                    self._door_lidar_motion_mode
                    and self._door_distance <= 0.0)
                or (
                    self._door_supervised_wheel_budget_mode
                    and self._door_lidar_motion_mode)
                or not 0.0 <= self._door_encoder_wheel_budget <= 2.0
                or (
                    self._door_lidar_motion_mode
                    and self._door_encoder_wheel_budget
                    <= self._door_distance)
                or not self._door_lidar_scan_topic
                or self._door_lidar_scan_timeout <= 0.0
                or self._door_lidar_recovery_timeout
                <= self._door_lidar_scan_timeout
                or not 0.5 <= self._door_lidar_max_range <= 8.0
                or self._door_lidar_min_points < 200
                or not 0.0 < self._door_lidar_max_cost <= 0.20
                or not 0.0 < self._door_lidar_min_support <= 1.0
                or not 0.0 < self._door_lidar_min_distinct_gap <= 0.02
                or not 0.0 < self._door_lidar_max_step <= 0.12
                or not 0.0 < self._door_lidar_max_yaw_step <= 0.17
                or not 0.0 < self._door_speed <= 0.08
                or self._door_heading_kp <= 0.0
                or self._door_lateral_kp < 0.0
                or not 0.0 < self._door_max_angular <= 0.10
                or not 0.0 < self._door_max_heading_error <= 0.26
                or not 0.0 < self._door_max_lateral_error <= 0.08
                or self._door_timeout <= 0.0
                or self._door_no_progress_timeout <= 0.0
                or self._door_progress_window <= 0.0
                or self._door_reverse_limit <= 0.0
                or self._door_stop_linear_tolerance <= 0.0
                or self._door_pose_timeout <= 0.0
                or self._door_pose_recovery_timeout
                <= self._door_pose_timeout
                or self._door_max_encoder_overrun <= 0.0
                or self._door_max_localization_lead <= 0.0
                or self._door_max_localized_step <= 0.0
                or self._door_max_localized_yaw_step <= 0.0
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
                or self._portal_min_component_area <= 0.0
                or self._portal_min_gap <= 0.0
                or self._portal_max_gap <= self._portal_min_gap
                or self._portal_exit_margin <= 0.0
                or self._portal_max_traverse_distance
                <= self._portal_exit_margin
                or self._portal_max_traverse_distance > 1.0
                or self._portal_encoder_budget_factor <= 1.0
                or self._portal_encoder_budget_margin <= 0.0
                or not 0.0 < self._portal_max_encoder_budget <= 2.0
                or self._portal_max_encoder_budget
                <= self._portal_max_traverse_distance
                or self._portal_corridor_half_width < 0.25
                or self._portal_front_overhang < 0.33
                or self._portal_lidar_min_far_points <= 0
                or self._portal_max_crossings <= 0
                or self._portal_revisit_radius <= 0.0
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
            OccupancyGrid, self._global_costmap_topic,
            self._on_global_costmap, 1, callback_group=self._cb)
        self.create_subscription(
            Odometry, self._odom_topic, self._on_odom, 20,
            callback_group=self._cb)
        self.create_subscription(
            LaserScan, self._door_lidar_scan_topic, self._on_door_lidar_scan,
            qos_profile_sensor_data, callback_group=self._cb)
        self._scan_cmd_pub = self.create_publisher(
            Twist, self._scan_cmd_topic, 10)
        self._door_cmd_pub = self.create_publisher(
            Twist, self._door_cmd_topic, 10)
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

    def _on_global_costmap(self, msg: OccupancyGrid):
        self._global_costmap = msg
        self._global_costmap_received_at = time.monotonic()

    def _on_odom(self, msg: Odometry):
        q = msg.pose.pose.orientation
        values = (
            q.x, q.y, q.z, q.w,
            msg.pose.pose.position.x, msg.pose.pose.position.y,
            msg.twist.twist.linear.x,
            msg.twist.twist.angular.z,
        )
        if not all(math.isfinite(value) for value in values):
            with self._odom_lock:
                self._odom_yaw = None
                self._odom_linear_speed = None
                self._odom_angular_speed = None
                self._odom_xy = None
                self._odom_received_at = None
            self._scan_cmd_pub.publish(Twist())
            self._door_cmd_pub.publish(Twist())
            return
        with self._odom_lock:
            self._odom_yaw = quaternion_yaw(q)
            self._odom_linear_speed = msg.twist.twist.linear.x
            self._odom_angular_speed = msg.twist.twist.angular.z
            self._odom_xy = (
                msg.pose.pose.position.x, msg.pose.pose.position.y)
            self._odom_received_at = time.monotonic()

    def _on_door_lidar_scan(self, msg: LaserScan):
        """Keep one immutable scan sample for slip-independent door motion."""
        stamp = msg.header.stamp
        sample = {
            'ranges': np.asarray(msg.ranges, dtype=np.float64).copy(),
            'angle_min': float(msg.angle_min),
            'angle_increment': float(msg.angle_increment),
            'range_min': float(msg.range_min),
            'range_max': float(msg.range_max),
            'frame_id': str(msg.header.frame_id),
            'key': (int(stamp.sec), int(stamp.nanosec), len(msg.ranges)),
            'received_at': time.monotonic(),
        }
        with self._door_scan_lock:
            self._door_scan_sample = sample

    def _door_lidar_scan_snapshot(self):
        with self._door_scan_lock:
            return self._door_scan_sample

    def _door_lidar_mount(self, frame_id: str):
        """Return the measured laser-to-base planar transform from TF."""
        if frame_id == self._robot_base_frame:
            return 0.0, 0.0, 0.0
        if not frame_id:
            return None
        try:
            transform = self._tf_buffer.lookup_transform(
                self._robot_base_frame, frame_id, rclpy.time.Time())
            mount = (
                float(transform.transform.translation.x),
                float(transform.transform.translation.y),
                quaternion_yaw(transform.transform.rotation),
            )
            return mount if all(math.isfinite(value) for value in mount) else None
        except Exception as exc:  # TransformException u.a.
            self.get_logger().warn(
                f'TF {self._robot_base_frame}<-{frame_id} fuer '
                f'LiDAR-Wegmessung fehlt: {exc}',
                throttle_duration_sec=5.0)
            return None

    def _odom_snapshot(self):
        with self._odom_lock:
            return (
                self._odom_yaw,
                self._odom_angular_speed,
                self._odom_received_at,
            )

    def _odom_xy_snapshot(self):
        with self._odom_lock:
            return self._odom_xy, self._odom_received_at

    def _motion_odom_snapshot(self):
        with self._odom_lock:
            return (
                self._odom_xy,
                self._odom_yaw,
                self._odom_linear_speed,
                self._odom_angular_speed,
                self._odom_received_at,
            )

    # ======================= Roboterpose via TF =========================
    def _robot_pose_sample(
            self
            ) -> Tuple[Optional[Tuple[float, float, float]], Optional[float]]:
        """Return latest map pose and TF age in seconds.

        The transform timestamp belongs to the latest common time of
        ``map->odom->base_link``.  Requiring it to be fresh prevents fresh
        encoder updates from disguising a stale LiDAR/SLAM correction while
        wheels spin on a threshold.
        """
        try:
            t = self._tf_buffer.lookup_transform(
                self._global_frame, self._robot_base_frame, rclpy.time.Time())
            pose = (
                t.transform.translation.x,
                t.transform.translation.y,
                quaternion_yaw(t.transform.rotation),
            )
            if not all(math.isfinite(value) for value in pose):
                return None, None
            stamp_ns = (
                int(t.header.stamp.sec) * 1_000_000_000
                + int(t.header.stamp.nanosec))
            if stamp_ns <= 0:
                return pose, None
            age_s = (self.get_clock().now().nanoseconds - stamp_ns) / 1e9
            return pose, age_s if math.isfinite(age_s) else None
        except Exception as exc:  # TransformException u.a.
            self.get_logger().warn(
                f"TF {self._global_frame}->{self._robot_base_frame} fehlt: {exc}",
                throttle_duration_sec=5.0)
            return None, None

    def _robot_pose(self) -> Optional[Tuple[float, float, float]]:
        pose, _age_s = self._robot_pose_sample()
        return pose

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
            'strategy': 'frontier_portal_then_adaptive_coverage',
            'coverage_ratio': self._coverage_ratio,
            'coverage_percent': 100.0 * self._coverage_ratio,
            'target_coverage_percent': 100.0 * self._coverage_target_ratio,
            'reachable_area_m2': self._reachable_area_m2,
            'covered_area_m2': self._covered_area_m2,
            'frontiers_visited': self._frontiers_visited_status,
            'frontier_stages_completed': self._frontier_stages_completed,
            'portal_crossings': self._portal_crossings,
            'portals_remaining': self._portals_remaining,
            'unresolved_frontiers': self._unresolved_frontiers,
            'coverage_goals_visited': self._coverage_goals_visited,
            'frontiers_remaining': self._frontiers_remaining,
            'frontier_ranking': self._frontier_rank_stats,
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
        """Pick a goal in the robot's connected, safely clear free space."""
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
        robot_col, robot_row = self._world_to_grid(
            robot_xy[0], robot_xy[1], info)
        seed_radius = max(1, int(math.ceil(
            (self._goal_clearance_m + 0.25) / info.resolution)))
        safe_rows, safe_cols = np.nonzero(safe_goal_cells)
        seed_distance_sq = (
            (safe_rows - robot_row) ** 2 + (safe_cols - robot_col) ** 2)
        seed_candidates = seed_distance_sq <= seed_radius ** 2
        if not np.any(seed_candidates):
            return None
        seed_rows = safe_rows[seed_candidates]
        seed_cols = safe_cols[seed_candidates]
        # Der LiDAR-Blindbereich kann mehrere sichere Inseln mit fast gleichem
        # Abstand rund um den Roboter hinterlassen. Fuer jede Frontier wird
        # bewusst die Insel in Richtung ihres Anfahrpunkts gewaehlt, nicht die
        # zufaellig zuerst gefundene seitliche Insel.
        seed_to_desired_sq = (
            (seed_rows - center_row) ** 2 +
            (seed_cols - center_col) ** 2)
        seed_index = int(np.argmin(seed_to_desired_sq))
        safe_seed = (
            int(seed_rows[seed_index]), int(seed_cols[seed_index]))
        reachable_goal_cells = connected_mask(safe_goal_cells, safe_seed)
        choices = []
        for row in range(center_row - search_cells, center_row + search_cells + 1):
            for col in range(center_col - search_cells, center_col + search_cells + 1):
                if not (0 <= row < info.height and 0 <= col < info.width):
                    continue
                if not reachable_goal_cells[row, col]:
                    continue
                wx, wy = self._grid_to_world(col, row, info)
                choices.append((math.hypot(wx - desired_x, wy - desired_y), wx, wy))
        frontier.goal_projected = not bool(choices)
        if not choices:
            # Eine Frontier kann hinter einer erst als schmaler Sichtschlitz
            # erkannten Tuer liegen. Niemals direkt in die getrennte freie
            # Insel planen: zuerst die aus der aktuellen Roboterseite sicher
            # erreichbare Zelle anfahren, die dem Anfahrpunkt am naechsten
            # liegt. Danach wird frisch kartiert und erneut geplant.
            rows, cols = np.nonzero(reachable_goal_cells)
            if rows.size == 0:
                return None
            for row, col in zip(rows.tolist(), cols.tolist()):
                wx, wy = self._grid_to_world(col, row, info)
                choices.append((
                    math.hypot(wx - desired_x, wy - desired_y), wx, wy))
        _, goal_x, goal_y = min(choices)
        costmap_goal = self._costmap_reachable_goal(
            (goal_x, goal_y), (desired_x, desired_y), robot_xy)
        if costmap_goal is None:
            return None
        (goal_x, goal_y), costmap_projected = costmap_goal
        frontier.goal_projected = (
            frontier.goal_projected or costmap_projected)
        return goal_x, goal_y

    def _costmap_reachable_goal(
            self, proposed_goal: Tuple[float, float],
            desired_goal: Tuple[float, float],
            robot_xy: Tuple[float, float]
            ) -> Optional[Tuple[Tuple[float, float], bool]]:
        """Verify/project a goal against NavFn's actual start component."""
        # Unit-level geometry callers created without __init__ retain the
        # map-only contract. A running ExploreNode always owns this attribute
        # and therefore fails closed until the real global Costmap is fresh.
        if not hasattr(self, '_global_costmap'):
            return proposed_goal, False
        costmap = self._global_costmap
        received_at = self._global_costmap_received_at
        if (
                costmap is None or received_at is None
                or not 0.0 <= time.monotonic() - received_at
                <= self._map_timeout_s
                or costmap.header.frame_id != self._global_frame):
            return None
        info = costmap.info
        if info.width <= 0 or info.height <= 0 or info.resolution <= 0.0:
            return None
        data = np.asarray(costmap.data, dtype=np.int16).reshape(
            (info.height, info.width))
        traversable = (data >= 0) & (data < 99)
        robot_col, robot_row = self._world_to_grid(
            robot_xy[0], robot_xy[1], info)
        seed = nearest_mask_cell(
            traversable, robot_row, robot_col,
            max(1, int(math.ceil(0.25 / info.resolution))))
        if seed is None:
            return None
        reachable = connected_mask(traversable, seed)
        goal_col, goal_row = self._world_to_grid(
            proposed_goal[0], proposed_goal[1], info)
        if (
                0 <= goal_row < info.height
                and 0 <= goal_col < info.width
                and reachable[goal_row, goal_col]
                and data[goal_row, goal_col]
                <= self._frontier_goal_max_cost):
            return proposed_goal, False

        safe_reachable = reachable & (
            data <= self._frontier_goal_max_cost)
        rows, cols = np.nonzero(safe_reachable)
        if rows.size == 0:
            return None
        desired_col, desired_row = self._world_to_grid(
            desired_goal[0], desired_goal[1], info)
        distances_sq = (
            (rows - desired_row) ** 2 + (cols - desired_col) ** 2)
        index = int(np.argmin(distances_sq))
        goal_x, goal_y = self._grid_to_world(
            int(cols[index]), int(rows[index]), info)
        return (goal_x, goal_y), True

    def _forward_costmap_stage(
            self, robot_pose: Tuple[float, float, float]
            ) -> Optional[Frontier]:
        """Choose a short direct forward stage from Nav2's live Costmap.

        This fallback is disabled by default and exists only for explicitly
        bounded profiles such as the supervised doorway test. It never enters
        unknown/lethal cells, never exceeds the configured distance/cone and
        additionally requires a direct non-lethal grid line from the robot's
        current Costmap component to the endpoint.
        """
        if (
                self._frontier_forward_stage_max_distance <= 0.0
                or self._frontier_forward_cone_half_angle <= 0.0):
            return None
        costmap = self._global_costmap
        received_at = self._global_costmap_received_at
        if (
                costmap is None or received_at is None
                or not 0.0 <= time.monotonic() - received_at
                <= self._map_timeout_s
                or costmap.header.frame_id != self._global_frame):
            return None
        info = costmap.info
        if info.width <= 0 or info.height <= 0 or info.resolution <= 0.0:
            return None
        data = np.asarray(costmap.data, dtype=np.int16).reshape(
            (info.height, info.width))
        traversable = (data >= 0) & (data < 99)
        robot_col, robot_row = self._world_to_grid(
            robot_pose[0], robot_pose[1], info)
        if not (
                0 <= robot_row < info.height
                and 0 <= robot_col < info.width
                and traversable[robot_row, robot_col]):
            return None
        seed = (robot_row, robot_col)
        reachable = connected_mask(traversable, seed)
        endpoint_mask = reachable & (data <= self._frontier_goal_max_cost)
        rows, cols = np.nonzero(endpoint_mask)
        choices = []
        for row, col in zip(rows.tolist(), cols.tolist()):
            goal_x, goal_y = self._grid_to_world(col, row, info)
            dx = goal_x - robot_pose[0]
            dy = goal_y - robot_pose[1]
            distance = math.hypot(dx, dy)
            if (
                    distance < self._min_goal_dist_m
                    or distance
                    > self._frontier_forward_stage_max_distance
                    + 0.5 * info.resolution):
                continue
            heading_error = abs(normalize_angle(
                math.atan2(dy, dx) - robot_pose[2]))
            if heading_error > self._frontier_forward_cone_half_angle:
                continue
            if not grid_line_is_clear(traversable, seed, (row, col)):
                continue
            if (
                    self._is_visited_frontier_goal(goal_x, goal_y)
                    or self._is_blacklisted(goal_x, goal_y)):
                continue
            choices.append((
                -distance, heading_error, int(data[row, col]),
                goal_x, goal_y))
        if not choices:
            return None
        _negative_distance, _heading, _cost, goal_x, goal_y = min(choices)
        stage = Frontier((goal_x, goal_y), 0)
        stage.goal_x, stage.goal_y = goal_x, goal_y
        stage.goal_projected = True
        stage.forward_staging = True
        return stage

    def _portal_plans(
            self, robot_pose: Tuple[float, float, float]
            ) -> List[PortalPlan]:
        """Find unvisited, bounded transitions in the live global Costmap."""
        if not self._portal_enabled:
            return []
        costmap = self._global_costmap
        received_at = self._global_costmap_received_at
        if (
                costmap is None or received_at is None
                or not 0.0 <= time.monotonic() - received_at
                <= self._map_timeout_s
                or costmap.header.frame_id != self._global_frame):
            return []
        info = costmap.info
        if info.width <= 0 or info.height <= 0 or info.resolution <= 0.0:
            return []
        robot_col, robot_row = self._world_to_grid(
            robot_pose[0], robot_pose[1], info)
        costs = np.asarray(costmap.data, dtype=np.int16).reshape(
            (info.height, info.width))
        bridges = find_portal_bridges(
            costs, (robot_row, robot_col),
            resolution_m=info.resolution,
            goal_max_cost=self._frontier_goal_max_cost,
            min_target_area_m2=self._portal_min_component_area,
            min_gap_m=self._portal_min_gap,
            max_gap_m=self._portal_max_gap,
            exit_margin_m=self._portal_exit_margin,
            max_traverse_distance_m=self._portal_max_traverse_distance)
        plans = []
        for bridge in bridges:
            staging_xy = self._grid_to_world(
                bridge.staging_col, bridge.staging_row, info)
            target_xy = self._grid_to_world(
                bridge.target_col, bridge.target_row, info)
            target_center_xy = self._grid_to_world(
                bridge.target_center_col, bridge.target_center_row, info)
            midpoint_xy = (
                0.5 * (staging_xy[0] + target_xy[0]),
                0.5 * (staging_xy[1] + target_xy[1]),
            )
            if self._is_visited_portal(*midpoint_xy):
                continue
            plans.append(PortalPlan(
                bridge, staging_xy, target_xy,
                target_center_xy, midpoint_xy))
        return plans

    def _is_visited_portal(self, x: float, y: float) -> bool:
        return any(
            math.hypot(x - visited_x, y - visited_y)
            < self._portal_revisit_radius
            for visited_x, visited_y in self._visited_portals)

    def _fresh_front_lidar_corridor(
            self, traverse_distance_m: float
            ) -> Tuple[str, Optional[CorridorCheck]]:
        """Validate one fully observed, footprint-wide forward corridor."""
        scan = self._door_lidar_scan_snapshot()
        if (
                scan is None
                or not 0.0 <= time.monotonic() - scan['received_at']
                <= self._door_lidar_scan_timeout):
            return 'lidar_scan_stale', None
        mount = self._door_lidar_mount(scan['frame_id'])
        if mount is None:
            return 'lidar_tf_missing', None
        try:
            points = scan_points_in_base(
                scan['ranges'], scan['angle_min'], scan['angle_increment'],
                scan['range_min'], scan['range_max'],
                laser_x_m=mount[0], laser_y_m=mount[1],
                laser_yaw_rad=mount[2],
                maximum_range_m=self._door_lidar_max_range)
            if points.shape[0] < self._door_lidar_min_points:
                return 'lidar_points_insufficient', None
            check = front_lidar_corridor_check(
                points, traverse_distance_m=traverse_distance_m,
                corridor_half_width_m=self._portal_corridor_half_width,
                front_overhang_m=self._portal_front_overhang,
                minimum_far_support_points=self._portal_lidar_min_far_points)
        except (ValueError, MemoryError):
            return 'lidar_scan_invalid', None
        return ('success' if check.clear else 'corridor_blocked'), check

    @staticmethod
    def _unresolved_frontier_count(stats) -> int:
        """Count raw map edges that were neither served nor safely close."""
        return sum(int(stats.get(key, 0)) for key in (
            'approach_unavailable', 'blacklisted', 'outside_forward_cone'))

    # ======================= Bewertung / Auswahl ========================
    def _rank_frontiers(
            self, frontiers: List[Frontier], robot_xy: Tuple[float, float],
            grid: OccupancyGrid, robot_yaw: Optional[float] = None
            ) -> List[Frontier]:
        rx, ry = robot_xy
        res = grid.info.resolution
        candidates: List[Frontier] = []
        self._frontiers_rejected_by_heading = 0
        stats = {
            'raw': len(frontiers),
            'approach_unavailable': 0,
            'too_near': 0,
            'visited': 0,
            'blacklisted': 0,
            'outside_forward_cone': 0,
            'accepted': 0,
            'projected': 0,
        }
        for f in frontiers:
            approach = self._frontier_approach_goal(f, robot_xy, grid)
            if approach is None:
                stats['approach_unavailable'] += 1
                continue
            f.goal_x, f.goal_y = approach
            if f.goal_projected:
                stats['projected'] += 1
            dist = math.hypot(f.goal_x - rx, f.goal_y - ry)
            if dist < self._min_goal_dist_m:
                stats['too_near'] += 1
                continue   # zu nah (quasi schon erreicht)
            if self._is_visited_frontier_goal(f.goal_x, f.goal_y):
                stats['visited'] += 1
                continue   # dieses lokale Frontier-Umfeld wurde schon bedient
            if self._is_blacklisted(f.cx, f.cy):
                stats['blacklisted'] += 1
                continue   # zuvor gescheitertes Ziel meiden
            # Kosten/Nutzen (Idee wie explore_lite):
            #   naeher  -> guenstiger (potential_scale * Distanz)
            #   groesser-> attraktiver (gain_scale * Frontier-Ausdehnung)
            f.cost = self._potential_scale * dist - self._gain_scale * (f.size * res)
            if robot_yaw is not None:
                goal_heading = math.atan2(f.goal_y - ry, f.goal_x - rx)
                heading_error = abs(normalize_angle(goal_heading - robot_yaw))
                if (
                        self._frontier_forward_cone_half_angle > 0.0
                        and heading_error
                        > self._frontier_forward_cone_half_angle):
                    self._frontiers_rejected_by_heading += 1
                    stats['outside_forward_cone'] += 1
                    continue
                f.cost += self._heading_scale * heading_error
            candidates.append(f)
            stats['accepted'] += 1
        candidates.sort(key=lambda fr: fr.cost)   # kleinste Kosten zuerst
        self._frontier_rank_stats = stats
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
        for visited in getattr(self, '_visited_frontier_goals', []):
            visited_x, visited_y = visited[:2]
            revisit_radius = (
                visited[2] if len(visited) >= 3
                else self._frontier_revisit_radius)
            if math.hypot(x - visited_x, y - visited_y) < (
                    revisit_radius):
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

    def _publish_door_stop(self):
        self._door_cmd_pub.publish(Twist())

    def _stop_door_and_confirm(self) -> str:
        """Command zero until encoder odometry confirms complete standstill."""
        deadline = time.monotonic() + self._scan_stop_timeout
        stable_since = None
        period = 1.0 / self._scan_command_rate
        while rclpy.ok() and time.monotonic() < deadline:
            self._publish_door_stop()
            (_xy, yaw, linear_speed, angular_speed,
             received_at) = self._motion_odom_snapshot()
            now = time.monotonic()
            if (
                    yaw is None or linear_speed is None
                    or angular_speed is None or received_at is None
                    or not 0.0 <= now - received_at
                    <= self._scan_odom_timeout):
                stable_since = None
            elif (
                    abs(linear_speed) <= self._door_stop_linear_tolerance
                    and abs(angular_speed) <= self._scan_stop_tolerance):
                if stable_since is None:
                    stable_since = now
                elif now - stable_since >= 0.5:
                    return 'success'
            else:
                stable_since = None
            time.sleep(period)
        self._publish_door_stop()
        return 'stop_unconfirmed'

    def _drive_forward_localized(
            self, distance_m: float, speed_mps: float, timeout_s: float,
            stop_requested=lambda: False
            ) -> Tuple[str, float, float, float, float]:
        """Drive a bounded straight stage using LiDAR/SLAM as pose truth.

        The dedicated command still passes through the mission gate, velocity
        smoother and collision monitor. Encoder odometry remains mandatory for
        hardware health and final standstill, but cannot complete the stage:
        limited wheel slip is tolerated and excessive slip stops the robot.
        """
        if distance_m <= 1e-9:
            return 'success', 0.0, 0.0, 0.0, 0.0
        started = time.monotonic()
        period = 1.0 / self._scan_command_rate
        localized_start_xy = None
        localized_start_yaw = None
        encoder_start_xy = None
        encoder_start_yaw = None
        previous_localized_pose = None
        localized_progress = 0.0
        encoder_progress = 0.0
        lateral = 0.0
        heading_error = 0.0
        progress_checkpoint = 0.0
        progress_checkpoint_at = started
        odom_pause_active = False
        localization_pause_active = False
        localization_unavailable_since = None
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

                (xy, yaw, _linear_speed, _angular_speed,
                 received_at) = self._motion_odom_snapshot()
                odom_state = odom_freshness_state(
                    now, received_at, started,
                    self._scan_odom_timeout,
                    self._scan_odom_recovery_timeout,
                    sample_valid=xy is not None and yaw is not None)
                localized_pose, localized_age = self._robot_pose_sample()
                localized_sample_valid = (
                    localized_pose is not None
                    and localized_age is not None
                    and localized_age >= 0.0)
                if localized_sample_valid:
                    localization_unavailable_since = None
                    localization_state = odom_freshness_state(
                        now, now - localized_age, started,
                        self._door_pose_timeout,
                        self._door_pose_recovery_timeout,
                        sample_valid=True)
                else:
                    if localization_unavailable_since is None:
                        localization_unavailable_since = now
                    localization_state = (
                        'pause'
                        if now - localization_unavailable_since
                        <= self._door_pose_recovery_timeout
                        else 'expired')

                if odom_state != 'fresh' or localization_state != 'fresh':
                    if not odom_pause_active:
                        if odom_state != 'fresh':
                            self.get_logger().warn(
                                'Encoder-Odometrie kurzzeitig nicht frisch; '
                                'Tuerkommando bleibt null.')
                            odom_pause_active = True
                    if not localization_pause_active:
                        if localization_state != 'fresh':
                            self.get_logger().warn(
                                'LiDAR/SLAM-Pose kurzzeitig nicht frisch; '
                                'Tuerkommando bleibt null.')
                            localization_pause_active = True
                    if odom_state == 'expired':
                        status = 'odom_stale'
                        break
                    if localization_state == 'expired':
                        status = 'localization_stale'
                        break
                    self._publish_door_stop()
                    time.sleep(period)
                    continue
                recovered = False
                if odom_pause_active:
                    self.get_logger().info(
                        'Encoder-Odometrie wieder frisch.')
                    odom_pause_active = False
                    recovered = True
                if localization_pause_active:
                    self.get_logger().info(
                        'LiDAR/SLAM-Pose wieder frisch; Tueretappe wird '
                        'kontrolliert fortgesetzt.')
                    localization_pause_active = False
                    recovered = True
                if recovered:
                    progress_checkpoint_at = now

                if localized_start_xy is None:
                    localized_start_xy = localized_pose[:2]
                    localized_start_yaw = localized_pose[2]
                    encoder_start_xy = xy
                    encoder_start_yaw = yaw
                    previous_localized_pose = localized_pose
                    progress_checkpoint_at = now
                else:
                    localized_step = math.hypot(
                        localized_pose[0] - previous_localized_pose[0],
                        localized_pose[1] - previous_localized_pose[1])
                    localized_yaw_step = abs(normalize_angle(
                        localized_pose[2] - previous_localized_pose[2]))
                    if localized_step > self._door_max_localized_step:
                        status = 'localization_jump'
                        break
                    if localized_yaw_step > self._door_max_localized_yaw_step:
                        status = 'localization_yaw_jump'
                        break
                    previous_localized_pose = localized_pose

                localized_progress, lateral, heading_error = (
                    relative_planar_motion(
                        localized_start_xy, localized_start_yaw,
                        localized_pose[:2], localized_pose[2]))
                encoder_progress, _encoder_lateral, _encoder_heading = (
                    relative_planar_motion(
                        encoder_start_xy, encoder_start_yaw, xy, yaw))

                if localized_progress < -self._door_reverse_limit:
                    status = 'wrong_direction'
                    break
                if encoder_progress < -self._door_reverse_limit:
                    status = 'encoder_wrong_direction'
                    break
                consistency = door_motion_consistency(
                    localized_progress, encoder_progress,
                    self._door_max_encoder_overrun,
                    self._door_max_localization_lead)
                if consistency != 'consistent':
                    status = consistency
                    break
                if abs(lateral) > self._door_max_lateral_error:
                    status = 'lateral_deviation'
                    break
                if abs(heading_error) > self._door_max_heading_error:
                    status = 'heading_deviation'
                    break
                if localized_progress >= distance_m:
                    status = 'success'
                    break
                if (
                        localized_progress - progress_checkpoint
                        >= self._door_progress_window):
                    progress_checkpoint = localized_progress
                    progress_checkpoint_at = now
                elif now - progress_checkpoint_at >= self._door_no_progress_timeout:
                    status = 'no_progress'
                    break

                command = Twist()
                command.linear.x = speed_mps
                command.angular.z = door_steering_command(
                    heading_error, lateral,
                    self._door_heading_kp, self._door_lateral_kp,
                    self._door_max_angular)
                self._door_cmd_pub.publish(command)
                time.sleep(period)
        finally:
            self._publish_door_stop()

        stop_status = self._stop_door_and_confirm()
        if stop_status != 'success':
            status = stop_status
        return (
            status,
            max(0.0, localized_progress),
            max(0.0, encoder_progress),
            lateral,
            heading_error,
        )

    def _drive_forward_lidar(
            self, distance_m: float, wheel_budget_m: float,
            speed_mps: float, timeout_s: float,
            stop_requested=lambda: False
            ) -> Tuple[str, float, float, float, float, float, float, int]:
        """Drive until a frozen local LiDAR contour confirms real motion.

        Wheel odometry remains mandatory, but only as health signal and hard
        rotation budget.  Unlike ``map->base_link``, the frozen reference scan
        is not advanced by encoder slip.  Therefore a spinning wheel can never
        complete this stage.
        """
        if distance_m <= 1e-9 or wheel_budget_m <= distance_m:
            return (
                'invalid_lidar_budget', 0.0, 0.0, 0.0, 0.0,
                float('inf'), 0.0, 0)

        started = time.monotonic()
        period = 1.0 / self._scan_command_rate
        matcher = None
        match_executor = ThreadPoolExecutor(
            max_workers=1, thread_name_prefix='door_lidar_match')
        match_future = None
        match_started_at = None
        lidar_mount = None
        last_scan_key = None
        last_lidar_pose = (0.0, 0.0, 0.0)
        lidar_forward = 0.0
        lidar_lateral = 0.0
        lidar_heading = 0.0
        lidar_cost = float('inf')
        lidar_support = 0.0
        rejected_matches = 0
        lidar_problem_since = None
        lidar_pause_logged = False

        encoder_start_xy = None
        encoder_start_yaw = None
        encoder_previous_xy = None
        encoder_forward = 0.0
        encoder_path = 0.0
        encoder_checkpoint = 0.0
        encoder_checkpoint_at = started
        odom_pause_active = False

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

                (xy, yaw, _linear_speed, _angular_speed,
                 received_at) = self._motion_odom_snapshot()
                odom_state = odom_freshness_state(
                    now, received_at, started,
                    self._scan_odom_timeout,
                    self._scan_odom_recovery_timeout,
                    sample_valid=xy is not None and yaw is not None)
                if odom_state != 'fresh':
                    if not odom_pause_active:
                        self.get_logger().warn(
                            'Encoder-Odometrie kurzzeitig nicht frisch; '
                            'LiDAR-Tueretappe bleibt null.')
                        odom_pause_active = True
                    if odom_state == 'expired':
                        status = 'odom_stale'
                        break
                    self._publish_door_stop()
                    time.sleep(period)
                    continue
                if odom_pause_active:
                    self.get_logger().info(
                        'Encoder-Odometrie wieder frisch; LiDAR-Tueretappe '
                        'wird kontrolliert fortgesetzt.')
                    odom_pause_active = False
                    encoder_checkpoint_at = now
                    progress_checkpoint_at = now

                if encoder_start_xy is None:
                    encoder_start_xy = xy
                    encoder_start_yaw = yaw
                    encoder_previous_xy = xy
                    encoder_checkpoint_at = now
                else:
                    encoder_step = math.hypot(
                        xy[0] - encoder_previous_xy[0],
                        xy[1] - encoder_previous_xy[1])
                    if encoder_step > self._door_max_localized_step:
                        status = 'encoder_jump'
                        break
                    encoder_path += encoder_step
                    encoder_previous_xy = xy
                encoder_forward, _encoder_lateral, _encoder_heading = (
                    relative_planar_motion(
                        encoder_start_xy, encoder_start_yaw, xy, yaw))
                if encoder_forward < -self._door_reverse_limit:
                    status = 'encoder_wrong_direction'
                    break
                if encoder_path >= wheel_budget_m:
                    status = 'wheel_budget_exhausted'
                    break
                if encoder_path - encoder_checkpoint >= self._door_progress_window:
                    encoder_checkpoint = encoder_path
                    encoder_checkpoint_at = now
                elif now - encoder_checkpoint_at >= self._door_no_progress_timeout:
                    status = 'encoder_no_progress'
                    break

                scan = self._door_lidar_scan_snapshot()
                scan_fresh = (
                    scan is not None
                    and 0.0 <= now - scan['received_at']
                    <= self._door_lidar_scan_timeout)
                if not scan_fresh:
                    if lidar_problem_since is None:
                        lidar_problem_since = now
                    if not lidar_pause_logged:
                        self.get_logger().warn(
                            'Unabhaengiger LiDAR-Scan kurzzeitig nicht '
                            'frisch; Tuerkommando bleibt null.')
                        lidar_pause_logged = True
                    self._publish_door_stop()
                    if (
                            now - lidar_problem_since
                            >= self._door_lidar_recovery_timeout):
                        status = 'lidar_scan_stale'
                        break
                    time.sleep(period)
                    continue

                if lidar_mount is None:
                    lidar_mount = self._door_lidar_mount(scan['frame_id'])
                    if lidar_mount is None:
                        if lidar_problem_since is None:
                            lidar_problem_since = now
                        self._publish_door_stop()
                        if (
                                now - lidar_problem_since
                                >= self._door_lidar_recovery_timeout):
                            status = 'lidar_tf_missing'
                            break
                        time.sleep(period)
                        continue

                candidate = None
                candidate_ready = False
                if match_future is not None and match_future.done():
                    try:
                        candidate = match_future.result()
                    except Exception as exc:
                        self.get_logger().warn(
                            f'LiDAR-Bewegungsmessung verworfen: {exc}',
                            throttle_duration_sec=2.0)
                    match_future = None
                    match_started_at = None
                    candidate_ready = True
                elif (
                        match_future is not None
                        and match_started_at is not None
                        and now - match_started_at
                        >= self._door_lidar_recovery_timeout):
                    self._publish_door_stop()
                    status = 'lidar_match_timeout'
                    break

                if matcher is None and scan['key'] != last_scan_key:
                    # The reference check is synchronous but the command is
                    # still zero. Every later, potentially expensive match is
                    # moved to the worker below so the 20-Hz drive heartbeat
                    # remains continuous on the physical threshold.
                    try:
                        points = scan_points_in_base(
                            scan['ranges'], scan['angle_min'],
                            scan['angle_increment'], scan['range_min'],
                            scan['range_max'],
                            laser_x_m=lidar_mount[0],
                            laser_y_m=lidar_mount[1],
                            laser_yaw_rad=lidar_mount[2],
                            maximum_range_m=self._door_lidar_max_range)
                        if points.shape[0] < self._door_lidar_min_points:
                            raise ValueError(
                                f'nur {points.shape[0]} gueltige Scanpunkte')
                        matcher = LidarReferenceMatcher(points)
                        candidate = matcher.estimate(
                            points, (0.0, 0.0, 0.0))
                    except (ValueError, MemoryError) as exc:
                        candidate = None
                        self.get_logger().warn(
                            f'LiDAR-Referenzmessung verworfen: {exc}',
                            throttle_duration_sec=2.0)
                    last_scan_key = scan['key']
                    candidate_ready = True

                if candidate_ready:
                    candidate_reliable = (
                        candidate is not None
                        and motion_estimate_is_reliable(
                            candidate,
                            max_cost_m=self._door_lidar_max_cost,
                            min_support_ratio=self._door_lidar_min_support,
                            min_distinct_gap_m=(
                                self._door_lidar_min_distinct_gap)))
                    if candidate_reliable:
                        lidar_step = math.hypot(
                            candidate.x_m - last_lidar_pose[0],
                            candidate.y_m - last_lidar_pose[1])
                        lidar_yaw_step = abs(normalize_angle(
                            candidate.yaw_rad - last_lidar_pose[2]))
                        candidate_reliable = (
                            lidar_step <= self._door_lidar_max_step
                            and lidar_yaw_step
                            <= self._door_lidar_max_yaw_step)

                    if not candidate_reliable:
                        rejected_matches += 1
                        if lidar_problem_since is None:
                            lidar_problem_since = now
                        if not lidar_pause_logged:
                            self.get_logger().warn(
                                'LiDAR-Bewegungsmessung nicht eindeutig; '
                                'Tuerkommando bleibt bis zur Erholung null.')
                            lidar_pause_logged = True
                        self._publish_door_stop()
                        if (
                                now - lidar_problem_since
                                >= self._door_lidar_recovery_timeout):
                            status = 'lidar_match_lost'
                            break
                        time.sleep(period)
                        continue

                    last_lidar_pose = (
                        candidate.x_m, candidate.y_m, candidate.yaw_rad)
                    lidar_forward = candidate.x_m
                    lidar_lateral = candidate.y_m
                    lidar_heading = candidate.yaw_rad
                    lidar_cost = candidate.cost_m
                    lidar_support = candidate.support_ratio
                    if lidar_problem_since is not None:
                        self.get_logger().info(
                            'LiDAR-Bewegungsmessung wieder eindeutig; '
                            'Tueretappe wird kontrolliert fortgesetzt.')
                        progress_checkpoint_at = now
                    lidar_problem_since = None
                    lidar_pause_logged = False

                if (
                        matcher is not None
                        and match_future is None
                        and scan['key'] != last_scan_key):
                    try:
                        points = scan_points_in_base(
                            scan['ranges'], scan['angle_min'],
                            scan['angle_increment'], scan['range_min'],
                            scan['range_max'],
                            laser_x_m=lidar_mount[0],
                            laser_y_m=lidar_mount[1],
                            laser_yaw_rad=lidar_mount[2],
                            maximum_range_m=self._door_lidar_max_range)
                        if points.shape[0] < self._door_lidar_min_points:
                            raise ValueError(
                                f'nur {points.shape[0]} gueltige Scanpunkte')
                        match_future = match_executor.submit(
                            matcher.estimate, points, last_lidar_pose)
                        match_started_at = now
                    except (ValueError, MemoryError) as exc:
                        self.get_logger().warn(
                            f'LiDAR-Scan verworfen: {exc}',
                            throttle_duration_sec=2.0)
                        if lidar_problem_since is None:
                            lidar_problem_since = now
                    last_scan_key = scan['key']

                if matcher is None or lidar_problem_since is not None:
                    self._publish_door_stop()
                    if (
                            lidar_problem_since is not None
                            and now - lidar_problem_since
                            >= self._door_lidar_recovery_timeout):
                        status = 'lidar_match_lost'
                        break
                    time.sleep(period)
                    continue
                if lidar_forward < -self._door_reverse_limit:
                    status = 'lidar_wrong_direction'
                    break
                if abs(lidar_lateral) > self._door_max_lateral_error:
                    status = 'lateral_deviation'
                    break
                if abs(lidar_heading) > self._door_max_heading_error:
                    status = 'heading_deviation'
                    break
                if lidar_forward >= distance_m:
                    status = 'success'
                    break
                if (
                        lidar_forward - progress_checkpoint
                        >= self._door_progress_window):
                    progress_checkpoint = lidar_forward
                    progress_checkpoint_at = now
                elif now - progress_checkpoint_at >= self._door_no_progress_timeout:
                    status = 'lidar_no_progress'
                    break

                command = Twist()
                command.linear.x = speed_mps
                command.angular.z = door_steering_command(
                    lidar_heading, lidar_lateral,
                    self._door_heading_kp, self._door_lateral_kp,
                    self._door_max_angular)
                self._door_cmd_pub.publish(command)
                time.sleep(period)
        finally:
            self._publish_door_stop()
            if match_future is not None:
                match_future.cancel()
            match_executor.shutdown(wait=True, cancel_futures=True)

        stop_status = self._stop_door_and_confirm()
        if stop_status != 'success':
            status = stop_status
        return (
            status,
            max(0.0, lidar_forward),
            max(0.0, encoder_path),
            lidar_lateral,
            lidar_heading,
            lidar_cost,
            lidar_support,
            rejected_matches,
        )

    def _drive_forward_supervised(
            self, wheel_budget_m: float, speed_mps: float, timeout_s: float,
            stop_requested=lambda: False
            ) -> Tuple[str, float, float, int]:
        """Run one observer-supervised traction stage with a wheel budget.

        This mode deliberately does not claim physical distance from either
        wheel odometry or ``map->base_link``. On the real threshold both
        advance while the chassis slips because slam_toolbox is seeded by the
        same odometry. Encoder travel is therefore only a hard upper bound on
        commanded wheel rotation. Small continuous map-yaw increments still
        steer the manually aligned robot, while localization jumps are ignored
        instead of terminating the stage. The collision monitor and mission
        gate remain downstream and can command zero at any time.
        """
        if wheel_budget_m <= 1e-9:
            return 'invalid_budget', 0.0, 0.0, 0

        started = time.monotonic()
        period = 1.0 / self._scan_command_rate
        encoder_start_xy = None
        encoder_start_yaw = None
        encoder_progress = 0.0
        filtered_heading = 0.0
        previous_localized_yaw = None
        rejected_localization_jumps = 0
        progress_checkpoint = 0.0
        progress_checkpoint_at = started
        odom_pause_active = False
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

                (xy, yaw, _linear_speed, _angular_speed,
                 received_at) = self._motion_odom_snapshot()
                odom_state = odom_freshness_state(
                    now, received_at, started,
                    self._scan_odom_timeout,
                    self._scan_odom_recovery_timeout,
                    sample_valid=xy is not None and yaw is not None)
                if odom_state != 'fresh':
                    if not odom_pause_active:
                        self.get_logger().warn(
                            'Encoder-Odometrie kurzzeitig nicht frisch; '
                            'Schlupfetappe bleibt null.')
                        odom_pause_active = True
                    if odom_state == 'expired':
                        status = 'odom_stale'
                        break
                    self._publish_door_stop()
                    time.sleep(period)
                    continue
                if odom_pause_active:
                    self.get_logger().info(
                        'Encoder-Odometrie wieder frisch; Schlupfetappe wird '
                        'kontrolliert fortgesetzt.')
                    odom_pause_active = False
                    progress_checkpoint_at = now

                if encoder_start_xy is None:
                    encoder_start_xy = xy
                    encoder_start_yaw = yaw
                    progress_checkpoint_at = now

                encoder_progress, _encoder_lateral, _encoder_heading = (
                    relative_planar_motion(
                        encoder_start_xy, encoder_start_yaw, xy, yaw))
                if encoder_progress < -self._door_reverse_limit:
                    status = 'encoder_wrong_direction'
                    break
                if encoder_progress >= wheel_budget_m:
                    status = 'wheel_budget_complete'
                    break
                if (
                        encoder_progress - progress_checkpoint
                        >= self._door_progress_window):
                    progress_checkpoint = encoder_progress
                    progress_checkpoint_at = now
                elif now - progress_checkpoint_at >= self._door_no_progress_timeout:
                    status = 'encoder_no_progress'
                    break

                localized_pose, localized_age = self._robot_pose_sample()
                localized_fresh = (
                    localized_pose is not None
                    and localized_age is not None
                    and 0.0 <= localized_age <= self._door_pose_timeout)
                if localized_fresh:
                    current_localized_yaw = localized_pose[2]
                    if previous_localized_yaw is None:
                        previous_localized_yaw = current_localized_yaw
                    else:
                        increment = bounded_heading_increment(
                            previous_localized_yaw,
                            current_localized_yaw,
                            self._door_max_localized_yaw_step)
                        previous_localized_yaw = current_localized_yaw
                        if increment is None:
                            rejected_localization_jumps += 1
                            if rejected_localization_jumps == 1:
                                self.get_logger().warn(
                                    'SLAM-Posensprung waehrend Schlupfetappe '
                                    'verworfen; Radbudget laeuft weiter.')
                        else:
                            filtered_heading = normalize_angle(
                                filtered_heading + increment)

                if abs(filtered_heading) > self._door_max_heading_error:
                    status = 'heading_deviation'
                    break

                command = Twist()
                command.linear.x = speed_mps
                command.angular.z = door_steering_command(
                    filtered_heading if localized_fresh else 0.0,
                    0.0,
                    self._door_heading_kp,
                    self._door_lateral_kp,
                    self._door_max_angular)
                self._door_cmd_pub.publish(command)
                time.sleep(period)
        finally:
            self._publish_door_stop()

        stop_status = self._stop_door_and_confirm()
        if stop_status != 'success':
            status = stop_status
        return (
            status,
            max(0.0, encoder_progress),
            filtered_heading,
            rejected_localization_jumps,
        )

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
        odom_pause_active = False
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
                odom_state = odom_freshness_state(
                    now, received_at, started,
                    self._scan_odom_timeout,
                    self._scan_odom_recovery_timeout,
                    sample_valid=yaw is not None)
                if odom_state != 'fresh':
                    if not odom_pause_active:
                        self.get_logger().warn(
                            'Odometrie kurzzeitig nicht frisch; Drehkommando '
                            'bleibt null, warte begrenzt auf Encoder-Daten.')
                        odom_pause_active = True
                    if odom_state == 'expired':
                        status = 'odom_stale'
                        break
                    self._publish_scan_stop()
                    time.sleep(period)
                    continue
                if odom_pause_active:
                    self.get_logger().info(
                        'Odometrie wieder frisch; kontrollierte Drehung wird '
                        'mit nachgetragenem Encoderwinkel fortgesetzt.')
                    odom_pause_active = False

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

    def _matching_portal_plan(
            self, reference: PortalPlan,
            robot_pose: Tuple[float, float, float]
            ) -> Optional[PortalPlan]:
        """Refresh one portal after motion without switching to another gap."""
        plans = self._portal_plans(robot_pose)
        if not plans:
            return None
        match = min(plans, key=lambda plan: math.hypot(
            plan.target_center_xy[0] - reference.target_center_xy[0],
            plan.target_center_xy[1] - reference.target_center_xy[1]))
        if math.hypot(
                match.target_center_xy[0] - reference.target_center_xy[0],
                match.target_center_xy[1] - reference.target_center_xy[1]
                ) > self._portal_revisit_radius:
            return None
        return match

    def _connected_portal_exit_goal(
            self, reference: PortalPlan,
            robot_pose: Tuple[float, float, float]
            ) -> Optional[Tuple[float, float]]:
        """Return a Nav2 goal beyond a portal that became connected.

        Approaching a doorway can add enough live map evidence for Nav2's
        formerly split Costmap components to merge.  That is a geometry
        improvement, not a portal failure.  The transition is accepted only
        when the *original* far-side endpoint is now in the robot's exact
        traversable component.  The selected endpoint must additionally lie
        at least half the configured exit margin beyond that far-side point;
        otherwise a projection back to the near side would look like success.
        """
        costmap = self._global_costmap
        received_at = self._global_costmap_received_at
        if (
                costmap is None or received_at is None
                or not 0.0 <= time.monotonic() - received_at
                <= self._map_timeout_s
                or costmap.header.frame_id != self._global_frame):
            return None
        info = costmap.info
        if info.width <= 0 or info.height <= 0 or info.resolution <= 0.0:
            return None
        data = np.asarray(costmap.data, dtype=np.int16).reshape(
            (info.height, info.width))
        traversable = (data >= 0) & (data < 99)
        robot_col, robot_row = self._world_to_grid(
            robot_pose[0], robot_pose[1], info)
        seed = nearest_mask_cell(
            traversable, robot_row, robot_col,
            max(1, int(math.ceil(0.25 / info.resolution))))
        if seed is None:
            return None
        reachable = connected_mask(traversable, seed)

        target_col, target_row = self._world_to_grid(
            reference.target_xy[0], reference.target_xy[1], info)
        if not (
                0 <= target_row < info.height
                and 0 <= target_col < info.width
                and reachable[target_row, target_col]
                and data[target_row, target_col]
                <= self._frontier_goal_max_cost):
            return None

        direction_x = reference.target_xy[0] - reference.staging_xy[0]
        direction_y = reference.target_xy[1] - reference.staging_xy[1]
        direction_norm = math.hypot(direction_x, direction_y)
        if direction_norm <= 1e-9:
            return None
        direction_x /= direction_norm
        direction_y /= direction_norm
        desired_x = (
            reference.target_xy[0]
            + self._portal_exit_margin * direction_x)
        desired_y = (
            reference.target_xy[1]
            + self._portal_exit_margin * direction_y)

        safe_reachable = reachable & (
            data <= self._frontier_goal_max_cost)
        rows, cols = np.nonzero(safe_reachable)
        if rows.size == 0:
            return None
        desired_col, desired_row = self._world_to_grid(
            desired_x, desired_y, info)
        distances_sq = (
            (rows - desired_row) ** 2 + (cols - desired_col) ** 2)
        index = int(np.argmin(distances_sq))
        goal_x, goal_y = self._grid_to_world(
            int(cols[index]), int(rows[index]), info)
        exit_progress = (
            (goal_x - reference.target_xy[0]) * direction_x
            + (goal_y - reference.target_xy[1]) * direction_y)
        if exit_progress < 0.5 * self._portal_exit_margin:
            return None
        return goal_x, goal_y

    def _navigate_connected_portal_exit(
            self, reference: PortalPlan,
            robot_pose: Tuple[float, float, float],
            stop_requested=lambda: False) -> Optional[str]:
        """Use normal Nav2 after fresh mapping has connected both rooms."""
        goal = self._connected_portal_exit_goal(reference, robot_pose)
        if goal is None:
            return None
        self.get_logger().info(
            'Portal ist durch neue Kartenevidenz regulaer verbunden; '
            'Nav2 uebernimmt die Fahrt bis zum Auslaufpunkt '
            f'({goal[0]:.2f}, {goal[1]:.2f}) m.')
        nav_status = self._navigate_to(
            goal[0], goal[1], self._goal_timeout_s,
            stop_requested=stop_requested)
        if nav_status != 'success':
            return f'portal_connected_{nav_status}'

        final_pose = self._robot_pose()
        if final_pose is None:
            return 'portal_connected_pose_missing'
        direction_x = reference.target_xy[0] - reference.staging_xy[0]
        direction_y = reference.target_xy[1] - reference.staging_xy[1]
        direction_norm = math.hypot(direction_x, direction_y)
        if direction_norm <= 1e-9:
            return 'portal_connected_direction_invalid'
        direction_x /= direction_norm
        direction_y /= direction_norm
        measured_exit = (
            (final_pose[0] - reference.target_xy[0]) * direction_x
            + (final_pose[1] - reference.target_xy[1]) * direction_y)
        if measured_exit < 0.5 * self._portal_exit_margin:
            return 'portal_connected_exit_not_reached'
        return 'connected_success'

    def _execute_portal_plan(
            self, plan: PortalPlan, stop_requested=lambda: False
            ) -> Tuple[str, Tuple[float, float]]:
        """Stage with Nav2, then bridge one proven-clear Costmap split.

        Nav2 remains responsible for all ordinary free-space travel.  Only the
        short disconnected strip is driven directly, behind the mission gate,
        smoother and collision monitor, and completed by frozen-scan LiDAR
        motion rather than wheel odometry.
        """
        pose = self._robot_pose()
        if pose is None:
            return 'portal_pose_missing', plan.midpoint_xy
        staging_distance = math.hypot(
            plan.staging_xy[0] - pose[0], plan.staging_xy[1] - pose[1])
        if staging_distance >= self._min_goal_dist_m:
            turn_status, _turned, _error, _residual = self._prealign_to_goal(
                plan.staging_xy[0], plan.staging_xy[1], pose,
                stop_requested=stop_requested)
            if turn_status not in ('success', 'skipped'):
                return f'portal_stage_prealign_{turn_status}', plan.midpoint_xy
            pose = self._robot_pose()
            if pose is None:
                return 'portal_pose_missing', plan.midpoint_xy
            refreshed = self._matching_portal_plan(plan, pose)
            if refreshed is None:
                connected_status = self._navigate_connected_portal_exit(
                    plan, pose, stop_requested=stop_requested)
                if connected_status is not None:
                    return connected_status, plan.midpoint_xy
                return 'portal_geometry_changed', plan.midpoint_xy
            plan = refreshed
            verify_status, _turned, _error, _residual = self._prealign_to_goal(
                plan.staging_xy[0], plan.staging_xy[1], pose,
                stop_requested=stop_requested)
            if verify_status not in ('success', 'skipped'):
                return (
                    f'portal_stage_verify_{verify_status}',
                    plan.midpoint_xy)
            nav_status = self._navigate_to(
                plan.staging_xy[0], plan.staging_xy[1],
                self._goal_timeout_s, stop_requested=stop_requested)
            if nav_status != 'success':
                return f'portal_stage_{nav_status}', plan.midpoint_xy

        pose = self._robot_pose()
        if pose is None:
            return 'portal_pose_missing', plan.midpoint_xy
        refreshed = self._matching_portal_plan(plan, pose)
        if refreshed is None:
            connected_status = self._navigate_connected_portal_exit(
                plan, pose, stop_requested=stop_requested)
            if connected_status is not None:
                return connected_status, plan.midpoint_xy
            return 'portal_geometry_changed', plan.midpoint_xy
        plan = refreshed
        turn_status, _turned, _error, residual = self._prealign_to_goal(
            plan.target_xy[0], plan.target_xy[1], pose,
            stop_requested=stop_requested)
        if turn_status not in ('success', 'skipped'):
            return f'portal_crossing_prealign_{turn_status}', plan.midpoint_xy
        if abs(residual) > self._prealign_handoff_tolerance:
            return 'portal_crossing_alignment_failed', plan.midpoint_xy

        pose = self._robot_pose()
        if pose is None:
            return 'portal_pose_missing', plan.midpoint_xy
        refreshed = self._matching_portal_plan(plan, pose)
        if refreshed is None:
            connected_status = self._navigate_connected_portal_exit(
                plan, pose, stop_requested=stop_requested)
            if connected_status is not None:
                return connected_status, plan.midpoint_xy
            return 'portal_geometry_changed', plan.midpoint_xy
        plan = refreshed
        traverse_distance = (
            math.hypot(
                plan.target_xy[0] - pose[0],
                plan.target_xy[1] - pose[1])
            + self._portal_exit_margin)
        if not 0.0 < traverse_distance <= self._portal_max_traverse_distance:
            return 'portal_traverse_out_of_bounds', plan.midpoint_xy
        corridor_status, corridor = self._fresh_front_lidar_corridor(
            traverse_distance)
        if corridor is not None:
            self.get_logger().info(
                'Portal-LiDAR-Korridor: Status='
                f'{corridor_status}, erforderlich='
                f'{corridor.required_clear_distance_m:.2f} m, naechster '
                f'Endpunkt={corridor.nearest_obstacle_m:.2f} m, '
                f'Fernstuetzung={corridor.far_support_points}.')
        if corridor_status != 'success':
            return f'portal_{corridor_status}', plan.midpoint_xy

        wheel_budget = min(
            self._portal_max_encoder_budget,
            traverse_distance * self._portal_encoder_budget_factor
            + self._portal_encoder_budget_margin)
        if wheel_budget <= traverse_distance:
            return 'portal_wheel_budget_invalid', plan.midpoint_xy
        self.get_logger().info(
            'Portaluebergang startet: LiDAR-Zielweg '
            f'{traverse_distance:.2f} m, Encoder-Radbudget '
            f'{wheel_budget:.2f} m, Costmap-Luecke '
            f'{plan.bridge.gap_m:.2f} m, Zielbereich '
            f'{plan.bridge.target_area_m2:.2f} m2.')
        (drive_status, lidar_progress, encoder_progress, lateral,
         heading_error, match_cost, match_support, rejected_matches) = (
            self._drive_forward_lidar(
                traverse_distance, wheel_budget,
                self._door_speed, self._door_timeout,
                stop_requested=stop_requested))
        self.get_logger().info(
            f'Portaluebergang beendet: Status={drive_status}, '
            f'LiDAR-Weg={lidar_progress:.3f} m, '
            f'Encoder-Radweg={encoder_progress:.3f} m, '
            f'seitlich={lateral:+.3f} m, Winkelfehler='
            f'{math.degrees(heading_error):+.1f} Grad, '
            f'Matchkosten={match_cost:.3f} m, '
            f'Stuetzung={100.0 * match_support:.1f} %, '
            f'Verwerfungen={rejected_matches}.')
        return (
            'success' if drive_status == 'success'
            else f'portal_drive_{drive_status}',
            plan.midpoint_xy)

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

    @staticmethod
    def _staging_progress_m(status, start_odom, end_odom):
        """Return measured odom progress only for a terminal Nav2 abort."""
        if status != 'aborted' or start_odom is None or end_odom is None:
            return None
        values = (*start_odom, *end_odom)
        if not all(math.isfinite(value) for value in values):
            return None
        return math.hypot(
            end_odom[0] - start_odom[0],
            end_odom[1] - start_odom[1])

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
        self._frontier_stages_completed = 0
        self._frontiers_remaining = 0
        self._visited_portals.clear()
        self._portal_crossings = 0
        self._portals_remaining = 0
        self._unresolved_frontiers = 0
        self._coverage_complete = False
        self._status_phase = 'waiting_for_map'
        self._status_message = 'Erkundung gestartet; warte auf SLAM-Karte und Pose.'
        self._publish_status('running')
        frontiers_visited = 0
        frontier_stages_completed = 0
        failed_goals = 0
        initial_scan_done = not self._initial_scan_enabled
        door_traverse_done = self._door_distance <= 0.0
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

            if not door_traverse_done:
                self._status_phase = 'door_traverse'
                if self._door_lidar_motion_mode:
                    self._status_message = (
                        'Schlupfunabhaengige LiDAR-Tuerdurchfahrt laeuft; '
                        f'realer Zielweg {self._door_distance:.2f} m, '
                        f'Radbudget {self._door_encoder_wheel_budget:.2f} m.')
                elif self._door_supervised_wheel_budget_mode:
                    self._status_message = (
                        'Beaufsichtigte Schlupfetappe laeuft; '
                        f'Radbudget {self._door_distance:.2f} m. Physische '
                        'Tuerdurchfahrt wird nur vom Beobachter bestaetigt.')
                else:
                    self._status_message = (
                        'Beaufsichtigte lokalisierte Tuerdurchfahrt laeuft; '
                        f'Zielstrecke {self._door_distance:.2f} m.')
                self._publish_status('running')
                if self._door_lidar_motion_mode:
                    self.get_logger().info(
                        'Tuerprofil: eingefrorener lokaler LiDAR-Scan misst '
                        f'{self._door_distance:.2f} m reale Vorwaertsbewegung; '
                        f'Encoderweg ist nur Radbudget '
                        f'{self._door_encoder_wheel_budget:.2f} m.')
                    (door_status, door_progress, door_encoder_progress,
                     door_lateral, door_heading_error, door_match_cost,
                     door_match_support, door_rejected_matches) = (
                        self._drive_forward_lidar(
                            self._door_distance,
                            self._door_encoder_wheel_budget,
                            self._door_speed,
                            self._door_timeout,
                            stop_requested=lambda: (
                                goal_handle.is_cancel_requested
                                or overall_expired())))
                    self.get_logger().info(
                        f'LiDAR-Tueretappe beendet: Status={door_status}, '
                        f'realer LiDAR-Weg={door_progress:.3f} m, '
                        f'Encoder-Radweg={door_encoder_progress:.3f} m, '
                        f'seitlich={door_lateral:+.3f} m, Winkelfehler='
                        f'{math.degrees(door_heading_error):+.1f} Grad, '
                        f'Matchkosten={door_match_cost:.3f} m, '
                        f'Stuetzung={100.0 * door_match_support:.1f} %, '
                        f'Verwerfungen={door_rejected_matches}.')
                    expected_status = 'success'
                elif self._door_supervised_wheel_budget_mode:
                    self.get_logger().info(
                        'Tuerprofil: beaufsichtigte Schlupfetappe mit '
                        f'{self._door_distance:.2f} m Radbudget und maximal '
                        f'{self._door_speed:.2f} m/s; SLAM-Spruenge beenden '
                        'die Fahrt nicht.')
                    (door_status, door_encoder_progress,
                     door_heading_error, door_pose_jumps) = (
                        self._drive_forward_supervised(
                            self._door_distance,
                            self._door_speed,
                            self._door_timeout,
                            stop_requested=lambda: (
                                goal_handle.is_cancel_requested
                                or overall_expired())))
                    door_progress = 0.0
                    self.get_logger().info(
                        f'Schlupfetappe beendet: Status={door_status}, '
                        f'Radbudget={door_encoder_progress:.3f} m, '
                        'physischer Weg=nicht sensorisch bestaetigt, '
                        f'gefilterter Winkelfehler='
                        f'{math.degrees(door_heading_error):+.1f} Grad, '
                        f'verworfene SLAM-Spruenge={door_pose_jumps}.')
                    expected_status = 'wheel_budget_complete'
                else:
                    self.get_logger().info(
                        'Tuerprofil: fahre gerade und lokalisiert '
                        f'{self._door_distance:.2f} m mit maximal '
                        f'{self._door_speed:.2f} m/s.')
                    (door_status, door_progress, door_encoder_progress,
                     door_lateral, door_heading_error) = (
                        self._drive_forward_localized(
                            self._door_distance,
                            self._door_speed,
                            self._door_timeout,
                            stop_requested=lambda: (
                                goal_handle.is_cancel_requested
                                or overall_expired())))
                    self.get_logger().info(
                        f'Tueretappe beendet: Status={door_status}, '
                        f'Kartenweg={door_progress:.3f} m, '
                        f'Encoderweg={door_encoder_progress:.3f} m, '
                        f'seitlich={door_lateral:+.3f} m, '
                        f'Winkelfehler='
                        f'{math.degrees(door_heading_error):+.1f} Grad.')
                    expected_status = 'success'

                if door_status != expected_status:
                    result.success = False
                    if goal_handle.is_cancel_requested:
                        goal_handle.canceled()
                        result.message = (
                            'Tuerdurchfahrt abgebrochen; Stillstand bestaetigt')
                    elif overall_expired():
                        goal_handle.abort()
                        result.message = (
                            'Gesamtzeitlimit waehrend Tuerdurchfahrt erreicht; '
                            'Stillstand bestaetigt')
                    else:
                        goal_handle.abort()
                        result.message = (
                            'Beaufsichtigte Tueretappe fehlgeschlagen: '
                            f'{door_status}; Kartenweg {door_progress:.3f} m; '
                            f'Encoderweg {door_encoder_progress:.3f} m')
                    return self._finish_result(result, frontiers_visited)
                door_traverse_done = True
                result.success = True
                if self._door_lidar_motion_mode:
                    result.message = (
                        'LiDAR-bestaetigte Tueretappe abgeschlossen: '
                        f'realer Weg {door_progress:.3f} m; '
                        f'Encoder-Radweg {door_encoder_progress:.3f} m')
                elif self._door_supervised_wheel_budget_mode:
                    result.message = (
                        'Beaufsichtigte Radetappe abgeschlossen; physische '
                        'Tuerdurchfahrt muss die anwesende Person bestaetigen. '
                        f'Radbudget {door_encoder_progress:.3f} m.')
                else:
                    result.message = (
                        'Beaufsichtigte Tuerdurchfahrt abgeschlossen: '
                        f'Kartenweg {door_progress:.3f} m; '
                        f'Encoderweg {door_encoder_progress:.3f} m')
                completion_reason = 'door_traverse_complete'
                break

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
            unprojected_candidates = [
                candidate for candidate in candidates
                if not candidate.goal_projected]
            portal_plans = self._portal_plans(robot_pose)
            self._portals_remaining = len(portal_plans)
            self._unresolved_frontiers = (
                self._unresolved_frontier_count(
                    self._frontier_rank_stats))
            forward_stage = None
            if frontiers and not candidates and not self._coverage_enabled:
                forward_stage = self._forward_costmap_stage(robot_pose)
            coverage_plan = self._coverage_plan(grid, robot_xy)
            self._apply_coverage_plan(coverage_plan)
            self._frontiers_remaining = (
                len(candidates) + len(portal_plans)
                + (1 if forward_stage is not None else 0))
            self._frontiers_visited_status = frontiers_visited

            # Ordinary Nav2-reachable frontiers remain the primary strategy.
            # A portal bridge is selected only when every remaining candidate
            # would otherwise be projected back into the current Costmap
            # component.  This is the exact multi-room deadlock measured at
            # the real doorway, not a generic replacement for navigation.
            if portal_plans and not unprojected_candidates:
                if self._portal_crossings >= self._portal_max_crossings:
                    goal_handle.abort()
                    result.success = False
                    result.message = (
                        'Portal-Uebergangslimit ohne Wohnungsabschluss '
                        f'erreicht ({self._portal_crossings}/'
                        f'{self._portal_max_crossings})')
                    return self._finish_result(result, frontiers_visited)
                portal = portal_plans[0]
                self._status_phase = 'portal_crossing'
                self._status_message = (
                    f'Uebergang {self._portal_crossings + 1} in einen '
                    f'{portal.bridge.target_area_m2:.1f} m2 grossen '
                    'Kartenbereich: Nav2-Anfahrt, LiDAR-Korridorpruefung '
                    'und begrenzte Schlupfbruecke.')
                self._publish_status('running')
                fb = ExploreArea.Feedback()
                fb.explored_percent = 100.0 * self._coverage_ratio
                fb.frontiers_remaining = self._frontiers_remaining
                fb.current_goal.header.frame_id = self._global_frame
                fb.current_goal.header.stamp = self.get_clock().now().to_msg()
                fb.current_goal.pose.position.x = portal.target_xy[0]
                fb.current_goal.pose.position.y = portal.target_xy[1]
                fb.current_goal.pose.orientation.w = 1.0
                goal_handle.publish_feedback(fb)
                portal_status, portal_midpoint = self._execute_portal_plan(
                    portal,
                    stop_requested=lambda: (
                        goal_handle.is_cancel_requested
                        or overall_expired()))
                if portal_status in ('success', 'connected_success'):
                    self._visited_portals.append(portal_midpoint)
                    self._portal_crossings += 1
                    self._portals_remaining = 0
                    self._record_coverage_pose(self._robot_xy())
                    if portal_status == 'connected_success':
                        self.get_logger().info(
                            'Portaluebergang nach Costmap-Verbindung regulaer '
                            'von Nav2 bestaetigt; normale Frontier-Neuplanung '
                            'im neuen Bereich startet.')
                    else:
                        self.get_logger().info(
                            'Portaluebergang LiDAR-bestaetigt; normale '
                            'Frontier-Neuplanung im neuen Bereich startet.')
                    if self._portal_stop_after_crossing:
                        result.success = True
                        if portal_status == 'connected_success':
                            result.message = (
                                'Begrenzte Portalabnahme abgeschlossen: '
                                'neuer Kartenbereich regulaer mit Nav2 '
                                'erreicht; Wohnungserkundung bewusst noch '
                                'nicht fertig')
                        else:
                            result.message = (
                                'Begrenzte Portalabnahme abgeschlossen: '
                                'neuer Kartenbereich LiDAR-bestaetigt '
                                'erreicht; Wohnungserkundung bewusst noch '
                                'nicht fertig')
                        completion_reason = 'portal_crossing_complete'
                        break
                    time.sleep(self._replan_period_s)
                    continue
                result.success = False
                if goal_handle.is_cancel_requested:
                    goal_handle.canceled()
                    result.message = (
                        'Portaluebergang abgebrochen; Stillstand bestaetigt')
                elif overall_expired():
                    goal_handle.abort()
                    result.message = (
                        'Gesamtzeitlimit beim Portaluebergang erreicht; '
                        'Stillstand bestaetigt')
                else:
                    goal_handle.abort()
                    result.message = (
                        'Portaluebergang fail-closed beendet: '
                        f'{portal_status}; Wohnungskarte unvollstaendig')
                return self._finish_result(result, frontiers_visited)

            coverage_goal = False
            forward_staging_goal = False
            if candidates:
                completed_frontier_steps = (
                    frontiers_visited + frontier_stages_completed)
                if completed_frontier_steps >= self._max_frontier_goals:
                    goal_handle.abort()
                    result.success = False
                    result.message = (
                        'Frontier-Etappenlimit ohne Abschluss erreicht '
                        f'({completed_frontier_steps}/'
                        f'{self._max_frontier_goals}); '
                        'Wiederholungs- oder Kartenfortschritt pruefen')
                    return self._finish_result(result, frontiers_visited)
                best = (
                    unprojected_candidates[0]
                    if unprojected_candidates else candidates[0])
                self._status_phase = 'frontier'
                self._status_message = (
                    f'Kartengrenze {completed_frontier_steps + 1} '
                    'wird angefahren; '
                    f'{len(candidates)} sichere Kandidaten offen.')
            elif forward_stage is not None:
                completed_frontier_steps = (
                    frontiers_visited + frontier_stages_completed)
                if completed_frontier_steps >= self._max_frontier_goals:
                    goal_handle.abort()
                    result.success = False
                    result.message = (
                        'Frontier-Etappenlimit ohne Abschluss erreicht '
                        f'({completed_frontier_steps}/'
                        f'{self._max_frontier_goals}); '
                        'Wiederholungs- oder Kartenfortschritt pruefen')
                    return self._finish_result(result, frontiers_visited)
                best = forward_stage
                forward_staging_goal = True
                self._status_phase = 'frontier_stage'
                self._status_message = (
                    f'Direkte Tuer-Vorwaertsetappe '
                    f'{completed_frontier_steps + 1} wird angefahren; '
                    'Ziel und gerader Korridor sind in der globalen '
                    'Costmap geprueft.')
            elif not self._coverage_enabled:
                if (
                        frontiers
                        and self._frontier_forward_cone_half_angle > 0.0):
                    goal_handle.abort()
                    result.success = False
                    result.message = (
                        'Tuerprofil: keine sichere Frontier im freigegebenen '
                        'Vorwaertskorridor und keine direkte sichere Etappe; '
                        'keine Translation ausgefuehrt; Auswahl='
                        f'{json.dumps(self._frontier_rank_stats, separators=(",", ":"))}')
                    return self._finish_result(result, frontiers_visited)
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
            elif self._unresolved_frontiers > 0:
                goal_handle.abort()
                result.success = False
                result.message = (
                    'Wohnungskarte unvollstaendig: '
                    f'{self._unresolved_frontiers} Kartengrenzen sind '
                    'weder sicher erreichbar noch durch einen '
                    'LiDAR-geprueften Portaluebergang verbunden; Auswahl='
                    f'{json.dumps(self._frontier_rank_stats, separators=(",", ":"))}')
                return self._finish_result(result, frontiers_visited)
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

            goal_label = (
                'Abdeckungsziel' if coverage_goal
                else 'Vorwaertsetappe' if forward_staging_goal
                else 'Frontier')
            self._publish_status('running')
            fb = ExploreArea.Feedback()
            fb.explored_percent = 100.0 * self._coverage_ratio
            fb.frontiers_remaining = self._frontiers_remaining
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
                elif forward_staging_goal:
                    refreshed_stage = self._forward_costmap_stage(
                        refreshed_pose)
                    if refreshed_stage is not None:
                        best = refreshed_stage
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
            nav_start_odom, nav_start_odom_at = self._odom_xy_snapshot()
            nav_started_at = time.monotonic()
            status = self._navigate_to(
                best.goal_x, best.goal_y, self._goal_timeout_s,
                stop_requested=lambda: (
                    goal_handle.is_cancel_requested
                    or overall_expired()
                    or not self._map_is_fresh()))
            nav_end_odom, nav_end_odom_at = self._odom_xy_snapshot()

            if status == 'success':
                if coverage_goal:
                    self._coverage_goals_visited += 1
                elif forward_staging_goal:
                    self._visited_frontier_goals.append((
                        best.goal_x, best.goal_y,
                        self._min_goal_dist_m + 0.05))
                    frontier_stages_completed += 1
                    self._frontier_stages_completed = (
                        frontier_stages_completed)
                else:
                    self._visited_frontier_goals.append(
                        (best.goal_x, best.goal_y,
                         min(self._frontier_revisit_radius,
                             self._min_goal_dist_m + 0.05)
                         if best.goal_projected
                         else self._frontier_revisit_radius))
                    frontiers_visited += 1
                    self._frontiers_visited_status = frontiers_visited
                time.sleep(self._replan_period_s)
                continue

            staging_progress = self._staging_progress_m(
                status, nav_start_odom, nav_end_odom)
            odom_fresh = (
                nav_start_odom_at is not None
                and nav_end_odom_at is not None
                and 0.0 <= nav_started_at - nav_start_odom_at
                <= self._scan_odom_timeout
                and nav_end_odom_at >= nav_start_odom_at
                and 0.0 <= time.monotonic() - nav_end_odom_at
                <= self._scan_odom_timeout)
            if (
                    not coverage_goal
                    and staging_progress is not None
                    and staging_progress >= self._frontier_stage_min_progress_m
                    and odom_fresh
                    and self._map_is_fresh()):
                # Nav2 hat wegen einer waehrend der Fahrt neu erkannten
                # Blockade terminal und damit mit gestopptem Controller
                # abgebrochen. Der gemessene Fortschritt ist kein Zielerfolg,
                # darf aber eine frische, kostenkartengepruefte Neuplanung
                # ausloesen, statt als erster harter Fehlversuch zu enden.
                end_pose = self._robot_pose()
                if end_pose is not None:
                    frontier_stages_completed += 1
                    self._frontier_stages_completed = (
                        frontier_stages_completed)
                    self._visited_frontier_goals.append((
                        end_pose[0], end_pose[1],
                        self._min_goal_dist_m + 0.05))
                    self.get_logger().warn(
                        f'Nav2-Pfad nach {staging_progress:.2f} m neu '
                        'blockiert; sichere Zwischenetappe bestaetigt, '
                        'Frontier wird frisch geplant.')
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
                'coverage_complete', 'complete', 'safe_complete',
                'door_traverse_complete', 'portal_crossing_complete'}:
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
