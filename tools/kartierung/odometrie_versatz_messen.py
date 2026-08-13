#!/usr/bin/env python3
"""Misst, ob die Odometrie je FAHRT einen festen Betrag verliert.

BEFUND, der dahintersteht (12.08.2026, acht Fahrten mit dem Lasermessgeraet):
Der Odometriefehler ist nicht streckenproportional, sondern besteht aus einem
Skalenanteil (ueber wheel_radius_m kalibrierbar) und einem FESTEN Anteil von
rund 15 mm, der bei jeder Fahrt einmal anfaellt - unabhaengig von ihrer Laenge.
Ein reiner Zeitverzug in der Drehzahlrueckmeldung erklaert das nicht: Ueber eine
Fahrt, die im Stillstand beginnt und endet, hebt der sich mathematisch exakt
auf.

MESSPRINZIP: Dieselbe Gesamtstrecke einmal am Stueck und einmal in mehreren
Etappen fahren. Der Skalenanteil ist in beiden Faellen gleich; der feste Anteil
faellt einmal beziehungsweise N-mal an. Die Differenz IST der feste Versatz,
und sie braucht kein aeusseres Messmittel - der LiDAR misst gegen dieselbe Wand,
und weil nur die Aenderung zaehlt, kuerzen sich seine systematischen Fehler
heraus.

    python3 odometrie_versatz_messen.py --fahrten 1 --strecke 0.80
    python3 odometrie_versatz_messen.py --fahrten 4 --strecke 0.20

NUR VORWAERTS: Der Mastsektor 236-304 Grad ist maskiert, nach hinten hat der
Roboter mit diesem Sensor keinerlei Wahrnehmung. Rueckwaertsfahrten waeren
blind und sind hier nicht vorgesehen.

Der Wandabstand wird ueber mehrere Scans gemittelt, nicht aus einem einzelnen
genommen - ein Einzelscan streute in frueheren Messungen um bis zu 24 mm.

ACHTUNG: Der Roboter faehrt. Not-Aus bereithalten, Strecke frei halten.
"""
import argparse
import math
import statistics
import sys
import time

import rclpy
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from rclpy.node import Node
from rclpy.qos import QoSProfile, QoSReliabilityPolicy
from sensor_msgs.msg import LaserScan

# Der LiDAR-Nullpunkt zeigt nach rechts, vorwaerts liegt bei 90 Grad.
VORWAERTS_GRAD = 90.0
SEKTOR_GRAD = 10.0


