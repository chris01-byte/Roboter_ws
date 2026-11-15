#!/usr/bin/env python3
"""Engstelle (Tür) an einem Punkt vermessen: Karte oder Kostenkarte (nur lesend, ohne ROS).

Anlass (W-1, 15.11.2026): Amadeus blieb schräg in der 80-cm-Tür zwischen
Labor und Flur stehen; der globale Planer fand von dort keinen Weg mehr. Der
globale Planer rechnet den Roboter als Kreis (``robot_radius`` 0,28 m): Jede
Zelle näher als 0,28 m an einer belegten Zelle ist für ihn gesperrt. In einer
80-cm-Tür bleibt rechnerisch ein Streifen von rund 0,25 m. Dieses Werkzeug
misst an den gesicherten Dateien, wie es wirklich war:

  1. Wie breit ist die Engstelle am Punkt (lichte Weite zwischen den nächsten
     belegten Zellen der beiden Seiten)?
  2. Wie viel davon ist für den Planer frei? In einer Karte: Zellen weiter als
     der Planungsradius von jeder belegten Zelle. In einer Kostenkarte: Zellen
     mit Kostenwert unter 99 (99 = gesperrt, 100 = belegt).
  3. Wo lag der Punkt in der Engstelle, und wie weit ist die nächste für den
     Planer freie Zelle entfernt?
  4. Mit ``--gier``: Wie schräg stand der Roboter zur Durchfahrtsachse, wie viel
     Breite braucht seine Kontur bei diesem Schrägstand, und liegen belegte
     Zellen in der Kontur?

Eingabe ist genau eine der beiden:

  --karte KARTE.yaml     Karte von ``map_saver_cli`` (yaml und pgm)
  --kostenkarte DATEI    Textausgabe von
                         ``ros2 topic echo --once --full-length <…/costmap>``

Der Punkt (``--punkt X Y``) und die Blickrichtung (``--gier GRAD``) gelten im
Rahmen der Datei (Karte und globale Kostenkarte: ``map``). Mit ``--mitte``
gilt die Mitte des Gitters als Punkt (lokale Kostenkarte: dort steht der
Roboter). Die Ausgabe enthält keine Koordinaten der Karte, nur Abstände und
Lagen relativ zum Roboter. Das Werkzeug öffnet nur die Eingabedateien.
"""

import argparse
import json
import math
import re
import sys
from pathlib import Path

FREI, BELEGT, UNBEKANNT, GESPERRT = 0, 1, 2, 3
UMKREIS_M = 1.2                  # so weit um den Punkt wird gesucht
TIEFE_M = 0.45                   # so weit darf der Punkt neben der Linie der Engstelle liegen
PLANUNGSRADIUS_M = 0.28          # robot_radius der globalen Kostenkarte
KOSTEN_GESPERRT, KOSTEN_BELEGT = 99, 100
# Kontur wie in nav2_params_real.yaml (lokale Kostenkarte), Polster 2 cm.
VORN_M, HINTEN_M, HALBE_BREITE_M, POLSTER_M = 0.31, 0.11, 0.23, 0.02


class Eingabefehler(ValueError):
    """Die Datei lässt sich nicht als Karte oder Kostenkarte lesen."""


class Gitter:
    """Zellen mit Klasse (frei, belegt, unbekannt, gesperrt) und, bei Kostenkarten, Kostenwert."""

    def __init__(self, breite, hoehe, aufloesung, ursprung, klassen, art, werte=None):
        if len(klassen) != breite*hoehe:
            raise Eingabefehler(f'erwartet {breite*hoehe} Zellen, gefunden {len(klassen)}')
        self.breite, self.hoehe, self.aufloesung = breite, hoehe, aufloesung
        self.ursprung, self.klassen, self.art, self.werte = ursprung, klassen, art, werte

    def zelle(self, x, y):
        i = math.floor((x - self.ursprung[0])/self.aufloesung)
        j = math.floor((y - self.ursprung[1])/self.aufloesung)
        return (i, j) if 0 <= i < self.breite and 0 <= j < self.hoehe else None

    def mitte(self, i, j):
        return (self.ursprung[0] + (i + .5)*self.aufloesung,
                self.ursprung[1] + (j + .5)*self.aufloesung)

    def klasse(self, i, j):
        return self.klassen[j*self.breite + i]

    def wert(self, i, j):
        return None if self.werte is None else self.werte[j*self.breite + i]


