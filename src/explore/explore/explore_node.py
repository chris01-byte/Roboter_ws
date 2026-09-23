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
#    Publish (opt) : /explore/region_graph/status_json
#                    (passiver Kartenstatus-Schatten, max. 1 Hz)
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
from pathlib import Path
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, replace
from typing import List, Optional, Tuple

import numpy as np

import rclpy
from rclpy.node import Node
from rclpy.parameter import Parameter
from rclpy.action import ActionServer, ActionClient, CancelResponse, GoalResponse
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from rclpy.qos import (
    DurabilityPolicy, HistoryPolicy, QoSProfile, ReliabilityPolicy,
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
from explore.raw_map_portal_adapter import (
    correlated_connected_portal_inventory,
)
from explore.frontier_task_feed import (
    FrontierTaskPolicy,
    frontier_inventory_from_clusters,
)
from explore.exploration_migration import (
    build_goal_candidate_status,
    build_passive_we_status_extension,
    build_unavailable_goal_candidate_status,
    build_unavailable_we_status_extension,
    build_we_status_extension,
    project_completion_for_legacy,
)
from explore.exploration_completion import (
    AccessibleScopeState,
    ChildNavigationState,
    CompletionObservation,
    CompletionPolicy,
    ExplorationCompletionSession,
    ExplorationResultState,
    ReturnResultState,
    TerminationCause,
    completion_from_termination,
)
from explore.exploration_persistence import (
    ExplorationPersistenceError,
    ExplorationStateRepository,
    binding_from_map_manager_status,
)
from explore.exploration_child_goal import (
    ExplorationGoalIntent,
    current_goal_intent_from_assessments,
)
from explore.exploration_policy import (
    ExplorationTaskPolicySession,
    PolicyAssessmentState,
    TaskAvailability,
    TaskAvailabilityState,
    assess_exploration_policy,
    score_task_utilities,
)
from explore.frontier_task_evidence import (
    FrontierTaskEvidencePolicy,
    build_frontier_task_evidence,
)
from explore.frontier_goal_candidate import (
    FrontierGoalCandidate,
    FrontierGoalCandidateError,
    build_frontier_goal_candidate,
    revalidate_active_frontier_goal_candidate,
)
from explore.frontier_task_resolution import (
    FrontierTaskResolutionState,
    build_frontier_task_resolution_evidence,
)
from explore.exploration_nav_runtime import (
    ExplorationNavigationSession,
    NavigationSourceState,
    NavigationStopCause,
)
from explore.portal_source_adapter import raw_map_portal_source_from_values
from explore.exploration_scope import AuthorizedExplorationScope
from explore.portal_memory import Point2D as PortalPoint2D
from explore.portal_task_evidence import (
    PortalGoalCandidate,
    PortalTaskEvidencePolicy,
    bind_portal_goal_candidate,
    build_portal_task_evidence,
    build_transit_purpose_evidence,
)
from explore.portal_traversal_runtime import (
    PortalTraversalRuntimePolicy,
    PortalTraversalRuntimeOutcome,
    retry_attempt_from_portal_outcome,
)
from explore.portal_traversal_evidence import PortalTraversalPolicy
from explore.portal_frozen_scan_runtime import (
    ExactTimeMapPose,
    FrozenScanMonitorPolicy,
    FrozenScanPortalMonitor,
    FrozenScanSample,
)
from explore.region_graph_shadow_lifecycle import (
    RegionGraphShadowLifecycle,
    RegionGraphShadowNotReadyError,
)
from explore.region_graph import (
    RegionTaskKind,
    RegionTaskSnapshot,
    RegionTaskState,
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


def validated_shadow_raw_map_capacity(
        shadow_enabled: bool, raw_map_enabled: bool,
        configured_capacity: int) -> Optional[int]:
    """Return the explicit join capacity or keep the raw-map path absent."""
    if not isinstance(shadow_enabled, bool) or not isinstance(
            raw_map_enabled, bool):
        raise ValueError('Schatten-Opt-ins muessen bool sein')
    if (
            isinstance(configured_capacity, bool)
            or not isinstance(configured_capacity, int)
            or configured_capacity < 0):
        raise ValueError(
            'Rohkartenkapazitaet muss eine nichtnegative Ganzzahl sein')
    if raw_map_enabled:
        if not shadow_enabled or configured_capacity <= 0:
            raise ValueError(
                'Rohkarten-Schatten braucht aktiven Regionsgraph und eine '
                'explizit positive Kapazitaet')
        return configured_capacity
    if configured_capacity != 0:
        raise ValueError(
            'Deaktivierter Rohkarten-Schatten braucht Kapazitaet 0')
    return None


def validated_shadow_connected_portal_feed(
        shadow_enabled: bool, raw_map_enabled: bool,
        connected_portals_enabled: bool, raw_map_capacity: int,
        analysis_clearance_m: float, uncertainty_m: float,
        retry_limit: int) -> bool:
    """Validate the third opt-in without creating runtime work."""
    flags = (shadow_enabled, raw_map_enabled, connected_portals_enabled)
    if any(not isinstance(value, bool) for value in flags):
        raise ValueError('Portalfeed-Opt-ins muessen bool sein')
    numeric_limits = (analysis_clearance_m, uncertainty_m)
    if (
            any(
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(float(value))
                for value in numeric_limits)
            or analysis_clearance_m <= 0.0
            or not 0.0 <= uncertainty_m <= 0.10
            or isinstance(retry_limit, bool)
            or not isinstance(retry_limit, int)
            or retry_limit <= 0):
        raise ValueError('Portalfeed-Grenzen sind ungueltig')
    if connected_portals_enabled and (
            not shadow_enabled or not raw_map_enabled
            or raw_map_capacity <= 0):
        raise ValueError(
            'Portalfeed braucht Schatten und positive Rohkartenkorrelation')
    return connected_portals_enabled


def validated_shadow_frontier_task_feed(
        shadow_enabled: bool, raw_map_enabled: bool,
        frontiers_enabled: bool, raw_map_capacity: int) -> bool:
    """Validate the independent passive frontier-task opt-in."""
    flags = (shadow_enabled, raw_map_enabled, frontiers_enabled)
    if any(not isinstance(value, bool) for value in flags):
        raise ValueError('Frontierfeed-Opt-ins muessen bool sein')
    if frontiers_enabled and (
            not shadow_enabled or not raw_map_enabled
            or raw_map_capacity <= 0):
        raise ValueError(
            'Frontierfeed braucht Schatten und positive Rohkartenkorrelation')
    return frontiers_enabled


def validated_passive_policy_enabled(
        shadow_enabled: bool, policy_enabled: bool) -> bool:
    """Validate the diagnostic policy opt-in without enabling its source."""
    if not isinstance(shadow_enabled, bool) or not isinstance(
            policy_enabled, bool):
        raise ValueError('Policy-Opt-ins muessen bool sein')
    if policy_enabled and not shadow_enabled:
        raise ValueError(
            'Passive Wohnungserkundungs-Policy braucht aktiven Schatten')
    return policy_enabled


def validated_we_navigation_enabled(
        shadow_enabled: bool, raw_map_enabled: bool,
        frontier_feed_enabled: bool, policy_enabled: bool,
        navigation_enabled: bool) -> bool:
    """Require the complete passive chain before active WE opt-in."""
    flags = (
        shadow_enabled, raw_map_enabled, frontier_feed_enabled,
        policy_enabled, navigation_enabled)
    if any(not isinstance(value, bool) for value in flags):
        raise ValueError('WE-Navigations-Opt-ins muessen bool sein')
    if navigation_enabled and not all(flags[:-1]):
        raise ValueError(
            'WE-Navigation braucht Schatten, Rohkarte, Frontierfeed und Policy')
    return navigation_enabled


def validated_portal_monitor_enabled(
        navigation_enabled: bool, scope_verified: bool,
        lidar_motion_mode: bool, monitor_enabled: bool) -> bool:
    """Require every independent portal-monitor opt-in explicitly."""
    flags = (
        navigation_enabled, scope_verified,
        lidar_motion_mode, monitor_enabled)
    if any(not isinstance(value, bool) for value in flags):
        raise ValueError('Portalmonitor-Opt-ins muessen bool sein')
    if monitor_enabled and not all(flags[:-1]):
        raise ValueError(
            'Portalmonitor braucht WE-Navigation, verifizierten Scope und '
            'eingefrorene LiDAR-Bewegungsmessung')
    return monitor_enabled


def validated_we_completion_configuration(
        accessible_scope_verified: bool,
        required_fresh_revisions: int):
    """Validate the explicit software-only completion confidence contract."""
    if not isinstance(accessible_scope_verified, bool):
        raise ValueError('WE-Bereichsnachweis muss bool sein')
    try:
        policy = CompletionPolicy(
            required_fresh_observations=required_fresh_revisions)
    except ValueError as error:
        raise ValueError(
            'WE-Abschlussfenster muss eine positive Ganzzahl sein') from error
    return accessible_scope_verified, policy


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
        self._region_graph_shadow_enabled = bool(self.declare_parameter(
            'region_graph_shadow_enabled', False).value)
        self._region_graph_shadow_raw_map_enabled = bool(
            self.declare_parameter(
                'region_graph_shadow_raw_map_enabled', False).value)
        self._region_graph_shadow_raw_map_capacity = int(
            self.declare_parameter(
                'region_graph_shadow_raw_map_capacity', 0).value)
        self._region_graph_shadow_connected_portals_enabled = bool(
            self.declare_parameter(
                'region_graph_shadow_connected_portals_enabled',
                False).value)
        self._region_graph_shadow_frontiers_enabled = bool(
            self.declare_parameter(
                'region_graph_shadow_frontiers_enabled', False).value)
        self._region_graph_shadow_portal_analysis_clearance = float(
            self.declare_parameter(
                'region_graph_shadow_portal_analysis_clearance_m',
                0.20).value)
        self._region_graph_shadow_portal_uncertainty = float(
            self.declare_parameter(
                'region_graph_shadow_portal_uncertainty_m', 0.05).value)
        self._region_graph_shadow_portal_retry_limit = int(
            self.declare_parameter(
                'region_graph_shadow_portal_retry_limit', 30).value)
        self._region_graph_shadow_session_id = str(self.declare_parameter(
            'region_graph_shadow_session_id', '').value).strip()
        self._region_graph_shadow_start_observation_id = str(
            self.declare_parameter(
                'region_graph_shadow_start_observation_id', '').value
        ).strip()
        self._region_graph_shadow_map_status_topic = str(
            self.declare_parameter(
                'region_graph_shadow_map_status_topic',
                '/robot_map_manager/status_json').value
        ).strip()
        self._region_graph_shadow_status_topic = str(self.declare_parameter(
            'region_graph_shadow_status_topic',
            '/explore/region_graph/status_json').value).strip()
        self._wohnungserkundung_policy_enabled = bool(
            self.declare_parameter(
                'wohnungserkundung_policy_enabled', False).value)
        self._wohnungserkundung_navigation_enabled = bool(
            self.declare_parameter(
                'wohnungserkundung_navigation_enabled', False).value)
        self._wohnungserkundung_persistence_enabled = bool(
            self.declare_parameter(
                'wohnungserkundung_persistence_enabled', False).value)
        self._wohnungserkundung_persistence_directory = str(
            self.declare_parameter(
                'wohnungserkundung_persistence_directory',
                '~/.local/share/amadeus/exploration_states').value).strip()
        self._wohnungserkundung_accessible_scope_verified = (
            self.declare_parameter(
                'wohnungserkundung_accessible_scope_verified', False).value)
        self._wohnungserkundung_completion_required_revisions = (
            self.declare_parameter(
                'wohnungserkundung_completion_required_revisions', 3).value)
        self._wohnungserkundung_evidence_clearance = float(
            self.declare_parameter(
                'wohnungserkundung_evidence_clearance_m', 0.28).value)
        self._wohnungserkundung_robot_seed_search = float(
            self.declare_parameter(
                'wohnungserkundung_robot_seed_search_m', 0.75).value)
        self._wohnungserkundung_task_cell_search = float(
            self.declare_parameter(
                'wohnungserkundung_task_cell_search_m', 0.60).value)
        self._wohnungserkundung_information_radius = float(
            self.declare_parameter(
                'wohnungserkundung_information_radius_m', 0.75).value)
        self._wohnungserkundung_evidence_max_cells = int(
            self.declare_parameter(
                'wohnungserkundung_evidence_max_cells', 262144).value)
        self._wohnungserkundung_scope_id = str(self.declare_parameter(
            'wohnungserkundung_scope_id', '').value).strip()
        scope_polygon_values = tuple(
            self.declare_parameter(
                'wohnungserkundung_scope_polygon_xy',
                Parameter.Type.DOUBLE_ARRAY,
            ).value or ())
        self._wohnungserkundung_scope_vertices = tuple(
            PortalPoint2D(
                float(scope_polygon_values[index]),
                float(scope_polygon_values[index + 1]),
            )
            for index in range(0, len(scope_polygon_values), 2)
        ) if len(scope_polygon_values) % 2 == 0 else ()
        self._wohnungserkundung_scope_configuration_valid = (
            (not self._wohnungserkundung_scope_id
             and not scope_polygon_values)
            or (
                bool(self._wohnungserkundung_scope_id)
                and len(scope_polygon_values) >= 6
                and len(scope_polygon_values) % 2 == 0)
        )
        self._wohnungserkundung_scope_clearance = float(
            self.declare_parameter(
                'wohnungserkundung_scope_clearance_m', 0.28).value)
        self._wohnungserkundung_portal_rear_overhang = float(
            self.declare_parameter(
                'wohnungserkundung_portal_rear_overhang_m', 0.35).value)
        self._wohnungserkundung_portal_exit_clearance = float(
            self.declare_parameter(
                'wohnungserkundung_portal_exit_clearance_m', 0.10).value)
        self._wohnungserkundung_portal_target_search = float(
            self.declare_parameter(
                'wohnungserkundung_portal_target_search_m', 0.35).value)
        self._wohnungserkundung_portal_target_lateral = float(
            self.declare_parameter(
                'wohnungserkundung_portal_target_lateral_m', 0.25).value)
        self._wohnungserkundung_portal_path_radius = float(
            self.declare_parameter(
                'wohnungserkundung_portal_path_radius_m', 0.25).value)
        self._wohnungserkundung_portal_monitor_requested = bool(
            self.declare_parameter(
                'wohnungserkundung_portal_monitor_enabled', False).value)
        self._wohnungserkundung_traversal_front_overhang = float(
            self.declare_parameter(
                'wohnungserkundung_traversal_front_overhang_m', 0.0).value)
        self._wohnungserkundung_traversal_rear_overhang = float(
            self.declare_parameter(
                'wohnungserkundung_traversal_rear_overhang_m', 0.0).value)
        self._wohnungserkundung_traversal_start_clearance = float(
            self.declare_parameter(
                'wohnungserkundung_traversal_start_clearance_m', 0.0).value)
        self._wohnungserkundung_traversal_exit_clearance = float(
            self.declare_parameter(
                'wohnungserkundung_traversal_exit_clearance_m', 0.0).value)
        self._wohnungserkundung_traversal_lateral_deviation = float(
            self.declare_parameter(
                'wohnungserkundung_traversal_max_lateral_deviation_m',
                0.0).value)
        self._wohnungserkundung_traversal_pose_step = float(
            self.declare_parameter(
                'wohnungserkundung_traversal_max_pose_step_m', 0.0).value)
        self._wohnungserkundung_traversal_pose_speed = float(
            self.declare_parameter(
                'wohnungserkundung_traversal_max_pose_speed_mps', 0.0).value)
        self._wohnungserkundung_traversal_yaw_error = float(
            self.declare_parameter(
                'wohnungserkundung_traversal_max_yaw_error_rad', 0.0).value)
        self._wohnungserkundung_traversal_yaw_step = float(
            self.declare_parameter(
                'wohnungserkundung_traversal_max_yaw_step_rad', 0.0).value)
        self._wohnungserkundung_traversal_backward_step = float(
            self.declare_parameter(
                'wohnungserkundung_traversal_max_backward_step_m', 0.0).value)
        self._wohnungserkundung_traversal_motion_disagreement = float(
            self.declare_parameter(
                'wohnungserkundung_traversal_max_motion_disagreement_m',
                0.0).value)
        self._wohnungserkundung_traversal_source_age = float(
            self.declare_parameter(
                'wohnungserkundung_traversal_max_source_age_s', 0.0).value)
        self._wohnungserkundung_traversal_revision_lag = int(
            self.declare_parameter(
                'wohnungserkundung_traversal_max_revision_lag', 0).value)
        self._wohnungserkundung_traversal_minimum_samples = int(
            self.declare_parameter(
                'wohnungserkundung_traversal_minimum_pose_samples', 3).value)
        self._wohnungserkundung_traversal_maximum_samples = int(
            self.declare_parameter(
                'wohnungserkundung_traversal_maximum_pose_samples', 256).value)
        self._wohnungserkundung_traversal_pose_interval = float(
            self.declare_parameter(
                'wohnungserkundung_traversal_max_pose_interval_s', 0.0).value)
        self._wohnungserkundung_traversal_scan_rejections = int(
            self.declare_parameter(
                'wohnungserkundung_traversal_max_scan_rejections', 3).value)

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
        if self._region_graph_shadow_enabled and (
                not self._region_graph_shadow_session_id
                or not self._region_graph_shadow_start_observation_id
                or not self._region_graph_shadow_map_status_topic
                or not self._region_graph_shadow_status_topic
                or self._region_graph_shadow_status_topic
                == self._status_topic
                or self._region_graph_shadow_status_topic
                == self._region_graph_shadow_map_status_topic):
            raise ValueError(
                'Aktiver Regionsgraph-Schatten braucht explizite IDs und '
                'getrennte, nichtleere Topics')
        if not self._wohnungserkundung_scope_configuration_valid:
            raise ValueError(
                'WE-Scope braucht eine ID und mindestens drei XY-Ecken')
        self._region_graph_shadow_raw_map_join_capacity = (
            validated_shadow_raw_map_capacity(
                self._region_graph_shadow_enabled,
                self._region_graph_shadow_raw_map_enabled,
                self._region_graph_shadow_raw_map_capacity,
            )
        )
        self._region_graph_shadow_connected_portal_feed = (
            validated_shadow_connected_portal_feed(
                self._region_graph_shadow_enabled,
                self._region_graph_shadow_raw_map_enabled,
                self._region_graph_shadow_connected_portals_enabled,
                self._region_graph_shadow_raw_map_capacity,
                self._region_graph_shadow_portal_analysis_clearance,
                self._region_graph_shadow_portal_uncertainty,
                self._region_graph_shadow_portal_retry_limit,
            )
        )
        self._region_graph_shadow_frontier_task_feed = (
            validated_shadow_frontier_task_feed(
                self._region_graph_shadow_enabled,
                self._region_graph_shadow_raw_map_enabled,
                self._region_graph_shadow_frontiers_enabled,
                self._region_graph_shadow_raw_map_capacity,
            )
        )
        self._region_graph_shadow_raw_event_feed = (
            self._region_graph_shadow_connected_portal_feed
            or self._region_graph_shadow_frontier_task_feed)
        self._wohnungserkundung_policy_enabled = (
            validated_passive_policy_enabled(
                self._region_graph_shadow_enabled,
                self._wohnungserkundung_policy_enabled,
            )
        )
        self._wohnungserkundung_navigation_enabled = (
            validated_we_navigation_enabled(
                self._region_graph_shadow_enabled,
                self._region_graph_shadow_raw_map_enabled,
                self._region_graph_shadow_frontier_task_feed,
                self._wohnungserkundung_policy_enabled,
                self._wohnungserkundung_navigation_enabled,
            )
        )
        # A controlled initial scan intentionally changes the raw-map
        # frontier topology.  Do not turn those incomplete, in-place
        # observations into persistent tasks before the scan has ended: doing
        # so retains every transient cluster as unresolved work even though
        # no translational WE decision has been made yet.  Legacy and
        # scan-free configurations keep their existing immediate feed.
        self._wohnungserkundung_frontier_feed_armed = not (
            self._wohnungserkundung_navigation_enabled
            and self._initial_scan_enabled)
        (
            self._wohnungserkundung_accessible_scope_verified,
            self._wohnungserkundung_completion_policy,
        ) = validated_we_completion_configuration(
            self._wohnungserkundung_accessible_scope_verified,
            self._wohnungserkundung_completion_required_revisions,
        )
        self._wohnungserkundung_portal_monitor_enabled = (
            validated_portal_monitor_enabled(
                self._wohnungserkundung_navigation_enabled,
                self._wohnungserkundung_accessible_scope_verified,
                self._door_lidar_motion_mode,
                self._wohnungserkundung_portal_monitor_requested,
            )
        )
        if self._wohnungserkundung_policy_enabled:
            self._wohnungserkundung_evidence_policy = (
                FrontierTaskEvidencePolicy(
                    clearance_m=(
                        self._wohnungserkundung_evidence_clearance),
                    robot_seed_search_m=(
                        self._wohnungserkundung_robot_seed_search),
                    task_cell_search_m=(
                        self._wohnungserkundung_task_cell_search),
                    information_radius_m=(
                        self._wohnungserkundung_information_radius),
                    max_cells=(
                        self._wohnungserkundung_evidence_max_cells),
                )
            )
            self._wohnungserkundung_portal_evidence_policy = (
                PortalTaskEvidencePolicy(
                    clearance_m=self._wohnungserkundung_evidence_clearance,
                    scope_clearance_m=(
                        self._wohnungserkundung_scope_clearance),
                    robot_seed_search_m=(
                        self._wohnungserkundung_robot_seed_search),
                    chassis_rear_overhang_m=(
                        self._wohnungserkundung_portal_rear_overhang),
                    exit_clearance_m=(
                        self._wohnungserkundung_portal_exit_clearance),
                    target_search_m=(
                        self._wohnungserkundung_portal_target_search),
                    maximum_target_lateral_m=(
                        self._wohnungserkundung_portal_target_lateral),
                    portal_path_radius_m=(
                        self._wohnungserkundung_portal_path_radius),
                    max_cells=self._wohnungserkundung_evidence_max_cells,
                )
            )
            if self._wohnungserkundung_portal_monitor_enabled:
                self._wohnungserkundung_portal_traversal_policy = (
                    PortalTraversalPolicy(
                        chassis_front_overhang_m=(
                            self._wohnungserkundung_traversal_front_overhang),
                        chassis_rear_overhang_m=(
                            self._wohnungserkundung_traversal_rear_overhang),
                        start_clearance_m=(
                            self._wohnungserkundung_traversal_start_clearance),
                        exit_clearance_m=(
                            self._wohnungserkundung_traversal_exit_clearance),
                        maximum_lateral_deviation_m=(
                            self._wohnungserkundung_traversal_lateral_deviation),
                        maximum_pose_step_m=(
                            self._wohnungserkundung_traversal_pose_step),
                        maximum_pose_speed_mps=(
                            self._wohnungserkundung_traversal_pose_speed),
                        maximum_yaw_error_rad=(
                            self._wohnungserkundung_traversal_yaw_error),
                        maximum_yaw_step_rad=(
                            self._wohnungserkundung_traversal_yaw_step),
                        maximum_backward_step_m=(
                            self._wohnungserkundung_traversal_backward_step),
                        maximum_motion_disagreement_m=(
                            self._wohnungserkundung_traversal_motion_disagreement),
                        maximum_source_age_ns=int(round(
                            self._wohnungserkundung_traversal_source_age
                            * 1_000_000_000)),
                        maximum_revision_lag=(
                            self._wohnungserkundung_traversal_revision_lag),
                        minimum_pose_samples=(
                            self._wohnungserkundung_traversal_minimum_samples),
                    )
                )
                self._wohnungserkundung_portal_runtime_policy = (
                    PortalTraversalRuntimePolicy(
                        max_samples=(
                            self._wohnungserkundung_traversal_maximum_samples),
                        maximum_sample_interval_ns=int(round(
                            self._wohnungserkundung_traversal_pose_interval
                            * 1_000_000_000)),
                    ))
                self._wohnungserkundung_frozen_scan_policy = (
                    FrozenScanMonitorPolicy(
                        max_cost_m=self._door_lidar_max_cost,
                        min_support_ratio=self._door_lidar_min_support,
                        min_distinct_gap_m=(
                            self._door_lidar_min_distinct_gap),
                        maximum_scan_step_m=self._door_lidar_max_step,
                        maximum_scan_yaw_step_rad=(
                            self._door_lidar_max_yaw_step),
                        maximum_consecutive_rejections=(
                            self._wohnungserkundung_traversal_scan_rejections),
                    )
                )
            self._wohnungserkundung_evidence_cache_key = None
            self._wohnungserkundung_evidence_cache = None
            self._wohnungserkundung_goal_cache_key = None
            self._wohnungserkundung_goal_cache = None
            self._wohnungserkundung_runtime_lock = threading.Lock()
            self._wohnungserkundung_runtime_condition = threading.Condition(
                self._wohnungserkundung_runtime_lock)
            self._wohnungserkundung_navigation_snapshot = None
            self._wohnungserkundung_policy_processed_revision = None
            # One map update may arrive just before the status timer publishes
            # its matching policy result.  Track the first unconfirmed update
            # per active intent so later raw maps cannot extend that interval.
            self._wohnungserkundung_unconfirmed_intent_id = None
            self._wohnungserkundung_unconfirmed_since = None
            self._wohnungserkundung_active_child = None
            self._wohnungserkundung_active_frontier_source = None
            self._wohnungserkundung_consumed_intent_id = None
            self._wohnungserkundung_task_policy_session = None
            self._wohnungserkundung_stateful_assessment = None
            self._wohnungserkundung_policy_snapshot = None
            self._wohnungserkundung_completion_assessment = None
            self._wohnungserkundung_pending_frontier_resolution = None
            self._wohnungserkundung_frontier_resolution_status = {
                'state': 'none',
            }
            self._wohnungserkundung_status_extension = (
                build_unavailable_we_status_extension(
                    'waiting_for_shadow_snapshot'))
            self._wohnungserkundung_policy_fault = None
            self._wohnungserkundung_persistence_repository = None
            self._wohnungserkundung_persistence_binding = None
            self._wohnungserkundung_persistence_state = 'disabled'
            if self._wohnungserkundung_persistence_enabled:
                storage_path = Path(
                    self._wohnungserkundung_persistence_directory).expanduser()
                self._wohnungserkundung_persistence_repository = (
                    ExplorationStateRepository(storage_path))
                self._wohnungserkundung_persistence_state = 'waiting_for_map'
            # A later target-profile adapter must provide paired map-pose and
            # slip-resistant motion samples.  Without it portal dispatch is
            # impossible even when regular WE navigation is enabled.
            self._wohnungserkundung_portal_monitor_factory = (
                self._create_wohnungserkundung_portal_monitor
                if self._wohnungserkundung_portal_monitor_enabled else None)
            self._wohnungserkundung_portal_traversal_status = {
                'state': 'unavailable',
                'reason': 'portal_traversal_monitor_unavailable',
            }

        # Reentrant-Group: Map-Callback, Action-Server und Nav-Client duerfen
        # sich NICHT gegenseitig blockieren (der Explore-Loop wartet blockierend
        # auf Nav-Ergebnisse, waehrend weiter Karten hereinkommen muessen).
        self._cb = ReentrantCallbackGroup()

        # Ohne explizite Aktivierung existieren weder Schattenzustand noch
        # zusaetzliche ROS-Schnittstellen. Der bestehende Explorerpfad bleibt
        # damit unveraendert.
        self._initialize_region_graph_shadow()

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

    def _initialize_region_graph_shadow(self):
        """Create the isolated, map-only shadow path when explicitly enabled."""
        if not self._region_graph_shadow_enabled:
            return
        lifecycle_arguments = {}
        if self._region_graph_shadow_raw_map_join_capacity is not None:
            lifecycle_arguments['raw_map_capacity'] = (
                self._region_graph_shadow_raw_map_join_capacity)
        if getattr(self, '_region_graph_shadow_frontier_task_feed', False):
            lifecycle_arguments['frontier_policy'] = FrontierTaskPolicy(
                association_radius_m=self._frontier_revisit_radius)
        self._region_graph_shadow = RegionGraphShadowLifecycle(
            self._region_graph_shadow_session_id,
            self._global_frame,
            self._region_graph_shadow_start_observation_id,
            **lifecycle_arguments,
        )
        self._region_graph_shadow_lock = threading.Lock()
        self._region_graph_shadow_fault = None
        if getattr(self, '_region_graph_shadow_raw_event_feed', False):
            self._region_graph_shadow_latest_raw_map = None
            self._region_graph_shadow_latest_raw_source = None
            self._region_graph_shadow_latest_correlation = None
            self._region_graph_shadow_latest_correlation_received_at = None
        if getattr(self, '_region_graph_shadow_connected_portal_feed', False):
            self._region_graph_shadow_processed_correlation = None
            self._region_graph_shadow_portal_retry_count = 0
        if getattr(self, '_region_graph_shadow_frontier_task_feed', False):
            self._region_graph_shadow_frontier_processed_correlation = None

        shadow_qos = QoSProfile(
            history=HistoryPolicy.KEEP_LAST,
            depth=1,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
            reliability=ReliabilityPolicy.RELIABLE,
        )
        self._region_graph_shadow_pub = self.create_publisher(
            String, self._region_graph_shadow_status_topic, shadow_qos)
        self._region_graph_shadow_subscription = self.create_subscription(
            String,
            self._region_graph_shadow_map_status_topic,
            self._on_region_graph_map_status,
            shadow_qos,
            callback_group=self._cb,
        )
        self._region_graph_shadow_timer = self.create_timer(
            1.0,
            self._publish_region_graph_shadow_status,
            callback_group=self._cb,
        )

    def _fault_region_graph_shadow(self, operation, error):
        self._region_graph_shadow_fault = (
            f'{operation}: {type(error).__name__}: {error}')
        self.get_logger().error(
            'Passiver Regionsgraph-Schatten bleibt bis zum Neustart '
            f'deaktiviert ({self._region_graph_shadow_fault}).')

    def _remember_shadow_raw_map_correlation(self, update, received_at):
        """Retain at most one exact join result while holding the lock."""
        if not getattr(
                self, '_region_graph_shadow_raw_event_feed',
                getattr(
                    self, '_region_graph_shadow_connected_portal_feed', False)
                or getattr(
                    self, '_region_graph_shadow_frontier_task_feed', False)):
            return
        correlation = getattr(update, 'raw_map_correlation', None)
        if correlation is None:
            return
        self._region_graph_shadow_latest_correlation = correlation
        self._region_graph_shadow_latest_correlation_received_at = received_at
        if getattr(self, '_region_graph_shadow_connected_portal_feed', False):
            self._region_graph_shadow_portal_retry_count = 0

    @staticmethod
    def _shadow_correlation_key(correlation):
        return (
            correlation.fingerprint,
            correlation.source_stamp_ns,
            correlation.context.frame_id,
            correlation.map_revision,
        )

    @staticmethod
    def _shadow_source_matches_correlation(source, correlation):
        return (
            source.fingerprint == correlation.fingerprint
            and source.source_stamp_ns == correlation.source_stamp_ns
            and source.frame_id == correlation.context.frame_id)

    def _try_observe_connected_raw_map_portals(self):
        """Try one bounded passive feed without holding the shadow lock."""
        if not getattr(self, '_region_graph_shadow_connected_portal_feed', False):
            return
        with self._region_graph_shadow_lock:
            if self._region_graph_shadow_fault is not None:
                return
            message = self._region_graph_shadow_latest_raw_map
            source = self._region_graph_shadow_latest_raw_source
            correlation = self._region_graph_shadow_latest_correlation
            if message is None or source is None or correlation is None:
                return
            correlation_key = self._shadow_correlation_key(correlation)
            if self._region_graph_shadow_processed_correlation == correlation_key:
                return
            if not self._shadow_source_matches_correlation(source, correlation):
                return

        robot_pose = self._robot_pose()
        if robot_pose is None:
            with self._region_graph_shadow_lock:
                if (
                        self._region_graph_shadow_fault is None
                        and self._region_graph_shadow_latest_correlation
                        == correlation
                        and self._region_graph_shadow_latest_raw_source
                        == source):
                    self._region_graph_shadow_portal_retry_count += 1
                    if (
                            self._region_graph_shadow_portal_retry_count
                            >= self._region_graph_shadow_portal_retry_limit):
                        self._fault_region_graph_shadow(
                            'Portalfeed', ValueError(
                                'Roboterpose fehlt nach begrenztem Retry'))
            return

        try:
            origin = message.info.origin
            inventory = correlated_connected_portal_inventory(
                correlation,
                width=message.info.width,
                height=message.info.height,
                resolution=message.info.resolution,
                frame_id=message.header.frame_id.strip(),
                origin=(
                    origin.position.x,
                    origin.position.y,
                    origin.position.z,
                    origin.orientation.x,
                    origin.orientation.y,
                    origin.orientation.z,
                    origin.orientation.w,
                ),
                cells=message.data,
                source_stamp_ns=(
                    int(message.header.stamp.sec) * 1_000_000_000
                    + int(message.header.stamp.nanosec)
                ),
                robot_xy=(robot_pose[0], robot_pose[1]),
                uncertainty_m=self._region_graph_shadow_portal_uncertainty,
                analysis_clearance_m=(
                    self._region_graph_shadow_portal_analysis_clearance),
                min_target_area_m2=self._portal_min_component_area,
                min_gap_m=self._portal_min_gap,
                max_gap_m=self._portal_max_gap,
                exit_margin_m=self._portal_exit_margin,
                max_traverse_distance_m=(
                    self._portal_max_traverse_distance),
            )
        except Exception as error:
            with self._region_graph_shadow_lock:
                if (
                        self._region_graph_shadow_fault is None
                        and self._region_graph_shadow_latest_correlation
                        == correlation
                        and self._region_graph_shadow_latest_raw_source
                        == source):
                    self._fault_region_graph_shadow('Portalfeed', error)
            return

        with self._region_graph_shadow_lock:
            if self._region_graph_shadow_fault is not None:
                return
            if (
                    self._region_graph_shadow_latest_correlation != correlation
                    or self._region_graph_shadow_latest_raw_source != source):
                return
            observed_at = time.monotonic()
            try:
                self._region_graph_shadow.observe_portal_inventory(
                    inventory,
                    observed_monotonic_seconds=observed_at,
                )
            except Exception as error:
                self._fault_region_graph_shadow('Portalfeed', error)
                return
            self._region_graph_shadow_processed_correlation = correlation_key
            self._region_graph_shadow_portal_retry_count = 0

    def _try_observe_correlated_raw_map_frontiers(self):
        """Feed every unfiltered raw-map frontier into passive tasks."""
        if not getattr(self, '_region_graph_shadow_frontier_task_feed', False):
            return
        # A WE start with an initial scan must first obtain that controlled
        # all-around observation.  The gate only defers task creation; it
        # neither changes raw maps nor permits any motion.
        if not getattr(self, '_wohnungserkundung_frontier_feed_armed', True):
            return
        with self._region_graph_shadow_lock:
            if self._region_graph_shadow_fault is not None:
                return
            message = self._region_graph_shadow_latest_raw_map
            source = self._region_graph_shadow_latest_raw_source
            correlation = self._region_graph_shadow_latest_correlation
            if message is None or source is None or correlation is None:
                return
            correlation_key = self._shadow_correlation_key(correlation)
            if (
                    self._region_graph_shadow_frontier_processed_correlation
                    == correlation_key):
                return
            if not self._shadow_source_matches_correlation(source, correlation):
                return

        try:
            frontiers = self._detect_frontiers(message, self._min_frontier_m)
            inventory = frontier_inventory_from_clusters(
                correlation,
                ((frontier.cx, frontier.cy, frontier.size)
                 for frontier in frontiers),
            )
        except Exception as error:
            with self._region_graph_shadow_lock:
                if (
                        self._region_graph_shadow_fault is None
                        and self._region_graph_shadow_latest_correlation
                        == correlation
                        and self._region_graph_shadow_latest_raw_source
                        == source):
                    self._fault_region_graph_shadow('Frontierfeed', error)
            return

        with self._region_graph_shadow_lock:
            if self._region_graph_shadow_fault is not None:
                return
            if (
                    self._region_graph_shadow_latest_correlation != correlation
                    or self._region_graph_shadow_latest_raw_source != source):
                return
            try:
                self._region_graph_shadow.observe_frontier_inventory(
                    inventory,
                    observed_monotonic_seconds=time.monotonic(),
                )
            except Exception as error:
                self._fault_region_graph_shadow('Frontierfeed', error)
                return
            self._region_graph_shadow_frontier_processed_correlation = (
                correlation_key)

    def _try_resolve_successful_wohnungserkundung_frontier(self):
        """Resolve a reached frontier only from a newer exact map snapshot."""
        if not getattr(self, '_wohnungserkundung_policy_enabled', False):
            return
        with self._wohnungserkundung_runtime_lock:
            pending = getattr(
                self, '_wohnungserkundung_pending_frontier_resolution', None)
            previous_status = getattr(
                self, '_wohnungserkundung_frontier_resolution_status', {})
        if pending is None:
            return
        candidate, disposition = pending
        with self._region_graph_shadow_lock:
            if self._region_graph_shadow_fault is not None:
                return
            raw_map = self._region_graph_shadow_latest_raw_map
            raw_source = self._region_graph_shadow_latest_raw_source
            correlation = self._region_graph_shadow_latest_correlation
            if raw_map is None or raw_source is None or correlation is None:
                return
            correlation_key = self._shadow_correlation_key(correlation)
            if (
                    correlation.map_revision <= candidate.map_revision
                    or self._region_graph_shadow_frontier_processed_correlation
                    != correlation_key
                    or not self._shadow_source_matches_correlation(
                        raw_source, correlation)):
                return
            if previous_status.get('evidence_map_revision') == (
                    correlation.map_revision):
                return
            try:
                tracks = self._region_graph_shadow.frontier_tracks()
            except Exception as error:
                status = {
                    'state': 'unavailable',
                    'reason': (
                        f'frontier_track_snapshot_error:'
                        f'{type(error).__name__}'),
                }
                with self._wohnungserkundung_runtime_lock:
                    if self._wohnungserkundung_pending_frontier_resolution == (
                            pending):
                        self._wohnungserkundung_frontier_resolution_status = (
                            status)
                return

        origin = raw_map.info.origin
        try:
            evidence = build_frontier_task_resolution_evidence(
                candidate,
                disposition,
                correlation,
                width=raw_map.info.width,
                height=raw_map.info.height,
                resolution=raw_map.info.resolution,
                frame_id=raw_map.header.frame_id.strip(),
                origin=(
                    origin.position.x,
                    origin.position.y,
                    origin.position.z,
                    origin.orientation.x,
                    origin.orientation.y,
                    origin.orientation.z,
                    origin.orientation.w,
                ),
                cells=raw_map.data,
                source_stamp_ns=(
                    int(raw_map.header.stamp.sec) * 1_000_000_000
                    + int(raw_map.header.stamp.nanosec)),
                tracks=tracks,
                policy=self._wohnungserkundung_evidence_policy,
            )
        except Exception as error:
            status = {
                'state': 'unavailable',
                'reason': f'resolution_evidence_error:{type(error).__name__}',
                'evidence_map_revision': correlation.map_revision,
            }
            with self._wohnungserkundung_runtime_lock:
                if self._wohnungserkundung_pending_frontier_resolution == pending:
                    self._wohnungserkundung_frontier_resolution_status = status
            return

        if evidence.state is FrontierTaskResolutionState.RESOLVED:
            with self._region_graph_shadow_lock:
                if self._region_graph_shadow_fault is not None:
                    return
                if (
                        self._region_graph_shadow_latest_correlation
                        != correlation
                        or self._region_graph_shadow_latest_raw_source
                        != raw_source):
                    return
                try:
                    self._region_graph_shadow.resolve_frontier_task(
                        evidence,
                        observed_monotonic_seconds=time.monotonic(),
                    )
                except Exception as error:
                    self._fault_region_graph_shadow(
                        'Frontierabschluss', error)
                    return
        status = {
            'state': evidence.state.value,
            'reason': evidence.reason,
            'task_id': evidence.task_id,
            'goal_map_revision': evidence.goal_map_revision,
            'evidence_map_revision': evidence.evidence_map_revision,
            'checked_information_cells': (
                evidence.checked_information_cells),
            'unknown_information_cells': (
                evidence.unknown_information_cells),
        }
        with self._wohnungserkundung_runtime_lock:
            if self._wohnungserkundung_pending_frontier_resolution != pending:
                return
            self._wohnungserkundung_frontier_resolution_status = status
            if evidence.resolved:
                self._wohnungserkundung_pending_frontier_resolution = None

    def _on_region_graph_map_status(self, msg: String):
        """Accept one map-manager envelope without affecting exploration."""
        with self._region_graph_shadow_lock:
            if self._region_graph_shadow_fault is not None:
                return
            received_at = time.monotonic()
            try:
                binding = None
                if getattr(
                        self, '_wohnungserkundung_persistence_enabled', False):
                    try:
                        binding = binding_from_map_manager_status(msg.data)
                    except ExplorationPersistenceError:
                        binding = None
                    if (
                            binding is not None
                            and self._region_graph_shadow.context is None
                            and self._wohnungserkundung_persistence_binding
                            is None):
                        repository = (
                            self._wohnungserkundung_persistence_repository)
                        try:
                            loaded = repository.load(binding)
                        except ExplorationPersistenceError as load_error:
                            version_directory = (
                                repository.root / binding.name / binding.version)
                            if version_directory.is_dir() and any(
                                    version_directory.iterdir()):
                                raise load_error
                            self._wohnungserkundung_persistence_state = 'new'
                        else:
                            self._region_graph_shadow.prepare_persistent_restore(
                                loaded.state)
                            self._wohnungserkundung_persistence_state = 'loaded'
                        self._wohnungserkundung_persistence_binding = binding
                update = self._region_graph_shadow.accept_map_status_json(
                    msg.data,
                    received_monotonic_seconds=received_at,
                )
                self._remember_shadow_raw_map_correlation(update, received_at)
                if (
                        binding is not None
                        and json.loads(msg.data).get('event') == 'save_result'
                        and json.loads(msg.data).get('ok') is True):
                    save_binding = binding_from_map_manager_status(
                        msg.data, require_successful_save_event=True)
                    if self._region_graph_shadow.context is not None:
                        self._wohnungserkundung_persistence_repository.save(
                            save_binding,
                            self._region_graph_shadow.persistent_state())
                        self._wohnungserkundung_persistence_binding = save_binding
                        self._wohnungserkundung_persistence_state = 'saved'
            except Exception as error:  # isolated telemetry must not escape
                self._fault_region_graph_shadow('Kartenstatus', error)

    def _publish_region_graph_shadow_status(self):
        """Publish at most once per timer tick after a complete map status."""
        self._try_observe_correlated_raw_map_frontiers()
        self._try_resolve_successful_wohnungserkundung_frontier()
        self._try_observe_connected_raw_map_portals()
        evidence_inputs = None
        candidate_inputs = None
        navigation_snapshot = None
        evidence_unavailable_reason = (
            'frontier_task_feed_disabled'
            if not getattr(
                self, '_region_graph_shadow_frontier_task_feed', False)
            else 'exact_frontier_map_evidence_unavailable')
        with self._region_graph_shadow_lock:
            if self._region_graph_shadow_fault is not None:
                return
            now = time.monotonic()
            try:
                status = self._region_graph_shadow.build_status(
                    now_monotonic_seconds=now)
            except RegionGraphShadowNotReadyError:
                return
            except Exception as error:  # isolated telemetry must not escape
                self._fault_region_graph_shadow('Statusausgabe', error)
                return
            payload = status.serialized
            if (
                    getattr(
                        self, '_wohnungserkundung_policy_enabled', False)
                    and getattr(
                        self, '_region_graph_shadow_frontier_task_feed', False)):
                raw_map = self._region_graph_shadow_latest_raw_map
                correlation = self._region_graph_shadow_latest_correlation
                raw_source = self._region_graph_shadow_latest_raw_source
                if (
                        raw_map is not None
                        and correlation is not None
                        and raw_source is not None
                        and self._shadow_source_matches_correlation(
                            raw_source, correlation)
                        and status.source.context == correlation.context
                        and status.source.source_map_revision
                        == correlation.map_revision):
                    try:
                        tracks = self._region_graph_shadow.frontier_tracks()
                    except Exception as error:
                        evidence_unavailable_reason = (
                            f'frontier_track_snapshot_error:'
                            f'{type(error).__name__}')
                    else:
                        evidence_inputs = (raw_map, correlation, tracks)
            message = String()
            message.data = payload
            self._region_graph_shadow_pub.publish(message)
        if getattr(self, '_wohnungserkundung_policy_enabled', False):
            try:
                task_availability = ()
                utility_evidence = ()
                evidence_status = {
                    'state': 'unavailable',
                    'reason': evidence_unavailable_reason,
                }
                if evidence_inputs is not None:
                    raw_map, correlation, tracks = evidence_inputs
                    robot_pose = self._robot_pose()
                    origin = raw_map.info.origin
                    scope = None
                    if getattr(self, '_wohnungserkundung_scope_id', ''):
                        scope = AuthorizedExplorationScope(
                            scope_id=self._wohnungserkundung_scope_id,
                            context=status.source.context,
                            vertices=(
                                self._wohnungserkundung_scope_vertices),
                        )
                    self._wohnungserkundung_refresh_active_frontier_source(
                        raw_map, correlation, robot_pose, scope)
                    robot_cell = (
                        None if robot_pose is None
                        else self._world_to_grid(
                            robot_pose[0], robot_pose[1], raw_map.info)
                    )
                    evidence_key = (
                        *self._shadow_correlation_key(correlation),
                        robot_cell,
                        None if scope is None else scope.fingerprint,
                    )
                    if evidence_key == (
                            self._wohnungserkundung_evidence_cache_key):
                        evidence = self._wohnungserkundung_evidence_cache
                    else:
                        evidence = build_frontier_task_evidence(
                            correlation,
                            width=raw_map.info.width,
                            height=raw_map.info.height,
                            resolution=raw_map.info.resolution,
                            frame_id=raw_map.header.frame_id.strip(),
                            origin=(
                                origin.position.x,
                                origin.position.y,
                                origin.position.z,
                                origin.orientation.x,
                                origin.orientation.y,
                                origin.orientation.z,
                                origin.orientation.w,
                            ),
                            cells=raw_map.data,
                            source_stamp_ns=(
                                int(raw_map.header.stamp.sec) * 1_000_000_000
                                + int(raw_map.header.stamp.nanosec)
                            ),
                            robot_xy=(
                                None if robot_pose is None
                                else (robot_pose[0], robot_pose[1])
                            ),
                            tasks=tuple(
                                task for task in status.source.graph.tasks
                                if (
                                    task.state is RegionTaskState.OPEN
                                    and getattr(
                                        task, 'kind',
                                        RegionTaskKind.FRONTIER)
                                    is RegionTaskKind.FRONTIER)),
                            tracks=tracks,
                            policy=self._wohnungserkundung_evidence_policy,
                            scope=scope,
                            scope_clearance_m=(
                                None if scope is None else
                                self._wohnungserkundung_scope_clearance),
                        )
                        self._wohnungserkundung_evidence_cache_key = (
                            evidence_key)
                        self._wohnungserkundung_evidence_cache = evidence
                    current_region_id = getattr(
                        status.source.graph, 'current_region_id', None)
                    current_frontier_task_ids = {
                        task.task_id for task in status.source.graph.tasks
                        if (
                            task.state is RegionTaskState.OPEN
                            and getattr(
                                task, 'kind', RegionTaskKind.FRONTIER)
                            is RegionTaskKind.FRONTIER
                            and (
                                current_region_id is None
                                or getattr(
                                    task, 'region_id', current_region_id)
                                == current_region_id))}
                    # A frontier's raw-map path may geometrically cross a
                    # known doorway.  It is not, by itself, permission to
                    # bypass the portal monitor into another region.  Remote
                    # frontiers stay visible in the passive assessment and are
                    # evaluated as a transit purpose below.
                    if all(
                            isinstance(item, TaskAvailability)
                            for item in evidence.availability):
                        current_frontier_availability = tuple(
                            item for item in evidence.availability
                            if item.task_id in current_frontier_task_ids)
                        current_frontier_utilities = tuple(
                            item for item in evidence.utilities
                            if item.task_id in current_frontier_task_ids)
                        current_frontier_availability = (
                            self.
                            _wohnungserkundung_costmap_filter_frontier_availability(
                                current_frontier_availability,
                                status.source.graph.tasks,
                                raw_map,
                                correlation,
                                tracks,
                                evidence,
                                robot_pose,
                                scope,
                            ))
                        # The costmap stage can withhold an otherwise valid
                        # raw-map frontier.  Its utility must be withheld in
                        # the same snapshot: score_task_utilities requires an
                        # exact one-to-one correspondence with selectable
                        # tasks and a blocked goal must never remain scored.
                        current_frontier_available_ids = {
                            item.task_id
                            for item in current_frontier_availability
                            if item.state is TaskAvailabilityState.AVAILABLE
                        }
                        current_frontier_utilities = tuple(
                            item for item in current_frontier_utilities
                            if item.task_id in current_frontier_available_ids)
                    else:
                        # Test-only status stand-ins preserve the historical
                        # passive contract without exercising typed transit.
                        current_frontier_availability = evidence.availability
                        current_frontier_utilities = evidence.utilities
                    portal_evidence = None
                    transit_purposes = None
                    if scope is not None:
                        portal_evidence = build_portal_task_evidence(
                            correlation,
                            width=raw_map.info.width,
                            height=raw_map.info.height,
                            resolution=raw_map.info.resolution,
                            frame_id=raw_map.header.frame_id.strip(),
                            origin=(
                                origin.position.x,
                                origin.position.y,
                                origin.position.z,
                                origin.orientation.x,
                                origin.orientation.y,
                                origin.orientation.z,
                                origin.orientation.w,
                            ),
                            cells=raw_map.data,
                            source_stamp_ns=(
                                int(raw_map.header.stamp.sec)
                                * 1_000_000_000
                                + int(raw_map.header.stamp.nanosec)
                            ),
                            robot_xy=(
                                None if robot_pose is None
                                else (robot_pose[0], robot_pose[1])
                            ),
                            current_region_id=(
                                status.source.graph.current_region_id),
                            tasks=tuple(
                                task for task
                                in status.source.graph.tasks
                                if (
                                    task.state is RegionTaskState.OPEN
                                    and task.kind in (
                                        RegionTaskKind.PORTAL,
                                        RegionTaskKind.TRANSIT))),
                            portals=status.source.portals,
                            connections=status.source.graph.connections,
                            scope=scope,
                            policy=(
                                self._wohnungserkundung_portal_evidence_policy),
                        )
                    if portal_evidence is None:
                        task_availability = current_frontier_availability
                        utility_evidence = current_frontier_utilities
                    else:
                        open_graph_tasks = tuple(
                            task for task in status.source.graph.tasks
                            if task.state is RegionTaskState.OPEN)
                        typed_transits = tuple(
                            task for task in open_graph_tasks
                            if task.kind is RegionTaskKind.TRANSIT)
                        if typed_transits and all(
                                isinstance(task, RegionTaskSnapshot)
                                for task in typed_transits):
                            transit_purposes = build_transit_purpose_evidence(
                                correlation,
                                width=raw_map.info.width,
                                height=raw_map.info.height,
                                resolution=raw_map.info.resolution,
                                frame_id=raw_map.header.frame_id.strip(),
                                origin=(
                                    origin.position.x,
                                    origin.position.y,
                                    origin.position.z,
                                    origin.orientation.x,
                                    origin.orientation.y,
                                    origin.orientation.z,
                                    origin.orientation.w,
                                ),
                                cells=raw_map.data,
                                source_stamp_ns=(
                                    int(raw_map.header.stamp.sec)
                                    * 1_000_000_000
                                    + int(raw_map.header.stamp.nanosec)
                                ),
                                tasks=open_graph_tasks,
                                portals=status.source.portals,
                                connections=status.source.graph.connections,
                                tracks=tracks,
                                scope=scope,
                                frontier_policy=(
                                    self._wohnungserkundung_evidence_policy),
                                portal_policy=(
                                    self._wohnungserkundung_portal_evidence_policy),
                                transit_evidence=portal_evidence,
                            )
                            transit_availability = {
                                item.task_id: item
                                for item in transit_purposes.availability}
                            portal_availability = tuple(
                                transit_availability.get(
                                    item.task_id, item)
                                for item in portal_evidence.availability)
                            portal_utilities = tuple(
                                item for item in portal_evidence.utilities
                                if transit_availability.get(
                                    item.task_id,
                                    None) is None
                                or transit_availability[item.task_id].state
                                is TaskAvailabilityState.AVAILABLE)
                        else:
                            # Compatibility for passive unit callers that use
                            # status-shaped stand-ins rather than graph values.
                            portal_availability = portal_evidence.availability
                            portal_utilities = portal_evidence.utilities
                        task_availability = tuple(sorted(
                            current_frontier_availability
                            + portal_availability,
                            key=lambda item: item.task_id,
                        ))
                        utility_evidence = tuple(sorted(
                            current_frontier_utilities + portal_utilities,
                            key=lambda item: item.task_id,
                        ))
                    candidate_inputs = (
                        raw_map, correlation, tracks, evidence,
                        portal_evidence, transit_purposes, robot_pose,
                        evidence_key, scope)
                    evidence_status = {
                        'state': 'current',
                        'map_revision': evidence.source_map_revision,
                        'robot_seed_available': (
                            evidence.robot_seed_available),
                        'current_frontier_track_count': (
                            evidence.current_frontier_track_count),
                        'availability_count': len(task_availability),
                        'utility_count': len(utility_evidence),
                    }
                    if portal_evidence is not None:
                        evidence_status['portal_scope_state'] = 'current'
                    if transit_purposes is not None:
                        evidence_status['transit_purposes'] = [
                            {
                                'task_id': item.transit_task_id,
                                'target_region_id': item.target_region_id,
                                'portal_id': item.portal_id,
                                'state': item.state.value,
                                'reason': item.reason,
                                'purpose_task_id': item.purpose_task_id,
                                'purpose_kind': (
                                    None if item.purpose_kind is None
                                    else item.purpose_kind.value),
                                'next_portal_id': item.next_portal_id,
                            }
                            for item in transit_purposes.assessments]
                assessment = assess_exploration_policy(
                    status.source, task_availability)
                scores = score_task_utilities(
                    assessment.eligible_task_ids,
                    utility_evidence,
                    status.source.source_map_revision,
                )
                with self._wohnungserkundung_runtime_lock:
                    task_policy_session = (
                        self._wohnungserkundung_task_policy_session)
                    if task_policy_session is None:
                        task_policy_session = ExplorationTaskPolicySession(
                            status.source.context)
                        self._wohnungserkundung_task_policy_session = (
                            task_policy_session)
                    latest_stateful_revision = (
                        task_policy_session.latest_assessment_revision)
                    if (
                            latest_stateful_revision is None
                            or status.source.source_map_revision
                            > latest_stateful_revision):
                        active_child = self._wohnungserkundung_active_child
                        stateful = task_policy_session.assess(
                            status.source,
                            task_availability,
                            utility_evidence if assessment.state is (
                                PolicyAssessmentState.READY_WITH_TASKS)
                            else (),
                            preferred_task_id=(
                                None if active_child is None else
                                active_child[0].task_id),
                        )
                        self._wohnungserkundung_stateful_assessment = stateful
                    elif status.source.source_map_revision < (
                            latest_stateful_revision):
                        raise ValueError(
                            'Policy-Snapshot ist aelter als der Runtimeverlauf')
                    else:
                        stateful = (
                            self._wohnungserkundung_stateful_assessment)
                        if stateful is None:
                            raise ValueError(
                                'Stateful-Policycache fehlt fuer aktuelle '
                                'Revision')
                extension = build_passive_we_status_extension(
                    assessment,
                    utility_scores=scores,
                    stateful=stateful,
                )
                extension['task_evidence_source'] = evidence_status
                if candidate_inputs is None:
                    goal_status = build_unavailable_goal_candidate_status(
                        'exact_goal_evidence_unavailable')
                else:
                    intent = current_goal_intent_from_assessments(
                        assessment, stateful)
                    if intent is None:
                        goal_status = build_unavailable_goal_candidate_status(
                            'withheld_by_current_policy')
                    else:
                        raw_map, correlation, tracks, evidence, (
                            portal_evidence), transit_purposes, robot_pose, (
                            evidence_key), scope = (
                            candidate_inputs)
                        matching_tasks = tuple(
                            task for task in status.source.graph.tasks
                            if task.task_id == intent.task_id)
                        try:
                            if len(matching_tasks) != 1:
                                raise ValueError(
                                    'Auswahl braucht genau eine Graphaufgabe')
                            selected_task = matching_tasks[0]
                            selected_kind = getattr(
                                selected_task, 'kind',
                                RegionTaskKind.FRONTIER)
                            goal_key = (*evidence_key, intent.intent_id)
                            with self._wohnungserkundung_runtime_lock:
                                cached_goal_key = (
                                    self._wohnungserkundung_goal_cache_key)
                                candidate = self._wohnungserkundung_goal_cache
                            if goal_key != cached_goal_key:
                                origin = raw_map.info.origin
                                if selected_kind is (
                                        RegionTaskKind.FRONTIER):
                                    candidate = build_frontier_goal_candidate(
                                        intent,
                                        correlation,
                                        width=raw_map.info.width,
                                        height=raw_map.info.height,
                                        resolution=raw_map.info.resolution,
                                        frame_id=(
                                            raw_map.header.frame_id.strip()),
                                        origin=(
                                            origin.position.x,
                                            origin.position.y,
                                            origin.position.z,
                                            origin.orientation.x,
                                            origin.orientation.y,
                                            origin.orientation.z,
                                            origin.orientation.w,
                                        ),
                                        cells=raw_map.data,
                                        source_stamp_ns=(
                                            int(raw_map.header.stamp.sec)
                                            * 1_000_000_000
                                            + int(raw_map.header.stamp.nanosec)
                                        ),
                                        robot_xy=(
                                            None if robot_pose is None
                                            else (robot_pose[0], robot_pose[1])
                                        ),
                                        task=selected_task,
                                        tracks=tracks,
                                        evidence=evidence,
                                        policy=(self.
                                            _wohnungserkundung_evidence_policy),
                                        scope=scope,
                                        scope_clearance_m=(
                                            None if scope is None else
                                            self._wohnungserkundung_scope_clearance),
                                    )
                                elif (
                                        selected_kind
                                        in (
                                            RegionTaskKind.PORTAL,
                                            RegionTaskKind.TRANSIT)
                                        and portal_evidence is not None):
                                    proposals = tuple(
                                        item for item
                                        in portal_evidence.proposals
                                        if item.task_id == intent.task_id)
                                    if len(proposals) != 1:
                                        raise ValueError(
                                            'Portalwahl braucht genau eine '
                                            'gepruefte Scope-Route')
                                    candidate = bind_portal_goal_candidate(
                                        intent, proposals[0])
                                else:
                                    raise ValueError(
                                        'Aufgabenart besitzt keinen '
                                        'Zieladapter')
                                with self._wohnungserkundung_runtime_lock:
                                    self._wohnungserkundung_goal_cache_key = (
                                        goal_key)
                                    self._wohnungserkundung_goal_cache = candidate
                            costmap_staged = False
                            costmap_blocked = False
                            if selected_kind is RegionTaskKind.FRONTIER:
                                staged_candidate = (
                                    self.
                                    _wohnungserkundung_bind_costmap_frontier_stage(
                                        intent,
                                        candidate,
                                        correlation,
                                        raw_map,
                                        robot_pose,
                                        scope,
                                    ))
                                if staged_candidate is None:
                                    costmap_blocked = True
                                else:
                                    costmap_staged = (
                                        staged_candidate is not candidate)
                                    candidate = staged_candidate
                            goal_status = build_goal_candidate_status(candidate)
                            if costmap_staged:
                                goal_status['nav2_costmap_stage'] = True
                            if (
                                    selected_kind is RegionTaskKind.TRANSIT
                                    and transit_purposes is not None):
                                matching_purposes = tuple(
                                    item for item in transit_purposes.assessments
                                    if item.transit_task_id == intent.task_id)
                                if len(matching_purposes) != 1:
                                    raise ValueError(
                                        'Transitwahl braucht genau einen Zweck')
                                purpose = matching_purposes[0]
                                if purpose.purpose_task_id is None:
                                    raise ValueError(
                                        'Transitwahl besitzt keinen Arbeitszweck')
                                goal_status['transit_purpose'] = {
                                    'task_id': purpose.purpose_task_id,
                                    'kind': purpose.purpose_kind.value,
                                    'target_region_id': purpose.target_region_id,
                                    'next_portal_id': purpose.next_portal_id,
                                }
                            if getattr(
                                    matching_tasks[0], 'kind',
                                    RegionTaskKind.FRONTIER) is (
                                    RegionTaskKind.FRONTIER):
                                if costmap_blocked:
                                    goal_status['dispatch_blocked_reason'] = (
                                        'nav2_costmap_route_unavailable')
                                else:
                                    navigation_snapshot = (intent, candidate)
                            else:
                                monitor_factory = getattr(
                                    self,
                                    '_wohnungserkundung_portal_monitor_factory',
                                    None,
                                )
                                if monitor_factory is None:
                                    goal_status['dispatch_blocked_reason'] = (
                                        'portal_traversal_monitor_unavailable')
                                elif not getattr(
                                        self,
                                        '_wohnungserkundung_accessible_scope_verified',
                                        False):
                                    goal_status['dispatch_blocked_reason'] = (
                                        'portal_scope_not_verified')
                                else:
                                    navigation_snapshot = (intent, candidate)
                        except Exception as goal_error:
                            goal_status = (
                                build_unavailable_goal_candidate_status(
                                    f'goal_candidate_error:'
                                    f'{type(goal_error).__name__}'))
                extension['goal_candidate'] = goal_status
            except Exception as error:
                fault = f'policy_error:{type(error).__name__}'
                unavailable = build_unavailable_we_status_extension(fault)
                report_fault = self._wohnungserkundung_policy_fault != fault
                with self._wohnungserkundung_runtime_lock:
                    self._wohnungserkundung_status_extension = unavailable
                    self._wohnungserkundung_navigation_snapshot = None
                    self._wohnungserkundung_policy_snapshot = None
                    self._wohnungserkundung_policy_fault = fault
                    condition = getattr(
                        self,
                        '_wohnungserkundung_runtime_condition',
                        None,
                    )
                    if condition is not None:
                        condition.notify_all()
                if report_fault:
                    self.get_logger().error(
                        'Passive Wohnungserkundungs-Policy bleibt ohne '
                        f'Wirkung ({fault}: {error}).')
            else:
                active_frontier_source = None
                with self._wohnungserkundung_runtime_lock:
                    child_for_validation = (
                        self._wohnungserkundung_active_child)
                if (
                        child_for_validation is not None
                        and isinstance(
                            child_for_validation[1],
                            FrontierGoalCandidate)):
                    active_intent, active_candidate = child_for_validation
                    validation_reason = 'exact_raw_map_unavailable'
                    validation_current = False
                    if candidate_inputs is not None:
                        (raw_map, correlation, _tracks, _evidence,
                         _portal_evidence, _transit_purposes, robot_pose,
                         _evidence_key, scope) = candidate_inputs
                        origin = raw_map.info.origin
                        try:
                            route_length_m = (
                                revalidate_active_frontier_goal_candidate(
                                    active_intent,
                                    active_candidate,
                                    correlation,
                                    width=raw_map.info.width,
                                    height=raw_map.info.height,
                                    resolution=raw_map.info.resolution,
                                    frame_id=(
                                        raw_map.header.frame_id.strip()),
                                    origin=(
                                        origin.position.x,
                                        origin.position.y,
                                        origin.position.z,
                                        origin.orientation.x,
                                        origin.orientation.y,
                                        origin.orientation.z,
                                        origin.orientation.w,
                                    ),
                                    cells=raw_map.data,
                                    source_stamp_ns=(
                                        int(raw_map.header.stamp.sec)
                                        * 1_000_000_000
                                        + int(raw_map.header.stamp.nanosec)
                                    ),
                                    robot_xy=(
                                        None if robot_pose is None else
                                        (robot_pose[0], robot_pose[1])),
                                    policy=(
                                        self._wohnungserkundung_evidence_policy),
                                    scope=scope,
                                    scope_clearance_m=(
                                        None if scope is None else
                                        self._wohnungserkundung_scope_clearance),
                                ))
                        except FrontierGoalCandidateError as error:
                            validation_reason = (
                                f'fixed_goal_invalid:{type(error).__name__}')
                        else:
                            validation_current = True
                            validation_reason = 'fixed_goal_revalidated'
                            extension['active_goal_validation'] = {
                                'state': 'current',
                                'map_revision': correlation.map_revision,
                                'task_id': active_intent.task_id,
                                'route_length_m': route_length_m,
                            }
                        active_frontier_source = (
                            active_intent.intent_id,
                            NavigationSourceState(
                                active_intent.context,
                                correlation.map_revision,
                                validation_current,
                            ),
                            validation_reason,
                        )
                    if not validation_current:
                        extension['active_goal_validation'] = {
                            'state': 'invalid',
                            'map_revision': status.source.source_map_revision,
                            'task_id': active_intent.task_id,
                            'reason': validation_reason,
                        }
                with self._wohnungserkundung_runtime_lock:
                    active_child = self._wohnungserkundung_active_child
                    consumed_intent_id = (
                        self._wohnungserkundung_consumed_intent_id)
                    if navigation_snapshot is not None:
                        intent, candidate = navigation_snapshot
                        if (
                                active_child is not None
                                and active_child[0].intent_id
                                == intent.intent_id):
                            extension['goal_candidate'][
                                'navigation_dispatched'] = True
                            extension['goal_candidate']['child_state'] = (
                                'active')
                        elif consumed_intent_id == intent.intent_id:
                            extension['goal_candidate']['state'] = 'consumed'
                    completion = (
                        getattr(
                            self,
                            '_wohnungserkundung_completion_assessment',
                            None))
                    if completion is not None:
                        extension['runtime_result'] = (
                            build_we_status_extension(completion))
                    resolution_status = getattr(
                        self,
                        '_wohnungserkundung_frontier_resolution_status',
                        None,
                    )
                    if resolution_status is not None:
                        extension['frontier_resolution'] = dict(
                            resolution_status)
                    traversal_status = getattr(
                        self,
                        '_wohnungserkundung_portal_traversal_status',
                        None,
                    )
                    if traversal_status is not None:
                        extension['portal_traversal'] = dict(
                            traversal_status)
                    if getattr(
                            self, '_wohnungserkundung_persistence_enabled',
                            False):
                        persistence = {
                            'state': self._wohnungserkundung_persistence_state,
                        }
                        binding = self._wohnungserkundung_persistence_binding
                        if binding is not None:
                            persistence.update({
                                'map_name': binding.name,
                                'map_version': binding.version,
                                'map_fingerprint': binding.fingerprint,
                            })
                        extension['persistence'] = persistence
                    self._wohnungserkundung_status_extension = extension
                    if (
                            active_frontier_source is not None
                            and active_child is not None
                            and active_child[0].intent_id
                            == active_frontier_source[0]):
                        self._wohnungserkundung_active_frontier_source = (
                            active_frontier_source)
                    self._wohnungserkundung_navigation_snapshot = (
                        navigation_snapshot)
                    self._wohnungserkundung_policy_processed_revision = (
                        status.source.source_map_revision)
                    self._wohnungserkundung_policy_snapshot = stateful
                    self._wohnungserkundung_policy_fault = None
                    condition = getattr(
                        self,
                        '_wohnungserkundung_runtime_condition',
                        None,
                    )
                    if condition is not None:
                        condition.notify_all()

    # ======================= Karten-Eingang =============================
    def _on_map(self, msg: OccupancyGrid):
        self._map = msg
        self._map_received_at = time.monotonic()
        if not getattr(self, '_region_graph_shadow_raw_map_enabled', False):
            return
        with self._region_graph_shadow_lock:
            if self._region_graph_shadow_fault is not None:
                return
        try:
            origin = msg.info.origin
            source = raw_map_portal_source_from_values(
                width=msg.info.width,
                height=msg.info.height,
                resolution=msg.info.resolution,
                frame_id=msg.header.frame_id.strip(),
                origin=(
                    origin.position.x,
                    origin.position.y,
                    origin.position.z,
                    origin.orientation.x,
                    origin.orientation.y,
                    origin.orientation.z,
                    origin.orientation.w,
                ),
                cells=msg.data,
                source_stamp_ns=(
                    int(msg.header.stamp.sec) * 1_000_000_000
                    + int(msg.header.stamp.nanosec)
                ),
            )
        except Exception as error:  # isolated telemetry must not escape
            with self._region_graph_shadow_lock:
                if self._region_graph_shadow_fault is None:
                    self._fault_region_graph_shadow('Rohkarte', error)
            return
        with self._region_graph_shadow_lock:
            if self._region_graph_shadow_fault is not None:
                return
            if getattr(
                    self, '_region_graph_shadow_raw_event_feed',
                    getattr(
                        self, '_region_graph_shadow_connected_portal_feed',
                        False)
                    or getattr(
                        self, '_region_graph_shadow_frontier_task_feed',
                        False)):
                self._region_graph_shadow_latest_raw_map = msg
                self._region_graph_shadow_latest_raw_source = source
            received_at = time.monotonic()
            try:
                update = self._region_graph_shadow.accept_raw_map_source(
                    source,
                    received_monotonic_seconds=received_at,
                )
                self._remember_shadow_raw_map_correlation(update, received_at)
            except Exception as error:  # isolated telemetry must not escape
                self._fault_region_graph_shadow('Rohkarte', error)

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

    def _wohnungserkundung_frozen_scan_sample(self):
        """Convert one fresh retained scan without reading a device directly."""
        scan = self._door_lidar_scan_snapshot()
        now = time.monotonic()
        if (
                scan is None
                or not 0.0 <= now - scan['received_at']
                <= self._door_lidar_scan_timeout):
            return None
        mount = self._door_lidar_mount(scan['frame_id'])
        if mount is None:
            return None
        try:
            points = scan_points_in_base(
                scan['ranges'],
                scan['angle_min'],
                scan['angle_increment'],
                scan['range_min'],
                scan['range_max'],
                laser_x_m=mount[0],
                laser_y_m=mount[1],
                laser_yaw_rad=mount[2],
                maximum_range_m=self._door_lidar_max_range,
            )
        except (ValueError, MemoryError):
            return None
        if points.shape[0] < self._door_lidar_min_points:
            return None
        second, nanosecond, count = scan['key']
        stamp_ns = second * 1_000_000_000 + nanosecond
        try:
            return FrozenScanSample(
                sample_id=f'we-scan-{second}-{nanosecond}-{count}',
                stamp_ns=stamp_ns,
                points=points,
            )
        except ValueError:
            return None

    def _wohnungserkundung_exact_time_pose(
            self, candidate, stamp_ns):
        """Read map pose at the exact independent scan timestamp."""
        if not self._wohnungserkundung_source_state(
                candidate, candidate).current:
            return None
        try:
            transform = self._tf_buffer.lookup_transform(
                self._global_frame,
                self._robot_base_frame,
                rclpy.time.Time(nanoseconds=stamp_ns),
            )
            pose = ExactTimeMapPose(
                context=candidate.context,
                map_revision=candidate.map_revision,
                stamp_ns=stamp_ns,
                x=float(transform.transform.translation.x),
                y=float(transform.transform.translation.y),
                yaw=quaternion_yaw(transform.transform.rotation),
            )
        except Exception:
            return None
        return pose

    def _create_wohnungserkundung_portal_monitor(
            self, candidate, portal):
        """Create one target-profile monitor for the selected child only."""
        scope = AuthorizedExplorationScope(
            scope_id=self._wohnungserkundung_scope_id,
            context=candidate.context,
            vertices=self._wohnungserkundung_scope_vertices,
        )
        return FrozenScanPortalMonitor(
            candidate,
            portal,
            self._wohnungserkundung_portal_traversal_policy,
            self._wohnungserkundung_portal_runtime_policy,
            self._wohnungserkundung_frozen_scan_policy,
            scope,
            self._wohnungserkundung_scope_clearance,
            self._wohnungserkundung_frozen_scan_sample,
            lambda stamp_ns: self._wohnungserkundung_exact_time_pose(
                candidate, stamp_ns),
        )

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
        if getattr(self, '_wohnungserkundung_policy_enabled', False):
            payload['wohnungserkundung'] = (
                self._wohnungserkundung_status_extension)
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

    def _wohnungserkundung_bind_costmap_frontier_stage(
            self, intent, candidate: FrontierGoalCandidate, correlation,
            raw_map: OccupancyGrid,
            robot_pose: Optional[Tuple[float, float, float]],
            scope: Optional[AuthorizedExplorationScope],
            ) -> Optional[FrontierGoalCandidate]:
        """Bind NavFn projection only after the same raw-map/scope checks.

        NavFn's current start component may end before the raw SLAM route,
        especially at the LiDAR blind area around the stationary robot.  The
        generic explorer already stages such a goal at the closest safe cell.
        WE may use that stage only when the projected metric point is also
        obstacle-clear, scope-contained and geodesically reachable on the
        exact correlated raw-map revision.  Thus the Costmap cannot widen the
        authorized scope or replace the raw-map safety contract.
        """
        if (
                not isinstance(candidate, FrontierGoalCandidate)
                or robot_pose is None
                or not hasattr(self, '_global_costmap')):
            return None
        checked = self._costmap_reachable_goal(
            (candidate.target_x_m, candidate.target_y_m),
            (candidate.target_x_m, candidate.target_y_m),
            (robot_pose[0], robot_pose[1]),
        )
        if checked is None:
            return None
        (goal_x, goal_y), projected = checked
        if not projected:
            return candidate
        goal_col, goal_row = self._world_to_grid(
            goal_x, goal_y, raw_map.info)
        delta_x = candidate.frontier_x_m - goal_x
        delta_y = candidate.frontier_y_m - goal_y
        goal_yaw = (
            candidate.target_yaw_rad
            if math.hypot(delta_x, delta_y) <= 1e-9
            else math.atan2(delta_y, delta_x))
        staged = replace(
            candidate,
            target_x_m=goal_x,
            target_y_m=goal_y,
            target_yaw_rad=goal_yaw,
            target_row=goal_row,
            target_col=goal_col,
        )
        origin = raw_map.info.origin
        try:
            route_length_m = revalidate_active_frontier_goal_candidate(
                intent,
                staged,
                correlation,
                width=raw_map.info.width,
                height=raw_map.info.height,
                resolution=raw_map.info.resolution,
                frame_id=raw_map.header.frame_id.strip(),
                origin=(
                    origin.position.x,
                    origin.position.y,
                    origin.position.z,
                    origin.orientation.x,
                    origin.orientation.y,
                    origin.orientation.z,
                    origin.orientation.w,
                ),
                cells=raw_map.data,
                source_stamp_ns=(
                    int(raw_map.header.stamp.sec) * 1_000_000_000
                    + int(raw_map.header.stamp.nanosec)
                ),
                robot_xy=(robot_pose[0], robot_pose[1]),
                policy=self._wohnungserkundung_evidence_policy,
                scope=scope,
                scope_clearance_m=(
                    None if scope is None else
                    self._wohnungserkundung_scope_clearance),
            )
        except FrontierGoalCandidateError:
            return None
        return replace(staged, route_length_m=route_length_m)

    def _wohnungserkundung_refresh_active_frontier_source(
            self, raw_map, correlation, robot_pose, scope):
        """Commit fixed-goal validity before the full policy recomputation.

        The revision-wide task assessment can be substantially more expensive
        than revalidating the one child already in motion.  This fast lane
        changes no target and performs the same raw-map/scope proof; it merely
        prevents a valid child from timing out while unrelated candidates are
        being rescored.
        """
        with self._wohnungserkundung_runtime_lock:
            active_child = self._wohnungserkundung_active_child
        if (
                active_child is None
                or not isinstance(active_child[1], FrontierGoalCandidate)):
            return
        intent, candidate = active_child
        current = False
        reason = 'fixed_goal_invalid:exact_raw_map_unavailable'
        if robot_pose is not None:
            origin = raw_map.info.origin
            try:
                revalidate_active_frontier_goal_candidate(
                    intent,
                    candidate,
                    correlation,
                    width=raw_map.info.width,
                    height=raw_map.info.height,
                    resolution=raw_map.info.resolution,
                    frame_id=raw_map.header.frame_id.strip(),
                    origin=(
                        origin.position.x,
                        origin.position.y,
                        origin.position.z,
                        origin.orientation.x,
                        origin.orientation.y,
                        origin.orientation.z,
                        origin.orientation.w,
                    ),
                    cells=raw_map.data,
                    source_stamp_ns=(
                        int(raw_map.header.stamp.sec) * 1_000_000_000
                        + int(raw_map.header.stamp.nanosec)
                    ),
                    robot_xy=(robot_pose[0], robot_pose[1]),
                    policy=self._wohnungserkundung_evidence_policy,
                    scope=scope,
                    scope_clearance_m=(
                        None if scope is None else
                        self._wohnungserkundung_scope_clearance),
                )
            except FrontierGoalCandidateError as error:
                reason = f'fixed_goal_invalid:{type(error).__name__}'
            else:
                current = True
                reason = 'fixed_goal_revalidated_fast'
        source = (
            intent.intent_id,
            NavigationSourceState(
                intent.context, correlation.map_revision, current),
            reason,
        )
        with self._wohnungserkundung_runtime_lock:
            if self._wohnungserkundung_active_child == active_child:
                self._wohnungserkundung_active_frontier_source = source
                condition = getattr(
                    self, '_wohnungserkundung_runtime_condition', None)
                if condition is not None:
                    condition.notify_all()

    def _wohnungserkundung_costmap_filter_frontier_availability(
            self, availability, tasks, raw_map, correlation, tracks, evidence,
            robot_pose, scope):
        """Withhold frontier tasks that cannot make a real Nav2-sized step."""
        if not all(isinstance(item, TaskAvailability) for item in availability):
            return availability
        if robot_pose is None:
            return tuple(
                replace(
                    item,
                    state=TaskAvailabilityState.TEMPORARILY_BLOCKED,
                    reason='nav2_costmap_route_unavailable',
                    recheck_condition=(
                        'reassess_after_costmap_or_map_update'),
                ) if item.state is TaskAvailabilityState.AVAILABLE else item
                for item in availability)
        tasks_by_id = {
            task.task_id: task for task in tasks
            if (
                isinstance(task, RegionTaskSnapshot)
                and task.kind is RegionTaskKind.FRONTIER)
        }
        origin = raw_map.info.origin
        filtered = []
        for index, item in enumerate(availability):
            if item.state is not TaskAvailabilityState.AVAILABLE:
                filtered.append(item)
                continue
            task = tasks_by_id.get(item.task_id)
            staged = None
            if task is not None:
                intent = ExplorationGoalIntent(
                    intent_id=(
                        f'costmap-preview-{correlation.map_revision}-{index}'),
                    task_id=task.task_id,
                    region_id=task.region_id,
                    context=correlation.context,
                    map_revision=correlation.map_revision,
                )
                try:
                    candidate = build_frontier_goal_candidate(
                        intent,
                        correlation,
                        width=raw_map.info.width,
                        height=raw_map.info.height,
                        resolution=raw_map.info.resolution,
                        frame_id=raw_map.header.frame_id.strip(),
                        origin=(
                            origin.position.x,
                            origin.position.y,
                            origin.position.z,
                            origin.orientation.x,
                            origin.orientation.y,
                            origin.orientation.z,
                            origin.orientation.w,
                        ),
                        cells=raw_map.data,
                        source_stamp_ns=(
                            int(raw_map.header.stamp.sec) * 1_000_000_000
                            + int(raw_map.header.stamp.nanosec)
                        ),
                        robot_xy=(robot_pose[0], robot_pose[1]),
                        task=task,
                        tracks=tracks,
                        evidence=evidence,
                        policy=self._wohnungserkundung_evidence_policy,
                        scope=scope,
                        scope_clearance_m=(
                            None if scope is None else
                            self._wohnungserkundung_scope_clearance),
                    )
                    staged = (
                        self._wohnungserkundung_bind_costmap_frontier_stage(
                            intent,
                            candidate,
                            correlation,
                            raw_map,
                            robot_pose,
                            scope,
                        ))
                except FrontierGoalCandidateError:
                    staged = None
            if staged is None:
                reason = 'nav2_costmap_route_unavailable'
            elif math.hypot(
                    staged.target_x_m - robot_pose[0],
                    staged.target_y_m - robot_pose[1]) < self._min_goal_dist_m:
                reason = 'nav2_costmap_stage_too_short'
            else:
                filtered.append(item)
                continue
            filtered.append(replace(
                item,
                state=TaskAvailabilityState.TEMPORARILY_BLOCKED,
                reason=reason,
                recheck_condition='reassess_after_costmap_or_map_update',
            ))
        return tuple(filtered)

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
            stop_requested=lambda: False, *,
            goal_yaw: Optional[float] = None,
            progress_observer=None) -> str:
        """Sendet EIN Fahrziel an Nav2 und wartet (blockierend) auf das Ergebnis.

        Rueckgabe: 'success' | 'aborted' | 'rejected' | 'timeout'
        """
        if not self._nav_client.wait_for_server(timeout_sec=5.0):
            self.get_logger().error("Nav2-Action 'navigate_to_pose' nicht erreichbar")
            return 'rejected'
        if progress_observer is not None:
            if not callable(progress_observer):
                return 'error'
            try:
                if progress_observer() is not True:
                    return 'error'
            except Exception:
                return 'error'

        ps = PoseStamped()
        ps.header.frame_id = self._global_frame
        ps.header.stamp = self.get_clock().now().to_msg()
        ps.pose.position.x = x
        ps.pose.position.y = y
        rxy = self._robot_xy()
        yaw = (
            goal_yaw if goal_yaw is not None
            else math.atan2(y - rxy[1], x - rxy[0]) if rxy else 0.0)
        if not isinstance(yaw, (int, float)) or not math.isfinite(float(yaw)):
            return 'rejected'
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
            if stop_reason is None and progress_observer is not None:
                try:
                    monitor_current = progress_observer() is True
                except Exception:
                    monitor_current = False
                if not monitor_current:
                    stop_reason = 'error'
                    stop_reason_started = now
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
        if stop_reason is None and progress_observer is not None:
            try:
                if progress_observer() is not True:
                    return 'error'
            except Exception:
                return 'error'
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
            completion = None
            if getattr(self, '_wohnungserkundung_navigation_enabled', False):
                with self._wohnungserkundung_runtime_lock:
                    completion = (
                        getattr(
                            self,
                            '_wohnungserkundung_completion_assessment',
                            None))
            if completion is not None:
                projection = project_completion_for_legacy(completion)
                state = projection.legacy_status_state
                self._status_phase = {
                    ExplorationResultState.COMPLETE_ACCESSIBLE: 'complete',
                    ExplorationResultState.PARTIAL: 'partial',
                    ExplorationResultState.ABORTED: 'failed',
                    ExplorationResultState.CANCELED: 'canceled',
                    ExplorationResultState.IN_PROGRESS: 'running',
                }[completion.state]
            elif goal_handle.is_cancel_requested or (
                    'abgebrochen' in result.message):
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

    def _wohnungserkundung_source_state(
            self, intent, candidate) -> NavigationSourceState:
        """Read whether current exact evidence still confirms the child goal.

        A newer map revision is not by itself an invalidation.  During the
        bounded status-timer hand-off it remains pending. Its deadline starts
        at the first unconfirmed revision for this intent, not at every later
        raw-map update. Afterwards a frontier child keeps its fixed metric
        target only while that target is revalidated on the exact newer raw
        map; a portal child still requires the exact current metric candidate.
        Any changed or withheld source evidence invalidates immediately.
        """
        with self._region_graph_shadow_lock:
            correlation = self._region_graph_shadow_latest_correlation
            received_at = getattr(
                self, '_region_graph_shadow_latest_correlation_received_at',
                None)
        if correlation is None:
            return NavigationSourceState(
                intent.context, intent.map_revision, False)
        exact_original = (
            correlation.context == intent.context
            and correlation.map_revision == intent.map_revision
            and correlation.fingerprint == candidate.source_fingerprint
            and correlation.source_stamp_ns == candidate.source_stamp_ns
            and correlation.context.frame_id == candidate.frame_id
        )
        if exact_original:
            self._clear_wohnungserkundung_unconfirmed_intent(intent)
            return NavigationSourceState(
                correlation.context, correlation.map_revision, True)
        # SLAM can republish an unchanged occupancy grid with a fresh source
        # stamp while Nav2 is executing a fixed Frontier goal.  The map
        # fingerprint covers the metric geometry that was validated for this
        # goal, so such a duplicate is current evidence, not a reason to
        # cancel and redispatch it.  Any content/context/frame change still
        # takes the normal exact newer-map revalidation path below.
        if (
                isinstance(candidate, FrontierGoalCandidate)
                and correlation.context == intent.context
                and correlation.map_revision >= intent.map_revision
                and correlation.fingerprint == candidate.source_fingerprint
                and correlation.context.frame_id == candidate.frame_id):
            self._clear_wohnungserkundung_unconfirmed_intent(intent)
            return NavigationSourceState(
                correlation.context, correlation.map_revision, True)
        if (
                correlation.context != intent.context
                or correlation.map_revision < intent.map_revision
                or correlation.context.frame_id != candidate.frame_id):
            return NavigationSourceState(
                correlation.context, correlation.map_revision, False)
        with self._wohnungserkundung_runtime_lock:
            processed_revision = getattr(
                self, '_wohnungserkundung_policy_processed_revision', None)
            snapshot = self._wohnungserkundung_navigation_snapshot
            active_frontier_source = getattr(
                self, '_wohnungserkundung_active_frontier_source', None)
        if (
                isinstance(candidate, FrontierGoalCandidate)
                and active_frontier_source is not None
                and active_frontier_source[0] == intent.intent_id
                and active_frontier_source[1].context == intent.context
                and active_frontier_source[1].map_revision
                == correlation.map_revision):
            if active_frontier_source[1].current:
                self._clear_wohnungserkundung_unconfirmed_intent(intent)
            return active_frontier_source[1]
        if processed_revision is None or processed_revision < (
                correlation.map_revision):
            pending = self._wohnungserkundung_unconfirmed_within_grace(
                intent, received_at)
            return NavigationSourceState(
                correlation.context,
                intent.map_revision if pending else correlation.map_revision,
                pending,
            )
        if isinstance(candidate, FrontierGoalCandidate):
            current = (
                active_frontier_source is not None
                and active_frontier_source[0] == intent.intent_id
                and active_frontier_source[1].context == intent.context
                and active_frontier_source[1].map_revision
                == correlation.map_revision
                and active_frontier_source[1].current)
        else:
            current = (
                snapshot is not None
                and snapshot[1].map_revision == correlation.map_revision
                and self._wohnungserkundung_same_metric_goal(
                    candidate, snapshot[1]))
        if current:
            self._clear_wohnungserkundung_unconfirmed_intent(intent)
        return NavigationSourceState(
            correlation.context, correlation.map_revision, current)

    def _wohnungserkundung_unconfirmed_within_grace(
            self, intent, received_at):
        """Bound pending-policy grace to one interval per active intent."""
        now = time.monotonic()
        with self._wohnungserkundung_runtime_lock:
            tracked_intent = getattr(
                self, '_wohnungserkundung_unconfirmed_intent_id', None)
            started_at = getattr(
                self, '_wohnungserkundung_unconfirmed_since', None)
            if tracked_intent != intent.intent_id or started_at is None:
                # ``received_at`` is used only for the initial hand-off. A
                # missing or non-monotonic value cannot widen the allowance.
                started_at = (
                    received_at if received_at is not None
                    and received_at <= now else now)
                self._wohnungserkundung_unconfirmed_intent_id = (
                    intent.intent_id)
                self._wohnungserkundung_unconfirmed_since = started_at
            return 0.0 <= now - started_at <= 1.25

    def _clear_wohnungserkundung_unconfirmed_intent(self, intent):
        """Forget a grace interval only after a valid confirmation."""
        lock = getattr(self, '_wohnungserkundung_runtime_lock', None)
        if lock is None:
            # Geometry-only unit callers do not initialize the WE runtime.
            return
        with lock:
            if getattr(
                    self, '_wohnungserkundung_unconfirmed_intent_id', None
                    ) == intent.intent_id:
                self._wohnungserkundung_unconfirmed_intent_id = None
                self._wohnungserkundung_unconfirmed_since = None

    @staticmethod
    def _wohnungserkundung_same_metric_goal(previous, current):
        """Require stable identity and bit-close metric goal across revisions."""
        if type(previous) is not type(current):
            return False
        common = (
            previous.task_id == current.task_id
            and previous.region_id == current.region_id
            and previous.frame_id == current.frame_id
            and math.isclose(
                previous.target_x_m, current.target_x_m,
                rel_tol=0.0, abs_tol=1e-9)
            and math.isclose(
                previous.target_y_m, current.target_y_m,
                rel_tol=0.0, abs_tol=1e-9)
            and math.isclose(
                previous.target_yaw_rad, current.target_yaw_rad,
                rel_tol=0.0, abs_tol=1e-9)
        )
        if isinstance(previous, FrontierGoalCandidate):
            return common and previous.frontier_id == current.frontier_id
        if isinstance(previous, PortalGoalCandidate):
            return (
                common
                and previous.portal_id == current.portal_id
                and previous.direction is current.direction
                and previous.scope_id == current.scope_id
                and previous.scope_fingerprint == current.scope_fingerprint)
        return False

    def _current_wohnungserkundung_navigation_target(self):
        """Return one atomic unconsumed preview only while its source matches."""
        with self._wohnungserkundung_runtime_lock:
            snapshot = self._wohnungserkundung_navigation_snapshot
            consumed = self._wohnungserkundung_consumed_intent_id
            pending = getattr(
                self, '_wohnungserkundung_pending_frontier_resolution', None)
        if snapshot is None or snapshot[0].intent_id == consumed:
            return None
        intent, candidate = snapshot
        # A reached metric target is not new work while its frontier result
        # still awaits a newer raw-map observation.  A new intent for exactly
        # that same target must not repeat the just-finished child.  Another
        # revalidated metric target of the same task remains eligible.
        if pending is not None and self._wohnungserkundung_same_metric_goal(
                pending[0], candidate):
            return None
        # The grace interval is solely for a child that was already dispatched.
        # An unconsumed preview must remain exact and never become a new goal
        # merely because policy processing is temporarily behind a raw map.
        with self._region_graph_shadow_lock:
            correlation = self._region_graph_shadow_latest_correlation
        if correlation is None:
            return None
        if correlation.map_revision != intent.map_revision:
            # SLAM may republish byte-identical maps faster than the one-Hz
            # policy projection.  This is not a changed map decision: the
            # current raw-map fingerprint proves the same metric target and
            # scope evidence.  Before the first dispatch, additionally demand
            # a fresh, unprojected Nav2-costmap route from the current pose.
            # A changed fingerprint, context, frame, stale Costmap or a
            # projected/zero-length route remains fail-closed until a fresh
            # policy snapshot supplies a new exact candidate.
            if not (
                    isinstance(candidate, FrontierGoalCandidate)
                    and correlation.context == intent.context
                    and correlation.context.frame_id == candidate.frame_id
                    and correlation.map_revision > intent.map_revision
                    and correlation.fingerprint
                    == candidate.source_fingerprint):
                return None
            robot_pose = self._robot_pose()
            if robot_pose is None:
                return None
            checked = self._costmap_reachable_goal(
                (candidate.target_x_m, candidate.target_y_m),
                (candidate.target_x_m, candidate.target_y_m),
                (robot_pose[0], robot_pose[1]),
            )
            if checked is None or checked[1] or math.hypot(
                    candidate.target_x_m - robot_pose[0],
                    candidate.target_y_m - robot_pose[1]) < (
                        self._min_goal_dist_m):
                return None
            return snapshot
        source = self._wohnungserkundung_source_state(intent, candidate)
        if not source.current:
            return None
        return snapshot

    def _record_revalidated_frontier_attempt(
            self, intent, attempt, timeout_s=3.0):
        """Atomically bind a child result to the committed policy revision.

        The status callback first advances the stateful task policy and then
        revalidates the fixed metric goal.  A child may finish inside that
        short calculation window.  A raw-map revalidation can legitimately
        arrive *ahead* of the next one-Hz policy commit while Nav2 reports its
        terminal result.  Wait for that policy commit instead of treating the
        newer, still-current source as an error.  Never accept an older source
        or relax its freshness decision.
        """
        deadline = time.monotonic() + timeout_s
        condition = self._wohnungserkundung_runtime_condition
        with condition:
            while True:
                task_policy = self._wohnungserkundung_task_policy_session
                if task_policy is None:
                    raise RuntimeError(
                        'Aufgabenpolicy fehlt bei terminalem Kindziel')
                fault = getattr(
                    self, '_wohnungserkundung_policy_fault', None)
                if fault is not None:
                    raise RuntimeError(
                        'Frontierabschluss wartet auf fehlerhaften '
                        f'Policy-Commit ({fault})')
                latest_revision = task_policy.latest_assessment_revision
                processed_revision = getattr(
                    self,
                    '_wohnungserkundung_policy_processed_revision',
                    None,
                )
                active_source = getattr(
                    self,
                    '_wohnungserkundung_active_frontier_source',
                    None,
                )
                source_matches_intent = (
                    active_source is not None
                    and active_source[0] == intent.intent_id
                    and active_source[1].context == intent.context)
                if source_matches_intent and not active_source[1].current:
                    raise RuntimeError(
                        'Frontierabschluss verlor aktuelle Revalidierung')
                if (
                        latest_revision is not None
                        and processed_revision == latest_revision
                        and source_matches_intent
                        and active_source[1].map_revision
                        == latest_revision):
                    task_policy.record_revalidated_attempt(
                        attempt, latest_revision)
                    return
                remaining = deadline - time.monotonic()
                if remaining <= 0.0:
                    raise RuntimeError(
                        'Frontierabschluss wartet vergeblich auf atomaren '
                        'Policy-Commit')
                condition.wait(timeout=remaining)

    def _run_wohnungserkundung_child(
            self, navigation_session, intent, candidate,
            goal_handle, overall_expired):
        """Dispatch exactly one validated child through the existing client."""
        portal_monitor = None
        if isinstance(candidate, PortalGoalCandidate):
            monitor_factory = getattr(
                self, '_wohnungserkundung_portal_monitor_factory', None)
            if monitor_factory is None:
                raise RuntimeError(
                    'Portalziel besitzt keinen Traversierungsmonitor')
            if not getattr(
                    self,
                    '_wohnungserkundung_accessible_scope_verified', False):
                raise RuntimeError(
                    'Portalziel besitzt keinen verifizierten Auftragsscope')
            with self._region_graph_shadow_lock:
                portals = tuple(
                    portal for portal
                    in self._region_graph_shadow.portal_snapshots()
                    if portal.portal_id == candidate.portal_id)
            if len(portals) != 1:
                raise RuntimeError(
                    'Portalziel braucht genau einen aktuellen Portalbeleg')
            portal_monitor = monitor_factory(candidate, portals[0])
            if (
                    portal_monitor is None
                    or not callable(getattr(portal_monitor, 'observe', None))
                    or not callable(getattr(portal_monitor, 'finish', None))):
                raise RuntimeError(
                    'Portalmonitor besitzt keinen Laufzeitvertrag')
        with self._wohnungserkundung_runtime_lock:
            if self._wohnungserkundung_active_child is not None:
                raise RuntimeError(
                    'Wohnungserkundung besitzt bereits ein aktives Kindziel')
            self._wohnungserkundung_active_child = (intent, candidate)
            if isinstance(candidate, FrontierGoalCandidate):
                self._wohnungserkundung_active_frontier_source = (
                    intent.intent_id,
                    NavigationSourceState(
                        intent.context, intent.map_revision, True),
                    'initial_exact_source',
                )
        try:
            run = navigation_session.run(
                intent,
                candidate,
                lambda selected, stop_requested: self._navigate_to(
                    selected.target_x_m,
                    selected.target_y_m,
                    self._goal_timeout_s,
                    stop_requested=stop_requested,
                    goal_yaw=selected.target_yaw_rad,
                    progress_observer=(
                        None if portal_monitor is None
                        else portal_monitor.observe),
                ),
                lambda: self._wohnungserkundung_source_state(
                    intent, candidate),
                lambda: goal_handle.is_cancel_requested,
                overall_expired,
            )
            portal_outcome = None
            if portal_monitor is not None:
                portal_outcome = portal_monitor.finish(
                    execution_succeeded=(
                        run.navigation_status == 'success'),
                    evaluated_at_ns=int(
                        self.get_clock().now().nanoseconds),
                )
                if not isinstance(
                        portal_outcome, PortalTraversalRuntimeOutcome):
                    raise RuntimeError(
                        'Portalmonitor lieferte kein typisiertes Ergebnis')
                if portal_outcome.confirmed:
                    assessment = portal_outcome.assessment
                    if (
                            assessment is None
                            or assessment.traversal_event is None):
                        raise RuntimeError(
                            'Bestaetigter Portalmonitor besitzt kein Ereignis')
                    with self._region_graph_shadow_lock:
                        traversal_result = (
                            self._region_graph_shadow
                            .record_validated_traversal(
                                assessment.traversal_event,
                                observed_monotonic_seconds=time.monotonic(),
                            ))
                    if not traversal_result.graph.entered:
                        raise RuntimeError(
                            'Portalereignis hat keine Region betreten')
            frontier_attempt_recorded = False
            if (
                    portal_outcome is None
                    and run.disposition.attempt is not None
                    and isinstance(candidate, FrontierGoalCandidate)):
                self._record_revalidated_frontier_attempt(
                    intent, run.disposition.attempt)
                frontier_attempt_recorded = True
            with self._wohnungserkundung_runtime_lock:
                task_policy = self._wohnungserkundung_task_policy_session
                if task_policy is None:
                    raise RuntimeError(
                        'Aufgabenpolicy fehlt bei terminalem Kindziel')
                if (
                        portal_outcome is not None
                        and run.navigation_status == 'success'
                        and not portal_outcome.confirmed):
                    task_policy.record_attempt(
                        retry_attempt_from_portal_outcome(
                            intent, portal_outcome))
                elif (
                        portal_outcome is None
                        and run.disposition.attempt is not None):
                    if not frontier_attempt_recorded:
                        task_policy.record_attempt(run.disposition.attempt)
                elif (
                        portal_outcome is not None
                        and run.navigation_status != 'success'
                        and run.disposition.attempt is not None):
                    task_policy.record_attempt(run.disposition.attempt)
                if portal_outcome is not None:
                    self._wohnungserkundung_portal_traversal_status = {
                        'state': (
                            'confirmed'
                            if portal_outcome.confirmed else 'unconfirmed'),
                        'task_id': intent.task_id,
                        'portal_id': candidate.portal_id,
                        'map_revision': intent.map_revision,
                        'sample_count': portal_outcome.sample_count,
                        'reason': portal_outcome.reason,
                    }
                self._wohnungserkundung_consumed_intent_id = intent.intent_id
            return run, portal_outcome
        finally:
            with self._wohnungserkundung_runtime_lock:
                self._wohnungserkundung_active_child = None
                if (
                        getattr(
                            self,
                            '_wohnungserkundung_active_frontier_source',
                            None) is not None
                        and self._wohnungserkundung_active_frontier_source[0]
                        == intent.intent_id):
                    self._wohnungserkundung_active_frontier_source = None

    def _store_wohnungserkundung_completion(self, completion):
        """Publish one immutable completion view beneath the existing status."""
        with self._wohnungserkundung_runtime_lock:
            self._wohnungserkundung_completion_assessment = completion
            extension = dict(getattr(
                self, '_wohnungserkundung_status_extension', {}))
            extension['runtime_result'] = build_we_status_extension(completion)
            self._wohnungserkundung_status_extension = extension

    def _observe_wohnungserkundung_completion(self, session, stateful):
        """Consume each exact stateful map revision at most once."""
        passive = stateful.passive
        if session is None:
            session = ExplorationCompletionSession(
                passive.context, self._wohnungserkundung_completion_policy)
        elif session.latest_revision is not None and (
                passive.source_map_revision <= session.latest_revision):
            return session, None
        with self._wohnungserkundung_runtime_lock:
            active_child = self._wohnungserkundung_active_child
        result = session.observe(CompletionObservation(
            observation_id=(
                f'runtime-completion-{passive.source_map_revision}'),
            context=passive.context,
            map_revision=passive.source_map_revision,
            assessment=stateful,
            accessible_scope=(
                AccessibleScopeState.VERIFIED
                if self._wohnungserkundung_accessible_scope_verified
                else AccessibleScopeState.UNVERIFIED),
            child_navigation=(
                ChildNavigationState.IDLE
                if active_child is None else ChildNavigationState.ACTIVE),
            termination=TerminationCause.NONE,
            reason='runtime_policy_observation',
        ))
        self._store_wohnungserkundung_completion(result)
        return session, result

    def _finish_wohnungserkundung_completion(
            self, goal_handle, completion, reached_goals):
        """Apply the documented additive projection to the legacy Action."""
        projection = project_completion_for_legacy(completion)
        result = ExploreArea.Result()
        result.success = bool(projection.legacy_action_success)
        result.message = {
            ExplorationResultState.COMPLETE_ACCESSIBLE: (
                'Zugaenglicher Erkundungsbereich durch mehrere frische '
                'Kartenrevisionen abgeschlossen'),
            ExplorationResultState.PARTIAL: (
                'Wohnungserkundungsbudget erreicht; belegter Teilstand, '
                'kein Vollabschluss'),
            ExplorationResultState.ABORTED: (
                f'Wohnungserkundung sicher abgebrochen: {completion.reason}'),
            ExplorationResultState.CANCELED: (
                'Wohnungserkundung durch Nutzer storniert'),
        }[completion.state]
        if completion.state is ExplorationResultState.COMPLETE_ACCESSIBLE:
            self._coverage_complete = True
            goal_handle.succeed()
        elif completion.state is ExplorationResultState.PARTIAL:
            goal_handle.succeed()
        elif completion.state is ExplorationResultState.ABORTED:
            goal_handle.abort()
        else:
            goal_handle.canceled()
        self._store_wohnungserkundung_completion(completion)
        return self._finish_result(result, reached_goals)

    def _execute_wohnungserkundung_navigation(
            self, goal_handle, overall_timeout):
        """Run the opt-in WE child loop without legacy frontier competition."""
        self._coverage_ratio = 0.0
        self._reachable_area_m2 = 0.0
        self._covered_area_m2 = 0.0
        self._frontiers_visited_status = 0
        self._frontiers_remaining = 0
        self._coverage_complete = False
        with self._wohnungserkundung_runtime_lock:
            self._wohnungserkundung_active_child = None
            self._wohnungserkundung_active_frontier_source = None
            self._wohnungserkundung_consumed_intent_id = None
            self._wohnungserkundung_completion_assessment = None
            self._wohnungserkundung_pending_frontier_resolution = None
            self._wohnungserkundung_frontier_resolution_status = {
                'state': 'none',
            }
            self._wohnungserkundung_portal_traversal_status = {
                'state': 'none',
            }
        self._status_phase = 'we_waiting_for_goal'
        self._status_message = (
            'Wohnungserkundung aktiv; warte auf aktuellen Zielkandidaten.')
        self._publish_status('running')
        started = time.monotonic()
        navigation_session = None
        completion_session = None
        reached_goals = 0
        attempted_goals = 0
        # The WE action owns a separate frontier loop and therefore does not
        # pass through the legacy loop below, where the controlled initial
        # observation normally runs.  Do not select a translational frontier
        # from the one-sided start map: once the exact WE sources are fresh,
        # reuse the already gated, odometry-measured in-place scan before the
        # first child target.  A missing or stale policy snapshot is never a
        # reason to rotate.
        initial_scan_pending = bool(getattr(
            self, '_initial_scan_enabled', False))

        def overall_expired():
            return (
                overall_timeout > 0.0
                and time.monotonic() - started >= overall_timeout)

        def terminate(cause, reason):
            if completion_session is None:
                completion = completion_from_termination(
                    cause,
                    reason,
                    policy=self._wohnungserkundung_completion_policy,
                    return_result=ReturnResultState.NOT_REQUESTED,
                )
            else:
                completion = completion_session.terminate(
                    cause,
                    reason,
                    return_result=ReturnResultState.NOT_REQUESTED,
                )
            return self._finish_wohnungserkundung_completion(
                goal_handle, completion, reached_goals)

        while rclpy.ok():
            if goal_handle.is_cancel_requested:
                return terminate(
                    TerminationCause.USER_CANCELED,
                    'user_canceled_without_active_child')
            if overall_expired():
                return terminate(
                    TerminationCause.BUDGET_EXHAUSTED,
                    'overall_budget_exhausted')

            with self._wohnungserkundung_runtime_lock:
                policy_snapshot = getattr(
                    self, '_wohnungserkundung_policy_snapshot', None)

            # The first full observation is a precondition for WE task
            # creation and completion alike.  In particular, an empty
            # pre-scan task inventory must never satisfy the completion
            # window before it was armed from a real all-around observation.
            if initial_scan_pending:
                passive = getattr(policy_snapshot, 'passive', None)
                if not getattr(passive, 'source_ready', False):
                    time.sleep(0.05)
                    continue
                self._status_phase = 'we_initial_scan'
                self._status_message = (
                    'WE-Quellen sind frisch; kontrollierter 360-Grad-'
                    'Rundblick vor der ersten Zielwahl laeuft.')
                self._publish_status('running')
                scan_status, _achieved = self._scan_in_place(
                    stop_requested=lambda: (
                        goal_handle.is_cancel_requested or overall_expired()))
                if scan_status == 'success':
                    if getattr(
                            self,
                            '_region_graph_shadow_frontier_task_feed',
                            False):
                        with self._region_graph_shadow_lock:
                            self._wohnungserkundung_frontier_feed_armed = True
                            # The latest exact correlation has deliberately
                            # not been consumed while the gate was closed.
                            # Resetting this marker makes the next timer pass
                            # create one task inventory from that fresh map.
                            self._region_graph_shadow_frontier_processed_correlation = (
                                None)
                    initial_scan_pending = False
                    time.sleep(self._replan_period_s)
                    continue
                if goal_handle.is_cancel_requested:
                    return terminate(
                        TerminationCause.USER_CANCELED,
                        'user_canceled_during_initial_scan')
                if overall_expired():
                    return terminate(
                        TerminationCause.BUDGET_EXHAUSTED,
                        'overall_budget_during_initial_scan')
                return terminate(
                    TerminationCause.SYSTEM_FAILURE,
                    f'initial_scan_{scan_status}')

            if policy_snapshot is not None:
                try:
                    completion_session, completion = (
                        self._observe_wohnungserkundung_completion(
                            completion_session, policy_snapshot))
                except Exception as error:
                    return terminate(
                        TerminationCause.SYSTEM_FAILURE,
                        f'completion_observation_{type(error).__name__}')
                if (
                        completion is not None
                        and completion.state is (
                            ExplorationResultState.COMPLETE_ACCESSIBLE)):
                    return self._finish_wohnungserkundung_completion(
                        goal_handle, completion, reached_goals)

            target = self._current_wohnungserkundung_navigation_target()
            if target is None:
                time.sleep(0.05)
                continue
            intent, candidate = target
            if navigation_session is None:
                navigation_session = ExplorationNavigationSession(
                    intent.context)
            elif navigation_session.context != intent.context:
                return terminate(
                    TerminationCause.SYSTEM_FAILURE,
                    'map_context_changed')
            if attempted_goals >= self._max_frontier_goals:
                return terminate(
                    TerminationCause.BUDGET_EXHAUSTED,
                    'goal_budget_exhausted')

            portal_candidate = isinstance(candidate, PortalGoalCandidate)
            self._status_phase = (
                'we_portal_navigation'
                if portal_candidate else 'we_frontier_navigation')
            self._status_message = (
                f'WE-{("Portal" if portal_candidate else "Frontier")}ziel '
                f'{intent.task_id} aus Revision '
                f'{intent.map_revision} wird vom vorhandenen Nav2-Client '
                'angefahren.')
            self._publish_status('running')
            feedback = ExploreArea.Feedback()
            feedback.explored_percent = 100.0 * self._coverage_ratio
            feedback.frontiers_remaining = self._frontiers_remaining
            feedback.current_goal.header.frame_id = candidate.frame_id
            feedback.current_goal.header.stamp = (
                self.get_clock().now().to_msg())
            feedback.current_goal.pose.position.x = candidate.target_x_m
            feedback.current_goal.pose.position.y = candidate.target_y_m
            feedback.current_goal.pose.orientation.z = math.sin(
                candidate.target_yaw_rad / 2.0)
            feedback.current_goal.pose.orientation.w = math.cos(
                candidate.target_yaw_rad / 2.0)
            goal_handle.publish_feedback(feedback)

            run, portal_outcome = self._run_wohnungserkundung_child(
                navigation_session,
                intent,
                candidate,
                goal_handle,
                overall_expired,
            )
            # A raw-map revision that invalidates a child is a safety replan,
            # not a completed navigation attempt.  The overall timeout still
            # bounds repeated revisions, while the goal budget remains for
            # actual Nav2 outcomes.
            if run.stop_cause is NavigationStopCause.SOURCE_INVALIDATED:
                # ``_navigate_to`` has confirmed the child goal stopped
                # because its exact raw-map proof is no longer current.  This
                # is intentionally neither a successful traversal nor a
                # retryable Nav2 failure: wait for the already asynchronous
                # policy refresh and select only a newly proven candidate.
                # Treating the resulting ``canceled`` action outcome as a
                # generic system failure would turn every safe map replan into
                # a terminal WE abort.
                self._status_phase = 'we_replanning_after_source_invalidation'
                self._status_message = (
                    'WE-Ziel wurde nach geaenderter Rohkartenquelle sicher '
                    'gestoppt; warte auf frisch belegten Zielkandidaten.')
                self._publish_status('running')
                time.sleep(self._replan_period_s)
                continue

            attempted_goals += 1
            disposition = run.disposition
            if portal_outcome is not None:
                if portal_outcome.confirmed:
                    reached_goals += 1
                    self._frontiers_visited_status = reached_goals
                    time.sleep(self._replan_period_s)
                    continue
                if run.navigation_status == 'success':
                    time.sleep(self._replan_period_s)
                    continue
            if disposition.state.value == 'progressed':
                reached_goals += 1
                self._frontiers_visited_status = reached_goals
                with self._wohnungserkundung_runtime_lock:
                    self._wohnungserkundung_pending_frontier_resolution = (
                        candidate, disposition)
                    self._wohnungserkundung_frontier_resolution_status = {
                        'state': 'waiting_for_new_map',
                        'task_id': candidate.task_id,
                        'goal_map_revision': candidate.map_revision,
                    }
                time.sleep(self._replan_period_s)
                continue
            if disposition.state.value in {'retry_scheduled', 'reevaluate'}:
                time.sleep(self._replan_period_s)
                continue
            if run.stop_cause is NavigationStopCause.USER_CANCELED:
                cause = TerminationCause.USER_CANCELED
                reason = 'user_canceled_active_child'
            elif run.stop_cause is NavigationStopCause.BUDGET_EXHAUSTED:
                cause = TerminationCause.BUDGET_EXHAUSTED
                reason = 'child_navigation_budget_exhausted'
            else:
                cause = TerminationCause.SYSTEM_FAILURE
                reason = f'child_navigation_{run.navigation_status}'
            return terminate(cause, reason)
        return terminate(TerminationCause.SYSTEM_FAILURE, 'ros_shutdown')

    def _execute_reserved(self, goal_handle):
        req = goal_handle.request
        overall_timeout = (
            req.timeout_s if req.timeout_s > 0 else self._overall_timeout_s)
        min_frontier_m = (
            req.min_frontier_size_m
            if req.min_frontier_size_m > 0 else self._min_frontier_m)
        return_to_start = req.return_to_start or self._return_to_start_p

        if getattr(self, '_wohnungserkundung_navigation_enabled', False):
            return self._execute_wohnungserkundung_navigation(
                goal_handle, overall_timeout)

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
