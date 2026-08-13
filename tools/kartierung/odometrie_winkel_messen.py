#!/usr/bin/env python3
"""Misst den Winkelfehler der Radodometrie gegen den LiDAR als Referenz.

WARUM NEU: ``odometrie_drehtest.py`` vergleicht nur den Anfangs- mit dem
Endscan. Das ist ein einziger Messpunkt, er ist modulo 360 Grad mehrdeutig, und
er verschweigt, ob der Fehler gleichmaessig ueber die Drehung entsteht. Drei
weitere Schwaechen verfaelschen ihn zusaetzlich:

1. Er liest ``/scan``. Der STL-27L liefert dort je Umdrehung 2145 bis 2176
   Strahlen, Referenz- und Endscan haben also verschiedene Winkelskalen.
   Dieses Werkzeug nimmt ``/scan_normiert`` mit fester Strahlenzahl.
2. Er summiert die Odometrie nur bis zum Erreichen der Sollzahl. Waehrend der
   Bremsphase dreht der Roboter weiter; dieser Anteil landet im LiDAR-Wert,
   nicht in der Odometrie. Hier laufen beide ueber dasselbe Zeitfenster.
3. Sein Korrekturvorschlag ist invers. Richtig ist:

       omega = (v_rechts - v_links) / spurweite

   Die Odometrie rechnet mit der angenommenen Spurweite, der Roboter dreht sich
   mit der echten. Daraus folgt

       winkel_echt / winkel_odometrie = spurweite_angenommen / spurweite_echt
       spurweite_echt = spurweite_angenommen * winkel_odom / winkel_echt

   Dreht der Roboter WENIGER als gemeldet, ist die echte Spurweite GROESSER
   als die angenommene.

WIE GEMESSEN WIRD: Zu Beginn wird ein Referenzscan aufgenommen. Zu jedem
weiteren Scan wird die zyklische Verschiebung gegen diesen Referenzscan
bestimmt - das ist die reale Orientierung, unabhaengig von den Raedern. Die
Suche startet bei der letzten Schaetzung plus dem Odometrie-ZUWACHS seit dem
letzten Scan (nicht dem Absolutwert), damit sich kein Odometriefehler
aufsummieren und das Ergebnis zur Odometrie hinziehen kann.

Aus allen Messpunkten wird eine Ursprungsgerade gelegt. Ihre Steigung ist der
gesuchte Skalenfaktor. Das Bestimmtheitsmass zeigt dabei mit an, ob ueberhaupt
ein sauberer Skalenfehler vorliegt oder etwas anderes im Spiel ist.

BEIDE DREHRICHTUNGEN: Ein echter Spurweitenfehler ist ein Skalenfaktor und muss
im Uhrzeigersinn genauso gross sein wie dagegen. Weicht er ab, ist es kein
Spurweitenfehler, sondern ein richtungsabhaengiger Effekt - etwa Laufzeit oder
Zeitstempel. Deshalb wird standardmaessig in beide Richtungen gefahren.

ACHTUNG: Der Roboter dreht sich. Not-Aus bereithalten, Flaeche frei halten.
Dieses Werkzeug aendert NICHTS an der Konfiguration; es misst und rechnet vor.

Aufruf:
    python3 odometrie_winkel_messen.py [--umdrehungen 1] [--w 0.25]
                                       [--richtung beide|ccw|cw]
"""
import argparse
import math
import sys
import time

import numpy as np
import rclpy
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from rclpy.node import Node
from rclpy.qos import QoSProfile, QoSReliabilityPolicy
from sensor_msgs.msg import LaserScan

MAX_REICHWEITE = 8.0     # m; weiter entfernte Punkte helfen beim Vergleich nicht
SUCHFENSTER = 45         # Bins um die Vorhersage herum
MINDEST_UEBERLAPP = 0.2  # Anteil gemeinsam gueltiger Strahlen

# Aktuell gesetzter Wert, siehe base_hardware_params.yaml. Wird nur fuer den
# Rechenvorschlag benutzt und NICHT veraendert.
SPURWEITE_ANGENOMMEN = 0.3845


