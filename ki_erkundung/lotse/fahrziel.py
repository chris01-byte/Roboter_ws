"""Fahrziel: aus einer gewählten Öffnung die Punkte für die Etappenfahrt.

Die KI nennt nur eine Nummer. Aus der dazu vermessenen Öffnung rechnet der
Roboter hier selbst, wohin er fährt, in zwei Schritten:

- **Anfahrt** (``anfahrt``): vom Standplatz im Raum vor die Tür, über einen
  Vorpunkt auf der Türachse; danach steht er mittig davor, Blick zur Tür.
- **Durchfahrt** (``gerade_linie``): von dort auf gerader Linie durch die
  Türmitte, neu vermessen.

Jeder Weg wird vor dem Senden an dem geprüft, was der Laser sieht. Der
Erkunder fährt die Punkte in kurzen geraden Etappen an (Anschlussstelle
``stage_drive_only``), prüft vor jeder Etappe den Streifen vor sich und
behält seine ganze Schutzkette.

Dieses Modul rechnet nur; es sendet nichts und kennt kein ROS.
"""
from __future__ import annotations

import json
import math
from typing import List, Optional, Sequence, Tuple

import numpy as np

Punkt = Tuple[float, float]

QUELLEN = ('ki', 'mensch', 'test')

# Grenzen wie im Erkunder (src/explore/explore/stage_drive.py, StageLimits).
# Hier nur, damit ein zu weites Ziel schon vor dem Senden mit Maß auffällt;
# geprüft wird im Erkunder ohnehin noch einmal.
MAX_PUNKTE = 3
MIN_STRECKE_M = 0.10
MAX_STRECKE_M = 2.5
MAX_GESAMT_M = 4.0

# Antriebsmitte bis Vorderkante 0,27 m (mit Polster 0,33 m), bis Hinterkante
# 0,11 m, halbe Breite 0,23 m. Gefahren wird auf einer geraden Linie vom
# Standplatz durch die Türmitte. Ein Zwischenpunkt liegt 1,2 m vor der
# Türlinie auf dieser Linie; dort stellt der Erkunder die Richtung nach,
# bevor er an Türblatt und Pfosten vorbeifährt. Am Auslaufpunkt ist die
# Hinterkante knapp einen halben Meter durch.
VOR_DER_TUER_M = 1.20
HINTER_DER_TUER_M = 0.60
MIN_BREITE_M = 0.60
# So viel muss links und rechts der Fahrlinie frei sein, gemessen am Laser:
# halbe Gehäusebreite und 7 cm. Der Erkunder hält an, wenn in seinem
# Streifen von 0,255 m etwas liegt; dazu bleiben 4,5 cm Abstand.
FREI_NEBEN_DER_LINIE_M = 0.30
VORDERKANTE_M = 0.33
# So schräg zur Türachse darf die Fahrlinie höchstens durch die Tür gehen.
MAX_SCHRAEG_GRAD = 10.0
# Als Tür gilt für eine Durchfahrt nur, was so breit vermessen ist. Breiter
# vermessene „Türen“ sind falsch vermessen (Befund KI-F1: 1,25 m statt
# 0,85 m bei schrägem Blick); ihre Achse stimmt dann nicht.
TUER_MIN_M = 0.65
TUER_MAX_M = 0.95


def tuer_punkte(pfosten: Sequence[Sequence[float]],
                standpunkt: Sequence[float] = (0.0, 0.0), *,
                vor_m: float = 1.10,
                hinter_m: float = HINTER_DER_TUER_M,
                min_breite_m: float = MIN_BREITE_M) -> Tuple[Punkt, Punkt]:
    """Vorpunkt und Auslaufpunkt auf der Achse einer Öffnung.

    ``pfosten``: die zwei Kanten der Öffnung; ``standpunkt``: wo der Roboter
    steht (derselbe Rahmen). Die Achse steht senkrecht auf der Verbindung der
    Pfosten und zeigt vom Standpunkt weg durch die Öffnung.
    """
    (ax, ay), (bx, by) = [(float(p[0]), float(p[1])) for p in pfosten]
    sx, sy = float(standpunkt[0]), float(standpunkt[1])
    werte = (ax, ay, bx, by, sx, sy, vor_m, hinter_m)
    if not all(math.isfinite(w) for w in werte) or vor_m <= 0.0 or hinter_m <= 0.0:
        raise ValueError('Fahrziel: Maße müssen endlich und positiv sein')
    breite = math.hypot(bx - ax, by - ay)
    if breite < min_breite_m:
        raise ValueError(
            f'Fahrziel: Öffnung {breite:.2f} m breit, nötig {min_breite_m:.2f} m')
    mx, my = 0.5 * (ax + bx), 0.5 * (ay + by)
    nx, ny = -(by - ay) / breite, (bx - ax) / breite
    seite = (sx - mx) * nx + (sy - my) * ny
    if abs(seite) < 0.05:
        raise ValueError('Fahrziel: Der Standpunkt liegt in der Türlinie')
    if seite > 0.0:                     # die Achse soll vom Standpunkt weg zeigen
        nx, ny = -nx, -ny
    return ((mx - vor_m * nx, my - vor_m * ny),
            (mx + hinter_m * nx, my + hinter_m * ny))


