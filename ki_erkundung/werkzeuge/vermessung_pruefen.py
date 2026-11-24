#!/usr/bin/env python3
"""Vermessung prüfen: Was hat der Laser je Blickrunde als Öffnung angeboten, was verworfen?

Liest gespeicherte Blickrunden und schreibt je Runde einen kurzen Text:
die angebotenen Öffnungen, die verworfenen Lücken mit Grund und, bei
Aufnahmen im Stand, wie ruhig das Echo in jeder Lücke war (Glas, Spiegel und
gestreifte Kanten geben ein unruhiges Echo). Es wird nichts gefahren, nichts
gestartet und kein KI-Rechner gebraucht.

Die Ausgabe enthält nur Maße einzelner Lücken (Breite, Richtung, Entfernung),
keine Bilder, keine Scans und keine Karte. Sie darf deshalb in einen Bericht.

Aufruf:
    python3 vermessung_pruefen.py --runden ORDNER [--bericht pruefung.md] [--alle]
"""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path
from typing import List, Optional

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lotse.blickrunde import (Blickrunde, echo_statistik, gier_schaetzen,  # noqa: E402
                              profil_der_runde, runden_finden)
from lotse.kandidaten import MITTEN_GLEICH_M, TUERBREIT_M, oeffnungen  # noqa: E402

GRUENDE = {
    'zu_flach': 'dahinter zu wenig freie Tiefe',
    'blick_zu_flach': 'Blick zu flach auf die Lücke',
    'entfernung': 'zu nah oder zu weit',
    'ueberdeckt': 'von einer anderen Lücke überdeckt',
    'verkehrt': 'Kanten verkehrt herum (Winkelbereich über 180°)',
    'schmalere_gewaehlt': 'von derselben Kante aus gab es eine schmalere',
    'nur_bis_zur_blattspitze': 'reicht nur bis zur Spitze eines Türblatts',
    'blatt_im_weg': 'das Türblatt steht im Weg',
    'zu_viele': 'mehr als acht Vorschläge',
}


def _unruhe(oeffnung, ursprung: np.ndarray, anteil: np.ndarray,
            spanne: np.ndarray) -> Optional[dict]:
    """Echo in den Richtungen zwischen den Pfosten einer Öffnung."""
    bins = len(anteil)
    schritt = 2 * math.pi / bins
    von, bis = (math.atan2(p[1] - ursprung[1], p[0] - ursprung[0])
                for p in oeffnung.pfosten)
    anzahl = int(round(((bis - von) % (2 * math.pi)) / schritt))
    erstes = int(math.floor((von + math.pi) / schritt))
    faecher = (erstes + np.arange(2, anzahl - 1)) % bins     # ohne die Pfosten selbst
    faecher = faecher[~np.isnan(anteil[faecher])]            # nur wo Strahlen hingingen
    if len(faecher) < 3:
        return None
    return {'ohne_echo': float(np.mean(anteil[faecher] < 0.5)),
            'unruhig': float(np.mean(np.nan_to_num(spanne[faecher]) > 0.3))}


