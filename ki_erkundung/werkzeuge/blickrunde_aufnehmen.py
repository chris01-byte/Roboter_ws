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

Mit ``--bis-wartephase SEK`` endet die Aufnahme von selbst: SEK Sekunden,
nachdem der Erkunder nach seinem Rundblick auf ein Fahrziel wartet (Phase
``stage_drive_wait_target`` auf ``/explore/status_json``, gelesen, nie
gesendet). Endet die Mission vorher, endet auch die Aufnahme. Ein Signal
(Strg+C, ``kill -INT``, SIGTERM) beendet sie ebenfalls; geschrieben wird in
jedem Fall, was bis dahin da ist (Befund KI-F9, Lauf 2w). Am Ende steht eine
Zeile ``ERGEBNIS grund=… runde=… aufnahmen=… …`` für die Ablaufhilfe, nach
einigen Sekunden eine Zeile ``BEREIT …`` mit den gemessenen Bildraten.

Die Aufnahme enthält Bilder und Maße der echten Wohnung. Sie wird außerhalb
des Repositorys abgelegt (Vorgabe ``~/.local/share/amadeus/ki_erkundung/
blickrunden``); ein Ziel innerhalb eines Git-Arbeitsverzeichnisses wird
abgelehnt.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from collections import deque
from pathlib import Path
from typing import Deque, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from lotse.blickrunde import scan_als_dict, schreibe_runde  # noqa: E402
from lotse.geometrie import Kamera, aus_tf  # noqa: E402
from ros_ende import Ende, ros_beenden, ros_starten  # noqa: E402

VORGABE_ZIEL = Path.home() / '.local/share/amadeus/ki_erkundung/blickrunden'
# Phasen des Erkunders (explore_node.py, Etappenfahrt); dieselbe Wartephase
# liest fahrziel_senden.py.
RUNDBLICK = 'initial_scan'
WARTEPHASE = 'stage_drive_wait_target'


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


class Rundblickende:
    """Wann die Aufnahme von selbst endet: kurz nach dem Rundblick des Erkunders.

    Reine Logik ohne ROS; gefüttert mit den Statusmeldungen des Erkunders.
    Erst nachdem die Mission mit dem Rundblick begonnen hat (Zustand
    ``running``, Phase ``initial_scan``), zählt die Wartephase als Ende des
    Rundblicks. Die Aufnahme endet ``nachlauf_s`` danach; so kommen noch
    Bilder im Stand und eine frische Lage in der Karte dazu. Endet die Mission
    nach Beginn des Rundblicks ohne Wartephase, endet die Aufnahme sofort. Eine
    Wartephase, vor der kein Rundblick zu sehen war (zum Beispiel der zuletzt
    gehaltene Status einer früheren Mission), zählt nicht.
    """

    def __init__(self, nachlauf_s: float):
        self.nachlauf_s = float(nachlauf_s)
        self.rundblick_seit: Optional[float] = None
        self.wartephase_seit: Optional[float] = None
        self.wartephase_unix: Optional[float] = None
        self.mission_ende: Optional[str] = None
        self.gehoert = False

    def melde(self, status: dict, jetzt: float, unix: Optional[float] = None) -> Optional[str]:
        """Eine Statusmeldung verarbeiten; Rückgabe: ein Satz, wenn sich etwas ändert."""
        self.gehoert = True
        zustand, phase = status.get('state'), status.get('phase')
        if self.rundblick_seit is None:
            if zustand == 'running' and phase == RUNDBLICK:
                self.rundblick_seit = jetzt
                return 'Erkunder: Rundblick läuft.'
            return None
        if self.wartephase_seit is not None or self.mission_ende is not None:
            return None
        if zustand == 'running' and phase == WARTEPHASE:
            self.wartephase_seit = jetzt
            self.wartephase_unix = time.time() if unix is None else unix
            uhr = time.strftime('%H:%M:%S', time.localtime(self.wartephase_unix))
            return (f'Erkunder: Wartephase seit {uhr}, Aufnahme endet in '
                    f'{self.nachlauf_s:.0f} s.')
        if zustand not in ('running', None):
            self.mission_ende = str(zustand)
            return f'Erkunder: Mission beendet ({zustand}) ohne Wartephase; Aufnahme endet.'
        return None

    def grund(self, jetzt: float) -> Optional[str]:
        """``wartephase`` oder ``mission_ende``, sobald die Aufnahme enden soll."""
        if self.mission_ende is not None:
            return 'mission_ende'
        if self.wartephase_seit is not None and jetzt - self.wartephase_seit >= self.nachlauf_s:
            return 'wartephase'
        return None


