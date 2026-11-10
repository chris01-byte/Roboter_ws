#!/usr/bin/env python3
"""Rein lesendes Fahrtprotokoll für eine Laborfahrt im Selbstheilungsbetrieb.

Konzept: docs/wohnungserkundung/KONZEPT_SELBSTHEILUNG.md §11 (Abnahmestufe 1).

Vor dem Missionsstart starten. Das Werkzeug abonniert nur Status- und
Messtopics, publiziert nichts und ruft keinen Dienst auf. Es endet von selbst
einige Sekunden nach dem Missionsende (oder nach --max-s / Strg-C) und
schreibt eine JSON-Zusammenfassung:

  - Zustandsfolge des Selbstheilungsbetriebs (Ziele, Heilungen, Warten,
    Umsehen, Spurrückfahrt, Endzustand und Grund),
  - HWT-Erholungszustände, Not-Aus-Wechsel, Tempolimit-Wechsel,
  - Fahrbefehle auf /cmd_vel (Maximum), gefahrene Strecke laut /odom,
  - Lücken im VL53-Status (länger als 0,8 s),
  - Abdeckungskurve: freie, belegte und bekannte Kartenfläche alle 30 s
    während der Fahrt und die Zeit, bis 85/90/95 % der freien Endfläche
    erreicht waren (Fahrplan MASTERPLAN §9, 09.11.2026),
  - die automatisch prüfbaren Kriterien der Abnahmestufe 1,
  - mit --stellprobe-m: Stellprobe (MASTERPLAN §9, Regel 6). Gemessen wird
    die Entfernung vom Standort beim Missionsstart; das Protokoll endet,
    sobald sie erreicht ist (plus Nachlauf) oder das Fenster abgelaufen ist.

Kontaktfreiheit, Eingriffe und der Nav2-Zustand nach der Fahrt sind
Beobachtungen bzw. eigene Prüfungen und stehen als „manuell“ im Ergebnis.
"""

import argparse
import json
import math
import os
import sys
import time


TERMINAL = ('success', 'partial', 'blocked', 'failed', 'canceled')
SAUBERES_ENDE = ('exploration_complete', 'usable_partial', 'blocked_help_required')
VL53_LUECKE_S = 0.8
ABDECKUNG_TAKT_S = 30.0
ABDECKUNG_ANTEILE = (0.85, 0.90, 0.95)
MANUELL = (
    'kein Kontakt mit Hindernissen oder Wänden (Beobachtung Christopher)',
    'kein Eingriff: kein Stopp, kein Not-Aus, kein Umsetzen (Beobachtung Christopher)',
    'Nav2 nach der Fahrt in einem klaren Zustand (ros2 lifecycle get)',
    'kein Absturz: kein "process has died" im launch.log',
)


