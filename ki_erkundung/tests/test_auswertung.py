"""Auswertung des Trockenlaufs gegen die Wahrheit (Kriterien K0-1 bis K0-6)."""
import pytest

from lotse.auswertung import SCHWELLEN, bericht, uebertrage, werte_aus


def antwort(modell, wahl, gueltig=True, wiederholung=0, dauer=8.0, fehler=None,
            arten=None, laden=0.1):
    eintrag = {'modell': modell, 'wiederholung': wiederholung, 'dauer_s': dauer,
               'fehler': fehler, 'meta': {'load_s': laden}}
    if fehler is None:
        eintrag['pruefung'] = {'gueltig': gueltig, 'wahl': wahl if gueltig else None,
                               'arten': arten or {}, 'fehler': [] if gueltig else ['x']}
    return eintrag


def runde(name, antworten, vollstaendig=True, richtungen=None, im_foto=None):
    eintrag = {'name': name, 'vollstaendig': vollstaendig, 'antworten': antworten}
    if richtungen is not None:
        eintrag['oeffnungen'] = [{'nr': nr, 'richtung_grad': grad}
                                 for nr, grad in richtungen.items()]
    if im_foto is not None:
        eintrag['sichtbar_in'] = {str(nr): bilder for nr, bilder in im_foto.items()}
    return eintrag


def test_alles_richtig_bei_zwoelf_runden_besteht_alle_kriterien():
    runden = [runde(f'r{i}', [antwort('m', 2, wiederholung=w,
                                      arten={'1': 'glas', '2': 'tuer_offen'})
                              for w in range(3)]) for i in range(12)]
    # jede Ansicht ein zweites Mal getrennt aufgenommen
    runden += [runde(f'r{i}_2', [antwort('m', 2, arten={'1': 'glas', '2': 'tuer_offen'})])
               for i in range(12)]
    wahr = {r['name']: {'ausgaenge': [2], 'arten': {'1': 'glas', '2': 'tuer_offen'}}
            for r in runden}
    ergebnis = werte_aus(runden, wahr)
    assert ergebnis['vermessung']['K0-6_anteil'] == 1.0
    m = ergebnis['modelle']['m']
    assert m['K0-1_richtig'] == 24 and m['K0-1_anteil'] == 1.0
    assert m['K0-2_gefaehrliche_wahlen'] == 0
    assert m['K0-3_anteil_verworfen'] == 0.0
    assert m['K0-4_median_s'] == 8.0 and m['K0-4_max_s'] == 8.0
    assert m['K0-5_paare'] == 12 and m['K0-5_anteil_gleich'] == 1.0
    assert m['einordnung_richtig'] == m['einordnung_gesamt'] == 96
    assert all(m['bestanden'].values())
    text = bericht(ergebnis)
    assert 'richtig 24 von 24 (100 %)' in text and 'nicht bestanden' not in text
    assert 'kein Urteil' not in text