def ergebnis_zeile(grund: str, ordner: Optional[Path], sammler: 'Sammler',
                   lage: bool, wartephase_unix: Optional[float]) -> str:
    """Eine Zeile zum Weiterverarbeiten (Ablaufhilfe), ohne Koordinaten."""
    gedreht = sammler.gedreht_grad()
    return ('ERGEBNIS'
            f' grund={grund}'
            f' runde={ordner.name if ordner is not None else "-"}'
            f' aufnahmen={len(sammler.aufnahmen)}'
            f' verworfen={sammler.verworfen_ohne_scan}'
            f' gedreht={"-" if gedreht is None else f"{gedreht:.0f}"}'
            f' lage={"ja" if lage else "nein"}'
            f' wartephase_unix={"-" if wartephase_unix is None else f"{wartephase_unix:.1f}"}')


def schreibe(sammler: Sammler, ziel: Path, name: str, kamera: Optional[Kamera],
             boden_kamera, boden_lidar, quelle: dict,
             karte: Optional[dict] = None) -> Optional[Path]:
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
        quelle=quelle, karte=karte)


def nehme_auf(wahl, halt=None, ende: Optional[Ende] = None) -> Optional[Path]:
    """Mit ROS mithören und die Blickrunde schreiben.

    ``halt``: Funktion, die True liefert, wenn die Aufnahme enden soll
    (Tests). ``ende``: Marke aus ``ros_ende`` (Strg+C, ``kill -INT``,
    SIGTERM). Geschrieben wird bei jedem Ende, auch nach einem Fehler beim
    Lesen; danach folgt die Zeile ``ERGEBNIS …``.
    """
    import rclpy
    from rclpy.executors import ExternalShutdownException
    from rclpy.qos import (QoSDurabilityPolicy, QoSHistoryPolicy, QoSProfile,
                           QoSReliabilityPolicy)
    from nav_msgs.msg import Odometry
    from sensor_msgs.msg import CameraInfo, CompressedImage, LaserScan
    from std_msgs.msg import String
    from tf2_ros import Buffer, TransformListener

    def sekunden(stempel) -> float:
        return stempel.sec + stempel.nanosec * 1e-9

    bis_wartephase = getattr(wahl, 'bis_wartephase', None)
    rundblick = Rundblickende(bis_wartephase) if bis_wartephase is not None else None
    eigener_kontext = ros_starten()
    # Reiner Zuhörer: nur Abonnements, keine Parameterdienste, kein /rosout.
    knoten = rclpy.create_node('ki_blickrunde_aufnahme', enable_rosout=False,
                               start_parameter_services=False)
    sensor = QoSProfile(history=QoSHistoryPolicy.KEEP_LAST, depth=5,
                        reliability=QoSReliabilityPolicy.BEST_EFFORT,
                        durability=QoSDurabilityPolicy.VOLATILE)
    letzter = QoSProfile(history=QoSHistoryPolicy.KEEP_LAST, depth=1,
                         reliability=QoSReliabilityPolicy.RELIABLE,
                         durability=QoSDurabilityPolicy.TRANSIENT_LOCAL)
    sammler = Sammler()
    stand = {'kamera': None, 'kamera_rahmen': None, 'lidar_rahmen': None,
             'boden_kamera': None, 'boden_lidar': None, 'karte': None}
    zaehler = {'bild': 0, 'scan': 0, 'info': 0, 'status': 0}
    meldungen: List[str] = []

    def auf_bild(nachricht):
        zaehler['bild'] += 1
        stand['kamera_rahmen'] = stand['kamera_rahmen'] or nachricht.header.frame_id
        sammler.bild(sekunden(nachricht.header.stamp), bytes(nachricht.data))

    def auf_tiefe(nachricht):
        sammler.tiefe(sekunden(nachricht.header.stamp), bytes(nachricht.data))

    def auf_info(nachricht):
        zaehler['info'] += 1
        if nachricht.k[0] > 0:
            stand['kamera'] = Kamera.aus_info({
                'breite': nachricht.width, 'hoehe': nachricht.height,
                'k': list(nachricht.k), 'd': list(nachricht.d)})
            stand['kamera_rahmen'] = nachricht.header.frame_id or stand['kamera_rahmen']

    def auf_scan(nachricht):
        zaehler['scan'] += 1
        stand['lidar_rahmen'] = nachricht.header.frame_id
        t = sekunden(nachricht.header.stamp)
        sammler.scan(t, scan_als_dict(nachricht.angle_min, nachricht.angle_increment,
                                      nachricht.ranges, nachricht.range_min,
                                      nachricht.range_max, t, nachricht.header.frame_id))

    def auf_odom(nachricht):
        q = nachricht.pose.pose.orientation
        sammler.gier(sekunden(nachricht.header.stamp),
                     gier_aus_quaternion(q.x, q.y, q.z, q.w))

    def auf_status(nachricht):
        zaehler['status'] += 1
        if rundblick is None:
            return
        try:
            status = json.loads(nachricht.data)
        except ValueError:
            return
        if isinstance(status, dict):
            satz = rundblick.melde(status, time.monotonic())
            if satz:
                meldungen.append(satz)

    knoten.create_subscription(CompressedImage, wahl.bild_topic, auf_bild, sensor)
    knoten.create_subscription(CompressedImage, wahl.tiefe_topic, auf_tiefe, sensor)
    knoten.create_subscription(CameraInfo, wahl.info_topic, auf_info, sensor)
    knoten.create_subscription(LaserScan, wahl.scan_topic, auf_scan, sensor)
    knoten.create_subscription(Odometry, wahl.odom_topic, auf_odom, sensor)
    knoten.create_subscription(String, getattr(wahl, 'status_topic', '/explore/status_json'),
                               auf_status, letzter)
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

    def lage_in_der_karte() -> Optional[dict]:
        """Wo der Roboter jetzt in der Karte steht (nur TF lesen)."""
        try:
            tf = tf_puffer.lookup_transform(wahl.karten_rahmen, wahl.basis_rahmen,
                                            rclpy.time.Time())
        except Exception:                      # noqa: BLE001 (tf2 wirft mehrere Arten)
            return None
        v, q = tf.transform.translation, tf.transform.rotation
        return {'rahmen': wahl.karten_rahmen,
                'basis_ende': [round(v.x, 4), round(v.y, 4),
                               round(gier_aus_quaternion(q.x, q.y, q.z, q.w), 5)],
                't': round(sekunden(tf.header.stamp), 3)}

    # Kurze Aufnahmen sind Ansichten im Stand (KI-0); zum Drehen ist keine Zeit.
    hinweis = ('Der Roboter bleibt stehen.' if wahl.dauer <= 20.0
               else 'Für eine Blickrunde dreht sich der Roboter einmal langsam ganz herum.')
    print(f'Aufnahme „{wahl.name}“ läuft (höchstens {wahl.dauer:.0f} s). {hinweis} '
          + ('Sie endet von selbst '
             f'{bis_wartephase:.0f} s nach dem Rundblick des Erkunders oder mit Strg+C.'
             if rundblick is not None else 'Ende mit Strg+C.'))
    beginn = time.monotonic()
    letzte_meldung = beginn
    bereit_nach = float(getattr(wahl, 'bereit_nach', 8.0))
    bereit_gemeldet = False
    grund = 'dauer'
    try:
        while True:
            if not rclpy.ok():
                grund = 'ros'
                break
            if time.monotonic() - beginn >= wahl.dauer:
                grund = 'dauer'
                break
            rclpy.spin_once(knoten, timeout_sec=0.1)
            if stand['boden_kamera'] is None:
                stand['boden_kamera'] = montage(stand['kamera_rahmen'])
            if stand['boden_lidar'] is None:
                stand['boden_lidar'] = montage(stand['lidar_rahmen'])
            # Die Lage am Ende der Runde: Mit ihr findet sich eine gewählte
            # Öffnung später in der Karte wieder (ki_tuer_waehlen.py).
            lage = lage_in_der_karte()
            if lage is not None:
                stand['karte'] = lage
            while meldungen:
                print(meldungen.pop(0))
            jetzt = time.monotonic()
            if not bereit_gemeldet and jetzt - beginn >= bereit_nach:
                bereit_gemeldet = True
                dauer = jetzt - beginn
                print(f'BEREIT bilder_hz={zaehler["bild"] / dauer:.1f} '
                      f'scan_hz={zaehler["scan"] / dauer:.1f} '
                      f'kamera_info={"ja" if stand["kamera"] else "nein"} '
                      f'erkunder={"ja" if zaehler["status"] else "nein"}')
            if ende is not None and ende.gesetzt():
                grund = 'signal'
                break
            if halt is not None and halt():
                grund = 'halt'
                break
            if rundblick is not None and rundblick.grund(jetzt):
                grund = rundblick.grund(jetzt)
                break
            if jetzt - letzte_meldung >= 5.0:
                letzte_meldung = jetzt
                gedreht = sammler.gedreht_grad()
                print(f'  {len(sammler.aufnahmen)} Aufnahmen'
                      + ('' if gedreht is None else f', gedreht etwa {gedreht:.0f}°')
                      + ('' if stand['kamera'] else ', noch keine Kameradaten')
                      + ('' if stand['lidar_rahmen'] else ', noch kein Scan'))
    except (KeyboardInterrupt, ExternalShutdownException):
        # Nur ohne die Marke aus ros_ende möglich (eingebettete Nutzung):
        # Strg+C heißt auch dann „Aufnahme beenden und schreiben“.
        grund = 'signal'
    except Exception as fehler:                # noqa: BLE001 (Runde nie verlieren)
        grund = 'fehler'
        print(f'Aufnahme unterbrochen ({type(fehler).__name__}: {fehler}); '
              'geschrieben wird, was bis dahin da ist.', file=sys.stderr)
    finally:
        ros_beenden([knoten], eigener_kontext=eigener_kontext)

    ziel = Path(wahl.ausgabe).expanduser() / f'{wahl.name}_{time.strftime("%Y%m%d_%H%M%S")}'
    ordner = schreibe(sammler, ziel, wahl.name, stand['kamera'],
                      stand['boden_kamera'], stand['boden_lidar'],
                      {'bild_topic': wahl.bild_topic, 'tiefe_topic': wahl.tiefe_topic,
                       'scan_topic': wahl.scan_topic, 'odom_topic': wahl.odom_topic,
                       'kamera_rahmen': stand['kamera_rahmen'],
                       'lidar_rahmen': stand['lidar_rahmen'],
                       'basis_rahmen': wahl.basis_rahmen, 'ende': grund},
                      karte=stand['karte'])
    if ordner is not None:
        gedreht = sammler.gedreht_grad()
        print(f'Blickrunde geschrieben: {ordner}\n'
              f'  {len(sammler.aufnahmen)} Aufnahmen, ohne Scan verworfen: '
              f'{sammler.verworfen_ohne_scan}'
              + ('' if gedreht is None else f', gedreht laut Odometrie {gedreht:.0f}°')
              + ('' if stand['boden_kamera'] is not None and stand['boden_lidar'] is not None
                 else '\n  Montage nicht aus TF gelesen; es gelten die Projektvorgaben.')
              + ('\n  Lage in der Karte am Ende: festgehalten.' if stand['karte']
                 else '\n  Lage in der Karte: nicht gelesen (TF); die Wahl der KI lässt '
                      'sich dann nicht an den Fahrteil übergeben.'))
    print(ergebnis_zeile(grund, ordner, sammler, bool(stand['karte']),
                         rundblick.wartephase_unix if rundblick is not None else None))
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
    leser.add_argument('--karten-rahmen', default='map',
                       help='Rahmen der Karte (für die Lage am Ende der Runde)')
    leser.add_argument('--basis-hoehe', type=float, default=0.09,
                       help='Höhe von base_link über dem Boden in Metern')
    leser.add_argument('--bis-wartephase', type=float, default=None, metavar='SEK',
                       help='von selbst enden, SEK Sekunden nachdem der Erkunder nach '
                            'seinem Rundblick auf ein Fahrziel wartet (nur lesend)')
    leser.add_argument('--status-topic', default='/explore/status_json',
                       help='Status des Erkunders (nur gelesen)')
    leser.add_argument('--bereit-nach', type=float, default=8.0,
                       help='nach so vielen Sekunden die Zeile BEREIT mit den Raten')
    return leser