def aufstellung(pfosten: Sequence[Sequence[float]],
                standpunkt: Sequence[float] = (0.0, 0.0),
                blick_rad: float = 0.0) -> dict:
    """Wie der Roboter zur Tür steht.

    ``abstand_m``: bis zur Türlinie, entlang der Türachse.
    ``seitlich_m``: Versatz neben der Türachse; positiv = der Roboter steht
    links der Achse (mit Blick zur Tür).
    ``winkel_grad``: Richtung der Türachse gegen die Blickrichtung; positiv =
    die Achse liegt links, der Roboter müsste sich nach links drehen.
    """
    (ax, ay), (bx, by) = [(float(p[0]), float(p[1])) for p in pfosten]
    sx, sy = float(standpunkt[0]), float(standpunkt[1])
    breite = math.hypot(bx - ax, by - ay)
    if not math.isfinite(breite) or breite <= 0.0:
        raise ValueError('Fahrziel: Pfosten fallen zusammen')
    mx, my = 0.5 * (ax + bx), 0.5 * (ay + by)
    nx, ny = -(by - ay) / breite, (bx - ax) / breite
    if (sx - mx) * nx + (sy - my) * ny > 0.0:      # Achse zeigt vom Standpunkt weg
        nx, ny = -nx, -ny
    abstand = (mx - sx) * nx + (my - sy) * ny
    seitlich = (sx - mx) * (-ny) + (sy - my) * nx
    winkel = math.degrees(math.atan2(math.sin(math.atan2(ny, nx) - blick_rad),
                                     math.cos(math.atan2(ny, nx) - blick_rad)))
    return {'breite_m': breite, 'abstand_m': abstand, 'seitlich_m': seitlich,
            'winkel_grad': winkel}


def aufstellung_hinweise(lage: dict, *, abstand_min_m: float = 1.5,
                         abstand_max_m: float = 2.6, seitlich_max_m: float = 0.25,
                         winkel_max_grad: float = 25.0) -> List[str]:
    """Was an der Aufstellung zu ändern ist; leere Liste = sie passt."""
    hinweise = []
    abstand, seitlich, winkel = lage['abstand_m'], lage['seitlich_m'], lage['winkel_grad']
    if abstand < abstand_min_m:
        hinweise.append(
            f'zu nah an der Tür ({abstand:.2f} m bis zur Türlinie): bitte auf '
            f'{abstand_min_m:.1f} bis {abstand_max_m:.1f} m zurückstellen')
    elif abstand > abstand_max_m:
        hinweise.append(
            f'zu weit von der Tür ({abstand:.2f} m bis zur Türlinie): bitte auf '
            f'{abstand_min_m:.1f} bis {abstand_max_m:.1f} m heranstellen')
    if abs(seitlich) > seitlich_max_m:
        hinweise.append(
            f'steht {abs(seitlich):.2f} m {"links" if seitlich > 0 else "rechts"} neben '
            f'der Türmitte: bitte etwa {100 * abs(seitlich):.0f} cm nach '
            f'{"rechts" if seitlich > 0 else "links"} versetzen')
    if abs(winkel) > winkel_max_grad:
        hinweise.append(
            f'die Tür liegt {abs(winkel):.0f}° {"links" if winkel > 0 else "rechts"} '
            f'von seiner Blickrichtung: bitte nach '
            f'{"links" if winkel > 0 else "rechts"} zur Tür drehen')
    return hinweise


def im_kartenrahmen(punkt: Sequence[float], pose: Sequence[float]) -> Punkt:
    """Punkt aus dem Standpunktrahmen in den Kartenrahmen (Pose x, y, Gier)."""
    x, y, gier = (float(v) for v in pose)
    c, s = math.cos(gier), math.sin(gier)
    return (x + c * float(punkt[0]) - s * float(punkt[1]),
            y + s * float(punkt[0]) + c * float(punkt[1]))


def geradeaus(strecke_m: float, pose: Sequence[float]) -> List[Punkt]:
    """Ein einzelner Punkt genau voraus, im Kartenrahmen."""
    if not math.isfinite(strecke_m) or not MIN_STRECKE_M <= strecke_m <= MAX_STRECKE_M:
        raise ValueError(
            f'Fahrziel: Strecke {strecke_m} m außerhalb von '
            f'{MIN_STRECKE_M} bis {MAX_STRECKE_M} m')
    return [im_kartenrahmen((strecke_m, 0.0), pose)]


def punkt_relativ(voraus_m: float, links_m: float, pose: Sequence[float]) -> List[Punkt]:
    """Ein einzelner Punkt, vom Roboter aus gesehen (voraus, links), im Kartenrahmen."""
    strecke = math.hypot(voraus_m, links_m)
    if not math.isfinite(strecke) or not MIN_STRECKE_M <= strecke <= MAX_STRECKE_M:
        raise ValueError(
            f'Fahrziel: Punkt {strecke:.2f} m entfernt, erlaubt '
            f'{MIN_STRECKE_M} bis {MAX_STRECKE_M} m')
    if voraus_m <= 0.0:
        raise ValueError('Fahrziel: Der Punkt muss vor dem Roboter liegen')
    return [im_kartenrahmen((voraus_m, links_m), pose)]