def test_falsche_gefaehrliche_verworfene_und_fehlende_antworten_werden_getrennt_gezaehlt():
    wahr = {
        'tuer': {'ausgaenge': [2], 'arten': {'1': 'glas', '2': 'tuer_offen'}},
        'glas': {'ausgaenge': [2], 'arten': {'1': 'glas', '2': 'tuer_offen'}},
        'keine': {'ausgaenge': [2]},
        'verworfen': {'ausgaenge': [1]},
        'stumm': {'ausgaenge': [1]},
        'nicht_angeboten': {'ausgaenge': [], 'ausgang_sichtbar': True},
        'kein_ausgang': {'ausgaenge': [], 'ausgang_sichtbar': False},
    }
    runden = [
        runde('tuer', [antwort('m', 2), antwort('m', 2, wiederholung=1)]),
        runde('glas', [antwort('m', 1), antwort('m', 2, wiederholung=1)]),
        runde('keine', [antwort('m', None)]),
        runde('verworfen', [antwort('m', 1, gueltig=False)]),
        runde('stumm', [antwort('m', None, fehler='zeitgrenze')]),
        runde('nicht_angeboten', [antwort('m', None)]),
        runde('kein_ausgang', [antwort('m', None)]),
        runde('ohne_wahrheit', [antwort('m', 3)], vollstaendig=False),
    ]
    ergebnis = werte_aus(runden, wahr)
    v = ergebnis['vermessung']
    assert v['runden'] == 8 and v['runden_mit_wahrheit'] == 7
    assert v['runden_mit_sichtbarem_ausgang'] == 6 and v['davon_ausgang_angeboten'] == 5
    assert v['unvollstaendige_runden'] == 1
    m = ergebnis['modelle']['m']
    # richtig: die Tür, und zweimal zu Recht keine Wahl, wo kein Ausgang angeboten war
    assert (m['K0-1_richtig'], m['K0-1_falsch'], m['K0-1_keine_wahl']) == (3, 1, 1)
    assert m['K0-1_runden'] == 7 and m['K0-1_runden_mit_angebotenem_ausgang'] == 5
    assert m['K0-1_gewaehlt_ohne_angebotenen_ausgang'] == 0
    assert m['K0-2_gefaehrliche_wahlen'] == 1           # einmal Glas gewählt
    assert m['ohne_antwort'] == 1 and m['fehlerarten'] == ['zeitgrenze']
    assert m['verworfen'] == 1
    assert m['K0-5_paare'] == 0 and m['K0-5_anteil_gleich'] is None
    urteile = {z['runde']: z['urteil'] for z in m['je_runde']}
    assert urteile == {'tuer': 'richtig', 'glas': 'falsch', 'keine': 'keine Wahl',
                       'verworfen': 'keine gültige Antwort',
                       'stumm': 'keine gültige Antwort',
                       'nicht_angeboten': 'richtig (kein Ausgang angeboten)',
                       'kein_ausgang': 'richtig (kein Ausgang angeboten)'}
    b = m['bestanden']
    assert b['K0-1'] is None                            # zu wenige Runden für ein Urteil
    assert b['K0-2'] is False and b['K0-5'] is None and b['K0-6'] is False
    text = bericht(ergebnis)
    assert '1 Wahlen auf Glas oder Spiegel' in text and 'kein Urteil' in text
    assert f'mindestens {SCHWELLEN["min_runden"]} Runden' in text


def test_antwortzeit_zaehlt_nur_bei_geladenem_modell_und_modelle_getrennt():
    runden = [runde('r', [antwort('a', 1, dauer=40.0, laden=30.0),
                          antwort('a', 1, wiederholung=1, dauer=1.3),
                          antwort('b', 1, dauer=50.0)]),
              runde('s', [antwort('a', 1, dauer=9.0), antwort('a', 1, wiederholung=1, dauer=1.2)]),
              runde('t', [antwort('a', 1, dauer=11.0)])]
    ergebnis = werte_aus(runden, {'r': {'ausgaenge': [1]}})
    # gezählt: erste Antworten bei geladenem Modell (9 s, 11 s); nicht das
    # Laden (40 s) und nicht die Wiederholungen aus dem Zwischenspeicher
    assert ergebnis['modelle']['a']['K0-4_median_s'] == 10.0
    assert ergebnis['modelle']['a']['K0-4_p95_s'] == 11.0
    assert '95 % bis 11.0 s' in bericht(ergebnis)
    assert ergebnis['modelle']['a']['K0-4_max_s'] == 11.0
    assert ergebnis['modelle']['a']['bestanden']['K0-4'] is True
    assert ergebnis['modelle']['b']['bestanden']['K0-4'] is False
    assert set(ergebnis['modelle']) == {'a', 'b'}