def main(argv=None) -> int:
    # Ohne Terminal puffert Python die Ausgabe; die Zwischenzeilen stünden
    # dann erst am Ende in der Datei (Befund KI-1).
    for strom in (sys.stdout, sys.stderr):
        if hasattr(strom, 'reconfigure'):
            strom.reconfigure(line_buffering=True)
    wahl = eingabe().parse_args(argv)
    if not wahl.name.replace('_', '').replace('-', '').isalnum():
        print('--name: nur Buchstaben, Ziffern, _ und -', file=sys.stderr)
        return 2
    if im_repository(Path(wahl.ausgabe)):
        print(f'{wahl.ausgabe} liegt in einem Git-Arbeitsverzeichnis. Aufnahmen '
              'der Wohnung gehören nicht ins Repository; bitte ein Ziel außerhalb '
              'wählen.', file=sys.stderr)
        return 2
    if wahl.bis_wartephase is not None and not 0.0 <= wahl.bis_wartephase <= 60.0:
        print('--bis-wartephase: 0 bis 60 s', file=sys.stderr)
        return 2
    # Zuerst die Marke, dann rclpy: Ein Signal setzt nur die Marke (ros_ende).
    ende = Ende().anmelden()
    try:
        return 0 if nehme_auf(wahl, ende=ende) is not None else 1
    finally:
        ende.abmelden()


if __name__ == '__main__':
    raise SystemExit(main())