def gerade_linie(pfosten: Sequence[Sequence[float]], *,
                 vor_m: float = VOR_DER_TUER_M, hinter_m: float = HINTER_DER_TUER_M,
                 max_schraeg_grad: float = MAX_SCHRAEG_GRAD,
                 min_anlauf_m: float = 0.40) -> List[Punkt]:
    """Fahrpunkte auf der geraden Linie vom Standplatz durch die Türmitte.

    Im Standpunktrahmen (Antriebsmitte im Ursprung, x voraus, y links). Der
    letzte Punkt liegt ``hinter_m`` hinter der Türlinie, der Zwischenpunkt
    ``vor_m`` davor (beides quer zur Türlinie gemessen); er entfällt, wenn
    bis dorthin weniger als ``min_anlauf_m`` zu fahren wäre.

    Warum eine gerade Linie und kein Vorpunkt auf der Türachse: In KI-F2
    (22.11.2026) fuhr der Roboter erst schräg zur Achse und wollte sich
    dort drehen; die schräge Strecke führte 1,5 cm an der Spitze des
    offenen Türblatts vorbei. Die gerade Linie hält dort 39 cm Abstand.
    """
    lage = aufstellung(pfosten)
    (ax, ay), (bx, by) = [(float(q[0]), float(q[1])) for q in pfosten]
    mx, my = 0.5 * (ax + bx), 0.5 * (ay + by)
    strecke = math.hypot(mx, my)
    if lage['breite_m'] < MIN_BREITE_M:
        raise ValueError(
            f'Fahrziel: Öffnung {lage["breite_m"]:.2f} m breit, nötig {MIN_BREITE_M:.2f} m')
    if strecke < 0.3 or lage['abstand_m'] <= 0.05:
        raise ValueError('Fahrziel: Der Standpunkt liegt in der Türlinie')
    kosinus = lage['abstand_m'] / strecke
    schraeg = math.degrees(math.acos(max(-1.0, min(1.0, kosinus))))
    if schraeg > max_schraeg_grad:
        raise ValueError(
            f'Fahrziel: Die gerade Linie ginge {schraeg:.0f}° schräg durch die Tür, '
            f'erlaubt {max_schraeg_grad:.0f}°')
    ux, uy = mx / strecke, my / strecke
    punkte = []
    bis_vor = (lage['abstand_m'] - vor_m) / kosinus
    if bis_vor >= min_anlauf_m:
        punkte.append((bis_vor * ux, bis_vor * uy))
    bis_ende = strecke + hinter_m / kosinus
    punkte.append((bis_ende * ux, bis_ende * uy))
    return punkte


def gerade_durch_die_tuer(pfosten: Sequence[Sequence[float]], pose: Sequence[float],
                          **optionen) -> List[Punkt]:
    """Wie ``gerade_linie``, im Kartenrahmen (``pose`` der Antriebsmitte)."""
    return [im_kartenrahmen(q, pose) for q in gerade_linie(pfosten, **optionen)]


def freiraum(hindernisse: Sequence[Sequence[float]], ziel: Sequence[float], *,
             start: Sequence[float] = (0.0, 0.0), vorn_m: float = VORDERKANTE_M,
             nah_m: float = 0.15) -> dict:
    """Wie viel neben der Fahrlinie frei ist, links und rechts.

    ``hindernisse``: Punkte, die der Laser sieht (derselbe Rahmen wie
    ``start`` und ``ziel``). Betrachtet wird die Strecke vom Start bis
    ``vorn_m`` hinter das Ziel (so weit reicht die Vorderkante). Rückgabe je
    Seite der kleinste Abstand eines Punkts von der Linie und wo er liegt
    (Meter voraus); ``inf``, wenn auf der Seite nichts liegt.
    """
    sx, sy = float(start[0]), float(start[1])
    dx, dy = float(ziel[0]) - sx, float(ziel[1]) - sy
    laenge = math.hypot(dx, dy)
    if not math.isfinite(laenge) or laenge < 0.05:
        raise ValueError('Fahrziel: Start und Ziel fallen zusammen')
    ux, uy = dx / laenge, dy / laenge
    frei = {'links_m': math.inf, 'links_voraus_m': None,
            'rechts_m': math.inf, 'rechts_voraus_m': None, 'laenge_m': laenge}
    for punkt in hindernisse:
        px, py = float(punkt[0]) - sx, float(punkt[1]) - sy
        if not (math.isfinite(px) and math.isfinite(py)):
            continue
        voraus = px * ux + py * uy
        if not nah_m < voraus < laenge + vorn_m:
            continue
        seitlich = -px * uy + py * ux
        seite = 'links' if seitlich >= 0.0 else 'rechts'
        if abs(seitlich) < frei[f'{seite}_m']:
            frei[f'{seite}_m'] = abs(seitlich)
            frei[f'{seite}_voraus_m'] = voraus
    return frei


