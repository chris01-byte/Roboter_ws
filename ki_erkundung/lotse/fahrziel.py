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
# halbe Gehäusebreite (0,23 m) und 3 cm. Der Erkunder prüft während der
# Fahrt selbst einen Streifen von 0,25 m je Seite und hält an, wenn dort
# etwas liegt; 1 cm Abstand dazu, damit er nicht mitten in der Tür hält.
# Festgelegt vom Projektinhaber am 23.11.2026 nach KI-F7 (vorher 0,30 m).
FREI_NEBEN_DER_LINIE_M = 0.26
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
                blick_rad: float = 0.0, achse: Optional[Sequence[float]] = None) -> dict:
    """Wie der Roboter zur Tür steht.

    ``abstand_m``: bis zur Türlinie, entlang der Türachse.
    ``seitlich_m``: Versatz neben der Türachse; positiv = der Roboter steht
    links der Achse (mit Blick zur Tür).
    ``winkel_grad``: Richtung der Türachse gegen die Blickrichtung; positiv =
    die Achse liegt links, der Roboter müsste sich nach links drehen.

    ``achse``: Richtung der Türachse (``tuerachse``, aus der Wand neben der
    Tür). Ohne sie steht die Achse senkrecht auf der Verbindung der zwei
    Kanten; dann kippt ein Fehler von wenigen Zentimetern an einer Kante die
    Achse um Grade (KI-F5, 23.11.2026: 7 cm an der rechten Kante, 7° Kippung,
    „30 cm daneben“ bei einem Roboter, der mittig stand).
    """
    (ax, ay), (bx, by) = [(float(p[0]), float(p[1])) for p in pfosten]
    sx, sy = float(standpunkt[0]), float(standpunkt[1])
    breite = math.hypot(bx - ax, by - ay)
    if not math.isfinite(breite) or breite <= 0.0:
        raise ValueError('Fahrziel: Pfosten fallen zusammen')
    mx, my = 0.5 * (ax + bx), 0.5 * (ay + by)
    if achse is not None:
        laenge = math.hypot(float(achse[0]), float(achse[1]))
        if not math.isfinite(laenge) or laenge < 1e-9:
            raise ValueError('Fahrziel: Türachse ohne Richtung')
        nx, ny = float(achse[0]) / laenge, float(achse[1]) / laenge
    else:
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
                 min_anlauf_m: float = 0.40,
                 achse: Optional[Sequence[float]] = None) -> List[Punkt]:
    """Fahrpunkte auf der geraden Linie vom Standplatz durch die Türmitte.

    Im Standpunktrahmen (Antriebsmitte im Ursprung, x voraus, y links). Der
    letzte Punkt liegt ``hinter_m`` hinter der Türlinie, der Zwischenpunkt
    ``vor_m`` davor (beides quer zur Türlinie gemessen); er entfällt, wenn
    bis dorthin weniger als ``min_anlauf_m`` zu fahren wäre.

    Warum eine gerade Linie und kein Vorpunkt auf der Türachse: In KI-F2
    (22.11.2026) fuhr der Roboter erst schräg zur Achse und wollte sich
    dort drehen; die schräge Strecke führte 1,5 cm an der Spitze des
    offenen Türblatts vorbei. Die gerade Linie hält dort 39 cm Abstand.

    ``achse`` wie bei ``aufstellung``.
    """
    lage = aufstellung(pfosten, achse=achse)
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
# Zum Drehen auf der Stelle: Die vorderen Gehäuseecken kreisen 0,355 m um
# die Antriebsmitte (0,27 m voraus, 0,23 m seitlich, gemessen am
# 18.08.2026); dazu 1,5 cm. Der Arm steht dabei in Transportstellung.
# Festgelegt vom Projektinhaber am 23.11.2026 nach KI-F7 (vorher 0,45 m mit
# dem gepolsterten Umriss).
DREHKREIS_M = 0.37
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


