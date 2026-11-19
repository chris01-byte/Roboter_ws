#!/usr/bin/env python3
"""Eine künstliche Blickrunde erzeugen (kein echtes Bild, keine echte Wohnung).

Zweck: den Trockenlauf ohne Roboter und ohne Wohnungsdaten ausprobieren und
testen. Die Welt ist ein ausgedachtes Zimmer mit einer 80-cm-Tür zum Flur,
einer Glastür zum Balkon, zwei Schränken mit einer Lücke dazwischen und
einer Kiste. Der Roboter dreht
sich auf der Stelle; das LiDAR sitzt wie am echten Amadeus 0,245 m vor der
Antriebsmitte und sieht den Mastsektor nicht. Die „Fotos“ sind einfache
gezeichnete Ansichten, damit man sieht, ob die Nummern an der richtigen
Stelle landen.

Aufruf:
    python3 beispielrunde_erzeugen.py --ausgabe /tmp/ki_beispiel
"""
from __future__ import annotations

import argparse
import io
import math
import sys
from pathlib import Path
from typing import List, Sequence, Tuple

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lotse.blickrunde import scan_als_dict, schreibe_runde  # noqa: E402
from lotse.geometrie import (Kamera, drehung_z, invertiere,  # noqa: E402
                             kamera_montage, lidar_montage, transformiere)

Strecke = Tuple[float, float, float, float]

# Tür in der Ostwand des Zimmers: x = 4,0, von y = 1,0 bis 1,8 (80 cm)
TUER = ((4.0, 1.0), (4.0, 1.8))
# Lücke zwischen zwei Schränken an der Nordwand: 70 cm breit, 50 cm tief.
# Das Gehäuse passt nicht hinein; die Vermessung zählt sie deshalb nicht als
# Öffnung (verlangt sind im Mittel 0,6 m freie Tiefe).
SPALT = ((1.2, 2.9), (1.9, 2.9))
# Glastür in der Südwand (y = 0), 90 cm breit, dahinter ein Balkon. Das LiDAR
# schaut durch das Glas und misst eine Öffnung; nur das Bild zeigt die Scheibe.
GLASTUER = ((1.0, 0.0), (1.9, 0.0))
STANDPUNKT = (1.8, 1.5, math.radians(90.0))      # x, y, Blickrichtung


def _kasten(x1: float, y1: float, x2: float, y2: float) -> List[Strecke]:
    return [(x1, y1, x2, y1), (x2, y1, x2, y2), (x2, y2, x1, y2), (x1, y2, x1, y1)]


def welt() -> List[dict]:
    """Flächen der Welt: Strecke am Boden, Höhe und Farbe."""
    flaechen = []

    def wand(strecke: Strecke, hoehe: float = 2.4, farbe=(205, 205, 200),
             glas: bool = False):
        flaechen.append({'strecke': strecke, 'hoehe': hoehe, 'farbe': farbe,
                         'glas': glas})

    # Zimmer 4,0 x 3,4 m; Ostwand mit Türöffnung, Südwand mit Glastür
    wand((0.0, 0.0, GLASTUER[0][0], 0.0))
    wand((GLASTUER[1][0], 0.0, 4.0, 0.0))
    wand((GLASTUER[0][0], 0.0, GLASTUER[1][0], 0.0), hoehe=2.0,
         farbe=(170, 215, 235), glas=True)
    # Balkon hinter der Glastür: 1,2 m tief, Brüstung 1,0 m hoch
    for strecke in ((0.6, 0.0, 0.6, -1.2), (0.6, -1.2, 2.3, -1.2), (2.3, -1.2, 2.3, 0.0)):
        wand(strecke, hoehe=1.0, farbe=(160, 160, 165))
    wand((0.0, 3.4, 4.0, 3.4))
    wand((0.0, 0.0, 0.0, 3.4))
    wand((4.0, 0.0, 4.0, TUER[0][1]))
    wand((4.0, TUER[1][1], 4.0, 3.4))
    # Flur östlich davon, 1,3 m breit
    wand((4.0, -1.0, 4.0, 0.0), farbe=(190, 195, 200))
    wand((4.0, 3.4, 4.0, 5.0), farbe=(190, 195, 200))
    wand((5.3, -1.0, 5.3, 5.0), farbe=(190, 195, 200))
    wand((4.0, -1.0, 5.3, -1.0), farbe=(190, 195, 200))
    wand((4.0, 5.0, 5.3, 5.0), farbe=(190, 195, 200))
    # Zwei Schränke an der Nordwand mit Lücke, eine Kiste an der Westwand
    for strecke in _kasten(0.3, SPALT[0][1], SPALT[0][0], 3.4):
        wand(strecke, hoehe=1.9, farbe=(150, 110, 70))
    for strecke in _kasten(SPALT[1][0], SPALT[0][1], 2.8, 3.4):
        wand(strecke, hoehe=1.9, farbe=(150, 110, 70))
    for strecke in _kasten(0.0, 0.6, 0.5, 1.2):
        wand(strecke, hoehe=0.9, farbe=(90, 110, 150))
    return flaechen