def karte_laden(yaml_pfad):
    """Karte von map_saver: yaml mit pgm daneben. Zeile 0 des Bildes ist oben."""
    import yaml
    import karte_fuer_nav2_pruefen as kn
    yaml_pfad = Path(yaml_pfad)
    config = yaml.safe_load(yaml_pfad.read_text(encoding='utf-8'))
    if not isinstance(config, dict) or 'image' not in config:
        raise Eingabefehler('yaml ohne image')
    bild = Path(config['image'])
    if not bild.is_absolute():
        bild = yaml_pfad.parent/bild
    ursprung = config.get('origin') or [0.0, 0.0, 0.0]
    if len(ursprung) > 2 and abs(float(ursprung[2])) > 1e-6:
        raise Eingabefehler('gedrehter Kartenursprung wird nicht unterstützt')
    belegt_ab = float(config.get('occupied_thresh', 0.65))
    frei_bis = float(config.get('free_thresh', 0.25))
    negiert = bool(config.get('negate', 0))
    breite, hoehe, maxval, pixel = kn.read_pgm(bild)
    marke = round(205*maxval/255)          # map_saver schreibt Unbekanntes als 205
    klassen = [UNBEKANNT]*(breite*hoehe)
    for zeile in range(hoehe):
        j = hoehe - 1 - zeile
        for i in range(breite):
            p = pixel[zeile*breite + i]
            belegung = p/maxval if negiert else (maxval - p)/maxval
            klassen[j*breite + i] = (UNBEKANNT if p == marke else BELEGT if belegung > belegt_ab
                                     else FREI if belegung < frei_bis else UNBEKANNT)
    return Gitter(breite, hoehe, float(config['resolution']),
                  (float(ursprung[0]), float(ursprung[1])), klassen, 'karte')


GANZZAHL = re.compile(r'-?\d+')


def kostenkarte_lesen(text):
    """Textausgabe von ``ros2 topic echo --once --full-length`` einer OccupancyGrid."""
    kopf, daten = {}, []
    daten_art, in_ursprung, in_position = None, False, False
    for roh in text.splitlines():
        zeile = roh.strip()
        if '...' in zeile and (daten_art is not None or zeile.startswith('data:')):
            raise Eingabefehler('Daten gekürzt („...“): ohne --full-length gesichert')
        if daten_art == 'block':
            if zeile.startswith('- '):
                daten.append(int(zeile[2:]))
                continue
            if not zeile:
                continue
            daten_art = None
        elif daten_art == 'fluss':
            daten += [int(z) for z in GANZZAHL.findall(zeile)]
            if ']' in zeile:
                daten_art = None
            continue
        if zeile.startswith('data:'):
            rest = zeile[len('data:'):].strip()
            if rest.startswith('['):
                daten += [int(z) for z in GANZZAHL.findall(rest)]
                daten_art = None if ']' in rest else 'fluss'
            else:
                daten_art = 'block'
            continue
        if zeile.startswith('origin:'):
            in_ursprung, in_position = True, False
            continue
        if in_ursprung and zeile.startswith('position:'):
            in_position = True
            continue
        if in_ursprung and zeile.startswith('orientation:'):
            in_ursprung = in_position = False
            continue
        try:
            for name in ('resolution', 'width', 'height'):
                if zeile.startswith(name + ':') and name not in kopf:
                    kopf[name] = float(zeile.split(':', 1)[1])
            if in_position:
                for achse in ('x', 'y'):
                    if zeile.startswith(achse + ':') and achse not in kopf:
                        kopf[achse] = float(zeile.split(':', 1)[1])
        except ValueError as fehler:
            raise Eingabefehler(f'Kopfzeile nicht lesbar: {zeile[:60]}') from fehler
    fehlend = [n for n in ('resolution', 'width', 'height', 'x', 'y') if n not in kopf]
    if fehlend:
        raise Eingabefehler(f'Kopf unvollständig, es fehlt: {", ".join(fehlend)}')
    breite, hoehe = int(kopf['width']), int(kopf['height'])
    if len(daten) != breite*hoehe:
        raise Eingabefehler(f'erwartet {breite*hoehe} Zellen, gefunden {len(daten)}')
    klassen = [UNBEKANNT if w < 0 else BELEGT if w >= KOSTEN_BELEGT
               else GESPERRT if w >= KOSTEN_GESPERRT else FREI for w in daten]
    return Gitter(breite, hoehe, kopf['resolution'], (kopf['x'], kopf['y']), klassen,
                  'kostenkarte', daten)