def gerade_stuecke(punkte: Sequence[Sequence[float]], *, luecke_m: float = 0.15,
                   spiel_m: float = 0.04, min_punkte: int = 6) -> List[dict]:
    """Gerade Stücke im Laserbild (Punkte in der Reihenfolge der Strahlen).

    Zusammenhängende Läufe (Abstand zum Nachbarn höchstens ``luecke_m``)
    werden an der Ecke geteilt (dem Punkt, der am weitesten von der Sehne
    liegt), solange ein Punkt mehr als ``spiel_m`` neben der ausgeglichenen
    Linie liegt; danach werden benachbarte Stücke, die zusammen wieder
    gerade sind, zusammengefügt. ``spiel_m`` ist etwa das Vierfache des
    Messrauschens (Laser ±1,5 cm). Rückgabe je Stück: ``a`` und ``b`` (Enden
    auf der ausgeglichenen Linie, in Strahlreihenfolge), ``richtung`` (von a
    nach b), ``schwer``, ``punkte``, ``laenge_m``, ``frei_a`` und ``frei_b``
    (das Ende ist zugleich das Ende des zusammenhängenden Laufs, und daneben
    sieht der Laser mindestens 0,30 m weiter oder gar nichts; endet der Lauf
    dagegen, weil etwas Näheres ihn verdeckt, ist das Ende nicht frei).
    """
    feld = np.asarray(punkte, dtype=float).reshape(-1, 2)
    if feld.shape[0] < min_punkte:
        return []
    # Das Laserbild ist ein Kreis: Es beginnt hinter dem Roboter willkürlich.
    # Damit dort keine Wand in zwei Stücke mit falschen „freien Enden“
    # zerfällt, beginnt die Liste am größten Sprung zwischen Nachbarn.
    rund = np.hypot(*(np.roll(feld, -1, axis=0) - feld).T)
    feld = np.roll(feld, -(int(np.argmax(rund)) + 1), axis=0)
    schritte = np.hypot(*np.diff(feld, axis=0).T)
    grenzen = [0] + [int(i) + 1 for i in np.flatnonzero(schritte > luecke_m)] + [len(feld)]
    weite = np.hypot(feld[:, 0], feld[:, 1])
    winkel = np.arctan2(feld[:, 1], feld[:, 0])

    def dahinter_frei(ende: int, nachbar: int) -> bool:
        """Sieht der Laser neben dem Laufende weiter (oder nichts)?"""
        nachbar %= len(feld)
        luecke = abs((float(winkel[nachbar] - winkel[ende]) + math.pi) % (2 * math.pi) - math.pi)
        return luecke > math.radians(2.0) or weite[nachbar] > weite[ende] + 0.30

    def abweichung(lauf: np.ndarray):
        schwer = lauf.mean(axis=0)
        _, _, achsen = np.linalg.svd(lauf - schwer)
        quer = np.abs((lauf - schwer) @ np.array([-achsen[0][1], achsen[0][0]]))
        return float(quer.max()), schwer, achsen[0]

    def teile(von: int, bis: int, ergebnis: List[Tuple[int, int]]):
        lauf = feld[von:bis]
        if lauf.shape[0] < 2:
            return
        if lauf.shape[0] >= 3 and abweichung(lauf)[0] > spiel_m:
            sehne = lauf[-1] - lauf[0]
            laenge = float(np.hypot(*sehne))
            if laenge > 1e-6:
                quer = np.abs(sehne[0] * (lauf[:, 1] - lauf[0, 1])
                              - sehne[1] * (lauf[:, 0] - lauf[0, 0])) / laenge
            else:
                quer = np.hypot(*(lauf - lauf[0]).T)
            k = int(np.argmax(quer[1:-1])) + 1
            teile(von, von + k + 1, ergebnis)
            teile(von + k, bis, ergebnis)
            return
        ergebnis.append((von, bis))

    stuecke: List[dict] = []
    for von, bis in zip(grenzen[:-1], grenzen[1:]):
        teile_liste: List[Tuple[int, int]] = []
        teile(von, bis, teile_liste)
        # Nachbarn zusammenfügen, die zusammen gerade sind (Rauschen, keine Ecke)
        zusammen: List[Tuple[int, int]] = []
        for stueck in teile_liste:
            if zusammen and abweichung(feld[zusammen[-1][0]:stueck[1]])[0] <= spiel_m:
                zusammen[-1] = (zusammen[-1][0], stueck[1])
            else:
                zusammen.append(stueck)
        for s_von, s_bis in zusammen:
            lauf = feld[s_von:s_bis]
            if lauf.shape[0] < min_punkte:
                continue
            _, schwer, richtung = abweichung(lauf)
            if float(richtung @ (lauf[-1] - lauf[0])) < 0.0:
                richtung = -richtung
            a = schwer + richtung * float((lauf[0] - schwer) @ richtung)
            b = schwer + richtung * float((lauf[-1] - schwer) @ richtung)
            stuecke.append({'a': a, 'b': b, 'richtung': richtung, 'schwer': schwer,
                            'punkte': int(lauf.shape[0]),
                            'laenge_m': float(np.hypot(*(b - a))),
                            'frei_a': s_von - von <= 2 and dahinter_frei(von, von - 1),
                            'frei_b': bis - s_bis <= 2 and dahinter_frei(bis - 1, bis)})
    return stuecke


# Ein offenes Türblatt: so lang wie eine Tür breit ist, gerade, an der Wand
# ansetzend und schräg bis senkrecht zu ihr. Bis 0,95 m: Zimmertüren sind
# schmaler; ein 1 m tiefer Schrank an der Wand sähe sonst von der Seite
# genauso aus (Simulation 23.11.2026).
BLATT_VON_M = 0.60
BLATT_BIS_M = 0.95
BLATT_MIN_WINKEL_GRAD = 55.0


