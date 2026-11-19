#!/usr/bin/env python3
"""Eine Blickrunde am Roboter aufnehmen (Stufe KI-0). Nur lesend.

Das Werkzeug hört während einer Drehung des Roboters mit und speichert
zusammengehörige Kamerabilder, Tiefenbilder und LiDAR-Scans als Blickrunde
(Format: ki_erkundung/lotse/blickrunde.py). Es legt nur Abonnements an:
keine Fahrbefehle, keine Dienstaufrufe, keine Parameteränderungen. Wie der
Roboter gedreht wird (Joystick oder von Hand), ist dem Werkzeug gleich; der
Drehwinkel wird später aus den Scans bestimmt.

Voraussetzung auf dem Jetson: Kamera mit Relay (``oak.launch.py``) und LiDAR
laufen. Gelesen werden in der Vorgabe:

    /oak/semantic/rgb/compressed    JPEG, 2 Hz (Relay)
    /oak/semantic/depth/compressed  16-Bit-PNG, 2 Hz (Relay), optional
    /oak/semantic/camera_info
    /scan                           LiDAR
    /odom                           optional, nur als Startwert

Aufruf (Beispiel):
    python3 blickrunde_aufnehmen.py --name labor_mitte --dauer 120
    # Roboter einmal langsam ganz herumdrehen, dann Strg+C

Die Aufnahme enthält Bilder und Maße der echten Wohnung. Sie wird außerhalb
des Repositorys abgelegt (Vorgabe ``~/.local/share/amadeus/ki_erkundung/
blickrunden``); ein Ziel innerhalb eines Git-Arbeitsverzeichnisses wird
abgelehnt.
"""
from __future__ import annotations

import argparse
import math
import sys
import time
from collections import deque
from pathlib import Path
from typing import Deque, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lotse.blickrunde import scan_als_dict, schreibe_runde  # noqa: E402
from lotse.geometrie import Kamera, aus_tf  # noqa: E402

VORGABE_ZIEL = Path.home() / '.local/share/amadeus/ki_erkundung/blickrunden'


def im_repository(pfad: Path) -> bool:
    """Liegt ``pfad`` in einem Git-Arbeitsverzeichnis?"""
    pfad = Path(pfad).expanduser().resolve()
    return any((eltern / '.git').exists() for eltern in [pfad, *pfad.parents])


def gier_aus_quaternion(x: float, y: float, z: float, w: float) -> float:
    return math.atan2(2.0 * (w * z + x * y), 1.0 - 2.0 * (y * y + z * z))


