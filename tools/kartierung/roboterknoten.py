#!/usr/bin/env python3
"""Listet laufende Amadeus-ROS-Knoten. Rueckgabe 0 = keiner laeuft.

WOZU: Zwei gleichzeitig laufende Stapel bedeuten zwei Publisher fuer
``map -> odom`` UND zwei scharfe ``base_hardware``-Knoten auf demselben
RS485-Bus. Am 12.08.2026 ist das passiert; die betroffene Messung war unbrauchbar
und der Zustand sicherheitsrelevant. Vor jedem Start pruefen.

WARUM ALS DATEI UND NICHT ALS EINZEILER: ``ps | grep -E 'muster'`` findet
zuverlaessig die eigene Shell, weil das Muster in deren Kommandozeile steht -
und in den Subshells der Kommandosubstitution, die eine ``$$``-Ausnahme nicht
abdeckt. Hier stehen die Muster im Dateiinhalt und tauchen in keiner
Kommandozeile auf. Gelesen wird direkt aus /proc.

Aufruf:
    python3 tools/kartierung/roboterknoten.py          # auflisten
    python3 tools/kartierung/roboterknoten.py --still  # nur Rueckgabewert

Als Wache vor einem Start:
    python3 tools/kartierung/roboterknoten.py --still || { echo "laeuft schon"; exit 1; }
"""
import argparse
import os
import sys

# Erkennung ueber den Pfad der ausfuehrbaren Datei beziehungsweise das
# ROS-Knotenargument - nicht ueber lose Namensfragmente, die auch in einer
# beliebigen Shell-Zeile vorkommen koennen.
MERKMALE = (
    'install/ldlidar_stl_ros2/lib',
    'install/slam_toolbox/lib',
    'install/base_hardware/lib',
    'install/amadeus_lidar_bringup/lib',
    'tf2_ros/static_transform_publisher',
    'ros2 launch amadeus_lidar_bringup',
)

KURZNAMEN = (
    ('ldlidar_stl_ros2', 'LiDAR-Treiber'),
    ('slam_toolbox', 'slam_toolbox'),
    ('base_hardware', 'base_hardware (Motoren!)'),
    ('scan_vereinheitlichen', 'Scan-Vereinheitlicher'),
    ('static_transform_publisher', 'statischer TF'),
    ('ros2 launch', 'ros2 launch'),
)


def kommandozeile(pid):
    try:
        with open(f'/proc/{pid}/cmdline', 'rb') as f:
            return f.read().replace(b'\0', b' ').decode('utf-8', 'replace').strip()
    except (OSError, ValueError):
        return None


def gefundene_knoten():
    eigen = {os.getpid(), os.getppid()}
    treffer = []
    for eintrag in os.listdir('/proc'):
        if not eintrag.isdigit():
            continue
        pid = int(eintrag)
        if pid in eigen:
            continue
        zeile = kommandozeile(pid)
        if not zeile:
            continue
        if not any(m in zeile for m in MERKMALE):
            continue
        name = next((n for s, n in KURZNAMEN if s in zeile), 'unbekannt')
        treffer.append((pid, name, zeile))
    return sorted(treffer)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--still', action='store_true',
                   help='nichts ausgeben, nur den Rueckgabewert setzen')
    p.add_argument('--lang', action='store_true',
                   help='vollstaendige Kommandozeilen zeigen')
    args = p.parse_args()

    knoten = gefundene_knoten()
    if not args.still:
        if not knoten:
            print('Keine Amadeus-Knoten aktiv.')
        else:
            print(f'{len(knoten)} Amadeus-Knoten aktiv:')
            for pid, name, zeile in knoten:
                print(f'  {pid:>7}  {name}')
                if args.lang:
                    print(f'           {zeile}')
            motoren = [k for k in knoten if 'base_hardware' in k[1]]
            if len(motoren) > 1:
                print(f'\nWARNUNG: {len(motoren)} base_hardware-Knoten auf '
                      f'demselben RS485-Bus. Sofort beenden.')
    return 1 if knoten else 0


if __name__ == '__main__':
    sys.exit(main())