class Versatzmessung(Node):

    def __init__(self, topic, cmd_topic='/cmd_vel'):
        super().__init__('odometrie_versatz_messen')
        # ACHTUNG: /cmd_vel geht DIREKT an base_hardware und umgeht den
        # collision_monitor. Der haengt als cmd_vel_smoothed -> cmd_vel
        # dazwischen. Fuer jede Fahrt mit Nahbereichsschutz muss hier
        # /cmd_vel_smoothed stehen.
        self.pub = self.create_publisher(Twist, cmd_topic, 10)
        self.create_subscription(Odometry, '/odom', self._auf_odom, 20)
        self.create_subscription(
            LaserScan, topic, self._auf_scan,
            QoSProfile(depth=5, reliability=QoSReliabilityPolicy.BEST_EFFORT))
        self.pos = None
        self.yaw = None
        self.scan = None

    def _auf_odom(self, m):
        q = m.pose.pose.orientation
        self.pos = (m.pose.pose.position.x, m.pose.pose.position.y)
        self.yaw = math.atan2(2 * (q.w * q.z + q.x * q.y),
                              1 - 2 * (q.y * q.y + q.z * q.z))

    def _auf_scan(self, m):
        self.scan = m

    def _wand_einmal(self):
        m = self.scan
        if m is None:
            return None
        werte = []
        for i, r in enumerate(m.ranges):
            if not (m.range_min <= r <= m.range_max):
                continue
            g = math.degrees(m.angle_min + i * m.angle_increment) % 360.0
            if abs((g - VORWAERTS_GRAD + 180.0) % 360.0 - 180.0) <= SEKTOR_GRAD / 2:
                werte.append(r)
        return statistics.median(werte) if werte else None

    def wandabstand(self, anzahl=15):
        """Median ueber mehrere Scans - ein Einzelscan ist zu unruhig."""
        proben = []
        ende = time.monotonic() + 8.0
        while len(proben) < anzahl and time.monotonic() < ende and rclpy.ok():
            self.scan = None
            while self.scan is None and time.monotonic() < ende and rclpy.ok():
                rclpy.spin_once(self, timeout_sec=0.1)
            d = self._wand_einmal()
            if d is not None:
                proben.append(d)
        if len(proben) < 3:
            return None, None
        return statistics.median(proben), statistics.pstdev(proben)

    def halt(self, sekunden):
        ende = time.monotonic() + sekunden
        while time.monotonic() < ende and rclpy.ok():
            self.pub.publish(Twist())
            rclpy.spin_once(self, timeout_sec=0.05)

    def fahre(self, strecke, v):
        """Eine Fahrt; gibt die von der Odometrie gemeldete Strecke zurueck."""
        start = self.pos
        t = Twist()
        t.linear.x = v
        frist = time.monotonic() + strecke / v * 3.0 + 20.0
        while rclpy.ok() and time.monotonic() < frist:
            if math.dist(self.pos, start) >= strecke:
                break
            self.pub.publish(t)
            rclpy.spin_once(self, timeout_sec=0.02)
        self.halt(2.0)
        # Nachlauf: die Bremsphase gehoert mit in die Odometrie, sonst fehlt
        # der Odometrie ein Weg, den der LiDAR sehr wohl sieht.
        ende = time.monotonic() + 3.0
        while time.monotonic() < ende and rclpy.ok():
            rclpy.spin_once(self, timeout_sec=0.05)
        return math.dist(self.pos, start)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--fahrten', type=int, default=1)
    p.add_argument('--strecke', type=float, default=0.80,
                   help='Strecke JE Fahrt in Metern')
    p.add_argument('--v', type=float, default=0.10, help='m/s')
    p.add_argument('--topic', default='/scan_normiert')
    p.add_argument('--cmd-topic', default='/cmd_vel',
                   help='/cmd_vel_smoothed faehrt durch den collision_monitor; /cmd_vel umgeht ihn')
    args = p.parse_args()

    if args.v <= 0 or args.strecke <= 0 or args.fahrten < 1:
        print('Unzulaessige Argumente.')
        return 2

    rclpy.init()
    n = Versatzmessung(args.topic, args.cmd_topic)
    t0 = time.monotonic()
    while (n.pos is None or n.scan is None) and time.monotonic() - t0 < 25 \
            and rclpy.ok():
        rclpy.spin_once(n, timeout_sec=0.1)
    if n.pos is None:
        print('KEINE Odometrie - laeuft base_hardware scharf?')
        return 1
    if n.scan is None:
        print(f'KEIN {args.topic} - laeuft der LiDAR?')
        return 1

    gesamt_soll = args.fahrten * args.strecke
    print(f'{args.fahrten} Fahrt(en) zu je {args.strecke:.2f} m '
          f'= {gesamt_soll:.2f} m gesamt, mit {args.v:.2f} m/s')
    print(f'Fahrbefehle auf {args.cmd_topic}'
          + ('' if args.cmd_topic != '/cmd_vel' else
             '  -- ACHTUNG: umgeht den collision_monitor!'))

    vor, vor_s = n.wandabstand()
    if vor is None:
        print('Keine Wand in Fahrtrichtung erkennbar.')
        return 1
    print(f'Wandabstand vorher : {vor:.4f} m  (Streuung {vor_s*1000:.1f} mm)')

    start_yaw = n.yaw
    gemeldet = 0.0
    for i in range(args.fahrten):
        d = n.fahre(args.strecke, args.v)
        gemeldet += d
        print(f'  Fahrt {i+1}/{args.fahrten}: Odometrie {d:.4f} m', flush=True)
        n.halt(1.0)

    nach, nach_s = n.wandabstand()
    print(f'Wandabstand nachher: {nach:.4f} m  (Streuung {nach_s*1000:.1f} mm)')

    echt = vor - nach
    dyaw = math.degrees((n.yaw - start_yaw + math.pi) % (2 * math.pi) - math.pi)

    print()
    print('=' * 62)
    print(f'Odometrie gesamt : {gemeldet:.4f} m')
    print(f'LiDAR gesamt     : {echt:.4f} m')
    print(f'Abweichung       : {(echt-gemeldet)*1000:+.1f} mm')
    print(f'  je Fahrt       : {(echt-gemeldet)/args.fahrten*1000:+.1f} mm')
    print(f'Kursabweichung   : {dyaw:+.2f} Grad')
    print('=' * 62)
    print('Aussagekraeftig wird das erst im Vergleich mit einem Lauf gleicher')
    print('Gesamtstrecke bei anderer Fahrtenzahl.')

    n.halt(1.0)
    n.destroy_node()
    rclpy.shutdown()
    return 0


if __name__ == '__main__':
    sys.exit(main())