def tuer_hinter_blatt(hindernisse: Sequence[Sequence[float]], *,
                      blatt_von_m: float = BLATT_VON_M, blatt_bis_m: float = BLATT_BIS_M,
                      wand_min_m: float = 0.40) -> Optional[dict]:
    """Die Tür, deren offenes Blatt sie verdeckt, aus Blatt und Wand geschätzt.

    Steht der Roboter auf der Seite, zu der das Türblatt aufgeht, sieht der
    Laser die Rückseite des Blatts, nicht die Öffnung (KI-F1, KI-F8: zu
    breit oder gar nicht vermessen). Zu sehen sind dann ein gerades Stück
    Wand und ein gerades, 0,60 bis 0,95 m langes Stück, das an dieser Wand
    ansetzt und schräg bis senkrecht von ihr in den Raum ragt: das Blatt.
    Dann liegt das Scharnier, wo das Blatt die Wand trifft, die Tür in der
    Wand auf der anderen Seite des Blatts, so breit wie das Blatt lang ist.

    Das ist eine Schätzung: Für die Anfahrt vor die Tür genügt sie; die
    Durchfahrt wird danach von vorn neu vermessen. Rückgabe ``None`` oder
    ``pfosten`` (Scharnier zuerst), ``normal`` (quer zur Wand),
    ``blatt_m``, ``winkel_grad`` (Blatt gegen Wand), ``wand_punkte``,
    ``wand_laenge_m``.
    """
    stuecke = gerade_stuecke(hindernisse)
    grenze = math.cos(math.radians(BLATT_MIN_WINKEL_GRAD))
    beste, wert = None, -math.inf
    for blatt in stuecke:
        if not blatt_von_m <= blatt['laenge_m'] <= blatt_bis_m:
            continue
        for wand in stuecke:
            if wand is blatt or wand['laenge_m'] < wand_min_m:
                continue
            d_w, d_b = wand['richtung'], blatt['richtung']
            cos_wb = float(d_w @ d_b)
            if abs(cos_wb) > grenze:
                continue
            n_w = np.array([-d_w[1], d_w[0]])

            def vor_der_wand(q, wand=wand, n_w=n_w):
                return float((q - wand['schwer']) @ n_w)

            ea, eb = vor_der_wand(blatt['a']), vor_der_wand(blatt['b'])
            spitze_bei_b = abs(ea) <= abs(eb)
            wurzel, spitze = ((blatt['a'], blatt['b']) if spitze_bei_b
                              else (blatt['b'], blatt['a']))
            if abs(vor_der_wand(wurzel)) > 0.10 or abs(vor_der_wand(spitze)) < 0.45:
                continue
            # Hinter der Spitze sieht der Laser weiter (an ihr vorbei); geht
            # das Laserbild dort um eine Ecke weiter, ist es ein Möbel.
            if not (blatt['frei_b'] if spitze_bei_b else blatt['frei_a']):
                continue
            # Die Spitze ragt auf der Seite des Roboters in den Raum.
            roboter = vor_der_wand(np.zeros(2))
            if roboter * vor_der_wand(spitze) <= 0.0:
                continue
            scharnier = wurzel - vor_der_wand(wurzel) * n_w
            lage = float((scharnier - wand['schwer']) @ d_w)
            enden = sorted((float((wand['a'] - wand['schwer']) @ d_w),
                            float((wand['b'] - wand['schwer']) @ d_w)))
            if not enden[0] - 0.20 <= lage <= enden[1] + 0.20:
                continue
            # Roboter und gesehene Wand liegen auf derselben Seite des Blatts;
            # die Tür liegt in der Wand auf der anderen.
            n_b = np.array([-d_b[1], d_b[0]])
            seite = float(-scharnier @ n_b)
            if seite == 0.0 or seite * float((wand['schwer'] - scharnier) @ n_b) <= 0.0:
                continue
            zur_tuer = d_w if float(d_w @ n_b) * seite < 0.0 else -d_w
            breite = min(max(blatt['laenge_m'], TUER_MIN_M), TUER_MAX_M)
            fern = scharnier + zur_tuer * breite
            guete = wand['punkte'] - 20.0 * abs(blatt['laenge_m'] - 0.82)
            if guete > wert:
                n = n_w if roboter < 0.0 else -n_w       # zeigt vom Roboter durch die Tür
                beste, wert = {
                    'pfosten': ((float(scharnier[0]), float(scharnier[1])),
                                (float(fern[0]), float(fern[1]))),
                    'normal': (float(n[0]), float(n[1])),
                    'blatt_m': blatt['laenge_m'],
                    'winkel_grad': math.degrees(math.acos(min(1.0, abs(cos_wb)))),
                    'wand_punkte': wand['punkte'], 'wand_laenge_m': wand['laenge_m'],
                }, guete
    return beste


def blatt_text(fund: dict) -> str:
    """Die Schätzung „Tür hinter dem Blatt“ in einem Satz."""
    (ax, ay), (bx, by) = fund['pfosten']
    mx, my = 0.5 * (ax + bx), 0.5 * (ay + by)
    breite = math.hypot(bx - ax, by - ay)
    richtung = math.degrees(math.atan2(my, mx))
    return (f'Türblatt gesehen: {fund["blatt_m"]:.2f} m lang, {fund["winkel_grad"]:.0f}° zur '
            f'Wand; die Öffnung dahinter verdeckt es. Tür geschätzt: {breite:.2f} m breit, '
            f'{richtung:+.1f}°, {math.hypot(mx, my):.2f} m (Wand: {fund["wand_punkte"]} '
            f'Laserpunkte über {fund["wand_laenge_m"]:.2f} m).')


def tuerachse(pfosten: Sequence[Sequence[float]],
              hindernisse: Sequence[Sequence[float]]) -> dict:
    """Die Richtung der Türachse und woraus sie stammt.

    Aus der geraden Wand neben der Tür (``wandrichtung``, viele Laserpunkte),
    nur ohne solche Wand aus der Verbindung der zwei Türkanten. Rückgabe:
    ``normal`` (Einheitsvektor quer zur Wand; die Seite legt ``aufstellung``
    fest), ``quelle`` (``'wand'`` oder ``'kanten'``), ``punkte``, ``laenge_m``.
    """
    wand = wandrichtung(pfosten, hindernisse)
    if wand is not None:
        rx, ry = wand['richtung']
        return {'normal': (-ry, rx), 'quelle': 'wand', 'punkte': wand['punkte'],
                'laenge_m': wand['laenge_m']}
    (ax, ay), (bx, by) = [(float(q[0]), float(q[1])) for q in pfosten]
    breite = math.hypot(bx - ax, by - ay)
    if not math.isfinite(breite) or breite <= 0.0:
        raise ValueError('Fahrziel: Pfosten fallen zusammen')
    return {'normal': (-(by - ay) / breite, (bx - ax) / breite), 'quelle': 'kanten',
            'punkte': 0, 'laenge_m': 0.0}


def achse_text(achse: dict) -> str:
    """Woraus die Türachse stammt, in einem Satz."""
    if achse.get('quelle') == 'wand':
        return (f'Türachse aus der Wand neben der Tür ({achse["punkte"]} Laserpunkte über '
                f'{achse["laenge_m"]:.2f} m).')
    if achse.get('quelle') == 'karte':
        return (f'Türachse aus der Wand neben der Tür, gemessen vor der Anfahrt '
                f'({achse["punkte"]} Laserpunkte über {achse["laenge_m"]:.2f} m); von hier '
                'sieht der Laser die Wand nicht lang genug.')
    return 'Türachse nur aus den zwei Türkanten (neben der Tür keine gerade Wand gesehen).'


