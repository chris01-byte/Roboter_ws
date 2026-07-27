#!/usr/bin/env python3
"""Kartierfahrt fuer den Testraum - hindernisbewusst, faehrt sich nicht fest.

WARUM DIESE FASSUNG:
Die erste Fassung verliess sich darauf, dass der nav2_collision_monitor bremst.
Das tut er - aber seine StopZone-Aktion nullt JEDE Bewegung, auch reine
Drehungen. Ein Roboter, der einmal in der StopZone steht, kommt aus eigener
Kraft nicht mehr heraus: er dreht dann nur noch ins Leere (real passiert
27.07.2026, 2 Minuten lang).

Deshalb jetzt drei Ebenen:
  1) VORAUSSCHAUEND: Das Skript hoert selbst auf /near_field/status und haelt
     bei NAH_STOP (0.35 m) an - klar VOR der StopZone (die beginnt bei 0.26 m
     vor dem Sensor). Der Monitor kommt so gar nicht erst zum Zug.
  2) ZEITLIMIT: Jede Fahrt und jede Drehung hat eine Frist. Passiert nichts,
     gilt das als Blockade statt als Endlosschleife.
  3) FLUCHT: Steckt er doch fest, faehrt er rueckwaerts frei - und zwar hoechstens
     so weit, wie er gerade vorwaerts gekommen ist. Dort war er eben noch, das
     ist der sicherste blinde Weg. Rueckwaerts geht nur direkt auf /cmd_vel,
     weil der Monitor im Stoppzustand auch das Rueckwaertsfahren sperren wuerde.

Zonen zum Nachrechnen (collision_monitor_params.yaml, VL53 sitzt bei x=0.29):
  StopZone  x 0.30..0.55  ->  0.01..0.26 m vor dem Sensor
  SlowZone  x 0.30..0.80  ->  0.01..0.51 m vor dem Sensor
"""
import json
import math
import sys
import time

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, QoSDurabilityPolicy, QoSReliabilityPolicy
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry, OccupancyGrid
from std_msgs.msg import String
from robot_interfaces.msg import NearFieldStatus

V_FAHRT = 0.08       # m/s   vorwaerts
V_FLUCHT = 0.05      # m/s   rueckwaerts beim Befreien
W_DREH = 0.25        # rad/s langsam, sonst bricht die visuelle Wiedererkennung
LEG_MAX = 1.00       # m     laengste Gerade
NAH_STOP = 0.35      # m     selbst anhalten (StopZone beginnt bei 0.26)
NAH_KRITISCH = 0.28  # m     bereits in/an der StopZone -> Flucht noetig
FLUCHT_MAX = 0.30    # m     hoechstens so weit rueckwaerts
BLOCK_V = 0.015      # m/s   darunter gilt "steht"
BLOCK_T = 2.5        # s     so lange stehen = blockiert
PAUSE = 1.2          # s     Verarbeitungspause