def belegte_im_umkreis(gitter, punkt, umkreis_m):
    i0, j0 = gitter.zelle(*punkt)
    n = int(math.ceil(umkreis_m/gitter.aufloesung))
    zellen = []
    for j in range(max(0, j0 - n), min(gitter.hoehe, j0 + n + 1)):
        for i in range(max(0, i0 - n), min(gitter.breite, i0 + n + 1)):
            if gitter.klasse(i, j) == BELEGT and math.dist(gitter.mitte(i, j), punkt) <= umkreis_m:
                zellen.append((i, j))
    return zellen


def gruppen(zellen):
    """Zusammenhängende Gruppen belegter Zellen (auch über Eck)."""
    offen, ergebnis = set(zellen), []
    while offen:
        start = offen.pop()
        gruppe, rand = [start], [start]
        while rand:
            i, j = rand.pop()
            for di in (-1, 0, 1):
                for dj in (-1, 0, 1):
                    nachbar = (i + di, j + dj)
                    if nachbar in offen:
                        offen.remove(nachbar)
                        gruppe.append(nachbar)
                        rand.append(nachbar)
        ergebnis.append(gruppe)
    return sorted(ergebnis, key=len, reverse=True)


def engstellen(gitter, punkt, zellgruppen, tiefe_m):
    """Je Gruppenpaar die engste Verbindung, zwischen deren Enden der Punkt liegt."""
    mitten = [[gitter.mitte(i, j) for i, j in g] for g in zellgruppen]
    funde = []
    for a in range(len(mitten)):
        for b in range(a + 1, len(mitten)):
            beste = None
            for pa in mitten[a]:
                for pb in mitten[b]:
                    weite = math.dist(pa, pb)
                    if beste is not None and weite >= beste['weite']:
                        continue
                    ex, ey = (pb[0] - pa[0])/weite, (pb[1] - pa[1])/weite
                    laengs = (punkt[0] - pa[0])*ex + (punkt[1] - pa[1])*ey
                    quer = -(punkt[0] - pa[0])*ey + (punkt[1] - pa[1])*ex
                    if 0.0 < laengs < weite and abs(quer) <= tiefe_m:
                        beste = dict(weite=weite, a=pa, b=pb, laengs=laengs, quer=quer,
                                     gruppen=(len(mitten[a]), len(mitten[b])))
            if beste is not None:
                funde.append(beste)
    return sorted(funde, key=lambda f: f['weite'])


def abstand_zur_naechsten_belegten(punkt, belegte_mitten):
    return min((math.dist(punkt, m) for m in belegte_mitten), default=math.inf)


def planer_gesperrt(gitter, i, j, belegte_mitten, radius_m):
    """Ob der Planer die Zelle meidet; in Karten nach Abstand, in Kostenkarten nach Kostenwert."""
    klasse = gitter.klasse(i, j)
    if klasse == BELEGT:
        return True
    if gitter.art == 'kostenkarte':
        return klasse == GESPERRT
    return abstand_zur_naechsten_belegten(gitter.mitte(i, j), belegte_mitten) <= radius_m


def streifen(gitter, engstelle, belegte_mitten, radius_m):
    """Längster zusammenhängender, für den Planer freier Abschnitt der Linie."""
    a, b, weite = engstelle['a'], engstelle['b'], engstelle['weite']
    schritte = max(1, int(math.ceil(weite/(gitter.aufloesung/4))))
    laengste = aktuell = 0
    werte, unbekannt, gesehen = [], 0, set()
    for k in range(schritte + 1):
        punkt = (a[0] + (b[0] - a[0])*k/schritte, a[1] + (b[1] - a[1])*k/schritte)
        zelle = gitter.zelle(*punkt)
        gesperrt = zelle is None or planer_gesperrt(gitter, *zelle, belegte_mitten, radius_m)
        aktuell = 0 if gesperrt else aktuell + 1
        laengste = max(laengste, aktuell)
        if zelle is not None and zelle not in gesehen:
            gesehen.add(zelle)
            if gitter.klasse(*zelle) == UNBEKANNT:
                unbekannt += 1
            if gitter.werte is not None and gitter.wert(*zelle) >= 0:
                werte.append(gitter.wert(*zelle))
    return dict(frei_m=round(laengste*weite/schritte, 2), unbekannte_zellen=unbekannt,
                kleinster_kostenwert=min(werte) if werte else None)


