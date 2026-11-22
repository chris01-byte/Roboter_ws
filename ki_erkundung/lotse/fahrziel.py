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
