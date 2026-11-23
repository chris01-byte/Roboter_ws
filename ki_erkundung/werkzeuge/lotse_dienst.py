#!/usr/bin/env python3
"""Lotsen-Dienst für den KI-Rechner: nimmt Fragen des Roboters an und fragt Ollama.

Läuft auf dem KI-Rechner neben den vorhandenen KI-Knoten (``llm_planner``,
``semantic_perception``) und nach demselben Muster: Der Roboter findet den
Dienst über ROS 2 DDS im WLAN; gerechnet wird lokal auf der Grafikkarte.
Der Dienst spricht nur mit Ollama auf diesem Rechner (Vorgabe
``http://localhost:11434``). Bilder gehen an keinen anderen Dienst.

Start (in der ROS-Umgebung des KI-Rechners, gleiche ``ROS_DOMAIN_ID`` wie der
Roboter):

    python3 lotse_dienst.py --modell qwen3.5:9b

Der Dienst beantwortet eine Frage zur Zeit. Trifft währenddessen eine zweite
ein, bekommt sie sofort die Antwort ``beschaeftigt``.

Mit ``--zustand ORDNER`` legt er jede Sekunde seinen Zustand als
``zustand.json`` ab und dazu die Bilder, den Text und die Antwort der
letzten zehn Fragen, jede in einem eigenen Unterordner von ``fragen/``;
ältere werden gelöscht. Daraus liest das Lotsen-Fenster
(``lotse_fenster.py``), was es anzeigt. Der Ordner liegt auf dem
KI-Rechner außerhalb des Repositorys.
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import re
import shutil
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ki_verbindung_ros import (THEMA_ANTWORT, THEMA_FRAGE, THEMA_STATUS,  # noqa: E402
                               qos_botschaft, qos_status)
from lotse import SCHEMA_VERSION  # noqa: E402
from lotse.antwort import pruefe  # noqa: E402
from lotse.botschaft import entpacke_frage, packe_antwort  # noqa: E402
from lotse.ki_rechner import (STANDARD_URL, Rohantwort, frage_stellen,  # noqa: E402
                              umgebung)

# So viele Fragen behält der Dienst mit Bildern für das Fenster.
FRAGEN_BEHALTEN = 10
# Name eines Unterordners in ``fragen/``: Zeit in Millisekunden, Kennung der Frage.
ABLAGE_MUSTER = re.compile(r'[0-9]{1,16}_[A-Za-z0-9]{1,16}')


def ablage_name(zeit_unix: float, frage_id) -> str:
    kennung = ''.join(z for z in str(frage_id or '') if z.isascii() and z.isalnum())[:16]
    return f'{int(round(zeit_unix * 1000))}_{kennung or "frage"}'


class Dienst:
    """Der Lotsen-Dienst an einem vorhandenen ROS-Knoten."""

    def __init__(self, knoten, modell: str, url: str = STANDARD_URL,
                 kontext: int = 8192, status_alle_s: float = 5.0,
                 zustand_ordner=None, zustand_alle_s: float = 1.0):
        from std_msgs.msg import String
        self._String = String
        self.knoten, self.modell, self.url, self.kontext = knoten, modell, url, kontext
        self._sperre = threading.Lock()
        self._beschaeftigt = False
        self._beantwortet = 0
        self._abgelehnt = 0
        self._gestartet = time.time()
        self._verlauf = collections.deque(maxlen=30)       # jüngste Fragen, neueste zuletzt
        self._fragen = collections.deque(maxlen=FRAGEN_BEHALTEN)   # mit Bildern, neueste zuletzt
        self._zustand_ordner = None if zustand_ordner is None else Path(zustand_ordner)
        self._umgebung = umgebung(modell, url)
        self._antwort = knoten.create_publisher(String, THEMA_ANTWORT, qos_botschaft())
        self._status = knoten.create_publisher(String, THEMA_STATUS, qos_status())
        knoten.create_subscription(String, THEMA_FRAGE, self._bei_frage, qos_botschaft())
        knoten.create_timer(status_alle_s, self._melde_status)
        self._melde_status()
        if self._zustand_ordner is not None:
            self._zustand_ordner.mkdir(parents=True, exist_ok=True)
            knoten.create_timer(zustand_alle_s, self.schreibe_zustand)
            self.schreibe_zustand()

    def zustand(self) -> dict:
        """Was das Lotsen-Fenster anzeigt (ohne Bilddaten, ohne Adressen)."""
        try:
            eigener = self.knoten.get_name()
            andere = sorted({name for name in self.knoten.get_node_names()
                             if name != eigener and not name.startswith('_')})
            fragende = int(self.knoten.count_publishers(THEMA_FRAGE))
        except Exception:                      # noqa: BLE001 (beim Beenden des Knotens)
            andere, fragende = [], 0
        with self._sperre:
            verlauf = list(self._verlauf)
            fragen = list(self._fragen)
        return {
            'schema_version': SCHEMA_VERSION, 'pid': os.getpid(),
            'zeit_unix': round(time.time(), 1), 'gestartet_unix': round(self._gestartet, 1),
            'modell': self.modell,
            'bereit': self._umgebung.get('modell_kennung') is not None,
            'beschaeftigt': self._beschaeftigt, 'umgebung': self._umgebung,
            'fragen_beantwortet': self._beantwortet, 'fragen_abgelehnt': self._abgelehnt,
            # Andere ROS-Programme im selben Netz (Roboter) und Programme, die
            # gerade eine Frage stellen können.
            'ros_andere_knoten': len(andere), 'ros_fragende': fragende,
            'verlauf': verlauf, 'fragen': fragen,
            'letzte_frage': fragen[-1] if fragen else None,
        }

    def schreibe_zustand(self) -> None:
        if self._zustand_ordner is None:
            return
        ziel = self._zustand_ordner / 'zustand.json'
        neu = ziel.with_suffix('.json.neu')
        try:
            neu.write_text(json.dumps(self.zustand(), ensure_ascii=False), encoding='utf-8')
            os.replace(neu, ziel)              # nie eine halb geschriebene Datei zeigen
        except OSError as fehler:
            self.knoten.get_logger().warning(f'Zustand nicht geschrieben: {fehler}')

    def _merke(self, eintrag: dict, frage=None, bilder=(), antworttext=None) -> None:
        """Eine Frage im Verlauf vermerken und ihre Bilder für das Fenster ablegen."""
        abgelegt = None
        if frage is not None and self._zustand_ordner is not None:
            wurzel = self._zustand_ordner / 'fragen'
            name = ablage_name(eintrag['zeit_unix'], eintrag.get('frage_id'))
            ordner = wurzel / name
            try:
                ordner.mkdir(parents=True, exist_ok=True)
                for nummer, bild in enumerate(bilder, start=1):
                    (ordner / f'bild_{nummer}.jpg').write_bytes(bytes(bild))
                (ordner / 'frage.txt').write_text(frage.text, encoding='utf-8')
                (ordner / 'antwort.txt').write_text(antworttext or '', encoding='utf-8')
                eintrag = dict(eintrag, ablage=name)
                abgelegt = dict(eintrag, bilder=len(bilder), antworttext=antworttext,
                                angeboten=list(frage.angeboten))
            except OSError as fehler:
                self.knoten.get_logger().warning(f'Frage nicht abgelegt: {fehler}')
            self._raeume_auf(wurzel)
        with self._sperre:
            self._verlauf.append(eintrag)
            if abgelegt is not None:
                self._fragen.append(abgelegt)
        self.schreibe_zustand()

    def _raeume_auf(self, wurzel: Path) -> None:
        """Nur die jüngsten FRAGEN_BEHALTEN Ablagen behalten (auch aus früheren Läufen)."""
        try:
            ablagen = [p for p in wurzel.iterdir()
                       if p.is_dir() and ABLAGE_MUSTER.fullmatch(p.name)]
        except OSError:
            return
        ablagen.sort(key=lambda p: int(p.name.split('_')[0]))
        for alt in ablagen[:-FRAGEN_BEHALTEN]:
            shutil.rmtree(alt, ignore_errors=True)

    def _melde_status(self) -> None:
        if self._umgebung.get('modell_kennung') is None and not self._beschaeftigt:
            self._umgebung = umgebung(self.modell, self.url, zeitgrenze_s=2.0)
        self._status.publish(self._String(data=json.dumps({
            'schema_version': SCHEMA_VERSION,
            'bereit': self._umgebung.get('modell_kennung') is not None,
            'beschaeftigt': self._beschaeftigt, 'modell': self.modell,
            'umgebung': self._umgebung, 'fragen_beantwortet': self._beantwortet,
            'fragen_abgelehnt': self._abgelehnt, 'zeit_unix': round(time.time(), 1),
        }, ensure_ascii=False)))

    def _bei_frage(self, nachricht) -> None:
        try:
            frage_id, frage, bilder, grenze, optionen, denken = entpacke_frage(nachricht.data)
        except ValueError as fehler:
            self._abgelehnt += 1
            self.knoten.get_logger().warning(f'Frage verworfen: {fehler}')
            self._merke({'zeit_unix': round(time.time(), 1), 'frage_id': None,
                         'ergebnis': 'unbrauchbare_frage', 'grund': str(fehler)})
            return
        with self._sperre:
            if self._beschaeftigt:
                self._antwort.publish(self._String(data=packe_antwort(
                    frage_id, self.modell, Rohantwort(None, 0.0, 'beschaeftigt'))))
                return
            self._beschaeftigt = True
        empfangen = time.time()

        def arbeite():
            try:
                einstellungen = dict({'num_ctx': self.kontext}, **optionen)
                roh = frage_stellen(frage, bilder, self.modell, url=self.url,
                                    zeitgrenze_s=grenze, optionen=einstellungen,
                                    denken=denken)
            except Exception as fehler:        # noqa: BLE001 (Dienst soll weiterlaufen)
                self.knoten.get_logger().error(f'Frage {frage_id}: {fehler!r}')
                roh = Rohantwort(None, 0.0, 'dienstfehler')
            finally:
                with self._sperre:
                    self._beschaeftigt = False
            self._beantwortet += 1
            self._antwort.publish(self._String(
                data=packe_antwort(frage_id, self.modell, roh)))
            self.knoten.get_logger().info(
                f'Frage {frage_id[:8]}: {len(bilder)} Bilder, '
                f'{"Antwort" if roh.fehler is None else roh.fehler}, {roh.dauer_s:.1f} s')
            # Nur zur Anzeige: Die maßgebliche Prüfung macht der Roboter.
            eintrag = {'zeit_unix': round(empfangen, 1), 'frage_id': frage_id[:8],
                       'bilder': len(bilder), 'dauer_s': round(roh.dauer_s, 1),
                       'denken': denken,
                       'ergebnis': 'antwort' if roh.fehler is None else roh.fehler}
            if roh.fehler is None:
                geprueft = pruefe(roh.text, frage.angeboten)
                eintrag.update(gueltig=geprueft.gueltig, wahl=geprueft.wahl,
                               raum=geprueft.raum, begruendung=geprueft.begruendung,
                               arten={str(k): v for k, v in sorted(geprueft.arten.items())},
                               fehler=list(geprueft.fehler))
            self._merke(eintrag, frage, bilder, roh.text)

        threading.Thread(target=arbeite, daemon=True).start()


def main(argv=None) -> int:
    eingabe = argparse.ArgumentParser(
        description='Lotsen-Dienst für den KI-Rechner (fragt Ollama lokal).')
    eingabe.add_argument('--modell', required=True,
                         help='Name des Bild-Sprach-Modells in Ollama, z. B. qwen3.5:9b')
    eingabe.add_argument('--url', default=STANDARD_URL,
                         help='Adresse von Ollama auf diesem Rechner')
    eingabe.add_argument('--kontext', type=int, default=8192,
                         help='Kontextlänge des Modells (num_ctx)')
    eingabe.add_argument('--zustand', metavar='ORDNER',
                         help='Zustand und letzte Frage für das Lotsen-Fenster hier ablegen '
                              '(auf dem KI-Rechner, außerhalb des Repositorys)')
    wahl = eingabe.parse_args(argv)

    import rclpy
    from rclpy.executors import ExternalShutdownException
    rclpy.init()
    knoten = rclpy.create_node('ki_lotse_dienst')
    dienst = Dienst(knoten, wahl.modell, wahl.url, wahl.kontext,
                    zustand_ordner=wahl.zustand)
    bekannt = dienst._umgebung
    knoten.get_logger().info(
        f'Lotsen-Dienst gestartet: Modell {wahl.modell}, Ollama '
        f'{bekannt.get("dienst_fassung") or "nicht erreichbar"}'
        + ('' if bekannt.get('modell_kennung') else '; das Modell ist dort NICHT vorhanden'))
    try:
        rclpy.spin(knoten)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass                    # Strg+C, je nach ROS-Fassung so oder so
    finally:
        knoten.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
