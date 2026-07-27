#!/usr/bin/env python3
"""Lokalisierungstest mit belastbarem Kriterium und echter Drehung.

Warum eine zweite Fassung:
  * Fassung 1 wertete "map->odom ist nicht die Identitaet" als Erfolg. Das ist
    zu schwach: RTAB-Map laedt beim Start die zuletzt gespeicherte Pose aus der
    Datenbank und setzt map->odom danach - ganz ohne Wiedererkennung. Genau
    dieser Trugschluss ist am 27.07.2026 zweimal passiert.
    Hartes Kriterium ist stattdessen /localization_pose: darauf publiziert
    RTAB-Map NUR nach einer bestaetigten Lokalisierung.
  * "ros2 topic pub" kam bei base_hardware nicht an (durchgehend TIMEOUT-STOP).
    Gedreht wird deshalb aus dem Skript heraus, wie in der Kartierfahrt.

Der Roboter dreht sich langsam einmal im Kreis, damit RTAB-Map ueberhaupt
Bilder verarbeitet (RGBD/AngularUpdate) und mehrere Ansichten sieht.
"""
import math
import sys
import time

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist, PoseWithCovarianceStamped
from nav_msgs.msg import Odometry
from tf2_ros import Buffer, TransformListener

W_DREH = 0.22


class Test(Node):
    def __init__(self):
        super().__init__('lokalisierung_test2')
        self.pub = self.create_publisher(Twist, '/cmd_vel_smoothed', 10)
        self.create_subscription(Odometry, '/odom', self._on_odom, 20)
        self.create_subscription(PoseWithCovarianceStamped, '/localization_pose',
                                 self._on_lok, 10)
        self.puffer = Buffer()
        TransformListener(self.puffer, self)
        self.yaw = 0.0
        self.have_odom = False
        self.lok_zahl = 0
        self.lok_letzte = None

    def _on_odom(self, msg):
        q = msg.pose.pose.orientation
        self.yaw = math.atan2(2.0 * (q.w * q.z + q.x * q.y),
                              1.0 - 2.0 * (q.y * q.y + q.z * q.z))
        self.have_odom = True

    def _on_lok(self, msg):
        self.lok_zahl += 1
        p = msg.pose.pose.position
        self.lok_letzte = (p.x, p.y)
        print(f'  >>> LOKALISIERT ({self.lok_zahl}.): Pose in der Karte '
              f'x={p.x:+.2f} y={p.y:+.2f}', flush=True)

    def korrektur(self):
        try:
            tf = self.puffer.lookup_transform('map', 'odom', rclpy.time.Time())
            t = tf.transform.translation
            return math.hypot(t.x, t.y)
        except Exception:
            return None


def main():
    rclpy.init()
    n = Test()
    for _ in range(200):
        rclpy.spin_once(n, timeout_sec=0.05)
        if n.have_odom:
            break
    if not n.have_odom:
        print('KEINE Odometrie - Abbruch.', flush=True)
        rclpy.shutdown()
        return 1

    # Der TF-Puffer braucht ein paar Sekunden, bis map->odom drinsteht.
    k0 = None
    frist_tf = time.monotonic() + 15.0
    while k0 is None and time.monotonic() < frist_tf and rclpy.ok():
        rclpy.spin_once(n, timeout_sec=0.1)
        k0 = n.korrektur()
    if k0 is None:
        print('KEINE TF map->odom - laeuft rtabmap? Abbruch.', flush=True)
        rclpy.shutdown()
        return 1
    print(f'map->odom VOR der Drehung: {k0:.3f} m '
          f'(beim Start aus der Datenbank geladen, noch KEIN Beweis)', flush=True)
    print('Drehe langsam einmal im Kreis ...', flush=True)

    t = Twist()
    t.angular.z = W_DREH
    rest = 2 * math.pi
    letzte = n.yaw
    gedreht = 0.0
    frist = time.monotonic() + 120.0
    while rclpy.ok() and rest > 0.05 and time.monotonic() < frist:
        n.pub.publish(t)
        rclpy.spin_once(n, timeout_sec=0.05)
        d = n.yaw - letzte
        while d > math.pi:
            d -= 2 * math.pi
        while d < -math.pi:
            d += 2 * math.pi
        if abs(d) > 1e-4:
            rest -= abs(d)
            gedreht += abs(d)
            letzte = n.yaw

    halt = Twist()
    ende = time.monotonic() + 2.0
    while time.monotonic() < ende and rclpy.ok():
        n.pub.publish(halt)
        rclpy.spin_once(n, timeout_sec=0.05)

    # Noch etwas nachlaufen lassen, RTAB-Map arbeitet mit ~1 Hz.
    ende = time.monotonic() + 15.0
    while time.monotonic() < ende and rclpy.ok():
        rclpy.spin_once(n, timeout_sec=0.1)

    k1 = n.korrektur()
    print()
    print(f'tatsaechlich gedreht      : {math.degrees(gedreht):.0f} Grad')
    print(f'Lokalisierungen gemeldet  : {n.lok_zahl}')
    print(f'map->odom vorher / nachher: {k0:.3f} m / '
          f'{"—" if k1 is None else f"{k1:.3f} m"}')
    print()
    if gedreht < math.radians(45):
        print('ERGEBNIS UNGUELTIG: Der Roboter hat sich kaum gedreht.')
        print('  Ohne Bewegung verarbeitet RTAB-Map keine Bilder - der Test')
        print('  sagt so gar nichts aus.')
    elif n.lok_zahl > 0:
        print(f'ERGEBNIS: BESTANDEN - {n.lok_zahl} bestaetigte Lokalisierungen.')
        print('  Der Roboter findet sich in der Karte wieder.')
    else:
        print('ERGEBNIS: NICHT BESTANDEN - keine einzige bestaetigte Lokalisierung,')
        print('  obwohl sich der Roboter gedreht hat.')
        print('  Der Versatz in map->odom stammt allein aus der geladenen Startpose.')

    n.destroy_node()
    rclpy.shutdown()
    return 0


if __name__ == '__main__':
    sys.exit(main())