def _strahlen(ursprung: np.ndarray, richtungen: np.ndarray,
              strecken: np.ndarray) -> np.ndarray:
    """Entfernung je Strahl bis zur ersten Strecke (inf = kein Treffer)."""
    p = strecken[:, :2] - ursprung                  # (M, 2)
    e = strecken[:, 2:] - strecken[:, :2]           # (M, 2)
    d = richtungen[:, None, :]                      # (N, 1, 2)
    nenner = d[..., 0] * e[None, :, 1] - d[..., 1] * e[None, :, 0]
    with np.errstate(divide='ignore', invalid='ignore'):
        t = (p[None, :, 0] * e[None, :, 1] - p[None, :, 1] * e[None, :, 0]) / nenner
        s = (p[None, :, 0] * d[..., 1] - p[None, :, 1] * d[..., 0]) / nenner
    gut = (np.abs(nenner) > 1e-12) & (t > 1e-6) & (s >= 0.0) & (s <= 1.0)
    return np.where(gut, t, np.inf).min(axis=1)


def scan(flaechen: Sequence[dict], x: float, y: float, gier: float, t: float,
         rauschen_m: float = 0.01, strahlen: int = 720,
         zufall: np.random.Generator = None) -> dict:
    """Ein LiDAR-Scan in der Welt; der Mastsektor fehlt wie am echten Gerät."""
    zufall = zufall or np.random.default_rng(0)
    boden_lidar = lidar_montage()
    ursprung = np.array([x, y]) + drehung_z(gier)[:2, :2] @ boden_lidar[:2, 3]
    lidar_gier = gier + math.atan2(boden_lidar[1, 0], boden_lidar[0, 0])
    schritt = 2 * math.pi / strahlen
    winkel = -math.pi + schritt * np.arange(strahlen)
    richtungen = np.column_stack([np.cos(winkel + lidar_gier),
                                  np.sin(winkel + lidar_gier)])
    # Das LiDAR sitzt 0,75 m hoch: Flächen darunter sieht es nicht. Durch
    # Glas schaut es hindurch.
    strecken = np.array([f['strecke'] for f in flaechen
                         if f['hoehe'] >= 0.75 and not f.get('glas')])
    r = _strahlen(ursprung, richtungen, strecken)
    r = r + zufall.normal(0.0, rauschen_m, size=r.shape)
    # Mast: hinten am Roboter, im LiDAR-Rahmen um 90 Grad, 68 Grad breit
    mast = np.abs(((winkel - math.pi / 2 + math.pi) % (2 * math.pi)) - math.pi) < math.radians(34)
    r[mast] = np.nan
    return scan_als_dict(float(winkel[0]), schritt, r, 0.03, 25.0, t)


def _beschneide_vorn(ecken: np.ndarray, nah: float = 0.12) -> np.ndarray:
    """Vieleck im Kamerarahmen an der Ebene z = nah beschneiden."""
    ergebnis = []
    for i in range(len(ecken)):
        a, b = ecken[i], ecken[(i + 1) % len(ecken)]
        innen_a, innen_b = a[2] >= nah, b[2] >= nah
        if innen_a:
            ergebnis.append(a)
        if innen_a != innen_b:
            anteil = (nah - a[2]) / (b[2] - a[2])
            ergebnis.append(a + anteil * (b - a))
    return np.array(ergebnis)


