#!/usr/bin/env python3
"""Auf dem Roboter: dem Erkunder ein Fahrziel für die Etappenfahrt geben.

Der Erkunder läuft im Betrieb „Etappenfahrt“ (Startargument
``stage_drive_only:=true``) und wartet nach dem Missionsstart auf genau ein
Fahrziel. Dieses Werkzeug wartet, bis er wartet, berechnet das Ziel und
schickt es ihm als Text. Es fährt nicht selbst: Gefahren wird vom Erkunder,
in kurzen geraden Etappen, mit Fahrtor und Kollisionsmonitor.

    # eine gerade Etappe von einem halben Meter (erster Test)
    python3 fahrziel_senden.py --geradeaus 0.5

    # durch die Öffnung, die etwa 20° links liegt (Nummer wählt die KI oder ein Mensch)
    python3 fahrziel_senden.py --tuer --richtung 20 --quelle mensch

Für ``--tuer`` misst das Werkzeug die Öffnungen im Stand neu (zwei Sekunden
Laser), nimmt die gewählte und legt einen Punkt 0,7 m vor und einen 0,6 m
hinter die Tür, beide auf der Türachse. Findet es die Öffnung nicht
eindeutig, sendet es nichts.

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
    botschaft, durch_die_tuer, geradeaus, pruefe_grenzen,
)
from lotse.geometrie import aus_tf  # noqa: E402
from lotse.kandidaten import TUERBREIT_M, Oeffnung, oeffnungen  # noqa: E402

WARTEPHASE = 'stage_drive_wait_target'


def waehle_oeffnung(liste: Sequence[Oeffnung], *, nummer: Optional[int] = None,
                    richtung_grad: Optional[float] = None,
                    toleranz_grad: float = 25.0,
                    nur_tuergross: bool = True) -> Oeffnung:
    """Die gemeinte Öffnung; ``ValueError`` mit Grund, wenn sie nicht eindeutig ist."""
    waehlbar = [o for o in liste if o.befahrbar
                and (not nur_tuergross or o.breite_m <= TUERBREIT_M)]
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


def tabelle(liste: Sequence[Oeffnung]) -> str:
    zeilen = ['Nr  Breite  Richtung  Entfernung  befahrbar  Schluss']
    for o in liste:
        zeilen.append(
            f'{o.nr:>2}  {o.breite_m:5.2f} m  {o.richtung_grad:+7.1f}°  '
            f'{o.entfernung_m:8.2f} m  {"ja" if o.befahrbar else "nein":>9}  {o.schluss}')
    return '\n'.join(zeilen)


def vermesse(scans: List[dict], boden_lidar) -> List[Oeffnung]:
    """Öffnungen aus Scans im Stand, im Standpunktrahmen (Antriebsmitte)."""
    gier = [0.0] * len(scans)
    winkel, profil = stand_profil(scans, gier, boden_lidar)
    return oeffnungen(winkel, profil, ursprung=profil_ursprung(gier, boden_lidar))


def eingabe() -> argparse.ArgumentParser:
    e = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    art = e.add_mutually_exclusive_group(required=True)
    art.add_argument('--geradeaus', type=float, metavar='METER',
                     help='ein Punkt genau voraus in dieser Entfernung')
    art.add_argument('--tuer', action='store_true',
                     help='durch eine vermessene Öffnung (Vorpunkt und Auslaufpunkt)')
    e.add_argument('--nummer', type=int, help='Nummer der Öffnung aus der Tabelle')
    e.add_argument('--richtung', type=float, metavar='GRAD',
                   help='Richtung der gemeinten Öffnung; 0 = voraus, positiv = links')
    e.add_argument('--richtung-toleranz', type=float, default=25.0)
    e.add_argument('--quelle', choices=('ki', 'mensch', 'test'), default='test',
                   help='wer gewählt hat; steht später in jeder Meldung des Erkunders')
    e.add_argument('--kennung', default='')
    e.add_argument('--vor', type=float, default=0.70, help='Vorpunkt vor der Türlinie, m')
    e.add_argument('--hinter', type=float, default=0.60,
                   help='Auslaufpunkt hinter der Türlinie, m')
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
    e.add_argument('--karten-rahmen', default='map')
    e.add_argument('--basis-rahmen', default='base_link')
    e.add_argument('--basis-hoehe', type=float, default=0.0)
    return e


def main(argv=None) -> int:
    wahl = eingabe().parse_args(argv)
    import rclpy
    from rclpy.qos import (QoSDurabilityPolicy, QoSProfile, QoSReliabilityPolicy,
                           qos_profile_sensor_data)
    from sensor_msgs.msg import LaserScan
    from std_msgs.msg import String
    from tf2_ros import Buffer, TransformListener

    from ki_verbindung_ros import Fahrzielsender

    rclpy.init()
    knoten = rclpy.create_node('ki_fahrziel')
    stand = {'status': None, 'scans': [], 'rahmen': None, 'sammeln': False}

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
        if wahl.tuer:
            stand['sammeln'] = True
            drehe(wahl.messdauer)
            stand['sammeln'] = False
            montage = tf(wahl.basis_rahmen, stand['rahmen']) if stand['rahmen'] else None
            if not stand['scans'] or montage is None:
                print('Kein Scan oder keine Montage des LiDAR (TF). Nichts gesendet.')
                return 4
            v, q = montage.translation, montage.rotation
            boden_lidar = aus_tf([v.x, v.y, v.z], [q.x, q.y, q.z, q.w], wahl.basis_hoehe)
            gefunden = vermesse(stand['scans'], boden_lidar)
            print(f'{len(stand["scans"])} Scans, {len(gefunden)} Öffnung(en):')
            print(tabelle(gefunden))
            if wahl.nur_messen:
                return 0
            try:
                gewaehlt = waehle_oeffnung(
                    gefunden, nummer=wahl.nummer, richtung_grad=wahl.richtung,
                    toleranz_grad=wahl.richtung_toleranz)
            except ValueError as grund:
                print(f'Nichts gesendet: {grund}.')
                return 2
            bemerkung = (f'Öffnung {gewaehlt.nr}, {gewaehlt.breite_m:.2f} m breit, '
                         f'{gewaehlt.richtung_grad:+.0f}°, {gewaehlt.entfernung_m:.2f} m')
            print(f'Gewählt: {bemerkung}.')

        lage = tf(wahl.karten_rahmen, wahl.basis_rahmen)
        if lage is None:
            drehe(3.0, lambda: tf(wahl.karten_rahmen, wahl.basis_rahmen) is not None)
            lage = tf(wahl.karten_rahmen, wahl.basis_rahmen)
        if lage is None:
            print('Die Lage des Roboters in der Karte fehlt (TF). Nichts gesendet.')
            return 4
        q = lage.rotation
        gier = math.atan2(2.0 * (q.w * q.z + q.x * q.y), 1.0 - 2.0 * (q.y * q.y + q.z * q.z))
        pose = (lage.translation.x, lage.translation.y, gier)

        try:
            if wahl.tuer:
                punkte = durch_die_tuer(gewaehlt.pfosten, pose,
                                        vor_m=wahl.vor, hinter_m=wahl.hinter)
            else:
                punkte = geradeaus(wahl.geradeaus, pose)
            gesamt = pruefe_grenzen(punkte, pose[:2])
        except ValueError as grund:
            print(f'Nichts gesendet: {grund}.')
            return 2

        kennung = wahl.kennung or f'{"tuer" if wahl.tuer else "gerade"}-{int(time.time())}'
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
        # Der Erkunder meldet einen gelungenen Auftrag ohne Flächenziel als „partial“.
        return 0 if (zustand in ('partial', 'success')
                     and meldung().startswith('Etappenfahrt abgeschlossen')) else 1
    finally:
        knoten.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    sys.exit(main())