class Sammler:
    """Ordnet Bilder, Tiefenbilder, Scans und Odometrie nach ihrer Zeit zu.

    Reine Logik ohne ROS. Ein Bild wird zur Aufnahme, sobald ein Scan mit
    höchstens ``max_versatz_scan_s`` Abstand vorliegt. Bilder ohne passenden
    Scan werden verworfen und gezählt, weil ohne Scan weder Drehwinkel noch
    Vorschläge entstehen.
    """

    def __init__(self, max_versatz_scan_s: float = 0.15,
                 max_versatz_tiefe_s: float = 0.25, min_abstand_s: float = 0.35,
                 puffer_s: float = 3.0):
        self.max_versatz_scan_s = max_versatz_scan_s
        self.max_versatz_tiefe_s = max_versatz_tiefe_s
        self.min_abstand_s = min_abstand_s
        self.puffer_s = puffer_s
        self._scans: Deque[Tuple[float, dict]] = deque()
        self._tiefen: Deque[Tuple[float, bytes]] = deque()
        self._gier: Deque[Tuple[float, float]] = deque()
        self._wartend: Deque[Tuple[float, bytes]] = deque()
        self.aufnahmen: List[dict] = []
        self.verworfen_ohne_scan = 0
        self.uebersprungen_zu_dicht = 0

    def _kuerzen(self, puffer: Deque, jetzt: float) -> None:
        while puffer and puffer[0][0] < jetzt - self.puffer_s:
            puffer.popleft()

    def scan(self, t: float, scan: dict) -> None:
        self._scans.append((t, scan))
        self._kuerzen(self._scans, t)
        self._zuordnen(bis=t - self.max_versatz_scan_s)

    def tiefe(self, t: float, daten: bytes) -> None:
        self._tiefen.append((t, daten))
        self._kuerzen(self._tiefen, t)

    def gier(self, t: float, gier_rad: float) -> None:
        self._gier.append((t, gier_rad))
        self._kuerzen(self._gier, t)

    def bild(self, t: float, daten: bytes) -> None:
        letzte = self._wartend[-1][0] if self._wartend else (
            self.aufnahmen[-1]['t'] if self.aufnahmen else None)
        if letzte is not None and t - letzte < self.min_abstand_s:
            self.uebersprungen_zu_dicht += 1
            return
        self._wartend.append((t, daten))

    @staticmethod
    def _naechster(puffer: Deque, t: float, grenze: float):
        if not puffer:
            return None
        zeit, wert = min(puffer, key=lambda eintrag: abs(eintrag[0] - t))
        return wert if abs(zeit - t) <= grenze else None

    def _zuordnen(self, bis: float) -> None:
        """Wartende Bilder abschließen, für die kein näherer Scan mehr kommt."""
        while self._wartend and self._wartend[0][0] <= bis:
            t, daten = self._wartend.popleft()
            scan = self._naechster(self._scans, t, self.max_versatz_scan_s)
            if scan is None:
                self.verworfen_ohne_scan += 1
                continue
            self.aufnahmen.append({
                't': t, 'bild': daten, 'scan': scan,
                'tiefe': self._naechster(self._tiefen, t, self.max_versatz_tiefe_s),
                'gier_odom': self._naechster(self._gier, t, 0.2),
            })

    def abschliessen(self) -> List[dict]:
        self._zuordnen(bis=float('inf'))
        return self.aufnahmen

    def gedreht_grad(self) -> Optional[float]:
        """Bisher gedrehter Winkel laut Odometrie (None ohne Odometrie)."""
        werte = [a['gier_odom'] for a in self.aufnahmen if a['gier_odom'] is not None]
        if len(werte) < 2:
            return None
        summe = 0.0
        for davor, danach in zip(werte, werte[1:]):
            summe += (danach - davor + math.pi) % (2 * math.pi) - math.pi
        return math.degrees(summe)


def schreibe(sammler: Sammler, ziel: Path, name: str, kamera: Optional[Kamera],
             boden_kamera, boden_lidar, quelle: dict) -> Optional[Path]:
    """Die gesammelten Aufnahmen als Blickrunde schreiben."""
    aufnahmen = sammler.abschliessen()
    if not aufnahmen:
        print('Keine vollständige Aufnahme (Bild mit Scan) erhalten; nichts geschrieben.',
              file=sys.stderr)
        return None
    if kamera is None:
        print('Keine Kameradaten (camera_info) erhalten; nichts geschrieben.',
              file=sys.stderr)
        return None
    alle_gier = [a['gier_odom'] for a in aufnahmen]
    quelle = dict(quelle, verworfen_ohne_scan=sammler.verworfen_ohne_scan,
                  uebersprungen_zu_dicht=sammler.uebersprungen_zu_dicht)
    return schreibe_runde(
        ziel, name, kamera,
        [a['bild'] for a in aufnahmen], [a['scan'] for a in aufnahmen],
        [a['t'] for a in aufnahmen],
        tiefen=[a['tiefe'] for a in aufnahmen],
        gier_odom=alle_gier if all(g is not None for g in alle_gier) else None,
        boden_kamera=boden_kamera, boden_lidar=boden_lidar,
        montage_quelle='tf' if boden_kamera is not None and boden_lidar is not None
        else 'vorgabe',
        quelle=quelle)


