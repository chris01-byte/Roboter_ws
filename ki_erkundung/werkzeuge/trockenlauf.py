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

    # auf dem Roboter: den Lotsen-Dienst auf dem KI-Rechner über ROS fragen
    python3 trockenlauf.py --runden ORDNER --ausgabe ORDNER --ueber-ros

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
sys.path.insert(0, str(Path(__file__).resolve().parent))

from lotse import SCHEMA_VERSION  # noqa: E402
from lotse.ablauf import befrage, bereite_vor  # noqa: E402
from lotse.blickrunde import Blickrunde, runden_finden  # noqa: E402
from lotse.ki_rechner import STANDARD_URL, modelle, umgebung  # noqa: E402
from ros_ende import Ende, ros_beenden, ros_starten  # noqa: E402


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
    eingabe.add_argument('--denken', choices=('an', 'aus'), default=None,
                         help='Denkschalter des Modells (zum Beispiel Qwen3.5); '
                              'ohne Angabe gilt die Vorgabe des Modells')
    eingabe.add_argument('--ueber-ros', action='store_true',
                         help='über den Lotsen-Dienst auf dem KI-Rechner fragen '
                              '(vom Roboter aus); das Modell bestimmt der Dienst')
    eingabe.add_argument('--nur-markieren', action='store_true',
                         help='nicht fragen, nur aufbereiten')
    wahl = eingabe.parse_args(argv)

    if not wahl.nur_markieren and not wahl.modell and not wahl.ueber_ros:
        eingabe.error('--modell, --ueber-ros oder --nur-markieren angeben')
    if wahl.ueber_ros and wahl.modell:
        eingabe.error('mit --ueber-ros bestimmt der Lotsen-Dienst das Modell')
    # Über ROS setzt ein Signal nur eine Marke (ros_ende); begonnene Runden
    # bleiben im Ergebnis. Ohne ROS bleibt Strg+C, wie es war.
    ende = Ende()
    if wahl.ueber_ros:
        ende.anmelden()
    try:
        return _trockenlauf(wahl, ende)
    finally:
        ende.abmelden()


def _trockenlauf(wahl, ende: Ende) -> int:
    denken = {'an': True, 'aus': False, None: None}[wahl.denken]
    ordner = runden_finden(wahl.runden)
    if not ordner:
        print(f'Keine Blickrunde unter {wahl.runden} gefunden.', file=sys.stderr)
        return 2
    ausgabe = Path(wahl.ausgabe)
    ausgabe.mkdir(parents=True, exist_ok=True)

    verbindung, weg, umgebungen = None, None, {}
    eigener_kontext = False
    if wahl.ueber_ros:
        from ki_verbindung_ros import Verbindung
        eigener_kontext = ros_starten()
        verbindung = Verbindung(abbruch=ende.gesetzt)
        status = verbindung.status(warten_s=8.0)
        if not status or not status.get('bereit'):
            print('Der Lotsen-Dienst auf dem KI-Rechner ist nicht zu hören oder '
                  f'nicht bereit (Status: {status}).', file=sys.stderr)
            verbindung.schliessen()
            ros_beenden(eigener_kontext=eigener_kontext)
            return 3
        wahl.modell = [str(status.get('modell'))]
        umgebungen = {wahl.modell[0]: status.get('umgebung') or {}}
        weg = verbindung.frage_stellen
    elif not wahl.nur_markieren:
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
        umgebungen = {m: umgebung(m, wahl.url) for m in wahl.modell}

    ergebnis = {
        'schema_version': SCHEMA_VERSION,
        'erzeugt_unix': round(time.time(), 1),
        'einstellungen': {
            'modelle': wahl.modell, 'wiederholungen': wahl.wiederholungen,
            'zeitgrenze_s': wahl.zeitgrenze, 'bilder': wahl.bilder,
            'mosaik': wahl.mosaik, 'kontext': wahl.kontext,
            'denken': wahl.denken, 'ueber_ros': wahl.ueber_ros,
            # Fassung des Dienstes und Kennung jedes Modells: Der Name allein
            # sagt nach einem Update nicht mehr, womit geantwortet wurde.
            'umgebung': umgebungen,
        },
        'runden': [],
    }
    for pfad in ordner:
        if ende.gesetzt():
            print(f'Abgebrochen ({ende.signal}); weitere Runden werden nicht befragt.',
                  file=sys.stderr)
            break
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
                    if ende.gesetzt():
                        break
                    antwort = befrage(vorbereitung, modell, url=wahl.url,
                                      zeitgrenze_s=wahl.zeitgrenze,
                                      wiederholung=nummer, mosaik=wahl.mosaik,
                                      optionen={'num_ctx': wahl.kontext},
                                      denken=denken, weg=weg)
                    eintrag['antworten'].append(antwort)
                    if antwort['fehler']:
                        meldung = (antwort.get('meta') or {}).get('meldung')
                        kurz = (f'keine Antwort ({antwort["fehler"]}'
                                + (f': {meldung}' if meldung else '') + ')')
                    elif antwort['pruefung']['gueltig']:
                        p = antwort['pruefung']
                        arten = ', '.join(f'{k}={v}' for k, v in p['arten'].items())
                        kurz = f'Wahl {p["wahl"]} [{arten}] Raum {p["raum"]!r}'
                    else:
                        kurz = f'verworfen {antwort["pruefung"]["fehler"]}'
                    meta = antwort.get('meta') or {}
                    zeiten = (f' (laden {meta["load_s"]} s, Bild/Text eingelesen '
                              f'{meta.get("prompt_eval_count")} Teile)'
                              if 'load_s' in meta else '')
                    print(f'  {modell} #{nummer + 1}: {kurz}, {antwort["dauer_s"]} s{zeiten}')
        ergebnis['runden'].append(eintrag)
        with open(ausgabe / 'ergebnis.json', 'w', encoding='utf-8') as datei:
            json.dump(ergebnis, datei, indent=1, ensure_ascii=False)
    if verbindung is not None:
        verbindung.schliessen()
    if wahl.ueber_ros:
        ros_beenden(eigener_kontext=eigener_kontext)
    print(f'Ergebnis: {ausgabe / "ergebnis.json"}')
    return 1 if ende.gesetzt() else 0


if __name__ == '__main__':
    raise SystemExit(main())
