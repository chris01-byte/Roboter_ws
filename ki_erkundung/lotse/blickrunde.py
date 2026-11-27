"""Blickrunde: Aufnahmeformat lesen/schreiben, Drehwinkel bestimmen, Bilder wählen.

Eine Blickrunde ist ein Ordner mit allem, was Amadeus an einem Standpunkt
während einer Drehung aufgenommen hat:

    meta.json            Beschreibung (Kamera, Montage, Liste der Aufnahmen)
    bild_000.jpg ...     Kamerabilder (JPEG, wie vom Kamera-Relay geliefert)
    tiefe_000.png ...    Tiefenbilder (16 Bit, Millimeter), optional
    scan_000.json ...    LiDAR-Scan zur selben Zeit, optional

Diese Ordner enthalten Bilder und Geometrie der echten Wohnung. Sie bleiben
auf Jetson und KI-Rechner und gehören nie ins Repository.

Der Drehwinkel jeder Aufnahme wird aus den Scans selbst bestimmt (ein
Freiheitsgrad: Drehung um die Antriebsmitte). Dadurch ist es gleich, ob
Amadeus mit dem Joystick oder von Hand gedreht wurde.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

from . import SCHEMA_VERSION
from .geometrie import Kamera, kamera_montage, lidar_montage, transformiere
from .kandidaten import lecks_schliessen


# ------------------------------------------------------------------ Scans

def scan_als_dict(winkel_min: float, winkel_schritt: float,
                  entfernungen: Sequence[float], bereich_min: float,
                  bereich_max: float, t: float, rahmen: str = 'laser_frame') -> dict:
    """Einen Scan in die gespeicherte Form bringen.

    Ungültige Werte (nan, zu nah) werden ``null``; „kein Echo“ (inf oder
    jenseits der Reichweite) steht als Indexliste in ``weit``.
    """
    werte: List[Optional[float]] = []
    weit: List[int] = []
    for i, wert in enumerate(entfernungen):
        wert = float(wert)
        if math.isnan(wert) or wert < bereich_min:
            werte.append(None)
        elif math.isinf(wert) or wert > bereich_max:
            werte.append(None)
            weit.append(i)
        else:
            werte.append(round(wert, 3))
    return {'t': float(t), 'rahmen': rahmen,
            'winkel_min': float(winkel_min),
            'winkel_schritt': float(winkel_schritt),
            'bereich_min': float(bereich_min),
            'bereich_max': float(bereich_max),
            'entfernungen': werte, 'weit': weit}


def scan_felder(scan: dict) -> Tuple[np.ndarray, np.ndarray]:
    """(Winkel, Entfernung) eines gespeicherten Scans; nan ungültig, inf weit."""
    r = np.array([np.nan if v is None else float(v)
                  for v in scan['entfernungen']], dtype=float)
    weit = np.asarray(scan.get('weit') or [], dtype=int)
    if weit.size:
        r[weit] = np.inf
    w = float(scan['winkel_min']) + float(scan['winkel_schritt']) * np.arange(len(r))
    return w, r


def scan_punkte(scan: dict, boden_lidar: np.ndarray, min_r: float = 0.4,
                max_r: float = 12.0) -> np.ndarray:
    """Messpunkte eines Scans als Nx2 im Bodenrahmen des Roboters."""
    w, r = scan_felder(scan)
    ok = np.isfinite(r) & (r >= min_r) & (r <= max_r)
    im_lidar = np.column_stack([r[ok] * np.cos(w[ok]), r[ok] * np.sin(w[ok]),
                                np.zeros(int(ok.sum()))])
    return transformiere(boden_lidar, im_lidar)[:, :2]


# ----------------------------------------------------------------- Raster

class _Raster:
    """Zählt, in wie vielen Aufnahmen eine Zelle getroffen wurde."""

    def __init__(self, halb_m: float = 12.0, zelle_m: float = 0.05):
        self.zelle = float(zelle_m)
        self.n = int(round(2 * halb_m / zelle_m))
        self.halb = self.n * self.zelle / 2.0
        self.zaehler = np.zeros((self.n, self.n), dtype=np.int32)

    def index(self, punkte: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        ix = np.floor((punkte[..., 0] + self.halb) / self.zelle).astype(int)
        iy = np.floor((punkte[..., 1] + self.halb) / self.zelle).astype(int)
        ok = (ix >= 0) & (ix < self.n) & (iy >= 0) & (iy < self.n)
        return ix, iy, ok

    def eintragen(self, punkte: np.ndarray) -> None:
        ix, iy, ok = self.index(punkte)
        einmal = np.zeros_like(self.zaehler, dtype=bool)
        einmal[iy[ok], ix[ok]] = True
        self.zaehler += einmal

    @staticmethod
    def _aufblasen(belegt: np.ndarray) -> np.ndarray:
        gross = belegt.copy()
        gross[1:, :] |= belegt[:-1, :]
        gross[:-1, :] |= belegt[1:, :]
        gross[:, 1:] |= belegt[:, :-1]
        gross[:, :-1] |= belegt[:, 1:]
        return gross

    def maske(self, min_treffer: int = 1) -> np.ndarray:
        return self.zaehler >= min_treffer

    def abstandsstufen(self, stufen: int) -> np.ndarray:
        """Je Zelle der Abstand zur nächsten belegten Zelle in Zellen.

        0 = belegt, 1..``stufen`` = so viele Zellen entfernt, ``stufen`` + 1
        = weiter weg.
        """
        aktuell = self.zaehler > 0
        stufe = np.full(aktuell.shape, stufen + 1, dtype=np.int16)
        stufe[aktuell] = 0
        for s in range(1, stufen + 1):
            gross = self._aufblasen(aktuell)
            stufe[gross & ~aktuell] = s
            aktuell = gross
        return stufe


def _drehe(punkte: np.ndarray, gier: np.ndarray) -> np.ndarray:
    """Nx2-Punkte um jeden Winkel aus ``gier`` drehen -> (G, N, 2)."""
    c, s = np.cos(gier)[:, None], np.sin(gier)[:, None]
    x, y = punkte[None, :, 0], punkte[None, :, 1]
    return np.stack([c * x - s * y, s * x + c * y], axis=-1)


def gier_schaetzen(scans: Sequence[dict], boden_lidar: np.ndarray,
                   vorgabe_rad: Optional[Sequence[Optional[float]]] = None,
                   fenster_grad: float = 30.0, grob_grad: float = 1.0,
                   fein_grad: float = 0.1) -> Tuple[np.ndarray, np.ndarray]:
    """Drehwinkel jeder Aufnahme gegenüber der ersten.

    Jede Aufnahme wird um die Antriebsmitte so gedreht, dass ihre Messpunkte
    am besten auf die bisher gesammelten Punkte fallen. ``vorgabe_rad``
    (zum Beispiel aus der Odometrie) dient nur als Startwert der Suche.

    Rückgabe: (Gier in rad, fortlaufend, erste Aufnahme 0; Güte 0..1 = Anteil
    der Messpunkte, die getroffen haben).
    """
    anzahl = len(scans)
    gier = np.zeros(anzahl)
    guete = np.ones(anzahl)
    if anzahl == 0:
        return gier, guete
    stufen = 5
    raster = _Raster(zelle_m=0.04)
    raster.eintragen(scan_punkte(scans[0], boden_lidar))
    vor = None
    if vorgabe_rad is not None and all(v is not None for v in vorgabe_rad):
        vor = np.unwrap(np.asarray(vorgabe_rad, dtype=float))
    for k in range(1, anzahl):
        punkte = scan_punkte(scans[k], boden_lidar)
        if len(punkte) < 30:
            gier[k], guete[k] = gier[k - 1], 0.0
            continue
        probe = punkte[::max(1, len(punkte) // 500)]
        if vor is not None:
            start = gier[k - 1] + (vor[k] - vor[k - 1])
        elif k >= 2:
            start = gier[k - 1] + (gier[k - 1] - gier[k - 2])
        else:
            start = gier[k - 1]
        stufe = raster.abstandsstufen(stufen)

        def abstand(punktfeld: np.ndarray, kandidaten: np.ndarray) -> np.ndarray:
            ix, iy, ok = raster.index(_drehe(punktfeld, kandidaten))
            ix, iy = np.clip(ix, 0, raster.n - 1), np.clip(iy, 0, raster.n - 1)
            return np.where(ok, stufe[iy, ix], stufen + 1)

        def wertung(kandidaten: np.ndarray) -> np.ndarray:
            # Je näher ein Messpunkt an der Sammlung liegt, desto mehr zählt er.
            # Das ergibt einen spitzen Höchstwert statt einer Hochebene.
            return (stufen + 1 - abstand(probe, kandidaten)).sum(axis=1)

        grob = start + np.radians(np.arange(-fenster_grad, fenster_grad + 1e-9, grob_grad))
        mitte = grob[int(np.argmax(wertung(grob)))]
        fein = mitte + np.radians(np.arange(-grob_grad, grob_grad + 1e-9, fein_grad))
        zahl = wertung(fein)
        # Bei Gleichstand die Mitte der besten Werte nehmen, nicht den ersten.
        beste = np.flatnonzero(zahl == zahl.max())
        gier[k] = float(fein[beste[len(beste) // 2]])
        gewaehlt = np.array([gier[k]])
        guete[k] = float(np.mean(abstand(probe, gewaehlt)[0] <= 1))
        if guete[k] >= 0.25:
            # Nur Neues eintragen (was bisher verdeckt war). Bekanntes bleibt
            # so scharf wie bei der ersten Beobachtung; sonst verschmiert die
            # Sammlung und die Winkel driften gemeinsam weg.
            neu_gesehen = abstand(punkte, gewaehlt)[0] >= 2
            if neu_gesehen.any():
                raster.eintragen(_drehe(punkte[neu_gesehen], gewaehlt)[0])
    return gier, guete


def bilder_waehlen(gier_rad: Sequence[float], anzahl: int = 8,
                   toleranz_grad: float = 12.0) -> dict:
    """Aus allen Aufnahmen die Bilder im gleichen Winkelabstand wählen.

    Bild 1 ist die erste Aufnahme; die weiteren folgen in Drehrichtung im
    Abstand 360°/``anzahl``. Liegen mehrere Aufnahmen gleich gut, gewinnt
    die ruhigste (kleinste Drehung zu den Nachbarn), wegen der Bildschärfe.
    """
    gier = np.asarray(gier_rad, dtype=float)
    if gier.size == 0:
        return {'bilder': [], 'vollstaendig': False, 'drehsinn': 0,
                'gedreht_grad': 0.0, 'ende_grad': 0.0}
    gesamt = float(gier[-1] - gier[0])
    weitester = float(gier[int(np.argmax(np.abs(gier - gier[0])))] - gier[0])
    drehsinn = 1 if weitester >= 0 else -1
    schritt = 2 * math.pi / anzahl
    unruhe = np.zeros(len(gier))
    if len(gier) >= 3:
        unruhe[1:-1] = np.abs(gier[2:] - gier[:-2])
        unruhe[0], unruhe[-1] = abs(gier[1] - gier[0]), abs(gier[-1] - gier[-2])
    bilder = []
    for j in range(anzahl):
        ziel = gier[0] + drehsinn * j * schritt
        abweichung = np.abs(gier - ziel)
        beste = float(abweichung.min())
        if math.degrees(beste) > toleranz_grad:
            continue
        nah = np.flatnonzero(abweichung <= beste + math.radians(3.0))
        k = int(nah[int(np.argmin(unruhe[nah]))])
        bilder.append({'bild': j + 1, 'aufnahme': k,
                       'gier_rad': float(gier[k] - gier[0]),
                       'soll_grad': round(math.degrees(drehsinn * j * schritt), 1),
                       'abweichung_grad': round(math.degrees(float(abweichung[k])), 1)})
    return {'bilder': bilder, 'vollstaendig': len(bilder) == anzahl,
            'drehsinn': drehsinn,
            'gedreht_grad': round(math.degrees(abs(weitester)), 1),
            'ende_grad': round(math.degrees(gesamt), 1)}


def profil_ursprung(gier_rad: Sequence[float], boden_lidar: np.ndarray,
                    stand_grad: float = 3.0) -> np.ndarray:
    """Der Punkt, von dem aus das Rundum-Profil gebildet wird (Standpunktrahmen).

    Hat sich der Roboter gedreht, ist es die Antriebsmitte: Das LiDAR
    umkreist sie und sieht jede Richtung einmal genau von dort aus. Stand er
    still, ist es der Ort des LiDAR selbst (24,5 cm vor der Antriebsmitte).
    Von der Antriebsmitte aus gesehen läge sonst hinter jeder nahen Kante
    ein Keil, den das LiDAR nie gesehen hat; das Profil hielte ihn für frei
    und die Vermessung fände dort Scheinöffnungen oder falsche Pfosten.
    """
    gier = np.asarray(gier_rad, dtype=float)
    if gier.size == 0 or float(np.max(np.abs(gier - gier[0]))) > math.radians(stand_grad):
        return np.zeros(2)
    mittel = float(np.mean(gier))
    c, s = math.cos(mittel), math.sin(mittel)
    x, y = float(boden_lidar[0, 3]), float(boden_lidar[1, 3])
    return np.array([c * x - s * y, s * x + c * y])


def rundum_profil(scans: Sequence[dict], gier_rad: Sequence[float],
                  boden_lidar: np.ndarray, bins: int = 720,
                  zelle_m: float = 0.04, reichweite_m: float = 8.0,
                  min_aufnahmen: int = 2, min_anteil: float = 0.15,
                  ursprung: Optional[Sequence[float]] = None
                  ) -> Tuple[np.ndarray, np.ndarray]:
    """Rundum-Profil des Standpunkts aus allen Scans einer Blickrunde.

    Alle Messpunkte werden in den Standpunktrahmen gedreht und in ein Raster
    eingetragen. Eine Zelle gilt als belegt, wenn mindestens
    ``min_aufnahmen`` Aufnahmen und mindestens der Anteil ``min_anteil``
    aller Aufnahmen sie getroffen haben (bei weniger als vier Aufnahmen
    genügt eine). Der Anteil hält die Kanten scharf: Kleine Winkelfehler
    verschmieren jede Kante über Nachbarzellen, die aber nur selten
    getroffen werden; ohne ihn würde jede Öffnung einige Zentimeter zu schmal.
    Danach wird vom Punkt ``ursprung`` aus (ohne Angabe die Antriebsmitte,
    siehe ``profil_ursprung``) je Richtung die erste belegte Zelle gesucht.

    Rückgabe: (Richtungen, Entfernung ab ``ursprung``); ``nan`` = Richtung
    nie beobachtet, ``inf`` = frei bis zur Reichweite.
    """
    start = np.zeros(2) if ursprung is None else np.asarray(ursprung, dtype=float)
    raster = _Raster(halb_m=reichweite_m + 1.0, zelle_m=zelle_m)
    schritt = 2 * math.pi / bins
    abgedeckt = np.zeros(bins, dtype=bool)
    lidar_gier = math.atan2(boden_lidar[1, 0], boden_lidar[0, 0])
    for scan, gier in zip(scans, gier_rad):
        punkte = scan_punkte(scan, boden_lidar, min_r=0.15,
                             max_r=reichweite_m + 0.5)
        if len(punkte):
            raster.eintragen(_drehe(punkte, np.array([float(gier)]))[0])
        w, r = scan_felder(scan)
        gesehen = w[~np.isnan(r)] + lidar_gier + float(gier)
        idx = np.floor(((gesehen + math.pi) % (2 * math.pi)) / schritt).astype(int) % bins
        abgedeckt[idx] = True
    # Zwischen zwei LiDAR-Strahlen liegende Richtungen nicht als Lücke werten.
    abgedeckt = abgedeckt | np.roll(abgedeckt, 1) | np.roll(abgedeckt, -1)
    schwelle = (max(min_aufnahmen, int(round(min_anteil * len(scans))))
                if len(scans) >= 4 else 1)
    belegt = raster.maske(min_treffer=schwelle)
    winkel = -math.pi + (np.arange(bins) + 0.5) * schritt
    weg = np.arange(0.10, reichweite_m, zelle_m / 2.0)
    strahlen = np.stack([start[0] + np.outer(np.cos(winkel), weg),
                         start[1] + np.outer(np.sin(winkel), weg)], axis=-1)
    ix, iy, ok = raster.index(strahlen)
    ix, iy = np.clip(ix, 0, raster.n - 1), np.clip(iy, 0, raster.n - 1)
    treffer = belegt[iy, ix] & ok
    erster = np.argmax(treffer, axis=1)
    r = np.where(treffer.any(axis=1), weg[erster], np.inf)
    r[~abgedeckt] = np.nan
    return winkel, lecks_schliessen(r)


def stand_profil(scans: Sequence[dict], gier_rad: Sequence[float],
                 boden_lidar: np.ndarray, bins: int = 720,
                 reichweite_m: float = 8.0) -> Tuple[np.ndarray, np.ndarray]:
    """Profil für Aufnahmen im Stand: je Richtung der Median aller Messungen.

    Stand der Roboter still, hat das LiDAR jede Richtung vom selben Punkt
    viele Male gemessen. Dann braucht es kein Raster: Der Median je Richtung
    ist auf wenige Millimeter genau. Das Raster (4 cm Zellen, 2 cm Schritt)
    verschiebt jeden Wandpunkt um bis zu einige Zentimeter; an echten
    Aufnahmen (KI-0N, 21.11.2026) wurde so an den meisten Türpfosten keine
    gerade Wand mehr erkannt, und die Regeln für schräg gesehene Türen und
    offene Türblätter griffen nicht.

    Rückgabe wie ``rundum_profil``, gesehen vom Ort des LiDAR
    (``profil_ursprung``): ``nan`` = nicht beobachtet, ``inf`` = kein Echo.
    """
    schritt = 2 * math.pi / bins
    lidar_gier = math.atan2(boden_lidar[1, 0], boden_lidar[0, 0])
    gemessen: List[List[float]] = [[] for _ in range(bins)]
    strahlen = np.zeros(bins, dtype=int)
    weit = np.zeros(bins, dtype=int)
    for scan, gier in zip(scans, gier_rad):
        w, r = scan_felder(scan)
        # Der kleine Zuschlag hält Strahlen, die genau auf einer Fachgrenze
        # liegen, trotz Rundung im selben Fach.
        fach = np.floor(((w + lidar_gier + float(gier) + math.pi) % (2 * math.pi))
                        / schritt + 1e-6).astype(int) % bins
        np.add.at(strahlen, fach, 1)
        np.add.at(weit, fach[np.isinf(r) | (r > reichweite_m)], 1)
        gut = np.isfinite(r) & (r >= 0.15) & (r <= reichweite_m)
        for f, wert in zip(fach[gut], r[gut]):
            gemessen[int(f)].append(float(wert))
    profil = np.full(bins, np.nan)
    for i in range(bins):
        if strahlen[i] == 0:
            continue
        if 2 * len(gemessen[i]) >= strahlen[i]:
            profil[i] = float(np.median(gemessen[i]))
        elif 2 * weit[i] >= strahlen[i]:
            profil[i] = np.inf
    # Ein einzelnes Fach, in das kein Strahl fiel (gröberes LiDAR als das
    # Fachraster), übernimmt den ferneren seiner Nachbarn.
    davor, danach = np.roll(profil, 1), np.roll(profil, -1)
    leer = (strahlen == 0) & ~np.isnan(davor) & ~np.isnan(danach)
    profil[leer] = np.maximum(davor, danach)[leer]
    winkel = -math.pi + (np.arange(bins) + 0.5) * schritt
    return winkel, lecks_schliessen(profil)


def profil_der_runde(scans: Sequence[dict], gier_rad: Sequence[float],
                     boden_lidar: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Das Profil einer Blickrunde auf dem jeweils genaueren Weg.

    Im Stand direkt aus den Messungen (``stand_profil``), nach einer Drehung
    über das Raster von der Antriebsmitte aus (``rundum_profil``).

    Rückgabe: (Richtungen, Entfernung, Ursprung des Profils im Standpunktrahmen).
    """
    ursprung = profil_ursprung(gier_rad, boden_lidar)
    if np.any(ursprung):
        winkel, entfernung = stand_profil(scans, gier_rad, boden_lidar)
    else:
        winkel, entfernung = rundum_profil(scans, gier_rad, boden_lidar)
    return winkel, entfernung, ursprung


