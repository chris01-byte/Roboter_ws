#!/usr/bin/env python3
"""Karte gross rendern, mit 1-m-Gitter und Legende - zum Draufschauen."""
import sys
from pathlib import Path
from PIL import Image, ImageDraw

import yaml


def main(ordner):
    o = Path(ordner)
    meta = yaml.safe_load((o / 'map.yaml').read_text())
    aufloesung = float(meta['resolution'])          # m je Zelle
    img = Image.open(o / 'map.pgm').convert('L')
    w, h = img.size
    px = list(img.getdata())

    # 254 = frei, 0 = belegt, 205 = unbekannt
    fein = Image.new('RGB', (w, h))
    fein.putdata([(255, 255, 255) if v > 250 else
                  (25, 28, 40) if v < 50 else
                  (155, 165, 180) for v in px])

    faktor = max(4, int(700 / max(w, h)))
    gross = fein.resize((w * faktor, h * faktor), Image.NEAREST)
    d = ImageDraw.Draw(gross)

    # 1-m-Gitter
    schritt = aufloesung and (1.0 / aufloesung) * faktor
    if schritt:
        x = 0.0
        while x < gross.width:
            d.line([(x, 0), (x, gross.height)], fill=(230, 90, 90), width=1)
            x += schritt
        y = 0.0
        while y < gross.height:
            d.line([(0, y), (gross.width, y)], fill=(230, 90, 90), width=1)
            y += schritt

    breite_m = w * aufloesung
    hoehe_m = h * aufloesung
    frei = sum(1 for v in px if v > 250)
    belegt = sum(1 for v in px if v < 50)
    unbek = len(px) - frei - belegt

    # Fussleiste mit den Zahlen
    leiste = 74
    ganz = Image.new('RGB', (gross.width, gross.height + leiste), (245, 245, 248))
    ganz.paste(gross, (0, 0))
    d2 = ImageDraw.Draw(ganz)
    y0 = gross.height + 8
    d2.text((10, y0), f'Raum {breite_m:.1f} x {hoehe_m:.1f} m   '
                      f'Zelle {aufloesung*100:.0f} cm   Gitter = 1 m',
            fill=(20, 20, 20))
    d2.text((10, y0 + 20), f'weiss = frei {frei} Zellen ({frei*aufloesung**2:.1f} qm)   '
                           f'dunkel = belegt {belegt}   grau = unbekannt {unbek}',
            fill=(20, 20, 20))
    d2.text((10, y0 + 40), f'Quelle: {o.name}', fill=(90, 90, 90))

    ziel = o / 'karte_gross.png'
    ganz.save(ziel)
    print(f'{ziel}')
    print(f'Raum {breite_m:.2f} x {hoehe_m:.2f} m, frei {frei*aufloesung**2:.1f} qm')


if __name__ == '__main__':
    main(sys.argv[1])
