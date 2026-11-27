"""Nummern im Foto und Kartenskizze."""
import io
import math

import numpy as np
from PIL import Image

from lotse.geometrie import Kamera, kamera_montage
from lotse.kandidaten import Oeffnung
from lotse.markierung import (als_jpeg, auseinander, marken_fuer_bild, markiere,
                              sichtbar_in, skizze, uebersicht)

KAMERA = Kamera.aus_oeffnungswinkel(640, 360, 69.0)


def oeffnung(nr, mitte, halbe_breite=0.4):
    """Öffnung quer zur Blickrichtung auf ihre Mitte."""
    mx, my = mitte
    laenge = math.hypot(mx, my)
    quer = (-my / laenge * halbe_breite, mx / laenge * halbe_breite)
    return Oeffnung(nr=nr, breite_m=2 * halbe_breite, mitte=mitte,
                    pfosten=((mx - quer[0], my - quer[1]), (mx + quer[0], my + quer[1])),
                    richtung_grad=math.degrees(math.atan2(my, mx)),
                    entfernung_m=laenge, tiefe_m=2.0, befahrbar=True)


def leeres_foto(farbe=(90, 90, 90)) -> bytes:
    puffer = io.BytesIO()
    Image.new('RGB', (640, 360), farbe).save(puffer, format='JPEG', quality=95)
    return puffer.getvalue()


def test_nummer_steht_im_bild_das_zur_oeffnung_schaut():
    vorn = oeffnung(1, (3.0, 0.0))
    marken = marken_fuer_bild([vorn], 0.0, kamera_montage(), KAMERA)
    assert len(marken) == 1
    marke = marken[0]
    assert marke['nr'] == 1 and not marke['am_rand']
    assert abs(marke['u'] - KAMERA.cx) < 1.0
    assert KAMERA.cy < marke['v'] < KAMERA.hoehe          # Boden, untere Bildhälfte
    (u1, _), (u2, _) = marke['pfosten_uv']
    assert u1 > marke['u'] > u2 or u1 < marke['u'] < u2   # Mitte zwischen den Pfosten


def test_nummer_fehlt_im_bild_das_wegschaut_und_im_nachbarbild_seitlich():
    links = oeffnung(1, (0.0, 3.0))
    assert marken_fuer_bild([links], 0.0, kamera_montage(), KAMERA) == []
    assert marken_fuer_bild([links], math.pi, kamera_montage(), KAMERA) == []
    schraeg = marken_fuer_bild([links], math.radians(70), kamera_montage(), KAMERA)
    assert len(schraeg) == 1
    assert schraeg[0]['u'] < KAMERA.cx                    # 20 Grad links der Bildmitte


def test_nahe_oeffnung_steht_am_unteren_bildrand():
    """Unter 1,6 m sieht die Kamera den Boden nicht mehr."""
    nah = oeffnung(1, (1.2, 0.0))
    marke = marken_fuer_bild([nah], 0.0, kamera_montage(), KAMERA)[0]
    assert marke['am_rand']
    assert marke['v'] <= KAMERA.hoehe - 1