def naechste_freie_zelle(gitter, punkt, belegte_mitten, radius_m, umkreis_m):
    """Abstand vom Punkt zur Mitte der nächsten Zelle, die der Planer benutzen darf (0 = eigene Zelle)."""
    i0, j0 = gitter.zelle(*punkt)
    if not planer_gesperrt(gitter, i0, j0, belegte_mitten, radius_m):
        return 0.0                                   # die eigene Zelle ist frei
    n = int(math.ceil(umkreis_m/gitter.aufloesung))
    beste = None
    for j in range(max(0, j0 - n), min(gitter.hoehe, j0 + n + 1)):
        for i in range(max(0, i0 - n), min(gitter.breite, i0 + n + 1)):
            if gitter.klasse(i, j) in (BELEGT, GESPERRT):
                continue
            d = math.dist(gitter.mitte(i, j), punkt)
            if (beste is None or d < beste) and d <= umkreis_m \
                    and not planer_gesperrt(gitter, i, j, belegte_mitten, radius_m):
                beste = d
    return None if beste is None else round(beste, 2)


def kontur_lage(punkt, gier_rad, belegte_mitten, vorn, hinten, halb, polster):
    """Belegte Zellen relativ zur Kontur des Roboters (Zellmitten, Roboterkoordinaten)."""
    c, s = math.cos(gier_rad), math.sin(gier_rad)
    innen_gepolstert = innen = 0
    naechste = None
    for mx, my in belegte_mitten:
        dx, dy = mx - punkt[0], my - punkt[1]
        x, y = c*dx + s*dy, -s*dx + c*dy                       # vor dem Roboter, links von ihm
        if -hinten <= x <= vorn and abs(y) <= halb:
            innen += 1
        ausserhalb_x = max(-(hinten + polster) - x, 0.0, x - (vorn + polster))
        ausserhalb_y = max(abs(y) - (halb + polster), 0.0)
        abstand = math.hypot(ausserhalb_x, ausserhalb_y)
        if abstand == 0.0:
            innen_gepolstert += 1
        if naechste is None or abstand < naechste[0] or (
                abstand == naechste[0] == 0.0 and math.hypot(x, y) < math.hypot(*naechste[1:])):
            naechste = (abstand, x, y)
    if naechste is None:
        return None
    _, x, y = naechste
    seite = ('vorn' if x > vorn/2 else 'hinten' if x < -hinten/2 else 'seitlich') + ' ' + \
            ('links' if y > 0 else 'rechts')
    return dict(belegte_in_gepolsterter_kontur=innen_gepolstert, belegte_in_kontur=innen,
                naechste_belegte=dict(abstand_zur_gepolsterten_kontur_m=round(naechste[0], 2),
                                      vor_dem_roboter_m=round(x, 2), links_vom_roboter_m=round(y, 2),
                                      seite=seite))