def echo_statistik(scans: Sequence[dict], gier_rad: Sequence[float],
                   boden_lidar: np.ndarray, ursprung: Sequence[float],
                   bins: int = 720, reichweite_m: float = 8.0
                   ) -> Tuple[np.ndarray, np.ndarray]:
    """Je Richtung: wie oft kam ein Echo, und wie stark schwankt die Entfernung?

    Nur für Aufnahmen im Stand sinnvoll (``ursprung`` = Ort des LiDAR): Dann
    sieht jede Aufnahme jede Richtung vom selben Punkt. Eine Wand ergibt in
    jeder Aufnahme dasselbe Echo. Glas, Spiegel und Kanten, die der Strahl
    nur streift (Tischplatte in Höhe des LiDAR), ergeben mal ein nahes, mal
    ein fernes, mal gar kein Echo.

    Rückgabe: (Anteil der Aufnahmen mit Echo, Spanne der Entfernung in m),
    je Richtung wie in ``rundum_profil``. ``nan`` steht beim Anteil, wo in
    keiner Aufnahme ein Strahl in die Richtung ging, und bei der Spanne, wo
    es weniger als zwei Echos gab.
    """
    start = np.asarray(ursprung, dtype=float)
    schritt = 2 * math.pi / bins
    lidar_gier = math.atan2(boden_lidar[1, 0], boden_lidar[0, 0])
    naechstes = np.full((len(scans), bins), np.nan)
    gesendet = np.zeros((len(scans), bins), dtype=bool)
    for k, (scan, gier) in enumerate(zip(scans, gier_rad)):
        # Strahlen ohne Echo zählen in dem Fach, in das sie gezielt haben;
        # Strahlen mit Echo dort, wo ihr Messpunkt liegt.
        w, r = scan_felder(scan)
        stumm = ~(np.isfinite(r) & (r >= 0.15) & (r <= reichweite_m + 0.5))
        strahl = np.floor(((w[stumm] + lidar_gier + float(gier) + math.pi)
                           % (2 * math.pi)) / schritt).astype(int) % bins
        gesendet[k, strahl] = True
        punkte = scan_punkte(scan, boden_lidar, min_r=0.15, max_r=reichweite_m + 0.5)
        if not len(punkte):
            continue
        punkte = _drehe(punkte, np.array([float(gier)]))[0] - start
        entfernung = np.hypot(punkte[:, 0], punkte[:, 1])
        richtung = np.arctan2(punkte[:, 1], punkte[:, 0])
        fach = np.floor((richtung + math.pi) / schritt).astype(int) % bins
        gesendet[k, fach] = True
        reihe = np.full(bins, np.inf)
        np.minimum.at(reihe, fach, entfernung)
        naechstes[k] = np.where(np.isfinite(reihe), reihe, np.nan)
    fehlt = np.isnan(naechstes)
    gezaehlt = np.sum(~fehlt, axis=0)
    moeglich = np.sum(gesendet, axis=0)
    with np.errstate(invalid='ignore', divide='ignore'):
        anteil = np.where(moeglich > 0, gezaehlt / np.maximum(moeglich, 1), np.nan)
    groesstes = np.max(np.where(fehlt, -np.inf, naechstes), axis=0, initial=-np.inf)
    kleinstes = np.min(np.where(fehlt, np.inf, naechstes), axis=0, initial=np.inf)
    with np.errstate(invalid='ignore'):
        spanne = np.where(gezaehlt >= 2, groesstes - kleinstes, np.nan)
    return anteil, spanne


