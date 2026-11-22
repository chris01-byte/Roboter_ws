#!/usr/bin/env python3
"""Auf dem Roboter, nur lesend: Warum ist der Radsensor (Encoder) gesperrt?

Der Motortreiber liest die Radstellungen etwa alle 50 ms. Liegen zwischen
zwei gültigen Lesungen mehr als 0,18 s, kann er nicht belegen, dass sich die
Räder in der Lücke nicht bewegt haben. Dann versucht er zwei Sekunden lang,
die Lücke zu überbrücken; gelingt das nicht, sperrt er die Radmessung bis
zum nächsten Start („fault_latched“). Ohne Radmessung fährt nichts. Das ist
gewollt (Motorsteuerung, AGENTS §2.7) und wird hier nicht geändert.

Dieses Werkzeug hört einmal auf ``/base_hardware/state_json`` und schreibt
die Angaben der Zeitwache in Klartext: wann und wie groß die erste Lücke war,
wie lange ein Lesepaar dauerte. Es sendet nichts und ändert nichts.

    python3 radsensor_zustand.py

Ausgegeben werden nur Zeiten und Zähler, keine Lage des Roboters.
"""
from __future__ import annotations

import json
import sys
import time
from typing import List, Optional


def _ms(wert) -> str:
    try:
        return f'{1000.0 * float(wert):.1f} ms'
    except (TypeError, ValueError):
        return '–'


def radsensor_zeilen(zustand: Optional[dict]) -> List[str]:
    """Die Angaben der Encoder-Zeitwache als Zeilen (nur Zeiten und Zähler)."""
    if not isinstance(zustand, dict):
        return ['Radsensor: keine Nachricht von base_hardware empfangen.']
    frisch = (zustand.get('encoder_feedback_ok') is True
              and zustand.get('encoder_stale') is False)
    alter = zustand.get('encoder_feedback_age_s')
    zeile = f'Radsensor: Messung frisch: {"ja" if frisch else "nein"}'
    if isinstance(alter, (int, float)):
        zeile += f'; letzte Messung vor {alter:.1f} s'
    zeilen = [zeile + '.']
    wache = zustand.get('encoder_timing_recovery')
    if not isinstance(wache, dict):
        zeilen.append('Zeitwache: keine Angaben (in diesem Start nicht eingeschaltet).')
        return zeilen
    zeilen.append(
        f'Zeitwache: Zustand {wache.get("state")!r}, Grund {wache.get("fault_reason")!r}; '
        f'Überbrückungsversuche {wache.get("timing_recovery_count")} von '
        f'{wache.get("timing_recovery_attempt_limit")}, Grenze für eine Lücke '
        f'{_ms(wache.get("continuity_max_gap_s"))}.')
    for name, schluessel in (('Erste Lücke', 'first_timing_rejection'),
                             ('Letzte Lücke', 'last_timing_rejection')):
        luecke = wache.get(schluessel)
        if isinstance(luecke, dict):
            zeilen.append(
                f'{name}: {luecke.get("reason")!r}, Abstand der Lesungen '
                f'{_ms(luecke.get("sample_gap_s"))}, '
                f'Lesepaar {_ms(luecke.get("pair_duration_s"))}, '
                f'Alter am Leseende {_ms(luecke.get("read_end_age_s"))}.')
        else:
            zeilen.append(f'{name}: keine.')
    zeilen.append(
        f'Lesepaare: {wache.get("complete_pair_count")} gültig, '
        f'{wache.get("rejected_pair_count")} verworfen, Lesefehler '
        f'{wache.get("fc03_pair_error_count")}; längstes Lesepaar '
        f'{_ms(wache.get("maximum_pair_duration_s"))}, längster Versuch '
        f'{_ms(wache.get("maximum_attempted_pair_duration_s"))}.')
    return zeilen


def main(argv=None) -> int:
    for strom in (sys.stdout, sys.stderr):
        if hasattr(strom, 'reconfigure'):
            strom.reconfigure(line_buffering=True)
    warten = 10.0
    import rclpy
    from std_msgs.msg import String

    rclpy.init()
    knoten = rclpy.create_node('ki_radsensor_zustand')
    stand = {'zustand': None}

    def auf_zustand(nachricht):
        try:
            stand['zustand'] = json.loads(nachricht.data)
        except ValueError:
            pass

    knoten.create_subscription(String, '/base_hardware/state_json', auf_zustand, 10)
    try:
        ende = time.monotonic() + warten
        while rclpy.ok() and time.monotonic() < ende and stand['zustand'] is None:
            rclpy.spin_once(knoten, timeout_sec=0.1)
        for zeile in radsensor_zeilen(stand['zustand']):
            print(zeile)
        return 0 if stand['zustand'] is not None else 1
    finally:
        knoten.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    sys.exit(main())
