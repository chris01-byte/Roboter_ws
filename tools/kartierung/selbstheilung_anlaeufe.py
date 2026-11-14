#!/usr/bin/env python3
"""Anläufe einer Erkundungsfahrt aus dem Log auswerten (nur lesend, ohne ROS).

Fahrplan MASTERPLAN §9 Schritt 2 (Erkundungstempo). Frage: Wohin geht die
Fahrzeit? Gelesen werden nur Logzeilen von ``bt_navigator`` und
``collision_monitor`` (``launch.log`` am Roboter, die Einzel-Logs der
Simulation oder ein ``ablauf.txt``-Auszug mit Uhrzeiten):

  - je Anlauf: Entfernung des Ziels vom Standort, Dauer, Ausgang
    (erreicht, gescheitert, abgebrochen),
  - Summen: Anteil der kurzen Anläufe, Median von Entfernung und Dauer,
    Fahrzeit in erreichten und in nicht erreichten Anläufen,
  - Zeitanteile des Kollisionsmonitors (Langsam-Zone, „approach“),
  - Fahrbefehle an der Basis (``base_hardware`` schreibt etwa einmal je
    Sekunde ``CMD: v=… w=…`` oder ``TIMEOUT-STOP``): wie viele Sekunden
    eines Anlaufs der Roboter vorwärts fahren, drehen, rückwärts fahren oder
    stehen sollte, wie lange gar kein Befehl ankam, und mit welcher
    Geschwindigkeit er fahren sollte.

Anlass (SH-8, 13.11.2026): Von 26 Anläufen lagen 14 Ziele näher als 0,5 m;
ein erreichtes Ziel kostete im Median 70 s. Die sechs vollen Fahrten aus
SH-6 und SH-7 (14.11.2026): effektiv 0,8–1,1 cm/s zum erreichten Ziel bei
befohlenen 10–13,5 cm/s, Ziele über 1,5 m nur in 2 von 42 Anläufen erreicht.
Die Fahrbefehle zeigen, ob die Basis so langsam fahren sollte oder ob
Befehle fehlten.

Aufruf:  selbstheilung_anlaeufe.py LOGDATEI [LOGDATEI ...] [--json AUSGABE]
"""

import argparse
import json
import math
import re
import statistics
import sys

ZEILE = re.compile(r'\[(\d+\.\d+)\]\s+\[([\w.]+)\]:\s+(.*)')
UHRZEIT = re.compile(r'^\s*(\d\d):(\d\d):(\d\d)\s+([\w.]+):\s+(.*)')
BEGINN = re.compile(r'Begin navigating from current location \(([-\d.]+), ([-\d.]+)\) '
                    r'to \(([-\d.]+), ([-\d.]+)\)')
ENDE = re.compile(r'Goal (succeeded|failed|canceled)')
AUSGANG = dict(succeeded='erreicht', failed='gescheitert', canceled='abgebrochen')
KURZ_M = 0.5
BASIS = re.compile(r'(CMD|TIMEOUT-STOP): v=([+-]?[\d.]+) m/s w=([+-]?[\d.]+) rad/s')
V_NULL, W_NULL = 0.002, 0.005        # darunter gilt ein Befehl als null
ABTAST_MAX_S = 2.0                   # ein Logeintrag steht höchstens für so viele Sekunden
KLASSEN = ('vorwaerts_s', 'drehen_s', 'rueckwaerts_s', 'stehen_s', 'ohne_befehl_s')


def zeilen(text):
    """(Zeit in s, Knoten, Meldung) aus ROS-Logzeilen oder Uhrzeit-Auszügen."""
    tage = 0
    letzte = None
    for zeile in text.splitlines():
        treffer = ZEILE.search(zeile)
        if treffer:
            yield float(treffer.group(1)), treffer.group(2), treffer.group(3)
            continue
        treffer = UHRZEIT.match(zeile)
        if treffer:
            h, m, s = (int(treffer.group(i)) for i in (1, 2, 3))
            t = h*3600 + m*60 + s + tage*86400
            if letzte is not None and t < letzte - 43200:   # über Mitternacht
                tage += 1
                t += 86400
            letzte = t
            yield float(t), treffer.group(4), treffer.group(5)


def befehlsklasse(modus, v, w):
    if modus != 'CMD':
        return 'ohne_befehl_s'
    if v >= V_NULL:
        return 'vorwaerts_s'
    if v <= -V_NULL:
        return 'rueckwaerts_s'
    return 'drehen_s' if abs(w) >= W_NULL else 'stehen_s'


