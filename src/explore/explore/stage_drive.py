"""Etappenfahrt: Rechenregeln für kurze gerade Etappen zu vorgegebenen Punkten.

Reine Funktionen ohne ROS. Der Erkunder fährt damit ohne Nav2 von Punkt zu
Punkt: auf den Punkt ausrichten (Drehen auf der Stelle), eine gerade, vom
Laser gemessene Etappe fahren, neu messen, wiederholen. Die Bewegungen
selbst kommen aus den vorhandenen, am 10./11.09.2026 real bestandenen
Bausteinen des Erkunders (``_rotate_in_place``, ``_drive_forward_lidar``).

Das Fahrziel liefert die getrennte Linie ``ki_erkundung`` als Text (JSON).
Hier wird es geprüft; angenommen wird nur, was vollständig, frisch und
innerhalb fester Grenzen ist.
"""

import json
import math
from dataclasses import dataclass
from typing import Optional, Tuple

import numpy as np


@dataclass(frozen=True)
class StageLimits:
    """Feste Grenzen eines Fahrziels."""

    max_points: int = 3
    min_leg_m: float = 0.10
    max_leg_m: float = 2.5
    max_total_m: float = 4.0
    max_age_s: float = 30.0

    def __post_init__(self):
        werte = (self.min_leg_m, self.max_leg_m, self.max_total_m, self.max_age_s)
        if (
                isinstance(self.max_points, bool)
                or not isinstance(self.max_points, int)
                or not 1 <= self.max_points <= 5
                or not all(math.isfinite(w) and w > 0.0 for w in werte)
                or self.min_leg_m >= self.max_leg_m
                or self.max_total_m < self.max_leg_m):
            raise ValueError('stage_limits_invalid')


@dataclass(frozen=True)
class StageTarget:
    """Ein geprüftes Fahrziel: wer es gewählt hat und die Punkte im Kartenframe.

    ``weiter``: Nach diesem Ziel folgt in derselben Mission ein Folgeziel
    (zum Beispiel erst die Anfahrt vor die Tür, dann die Durchfahrt). Ohne
    die Angabe endet die Mission nach dem Ziel wie bisher.
    """

    kennung: str
    quelle: str
    punkte: Tuple[Tuple[float, float], ...]
    laenge_m: float
    weiter: bool = False


@dataclass(frozen=True)
class StageEnd:
    """Die KI-Linie beendet das Warten: Es kommt kein (weiteres) Fahrziel."""

    kennung: str
    quelle: str


QUELLEN = ('ki', 'mensch', 'test')


def _zahl(wert) -> float:
    if isinstance(wert, bool) or not isinstance(wert, (int, float)):
        raise ValueError('target_point_invalid')
    zahl = float(wert)
    if not math.isfinite(zahl):
        raise ValueError('target_point_invalid')
    return zahl


