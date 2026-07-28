#!/usr/bin/env python3
"""Erkundungsfahrt: sucht sich Ziele dort, wo die Karte noch Luecken hat.

WARUM DIESE FASSUNG:
`kartierfahrt.py` faehrt ein blindes Muster (1 m geradeaus, wegdrehen). Ergebnis
am 27.07.: 17,5 m gefahren, aber am Ende nur 1 m vom Start entfernt - der
Roboter drehte sich im Kreis, statt den Raum abzuschreiten. Die Karte blieb
entsprechend klein.

Hier waehlt der Roboter seine Ziele stattdessen aus der Karte selbst: an einer
GRENZE ("Frontier"), also dort, wo bekannter freier Boden an unbekanntes Gebiet
stoesst. Genau dort bringt Hinfahren neue Information. Ist keine Grenze mehr
erreichbar, ist der Raum erfasst und die Fahrt endet von selbst.

Sicherheit wie in kartierfahrt.py - der collision_monitor ist nur die Notbremse:
  * eigener Halt schon bei 0.35 m (StopZone beginnt erst bei 0.26 m)
  * Frist fuer jede Bewegung, kein Drehen ins Leere
  * Rueckwaertsflucht, hoechstens so weit wie eben vorwaerts gefahren
Zusaetzlich wird jedes Ziel vorher geprueft: Es muss ringsum Platz fuer den
Roboter haben, sonst wird es gar nicht erst angefahren.
"""
import json
import math
import sys
import time

import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, QoSDurabilityPolicy, QoSReliabilityPolicy
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry, OccupancyGrid
from std_msgs.msg import String
from tf2_ros import Buffer, TransformListener

from robot_interfaces.msg import NearFieldStatus

V_FAHRT = 0.09        # m/s
V_FLUCHT = 0.05       # m/s rueckwaerts
W_DREH = 0.25         # rad/s
NAH_STOP = 0.35       # m  selbst anhalten
NAH_KRITISCH = 0.28   # m  schon in der StopZone
FLUCHT_MAX = 0.30     # m
BLOCK_V = 0.015       # m/s
BLOCK_T = 2.5         # s
ZIEL_TOLERANZ = 0.35  # m  so nah gilt als angekommen
ZIEL_MIN = 0.70       # m  naeher gelegene Grenzen lohnen die Fahrt nicht
ZIEL_MAX = 3.50       # m  weiter weg wird die blinde Geradeausfahrt unsicher
ROBOTER_RADIUS = 0.40 # m  Platzbedarf, der um ein Ziel herum frei sein muss