def test_ohne_wahrheit_und_ohne_antworten_gibt_es_kein_urteil():
    ergebnis = werte_aus([runde('r', [])], {})
    assert ergebnis['modelle'] == {}
    assert ergebnis['vermessung']['K0-6_anteil'] is None
    assert 'Blickrunden: 1, davon mit Wahrheit: 0' in bericht(ergebnis)
    nur_antworten = werte_aus([runde('r', [antwort('m', 1)])], {})
    assert nur_antworten['modelle']['m']['bestanden']['K0-1'] is None
    assert nur_antworten['modelle']['m']['bestanden']['K0-2'] is None


def test_zahlen_des_ersten_echten_laufs_vom_21_11_2026_ohne_denken():
    """Sechs Ansichten im Labor, nachgerechnet mit der korrigierten Auswertung.

    Vorher stand dort: K0-1 „richtig 4 von 5“, K0-2 „bestanden“, K0-5 nicht
    berechnet. Die Wahl einer Möbellücke als Durchgang (labor_tuer_weit)
    fehlte, weil dort kein echter Ausgang angeboten war.
    """
    wahr = {
        'labor_tuer_vorn': {'ausgaenge': [1], 'arten': {'1': 'tuer_offen'}},
        'labor_tuer_seite_nah_b': {'ausgaenge': [2],
                                   'arten': {'1': 'unklar', '2': 'tuer_offen'}},
        'labor_tuer_weit': {'ausgaenge': [], 'ausgang_sichtbar': True,
                            'arten': {'1': 'moebelspalt'}},
        'labor_ecke': {'ausgaenge': [2], 'arten': {'1': 'moebelspalt', '2': 'tuer_offen'}},
        'labor_tuer_weit_seite': {'ausgaenge': [3], 'arten': {
            '1': 'moebelspalt', '2': 'moebelspalt', '3': 'tuer_offen'}},
        'labor_tuer_vorn_2': {'ausgaenge': [1], 'arten': {'1': 'tuer_offen'}},
    }
    runden = [
        runde('labor_tuer_vorn', [antwort('q', 1, dauer=4.02, laden=2.39,
                                          arten={'1': 'tuer_offen'})],
              False, {1: -1.3}, {1: [1]}),
        runde('labor_tuer_seite_nah_b', [antwort('q', 2, dauer=1.85, arten={
            '1': 'moebelspalt', '2': 'tuer_offen'})], False, {1: -76.8, 2: -18.3}, {2: [1]}),
        runde('labor_tuer_weit', [antwort('q', 1, dauer=1.59, arten={'1': 'durchgang'})],
              False, {1: 15.9}, {1: [1]}),
        runde('labor_ecke', [antwort('q', None, dauer=2.03, arten={
            '1': 'moebelspalt', '2': 'tuer_offen'})], False, {1: 15.3, 2: 56.9}, {1: [1]}),
        runde('labor_tuer_weit_seite',
              [antwort('q', 3, dauer=2.69,
                       arten={'1': 'moebelspalt', '2': 'tuer_offen', '3': 'durchgang'})],
              False, {1: 95.7, 2: -56.2, 3: -13.6}, {3: [1]}),
        runde('labor_tuer_vorn_2', [antwort('q', 1, dauer=1.52, arten={'1': 'durchgang'})],
              False, {1: -5.2}, {1: [1]}),
    ]
    ergebnis = werte_aus(runden, wahr)
    v, m = ergebnis['vermessung'], ergebnis['modelle']['q']
    assert (v['davon_ausgang_angeboten'], v['runden_mit_sichtbarem_ausgang']) == (5, 6)
    assert (m['K0-1_richtig'], m['K0-1_runden']) == (4, 6)
    assert m['K0-1_gewaehlt_ohne_angebotenen_ausgang'] == 1 and m['K0-1_keine_wahl'] == 1
    assert m['bestanden']['K0-2'] is None               # keine Glas- oder Spiegelfläche dabei
    assert (m['K0-5_paare'], m['K0-5_anteil_gleich']) == (1, 1.0)
    assert (m['K0-4_gezaehlt'], m['K0-4_ausgenommen_laden']) == (5, 1)
    assert m['K0-4_median_s'] == 1.9 and m['K0-4_max_s'] == 2.7
    assert (m['einordnung_richtig'], m['einordnung_gesamt']) == (5, 10)
    foto = {z['runde']: z['ausgang_im_foto'] for z in m['je_runde']}
    assert foto['labor_ecke'] is False and foto['labor_tuer_vorn'] is True
    assert foto['labor_tuer_weit'] is None
    text = bericht(ergebnis)
    assert 'richtig 4 von 6 (67 %); falsch 1, davon 1 gewählt, obwohl kein' in text
    assert '| labor_ecke | – | keine Wahl | nur in der Skizze |' in text
    assert 'None' not in text