def nehme_auf(wahl, halt=None) -> Optional[Path]:
    """Mit ROS mithören und die Blickrunde schreiben. ``halt``: Funktion, die
    True liefert, wenn die Aufnahme enden soll (für Tests)."""
    import rclpy
    from rclpy.qos import (QoSDurabilityPolicy, QoSHistoryPolicy, QoSProfile,
                           QoSReliabilityPolicy)
    from nav_msgs.msg import Odometry
    from sensor_msgs.msg import CameraInfo, CompressedImage, LaserScan
    from tf2_ros import Buffer, TransformListener

    def sekunden(stempel) -> float:
        return stempel.sec + stempel.nanosec * 1e-9

    eigener_kontext = not rclpy.ok()
    if eigener_kontext:
        rclpy.init()
    # Reiner Zuhörer: nur Abonnements, keine Parameterdienste, kein /rosout.
    knoten = rclpy.create_node('ki_blickrunde_aufnahme', enable_rosout=False,
                               start_parameter_services=False)
    sensor = QoSProfile(history=QoSHistoryPolicy.KEEP_LAST, depth=5,
                        reliability=QoSReliabilityPolicy.BEST_EFFORT,
                        durability=QoSDurabilityPolicy.VOLATILE)
    sammler = Sammler()
    stand = {'kamera': None, 'kamera_rahmen': None, 'lidar_rahmen': None,
             'boden_kamera': None, 'boden_lidar': None}

    def auf_bild(nachricht):
        stand['kamera_rahmen'] = stand['kamera_rahmen'] or nachricht.header.frame_id
        sammler.bild(sekunden(nachricht.header.stamp), bytes(nachricht.data))

    def auf_tiefe(nachricht):
        sammler.tiefe(sekunden(nachricht.header.stamp), bytes(nachricht.data))

    def auf_info(nachricht):
        if nachricht.k[0] > 0:
            stand['kamera'] = Kamera.aus_info({
                'breite': nachricht.width, 'hoehe': nachricht.height,
                'k': list(nachricht.k), 'd': list(nachricht.d)})
            stand['kamera_rahmen'] = nachricht.header.frame_id or stand['kamera_rahmen']

    def auf_scan(nachricht):
        stand['lidar_rahmen'] = nachricht.header.frame_id
        t = sekunden(nachricht.header.stamp)
        sammler.scan(t, scan_als_dict(nachricht.angle_min, nachricht.angle_increment,
                                      nachricht.ranges, nachricht.range_min,
                                      nachricht.range_max, t, nachricht.header.frame_id))

    def auf_odom(nachricht):
        q = nachricht.pose.pose.orientation
        sammler.gier(sekunden(nachricht.header.stamp),
                     gier_aus_quaternion(q.x, q.y, q.z, q.w))

    knoten.create_subscription(CompressedImage, wahl.bild_topic, auf_bild, sensor)
    knoten.create_subscription(CompressedImage, wahl.tiefe_topic, auf_tiefe, sensor)
    knoten.create_subscription(CameraInfo, wahl.info_topic, auf_info, sensor)
    knoten.create_subscription(LaserScan, wahl.scan_topic, auf_scan, sensor)
    knoten.create_subscription(Odometry, wahl.odom_topic, auf_odom, sensor)
    tf_puffer = Buffer()
    TransformListener(tf_puffer, knoten)

    def montage(rahmen: Optional[str]):
        if not rahmen:
            return None
        try:
            tf = tf_puffer.lookup_transform(wahl.basis_rahmen, rahmen, rclpy.time.Time())
        except Exception:                      # noqa: BLE001 (tf2 wirft mehrere Arten)
            return None
        v, q = tf.transform.translation, tf.transform.rotation
        return aus_tf([v.x, v.y, v.z], [q.x, q.y, q.z, q.w], wahl.basis_hoehe)

    print(f'Aufnahme „{wahl.name}“ läuft (höchstens {wahl.dauer:.0f} s). '
          'Roboter jetzt einmal langsam ganz herumdrehen; Ende mit Strg+C.')
    beginn = time.monotonic()
    letzte_meldung = beginn
    try:
        while rclpy.ok() and time.monotonic() - beginn < wahl.dauer:
            rclpy.spin_once(knoten, timeout_sec=0.1)
            if stand['boden_kamera'] is None:
                stand['boden_kamera'] = montage(stand['kamera_rahmen'])
            if stand['boden_lidar'] is None:
                stand['boden_lidar'] = montage(stand['lidar_rahmen'])
            if halt is not None and halt():
                break
            if time.monotonic() - letzte_meldung >= 5.0:
                letzte_meldung = time.monotonic()
                gedreht = sammler.gedreht_grad()
                print(f'  {len(sammler.aufnahmen)} Aufnahmen'
                      + ('' if gedreht is None else f', gedreht etwa {gedreht:.0f}°')
                      + ('' if stand['kamera'] else ', noch keine Kameradaten')
                      + ('' if stand['lidar_rahmen'] else ', noch kein Scan'))
    except KeyboardInterrupt:
        pass
    finally:
        knoten.destroy_node()
        if eigener_kontext and rclpy.ok():
            rclpy.shutdown()

    ziel = Path(wahl.ausgabe).expanduser() / f'{wahl.name}_{time.strftime("%Y%m%d_%H%M%S")}'
    ordner = schreibe(sammler, ziel, wahl.name, stand['kamera'],
                      stand['boden_kamera'], stand['boden_lidar'],
                      {'bild_topic': wahl.bild_topic, 'tiefe_topic': wahl.tiefe_topic,
                       'scan_topic': wahl.scan_topic, 'odom_topic': wahl.odom_topic,
                       'kamera_rahmen': stand['kamera_rahmen'],
                       'lidar_rahmen': stand['lidar_rahmen'],
                       'basis_rahmen': wahl.basis_rahmen})
    if ordner is not None:
        gedreht = sammler.gedreht_grad()
        print(f'Blickrunde geschrieben: {ordner}\n'
              f'  {len(sammler.aufnahmen)} Aufnahmen, ohne Scan verworfen: '
              f'{sammler.verworfen_ohne_scan}'
              + ('' if gedreht is None else f', gedreht laut Odometrie {gedreht:.0f}°')
              + ('' if stand['boden_kamera'] is not None and stand['boden_lidar'] is not None
                 else '\n  Montage nicht aus TF gelesen; es gelten die Projektvorgaben.'))
    return ordner