class Erkundung(Node):
    def __init__(self, budget_s):
        super().__init__('erkundungsfahrt')
        self.budget_s = budget_s
        self.pub = self.create_publisher(Twist, '/cmd_vel_smoothed', 10)
        self.pub_direkt = self.create_publisher(Twist, '/cmd_vel', 10)

        self.create_subscription(Odometry, '/odom', self._on_odom, 20)
        self.create_subscription(String, '/base_hardware/state_json', self._on_state, 10)
        self.create_subscription(NearFieldStatus, '/near_field/status', self._on_nf, 10)
        # /map kommt TRANSIENT_LOCAL - mit Standard-QoS sieht man NICHTS.
        self.create_subscription(
            OccupancyGrid, '/map', self._on_map,
            QoSProfile(depth=1, durability=QoSDurabilityPolicy.TRANSIENT_LOCAL,
                       reliability=QoSReliabilityPolicy.RELIABLE))
        self.puffer = Buffer()
        TransformListener(self.puffer, self)

        self.x = self.y = self.yaw = 0.0
        self.meas_v = 0.0
        self.have_odom = False
        self.d_left = self.d_right = self.d_middle = 9.9
        self.nf_stamp = 0.0
        self.grid = None
        self.info = None
        self.t0 = time.monotonic()
        self.fluchten = 0
        self.verworfen = []          # Ziele, die sich als unerreichbar zeigten

    # -------- Rueckmeldungen --------
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
        def gueltig(v):
            # -1.0 heisst "nichts gesehen" = frei, nicht "direkt davor"
            return v if v and v > 0.01 else 9.9
        self.d_left = gueltig(msg.min_dist_left)
        self.d_right = gueltig(msg.min_dist_right)
        self.d_middle = gueltig(msg.min_dist_middle)
        self.nf_stamp = time.monotonic()

    def _on_map(self, msg):
        self.info = msg.info
        self.grid = np.array(msg.data, dtype=np.int8).reshape(
            msg.info.height, msg.info.width)

    # -------- Lage --------
    def naehe(self):
        if time.monotonic() - self.nf_stamp > 3.0:
            return 0.0 if self.nf_stamp > 0 else 9.9
        return min(self.d_left, self.d_right, self.d_middle)

    def pose_in_karte(self):
        """Roboterpose im map-Frame - die Karte steht in map-Koordinaten."""
        try:
            tf = self.puffer.lookup_transform('map', 'base_link', rclpy.time.Time())
            t, q = tf.transform.translation, tf.transform.rotation
            gier = math.atan2(2.0 * (q.w * q.z + q.x * q.y),
                              1.0 - 2.0 * (q.y * q.y + q.z * q.z))
            return t.x, t.y, gier
        except Exception:
            return None

    def kartenstand(self):
        if self.grid is None:
            return 0, 0, 0
        frei = int(((self.grid >= 0) & (self.grid < 50)).sum())
        belegt = int((self.grid >= 50).sum())
        return frei + belegt, frei, belegt

    # -------- Zielsuche --------
    def finde_ziel(self):
        """Naechstgelegene lohnende Grenze zwischen bekannt-frei und unbekannt."""
        if self.grid is None or self.info is None:
            return None
        pose = self.pose_in_karte()
        if pose is None:
            return None
        rx, ry, _ = pose

        g = self.grid
        frei = (g >= 0) & (g < 50)
        unbekannt = g < 0
        belegt = g >= 50

        # Grenze = freie Zelle mit mindestens einem unbekannten Nachbarn
        nachbar_unbekannt = np.zeros_like(unbekannt)
        nachbar_unbekannt[1:, :] |= unbekannt[:-1, :]
        nachbar_unbekannt[:-1, :] |= unbekannt[1:, :]
        nachbar_unbekannt[:, 1:] |= unbekannt[:, :-1]
        nachbar_unbekannt[:, :-1] |= unbekannt[:, 1:]
        grenze = frei & nachbar_unbekannt

        if not grenze.any():
            return None

        # Zellen mit Hindernis in Roboternaehe ausschliessen: um jedes Ziel muss
        # ein Kreis vom Roboterradius frei sein, sonst passt er dort nicht hin.
        aufl = self.info.resolution
        r = max(1, int(round(ROBOTER_RADIUS / aufl)))
        eng = np.zeros_like(belegt)
        idx = np.argwhere(belegt)
        h, w = belegt.shape
        for cy, cx in idx:
            y0, y1 = max(0, cy - r), min(h, cy + r + 1)
            x0, x1 = max(0, cx - r), min(w, cx + r + 1)
            eng[y0:y1, x0:x1] = True
        kandidaten = np.argwhere(grenze & ~eng)
        if kandidaten.size == 0:
            return None

        ox = self.info.origin.position.x
        oy = self.info.origin.position.y
        bestes = None
        for cy, cx in kandidaten:
            wx = ox + (cx + 0.5) * aufl
            wy = oy + (cy + 0.5) * aufl
            d = math.hypot(wx - rx, wy - ry)
            if d < ZIEL_MIN or d > ZIEL_MAX:
                continue
            # schon gescheiterte Ziele meiden
            if any(math.hypot(wx - vx, wy - vy) < 0.5 for vx, vy in self.verworfen):
                continue
            if bestes is None or d < bestes[2]:
                bestes = (wx, wy, d)
        return bestes

    # -------- Bewegung --------
    def _budget_ok(self):
        return (time.monotonic() - self.t0) < self.budget_s

    def stop(self, dauer=1.2):
        t = Twist()
        ende = time.monotonic() + dauer
        while time.monotonic() < ende and rclpy.ok():
            self.pub.publish(t)
            rclpy.spin_once(self, timeout_sec=0.05)

    def drehe(self, winkel):
        rest = abs(winkel)
        t = Twist()
        t.angular.z = math.copysign(W_DREH, winkel)
        letzte = self.yaw
        frist = time.monotonic() + rest / W_DREH * 3.0 + 5.0
        ohne = time.monotonic()
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
                ohne = time.monotonic()
            elif time.monotonic() - ohne > BLOCK_T:
                self.stop()
                return False
        self.stop()
        return rest <= 0.05

    def fahre(self, strecke):
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

    def befreie(self, rueckweg):
        weg = max(0.10, min(rueckweg, FLUCHT_MAX))
        self.fluchten += 1
        print(f'    FLUCHT: {weg:.2f} m rueckwaerts (vorne {self.naehe():.2f} m)',
              flush=True)
        x0, y0 = self.x, self.y
        t = Twist()
        t.linear.x = -V_FLUCHT
        frist = time.monotonic() + weg / V_FLUCHT * 3.0 + 5.0
        while rclpy.ok() and time.monotonic() < frist:
            if math.hypot(self.x - x0, self.y - y0) >= weg:
                break
            self.pub_direkt.publish(t)
            rclpy.spin_once(self, timeout_sec=0.05)
        halt = Twist()
        ende = time.monotonic() + 1.0
        while time.monotonic() < ende and rclpy.ok():
            self.pub_direkt.publish(halt)
            self.pub.publish(halt)
            rclpy.spin_once(self, timeout_sec=0.05)
        gefahren = math.hypot(self.x - x0, self.y - y0)
        print(f'    FLUCHT beendet: {gefahren:.2f} m, vorne jetzt {self.naehe():.2f} m',
              flush=True)
        return gefahren > 0.03

    def rundumblick(self, viertel=4):
        for i in range(viertel):
            if not (rclpy.ok() and self._budget_ok()):
                return False
            if not self.drehe(math.pi / 2):
                print('    Rundumblick: Drehung blockiert', flush=True)
                return False
            self.stop(1.5)
            bek, frei, belegt = self.kartenstand()
            print(f'    Blick {(i+1)*90:3d} Grad | Karte {bek:6d} bekannt '
                  f'({frei} frei / {belegt} belegt)', flush=True)
        return True

    def fahre_zu(self, zx, zy):
        """Zum Ziel ausrichten und hinfahren. Rueckgabe: 'ok'|'nah'|'blockiert'|'zeit'."""
        pose = self.pose_in_karte()
        if pose is None:
            return 'zeit'
        rx, ry, gier = pose
        soll = math.atan2(zy - ry, zx - rx)
        diff = soll - gier
        while diff > math.pi:
            diff -= 2 * math.pi
        while diff < -math.pi:
            diff += 2 * math.pi
        if abs(diff) > 0.10 and not self.drehe(diff):
            return 'blockiert'

        strecke = math.hypot(zx - rx, zy - ry)
        grund, gefahren = self.fahre(max(0.0, strecke - ZIEL_TOLERANZ))
        return {'ziel': 'ok'}.get(grund, grund), gefahren


