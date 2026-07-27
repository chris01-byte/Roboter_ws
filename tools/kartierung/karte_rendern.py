#!/usr/bin/env python3
"""Gespeicherte Karte als PNG rendern und ehrlich auszaehlen.

PGM-Semantik von map_server: 254 = frei, 0 = belegt, 205 = UNBEKANNT.
Eine Schwelle wie ">200 ist frei" zaehlt Unbekanntes faelschlich als frei -
dieser Fehler ist in diesem Projekt schon einmal passiert.
"""
import sys
from pathlib import Path
from PIL import Image

def main(pgm_pfad):
    p = Path(pgm_pfad)
    img = Image.open(p).convert('L')
    w, h = img.size
    px = list(img.getdata())

    frei = sum(1 for v in px if v > 250)          # 254
    belegt = sum(1 for v in px if v < 50)         # 0
    unbekannt = len(px) - frei - belegt           # 205 und alles dazwischen

    # Farbig einfaerben: frei = weiss, belegt = schwarz, unbekannt = grau-blau
    aus = Image.new('RGB', (w, h))
    aus.putdata([(255, 255, 255) if v > 250 else
                 (20, 20, 30) if v < 50 else
                 (150, 160, 175) for v in px])
    gross = aus.resize((w * 4, h * 4), Image.NEAREST)
    ziel = p.with_suffix('.png')
    gross.save(ziel)

    ges = len(px)
    print(f'Datei      : {p}')
    print(f'Raster     : {w} x {h} Zellen')
    print(f'frei       : {frei:6d}  ({100*frei/ges:5.1f} %)')
    print(f'belegt     : {belegt:6d}  ({100*belegt/ges:5.1f} %)')
    print(f'unbekannt  : {unbekannt:6d}  ({100*unbekannt/ges:5.1f} %)')
    print(f'bekannt ges: {frei+belegt:6d}')
    print(f'PNG        : {ziel}')

if __name__ == '__main__':
    main(sys.argv[1])