class LaufProtokoll:
    """Sammelt Ereignisse einer Fahrt; ohne ROS testbar."""

    def __init__(self, start):
        self.start = start
        self.ereignisse = []
        self.self_healing = None
        self.explore_status = None
        self.gestartet_um = None
        self.beendet_um = None
        self._sh_schluessel = None
        self._mission_zustand = None
        self.mission_letzter = None
        self.estop = None
        self.estop_aktiv_waehrend_fahrt = False
        self.tempolimit = None
        self.cmd = dict(nachrichten=0, ungleich_null=0, max_v=0.0, max_w=0.0)
        self.odom_letzte = None
        self.strecke_m = 0.0
        self.vl53_letzte = None
        self.vl53_luecken = 0
        self.vl53_max_luecke_s = 0.0
        self.hwt_zustand = None
        self.abdeckung = []
        self._abdeckung_letzte = None
        # Stellprobe: Entfernung vom Standort beim Missionsstart.
        self.stellprobe_start = None
        self.stellprobe_max_m = 0.0
        self.stellprobe_weg = None       # dict beim ersten Erreichen der Schwelle
        self.stellprobe_weg_um = None

    def _t(self, t):
        return round(t - self.start, 2)

    def _ereignis(self, t, art, **daten):
        self.ereignisse.append(dict(t_s=self._t(t), art=art, **daten))

    def faehrt(self):
        return self.gestartet_um is not None and self.beendet_um is None

    # --- Eingänge -------------------------------------------------------
    def explore(self, status, t):
        self.explore_status = status
        hwt = status.get('hwt_recovery_state')
        if hwt is not None and hwt != self.hwt_zustand:
            self._ereignis(t, 'hwt', zustand=hwt, vorher=self.hwt_zustand)
            self.hwt_zustand = hwt
        sh = status.get('self_healing')
        if not isinstance(sh, dict):
            return
        self.self_healing = sh
        zustand = sh.get('state')
        schluessel = tuple(sh.get(k) for k in (
            'state', 'reason', 'waiting_for', 'goals_reached', 'heals',
            'deferred_goals', 'track_backs', 'look_arounds'))
        if schluessel != self._sh_schluessel:
            self._sh_schluessel = schluessel
            self._ereignis(t, 'selbstheilung', **{k: sh.get(k) for k in (
                'state', 'outcome', 'reason', 'waiting_for', 'goals_reached', 'heals',
                'deferred_goals', 'track_backs', 'look_arounds')})
        if zustand in ('running', 'waiting', 'checking_completion') and self.gestartet_um is None:
            self.gestartet_um = t
        if zustand in TERMINAL and self.gestartet_um is not None and self.beendet_um is None:
            self.beendet_um = t

    def mission(self, status, t):
        self.mission_letzter = status
        zustand = status.get('state')
        if zustand != self._mission_zustand:
            self._ereignis(t, 'mission', zustand=zustand)
            self._mission_zustand = zustand

    def estop_wert(self, aktiv, t):
        if aktiv != self.estop:
            self._ereignis(t, 'not_aus', aktiv=aktiv)
            self.estop = aktiv
        if aktiv and self.faehrt():
            self.estop_aktiv_waehrend_fahrt = True

    def tempo(self, limit, t):
        limit = round(float(limit), 3)
        if limit != self.tempolimit:
            self._ereignis(t, 'tempolimit', mps=limit)
            self.tempolimit = limit

    def cmd_vel(self, v, w):
        self.cmd['nachrichten'] += 1
        if v != 0.0 or w != 0.0:
            self.cmd['ungleich_null'] += 1
        self.cmd['max_v'] = max(self.cmd['max_v'], abs(v))
        self.cmd['max_w'] = max(self.cmd['max_w'], abs(w))

    def odom(self, x, y):
        if not (math.isfinite(x) and math.isfinite(y)):
            return
        if self.odom_letzte is not None:
            schritt = math.dist(self.odom_letzte, (x, y))
            if schritt < 0.5:          # Sprünge (Neustart, Reset) nicht addieren
                self.strecke_m += schritt
        self.odom_letzte = (x, y)

    def stellprobe(self, x, y, t, schwelle_m):
        """Entfernung vom Standort beim Missionsstart; merkt das erste Erreichen."""
        if not self.faehrt() or not (math.isfinite(x) and math.isfinite(y)):
            return
        if self.stellprobe_start is None:
            self.stellprobe_start = (x, y)
        entfernung = math.dist(self.stellprobe_start, (x, y))
        self.stellprobe_max_m = max(self.stellprobe_max_m, entfernung)
        if schwelle_m > 0 and entfernung >= schwelle_m and self.stellprobe_weg is None:
            sh = self.self_healing or {}
            self.stellprobe_weg_um = t
            self.stellprobe_weg = dict(
                nach_s=round(t - self.gestartet_um, 1), entfernung_m=round(entfernung, 3),
                heilungen_bis_dahin=sh.get('heals'), rueckfahrten_bis_dahin=sh.get('track_backs'),
                ziele_bis_dahin=sh.get('goals_reached'))

    def stellprobe_ergebnis(self, schwelle_m):
        """befreit / nicht_blockiert / nicht_befreit; None ohne Stellprobe oder Fahrt."""
        if schwelle_m <= 0 or self.gestartet_um is None:
            return None
        weg = self.stellprobe_weg
        if weg is None:
            urteil = 'nicht_befreit'
        elif not weg['heilungen_bis_dahin']:
            urteil = 'nicht_blockiert'     # ohne Heilung weggefahren: Stelle sagt nichts aus
        else:
            urteil = 'befreit'
        return dict(schwelle_m=schwelle_m, urteil=urteil, weg=weg,
                    max_entfernung_m=round(self.stellprobe_max_m, 3))

    def vl53(self, t):
        if self.vl53_letzte is not None and self.faehrt():
            luecke = t - self.vl53_letzte
            if luecke > VL53_LUECKE_S:
                self.vl53_luecken += 1
                self.vl53_max_luecke_s = max(self.vl53_max_luecke_s, luecke)
                self._ereignis(t, 'vl53_luecke', dauer_s=round(luecke, 3))
        self.vl53_letzte = t

    def karte(self, werte, aufloesung, t):
        """Abdeckungskurve: höchstens alle 30 s und nur während der Fahrt."""
        if not self.faehrt() or not aufloesung > 0:
            return
        if self._abdeckung_letzte is not None and t - self._abdeckung_letzte < ABDECKUNG_TAKT_S:
            return
        self._abdeckung_letzte = t
        self.abdeckung.append(dict(t_s=self._t(t),
                                   fahrt_s=round(t - self.gestartet_um, 1),
                                   **flaechen(werte, aufloesung)))

    def abdeckung_zeiten(self):
        """Fahrzeit bis zu 85/90/95 % der freien Fläche am Ende (Endfläche = 100 %)."""
        if not self.abdeckung:
            return None
        ende = self.abdeckung[-1]['frei_m2']
        zeiten = {}
        for anteil in ABDECKUNG_ANTEILE:
            treffer = [p['fahrt_s'] for p in self.abdeckung
                       if ende > 0 and p['frei_m2'] >= anteil*ende]
            zeiten[f'{int(anteil*100)}_prozent_s'] = treffer[0] if treffer else None
        return dict(frei_ende_m2=ende, **zeiten)

    # --- Ergebnis -------------------------------------------------------
    def kriterien(self):
        sh = self.self_healing or {}
        ziele = sh.get('goals_reached') or 0
        return {
            'fahrt_begonnen': self.gestartet_um is not None,
            'fahrt_beendet': self.beendet_um is not None,
            'mehrere_ziele_erreicht': ziele >= 2,
            'sauberes_ende': sh.get('outcome') in SAUBERES_ENDE,
            'kein_not_aus_waehrend_fahrt': not self.estop_aktiv_waehrend_fahrt,
        }

    def zusammenfassung(self):
        sh = self.self_healing or {}
        dauer = (None if self.gestartet_um is None or self.beendet_um is None
                 else round(self.beendet_um - self.gestartet_um, 1))
        kriterien = self.kriterien()
        return {
            'schema_version': 1,
            'dauer_s': dauer,
            'endzustand': {k: sh.get(k) for k in (
                'state', 'outcome', 'reason', 'goals_reached', 'heals',
                'deferred_goals', 'track_backs', 'look_arounds')},
            'heilungsverlauf': (sh.get('ladder') or {}).get('history'),
            'karte_speicherbar': (self.explore_status or {}).get('map_ready_to_save'),
            'hwt_endzustand': self.hwt_zustand,
            'fahrbefehle': {k: (round(v, 3) if isinstance(v, float) else v)
                            for k, v in self.cmd.items()},
            'strecke_odom_m': round(self.strecke_m, 2),
            'vl53_luecken': {'anzahl': self.vl53_luecken,
                             'max_s': round(self.vl53_max_luecke_s, 3)},
            'abdeckung': self.abdeckung_zeiten(),
            'abdeckungskurve': self.abdeckung,
            'kriterien_automatisch': kriterien,
            'automatisch_erfuellt': all(kriterien.values()),
            'kriterien_manuell': list(MANUELL),
            'ereignisse': self.ereignisse,
        }


