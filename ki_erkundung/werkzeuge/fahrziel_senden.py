#!/usr/bin/env python3
"""Auf dem Roboter: dem Erkunder ein Fahrziel für die Etappenfahrt geben.

Der Erkunder läuft im Betrieb „Etappenfahrt“ (Startargument
``stage_drive_only:=true``) und wartet nach dem Missionsstart auf genau ein
Fahrziel. Dieses Werkzeug wartet, bis er wartet, berechnet das Ziel und
schickt es ihm als Text. Es fährt nicht selbst: Gefahren wird vom Erkunder,
in kurzen geraden Etappen, mit Fahrtor und Kollisionsmonitor.

    # eine gerade Etappe von einem halben Meter (erster Test)
    python3 fahrziel_senden.py --geradeaus 0.5

    # ein Punkt 0,40 m voraus und 0,25 m links: erst ausrichten, dann eine Etappe
    python3 fahrziel_senden.py --punkt 0.40,0.25

    # durch die Öffnung, die etwa 20° links liegt (Nummer wählt die KI oder ein Mensch)
    python3 fahrziel_senden.py --tuer --richtung 20 --quelle mensch

    # vom Platz im Raum selbst vor diese Öffnung fahren (danach --tuer)
    python3 fahrziel_senden.py --vor-die-tuer --richtung 20 --quelle mensch

    # selbst entscheiden: steht er passend, gleich hindurch; sonst erst davor
    python3 fahrziel_senden.py --zur-tuer --richtung 20 --quelle mensch

    # die Tür, die die KI gewählt hat (Wahl-Datei von ki_tuer_waehlen.py)
    python3 fahrziel_senden.py --zur-tuer --wahl DATEI

    # kein Fahrziel: dem wartenden Erkunder sagen, dass keines kommt
    python3 fahrziel_senden.py --ende --quelle mensch

Für ``--tuer`` misst das Werkzeug die Öffnungen im Stand neu (zwei Sekunden
Laser), nimmt die gewählte und legt die Fahrpunkte auf die **gerade Linie
vom Standplatz durch die Türmitte**: einen 1,2 m vor und einen 0,6 m hinter
der Türlinie. Es sendet nichts, wenn es die Öffnung nicht eindeutig findet,
wenn sie nicht türbreit vermessen ist (0,65 bis 0,95 m), wenn ihr zweiter
Pfosten nur aus dem Lot geschätzt ist (keine gemessene Kante, seit KI-F9N),
wenn der Roboter nicht passend vor der Tür steht oder wenn neben der
Fahrlinie nicht beidseits 0,26 m frei sind (gemessen am selben Laserbild:
Türblatt, Pfosten, alles, was im Weg steht); dann sagt es, was an der
Aufstellung zu ändern ist. ``--tuer --nur-messen`` zeigt dasselbe, ohne zu
senden, und dazu das Protokoll der Vermessung.

``--zur-tuer`` entscheidet selbst: Passen Aufstellung, Weg und Kostenkarte,
sendet es die Durchfahrt; sonst die Anfahrt vor die Tür. Ist der zweite
Pfosten nur aus dem Lot geschätzt, nie gleich die Durchfahrt: höchstens die
Anfahrt, und hindurch erst, wenn die neue Messung davor zwei gemessene
Kanten zeigt. **Alles in einem Aufruf und einer Mission:** Die Anfahrt
trägt den Vermerk „es folgt ein Folgeziel“; danach misst das Werkzeug im
Stand neu, findet die gemerkte Tür wieder und sendet die Durchfahrt (nicht,
wenn ihr zweiter Pfosten weiter nur geschätzt ist). Sieht der Laser von dort
die Wand neben der Tür nicht lang genug, nimmt es die Türachse aus der
ersten Messung. Niemand muss den Roboter dafür umstellen. Passt etwas nicht,
schickt es dem Erkunder ein „Ende“; die Mission schließt dann sofort.

``--wahl DATEI`` nimmt statt Nummer oder Richtung die Wahl der KI: Die
Datei nennt den Ort der gewählten Öffnung in der Karte; das Werkzeug misst
neu und nimmt die türbreite Öffnung, deren Mitte dort liegt (höchstens
0,40 m daneben, keine zweite fast gleich nah). Liegt dort keine, sendet es
das „Ende“. Die Quelle ist dann ``ki``. Freigeben muss die Wahl vorher ein
Mensch; dieses Werkzeug fragt nicht.

``--ende`` sendet kein Fahrziel, sondern dem wartenden Erkunder das „Ende“
(nach einem Nein zur Wahl der KI oder wenn sie keinen Ausgang nennt).

``--vor-die-tuer`` ist die **Anfahrt**: Steht der Roboter irgendwo im Raum,
fährt er über einen Punkt auf der Türachse vor die Tür und dreht sich zu
ihr; danach steht er so, wie ``--tuer`` es verlangt. Auch dieser Weg wird am
Laserbild geprüft (frei neben jeder Strecke, Platz zum Drehen, freie Sicht
auf die Punkte); passt er nicht, wird nichts gesendet.

Vor dem Senden prüft es außerdem die Kostenkarte auf dem **ganzen Weg** so,
wie der Nahbereichs-Halt des Erkunders sie liest: Liegt im Streifen vor der
Vorderkante irgendwo auf der Strecke etwas Belegtes, würde der Erkunder dort
anhalten; dann wird nichts gesendet. Für eine belegte Stelle (vor dem Senden
und nach einem Halt) sagt es, welche Quelle dort etwas sieht: die Karte des
SLAM (Laser), einer der beiden Nahsensoren (mit Höhe über dem Boden) oder
der Laser gerade jetzt.

Was es zur Entscheidung gesehen hat, legt es als **Belege** auf dem Roboter
ab (``--belege``, Vorgabe ``~/.local/share/amadeus/ki_erkundung/belege``):
je Aufruf einen Ordner mit den Scans jeder Messung im Stand und den belegten
Zellen von Karte und Kostenkarte um jede sperrende Stelle. Sie enthalten
Maße der Wohnung und bleiben auf dem Jetson, nie im Repository, nie im
Bericht.

Strg+C, ``kill -INT`` oder SIGTERM beenden das Werkzeug geordnet (Rückgabe
130): Nach dem Signal wird nichts mehr gesendet, auch kein „Ende“. Ein schon
angenommenes Fahrziel fährt der Erkunder mit seiner Schutzkette zu Ende;
sonst schließt er die Mission nach seiner Wartezeit von selbst.

Ausgegeben werden nur Maße und Meldungen, keine Bilder und keine Koordinaten
der Wohnung.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path
from typing import List, Optional, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from lotse.blickrunde import profil_ursprung, scan_als_dict, stand_profil  # noqa: E402
from lotse.fahrziel import (  # noqa: E402
    BASIS_UEBER_BODEN_M, FREI_NEBEN_DER_LINIE_M, HINTER_DER_TUER_M, TUER_MAX_M, TUER_MIN_M,
    VOR_DER_TUER_M, achse_aus_karte, achse_text, anfahrt, anfahrt_im_kartenrahmen, anfahrt_text,
    aufstellung, aufstellung_hinweise, belegt_auf_dem_weg, botschaft, ende_botschaft, freiraum,
    freiraum_hinweise, gerade_durch_die_tuer, gerade_linie, geradeaus, herkunft, herkunft_text,
    in_den_boden, kostenkarte_text, kostenkarte_voraus, nah_text, pruefe_grenzen, punkt_relativ,
    tuer_merken, tuerachse, weg_belegt_text, wiederfinden, wiederfinden_zeilen, wolke_xyz,
    zellen_um,
)
from lotse.fahrziel import blatt_text, tuer_hinter_blatt  # noqa: E402
from lotse.geometrie import aus_tf  # noqa: E402
from lotse.kandidaten import SCHLUSS_LOT, TUERBREIT_M, Oeffnung, oeffnungen  # noqa: E402
from lotse.wahl import im_standpunktrahmen, wahl_lesen, zur_wahl  # noqa: E402
from ros_ende import Ende, ros_beenden, ros_starten  # noqa: E402

WARTEPHASE = 'stage_drive_wait_target'
RC_ABGEBROCHEN = 130
VORGABE_BELEGE = Path.home() / '.local/share/amadeus/ki_erkundung/belege'


def im_repository(pfad: Path) -> bool:
    """Liegt ``pfad`` in einem Git-Arbeitsverzeichnis? Dort gehören keine Wohnungsdaten hin."""
    pfad = Path(pfad).expanduser().resolve()
    return any((eltern / '.git').exists() for eltern in [pfad, *pfad.parents])


class Belege:
    """Was das Werkzeug zur Entscheidung gesehen hat, auf dem Roboter abgelegt.

    Je Aufruf ein Ordner: ``messung_N.json`` (Scans einer Messung im Stand,
    Montage des LiDAR, Lage in der Karte) und ``sperre_N.json`` (belegte Zellen
    von Karte und Kostenkarte um eine sperrende Stelle, mit dem Alter beider).
    Für 2w2 fehlte genau dieser Beleg (Bewertung nach KI-F9, §3). Ein Fehler
    beim Schreiben hält das Werkzeug nicht auf.
    """

    def __init__(self, wurzel: Optional[Path], art: str):
        self.ordner = (None if wurzel is None
                       else Path(wurzel) / f'{time.strftime("%Y%m%d_%H%M%S")}_{art}')
        self.zaehler: dict = {}

    def schreibe(self, art: str, daten: dict) -> Optional[Path]:
        if self.ordner is None:
            return None
        try:
            self.ordner.mkdir(parents=True, exist_ok=True)
            self.zaehler[art] = self.zaehler.get(art, 0) + 1
            pfad = self.ordner / f'{art}_{self.zaehler[art]}.json'
            with open(pfad, 'w', encoding='utf-8') as datei:
                json.dump(daten, datei, ensure_ascii=False)
            return pfad
        except (OSError, TypeError, ValueError) as fehler:
            print(f'Belege nicht geschrieben ({fehler}); weiter ohne.', file=sys.stderr)
            self.ordner = None
            return None


class Abbruch(Exception):
    """Ein Signal kam (Strg+C, kill -INT, SIGTERM): nichts mehr senden, geordnet enden."""


def waehle_oeffnung(liste: Sequence[Oeffnung], *, nummer: Optional[int] = None,
                    richtung_grad: Optional[float] = None,
                    toleranz_grad: float = 25.0,
                    nur_tuergross: bool = True,
                    breite_von_m: Optional[float] = None,
                    breite_bis_m: Optional[float] = None) -> Oeffnung:
    """Die gemeinte Öffnung; ``ValueError`` mit Grund, wenn sie nicht eindeutig ist.

    Mit ``breite_von_m`` und ``breite_bis_m`` zählt nur, was so breit vermessen
    ist; eine als Tür gemeinte, aber falsch vermessene Öffnung wird dann mit
    ihrem Maß genannt und nicht gewählt.
    """
    waehlbar = [o for o in liste if o.befahrbar
                and (not nur_tuergross or o.breite_m <= TUERBREIT_M)]
    if breite_von_m is not None and breite_bis_m is not None:
        passend = [o for o in waehlbar if breite_von_m <= o.breite_m <= breite_bis_m]
        if waehlbar and not passend:
            masse = ', '.join(f'{o.breite_m:.2f} m' for o in waehlbar)
            raise ValueError(
                f'keine Öffnung ist türbreit vermessen ({breite_von_m:.2f} bis '
                f'{breite_bis_m:.2f} m); vermessen: {masse}')
        waehlbar = passend
    if not waehlbar:
        raise ValueError('keine befahrbare, türgroße Öffnung vermessen')
    if nummer is not None:
        treffer = [o for o in waehlbar if o.nr == nummer]
        if not treffer:
            raise ValueError(f'Nummer {nummer} ist keine befahrbare, türgroße Öffnung')
        return treffer[0]
    if richtung_grad is None:
        if len(waehlbar) > 1:
            raise ValueError(
                f'{len(waehlbar)} Öffnungen kommen in Frage; Nummer oder Richtung nennen')
        return waehlbar[0]

    def abstand(o: Oeffnung) -> float:
        return abs((o.richtung_grad - richtung_grad + 180.0) % 360.0 - 180.0)

    nah = sorted((o for o in waehlbar if abstand(o) <= toleranz_grad), key=abstand)
    if not nah:
        raise ValueError(
            f'keine Öffnung innerhalb von {toleranz_grad:.0f}° um {richtung_grad:.0f}°')
    if len(nah) > 1 and abstand(nah[1]) - abstand(nah[0]) < 5.0:
        raise ValueError(
            f'zwei Öffnungen liegen gleich nah an {richtung_grad:.0f}° '
            f'(Nummern {nah[0].nr} und {nah[1].nr}); Nummer nennen')
    return nah[0]


def lies_punkt(text: str):
    """``'0.40,0.25'`` -> (0.40, 0.25); ``ValueError`` bei allem anderen."""
    teile = text.split(',')
    if len(teile) != 2:
        raise ValueError(f'Punkt {text!r}: erwartet VORAUS,LINKS in Metern')
    try:
        return float(teile[0]), float(teile[1])
    except ValueError as fehler:
        raise ValueError(f'Punkt {text!r}: keine Zahlen') from fehler


def tabelle(liste: Sequence[Oeffnung]) -> str:
    zeilen = ['Nr  Breite  Richtung  Entfernung  befahrbar  Schluss']
    for o in liste:
        zeilen.append(
            f'{o.nr:>2}  {o.breite_m:5.2f} m  {o.richtung_grad:+7.1f}°  '
            f'{o.entfernung_m:8.2f} m  {"ja" if o.befahrbar else "nein":>9}  {o.schluss}')
    return '\n'.join(zeilen)


def vermesse(scans: List[dict], boden_lidar,
             protokoll: Optional[List[dict]] = None,
             hindernisse: Optional[List] = None,
             sicht: Optional[dict] = None) -> List[Oeffnung]:
    """Öffnungen aus Scans im Stand, im Standpunktrahmen (Antriebsmitte).

    In ``hindernisse`` legt die Funktion ab, was der Laser sieht: je
    Richtung ein Punkt im selben Rahmen (für die Prüfung des Freiraums). In
    ``sicht`` legt sie das Profil selbst ab (für die Frage, ob ein Punkt
    frei gesehen wurde).
    """
    gier = [0.0] * len(scans)
    winkel, profil = stand_profil(scans, gier, boden_lidar)
    ursprung = profil_ursprung(gier, boden_lidar)
    if sicht is not None:
        sicht.update(ursprung=(float(ursprung[0]), float(ursprung[1])),
                     winkel=winkel, profil=profil)
    if hindernisse is not None:
        for w, r in zip(winkel, profil):
            if math.isfinite(r):
                hindernisse.append((float(ursprung[0]) + float(r) * math.cos(float(w)),
                                    float(ursprung[1]) + float(r) * math.sin(float(w))))
    return oeffnungen(winkel, profil, ursprung=ursprung, protokoll=protokoll)


def weg_text(o: Oeffnung, hindernisse: Sequence, vor_m: float, hinter_m: float,
             achse: Optional[dict] = None):
    """Die Fahrlinie durch eine Öffnung in einem Satz; dazu, ob sie passt."""
    try:
        linie = gerade_linie(o.pfosten, vor_m=vor_m, hinter_m=hinter_m,
                             achse=None if achse is None else achse['normal'])
    except ValueError as grund:
        return f'Fahrlinie: {grund}.', False
    frei = freiraum(hindernisse, linie[-1])
    hinweise = freiraum_hinweise(frei)

    def seite(name: str) -> str:
        wert = frei[f'{name}_m']
        return f'{name} {"über 2 m" if wert > 2.0 else f"{wert:.2f} m"}'

    text = (f'Fahrlinie: gerade durch die Türmitte, {frei["laenge_m"]:.2f} m; frei neben '
            f'der Linie {seite("links")}, {seite("rechts")} '
            f'(nötig {FREI_NEBEN_DER_LINIE_M:.2f} m)')
    return (text + (' – Weg passt.' if not hinweise
                    else ' – Weg passt nicht: ' + '; '.join(hinweise) + '.'), not hinweise)


def anfahrt_zeile(o: Oeffnung, hindernisse: Sequence, sicht: Optional[dict],
                  achse: Optional[dict] = None):
    """Die Anfahrt vor eine Öffnung in einem Satz; dazu der Weg (oder ``None``).

    Rückgabe ``(text, weg, noetig)``: ``noetig`` ist falsch, wenn der Roboter
    schon passend vor der Tür steht.
    """
    if not aufstellung_hinweise(aufstellung(
            o.pfosten, achse=None if achse is None else achse['normal'])):
        return 'Anfahrt: nicht nötig, er steht schon passend vor der Tür.', None, False
    try:
        weg = anfahrt(o.pfosten, hindernisse, sicht or None)
    except ValueError as grund:
        text = str(grund)
        return ('Anfahrt passt nicht: '
                + (text[9:] if text.startswith('Anfahrt: ') else text) + '.'), None, True
    return anfahrt_text(weg) + ' – Anfahrt passt.', weg, True


def lage_text(o: Oeffnung, mit_hinweisen: bool = True, achse: Optional[dict] = None) -> str:
    """Die Aufstellung zu einer Öffnung in einem Satz, mit dem, was zu ändern ist."""
    lage = aufstellung(o.pfosten, achse=None if achse is None else achse['normal'])
    hinweise = aufstellung_hinweise(lage) if mit_hinweisen else None
    seite = 'links' if lage['seitlich_m'] > 0 else 'rechts'
    text = (f'Nr. {o.nr}: {lage["abstand_m"]:.2f} m vor der Türlinie, '
            f'{abs(lage["seitlich_m"]):.2f} m {seite} neben der Türmitte, Tür '
            f'{abs(lage["winkel_grad"]):.0f}° '
            f'{"links" if lage["winkel_grad"] > 0 else "rechts"} von der Blickrichtung')
    if hinweise is None:
        return text + '.'
    return text + (' – Aufstellung passt.' if not hinweise
                   else ' – Aufstellung passt nicht: ' + '; '.join(hinweise) + '.')


def nur_geschaetzt(o) -> bool:
    """Ist der zweite Pfosten der Öffnung nur aus dem Lot geschätzt?

    Dann gibt es dort keine gemessene Kante. Durch so eine Öffnung fährt er nie
    direkt (seit KI-F9N): höchstens erst davor, neu messen und hindurch nur
    mit zwei gemessenen Kanten. Jede Stelle, die eine Durchfahrt sendet,
    fragt hier.
    """
    return getattr(o, 'schluss', None) == SCHLUSS_LOT


def entscheidung(lage_passt: bool, weg_passt: bool, anfahrt_moeglich: bool,
                 geschaetzt: bool = False) -> str:
    """Was ``--zur-tuer`` sendet: ``'durchfahrt'``, ``'anfahrt'`` oder ``'nichts'``.

    Steht der Roboter passend und ist die gerade Linie frei, fährt er gleich
    hindurch. Sonst stellt er sich zuerst selbst vor die Tür, wenn die
    Anfahrt geprüft möglich ist. Niemand muss ihn dafür umstellen.

    ``geschaetzt``: Der zweite Pfosten ist nur geschätzt (Schluss „lot“). Dann
    nie gleich hindurch, nur vorfahren und neu messen (Bewertung nach KI-F9,
    §8); hindurch erst, wenn er danach zwei gemessene Kanten sieht.
    """
    if geschaetzt:
        return 'anfahrt' if not lage_passt and anfahrt_moeglich else 'nichts'
    if lage_passt and weg_passt:
        return 'durchfahrt'
    if not lage_passt and anfahrt_moeglich:
        return 'anfahrt'
    return 'nichts'


GESCHAETZT_TEXT = ('Der zweite Pfosten ist nur geschätzt (Lot, keine gemessene Kante): '
                   'Gleich hindurch fährt er nicht, höchstens erst davor und neu messen.')

ENTSCHEIDUNG_TEXT = {
    'durchfahrt': 'Entscheidung: Durchfahrt – er steht passend, gerade durch die Türmitte.',
    'anfahrt': ('Entscheidung: Anfahrt – er stellt sich zuerst selbst vor die Tür; danach '
                'misst er neu und fährt in derselben Mission hindurch.'),
    'nichts': 'Entscheidung: keine Fahrt – weder Durchfahrt noch Anfahrt passen.',
}


def vorschlag(tueren: Sequence[Oeffnung]) -> Optional[Oeffnung]:
    """Die türbreite Öffnung mit dem meisten freien Raum dahinter (eine Tür
    führt in einen Raum, eine Lücke zwischen Möbeln nicht)."""
    return max(tueren, key=lambda o: o.tiefe_m, default=None)


def tuer_aus_blatt(hindernisse: Sequence, nr: int):
    """Die hinter dem offenen Türblatt geschätzte Tür als Öffnung, mit Achse.

    Rückgabe ``(oeffnung, achse, fund)`` oder ``None``. Die Achse kommt aus
    der Wand neben dem Scharnier. Gefahren wird zu dieser Schätzung nur die
    Anfahrt; durch die Tür erst nach neuer Messung von vorn.
    """
    fund = tuer_hinter_blatt(hindernisse)
    if fund is None:
        return None
    (ax, ay), (bx, by) = fund['pfosten']
    mx, my = 0.5 * (ax + bx), 0.5 * (ay + by)
    o = Oeffnung(nr, math.hypot(bx - ax, by - ay), (mx, my), fund['pfosten'],
                 math.degrees(math.atan2(my, mx)), math.hypot(mx, my), 0.0, True,
                 'blatt_geschaetzt')
    achse = {'normal': fund['normal'], 'quelle': 'wand', 'punkte': fund['wand_punkte'],
             'laenge_m': fund['wand_laenge_m']}
    return o, achse, fund


# Eine hinter dem Türblatt geschätzte Tür gilt als die gewählte, wenn ihre
# Mitte höchstens so weit von der Mitte aus der Blickrunde entfernt liegt
# (die Schätzung aus Blatt und Wand ist ungenauer als eine Vermessung).
WAHL_BLATT_ABSTAND_M = 0.50


def oeffnung_zur_wahl(gefunden: Sequence[Oeffnung], tueren: Sequence[Oeffnung],
                      wahl_daten: dict, pose: Sequence[float], *,
                      breite_von_m: float = TUER_MIN_M, breite_bis_m: float = TUER_MAX_M):
    """Die neu vermessene Öffnung zur Wahl der KI: ``(oeffnung, abstand_m)``.

    ``ValueError`` mit Grund; liegt an der Stelle eine Öffnung, die nicht
    türbreit vermessen ist, wird sie mit ihrem Maß genannt.
    """
    try:
        return zur_wahl(tueren, wahl_daten, pose)
    except ValueError as grund:
        andere = [o for o in gefunden if o not in tueren]
        try:
            o, _ = zur_wahl(andere, wahl_daten, pose, eindeutig_m=0.0)
        except ValueError:
            raise grund from None
        raise ValueError(
            f'an der gewählten Stelle ist Öffnung {o.nr} vermessen, {o.breite_m:.2f} m breit – '
            f'nicht türbreit ({breite_von_m:.2f} bis {breite_bis_m:.2f} m)') from grund


def blatt_passt_zur_wahl(o: Oeffnung, wahl_daten: dict, pose: Sequence[float],
                         max_abstand_m: float = WAHL_BLATT_ABSTAND_M) -> bool:
    ziel = im_standpunktrahmen(wahl_daten['mitte'], pose)
    mx = 0.5 * (o.pfosten[0][0] + o.pfosten[1][0])
    my = 0.5 * (o.pfosten[0][1] + o.pfosten[1][1])
    return math.hypot(mx - ziel[0], my - ziel[1]) <= max_abstand_m


def richtung_passt(o: Oeffnung, richtung_grad: Optional[float], toleranz_grad: float) -> bool:
    if richtung_grad is None:
        return True
    return abs((o.richtung_grad - richtung_grad + 180.0) % 360.0 - 180.0) <= toleranz_grad


def protokoll_text(protokoll: Sequence[dict], max_breite_m: float = 1.6,
                   max_zeilen: int = 16) -> str:
    """Das Protokoll der Vermessung als Zeilen, nur Maße vom Roboter aus."""
    def kanten(z: dict) -> str:
        return ' · '.join(f'{w:+.1f}°/{r:.2f} m' for w, r in z['pfosten'])

    def anteil(wert) -> str:
        return '–' if wert is None else f'{100 * wert:.0f} %'

    zeilen, gesehen = ['Protokoll der Vermessung (Maße vom Roboter aus):'], set()
    for z in sorted(protokoll, key=lambda z: (z['ergebnis'] != 'angeboten',
                                              z['richtung_grad'], z['breite_m'])):
        if z['breite_m'] is None or z['breite_m'] > max_breite_m:
            continue
        schluessel = (z['ergebnis'], round(z['richtung_grad'] / 2.0), round(z['breite_m'], 1))
        if schluessel in gesehen:
            continue
        gesehen.add(schluessel)
        if len(zeilen) > max_zeilen:
            zeilen.append('  … weitere Zeilen ausgelassen')
            break
        tiefe = '–' if z['tiefe_m'] is None else f'{z["tiefe_m"]:.2f} m'
        zeilen.append(
            f'  {z["ergebnis"]:<10} {z["breite_m"]:.2f} m  {z["richtung_grad"]:+6.1f}°  '
            f'{z["entfernung_m"]:.2f} m  {z["schluss"]:<6} Kanten {kanten(z)}  '
            f'tief {tiefe} ({anteil(z["anteil_tief"])}), davor {anteil(z["anteil_davor"])}  '
            f'Vermerk {z.get("blatt") or "–"}')
    return '\n'.join(zeilen)


def eingabe() -> argparse.ArgumentParser:
    e = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    art = e.add_mutually_exclusive_group(required=True)
    art.add_argument('--geradeaus', type=float, metavar='METER',
                     help='ein Punkt genau voraus in dieser Entfernung')
    art.add_argument('--punkt', metavar='VORAUS,LINKS',
                     help='ein Punkt vom Roboter aus, in Metern (links negativ = rechts)')
    art.add_argument('--tuer', action='store_true',
                     help='auf gerader Linie durch eine vermessene Öffnung')
    art.add_argument('--vor-die-tuer', action='store_true',
                     help='Anfahrt: vom Platz im Raum vor eine vermessene Öffnung')
    art.add_argument('--zur-tuer', action='store_true',
                     help='selbst entscheiden: gleich hindurch oder zuerst davor (Anfahrt)')
    art.add_argument('--ende', action='store_true',
                     help='kein Fahrziel: dem wartenden Erkunder sagen, dass keines kommt')
    e.add_argument('--nummer', type=int, help='Nummer der Öffnung aus der Tabelle')
    e.add_argument('--richtung', type=float, metavar='GRAD',
                   help='Richtung der gemeinten Öffnung; 0 = voraus, positiv = links')
    e.add_argument('--richtung-toleranz', type=float, default=25.0)
    e.add_argument('--wahl', metavar='DATEI',
                   help='nur mit --zur-tuer: die Tür, die die KI gewählt hat (Wahl-Datei '
                        'von ki_tuer_waehlen.py); ersetzt --nummer und --richtung')
    e.add_argument('--quelle', choices=('ki', 'mensch', 'test'), default=None,
                   help='wer gewählt hat; steht später in jeder Meldung des Erkunders '
                        '(Vorgabe: ki mit --wahl, sonst test)')
    e.add_argument('--kennung', default='')
    e.add_argument('--vor', type=float, default=VOR_DER_TUER_M,
                   help='Zwischenpunkt vor der Türlinie, m')
    e.add_argument('--hinter', type=float, default=HINTER_DER_TUER_M,
                   help='Auslaufpunkt hinter der Türlinie, m')
    e.add_argument('--breite-min', type=float, default=TUER_MIN_M,
                   help='so breit muss die Öffnung mindestens vermessen sein, m')
    e.add_argument('--breite-max', type=float, default=TUER_MAX_M,
                   help='so breit darf sie höchstens vermessen sein, m')
    e.add_argument('--aufstellung-egal', action='store_true',
                   help='auch senden, wenn Aufstellung oder Freiraum nicht passen')
    e.add_argument('--messdauer', type=float, default=2.0,
                   help='so lange Laser sammeln, s (nur --tuer)')
    e.add_argument('--warten', type=float, default=300.0,
                   help='so lange auf den wartenden Erkunder warten, s')
    e.add_argument('--beobachten', type=float, default=600.0,
                   help='nach dem Senden die Meldungen des Erkunders so lange zeigen, s')
    e.add_argument('--nur-messen', action='store_true',
                   help='Öffnungen messen und zeigen, nichts senden')
    e.add_argument('--scan-topic', default='/scan')
    e.add_argument('--status-topic', default='/explore/status_json')
    e.add_argument('--kostenkarte-topic', default='/global_costmap/costmap')
    e.add_argument('--karten-topic', default='/map',
                   help='Karte des SLAM (Quelle der festen Einträge der Kostenkarte)')
    e.add_argument('--karten-rahmen', default='map')
    e.add_argument('--basis-rahmen', default='base_link')
    e.add_argument('--basis-hoehe', type=float, default=0.0)
    e.add_argument('--belege', default=str(VORGABE_BELEGE),
                   help='Ordner für die Belege jeder Entscheidung (auf dem Roboter, '
                        'außerhalb des Repositorys)')
    e.add_argument('--keine-belege', action='store_true',
                   help='keine Belege ablegen')
    return e


def main(argv=None) -> int:
    # Ohne Terminal puffert Python die Ausgabe; die Zeilen kämen sonst erst am Ende.
    for strom in (sys.stdout, sys.stderr):
        if hasattr(strom, 'reconfigure'):
            strom.reconfigure(line_buffering=True)
    leser = eingabe()
    wahl = leser.parse_args(argv)
    if wahl.wahl is not None:
        if not wahl.zur_tuer:
            leser.error('--wahl nur mit --zur-tuer')
        if wahl.nummer is not None or wahl.richtung is not None:
            leser.error('--wahl ersetzt --nummer und --richtung')
        if wahl.quelle not in (None, 'ki'):
            leser.error('mit --wahl hat die KI gewählt: Quelle ki')
    wahl.quelle = wahl.quelle or ('ki' if wahl.wahl is not None else 'test')
    wahl_text, wahl_fehler = None, None
    if wahl.wahl is not None:
        try:
            wahl_text = Path(wahl.wahl).expanduser().read_text(encoding='utf-8')
        except OSError as fehler:
            wahl_fehler = f'Wahl-Datei nicht lesbar ({fehler.strerror or fehler})'
    import rclpy
    from rclpy.qos import (QoSDurabilityPolicy, QoSProfile, QoSReliabilityPolicy,
                           qos_profile_sensor_data)
    import numpy as np
    from nav_msgs.msg import OccupancyGrid
    from sensor_msgs.msg import LaserScan, PointCloud2
    from std_msgs.msg import String
    from tf2_ros import Buffer, TransformListener

    from ki_verbindung_ros import Fahrzielsender

    belege_wurzel = None if wahl.keine_belege else Path(wahl.belege).expanduser()
    if belege_wurzel is not None and im_repository(belege_wurzel):
        print(f'{belege_wurzel} liegt in einem Git-Arbeitsverzeichnis; die Belege enthalten '
              'Maße der Wohnung und bleiben außerhalb. Nichts gesendet.', file=sys.stderr)
        return 2
    belege = Belege(belege_wurzel, 'ende' if wahl.ende else 'zur_tuer' if wahl.zur_tuer
                    else 'vor_die_tuer' if wahl.vor_die_tuer else 'tuer' if wahl.tuer
                    else 'fahrt')

    # Zuerst die Marke, dann rclpy ohne eigene Handler (ros_ende).
    marke = Ende().anmelden()
    eigener_kontext = ros_starten()
    knoten = rclpy.create_node('ki_fahrziel')
    stand = {'status': None, 'scans': [], 'rahmen': None, 'sammeln': False,
             'kostenkarte': None, 'karte': None, 'nah': {'links': [], 'rechts': []},
             'kostenkarte_t': None, 'karte_t': None}

    def auf_kostenkarte(nachricht):
        stand['kostenkarte'] = nachricht
        stand['kostenkarte_t'] = time.monotonic()

    def auf_karte(nachricht):
        stand['karte'] = nachricht
        stand['karte_t'] = time.monotonic()

    def auf_wolke(seite):
        def merke(nachricht):
            liste = stand['nah'][seite]
            liste.append((time.monotonic(), nachricht))
            del liste[:-5]
        return merke

    def auf_status(nachricht):
        try:
            stand['status'] = json.loads(nachricht.data)
        except ValueError:
            pass

    def auf_scan(nachricht):
        stand['rahmen'] = nachricht.header.frame_id
        if stand['sammeln']:
            t = nachricht.header.stamp.sec + 1e-9 * nachricht.header.stamp.nanosec
            stand['scans'].append(scan_als_dict(
                nachricht.angle_min, nachricht.angle_increment, nachricht.ranges,
                nachricht.range_min, nachricht.range_max, t, nachricht.header.frame_id))

    letzter = QoSProfile(depth=1, reliability=QoSReliabilityPolicy.RELIABLE,
                         durability=QoSDurabilityPolicy.TRANSIENT_LOCAL)
    knoten.create_subscription(String, wahl.status_topic, auf_status, letzter)
    knoten.create_subscription(LaserScan, wahl.scan_topic, auf_scan, qos_profile_sensor_data)
    knoten.create_subscription(OccupancyGrid, wahl.kostenkarte_topic, auf_kostenkarte, letzter)
    knoten.create_subscription(OccupancyGrid, wahl.karten_topic, auf_karte, letzter)
    for seite, name in (('links', 'left'), ('rechts', 'right')):
        knoten.create_subscription(PointCloud2, f'/near_field/{name}/points', auf_wolke(seite),
                                   qos_profile_sensor_data)
    tf_puffer = Buffer()
    TransformListener(tf_puffer, knoten)
    sender = Fahrzielsender(knoten)

    def drehe(sekunden: float, fertig=lambda: False) -> bool:
        bis = time.monotonic() + sekunden
        while rclpy.ok() and time.monotonic() < bis:
            if marke.gesetzt():
                raise Abbruch()
            rclpy.spin_once(knoten, timeout_sec=0.05)
            if fertig():
                return True
        if marke.gesetzt():
            raise Abbruch()
        return fertig()

    def tf(ziel: str, quelle: str):
        try:
            t = tf_puffer.lookup_transform(ziel, quelle, rclpy.time.Time())
        except Exception:                      # noqa: BLE001 (tf2 wirft mehrere Arten)
            return None
        return t.transform

    def lage_in_der_karte():
        t = tf(wahl.karten_rahmen, wahl.basis_rahmen)
        if t is None:
            return None
        q = t.rotation
        gier = math.atan2(2.0 * (q.w * q.z + q.x * q.y), 1.0 - 2.0 * (q.y * q.y + q.z * q.z))
        return t.translation.x, t.translation.y, gier

    def kostenkarte_zeile() -> str:
        """Was der Erkunder für seinen Nahbereichs-Halt vor dem Roboter sieht."""
        karte, pose = stand['kostenkarte'], lage_in_der_karte()
        if karte is None or pose is None:
            return 'Kostenkarte vor dem Roboter: nicht empfangen.'
        try:
            return kostenkarte_text(kostenkarte_voraus(
                karte.data, karte.info.width, karte.info.height, karte.info.resolution,
                (karte.info.origin.position.x, karte.info.origin.position.y), pose))
        except ValueError as grund:
            return f'Kostenkarte vor dem Roboter: {grund}.'

    def laserbild(dauer: float):
        """Scans im Stand sammeln; Rückgabe (Scans, Lage des LiDAR) oder (None, None)."""
        stand['scans'] = []
        stand['sammeln'] = True
        drehe(dauer)
        stand['sammeln'] = False
        montage = tf(wahl.basis_rahmen, stand['rahmen']) if stand['rahmen'] else None
        if not stand['scans'] or montage is None:
            return None, None
        v, q = montage.translation, montage.rotation
        boden = aus_tf([v.x, v.y, v.z], [q.x, q.y, q.z, q.w], wahl.basis_hoehe)
        belege.schreibe('messung', {
            'zeit_unix': round(time.time(), 2), 'dauer_s': dauer,
            'lidar_rahmen': stand['rahmen'], 'boden_lidar': np.asarray(boden).tolist(),
            'pose_karte': lage_in_der_karte(), 'scans': list(stand['scans'])})
        return list(stand['scans']), boden

    def nah_jetzt(alter_s: float = 1.5):
        """Die frischen Punkte beider Nahsensoren: voraus, seitlich, Höhe über dem Boden."""
        ergebnis = {}
        for seite in ('links', 'rechts'):
            frisch = [n for t, n in stand['nah'][seite] if time.monotonic() - t <= alter_s]
            teile = []
            for wolke in frisch:
                lage = tf(wahl.basis_rahmen, wolke.header.frame_id)
                if lage is None:
                    continue
                v, q = lage.translation, lage.rotation
                try:
                    roh = wolke_xyz(wolke.data, {f.name: (f.offset, f.datatype)
                                                 for f in wolke.fields},
                                    wolke.point_step, wolke.width * wolke.height,
                                    wolke.is_bigendian)
                except ValueError:
                    continue
                teile.append(in_den_boden(roh, aus_tf([v.x, v.y, v.z], [q.x, q.y, q.z, q.w],
                                                      BASIS_UEBER_BODEN_M)))
            ergebnis[seite] = np.vstack(teile) if teile else None
        return ergebnis

    def zellen_um_die_stelle(raster, pose, stelle, radius_m: float = 0.15):
        """Belegte Zellen eines Rasters (Karte oder Kostenkarte) rings um eine Stelle."""
        if raster is None or pose is None:
            return None
        try:
            return zellen_um(
                raster.data, raster.info.width, raster.info.height, raster.info.resolution,
                (raster.info.origin.position.x, raster.info.origin.position.y),
                pose, stelle, radius_m=radius_m)
        except ValueError:
            return None

    def alter(schluessel: str) -> str:
        zeit = stand[schluessel]
        return 'nie' if zeit is None else f'vor {time.monotonic() - zeit:.0f} s'

    def herkunft_befund(stelle, pose, laser=None) -> dict:
        """Was Karte, Nahsensoren und Laser an einer belegten Stelle (im Rahmen des
        Roboters) sehen; ohne ``laser`` misst es selbst (1 s Laserbild).

        Die Karte wird rings um die Stelle abgefragt, nicht nur vor dem Roboter
        (vorher galt eine Stelle seitlich daneben fälschlich als „frei“, KI-F9).
        """
        if laser is None:
            scans, boden_lidar = laserbild(1.0)
            if scans is not None:
                laser = []
                vermesse(scans, boden_lidar, None, laser)
        return herkunft(
            stelle, karte=zellen_um_die_stelle(stand['karte'], pose, stelle), nah=nah_jetzt(),
            laser=None if laser is None else np.asarray(laser, dtype=float).reshape(-1, 2))

    def herkunft_zeile(stelle, pose, laser=None, befund=None) -> str:
        """Woher eine belegte Stelle stammt, in einem Satz (``befund``: schon gemessen)."""
        text = herkunft_text(herkunft_befund(stelle, pose, laser) if befund is None else befund)
        return (text[:-1] + f' (Karte {alter("karte_t")}, Kostenkarte '
                f'{alter("kostenkarte_t")} empfangen).')

    def naechste_stelle(pose):
        """Die nächste belegte Zelle im Fahrstreifen bis 1,5 m (Rahmen des Roboters) oder None."""
        karte = stand['kostenkarte']
        if karte is None or pose is None:
            return None
        try:
            return kostenkarte_voraus(
                karte.data, karte.info.width, karte.info.height, karte.info.resolution,
                (karte.info.origin.position.x, karte.info.origin.position.y),
                pose)['im_streifen']
        except ValueError:
            return None

    def im_roboterrahmen(ort, pose):
        dx, dy = float(ort[0]) - pose[0], float(ort[1]) - pose[1]
        c, s = math.cos(pose[2]), math.sin(pose[2])
        return c * dx + s * dy, -s * dx + c * dy

    def weg_in_der_kostenkarte(punkte, pose, laser=None):
        """Zeilen zur Kostenkarte auf dem ganzen Weg; dazu, ob sie frei ist."""
        karte = stand['kostenkarte']
        if karte is None or pose is None:
            return ['Kostenkarte auf dem Weg: nicht empfangen – Kostenkarte passt nicht.'], False
        laenge = sum(math.hypot(b[0] - a[0], b[1] - a[1])
                     for a, b in zip([pose[:2], *punkte[:-1]], punkte))
        try:
            befund = belegt_auf_dem_weg(
                karte.data, karte.info.width, karte.info.height, karte.info.resolution,
                (karte.info.origin.position.x, karte.info.origin.position.y), pose, punkte)
        except ValueError as grund:
            return [f'Kostenkarte auf dem Weg: {grund} – Kostenkarte passt nicht.'], False
        zeilen = [weg_belegt_text(befund, laenge)]
        if befund is not None:
            stelle = im_roboterrahmen(befund['ort'], pose)
            quellen = herkunft_befund(stelle, pose, laser)    # derselbe Befund in Zeile und Beleg
            zeilen.append(herkunft_zeile(stelle, pose, befund=quellen))
            umgebung = {name: zellen_um_die_stelle(stand[name], pose, stelle, 0.30)
                        for name in ('kostenkarte', 'karte')}
            belege.schreibe('sperre', {
                'zeit_unix': round(time.time(), 2), 'pose_karte': list(pose),
                'punkte_karte': [list(map(float, q)) for q in punkte],
                'befund': {k: (list(v) if isinstance(v, tuple) else v)
                           for k, v in befund.items()},
                'stelle_roboter': list(stelle),
                'zellen_kostenkarte': (None if umgebung['kostenkarte'] is None
                                       else umgebung['kostenkarte'].round(3).tolist()),
                'zellen_karte': (None if umgebung['karte'] is None
                                 else umgebung['karte'].round(3).tolist()),
                'alter_kostenkarte': alter('kostenkarte_t'), 'alter_karte': alter('karte_t'),
                # Punkte im Umkreis der Stelle (wie in der Herkunftszeile), nicht alle
                'herkunft': quellen, 'laser_nahe': quellen['laser']})
        return zeilen, befund is None

    def plan_zeilen(o, achse, hindernisse, sicht, pose):
        """Was ``--zur-tuer`` für eine Öffnung täte; Zeilen, Entscheidung, Anfahrt."""
        zeilen = [lage_text(o, achse=achse), achse_text(achse)]
        weg, weg_passt = weg_text(o, hindernisse, wahl.vor, wahl.hinter, achse)
        zeilen.append(weg)
        lage_passt = not aufstellung_hinweise(aufstellung(o.pfosten, achse=achse['normal']))
        kosten_frei = True
        if lage_passt and weg_passt and pose is not None:
            try:
                linie = gerade_durch_die_tuer(o.pfosten, pose, vor_m=wahl.vor,
                                              hinter_m=wahl.hinter, achse=achse['normal'])
                kz, kosten_frei = weg_in_der_kostenkarte(linie, pose, hindernisse)
                zeilen += kz
            except ValueError as grund:
                zeilen.append(f'Fahrlinie: {grund}.')
                kosten_frei = False
        weg_a = None
        if not (lage_passt and weg_passt and kosten_frei):
            zeile, weg_a, _ = anfahrt_zeile(o, hindernisse, sicht, achse)
            zeilen.append(zeile)
            if weg_a is not None and pose is not None:
                kz, anfahrt_frei = weg_in_der_kostenkarte(
                    anfahrt_im_kartenrahmen(weg_a, pose), pose, hindernisse)
                zeilen += kz
                if not anfahrt_frei:
                    weg_a = None
        geschaetzt = nur_geschaetzt(o)
        if geschaetzt:
            zeilen.append(GESCHAETZT_TEXT)
        plan = entscheidung(lage_passt, weg_passt and kosten_frei, weg_a is not None,
                            geschaetzt)
        zeilen.append(ENTSCHEIDUNG_TEXT[plan])
        return zeilen, plan, weg_a

    def phase() -> Optional[str]:
        return (stand['status'] or {}).get('phase')

    def meldung() -> str:
        return str((stand['status'] or {}).get('message', ''))

    def ende_senden() -> bool:
        """Dem wartenden Erkunder das Ende sagen; wahr, wenn er danach nicht mehr läuft."""
        if wahl.nur_messen or sender.empfaenger() == 0:
            return False
        if marke.gesetzt():
            raise Abbruch()
        sender.sende(ende_botschaft(kennung=f'ende-{int(time.time())}',
                                    quelle=wahl.quelle, zeit_s=time.time(),
                                    frame=wahl.karten_rahmen))
        drehe(10.0, lambda: (stand['status'] or {}).get('state') not in ('running', None))
        zustand = (stand['status'] or {}).get('state')
        print(f'Ende an den Erkunder gesendet; Zustand {zustand!r}; {meldung()}')
        return zustand not in ('running', None)

    def nichts_gesendet(grund: str, code: int = 2) -> int:
        """Nichts senden, aber dem wartenden Erkunder das Ende sagen."""
        print(f'Nichts gesendet: {grund}.')
        ende_senden()
        return code

    def senden_und_beobachten(punkte, art_name: str, bemerkung, gesamt: float,
                              weiter: bool = False):
        """Fahrziel senden und die Meldungen zeigen, bis es erreicht oder vorbei ist.

        Rückgabe ``(zustand, angekommen)``: ``angekommen`` heißt, der Erkunder
        hat ein Ziel mit Folgeziel erreicht und wartet stehend auf das nächste.
        """
        kennung = (f'{wahl.kennung}-{art_name}' if wahl.kennung
                   else f'{art_name}-{int(time.time())}')
        text = botschaft(punkte, kennung=kennung, quelle=wahl.quelle, zeit_s=time.time(),
                         frame=wahl.karten_rahmen, bemerkung=bemerkung, weiter=weiter)
        if marke.gesetzt():
            raise Abbruch()
        sender.sende(text)
        print(f'Fahrziel gesendet: {len(punkte)} Punkt(e), zusammen {gesamt:.2f} m, '
              f'Quelle {wahl.quelle}, Kennung {kennung}'
              + ('; danach folgt die Durchfahrt in derselben Mission.' if weiter else '.'),
              flush=True)
        letzte = None
        bis = time.monotonic() + wahl.beobachten
        while rclpy.ok() and time.monotonic() < bis:
            if marke.gesetzt():
                raise Abbruch()
            rclpy.spin_once(knoten, timeout_sec=0.2)
            jetzt = (phase(), meldung())
            if jetzt != letzte and jetzt[0] != WARTEPHASE:
                letzte = jetzt
                print(f'  Erkunder: {jetzt[1]}', flush=True)
            if (weiter and jetzt[0] == WARTEPHASE
                    and jetzt[1].startswith('Etappenfahrt: Fahrziel ')
                    and ' erreicht (' in jetzt[1]):
                print(f'  Erkunder: {jetzt[1]}', flush=True)
                return (stand['status'] or {}).get('state'), True
            if (stand['status'] or {}).get('state') not in ('running', None):
                break
        return (stand['status'] or {}).get('state'), False

    def schluss(zustand, art_name: str) -> int:
        """Ende der Fahrt: Zustand, Kostenkarte, nach einem Halt die Herkunft."""
        print(f'Ende: Zustand des Erkunders {zustand!r}; {meldung()}')
        drehe(1.5)                       # die Kostenkarte kommt einmal je Sekunde
        print(kostenkarte_zeile())
        # Nach einem Halt: woher stammt die nächste belegte Stelle vor dem Roboter?
        pose_ende = lage_in_der_karte()
        stelle = naechste_stelle(pose_ende)
        if stelle is not None:
            print(herkunft_zeile(stelle, pose_ende))
        print(nah_text(nah_jetzt()))
        # Der Erkunder meldet einen gelungenen Auftrag ohne Flächenziel als „partial“.
        gelungen = (zustand in ('partial', 'success')
                    and meldung().startswith('Etappenfahrt abgeschlossen'))
        if gelungen and art_name == 'anfahrt':
            print('Anfahrt abgeschlossen.')
        elif gelungen and art_name == 'tuer':
            print('Durchfahrt abgeschlossen.')
        return 0 if gelungen else 1

    def durchfahrt_nach_anfahrt(gemerkt: dict) -> int:
        """Nach der Anfahrt: neu messen, die Tür wiederfinden, gerade hindurch."""
        drehe(1.0)
        scans, boden_lidar = laserbild(wahl.messdauer)
        if scans is None:
            return nichts_gesendet('Kein Scan oder keine Montage des LiDAR (TF) nach der '
                                   'Anfahrt', 4)
        hindernisse2: List = []
        sicht2: dict = {}
        gefunden2 = vermesse(scans, boden_lidar, [], hindernisse2, sicht2)
        print(f'Neu gemessen nach der Anfahrt: {len(scans)} Scans, {len(gefunden2)} '
              f'Öffnung(en):')
        print(tabelle(gefunden2))
        pose2 = lage_in_der_karte()
        if pose2 is None:
            return nichts_gesendet('Die Lage des Roboters in der Karte fehlt (TF)', 4)
        tueren2 = [o for o in gefunden2
                   if o.befahrbar and wahl.breite_min <= o.breite_m <= wahl.breite_max]
        # Nur zur Meldung: wie weit jede Öffnung neben der gemerkten Tür liegt.
        for zeile in wiederfinden_zeilen(tueren2, gemerkt, pose2):
            print(zeile)
        o = wiederfinden(tueren2, gemerkt, pose2)
        if o is None:
            return nichts_gesendet('Die Tür von vorhin ist nach der Anfahrt nicht '
                                   'wiederzufinden')
        print(f'Wiedergefunden: Öffnung {o.nr}, {o.breite_m:.2f} m breit, '
              f'{o.richtung_grad:+.0f}°, {o.entfernung_m:.2f} m.')
        if nur_geschaetzt(o):
            return nichts_gesendet('Nach der Anfahrt ist der zweite Pfosten weiter nur '
                                   'geschätzt (Lot); durch so eine Öffnung fährt er nicht')
        achse2 = tuerachse(o.pfosten, hindernisse2)
        if achse2['quelle'] != 'wand' and gemerkt['quelle'] == 'wand':
            achse2 = achse_aus_karte(gemerkt, pose2)
        print(lage_text(o, achse=achse2))
        print(achse_text(achse2))
        weg2, weg_passt = weg_text(o, hindernisse2, wahl.vor, wahl.hinter, achse2)
        print(weg2)
        if aufstellung_hinweise(aufstellung(o.pfosten, achse=achse2['normal'])):
            return nichts_gesendet('Die Aufstellung nach der Anfahrt passt nicht')
        if not weg_passt:
            return nichts_gesendet('Neben der Fahrlinie ist nicht genug frei')
        drehe(2.0)
        try:
            punkte2 = gerade_durch_die_tuer(o.pfosten, pose2, vor_m=wahl.vor,
                                            hinter_m=wahl.hinter, achse=achse2['normal'])
            gesamt2 = pruefe_grenzen(punkte2, pose2[:2])
        except ValueError as grund:
            return nichts_gesendet(str(grund))
        zeilen2, frei2 = weg_in_der_kostenkarte(punkte2, pose2, hindernisse2)
        for zeile in zeilen2:
            print(zeile)
        if not frei2:
            return nichts_gesendet('Auf dem Weg ist die Kostenkarte belegt; dort könnte der '
                                   'Nahbereichs-Halt des Erkunders anhalten')
        bemerkung2 = (f'Öffnung {o.nr}, {o.breite_m:.2f} m breit, {o.richtung_grad:+.0f}°, '
                      f'{o.entfernung_m:.2f} m (nach der Anfahrt)')
        zustand2, _ = senden_und_beobachten(punkte2, 'tuer', bemerkung2, gesamt2)
        return schluss(zustand2, 'tuer')

    try:
        if not wahl.nur_messen:
            print(f'Warte, bis der Erkunder auf ein Fahrziel wartet (höchstens '
                  f'{wahl.warten:.0f} s) …', flush=True)
            if not drehe(wahl.warten, lambda: phase() == WARTEPHASE
                         and sender.empfaenger() > 0):
                print('Der Erkunder wartet nicht auf ein Fahrziel '
                      f'(Phase: {phase()!r}). Nichts gesendet.')
                return 3

        if wahl.ende:
            print(f'Kein Fahrziel: Ende auf Wunsch (Quelle {wahl.quelle}).')
            return 0 if ende_senden() else 1

        wahl_daten = None
        if wahl.wahl is not None:
            if wahl_fehler is None:
                try:
                    wahl_daten = wahl_lesen(wahl_text, jetzt_s=time.time(),
                                            rahmen=wahl.karten_rahmen)
                except ValueError as grund:
                    wahl_fehler = str(grund)
            if wahl_fehler is not None:
                return nichts_gesendet(wahl_fehler)
            print(f'Wahl der KI: Nr. {wahl_daten["nr"]} aus der Blickrunde '
                  f'{wahl_daten.get("runde")!r} ({wahl_daten.get("einordnung")}, '
                  f'{float(wahl_daten.get("breite_m") or 0.0):.2f} m breit).')

        punkte: List = []
        bemerkung = None
        weg_anfahrt = None
        plan = None
        zur_tuer = wahl.zur_tuer
        if wahl.tuer or wahl.vor_die_tuer or zur_tuer:
            scans, boden_lidar = laserbild(wahl.messdauer)
            if scans is None:
                return nichts_gesendet('Kein Scan oder keine Montage des LiDAR (TF)', 4)
            protokoll: List[dict] = []
            hindernisse: List = []
            sicht: dict = {}
            gefunden = vermesse(scans, boden_lidar, protokoll, hindernisse, sicht)
            print(f'{len(scans)} Scans, {len(gefunden)} Öffnung(en):')
            print(tabelle(gefunden))
            tueren = [o for o in gefunden
                      if o.befahrbar and wahl.breite_min <= o.breite_m <= wahl.breite_max]
            achsen = {o.nr: tuerachse(o.pfosten, hindernisse) for o in tueren}
            pose_wahl, zur_wahl_o, zur_wahl_grund = None, None, None
            if wahl_daten is not None:
                if lage_in_der_karte() is None:
                    drehe(3.0, lambda: lage_in_der_karte() is not None)
                pose_wahl = lage_in_der_karte()
                if pose_wahl is None:
                    return nichts_gesendet('Die Lage des Roboters in der Karte fehlt (TF); '
                                           'die Wahl der KI lässt sich nicht zuordnen', 4)
                try:
                    zur_wahl_o, abstand_wahl = oeffnung_zur_wahl(
                        gefunden, tueren, wahl_daten, pose_wahl,
                        breite_von_m=wahl.breite_min, breite_bis_m=wahl.breite_max)
                    print(f'Zur Wahl der KI passt Öffnung {zur_wahl_o.nr} '
                          f'(die Mitten liegen {abstand_wahl:.2f} m auseinander).')
                except ValueError as grund:
                    zur_wahl_grund = str(grund)
                    print(f'Zur Wahl der KI passt keine türbreite Öffnung: {grund}.')
            if wahl.nur_messen:
                # Die Kostenkarte kommt einmal je Sekunde und ist groß.
                drehe(5.0, lambda: stand['kostenkarte'] is not None)
                pose_jetzt = lage_in_der_karte()
                plaene = []
                if tueren:
                    print(f'Türbreit vermessen ({wahl.breite_min:.2f} bis '
                          f'{wahl.breite_max:.2f} m):')
                    for o in tueren:
                        if zur_tuer:
                            zeilen_o, plan_o, _ = plan_zeilen(o, achsen[o.nr], hindernisse,
                                                              sicht, pose_jetzt)
                            plaene.append(plan_o)
                            for z in zeilen_o:
                                print('  ' + z)
                            continue
                        if wahl.vor_die_tuer:
                            print('  ' + lage_text(o, mit_hinweisen=False))
                            zeile, weg_a, _ = anfahrt_zeile(o, hindernisse, sicht, achsen[o.nr])
                            print('  ' + zeile)
                            if weg_a is not None and pose_jetzt is not None:
                                for z in weg_in_der_kostenkarte(
                                        anfahrt_im_kartenrahmen(weg_a, pose_jetzt), pose_jetzt,
                                        hindernisse)[0]:
                                    print('  ' + z)
                            continue
                        print('  ' + lage_text(o, achse=achsen[o.nr]))
                        if nur_geschaetzt(o):
                            print('  ' + GESCHAETZT_TEXT + ' Mit --tuer sendet es '
                                  'hier nichts.')
                        print('  ' + achse_text(achsen[o.nr]))
                        print('  ' + weg_text(o, hindernisse, wahl.vor, wahl.hinter,
                                              achsen[o.nr])[0])
                        if pose_jetzt is None:
                            print('  Kostenkarte auf dem Weg: Lage in der Karte fehlt (TF) – '
                                  'Kostenkarte passt nicht.')
                            continue
                        try:
                            linie = gerade_durch_die_tuer(o.pfosten, pose_jetzt,
                                                          vor_m=wahl.vor, hinter_m=wahl.hinter,
                                                          achse=achsen[o.nr]['normal'])
                        except ValueError:
                            continue
                        for z in weg_in_der_kostenkarte(linie, pose_jetzt, hindernisse)[0]:
                            print('  ' + z)
                    if zur_tuer and len(tueren) > 1:
                        v = vorschlag(tueren)
                        print(f'Vorschlag: Nr. {v.nr}, {v.breite_m:.2f} m breit, '
                              f'{v.richtung_grad:+.1f}°, {v.entfernung_m:.2f} m (dahinter '
                              f'{v.tiefe_m:.2f} m frei, die tiefste türbreite Öffnung).')
                else:
                    print(f'Keine Öffnung ist türbreit vermessen ({wahl.breite_min:.2f} '
                          f'bis {wahl.breite_max:.2f} m). So würde nichts gesendet.')
                if zur_tuer and all(plan_o == 'nichts' for plan_o in plaene):
                    ersatz = tuer_aus_blatt(hindernisse, 1 + max((o.nr for o in gefunden),
                                                                 default=0))
                    if ersatz is not None:
                        o_e, achse_e, fund_e = ersatz
                        print(blatt_text(fund_e))
                        print(f'Tür hinter dem Türblatt geschätzt: Nr. {o_e.nr}, Richtung '
                              f'{o_e.richtung_grad:+.1f}° (für --richtung).')
                        zeilen_e, plan_e, _ = plan_zeilen(o_e, achse_e, hindernisse, sicht,
                                                          pose_jetzt)
                        for z in zeilen_e:
                            print('  ' + z)
                print(kostenkarte_zeile())
                stelle = naechste_stelle(pose_jetzt)
                if stelle is not None:
                    print(herkunft_zeile(stelle, pose_jetzt, hindernisse))
                print(nah_text(nah_jetzt()))
                print(protokoll_text(protokoll))
                return 0
            ersatz = None
            if zur_tuer:
                ersatz = tuer_aus_blatt(hindernisse, 1 + max((o.nr for o in gefunden),
                                                             default=0))
                if ersatz is not None and not richtung_passt(ersatz[0], wahl.richtung,
                                                             wahl.richtung_toleranz):
                    ersatz = None
                if (ersatz is not None and wahl_daten is not None
                        and not blatt_passt_zur_wahl(ersatz[0], wahl_daten, pose_wahl)):
                    ersatz = None
            try:
                if wahl_daten is not None:
                    if zur_wahl_o is None:
                        raise ValueError(f'Die Wahl der KI ist hier nicht wiederzufinden: '
                                         f'{zur_wahl_grund}')
                    gewaehlt = zur_wahl_o
                else:
                    gewaehlt = waehle_oeffnung(
                        gefunden, nummer=wahl.nummer, richtung_grad=wahl.richtung,
                        toleranz_grad=wahl.richtung_toleranz,
                        breite_von_m=wahl.breite_min, breite_bis_m=wahl.breite_max)
                achse = achsen.get(gewaehlt.nr) or tuerachse(gewaehlt.pfosten, hindernisse)
            except ValueError as grund:
                if ersatz is None:
                    return nichts_gesendet(str(grund))
                print(f'Keine passende Öffnung vermessen ({grund}).')
                gewaehlt, achse = ersatz[0], ersatz[1]
            if zur_tuer:
                pose_jetzt = lage_in_der_karte()
                drehe(5.0, lambda: stand['kostenkarte'] is not None)
                zeilen_plan, plan, weg_anfahrt = plan_zeilen(gewaehlt, achse, hindernisse, sicht,
                                                             pose_jetzt)
                if plan == 'nichts' and ersatz is not None and gewaehlt is not ersatz[0]:
                    for z in zeilen_plan:
                        print(z)
                    gewaehlt, achse = ersatz[0], ersatz[1]
                    zeilen_plan, plan, weg_anfahrt = plan_zeilen(gewaehlt, achse, hindernisse,
                                                                 sicht, pose_jetzt)
                if ersatz is not None and gewaehlt is ersatz[0]:
                    print(blatt_text(ersatz[2]))
                    if plan == 'durchfahrt':
                        # Durch eine nur geschätzte Tür wird nicht gefahren.
                        plan = 'nichts'
                for z in zeilen_plan:
                    print(z)
                if plan == 'nichts':
                    return nichts_gesendet('Weder Durchfahrt noch Anfahrt passen')
            bemerkung = (f'Öffnung {gewaehlt.nr}, {gewaehlt.breite_m:.2f} m breit, '
                         f'{gewaehlt.richtung_grad:+.0f}°, {gewaehlt.entfernung_m:.2f} m'
                         + (' (hinter dem Türblatt geschätzt)'
                            if gewaehlt.schluss == 'blatt_geschaetzt' else '')
                         + ('' if wahl_daten is None
                            else f'; Wahl der KI Nr. {wahl_daten["nr"]}'))
            print(f'Gewählt: {bemerkung}.')
            if wahl.vor_die_tuer:
                print(lage_text(gewaehlt, mit_hinweisen=False))
                zeile, weg_anfahrt, noetig = anfahrt_zeile(gewaehlt, hindernisse, sicht, achse)
                print(zeile)
                if not noetig:
                    return nichts_gesendet('Er steht schon passend vor der Tür')
                if weg_anfahrt is None:
                    return nichts_gesendet('Die Anfahrt passt nicht')
        if wahl.tuer:
            print(lage_text(gewaehlt, achse=achse))
            if nur_geschaetzt(gewaehlt):
                print(GESCHAETZT_TEXT)
                return nichts_gesendet('Der zweite Pfosten ist nur geschätzt (Lot)')
            print(achse_text(achse))
            weg, weg_passt = weg_text(gewaehlt, hindernisse, wahl.vor, wahl.hinter, achse)
            print(weg)
            if not wahl.aufstellung_egal:
                if aufstellung_hinweise(aufstellung(gewaehlt.pfosten, achse=achse['normal'])):
                    return nichts_gesendet('Die Aufstellung passt nicht')
                if not weg_passt:
                    return nichts_gesendet('Neben der Fahrlinie ist nicht genug frei')

        pose = lage_in_der_karte()
        if pose is None:
            drehe(3.0, lambda: lage_in_der_karte() is not None)
            pose = lage_in_der_karte()
        if pose is None:
            return nichts_gesendet('Die Lage des Roboters in der Karte fehlt (TF)', 4)
        drehe(5.0, lambda: stand['kostenkarte'] is not None)
        print(kostenkarte_zeile())

        try:
            if wahl.vor_die_tuer or plan == 'anfahrt':
                punkte = anfahrt_im_kartenrahmen(weg_anfahrt, pose)
            elif wahl.tuer or plan == 'durchfahrt':
                punkte = gerade_durch_die_tuer(gewaehlt.pfosten, pose,
                                               vor_m=wahl.vor, hinter_m=wahl.hinter,
                                               achse=achse['normal'])
            elif wahl.punkt:
                punkte = punkt_relativ(*lies_punkt(wahl.punkt), pose)
            else:
                punkte = geradeaus(wahl.geradeaus, pose)
            gesamt = pruefe_grenzen(punkte, pose[:2])
        except ValueError as grund:
            return nichts_gesendet(str(grund))
        zeilen, frei = weg_in_der_kostenkarte(
            punkte, pose, hindernisse if (wahl.tuer or wahl.vor_die_tuer or zur_tuer) else None)
        # Bei --zur-tuer stehen dieselben Zeilen schon in der Entscheidung.
        for zeile in ([] if zur_tuer and frei else zeilen):
            print(zeile)
        if not frei and not wahl.aufstellung_egal:
            return nichts_gesendet('Auf dem Weg ist die Kostenkarte belegt; dort könnte der '
                                   'Nahbereichs-Halt des Erkunders anhalten')

        art_name = ('anfahrt' if wahl.vor_die_tuer or plan == 'anfahrt'
                    else 'tuer' if wahl.tuer or plan == 'durchfahrt'
                    else 'punkt' if wahl.punkt else 'gerade')
        # --zur-tuer: Anfahrt und Durchfahrt in einer Mission
        weiter = zur_tuer and plan == 'anfahrt'
        gemerkt = (tuer_merken(gewaehlt.pfosten, achse, pose, breite_m=gewaehlt.breite_m,
                               schluss=gewaehlt.schluss) if weiter else None)
        zustand, angekommen = senden_und_beobachten(punkte, art_name, bemerkung, gesamt,
                                                    weiter=weiter)
        if weiter and angekommen:
            print('Anfahrt abgeschlossen. Jetzt misst er neu und fährt in derselben Mission '
                  'hindurch.', flush=True)
            return durchfahrt_nach_anfahrt(gemerkt)
        return schluss(zustand, art_name)
    except Abbruch:
        print(f'Abgebrochen ({marke.signal}). Nach dem Signal wurde nichts mehr gesendet, '
              'auch kein Ende. Ein schon angenommenes Fahrziel fährt der Erkunder mit seiner '
              'Schutzkette zu Ende; sonst schließt er die Mission nach seiner Wartezeit von '
              'selbst.', flush=True)
        return RC_ABGEBROCHEN
    finally:
        ros_beenden([knoten], eigener_kontext=eigener_kontext)
        marke.abmelden()


if __name__ == '__main__':
    sys.exit(main())
