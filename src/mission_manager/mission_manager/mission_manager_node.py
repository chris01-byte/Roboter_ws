#!/usr/bin/env python3
# ============================================================================
#  mission_manager_node.py - WP-4 Bedien-Layer (K1: echte Ausfuehrung)
#  ===========================================================================
#  Aufgabe:
#    - Smartphone-/LLM-Auftraege als JSON empfangen (command_json).
#    - Auftrag validieren.
#    - Fuer Typen MIT Behavior-Tree (pick_and_place, explore): den Auftrag als
#      RunMission-Action an den bt_orchestrator schicken -> ECHTE Ausfuehrung.
#      Phase/Fortschritt kommen als Action-Feedback zurueck (Befund K1).
#    - pick_object bleibt eine klar markierte Phasen-Simulation.
#    - go_to_room loest ein Karten-/Revisions-gebundenes Ziel aus der
#      semantischen Karte auf. Standardmaessig bleibt es Simulation; nur ein
#      separater Opt-in sendet das Ziel mit einem Recovery-freien Baum an Nav2.
#    - Status JSON fuer die GUI publizieren (bestehende Felder unveraendert,
#      Semantikfelder ausschliesslich additiv).
#
#  WICHTIGE TOPICS/ACTIONS:
#    Eingang : /mission_manager/command_json   (std_msgs/String)
#    Action  : <run_mission_action> (Client)   robot_interfaces/RunMission
#    Eingang : /offboard/available             (std_msgs/Bool, optional)
#    Eingang : /semantic/catalog_json          (std_msgs/String, optional)
#    Eingang : /semantic_map/status_json       (std_msgs/String, read-only)
#    Ausgang : /mission_manager/status_json    (std_msgs/String)
#
#  ALLE PARAMETER -> config/mission_catalog.yaml.
# ============================================================================

import json
import math
import time
from typing import Dict, List, Optional

import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from rclpy.qos import QoSProfile, QoSDurabilityPolicy, QoSReliabilityPolicy
from rcl_interfaces.msg import ParameterDescriptor
from action_msgs.msg import GoalStatus
from action_msgs.srv import CancelGoal
from std_msgs.msg import String, Bool
from geometry_msgs.msg import PoseStamped
from nav2_msgs.action import NavigateToPose

from robot_interfaces.action import RunMission
from mission_manager.action_outcome import cancel_was_accepted, terminal_state
from mission_manager.command_payload import decode_command_payload
from mission_manager.execution_policy import (
    effective_real_types,
    execution_mode,
    go_to_room_execution_status,
    localization_loss_state,
    pick_and_place_room_allowed,
)
from mission_manager.semantic_catalog import decode_catalog_payload
from mission_manager.semantic_room_goal import (
    decode_semantic_map_status,
    resolve_room_goal,
    semantic_snapshot_is_fresh,
)