def tuer_merken(pfosten: Sequence[Sequence[float]], achse: dict,
                pose: Sequence[float], *, breite_m: Optional[float] = None,
                schluss: Optional[str] = None) -> dict:
    """Die Tür im Kartenrahmen merken, um sie nach der Anfahrt wiederzufinden.

    ``pfosten`` und ``achse`` sind im Standpunktrahmen gemessen, ``pose`` ist
    die Lage des Roboters in der Karte dabei. Rückgabe: ``mitte`` und
    ``normal`` im Kartenrahmen, dazu Quelle und Umfang der Achse. Für die
    Meldung beim Wiederfinden außerdem Breite, Schluss der Vermessung und
    wie schräg die Tür gesehen wurde (``schraeg_grad``: Winkel zwischen Blick
    zur Türmitte und Türachse).
    """
    x, y, gier = float(pose[0]), float(pose[1]), float(pose[2])
    c, s = math.cos(gier), math.sin(gier)
    mx = 0.5 * (float(pfosten[0][0]) + float(pfosten[1][0]))
    my = 0.5 * (float(pfosten[0][1]) + float(pfosten[1][1]))
    nx, ny = achse['normal']
    weite = math.hypot(mx, my)
    schraeg = (math.degrees(math.acos(min(1.0, abs(mx * nx + my * ny) / weite)))
               if weite > 1e-9 else 0.0)
    return {'mitte': (x + c * mx - s * my, y + s * mx + c * my),
            'normal': (c * nx - s * ny, s * nx + c * ny),
            'quelle': achse.get('quelle'), 'punkte': achse.get('punkte', 0),
            'laenge_m': achse.get('laenge_m', 0.0),
            'breite_m': None if breite_m is None else float(breite_m),
            'schluss': schluss, 'schraeg_grad': schraeg}


def im_standpunktrahmen(ort: Sequence[float], pose: Sequence[float]) -> Tuple[float, float]:
    """Ein Ort der Karte vom Roboter aus (x voraus, y links)."""
    dx, dy = float(ort[0]) - float(pose[0]), float(ort[1]) - float(pose[1])
    c, s = math.cos(float(pose[2])), math.sin(float(pose[2]))
    return c * dx + s * dy, -s * dx + c * dy


def wiederfinden(tueren: Sequence, gemerkt: dict, pose: Sequence[float],
                 max_abstand_m: float = 0.35):
    """Unter den neu vermessenen türbreiten Öffnungen die gemerkte Tür.

    Gewählt wird die, deren Mitte der gemerkten am nächsten liegt, höchstens
    ``max_abstand_m`` davon entfernt; sonst ``None``.
    """
    ziel = im_standpunktrahmen(gemerkt['mitte'], pose)
    beste, abstand = None, max_abstand_m
    for o in tueren:
        mx = 0.5 * (o.pfosten[0][0] + o.pfosten[1][0])
        my = 0.5 * (o.pfosten[0][1] + o.pfosten[1][1])
        d = math.hypot(mx - ziel[0], my - ziel[1])
        if d <= abstand:
            beste, abstand = o, d
    return beste


def abweichung(o, gemerkt: dict, pose: Sequence[float]) -> dict:
    """Wie weit eine neu vermessene Öffnung neben der gemerkten Tür liegt.

    Nur für die Meldung, die Regel des Wiederfindens bleibt ``wiederfinden``.
    Zerlegt entlang der gemerkten Türachse, vom jetzigen Standplatz aus:
    ``tiefer_m`` positiv = weiter weg, durch die Tür hindurch; ``links_m``
    positiv = links mit Blick zur Tür. Dazu ``abstand_m`` der Mitten und
    ``breiter_m`` gegen die gemerkte Breite (``None`` ohne sie).
    """
    zx, zy = im_standpunktrahmen(gemerkt['mitte'], pose)
    mx = 0.5 * (o.pfosten[0][0] + o.pfosten[1][0])
    my = 0.5 * (o.pfosten[0][1] + o.pfosten[1][1])
    nx, ny = achse_aus_karte(gemerkt, pose)['normal']
    if nx * zx + ny * zy < 0.0:                     # Achse zeigt durch die Tür
        nx, ny = -nx, -ny
    dx, dy = mx - zx, my - zy
    return {'tiefer_m': dx * nx + dy * ny, 'links_m': -dx * ny + dy * nx,
            'abstand_m': math.hypot(dx, dy),
            'breiter_m': (None if gemerkt.get('breite_m') is None
                          else float(o.breite_m) - float(gemerkt['breite_m']))}


def wiederfinden_zeilen(tueren: Sequence, gemerkt: dict, pose: Sequence[float],
                        max_abstand_m: float = 0.35) -> List[str]:
    """Was das Wiederfinden sieht, in Zeilen: erwartete Lage, je Öffnung die Abweichung."""
    zx, zy = im_standpunktrahmen(gemerkt['mitte'], pose)
    gemerkt_text = ', '.join(teil for teil in (
        None if gemerkt.get('breite_m') is None else f'{gemerkt["breite_m"]:.2f} m breit',
        None if not gemerkt.get('schluss') else f'Schluss {gemerkt["schluss"]}',
        None if gemerkt.get('schraeg_grad') is None
        else f'{gemerkt["schraeg_grad"]:.0f}° schräg gesehen') if teil)
    zeilen = [f'Wiederfinden: erwartet {math.hypot(zx, zy):.2f} m, '
              f'{math.degrees(math.atan2(zy, zx)):+.0f}°'
              + (f' (erste Messung: {gemerkt_text})' if gemerkt_text else '')
              + f'; Grenze {max_abstand_m:.2f} m.']
    if not tueren:
        zeilen.append('  keine türbreite Öffnung neu vermessen.')
    for o in tueren:
        a = abweichung(o, gemerkt, pose)
        teile = [f'{abs(a["tiefer_m"]):.2f} m {"tiefer" if a["tiefer_m"] >= 0 else "näher"}',
                 f'{abs(a["links_m"]):.2f} m {"links" if a["links_m"] >= 0 else "rechts"}']
        if a['breiter_m'] is not None:
            teile.append(f'{abs(a["breiter_m"]):.2f} m '
                         f'{"breiter" if a["breiter_m"] >= 0 else "schmaler"}')
        zeilen.append(f'  Öffnung {o.nr}: {o.breite_m:.2f} m breit, {o.entfernung_m:.2f} m, '
                      f'{o.richtung_grad:+.0f}°, Schluss {o.schluss}: ' + ', '.join(teile)
                      + f'; Mitten {a["abstand_m"]:.2f} m auseinander'
                      + (' – passt.' if a['abstand_m'] <= max_abstand_m else ' – zu weit.'))
    return zeilen


