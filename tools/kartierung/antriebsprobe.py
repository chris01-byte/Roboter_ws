#!/usr/bin/env python3
"""Antriebsprobe AT-1: Sollwert gegen Encoder-Tempo (kurze Messfahrt).

ACHTUNG: Dieses Werkzeug BEWEGT den Roboter. Es läuft nur mit
``--freigabe AT-1`` und nur im Rahmen des gleichnamigen Auftrags
(docs/wohnungserkundung/AGENTENAUFTRAG.md, LAB-1). Freie Fläche: vor der
Front mindestens 1,5 m, seitlich je 0,6 m, hinten 0,5 m. Not-Aus in
Reichweite.

Anlass (14.11.2026): In sechs Fahrten kamen an der Basis 6,4–10,1 cm/s an,
gefahren wurden 1,3–1,7 cm/s. In SH-8b legten vier Rückfahrten mit 30 s und
−1,5 cm/s genau 0,151 m (dreimal) und 0,215 m zurück; das entspricht 8 und
11 U/min am Motor, den ersten Stufen der Anfahrrampe des Glätters.
Hypothese: Der Antrieb übernimmt einen Sollwert nur mit dem Startimpuls
beim Anfahren und fährt danach mit dem ersten kleinen Wert weiter.

Die Probe fährt feste Sollwertfolgen und misst über ``/odom``:

  A  Sprung vorwärts      0 → 0,10 m/s, 5 s
  B  Treppe aufwärts      0,02 m/s 4 s, dann 0,10 m/s 5 s
  C  Rampe wie Nav2       0 → 0,10 m/s mit 0,12 m/s² in 20-Hz-Schritten, 6 s
  F  Treppe abwärts       0,10 m/s 3 s, dann 0,03 m/s 4 s
  D  Sprung drehen        0 → 0,25 rad/s, 6 s
  E  Rampe drehen         0 → 0,25 rad/s mit 0,30 rad/s² in 20-Hz-Schritten, 6 s

Nach jeder Phase 3 s Stillstand (Nullbefehl = Stopp des Antriebs), dann mit
einem Sprung zurück zum Ausgangspunkt bzw. zur Ausgangsrichtung.

Die Befehle gehen auf ``/cmd_vel_smoothed``, also durch den
Kollisionsmonitor (VL53) zur Basis; der Glätter davor wird umgangen, damit
die Folge unverändert ankommt. Publiziert wird ausschließlich dieses eine
Topic. Abbruch mit Nullbefehlen bei Not-Aus, veralteter Odometrie, mehr als
0,9 m vor oder 0,2 m hinter dem Ausgangspunkt, mehr als 0,35 rad Abweichung
in einer Geradeausphase, Zeitüberschreitung oder Strg-C. Fällt das Werkzeug
aus, stoppt die Basis nach 0,25 s von selbst (Watchdog).
"""

import argparse
import json
import math
import os
import sys
import time

FREIGABE = 'AT-1'
RATE_HZ = 20.0
PAUSE_S = 3.0
V_SPRUNG, V_KLEIN, V_MITTEL = 0.10, 0.02, 0.03
W_SPRUNG = 0.25
A_LIN, A_ROT = 0.12, 0.30            # wie velocity_smoother max_accel
V_ZURUECK = 0.05                     # wie die erlaubte Rückwärtsgrenze des Glätters
GRENZE_VOR_M, GRENZE_ZURUECK_M = 0.90, 0.20
GRENZE_GIER_RAD = 0.35
ODOM_MAX_ALTER_S = 0.5
TOPIC = '/cmd_vel_smoothed'


def rampe(ziel, beschleunigung, t):
    """Wert einer Rampe in 20-Hz-Stufen, wie der Glätter sie ausgibt."""
    schritte = math.floor(t*RATE_HZ) + 1
    return min(ziel, schritte*beschleunigung/RATE_HZ)


