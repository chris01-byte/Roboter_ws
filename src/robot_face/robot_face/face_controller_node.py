#!/usr/bin/env python3
# ============================================================================
#  face_controller_node.py  -  Ereignisse -> Gesichtsausdruck
#  ---------------------------------------------------------------------------
#  ZWECK:
#    Uebersetzt System-Ereignisse in EINEN aktuellen Gesichtsausdruck fuer
#    die Web-Anzeige (web/face.js). Kein bestehender Node muss dafuer
#    angepasst werden - dieser Controller haengt sich an die vorhandenen
#    Status-Topics (gleiches Muster wie llm_planner vor dem mission_manager).
#
#  ERWEITERBARKEIT (bewusst von Anfang an):
#    Neue Ausloeser (Personenerkennung, Beruehrung, Mikrofon, ...) muessen
#    diesen Node NICHT aendern. Sie publizieren einfach auf /face/event:
#      {"event": "person_detected"}                      -> Name wird ueber
#         config/event_expression_map.yaml aufgeloest (nur Dateneintrag!)
#      {"expression": "happy", "prio": 50, "ttl_s": 3}   -> direkt, ohne Map
#
#  EINGAENGE (alle vorhanden bzw. generisch):
#    /mission_manager/status_json   (String)  Missionszustand
#    /safety/estop                  (Bool)    Not-Aus (hat immer Vorrang)
#    /offboard/available            (Bool)    KI-Server erreichbar?
#    /llm_planner/status_json       (String)  Sprachauftrag verstanden/abgelehnt
#    /llm_planner/instruction       (String)  Anweisung eingegangen -> denkt nach
#    /face/event                    (String)  generischer Ereignis-Bus (Zukunft)
#
#  AUSGANG:
#    /face/state_json (String, latched + 1-Hz-Republish):
#      {"expression": "...", "source": "...", "detail": "...", "time": ...}
#
#  AUSDRUECKE (Namen = Schluessel in Map-Datei und web/face.js):
#    neutral, listening, thinking, happy, sad, surprised, alarm,
#    confused, sleeping
#
#  ALLE PARAMETER -> config/face_params.yaml; das Ereignis->Ausdruck-Mapping
#  liegt bewusst in einer EIGENEN Datei config/event_expression_map.yaml.
# ============================================================================

import json
import os
import time
from typing import Dict, List, Optional

import yaml

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, QoSDurabilityPolicy, QoSReliabilityPolicy
from std_msgs.msg import String, Bool

from ament_index_python.packages import get_package_share_directory


class ActiveEvent:
    """Ein gerade wirksames Ereignis (Zustand ODER kurzer Impuls)."""

    def __init__(self, name: str, expression: str, prio: int,
                 deadline: Optional[float], source: str, detail: str = ''):
        self.name = name
        self.expression = expression
        self.prio = prio
        self.deadline = deadline      # None = Zustand (bleibt bis geloescht)
        self.source = source
        self.detail = detail
        self.stamp = time.monotonic()

    def expired(self, now: float) -> bool:
        return self.deadline is not None and now > self.deadline


