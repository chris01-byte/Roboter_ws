#!/usr/bin/env python3
"""Rechenmodell des ESS23-RS-Antriebs, abgeleitet aus AT-1b (15.11.2026).

Nur Rechnung, kein ROS, keine Hardware. Das Modell hat eine einzige Regel:

    Der Antrieb verteilt jede Sollwertänderung auf die eingestellte
    Rampenzeit (Register 0x001E beim Beschleunigen, 0x001F beim Bremsen),
    gerechnet ab dem VORIGEN SOLLWERT, nicht ab dem tatsächlichen Tempo.

Folge: Ein Sprung 0 -> 153 U/min wird mit 153/2 s beschleunigt und ist nach
2 s erreicht. Eine Rampe in 20-Hz-Schritten endet mit einem kleinen Schritt
(z. B. 147 -> 153 U/min); der Antrieb beschleunigt danach nur noch mit
6/2 s = 3 U/min je Sekunde und braucht für den Rest fast eine Minute.

Das Modell gibt mit einer einzigen angepassten Größe (0,13 s Laufzeit vom
Befehl bis zum Motor) alle Tempoverläufe aus AT-1b wieder und, ohne
Anpassung, die Rückfahrstrecke aus SH-8b (0,153 m gerechnet, 0,151 m
gemessen). Es ist trotzdem ein Modell: Für andere Rampenzeiten als 2000 ms
ist es eine Vorhersage, keine Messung.

Aufruf: antriebsmodell.py [Rampenzeit ms ...]   (Vorgabe: 2000 100)
"""

import math
import sys

RADUMFANG_M = 2*math.pi*0.0624
GETRIEBE = 10.0
SCHREIBTAKT_S = 0.05          # base_hardware: modbus_write_period_s
LAUFZEIT_S = 0.13             # Befehl bis Motor, aus AT-1b Phase A
BREMSEN_MS = 400
MPS_JE_RPM = RADUMFANG_M/60.0/GETRIEBE
RADPS_JE_RPM = 0.25/73.9      # 0,25 rad/s entsprechen 73,9 U/min am Motor


def motor_rpm(v_mps):
    """Motordrehzahl zu einer Fahrgeschwindigkeit, ganzzahlig wie im Treiber."""
    return round(v_mps/MPS_JE_RPM)


def simuliere(sollwert_rpm, dauer_s, accel_ms, decel_ms=BREMSEN_MS,
              laufzeit_s=LAUFZEIT_S, dt=0.001):
    """Tempoverlauf [(t, U/min)] zu einer Sollwertfunktion t -> U/min."""
    tempo, ziel, rate = 0.0, 0, 0.0
    verlauf, t, naechster = [], 0.0, 0.0
    while t < dauer_s:
        if t >= naechster:
            naechster += SCHREIBTAKT_S
            neu = sollwert_rpm(t - laufzeit_s) if t >= laufzeit_s else 0
            if neu != ziel:
                zeit_ms = accel_ms if abs(neu) > abs(ziel) else decel_ms
                rate = abs(neu - ziel)/(zeit_ms/1000.0)
                ziel = neu
        if tempo < ziel:
            tempo = min(ziel, tempo + rate*dt)
        elif tempo > ziel:
            tempo = max(ziel, tempo - rate*dt)
        verlauf.append((t, tempo))
        t += dt
    return verlauf


def tempo_je_sekunde(verlauf, je_rpm):
    """Mittel je voller Sekunde, in der Einheit von ``je_rpm``."""
    werte = []
    for sekunde in range(int(verlauf[-1][0] + 1e-9) + 1):
        teil = [v for t, v in verlauf if sekunde <= t < sekunde + 1]
        if len(teil) >= 500:
            werte.append(round(sum(teil)/len(teil)*je_rpm, 4))
    return werte


def weg_m(verlauf, dt=0.001):
    return sum(v for _, v in verlauf)*dt*MPS_JE_RPM


def rampe_rpm(ziel_mps, schritt_mps):
    """Sollwertfunktion einer 20-Hz-Rampe (Glätter), in U/min."""
    return lambda t: motor_rpm(min(ziel_mps, (math.floor(max(0.0, t)*20) + 1)*schritt_mps))


def main(argv=None):
    zeiten = [int(a) for a in (argv if argv is not None else sys.argv[1:])] or [2000, 100]
    for accel_ms in zeiten:
        print(f'Rampenzeit {accel_ms} ms')
        faelle = (
            ('Sprung auf 0,10 m/s', lambda t: motor_rpm(0.10), 5.0),
            ('Rampe wie Nav2 auf 0,10 m/s', rampe_rpm(0.10, 0.006), 6.0),
            ('Rückfahrt Langsam-Zone −0,015 m/s', rampe_rpm(0.015, 0.0018), 30.1),
        )
        for name, soll, dauer in faelle:
            verlauf = simuliere(soll, dauer, accel_ms)
            print(f'  {name}: Weg {weg_m(verlauf):.3f} m, '
                  f'Tempo je Sekunde {tempo_je_sekunde(verlauf, MPS_JE_RPM)[:6]}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