def parse_stage_target(
        text: str, *, frame: str, now_s: float,
        start_xy: Tuple[float, float], limits: StageLimits) -> StageTarget:
    """Prüfe ein Fahrziel; bei jedem Mangel ``ValueError`` mit dem Grund.

    Erwartet wird ein JSON-Objekt mit ``kennung`` (Text), ``quelle`` (wer
    gewählt hat: ``ki``, ``mensch`` oder ``test``), ``frame`` (muss der
    Kartenframe sein), ``zeit_s`` (Sendezeit, Sekunden seit 1970) und
    ``punkte`` (ein bis ``max_points`` Paare ``[x, y]`` in Metern).
    """
    try:
        daten = json.loads(text)
    except (TypeError, ValueError) as fehler:
        raise ValueError('target_not_json') from fehler
    if not isinstance(daten, dict):
        raise ValueError('target_not_object')

    kennung = daten.get('kennung')
    if not isinstance(kennung, str) or not 1 <= len(kennung) <= 80:
        raise ValueError('target_id_invalid')
    quelle = daten.get('quelle')
    if quelle not in QUELLEN:
        raise ValueError('target_source_invalid')
    if daten.get('frame') != frame:
        raise ValueError('target_frame_mismatch')

    zeit = daten.get('zeit_s')
    if isinstance(zeit, bool) or not isinstance(zeit, (int, float)):
        raise ValueError('target_time_invalid')
    alter = float(now_s) - float(zeit)
    if not math.isfinite(alter) or alter < -2.0:
        raise ValueError('target_time_invalid')
    if alter > limits.max_age_s:
        raise ValueError('target_stale')

    weiter = daten.get('weiter', False)
    if not isinstance(weiter, bool):
        raise ValueError('target_continue_invalid')

    roh = daten.get('punkte')
    if not isinstance(roh, list) or not 1 <= len(roh) <= limits.max_points:
        raise ValueError('target_point_count_invalid')
    punkte = []
    for eintrag in roh:
        if not isinstance(eintrag, (list, tuple)) or len(eintrag) != 2:
            raise ValueError('target_point_invalid')
        punkte.append((_zahl(eintrag[0]), _zahl(eintrag[1])))

    vorher = (_zahl(start_xy[0]), _zahl(start_xy[1]))
    gesamt = 0.0
    for nummer, punkt in enumerate(punkte):
        strecke = math.hypot(punkt[0] - vorher[0], punkt[1] - vorher[1])
        # Der erste Punkt darf dort liegen, wo der Roboter schon steht; dann
        # wird dorthin nicht gefahren. Jeder weitere braucht eine Mindestlänge.
        if strecke > limits.max_leg_m:
            raise ValueError('target_leg_too_long')
        if nummer > 0 and strecke < limits.min_leg_m:
            raise ValueError('target_leg_too_short')
        gesamt += strecke
        vorher = punkt
    if gesamt > limits.max_total_m:
        raise ValueError('target_total_too_long')
    if gesamt < limits.min_leg_m:
        raise ValueError('target_total_too_short')
    return StageTarget(kennung, quelle, tuple(punkte), gesamt, weiter)


def parse_stage_message(
        text: str, *, frame: str, now_s: float,
        start_xy: Tuple[float, float], limits: StageLimits):
    """Ein Fahrziel (``StageTarget``) oder das Ende des Wartens (``StageEnd``).

    Das Ende ist ein JSON-Objekt mit ``"ende": true``, ``kennung``,
    ``quelle``, ``frame`` und ``zeit_s`` wie beim Fahrziel, ohne Punkte. Es
    wird genauso streng auf Herkunft und Alter geprüft.
    """
    try:
        daten = json.loads(text)
    except (TypeError, ValueError) as fehler:
        raise ValueError('target_not_json') from fehler
    if not isinstance(daten, dict):
        raise ValueError('target_not_object')
    if 'ende' not in daten:
        return parse_stage_target(
            text, frame=frame, now_s=now_s, start_xy=start_xy, limits=limits)
    if daten.get('ende') is not True or 'punkte' in daten:
        raise ValueError('end_invalid')
    kennung = daten.get('kennung')
    if not isinstance(kennung, str) or not 1 <= len(kennung) <= 80:
        raise ValueError('target_id_invalid')
    quelle = daten.get('quelle')
    if quelle not in QUELLEN:
        raise ValueError('target_source_invalid')
    if daten.get('frame') != frame:
        raise ValueError('target_frame_mismatch')
    zeit = daten.get('zeit_s')
    if isinstance(zeit, bool) or not isinstance(zeit, (int, float)):
        raise ValueError('target_time_invalid')
    alter = float(now_s) - float(zeit)
    if not math.isfinite(alter) or alter < -2.0:
        raise ValueError('target_time_invalid')
    if alter > limits.max_age_s:
        raise ValueError('target_stale')
    return StageEnd(kennung, quelle)


def normalize_angle(winkel: float) -> float:
    return math.atan2(math.sin(winkel), math.cos(winkel))


