#!/usr/bin/env python3
"""Prüfkontur für die Rückfahrt (Nav2 BackUp), nur im Selbstheilungsbetrieb.

WARUM (SH-7N, 08.11.2026): Amadeus fuhr bis auf 1–5 cm an echte Hindernisse
heran (Garderobe, Ecke). Der Behavior-Server prüft bei BackUp zuerst die
*aktuelle* Pose mit der vollen gepolsterten Roboterkontur. Lag diese schon an
einer belegten 5-cm-Zelle an, brach die Rückfahrt nach 1 ms mit „Collision
Ahead“ ab, obwohl hinter dem Roboter frei war (Humble und Jazzy gleich).

Eine gerade Rückwärtsfahrt bewegt den Roboter nie auf Hindernisse vor ihm
oder neben ihm zu. Neu befahren wird nur die Fläche hinter dem Heck, so breit
wie der Roboter. Diese Kontur deckt genau das ab:

* Heck mit dem Polster der lokalen Karte (Fahrtrichtung, volle Vorsicht),
* Breite 1 cm unter der echten halben Breite, damit eine Wand längs der
  Flanke die Prüfung nicht schon im Stand blockiert,
* vorn endet sie innerhalb des Roboters; was vor ihm anliegt, zählt nicht.

Der Behavior-Server prüft damit weiterhin laufend 2 s voraus gegen die lokale
Karte. Regler (RPP) und Kollisionsmonitor nutzen unverändert die volle
gepolsterte Kontur. Der Knoten publiziert nur Geometrie und bewegt nichts.
"""
import math

import rclpy
from geometry_msgs.msg import Point32, PolygonStamped
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node

# Gemessene Plattform (nav2_params_real.yaml, lokale Karte): vorn 0,31 m,
# hinten 0,11 m, halbe Breite 0,23 m, Polster 0,02 m.
STANDARD_PUNKTE = (0.05, 0.22, 0.05, -0.22, -0.13, -0.22, -0.13, 0.22)


def kontur_punkte(werte):
    """Flache Liste x0, y0, x1, y1, … in Punkte; prüft Form und Endlichkeit."""
    werte = [float(v) for v in werte]
    if len(werte) < 6 or len(werte) % 2:
        raise ValueError('punkte braucht mindestens drei x/y-Paare')
    if not all(math.isfinite(v) for v in werte):
        raise ValueError('punkte muss endlich sein')
    punkte = list(zip(werte[0::2], werte[1::2]))
    flaeche = 0.5*sum(x0*y1 - x1*y0 for (x0, y0), (x1, y1)
                      in zip(punkte, punkte[1:] + punkte[:1]))
    if abs(flaeche) < 1e-4:
        raise ValueError('punkte umschließen keine Fläche')
    return punkte


def polygon(punkte, frame_id, stamp):
    nachricht = PolygonStamped()
    nachricht.header.frame_id = frame_id
    nachricht.header.stamp = stamp
    nachricht.polygon.points = [Point32(x=float(x), y=float(y), z=0.0) for x, y in punkte]
    return nachricht


class RueckfahrKontur(Node):

    def __init__(self):
        super().__init__('rueckfahr_kontur')
        self.declare_parameter('topic', 'rueckfahr_kontur')
        self.declare_parameter('frame_id', 'base_link')
        self.declare_parameter('punkte', list(STANDARD_PUNKTE))
        self.declare_parameter('rate_hz', 2.0)
        self._punkte = kontur_punkte(self.get_parameter('punkte').value)
        self._frame = str(self.get_parameter('frame_id').value).strip()
        rate = float(self.get_parameter('rate_hz').value)
        if not self._frame or not 0.2 <= rate <= 20.0:
            raise ValueError('frame_id leer oder rate_hz außerhalb 0,2–20')
        self._pub = self.create_publisher(
            PolygonStamped, str(self.get_parameter('topic').value), 10)
        self.create_timer(1.0/rate, self._senden)
        self._senden()
        self.get_logger().info(
            f'Rückfahrkontur {self._punkte} im Rahmen {self._frame} auf {self._pub.topic_name}')

    def _senden(self):
        self._pub.publish(polygon(self._punkte, self._frame, self.get_clock().now().to_msg()))


def main(args=None):
    rclpy.init(args=args)
    node = None
    try:
        node = RueckfahrKontur()
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        if node is not None:
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
