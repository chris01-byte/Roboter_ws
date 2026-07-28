#!/usr/bin/env python3
"""Ehrlicher Lokalisierungstest: Findet der Roboter seine Position OHNE Vorwissen?

Voraussetzung: Der Stack laeuft mit
    ./start_lokalisierung.sh <log> true      (= start_at_origin:=true)
Dann beginnt RTAB-Map am Kartenursprung und kennt seine Position NICHT.

Der Test misst drei Dinge:
  1. Startversatz map->odom - muss nahe null sein. Ist er es nicht, hat RTAB-Map
     doch Vorwissen geladen und der Test taugt nichts.
  2. Meldungen auf /localization_pose - nur die zaehlen als Lokalisierung.
  3. Endversatz map->odom - der SPRUNG vom Ursprung auf die tatsaechliche
     Position. Das ist der eigentliche Beweis.

Der Roboter dreht sich dabei langsam, sonst verarbeitet RTAB-Map wegen
RGBD/AngularUpdate ueberhaupt keine Bilder.

Aufruf:  python3 lokalisierung_kidnapped.py [Name des Durchlaufs]
Das Ergebnis wird an ~/.local/share/amadeus/lokalisierungstests.log angehaengt,
damit sich mehrere Durchlaeufe von derselben Bodenmarkierung vergleichen lassen:
Erst wenn zwei Durchlaeufe dieselbe Pose melden, ist die Lokalisierung
reproduzierbar - ein einzelner Treffer koennte Zufall sein.
"""
import math
import sys
import time
from datetime import datetime
from pathlib import Path

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist, PoseWithCovarianceStamped
from nav_msgs.msg import Odometry
from tf2_ros import Buffer, TransformListener

W_DREH = 0.22
DREHUNGEN = 2          # zweimal herum, damit er reichlich Ansichten bekommt
START_GRENZE = 0.10    # m - darueber gilt "hatte doch Vorwissen"


class Test(Node):
    def __init__(self):
        super().__init__('lokalisierung_kidnapped')
        self.pub = self.create_publisher(Twist, '/cmd_vel_smoothed', 10)
        self.create_subscription(Odometry, '/odom', self._on_odom, 20)
        self.create_subscription(PoseWithCovarianceStamped, '/localization_pose',
                                 self._on_lok, 10)
        self.puffer = Buffer()
        TransformListener(self.puffer, self)
        self.yaw = 0.0
        self.have_odom = False
        self.lok_zahl = 0
        self.lok_erste = None
        self.lok_letzte = None

    def _on_odom(self, msg):
        q = msg.pose.pose.orientation
        self.yaw = math.atan2(2.0 * (q.w * q.z + q.x * q.y),
                              1.0 - 2.0 * (q.y * q.y + q.z * q.z))
        self.have_odom = True

    def _on_lok(self, msg):
        p = msg.pose.pose.position
        q = msg.pose.pose.orientation
        gier = math.degrees(math.atan2(2.0 * (q.w * q.z + q.x * q.y),
                                       1.0 - 2.0 * (q.y * q.y + q.z * q.z)))
        self.lok_zahl += 1
        eintrag = (p.x, p.y, gier)
        if self.lok_erste is None:
            self.lok_erste = eintrag
            print(f'  >>> ERSTE LOKALISIERUNG nach {self.lok_zahl} Meldung(en): '
                  f'x={p.x:+.2f} y={p.y:+.2f} gier={gier:+.0f} Grad', flush=True)
        self.lok_letzte = eintrag

    def versatz(self):
        try:
            tf = self.puffer.lookup_transform('map', 'odom', rclpy.time.Time())
            t = tf.transform.translation
            return math.hypot(t.x, t.y)
        except Exception:
            return None

    def pose_in_karte(self):
        try:
            tf = self.puffer.lookup_transform('map', 'base_link', rclpy.time.Time())
            t = tf.transform.translation
            q = tf.transform.rotation
            gier = math.degrees(math.atan2(2.0 * (q.w * q.z + q.x * q.y),
                                           1.0 - 2.0 * (q.y * q.y + q.z * q.z)))
            return t.x, t.y, gier
        except Exception:
            return None


