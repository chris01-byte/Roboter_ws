"""Nummern ins Foto zeichnen und die Kartenskizze bauen.

Bild-Sprach-Modelle sind unzuverlässig bei Meterangaben, aber gut darin,
zwischen markierten Stellen zu wählen. Deshalb bekommt jede vermessene
Öffnung eine Nummer: als weiße Scheibe am Boden der Öffnung im Foto und an
derselben Stelle in einer Skizze von oben.
"""
from __future__ import annotations

import io
import math
from typing import Dict, List, Optional, Sequence

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from .geometrie import Kamera, standpunkt_nach_kamera
from .kandidaten import Oeffnung

_SCHRIFTEN = (
    'DejaVuSans-Bold.ttf',
    '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
    '/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf',
    'LiberationSans-Bold.ttf',
)


def _schrift(groesse: int):
    for name in _SCHRIFTEN:
        try:
            return ImageFont.truetype(name, groesse)
        except OSError:
            continue
    try:                                  # Pillow ab 10.1: skalierbare Vorgabe
        return ImageFont.load_default(size=groesse)
    except TypeError:
        return None


def _text_bild(text: str, hoehe: int, farbe=(0, 0, 0)) -> Image.Image:
    """Text als freigestelltes Bild der Höhe ``hoehe`` (ohne feste Schriftdatei)."""
    schrift = _schrift(hoehe)
    if schrift is not None:
        kasten = schrift.getbbox(text)
        bild = Image.new('RGBA', (kasten[2] - kasten[0] + 2, kasten[3] - kasten[1] + 2),
                         (0, 0, 0, 0))
        ImageDraw.Draw(bild).text((1 - kasten[0], 1 - kasten[1]), text,
                                  font=schrift, fill=farbe + (255,))
        return bild
    klein = ImageFont.load_default()      # alte Pillow-Fassung: Rasterschrift
    kasten = ImageDraw.Draw(Image.new('RGBA', (1, 1))).textbbox((0, 0), text, font=klein)
    bild = Image.new('RGBA', (kasten[2] + 2, kasten[3] + 2), (0, 0, 0, 0))
    ImageDraw.Draw(bild).text((1, 1), text, font=klein, fill=farbe + (255,))
    faktor = max(1, int(round(hoehe / max(1, kasten[3]))))
    return bild.resize((bild.width * faktor, bild.height * faktor), Image.NEAREST)


