#!/usr/bin/env python3
"""Verbindung zwischen Roboter und KI-Rechner für den Lotsen (über ROS 2).

Derselbe Weg wie bei der Objekterkennung: Roboter und KI-Rechner finden sich
über ROS 2 DDS im WLAN (gleiche ``ROS_DOMAIN_ID``). Der Roboter schickt eine
vorbereitete Frage, der Lotsen-Dienst auf dem KI-Rechner fragt dort Ollama und
schickt die Rohantwort zurück.

Es gibt nur diese drei eigenen Themen, alle mit JSON-Text:

    /ki_erkundung/frage_json          Roboter -> KI-Rechner
    /ki_erkundung/antwort_json        KI-Rechner -> Roboter
    /ki_erkundung/lotse_status_json   KI-Rechner: bereit, Modell, Fassung

Fahrbefehle, Dienste oder Aktionen gibt es hier nicht. Kommt keine Antwort,
ist das ein gewöhnliches Ergebnis (``zeitgrenze`` oder
``lotse_nicht_erreichbar``); der Roboter bleibt davon unberührt fahrfähig.
"""
from __future__ import annotations

import json
import sys
import time
import uuid
from pathlib import Path
from typing import Optional, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lotse.botschaft import entpacke_antwort, packe_frage  # noqa: E402
from lotse.frage import Frage  # noqa: E402
from lotse.ki_rechner import Rohantwort  # noqa: E402

THEMA_FRAGE = '/ki_erkundung/frage_json'
THEMA_ANTWORT = '/ki_erkundung/antwort_json'
THEMA_STATUS = '/ki_erkundung/lotse_status_json'


def qos_botschaft():
    """Zuverlässig, kleine Warteschlange: Fragen und Antworten gehen nicht verloren."""
    from rclpy.qos import QoSHistoryPolicy, QoSProfile, QoSReliabilityPolicy
    return QoSProfile(history=QoSHistoryPolicy.KEEP_LAST, depth=2,
                      reliability=QoSReliabilityPolicy.RELIABLE)


def qos_status():
    """Der letzte Status bleibt für später Hinzukommende abrufbar."""
    from rclpy.qos import (QoSDurabilityPolicy, QoSHistoryPolicy, QoSProfile,
                           QoSReliabilityPolicy)
    return QoSProfile(history=QoSHistoryPolicy.KEEP_LAST, depth=1,
                      reliability=QoSReliabilityPolicy.RELIABLE,
                      durability=QoSDurabilityPolicy.TRANSIENT_LOCAL)


class Verbindung:
    """Fragt den Lotsen-Dienst auf dem KI-Rechner. Seite des Roboters."""

    def __init__(self, knoten=None, name: str = 'ki_lotse_frager'):
        import rclpy
        from rclpy.executors import SingleThreadedExecutor
        from std_msgs.msg import String
        self._rclpy, self._String = rclpy, String
        self._eigener_knoten = knoten is None
        self.knoten = knoten or rclpy.create_node(
            name, enable_rosout=False, start_parameter_services=False)
        self._ausfuehrer = SingleThreadedExecutor()
        self._ausfuehrer.add_node(self.knoten)
        self._antworten = {}
        self._status = None
        self._sender = self.knoten.create_publisher(String, THEMA_FRAGE, qos_botschaft())
        self.knoten.create_subscription(String, THEMA_ANTWORT, self._bei_antwort,
                                        qos_botschaft())
        self.knoten.create_subscription(String, THEMA_STATUS, self._bei_status,
                                        qos_status())

    def _bei_antwort(self, nachricht) -> None:
        try:
            frage_id, modell, roh = entpacke_antwort(nachricht.data)
        except ValueError:
            return
        if modell:
            roh.meta = dict(roh.meta, modell_dienst=modell)
        self._antworten[frage_id] = roh

    def _bei_status(self, nachricht) -> None:
        try:
            status = json.loads(nachricht.data)
        except ValueError:
            return
        if isinstance(status, dict):
            self._status = status

    def _drehe(self, bis: float, fertig) -> bool:
        while time.monotonic() < bis:
            if fertig():
                return True
            self._ausfuehrer.spin_once(timeout_sec=0.05)
        return bool(fertig())

    def status(self, warten_s: float = 5.0) -> Optional[dict]:
        """Letzter Status des Lotsen-Dienstes; None, wenn keiner zu hören ist."""
        self._drehe(time.monotonic() + warten_s, lambda: self._status is not None)
        return self._status

    def frage_stellen(self, frage: Frage, bilder: Sequence[bytes],
                      modell: Optional[str] = None, url: Optional[str] = None,
                      zeitgrenze_s: float = 60.0, optionen: Optional[dict] = None,
                      mit_schema: bool = True, denken: Optional[bool] = None,
                      finden_s: float = 5.0) -> Rohantwort:
        """Wie ``lotse.ki_rechner.frage_stellen``, aber über den Lotsen-Dienst.

        ``modell`` und ``url`` bestimmt der Dienst auf dem KI-Rechner; die
        Angaben hier werden nicht übertragen.
        """
        beginn = time.monotonic()

        def verbunden() -> bool:
            # Beide Richtungen müssen stehen, sonst geht die Frage oder die
            # Antwort beim ersten Kontakt verloren.
            return (self._sender.get_subscription_count() > 0
                    and self.knoten.count_publishers(THEMA_ANTWORT) > 0)

        if not verbunden():
            if not self._drehe(beginn + finden_s, verbunden):
                return Rohantwort(None, time.monotonic() - beginn,
                                  'lotse_nicht_erreichbar', denken=denken)
            self._drehe(time.monotonic() + 0.3, lambda: False)   # kurz setzen lassen
        frage_id = uuid.uuid4().hex
        self._sender.publish(self._String(
            data=packe_frage(frage_id, frage, bilder, zeitgrenze_s, optionen, denken)))
        # Der Dienst hält die Zeitgrenze selbst ein; hier etwas Zugabe für den Weg.
        self._drehe(time.monotonic() + zeitgrenze_s + 5.0,
                    lambda: frage_id in self._antworten)
        roh = self._antworten.pop(frage_id, None)
        if roh is None:
            return Rohantwort(None, time.monotonic() - beginn, 'zeitgrenze', denken=denken)
        roh.meta = dict(roh.meta, weg_s=round(time.monotonic() - beginn - roh.dauer_s, 2))
        roh.dauer_s = time.monotonic() - beginn        # Zeit aus Sicht des Roboters
        return roh

    def schliessen(self) -> None:
        self._ausfuehrer.remove_node(self.knoten)
        if self._eigener_knoten:
            self.knoten.destroy_node()
