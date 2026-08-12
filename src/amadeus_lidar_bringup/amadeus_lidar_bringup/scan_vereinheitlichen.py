#!/usr/bin/env python3
"""Setzt /scan auf eine feste Strahlenzahl um, bevor slam_toolbox ihn sieht.

WARUM DAS NOETIG IST (gemessen 12.08.2026, 424 Scans am stehenden Roboter):
Der STL-27L liefert je Umdrehung zwischen 2146 und 2176 Strahlen - 19
verschiedene Werte, der haeufigste deckt nur 25.7 % ab. Der Treiber ist dabei
in sich stimmig: er zieht ``angle_increment`` mit, sodass ``(N-1)*increment``
immer genau 360 Grad ergibt. Die Winkel stimmen also.

Karto stoert das trotzdem. ``LaserRangeFinder::Validate`` vergleicht die
Strahlenzahl mit der des ersten verarbeiteten Scans und gibt bei Abweichung
false zurueck; ``Mapper::Process`` bricht dann sofort ab - ohne Knoten, ohne
Kartenbeitrag und ohne Warnung im ROS-Log (die Meldung geht auf stdout).

Folge am realen Roboter: Von den rund 42 Scans, die eine 360-Grad-Drehung
ueber die Winkelschwelle bringen sollte, kamen nur 10 Knoten an - das sind die
25.7 %, die zufaellig die passende Strahlenzahl hatten.

Dieser Knoten haengt sich dazwischen und gibt ein festes Gitter aus. Der
Herstellertreiber bleibt unveraendert; er bietet fuer die Punktzahl ohnehin
keinen Parameter.
"""
import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, QoSReliabilityPolicy
from sensor_msgs.msg import LaserScan

from amadeus_lidar_bringup.scan_gitter import auf_gitter, gitter_indizes


class ScanVereinheitlichen(Node):

    def __init__(self):
        super().__init__('scan_vereinheitlichen')

        self.declare_parameter('eingang', '/scan')
        self.declare_parameter('ausgang', '/scan_normiert')
        # 2160 liegt innerhalb der beobachteten Spanne 2146..2176 und nahe der
        # Nennaufloesung des STL-27L (360/0.167 = 2156). Damit wird beim
        # Umsetzen eher ein Strahl verworfen als einer verdoppelt - ein
        # verdoppelter Strahl waere eine erfundene Zusatzmessung.
        self.declare_parameter('strahlen', 2160)
        self.declare_parameter('meldeintervall_s', 30.0)

        eingang = self.get_parameter('eingang').value
        ausgang = self.get_parameter('ausgang').value
        self.anzahl_aus = int(self.get_parameter('strahlen').value)
        if self.anzahl_aus < 2:
            raise ValueError('Parameter "strahlen" muss mindestens 2 sein.')

        # Sensordaten laufen best effort; mit RELIABLE wuerde der Filter
        # Nachrichten des Treibers gar nicht erst bekommen.
        qos = QoSProfile(depth=5, reliability=QoSReliabilityPolicy.BEST_EFFORT)
        self.pub = self.create_publisher(LaserScan, ausgang, qos)
        self.create_subscription(LaserScan, eingang, self._auf_scan, qos)

        self._zwischenspeicher = {}
        self.gesehen = 0
        self.umgesetzt = 0
        self.groessen = set()
        self.letzte_meldung = self.get_clock().now()

        self.get_logger().info(
            f'Vereinheitliche {eingang} -> {ausgang} auf feste '
            f'{self.anzahl_aus} Strahlen.')

    def _indizes(self, msg, inkrement_aus):
        """Indexabbildung je Eingabeformat einmal rechnen und merken.

        Der Schluessel enthaelt alles, was die Abbildung bestimmt - auch
        angle_max, denn daraus folgt das Ausgabeinkrement. Fehlte es, bliebe
        bei geaenderter Spanne eine falsche Abbildung im Speicher stehen.
        """
        schluessel = (len(msg.ranges), msg.angle_min, msg.angle_max,
                      msg.angle_increment)
        if schluessel not in self._zwischenspeicher:
            self._zwischenspeicher[schluessel] = gitter_indizes(
                len(msg.ranges), msg.angle_min, msg.angle_increment,
                self.anzahl_aus, msg.angle_min, inkrement_aus)
        return self._zwischenspeicher[schluessel]

    def _auf_scan(self, msg):
        self.gesehen += 1
        self.groessen.add(len(msg.ranges))

        if len(msg.ranges) < 2 or msg.angle_increment == 0.0:
            self.get_logger().warn(
                f'Scan mit {len(msg.ranges)} Strahlen und increment '
                f'{msg.angle_increment} verworfen - nicht auswertbar.')
            return

        # Ausgabegitter spannt exakt denselben Winkelbereich wie die Eingabe.
        inkrement_aus = (msg.angle_max - msg.angle_min) / (self.anzahl_aus - 1)
        idx = self._indizes(msg, inkrement_aus)

        neu = LaserScan()
        neu.header = msg.header
        neu.angle_min = msg.angle_min
        neu.angle_max = msg.angle_max
        neu.angle_increment = inkrement_aus
        neu.time_increment = (
            msg.time_increment * len(msg.ranges) / self.anzahl_aus
            if msg.time_increment else 0.0)
        neu.scan_time = msg.scan_time
        neu.range_min = msg.range_min
        neu.range_max = msg.range_max
        neu.ranges = auf_gitter(msg.ranges, idx).tolist()
        if len(msg.intensities) == len(msg.ranges):
            neu.intensities = auf_gitter(msg.intensities, idx, 0.0).tolist()

        self.pub.publish(neu)
        self.umgesetzt += 1
        self._melden()

    def _melden(self):
        intervall = float(self.get_parameter('meldeintervall_s').value)
        if intervall <= 0.0:
            return
        jetzt = self.get_clock().now()
        if (jetzt - self.letzte_meldung).nanoseconds < intervall * 1e9:
            return
        self.letzte_meldung = jetzt
        if self.groessen:
            self.get_logger().info(
                f'{self.umgesetzt}/{self.gesehen} Scans umgesetzt; Eingabe '
                f'schwankte ueber {len(self.groessen)} verschiedene Groessen '
                f'({min(self.groessen)}..{max(self.groessen)}), Ausgabe fest '
                f'{self.anzahl_aus}.')


def main(args=None):
    rclpy.init(args=args)
    n = ScanVereinheitlichen()
    try:
        rclpy.spin(n)
    except KeyboardInterrupt:
        pass
    finally:
        n.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