# ------------------------------------------------------------------ Ordner

class Blickrunde:
    """Eine gespeicherte Blickrunde."""

    def __init__(self, ordner: Path, meta: dict):
        self.ordner = Path(ordner)
        self.meta = meta

    @classmethod
    def lade(cls, ordner) -> 'Blickrunde':
        ordner = Path(ordner)
        with open(ordner / 'meta.json', encoding='utf-8') as datei:
            meta = json.load(datei)
        if meta.get('schema_version') != SCHEMA_VERSION:
            raise ValueError(
                f'{ordner}: unbekannte schema_version {meta.get("schema_version")!r}')
        if not isinstance(meta.get('aufnahmen'), list):
            raise ValueError(f'{ordner}: meta.json ohne Aufnahmenliste')
        return cls(ordner, meta)

    @property
    def name(self) -> str:
        return str(self.meta.get('name') or self.ordner.name)

    @property
    def aufnahmen(self) -> List[dict]:
        return self.meta['aufnahmen']

    def bild_bytes(self, index: int) -> bytes:
        return (self.ordner / self.aufnahmen[index]['bild']).read_bytes()

    def scan(self, index: int) -> Optional[dict]:
        name = self.aufnahmen[index].get('scan')
        if not name:
            return None
        with open(self.ordner / name, encoding='utf-8') as datei:
            return json.load(datei)

    def kamera(self) -> Kamera:
        return Kamera.aus_info(self.meta['kamera'])

    def _montage(self, schluessel: str, vorgabe: np.ndarray) -> np.ndarray:
        werte = (self.meta.get('montage') or {}).get(schluessel)
        if werte is None:
            return vorgabe
        matrix = np.asarray(werte, dtype=float)
        if matrix.shape != (4, 4):
            raise ValueError(f'{self.ordner}: montage.{schluessel} ist keine 4x4-Matrix')
        return matrix

    def boden_kamera(self) -> np.ndarray:
        return self._montage('boden_kamera', kamera_montage())

    def boden_lidar(self) -> np.ndarray:
        return self._montage('boden_lidar', lidar_montage())

    @property
    def karte(self) -> Optional[dict]:
        """Lage am Ende der Runde in der Karte (oder None bei älteren Runden)."""
        return self.meta.get('karte')

    def vorgabe_gier(self) -> Optional[List[Optional[float]]]:
        werte = [a.get('gier_odom') for a in self.aufnahmen]
        return werte if all(v is not None for v in werte) else None


