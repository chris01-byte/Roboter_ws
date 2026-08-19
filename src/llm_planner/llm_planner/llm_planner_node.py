#!/usr/bin/env python3
# ============================================================================
#  llm_planner_node.py  -  Sprach-/Aufgabenplaner (WP-5 Baustein C, OFFBOARD)
#  ---------------------------------------------------------------------------
#  ZWECK:
#    Wandelt eine natuerlichsprachige Anweisung ("Bring mir die Tasse aus der
#    Kueche") in EINEN strukturierten Missionsauftrag im BESTEHENDEN
#    command_json-Format des mission_manager um und schickt ihn dorthin.
#    Der mission_manager bleibt damit UNVERAENDERT - der LLM-Planer haengt
#    sich einfach davor.
#
#  WICHTIG (Architektur):
#    - Laeuft OFFBOARD auf dem KI-Server (Ubuntu/ROS 2, RTX 3090).
#    - ASYNCHRON und High-Level - NIE im Echtzeit-Regelkreis.
#    - Faellt der Server/das WLAN aus, kommen einfach keine neuen Auftraege;
#      der Roboter bleibt sicher (Sicherheit/Navigation laufen onboard).
#
#  SCHNITTSTELLEN:
#    Eingang : /llm_planner/instruction     (std_msgs/String, Klartext)
#    Ausgang : /mission_manager/command_json (std_msgs/String, JSON-Auftrag)
#    Status  : /llm_planner/status_json      (std_msgs/String, was verstanden)
#
#  LLM-BACKEND:
#    Standard = Ollama (lokales LLM, HTTP-API). Ist Ollama nicht erreichbar
#    ODER use_ollama=false, greift ein einfacher regelbasierter Parser als
#    Fallback - so ist der Node auch OHNE LLM trocken testbar.
#
#  ALLE PARAMETER -> config/llm_planner_params.yaml.
# ============================================================================

import json
from typing import Dict, List, Optional

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, QoSDurabilityPolicy, QoSReliabilityPolicy
from std_msgs.msg import String

from llm_planner.catalog import CatalogValidationError, merge_catalog_json


MAXIMUM_LLM_RESPONSE_BYTES = 64 * 1024