def next_stage(
        pose: Tuple[float, float, float], waypoint: Tuple[float, float], *,
        arrive_tolerance_m: float, aim_min_distance_m: float,
        align_tolerance_rad: float, stage_max_m: float) -> Tuple[str, float]:
    """Nächster Schritt zum Wegpunkt: angekommen, ausrichten oder fahren.

    Rückgabe ``('arrived', rest_m)``, ``('align', winkel_rad)`` oder
    ``('drive', laenge_m)``. Nahe am Punkt wird nicht mehr neu gezielt (dort
    macht ein kleiner Seitenversatz einen großen Winkel); gefahren wird dann
    nur noch der Rest entlang der eigenen Blickrichtung. Längere Strecken
    werden in gleich lange Etappen bis ``stage_max_m`` geteilt.
    """
    werte = (
        *pose, *waypoint, arrive_tolerance_m, aim_min_distance_m,
        align_tolerance_rad, stage_max_m)
    if not all(isinstance(w, (int, float)) and math.isfinite(w) for w in werte):
        raise ValueError('stage_values_invalid')
    if (
            arrive_tolerance_m <= 0.0 or stage_max_m <= arrive_tolerance_m
            or aim_min_distance_m < arrive_tolerance_m
            or align_tolerance_rad <= 0.0):
        raise ValueError('stage_values_invalid')

    dx = waypoint[0] - pose[0]
    dy = waypoint[1] - pose[1]
    abstand = math.hypot(dx, dy)
    if abstand <= arrive_tolerance_m:
        return 'arrived', abstand
    fehler = normalize_angle(math.atan2(dy, dx) - pose[2])
    if abstand > aim_min_distance_m:
        if abs(fehler) > align_tolerance_rad:
            return 'align', fehler
        strecke = abstand
    else:
        strecke = abstand * math.cos(fehler)
        if strecke <= arrive_tolerance_m:
            return 'arrived', abstand
    etappen = max(1, math.ceil(strecke / stage_max_m - 1e-9))
    return 'drive', strecke / etappen


def obstacle_ahead_m(
        data, width: int, height: int, resolution: float,
        origin_xy: Tuple[float, float], pose: Tuple[float, float, float], *,
        front_m: float, reach_m: float, half_width_m: float,
        lethal: int = 100) -> Optional[float]:
    """Abstand der nächsten belegten Kostenkartenzelle vor der Vorderkante.

    Betrachtet wird der Streifen in Fahrzeugbreite von der Vorderkante
    (``front_m`` vor der Antriebsmitte) bis ``reach_m`` weiter. Gezählt
    werden nur wirklich belegte Zellen (``lethal``), nicht die aufgeblasene
    Umgebung; ein Türpfosten neben dem Streifen sperrt deshalb nicht. In
    der Kostenkarte stehen auch die Treffer der Nahsensoren (VL53), also
    niedrige Dinge, die der Laser in 0,75 m Höhe nicht sieht.

    Rückgabe: Abstand in Metern ab der Vorderkante oder ``None``, wenn der
    Streifen frei ist.
    """
    werte = (resolution, *origin_xy, *pose, front_m, reach_m, half_width_m)
    if (
            not all(isinstance(w, (int, float)) and math.isfinite(w) for w in werte)
            or resolution <= 0.0 or reach_m <= 0.0 or half_width_m <= 0.0
            or width <= 0 or height <= 0):
        raise ValueError('strip_values_invalid')
    grid = np.asarray(data, dtype=np.int16)
    if grid.size != width * height:
        raise ValueError('strip_grid_size_mismatch')
    index = np.flatnonzero(grid >= lethal)
    if index.size == 0:
        return None
    x = origin_xy[0] + (index % width + 0.5) * resolution - pose[0]
    y = origin_xy[1] + (index // width + 0.5) * resolution - pose[1]
    c, s = math.cos(pose[2]), math.sin(pose[2])
    voraus = c * x + s * y
    seitlich = -s * x + c * y
    # halbe Zelle Zuschlag: die Zelle zählt, sobald sie den Streifen berührt
    rand = 0.5 * resolution
    im_streifen = (
        (voraus >= front_m - rand) & (voraus <= front_m + reach_m + rand)
        & (np.abs(seitlich) <= half_width_m + rand))
    if not np.any(im_streifen):
        return None
    return max(0.0, float(np.min(voraus[im_streifen])) - front_m)
