#!/usr/bin/env python3
"""Sauberes Ende der ROS-Werkzeuge dieser Linie (Strg+C, ``kill -INT``, SIGTERM).

Befund KI-F9, Lauf 2w (Bewertung nach KI-F9, §5): Unter ROS 2 Humble ruft
der Signal-Handler von rclpy Pythons eigenen Handler auf. Der wirft einen
``KeyboardInterrupt`` an beliebiger Stelle, auch mitten im Umwandeln einer
gerade empfangenen Nachricht; dort wird daraus ein ``RuntimeError`` („Unable
to convert call argument …“). Ein Werkzeug, das nur ``KeyboardInterrupt``
abfängt, bricht dann ab, ohne zu schreiben. Seltener beendet rclpy den
Kontext in einem eigenen Faden, während gelesen wird („context is not
valid“).

Abhilfe wie im Erkunder der Hauptlinie (``main`` in ``explore_node.py``, am
Roboter seit September im Einsatz): Ein Signal setzt nur eine Marke, und
rclpy läuft ohne eigenen Handler (``SignalHandlerOptions.NO``). Die Schleifen
der Werkzeuge fragen die Marke ab (``spin_once`` mit kurzer Wartezeit) und
enden geordnet; geschrieben wird danach wie bei jedem anderen Ende.

    ende = Ende().anmelden()            # zuerst, vor rclpy
    eigener = ros_starten()
    try:
        while not ende.gesetzt() and rclpy.ok():
            rclpy.spin_once(knoten, timeout_sec=0.1)
    finally:
        ros_beenden([knoten], eigener_kontext=eigener)
        ende.abmelden()

Hier wird nur die Signalbehandlung des eigenen Prozesses geändert; an andere
Prozesse wird nichts gesendet.
"""
from __future__ import annotations

import signal
import threading
from typing import Iterable, Optional

ENDE_SIGNALE = (signal.SIGINT, signal.SIGTERM)


class Ende:
    """Marke für ein angefordertes Ende. Ein Signal setzt nur sie."""

    def __init__(self) -> None:
        self.marke = threading.Event()
        self.signal: Optional[str] = None
        self._vorher: dict = {}

    def anmelden(self, signale: Iterable[int] = ENDE_SIGNALE) -> 'Ende':
        """Die Signale auf die Marke legen; die vorigen Handler werden gemerkt.

        Nur aus dem Hauptfaden aufrufen (Vorgabe von Python).
        """
        for nummer in signale:
            if nummer not in self._vorher:
                self._vorher[nummer] = signal.getsignal(nummer)
            signal.signal(nummer, self._bei_signal)
        return self

    def _bei_signal(self, nummer, _rahmen) -> None:
        if self.signal is None:
            try:
                self.signal = signal.Signals(nummer).name
            except ValueError:
                self.signal = str(nummer)
        self.marke.set()

    def gesetzt(self) -> bool:
        return self.marke.is_set()

    def abmelden(self) -> None:
        """Die vorigen Handler wieder setzen (ohne Python-Handler: Vorgabe des Systems)."""
        for nummer, vorher in self._vorher.items():
            signal.signal(nummer, vorher if vorher is not None else signal.SIG_DFL)
        self._vorher.clear()

    def __enter__(self) -> 'Ende':
        return self.anmelden()

    def __exit__(self, *_ausnahme) -> None:
        self.abmelden()


def ros_starten(args=None) -> bool:
    """rclpy ohne eigene Signal-Handler starten.

    Rückgabe: True, wenn der Kontext hier neu angelegt wurde (dann beendet ihn
    ``ros_beenden``); False, wenn schon einer lief (Tests, eingebettete Nutzung).
    """
    import rclpy
    from rclpy.signals import SignalHandlerOptions

    if rclpy.ok():
        return False
    rclpy.init(args=args, signal_handler_options=SignalHandlerOptions.NO)
    return True


def ros_beenden(knoten=(), ausfuehrer=None, eigener_kontext: bool = True) -> None:
    """Ausführer, dann Knoten, dann Kontext beenden; jede Stufe für sich.

    Ein Fehler in einer Stufe hält die folgenden nicht auf: Am Ende soll das
    Werkzeug immer noch schreiben und sauber zurückkehren können.
    """
    import rclpy

    if ausfuehrer is not None:
        try:
            ausfuehrer.shutdown(timeout_sec=5.0)
        except Exception:                       # noqa: BLE001 (Ende in jedem Fall)
            pass
    for einzel in knoten:
        if einzel is None:
            continue
        try:
            einzel.destroy_node()
        except Exception:                       # noqa: BLE001
            pass
    if eigener_kontext:
        try:
            if rclpy.ok():
                rclpy.shutdown()
        except Exception:                       # noqa: BLE001
            pass
