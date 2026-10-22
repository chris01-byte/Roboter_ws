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
  - die automatisch prüfbaren Kriterien der Abnahmestufe 1.

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

    def vl53(self, t):
        if self.vl53_letzte is not None and self.faehrt():
            luecke = t - self.vl53_letzte
            if luecke > VL53_LUECKE_S:
                self.vl53_luecken += 1
                self.vl53_max_luecke_s = max(self.vl53_max_luecke_s, luecke)
                self._ereignis(t, 'vl53_luecke', dauer_s=round(luecke, 3))
        self.vl53_letzte = t

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
            'kriterien_automatisch': kriterien,
            'automatisch_erfuellt': all(kriterien.values()),
            'kriterien_manuell': list(MANUELL),
            'ereignisse': self.ereignisse,
        }


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
    args = parser.parse_args(argv)

    import rclpy
    from geometry_msgs.msg import Twist
    from nav2_msgs.msg import SpeedLimit
    from nav_msgs.msg import Odometry
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
    node.create_subscription(Odometry, '/odom',
                             lambda m: protokoll.odom(m.pose.pose.position.x,
                                                      m.pose.pose.position.y),
                             qos_profile_sensor_data)
    node.create_subscription(NearFieldStatus, '/near_field/status',
                             lambda m: protokoll.vl53(jetzt()), qos_profile_sensor_data)

    print('Fahrtprotokoll läuft; wartet auf den Missionsstart.', flush=True)
    ende = jetzt() + args.max_s
    try:
        while rclpy.ok() and jetzt() < ende:
            rclpy.spin_once(node, timeout_sec=0.1)
            if (protokoll.beendet_um is not None
                    and jetzt() - protokoll.beendet_um >= args.nachlauf_s):
                break
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()

    ergebnis = protokoll.zusammenfassung()
    ergebnis['protokoll_ende'] = ('missionsende' if protokoll.beendet_um is not None
                                  else 'zeitlimit_oder_abbruch')
    os.makedirs(os.path.dirname(os.path.abspath(args.json)), exist_ok=True)
    with open(args.json, 'w', encoding='utf-8') as handle:
        json.dump(ergebnis, handle, ensure_ascii=False, indent=2)
    ausgabe = {k: v for k, v in ergebnis.items() if k not in ('ereignisse', 'heilungsverlauf')}
    print(json.dumps(ausgabe, ensure_ascii=False, indent=2))
    return 0 if ergebnis['automatisch_erfuellt'] else 1


if __name__ == '__main__':
    sys.exit(main())
