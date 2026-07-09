#!/usr/bin/env python3
# ============================================================================
#  explore_node.py  -  Autonome Frontier-Exploration (WP-5, Ebene 1)
#  ---------------------------------------------------------------------------
#  ZWECK:
#    Der Roboter erkundet die Wohnung SELBSTSTAENDIG und ZIELGERICHTET -
#    NICHT per Zufallsgenerator. Er nutzt die "Frontier"-Methode:
#      * Eine Frontier ist die Grenze zwischen bekannt-freiem und noch
#        unbekanntem Raum in der SLAM-Karte.
#      * Der Node sucht alle Frontiers, bewertet sie (Kosten/Nutzen) und
#        schickt die beste als Fahrziel an Nav2.
#      * Ist die naechste Frontier erreicht, wiederholt sich das - bis keine
#        Frontiers mehr uebrig sind: dann ist die Wohnung vollstaendig kartiert.
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
#
#  ALLE PARAMETER -> config/explore_params.yaml (nur dort aendern!).
#
#  HINWEIS: Wie die uebrigen Pakete ist dieser Node noch NICHT in einer
#  ROS-Umgebung kompiliert/getestet worden. API-Stand: ROS 2 Humble.
# ============================================================================

import math
import threading
import time
from collections import deque
from typing import List, Optional, Tuple

import numpy as np

import rclpy
from rclpy.node import Node
from rclpy.action import ActionServer, ActionClient, CancelResponse, GoalResponse
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor

from nav_msgs.msg import OccupancyGrid
from geometry_msgs.msg import PoseStamped, Point
from visualization_msgs.msg import Marker, MarkerArray
from action_msgs.msg import GoalStatus
from nav2_msgs.action import NavigateToPose
from robot_interfaces.action import ExploreArea

import tf2_ros


