#!/usr/bin/env python3
"""Prueft, ob die Radodometrie Drehungen richtig misst.

WARUM: Die LiDAR-Karten zeigen bei laengeren Fahrten Ueberlagerungen - dieselbe
Wand landet an zwei bis drei Stellen. Das Muster passt zu einem Winkelfehler
der Radodometrie: Was aus den Raddrehzahlen als Drehung errechnet wird, weicht
vom echten Winkel ab, und der Fehler summiert sich ueber jede Kurve. Bestimmt
wird diese Umrechnung von wheel_separation_m; eine IMU, die das abfinge, hat
der Roboter nicht.

WIE GEMESSEN WIRD: Der LiDAR ist hier das Referenzinstrument, nicht das Auge.
Vor der Drehung wird ein Referenzscan aufgenommen. Waehrend der Roboter dreht,
wird jeder neue Scan gegen diesen Referenzscan verschoben, bis er am besten
passt - diese Verschiebung IST die reale Drehung, unabhaengig von den Raedern.
Am Ende steht der Vergleich: gemeldeter Winkel (Odometrie) gegen echten Winkel
(LiDAR).

Der Roboter dreht dabei AUF DER STELLE. Er darf nicht wandern, sonst aendert
sich das Scanprofil und der Vergleich wird ungenau.

Aufruf:  python3 odometrie_drehtest.py [Umdrehungen]
Voraussetzung: slam_lidar.launch.py laeuft mit active_drive:=true
               (oder LiDAR + base_hardware scharf, SLAM ist nicht noetig).
"""
import math
import sys
import time

import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, QoSReliabilityPolicy
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from sensor_msgs.msg import LaserScan

W_DREH = 0.30          # rad/s - langsam, damit die Scans scharf bleiben
MAX_REICHWEITE = 8.0   # m - weiter entfernte Punkte sind fuer den Vergleich unnoetig


def scan_vektor(msg, laenge):
    """Scan als Distanzprofil fester Laenge, ungueltige Werte auf 0."""
    v = np.zeros(laenge, dtype=np.float32)
    n = min(len(msg.ranges), laenge)
    r = np.array(msg.ranges[:n], dtype=np.float32)
    gut = np.isfinite(r) & (r >= msg.range_min) & (r <= min(msg.range_max, MAX_REICHWEITE))
    v[:n] = np.where(gut, r, 0.0)
    return v


def beste_verschiebung(ref, akt):
    """Um wie viele Bins ist akt gegen ref verdreht? (kleinster Abstand)"""
    n = len(ref)
    gueltig = (ref > 0) & (akt > 0)
    if gueltig.sum() < n * 0.2:
        return None, None
    beste, bester_wert = 0, float('inf')
    # grob in 5er-Schritten, dann fein
    for grob in range(0, n, 5):
        g = np.roll(akt, grob)
        m = (ref > 0) & (g > 0)
        if m.sum() < n * 0.2:
            continue
        wert = float(np.mean(np.abs(ref[m] - g[m])))
        if wert < bester_wert:
            bester_wert, beste = wert, grob
    for fein in range(max(0, beste - 6), beste + 7):
        g = np.roll(akt, fein % n)
        m = (ref > 0) & (g > 0)
        if m.sum() < n * 0.2:
            continue
        wert = float(np.mean(np.abs(ref[m] - g[m])))
        if wert < bester_wert:
            bester_wert, beste = wert, fein % n
    return beste, bester_wert


class Drehtest(Node):
    def __init__(self):
        super().__init__('odometrie_drehtest')
        self.pub = self.create_publisher(Twist, '/cmd_vel', 10)
        self.create_subscription(Odometry, '/odom', self._on_odom, 20)
        self.create_subscription(
            LaserScan, '/scan', self._on_scan,
            QoSProfile(depth=5, reliability=QoSReliabilityPolicy.BEST_EFFORT))
        self.yaw = None
        self.pos = None
        self.scan = None

    def _on_odom(self, m):
        q = m.pose.pose.orientation
        self.yaw = math.atan2(2*(q.w*q.z + q.x*q.y), 1-2*(q.y*q.y + q.z*q.z))
        self.pos = (m.pose.pose.position.x, m.pose.pose.position.y)

    def _on_scan(self, m):
        self.scan = m