def eingabe() -> argparse.ArgumentParser:
    leser = argparse.ArgumentParser(
        description='Eine Blickrunde am Roboter aufnehmen (nur lesend).')
    leser.add_argument('--name', required=True,
                       help='Bezeichnung des Standpunkts, zum Beispiel labor_mitte')
    leser.add_argument('--ausgabe', default=str(VORGABE_ZIEL),
                       help='Zielordner außerhalb des Repositorys')
    leser.add_argument('--dauer', type=float, default=120.0,
                       help='höchste Aufnahmedauer in Sekunden')
    leser.add_argument('--bild-topic', default='/oak/semantic/rgb/compressed')
    leser.add_argument('--tiefe-topic', default='/oak/semantic/depth/compressed')
    leser.add_argument('--info-topic', default='/oak/semantic/camera_info')
    leser.add_argument('--scan-topic', default='/scan')
    leser.add_argument('--odom-topic', default='/odom')
    leser.add_argument('--basis-rahmen', default='base_link')
    leser.add_argument('--basis-hoehe', type=float, default=0.09,
                       help='Höhe von base_link über dem Boden in Metern')
    return leser


def main(argv=None) -> int:
    wahl = eingabe().parse_args(argv)
    if not wahl.name.replace('_', '').replace('-', '').isalnum():
        print('--name: nur Buchstaben, Ziffern, _ und -', file=sys.stderr)
        return 2
    if im_repository(Path(wahl.ausgabe)):
        print(f'{wahl.ausgabe} liegt in einem Git-Arbeitsverzeichnis. Aufnahmen '
              'der Wohnung gehören nicht ins Repository; bitte ein Ziel außerhalb '
              'wählen.', file=sys.stderr)
        return 2
    return 0 if nehme_auf(wahl) is not None else 1


if __name__ == '__main__':
    raise SystemExit(main())