def _scheibe(bild: Image.Image, u: float, v: float, nr: int, radius: int) -> None:
    """Weiße Scheibe mit schwarzem Rand und schwarzer Zahl."""
    zeichner = ImageDraw.Draw(bild)
    zeichner.ellipse([u - radius, v - radius, u + radius, v + radius],
                     fill=(255, 255, 255), outline=(0, 0, 0),
                     width=max(2, radius // 6))
    zahl = _text_bild(str(nr), int(radius * 1.25))
    bild.paste(zahl, (int(round(u - zahl.width / 2)), int(round(v - zahl.height / 2))), zahl)


def _schild(bild: Image.Image, text: str, hoehe: int) -> None:
    """Bildname oben links (zum Beispiel „B3“), damit die KI Bilder benennen kann."""
    schrift = _text_bild(text, hoehe, farbe=(255, 255, 255))
    rand = max(2, hoehe // 4)
    ImageDraw.Draw(bild).rectangle(
        [0, 0, schrift.width + 2 * rand, schrift.height + 2 * rand], fill=(0, 0, 0))
    bild.paste(schrift, (rand, rand), schrift)


def marken_fuer_bild(oeffnungen: Sequence[Oeffnung], gier_rad: float,
                     boden_kamera: np.ndarray, kamera: Kamera,
                     rand_px: int = 12) -> List[dict]:
    """Wo die Nummern in einem Foto stehen, das bei ``gier_rad`` entstand.

    Eine Öffnung zählt als „im Bild“, wenn die Bodenmitte zwischen ihren
    Pfosten waagerecht im Bild liegt. Liegt sie unterhalb des Bildes (nahe
    Öffnung, die Kamera sieht den Boden erst ab etwa 1,6 m), wird die Nummer
    an den unteren Bildrand gesetzt und als ``am_rand`` vermerkt.
    """
    marken = []
    for o in oeffnungen:
        punkte = np.array([[o.mitte[0], o.mitte[1], 0.0],
                           [o.pfosten[0][0], o.pfosten[0][1], 0.0],
                           [o.pfosten[1][0], o.pfosten[1][1], 0.0]])
        im_kamerarahmen = standpunkt_nach_kamera(punkte, gier_rad, boden_kamera)
        uv, vorn = kamera.projiziere(im_kamerarahmen)
        u, v = float(uv[0, 0]), float(uv[0, 1])
        if not vorn[0]:
            # Bodenmitte außerhalb des Bildkegels: Liegt sie nur unterhalb des
            # Bildes (nahe Öffnung), zählt die Spalte der idealen Abbildung.
            ideal, davor = kamera.projiziere_ideal(im_kamerarahmen[:1])
            u, v = float(ideal[0, 0]), float(ideal[0, 1])
            if not davor[0] or v <= kamera.hoehe - 1:
                continue
        if not (rand_px <= u <= kamera.breite - 1 - rand_px):
            continue
        am_rand = v > kamera.hoehe - 1 - rand_px
        marken.append({
            'nr': o.nr, 'u': u,
            'v': min(max(v, rand_px), kamera.hoehe - 1 - rand_px),
            'am_rand': bool(am_rand),
            'pfosten_uv': ([[float(uv[1, 0]), float(uv[1, 1])],
                            [float(uv[2, 0]), float(uv[2, 1])]]
                           if vorn[1] and vorn[2] else None),
        })
    return marken


def markiere(bild_bytes: bytes, marken: Sequence[dict],
             schild: Optional[str] = None) -> Image.Image:
    """Ein Foto mit Nummern und Bildname versehen."""
    bild = Image.open(io.BytesIO(bild_bytes)).convert('RGB')
    radius = max(11, bild.width // 32)
    zeichner = ImageDraw.Draw(bild)
    for marke in marken:
        if marke.get('pfosten_uv'):
            (u1, v1), (u2, v2) = marke['pfosten_uv']
            zeichner.line([u1, v1, u2, v2], fill=(0, 0, 0), width=max(5, radius // 3))
            zeichner.line([u1, v1, u2, v2], fill=(255, 255, 255), width=max(2, radius // 6))
    for marke in marken:
        v = min(marke['v'], bild.height - 1 - radius)
        _scheibe(bild, marke['u'], max(v, radius), marke['nr'], radius)
    if schild:
        _schild(bild, schild, max(14, bild.height // 14))
    return bild


def skizze(winkel_rad, entfernung_m, oeffnungen: Sequence[Oeffnung],
           bildrichtungen_rad: Sequence[float], groesse: int = 640,
           reichweite_m: Optional[float] = None) -> Image.Image:
    """Kartenskizze von oben: Roboter in der Mitte, Blick von Bild 1 nach oben.

    Ohne Angabe richtet sich der Ausschnitt nach dem Raum (zwischen 2,5 und
    6 m Halbmesser), damit ein kleines Zimmer das Blatt füllt.
    """
    bild = Image.new('RGB', (groesse, groesse), (255, 255, 255))
    zeichner = ImageDraw.Draw(bild)
    mitte = groesse / 2.0
    rand = groesse * 0.09
    if reichweite_m is None:
        gemessen = np.asarray(entfernung_m, dtype=float)
        gemessen = gemessen[np.isfinite(gemessen)]
        weit = float(np.percentile(gemessen, 97)) if gemessen.size else 4.0
        for o in oeffnungen:
            weit = max(weit, o.entfernung_m + 0.5 * o.breite_m)
        reichweite_m = min(6.0, max(2.5, 1.15 * weit))
    massstab = (mitte - rand) / reichweite_m

    def px(x: float, y: float):
        return (mitte - y * massstab, mitte - x * massstab)

    for meter in range(1, int(math.ceil(reichweite_m)) + 1):   # Entfernungsringe
        r = meter * massstab
        zeichner.ellipse([mitte - r, mitte - r, mitte + r, mitte + r],
                         outline=(215, 215, 215))
    w = np.asarray(winkel_rad, dtype=float)
    r = np.asarray(entfernung_m, dtype=float)
    ok = np.isfinite(r) & (r <= reichweite_m)
    dick = max(1, groesse // 320)
    for x, y in zip(r[ok] * np.cos(w[ok]), r[ok] * np.sin(w[ok])):
        u, v = px(x, y)
        zeichner.rectangle([u - dick, v - dick, u + dick, v + dick], fill=(0, 0, 0))
    aussen = mitte - rand * 0.45
    for j, richtung in enumerate(bildrichtungen_rad):       # Blickrichtungen
        x, y = math.cos(richtung), math.sin(richtung)
        u, v = mitte - y * aussen, mitte - x * aussen
        name = _text_bild(f'B{j + 1}', max(11, groesse // 36), farbe=(90, 90, 90))
        bild.paste(name, (int(u - name.width / 2), int(v - name.height / 2)), name)
    spitze, links, rechts = px(0.35, 0.0), px(-0.2, 0.2), px(-0.2, -0.2)
    zeichner.polygon([spitze, links, rechts], fill=(120, 120, 120), outline=(0, 0, 0))
    radius = max(11, groesse // 34)
    for o in oeffnungen:
        zeichner.line([px(*o.pfosten[0]), px(*o.pfosten[1])], fill=(0, 0, 0),
                      width=max(3, groesse // 160))
    for o in oeffnungen:
        u, v = px(*o.mitte)
        _scheibe(bild, u, v, o.nr, radius)
    return bild


def als_jpeg(bild: Image.Image, guete: int = 88) -> bytes:
    puffer = io.BytesIO()
    bild.convert('RGB').save(puffer, format='JPEG', quality=guete)
    return puffer.getvalue()


def uebersicht(bilder: Sequence[Image.Image], skizze_bild: Image.Image,
               spalten: int = 3) -> Image.Image:
    """Alle Fotos und die Skizze auf einem Blatt (für den Menschen)."""
    if not bilder:
        return skizze_bild.copy()
    breite, hoehe = bilder[0].size
    felder = list(bilder) + [skizze_bild.resize(
        (int(skizze_bild.width * hoehe / skizze_bild.height), hoehe), Image.BILINEAR)]
    zeilen = math.ceil(len(felder) / spalten)
    blatt = Image.new('RGB', (spalten * breite, zeilen * hoehe), (255, 255, 255))
    for i, feld in enumerate(felder):
        x = (i % spalten) * breite + (breite - feld.width) // 2
        blatt.paste(feld, (x, (i // spalten) * hoehe))
    return blatt


def sichtbar_in(marken_je_bild: Dict[int, Sequence[dict]]) -> Dict[int, List[int]]:
    """Je Nummer die Bilder, in denen sie eingezeichnet ist."""
    ergebnis: Dict[int, List[int]] = {}
    for bild_nr in sorted(marken_je_bild):
        for marke in marken_je_bild[bild_nr]:
            ergebnis.setdefault(int(marke['nr']), []).append(int(bild_nr))
    return ergebnis
