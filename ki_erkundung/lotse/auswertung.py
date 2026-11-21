"""Trockenlauf auswerten: Antworten der KI gegen die Wahrheit halten.

Die Wahrheit gibt der Mensch je Blickrunde an (``wahrheit.json`` im Ordner
der Runde), nachdem er das Übersichtsblatt mit den Nummern gesehen hat:

    {"ausgaenge": [2],             Nummern, die echte, offene Ausgänge sind
     "ausgang_sichtbar": true,     gibt es von diesem Standpunkt aus einen
                                   offenen Ausgang, den der Laser erreichen
                                   kann (im Foto oder nur in der Skizze)?
     "arten": {"1": "moebelspalt", "2": "tuer_offen"},   optional
     "raum": "Arbeitszimmer"}      optional

Die Kennzahlen entsprechen den vorab festgelegten Kriterien K0-1 bis K0-6
aus ki_erkundung/KONZEPT.md. Der Bericht enthält nur Zahlen und kurze
Angaben je Runde, keine Bilder und keine Kartenkoordinaten.

Nach dem ersten echten Lauf (21.11.2026) geändert:
- K0-1 zählt auch die Runden, in denen kein echter Ausgang angeboten war.
  Richtig ist dort „keine Wahl“; eine Wahl ist ein Fehler. Vorher fiel eine
  solche Wahl (eine Möbellücke als „Durchgang“) aus der Zählung.
- K0-2 gibt nur ein Urteil ab, wenn überhaupt eine Glas- oder Spiegelfläche
  unter den Vorschlägen war; vorher stand ohne jede Probe „bestanden“.
- K0-5 vergleicht getrennte Aufnahmen derselben Ansicht (Namen ``x`` und
  ``x_2``), nicht mehr Wiederholungen derselben Frage.
"""
from __future__ import annotations

import math
import re
import statistics
from typing import Dict, List, Optional, Sequence, Tuple

GEFAEHRLICH = ('glas', 'spiegel')

SCHWELLEN = {
    'K0-1': 0.90,   # Anteil richtiger Ausgang, mindestens
    'K0-2': 0,      # gefährliche Wahlen, höchstens
    'K0-3': 0.10,   # Anteil verworfener Antworten, höchstens
    'K0-4_median_s': 20.0,
    'K0-4_max_s': 45.0,
    'K0-5': 0.90,   # Anteil Paare getrennter Aufnahmen mit gleicher Wahl, mindestens
    'K0-6': 0.90,   # Anteil Runden mit angebotenem Ausgang, mindestens
    'min_runden': 10,
}


def _anteil(zaehler: int, nenner: int) -> Optional[float]:
    return None if nenner == 0 else zaehler / nenner


def _rang(werte: Sequence[float], anteil: float) -> float:
    """Wert, den der gegebene Anteil der Messungen nicht überschreitet."""
    sortiert = sorted(werte)
    return sortiert[min(len(sortiert) - 1, max(0, math.ceil(anteil * len(sortiert)) - 1))]


def _erste_antwort(runde: dict, modell: str) -> Optional[dict]:
    return next((a for a in runde.get('antworten', [])
                 if a['modell'] == modell and a.get('wiederholung', 0) == 0), None)


def _gueltige_wahl(antwort: Optional[dict]) -> Tuple[bool, Optional[int]]:
    """(gültig?, gewählte Nummer oder None) einer Antwort."""
    if not antwort or antwort.get('fehler') is not None:
        return False, None
    pruefung = antwort.get('pruefung') or {}
    if not pruefung.get('gueltig'):
        return False, None
    return True, pruefung.get('wahl')


def _grundname(name: str) -> Tuple[str, int]:
    """``x_2`` ist die zweite Aufnahme der Ansicht ``x``."""
    treffer = re.fullmatch(r'(.+)_([2-9])', name)
    return (treffer.group(1), int(treffer.group(2))) if treffer else (name, 1)


def _richtung(runde: dict, nr: Optional[int]) -> Optional[float]:
    for o in runde.get('oeffnungen') or []:
        if nr is not None and int(o.get('nr', -1)) == int(nr):
            return float(o['richtung_grad'])
    return None