class Kartierfahrt(Node):
    def __init__(self, budget_s: float):
        super().__init__('kartierfahrt')
        self.budget_s = budget_s
        # Normalbetrieb laeuft durch den collision_monitor ...
        self.pub = self.create_publisher(Twist, '/cmd_vel_smoothed', 10)
        # ... nur das Fluchtmanoever geht direkt an die Basis.
        self.pub_direkt = self.create_publisher(Twist, '/cmd_vel', 10)

        self.create_subscription(Odometry, '/odom', self._on_odom, 20)
        self.create_subscription(String, '/base_hardware/state_json', self._on_state, 10)
        self.create_subscription(NearFieldStatus, '/near_field/status', self._on_nf, 10)
        # RTAB-Map publiziert /map mit TRANSIENT_LOCAL - mit Standard-QoS
        # bekaeme man NICHTS zu sehen.
        self.create_subscription(
            OccupancyGrid, '/map', self._on_map,
            QoSProfile(depth=1, durability=QoSDurabilityPolicy.TRANSIENT_LOCAL,
                       reliability=QoSReliabilityPolicy.RELIABLE))

        self.x = self.y = self.yaw = 0.0
        self.meas_v = 0.0
        self.have_odom = False
        self.d_left = self.d_right = self.d_middle = 9.9
        self.nf_stamp = 0.0
        self.map_known = self.map_free = self.map_occ = 0
        self.map_w = self.map_h = 0
        self.t0 = time.monotonic()
        self.fluchten = 0

    # ---------------- Rueckmeldungen ----------------
    def _on_odom(self, msg):
        p, q = msg.pose.pose.position, msg.pose.pose.orientation
        self.x, self.y = p.x, p.y
        self.yaw = math.atan2(2.0 * (q.w * q.z + q.x * q.y),
                              1.0 - 2.0 * (q.y * q.y + q.z * q.z))
        self.meas_v = msg.twist.twist.linear.x
        self.have_odom = True

    def _on_state(self, msg):
        try:
            d = json.loads(msg.data)
            if d.get('meas_v_mps') is not None:
                self.meas_v = float(d['meas_v_mps'])
        except Exception:
            pass

    def _on_nf(self, msg):
        # 0.0 heisst "nichts gesehen" - das ist FREI, nicht "direkt davor".
        def gueltig(v):
            return v if v and v > 0.01 else 9.9
        self.d_left = gueltig(msg.min_dist_left)
        self.d_right = gueltig(msg.min_dist_right)
        self.d_middle = gueltig(msg.min_dist_middle)
        self.nf_stamp = time.monotonic()

    def _on_map(self, msg):
        self.map_w, self.map_h = msg.info.width, msg.info.height
        self.map_free = sum(1 for c in msg.data if 0 <= c < 50)
        self.map_occ = sum(1 for c in msg.data if c >= 50)
        self.map_known = self.map_free + self.map_occ

    # ---------------- Lagebeurteilung ----------------
    def naehe(self):
        """Kleinster Abstand nach vorn [m]. Veraltete Daten = vorsichtshalber nah."""
        if time.monotonic() - self.nf_stamp > 3.0:
            return 0.0 if self.nf_stamp > 0 else 9.9
        return min(self.d_left, self.d_right, self.d_middle)

    def freiere_seite(self):
        """+1 = nach links drehen ist freier, -1 = nach rechts."""
        return 1.0 if self.d_left >= self.d_right else -1.0

    # ---------------- Bewegung ----------------
    def stop(self, dauer=PAUSE):
        t = Twist()
        ende = time.monotonic() + dauer
        while time.monotonic() < ende and rclpy.ok():
            self.pub.publish(t)
            rclpy.spin_once(self, timeout_sec=0.05)

    def _budget_ok(self):
        return (time.monotonic() - self.t0) < self.budget_s

    def fahre(self, strecke):
        """Vorwaerts. Rueckgabe: ('ziel'|'nah'|'blockiert'|'zeit', gefahrene Strecke)."""
        x0, y0 = self.x, self.y
        t = Twist()
        t.linear.x = V_FAHRT
        steht_seit = None
        frist = time.monotonic() + strecke / V_FAHRT * 3.0 + 6.0
        while rclpy.ok() and self._budget_ok():
            d = math.hypot(self.x - x0, self.y - y0)
            if self.naehe() < NAH_STOP:
                self.stop()
                return 'nah', d
            if d >= strecke:
                self.stop()
                return 'ziel', d
            if time.monotonic() > frist:
                self.stop()
                return 'zeit', d
            if abs(self.meas_v) < BLOCK_V:
                steht_seit = steht_seit or time.monotonic()
                if time.monotonic() - steht_seit > BLOCK_T:
                    self.stop()
                    return 'blockiert', d
            else:
                steht_seit = None
            self.pub.publish(t)
            rclpy.spin_once(self, timeout_sec=0.05)
        self.stop()
        return 'zeit', math.hypot(self.x - x0, self.y - y0)

    def drehe(self, winkel):
        """Drehen mit Frist. True = geschafft, False = kam nicht voran."""
        rest = abs(winkel)
        t = Twist()
        t.angular.z = math.copysign(W_DREH, winkel)
        letzte = self.yaw
        # Grosszuegig: dreifache Solldauer plus Anlauf.
        frist = time.monotonic() + rest / W_DREH * 3.0 + 5.0
        ohne_fortschritt_seit = time.monotonic()
        while rclpy.ok() and self._budget_ok() and rest > 0.05:
            if time.monotonic() > frist:
                self.stop()
                return False
            self.pub.publish(t)
            rclpy.spin_once(self, timeout_sec=0.05)
            d = self.yaw - letzte
            while d > math.pi:
                d -= 2 * math.pi
            while d < -math.pi:
                d += 2 * math.pi
            if abs(d) > 1e-4:
                rest -= abs(d)
                letzte = self.yaw
                ohne_fortschritt_seit = time.monotonic()
            elif time.monotonic() - ohne_fortschritt_seit > BLOCK_T:
                self.stop()
                return False
        self.stop()
        return rest <= 0.05

    def befreie(self, rueckweg):
        """Rueckwaerts freifahren - direkt an der Notbremse vorbei.

        Nur so weit, wie eben vorwaerts gefahren wurde (dort war der Roboter
        gerade noch), hoechstens FLUCHT_MAX.
        """
        weg = max(0.10, min(rueckweg, FLUCHT_MAX))
        self.fluchten += 1
        print(f'    FLUCHT: {weg:.2f} m rueckwaerts (vorne {self.naehe():.2f} m)', flush=True)
        x0, y0 = self.x, self.y
        t = Twist()
        t.linear.x = -V_FLUCHT
        frist = time.monotonic() + weg / V_FLUCHT * 3.0 + 5.0
        while rclpy.ok() and time.monotonic() < frist:
            if math.hypot(self.x - x0, self.y - y0) >= weg:
                break
            self.pub_direkt.publish(t)
            rclpy.spin_once(self, timeout_sec=0.05)
        # Anhalten auf BEIDEN Wegen, damit nichts nachlaeuft.
        halt = Twist()
        ende = time.monotonic() + 1.0
        while time.monotonic() < ende and rclpy.ok():
            self.pub_direkt.publish(halt)
            self.pub.publish(halt)
            rclpy.spin_once(self, timeout_sec=0.05)
        gefahren = math.hypot(self.x - x0, self.y - y0)
        print(f'    FLUCHT beendet: {gefahren:.2f} m zurueck, vorne jetzt '
              f'{self.naehe():.2f} m', flush=True)
        return gefahren > 0.03

    def rundumblick(self):
        """360 Grad in vier Vierteln mit Pausen - gibt RTAB-Map Zeit."""
        for i in range(4):
            if not (rclpy.ok() and self._budget_ok()):
                return False
            if not self.drehe(math.pi / 2):
                print('    Rundumblick: Drehung blockiert', flush=True)
                return False
            self.stop(1.5)
            print(f'    Rundumblick {(i+1)*90:3d} Grad | vorne {self.naehe():4.2f} m | '
                  f'Karte {self.map_known:6d} bekannt ({self.map_free} frei / '
                  f'{self.map_occ} belegt) {self.map_w}x{self.map_h}', flush=True)
        return True


