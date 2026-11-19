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
"""
from __future__ import annotations

import argparse
import json
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ki_verbindung_ros import (THEMA_ANTWORT, THEMA_FRAGE, THEMA_STATUS,  # noqa: E402
                               qos_botschaft, qos_status)
from lotse import SCHEMA_VERSION  # noqa: E402
from lotse.botschaft import entpacke_frage, packe_antwort  # noqa: E402
from lotse.ki_rechner import (STANDARD_URL, Rohantwort, frage_stellen,  # noqa: E402
                              umgebung)


class Dienst:
    """Der Lotsen-Dienst an einem vorhandenen ROS-Knoten."""

    def __init__(self, knoten, modell: str, url: str = STANDARD_URL,
                 kontext: int = 8192, status_alle_s: float = 5.0):
        from std_msgs.msg import String
        self._String = String
        self.knoten, self.modell, self.url, self.kontext = knoten, modell, url, kontext
        self._sperre = threading.Lock()
        self._beschaeftigt = False
        self._beantwortet = 0
        self._abgelehnt = 0
        self._umgebung = umgebung(modell, url)
        self._antwort = knoten.create_publisher(String, THEMA_ANTWORT, qos_botschaft())
        self._status = knoten.create_publisher(String, THEMA_STATUS, qos_status())
        knoten.create_subscription(String, THEMA_FRAGE, self._bei_frage, qos_botschaft())
        knoten.create_timer(status_alle_s, self._melde_status)
        self._melde_status()

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
            return
        with self._sperre:
            if self._beschaeftigt:
                self._antwort.publish(self._String(data=packe_antwort(
                    frage_id, self.modell, Rohantwort(None, 0.0, 'beschaeftigt'))))
                return
            self._beschaeftigt = True

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
    wahl = eingabe.parse_args(argv)

    import rclpy
    rclpy.init()
    knoten = rclpy.create_node('ki_lotse_dienst')
    dienst = Dienst(knoten, wahl.modell, wahl.url, wahl.kontext)
    bekannt = dienst._umgebung
    knoten.get_logger().info(
        f'Lotsen-Dienst gestartet: Modell {wahl.modell}, Ollama '
        f'{bekannt.get("dienst_fassung") or "nicht erreichbar"}'
        + ('' if bekannt.get('modell_kennung') else '; das Modell ist dort NICHT vorhanden'))
    try:
        rclpy.spin(knoten)
    except KeyboardInterrupt:
        pass
    finally:
        knoten.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
