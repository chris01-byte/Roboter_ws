#!/usr/bin/env python3
"""Auf dem Roboter: die KI aus der letzten Blickrunde den Ausgang wählen lassen.

Nach dem Rundblick (der Erkunder wartet stehend auf ein Fahrziel) bereitet
das Werkzeug die neueste Blickrunde auf wie der Trockenlauf – Drehwinkel,
acht Bilder, Öffnungen vermessen, Nummern einzeichnen – und fragt die KI auf
dem KI-Rechner über den Lotsen-Dienst. Die Antwort wird geprüft und gegen die
Vermessung gehalten. Eine gültige Wahl schreibt es mit ihrem Ort in der
Karte in eine Wahl-Datei. **Es fährt nicht und sendet dem Erkunder nichts:**
Zum Fahren gibt ein Mensch die Wahl frei, dann übernimmt
``fahrziel_senden.py --zur-tuer --wahl DATEI``; sagt er nein, schließt
``fahrziel_senden.py --ende`` die Mission.

    python3 ki_tuer_waehlen.py --ueber-ros

Ausgegeben werden ein Satz zur Wahl (nur Maße vom Roboter aus, Richtung zu
seiner jetzigen Blickrichtung), die Einordnung jeder Nummer, die Begründung
der KI und der Pfad der Wahl-Datei. Wahl-Datei und Protokoll liegen unter
``~/.local/share/amadeus/ki_erkundung/wahl/`` auf dem Roboter. Sie enthalten
Koordinaten der Wohnung, aber keine Bilder, und gehören nicht ins
Repository.

Nach dem Schreiben steht da „Kennung der Wahl: xxxxxx“ (die ersten sechs
Zeichen der Prüfsumme der Wahl-Datei, ohne Koordinaten). Damit lässt sich
die Antwort des Menschen an genau diese Wahl binden (``ki_lauf.py``).

Rückgabe: 0 Wahl geschrieben; 2 die KI nennt keinen geeigneten Ausgang oder
die Vermessung spricht gegen die Wahl; 3 keine gültige Antwort (auch nach
Strg+C oder ``kill -INT``: Das Protokoll wird geschrieben, eine Wahl nicht);
4 Blickrunde, ihre Lage in der Karte oder eine wählbare Öffnung fehlt;
5 KI-Rechner nicht erreichbar; 6 ROS-Umgebung fehlt (mit ``--ueber-ros``,
geprüft vor dem Aufbereiten).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import time
from pathlib import Path
from typing import List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from lotse import SCHEMA_VERSION  # noqa: E402
from lotse.ablauf import befrage, bereite_vor  # noqa: E402
from lotse.blickrunde import Blickrunde, runden_finden  # noqa: E402
from lotse.ki_rechner import STANDARD_URL, modelle  # noqa: E402
from lotse.wahl import (ARTEN_TEXT, standpunkt_in_der_karte, wahl_aufschreiben,  # noqa: E402
                        wahl_satz)
from ros_ende import Ende, ros_beenden, ros_starten  # noqa: E402

VORGABE_RUNDEN = Path.home() / '.local/share/amadeus/ki_erkundung/blickrunden'
VORGABE_AUSGABE = Path.home() / '.local/share/amadeus/ki_erkundung/wahl'

RC_WAHL, RC_KEINE_WAHL, RC_KEINE_ANTWORT, RC_RUNDE, RC_KI_RECHNER = 0, 2, 3, 4, 5
RC_UMGEBUNG = 6


def kennung_der_wahl(pfad: Path) -> str:
    """Die ersten sechs Zeichen der SHA-256-Prüfsumme der Wahl-Datei."""
    return hashlib.sha256(Path(pfad).read_bytes()).hexdigest()[:6]


def ros_umgebung_fehlt() -> Optional[str]:
    """Grund, wenn rclpy oder std_msgs nicht zu laden sind; sonst None."""
    try:
        import rclpy  # noqa: F401
        from std_msgs.msg import String  # noqa: F401
    except ImportError as fehler:
        return str(fehler)
    return None


def im_repository(pfad: Path) -> bool:
    """Liegt ``pfad`` in einem Git-Arbeitsverzeichnis? Dort gehören keine Koordinaten hin."""
    pfad = Path(pfad).expanduser().resolve()
    return any((eltern / '.git').exists() for eltern in [pfad, *pfad.parents])


def neueste_runde(wurzel, name: Optional[str] = None) -> Optional[Path]:
    """Die zuletzt fertig geschriebene Blickrunde (nach der Zeit ihrer meta.json)."""
    ordner = [p for p in runden_finden(wurzel)
              if name is None or p.name.startswith(name)]
    return max(ordner, key=lambda p: (p / 'meta.json').stat().st_mtime, default=None)


def _komma(wert: float, stellen: int) -> str:
    return f'{wert:.{stellen}f}'.replace('.', ',')


def richtung_text(grad: float) -> str:
    if abs(grad) < 3.0:
        return 'geradeaus'
    return f'{abs(grad):.0f}° {"links" if grad > 0 else "rechts"}'


def zeilen_der_nummern(vorbereitung, pruefung: Optional[dict]) -> List[str]:
    """Jede angebotene Nummer: Maße vom Roboter aus und was die KI darin sieht."""
    arten = (pruefung or {}).get('arten') or {}
    sicherheit = (pruefung or {}).get('sicherheit') or {}
    gewaehlt = (pruefung or {}).get('wahl')
    gier_ende = vorbereitung.gier_ende_rad or 0.0
    zeilen = []
    for o in vorbereitung.oeffnungen:
        if o.nr not in vorbereitung.frage.angeboten:
            continue
        jetzt = math.degrees(math.atan2(math.sin(math.radians(o.richtung_grad) - gier_ende),
                                        math.cos(math.radians(o.richtung_grad) - gier_ende)))
        art = arten.get(str(o.nr))
        ki = ('–' if art is None else ARTEN_TEXT.get(art, art)
              + ('' if sicherheit.get(str(o.nr)) is None
                 else f' (sicher zu {round(100 * float(sicherheit[str(o.nr)])):d} %)'))
        zeilen.append(f'  Nr. {o.nr}: {_komma(o.breite_m, 2)} m breit, '
                      f'{_komma(o.entfernung_m, 1)} m entfernt, {richtung_text(jetzt)}; '
                      f'KI: {ki}' + ('  ← gewählt' if gewaehlt == o.nr else ''))
    return zeilen


def kurz(eintrag: dict) -> str:
    """Eine Antwort der KI in einer Zeile (wie im Trockenlauf)."""
    if eintrag.get('fehler'):
        meldung = (eintrag.get('meta') or {}).get('meldung')
        return f'keine Antwort ({eintrag["fehler"]}' + (f': {meldung}' if meldung else '') + ')'
    p = eintrag.get('pruefung') or {}
    if not p.get('gueltig'):
        return f'verworfen {p.get("fehler")}'
    return (f'Wahl {p.get("wahl")}'
            + (f', Vermessung dagegen: {eintrag["nachmessen"]}' if eintrag.get('nachmessen')
               else ''))


def eingabe() -> argparse.ArgumentParser:
    e = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    e.add_argument('--runde', help='diese Blickrunde (Ordner); sonst die neueste')
    e.add_argument('--runden', default=str(VORGABE_RUNDEN),
                   help='Ordner der Blickrunden, aus dem die neueste genommen wird')
    e.add_argument('--name', help='nur Blickrunden, deren Ordner so beginnt')
    e.add_argument('--max-alter', type=float, default=600.0,
                   help='so alt darf die Blickrunde höchstens sein, s (sonst gehört '
                        'sie nicht zu dieser Mission)')
    e.add_argument('--ausgabe', default=str(VORGABE_AUSGABE),
                   help='Ordner für Wahl-Datei und Protokoll (auf dem Roboter)')
    e.add_argument('--ueber-ros', action='store_true',
                   help='über den Lotsen-Dienst auf dem KI-Rechner fragen (vom Roboter '
                        'aus); das Modell bestimmt der Dienst')
    e.add_argument('--url', default=STANDARD_URL,
                   help='ohne --ueber-ros: Adresse des Ollama-Dienstes (Prüfung, Tests)')
    e.add_argument('--modell', help='ohne --ueber-ros: Modellname in Ollama')
    e.add_argument('--zeitgrenze', type=float, default=120.0, help='Sekunden je Antwort')
    e.add_argument('--versuche', type=int, default=2,
                   help='so oft fragen, bis eine gültige Antwort da ist')
    e.add_argument('--denken', choices=('an', 'aus'), default='aus',
                   help='Denkschalter des Modells (wie in KI-1: aus)')
    e.add_argument('--kontext', type=int, default=8192, help='Kontextlänge (num_ctx)')
    e.add_argument('--bilder', type=int, default=8, help='Anzahl Fotos')
    e.add_argument('--karten-rahmen', default='map')
    return e


def main(argv=None) -> int:
    for strom in (sys.stdout, sys.stderr):
        if hasattr(strom, 'reconfigure'):
            strom.reconfigure(line_buffering=True)
    wahl = eingabe().parse_args(argv)
    if wahl.ueber_ros and wahl.modell:
        eingabe().error('mit --ueber-ros bestimmt der Lotsen-Dienst das Modell')
    if not wahl.ueber_ros and not wahl.modell:
        eingabe().error('--ueber-ros oder --modell angeben')
    if not 1 <= wahl.versuche <= 3:
        eingabe().error('--versuche: 1 bis 3')
    if wahl.ueber_ros:
        # Zuerst: Fehlt die ROS-Umgebung, gleich sagen – nicht erst nach dem
        # Aufbereiten der Runde (KI-F9, Lauf 2w3: Fehler nach 8 s).
        grund = ros_umgebung_fehlt()
        if grund is not None:
            print(f'ROS-Umgebung fehlt ({grund}). Über ki_lauf.py aufrufen oder vorher die '
                  'Umgebung der Kamera sourcen (zum Beispiel source '
                  '~/ki_trockenlauf_ki0/umgebung_we1.bash).')
            return RC_UMGEBUNG
    # Ein Signal setzt nur eine Marke (ros_ende); danach wird nicht weiter gefragt.
    ende = Ende().anmelden()
    try:
        return _waehle(wahl, ende)
    finally:
        ende.abmelden()


def _waehle(wahl, ende: Ende) -> int:
    ausgabe = Path(wahl.ausgabe).expanduser()
    if im_repository(ausgabe):
        print(f'{ausgabe} liegt in einem Git-Arbeitsverzeichnis; die Wahl-Datei enthält '
              'Koordinaten der Wohnung und bleibt außerhalb.', file=sys.stderr)
        return RC_RUNDE

    # ---- Blickrunde ------------------------------------------------------
    pfad = Path(wahl.runde).expanduser() if wahl.runde else neueste_runde(
        Path(wahl.runden).expanduser(), wahl.name)
    if pfad is None or not (pfad / 'meta.json').is_file():
        print('Keine Blickrunde gefunden; die KI kann nichts wählen.')
        return RC_RUNDE
    alter = time.time() - (pfad / 'meta.json').stat().st_mtime
    if alter > wahl.max_alter:
        print(f'Die Blickrunde {pfad.name} ist {alter:.0f} s alt (höchstens '
              f'{wahl.max_alter:.0f} s); sie gehört nicht zu dieser Mission.')
        return RC_RUNDE
    try:
        runde = Blickrunde.lade(pfad)
    except (ValueError, OSError, KeyError) as fehler:
        print(f'Blickrunde {pfad.name} nicht lesbar: {fehler}')
        return RC_RUNDE
    if not runde.karte:
        print(f'Blickrunde {runde.name}: Die Lage in der Karte fehlt (TF bei der Aufnahme); '
              'eine Wahl ließe sich nicht an den Fahrteil übergeben. Die KI wird nicht '
              'gefragt.')
        return RC_RUNDE
    beginn = time.monotonic()
    try:
        vorbereitung = bereite_vor(runde, wahl.bilder)
    except (ValueError, OSError, KeyError) as fehler:
        print(f'Blickrunde {runde.name} nicht aufzubereiten: {fehler}')
        return RC_RUNDE
    standpunkt = standpunkt_in_der_karte(runde.karte, vorbereitung.gier_ende_rad,
                                         wahl.karten_rahmen)
    print(f'Blickrunde {runde.name}: gedreht {vorbereitung.auswahl["gedreht_grad"]}°, '
          f'{len(vorbereitung.auswahl["bilder"])} Bilder, {len(vorbereitung.oeffnungen)} '
          f'Öffnung(en) vermessen, angeboten {vorbereitung.frage.angeboten}; '
          f'aufbereitet in {_komma(time.monotonic() - beginn, 1)} s.')
    if standpunkt is None:
        print(f'Die Lage in der Karte passt nicht (Rahmen {wahl.karten_rahmen!r} erwartet); '
              'die KI wird nicht gefragt.')
        return RC_RUNDE
    if not vorbereitung.frage.angeboten:
        print('Keine Öffnung vermessen, die die KI wählen könnte; sie wird nicht gefragt.')
        return RC_RUNDE

    # ---- KI-Rechner ------------------------------------------------------
    verbindung, weg, modell = None, None, wahl.modell
    eigener_kontext = False
    denken = {'an': True, 'aus': False}[wahl.denken]
    antworten: List[dict] = []
    try:
        if wahl.ueber_ros:
            from ki_verbindung_ros import Verbindung
            eigener_kontext = ros_starten()
            verbindung = Verbindung(abbruch=ende.gesetzt)
            status = verbindung.status(warten_s=8.0)
            if ende.gesetzt():
                print(f'Abgebrochen ({ende.signal}); die KI wird nicht gefragt.')
                return RC_KEINE_ANTWORT
            if not status or not status.get('bereit'):
                print('Der Lotsen-Dienst auf dem KI-Rechner ist nicht zu hören oder nicht '
                      f'bereit (Status: {status}).')
                return RC_KI_RECHNER
            modell, weg = str(status.get('modell')), verbindung.frage_stellen
        else:
            vorhanden = modelle(wahl.url)
            if vorhanden is None:
                print(f'Der KI-Rechner antwortet nicht unter {wahl.url}.')
                return RC_KI_RECHNER
            if modell not in vorhanden and f'{modell}:latest' not in vorhanden:
                print(f'Das Modell {modell} ist dort nicht vorhanden: {vorhanden}.')
                return RC_KI_RECHNER

        for versuch in range(wahl.versuche):
            if ende.gesetzt():
                break
            eintrag = befrage(vorbereitung, modell, url=wahl.url, zeitgrenze_s=wahl.zeitgrenze,
                              wiederholung=versuch, optionen={'num_ctx': wahl.kontext},
                              denken=denken, weg=weg)
            antworten.append(eintrag)
            print(f'Frage {versuch + 1} an {modell}: {kurz(eintrag)}, '
                  f'{_komma(float(eintrag.get("dauer_s") or 0.0), 1)} s')
            if not eintrag.get('fehler') and (eintrag.get('pruefung') or {}).get('gueltig'):
                break
    finally:
        if verbindung is not None:
            verbindung.schliessen()
        if wahl.ueber_ros:
            ros_beenden(eigener_kontext=eigener_kontext)

    # ---- Ergebnis --------------------------------------------------------
    if ende.gesetzt():
        print(f'Abgebrochen ({ende.signal}); es wird keine Wahl geschrieben.')
        # Die echten Antworten bleiben im Protokoll; der Vermerk kommt dazu.
        antworten.append({'fehler': 'abgebrochen', 'pruefung': None, 'dauer_s': 0.0})
    letzte = antworten[-1]
    jetzt = time.time()
    stempel = time.strftime('%Y%m%d_%H%M%S', time.localtime(jetzt))
    ausgabe.mkdir(parents=True, exist_ok=True)
    protokoll = {'schema_version': SCHEMA_VERSION, 'erzeugt_unix': round(jetzt, 1),
                 'runde': runde.name, 'modell': modell, 'ueber_ros': wahl.ueber_ros,
                 'vorbereitung': vorbereitung.als_dict(), 'antworten': antworten}
    try:
        daten = wahl_aufschreiben(vorbereitung, letzte, standpunkt, jetzt_s=jetzt,
                                  rahmen=wahl.karten_rahmen)
    except ValueError as grund:
        daten, ablehnung = None, str(grund)
    else:
        ablehnung = None
    protokoll['wahl'] = daten
    protokoll['ablehnung'] = ablehnung
    protokoll_pfad = ausgabe / f'{runde.name}_{stempel}_protokoll.json'
    with open(protokoll_pfad, 'w', encoding='utf-8') as datei:
        json.dump(protokoll, datei, indent=1, ensure_ascii=False)

    pruefung = letzte.get('pruefung') if not letzte.get('fehler') else None
    if pruefung and pruefung.get('gueltig'):
        print('Was die KI in den Nummern sieht (Richtung von seiner jetzigen Blickrichtung):')
        for zeile in zeilen_der_nummern(vorbereitung, pruefung):
            print(zeile)
        if pruefung.get('raum'):
            print(f'Raum laut KI: {pruefung["raum"]}')
        if pruefung.get('begruendung'):
            print(f'Begründung der KI: {pruefung["begruendung"]}')
        if pruefung.get('gefahren'):
            print(f'Gefahren laut KI: {", ".join(map(str, pruefung["gefahren"]))}')
    print(f'Protokoll: {protokoll_pfad}')
    if daten is None:
        print(f'Keine Wahl: {ablehnung}.')
        if letzte.get('fehler') == 'lotse_nicht_erreichbar':
            return RC_KI_RECHNER
        if letzte.get('fehler') or not (pruefung or {}).get('gueltig'):
            return RC_KEINE_ANTWORT
        return RC_KEINE_WAHL
    wahl_pfad = ausgabe / f'{runde.name}_{stempel}_wahl.json'
    with open(wahl_pfad, 'w', encoding='utf-8') as datei:
        json.dump(daten, datei, indent=1, ensure_ascii=False)
    print(wahl_satz(daten))
    print(f'Wahl-Datei: {wahl_pfad}')
    print(f'Kennung der Wahl: {kennung_der_wahl(wahl_pfad)}')
    print('Gefahren wird erst nach einem Ja des Menschen: fahrziel_senden.py --zur-tuer '
          '--wahl DATEI; bei Nein: fahrziel_senden.py --ende --quelle mensch.')
    return RC_WAHL


if __name__ == '__main__':
    sys.exit(main())
