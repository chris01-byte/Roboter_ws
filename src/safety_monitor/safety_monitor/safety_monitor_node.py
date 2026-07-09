#!/usr/bin/env python3
# ============================================================================
#  safety_monitor_node.py  -  Onboard-Not-Aus-Waechter (Befund K4)
#  ===========================================================================
#  ZWECK:
#    Publiziert das Topic /safety/estop, das der Behavior-Tree bei JEDEM Tick
#    prueft (IsEstopClear). Vorher gab es dafuer auf dem echten Roboter KEINEN
#    Publisher -> jede echte Mission waere sofort mit FAILURE gestorben (das
#    fiel erst auf, seit Missionen mit K1 wirklich laufen). Dieser Node
#    schliesst die Luecke und ist die Onboard-Sicherheitsebene aus Sicht des
#    BT.
#
#  KONVENTION /safety/estop (std_msgs/Bool, latched):
#    data == true   -> Not-Aus AKTIV (BT haelt sofort an)
#    data == false  -> frei (Roboter darf arbeiten)
#    (deckt sich mit condition_nodes.hpp und den Mock-Servern)
#
#  QUELLEN DES NOT-AUS (ODER-verknuepft):
#    1) Software-Anforderung  /safety/estop_request (Bool) - z.B. GUI-Button
#       oder eine kleine Bruecke von einem Hardware-Taster. true = ausgeloest.
#    2) Optional Nahbereich   near_field/status: nur wenn use_near_field_estop
#       (Default AUS). Gedacht als HARTE Notbremse bei EXTREM naher Distanz -
#       die normale reaktive Verlangsamung macht weiter der collision_monitor.
#    3) Hardware-Taster (GPIO): Platzhalter (wie base_hardware RS485) - erst
#       aktiv, wenn Jetson.GPIO eingebunden ist. Bis dahin ueber (1) bruecken.
#
#  WICHTIG (Ruhestromprinzip, Befund S5): ein echter Hardware-Not-Aus MUSS
#  fail-safe verdrahtet sein (Drahtbruch -> ausgeloest). Solange nur die
#  Software-Anforderung genutzt wird, ist das NICHT gegeben - der Node meldet
#  das beim Start klar. Die hardwired Sicherheitskette bleibt die primaere
#  Ebene; dieser Node ist die Firmware-/BT-Sicht darauf.
#
#  ALLE PARAMETER -> config/safety_monitor_params.yaml.
# ============================================================================

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, QoSDurabilityPolicy, QoSReliabilityPolicy
from std_msgs.msg import Bool

from robot_interfaces.msg import NearFieldStatus


class SafetyMonitor(Node):
    def __init__(self):
        super().__init__('safety_monitor')

        # -------------------------------------------------------------------
        #  Parameter
        # -------------------------------------------------------------------
        gp = lambda n, d: self.declare_parameter(n, d).value
        self._estop_topic     = str(gp('estop_topic', '/safety/estop'))
        self._request_topic   = str(gp('estop_request_topic', '/safety/estop_request'))
        self._publish_period  = float(gp('publish_period_s', 0.2))
        self._initial_estop   = bool(gp('initial_estop', False))
        # Nahbereich als harte Notbremse (Default aus - siehe Kopf).
        self._use_near_field  = bool(gp('use_near_field_estop', False))
        self._nf_status_topic = str(gp('near_field_status_topic', '/near_field/status'))
        self._nf_estop_dist   = float(gp('near_field_estop_dist_m', 0.08))
        # Hardware-Taster (Platzhalter, noch nicht implementiert).
        self._use_gpio        = bool(gp('use_gpio_estop', False))
        self._gpio_pin        = int(gp('gpio_estop_pin', 0))

        # -------------------------------------------------------------------
        #  Zustand (ODER-Quellen)
        # -------------------------------------------------------------------
        self._request_estop = self._initial_estop   # Software-Anforderung
        self._near_estop = False                     # Nahbereich
        self._last_published = None

        # -------------------------------------------------------------------
        #  Publisher (latched: spaete Subscriber bekommen den letzten Stand)
        # -------------------------------------------------------------------
        latched = QoSProfile(depth=1)
        latched.reliability = QoSReliabilityPolicy.RELIABLE
        latched.durability = QoSDurabilityPolicy.TRANSIENT_LOCAL
        self._estop_pub = self.create_publisher(Bool, self._estop_topic, latched)

        # -------------------------------------------------------------------
        #  Eingaenge
        # -------------------------------------------------------------------
        self.create_subscription(Bool, self._request_topic, self._on_request, 10)
        if self._use_near_field:
            self.create_subscription(
                NearFieldStatus, self._nf_status_topic, self._on_near_field, 10)

        if self._use_gpio:
            self.get_logger().warn(
                "use_gpio_estop=true, aber die GPIO-Anbindung ist noch NICHT "
                "implementiert (Platzhalter). Bis dahin Not-Aus ueber "
                f"'{self._request_topic}' bruecken.")

        # Sofort publizieren + periodisch nachpublizieren.
        self._publish()
        self.create_timer(self._publish_period, self._publish)

        self.get_logger().info(
            f"safety_monitor bereit -> '{self._estop_topic}' "
            f"(Start: {'NOT-AUS' if self._request_estop else 'frei'}). "
            f"Anforderung an '{self._request_topic}'.")
        if not self._use_gpio:
            self.get_logger().warn(
                "Kein Hardware-Not-Aus angebunden (use_gpio_estop=false). Das "
                "Ruhestromprinzip (Drahtbruch -> ausgeloest) ist damit NICHT "
                "erfuellt - die hardwired Sicherheitskette bleibt Pflicht.")

    # ======================= Eingaenge ==================================
    def _on_request(self, msg: Bool):
        if self._request_estop != msg.data:
            self._request_estop = bool(msg.data)
            self.get_logger().warn(
                f"Not-Aus-Anforderung (Software): {'AUSGELOEST' if msg.data else 'zurueckgesetzt'}.")
            self._publish()

    def _on_near_field(self, msg: NearFieldStatus):
        # Nur gueltige (>=0) Distanzen betrachten; -1.0 = Zone leer/ungueltig.
        dists = [d for d in (msg.min_dist_left, msg.min_dist_right, msg.min_dist_middle)
                 if d >= 0.0]
        too_close = any(d < self._nf_estop_dist for d in dists)
        if too_close != self._near_estop:
            self._near_estop = too_close
            if too_close:
                self.get_logger().warn(
                    f"Nahbereich-Notbremse: Objekt naeher als {self._nf_estop_dist:.2f} m.")
            self._publish()

    # ======================= Ausgabe ====================================
    def _estop_active(self) -> bool:
        return bool(self._request_estop or self._near_estop)

    def _publish(self):
        active = self._estop_active()
        self._estop_pub.publish(Bool(data=active))
        if active != self._last_published:
            self.get_logger().info(
                f"/safety/estop = {active} ({'NOT-AUS aktiv' if active else 'frei'}).")
            self._last_published = active


def main(args=None):
    rclpy.init(args=args)
    node = SafetyMonitor()
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