# Phase: (Kennung, Art, Dauer s, Sollwertfunktion t -> (v, w), Beschreibung)
PHASEN = (
    ('A', 'gerade', 5.0, lambda t: (V_SPRUNG, 0.0), 'Sprung vorwärts 0,10 m/s'),
    ('B', 'gerade', 9.0, lambda t: (V_KLEIN if t < 4.0 else V_SPRUNG, 0.0),
     'Treppe 0,02 m/s (4 s), dann 0,10 m/s (5 s)'),
    ('C', 'gerade', 6.0, lambda t: (rampe(V_SPRUNG, A_LIN, t), 0.0),
     'Rampe wie Nav2 auf 0,10 m/s'),
    ('F', 'gerade', 7.0, lambda t: (V_SPRUNG if t < 3.0 else V_MITTEL, 0.0),
     'Treppe abwärts 0,10 m/s (3 s), dann 0,03 m/s (4 s)'),
    ('D', 'drehen', 6.0, lambda t: (0.0, W_SPRUNG), 'Sprung drehen 0,25 rad/s'),
    ('E', 'drehen', 6.0, lambda t: (0.0, rampe(W_SPRUNG, A_ROT, t)),
     'Rampe drehen auf 0,25 rad/s'),
)
# Abschnitte je Phase, über die ein Tempo gemittelt wird: (Name, von s, bis s, Sollwert).
ABSCHNITTE = {
    'A': (('ende', 3.0, 5.0, V_SPRUNG),),
    'B': (('stufe_1', 2.0, 4.0, V_KLEIN), ('stufe_2', 7.0, 9.0, V_SPRUNG)),
    'C': (('ende', 4.0, 6.0, V_SPRUNG),),
    'F': (('stufe_1', 1.5, 3.0, V_SPRUNG), ('stufe_2', 5.0, 7.0, V_MITTEL)),
    'D': (('ende', 4.0, 6.0, W_SPRUNG),),
    'E': (('ende', 4.0, 6.0, W_SPRUNG),),
}


def winkel(a):
    return math.atan2(math.sin(a), math.cos(a))


def lage(start, pose):
    """(längs, quer, Gier) der Pose relativ zur Startpose der Probe."""
    dx, dy = pose[0]-start[0], pose[1]-start[1]
    c, s = math.cos(start[2]), math.sin(start[2])
    return c*dx + s*dy, -s*dx + c*dy, winkel(pose[2]-start[2])


def grenzverletzung(art, laengs, gier_seit_phase):
    """Grund für den Abbruch oder None."""
    if laengs > GRENZE_VOR_M:
        return f'mehr als {GRENZE_VOR_M} m vor dem Ausgangspunkt'
    if laengs < -GRENZE_ZURUECK_M:
        return f'mehr als {GRENZE_ZURUECK_M} m hinter dem Ausgangspunkt'
    if art == 'gerade' and abs(gier_seit_phase) > GRENZE_GIER_RAD:
        return f'Richtung in der Geradeausphase um mehr als {GRENZE_GIER_RAD} rad geändert'
    return None


def tempo(reihe, von, bis, groesse):
    """Mittleres Tempo zwischen zwei Zeiten aus (t, längs, Gier-ungefaltet)."""
    index = 1 if groesse == 'weg' else 2
    teil = [p for p in reihe if von <= p[0] <= bis]
    if len(teil) < 2 or teil[-1][0] - teil[0][0] < 0.5:
        return None
    return (teil[-1][index] - teil[0][index])/(teil[-1][0] - teil[0][0])


def auswertung(kennung, art, reihe, befehle):
    """Kennwerte einer Phase. ``reihe``: (t, längs seit Phasenbeginn, Gier seit
    Phasenbeginn ungefaltet); ``befehle``: (t, v, w) wie an der Basis angekommen."""
    groesse = 'weg' if art == 'gerade' else 'gier'
    einheit = 'mps' if art == 'gerade' else 'radps'
    ergebnis = {'phase': kennung, 'art': art, 'messpunkte': len(reihe),
                'weg_m': round(reihe[-1][1], 3) if reihe else None,
                'gier_rad': round(reihe[-1][2], 3) if reihe else None,
                'abschnitte': {}}
    for name, von, bis, soll in ABSCHNITTE[kennung]:
        ist = tempo(reihe, von, bis, groesse)
        an_basis = [b[1] if art == 'gerade' else b[2] for b in befehle if von <= b[0] <= bis]
        ergebnis['abschnitte'][name] = {
            f'soll_{einheit}': soll,
            f'an_der_basis_{einheit}': (round(sum(an_basis)/len(an_basis), 4)
                                        if an_basis else None),
            f'ist_{einheit}': None if ist is None else round(ist, 4),
            'ist_zu_soll': None if ist is None else round(ist/soll, 2),
        }
    return ergebnis