def foto(flaechen: Sequence[dict], kamera: Kamera, x: float, y: float,
         gier: float) -> bytes:
    """Eine gezeichnete Ansicht der Welt aus Sicht der Kamera."""
    welt_boden = np.eye(4)                      # Bodenrahmen des Roboters in der Welt
    welt_boden[:3, :3] = drehung_z(gier)
    welt_boden[:3, 3] = [x, y, 0.0]
    kamera_welt = invertiere(welt_boden @ kamera_montage())
    bild = Image.new('RGB', (kamera.breite, kamera.hoehe), (120, 125, 130))
    zeichner = ImageDraw.Draw(bild)
    # Boden: alles unter dem Horizont
    horizont = kamera.cy - kamera.fy * math.tan(0.3306)
    zeichner.rectangle([0, max(0, horizont), kamera.breite, kamera.hoehe],
                       fill=(196, 178, 150))
    stand = np.array([x, y])
    ordnung = sorted(flaechen, key=lambda f: -np.hypot(
        (f['strecke'][0] + f['strecke'][2]) / 2 - stand[0],
        (f['strecke'][1] + f['strecke'][3]) / 2 - stand[1]))
    for flaeche in ordnung:
        x1, y1, x2, y2 = flaeche['strecke']
        ecken = np.array([[x1, y1, 0.0], [x2, y2, 0.0],
                          [x2, y2, flaeche['hoehe']], [x1, y1, flaeche['hoehe']]])
        sicht = _beschneide_vorn(transformiere(kamera_welt, ecken))
        if len(sicht) < 3:
            continue
        punkte = [(kamera.fx * p[0] / p[2] + kamera.cx,
                   kamera.fy * p[1] / p[2] + kamera.cy) for p in sicht]
        if flaeche.get('glas'):
            # Scheibe: nur Rahmen und Spiegelstriche, das Dahinter bleibt sichtbar
            zeichner.polygon(punkte, outline=flaeche['farbe'])
            zeichner.line(punkte + [punkte[0]], fill=flaeche['farbe'], width=4)
            zeichner.line([punkte[0], punkte[2 % len(punkte)]],
                          fill=flaeche['farbe'], width=2)
            continue
        # leichte Schattierung nach Wandrichtung, damit Ecken erkennbar sind
        hell = 0.85 + 0.15 * abs(math.cos(math.atan2(y2 - y1, x2 - x1)))
        farbe = tuple(int(c * hell) for c in flaeche['farbe'])
        zeichner.polygon(punkte, fill=farbe, outline=(70, 70, 70))
    puffer = io.BytesIO()
    bild.save(puffer, format='JPEG', quality=85)
    return puffer.getvalue()


def erzeuge(ausgabe, name: str = 'beispiel_zimmer', schritt_grad: float = 5.0,
            gesamt_grad: float = 365.0, drehsinn: int = 1, saat: int = 1,
            mit_odometrie: bool = False,
            standpunkt: Tuple[float, float, float] = STANDPUNKT) -> Path:
    """Die künstliche Blickrunde in ``ausgabe/name`` schreiben."""
    zufall = np.random.default_rng(saat)
    flaechen = welt()
    kamera = Kamera.aus_oeffnungswinkel(640, 360, 69.0)
    x, y, gier0 = standpunkt
    bilder, scans, zeiten, odometrie = [], [], [], []
    for k in range(int(gesamt_grad / schritt_grad) + 1):
        gier = gier0 + drehsinn * math.radians(k * schritt_grad)
        t = 1000.0 + 0.5 * k
        bilder.append(foto(flaechen, kamera, x, y, gier))
        scans.append(scan(flaechen, x, y, gier, t, zufall=zufall))
        zeiten.append(t)
        odometrie.append(gier - gier0 + zufall.normal(0.0, 0.01))
    return schreibe_runde(
        Path(ausgabe) / name, name, kamera, bilder, scans, zeiten,
        gier_odom=odometrie if mit_odometrie else None,
        boden_kamera=kamera_montage(), boden_lidar=lidar_montage(),
        montage_quelle='kuenstlich',
        quelle={'art': 'kuenstliche Beispielwelt, keine echte Wohnung'},
        bemerkung='Künstliche Blickrunde zum Ausprobieren des Trockenlaufs.')


def tuer_im_standpunktrahmen(standpunkt: Tuple[float, float, float] = STANDPUNKT):
    """Mitte von Tür, Schranklücke und Glastür im Standpunktrahmen (für Tests)."""
    x, y, gier = standpunkt
    zurueck = drehung_z(-gier)[:2, :2]

    def mitte(strecke):
        m = (np.array(strecke[0]) + np.array(strecke[1])) / 2.0
        return zurueck @ (m - np.array([x, y]))

    return mitte(TUER), mitte(SPALT), mitte(GLASTUER)


def main(argv=None) -> int:
    eingabe = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    eingabe.add_argument('--ausgabe', required=True,
                         help='Zielordner; die Runde entsteht als Unterordner')
    eingabe.add_argument('--name', default='beispiel_zimmer')
    eingabe.add_argument('--schritt-grad', type=float, default=5.0)
    eingabe.add_argument('--rechtsherum', action='store_true',
                         help='im Uhrzeigersinn drehen')
    eingabe.add_argument('--mit-odometrie', action='store_true')
    wahl = eingabe.parse_args(argv)
    ordner = erzeuge(wahl.ausgabe, wahl.name, wahl.schritt_grad,
                     drehsinn=-1 if wahl.rechtsherum else 1,
                     mit_odometrie=wahl.mit_odometrie)
    print(f'Künstliche Blickrunde geschrieben: {ordner}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