def main():
    budget = float(sys.argv[1]) if len(sys.argv) > 1 else 900.0
    rclpy.init()
    n = Erkundung(budget)

    print('Warte auf Odometrie, Nahbereich und Karte ...', flush=True)
    for _ in range(600):
        rclpy.spin_once(n, timeout_sec=0.05)
        if n.have_odom and n.nf_stamp > 0 and n.grid is not None:
            break
    if not n.have_odom:
        print('KEINE Odometrie - Abbruch.', flush=True)
        rclpy.shutdown()
        return 1
    if n.nf_stamp == 0:
        print('KEINE VL53-Daten - Abbruch, blind wird nicht gefahren.', flush=True)
        rclpy.shutdown()
        return 1
    if n.grid is None:
        print('KEINE Karte auf /map - laeuft rtabmap? Abbruch.', flush=True)
        rclpy.shutdown()
        return 1

    bek, frei, belegt = n.kartenstand()
    print(f'Start. Budget {budget:.0f} s | vorne {n.naehe():.2f} m | '
          f'Karte {bek} bekannt ({frei} frei / {belegt} belegt)', flush=True)

    ziele_erreicht = 0
    letzte_strecke = 0.0
    try:
        print('  Rundumblick am Startpunkt', flush=True)
        n.rundumblick()

        runde = 0
        while rclpy.ok() and n._budget_ok():
            runde += 1
            rest = budget - (time.monotonic() - n.t0)

            if n.naehe() < NAH_KRITISCH:
                n.befreie(max(letzte_strecke, 0.20))

            ziel = n.finde_ziel()
            if ziel is None:
                print(f'  [{runde}] keine erreichbare Kartenluecke mehr - '
                      f'Raum erfasst.', flush=True)
                break
            zx, zy, d = ziel
            print(f'  [{runde}] noch {rest:.0f} s | Ziel x={zx:+.2f} y={zy:+.2f} '
                  f'({d:.2f} m entfernt)', flush=True)

            grund, gefahren = n.fahre_zu(zx, zy)
            letzte_strecke = gefahren
            print(f'    gefahren {gefahren:.2f} m -> {grund}', flush=True)

            if grund == 'ok':
                ziele_erreicht += 1
                n.rundumblick(2)          # halbe Drehung reicht am Zwischenziel
            else:
                # Ziel merken, damit es nicht endlos wiederholt wird
                n.verworfen.append((zx, zy))
                if grund in ('blockiert', 'nah'):
                    if not n.befreie(max(gefahren, 0.20)):
                        if not n.drehe(1.05):
                            print('    kommt nicht frei - Fahrt wird beendet.',
                                  flush=True)
                            break
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
        bek, frei, belegt = n.kartenstand()
        pose = n.pose_in_karte()
        wo = f'x={pose[0]:+.2f} y={pose[1]:+.2f}' if pose else 'unbekannt'
        print(f'\nENDE nach {time.monotonic()-n.t0:.0f} s | {ziele_erreicht} Ziele '
              f'erreicht | {n.fluchten} Fluchtmanoever | Pose {wo}', flush=True)
        print(f'Karte {bek} bekannt ({frei} frei / {belegt} belegt)', flush=True)
        n.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
    return 0


if __name__ == '__main__':
    sys.exit(main())