def freiraum_hinweise(frei: dict, *, noetig_m: float = FREI_NEBEN_DER_LINIE_M) -> List[str]:
    """Was zu ändern ist, damit neben der Fahrlinie genug frei ist; leer = reicht."""
    hinweise = []
    for seite, weg_von in (('links', 'rechts'), ('rechts', 'links')):
        abstand, voraus = frei[f'{seite}_m'], frei[f'{seite}_voraus_m']
        if abstand >= noetig_m:
            continue
        # Den Standplatz quer versetzen dreht die Linie um die Türmitte; an
        # einer Stelle ``voraus`` wirkt davon nur der Anteil bis zur Tür.
        anteil = 1.0 - voraus / frei['laenge_m']
        fehlt = noetig_m - abstand
        text = (f'{seite} neben der Fahrlinie sind nur {abstand:.2f} m frei '
                f'({voraus:.1f} m voraus), nötig {noetig_m:.2f} m')
        if anteil > 0.25 and fehlt / anteil <= 0.60:
            versatz = 5 * math.ceil(100 * fehlt / anteil / 5)
            text += f': bitte etwa {versatz} cm nach {weg_von} versetzen'
        else:
            text += ': von hier ist die Durchfahrt zu knapp'
        hinweise.append(text)
    return hinweise


# Anfahrt: Der Roboter stellt sich selbst vor die Tür. Er fährt zu einem
# Vorpunkt auf der Türachse, dreht sich dort zur Tür und fährt ein kurzes
# Stück auf sie zu. Danach steht er so, wie ihn sonst ein Mensch hinstellt
# (``aufstellung_hinweise``), und die Durchfahrt wird von dort neu vermessen.
# Endpunkt so weit vor der Türlinie (die Aufstellung passt bei 1,5 bis 2,6 m;
# der Erkunder kommt auf 0,10 m genau an):
ANFAHRT_VOR_M = (1.6, 1.7, 1.8, 1.9, 2.0, 2.1)
# Der Vorpunkt liegt so viel weiter von der Tür weg. Mehr als 0,35 m, damit
# der Erkunder sich dort zur Tür ausrichtet.
ANFAHRT_ANLAUF_M = 0.45
# Zum Drehen auf der Stelle: Die vorderen Ecken kreisen 0,40 m um die
# Antriebsmitte (0,33 m voraus, 0,23 m seitlich); dazu 5 cm.
DREHKREIS_M = 0.45
MIN_ANLAUF_M = 0.40


def frei_gesehen(sicht: Optional[dict], punkt: Sequence[float], *,
                 spiel_m: float = 0.05) -> bool:
    """Ob der Laser bis zu diesem Punkt freie Sicht hatte.

    ``sicht``: ``{'ursprung': (x, y), 'winkel': …, 'profil': …}`` aus der
    Vermessung im Stand (je Richtung die Entfernung; ``nan`` = nicht
    beobachtet, ``inf`` = kein Echo). Liegt vor dem Punkt etwas, oder hat der
    Laser in diese Richtung nicht gemessen, ist der Punkt nicht „frei
    gesehen“: Was dahinter liegt, kennt der Roboter von hier nicht.
    Ohne ``sicht`` wird nichts geprüft.
    """
    if sicht is None:
        return True
    winkel = np.asarray(sicht['winkel'], dtype=float)
    profil = np.asarray(sicht['profil'], dtype=float)
    dx = float(punkt[0]) - float(sicht['ursprung'][0])
    dy = float(punkt[1]) - float(sicht['ursprung'][1])
    strecke = math.hypot(dx, dy)
    if strecke < 0.15:
        return True
    unterschied = np.abs((winkel - math.atan2(dy, dx) + math.pi) % (2 * math.pi) - math.pi)
    weite = float(profil[int(np.argmin(unterschied))])
    if math.isnan(weite):
        return False
    return weite >= strecke - spiel_m


def frei_um(hindernisse: Sequence[Sequence[float]], punkt: Sequence[float]) -> float:
    """Abstand des nächsten Laserpunkts von ``punkt``; ``inf`` ohne Punkte."""
    feld = np.asarray(hindernisse, dtype=float).reshape(-1, 2)
    if feld.size == 0:
        return math.inf
    return float(np.min(np.hypot(feld[:, 0] - float(punkt[0]), feld[:, 1] - float(punkt[1]))))


def _winkel(rad: float) -> float:
    return math.degrees(math.atan2(math.sin(rad), math.cos(rad)))


