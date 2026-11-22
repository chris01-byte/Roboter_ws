"""Fahrziel: aus einer gewählten Öffnung zwei Punkte für die Etappenfahrt.

Die KI nennt nur eine Nummer. Aus der dazu vermessenen Öffnung rechnet der
Roboter hier selbst zwei Punkte auf der Türachse: einen **Vorpunkt** vor der
Tür und einen **Auslaufpunkt** dahinter. Der Erkunder fährt sie in kurzen
geraden Etappen an (Anschlussstelle ``stage_drive_only``), prüft vor jeder
Etappe den Streifen vor sich und behält seine ganze Schutzkette.

Dieses Modul rechnet nur; es sendet nichts und kennt kein ROS.
"""
from __future__ import annotations

import json
import math
from typing import List, Optional, Sequence, Tuple

Punkt = Tuple[float, float]

QUELLEN = ('ki', 'mensch', 'test')

# Grenzen wie im Erkunder (src/explore/explore/stage_drive.py, StageLimits).
# Hier nur, damit ein zu weites Ziel schon vor dem Senden mit Maß auffällt;
# geprüft wird im Erkunder ohnehin noch einmal.
MAX_PUNKTE = 3
MIN_STRECKE_M = 0.10
MAX_STRECKE_M = 2.5
MAX_GESAMT_M = 4.0

# Antriebsmitte bis Vorderkante 0,27 m, bis Hinterkante 0,11 m. Der Vorpunkt
# liegt 1,1 m vor der Türlinie: Ein Türblatt, das in den Raum hinein offen
# steht (bis 0,9 m lang), endet davor; richtet sich der Roboter am Vorpunkt
# aus, schwenken seine Ecken (0,39 m um die Antriebsmitte) nicht bis ans
# Blatt. Am Auslaufpunkt ist die Hinterkante knapp einen halben Meter durch.
VOR_DER_TUER_M = 1.10
HINTER_DER_TUER_M = 0.60
MIN_BREITE_M = 0.60
# Als Tür gilt für eine Durchfahrt nur, was so breit vermessen ist. Breiter
# vermessene „Türen“ sind falsch vermessen (Befund KI-F1: 1,25 m statt
# 0,85 m bei schrägem Blick); ihre Achse stimmt dann nicht.
TUER_MIN_M = 0.65
TUER_MAX_M = 0.95


def tuer_punkte(pfosten: Sequence[Sequence[float]],
                standpunkt: Sequence[float] = (0.0, 0.0), *,
                vor_m: float = VOR_DER_TUER_M,
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


def durch_die_tuer(pfosten: Sequence[Sequence[float]], pose: Sequence[float], *,
                   vor_m: float = VOR_DER_TUER_M, hinter_m: float = HINTER_DER_TUER_M,
                   vorpunkt_ab_m: float = 0.15) -> List[Punkt]:
    """Vorpunkt und Auslaufpunkt im Kartenrahmen.

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