def scan_vektor(msg, laenge):
    """Scan als Distanzprofil; ungueltige Werte (auch NaN) werden 0."""
    v = np.zeros(laenge, dtype=np.float32)
    n = min(len(msg.ranges), laenge)
    r = np.array(msg.ranges[:n], dtype=np.float32)
    gut = (np.isfinite(r) & (r >= msg.range_min)
           & (r <= min(msg.range_max, MAX_REICHWEITE)))
    v[:n] = np.where(gut, r, 0.0)
    return v


def verschiebung_bei(ref, akt, kandidat):
    """Mittlere Abweichung, wenn akt um kandidat Bins gerollt wird."""
    g = np.roll(akt, kandidat)
    m = (ref > 0) & (g > 0)
    if m.sum() < len(ref) * MINDEST_UEBERLAPP:
        return None
    return float(np.mean(np.abs(ref[m] - g[m])))


def beste_verschiebung(ref, akt, mitte):
    """Beste zyklische Verschiebung im Fenster um mitte."""
    n = len(ref)
    beste, bester_wert = None, float('inf')
    for d in range(-SUCHFENSTER, SUCHFENSTER + 1):
        k = int(mitte + d) % n
        wert = verschiebung_bei(ref, akt, k)
        if wert is not None and wert < bester_wert:
            bester_wert, beste = wert, k
    return beste, bester_wert


class Winkelmessung(Node):

    def __init__(self, scan_topic):
        super().__init__('odometrie_winkel_messen')
        self.pub = self.create_publisher(Twist, '/cmd_vel', 10)
        self.create_subscription(Odometry, '/odom', self._auf_odom, 20)
        self.create_subscription(
            LaserScan, scan_topic, self._auf_scan,
            QoSProfile(depth=5, reliability=QoSReliabilityPolicy.BEST_EFFORT))
        self.yaw = None
        self.pos = None
        self.scan = None
        self.scan_neu = False

    def _auf_odom(self, m):
        q = m.pose.pose.orientation
        self.yaw = math.atan2(2 * (q.w * q.z + q.x * q.y),
                              1 - 2 * (q.y * q.y + q.z * q.z))
        self.pos = (m.pose.pose.position.x, m.pose.pose.position.y)

    def _auf_scan(self, m):
        self.scan = m
        self.scan_neu = True

    def halt(self, sekunden=3.0):
        """Stoppkommandos senden und dabei weiter zuhoeren."""
        ende = time.monotonic() + sekunden
        while time.monotonic() < ende and rclpy.ok():
            self.pub.publish(Twist())
            rclpy.spin_once(self, timeout_sec=0.05)