def fahrbefehle(befehle, anlaeufe):
    """Zeitanteile der Basisbefehle während der Anläufe; ergänzt jeden Anlauf.

    ``befehle``: (Zeit, Modus, v, w), etwa einmal je Sekunde. Jeder Eintrag
    zählt bis zum nächsten, höchstens ``ABTAST_MAX_S``. Ohne Basiszeilen
    (Auszug, Simulation ohne Basis) ``None``.
    """
    if not befehle:
        return None
    summe = dict.fromkeys(KLASSEN, 0.0)
    v_vor, w_dreh, weg = [], [], 0.0
    for anlauf in anlaeufe:
        anlauf.update({k: 0.0 for k in KLASSEN}, v_mittel_mps=None)
    grenzen = [(a['_t'], a['_t'] + a['dauer_s'], a) for a in anlaeufe]
    for i, (t, modus, v, w) in enumerate(befehle):
        dt = min(befehle[i+1][0] - t, ABTAST_MAX_S) if i + 1 < len(befehle) else 1.0
        if dt <= 0:
            continue
        treffer, ende = next(((a, bis) for von, bis, a in grenzen if von <= t <= bis),
                             (None, None))
        if treffer is None:
            continue                      # zwischen den Anläufen: nicht Teil der Frage
        dt = min(dt, ende - t)            # nicht über das Ende des Anlaufs hinaus
        if dt <= 0:
            continue
        klasse = befehlsklasse(modus, v, w)
        summe[klasse] += dt
        treffer[klasse] += dt
        if klasse == 'vorwaerts_s':
            v_vor.append(v)
            weg += v*dt
            treffer.setdefault('_v', []).append(v)
        elif klasse == 'drehen_s':
            w_dreh.append(abs(w))
    for anlauf in anlaeufe:
        werte = anlauf.pop('_v', [])
        anlauf['v_mittel_mps'] = round(statistics.fmean(werte), 3) if werte else None
        for k in KLASSEN:
            anlauf[k] = round(anlauf[k], 1)
    gesamt = sum(summe.values())
    erreicht = [a for a in anlaeufe if a['ausgang'] == 'erreicht']
    v_sortiert = sorted(v_vor)
    return {
        'in_anlaeufen_s': {k: round(v, 1) for k, v in summe.items()},
        'anteile': ({k[:-2]: round(v/gesamt, 2) for k, v in summe.items()} if gesamt > 0 else None),
        'v_vorwaerts_median_mps': round(statistics.median(v_vor), 3) if v_vor else None,
        'v_vorwaerts_mittel_mps': round(statistics.fmean(v_vor), 3) if v_vor else None,
        'v_vorwaerts_p90_mps': (round(v_sortiert[int(.9*(len(v_sortiert)-1))], 3)
                                if v_vor else None),
        'w_drehen_median_radps': round(statistics.median(w_dreh), 3) if w_dreh else None,
        'befohlener_weg_vorwaerts_m': round(weg, 2),
        'erreicht_vorwaerts_s': round(sum(a['vorwaerts_s'] for a in erreicht), 1),
        'erreicht_drehen_s': round(sum(a['drehen_s'] for a in erreicht), 1),
        'erreicht_stehen_oder_ohne_befehl_s': round(sum(
            a['stehen_s'] + a['ohne_befehl_s'] for a in erreicht), 1),
    }


