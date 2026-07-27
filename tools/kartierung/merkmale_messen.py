#!/usr/bin/env python3
"""Misst, warum RTAB-Map Wiedererkennungen ablehnt - statt es zu vermuten.

Hintergrund: Im Log stehen massenhaft
    "Rejected loop closure A -> B: Not enough inliers 0/20 (matches=50)"
Viele Uebereinstimmungen, aber null geometrisch bestaetigte. Der Verdacht ist,
dass den Bildmerkmalen die TIEFE fehlt: ohne 3D-Punkt kann die Pose nicht
geprueft werden. Genau das wird hier nachgezaehlt.

In der Feature-Tabelle stehen depth_x/y/z je Merkmal. Fehlt die Tiefe, sind
sie NULL (bzw. NaN).
"""
import math
import sqlite3
import struct
import sys


def to_float(b):
    """depth_* liegt als 4-Byte-Float-BLOB oder als Zahl vor."""
    if b is None:
        return None
    if isinstance(b, (int, float)):
        return float(b)
    if isinstance(b, (bytes, bytearray)) and len(b) >= 4:
        try:
            return struct.unpack('f', bytes(b[:4]))[0]
        except Exception:
            return None
    return None


def main(db):
    c = sqlite3.connect(f'file:{db}?mode=ro', uri=True)
    cur = c.cursor()

    cur.execute('SELECT COUNT(*) FROM Node')
    knoten = cur.fetchone()[0]
    cur.execute('SELECT COUNT(*) FROM Word')
    woerter = cur.fetchone()[0]
    cur.execute('SELECT COUNT(*) FROM Feature')
    gesamt = cur.fetchone()[0]

    print(f'Knoten            : {knoten}')
    print(f'Woerterbuch       : {woerter} Woerter'
          f'{"  << FEHLT!" if woerter == 0 else ""}')
    print(f'Bildmerkmale      : {gesamt}')

    # Stichprobe reicht und schont den Jetson.
    cur.execute('SELECT depth_x, depth_y, depth_z FROM Feature LIMIT 40000')
    mit, ohne = 0, 0
    tiefen = []
    for dx, dy, dz in cur.fetchall():
        z = to_float(dz)
        if z is None or (isinstance(z, float) and (math.isnan(z) or z <= 0.0)):
            ohne += 1
        else:
            mit += 1
            tiefen.append(z)
    stichprobe = mit + ohne
    if stichprobe:
        print(f'\nStichprobe        : {stichprobe} Merkmale')
        print(f'  MIT Tiefe       : {mit:6d}  ({100*mit/stichprobe:5.1f} %)')
        print(f'  OHNE Tiefe      : {ohne:6d}  ({100*ohne/stichprobe:5.1f} %)')
    if tiefen:
        tiefen.sort()
        n = len(tiefen)
        print(f'\nTiefenverteilung der brauchbaren Merkmale [m]:')
        print(f'  Minimum         : {tiefen[0]:.2f}')
        print(f'  25 %            : {tiefen[n//4]:.2f}')
        print(f'  Median          : {tiefen[n//2]:.2f}')
        print(f'  75 %            : {tiefen[3*n//4]:.2f}')
        print(f'  Maximum         : {tiefen[-1]:.2f}')

    # Wie viele Merkmale hat ein Knoten typischerweise MIT Tiefe?
    cur.execute('''SELECT node_id, COUNT(*) FROM Feature
                   WHERE depth_z IS NOT NULL GROUP BY node_id LIMIT 300''')
    proknoten = sorted(r[1] for r in cur.fetchall())
    if proknoten:
        m = len(proknoten)
        print(f'\nMerkmale MIT Tiefe je Knoten: Median {proknoten[m//2]}, '
              f'kleinster {proknoten[0]}, groesster {proknoten[-1]}')
        print('  (Vis/MinInliers steht auf 20 - der Median muss deutlich')
        print('   darueber liegen, sonst kann eine Pruefung gar nicht gelingen.)')


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else
         '/home/p/.local/share/amadeus/rtabmap.db')
