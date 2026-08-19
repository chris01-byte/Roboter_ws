#!/usr/bin/env python3
"""Vergleicht mehrere Belegungskarten anhand messbarer Merkmale.

Warum nicht nach Augenmass: Die Kennzahl "freie Flaeche" allein taeuscht - eine
verschmierte Karte, in der dieselbe Wand mehrfach versetzt liegt, meldet sogar
MEHR Freiflaeche. Aussagekraeftig sind stattdessen:

  Wanddicke   Wie viele Wandzellen ueberleben eine Erosion? Eine saubere Wand
              ist 1-2 Zellen duenn und verschwindet dabei fast vollstaendig.
              Verschmierte, mehrfach eingetragene Waende sind dick und bleiben
              stehen. DAS ist der eigentliche Verschmierungsindikator.
  Wand/frei   Verhaeltnis der Zellzahlen; steigt bei Mehrfacheintraegen.
  Geometrie   Ausdehnung entlang der Hauptachsen, gegen die realen Raummasse.

Aufruf:  python3 karten_vergleichen.py karte1.pgm karte2.pgm ...
"""
import sys
from pathlib import Path

import numpy as np
import yaml
from PIL import Image


def erodiere(maske):
    """Eine Zelle bleibt, wenn alle vier Nachbarn ebenfalls gesetzt sind."""
    m = maske
    e = np.zeros_like(m)
    e[1:-1, 1:-1] = (m[1:-1, 1:-1] & m[:-2, 1:-1] & m[2:, 1:-1]
                     & m[1:-1, :-2] & m[1:-1, 2:])
    return e


def auswerten(pfad):
    p = Path(pfad)
    meta = yaml.safe_load((p.with_suffix('.yaml')).read_text())
    r = float(meta['resolution'])
    a = np.array(Image.open(p).convert('L'))
    frei = a > 250
    belegt = a < 50
    nf, nb = int(frei.sum()), int(belegt.sum())

    dick = int(erodiere(belegt).sum())
    anteil_dick = dick / nb if nb else 0.0

    # Ausdehnung entlang der Hauptachsen der Wandpunkte
    pts = np.argwhere(belegt)
    if len(pts) > 20:
        xy = np.column_stack([pts[:, 1]*r, -pts[:, 0]*r])
        z = xy - xy.mean(axis=0)
        _, _, vt = np.linalg.svd(z, full_matrices=False)
        h = z @ vt[0]
        n = z @ vt[1]
        haupt = float(np.percentile(h, 98) - np.percentile(h, 2))
        neben = float(np.percentile(n, 98) - np.percentile(n, 2))
    else:
        haupt = neben = float('nan')

    return {
        'name': p.stem, 'res': r,
        'breite': a.shape[1]*r, 'hoehe': a.shape[0]*r,
        'frei_qm': nf*r*r, 'wand': nb,
        'verh': nb/nf if nf else 0.0,
        'dick': anteil_dick,
        'haupt': haupt, 'neben': neben,
    }


def main(pfade):
    ergebnisse = [auswerten(p) for p in pfade]
    print(f'{"Karte":<26} {"Aufl":>5} {"Ausdehnung":>13} {"frei":>8} '
          f'{"Wand":>6} {"W/frei":>7} {"dicke W.":>9}')
    print('-' * 82)
    for e in ergebnisse:
        print(f'{e["name"]:<26} {e["res"]*100:4.0f}cm '
              f'{e["breite"]:5.1f}x{e["hoehe"]:5.1f}m '
              f'{e["frei_qm"]:6.1f}qm {e["wand"]:6d} {e["verh"]:7.3f} '
              f'{e["dick"]*100:7.1f} %')
    print()
    print('Geometrie gegen die realen Raummasse 3.80 x 4.90 m:')
    for e in ergebnisse:
        print(f'  {e["name"]:<26} Hauptachse {e["haupt"]:5.2f} m | '
              f'Nebenachse {e["neben"]:5.2f} m')
    print()
    print('LESEHILFE')
    print('  "dicke W." = Anteil der Wandzellen, der eine Erosion ueberlebt.')
    print('    Nahe 0 %  = duenne, einfach eingetragene Waende (gut).')
    print('    Hoch      = dicke oder mehrfach versetzte Waende (verschmiert).')
    print('  Die freie Flaeche allein sagt WENIG aus: Verschmierte Karten')
    print('  melden oft mehr davon, weil derselbe Raum mehrfach drinsteht.')


if __name__ == '__main__':
    main(sys.argv[1:])
