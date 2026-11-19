#!/usr/bin/env python3
"""Trockenlauf KI-0: Blickrunden aufbereiten und den KI-Rechner befragen.

Für jede Blickrunde: Drehwinkel bestimmen, acht Bilder wählen, Öffnungen
vermessen, Nummern einzeichnen, Skizze bauen, Frage stellen, Antwort prüfen.
Es wird nichts gefahren und nichts am Roboter verändert.

Aufrufe:
    # nur aufbereiten und ansehen (ohne KI-Rechner)
    python3 trockenlauf.py --runden ORDNER --ausgabe ORDNER --nur-markieren

    # am KI-Rechner fragen, je Runde dreimal, zwei Modelle im Vergleich
    python3 trockenlauf.py --runden ORDNER --ausgabe ORDNER \\
        --modell MODELL_A --modell MODELL_B --wiederholungen 3

Die Ausgabe (markierte Fotos, Skizzen, Ergebnisdatei) enthält Bilder und
Maße der Wohnung. Sie bleibt auf dem KI-Rechner und gehört nicht ins
Repository.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lotse import SCHEMA_VERSION  # noqa: E402
from lotse.ablauf import befrage, bereite_vor  # noqa: E402
from lotse.blickrunde import Blickrunde, runden_finden  # noqa: E402
from lotse.ki_rechner import STANDARD_URL, modelle  # noqa: E402


def _speichere_ansicht(vorbereitung, ordner: Path) -> None:
    ordner.mkdir(parents=True, exist_ok=True)
    for eintrag, foto in zip(vorbereitung.auswahl['bilder'], vorbereitung.fotos):
        foto.save(ordner / f'B{eintrag["bild"]}.jpg', quality=90)
    vorbereitung.skizze.save(ordner / 'skizze.png')
    vorbereitung.blatt.save(ordner / 'uebersicht.jpg', quality=90)
    (ordner / 'frage.txt').write_text(vorbereitung.frage.text, encoding='utf-8')


def main(argv=None) -> int:
    eingabe = argparse.ArgumentParser(
        description='Trockenlauf KI-0: Blickrunden aufbereiten und die KI befragen.')
    eingabe.add_argument('--runden', required=True,
                         help='Ordner mit Blickrunden (oder eine einzelne Runde)')
    eingabe.add_argument('--ausgabe', required=True,
                         help='Zielordner für markierte Fotos, Skizzen, Ergebnis')
    eingabe.add_argument('--modell', action='append', default=[],
                         help='Modellname in Ollama; mehrfach für einen Vergleich')
    eingabe.add_argument('--wiederholungen', type=int, default=1)
    eingabe.add_argument('--url', default=STANDARD_URL,
                         help='Adresse des Ollama-Dienstes im Haus')
    eingabe.add_argument('--zeitgrenze', type=float, default=60.0,
                         help='Sekunden je Antwort')
    eingabe.add_argument('--bilder', type=int, default=8,
                         help='Anzahl Fotos je Blickrunde')
    eingabe.add_argument('--mosaik', action='store_true',
                         help='alle Fotos auf einem Blatt senden (für Modelle, '
                              'die nur ein Bild annehmen)')
    eingabe.add_argument('--kontext', type=int, default=8192,
                         help='Kontextlänge des Modells (num_ctx)')
    eingabe.add_argument('--nur-markieren', action='store_true',
                         help='nicht fragen, nur aufbereiten')
    wahl = eingabe.parse_args(argv)

    if not wahl.nur_markieren and not wahl.modell:
        eingabe.error('--modell angeben oder --nur-markieren setzen')
    ordner = runden_finden(wahl.runden)
    if not ordner:
        print(f'Keine Blickrunde unter {wahl.runden} gefunden.', file=sys.stderr)
        return 2
    ausgabe = Path(wahl.ausgabe)
    ausgabe.mkdir(parents=True, exist_ok=True)

    if not wahl.nur_markieren:
        vorhanden = modelle(wahl.url)
        if vorhanden is None:
            print(f'Der KI-Rechner antwortet nicht unter {wahl.url}.', file=sys.stderr)
            return 3
        fehlend = [m for m in wahl.modell if m not in vorhanden
                   and f'{m}:latest' not in vorhanden]
        if fehlend:
            print(f'Diese Modelle sind dort nicht vorhanden: {fehlend}. '
                  f'Vorhanden: {vorhanden}', file=sys.stderr)
            return 3

    ergebnis = {
        'schema_version': SCHEMA_VERSION,
        'erzeugt_unix': round(time.time(), 1),
        'einstellungen': {
            'modelle': wahl.modell, 'wiederholungen': wahl.wiederholungen,
            'zeitgrenze_s': wahl.zeitgrenze, 'bilder': wahl.bilder,
            'mosaik': wahl.mosaik, 'kontext': wahl.kontext,
        },
        'runden': [],
    }
    for pfad in ordner:
        try:
            vorbereitung = bereite_vor(Blickrunde.lade(pfad), wahl.bilder,
                                       mosaik=wahl.mosaik)
        except (ValueError, OSError, KeyError) as fehler:
            print(f'{pfad.name}: übersprungen ({fehler})', file=sys.stderr)
            ergebnis['runden'].append({'name': pfad.name, 'fehler': str(fehler),
                                       'vollstaendig': False, 'antworten': []})
            continue
        _speichere_ansicht(vorbereitung, ausgabe / vorbereitung.name)
        eintrag = vorbereitung.als_dict()
        eintrag['antworten'] = []
        print(f'{vorbereitung.name}: {len(vorbereitung.auswahl["bilder"])} Bilder, '
              f'gedreht {vorbereitung.auswahl["gedreht_grad"]}°, '
              f'{len(vorbereitung.oeffnungen)} Öffnung(en) vermessen')
        if not wahl.nur_markieren:
            for modell in wahl.modell:
                for nummer in range(wahl.wiederholungen):
                    antwort = befrage(vorbereitung, modell, url=wahl.url,
                                      zeitgrenze_s=wahl.zeitgrenze,
                                      wiederholung=nummer, mosaik=wahl.mosaik,
                                      optionen={'num_ctx': wahl.kontext})
                    eintrag['antworten'].append(antwort)
                    if antwort['fehler']:
                        kurz = f'keine Antwort ({antwort["fehler"]})'
                    elif antwort['pruefung']['gueltig']:
                        kurz = f'Wahl {antwort["pruefung"]["wahl"]}'
                    else:
                        kurz = f'verworfen {antwort["pruefung"]["fehler"]}'
                    print(f'  {modell} #{nummer + 1}: {kurz}, {antwort["dauer_s"]} s')
        ergebnis['runden'].append(eintrag)
        with open(ausgabe / 'ergebnis.json', 'w', encoding='utf-8') as datei:
            json.dump(ergebnis, datei, indent=1, ensure_ascii=False)
    print(f'Ergebnis: {ausgabe / "ergebnis.json"}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