def flaechen(werte, aufloesung):
    """Freie, belegte und bekannte Fläche einer OccupancyGrid-Wertefolge in m²."""
    import numpy as np
    zellen = np.asarray(werte, dtype=np.int16)
    zelle_m2 = float(aufloesung)**2
    frei = int(np.count_nonzero((zellen >= 0) & (zellen < 25)))
    belegt = int(np.count_nonzero(zellen >= 65))
    bekannt = int(np.count_nonzero(zellen >= 0))
    return dict(frei_m2=round(frei*zelle_m2, 2), belegt_m2=round(belegt*zelle_m2, 2),
                bekannt_m2=round(bekannt*zelle_m2, 2))


# ---------------------------------------------------------------------------
#  ROS-Teil (nur Abonnements)
# ---------------------------------------------------------------------------

def _json(msg):
    try:
        daten = json.loads(msg.data)
    except (ValueError, TypeError):
        return None
    return daten if isinstance(daten, dict) else None


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--json', required=True, help='Zusammenfassung (lokal, nicht ins Repo)')
    parser.add_argument('--max-s', type=float, default=1800.0,
                        help='Sicherheitsende des Protokolls (Standard 30 min)')
    parser.add_argument('--nachlauf-s', type=float, default=5.0,
                        help='So lange nach dem Missionsende weiter mitschreiben')
    parser.add_argument('--stellprobe-m', type=float, default=0.0,
                        help='Stellprobe: Ende, sobald der Roboter so weit vom Standort beim '
                             'Missionsstart entfernt ist (0 = aus)')
    parser.add_argument('--stellprobe-fenster-s', type=float, default=300.0,
                        help='Stellprobe: Ende spätestens so lange nach dem Missionsstart')
    args = parser.parse_args(argv)

    import rclpy
    from geometry_msgs.msg import Twist
    from nav2_msgs.msg import SpeedLimit
    from nav_msgs.msg import OccupancyGrid, Odometry
    from rclpy.qos import (QoSProfile, DurabilityPolicy, ReliabilityPolicy,
                           qos_profile_sensor_data)
    from robot_interfaces.msg import NearFieldStatus
    from std_msgs.msg import Bool, String

    rclpy.init()
    node = rclpy.create_node('selbstheilung_lauf_protokoll')
    protokoll = LaufProtokoll(time.monotonic())
    jetzt = time.monotonic
    latched = QoSProfile(depth=1, reliability=ReliabilityPolicy.RELIABLE,
                         durability=DurabilityPolicy.TRANSIENT_LOCAL)

    def on_explore(msg):
        daten = _json(msg)
        if daten is not None:
            protokoll.explore(daten, jetzt())

    def on_mission(msg):
        daten = _json(msg)
        if daten is not None:
            protokoll.mission(daten, jetzt())

    node.create_subscription(String, '/explore/status_json', on_explore, 10)
    node.create_subscription(String, '/mission_manager/status_json', on_mission, latched)
    node.create_subscription(Bool, '/safety/estop',
                             lambda m: protokoll.estop_wert(bool(m.data), jetzt()), latched)
    node.create_subscription(SpeedLimit, '/speed_limit',
                             lambda m: protokoll.tempo(m.speed_limit, jetzt()), 10)
    node.create_subscription(Twist, '/cmd_vel',
                             lambda m: protokoll.cmd_vel(m.linear.x, m.angular.z),
                             qos_profile_sensor_data)
    def on_odom(m):
        x, y = m.pose.pose.position.x, m.pose.pose.position.y
        protokoll.odom(x, y)
        protokoll.stellprobe(x, y, jetzt(), args.stellprobe_m)

    node.create_subscription(Odometry, '/odom', on_odom, qos_profile_sensor_data)
    node.create_subscription(NearFieldStatus, '/near_field/status',
                             lambda m: protokoll.vl53(jetzt()), qos_profile_sensor_data)
    node.create_subscription(OccupancyGrid, '/map',
                             lambda m: protokoll.karte(m.data, m.info.resolution, jetzt()),
                             latched)

    print('Fahrtprotokoll läuft; wartet auf den Missionsstart.', flush=True)
    ende = jetzt() + args.max_s
    ende_grund = None
    try:
        while rclpy.ok() and jetzt() < ende:
            rclpy.spin_once(node, timeout_sec=0.1)
            if (protokoll.beendet_um is not None
                    and jetzt() - protokoll.beendet_um >= args.nachlauf_s):
                break
            if args.stellprobe_m > 0 and protokoll.gestartet_um is not None:
                if (protokoll.stellprobe_weg_um is not None
                        and jetzt() - protokoll.stellprobe_weg_um >= args.nachlauf_s):
                    ende_grund = 'stellprobe_weg'
                    break
                if jetzt() - protokoll.gestartet_um >= args.stellprobe_fenster_s:
                    ende_grund = 'stellprobe_fenster'
                    break
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()

    ergebnis = protokoll.zusammenfassung()
    ergebnis['protokoll_ende'] = ('missionsende' if protokoll.beendet_um is not None
                                  else ende_grund or 'zeitlimit_oder_abbruch')
    ergebnis['stellprobe'] = protokoll.stellprobe_ergebnis(args.stellprobe_m)
    os.makedirs(os.path.dirname(os.path.abspath(args.json)), exist_ok=True)
    with open(args.json, 'w', encoding='utf-8') as handle:
        json.dump(ergebnis, handle, ensure_ascii=False, indent=2)
    ausgabe = {k: v for k, v in ergebnis.items()
               if k not in ('ereignisse', 'heilungsverlauf', 'abdeckungskurve')}
    print(json.dumps(ausgabe, ensure_ascii=False, indent=2))
    if args.stellprobe_m > 0:
        return 0        # Urteil der Stellprobe steht im Ergebnis, nicht im Exit-Code
    return 0 if ergebnis['automatisch_erfuellt'] else 1


if __name__ == '__main__':
    sys.exit(main())
