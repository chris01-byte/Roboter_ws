"""Trockenlauf auswerten: Antworten der KI gegen die Wahrheit halten.

Die Wahrheit gibt der Mensch je Blickrunde an (``wahrheit.json`` im Ordner
der Runde), nachdem er das Übersichtsblatt mit den Nummern gesehen hat:

    {"ausgaenge": [2],             Nummern, die echte, offene Ausgänge sind
     "ausgang_sichtbar": true,     war überhaupt ein Ausgang zu sehen?
     "arten": {"1": "moebelspalt", "2": "tuer_offen"},   optional
     "raum": "Arbeitszimmer"}      optional

Die Kennzahlen entsprechen den vorab festgelegten Kriterien K0-1 bis K0-6
aus ki_erkundung/KONZEPT.md. Der Bericht enthält nur Zahlen und kurze
Angaben je Runde, keine Bilder und keine Kartenkoordinaten.
"""
from __future__ import annotations

import math
import statistics
from typing import Dict, List, Optional, Sequence

GEFAEHRLICH = ('glas', 'spiegel')

SCHWELLEN = {
    'K0-1': 0.90,   # Anteil richtiger Ausgang, mindestens
    'K0-2': 0,      # gefährliche Wahlen, höchstens
    'K0-3': 0.10,   # Anteil verworfener Antworten, höchstens
    'K0-4_median_s': 20.0,
    'K0-4_max_s': 45.0,
    'K0-5': 0.90,   # Anteil Runden mit gleicher Wahl, mindestens
    'K0-6': 0.90,   # Anteil Runden mit angebotenem Ausgang, mindestens
    'min_runden': 10,
}


def _anteil(zaehler: int, nenner: int) -> Optional[float]:
    return None if nenner == 0 else zaehler / nenner


def _rang(werte: Sequence[float], anteil: float) -> float:
    """Wert, den der gegebene Anteil der Messungen nicht überschreitet."""
    sortiert = sorted(werte)
    return sortiert[min(len(sortiert) - 1, max(0, math.ceil(anteil * len(sortiert)) - 1))]


