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

Für ``--tuer`` misst das Werkzeug die Öffnungen im Stand neu (zwei Sekunden
Laser), nimmt die gewählte und legt die Fahrpunkte auf die **gerade Linie
vom Standplatz durch die Türmitte**: einen 1,2 m vor und einen 0,6 m hinter
der Türlinie. Es sendet nichts, wenn es die Öffnung nicht eindeutig findet,
wenn sie nicht türbreit vermessen ist (0,65 bis 0,95 m), wenn der Roboter
nicht passend vor der Tür steht oder wenn neben der Fahrlinie nicht
beidseits 0,30 m frei sind (gemessen am selben Laserbild: Türblatt,
Pfosten, alles, was im Weg steht); dann sagt es, was an der Aufstellung zu
ändern ist. ``--tuer --nur-messen`` zeigt dasselbe, ohne zu senden, und dazu
das Protokoll der Vermessung.

``--zur-tuer`` entscheidet selbst: Passen Aufstellung, Weg und Kostenkarte,
sendet es die Durchfahrt; sonst die Anfahrt vor die Tür (danach eine zweite
Mission und ``--tuer``). Niemand muss den Roboter dafür umstellen. Die
Türachse kommt in allen Betrieben aus der geraden Wand neben der Tür, nicht
nur aus den zwei Kanten.

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
    VOR_DER_TUER_M, achse_text, anfahrt, anfahrt_im_kartenrahmen, anfahrt_text, aufstellung,
    aufstellung_hinweise, belegt_auf_dem_weg, botschaft, freiraum, freiraum_hinweise,
    gerade_durch_die_tuer, gerade_linie, geradeaus, herkunft, herkunft_text, in_den_boden,
    kostenkarte_text, kostenkarte_voraus, nah_text, pruefe_grenzen, punkt_relativ,
    tuerachse, weg_belegt_text, wolke_xyz, zellen_im_streifen,
)
from lotse.geometrie import aus_tf  # noqa: E402
from lotse.kandidaten import TUERBREIT_M, Oeffnung, oeffnungen  # noqa: E402

WARTEPHASE = 'stage_drive_wait_target'


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


def entscheidung(lage_passt: bool, weg_passt: bool, anfahrt_moeglich: bool) -> str:
    """Was ``--zur-tuer`` sendet: ``'durchfahrt'``, ``'anfahrt'`` oder ``'nichts'``.

    Steht der Roboter passend und ist die gerade Linie frei, fährt er gleich
    hindurch. Sonst stellt er sich zuerst selbst vor die Tür, wenn die
    Anfahrt geprüft möglich ist. Niemand muss ihn dafür umstellen.
    """
    if lage_passt and weg_passt:
        return 'durchfahrt'
    if not lage_passt and anfahrt_moeglich:
        return 'anfahrt'
    return 'nichts'


ENTSCHEIDUNG_TEXT = {
    'durchfahrt': 'Entscheidung: Durchfahrt – er steht passend, gerade durch die Türmitte.',
    'anfahrt': ('Entscheidung: Anfahrt – er stellt sich zuerst selbst vor die Tür; danach '
                'eine zweite Mission und die Durchfahrt mit --tuer.'),
    'nichts': 'Entscheidung: keine Fahrt – weder Durchfahrt noch Anfahrt passen.',
}


def vorschlag(tueren: Sequence[Oeffnung]) -> Optional[Oeffnung]:
    """Die türbreite Öffnung mit dem meisten freien Raum dahinter (eine Tür
    führt in einen Raum, eine Lücke zwischen Möbeln nicht)."""
    return max(tueren, key=lambda o: o.tiefe_m, default=None)


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
    e.add_argument('--nummer', type=int, help='Nummer der Öffnung aus der Tabelle')
    e.add_argument('--richtung', type=float, metavar='GRAD',
                   help='Richtung der gemeinten Öffnung; 0 = voraus, positiv = links')
    e.add_argument('--richtung-toleranz', type=float, default=25.0)
    e.add_argument('--quelle', choices=('ki', 'mensch', 'test'), default='test',
                   help='wer gewählt hat; steht später in jeder Meldung des Erkunders')
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
    return e