def wandrichtung(pfosten: Sequence[Sequence[float]], hindernisse: Sequence[Sequence[float]], *,
                 band_m: float = 0.30, bis_m: float = 1.5, spiel_m: float = 0.03,
                 min_punkte: int = 12, min_laenge_m: float = 0.40,
                 max_abweichung_grad: float = 20.0) -> Optional[dict]:
    """Die Richtung der Wand, in der die Tür sitzt, aus den Laserpunkten daneben.

    Warum: Schräg gesehen liegen die zwei vermessenen Türkanten nicht auf
    einer Linie mit der Wand. Die nahe Kante ist die raumseitige Ecke des
    Pfostens, die ferne die hintere Ecke der Laibung oder ein Punkt auf dem
    offenen Türblatt. Die Verbindung der Kanten ist dann um einige Grad
    verdreht (Simulation, 22.11.2026: 6°), und ein Punkt 1,6 m vor der Tür
    auf dieser „Achse“ liegt 17 cm neben der wahren. Die Wand neben der Tür
    ist dagegen ein langes gerades Stück.

    Gesucht wird je Seite der Tür die gerade Linie mit den meisten
    Laserpunkten (höchstens ``spiel_m`` daneben), die höchstens
    ``max_abweichung_grad`` von der Verbindung der Türkanten abweicht.
    Rückgabe ``{'richtung': (x, y), 'punkte': n, 'laenge_m': …}`` für die
    bessere Seite oder ``None``, wenn neben der Tür keine gerade Wand
    gesehen wird.
    """
    (ax, ay), (bx, by) = [(float(q[0]), float(q[1])) for q in pfosten]
    breite = math.hypot(bx - ax, by - ay)
    feld = np.asarray(hindernisse, dtype=float).reshape(-1, 2)
    if breite <= 0.0 or feld.shape[0] < min_punkte:
        return None
    u = np.array([(bx - ax) / breite, (by - ay) / breite])
    quer = np.array([-u[1], u[0]])
    mitte = np.array([0.5 * (ax + bx), 0.5 * (ay + by)])
    rel = feld - mitte
    laengs, tief = rel @ u, rel @ quer
    grenze = math.cos(math.radians(max_abweichung_grad))
    beste = None
    for seite in (-1.0, 1.0):
        maske = ((np.abs(tief) <= band_m) & (seite * laengs >= 0.5 * breite + 0.03)
                 & (seite * laengs <= 0.5 * breite + bis_m))
        punkte = feld[maske]
        if punkte.shape[0] < min_punkte:
            continue
        fund = None
        for i in range(punkte.shape[0] - 1):
            differenz = punkte[i + 1:] - punkte[i]
            weite = np.hypot(differenz[:, 0], differenz[:, 1])
            for j in np.flatnonzero(weite >= 0.25):
                richtung = differenz[j] / weite[j]
                if abs(float(richtung @ u)) < grenze:
                    continue
                abstand = np.abs((punkte - punkte[i]) @ np.array([-richtung[1], richtung[0]]))
                zahl = int(np.count_nonzero(abstand <= spiel_m))
                if fund is None or zahl > fund[0]:
                    fund = (zahl, abstand <= spiel_m)
        if fund is None or fund[0] < min_punkte:
            continue
        drin = punkte[fund[1]]
        schwer = drin.mean(axis=0)
        _, _, vt = np.linalg.svd(drin - schwer)
        richtung = vt[0] if float(vt[0] @ u) >= 0.0 else -vt[0]
        entlang = (drin - schwer) @ richtung
        laenge = float(entlang.max() - entlang.min())
        if laenge < min_laenge_m or abs(float(richtung @ u)) < grenze:
            continue
        if beste is None or laenge > beste['laenge_m']:
            beste = {'richtung': (float(richtung[0]), float(richtung[1])),
                     'punkte': int(drin.shape[0]), 'laenge_m': laenge}
    return beste