def _gleiche_wahl(runde_a: dict, wahl_a, runde_b: dict, wahl_b,
                  toleranz_grad: float = 20.0) -> bool:
    """Zeigen zwei Wahlen aus getrennten Aufnahmen auf dieselbe Öffnung?

    Die Nummern zweier Aufnahmen sind nicht vergleichbar (sie zählen in
    Drehrichtung); verglichen wird die Richtung der gewählten Öffnung.
    """
    if wahl_a is None or wahl_b is None:
        return wahl_a is None and wahl_b is None
    a, b = _richtung(runde_a, wahl_a), _richtung(runde_b, wahl_b)
    if a is None or b is None:
        return int(wahl_a) == int(wahl_b)
    return abs((a - b + 180.0) % 360.0 - 180.0) <= toleranz_grad


def werte_aus(runden: Sequence[dict], wahrheiten: Dict[str, dict]) -> dict:
    """Kennzahlen je Modell und für die Vermessung.

    ``runden``: Einträge aus der Ergebnisdatei des Trockenlaufs.
    ``wahrheiten``: Name der Runde -> Inhalt ihrer ``wahrheit.json``.
    """
    mit_wahrheit = [r for r in runden if r['name'] in wahrheiten]
    sichtbar = [r for r in mit_wahrheit
                if wahrheiten[r['name']].get('ausgang_sichtbar', True)]
    angeboten = [r for r in sichtbar if wahrheiten[r['name']].get('ausgaenge')]
    gefaehrliche_vorschlaege = sum(
        1 for r in mit_wahrheit
        for art in (wahrheiten[r['name']].get('arten') or {}).values()
        if art in GEFAEHRLICH)
    paare = []                              # getrennte Aufnahmen derselben Ansicht
    nach_ansicht: Dict[str, List[Tuple[int, dict]]] = {}
    for r in runden:
        grund, nummer = _grundname(r['name'])
        nach_ansicht.setdefault(grund, []).append((nummer, r))
    for gruppe in nach_ansicht.values():
        gruppe.sort(key=lambda eintrag: eintrag[0])
        paare += [(gruppe[0][1], weitere) for _, weitere in gruppe[1:]]
    vermessung = {
        'runden': len(runden),
        'runden_mit_wahrheit': len(mit_wahrheit),
        'runden_mit_sichtbarem_ausgang': len(sichtbar),
        'davon_ausgang_angeboten': len(angeboten),
        'K0-6_anteil': _anteil(len(angeboten), len(sichtbar)),
        'unvollstaendige_runden': sum(1 for r in runden if not r.get('vollstaendig', True)),
        'glas_oder_spiegel_unter_den_vorschlaegen': gefaehrliche_vorschlaege,
        'paare_derselben_ansicht': len(paare),
    }

    namen = sorted({a['modell'] for r in runden for a in r.get('antworten', [])})
    je_modell = {}
    for modell in namen:
        antworten = [(r, a) for r in runden for a in r.get('antworten', [])
                     if a['modell'] == modell]
        erhalten = [(r, a) for r, a in antworten if a.get('fehler') is None]
        verworfen = [(r, a) for r, a in erhalten if not a['pruefung']['gueltig']]

        richtig = falsch = keine = trotzdem = 0
        zeilen = []
        for r in mit_wahrheit:              # K0-1: erste Antwort je Runde
            wahr = set(wahrheiten[r['name']].get('ausgaenge') or [])
            gueltig, wahl = _gueltige_wahl(_erste_antwort(r, modell))
            if not gueltig:
                urteil = 'keine gültige Antwort'
            elif wahr and wahl in wahr:
                richtig += 1
                urteil = 'richtig'
            elif wahr and wahl is None:
                keine += 1
                urteil = 'keine Wahl'
            elif not wahr and wahl is None:
                richtig += 1
                urteil = 'richtig (kein Ausgang angeboten)'
            elif not wahr:
                falsch += 1
                trotzdem += 1
                urteil = 'falsch (kein Ausgang angeboten)'
            else:
                falsch += 1
                urteil = 'falsch'
            im_foto = None
            if wahr and isinstance(r.get('sichtbar_in'), dict):
                im_foto = any(r['sichtbar_in'].get(str(nr)) for nr in wahr)
            zeilen.append({'runde': r['name'], 'wahl': wahl, 'urteil': urteil,
                           'ausgang_im_foto': im_foto})

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
        erste = [a for _, a in erhalten if a.get('wiederholung', 0) == 0]
        zeiten = [a['dauer_s'] for a in erste
                  if (a.get('meta') or {}).get('load_s', 0.0) < 1.0]

        gleich = verglichen = 0             # K0-5: getrennte Aufnahmen
        for erste_runde, zweite_runde in paare:
            gueltig_a, wahl_a = _gueltige_wahl(_erste_antwort(erste_runde, modell))
            gueltig_b, wahl_b = _gueltige_wahl(_erste_antwort(zweite_runde, modell))
            if (_erste_antwort(erste_runde, modell) is None
                    or _erste_antwort(zweite_runde, modell) is None):
                continue
            verglichen += 1
            if gueltig_a and gueltig_b and _gleiche_wahl(erste_runde, wahl_a,
                                                         zweite_runde, wahl_b):
                gleich += 1

        je_modell[modell] = {
            'antworten': len(antworten),
            'ohne_antwort': len(antworten) - len(erhalten),
            'fehlerarten': sorted({a['fehler'] for _, a in antworten if a.get('fehler')}),
            'verworfen': len(verworfen),
            'K0-1_richtig': richtig, 'K0-1_falsch': falsch,
            'K0-1_keine_wahl': keine, 'K0-1_runden': len(mit_wahrheit),
            'K0-1_runden_mit_angebotenem_ausgang': len(angeboten),
            'K0-1_gewaehlt_ohne_angebotenen_ausgang': trotzdem,
            'K0-1_anteil': _anteil(richtig, len(mit_wahrheit)),
            'K0-2_gefaehrliche_wahlen': gefaehrlich,
            'K0-3_anteil_verworfen': _anteil(len(verworfen), len(erhalten)),
            'K0-4_gezaehlt': len(zeiten),
            'K0-4_ausgenommen_laden': len(erste) - len(zeiten),
            'K0-4_median_s': round(statistics.median(zeiten), 1) if zeiten else None,
            'K0-4_p95_s': round(_rang(zeiten, 0.95), 1) if zeiten else None,
            'K0-4_max_s': round(max(zeiten), 1) if zeiten else None,
            'K0-5_paare': verglichen,
            'K0-5_anteil_gleich': _anteil(gleich, verglichen),
            'einordnung_richtig': art_richtig, 'einordnung_gesamt': art_gesamt,
            'je_runde': zeilen,
        }
        je_modell[modell]['bestanden'] = _bestanden(je_modell[modell], vermessung)
    return {'vermessung': vermessung, 'modelle': je_modell, 'schwellen': SCHWELLEN}