def eine_richtung(n, ziel, w_soll, name):
    """Eine Drehung fahren und dabei LiDAR gegen Odometrie mitschreiben."""
    laenge = len(n.scan.ranges)
    grad_je_bin = 360.0 / laenge
    ref = scan_vektor(n.scan, laenge)
    start_yaw = n.yaw
    start_pos = n.pos

    print(f'\n--- {name} ---')
    print(f'Referenzscan: {laenge} Strahlen, {grad_je_bin:.4f} Grad je Bin')
    print(f'Drehe {math.degrees(ziel):.0f} Grad mit {abs(w_soll):.2f} rad/s')

    odom_summe = 0.0          # vorzeichenbehaftet, entwickelt sich mit
    letzte_yaw = n.yaw
    lidar_bins = 0.0          # aufgewickelte LiDAR-Verschiebung in Bins
    letzter_odom_bei_scan = 0.0
    punkte = []               # (odometrie_grad, lidar_grad)
    guete = []
    uebersprungen = 0

    t = Twist()
    t.angular.z = w_soll
    frist = time.monotonic() + abs(ziel / w_soll) * 3.0 + 40.0
    fahren = True

    while rclpy.ok() and time.monotonic() < frist:
        if fahren:
            n.pub.publish(t)
        else:
            n.pub.publish(Twist())
        rclpy.spin_once(n, timeout_sec=0.02)

        d = n.yaw - letzte_yaw
        while d > math.pi:
            d -= 2 * math.pi
        while d < -math.pi:
            d += 2 * math.pi
        if abs(d) > 1e-6:
            odom_summe += d
            letzte_yaw = n.yaw

        if fahren and abs(odom_summe) >= ziel:
            # Nicht abbrechen: die Bremsphase gehoert mit ins Fenster, sonst
            # zaehlt der LiDAR eine Drehung mit, die die Odometrie nicht sieht.
            fahren = False
            aus_bei = time.monotonic() + 3.0

        if not fahren and time.monotonic() > aus_bei:
            break

        if n.scan_neu:
            n.scan_neu = False
            if len(n.scan.ranges) != laenge:
                # Auf /scan_normiert kommt das nie vor. Auf /scan schon, und
                # dann klaffen zwischen brauchbaren Scans grosse Luecken.
                uebersprungen += 1
                continue
            zuwachs = math.degrees(odom_summe) - letzter_odom_bei_scan
            letzter_odom_bei_scan = math.degrees(odom_summe)
            vorhersage = lidar_bins + zuwachs / grad_je_bin
            akt = scan_vektor(n.scan, laenge)
            k, wert = beste_verschiebung(ref, akt, round(vorhersage))
            if k is None:
                continue
            # k liegt in [0, laenge); auf die Vorhersage aufwickeln.
            versatz = (k - vorhersage) % laenge
            if versatz > laenge / 2:
                versatz -= laenge
            lidar_bins = vorhersage + versatz
            guete.append(wert)
            punkte.append((math.degrees(odom_summe), lidar_bins * grad_je_bin))

    n.halt(3.0)

    if uebersprungen:
        print(f'WARNUNG: {uebersprungen} Scans wegen abweichender '
              f'Strahlenzahl uebersprungen.')
    if len(punkte) < 60:
        print(f'ZU WENIGE MESSPUNKTE ({len(punkte)}) - keine belastbare '
              f'Aussage. Bei 10 Hz und einer Umdrehung sind rund 250 zu '
              f'erwarten; deutlich weniger heisst, dass die Verfolgung '
              f'zwischen den Scans zu grosse Spruenge machen musste.')
        return None

    o = np.array([p[0] for p in punkte])
    l = np.array([p[1] for p in punkte])
    # Vorzeichen der LiDAR-Achse an die Odometrie angleichen: die Bin-Richtung
    # des Sensors ist Konvention, die Physik ist es nicht.
    if np.dot(o, l) < 0:
        l = -l
        richtungshinweis = ('Bin-Richtung des Sensors laeuft der Odometrie '
                            'entgegen (erwartet, laser_scan_dir=Clockwise)')
    else:
        richtungshinweis = 'Bin-Richtung laeuft mit der Odometrie'

    # Ursprungsgerade: die Drehung startet definitionsgemaess bei 0/0.
    k_faktor = float(np.dot(o, l) / np.dot(o, o))
    rest = l - k_faktor * o
    r2 = 1.0 - float(np.dot(rest, rest) / np.dot(l - l.mean(), l - l.mean()))

    versatz_m = math.dist(n.pos, start_pos) if (n.pos and start_pos) else float('nan')

    print(f'Messpunkte         : {len(punkte)}')
    print(f'Vergleichsguete    : {np.mean(guete):.3f} m mittlere Abweichung')
    print(f'Odometrie gesamt   : {abs(o[-1]):8.2f} Grad')
    print(f'LiDAR gesamt       : {abs(l[-1]):8.2f} Grad')
    print(f'Skalenfaktor       : {k_faktor:.5f}   (echt / gemeldet)')
    print(f'Bestimmtheitsmass  : {r2:.5f}')
    print(f'Seitlicher Versatz : {versatz_m*100:.1f} cm')
    print(f'Hinweis            : {richtungshinweis}')
    return {'name': name, 'k': k_faktor, 'r2': r2, 'punkte': len(punkte),
            'odom': abs(o[-1]), 'lidar': abs(l[-1]), 'versatz': versatz_m,
            'guete': float(np.mean(guete))}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--umdrehungen', type=float, default=1.0)
    p.add_argument('--w', type=float, default=0.25,
                   help='Drehgeschwindigkeit in rad/s (Betrag)')
    p.add_argument('--richtung', choices=('beide', 'ccw', 'cw'),
                   default='beide')
    p.add_argument('--topic', default=None,
                   help='Scan-Topic; Standard /scan_normiert mit Rueckfall')
    args = p.parse_args()

    ziel = args.umdrehungen * 2 * math.pi

    rclpy.init()
    probe = rclpy.create_node('winkel_topic_probe')
    topic = args.topic
    if topic is None:
        # Erst spinnen lassen: direkt nach dem Anlegen ist der Graph noch leer
        # und die Erkennung faellt faelschlich auf /scan zurueck. Auf /scan
        # schwankt die Strahlenzahl, und da nur gleich lange Scans verglichen
        # werden koennen, bleiben davon wenige Prozent uebrig - die Verfolgung
        # verliert dann die Spur.
        ende = time.monotonic() + 8.0
        vorhanden = []
        while time.monotonic() < ende and rclpy.ok():
            rclpy.spin_once(probe, timeout_sec=0.2)
            vorhanden = [t for t, _ in probe.get_topic_names_and_types()]
            if '/scan_normiert' in vorhanden:
                break
        topic = '/scan_normiert' if '/scan_normiert' in vorhanden else '/scan'
        if topic == '/scan':
            print('WARNUNG: /scan_normiert nicht gefunden. Auf /scan schwankt '
                  'die Strahlenzahl; brauchbar bleibt nur ein Bruchteil der '
                  'Scans und die Messung wird unzuverlaessig. Launch mit '
                  'normalize_scan:=true starten.')
    probe.destroy_node()
    print(f'Referenz-Topic: {topic}')

    n = Winkelmessung(topic)
    t0 = time.monotonic()
    while (n.yaw is None or n.scan is None) and time.monotonic() - t0 < 25 \
            and rclpy.ok():
        rclpy.spin_once(n, timeout_sec=0.1)
    if n.yaw is None:
        print('KEINE Odometrie - laeuft base_hardware scharf?')
        return 1
    if n.scan is None:
        print(f'KEIN {topic} - laeuft der LiDAR?')
        return 1

    laeufe = []
    if args.richtung in ('beide', 'ccw'):
        e = eine_richtung(n, ziel, abs(args.w), 'gegen den Uhrzeigersinn (CCW)')
        if e:
            laeufe.append(e)
        n.halt(4.0)
    if args.richtung in ('beide', 'cw'):
        e = eine_richtung(n, ziel, -abs(args.w), 'im Uhrzeigersinn (CW)')
        if e:
            laeufe.append(e)
    n.halt(3.0)

    print('\n' + '=' * 66)
    print('ERGEBNIS')
    print('=' * 66)
    print(f'{"Richtung":>32} {"Faktor":>9} {"R2":>8} {"Versatz":>9}')
    for e in laeufe:
        print(f'{e["name"]:>32} {e["k"]:>9.5f} {e["r2"]:>8.5f} '
              f'{e["versatz"]*100:>7.1f}cm')

    if len(laeufe) == 2:
        unterschied = abs(laeufe[0]['k'] - laeufe[1]['k'])
        print(f'\nUnterschied zwischen den Richtungen: {unterschied:.5f}')
        if unterschied > 0.005:
            print('  >>> Die Richtungen weichen deutlich voneinander ab. Ein')
            print('      Spurweitenfehler ist ein Skalenfaktor und muesste in')
            print('      beiden Richtungen gleich sein. Hier wirkt etwas')
            print('      Richtungsabhaengiges - NICHT die Spurweite anpassen.')
            return 0
        print('  Beide Richtungen stimmen ueberein: das Verhalten eines')
        print('  echten Spurweitenfehlers.')

    mittel = float(np.mean([e['k'] for e in laeufe]))
    print(f'\nMittlerer Skalenfaktor: {mittel:.5f}')
    if abs(1.0 - mittel) < 0.004:
        print('Das sind weniger als 1.5 Grad je Umdrehung - im Rahmen der')
        print('Messgenauigkeit. Kein Handlungsbedarf.')
        return 0

    neu = SPURWEITE_ANGENOMMEN / mittel
    print(f'Fehler je Umdrehung   : {(mittel - 1.0) * 360.0:+.2f} Grad')
    print(f'\nRECHNERISCHER VORSCHLAG (nicht angewendet):')
    print(f'  wheel_separation_m: {SPURWEITE_ANGENOMMEN:.4f} -> {neu:.4f}')
    print(f'  aus spurweite_echt = spurweite_angenommen / skalenfaktor')
    print('  Der Roboter dreht sich '
          f'{"WENIGER" if mittel < 1 else "MEHR"} als gemeldet, die echte '
          f'Spurweite ist also '
          f'{"GROESSER" if mittel < 1 else "KLEINER"}.')
    print('\nVor dem Uebernehmen: Kalibrierung ist sicherheitsrelevant und wird')
    print('laut AGENTS.md getrennt geaendert und getrennt getestet.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