def anfahrt(pfosten: Sequence[Sequence[float]], hindernisse: Sequence[Sequence[float]],
            sicht: Optional[dict] = None, *,
            vor_m: Sequence[float] = ANFAHRT_VOR_M, anlauf_m: float = ANFAHRT_ANLAUF_M,
            noetig_m: float = FREI_NEBEN_DER_LINIE_M,
            drehkreis_m: float = DREHKREIS_M) -> dict:
    """Der Weg vom Standplatz vor die Tür, geprüft an dem, was der Laser sieht.

    Im Standpunktrahmen (Antriebsmitte im Ursprung, x voraus, y links).
    Rückgabe: ``punkte`` (ein oder zwei), ``vor_m`` (wie weit vor der
    Türlinie der Roboter danach steht), ``drehen_grad`` (je Punkt, links
    positiv), ``strecken_m`` (je Punkt), ``frei_m`` (kleinster Abstand neben
    dem Weg) und ``drehkreis_m`` (kleinster freier Kreis an den Stellen, an
    denen er sich dreht). ``ValueError`` mit Grund, wenn kein Weg passt.

    Geprüft wird je Strecke der Freiraum links und rechts, an jeder
    Drehstelle ein freier Kreis und dass der Laser die Punkte frei gesehen
    hat. Was der Laser von hier nicht sieht, gilt nicht als frei.

    Die Türachse steht senkrecht auf der Wand neben der Tür
    (``wandrichtung``); nur wenn dort keine gerade Wand gesehen wird,
    senkrecht auf der Verbindung der Türkanten. ``achse_aus`` nennt, woraus.
    """
    lage = aufstellung(pfosten)
    if lage['breite_m'] < MIN_BREITE_M:
        raise ValueError(
            f'Anfahrt: Öffnung {lage["breite_m"]:.2f} m breit, nötig {MIN_BREITE_M:.2f} m')
    if lage['abstand_m'] <= 0.3:
        raise ValueError('Anfahrt: Der Standpunkt liegt in oder hinter der Türlinie')
    (ax, ay), (bx, by) = [(float(q[0]), float(q[1])) for q in pfosten]
    mx, my = 0.5 * (ax + bx), 0.5 * (ay + by)
    # Die Türachse zeigt vom Standplatz weg durch die Tür.
    wand = wandrichtung(pfosten, hindernisse)
    if wand is not None:
        nx, ny = -wand['richtung'][1], wand['richtung'][0]
    else:
        nx, ny = -(by - ay) / lage['breite_m'], (bx - ax) / lage['breite_m']
    if mx * nx + my * ny < 0.0:
        nx, ny = -nx, -ny
    achse = math.atan2(ny, nx)
    achse_aus = ('wand', wand['punkte'], wand['laenge_m']) if wand else ('kanten', 0, 0.0)

    def pruefe(punkte: List[Punkt]) -> dict:
        drehen, strecken = [], []
        frei_seite, kreis = math.inf, math.inf
        ort, blick = (0.0, 0.0), 0.0
        pruefe_grenzen(punkte, ort)
        for nummer, ziel in enumerate(punkte, start=1):
            strecke = math.hypot(ziel[0] - ort[0], ziel[1] - ort[1])
            if strecke < MIN_ANLAUF_M:
                raise ValueError(f'Strecke {nummer} wäre nur {strecke:.2f} m lang')
            richtung = math.atan2(ziel[1] - ort[1], ziel[0] - ort[0])
            dreh = _winkel(richtung - blick)
            if abs(dreh) > 10.0:
                platz = frei_um(hindernisse, ort)
                if platz < drehkreis_m:
                    wo = 'am Standplatz' if nummer == 1 else 'am Punkt vor der Tür'
                    raise ValueError(
                        f'zum Drehen ist {wo} nicht genug Platz '
                        f'({platz:.2f} m frei, nötig {drehkreis_m:.2f} m)')
                if nummer > 1:
                    for k in range(12):
                        rand = (ort[0] + drehkreis_m * math.cos(k * math.pi / 6),
                                ort[1] + drehkreis_m * math.sin(k * math.pi / 6))
                        if not frei_gesehen(sicht, rand):
                            raise ValueError(
                                'den Platz zum Drehen vor der Tür sieht der Laser von '
                                'hier nicht ganz ein')
                kreis = min(kreis, platz)
            frei = freiraum(hindernisse, ziel, start=ort)
            for seite in ('links', 'rechts'):
                if frei[f'{seite}_m'] < noetig_m:
                    raise ValueError(
                        f'auf Strecke {nummer} sind {seite} nur {frei[f"{seite}_m"]:.2f} m '
                        f'frei ({frei[f"{seite}_voraus_m"]:.1f} m voraus), '
                        f'nötig {noetig_m:.2f} m')
                frei_seite = min(frei_seite, frei[f'{seite}_m'])
            if not frei_gesehen(sicht, ziel):
                raise ValueError(
                    f'Punkt {nummer} sieht der Laser von hier nicht frei ein')
            drehen.append(dreh)
            strecken.append(strecke)
            ort, blick = (float(ziel[0]), float(ziel[1])), richtung
        return {'punkte': list(punkte), 'drehen_grad': drehen, 'strecken_m': strecken,
                'frei_m': frei_seite, 'drehkreis_m': kreis,
                'schraeg_grad': abs(_winkel(blick - achse))}

    wege, gruende = [], []
    for vor in vor_m:
        ende = (mx - vor * nx, my - vor * ny)
        vorpunkt = (mx - (vor + anlauf_m) * nx, my - (vor + anlauf_m) * ny)
        for punkte in ([ende], [vorpunkt, ende]):
            # Ohne Vorpunkt nur, wenn er danach fast in Richtung der Tür steht.
            if len(punkte) == 1 and abs(_winkel(math.atan2(ende[1], ende[0]) - achse)) > 10.0:
                continue
            try:
                weg = pruefe(punkte)
            except ValueError as grund:
                text = str(grund)
                gruende.append(text[10:] if text.startswith('Fahrziel: ') else text)
                continue
            weg['vor_m'] = vor
            weg['achse_aus'] = achse_aus
            wege.append(weg)
    if not wege:
        # Der häufigste Grund sagt am ehesten, was am Standplatz zu ändern ist.
        grund = max(set(gruende), key=gruende.count) if gruende else 'kein Weg gefunden'
        raise ValueError(f'Anfahrt: {grund}')
    return min(wege, key=lambda w: (round(sum(abs(d) for d in w['drehen_grad']), 0),
                                    len(w['punkte']), w['vor_m']))