def test_markiertes_foto_hat_scheibe_bildnamen_und_gleiche_groesse():
    marken = marken_fuer_bild([oeffnung(3, (3.0, 0.0))], 0.0, kamera_montage(), KAMERA)
    bild = markiere(leeres_foto(), marken, schild='B4')
    assert bild.size == (640, 360)
    pixel = np.asarray(bild)
    u, v = int(marken[0]['u']), int(marken[0]['v'])
    radius = 640 // 32
    # In der Scheibe überwiegt Weiß, am Bildnamen oben links Schwarz.
    scheibe = pixel[v - radius // 2:v + radius // 2, u - radius // 2:u + radius // 2]
    assert (scheibe.mean(axis=2) > 200).mean() > 0.45
    assert (scheibe.mean(axis=2) < 80).any()              # die Ziffer
    assert pixel[2, 2].mean() < 40
    unmarkiert = np.asarray(markiere(leeres_foto(), []))
    assert abs(float(unmarkiert.mean()) - 90.0) < 3.0


def test_skizze_zeigt_bild_eins_oben_und_die_nummer_an_ihrer_stelle():
    winkel = -math.pi + (np.arange(720) + 0.5) * (2 * math.pi / 720)
    entfernung = np.full(720, 2.0)
    vorn = oeffnung(1, (2.0, 0.0))
    bild = skizze(winkel, entfernung, [vorn], [0.0, math.pi / 2], groesse=400,
                  reichweite_m=4.0)
    assert bild.size == (400, 400)
    pixel = np.asarray(bild).mean(axis=2)
    massstab = (200 - 36) / 4.0
    oben = pixel[int(200 - 2.0 * massstab) - 4:int(200 - 2.0 * massstab) + 4, 196:204]
    assert (oben > 200).mean() > 0.3                      # weiße Scheibe vorn = oben
    # Messpunkte bilden einen Kreis mit 2 m Halbmesser: links der Mitte schwarz
    assert pixel[200, int(200 - 2.0 * massstab)] < 60
    # ohne Angabe richtet sich der Ausschnitt nach dem Raum
    assert skizze(winkel, entfernung, [vorn], [0.0]).size == (640, 640)


def test_uebersicht_legt_fotos_und_skizze_auf_ein_blatt():
    fotos = [Image.new('RGB', (640, 360), (i * 20, 0, 0)) for i in range(8)]
    blatt = uebersicht(fotos, Image.new('RGB', (640, 640), (255, 255, 255)))
    assert blatt.size == (3 * 640, 3 * 360)
    assert uebersicht([], Image.new('RGB', (64, 64))).size == (64, 64)
    assert Image.open(io.BytesIO(als_jpeg(blatt))).format == 'JPEG'


def test_uebersicht_vergroessert_kleine_fotos_und_laesst_keine_leere_spalte():
    """Am 21.11.2026 lieferte die Kamera 320 x 180; das Blatt war kaum zu erkennen."""
    klein = [Image.new('RGB', (320, 180), (0, 90, 0))]
    blatt = uebersicht(klein, Image.new('RGB', (640, 640), (255, 255, 255)))
    assert blatt.size == (2 * 640, 360)                   # Foto und Skizze nebeneinander
    assert blatt.getpixel((320, 180)) == (0, 90, 0)


def test_nummer_steht_auf_der_marke_wenn_die_mitte_verdeckt_ist():
    """Offenes Türblatt: Die Nummer gehört auf das sichtbare Stück der Schwelle."""
    import dataclasses
    mitte = oeffnung(1, (3.0, 0.0))
    versetzt = dataclasses.replace(mitte, marke=(3.0, 0.3))
    u_mitte = marken_fuer_bild([mitte], 0.0, kamera_montage(), KAMERA)[0]['u']
    marke = marken_fuer_bild([versetzt], 0.0, kamera_montage(), KAMERA)[0]
    assert marke['u'] < u_mitte - 20                      # 30 cm weiter links im Bild
    assert versetzt.marke_oder_mitte == (3.0, 0.3) and mitte.marke_oder_mitte == (3.0, 0.0)
    bild = skizze(np.array([0.0]), np.array([3.0]), [versetzt], [0.0], groesse=400)
    assert bild.size == (400, 400)


def test_sichtbar_in_fasst_je_nummer_die_bilder_zusammen():
    marken = {1: [{'nr': 2}], 2: [{'nr': 2}, {'nr': 5}], 3: []}
    assert sichtbar_in(marken) == {2: [1, 2], 5: [2]}


def test_ohne_schriftdatei_bleiben_die_nummern_lesbar(monkeypatch):
    """Auf einem Rechner ohne DejaVu-Schrift und mit alter Pillow-Fassung."""
    import lotse.markierung as markierung
    monkeypatch.setattr(markierung, '_schrift', lambda groesse: None)
    zahl = markierung._text_bild('7', 24)
    assert zahl.height >= 16 and np.asarray(zahl)[..., 3].max() > 150
    marken = marken_fuer_bild([oeffnung(7, (3.0, 0.0))], 0.0, kamera_montage(), KAMERA)
    pixel = np.asarray(markiere(leeres_foto(), marken, schild='B1')).mean(axis=2)
    u, v = int(marken[0]['u']), int(marken[0]['v'])
    scheibe = pixel[v - 10:v + 10, u - 10:u + 10]
    assert (scheibe > 200).mean() > 0.4 and (scheibe < 80).any()


def test_stellen_werden_auseinandergeschoben_bis_sich_nichts_mehr_deckt():
    neu = auseinander([(100.0, 50.0), (100.0, 50.0), (104.0, 52.0)], 44.0, (20, 20, 619, 339))
    for i in range(3):
        for j in range(i + 1, 3):
            assert math.hypot(neu[i][0] - neu[j][0], neu[i][1] - neu[j][1]) >= 44.0 - 1e-6
    assert neu[0][0] < neu[1][0]                    # die frühere weicht nach links
    # am Rand bleiben sie im Bild
    rand = auseinander([(615.0, 300.0), (617.0, 300.0)], 44.0, (20, 20, 619, 339))
    assert all(20 <= u <= 619 for u, _ in rand)
    assert abs(rand[0][0] - rand[1][0]) >= 44.0 - 1e-6
    # weit genug auseinander: nichts bewegt sich
    assert auseinander([(100.0, 50.0), (300.0, 50.0)], 44.0) == [(100.0, 50.0), (300.0, 50.0)]


def test_zwei_nummern_an_derselben_stelle_sind_beide_zu_sehen():
    """KI-F9, Lauf 2: zwei Nummern 4 bis 23 Bildpunkte auseinander; die zweite deckte die
    erste fast ganz zu. Hier liegen beide genau aufeinander."""
    marken = marken_fuer_bild([oeffnung(1, (2.6, 0.0)), oeffnung(2, (2.6, 0.0))], 0.0,
                              kamera_montage(), KAMERA)
    assert len(marken) == 2 and marken[0]['u'] == marken[1]['u']
    pixel = np.asarray(markiere(leeres_foto(), marken)).mean(axis=2)
    radius = 640 // 32
    u0 = marken[0]['u']
    v = int(round(min(max(marken[0]['v'], radius), 359 - radius)))
    for seite in (-1, 1):       # links und rechts je eine eigene Scheibe, weiter außen
        u = int(round(u0 + seite * 1.35 * radius))      # als eine Scheibe reicht
        flecken = pixel[v - radius // 3:v + radius // 3, u - radius // 3:u + radius // 3]
        assert (flecken > 200).mean() > 0.3, seite


def test_auseinander_am_bildrand_haelt_den_abstand():
    """Gegenprüfung Schritt 3: Wurde eine Stelle an den Rand zurückgeholt, prüfte
    die alte Fassung den Abstand danach nicht mehr (37 statt 44 Bildpunkte)."""
    neu = auseinander([(12.5, 200.0), (57.0, 200.0)], 44.0, (20.0, 20.0, 619.0, 339.0))
    assert math.dist(*neu) >= 44.0 - 0.01
    assert all(20.0 <= u <= 619.0 for u, _ in neu)
    # zwei Stellen jenseits des oberen Rands: nicht beide auf denselben Punkt
    neu = auseinander([(320.0, -10.0), (320.0, -60.0)], 44.0, (20.0, 18.0, 619.0, 339.0))
    assert math.dist(*neu) >= 44.0 - 0.01


def test_auseinander_behaelt_die_reihenfolge_einer_dichten_gruppe():
    """Gegenprüfung Schritt 3: Paarweise nacheinander geschoben, lasen sich drei
    Nummern auf einer Reihe „1 3 2“, und Scheibe 3 lag genau auf Stelle 2."""
    stellen = [(150.0, 90.0), (158.0, 90.0), (166.0, 90.0)]
    neu = auseinander(stellen, 24.2, (11.0, 11.0, 308.0, 168.0))
    assert [u for u, _ in neu] == sorted(u for u, _ in neu)
    assert min(math.dist(a, b) for i, a in enumerate(neu) for b in neu[i + 1:]) >= 24.2 - 0.01
