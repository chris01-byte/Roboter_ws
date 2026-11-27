#!/usr/bin/env python3
"""Trockenlauf KI-0 auswerten: Antworten der KI gegen die Wahrheit halten.

Liest die Ergebnisdatei von ``trockenlauf.py`` und je Blickrunde die Datei
``wahrheit.json`` (vom Menschen angegeben, siehe unten) und schreibt einen
Kurzbericht mit den Kriterien K0-1 bis K0-6. Der Bericht enthält nur Zahlen
und kurze Angaben je Runde, keine Bilder und keine Kartenkoordinaten.

``wahrheit.json`` im Ordner der Blickrunde:
    {"ausgaenge": [2], "ausgang_sichtbar": true,
     "arten": {"1": "moebelspalt", "2": "tuer_offen"}, "raum": "Arbeitszimmer"}

Aufruf:
    python3 trockenlauf_auswerten.py --ergebnis AUSGABE/ergebnis.json \\
        --runden ORDNER [--bericht bericht.md] [--json auswertung.json]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lotse.auswertung import bericht, werte_aus  # noqa: E402
from lotse.blickrunde import runden_finden  # noqa: E402
from lotse.frage import ARTEN  # noqa: E402


def lies_wahrheiten(wurzel) -> dict:
    """``wahrheit.json`` aller Runden lesen und auf Form prüfen."""
    wahrheiten = {}
    for ordner in runden_finden(wurzel):
        datei = ordner / 'wahrheit.json'
        if not datei.is_file():
            continue
        with open(datei, encoding='utf-8') as offen:
            wahr = json.load(offen)
        ausgaenge = wahr.get('ausgaenge')
        if not isinstance(ausgaenge, list) or not all(
                isinstance(n, int) and not isinstance(n, bool) for n in ausgaenge):
            raise ValueError(f'{datei}: "ausgaenge" muss eine Liste ganzer Zahlen sein')
        for nr, art in (wahr.get('arten') or {}).items():
            if art not in ARTEN:
                raise ValueError(f'{datei}: unbekannte art {art!r} für Nummer {nr}')
        with open(ordner / 'meta.json', encoding='utf-8') as offen:
            name = json.load(offen).get('name') or ordner.name
        wahrheiten[str(name)] = wahr
    return wahrheiten


def main(argv=None) -> int:
    eingabe = argparse.ArgumentParser(
        description='Trockenlauf KI-0 auswerten (Kriterien K0-1 bis K0-6).')
    eingabe.add_argument('--ergebnis', required=True)
    eingabe.add_argument('--runden', required=True,
                         help='Ordner der Blickrunden mit wahrheit.json')
    eingabe.add_argument('--bericht', help='Kurzbericht als Markdown schreiben')
    eingabe.add_argument('--json', help='Kennzahlen als JSON schreiben')
    wahl = eingabe.parse_args(argv)

    with open(wahl.ergebnis, encoding='utf-8') as datei:
        ergebnis = json.load(datei)
    try:
        wahrheiten = lies_wahrheiten(wahl.runden)
    except ValueError as fehler:
        print(str(fehler), file=sys.stderr)
        return 2
    auswertung = werte_aus(ergebnis.get('runden', []), wahrheiten)
    text = bericht(auswertung)
    print(text)
    if wahl.bericht:
        Path(wahl.bericht).write_text(text + '\n', encoding='utf-8')
    if wahl.json:
        with open(wahl.json, 'w', encoding='utf-8') as datei:
            json.dump(auswertung, datei, indent=1, ensure_ascii=False)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