def anfahrt_im_kartenrahmen(weg: dict, pose: Sequence[float]) -> List[Punkt]:
    """Die Punkte einer ``anfahrt`` im Kartenrahmen (``pose`` der Antriebsmitte)."""
    return [im_kartenrahmen(q, pose) for q in weg['punkte']]


def anfahrt_text(weg: dict) -> str:
    """Die Anfahrt in einem Satz, so wie der Roboter sie fährt."""
    def dreh(grad: float) -> str:
        return f'{abs(grad):.0f}° nach {"links" if grad > 0 else "rechts"} drehen'

    schritte = []
    for grad, strecke in zip(weg['drehen_grad'], weg['strecken_m']):
        if abs(grad) >= 3.0:
            schritte.append(dreh(grad))
        schritte.append(f'{strecke:.2f} m fahren')
    kreis = ('' if not math.isfinite(weg['drehkreis_m'])
             else f', zum Drehen {min(weg["drehkreis_m"], 9.99):.2f} m '
                  f'(nötig {DREHKREIS_M:.2f} m)')
    seite = 'über 2 m' if weg['frei_m'] > 2.0 else f'{weg["frei_m"]:.2f} m'
    woraus, zahl, laenge = weg.get('achse_aus', ('kanten', 0, 0.0))
    achse = (f'Türachse aus der Wand neben der Tür ({zahl} Laserpunkte über {laenge:.2f} m)'
             if woraus == 'wand'
             else 'Türachse nur aus den zwei Türkanten (neben der Tür keine gerade Wand gesehen)')
    return ('Anfahrt: ' + ', '.join(schritte)
            + f'; danach steht er {weg["vor_m"]:.1f} m mittig vor der Tür, Blick zur Tür. '
            + f'Frei neben dem Weg mindestens {seite} '
            + f'(nötig {FREI_NEBEN_DER_LINIE_M:.2f} m){kreis}. {achse}')


# Der Streifen, in dem der Erkunder anhält (stage_drive: halbe Breite 0,25 m,
# dazu eine halbe Zelle), und wie weit er vor die Vorderkante schaut.
STREIFEN_HALB_M = 0.255
NAHBEREICH_M = 0.25