def achse_aus_karte(gemerkt: dict, pose: Sequence[float]) -> dict:
    """Die gemerkte Türachse vom jetzigen Standplatz aus (Quelle ``'karte'``)."""
    nx, ny = gemerkt['normal']
    c, s = math.cos(float(pose[2])), math.sin(float(pose[2]))
    return {'normal': (c * nx + s * ny, -s * nx + c * ny), 'quelle': 'karte',
            'punkte': gemerkt['punkte'], 'laenge_m': gemerkt['laenge_m']}


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
    tuer = tuerachse(pfosten, hindernisse)
    nx, ny = tuer['normal']
    if mx * nx + my * ny < 0.0:
        nx, ny = -nx, -ny
    achse = math.atan2(ny, nx)
    achse_aus = (tuer['quelle'], tuer['punkte'], tuer['laenge_m'])

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


# So weit voraus hält der Erkunder an: Vorderkante und Nahbereich.
NAHHALT_BIS_M = VORDERKANTE_M + NAHBEREICH_M
# base_link liegt so hoch über dem Boden (nav2_params_real.yaml, OAK-Quelle).
BASIS_UEBER_BODEN_M = 0.09
# Das Gehäuse selbst endet so weit vor der Antriebsmitte; die „Vorderkante“
# der Meldungen (VORDERKANTE_M) liegt 6 cm weiter, mit Polster. Für ein
# Maßband vom Gehäuse aus.
GEHAEUSE_VORN_M = 0.27


def _vor_dem_gehaeuse(voraus_m: float) -> str:
    return f'{100 * (voraus_m - GEHAEUSE_VORN_M):.0f} cm vor dem Gehäuse'


def lage_vom_roboter(voraus_m: float, seitlich_m: float) -> str:
    """Wo eine Stelle vom Roboter aus liegt, in Worten für ein Maßband.

    Vor der gepolsterten Vorderkante: Abstand zu ihr und zum Gehäuse. Neben
    oder hinter dem Roboter: seitlicher Abstand und wie weit vor oder hinter
    der Antriebsmitte (KI-F9, 2w2: „-0.57 m vor der Vorderkante“ war für
    einen Menschen nicht zu verstehen).
    """
    seite = 'links' if seitlich_m >= 0 else 'rechts'
    if voraus_m >= VORDERKANTE_M:
        return (f'{voraus_m - VORDERKANTE_M:.2f} m vor der gepolsterten Vorderkante '
                f'({_vor_dem_gehaeuse(voraus_m)}), {abs(seitlich_m):.2f} m {seite} der Mitte')
    laengs = (f'{voraus_m:.2f} m vor seiner Antriebsmitte' if voraus_m >= 0
              else f'{-voraus_m:.2f} m hinter seiner Antriebsmitte')
    return f'{abs(seitlich_m):.2f} m {seite} von ihm, {laengs}'


def zellen_um(daten, breite: int, hoehe: int, zelle_m: float,
              ursprung_xy: Sequence[float], pose: Sequence[float],
              stelle: Sequence[float], *, radius_m: float = 0.15,
              belegt: int = 100) -> np.ndarray:
    """Belegte Zellen eines Rasters rings um eine Stelle, in jeder Richtung.

    ``stelle`` und das Ergebnis (``N x 2``: voraus, seitlich) im Rahmen des
    Roboters, ``pose`` seine Lage im Rahmen des Rasters. Für die Herkunft
    einer belegten Stelle: Früher wurde die Karte nur in einem Streifen vor
    dem Roboter abgefragt; eine Stelle seitlich daneben galt dann als „frei“,
    obwohl die Karte dort belegt war (KI-F9, 2w2).
    """
    feld = np.asarray(daten, dtype=np.int16)
    if feld.size != breite * hoehe or zelle_m <= 0.0:
        raise ValueError('Raster: Größe passt nicht')
    x0, y0, gier = float(pose[0]), float(pose[1]), float(pose[2])
    c, s = math.cos(gier), math.sin(gier)
    vx, vy = float(stelle[0]), float(stelle[1])
    ox, oy = x0 + c * vx - s * vy, y0 + s * vx + c * vy
    n = int(math.ceil(radius_m / zelle_m)) + 1
    i0 = int(math.floor((ox - float(ursprung_xy[0])) / zelle_m))
    j0 = int(math.floor((oy - float(ursprung_xy[1])) / zelle_m))
    spalten = np.arange(max(0, i0 - n), min(breite, i0 + n + 1))
    zeilen = np.arange(max(0, j0 - n), min(hoehe, j0 + n + 1))
    if spalten.size == 0 or zeilen.size == 0:
        return np.zeros((0, 2))
    jj, ii = np.meshgrid(zeilen, spalten, indexing='ij')
    werte = feld.reshape(hoehe, breite)[jj, ii]
    drin = werte >= belegt
    xs = float(ursprung_xy[0]) + (ii[drin] + 0.5) * zelle_m
    ys = float(ursprung_xy[1]) + (jj[drin] + 0.5) * zelle_m
    nah = np.hypot(xs - ox, ys - oy) <= radius_m
    dx, dy = xs[nah] - x0, ys[nah] - y0
    return np.column_stack([c * dx + s * dy, -s * dx + c * dy]) if dx.size else np.zeros((0, 2))