def auswerten(eintraege):
    """Anläufe und Zeitanteile aus einer zeitlich sortierten Eintragsfolge."""
    anlaeufe, offen = [], None
    befehle = []
    zustand, seit = None, None
    anteile = dict(langsam_s=0.0, approach_s=0.0)
    erste = letzte = None
    for t, knoten, meldung in eintraege:
        erste = t if erste is None else erste
        letzte = t
        basis = BASIS.match(meldung)
        if basis:
            befehle.append((t, basis.group(1), float(basis.group(2)), float(basis.group(3))))
            continue
        if knoten == 'collision_monitor' and 'Robot to' in meldung:
            if zustand is not None:
                anteile[zustand] += t - seit
            zustand = ('langsam_s' if 'slowdown' in meldung
                       else 'approach_s' if 'approach' in meldung else None)
            seit = t
            continue
        if knoten != 'bt_navigator':
            continue
        beginn = BEGINN.search(meldung)
        if beginn:
            x0, y0, x1, y1 = (float(v) for v in beginn.groups())
            offen = dict(t_s=t, _t=t, von=[x0, y0], ziel=[x1, y1],
                         entfernung_m=round(math.dist((x0, y0), (x1, y1)), 2))
            continue
        ende = ENDE.search(meldung)
        if ende and offen is not None:
            offen.update(dauer_s=round(t - offen['t_s'], 1), ausgang=AUSGANG[ende.group(1)])
            anlaeufe.append(offen)
            offen = None
    if zustand is not None and letzte is not None:
        anteile[zustand] += letzte - seit
    dauer = 0.0 if erste is None else letzte - erste
    befehlsblock = fahrbefehle(befehle, anlaeufe)
    for anlauf in anlaeufe:
        anlauf['t_s'] = round(anlauf.pop('_t') - erste, 1)
    return anlaeufe, dict(dauer_s=round(dauer, 1), fahrbefehle=befehlsblock,
                          **{k: round(v, 1) for k, v in anteile.items()})


def zusammenfassung(anlaeufe, zeiten):
    erreicht = [a for a in anlaeufe if a['ausgang'] == 'erreicht']
    andere = [a for a in anlaeufe if a['ausgang'] != 'erreicht']

    def median(werte):
        return round(statistics.median(werte), 2) if werte else None

    dauer = zeiten['dauer_s']
    return {
        'anlaeufe': len(anlaeufe),
        'erreicht': len(erreicht),
        'gescheitert': sum(a['ausgang'] == 'gescheitert' for a in anlaeufe),
        'abgebrochen': sum(a['ausgang'] == 'abgebrochen' for a in anlaeufe),
        'ziel_entfernung_median_m': median([a['entfernung_m'] for a in anlaeufe]),
        f'ziele_unter_{KURZ_M}_m': sum(a['entfernung_m'] < KURZ_M for a in anlaeufe),
        'dauer_erreicht_median_s': median([a['dauer_s'] for a in erreicht]),
        'zeit_in_erreichten_s': round(sum(a['dauer_s'] for a in erreicht), 1),
        'zeit_in_nicht_erreichten_s': round(sum(a['dauer_s'] for a in andere), 1),
        'weg_zu_erreichten_zielen_m': round(sum(a['entfernung_m'] for a in erreicht), 2),
        'dauer_s': dauer,
        'anteil_langsam_zone': round(zeiten['langsam_s']/dauer, 2) if dauer > 0 else None,
        'anteil_approach': round(zeiten['approach_s']/dauer, 2) if dauer > 0 else None,
        'fahrbefehle': zeiten.get('fahrbefehle'),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('logs', nargs='+')
    parser.add_argument('--json', help='Ergebnis zusätzlich als JSON (lokal, nicht ins Repo)')
    args = parser.parse_args(argv)
    eintraege = []
    for pfad in args.logs:
        with open(pfad, 'r', encoding='utf-8', errors='replace') as handle:
            eintraege += list(zeilen(handle.read()))
    eintraege.sort(key=lambda e: e[0])
    anlaeufe, zeiten = auswerten(eintraege)
    ergebnis = dict(zusammenfassung=zusammenfassung(anlaeufe, zeiten), anlaeufe=anlaeufe)
    print(json.dumps(ergebnis['zusammenfassung'], ensure_ascii=False, indent=2))
    for a in anlaeufe:
        zeile = (f"{a['t_s']:8.1f} s  {a['ausgang']:11s} {a['dauer_s']:6.1f} s  "
                 f"Ziel {a['entfernung_m']:.2f} m entfernt")
        if 'vorwaerts_s' in a:
            v = a['v_mittel_mps']
            zeile += (f"  | vor {a['vorwaerts_s']:5.1f} s"
                      f" ({'-' if v is None else format(v, '.3f')} m/s)"
                      f"  drehen {a['drehen_s']:5.1f} s  zurück {a['rueckwaerts_s']:4.1f} s"
                      f"  stehen {a['stehen_s']:5.1f} s  ohne Befehl {a['ohne_befehl_s']:5.1f} s")
        print(zeile)
    if args.json:
        with open(args.json, 'w', encoding='utf-8') as handle:
            json.dump(ergebnis, handle, ensure_ascii=False, indent=2)
    return 0


if __name__ == '__main__':
    sys.exit(main())