def kostenkarte_voraus(daten, breite: int, hoehe: int, zelle_m: float,
                       ursprung_xy: Sequence[float], pose: Sequence[float], *,
                       bis_m: float = 1.5, halb_m: float = 0.50, belegt: int = 100) -> dict:
    """Was in der Kostenkarte vor dem Roboter belegt ist (nur zur Auskunft).

    Dieselbe Karte liest der Erkunder für seinen Nahbereichs-Halt. Genannt
    wird die nächste belegte Zelle im Fahrstreifen und je Seite knapp
    daneben, jeweils als (Meter voraus ab Antriebsmitte, Meter seitlich,
    links positiv); ``None``, wenn dort bis ``bis_m`` nichts liegt.
    """
    feld = np.asarray(daten, dtype=np.int16)
    if feld.size != breite * hoehe or zelle_m <= 0.0:
        raise ValueError('Kostenkarte: Größe passt nicht')
    index = np.flatnonzero(feld >= belegt)
    ergebnis = {'im_streifen': None, 'links_daneben': None, 'rechts_daneben': None,
                'zellen': int(index.size)}
    if index.size == 0:
        return ergebnis
    x = float(ursprung_xy[0]) + (index % breite + 0.5) * zelle_m - float(pose[0])
    y = float(ursprung_xy[1]) + (index // breite + 0.5) * zelle_m - float(pose[1])
    c, s = math.cos(float(pose[2])), math.sin(float(pose[2]))
    voraus, seitlich = c * x + s * y, -s * x + c * y
    vorn = (voraus > VORDERKANTE_M - 0.5 * zelle_m) & (voraus <= bis_m)

    def naechste(maske):
        if not np.any(maske):
            return None
        i = int(np.argmin(np.where(maske, voraus, np.inf)))
        return round(float(voraus[i]), 2), round(float(seitlich[i]), 2)

    ergebnis['im_streifen'] = naechste(vorn & (np.abs(seitlich) <= STREIFEN_HALB_M))
    ergebnis['links_daneben'] = naechste(
        vorn & (seitlich > STREIFEN_HALB_M) & (seitlich <= halb_m))
    ergebnis['rechts_daneben'] = naechste(
        vorn & (seitlich < -STREIFEN_HALB_M) & (seitlich >= -halb_m))
    return ergebnis


def kostenkarte_text(sicht: dict) -> str:
    """Die Auskunft aus ``kostenkarte_voraus`` in einem Satz."""
    def stelle(wert, mit_seite=True) -> str:
        if wert is None:
            return 'nichts'
        text = f'{wert[0] - VORDERKANTE_M:.2f} m vor der Vorderkante'
        if mit_seite:
            text += f', {abs(wert[1]):.2f} m {"links" if wert[1] >= 0 else "rechts"} der Mitte'
        return text

    streifen = sicht['im_streifen']
    haelt = streifen is not None and streifen[0] - VORDERKANTE_M <= NAHBEREICH_M + 0.01
    return ('Kostenkarte vor dem Roboter (belegte Zellen bis 1,5 m): im Fahrstreifen '
            f'{stelle(streifen)}' + (' – so nah hält der Erkunder an' if haelt else '')
            + f'; links daneben {stelle(sicht["links_daneben"])}'
            + f'; rechts daneben {stelle(sicht["rechts_daneben"])}.')


def durch_die_tuer(pfosten: Sequence[Sequence[float]], pose: Sequence[float], *,
                   vor_m: float = 1.10, hinter_m: float = HINTER_DER_TUER_M,
                   vorpunkt_ab_m: float = 0.15) -> List[Punkt]:
    """Vorpunkt und Auslaufpunkt auf der Türachse, im Kartenrahmen.

    **Für die Etappenfahrt nicht mehr verwendet** (seit KI-F2 fährt sie die
    gerade Linie, ``gerade_durch_die_tuer``): Der Weg über den Vorpunkt
    führt schräg zur Achse und damit nah an ein offenes Türblatt. Die
    Rechnung bleibt für einen geplanten Weg (Nav2), der Hindernisse selbst
    umgeht.

    ``pfosten`` im Standpunktrahmen (Antriebsmitte, x voraus, y links),
    ``pose`` der Antriebsmitte in der Karte. Steht der Roboter schon am
    Vorpunkt (näher als ``vorpunkt_ab_m``), entfällt dieser.
    """
    vorpunkt, auslauf = tuer_punkte(pfosten, (0.0, 0.0), vor_m=vor_m, hinter_m=hinter_m)
    lage = aufstellung(pfosten)
    if lage['abstand_m'] < vor_m + vorpunkt_ab_m:
        # Der Roboter steht schon so nah wie der Vorpunkt oder näher. Zurück
        # wird nicht gefahren: Auf der Türachse geht es direkt zum Auslauf,
        # neben ihr gibt es kein Ziel.
        if abs(lage['seitlich_m']) > vorpunkt_ab_m:
            raise ValueError(
                f'Fahrziel: zu nah an der Tür ({lage["abstand_m"]:.2f} m) und '
                f'{abs(lage["seitlich_m"]):.2f} m neben der Türachse')
        punkte = []
    else:
        punkte = [vorpunkt]
    return [im_kartenrahmen(p, pose) for p in (*punkte, auslauf)]


def pruefe_grenzen(punkte: Sequence[Sequence[float]], start: Sequence[float]) -> float:
    """Gesamtstrecke in Metern; ``ValueError`` mit Maß, wenn eine Grenze verletzt ist."""
    if not 1 <= len(punkte) <= MAX_PUNKTE:
        raise ValueError(f'Fahrziel: {len(punkte)} Punkte, erlaubt 1 bis {MAX_PUNKTE}')
    vorher = (float(start[0]), float(start[1]))
    gesamt = 0.0
    for nummer, punkt in enumerate(punkte, start=1):
        strecke = math.hypot(float(punkt[0]) - vorher[0], float(punkt[1]) - vorher[1])
        if not math.isfinite(strecke):
            raise ValueError('Fahrziel: Punkt ist keine Zahl')
        if strecke > MAX_STRECKE_M:
            raise ValueError(
                f'Fahrziel: Strecke {nummer} ist {strecke:.2f} m lang, '
                f'erlaubt {MAX_STRECKE_M:.1f} m')
        if nummer > 1 and strecke < MIN_STRECKE_M:
            raise ValueError(f'Fahrziel: Strecke {nummer} ist nur {strecke:.2f} m lang')
        gesamt += strecke
        vorher = (float(punkt[0]), float(punkt[1]))
    if gesamt > MAX_GESAMT_M:
        raise ValueError(
            f'Fahrziel: zusammen {gesamt:.2f} m, erlaubt {MAX_GESAMT_M:.1f} m')
    if gesamt < MIN_STRECKE_M:
        raise ValueError(f'Fahrziel: zusammen nur {gesamt:.2f} m')
    return gesamt


def botschaft(punkte: Sequence[Sequence[float]], *, kennung: str, quelle: str,
              zeit_s: float, frame: str = 'map',
              bemerkung: Optional[str] = None) -> str:
    """Das Fahrziel als Text für den Erkunder.

    ``quelle`` sagt, wer gewählt hat: ``ki``, ``mensch`` oder ``test``. Der
    Erkunder schreibt sie in seine Meldungen, damit jede Fahrt zeigt, wer
    entschieden hat.
    """
    if quelle not in QUELLEN:
        raise ValueError(f'Fahrziel: Quelle {quelle!r} unbekannt')
    if not kennung or len(kennung) > 80:
        raise ValueError('Fahrziel: Kennung fehlt oder ist zu lang')
    daten = {'kennung': kennung, 'quelle': quelle, 'frame': frame,
             'zeit_s': float(zeit_s),
             'punkte': [[round(float(p[0]), 3), round(float(p[1]), 3)] for p in punkte]}
    if bemerkung:
        daten['bemerkung'] = str(bemerkung)[:200]
    return json.dumps(daten, ensure_ascii=False)
