#!/usr/bin/env python3
"""Misst den vom eigenen Rumpf verdeckten Winkelsektor des STL-27L.

Hintergrund: Der LiDAR sitzt vor dem Kameramast. Mast und Rumpf erzeugen
konstante Nahreflexionen, die als Hindernis in die Karte wandern wuerden. Der
Integrationsplan verlangt, diese Grenzen zu MESSEN statt aus der
Gehaeusezeichnung zu schaetzen (Abschnitt 5.5).

Verfahren: Ueber viele Scans wird je Winkel der Median der Entfernung und die
Streuung gebildet. Eigene Aufbauten erkennt man daran, dass sie
  * nah sind (unter NAH_GRENZE) und
  * sich NICHT bewegen (winzige Streuung ueber alle Scans).
Ein Mensch oder ein Karton in der Naehe schwankt dagegen.

Voraussetzung: Roboter steht still und frei, mindestens ~1,5 m Abstand nach
vorn. Der Treiber laeuft mit crop:=false, sonst misst man die eigene Maske.

Aufruf:  python3 lidar_totzone_messen.py [Anzahl Scans]
"""
import math
import sys
import time

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, QoSReliabilityPolicy
from sensor_msgs.msg import LaserScan

NAH_GRENZE = 0.60      # m  - naeher gilt als verdaechtig (eigener Aufbau)
STREU_GRENZE = 0.02    # m  - darunter gilt als unbeweglich
SICHERHEIT = 4.0       # Grad Zugabe je Rand (Plan: 3-5)


def main():
    ziel = int(sys.argv[1]) if len(sys.argv) > 1 else 40
    rclpy.init()
    n = Node('lidar_totzone')
    scans = []
    qos = QoSProfile(depth=10, reliability=QoSReliabilityPolicy.BEST_EFFORT)
    n.create_subscription(LaserScan, '/scan', lambda m: scans.append(m), qos)

    print(f'Sammle {ziel} Scans - Roboter bitte NICHT bewegen ...', flush=True)
    t0 = time.monotonic()
    while len(scans) < ziel and time.monotonic() - t0 < 60 and rclpy.ok():
        rclpy.spin_once(n, timeout_sec=0.1)
    if len(scans) < 5:
        print('zu wenige Scans empfangen'); rclpy.shutdown(); return 1
    print(f'{len(scans)} Scans ausgewertet.\n', flush=True)

    m0 = scans[0]
    anz = len(m0.ranges)
    # je Strahl ueber alle Scans sammeln
    fest = []      # Indizes, die nah UND unbeweglich sind
    for i in range(anz):
        werte = [s.ranges[i] for s in scans
                 if i < len(s.ranges) and m0.range_min <= s.ranges[i] <= m0.range_max]
        if len(werte) < len(scans) * 0.8:
            continue                      # zu oft ungueltig -> kein fester Aufbau
        werte.sort()
        med = werte[len(werte) // 2]
        streu = werte[-1] - werte[0]
        if med < NAH_GRENZE and streu < STREU_GRENZE:
            fest.append((i, med))

    def grad(i):
        return math.degrees(m0.angle_min + i * m0.angle_increment) % 360.0

    print(f'Strahlen gesamt              : {anz}')
    print(f'nah UND unbeweglich          : {len(fest)}  '
          f'(< {NAH_GRENZE} m, Streuung < {STREU_GRENZE*100:.0f} mm)')
    if not fest:
        print('\nKein fester Aufbau im Sichtfeld gefunden.')
        print('Entweder steht der Sensor voellig frei - oder er ist noch nicht')
        print('montiert. Dann ist keine Maskierung noetig.')
        n.destroy_node(); rclpy.shutdown(); return 0

    # zusammenhaengende Sektoren bilden (auf dem Kreis)
    winkel = sorted(grad(i) for i, _ in fest)
    sektoren = []
    start = prev = winkel[0]
    for w in winkel[1:]:
        if w - prev > 2.0:            # Luecke > 2 Grad -> neuer Sektor
            sektoren.append((start, prev))
            start = w
        prev = w
    sektoren.append((start, prev))
    # Sektor ueber die 0-Grad-Naht zusammenfuehren
    if len(sektoren) > 1 and sektoren[0][0] < 2.0 and sektoren[-1][1] > 358.0:
        sektoren[0] = (sektoren[-1][0] - 360.0, sektoren[0][1])
        sektoren.pop()

    print('\nGefundene feste Sektoren (vermutlich Mast/Rumpf):')
    entf = {i: d for i, d in fest}
    for a, b in sorted(sektoren, key=lambda s: s[1]-s[0], reverse=True):
        breite = b - a
        nahe = [d for i, d in fest if a <= grad(i) <= b or a < 0 <= grad(i)-360 <= b]
        med = sorted(nahe)[len(nahe)//2] if nahe else float('nan')
        print(f'  {a:+7.1f} bis {b:+7.1f} Grad  (Breite {breite:5.1f} Grad, '
              f'Abstand ~{med:.2f} m)')

    groesster = max(sektoren, key=lambda s: s[1]-s[0])
    a, b = groesster
    print('\n--- Vorschlag fuer die Maskierung ---')
    print(f'  groesster fester Sektor : {a:+.1f} bis {b:+.1f} Grad')
    print(f'  mit {SICHERHEIT:.0f} Grad Zugabe je Rand:')
    print(f'      angle_crop_min: {a - SICHERHEIT:.1f}')
    print(f'      angle_crop_max: {b + SICHERHEIT:.1f}')
    verdeckt = (b + SICHERHEIT) - (a - SICHERHEIT)
    print(f'  verdeckt: {verdeckt:.1f} Grad  ->  nutzbares Sichtfeld '
          f'{360 - verdeckt:.1f} Grad')
    print('\nWICHTIG: Diese Werte sind ein VORSCHLAG aus der Messung. Vor der')
    print('Uebernahme mit crop:=true gegenpruefen, dass kein Rumpfteil mehr in')
    print('/scan erscheint, und mit einem Karton knapp innerhalb und ausserhalb')
    print('beider Grenzen testen.')

    n.destroy_node()
    rclpy.shutdown()
    return 0


if __name__ == '__main__':
    sys.exit(main())