def test_getrennte_aufnahmen_mit_verschiedener_wahl_und_andere_nummerierung():
    wahr = {'a': {'ausgaenge': [1]}, 'a_2': {'ausgaenge': [2]},
            'b': {'ausgaenge': [1]}, 'b_2': {'ausgaenge': [1]}}
    runden = [
        # dieselbe Tür, in der zweiten Aufnahme hat sie die Nummer 2
        runde('a', [antwort('m', 1)], richtungen={1: 10.0, 2: 90.0}),
        runde('a_2', [antwort('m', 2)], richtungen={1: -80.0, 2: 14.0}),
        # gleiche Nummer, aber eine andere Öffnung
        runde('b', [antwort('m', 1)], richtungen={1: 0.0}),
        runde('b_2', [antwort('m', 1)], richtungen={1: 70.0}),
        # nur eine der beiden Aufnahmen beantwortet: zählt nicht als Paar
        runde('c', [antwort('m', 1)]), runde('c_2', []),
    ]
    m = werte_aus(runden, wahr)['modelle']['m']
    assert (m['K0-5_paare'], m['K0-5_anteil_gleich']) == (2, 0.5)
    einzeln = werte_aus([runde('x', [antwort('m', 1, dauer=4.0, laden=3.0)])],
                        {'x': {'ausgaenge': [1]}})
    assert 'Median – s' in bericht(einzeln)


# ----------------------------------------- Angaben des Menschen nach Lage

def runde_mit_lage(name, antworten, lagen):
    """``lagen``: Nummer -> (x, y) der Mitte, wie in der Ergebnisdatei."""
    eintrag = runde(name, antworten)
    eintrag['oeffnungen'] = [{'nr': nr, 'mitte': list(mitte), 'richtung_grad': 0.0}
                             for nr, mitte in lagen.items()]
    return eintrag


WAHR_MIT_LAGE = {'ausgaenge': [2], 'ausgang_sichtbar': True,
                 'arten': {'1': 'moebelspalt', '2': 'tuer_offen'},
                 'lage': {'1': {'mitte': [1.0, 1.5]}, '2': {'mitte': [2.0, -0.5]}}}


