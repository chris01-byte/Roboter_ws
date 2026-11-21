#!/usr/bin/env python3
"""Die Angaben des Menschen zu einer Blickrunde als ``wahrheit.json`` eintragen.

Nach dem Blick auf das Übersichtsblatt sagt der Mensch, welche Nummern echte,
offene Ausgänge sind und was jede Nummer wirklich ist. Dieses Werkzeug prüft
die Angaben gegen die Ergebnisdatei des Trockenlaufs (gibt es die Nummern?)
und schreibt sie in den Ordner der Blickrunde. Zu jeder Nummer hält es fest,
wo die Öffnung lag: Die Nummern gelten nur für die Vermessung, mit der das
Blatt entstand; ändert sie sich, lässt sich so nachvollziehen, was gemeint war.
Eine vorhandene ``wahrheit.json`` wird nicht überschrieben, sondern als
``wahrheit_vorher_N.json`` aufbewahrt.

Aufruf (Beispiel):
    python3 wahrheit_eintragen.py --ergebnis AUSGABE/ergebnis.json --runden ORDNER \\
        --name labor_tuer_vorn --ausgaenge 1 --arten 1=tuer_offen --raum Labor
    # kein echter Ausgang unter den Nummern, aber einer ohne Nummer zu sehen:
    python3 wahrheit_eintragen.py ... --ausgaenge --arten 1=moebelspalt \\
        --ausgang-ohne-nummer ja --raum Labor
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lotse.blickrunde import runden_finden  # noqa: E402
from lotse.frage import ARTEN  # noqa: E402


def _ordner_der_runde(wurzel, name: str):
    for ordner in runden_finden(wurzel):
        with open(ordner / 'meta.json', encoding='utf-8') as datei:
            if str(json.load(datei).get('name') or ordner.name) == name:
                return ordner
    return None


def main(argv=None) -> int:
    eingabe = argparse.ArgumentParser(
        description='Angaben des Menschen zu einer Blickrunde als wahrheit.json eintragen.')
    eingabe.add_argument('--ergebnis', required=True,
                         help='ergebnis.json des Trockenlaufs, zu dem das Blatt gehört')
    eingabe.add_argument('--runden', required=True, help='Ordner der Blickrunden')
    eingabe.add_argument('--name', required=True, help='Name der Blickrunde')
    eingabe.add_argument('--ausgaenge', type=int, nargs='*', default=[],
                         help='Nummern der echten, offenen Ausgänge (leer: keiner)')
    eingabe.add_argument('--arten', nargs='*', default=[], metavar='NR=ART',
                         help='was jede Nummer wirklich ist; Arten: ' + ', '.join(ARTEN))
    eingabe.add_argument('--raum', default='')
    eingabe.add_argument('--ausgang-ohne-nummer', choices=('ja', 'nein'), default='nein',
                         help='gibt es von hier einen offenen Ausgang, der keine Nummer hat?')
    eingabe.add_argument('--bemerkung', default='',
                         help='wörtliche Anmerkung des Menschen, zum Beispiel zur Lage der Nummer')
    wahl = eingabe.parse_args(argv)

    with open(wahl.ergebnis, encoding='utf-8') as datei:
        ergebnis = json.load(datei)
    runde = next((r for r in ergebnis.get('runden', []) if r.get('name') == wahl.name), None)
    if runde is None:
        print(f'{wahl.ergebnis}: keine Runde „{wahl.name}“.', file=sys.stderr)
        return 2
    ordner = _ordner_der_runde(wahl.runden, wahl.name)
    if ordner is None:
        print(f'Keine Blickrunde „{wahl.name}“ unter {wahl.runden}.', file=sys.stderr)
        return 2
    vermessen = {int(o['nr']): o for o in runde.get('oeffnungen') or []}
    arten = {}
    for eintrag in wahl.arten:
        nr, _, art = eintrag.partition('=')
        if not nr.isdigit() or art not in ARTEN:
            print(f'--arten {eintrag!r}: erwartet NR=ART mit ART aus {", ".join(ARTEN)}.',
                  file=sys.stderr)
            return 2
        arten[int(nr)] = art
    unbekannt = sorted(nr for nr in set(wahl.ausgaenge) | set(arten) if nr not in vermessen)
    if unbekannt:
        print(f'Nummern {unbekannt} gibt es in dieser Runde nicht '
              f'(vermessen: {sorted(vermessen)}).', file=sys.stderr)
        return 2
    wahrheit = {
        'ausgaenge': sorted(set(wahl.ausgaenge)),
        # Von hier aus gibt es einen offenen Ausgang, den der Laser erreichen kann.
        'ausgang_sichtbar': bool(wahl.ausgaenge) or wahl.ausgang_ohne_nummer == 'ja',
        'arten': {str(nr): art for nr, art in sorted(arten.items())},
        'raum': wahl.raum,
        'bemerkung': wahl.bemerkung,
        # Wo jede Nummer lag, als das Blatt entstand (Standpunktrahmen).
        'lage': {str(nr): {'mitte': o.get('mitte'), 'breite_m': o.get('breite_m'),
                           'richtung_grad': o.get('richtung_grad'),
                           'entfernung_m': o.get('entfernung_m')}
                 for nr, o in sorted(vermessen.items())},
    }
    ziel = ordner / 'wahrheit.json'
    if ziel.exists():
        nummer = 1
        while (ordner / f'wahrheit_vorher_{nummer}.json').exists():
            nummer += 1
        ziel.rename(ordner / f'wahrheit_vorher_{nummer}.json')
        print(f'Vorhandene Angaben aufbewahrt als wahrheit_vorher_{nummer}.json')
    with open(ziel, 'w', encoding='utf-8') as datei:
        json.dump(wahrheit, datei, indent=1, ensure_ascii=False)
    kurz = {k: v for k, v in wahrheit.items() if k != 'lage'}
    print(f'{ziel}: {json.dumps(kurz, ensure_ascii=False)}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