def main():
    budget = float(sys.argv[1]) if len(sys.argv) > 1 else 900.0
    rclpy.init()
    n = Kartierfahrt(budget)

    print('Warte auf Odometrie und Nahbereichssensorik ...', flush=True)
    for _ in range(300):
        rclpy.spin_once(n, timeout_sec=0.05)
        if n.have_odom and n.nf_stamp > 0:
            break
    if not n.have_odom:
        print('KEINE Odometrie - Abbruch, es wird nicht gefahren.', flush=True)
        rclpy.shutdown()
        return 1
    if n.nf_stamp == 0:
        print('KEINE VL53-Daten - Abbruch, blind wird nicht gefahren.', flush=True)
        rclpy.shutdown()
        return 1

    print(f'Start. Budget {budget:.0f} s | vorne frei bis {n.naehe():.2f} m', flush=True)
    letzte_strecke = 0.0
    try:
        print('  [1] Rundumblick am Startpunkt', flush=True)
        if not n.rundumblick():
            n.befreie(0.20)

        zyklus = 0
        haenger = 0
        while rclpy.ok() and n._budget_ok():
            zyklus += 1
            rest = budget - (time.monotonic() - n.t0)
            print(f'  [{zyklus+1}] noch {rest:.0f} s | vorne {n.naehe():4.2f} m', flush=True)

            # Steht er schon zu dicht dran, erst freifahren.
            if n.naehe() < NAH_KRITISCH:
                n.befreie(max(letzte_strecke, 0.20))

            grund, gefahren = n.fahre(LEG_MAX)
            letzte_strecke = gefahren
            print(f'    gefahren {gefahren:4.2f} m -> {grund}', flush=True)

            if not n._budget_ok():
                break

            if grund == 'blockiert':
                # Der Monitor hat gebremst, obwohl die VL53 nichts Nahes melden.
                haenger += 1
                if not n.befreie(max(gefahren, 0.20)):
                    if haenger >= 3:
                        print('    Kommt nicht frei - Fahrt wird beendet.', flush=True)
                        break
            else:
                haenger = 0

            # Zur freieren Seite wegdrehen, Betrag wechselnd damit er den Raum
            # ausschreitet statt im Kreis zu laufen.
            betrag = [1.05, 1.57, 2.10, 1.05, 2.62, 1.57][zyklus % 6]
            if not n.drehe(n.freiere_seite() * betrag):
                print('    Drehung blockiert', flush=True)
                if not n.befreie(max(gefahren, 0.20)):
                    haenger += 1
                    if haenger >= 3:
                        print('    Kommt nicht frei - Fahrt wird beendet.', flush=True)
                        break

            if zyklus % 3 == 0:
                print('    Zwischen-Rundumblick', flush=True)
                n.rundumblick()
    except KeyboardInterrupt:
        print('\nAbbruch durch Signal.', flush=True)
    except Exception as exc:
        import traceback
        print(f'\nFEHLER: {type(exc).__name__}: {exc}', flush=True)
        traceback.print_exc()
    finally:
        try:
            n.stop(1.5)
        except Exception:
            pass
        print(f'ENDE nach {time.monotonic()-n.t0:.0f} s | Pose x={n.x:.2f} y={n.y:.2f} '
              f'| {n.fluchten} Fluchtmanoever | Karte {n.map_known} bekannt '
              f'({n.map_free} frei / {n.map_occ} belegt) {n.map_w}x{n.map_h}', flush=True)
        n.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
    return 0


if __name__ == '__main__':
    sys.exit(main())
