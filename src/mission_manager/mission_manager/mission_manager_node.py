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
#    - Fuer Typen OHNE eigenen Baum (go_to_room, pick_object): weiterhin
#      Phasen-Simulation, klar als "(Simulation)" markiert (bis Baum/Posen-
#      Katalog existieren).
#    - Status JSON fuer die GUI publizieren (Format UNVERAENDERT).
#
#  WICHTIGE TOPICS/ACTIONS:
#    Eingang : /mission_manager/command_json   (std_msgs/String)
#    Action  : <run_mission_action> (Client)   robot_interfaces/RunMission
#    Eingang : /offboard/available             (std_msgs/Bool, optional)
#    Eingang : /semantic/catalog_json          (std_msgs/String, optional)
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
from std_msgs.msg import String, Bool
from geometry_msgs.msg import PoseStamped

from robot_interfaces.action import RunMission


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
        self.declare_parameter('offboard_topic', '/offboard/available')
        # K1: welche Auftragstypen ECHT ueber den Behavior-Tree laufen.
        self.declare_parameter('real_mission_types', ['pick_and_place', 'explore'])
        self.declare_parameter('run_mission_action', '/run_mission')

        self.rooms = list(self.get_parameter('rooms').value)
        self.targets = list(self.get_parameter('targets').value)
        self.objects = list(self.get_parameter('objects').value)
        self.phase_duration_s = float(self.get_parameter('phase_duration_s').value)
        self.use_dynamic_catalog = bool(self.get_parameter('use_dynamic_catalog').value)
        self.catalog_topic = self.get_parameter('catalog_topic').value
        self.offboard_topic = self.get_parameter('offboard_topic').value
        self.real_types = set(self.get_parameter('real_mission_types').value)
        self.run_mission_action = self.get_parameter('run_mission_action').value

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
            self.catalog_sub = self.create_subscription(
                String, self.catalog_topic, self._on_catalog, 10)

        # K1: Action-Client zum bt_orchestrator.
        self.mission_client = ActionClient(self, RunMission, self.run_mission_action)

        # -------------------------------------------------------------------
        # Interner Zustand
        # -------------------------------------------------------------------
        self.state = 'idle'       # idle | running | success | failed | canceled
        self.phase = 'bereit'
        self.message = 'Bereit'
        self.progress = 0.0
        self.active_command: Dict = {}
        self.mode: Optional[str] = None   # 'real' | 'sim' | None
        self.history: List[Dict] = []
        self.offboard_available = None
        self.last_rejection = ''          # S1-Fix: Ablehnung getrennt vom Zustand

        # Simulation (nur fuer Typen ohne Baum)
        self.phase_index = 0
        self.phase_started_at = time.monotonic()
        self.current_phases: List[str] = []

        # Echte Mission (Action)
        self._goal_handle = None

        self.timer = self.create_timer(0.2, self._timer_tick)
        self._publish_status()
        self.get_logger().info(
            f"mission_manager bereit (echte Typen: {sorted(self.real_types)}, "
            f"Action '{self.run_mission_action}').")

    # ======================= Eingang / Validierung =======================
    def _on_command(self, msg: String):
        try:
            cmd = json.loads(msg.data)
        except json.JSONDecodeError as exc:
            self._reject(f'Ungueltiges JSON: {exc}')
            return

        command_type = str(cmd.get('type', '')).strip()
        self.get_logger().info(f'Auftrag empfangen: {cmd}')

        if command_type == 'cancel':
            self._cancel_current('Mission durch GUI abgebrochen')
            return

        if self.state == 'running':
            # S1-Fix: NICHT die laufende Mission abbrechen - nur ablehnen.
            self._reject('Es laeuft bereits eine Mission')
            return

        ok, reason = self._validate_command(command_type, cmd)
        if not ok:
            self._reject(reason)
            return

        self.last_rejection = ''
        if command_type in self.real_types:
            self._start_real_mission(command_type, cmd)
        else:
            self._start_sim_mission(command_type, cmd)

    def _validate_command(self, command_type: str, cmd: Dict):
        if command_type == 'go_to_room':
            if cmd.get('room') not in self.rooms:
                return False, f"Unbekannter Raum: {cmd.get('room')}"
            return True, 'ok'
        if command_type == 'pick_object':
            if cmd.get('object') not in self.objects:
                return False, f"Unbekanntes Objekt: {cmd.get('object')}"
            return True, 'ok'
        if command_type == 'pick_and_place':
            if cmd.get('object') not in self.objects:
                return False, f"Unbekanntes Objekt: {cmd.get('object')}"
            if cmd.get('room') not in self.rooms:
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
        self.history.append({'event': 'start', 'command': cmd, 't': time.time()})
        self._publish_status()

        send_future = self.mission_client.send_goal_async(
            goal, feedback_callback=self._on_mission_feedback)
        send_future.add_done_callback(self._on_goal_response)

    def _on_goal_response(self, future):
        goal_handle = future.result()
        if not goal_handle.accepted:
            self._finish('failed', 'fehler',
                         'Mission vom bt_orchestrator abgelehnt (laeuft dort schon eine?).',
                         self.active_command)
            return
        self._goal_handle = goal_handle
        self.message = 'Mission angenommen, laeuft ...'
        self._publish_status()
        goal_handle.get_result_async().add_done_callback(self._on_mission_result)

    def _on_mission_feedback(self, feedback_msg):
        fb = feedback_msg.feedback
        if self.state != 'running' or self.mode != 'real':
            return
        if fb.phase:
            self.phase = fb.phase
        self.progress = float(fb.progress)
        self.message = f'Phase: {self.phase}'
        self._publish_status()

    def _on_mission_result(self, future):
        result = future.result().result
        self._goal_handle = None
        if result.success:
            self._finish('success', 'fertig',
                         result.message or 'Mission erfolgreich abgeschlossen',
                         self.active_command, progress=1.0)
        else:
            # Abbruch wurde bereits in _cancel_current als 'canceled' gemeldet;
            # sonst echter Fehlschlag.
            if self.state != 'canceled':
                self._finish('failed', 'fehler',
                             result.message or 'Mission fehlgeschlagen',
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
            self.current_phases = ['Ort aufloesen', 'Navigation starten', 'Ziel erreicht']
        elif command_type == 'pick_object':
            self.current_phases = ['Objekt suchen', 'Greifpose berechnen', 'Greifen', 'Griff pruefen']
        else:
            self.current_phases = ['Schritt 1', 'Schritt 2', 'Schritt 3']

        self.phase = self.current_phases[0]
        self.message = f'Mission gestartet: {command_type} (Simulation - noch kein Baum)'
        self.history.append({'event': 'start_sim', 'command': cmd, 't': time.time()})
        self._publish_status()

    def _timer_tick(self):
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
        if self.state == 'running' and self.mode == 'real' and self._goal_handle is not None:
            self._goal_handle.cancel_goal_async()
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

    def _on_catalog(self, msg: String):
        try:
            cat = json.loads(msg.data)
        except json.JSONDecodeError:
            return
        objs = cat.get('objects')
        rooms = cat.get('rooms')
        changed = False
        if isinstance(objs, list) and objs and objs != self.objects:
            self.objects = list(objs)
            changed = True
        if isinstance(rooms, list) and rooms and rooms != self.rooms:
            self.rooms = list(rooms)
            changed = True
        if changed:
            self.get_logger().info(
                f"Katalog aus Semantik aktualisiert: {len(self.objects)} Objekte, "
                f"{len(self.rooms)} Raeume.")
            self._publish_status()

    # ======================= Statusausgabe =============================
    def _publish_status(self):
        payload = {
            'state': self.state,
            'phase': self.phase,
            'message': self.message,
            'progress': self.progress,
            'active_command': self.active_command,
            'rooms': self.rooms,
            'targets': self.targets,
            'objects': self.objects,
            'offboard_available': self.offboard_available,
            'last_rejection': self.last_rejection,
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