def main():
    name = sys.argv[1] if len(sys.argv) > 1 else 'Durchlauf'
    rclpy.init()
    n = Test()

    for _ in range(200):
        rclpy.spin_once(n, timeout_sec=0.05)
        if n.have_odom:
            break
    if not n.have_odom:
        print('KEINE Odometrie - Abbruch, es wird nicht gefahren.', flush=True)
        rclpy.shutdown()
        return 1

    v0 = None
    frist = time.monotonic() + 20.0
    while v0 is None and time.monotonic() < frist and rclpy.ok():
        rclpy.spin_once(n, timeout_sec=0.1)
        v0 = n.versatz()
    if v0 is None:
        print('KEINE TF map->odom - laeuft rtabmap? Abbruch.', flush=True)
        rclpy.shutdown()
        return 1

    print(f'Startversatz map->odom: {v0:.3f} m', flush=True)
    if v0 > START_GRENZE:
        print(f'  WARNUNG: groesser als {START_GRENZE} m - RTAB-Map hat offenbar doch',
              flush=True)
        print('  eine Pose geladen. Laeuft der Stack wirklich mit start_at_origin:=true?',
              flush=True)
    else:
        print('  Gut - der Roboter startet ohne Vorwissen am Kartenursprung.', flush=True)

    print(f'Drehe {DREHUNGEN}x im Kreis und warte auf Wiedererkennung ...', flush=True)
    t = Twist()
    t.angular.z = W_DREH
    rest = DREHUNGEN * 2 * math.pi
    letzte = n.yaw
    gedreht = 0.0
    frist = time.monotonic() + 240.0
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
    ende = time.monotonic() + 15.0
    while time.monotonic() < ende and rclpy.ok():
        rclpy.spin_once(n, timeout_sec=0.1)

    v1 = n.versatz()
    pose = n.pose_in_karte()

    print()
    print('=' * 62)
    print(f'gedreht                   : {math.degrees(gedreht):.0f} Grad')
    print(f'Startversatz map->odom    : {v0:.3f} m')
    print(f'Endversatz map->odom      : {"—" if v1 is None else f"{v1:.3f} m"}')
    print(f'Lokalisierungen gemeldet  : {n.lok_zahl}')
    if pose:
        print(f'Pose in der Karte         : x={pose[0]:+.2f} y={pose[1]:+.2f} '
              f'gier={pose[2]:+.0f} Grad')
    print('=' * 62)

    sprung = (v1 - v0) if (v1 is not None) else 0.0
    if gedreht < math.radians(90):
        urteil = 'UNGUELTIG - der Roboter hat sich kaum gedreht.'
    elif v0 > START_GRENZE:
        urteil = ('UNGUELTIG - Start nicht am Ursprung, RTAB-Map hatte Vorwissen.')
    elif n.lok_zahl == 0:
        urteil = ('NICHT BESTANDEN - keine einzige Lokalisierung. Der Roboter kann '
                  'seine Position nicht selbst bestimmen.')
    elif abs(sprung) < 0.10:
        urteil = ('ZWEIFELHAFT - es gab Lokalisierungen, aber der Versatz blieb am '
                  'Ursprung kleben. Sieht nicht nach echter Positionsbestimmung aus.')
    else:
        urteil = (f'BESTANDEN - {n.lok_zahl} Lokalisierungen, und die Position ist um '
                  f'{abs(sprung):.2f} m vom Ursprung auf die tatsaechliche Stelle '
                  f'gesprungen.')
    print(urteil)
    print()
    print('WICHTIG: Ein einzelner Durchlauf beweist noch keine Genauigkeit. Erst wenn')
    print('zwei Durchlaeufe von DERSELBEN Bodenmarkierung dieselbe Pose melden, ist')
    print('die Lokalisierung reproduzierbar.')

    # Fuer den Vergleich mehrerer Durchlaeufe festhalten
    protokoll = Path.home() / '.local/share/amadeus/lokalisierungstests.log'
    protokoll.parent.mkdir(parents=True, exist_ok=True)
    with protokoll.open('a') as f:
        p = pose if pose else (float('nan'),) * 3
        f.write(f'{datetime.now():%Y-%m-%d %H:%M:%S} | {name:22s} | '
                f'Start {v0:5.3f} m | Ende {0 if v1 is None else v1:5.3f} m | '
                f'{n.lok_zahl:4d} Lok. | Pose x={p[0]:+.2f} y={p[1]:+.2f} '
                f'gier={p[2]:+.0f} | {urteil.split(" - ")[0]}\n')
    print(f'\nProtokoll: {protokoll}')

    n.destroy_node()
    rclpy.shutdown()
    return 0


if __name__ == '__main__':
    sys.exit(main())