def werte_aus(runden: Sequence[dict], wahrheiten: Dict[str, dict]) -> dict:
    """Kennzahlen je Modell und für die Vermessung.

    ``runden``: Einträge aus der Ergebnisdatei des Trockenlaufs.
    ``wahrheiten``: Name der Runde -> Inhalt ihrer ``wahrheit.json``.
    """
    mit_wahrheit = [r for r in runden if r['name'] in wahrheiten]
    sichtbar = [r for r in mit_wahrheit
                if wahrheiten[r['name']].get('ausgang_sichtbar', True)]
    angeboten = [r for r in sichtbar if wahrheiten[r['name']].get('ausgaenge')]
    vermessung = {
        'runden': len(runden),
        'runden_mit_wahrheit': len(mit_wahrheit),
        'runden_mit_sichtbarem_ausgang': len(sichtbar),
        'davon_ausgang_angeboten': len(angeboten),
        'K0-6_anteil': _anteil(len(angeboten), len(sichtbar)),
        'unvollstaendige_runden': sum(1 for r in runden if not r.get('vollstaendig', True)),
    }

    namen = sorted({a['modell'] for r in runden for a in r.get('antworten', [])})
    je_modell = {}
    for modell in namen:
        antworten = [(r, a) for r in runden for a in r.get('antworten', [])
                     if a['modell'] == modell]
        erhalten = [(r, a) for r, a in antworten if a.get('fehler') is None]
        verworfen = [(r, a) for r, a in erhalten if not a['pruefung']['gueltig']]

        richtig = falsch = keine = 0
        zeilen = []
        for r in angeboten:                 # K0-1: erste Antwort je Runde
            erste = next((a for a in r.get('antworten', [])
                          if a['modell'] == modell and a.get('wiederholung', 0) == 0), None)
            wahr = set(wahrheiten[r['name']]['ausgaenge'])
            wahl = (erste or {}).get('pruefung', {}).get('wahl') if erste else None
            gueltig = bool(erste and erste.get('fehler') is None
                           and erste['pruefung']['gueltig'])
            if gueltig and wahl in wahr:
                richtig += 1
                urteil = 'richtig'
            elif gueltig and wahl is None:
                keine += 1
                urteil = 'keine Wahl'
            elif gueltig:
                falsch += 1
                urteil = 'falsch'
            else:
                urteil = 'keine gültige Antwort'
            zeilen.append({'runde': r['name'], 'wahl': wahl, 'urteil': urteil})

        gefaehrlich = 0                     # K0-2: alle Antworten
        art_richtig = art_gesamt = 0
        for r, a in erhalten:
            wahr = wahrheiten.get(r['name'])
            if not wahr or not a['pruefung']['gueltig']:
                continue
            arten = {int(k): v for k, v in (wahr.get('arten') or {}).items()}
            wahl = a['pruefung'].get('wahl')
            if wahl is not None and arten.get(int(wahl)) in GEFAEHRLICH:
                gefaehrlich += 1
            for nr, art in arten.items():
                art_gesamt += 1
                if a['pruefung']['arten'].get(str(nr)) == art:
                    art_richtig += 1

        # K0-4: nur die erste Antwort je Frage und nur bei geladenem Modell.
        # Wiederholungen derselben Frage kommen aus dem Zwischenspeicher des
        # Dienstes (erster echter Lauf 19.11.2026: 37 s, dann 1,3 s und 1,3 s)
        # und würden die Zeit schönen.
        zeiten = [a['dauer_s'] for _, a in erhalten
                  if a.get('wiederholung', 0) == 0
                  and (a.get('meta') or {}).get('load_s', 0.0) < 1.0]
        gleich = mehrfach = 0               # K0-5
        for r in runden:
            eigene = [a for a in r.get('antworten', []) if a['modell'] == modell]
            if len(eigene) < 2:
                continue
            mehrfach += 1
            wahlen = {(a['pruefung'].get('wahl') if a.get('fehler') is None
                       and a['pruefung']['gueltig'] else 'ungueltig') for a in eigene}
            gleich += 1 if len(wahlen) == 1 and 'ungueltig' not in wahlen else 0

        je_modell[modell] = {
            'antworten': len(antworten),
            'ohne_antwort': len(antworten) - len(erhalten),
            'fehlerarten': sorted({a['fehler'] for _, a in antworten if a.get('fehler')}),
            'verworfen': len(verworfen),
            'K0-1_richtig': richtig, 'K0-1_falsch': falsch,
            'K0-1_keine_wahl': keine, 'K0-1_runden': len(angeboten),
            'K0-1_anteil': _anteil(richtig, len(angeboten)),
            'K0-2_gefaehrliche_wahlen': gefaehrlich,
            'K0-3_anteil_verworfen': _anteil(len(verworfen), len(erhalten)),
            'K0-4_median_s': round(statistics.median(zeiten), 1) if zeiten else None,
            'K0-4_p95_s': round(_rang(zeiten, 0.95), 1) if zeiten else None,
            'K0-4_max_s': round(max(zeiten), 1) if zeiten else None,
            'K0-5_runden_mit_wiederholung': mehrfach,
            'K0-5_anteil_gleich': _anteil(gleich, mehrfach),
            'einordnung_richtig': art_richtig, 'einordnung_gesamt': art_gesamt,
            'je_runde': zeilen,
        }
        je_modell[modell]['bestanden'] = _bestanden(je_modell[modell], vermessung)
    return {'vermessung': vermessung, 'modelle': je_modell, 'schwellen': SCHWELLEN}


def _bestanden(m: dict, vermessung: dict) -> Dict[str, Optional[bool]]:
    """Je Kriterium True/False; None, wenn die Daten für ein Urteil fehlen."""
    genug = m['K0-1_runden'] >= SCHWELLEN['min_runden']

    def ab(wert, schwelle):
        return None if wert is None else wert >= schwelle

    def bis(wert, schwelle):
        return None if wert is None else wert <= schwelle

    zeit = None
    if m['K0-4_median_s'] is not None:
        zeit = (m['K0-4_median_s'] <= SCHWELLEN['K0-4_median_s']
                and m['K0-4_max_s'] <= SCHWELLEN['K0-4_max_s'])
    return {
        'K0-1': ab(m['K0-1_anteil'], SCHWELLEN['K0-1']) if genug else None,
        'K0-2': (m['K0-2_gefaehrliche_wahlen'] <= SCHWELLEN['K0-2']
                 if vermessung['runden_mit_wahrheit'] else None),
        'K0-3': bis(m['K0-3_anteil_verworfen'], SCHWELLEN['K0-3']),
        'K0-4': zeit,
        'K0-5': ab(m['K0-5_anteil_gleich'], SCHWELLEN['K0-5']),
        'K0-6': ab(vermessung['K0-6_anteil'], SCHWELLEN['K0-6']),
    }


