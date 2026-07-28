#!/usr/bin/env python3
"""Entfernt Strahlartefakte aus einer gespeicherten Karte.

DAS PROBLEM:
Wo die Tiefenkamera keine verlaessliche Entfernung messen kann - Fensterflaechen,
Spiegel, glatte helle Waende - liefert sie Punkte weit hinter der echten Flaeche.
RTAB-Maps Strahlverfolgung traegt dann die ganze Bahn dorthin als FREI ein, quer
durch Waende. In der Karte sieht das aus wie lange helle Strahlen, die vom
Standort nach aussen schiessen. Sie blaehen die gemessene Freiflaeche auf: die
Karte vom 28.07.2026 meldete 26.5 qm in einem Raum von 18.6 qm.

DIE LOESUNG:
Diese Strahlen liegen jenseits der Waende und haengen deshalb NICHT mit der
Flaeche zusammen, auf der der Roboter steht. Ein Flutfuellen vom groessten
zusammenhaengenden Freibereich aus findet genau das heraus: Was von dort nicht
erreichbar ist, kann der Roboter auch nicht befahren und wird auf UNBEKANNT
gesetzt.

Das ist bewusst konservativ: Es wird nur weggenommen, nie hinzugefuegt. Echte
Freiflaeche hinter einer offenen Tuer verschwindet dadurch nur, wenn die Tuer in
der Karte zugewachsen ist - dann war sie ohnehin nicht befahrbar.

PGM-Werte: 254 = frei, 0 = belegt, 205 = unbekannt.
Eine Schwelle wie ">200 ist frei" zaehlt Unbekanntes faelschlich mit - dieser
Fehler ist im Projekt schon passiert.

Aufruf:  python3 karte_bereinigen.py <kartenordner> [--schreiben]
Ohne --schreiben wird nur berichtet und eine Vorschau erzeugt.
"""
import sys
from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image
import yaml

FREI, BELEGT, UNBEKANNT = 254, 0, 205


def flutfuellen(frei_maske):
    """Groesster zusammenhaengender Freibereich (4er-Nachbarschaft)."""
    h, w = frei_maske.shape
    besucht = np.zeros_like(frei_maske, dtype=bool)
    bestes = np.zeros_like(frei_maske, dtype=bool)
    bestgroesse = 0
    for sy in range(h):
        for sx in range(w):
            if not frei_maske[sy, sx] or besucht[sy, sx]:
                continue
            gruppe = []
            q = deque([(sy, sx)])
            besucht[sy, sx] = True
            while q:
                y, x = q.popleft()
                gruppe.append((y, x))
                for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    ny, nx = y + dy, x + dx
                    if (0 <= ny < h and 0 <= nx < w
                            and frei_maske[ny, nx] and not besucht[ny, nx]):
                        besucht[ny, nx] = True
                        q.append((ny, nx))
            if len(gruppe) > bestgroesse:
                bestgroesse = len(gruppe)
                bestes = np.zeros_like(frei_maske, dtype=bool)
                for y, x in gruppe:
                    bestes[y, x] = True
    return bestes


def main(ordner, schreiben=False):
    o = Path(ordner)
    meta = yaml.safe_load((o / 'map.yaml').read_text())
    aufl = float(meta['resolution'])
    img = Image.open(o / 'map.pgm').convert('L')
    a = np.array(img)

    frei = a > 250
    belegt = a < 50
    print(f'Karte {a.shape[1]}x{a.shape[0]} @ {aufl:.2f} m')
    print(f'  vorher: frei {frei.sum()} ({frei.sum()*aufl**2:.1f} qm), '
          f'belegt {belegt.sum()}')

    haupt = flutfuellen(frei)
    weg = frei & ~haupt
    print(f'  groesster zusammenhaengender Bereich: {haupt.sum()} Zellen '
          f'({haupt.sum()*aufl**2:.1f} qm)')
    print(f'  abgetrennte Freiflaeche (Artefakte): {weg.sum()} Zellen '
          f'({weg.sum()*aufl**2:.1f} qm) -> {100.0*weg.sum()/max(1,frei.sum()):.1f} %')

    neu = a.copy()
    neu[weg] = UNBEKANNT
    # Belegte Zellen weit ausserhalb des Hauptbereichs sind meist Strahlenenden.
    # Sie bleiben stehen - lieber ein Hindernis zu viel als eines zu wenig.

    vorschau = Image.new('RGB', (a.shape[1], a.shape[0]))
    px = []
    for y in range(a.shape[0]):
        for x in range(a.shape[1]):
            if haupt[y, x]:
                px.append((255, 255, 255))        # bleibt: befahrbar
            elif weg[y, x]:
                px.append((215, 95, 95))          # entfernt: Artefakt
            elif belegt[y, x]:
                px.append((25, 28, 40))
            else:
                px.append((155, 165, 180))
    vorschau.putdata(px)
    f = max(4, int(700 / max(a.shape)))
    vorschau = vorschau.resize((a.shape[1]*f, a.shape[0]*f), Image.NEAREST)
    ziel = o / 'karte_bereinigt_vorschau.png'
    vorschau.save(ziel)
    print(f'  Vorschau (rot = entfernt): {ziel}')

    if schreiben:
        Image.fromarray(neu).save(o / 'map_bereinigt.pgm')
        y = dict(meta)
        y['image'] = 'map_bereinigt.pgm'
        (o / 'map_bereinigt.yaml').write_text(yaml.safe_dump(y, sort_keys=False))
        print(f'  geschrieben: {o}/map_bereinigt.pgm + .yaml')
    else:
        print('  (nur Bericht - mit --schreiben wird die bereinigte Karte abgelegt)')


if __name__ == '__main__':
    main(sys.argv[1], '--schreiben' in sys.argv)