class LlmPlanner(Node):
    def __init__(self):
        super().__init__('llm_planner')

        # -------------------------------------------------------------------
        #  Parameter
        # -------------------------------------------------------------------
        self._use_ollama   = bool(self.declare_parameter('use_ollama', True).value)
        self._ollama_url   = self.declare_parameter('ollama_url', 'http://localhost:11434').value
        self._model        = self.declare_parameter('model', 'llama3.2').value
        self._temperature  = float(self.declare_parameter('temperature', 0.1).value)
        self._timeout_s    = float(self.declare_parameter('request_timeout_s', 30.0).value)
        self._instr_topic  = self.declare_parameter('instruction_topic', '/llm_planner/instruction').value
        self._command_topic = self.declare_parameter('command_topic', '/mission_manager/command_json').value
        self._rooms   = list(self.declare_parameter('rooms', ['Wohnzimmer', 'Kueche', 'Flur']).value)
        self._targets = list(self.declare_parameter('targets', ['Tisch', 'Regal']).value)
        self._objects = list(self.declare_parameter('objects', ['Tasse', 'Flasche']).value)
        self._static_rooms = tuple(self._rooms)
        self._static_targets = tuple(self._targets)
        self._static_objects = tuple(self._objects)
        self._use_dynamic_catalog = bool(
            self.declare_parameter('use_dynamic_catalog', True).value)
        self._catalog_topic = self.declare_parameter(
            'catalog_topic', '/semantic/catalog_json').value

        # -------------------------------------------------------------------
        #  ROS-Schnittstellen
        # -------------------------------------------------------------------
        latched = QoSProfile(depth=1)
        latched.reliability = QoSReliabilityPolicy.RELIABLE
        latched.durability = QoSDurabilityPolicy.TRANSIENT_LOCAL

        self._command_pub = self.create_publisher(String, self._command_topic, 10)
        self._status_pub = self.create_publisher(String, '/llm_planner/status_json', latched)
        self.create_subscription(String, self._instr_topic, self._on_instruction, 10)
        if self._use_dynamic_catalog:
            self.create_subscription(
                String, self._catalog_topic, self._on_catalog, latched)

        mode = 'Ollama' if self._use_ollama else 'Regel-Fallback'
        self.get_logger().info(
            f"llm_planner bereit ({mode}). Anweisungen an '{self._instr_topic}', "
            f"Auftraege an '{self._command_topic}'.")

    def _on_catalog(self, msg: String):
        """Uebernimmt nur vollstaendig validierte, nichtleere Teilkataloge."""
        try:
            catalog = merge_catalog_json(
                msg.data,
                rooms=self._static_rooms,
                targets=self._static_targets,
                objects=self._static_objects,
            )
        except CatalogValidationError as exc:
            self.get_logger().warn(f"Semantik-Katalog verworfen: {exc}")
            return
        changed = (
            tuple(self._rooms) != catalog.rooms
            or tuple(self._targets) != catalog.targets
            or tuple(self._objects) != catalog.objects
        )
        self._rooms = list(catalog.rooms)
        self._targets = list(catalog.targets)
        self._objects = list(catalog.objects)
        if changed:
            self.get_logger().info(
                f"Semantik-Katalog aktiv: {len(self._rooms)} Raeume, "
                f"{len(self._targets)} Ziele, {len(self._objects)} Objekte.")

    # ======================= Eingang ====================================
    def _on_instruction(self, msg: String):
        text = (msg.data or '').strip()
        if not text:
            return
        self.get_logger().info(f"Anweisung: {text}")

        cmd = None
        if self._use_ollama:
            cmd = self._plan_with_ollama(text)
        if cmd is None:
            # Kein/gescheitertes LLM -> regelbasierter Fallback
            cmd = self._plan_rule_based(text)

        ok, reason = self._validate(cmd)
        if not ok:
            self._publish_status('rejected', text, cmd, reason)
            self.get_logger().warn(f"Auftrag verworfen: {reason}")
            return

        self._command_pub.publish(String(data=json.dumps(cmd, ensure_ascii=False)))
        self._publish_status('dispatched', text, cmd, 'an mission_manager gesendet')
        self.get_logger().info(f"Auftrag gesendet: {cmd}")

    # ======================= LLM (Ollama) ===============================
    def _plan_with_ollama(self, text: str) -> Optional[Dict]:
        """Fragt das lokale LLM ueber die Ollama-HTTP-API. None bei Fehler."""
        try:
            import requests  # lazy import: Node laeuft auch ohne requests (Fallback)
        except Exception:
            self.get_logger().warn("Python-Paket 'requests' fehlt -> Regel-Fallback.")
            return None

        payload = {
            'model': self._model,
            'messages': [
                {'role': 'system', 'content': self._build_system_prompt()},
                {'role': 'user', 'content': text},
            ],
            'stream': False,
            'options': {'temperature': self._temperature},
        }
        try:
            resp = requests.post(f"{self._ollama_url}/api/chat",
                                 json=payload, timeout=self._timeout_s)
            resp.raise_for_status()
            content = resp.json().get('message', {}).get('content', '')
        except Exception as exc:
            self.get_logger().warn(f"Ollama nicht erreichbar ({exc}) -> Regel-Fallback.")
            return None

        cmd = self._extract_json(content)
        if cmd is None:
            self.get_logger().warn(f"LLM-Antwort ohne gueltiges JSON: {content[:200]}")
        return cmd

    def _build_system_prompt(self) -> str:
        return (
            "Du bist der Aufgabenplaner eines Haushaltsroboters. Wandle die Anweisung "
            "des Nutzers in GENAU EIN JSON-Objekt um.\n"
            "Erlaubte Befehle:\n"
            '  {"type": "go_to_room", "room": <RAUM>}\n'
            '  {"type": "pick_object", "object": <OBJEKT>}\n'
            '  {"type": "pick_and_place", "object": <OBJEKT>, "room": <RAUM>, "target": <ABLAGE>}\n'
            '  {"type": "explore"}\n'
            '  {"type": "cancel"}\n'
            f"Erlaubte RAUM-Werte: {self._rooms}\n"
            f"RAUM fuer pick_and_place nur aus dieser statischen Liste: "
            f"{list(self._static_rooms)}\n"
            f"Erlaubte OBJEKT-Werte: {self._objects}\n"
            f"Erlaubte ABLAGE-Werte: {self._targets}\n"
            "Antworte AUSSCHLIESSLICH mit dem JSON-Objekt - ohne Erklaerung, ohne Markdown.\n"
            'Passt nichts, antworte mit {"type": "unknown", "reason": "<kurz>"}.'
        )

    @staticmethod
    def _extract_json(text: str) -> Optional[Dict]:
        """Holt ein begrenztes erstes JSON-Objekt fail-closed aus LLM-Text."""
        if not isinstance(text, str) or not text:
            return None
        # Das Offboard-Modell ist keine vertrauenswuerdige JSON-Quelle. Dieselbe
        # 64-KiB-Grenze wie am Missionseingang verhindert grosse Kopien; eine
        # ungueltige Surrogat-Zeichenfolge wird bereits vor json.loads verworfen.
        if len(text) > MAXIMUM_LLM_RESPONSE_BYTES:
            return None
        try:
            encoded_size = len(text.encode('utf-8'))
        except UnicodeError:
            return None
        if encoded_size > MAXIMUM_LLM_RESPONSE_BYTES:
            return None
        # ```json ... ``` entfernen, dann erstes balanciertes { ... } suchen.
        depth = 0
        start = -1
        for i, ch in enumerate(text):
            if ch == '{':
                if depth == 0:
                    start = i
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0 and start >= 0:
                    try:
                        return json.loads(text[start:i + 1])
                    except (json.JSONDecodeError, UnicodeError, RecursionError):
                        start = -1
        return None

    # ======================= Regel-Fallback =============================
    def _plan_rule_based(self, text: str) -> Dict:
        """Einfacher Schluesselwort-Parser (ohne LLM), fuer Trockentest."""
        low = text.lower()

        if any(w in low for w in ('abbrechen', 'stopp', 'stop', 'cancel', 'halt')):
            return {'type': 'cancel'}
        if any(w in low for w in ('erkunde', 'erkunden', 'erforsche', 'explore', 'umschauen', 'kartier')):
            return {'type': 'explore'}

        obj = self._match_catalog(low, self._objects)
        room = self._match_catalog(low, self._rooms)
        carry_room = self._match_catalog(low, list(self._static_rooms))
        target = self._match_catalog(low, self._targets)

        if obj and carry_room and target:
            return {
                'type': 'pick_and_place',
                'object': obj,
                'room': carry_room,
                'target': target,
            }
        if obj:
            return {'type': 'pick_object', 'object': obj}
        if room:
            return {'type': 'go_to_room', 'room': room}
        return {'type': 'unknown', 'reason': 'Keine bekannten Schluesselwoerter erkannt'}

    @staticmethod
    def _match_catalog(low_text: str, catalog: List[str]) -> Optional[str]:
        """Findet den ersten Katalog-Wert, der als Wort im Text vorkommt (tolerant)."""
        for item in catalog:
            if item.lower() in low_text:
                return item
        return None

    # ======================= Validierung ================================
    def _validate(self, cmd: Optional[Dict]):
        if not isinstance(cmd, dict) or 'type' not in cmd:
            return False, 'Kein gueltiges Auftrags-JSON'
        t = cmd['type']
        if t == 'cancel' or t == 'explore':
            return True, 'ok'
        if t == 'go_to_room':
            return (cmd.get('room') in self._rooms), f"Raum ungueltig: {cmd.get('room')}"
        if t == 'pick_object':
            return (cmd.get('object') in self._objects), f"Objekt ungueltig: {cmd.get('object')}"
        if t == 'pick_and_place':
            if cmd.get('object') not in self._objects:
                return False, f"Objekt ungueltig: {cmd.get('object')}"
            if cmd.get('room') not in self._static_rooms:
                return False, f"Raum ungueltig: {cmd.get('room')}"
            if cmd.get('target') not in self._targets:
                return False, f"Ablage ungueltig: {cmd.get('target')}"
            return True, 'ok'
        return False, f"Unbekannter/uneindeutiger Auftrag: {t}"

    # ======================= Status =====================================
    def _publish_status(self, state: str, instruction: str, cmd, detail: str):
        payload = {'state': state, 'instruction': instruction, 'command': cmd, 'detail': detail}
        self._status_pub.publish(String(data=json.dumps(payload, ensure_ascii=False)))


def main(args=None):
    rclpy.init(args=args)
    node = LlmPlanner()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
