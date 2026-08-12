#!/usr/bin/env python3
"""Beobachtet, ob slam_toolbox waehrend einer Bewegung neue Kartenknoten anlegt.

HINTERGRUND: Nach einer 360-Grad-Drehung auf der Stelle blieb die Karte fast
unveraendert - der vom Mast verdeckte Sektor wurde nicht aufgefuellt, obwohl er
waehrend der Drehung ueber alle Richtungen wandert. Verdacht: slam_toolbox legt
bei reiner Drehung keine neuen Knoten an, weil minimum_travel_distance nie
erreicht wird.

slam_toolbox veroeffentlicht seinen Knotengraphen als Marker-Array. Das Array
enthaelt aber ausser den Knoten auch DELETEALL- und Kanten-Marker. Deshalb darf
``len(msg.markers)`` NICHT als Knotenzahl verwendet werden. Dieses Skript
zaehlt nur die von slam_toolbox als Kugeln veroeffentlichten Knoten-Marker und
meldet jede Aenderung zusammen mit der aktuellen Roboterpose.

Aufruf:  python3 slam_knoten_beobachten.py [Sekunden]
Parallel dazu den Roboter drehen (z.B. mit odometrie_drehtest.py).
"""
import math
import sys
import time

import rclpy
from rclpy.node import Node
from tf2_ros import Buffer, TransformListener
from visualization_msgs.msg import MarkerArray

from slam_graph_marker import zaehle_knoten_marker


def main():
    dauer = float(sys.argv[1]) if len(sys.argv) > 1 else 90.0
    rclpy.init()
    n = Node('slam_knoten_beobachten')
    stand = {'n': 0}

    def on_graph(msg):
        # Upstream slam_toolbox erzeugt jeden Posegraph-Knoten als SPHERE im
        # Namespace "slam_toolbox". Zusaetzlich befinden sich ein DELETEALL-
        # Marker und zwei LINE_LIST-Marker fuer Kanten im selben MarkerArray.
        # Diese drei Verwaltungsmarker duerfen nicht mitgezaehlt werden.
        stand['n'] = zaehle_knoten_marker(msg.markers)

    n.create_subscription(MarkerArray, '/slam_toolbox/graph_visualization',
                          on_graph, 10)
    puf = Buffer()
    TransformListener(puf, n)

    print(f'Beobachte {dauer:.0f} s. Jetzt den Roboter drehen.\n', flush=True)
    print(f'{"Zeit":>6} {"Knoten":>7} {"Pose in der Karte":>28} {"Drehung":>9}')
    print('-' * 56)
    t0 = time.monotonic()
    vor = -1
    gedreht = 0.0
    letzte_yaw = None
    # Knotenstand einlesen, BEVOR bewegt wird - die ersten Knoten entstehen
    # schon beim Start und duerfen der Bewegung nicht zugerechnet werden.
    for _ in range(30):
        rclpy.spin_once(n, timeout_sec=0.1)
    knoten_am_anfang = stand['n']
    print(f'(Knotenstand vor der Bewegung: {knoten_am_anfang})\n', flush=True)
    while rclpy.ok() and time.monotonic() - t0 < dauer:
        rclpy.spin_once(n, timeout_sec=0.1)
        try:
            tf = puf.lookup_transform('map', 'base_link', rclpy.time.Time())
            t = tf.transform.translation
            q = tf.transform.rotation
            yaw = math.atan2(2*(q.w*q.z+q.x*q.y), 1-2*(q.y*q.y+q.z*q.z))
        except Exception:
            continue
        if letzte_yaw is not None:
            d = yaw - letzte_yaw
            while d > math.pi:
                d -= 2*math.pi
            while d < -math.pi:
                d += 2*math.pi
            gedreht += abs(d)
        letzte_yaw = yaw
        if stand['n'] != vor:
            vor = stand['n']
            print(f'{time.monotonic()-t0:5.1f}s {stand["n"]:7d} '
                  f'  x={t.x:+.2f} y={t.y:+.2f} yaw={math.degrees(yaw):+7.1f}  '
                  f'{math.degrees(gedreht):7.1f} Grad', flush=True)

    print()
    print(f'Knoten zu Beginn    : {knoten_am_anfang}')
    print(f'Knoten am Ende      : {stand["n"]}')
    print(f'davon NEU           : {stand["n"] - knoten_am_anfang}')
    print(f'insgesamt gedreht   : {math.degrees(gedreht):.1f} Grad')
    # Entscheidend ist, wie viele Knoten WAEHREND der Bewegung dazukamen -
    # nicht die Gesamtzahl. Die ersten Knoten entstehen schon beim Start.
    neu = stand['n'] - knoten_am_anfang
    if gedreht > math.radians(90) and neu == 0:
        print('\nBEFUND: Trotz deutlicher Drehung kam KEIN neuer Knoten dazu.')
        print('  Damit traegt slam_toolbox die neu sichtbaren Bereiche nicht ein.')
        print('  Ursache unter ROS 2 Humble: Der Vorfilter prueft nur Translation.')
        print('  Abhilfe: gepinnten Upstream-Backport installieren und')
        print('  check_min_dist_and_heading_precisely=true setzen.')
    elif neu > 0:
        print(f'\nBEFUND: Die Drehung erzeugt Knoten '
              f'({math.degrees(gedreht)/neu:.1f} Grad je neuem Knoten).')
    else:
        print('\nZu wenig Bewegung fuer eine Aussage.')
    n.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