def main(argv=None) -> int:
    # Ohne Terminal puffert Python die Ausgabe; die Zeilen kämen sonst erst am Ende.
    for strom in (sys.stdout, sys.stderr):
        if hasattr(strom, 'reconfigure'):
            strom.reconfigure(line_buffering=True)
    wahl = eingabe().parse_args(argv)
    import rclpy
    from rclpy.qos import (QoSDurabilityPolicy, QoSProfile, QoSReliabilityPolicy,
                           qos_profile_sensor_data)
    import numpy as np
    from nav_msgs.msg import OccupancyGrid
    from sensor_msgs.msg import LaserScan, PointCloud2
    from std_msgs.msg import String
    from tf2_ros import Buffer, TransformListener

    from ki_verbindung_ros import Fahrzielsender

    rclpy.init()
    knoten = rclpy.create_node('ki_fahrziel')
    stand = {'status': None, 'scans': [], 'rahmen': None, 'sammeln': False,
             'kostenkarte': None, 'karte': None, 'nah': {'links': [], 'rechts': []}}

    def auf_kostenkarte(nachricht):
        stand['kostenkarte'] = nachricht

    def auf_karte(nachricht):
        stand['karte'] = nachricht

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
        ende = time.monotonic() + sekunden
        while rclpy.ok() and time.monotonic() < ende:
            rclpy.spin_once(knoten, timeout_sec=0.05)
            if fertig():
                return True
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
        return list(stand['scans']), aus_tf([v.x, v.y, v.z], [q.x, q.y, q.z, q.w],
                                            wahl.basis_hoehe)

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

    def karte_vor_dem_roboter(pose):
        """Belegte Zellen der SLAM-Karte vor dem Roboter (voraus, seitlich) oder None."""
        karte = stand['karte']
        if karte is None or pose is None:
            return None
        try:
            return zellen_im_streifen(
                karte.data, karte.info.width, karte.info.height, karte.info.resolution,
                (karte.info.origin.position.x, karte.info.origin.position.y),
                pose[:2], pose[2], von_m=0.0, bis_m=4.0, halb_m=0.70)
        except ValueError:
            return None

    def herkunft_zeile(stelle, pose, laser=None) -> str:
        """Woher eine belegte Stelle (im Rahmen des Roboters) stammt, in einem Satz."""
        if laser is None:
            scans, boden_lidar = laserbild(1.0)
            if scans is not None:
                laser = []
                vermesse(scans, boden_lidar, None, laser)
        return herkunft_text(herkunft(
            stelle, karte=karte_vor_dem_roboter(pose), nah=nah_jetzt(),
            laser=None if laser is None else np.asarray(laser, dtype=float).reshape(-1, 2)))

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
            zeilen.append(herkunft_zeile(im_roboterrahmen(befund['ort'], pose), pose, laser))
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
        plan = entscheidung(lage_passt, weg_passt and kosten_frei, weg_a is not None)
        zeilen.append(ENTSCHEIDUNG_TEXT[plan])
        return zeilen, plan, weg_a

    def phase() -> Optional[str]:
        return (stand['status'] or {}).get('phase')

    def meldung() -> str:
        return str((stand['status'] or {}).get('message', ''))

    try:
        if not wahl.nur_messen:
            print(f'Warte, bis der Erkunder auf ein Fahrziel wartet (höchstens '
                  f'{wahl.warten:.0f} s) …', flush=True)
            if not drehe(wahl.warten, lambda: phase() == WARTEPHASE
                         and sender.empfaenger() > 0):
                print('Der Erkunder wartet nicht auf ein Fahrziel '
                      f'(Phase: {phase()!r}). Nichts gesendet.')
                return 3

        punkte: List = []
        bemerkung = None
        weg_anfahrt = None
        plan = None
        zur_tuer = wahl.zur_tuer
        if wahl.tuer or wahl.vor_die_tuer or zur_tuer:
            scans, boden_lidar = laserbild(wahl.messdauer)
            if scans is None:
                print('Kein Scan oder keine Montage des LiDAR (TF). Nichts gesendet.')
                return 4
            protokoll: List[dict] = []
            hindernisse: List = []
            sicht: dict = {}
            gefunden = vermesse(scans, boden_lidar, protokoll, hindernisse, sicht)
            print(f'{len(scans)} Scans, {len(gefunden)} Öffnung(en):')
            print(tabelle(gefunden))
            tueren = [o for o in gefunden
                      if o.befahrbar and wahl.breite_min <= o.breite_m <= wahl.breite_max]
            achsen = {o.nr: tuerachse(o.pfosten, hindernisse) for o in tueren}
            if wahl.nur_messen:
                # Die Kostenkarte kommt einmal je Sekunde und ist groß.
                drehe(5.0, lambda: stand['kostenkarte'] is not None)
                pose_jetzt = lage_in_der_karte()
                if tueren:
                    print(f'Türbreit vermessen ({wahl.breite_min:.2f} bis '
                          f'{wahl.breite_max:.2f} m):')
                    for o in tueren:
                        if zur_tuer:
                            for z in plan_zeilen(o, achsen[o.nr], hindernisse, sicht,
                                                 pose_jetzt)[0]:
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
                print(kostenkarte_zeile())
                stelle = naechste_stelle(pose_jetzt)
                if stelle is not None:
                    print(herkunft_zeile(stelle, pose_jetzt, hindernisse))
                print(nah_text(nah_jetzt()))
                print(protokoll_text(protokoll))
                return 0
            try:
                gewaehlt = waehle_oeffnung(
                    gefunden, nummer=wahl.nummer, richtung_grad=wahl.richtung,
                    toleranz_grad=wahl.richtung_toleranz,
                    breite_von_m=wahl.breite_min, breite_bis_m=wahl.breite_max)
            except ValueError as grund:
                print(f'Nichts gesendet: {grund}.')
                return 2
            bemerkung = (f'Öffnung {gewaehlt.nr}, {gewaehlt.breite_m:.2f} m breit, '
                         f'{gewaehlt.richtung_grad:+.0f}°, {gewaehlt.entfernung_m:.2f} m')
            print(f'Gewählt: {bemerkung}.')
            achse = achsen.get(gewaehlt.nr) or tuerachse(gewaehlt.pfosten, hindernisse)
            if zur_tuer:
                pose_jetzt = lage_in_der_karte()
                drehe(5.0, lambda: stand['kostenkarte'] is not None)
                zeilen_plan, plan, weg_anfahrt = plan_zeilen(gewaehlt, achse, hindernisse, sicht,
                                                             pose_jetzt)
                for z in zeilen_plan:
                    print(z)
                if plan == 'nichts':
                    print('Nichts gesendet: Weder Durchfahrt noch Anfahrt passen.')
                    return 2
            if wahl.vor_die_tuer:
                print(lage_text(gewaehlt, mit_hinweisen=False))
                zeile, weg_anfahrt, noetig = anfahrt_zeile(gewaehlt, hindernisse, sicht, achse)
                print(zeile)
                if not noetig:
                    print('Nichts gesendet: Er steht schon passend vor der Tür.')
                    return 2
                if weg_anfahrt is None:
                    print('Nichts gesendet: Die Anfahrt passt nicht.')
                    return 2
        if wahl.tuer:
            print(lage_text(gewaehlt, achse=achse))
            print(achse_text(achse))
            weg, weg_passt = weg_text(gewaehlt, hindernisse, wahl.vor, wahl.hinter, achse)
            print(weg)
            if not wahl.aufstellung_egal:
                if aufstellung_hinweise(aufstellung(gewaehlt.pfosten, achse=achse['normal'])):
                    print('Nichts gesendet: Die Aufstellung passt nicht.')
                    return 2
                if not weg_passt:
                    print('Nichts gesendet: Neben der Fahrlinie ist nicht genug frei.')
                    return 2

        pose = lage_in_der_karte()
        if pose is None:
            drehe(3.0, lambda: lage_in_der_karte() is not None)
            pose = lage_in_der_karte()
        if pose is None:
            print('Die Lage des Roboters in der Karte fehlt (TF). Nichts gesendet.')
            return 4
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
            print(f'Nichts gesendet: {grund}.')
            return 2
        zeilen, frei = weg_in_der_kostenkarte(
            punkte, pose, hindernisse if (wahl.tuer or wahl.vor_die_tuer or zur_tuer) else None)
        # Bei --zur-tuer stehen dieselben Zeilen schon in der Entscheidung.
        for zeile in ([] if zur_tuer and frei else zeilen):
            print(zeile)
        if not frei and not wahl.aufstellung_egal:
            print('Nichts gesendet: Auf dem Weg ist die Kostenkarte belegt; dort hielte der '
                  'Erkunder an.')
            return 2

        art_name = ('anfahrt' if wahl.vor_die_tuer or plan == 'anfahrt'
                    else 'tuer' if wahl.tuer or plan == 'durchfahrt'
                    else 'punkt' if wahl.punkt else 'gerade')
        kennung = wahl.kennung or f'{art_name}-{int(time.time())}'
        text = botschaft(punkte, kennung=kennung, quelle=wahl.quelle, zeit_s=time.time(),
                         frame=wahl.karten_rahmen, bemerkung=bemerkung)
        sender.sende(text)
        print(f'Fahrziel gesendet: {len(punkte)} Punkt(e), zusammen {gesamt:.2f} m, '
              f'Quelle {wahl.quelle}, Kennung {kennung}.', flush=True)

        letzte = None
        ende = time.monotonic() + wahl.beobachten
        while rclpy.ok() and time.monotonic() < ende:
            rclpy.spin_once(knoten, timeout_sec=0.2)
            jetzt = (phase(), meldung())
            if jetzt != letzte and jetzt[0] != WARTEPHASE:
                letzte = jetzt
                print(f'  Erkunder: {jetzt[1]}', flush=True)
            if (stand['status'] or {}).get('state') not in ('running', None):
                break
        zustand = (stand['status'] or {}).get('state')
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
            print('Anfahrt abgeschlossen. Als Nächstes die Durchfahrt: zweite Mission, dann '
                  'fahrziel_senden.py --tuer --richtung 0.')
        elif gelungen and art_name == 'tuer':
            # auch für --tuer, die zweite Mission nach der Anfahrt
            print('Durchfahrt abgeschlossen.')
        return 0 if gelungen else 1
    finally:
        knoten.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    sys.exit(main())