def urteil(phasen):
    """Vorab festgelegte Auswertung der Hypothese „Sollwert nur beim Anfahren“."""
    def anteil(kennung, abschnitt):
        phase = phasen.get(kennung)
        return None if phase is None else phase['abschnitte'][abschnitt]['ist_zu_soll']

    sprung, rampe_v, stufe_2 = anteil('A', 'ende'), anteil('C', 'ende'), anteil('B', 'stufe_2')
    if None in (sprung, rampe_v, stufe_2):
        return {'hypothese_sollwert_nur_beim_anfahren': 'nicht_auswertbar'}
    if sprung >= .8 and rampe_v < .4 and stufe_2 < .4:
        befund = 'bestaetigt'
    elif rampe_v >= .8 and stufe_2 >= .8:
        befund = 'widerlegt'
    else:
        befund = 'unklar'
    return {'hypothese_sollwert_nur_beim_anfahren': befund,
            'sprung_ist_zu_soll': sprung, 'rampe_ist_zu_soll': rampe_v,
            'treppe_stufe_2_ist_zu_soll': stufe_2,
            'treppe_abwaerts_stufe_2_ist_zu_soll': anteil('F', 'stufe_2'),
            'drehen_sprung_ist_zu_soll': anteil('D', 'ende'),
            'drehen_rampe_ist_zu_soll': anteil('E', 'ende')}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--freigabe', default='',
                        help=f'muss genau "{FREIGABE}" sein, sonst wird nichts gesendet')
    parser.add_argument('--json', required=True, help='Ergebnis (lokal, nicht ins Repo)')
    parser.add_argument('--phasen', default='A,B,C,F,D,E',
                        help='Auswahl und Reihenfolge, z. B. "A,C"')
    parser.add_argument('--topic', default=TOPIC)
    args = parser.parse_args(argv)
    if args.freigabe != FREIGABE:
        print(f'Keine Bewegung: --freigabe {FREIGABE} fehlt.', file=sys.stderr)
        return 2
    gewaehlt = [k.strip().upper() for k in args.phasen.split(',') if k.strip()]
    plan = {p[0]: p for p in PHASEN}
    if not gewaehlt or any(k not in plan for k in gewaehlt):
        print('Unbekannte Phase; erlaubt sind A, B, C, F, D, E.', file=sys.stderr)
        return 2

    import rclpy
    from geometry_msgs.msg import Twist
    from nav_msgs.msg import Odometry
    from rclpy.qos import (DurabilityPolicy, QoSProfile, ReliabilityPolicy,
                           qos_profile_sensor_data)
    from std_msgs.msg import Bool

    rclpy.init()
    node = rclpy.create_node('antriebsprobe')
    zustand = dict(pose=None, pose_zeit=None, estop=None, basis=[])
    latched = QoSProfile(depth=1, reliability=ReliabilityPolicy.RELIABLE,
                         durability=DurabilityPolicy.TRANSIENT_LOCAL)

    def on_odom(m):
        q = m.pose.pose.orientation
        gier = math.atan2(2*(q.w*q.z + q.x*q.y), 1 - 2*(q.y*q.y + q.z*q.z))
        zustand.update(pose=(m.pose.pose.position.x, m.pose.pose.position.y, gier),
                       pose_zeit=time.monotonic())

    node.create_subscription(Odometry, '/odom', on_odom, qos_profile_sensor_data)
    node.create_subscription(Bool, '/safety/estop',
                             lambda m: zustand.update(estop=bool(m.data)), latched)
    node.create_subscription(Twist, '/cmd_vel', lambda m: zustand['basis'].append(
        (time.monotonic(), m.linear.x, m.angular.z)), qos_profile_sensor_data)
    pub = node.create_publisher(Twist, args.topic, 1)

    def sende(v, w):
        msg = Twist()
        msg.linear.x, msg.angular.z = float(v), float(w)
        pub.publish(msg)

    def takt():
        """Eingänge verarbeiten bis zum nächsten 20-Hz-Takt (ein Befehl je Takt)."""
        ende = time.monotonic() + 1.0/RATE_HZ
        while True:
            rest = ende - time.monotonic()
            if rest <= 0:
                return
            rclpy.spin_once(node, timeout_sec=rest)

    def halt(sekunden=1.0):
        ende = time.monotonic() + sekunden
        while time.monotonic() < ende:
            sende(0.0, 0.0)
            takt()

    def stoerung():
        if zustand['estop'] is not False:
            return 'Not-Aus aktiv oder Not-Aus-Zustand unbekannt'
        if zustand['pose_zeit'] is None or time.monotonic()-zustand['pose_zeit'] > ODOM_MAX_ALTER_S:
            return 'Odometrie fehlt oder ist veraltet'
        return None

    ergebnis = {'schema_version': 1, 'freigabe': FREIGABE, 'topic': args.topic,
                'zeit': time.strftime('%Y-%m-%dT%H:%M:%S'), 'phasen': {}, 'rueckwege': [],
                'abbruch': None}
    start = None

    def fahre(art, dauer, sollwert, zurueck_zu=None):
        """Eine Phase oder ein Rückweg; liefert (Reihe, Befehle an der Basis, Abbruchgrund)."""
        anfang = time.monotonic()
        pose0 = zustand['pose']
        reihe, gier_summe, gier_letzt = [], 0.0, pose0[2]
        zustand['basis'] = []
        while True:
            t = time.monotonic() - anfang
            grund = stoerung()
            pose = zustand['pose']
            laengs, _, _ = lage(start, pose)
            gier_summe += winkel(pose[2] - gier_letzt)
            gier_letzt = pose[2]
            laengs0, _, _ = lage(pose0, pose)
            reihe.append((round(t, 3), laengs0, gier_summe))
            grund = grund or grenzverletzung(art, laengs, gier_summe)
            if grund or t >= dauer:
                break
            if zurueck_zu is not None and zurueck_zu(pose):
                break
            sende(*sollwert(t))
            takt()
        befehle = [(round(b[0]-anfang, 3), b[1], b[2]) for b in zustand['basis']]
        halt(PAUSE_S if grund is None else 1.0)
        return reihe, befehle, grund

    try:
        frist = time.monotonic() + 5.0
        while time.monotonic() < frist and (zustand['pose'] is None or zustand['estop'] is None):
            rclpy.spin_once(node, timeout_sec=0.1)
        grund = stoerung()
        if grund is None and pub.get_subscription_count() == 0:
            grund = f'niemand hört auf {args.topic} (Kollisionsmonitor läuft nicht?)'
        if grund:
            ergebnis['abbruch'] = f'vor dem Start: {grund}'
        else:
            start = zustand['pose']
            halt(PAUSE_S)
            for kennung in gewaehlt:
                _, art, dauer, sollwert, text = plan[kennung]
                print(f'Phase {kennung}: {text}', flush=True)
                reihe, befehle, grund = fahre(art, dauer, sollwert)
                phase = auswertung(kennung, art, reihe, befehle)
                phase['beschreibung'] = text
                ergebnis['phasen'][kennung] = phase
                print(json.dumps(phase['abschnitte'], ensure_ascii=False), flush=True)
                if grund:
                    ergebnis['abbruch'] = f'Phase {kennung}: {grund}'
                    break
                # Zurück mit einem Sprung (voller Sollwert ab dem Anfahren).
                if art == 'gerade':
                    weg = lage(start, zustand['pose'])[0]
                    richtung = -1.0 if weg > 0 else 1.0
                    reihe, _, grund = fahre(
                        'gerade', abs(weg)/V_ZURUECK*2.0 + 5.0,
                        lambda t, r=richtung: (r*V_ZURUECK, 0.0),
                        zurueck_zu=lambda p, r=richtung: r*lage(start, p)[0] >= -0.01)
                else:
                    fehler = lage(start, zustand['pose'])[2]
                    richtung = -1.0 if fehler > 0 else 1.0
                    reihe, _, grund = fahre(
                        'drehen', abs(fehler)/W_SPRUNG*2.0 + 8.0,
                        lambda t, r=richtung: (0.0, r*W_SPRUNG),
                        zurueck_zu=lambda p, r=richtung: r*lage(start, p)[2] >= -0.03)
                rest = lage(start, zustand['pose'])
                ergebnis['rueckwege'].append({
                    'nach_phase': kennung, 'dauer_s': reihe[-1][0],
                    'rest_laengs_m': round(rest[0], 3), 'rest_quer_m': round(rest[1], 3),
                    'rest_gier_rad': round(rest[2], 3)})
                if grund:
                    ergebnis['abbruch'] = f'Rückweg nach Phase {kennung}: {grund}'
                    break
    except KeyboardInterrupt:
        ergebnis['abbruch'] = 'Strg-C'
    finally:
        try:
            halt(1.0)
        finally:
            node.destroy_node()
            rclpy.try_shutdown()

    ergebnis['urteil'] = urteil(ergebnis['phasen'])
    os.makedirs(os.path.dirname(os.path.abspath(args.json)), exist_ok=True)
    with open(args.json, 'w', encoding='utf-8') as handle:
        json.dump(ergebnis, handle, ensure_ascii=False, indent=2)
    print(json.dumps({'abbruch': ergebnis['abbruch'], 'urteil': ergebnis['urteil']},
                     ensure_ascii=False, indent=2))
    return 0 if ergebnis['abbruch'] is None else 1


if __name__ == '__main__':
    sys.exit(main())