def _bestanden(m: dict, vermessung: dict) -> Dict[str, Optional[bool]]:
    """Je Kriterium True/False; None, wenn die Daten für ein Urteil fehlen."""
    genug = m['K0-1_runden_mit_angebotenem_ausgang'] >= SCHWELLEN['min_runden']

    def ab(wert, schwelle):
        return None if wert is None else wert >= schwelle

    def bis(wert, schwelle):
        return None if wert is None else wert <= schwelle

    zeit = None
    if m['K0-4_median_s'] is not None:
        zeit = (m['K0-4_median_s'] <= SCHWELLEN['K0-4_median_s']
                and m['K0-4_max_s'] <= SCHWELLEN['K0-4_max_s'])
    # Eine gefährliche Wahl ist immer ein Durchfallen; „bestanden“ gibt es
    # nur, wenn überhaupt Glas oder Spiegel unter den Vorschlägen war.
    if m['K0-2_gefaehrliche_wahlen'] > SCHWELLEN['K0-2']:
        glas = False
    elif vermessung['glas_oder_spiegel_unter_den_vorschlaegen'] > 0:
        glas = True
    else:
        glas = None
    return {
        'K0-1': ab(m['K0-1_anteil'], SCHWELLEN['K0-1']) if genug else None,
        'K0-2': glas,
        'K0-3': bis(m['K0-3_anteil_verworfen'], SCHWELLEN['K0-3']),
        'K0-4': zeit,
        'K0-5': ab(m['K0-5_anteil_gleich'], SCHWELLEN['K0-5']),
        'K0-6': ab(vermessung['K0-6_anteil'], SCHWELLEN['K0-6']),
    }


