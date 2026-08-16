#!/usr/bin/env python3
"""Prueft, ob die Radodometrie Strecken richtig misst.

Gegenstueck zum Drehtest: Der prueft wheel_separation_m (Winkel), dieser prueft
wheel_radius_m (Strecke). Beide Fehler wirken unabhaengig voneinander.

Der Roboter faehrt geradeaus, bis die Odometrie die Sollstrecke meldet, und
haelt an. Zwei unabhaengige Gegenmessungen:
  1. Der LiDAR misst selbst, wie weit sich eine Wand vor dem Roboter genaehert
     hat - das braucht eine ebene Flaeche in Fahrtrichtung.
  2. Der Mensch misst mit dem Lasermessgeraet nach.

Weicht die Strecke ab, wird wheel_radius_m korrigiert:
    neu = alt * (echte Strecke / gemeldete Strecke)

Aufruf:  python3 odometrie_streckentest.py [Meter] [rueckwaerts]
         z.B.  python3 odometrie_streckentest.py 1.0
               python3 odometrie_streckentest.py 1.0 rueckwaerts
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

V_FAHRT = 0.10        # m/s, langsam und gut wiederholbar
SEKTOR = 10.0         # Grad um die Fahrtrichtung fuer die Wandmessung


def wandabstand(msg, richtung_grad):
    """Median-Abstand in einem schmalen Sektor um eine Richtung [Grad]."""
    werte = []
    for i, r in enumerate(msg.ranges):
        if not (msg.range_min <= r <= msg.range_max):
            continue
        g = math.degrees(msg.angle_min + i * msg.angle_increment) % 360.0
        d = abs((g - richtung_grad + 180.0) % 360.0 - 180.0)
        if d <= SEKTOR / 2:
            werte.append(r)
    if len(werte) < 5:
        return None
    return float(np.median(werte))


def hole_radius(node, vorgabe=0.0612):
    """Aktuellen wheel_radius_m vom laufenden base_hardware erfragen."""
    from rcl_interfaces.srv import GetParameters
    cli = node.create_client(GetParameters, '/base_hardware/get_parameters')
    if not cli.wait_for_service(timeout_sec=3.0):
        return vorgabe
    req = GetParameters.Request(names=['wheel_radius_m'])
    fut = cli.call_async(req)
    rclpy.spin_until_future_complete(node, fut, timeout_sec=3.0)
    try:
        return fut.result().values[0].double_value or vorgabe
    except Exception:
        return vorgabe


class Streckentest(Node):
    def __init__(self):
        super().__init__('odometrie_streckentest')
        self.pub = self.create_publisher(Twist, '/cmd_vel', 10)
        self.create_subscription(Odometry, '/odom', self._on_odom, 20)
        self.create_subscription(
            LaserScan, '/scan', self._on_scan,
            QoSProfile(depth=5, reliability=QoSReliabilityPolicy.BEST_EFFORT))
        self.pos = None
        self.yaw = None
        self.scan = None

    def _on_odom(self, m):
        p = m.pose.pose.position
        q = m.pose.pose.orientation
        self.pos = (p.x, p.y)
        self.yaw = math.atan2(2*(q.w*q.z + q.x*q.y), 1-2*(q.y*q.y + q.z*q.z))

    def _on_scan(self, m):
        self.scan = m


def main():
    soll = float(sys.argv[1]) if len(sys.argv) > 1 else 1.0
    rueck = len(sys.argv) > 2 and sys.argv[2].startswith('r')
    richtung = -1.0 if rueck else 1.0

    rclpy.init()
    n = Streckentest()
    t0 = time.monotonic()
    while (n.pos is None or n.scan is None) and time.monotonic()-t0 < 20 and rclpy.ok():
        rclpy.spin_once(n, timeout_sec=0.1)
    if n.pos is None:
        print('KEINE Odometrie - laeuft base_hardware scharf?'); rclpy.shutdown(); return 1

    # Der ROS-konforme CCW-Scan ist gegenueber den nativen CW-Bins gedreht:
    # physisch vorwaerts liegt in laser_frame bei 270 Grad, rueckwaerts bei 90.
    mess_richtung = 270.0 if not rueck else 90.0
    vor_wand = wandabstand(n.scan, mess_richtung) if n.scan else None
    start = n.pos
    start_yaw = n.yaw

    print(f'{"Rueckwaerts" if rueck else "Vorwaerts"} {soll:.2f} m mit {V_FAHRT} m/s')
    if vor_wand:
        print(f'Wandabstand vorher (LiDAR): {vor_wand:.3f} m')
    else:
        print('Keine Flaeche in Fahrtrichtung erkannt - nur Odometrie und Massband.')
    print('Startpunkt bitte markiert haben.\n', flush=True)

    t = Twist(); t.linear.x = richtung * V_FAHRT
    frist = time.monotonic() + soll / V_FAHRT * 3.0 + 20
    while rclpy.ok() and time.monotonic() < frist:
        gefahren = math.dist(n.pos, start)
        if gefahren >= soll:
            break
        n.pub.publish(t)
        rclpy.spin_once(n, timeout_sec=0.02)

    halt = Twist()
    ende = time.monotonic() + 2.0
    while time.monotonic() < ende and rclpy.ok():
        n.pub.publish(halt)
        rclpy.spin_once(n, timeout_sec=0.05)
    ende = time.monotonic() + 2.0
    while time.monotonic() < ende and rclpy.ok():
        rclpy.spin_once(n, timeout_sec=0.05)

    gemeldet = math.dist(n.pos, start)
    nach_wand = wandabstand(n.scan, mess_richtung) if n.scan else None
    dyaw = math.degrees((n.yaw - start_yaw + math.pi) % (2*math.pi) - math.pi)

    print('=' * 62)
    print(f'Odometrie meldet    : {gemeldet:.3f} m')
    if vor_wand and nach_wand:
        echt = abs(vor_wand - nach_wand)
        print(f'LiDAR misst         : {echt:.3f} m   '
              f'(Wand {vor_wand:.3f} -> {nach_wand:.3f} m)')
        fehler = echt - gemeldet
        print(f'Abweichung          : {fehler*1000:+.0f} mm')
        if abs(fehler) > 0.005:
            # Den AKTUELLEN Wert aus dem laufenden Knoten holen, nicht einen
            # fest verdrahteten Altwert - sonst ist der Vorschlag nach der
            # ersten Kalibrierung falsch.
            alt = hole_radius(n)
            neu = alt * (echt / gemeldet)
            print(f'  Korrekturvorschlag wheel_radius_m: {alt:.5f} -> {neu:.5f}')
            print(f'  ACHTUNG: wheel_separation_m im selben Verhaeltnis mitziehen '
                  f'(Faktor {echt/gemeldet:.5f}), sonst stimmt die Drehung nicht mehr.')
        else:
            print('  Im Rahmen der Messgenauigkeit - keine Korrektur noetig.')
    print(f'Kursabweichung      : {dyaw:+.2f} Grad  (sollte nahe 0 sein)')
    print('=' * 62)
    print('\nJETZT MIT DEM LASERMESSGERAET NACHMESSEN.')
    print(f'Gemessene Strecke gegen die gemeldeten {gemeldet:.3f} m halten.')
    print('Korrektur:  wheel_radius_m_neu = 0.0625 * (echt / gemeldet)')

    n.destroy_node()
    rclpy.shutdown()
    return 0


if __name__ == '__main__':
    sys.exit(main())