def test_angaben_bleiben_bei_gleicher_vermessung_und_folgen_neuen_nummern():
    gleich = uebertrage(runde_mit_lage('r', [], {1: (1.0, 1.5), 2: (2.0, -0.5)}), WAHR_MIT_LAGE)
    assert gleich['ausgaenge'] == [2] and gleich['arten'] == WAHR_MIT_LAGE['arten']
    assert gleich['nicht_beurteilt'] == [] and gleich['entfallen'] == []
    # Die Möbellücke wird nicht mehr angeboten; die Tür heißt jetzt Nummer 1
    # und liegt 10 cm daneben (genauer vermessen).
    neu = uebertrage(runde_mit_lage('r', [], {1: (2.05, -0.42)}), WAHR_MIT_LAGE)
    assert neu['ausgaenge'] == [1] and neu['arten'] == {'1': 'tuer_offen'}
    assert neu['nicht_beurteilt'] == [] and neu['entfallen'] == [1]
    # Eine Öffnung an neuer Stelle hat keine Angabe.
    dazu = uebertrage(runde_mit_lage('r', [], {1: (2.0, -0.5), 2: (3.5, 2.0)}), WAHR_MIT_LAGE)
    assert dazu['ausgaenge'] == [1] and dazu['nicht_beurteilt'] == [2]
    assert dazu['entfallen'] == [1]
    assert dazu['naechste_fruehere'] == {'2': {'nr': 1, 'abstand_m': 2.55, 'art': 'moebelspalt',
                                               'versatz_grad': -26.6, 'war_ausgang': False}}
    # Die Tür ist 45 cm nach links gewandert (vorher stand die Nummer neben der Tür):
    # zu weit für die Übertragung, aber als Nachbarin der früheren Tür erkennbar.
    gewandert = uebertrage(runde_mit_lage('r', [], {1: (2.0, -0.05)}), WAHR_MIT_LAGE)
    assert gewandert['ausgaenge'] == [] and gewandert['nicht_beurteilt'] == [1]
    nah = gewandert['naechste_fruehere']['1']
    assert (nah['nr'], nah['abstand_m'], nah['war_ausgang']) == (2, 0.45, True)
    assert nah['versatz_grad'] == pytest.approx(12.6, abs=0.1)            # links davon
    # Zwei jetzige Öffnungen nahe einer früheren: nur die nähere bekommt die Angabe.
    doppelt = uebertrage(runde_mit_lage('r', [], {1: (2.3, -0.5), 2: (2.05, -0.5)}),
                         WAHR_MIT_LAGE)
    assert doppelt['ausgaenge'] == [2] and doppelt['nicht_beurteilt'] == [1]
    # Ohne festgehaltene Lage gelten die Nummern, wie sie sind.
    ohne = uebertrage(runde_mit_lage('r', [], {1: (9.0, 9.0)}), {'ausgaenge': [1]})
    assert ohne['ausgaenge'] == [1] and ohne['nicht_beurteilt'] == []


def test_auswertung_uebertraegt_und_zaehlt_unbeurteilte_wahlen_nicht():
    runden = [
        # Tür jetzt Nummer 1: die Wahl 1 ist richtig
        runde_mit_lage('a', [antwort('m', 1)], {1: (2.05, -0.42)}),
        # die KI wählt eine Öffnung an neuer Stelle: weder richtig noch falsch
        runde_mit_lage('b', [antwort('m', 2)], {1: (2.0, -0.5), 2: (3.5, 2.0)}),
        # unverändert: Möbellücke gewählt, falsch
        runde_mit_lage('c', [antwort('m', 1)], {1: (1.0, 1.5), 2: (2.0, -0.5)}),
    ]
    ergebnis = werte_aus(runden, {name: WAHR_MIT_LAGE for name in 'abc'})
    m = ergebnis['modelle']['m']
    assert (m['K0-1_richtig'], m['K0-1_falsch'], m['K0-1_nicht_beurteilt']) == (1, 1, 1)
    assert m['K0-1_anteil'] == 0.5                     # 1 von 2 beurteilten
    urteile = {z['runde']: z['urteil'] for z in m['je_runde']}
    assert urteile == {'a': 'richtig', 'b': 'nicht beurteilt (Öffnung an neuer Stelle)',
                       'c': 'falsch'}
    v = ergebnis['vermessung']
    assert v['nicht_beurteilte_oeffnungen'] == {'b': [2]}
    assert v['entfallene_oeffnungen'] == {'a': [1], 'b': [1]}
    assert v['davon_ausgang_angeboten'] == 3
    text = bericht(ergebnis)
    assert 'Übertragen wurde nach der Lage der Öffnungen.' in text
    assert '- b: Nr. 2 liegt an neuer Stelle und ist nicht beurteilt.' in text
    assert ('  - Nr. 2: 2.55 m von der früheren Nr. 1 (moebelspalt), 26.6° rechts davon.'
            in text)
    assert 'richtig 1 von 2 (50 %)' in text and 'nicht beurteilt 1' in text