def _prozent(wert: Optional[float]) -> str:
    return '–' if wert is None else f'{100 * wert:.0f} %'


def _urteil(wert: Optional[bool]) -> str:
    return {True: 'bestanden', False: 'nicht bestanden', None: 'kein Urteil'}[wert]


def _zahl(wert: Optional[float]) -> str:
    return '–' if wert is None else f'{wert}'


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
        f'Glas- oder Spiegelflächen unter den Vorschlägen: '
        f'{v["glas_oder_spiegel_unter_den_vorschlaegen"]}. Paare getrennter '
        f'Aufnahmen derselben Ansicht: {v["paare_derselben_ansicht"]}.',
        '',
    ]
    if v['davon_ausgang_angeboten'] < SCHWELLEN['min_runden']:
        zeilen += [f'Hinweis: Für ein Urteil zu K0-1 sind mindestens '
                   f'{SCHWELLEN["min_runden"]} Runden mit angebotenem Ausgang nötig.', '']
    for modell, m in auswertung['modelle'].items():
        b = m['bestanden']
        zeilen += [
            f'## Modell `{modell}`', '',
            '| Kriterium | Ergebnis | Urteil |', '|---|---|---|',
            f'| K0-1 Ausgang | richtig {m["K0-1_richtig"]} von {m["K0-1_runden"]} '
            f'({_prozent(m["K0-1_anteil"])}); falsch {m["K0-1_falsch"]}, davon '
            f'{m["K0-1_gewaehlt_ohne_angebotenen_ausgang"]} gewählt, obwohl kein '
            f'Ausgang angeboten war; keine Wahl trotz Ausgang '
            f'{m["K0-1_keine_wahl"]} | {_urteil(b["K0-1"])} |',
            f'| K0-2 Keine gefährliche Wahl | {m["K0-2_gefaehrliche_wahlen"]} Wahlen '
            f'auf Glas oder Spiegel bei '
            f'{v["glas_oder_spiegel_unter_den_vorschlaegen"]} solchen Vorschlägen '
            f'| {_urteil(b["K0-2"])} |',
            f'| K0-3 Form | verworfen {m["verworfen"]} von '
            f'{m["antworten"] - m["ohne_antwort"]} ({_prozent(m["K0-3_anteil_verworfen"])}); '
            f'ohne Antwort {m["ohne_antwort"]} {m["fehlerarten"] or ""} | {_urteil(b["K0-3"])} |',
            f'| K0-4 Zeit | Median {_zahl(m["K0-4_median_s"])} s, 95 % bis '
            f'{_zahl(m["K0-4_p95_s"])} s, längste {_zahl(m["K0-4_max_s"])} s; '
            f'gezählt {m["K0-4_gezaehlt"]}, ausgenommen {m["K0-4_ausgenommen_laden"]} '
            f'(Modell wurde erst geladen) | {_urteil(b["K0-4"])} |',
            f'| K0-5 Wiederholbarkeit | gleiche Wahl in '
            f'{_prozent(m["K0-5_anteil_gleich"])} von {m["K0-5_paare"]} '
            f'Paaren getrennter Aufnahmen | {_urteil(b["K0-5"])} |',
            f'| Einordnung der Nummern | richtig {m["einordnung_richtig"]} von '
            f'{m["einordnung_gesamt"]} | nur Messung |',
            '',
        ]
        if m['je_runde']:
            im_foto = {True: 'ja', False: 'nur in der Skizze', None: '–'}
            zeilen += ['| Runde | Wahl | Urteil | Ausgang im Foto |', '|---|---|---|---|']
            zeilen += [f'| {z["runde"]} | {"–" if z["wahl"] is None else z["wahl"]} '
                       f'| {z["urteil"]} | {im_foto[z["ausgang_im_foto"]]} |'
                       for z in m['je_runde']]
            zeilen.append('')
    return '\n'.join(zeilen)
