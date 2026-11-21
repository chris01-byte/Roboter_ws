#!/usr/bin/env python3
"""Kontur für den Kollisionsmonitor (KM-2), nur im Selbstheilungsbetrieb.

WARUM (SH-8 am 13.11.2026 und SH-8c am 15.11.2026, Mülleimer): Der
Kollisionsmonitor prüft „approach“ gegen die gepolsterte Roboterkontur
(Gehäuse plus 2 cm). Liegt ein VL53-Punkt in diesem Polsterband, setzt er
jede Bewegung auf null, auch die gerade Rückfahrt vom Hindernis weg. In
SH-8c s3a hielt er die Rückfahrt 16 s lang an (102 VL53-Punkte im
Polsterband); danach gab es keinen Ausweg mehr, und es kam „Hilfe benötigt“.

Dieser Knoten liefert dem Kollisionsmonitor die Kontur, gegen die er prüft:

* **Normalfall** (Vorwärtsfahrt, Drehen, Stand, kein oder ein alter Befehl):
  die volle gepolsterte Kontur, wie bisher aus der lokalen Karte.
* **Nur bei reiner gerader Rückwärtsfahrt** (v deutlich negativ, praktisch
  keine Drehung): die Rückfahrkontur aus AW-1. Eine gerade Rückwärtsfahrt
  bewegt den Roboter nie auf Hindernisse vor ihm oder neben ihm zu; neu
  befahren wird nur die Fläche hinter dem Heck. Die VL53 sehen ohnehin nur
  nach vorn.

Damit bleibt die Sperre für Vorwärtsfahrt und Drehen bestehen (Variante A
vom 09.11.2026 nahm das Polster immer weg und wurde verworfen, weil das
Gehäuse beim Drehen berührte). Die Langsam-Zone des Kollisionsmonitors gilt
unverändert, auch rückwärts. Der Knoten publiziert nur Geometrie und bewegt
nichts.
"""
import time

import rclpy
from geometry_msgs.msg import PolygonStamped, Twist
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node

from robot_navigation.rueckfahr_kontur import STANDARD_PUNKTE, kontur_punkte, polygon

# Gehäuse vorn 0,31 m, hinten 0,11 m, halbe Breite 0,23 m, dazu 0,02 m Polster:
# dieselbe Kontur, die die lokale Karte als published_footprint ausgibt.
VOLL_PUNKTE = (0.33, 0.25, 0.33, -0.25, -0.13, -0.25, -0.13, 0.25)
V_RUECK_MPS = -0.004       # ab hier gilt ein Befehl als Rückwärtsfahrt
W_GERADE_RADPS = 0.02      # bis hier gilt er als gerade
BEFEHL_ALTER_S = 0.3       # älter: Normalfall


def rueckzug_erlaubt(v, w, alter_s):
    """True nur für einen frischen Befehl „gerade rückwärts“."""
    return (alter_s is not None and 0.0 <= alter_s <= BEFEHL_ALTER_S
            and v <= V_RUECK_MPS and abs(w) <= W_GERADE_RADPS)


class MonitorKontur(Node):

    def __init__(self):
        super().__init__('monitor_kontur')
        self.declare_parameter('topic', 'kollisionsmonitor_kontur')
        self.declare_parameter('befehl_topic', 'cmd_vel_smoothed')
        self.declare_parameter('frame_id', 'base_link')
        self.declare_parameter('voll_punkte', list(VOLL_PUNKTE))
        self.declare_parameter('rueckzug_punkte', list(STANDARD_PUNKTE))
        self.declare_parameter('rate_hz', 20.0)
        self._voll = kontur_punkte(self.get_parameter('voll_punkte').value)
        self._rueckzug = kontur_punkte(self.get_parameter('rueckzug_punkte').value)
        self._frame = str(self.get_parameter('frame_id').value).strip()
        rate = float(self.get_parameter('rate_hz').value)
        if not self._frame or not 5.0 <= rate <= 50.0:
            raise ValueError('frame_id leer oder rate_hz außerhalb 5–50')
        self._befehl = None                  # (Zeit, v, w)
        self._rueckzug_aktiv = False
        self._pub = self.create_publisher(
            PolygonStamped, str(self.get_parameter('topic').value), 10)
        self.create_subscription(
            Twist, str(self.get_parameter('befehl_topic').value), self._on_befehl, 10)
        self.create_timer(1.0/rate, self._senden)
        self._senden()
        self.get_logger().info(
            f'Kollisionsmonitor-Kontur auf {self._pub.topic_name}: voll {self._voll}, '
            f'bei gerader Rückfahrt {self._rueckzug}')

    def _on_befehl(self, nachricht):
        self._befehl = (time.monotonic(), nachricht.linear.x, nachricht.angular.z)
        self._senden()                       # sofort, nicht erst beim nächsten Takt

    def _senden(self):
        befehl = self._befehl
        aktiv = befehl is not None and rueckzug_erlaubt(
            befehl[1], befehl[2], time.monotonic() - befehl[0])
        if aktiv != self._rueckzug_aktiv:
            self._rueckzug_aktiv = aktiv
            self.get_logger().info(
                'Kontur: Rückzug (gerade Rückwärtsfahrt)' if aktiv else 'Kontur: voll')
        self._pub.publish(polygon(self._rueckzug if aktiv else self._voll, self._frame,
                                  self.get_clock().now().to_msg()))


def main(args=None):
    rclpy.init(args=args)
    node = None
    try:
        node = MonitorKontur()
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