def schreibe_runde(ordner, name: str, kamera: Kamera,
                   bilder: Sequence[bytes], scans: Sequence[Optional[dict]],
                   zeiten: Sequence[float], *,
                   tiefen: Optional[Sequence[Optional[bytes]]] = None,
                   gier_odom: Optional[Sequence[Optional[float]]] = None,
                   boden_kamera: Optional[np.ndarray] = None,
                   boden_lidar: Optional[np.ndarray] = None,
                   montage_quelle: str = 'vorgabe', quelle: Optional[dict] = None,
                   bemerkung: str = '', karte: Optional[dict] = None) -> Path:
    """Eine Blickrunde als Ordner schreiben (Aufnahme und künstliche Beispiele).

    ``karte``: wo der Roboter am Ende der Runde in der Karte stand
    (``rahmen``, ``basis_ende`` = [x, y, gier]); damit lässt sich eine
    gewählte Öffnung später in der Karte wiederfinden. Die Angabe bleibt
    mit der Runde auf dem Roboter.
    """
    ordner = Path(ordner)
    ordner.mkdir(parents=True, exist_ok=True)
    aufnahmen = []
    for i, (bild, scan, t) in enumerate(zip(bilder, scans, zeiten)):
        eintrag: Dict[str, object] = {'nr': i, 't': float(t),
                                      'bild': f'bild_{i:03d}.jpg'}
        (ordner / eintrag['bild']).write_bytes(bytes(bild))
        if tiefen is not None and tiefen[i] is not None:
            eintrag['tiefe'] = f'tiefe_{i:03d}.png'
            (ordner / eintrag['tiefe']).write_bytes(bytes(tiefen[i]))
        if scan is not None:
            eintrag['scan'] = f'scan_{i:03d}.json'
            with open(ordner / eintrag['scan'], 'w', encoding='utf-8') as datei:
                json.dump(scan, datei, separators=(',', ':'))
        if gier_odom is not None:
            eintrag['gier_odom'] = (None if gier_odom[i] is None
                                    else float(gier_odom[i]))
        aufnahmen.append(eintrag)
    meta = {
        'schema_version': SCHEMA_VERSION,
        'name': name,
        'bemerkung': bemerkung,
        'kamera': kamera.als_info(),
        'montage': {
            'quelle': montage_quelle,
            'boden_kamera': None if boden_kamera is None else np.asarray(boden_kamera).tolist(),
            'boden_lidar': None if boden_lidar is None else np.asarray(boden_lidar).tolist(),
        },
        'quelle': quelle or {},
        'karte': karte,
        'aufnahmen': aufnahmen,
    }
    with open(ordner / 'meta.json', 'w', encoding='utf-8') as datei:
        json.dump(meta, datei, indent=1, ensure_ascii=False)
    return ordner


def runden_finden(wurzel) -> List[Path]:
    """Alle Blickrunden-Ordner unter ``wurzel`` (oder ``wurzel`` selbst)."""
    wurzel = Path(wurzel)
    if (wurzel / 'meta.json').is_file():
        return [wurzel]
    return sorted(p.parent for p in wurzel.glob('*/meta.json'))