class Frontier:
    """Eine zusammenhaengende Frontier-Region (Grenze frei<->unbekannt)."""
    def __init__(self, centroid_world: Tuple[float, float], size_cells: int):
        self.cx = centroid_world[0]      # Schwerpunkt X in Weltkoordinaten [m]
        self.cy = centroid_world[1]      # Schwerpunkt Y in Weltkoordinaten [m]
        self.size = size_cells           # Anzahl Frontier-Zellen (Nutzen-Mass)
        self.cost = 0.0                  # berechnete Gesamtkosten (kleiner = besser)


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
        self._min_goal_dist_m   = float(self.declare_parameter('min_goal_distance_m', 0.30).value)
        self._blacklist_radius  = float(self.declare_parameter('blacklist_radius_m', 0.35).value)
        self._return_to_start_p = bool(self.declare_parameter('return_to_start', False).value)
        self._visualize         = bool(self.declare_parameter('visualize', True).value)
        self._marker_topic      = self.declare_parameter('marker_topic', '/explore/frontiers').value

        # -------------------------------------------------------------------
        #  Laufzeit-Zustand
        # -------------------------------------------------------------------
        self._map: Optional[OccupancyGrid] = None
        self._blacklist: List[Tuple[float, float]] = []   # gescheiterte Ziele (Weltkoord.)
        self._start_xy: Optional[Tuple[float, float]] = None

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

    # ======================= Karten-Eingang =============================
    def _on_map(self, msg: OccupancyGrid):
        self._map = msg

    # ======================= Roboterpose via TF =========================
    def _robot_xy(self) -> Optional[Tuple[float, float]]:
        try:
            t = self._tf_buffer.lookup_transform(
                self._global_frame, self._robot_base_frame, rclpy.time.Time())
            return (t.transform.translation.x, t.transform.translation.y)
        except Exception as exc:  # TransformException u.a.
            self.get_logger().warn(
                f"TF {self._global_frame}->{self._robot_base_frame} fehlt: {exc}",
                throttle_duration_sec=5.0)
            return None

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
        # Annahme: Karten-Origin ohne Rotation (bei 2D-SLAM-Karten ueblich yaw=0).
        wx = info.origin.position.x + (col + 0.5) * info.resolution
        wy = info.origin.position.y + (row + 0.5) * info.resolution
        return wx, wy

    # ======================= Bewertung / Auswahl ========================
    def _rank_frontiers(self, frontiers: List[Frontier], robot_xy: Tuple[float, float],
                        res: float) -> List[Frontier]:
        rx, ry = robot_xy
        candidates: List[Frontier] = []
        for f in frontiers:
            dist = math.hypot(f.cx - rx, f.cy - ry)
            if dist < self._min_goal_dist_m:
                continue   # zu nah (quasi schon erreicht)
            if self._is_blacklisted(f.cx, f.cy):
                continue   # zuvor gescheitertes Ziel meiden
            # Kosten/Nutzen (Idee wie explore_lite):
            #   naeher  -> guenstiger (potential_scale * Distanz)
            #   groesser-> attraktiver (gain_scale * Frontier-Ausdehnung)
            f.cost = self._potential_scale * dist - self._gain_scale * (f.size * res)
            candidates.append(f)
        candidates.sort(key=lambda fr: fr.cost)   # kleinste Kosten zuerst
        return candidates

    def _is_blacklisted(self, x: float, y: float) -> bool:
        for bx, by in self._blacklist:
            if math.hypot(x - bx, y - by) < self._blacklist_radius:
                return True
        return False

    @staticmethod
    def _progress_percent(grid: OccupancyGrid) -> float:
        data = np.asarray(grid.data, dtype=np.int16)
        known = int(np.count_nonzero(data >= 0))
        return 100.0 * known / max(1, data.size)

    # ======================= Nav2 anfahren ==============================
    def _navigate_to(self, x: float, y: float, timeout_s: float) -> str:
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

        done = threading.Event()
        holder = {'status': None, 'handle': None}

        def _on_result(fut):
            try:
                holder['status'] = fut.result().status
            except Exception:
                holder['status'] = 'error'
            done.set()

        def _on_goal(fut):
            gh = fut.result()
            if not gh.accepted:
                holder['status'] = 'rejected'
                done.set()
                return
            holder['handle'] = gh
            gh.get_result_async().add_done_callback(_on_result)

        self._nav_client.send_goal_async(goal).add_done_callback(_on_goal)

        waited = done.wait(timeout=timeout_s if timeout_s > 0 else None)
        if not waited:
            if holder['handle'] is not None:
                holder['handle'].cancel_goal_async()   # Nav-Ziel abbrechen
            return 'timeout'
        if holder['status'] == GoalStatus.STATUS_SUCCEEDED:
            return 'success'
        if holder['status'] == 'rejected':
            return 'rejected'
        return 'aborted'

    # ======================= Action-Server ==============================
    def _goal_cb(self, goal_request) -> GoalResponse:
        return GoalResponse.ACCEPT

    def _cancel_cb(self, goal_handle) -> CancelResponse:
        return CancelResponse.ACCEPT

    def _execute(self, goal_handle):
        """Der eigentliche Explorations-Loop (laeuft bis fertig/abgebrochen)."""
        req = goal_handle.request
        overall_timeout = req.timeout_s if req.timeout_s > 0 else self._overall_timeout_s
        min_frontier_m = req.min_frontier_size_m if req.min_frontier_size_m > 0 else self._min_frontier_m
        return_to_start = req.return_to_start or self._return_to_start_p

        self._blacklist.clear()
        self._start_xy = None
        frontiers_visited = 0
        t_start = time.monotonic()
        result = ExploreArea.Result()

        self.get_logger().info("Exploration gestartet.")

        while rclpy.ok():
            # 1) Abbruch durch Aufrufer?
            if goal_handle.is_cancel_requested:
                goal_handle.canceled()
                result.success = False
                result.message = 'Erkundung abgebrochen'
                result.frontiers_visited = frontiers_visited
                self.get_logger().info("Exploration abgebrochen.")
                return result

            # 2) Gesamt-Zeitlimit?
            if overall_timeout > 0 and (time.monotonic() - t_start) > overall_timeout:
                result.success = True
                result.message = 'Zeitlimit erreicht - Erkundung sauber beendet'
                break

            # 3) Voraussetzungen: Karte + Roboterpose vorhanden?
            grid = self._map
            if grid is None:
                self.get_logger().warn("Warte auf Karte ...", throttle_duration_sec=5.0)
                time.sleep(0.5)
                continue
            robot_xy = self._robot_xy()
            if robot_xy is None:
                time.sleep(0.5)
                continue
            if self._start_xy is None:
                self._start_xy = robot_xy   # Startpose fuer return_to_start merken

            # 4) Frontiers finden + bewerten
            frontiers = self._detect_frontiers(grid, min_frontier_m)
            if self._visualize:
                self._publish_markers(frontiers, grid.header.frame_id)
            candidates = self._rank_frontiers(frontiers, robot_xy, grid.info.resolution)

            # 5) Keine offenen Frontiers -> Wohnung vollstaendig erkundet
            if not candidates:
                result.success = True
                result.message = 'Keine offenen Frontiers mehr - Wohnung vollstaendig erkundet'
                break

            best = candidates[0]

            # 6) Feedback an den Aufrufer (GUI/BT)
            fb = ExploreArea.Feedback()
            fb.explored_percent = self._progress_percent(grid)
            fb.frontiers_remaining = len(candidates)
            goal_pose = PoseStamped()
            goal_pose.header.frame_id = self._global_frame
            goal_pose.header.stamp = self.get_clock().now().to_msg()
            goal_pose.pose.position.x = best.cx
            goal_pose.pose.position.y = best.cy
            goal_pose.pose.orientation.w = 1.0
            fb.current_goal = goal_pose
            goal_handle.publish_feedback(fb)

            # 7) Beste Frontier anfahren
            self.get_logger().info(
                f"Fahre zu Frontier ({best.cx:.2f}, {best.cy:.2f}), "
                f"Groesse={best.size}, offen={len(candidates)}")
            status = self._navigate_to(best.cx, best.cy, self._goal_timeout_s)

            if status == 'success':
                frontiers_visited += 1
                time.sleep(self._replan_period_s)   # Karte kurz aktualisieren lassen
            else:
                # Ziel blacklisten, damit wir uns nicht festfahren
                self._blacklist.append((best.cx, best.cy))
                self.get_logger().warn(
                    f"Ziel {status} - blacklistet ({best.cx:.2f}, {best.cy:.2f})")
                time.sleep(0.5)

        # 8) Optional zur Startpose zurueck
        if return_to_start and self._start_xy is not None:
            self.get_logger().info("Kehre zur Startpose zurueck ...")
            self._navigate_to(self._start_xy[0], self._start_xy[1], self._goal_timeout_s)

        # 9) Ergebnis abschliessen
        result.frontiers_visited = frontiers_visited
        if self._map is not None:
            data = np.asarray(self._map.data, dtype=np.int16)
            free_cells = int(np.count_nonzero(data == 0))
            result.explored_area_m2 = float(free_cells) * (self._map.info.resolution ** 2)
        goal_handle.succeed()
        self.get_logger().info(f"Exploration beendet: {result.message}")
        return result

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
        rclpy.shutdown()


if __name__ == '__main__':
    main()