def zellen_im_streifen(daten, breite: int, hoehe: int, zelle_m: float,
                       ursprung_xy: Sequence[float], start: Sequence[float],
                       richtung_rad: float, *, von_m: float, bis_m: float,
                       halb_m: float = STREIFEN_HALB_M, belegt: int = 100) -> np.ndarray:
    """Belegte Zellen eines Rasters in einem Streifen entlang einer Richtung.

    Rückgabe ``N x 2``: je Zelle (Meter voraus ab ``start``, Meter seitlich,
    links positiv), nach „voraus“ geordnet. Gilt für die Kostenkarte
    (belegt = 100) und für die Karte des SLAM (belegt = 100).
    """
    feld = np.asarray(daten, dtype=np.int16)
    if feld.size != breite * hoehe or zelle_m <= 0.0:
        raise ValueError('Raster: Größe passt nicht')
    index = np.flatnonzero(feld >= belegt)
    if index.size == 0:
        return np.zeros((0, 2))
    x = float(ursprung_xy[0]) + (index % breite + 0.5) * zelle_m - float(start[0])
    y = float(ursprung_xy[1]) + (index // breite + 0.5) * zelle_m - float(start[1])
    c, s = math.cos(richtung_rad), math.sin(richtung_rad)
    voraus, seitlich = c * x + s * y, -s * x + c * y
    rand = 0.5 * zelle_m
    drin = ((voraus >= von_m - rand) & (voraus <= bis_m + rand)
            & (np.abs(seitlich) <= halb_m))
    zellen = np.column_stack([voraus[drin], seitlich[drin]])
    return zellen[np.argsort(zellen[:, 0], kind='stable')]


def belegt_auf_dem_weg(daten, breite: int, hoehe: int, zelle_m: float,
                       ursprung_xy: Sequence[float], pose: Sequence[float],
                       punkte: Sequence[Sequence[float]], *, belegt: int = 100) -> Optional[dict]:
    """Die erste Stelle der Kostenkarte, an der der Erkunder auf diesem Weg anhielte.

    ``pose`` und ``punkte`` im Kartenrahmen. Je Strecke wird der Streifen
    geprüft, den der Nahbereichs-Halt sieht: in Fahrzeugbreite von der
    Vorderkante bis 0,25 m davor, über die ganze Strecke und am Ende noch
    so weit voraus. Rückgabe ``None``, wenn der Weg frei ist, sonst Strecke,
    Lage zur Linie (voraus ab Streckenbeginn, seitlich), Länge der Strecke
    (``strecke_m``), Meter ab dem Start und der Ort im Kartenrahmen. Liegt
    die Stelle hinter dem Ende ihrer Strecke im Fahrstreifen einer folgenden
    (bei der Durchfahrt geht es am Zwischenpunkt geradeaus weiter), stehen
    deren Nummer (``folgestrecke``) und die Meter ab dem Zwischenpunkt
    (``auf_folgestrecke_m``) dabei.
    """
    vorher = (float(pose[0]), float(pose[1]))
    zurueck = 0.0
    for nummer, ziel in enumerate(punkte, start=1):
        dx, dy = float(ziel[0]) - vorher[0], float(ziel[1]) - vorher[1]
        laenge = math.hypot(dx, dy)
        if laenge < 1e-6:
            continue
        richtung = math.atan2(dy, dx)
        zellen = zellen_im_streifen(daten, breite, hoehe, zelle_m, ursprung_xy, vorher,
                                    richtung, von_m=VORDERKANTE_M,
                                    bis_m=laenge + NAHHALT_BIS_M, belegt=belegt)
        if zellen.size:
            voraus, seitlich = (float(v) for v in zellen[0])
            c, s = math.cos(richtung), math.sin(richtung)
            ort = (vorher[0] + c * voraus - s * seitlich, vorher[1] + s * voraus + c * seitlich)
            befund = {'strecke': nummer, 'voraus_m': voraus, 'seitlich_m': seitlich,
                      'strecke_m': laenge, 'ab_start_m': zurueck + voraus, 'ort': ort}
            folge = (_auf_folgestrecke(ort, ziel, punkte[nummer:]) if voraus > laenge
                     else None)
            if folge is not None:
                befund['folgestrecke'] = nummer + folge[0]
                befund['auf_folgestrecke_m'] = folge[1]
            return befund
        zurueck += laenge
        vorher = (float(ziel[0]), float(ziel[1]))
    return None


def _auf_folgestrecke(ort: Sequence[float], anfang: Sequence[float],
                      folgende: Sequence[Sequence[float]],
                      halb_m: float = STREIFEN_HALB_M) -> Optional[Tuple[int, float]]:
    """(wievielte folgende Strecke, Meter ab ``anfang``), wenn ``ort`` in ihrem
    Fahrstreifen liegt (längs zwischen Anfang und Ende); sonst None."""
    vorher = (float(anfang[0]), float(anfang[1]))
    zurueck = 0.0
    for k, ziel in enumerate(folgende, start=1):
        dx, dy = float(ziel[0]) - vorher[0], float(ziel[1]) - vorher[1]
        laenge = math.hypot(dx, dy)
        if laenge < 1e-6:
            continue
        c, s = dx / laenge, dy / laenge
        ox, oy = float(ort[0]) - vorher[0], float(ort[1]) - vorher[1]
        laengs, quer = c * ox + s * oy, -s * ox + c * oy
        if 0.0 <= laengs <= laenge and abs(quer) <= halb_m:
            return k, zurueck + laengs
        zurueck += laenge
        vorher = (float(ziel[0]), float(ziel[1]))
    return None


def wolke_xyz(daten, felder: dict, punkt_schritt: int, anzahl: int,
              grossendian: bool = False) -> np.ndarray:
    """Punkte einer PointCloud2 als ``N x 3`` (x, y, z), ohne ungültige.

    ``felder``: Name -> (Versatz, Datentyp) mit den Datentypen von
    PointCloud2 (7 = float32, 8 = float64).
    """
    typen = {7: 'f4', 8: 'f8'}
    try:
        formate = [('>' if grossendian else '<') + typen[felder[n][1]] for n in 'xyz']
    except KeyError as fehler:
        raise ValueError(f'Punktwolke: Feld oder Datentyp fehlt ({fehler})') from fehler
    roh = bytes(daten)
    if anzahl <= 0 or punkt_schritt <= 0:
        return np.zeros((0, 3))
    if len(roh) < anzahl * punkt_schritt:
        raise ValueError('Punktwolke: zu wenige Daten')
    art = np.dtype({'names': ['x', 'y', 'z'], 'formats': formate,
                    'offsets': [int(felder[n][0]) for n in 'xyz'],
                    'itemsize': int(punkt_schritt)})
    feld = np.frombuffer(roh, dtype=art, count=anzahl)
    punkte = np.column_stack([feld['x'], feld['y'], feld['z']]).astype(float)
    return punkte[np.all(np.isfinite(punkte), axis=1)]


def in_den_boden(punkte: np.ndarray, boden_von_sensor: np.ndarray) -> np.ndarray:
    """Punkte aus dem Sensorrahmen in den Bodenrahmen unter base_link.

    ``boden_von_sensor``: 4 x 4 aus ``geometrie.aus_tf`` (TF base_link ->
    Sensor, base_link ``BASIS_UEBER_BODEN_M`` über dem Boden). Ergebnis:
    (voraus, seitlich, Höhe über dem Boden).
    """
    punkte = np.asarray(punkte, dtype=float).reshape(-1, 3)
    if punkte.size == 0:
        return np.zeros((0, 3))
    homogen = np.column_stack([punkte, np.ones(len(punkte))])
    return (homogen @ np.asarray(boden_von_sensor, dtype=float).T)[:, :3]


def nahe_punkte(punkte, stelle: Sequence[float], radius_m: float) -> np.ndarray:
    """Die Punkte (erste zwei Spalten: voraus, seitlich) nahe einer Stelle."""
    feld = np.asarray(punkte, dtype=float)
    if feld.size == 0:
        return feld.reshape(0, feld.shape[1] if feld.ndim == 2 else 2)
    abstand = np.hypot(feld[:, 0] - float(stelle[0]), feld[:, 1] - float(stelle[1]))
    return feld[abstand <= radius_m]


def herkunft(stelle: Sequence[float], *, karte=None, nah=None, laser=None,
             radius_m: float = 0.07) -> dict:
    """Welche Quelle an einer Stelle vor dem Roboter etwas sieht.

    Alles im Rahmen des Roboters (voraus, seitlich ab der Antriebsmitte):
    ``karte`` belegte Zellen der SLAM-Karte (N x 2), ``nah`` je Seite die
    Punkte der Nahsensoren (N x 3, dritte Spalte Höhe über dem Boden),
    ``laser`` Punkte des Lasers (N x 2). ``None`` heißt: nicht empfangen.
    Der Radius deckt die Rasterung der Kostenkarte und die Breite einer
    Messzone der Nahsensoren ab.
    """
    befund = {'stelle': (float(stelle[0]), float(stelle[1]))}
    befund['karte'] = None if karte is None else int(len(nahe_punkte(karte, stelle, radius_m)))
    befund['laser'] = None if laser is None else int(len(nahe_punkte(laser, stelle, radius_m)))
    befund['nah'] = {}
    for seite, punkte in (nah or {}).items():
        if punkte is None:
            befund['nah'][seite] = None
            continue
        treffer = nahe_punkte(punkte, stelle, radius_m)
        befund['nah'][seite] = (int(len(treffer)),
                                float(treffer[:, 2].min()) if len(treffer) else None,
                                float(treffer[:, 2].max()) if len(treffer) else None)
    return befund


def herkunft_text(befund: dict) -> str:
    """Der Befund aus ``herkunft`` in einem Satz."""
    voraus, seitlich = befund['stelle']
    teile = []
    if befund['karte'] is None:
        teile.append('Karte (SLAM) nicht empfangen')
    else:
        teile.append(f'Karte (SLAM) {"belegt" if befund["karte"] else "frei"}')
    for seite in ('links', 'rechts'):
        wert = befund['nah'].get(seite, None) if befund['nah'] else None
        if wert is None:
            teile.append(f'Nahsensor {seite} nicht empfangen')
        elif wert[0] == 0:
            teile.append(f'Nahsensor {seite} sieht dort nichts')
        else:
            teile.append(f'Nahsensor {seite} {wert[0]} Punkt(e), {100 * wert[1]:.0f} bis '
                         f'{100 * wert[2]:.0f} cm über dem Boden')
    if befund['laser'] is None:
        teile.append('Laser nicht empfangen')
    else:
        teile.append(f'Laser {"sieht dort etwas" if befund["laser"] else "sieht dort nichts"}')
    keiner = (not befund['karte'] and not befund['laser']
              and not any(w and w[0] for w in (befund['nah'] or {}).values()))
    ohne_nahsensoren = all((befund['nah'] or {}).get(seite) is None
                           for seite in ('links', 'rechts'))
    # Nicht empfangen ist nicht „frei“: dann lässt sich nichts gegeneinander prüfen.
    fehlt = [name for name, wert in (('Karte (SLAM)', befund['karte']),
                                     ('Laser', befund['laser'])) if wert is None]
    text = f'Herkunft der Stelle {lage_vom_roboter(voraus, seitlich)}: ' + '; '.join(teile)
    if keiner and fehlt:
        text += f' – {" und ".join(fehlt)} nicht empfangen: Herkunft offen'
    elif keiner and ohne_nahsensoren:
        # Ohne Nahsensoren kommt die Kostenkarte nur aus der Karte (SLAM).
        text += (' – keine Quelle sieht dort jetzt etwas, und ohne Nahsensoren stammt die '
                 'Kostenkarte nur aus der Karte (SLAM): Prüfung widersprüchlich, vermutlich '
                 'verschiedene Zeitstände von Karte und Kostenkarte')
    elif keiner:
        text += (' – keine Quelle sieht dort jetzt etwas: eine ältere Markierung, '
                 'vermutlich der Nahsensoren (die räumen erst ab 0,45 m)')
    return text + '.'


def nah_text(nah: Optional[dict], *, bis_m: float = 1.0, halb_m: float = STREIFEN_HALB_M) -> str:
    """Was die Nahsensoren gerade im Fahrstreifen sehen, in einem Satz."""
    if not nah:
        return 'Nahsensoren im Fahrstreifen: nicht empfangen.'
    teile = []
    for seite in ('links', 'rechts'):
        punkte = nah.get(seite)
        if punkte is None:
            teile.append(f'{seite} nicht empfangen')
            continue
        feld = np.asarray(punkte, dtype=float).reshape(-1, 3)
        drin = feld[(feld[:, 0] >= VORDERKANTE_M - 0.05) & (feld[:, 0] <= bis_m)
                    & (np.abs(feld[:, 1]) <= halb_m)]
        if not len(drin):
            teile.append(f'{seite} nichts')
            continue
        naechster = drin[int(np.argmin(drin[:, 0]))]
        teile.append(
            f'{seite} {len(drin)} Punkt(e), der nächste {naechster[0] - VORDERKANTE_M:.2f} m '
            f'vor der Vorderkante ({_vor_dem_gehaeuse(naechster[0])}), {abs(naechster[1]):.2f} m '
            f'{"links" if naechster[1] >= 0 else "rechts"} der Mitte, Höhe '
            f'{100 * drin[:, 2].min():.0f} bis {100 * drin[:, 2].max():.0f} cm über dem Boden')
    return 'Nahsensoren im Fahrstreifen: ' + '; '.join(teile) + '.'


def weg_belegt_text(befund: Optional[dict], laenge_m: float) -> str:
    """Ob die Kostenkarte auf dem ganzen Weg frei ist, in einem Satz."""
    if befund is None:
        return (f'Kostenkarte auf dem ganzen Weg ({laenge_m:.2f} m und den Nahbereich '
                'dahinter): frei – Kostenkarte passt.')
    text = (f'Kostenkarte auf dem Weg: belegt {befund["ab_start_m"]:.2f} m voraus '
            f'(Strecke {befund["strecke"]}), {abs(befund["seitlich_m"]):.2f} m '
            f'{"links" if befund["seitlich_m"] >= 0 else "rechts"} der Linie')
    strecke = befund.get('strecke_m')
    hinter = None if strecke is None else befund['voraus_m'] - strecke
    folge = befund.get('folgestrecke')
    auf_folge = (None if folge is None else
                 f'Strecke {folge}, {befund["auf_folgestrecke_m"]:.2f} m nach dem Zwischenpunkt')
    if hinter is not None and hinter >= VORDERKANTE_M and auf_folge:
        # Bei der Durchfahrt geht es am Zwischenpunkt geradeaus weiter: auf dem Weg.
        text += f'. Die Stelle liegt auf {auf_folge}, also auf dem Weg'
    elif hinter is not None and hinter >= VORDERKANTE_M:
        # Hinter dem Ende der Strecke: nicht auf dem Weg, aber im Blick des
        # Nahbereichs-Halts, der auch auf den letzten Zentimetern so weit schaut.
        text += (f'. Die Stelle liegt nicht auf der Strecke, sondern {hinter:.2f} m hinter '
                 f'ihrem Ende, wo er sich dreht oder hält; dort läge sie '
                 f'{hinter - GEHAEUSE_VORN_M:.2f} m vor seinem Gehäuse und '
                 f'{hinter - VORDERKANTE_M:.2f} m vor der gepolsterten Vorderkante')
    elif hinter is not None and hinter > 0.0:
        # So knapp dahinter überfährt die Vorderkante sie am Ende der Strecke.
        text += (f'. Die Stelle liegt {hinter:.2f} m hinter dem Ende der Strecke, so nah, dass '
                 'seine Vorderkante sie am Ende überfahren würde')
        if auf_folge:
            text += f'; sie liegt auch auf {auf_folge}'
    return text + (' – Kostenkarte passt nicht: dort könnte der Nahbereichs-Halt des '
                   'Erkunders anhalten.')


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
              bemerkung: Optional[str] = None, weiter: bool = False) -> str:
    """Das Fahrziel als Text für den Erkunder.

    ``quelle`` sagt, wer gewählt hat: ``ki``, ``mensch`` oder ``test``. Der
    Erkunder schreibt sie in seine Meldungen, damit jede Fahrt zeigt, wer
    entschieden hat. ``weiter``: Nach diesem Ziel folgt in derselben Mission
    ein Folgeziel (Anfahrt, dann Durchfahrt).
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
    if weiter:
        daten['weiter'] = True
    return json.dumps(daten, ensure_ascii=False)


def ende_botschaft(*, kennung: str, quelle: str, zeit_s: float, frame: str = 'map') -> str:
    """Das Ende des Wartens als Text: Es kommt kein (weiteres) Fahrziel.

    Der Erkunder schließt die Mission dann sofort ab, statt bis zum Ablauf
    seiner Wartefrist stehen zu bleiben.
    """
    if quelle not in QUELLEN:
        raise ValueError(f'Ende: Quelle {quelle!r} unbekannt')
    if not kennung or len(kennung) > 80:
        raise ValueError('Ende: Kennung fehlt oder ist zu lang')
    return json.dumps({'ende': True, 'kennung': kennung, 'quelle': quelle, 'frame': frame,
                       'zeit_s': float(zeit_s)}, ensure_ascii=False)
