#!/usr/bin/env python3
"""Beobachtet eine laufende Kartierfahrt und meldet den Fortschritt.

Meldet alle 30 s: freie Flaeche, Zahl der Wandzellen, Kartenausdehnung,
zurueckgelegten Weg und die Pose. Stagniert die Karte trotz Fahrt, wird das
ausdruecklich vermerkt - dann hat der Sensor entweder schon alles gesehen,
oder es klemmt.

WICHTIG: Die Kennzahl "freie Flaeche" allein taugt NICHT zur Beurteilung einer
Karte. Bei Odometriefehlern waechst sie sogar, weil derselbe Raum mehrfach
versetzt eingetragen wird. Zwischendurch rendern und hinsehen
(karte_ansehen.py).
"""
import math
import sys
import time

import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, QoSDurabilityPolicy, QoSReliabilityPolicy
from nav_msgs.msg import OccupancyGrid
from tf2_ros import Buffer, TransformListener


def main():
    dauer = float(sys.argv[1]) if len(sys.argv) > 1 else 2400.0
    rclpy.init()
    n = Node('kartenwacht')
    d = {}
    n.create_subscription(
        OccupancyGrid, '/map', lambda m: d.__setitem__('m', m),
        QoSProfile(depth=1, durability=QoSDurabilityPolicy.TRANSIENT_LOCAL,
                   reliability=QoSReliabilityPolicy.RELIABLE))
    puf = Buffer()
    TransformListener(puf, n)

    letzte = 0.0
    start = time.monotonic()
    vor_frei = -1
    vor_pose = None
    weg = 0.0
    while rclpy.ok() and time.monotonic() - start < dauer:
        rclpy.spin_once(n, timeout_sec=0.2)
        # Weg laufend mitzaehlen, unabhaengig vom Meldetakt
        try:
            tf = puf.lookup_transform('map', 'base_link', rclpy.time.Time())
            p = (tf.transform.translation.x, tf.transform.translation.y)
            if vor_pose:
                s = math.dist(p, vor_pose)
                if 0.01 < s < 1.0:      # Spruenge durch Neuoptimierung ignorieren
                    weg += s
            vor_pose = p
        except Exception:
            p = None
        if time.monotonic() - letzte < 30 or 'm' not in d:
            continue
        letzte = time.monotonic()
        m = d['m']
        g = np.array(m.data, dtype=np.int8)
        r = m.info.resolution
        frei = int(((g >= 0) & (g < 50)).sum())
        belegt = int((g >= 50).sum())
        wo = f'{p[0]:+.1f}/{p[1]:+.1f}' if p else '?'
        zuwachs = frei - vor_frei if vor_frei >= 0 else 0
        hinweis = ''
        if vor_frei >= 0 and abs(zuwachs) < 20 and weg > 0.5:
            hinweis = f' | STAGNIERT trotz {weg:.1f} m Fahrt'
        print(f'{(time.monotonic()-start)/60:4.1f} min | frei {frei*r*r:5.1f} qm '
              f'({zuwachs:+6d} Zellen) | Waende {belegt:5d} | '
              f'Karte {m.info.width*r:.1f}x{m.info.height*r:.1f} m | '
              f'Weg {weg:4.1f} m | Pose {wo}{hinweis}', flush=True)
        vor_frei = frei
        weg = 0.0

    n.destroy_node()
    rclpy.shutdown()
    return 0


if __name__ == '__main__':
    sys.exit(main())