def pruefe_runde(runde: Blickrunde, alle: bool = False) -> List[str]:
    scans = [runde.scan(i) for i in range(len(runde.aufnahmen))]
    if not scans or any(s is None for s in scans):
        return [f'## {runde.name}', '', 'Ohne LiDAR-Scans; nichts zu prüfen.', '']
    lidar = runde.boden_lidar()
    gier, guete = gier_schaetzen(scans, lidar, runde.vorgabe_gier())
    winkel, entfernung, ursprung = profil_der_runde(scans, gier, lidar)
    im_stand = bool(np.any(ursprung))
    protokoll: List[dict] = []
    gefunden = oeffnungen(winkel, entfernung, ursprung=ursprung, protokoll=protokoll,
                          mitten_gleich_m=MITTEN_GLEICH_M)
    echo = echo_statistik(scans, gier, lidar, ursprung) if im_stand else None
    gedreht = math.degrees(float(np.max(np.abs(gier - gier[0])))) if len(gier) else 0.0
    unbeobachtet = float(np.mean(np.isnan(entfernung)))
    zeilen = [
        f'## {runde.name}', '',
        f'{len(scans)} Aufnahmen, gedreht {gedreht:.1f}°, vermessen '
        f'{"vom Ort des LiDAR (im Stand)" if im_stand else "von der Antriebsmitte"}; '
        f'{100 * unbeobachtet:.0f} % der Richtungen ohne Beobachtung, '
        f'schwächste Zuordnung der Drehwinkel {float(np.min(guete)):.2f}.', '',
    ]
    if gefunden:
        zeilen += ['Angeboten:', '',
                   '| Nr. | Breite | Richtung | Entfernung | Kanten (Richtung / Entfernung) | '
                   'freie Tiefe | zweite Kante | Vermerk | ohne Echo | unruhiges Echo |',
                   '|---|---|---|---|---|---|---|---|---|---|']
        eintrag = {z['nr']: z for z in protokoll if z['ergebnis'] == 'angeboten'}
        for o in gefunden:
            u = _unruhe(o, ursprung, *echo) if echo else None
            # Dieselbe Lücke aus der anderen Durchlaufrichtung trägt oft den
            # aufschlussreicheren Vermerk (dort begann die Suche am anderen Pfosten).
            vermerke = [eintrag[o.nr].get('blatt')] + [
                z.get('blatt') for z in protokoll if z['ergebnis'] != 'angeboten'
                and abs((z['richtung_grad'] - o.richtung_grad + 180.0) % 360.0 - 180.0) < 3.0
                and abs(z['breite_m'] - o.breite_m) < 0.1]
            vermerke = list(dict.fromkeys(v for v in vermerke if v))
            kanten = ' · '.join(f'{r:+.1f}° / {d:.2f} m' for r, d in eintrag[o.nr]['pfosten'])
            zeilen.append(
                f'| {o.nr} | {o.breite_m:.2f} m | {o.richtung_grad:+.1f}° | '
                f'{o.entfernung_m:.2f} m | {kanten} | {o.tiefe_m:.2f} m | {o.schluss} | '
                f'{"; ".join(vermerke) or "–"} | '
                + (f'{100 * u["ohne_echo"]:.0f} % | {100 * u["unruhig"]:.0f} % |'
                   if u else '– | – |'))
    else:
        zeilen.append('Angeboten: nichts.')
    zeilen.append('')

    def wie_angeboten(z: dict) -> bool:
        """Dieselbe Lücke ein zweites Mal (andere Durchlaufrichtung, andere Regel)."""
        return any(abs((z['richtung_grad'] - o.richtung_grad + 180.0) % 360.0 - 180.0) < 3.0
                   and abs(z['breite_m'] - o.breite_m) < 0.1 for o in gefunden)

    verworfen = [z for z in protokoll if z['ergebnis'] != 'angeboten'
                 and (alle or (z['breite_m'] <= TUERBREIT_M + 0.2 and not wie_angeboten(z)))]
    # dieselbe Lücke aus beiden Durchlaufrichtungen nur einmal nennen
    gesehen, einmal = set(), []
    for z in sorted(verworfen, key=lambda z: (z['richtung_grad'], z['breite_m'])):
        schluessel = (round(z['richtung_grad'] / 2.0), round(z['breite_m'], 1), z['ergebnis'])
        if schluessel not in gesehen:
            gesehen.add(schluessel)
            einmal.append(z)
    if einmal:
        zeilen += ['Verworfen' + ('' if alle else f' (bis {TUERBREIT_M + 0.2:.1f} m Breite)')
                   + ':', '',
                   '| Breite | Richtung | Entfernung | Grund | zweite Kante | freie Tiefe | '
                   'Anteil tief | Anteil davor | Vermerk |',
                   '|---|---|---|---|---|---|---|---|---|']
        for z in einmal[:25]:
            def wert(schluessel, einheit='', faktor=1.0, stellen=2):
                return ('–' if z[schluessel] is None
                        else f'{faktor * z[schluessel]:.{stellen}f}{einheit}')
            zeilen.append(
                f'| {z["breite_m"]:.2f} m | {z["richtung_grad"]:+.1f}° | '
                f'{z["entfernung_m"]:.2f} m | {GRUENDE.get(z["ergebnis"], z["ergebnis"])} | '
                f'{z["schluss"]} | {wert("tiefe_m", " m")} | '
                f'{wert("anteil_tief", " %", 100.0, 0)} | '
                f'{wert("anteil_davor", " %", 100.0, 0)} | {z.get("blatt") or "–"} |')
        if len(einmal) > 25:
            zeilen.append(f'| … | | | {len(einmal) - 25} weitere | | | | | |')
        zeilen.append('')
    return zeilen


def main(argv=None) -> int:
    eingabe = argparse.ArgumentParser(
        description='Vermessung prüfen: angebotene und verworfene Lücken je Blickrunde.')
    eingabe.add_argument('--runden', required=True,
                         help='Ordner mit Blickrunden (oder eine einzelne Runde)')
    eingabe.add_argument('--bericht', help='Text zusätzlich in diese Datei schreiben')
    eingabe.add_argument('--alle', action='store_true',
                         help='auch verworfene Lücken nennen, die breiter als eine Tür sind')
    wahl = eingabe.parse_args(argv)
    ordner = runden_finden(wahl.runden)
    if not ordner:
        print(f'Keine Blickrunde unter {wahl.runden} gefunden.', file=sys.stderr)
        return 2
    zeilen = [
        '# Vermessung geprüft', '',
        'Zweite Kante: „sprung“ = die Entfernung springt wieder nach vorn; „linie“ = '
        'das Profil kehrt auf die Wandlinie zurück; „blatt“ = ein offenes Türblatt '
        'verdeckt den zweiten Pfosten, er liegt am Scharnier; „lot“ = wie „blatt“, das '
        'Blatt war aber nicht zu verfolgen.',
        'Anteil tief: Strahlen durch die Lücke mit mindestens 0,5 m freier Tiefe '
        'dahinter. Anteil davor: Strahlen, die schon vor der Lücke enden.',
        'Ohne Echo / unruhiges Echo (nur im Stand): Richtungen in der Lücke, in denen '
        'in weniger als der Hälfte der Aufnahmen ein Echo kam / in denen die Entfernung '
        'zwischen den Aufnahmen um mehr als 0,3 m schwankt.', '',
    ]
    for pfad in ordner:
        try:
            zeilen += pruefe_runde(Blickrunde.lade(pfad), wahl.alle)
        except (ValueError, OSError, KeyError) as fehler:
            zeilen += [f'## {pfad.name}', '', f'Übersprungen: {fehler}', '']
    text = '\n'.join(zeilen)
    print(text)
    if wahl.bericht:
        Path(wahl.bericht).write_text(text + '\n', encoding='utf-8')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