class MissionManager(Node):
    def __init__(self):
        super().__init__('mission_manager')

        # -------------------------------------------------------------------
        # Parameter aus mission_catalog.yaml
        # -------------------------------------------------------------------
        self.declare_parameter('rooms', ['Wohnzimmer', 'Kueche', 'Flur'])
        self.declare_parameter('targets', ['Tisch', 'Regal'])
        self.declare_parameter('objects', ['Tasse', 'Flasche'])
        self.declare_parameter('phase_duration_s', 1.2)
        self.declare_parameter('use_dynamic_catalog', False)
        self.declare_parameter('catalog_topic', '/semantic/catalog_json')
        self.declare_parameter('semantic_map_status_topic', '/semantic_map/status_json')
        self.declare_parameter('semantic_map_expected_frame', 'map')
        self.declare_parameter('semantic_map_expected_fingerprint', '')
        self.declare_parameter('semantic_map_status_stale_timeout_s', 6.0)
        self.declare_parameter('offboard_topic', '/offboard/available')
        # K1: welche Auftragstypen ECHT ueber den Behavior-Tree laufen.
        self.declare_parameter('real_mission_types', ['pick_and_place', 'explore'])
        self.declare_parameter('run_mission_action', '/run_mission')
        # Reale Raumfahrt ist ein separater, standardmaessig AUSgeschalteter
        # Nav2-Pfad. Sie kann nicht versehentlich ueber real_mission_types
        # aktiviert werden.
        self.declare_parameter('enable_real_go_to_room', False)
        self.declare_parameter('navigate_to_pose_action', '/navigate_to_pose')
        self.declare_parameter('go_to_room_behavior_tree', '')
        self.declare_parameter(
            'require_localization_for_real_go_to_room', True)
        self.declare_parameter(
            'localization_ready_topic', '/localization/ready')
        self.declare_parameter('localization_ready_timeout_s', 1.0)
        self.declare_parameter('localization_loss_grace_s', 0.8)

        self.rooms = list(self.get_parameter('rooms').value)
        # Diese ursprüngliche Allowlist bleibt getrennt vom dynamischen
        # Raumkatalog. Der bestehende echte pick_and_place-Baum ignoriert das
        # Feld room und darf durch einen neu gezeichneten Raum nicht zusätzlich
        # freigeschaltet werden.
        self.pick_and_place_rooms = tuple(self.rooms)
        self.static_rooms = tuple(self.rooms)
        self.targets = list(self.get_parameter('targets').value)
        self.objects = list(self.get_parameter('objects').value)
        self.phase_duration_s = float(self.get_parameter('phase_duration_s').value)
        self.use_dynamic_catalog = bool(self.get_parameter('use_dynamic_catalog').value)
        self.catalog_topic = self.get_parameter('catalog_topic').value
        self.semantic_map_status_topic = str(
            self.get_parameter('semantic_map_status_topic').value)
        self.semantic_map_expected_frame = str(
            self.get_parameter('semantic_map_expected_frame').value)
        self.semantic_map_expected_fingerprint = str(
            self.get_parameter('semantic_map_expected_fingerprint').value)
        self.semantic_map_status_stale_timeout_s = float(
            self.get_parameter('semantic_map_status_stale_timeout_s').value)
        if (
                not math.isfinite(self.semantic_map_status_stale_timeout_s)
                or self.semantic_map_status_stale_timeout_s <= 0.0):
            raise ValueError(
                'semantic_map_status_stale_timeout_s muss endlich und > 0 sein')
        self.offboard_topic = self.get_parameter('offboard_topic').value
        configured_real_types = set(self.get_parameter('real_mission_types').value)
        self.real_types = effective_real_types(configured_real_types)
        # Sicherheitsbarriere: Ein Konfigurationsfehler darf die vorbereitende
        # go_to_room-Simulation niemals in den Action-/Nav2-Pfad heben.
        if 'go_to_room' in configured_real_types:
            self.get_logger().error(
                "'go_to_room' aus real_mission_types entfernt: reale Fahrt ist nicht freigegeben.")
        self.run_mission_action = self.get_parameter('run_mission_action').value
        self.enable_real_go_to_room = bool(
            self.get_parameter('enable_real_go_to_room').value)
        self.navigate_to_pose_action = str(
            self.get_parameter('navigate_to_pose_action').value).strip()
        if not self.navigate_to_pose_action:
            raise ValueError('navigate_to_pose_action darf nicht leer sein')
        self.go_to_room_behavior_tree = str(
            self.get_parameter('go_to_room_behavior_tree').value).strip()
        if self.enable_real_go_to_room and not self.go_to_room_behavior_tree:
            raise ValueError(
                'Reale Raumfahrt verlangt einen expliziten Recovery-freien '
                'go_to_room_behavior_tree')
        self.require_localization_for_real_go_to_room = bool(
            self.get_parameter(
                'require_localization_for_real_go_to_room').value)
        self.localization_ready_topic = str(
            self.get_parameter('localization_ready_topic').value).strip()
        if not self.localization_ready_topic:
            raise ValueError('localization_ready_topic darf nicht leer sein')
        self.localization_ready_timeout_s = float(
            self.get_parameter('localization_ready_timeout_s').value)
        if (
                not math.isfinite(self.localization_ready_timeout_s)
                or self.localization_ready_timeout_s <= 0.0):
            raise ValueError(
                'localization_ready_timeout_s muss endlich und > 0 sein')
        self.localization_loss_grace_s = float(
            self.get_parameter('localization_loss_grace_s').value)
        if (
                not math.isfinite(self.localization_loss_grace_s)
                or self.localization_loss_grace_s <= 0.0):
            raise ValueError(
                'localization_loss_grace_s muss endlich und > 0 sein')

        # Pose-Katalog: Ablageort -> Pose. Dynamisch getypt, damit ein fehlender
        # Eintrag als None erkennbar ist (dann nutzt der BT seine Default-Pose).
        self.place_base_frame = str(self.declare_parameter('place_base_frame', 'map').value)
        self.place_arm_frame = str(self.declare_parameter('place_arm_frame', 'base_link').value)
        dyn = ParameterDescriptor(dynamic_typing=True)
        for t in self.targets:
            self.declare_parameter(f'place_base.{t}', descriptor=dyn)
            self.declare_parameter(f'place_arm.{t}', descriptor=dyn)

        # -------------------------------------------------------------------
        # Status-Publisher transient_local: spaete GUI-Verbindung bekommt Stand.
        # -------------------------------------------------------------------
        status_qos = QoSProfile(depth=1)
        status_qos.reliability = QoSReliabilityPolicy.RELIABLE
        status_qos.durability = QoSDurabilityPolicy.TRANSIENT_LOCAL

        self.status_pub = self.create_publisher(String, '/mission_manager/status_json', status_qos)
        self.command_sub = self.create_subscription(
            String, '/mission_manager/command_json', self._on_command, 10)
        self.offboard_sub = self.create_subscription(
            Bool, self.offboard_topic, self._on_offboard, 10)
        if self.use_dynamic_catalog:
            catalog_qos = QoSProfile(depth=1)
            catalog_qos.reliability = QoSReliabilityPolicy.RELIABLE
            catalog_qos.durability = QoSDurabilityPolicy.TRANSIENT_LOCAL
            self.catalog_sub = self.create_subscription(
                String, self.catalog_topic, self._on_catalog, catalog_qos)

        # Read-only Cache der passiven semantischen Karte. Die Subscription
        # ist transient-local, damit auch ein spaeter gestarteter Manager den
        # letzten bestaetigten Snapshot bekommt.
        self.semantic_map_sub = self.create_subscription(
            String, self.semantic_map_status_topic,
            self._on_semantic_map_status, status_qos)
        self.localization_ready_sub = self.create_subscription(
            Bool, self.localization_ready_topic,
            self._on_localization_ready, 10)

        # K1: Action-Client zum bt_orchestrator.
        self.mission_client = ActionClient(self, RunMission, self.run_mission_action)
        self.navigation_client = ActionClient(
            self, NavigateToPose, self.navigate_to_pose_action)

        # -------------------------------------------------------------------
        # Interner Zustand
        # -------------------------------------------------------------------
        self.state = 'idle'       # idle | running | success | failed | canceled
        self.phase = 'bereit'
        self.message = 'Bereit'
        self.progress = 0.0
        self.active_command: Dict = {}
        self.mode: Optional[str] = None   # 'real' | 'nav2' | 'sim' | None
        self.history: List[Dict] = []
        self.offboard_available = None
        self.last_rejection = ''          # S1-Fix: Ablehnung getrennt vom Zustand
        self._semantic_snapshot = None
        self._semantic_snapshot_received_monotonic = None
        self.semantic_map_error = 'Noch kein gueltiger Semantik-Status empfangen'
        self.resolved_room_goal = None
        self._localization_ready = False
        self._localization_ready_received_monotonic = None
        self._localization_loss_started_monotonic = None

        # Simulation (nur fuer Typen ohne Baum)
        self.phase_index = 0
        self.phase_started_at = time.monotonic()
        self.current_phases: List[str] = []

        # Echte Mission (Action)
        self._goal_handle = None
        # Massgebliche Sperre fuer den gesamten Action-Lebenszyklus: von
        # send_goal_async() bis Goal-Ablehnung oder bestaetigtem terminalem
        # WrappedResult. Zwischen Send und Goal-Antwort existiert noch kein
        # Handle; ein Abbruch in diesem Fenster wird deshalb vorgemerkt.
        self._real_goal_pending = False
        self._cancel_requested = False
        self._cancel_future = None
        self._action_epoch = 0
        self._active_action_epoch = None
        self._room_initial_distance = None

        self.timer = self.create_timer(0.2, self._timer_tick)
        self._publish_status()
        self.get_logger().info(
            f"mission_manager bereit (echte Typen: {sorted(self.real_types)}, "
            f"Action '{self.run_mission_action}').")
        if self.enable_real_go_to_room:
            self.get_logger().warn(
                'REALE RAUMFAHRT AKTIV: go_to_room sendet ein Nav2-Ziel an '
                f"'{self.navigate_to_pose_action}' mit Behavior Tree "
                f"'{self.go_to_room_behavior_tree}'. "
                + ('Eine frische Lokalisierungsfreigabe ist Pflicht.'
                   if self.require_localization_for_real_go_to_room
                   else 'Lokalisierungsfreigabe ist AUSGESCHALTET.'))

    # ======================= Eingang / Validierung =======================
    def _on_command(self, msg: String):
        cmd, error = decode_command_payload(msg.data)
        if error is not None:
            self._reject(error)
            return

        command_type = str(cmd.get('type', '')).strip()
        self.get_logger().info(f'Auftrag empfangen: {cmd}')

        if command_type == 'cancel':
            self._cancel_current('Mission durch GUI abgebrochen')
            return

        if self.state == 'running' or self._real_goal_pending:
            # S1-Fix: NICHT die laufende Mission abbrechen - nur ablehnen.
            self._reject(
                'Vorherige Mission wird noch abgebrochen'
                if self._cancel_requested
                else 'Es laeuft bereits eine Mission')
            return

        self.resolved_room_goal = None
        ok, reason = self._validate_command(command_type, cmd)
        if not ok:
            self._reject(reason)
            return

        self.last_rejection = ''
        if command_type == 'go_to_room' and self.enable_real_go_to_room:
            self._start_room_navigation(cmd)
            return
        mode = execution_mode(command_type, self.real_types)
        if mode == 'real':
            self._start_real_mission(command_type, cmd)
        else:
            self._start_sim_mission(command_type, cmd)

    def _validate_command(self, command_type: str, cmd: Dict):
        if command_type == 'go_to_room':
            self._expire_semantic_snapshot_if_stale()
            if self._semantic_snapshot is None:
                return False, (
                    'Kein gueltiges semantisches Raumziel verfuegbar: '
                    f'{self.semantic_map_error}')
            goal, error = resolve_room_goal(
                self._semantic_snapshot,
                room_name=cmd.get('room'),
                room_id=cmd.get('room_id'))
            if error is not None:
                return False, error
            self.resolved_room_goal = goal
            if (
                    self.enable_real_go_to_room
                    and self.require_localization_for_real_go_to_room
                    and not self._localization_is_ready()):
                return False, (
                    'Reale Raumfahrt gesperrt: globale Lokalisierung fehlt '
                    'oder ist veraltet')
            return True, 'ok'
        if command_type == 'pick_object':
            if cmd.get('object') not in self.objects:
                return False, f"Unbekanntes Objekt: {cmd.get('object')}"
            return True, 'ok'
        if command_type == 'pick_and_place':
            if cmd.get('object') not in self.objects:
                return False, f"Unbekanntes Objekt: {cmd.get('object')}"
            if not pick_and_place_room_allowed(
                    cmd.get('room'), self.pick_and_place_rooms):
                return False, f"Unbekannter Zielraum: {cmd.get('room')}"
            if cmd.get('target') not in self.targets:
                return False, f"Unbekannter Ablageort: {cmd.get('target')}"
            return True, 'ok'
        if command_type == 'explore':
            return True, 'ok'
        return False, f"Unbekannter Auftragstyp: {command_type}"

    # ======================= Pose-Katalog ===============================
    def _catalog_pose(self, param_name: str, frame: str, yaw_deg: bool):
        """Baut aus einem Katalog-Parameter eine PoseStamped. None, wenn der
        Eintrag fehlt/ungueltig ist (dann nutzt der BT seine Default-Pose).
        yaw_deg=True: [x, y, yaw_grad] (Basis) | False: [x, y, z] (Arm)."""
        arr = self.get_parameter(param_name).value
        if not isinstance(arr, (list, tuple)) or len(arr) < 3:
            return None
        p = PoseStamped()
        p.header.frame_id = frame
        p.pose.position.x = float(arr[0])
        p.pose.position.y = float(arr[1])
        if yaw_deg:
            yaw = math.radians(float(arr[2]))
            p.pose.orientation.z = math.sin(yaw / 2.0)
            p.pose.orientation.w = math.cos(yaw / 2.0)
        else:
            p.pose.position.z = float(arr[2])
            p.pose.orientation.w = 1.0
        return p

    # ======================= Echte Mission (Action) =====================
    def _start_room_navigation(self, cmd: Dict):
        if self.resolved_room_goal is None:
            self._finish(
                'failed', 'fehler',
                'Internes Raumziel fehlt; keine Navigation gestartet.', cmd)
            return
        if not self.navigation_client.server_is_ready():
            self._finish(
                'failed', 'fehler',
                f"Nav2 nicht erreichbar (Action '{self.navigate_to_pose_action}').",
                cmd)
            return

        resolved = self.resolved_room_goal
        goal = NavigateToPose.Goal()
        goal.pose.header.frame_id = resolved.frame_id
        goal.pose.header.stamp = self.get_clock().now().to_msg()
        goal.pose.pose.position.x = resolved.x
        goal.pose.pose.position.y = resolved.y
        goal.pose.pose.orientation.z = math.sin(resolved.yaw / 2.0)
        goal.pose.pose.orientation.w = math.cos(resolved.yaw / 2.0)
        goal.behavior_tree = self.go_to_room_behavior_tree

        self.state = 'running'
        self.mode = 'nav2'
        self.active_command = dict(cmd)
        self.phase = 'nav2_ziel_senden'
        self.message = f"Fahrt zu '{resolved.room_name}' wird gestartet."
        self.progress = 0.0
        self._room_initial_distance = None
        self._localization_loss_started_monotonic = None
        self._goal_handle = None
        self._real_goal_pending = True
        self._cancel_requested = False
        self._cancel_future = None
        self._action_epoch += 1
        action_epoch = self._action_epoch
        self._active_action_epoch = action_epoch
        self.history.append({
            'event': 'start_room_navigation',
            'command': cmd,
            'map_fingerprint': resolved.map_fingerprint,
            'map_revision': resolved.map_revision,
            't': time.time(),
        })
        self._publish_status()

        send_future = self.navigation_client.send_goal_async(
            goal,
            feedback_callback=lambda feedback, epoch=action_epoch:
                self._on_room_navigation_feedback(feedback, epoch))
        send_future.add_done_callback(
            lambda response_future, epoch=action_epoch:
                self._on_room_navigation_goal_response(response_future, epoch))

    def _on_room_navigation_goal_response(self, future, action_epoch):
        if self._active_action_epoch != action_epoch:
            return
        try:
            goal_handle = future.result()
        except Exception as exc:
            self._clear_action_state()
            self._finish(
                'failed', 'fehler',
                f'Nav2-Ziel konnte nicht gesendet werden: {exc}',
                self.active_command)
            return

        if not goal_handle.accepted:
            was_canceled = self._cancel_requested
            self._clear_action_state()
            self._finish(
                'canceled' if was_canceled else 'failed',
                'abgebrochen' if was_canceled else 'fehler',
                'Raumfahrt vor der Zielannahme abgebrochen.'
                if was_canceled else 'Nav2 hat das Raumziel abgelehnt.',
                self.active_command)
            return

        self._goal_handle = goal_handle
        goal_handle.get_result_async().add_done_callback(
            lambda result_future, handle=goal_handle, epoch=action_epoch:
                self._on_room_navigation_result(result_future, handle, epoch))

        if self._cancel_requested:
            self._request_real_cancel(goal_handle, action_epoch)
            return

        self.phase = 'fahre_zum_raum'
        self.message = 'Nav2-Ziel angenommen; Raumfahrt laeuft.'
        self._publish_status()

    def _on_room_navigation_feedback(self, feedback_msg, action_epoch):
        if (
                self._active_action_epoch != action_epoch
                or self.state != 'running'
                or self.mode != 'nav2'
                or self._cancel_requested):
            return
        remaining = max(0.0, float(feedback_msg.feedback.distance_remaining))
        if remaining > 0.01 and self._room_initial_distance is None:
            self._room_initial_distance = remaining
        if self._room_initial_distance:
            self.progress = max(
                0.0,
                min(0.99, 1.0 - remaining / self._room_initial_distance))
        self.phase = 'fahre_zum_raum'
        self.message = f'Noch {remaining:.2f} m bis zum Raumziel.'
        self._publish_status()

    def _on_room_navigation_result(self, future, goal_handle, action_epoch):
        if (
                self._active_action_epoch != action_epoch
                or self._goal_handle is not goal_handle):
            return
        try:
            wrapped_result = future.result()
            action_status = wrapped_result.status
        except Exception as exc:
            self._cancel_requested = False
            self._cancel_future = None
            self.phase = 'status_unbekannt'
            self.message = (
                f'Nav2-Ergebnis nicht lesbar: {exc}. '
                'Keine neue Mission starten; mission_manager pruefen.')
            self._reject(self.message)
            return

        outcome = terminal_state(
            action_status,
            True,
            succeeded_status=GoalStatus.STATUS_SUCCEEDED,
            canceled_status=GoalStatus.STATUS_CANCELED,
            aborted_status=GoalStatus.STATUS_ABORTED)
        if outcome is None:
            self._cancel_requested = False
            self._cancel_future = None
            self.phase = 'status_unbekannt'
            self.message = (
                f'Unerwarteter nichtterminaler Nav2-Status {action_status}; '
                'mission_manager pruefen.')
            self._reject(self.message)
            return

        self._clear_action_state()
        if outcome == 'success':
            self._finish(
                'success', 'angekommen', 'Raumziel erreicht.',
                self.active_command, progress=1.0)
        elif outcome == 'canceled':
            self._finish(
                'canceled', 'abgebrochen', 'Raumfahrt abgebrochen.',
                self.active_command)
        else:
            self._finish(
                'failed', 'fehler',
                f'Nav2-Raumfahrt fehlgeschlagen (Action-Status {action_status}).',
                self.active_command)

    def _clear_action_state(self):
        self._real_goal_pending = False
        self._goal_handle = None
        self._cancel_requested = False
        self._cancel_future = None
        self._active_action_epoch = None
        self._room_initial_distance = None

    def _start_real_mission(self, command_type: str, cmd: Dict):
        if not self.mission_client.server_is_ready():
            # bt_orchestrator laeuft (noch) nicht -> ehrliche Fehlermeldung.
            self._finish('failed', 'fehler',
                         f"bt_orchestrator nicht erreichbar (Action '{self.run_mission_action}').",
                         cmd)
            return

        goal = RunMission.Goal()
        goal.mission_type = command_type
        goal.object = str(cmd.get('object', '') or '')
        goal.room = str(cmd.get('room', '') or '')
        goal.target = str(cmd.get('target', '') or '')

        # Pose-Katalog: Ablageort -> konkrete Posen ins Goal (sonst BT-Default).
        target = goal.target
        if target:
            base = self._catalog_pose(f'place_base.{target}', self.place_base_frame, yaw_deg=True)
            arm = self._catalog_pose(f'place_arm.{target}', self.place_arm_frame, yaw_deg=False)
            if base is not None:
                goal.place_base_goal = base
            if arm is not None:
                goal.place_pose = arm
            if base is None and command_type == 'pick_and_place':
                self.get_logger().warn(
                    f"Kein place_base-Katalogeintrag fuer '{target}' - BT nutzt Default-Pose.")
            elif base is not None:
                self.get_logger().info(
                    f"Ablegen bei '{target}': Basis ({base.pose.position.x:.2f}, "
                    f"{base.pose.position.y:.2f}) im {self.place_base_frame}.")

        self.state = 'running'
        self.mode = 'real'
        self.active_command = dict(cmd)
        self.phase = 'gestartet'
        self.message = f'Mission gestartet: {command_type}'
        self.progress = 0.0
        self._goal_handle = None
        self._real_goal_pending = True
        self._cancel_requested = False
        self._cancel_future = None
        self._action_epoch += 1
        action_epoch = self._action_epoch
        self._active_action_epoch = action_epoch
        self.history.append({'event': 'start', 'command': cmd, 't': time.time()})
        self._publish_status()

        send_future = self.mission_client.send_goal_async(
            goal,
            feedback_callback=lambda feedback, epoch=action_epoch:
                self._on_mission_feedback(feedback, epoch))
        send_future.add_done_callback(
            lambda response_future, epoch=action_epoch:
                self._on_goal_response(response_future, epoch))

    def _on_goal_response(self, future, action_epoch):
        if self._active_action_epoch != action_epoch:
            return
        try:
            goal_handle = future.result()
        except Exception as exc:
            self._real_goal_pending = False
            self._cancel_requested = False
            self._cancel_future = None
            self._active_action_epoch = None
            self._finish('failed', 'fehler',
                         f'Mission konnte nicht an bt_orchestrator gesendet werden: {exc}',
                         self.active_command)
            return

        if not goal_handle.accepted:
            self._real_goal_pending = False
            self._goal_handle = None
            self._cancel_future = None
            self._active_action_epoch = None
            if self._cancel_requested:
                self._cancel_requested = False
                self._finish(
                    'canceled',
                    'abgebrochen',
                    'Mission vor dem Start abgebrochen; Action-Goal wurde nicht angenommen.',
                    self.active_command)
                return
            self._finish('failed', 'fehler',
                         'Mission vom bt_orchestrator abgelehnt (laeuft dort schon eine?).',
                         self.active_command)
            return

        self._goal_handle = goal_handle
        goal_handle.get_result_async().add_done_callback(
            lambda result_future, handle=goal_handle, epoch=action_epoch:
                self._on_mission_result(result_future, handle, epoch))

        if self._cancel_requested:
            # Abbruch kam an, waehrend send_goal_async noch auf die Annahme
            # wartete. Jetzt existiert das Handle: sofort serverseitig stoppen.
            self._request_real_cancel(goal_handle, action_epoch)
            self.get_logger().warn(
                'Vorgemerkten Missionsabbruch nach Goal-Annahme weitergegeben.')
            return

        self.message = 'Mission angenommen, laeuft ...'
        self._publish_status()

    def _on_mission_feedback(self, feedback_msg, action_epoch):
        if self._active_action_epoch != action_epoch:
            return
        fb = feedback_msg.feedback
        if self.state != 'running' or self.mode != 'real' or self._cancel_requested:
            return
        if fb.phase:
            self.phase = fb.phase
        self.progress = float(fb.progress)
        self.message = f'Phase: {self.phase}'
        self._publish_status()

    def _request_real_cancel(self, goal_handle, action_epoch):
        if (
                self._active_action_epoch != action_epoch
                or self._goal_handle is not goal_handle
                or self._cancel_future is not None):
            return
        try:
            cancel_future = goal_handle.cancel_goal_async()
        except Exception as exc:
            self._cancel_requested = False
            self.phase = 'laeuft'
            self.message = f'Abbruch konnte nicht angefordert werden: {exc}'
            self._reject(self.message)
            return

        self._cancel_future = cancel_future
        cancel_future.add_done_callback(
            lambda response_future, handle=goal_handle, epoch=action_epoch:
                self._on_cancel_response(response_future, handle, epoch))

    def _on_cancel_response(self, future, goal_handle, action_epoch):
        if (
                self._active_action_epoch != action_epoch
                or self._goal_handle is not goal_handle):
            # Das terminale Result kann vor der Cancel-Antwort eintreffen.
            return
        self._cancel_future = None
        try:
            response = future.result()
            canceling_goal_ids = (
                tuple(goal_info.goal_id.uuid)
                for goal_info in response.goals_canceling
            )
            accepted = cancel_was_accepted(
                response.return_code,
                canceling_goal_ids,
                tuple(goal_handle.goal_id.uuid),
                success_code=CancelGoal.Response.ERROR_NONE)
        except Exception as exc:
            self._cancel_requested = False
            self.phase = 'laeuft'
            self.message = f'Abbruch konnte nicht bestaetigt werden: {exc}'
            self._reject(self.message)
            return

        if accepted:
            self.phase = 'abbruch_angefordert'
            self.message = 'Abbruch angenommen; warte auf Action-Ergebnis ...'
            self._publish_status()
            return

        # Ein leerer goals_canceling-Vektor bedeutet: Der Server hat den
        # Abbruch nicht angenommen (oft weil das Goal bereits terminal war).
        # Das nachfolgende WrappedResult entscheidet wahrheitsgemaess zwischen
        # success/failed/canceled.
        self._cancel_requested = False
        self.phase = 'abschluss_ausstehend'
        self.message = (
            f'Abbruch nicht angenommen (Code {response.return_code}); '
            'warte auf Missionsergebnis.')
        self._reject(self.message)

    def _on_mission_result(self, future, goal_handle, action_epoch):
        if (
                self._active_action_epoch != action_epoch
                or self._goal_handle is not goal_handle):
            return
        try:
            wrapped_result = future.result()
            result = wrapped_result.result
            action_status = wrapped_result.status
        except Exception as exc:
            # Ohne WrappedResult ist nicht bewiesen, dass das Action-Goal
            # terminal ist. Aus Sicherheitsgruenden bleibt der Manager
            # gesperrt, damit kein zweites Goal parallel gestartet wird.
            self._cancel_requested = False
            self._cancel_future = None
            self.phase = 'status_unbekannt'
            self.message = (
                f'Missionsergebnis nicht lesbar: {exc}. '
                'Keine neue Mission starten; mission_manager pruefen.')
            self._reject(self.message)
            return

        outcome = terminal_state(
            action_status,
            bool(result.success),
            succeeded_status=GoalStatus.STATUS_SUCCEEDED,
            canceled_status=GoalStatus.STATUS_CANCELED,
            aborted_status=GoalStatus.STATUS_ABORTED)
        if outcome is None:
            # get_result_async() sollte nur terminal aufloesen. Bei einem
            # unerwarteten nichtterminalen Status bleibt die Sperre bestehen.
            self._cancel_requested = False
            self._cancel_future = None
            self.phase = 'status_unbekannt'
            self.message = (
                f'Unerwarteter nichtterminaler Action-Status {action_status}; '
                'mission_manager pruefen.')
            self._reject(self.message)
            return

        self._real_goal_pending = False
        self._goal_handle = None
        self._cancel_requested = False
        self._cancel_future = None
        self._active_action_epoch = None

        if outcome == 'canceled':
            self._finish('canceled', 'abgebrochen',
                         result.message or 'Mission vom Action-Server abgebrochen',
                         self.active_command)
        elif outcome == 'success':
            self._finish('success', 'fertig',
                         result.message or 'Mission erfolgreich abgeschlossen',
                         self.active_command, progress=1.0)
        else:
            self._finish('failed', 'fehler',
                         result.message or
                         f'Mission fehlgeschlagen (Action-Status {action_status})',
                         self.active_command)

    # ======================= Simulierte Mission =========================
    def _start_sim_mission(self, command_type: str, cmd: Dict):
        self.state = 'running'
        self.mode = 'sim'
        self.active_command = dict(cmd)
        self.phase_index = 0
        self.phase_started_at = time.monotonic()
        self.progress = 0.0

        if command_type == 'go_to_room':
            self.current_phases = [
                'Semantisches Ziel validiert',
                'Navigationsziel vorbereitet',
                'Vorbereitung abgeschlossen',
            ]
        elif command_type == 'pick_object':
            self.current_phases = ['Objekt suchen', 'Greifpose berechnen', 'Greifen', 'Griff pruefen']
        else:
            self.current_phases = ['Schritt 1', 'Schritt 2', 'Schritt 3']

        self.phase = self.current_phases[0]
        if command_type == 'go_to_room':
            self.message = (
                'Raumziel sicher aufgeloest (Simulation - keine Fahrt, kein Nav2-Auftrag)')
        else:
            self.message = f'Mission gestartet: {command_type} (Simulation - noch kein Baum)'
        self.history.append({'event': 'start_sim', 'command': cmd, 't': time.time()})
        self._publish_status()

    def _timer_tick(self):
        if self._expire_semantic_snapshot_if_stale():
            return
        if (
                self.require_localization_for_real_go_to_room
                and self._active_room_navigation()
                and self._localization_loss_requires_cancel()
                and self._fail_active_room_localization(
                    'Lokalisierungsfreigabe fehlt oder ist anhaltend veraltet')):
            return
        if self.state == 'running' and self.mode == 'sim':
            self._tick_sim_mission()
        else:
            # Status regelmaessig auffrischen (GUI nach Verbindungswechsel).
            self._publish_status()

    def _tick_sim_mission(self):
        elapsed = time.monotonic() - self.phase_started_at
        if elapsed < self.phase_duration_s:
            self.progress = self._sim_progress()
            self._publish_status()
            return
        self.phase_index += 1
        if self.phase_index >= len(self.current_phases):
            if self.active_command.get('type') == 'go_to_room':
                self._finish(
                    'success', 'vorbereitet',
                    'Semantisches Raumziel vorbereitet (Simulation - keine Fahrt)',
                    self.active_command, progress=1.0)
                return
            self._finish('success', 'fertig',
                         'Mission erfolgreich abgeschlossen (Simulation)',
                         self.active_command, progress=1.0)
            return
        self.phase = self.current_phases[self.phase_index]
        self.phase_started_at = time.monotonic()
        self.progress = self._sim_progress()
        self.message = f'Phase: {self.phase} (Simulation)'
        self._publish_status()

    def _sim_progress(self):
        if not self.current_phases:
            return 0.0
        return float(self.phase_index) / float(max(1, len(self.current_phases)))

    # ======================= Abbruch / Ablehnung ========================
    def _cancel_current(self, reason: str):
        if self.state != 'running' and not self._real_goal_pending:
            self._reject('Keine laufende Mission')
            return
        if self.state == 'running' and self.mode in {'real', 'nav2'}:
            if self._cancel_requested:
                self._reject('Abbruch wurde bereits angefordert')
                return
            self._cancel_requested = True
            self.phase = 'abbruch_angefordert'
            self.message = f'{reason}; warte auf Action-Bestaetigung ...'
            self.history.append({
                'event': 'cancel_requested',
                'command': self.active_command,
                't': time.time(),
            })
            if self._goal_handle is not None:
                self._request_real_cancel(
                    self._goal_handle,
                    self._active_action_epoch)
            self._publish_status()
            return
        self._finish('canceled', 'abgebrochen', reason, self.active_command)

    def _reject(self, reason: str):
        # S1-Fix: Ablehnung aendert den laufenden Missionszustand NICHT.
        self.last_rejection = reason
        self.get_logger().warn(f'Auftrag abgelehnt: {reason}')
        self.history.append({'event': 'rejected', 'reason': reason, 't': time.time()})
        self._publish_status()

    def _finish(self, state: str, phase: str, message: str, cmd: Dict, progress=None):
        self.state = state
        self.mode = None
        self._localization_loss_started_monotonic = None
        self.phase = phase
        self.message = message
        if progress is not None:
            self.progress = progress
        self.history.append({'event': state, 'command': cmd, 't': time.time()})
        self._publish_status()

    # ======================= WP-5: Offboard / dyn. Katalog =============
    def _on_offboard(self, msg: Bool):
        if self.offboard_available != msg.data:
            self.offboard_available = msg.data
            self.get_logger().info(
                f"Offboard-Server {'erreichbar' if msg.data else 'NICHT erreichbar'}.")
            self._publish_status()

    def _localization_is_ready(self):
        received = self._localization_ready_received_monotonic
        if received is None or self._localization_ready is not True:
            return False
        age = time.monotonic() - received
        return 0.0 <= age <= self.localization_ready_timeout_s

    def _on_localization_ready(self, msg: Bool):
        self._localization_ready = msg.data is True
        self._localization_ready_received_monotonic = time.monotonic()
        if self._localization_ready:
            self._localization_loss_started_monotonic = None
        self._publish_status()

    def _localization_loss_requires_cancel(self) -> bool:
        now = time.monotonic()
        (
            self._localization_loss_started_monotonic,
            grace_expired,
        ) = localization_loss_state(
            self._localization_is_ready(),
            now=now,
            loss_started=self._localization_loss_started_monotonic,
            grace_s=self.localization_loss_grace_s)
        return grace_expired

    def _fail_active_room_localization(self, reason: str) -> bool:
        if not self._active_room_navigation():
            return False
        if not self._cancel_requested:
            self._cancel_requested = True
            self.phase = 'lokalisierung_verloren'
            self.message = f'{reason}; Nav2-Abbruch angefordert.'
            if self._goal_handle is not None:
                self._request_real_cancel(
                    self._goal_handle, self._active_action_epoch)
            self._publish_status()
        return True

    def _active_room_navigation(self) -> bool:
        return (
            self.state == 'running'
            and self.mode == 'nav2'
            and self.active_command.get('type') == 'go_to_room'
        )

    def _on_catalog(self, msg: String):
        update, error = decode_catalog_payload(msg.data)
        if error is not None:
            self.get_logger().warn(f'Semantik-Katalog ignoriert: {error}')
            return
        changed = False
        desired_rooms = list(update.get('rooms') or self.static_rooms)
        if desired_rooms != self.rooms:
            self.rooms = desired_rooms
            changed = True
        if changed:
            self.get_logger().info(
                f"Raumkatalog aus Semantik aktualisiert: {len(self.rooms)} Raeume; "
                'Objekte/Ablageziele bleiben statisch freigegeben.')
            self._publish_status()

    def _fail_active_room_preparation(self, reason: str) -> bool:
        if (
                self.state == 'running'
                and self.mode == 'sim'
                and self.active_command.get('type') == 'go_to_room'):
            self._finish(
                'failed', 'ziel_ungueltig',
                f'Semantisches Raumziel wurde ungueltig: {reason} (keine Fahrt)',
                self.active_command)
            return True
        if (
                self.state == 'running'
                and self.mode == 'nav2'
                and self.active_command.get('type') == 'go_to_room'):
            if not self._cancel_requested:
                self._cancel_requested = True
                self.phase = 'ziel_ungueltig'
                self.message = (
                    f'Semantisches Raumziel wurde ungueltig: {reason}; '
                    'Nav2-Abbruch angefordert.')
                if self._goal_handle is not None:
                    self._request_real_cancel(
                        self._goal_handle, self._active_action_epoch)
                self._publish_status()
            return True
        return False

    def _invalidate_semantic_snapshot(self, reason: str) -> None:
        self._semantic_snapshot = None
        self._semantic_snapshot_received_monotonic = None
        self.semantic_map_error = reason
        self.resolved_room_goal = None

    def _semantic_snapshot_is_fresh(self) -> bool:
        return semantic_snapshot_is_fresh(
            self._semantic_snapshot_received_monotonic,
            time.monotonic(),
            self.semantic_map_status_stale_timeout_s)

    def _expire_semantic_snapshot_if_stale(self) -> bool:
        if self._semantic_snapshot is None or self._semantic_snapshot_is_fresh():
            return False
        reason = (
            'Semantik-Status ist aelter als '
            f'{self.semantic_map_status_stale_timeout_s:.1f} s')
        self._invalidate_semantic_snapshot(reason)
        self.get_logger().warn(f'Semantische Raumkarte abgelaufen: {reason}')
        return self._fail_active_room_preparation(reason)

    def _on_semantic_map_status(self, msg: String):
        snapshot, error = decode_semantic_map_status(
            msg.data,
            expected_frame_id=self.semantic_map_expected_frame,
            expected_fingerprint=self.semantic_map_expected_fingerprint)
        if error is not None:
            # Ein neuer ungueltiger Status invalidiert den alten Cache. So kann
            # nach Kartenwechsel/Fehler nie ein zuvor aufgeloestes Ziel weiter
            # als aktuell erscheinen.
            self._invalidate_semantic_snapshot(error)
            self.get_logger().warn(f'Semantische Raumkarte nicht verwendbar: {error}')
            if not self._fail_active_room_preparation(error):
                self._publish_status()
            return

        previous_binding = None
        if self._semantic_snapshot is not None:
            previous_binding = (
                self._semantic_snapshot.fingerprint,
                self._semantic_snapshot.revision)
        new_binding = (snapshot.fingerprint, snapshot.revision)
        self._semantic_snapshot = snapshot
        self._semantic_snapshot_received_monotonic = time.monotonic()
        self.semantic_map_error = ''
        if previous_binding is not None and previous_binding != new_binding:
            self.resolved_room_goal = None
            if self._fail_active_room_preparation(
                    'Kartenfingerprint oder Revision hat sich geaendert'):
                return
        self.get_logger().info(
            f'Semantische Raumkarte bereit: Revision {snapshot.revision}, '
            f'{len(snapshot.rooms)} Raeume, Fingerprint {snapshot.fingerprint[:12]}...')
        self._publish_status()

    # ======================= Statusausgabe =============================
    def _publish_status(self):
        semantic_status_age = (
            None
            if self._semantic_snapshot_received_monotonic is None
            else max(
                0.0,
                time.monotonic() - self._semantic_snapshot_received_monotonic)
        )
        semantic_map = {
            'available': self._semantic_snapshot is not None,
            'error': self.semantic_map_error,
            'status_age_seconds': semantic_status_age,
            'stale_timeout_seconds': self.semantic_map_status_stale_timeout_s,
        }
        if self._semantic_snapshot is not None:
            semantic_map.update({
                'map_fingerprint': self._semantic_snapshot.fingerprint,
                'map_revision': self._semantic_snapshot.revision,
                'frame_id': self._semantic_snapshot.frame_id,
                'room_count': len(self._semantic_snapshot.rooms),
            })
        localization_age = (
            None
            if self._localization_ready_received_monotonic is None
            else max(
                0.0,
                time.monotonic()
                - self._localization_ready_received_monotonic)
        )
        localization_loss_age = (
            None
            if self._localization_loss_started_monotonic is None
            else max(
                0.0,
                time.monotonic()
                - self._localization_loss_started_monotonic)
        )
        payload = {
            'state': self.state,
            'phase': self.phase,
            'message': self.message,
            'progress': self.progress,
            'active_command': self.active_command,
            'rooms': self.rooms,
            'pick_and_place_rooms': list(self.pick_and_place_rooms),
            'targets': self.targets,
            'objects': self.objects,
            'offboard_available': self.offboard_available,
            'cancel_pending': self._cancel_requested,
            'last_rejection': self.last_rejection,
            'semantic_map': semantic_map,
            'localization': {
                'required_for_real_go_to_room': (
                    self.require_localization_for_real_go_to_room),
                'ready': self._localization_is_ready(),
                'last_signal': self._localization_ready,
                'status_age_seconds': localization_age,
                'stale_timeout_seconds': self.localization_ready_timeout_s,
                'loss_age_seconds': localization_loss_age,
                'mission_cancel_grace_seconds': self.localization_loss_grace_s,
            },
            'resolved_room_goal': (
                self.resolved_room_goal.as_dict()
                if self.resolved_room_goal is not None else None),
            'go_to_room_execution': go_to_room_execution_status(
                self.enable_real_go_to_room),
            'time': time.time(),
        }
        self.status_pub.publish(String(data=json.dumps(payload, ensure_ascii=False)))


def main(args=None):
    rclpy.init(args=args)
    node = MissionManager()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