def _prozent(wert: Optional[float]) -> str:
    return '–' if wert is None else f'{100 * wert:.0f} %'


def _urteil(wert: Optional[bool]) -> str:
    return {True: 'bestanden', False: 'nicht bestanden', None: 'kein Urteil'}[wert]


def bericht(auswertung: dict) -> str:
    """Kurzbericht als Markdown (ohne Bilder, ohne Koordinaten)."""
    v = auswertung['vermessung']
    zeilen: List[str] = [
        '# Trockenlauf KI-0 – Auswertung', '',
        f'Blickrunden: {v["runden"]}, davon mit Wahrheit: '
        f'{v["runden_mit_wahrheit"]}, unvollständig gedreht: '
        f'{v["unvollstaendige_runden"]}.',
        f'K0-6 Vorschläge: In {v["davon_ausgang_angeboten"]} von '
        f'{v["runden_mit_sichtbarem_ausgang"]} Runden mit sichtbarem Ausgang '
        f'war er unter den vermessenen Vorschlägen ({_prozent(v["K0-6_anteil"])}).',
        '',
    ]
    if v['runden_mit_wahrheit'] < SCHWELLEN['min_runden']:
        zeilen += [f'Hinweis: Für ein Urteil zu K0-1 sind mindestens '
                   f'{SCHWELLEN["min_runden"]} Runden mit angebotenem Ausgang nötig.', '']
    for modell, m in auswertung['modelle'].items():
        b = m['bestanden']
        zeilen += [
            f'## Modell `{modell}`', '',
            '| Kriterium | Ergebnis | Urteil |', '|---|---|---|',
            f'| K0-1 Ausgang | richtig {m["K0-1_richtig"]} von {m["K0-1_runden"]} '
            f'({_prozent(m["K0-1_anteil"])}); falsch {m["K0-1_falsch"]}, keine Wahl '
            f'{m["K0-1_keine_wahl"]} | {_urteil(b["K0-1"])} |',
            f'| K0-2 Keine gefährliche Wahl | {m["K0-2_gefaehrliche_wahlen"]} Wahlen '
            f'auf Glas oder Spiegel | {_urteil(b["K0-2"])} |',
            f'| K0-3 Form | verworfen {m["verworfen"]} von '
            f'{m["antworten"] - m["ohne_antwort"]} ({_prozent(m["K0-3_anteil_verworfen"])}); '
            f'ohne Antwort {m["ohne_antwort"]} {m["fehlerarten"] or ""} | {_urteil(b["K0-3"])} |',
            f'| K0-4 Zeit | Median {m["K0-4_median_s"]} s, 95 % bis {m["K0-4_p95_s"]} s, '
            f'längste {m["K0-4_max_s"]} s | {_urteil(b["K0-4"])} |',
            f'| K0-5 Wiederholbarkeit | gleiche Wahl in '
            f'{_prozent(m["K0-5_anteil_gleich"])} von {m["K0-5_runden_mit_wiederholung"]} '
            f'Runden | {_urteil(b["K0-5"])} |',
            f'| Einordnung der Nummern | richtig {m["einordnung_richtig"]} von '
            f'{m["einordnung_gesamt"]} | nur Messung |',
            '',
        ]
        if m['je_runde']:
            zeilen += ['| Runde | Wahl | Urteil |', '|---|---|---|']
            zeilen += [f'| {z["runde"]} | {"–" if z["wahl"] is None else z["wahl"]} '
                       f'| {z["urteil"]} |' for z in m['je_runde']]
            zeilen.append('')
    return '\n'.join(zeilen)
