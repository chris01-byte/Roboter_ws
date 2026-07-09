#!/usr/bin/env python3
# ============================================================================
#  link_monitor_node.py  -  Server-Erreichbarkeit ueberwachen (WP-5 Baustein D)
#  ---------------------------------------------------------------------------
#  ZWECK:
#    Der mobile Roboter (ONBOARD) und der KI-Server (OFFBOARD) reden ueber
#    ROS 2 DDS via WLAN. Faellt das WLAN oder der Server aus, muss der Roboter
#    das WISSEN, um sicher weiterzuarbeiten (Sicherheit/Navigation/Exploration
#    laufen lokal weiter; nur die KI-Funktionen entfallen).
#
#    Dieser Node prueft periodisch, ob die erwarteten Offboard-Nodes im
#    ROS-2-Graphen sichtbar sind, und meldet das Ergebnis:
#      /offboard/available    (std_msgs/Bool)   true = Server erreichbar
#      /offboard/status_json  (std_msgs/String) Details (welche Nodes fehlen)
#
#    GUI und mission_manager koennen so anzeigen/entscheiden, ob KI-Funktionen
#    (LLM-Planer, Semantik) gerade verfuegbar sind.
#
#  ALLE PARAMETER -> config/link_monitor_params.yaml.
#
#  HINWEIS: Graph-Sichtbarkeit ist ein einfacher, robuster Erreichbarkeits-
#  Indikator. Fuer harte Echtzeit-Garantien ist sie NICHT gedacht - die
#  Sicherheit haengt bewusst NICHT vom Server ab (sie ist rein onboard).
# ============================================================================

import json

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, QoSDurabilityPolicy, QoSReliabilityPolicy
from std_msgs.msg import Bool, String


class LinkMonitor(Node):
    def __init__(self):
        super().__init__('link_monitor')

        # -------------------------------------------------------------------
        #  Parameter
        # -------------------------------------------------------------------
        self._watched = list(self.declare_parameter(
            'watched_nodes', ['llm_planner', 'semantic_perception']).value)
        self._period_s = float(self.declare_parameter('check_period_s', 2.0).value)

        # -------------------------------------------------------------------
        #  Publisher (transient_local: spaete Abonnenten bekommen letzten Stand)
        # -------------------------------------------------------------------
        latched = QoSProfile(depth=1)
        latched.reliability = QoSReliabilityPolicy.RELIABLE
        latched.durability = QoSDurabilityPolicy.TRANSIENT_LOCAL

        self._avail_pub = self.create_publisher(Bool, '/offboard/available', latched)
        self._status_pub = self.create_publisher(String, '/offboard/status_json', latched)

        self._last_available = None
        self._timer = self.create_timer(self._period_s, self._check)
        self.get_logger().info(
            f"link_monitor bereit. Ueberwache Offboard-Nodes: {self._watched}")

    def _check(self):
        # Alle aktuell im ROS-2-Graphen sichtbaren Node-Namen abfragen.
        try:
            graph_names = set(self.get_node_names())
        except Exception as exc:
            self.get_logger().warn(f"Graph-Abfrage fehlgeschlagen: {exc}")
            return

        present = [n for n in self._watched if n in graph_names]
        missing = [n for n in self._watched if n not in graph_names]
        available = len(present) > 0   # mindestens ein Offboard-Node sichtbar

        self._avail_pub.publish(Bool(data=available))
        payload = {
            'available': available,
            'watched': self._watched,
            'present': present,
            'missing': missing,
        }
        self._status_pub.publish(String(data=json.dumps(payload, ensure_ascii=False)))

        # Nur bei Zustandswechsel loggen (nicht spammen).
        if available != self._last_available:
            if available:
                self.get_logger().info(f"Offboard-Server ERREICHBAR (aktiv: {present})")
            else:
                self.get_logger().warn(
                    "Offboard-Server NICHT erreichbar - KI-Funktionen entfallen, "
                    "Sicherheit/Navigation/Exploration laufen lokal weiter.")
            self._last_available = available


def main(args=None):
    rclpy.init(args=args)
    node = LinkMonitor()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