def auswerten(gitter, punkt, gier_grad=None, umkreis_m=UMKREIS_M, tiefe_m=TIEFE_M,
              radius_m=PLANUNGSRADIUS_M, vorn=VORN_M, hinten=HINTEN_M, halb=HALBE_BREITE_M,
              polster=POLSTER_M):
    zelle = gitter.zelle(*punkt)
    if zelle is None:
        raise Eingabefehler('der Punkt liegt außerhalb des Gitters')
    belegte = belegte_im_umkreis(gitter, punkt, umkreis_m)
    # Für den Abstand zählen auch belegte Zellen knapp außerhalb des Umkreises.
    belegte_mitten = [gitter.mitte(i, j) for i, j in
                      belegte_im_umkreis(gitter, punkt, umkreis_m + radius_m + gitter.aufloesung)]
    zellgruppen = gruppen(belegte)
    funde = engstellen(gitter, punkt, zellgruppen, tiefe_m)
    namen = {FREI: 'frei', BELEGT: 'belegt', UNBEKANNT: 'unbekannt', GESPERRT: 'gesperrt'}
    naechste_belegte = abstand_zur_naechsten_belegten(punkt, belegte_mitten)
    ergebnis = dict(
        quelle=gitter.art, aufloesung_m=round(gitter.aufloesung, 4),
        umkreis_m=umkreis_m, planungsradius_m=radius_m if gitter.art == 'karte' else None,
        belegte_zellen_im_umkreis=len(belegte), gruppen=[len(g) for g in zellgruppen],
        punkt=dict(
            klasse=namen[gitter.klasse(*zelle)], kostenwert=gitter.wert(*zelle),
            naechste_belegte_zelle_m=(None if math.isinf(naechste_belegte)
                                      else round(naechste_belegte, 2)),
            fuer_planer_gesperrt=planer_gesperrt(gitter, *zelle, belegte_mitten, radius_m),
            naechste_fuer_planer_freie_zelle_m=naechste_freie_zelle(
                gitter, punkt, belegte_mitten, radius_m, umkreis_m)),
        engstelle=None, weitere_engstellen=[], lage=None)
    if funde:
        erste = funde[0]
        lichte = erste['weite'] - gitter.aufloesung
        ergebnis['engstelle'] = dict(
            lichte_weite_m=round(lichte, 2), zellmitten_m=round(erste['weite'], 2),
            gruppen=list(erste['gruppen']),
            punkt_neben_der_mitte_m=round(abs(erste['laengs'] - erste['weite']/2), 2),
            punkt_neben_der_linie_m=round(abs(erste['quer']), 2),
            rechnerisch_frei_m=(round(max(0.0, erste['weite'] - 2*radius_m), 2)
                                if gitter.art == 'karte' else None),
            **streifen(gitter, erste, belegte_mitten, radius_m))
        ergebnis['weitere_engstellen'] = [
            dict(lichte_weite_m=round(f['weite'] - gitter.aufloesung, 2), gruppen=list(f['gruppen']))
            for f in funde[1:3]]
    if gier_grad is not None:
        gier = math.radians(gier_grad)
        lage = kontur_lage(punkt, gier, belegte_mitten, vorn, hinten, halb, polster) or {}
        if funde:
            erste = funde[0]
            ex, ey = ((erste['b'][0] - erste['a'][0])/erste['weite'],
                      (erste['b'][1] - erste['a'][1])/erste['weite'])
            # Durchfahrtsachse steht senkrecht auf der Linie der Engstelle.
            schraeg = math.degrees(math.asin(min(1.0, abs(math.cos(gier)*ex + math.sin(gier)*ey))))
            laenge, breite = vorn + hinten + 2*polster, 2*(halb + polster)
            winkel = math.radians(schraeg)
            braucht = laenge*math.sin(winkel) + breite*math.cos(winkel)
            lage.update(schraegstand_grad=round(schraeg, 1),
                        gepolsterte_kontur_braucht_m=round(braucht, 2),
                        gerade_braucht_m=round(breite, 2),
                        rest_bei_diesem_schraegstand_m=round(
                            erste['weite'] - gitter.aufloesung - braucht, 2))
        ergebnis['lage'] = lage
    return ergebnis