def main():
    umdrehungen = float(sys.argv[1]) if len(sys.argv) > 1 else 1.0
    ziel = umdrehungen * 2 * math.pi

    rclpy.init()
    n = Drehtest()
    t0 = time.monotonic()
    while (n.yaw is None or n.scan is None) and time.monotonic()-t0 < 20 and rclpy.ok():
        rclpy.spin_once(n, timeout_sec=0.1)
    if n.yaw is None:
        print('KEINE Odometrie - laeuft base_hardware scharf?'); rclpy.shutdown(); return 1
    if n.scan is None:
        print('KEIN /scan - laeuft der LiDAR?'); rclpy.shutdown(); return 1

    laenge = len(n.scan.ranges)
    grad_je_bin = 360.0 / laenge
    ref = scan_vektor(n.scan, laenge)
    start_pos = n.pos
    print(f'Referenzscan aufgenommen ({laenge} Strahlen, {grad_je_bin:.3f} Grad je Bin)')
    print(f'Drehe {umdrehungen:.0f}x360 Grad mit {W_DREH} rad/s ...\n', flush=True)

    t = Twist(); t.angular.z = W_DREH
    letzte = n.yaw
    gedreht = 0.0
    frist = time.monotonic() + ziel / W_DREH * 3.0 + 30
    while rclpy.ok() and gedreht < ziel and time.monotonic() < frist:
        n.pub.publish(t)
        rclpy.spin_once(n, timeout_sec=0.02)
        d = n.yaw - letzte
        while d > math.pi:
            d -= 2*math.pi
        while d < -math.pi:
            d += 2*math.pi
        if abs(d) > 1e-5:
            gedreht += abs(d)
            letzte = n.yaw

    halt = Twist()
    ende = time.monotonic() + 2.0
    while time.monotonic() < ende and rclpy.ok():
        n.pub.publish(halt)
        rclpy.spin_once(n, timeout_sec=0.05)
    # ausschwingen lassen und frischen Scan holen
    ende = time.monotonic() + 3.0
    while time.monotonic() < ende and rclpy.ok():
        rclpy.spin_once(n, timeout_sec=0.05)

    akt = scan_vektor(n.scan, laenge)
    bins, guete = beste_verschiebung(ref, akt)
    versatz = math.dist(n.pos, start_pos) if (n.pos and start_pos) else float('nan')

    print('=' * 62)
    print(f'Odometrie meldet   : {math.degrees(gedreht):8.2f} Grad')
    if bins is None:
        print('LiDAR-Vergleich fehlgeschlagen - zu wenige gueltige Punkte.')
        rest = None
    else:
        # Verschiebung in Grad; die Drehrichtung ist positiv (gegen Uhrzeiger)
        rest = (bins * grad_je_bin) % 360.0
        # naeher an 0 oder an 360? Der Fehler ist der kleinere Betrag.
        fehler = rest if rest <= 180 else rest - 360.0
        echt = math.degrees(gedreht) + fehler
        print(f'LiDAR sagt wirklich: {echt:8.2f} Grad   (Restversatz {fehler:+.2f} Grad)')
        print(f'Vergleichsguete    : {guete:.3f} m mittlere Abweichung je Strahl')
        print(f'Seitlicher Versatz : {versatz*100:.1f} cm  (sollte klein sein)')
        print()
        if abs(fehler) < 1.5:
            print('ERGEBNIS: Die Odometrie stimmt im Rahmen der Messgenauigkeit.')
            print('  Die Kartenueberlagerungen haben dann eine andere Ursache.')
        else:
            faktor = echt / math.degrees(gedreht)
            alt = 0.378
            neu = alt * faktor
            print(f'ERGEBNIS: Winkelfehler {fehler:+.2f} Grad je {umdrehungen:.0f} Umdrehung(en)'
                  f' = {fehler/umdrehungen:+.2f} Grad je Umdrehung.')
            print(f'  Der Roboter dreht sich real '
                  f'{"MEHR" if fehler > 0 else "WENIGER"} als gemeldet.')
            print(f'  Korrekturvorschlag wheel_separation_m: {alt:.4f} -> {neu:.4f}')
            print(f'  (Faktor {faktor:.4f}; groessere Spurweite = weniger berechnete Drehung)')
    print('=' * 62)
    print('\nBITTE VISUELL GEGENPRUEFEN: Steht der Roboter wieder genau auf der')
    print('Markierung und in der Ausgangsrichtung? Eine sichtbare Abweichung')
    print('bestaetigt das Messergebnis.')

    n.destroy_node()
    rclpy.shutdown()
    return 0


if __name__ == '__main__':
    sys.exit(main())