class FaceController(Node):
    def __init__(self):
        super().__init__('face_controller')

        # -------------------------------------------------------------------
        #  Parameter
        # -------------------------------------------------------------------
        gp = lambda n, d: self.declare_parameter(n, d).value
        self.mission_topic  = str(gp('mission_status_topic', '/mission_manager/status_json'))
        self.estop_topic    = str(gp('estop_topic', '/safety/estop'))
        self.offboard_topic = str(gp('offboard_topic', '/offboard/available'))
        self.llm_status_topic = str(gp('llm_status_topic', '/llm_planner/status_json'))
        self.llm_instr_topic  = str(gp('llm_instruction_topic', '/llm_planner/instruction'))
        self.event_topic    = str(gp('event_topic', '/face/event'))
        self.state_topic    = str(gp('state_topic', '/face/state_json'))
        self.tick_hz        = float(gp('tick_hz', 10.0))
        self.sleep_timeout_s = float(gp('sleep_timeout_s', 120.0))
        map_file            = str(gp('expression_map_file', ''))

        # -------------------------------------------------------------------
        #  Ereignis->Ausdruck-Mapping laden (reine Datendatei)
        # -------------------------------------------------------------------
        if not map_file:
            map_file = os.path.join(get_package_share_directory('robot_face'),
                                    'config', 'event_expression_map.yaml')
        with open(map_file, 'r', encoding='utf-8') as f:
            self.event_map: Dict[str, dict] = (yaml.safe_load(f) or {}).get('events', {})
        self.get_logger().info(
            f"Ereignis-Mapping geladen ({len(self.event_map)} Eintraege): {map_file}")

        # -------------------------------------------------------------------
        #  Zustand
        # -------------------------------------------------------------------
        self.active: List[ActiveEvent] = []
        self.last_activity = time.monotonic()
        self.last_published: Optional[str] = None
        self.last_pub_time = 0.0
        self.mission_state = 'idle'

        # -------------------------------------------------------------------
        #  ROS-Schnittstellen
        # -------------------------------------------------------------------
        latched = QoSProfile(depth=1)
        latched.reliability = QoSReliabilityPolicy.RELIABLE
        latched.durability = QoSDurabilityPolicy.TRANSIENT_LOCAL
        self.state_pub = self.create_publisher(String, self.state_topic, latched)

        self.create_subscription(String, self.mission_topic, self._on_mission, 10)
        self.create_subscription(Bool, self.estop_topic, self._on_estop, 10)
        self.create_subscription(Bool, self.offboard_topic, self._on_offboard, 10)
        self.create_subscription(String, self.llm_status_topic, self._on_llm_status, 10)
        self.create_subscription(String, self.llm_instr_topic, self._on_llm_instruction, 10)
        self.create_subscription(String, self.event_topic, self._on_external_event, 10)

        self.create_timer(1.0 / self.tick_hz, self._tick)
        self._publish('neutral', 'startup', 'Gesicht bereit')
        self.get_logger().info(
            f"face_controller bereit -> publiziert '{self.state_topic}'.")

    # ======================= Ereignisverwaltung =========================
    def _raise(self, name: str, source: str, detail: str = '',
               override: Optional[dict] = None):
        """Ereignis ausloesen. Definition kommt aus der Map-Datei oder
        (fuer den generischen Bus) direkt aus der Nachricht (override)."""
        spec = override if override is not None else self.event_map.get(name)
        if spec is None:
            self.get_logger().warn(
                f"Unbekanntes Ereignis '{name}' (nicht in event_expression_map.yaml) "
                "- ignoriert.")
            return
        expression = str(spec.get('expression', 'neutral'))
        prio = int(spec.get('prio', 10))
        ttl = float(spec.get('ttl_s', 0.0))
        now = time.monotonic()
        deadline = (now + ttl) if ttl > 0.0 else None

        self._clear(name)                       # gleiches Ereignis ersetzen
        self.active.append(ActiveEvent(name, expression, prio, deadline,
                                       source, detail))
        self.last_activity = now

    def _clear(self, name: str):
        self.active = [e for e in self.active if e.name != name]

    # ======================= Eingaenge ==================================
    def _on_estop(self, msg: Bool):
        # Not-Aus ist ein ZUSTAND (ttl_s: 0 in der Map) und ueberstimmt alles.
        if msg.data:
            self._raise('estop_active', self.estop_topic, 'Not-Aus aktiv')
        else:
            self._clear('estop_active')
            self.last_activity = time.monotonic()

    def _on_offboard(self, msg: Bool):
        if msg.data:
            self._clear('offboard_lost')
        else:
            self._raise('offboard_lost', self.offboard_topic,
                        'KI-Server nicht erreichbar')

    def _on_mission(self, msg: String):
        try:
            status = json.loads(msg.data)
        except json.JSONDecodeError:
            return
        state = str(status.get('state', 'idle'))
        if state == self.mission_state:
            return                              # nur Zustandswechsel interessiert
        self.mission_state = state
        detail = str(status.get('message', ''))

        self._clear('mission_running')
        if state == 'running':
            self._raise('mission_running', self.mission_topic, detail)
        elif state == 'success':
            self._raise('mission_success', self.mission_topic, detail)
        elif state == 'failed':
            self._raise('mission_failed', self.mission_topic, detail)
        elif state == 'canceled':
            self._raise('mission_canceled', self.mission_topic, detail)
        # 'idle' -> nichts aktiv lassen

    def _on_llm_instruction(self, msg: String):
        text = (msg.data or '').strip()
        if text:
            self._raise('llm_thinking', self.llm_instr_topic, text[:80])

    def _on_llm_status(self, msg: String):
        try:
            status = json.loads(msg.data)
        except json.JSONDecodeError:
            return
        self._clear('llm_thinking')             # Antwort ist da
        state = str(status.get('state', ''))
        detail = str(status.get('detail', ''))
        if state == 'dispatched':
            self._raise('llm_dispatched', self.llm_status_topic, detail)
        elif state == 'rejected':
            self._raise('llm_rejected', self.llm_status_topic, detail)

    def _on_external_event(self, msg: String):
        """Generischer Bus fuer KUENFTIGE Ausloeser (Person erkannt,
        Beruehrung, ...). Zwei Formen, siehe Kopfkommentar."""
        try:
            data = json.loads(msg.data)
        except json.JSONDecodeError:
            self.get_logger().warn('face/event: ungueltiges JSON - ignoriert.')
            return
        name = str(data.get('event', '')).strip()
        if name:
            self._raise(name, self.event_topic, str(data.get('detail', '')))
            return
        if 'expression' in data:                # Direktform ohne Map-Eintrag
            self._raise(f"direct_{data['expression']}", self.event_topic,
                        str(data.get('detail', '')),
                        override=dict(expression=data['expression'],
                                      prio=data.get('prio', 10),
                                      ttl_s=data.get('ttl_s', 3.0)))

    # ======================= Auswertung / Ausgabe =======================
    def _tick(self):
        now = time.monotonic()
        self.active = [e for e in self.active if not e.expired(now)]

        if self.active:
            # Hoechste Prioritaet gewinnt; bei Gleichstand das juengste.
            best = max(self.active, key=lambda e: (e.prio, e.stamp))
            self._publish(best.expression, best.source, best.detail,
                          event=best.name)
        elif now - self.last_activity > self.sleep_timeout_s:
            self._publish('sleeping', 'face_controller',
                          f'keine Aktivitaet seit {int(self.sleep_timeout_s)} s')
        else:
            self._publish('neutral', 'face_controller', '')

    def _publish(self, expression: str, source: str, detail: str,
                 event: str = ''):
        now = time.monotonic()
        # Nur bei Aenderung sofort senden, sonst 1x pro Sekunde auffrischen
        # (rosbridge-Clients, die sich spaeter verbinden, bekommen so Stand).
        if expression == self.last_published and now - self.last_pub_time < 1.0:
            return
        payload = {
            'expression': expression,
            'event': event,
            'source': source,
            'detail': detail,
            'active': [e.name for e in sorted(self.active,
                                              key=lambda e: -e.prio)],
            'time': time.time(),
        }
        self.state_pub.publish(String(data=json.dumps(payload, ensure_ascii=False)))
        if expression != self.last_published:
            self.get_logger().info(f"Ausdruck: {expression}"
                                   + (f" (Ereignis: {event})" if event else ''))
        self.last_published = expression
        self.last_pub_time = now


def main(args=None):
    rclpy.init(args=args)
    node = FaceController()
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