def text(e):
    kosten = e['quelle'] == 'kostenkarte'
    aus = [f"Quelle: {'Kostenkarte' if kosten else 'Karte'}, Auflösung {e['aufloesung_m']} m; "
           f"belegte Zellen im Umkreis {e['umkreis_m']} m: {e['belegte_zellen_im_umkreis']} "
           f"in {len(e['gruppen'])} Gruppen (Größen {e['gruppen'][:8]})"]
    p = e['punkt']
    aus.append(f"Punkt: {p['klasse']}"
               + (f", Kostenwert {p['kostenwert']}" if kosten else '')
               + f"; nächste belegte Zelle {p['naechste_belegte_zelle_m']} m; für den Planer "
               + ('gesperrt' if p['fuer_planer_gesperrt'] else 'frei')
               + f"; nächste für den Planer freie Zelle {p['naechste_fuer_planer_freie_zelle_m']} m")
    g = e['engstelle']
    if g is None:
        aus.append('Engstelle am Punkt: keine gefunden (keine zwei getrennten Seiten um den Punkt)')
    else:
        aus.append(f"Engstelle am Punkt: lichte Weite {g['lichte_weite_m']} m (Zellmitten "
                   f"{g['zellmitten_m']} m) zwischen Gruppen mit {g['gruppen'][0]} und "
                   f"{g['gruppen'][1]} Zellen")
        aus.append(f"  Punkt {g['punkt_neben_der_mitte_m']} m neben der Mitte der Engstelle, "
                   f"{g['punkt_neben_der_linie_m']} m vor oder hinter ihrer Linie")
        if kosten:
            aus.append(f"  Für den Planer frei (Kostenwert unter 99): {g['frei_m']} m der Linie; "
                       f"kleinster Kostenwert auf der Linie {g['kleinster_kostenwert']}; "
                       f"unbekannte Zellen auf der Linie {g['unbekannte_zellen']}")
        else:
            aus.append(f"  Für den Planer frei (weiter als {e['planungsradius_m']} m von jeder "
                       f"belegten Zelle): {g['frei_m']} m der Linie; rechnerisch "
                       f"{g['rechnerisch_frei_m']} m; unbekannte Zellen auf der Linie "
                       f"{g['unbekannte_zellen']}")
        for w in e['weitere_engstellen']:
            aus.append(f"  Weitere Engstelle am Punkt: {w['lichte_weite_m']} m (Gruppen "
                       f"{w['gruppen'][0]} und {w['gruppen'][1]} Zellen)")
    lage = e['lage']
    if lage:
        if 'schraegstand_grad' in lage:
            aus.append(f"Lage: Schrägstand zur Durchfahrtsachse {lage['schraegstand_grad']}°; die "
                       f"gepolsterte Kontur braucht dabei {lage['gepolsterte_kontur_braucht_m']} m "
                       f"(gerade {lage['gerade_braucht_m']} m); Rest "
                       f"{lage['rest_bei_diesem_schraegstand_m']} m")
        if 'naechste_belegte' in lage:
            n = lage['naechste_belegte']
            aus.append(f"Kontur: {lage['belegte_in_gepolsterter_kontur']} belegte Zellen in der "
                       f"gepolsterten Kontur, {lage['belegte_in_kontur']} in der Kontur ohne Polster; "
                       f"nächste belegte Zelle {n['abstand_zur_gepolsterten_kontur_m']} m von der "
                       f"gepolsterten Kontur, {n['vor_dem_roboter_m']} m vor und "
                       f"{n['links_vom_roboter_m']} m links vom Roboter ({n['seite']})")
    return '\n'.join(aus)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    quelle = parser.add_mutually_exclusive_group(required=True)
    quelle.add_argument('--karte', help='yaml einer Karte von map_saver_cli')
    quelle.add_argument('--kostenkarte', help='Textausgabe von ros2 topic echo --full-length')
    ort = parser.add_mutually_exclusive_group(required=True)
    ort.add_argument('--punkt', nargs=2, type=float, metavar=('X', 'Y'),
                     help='Standort im Rahmen der Datei; bleibt lokal')
    ort.add_argument('--mitte', action='store_true',
                     help='Mitte des Gitters als Standort (lokale Kostenkarte)')
    parser.add_argument('--gier', type=float, metavar='GRAD',
                        help='Blickrichtung des Roboters im Rahmen der Datei')
    parser.add_argument('--radius', type=float, default=PLANUNGSRADIUS_M,
                        help='Planungsradius für Karten (Standard 0,28 m)')
    parser.add_argument('--umkreis', type=float, default=UMKREIS_M)
    parser.add_argument('--json', help='Ergebnis zusätzlich als JSON (lokal, nicht ins Repo)')
    args = parser.parse_args(argv)
    try:
        if args.karte:
            gitter = karte_laden(args.karte)
        else:
            with open(args.kostenkarte, 'r', encoding='utf-8', errors='replace') as handle:
                gitter = kostenkarte_lesen(handle.read())
        punkt = (tuple(args.punkt) if args.punkt else
                 (gitter.ursprung[0] + gitter.breite*gitter.aufloesung/2,
                  gitter.ursprung[1] + gitter.hoehe*gitter.aufloesung/2))
        ergebnis = auswerten(gitter, punkt, args.gier, umkreis_m=args.umkreis, radius_m=args.radius)
    except (Eingabefehler, OSError, ValueError) as fehler:
        print(f'FEHLER: {fehler}', file=sys.stderr)
        return 2
    print(text(ergebnis))
    if args.json:
        with open(args.json, 'w', encoding='utf-8') as handle:
            json.dump(ergebnis, handle, ensure_ascii=False, indent=2)
    return 0


if __name__ == '__main__':
    sys.exit(main())
