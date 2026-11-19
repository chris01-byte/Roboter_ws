"""Auswertung des Trockenlaufs gegen die Wahrheit (Kriterien K0-1 bis K0-6)."""
from lotse.auswertung import SCHWELLEN, bericht, werte_aus


def antwort(modell, wahl, gueltig=True, wiederholung=0, dauer=8.0, fehler=None,
            arten=None, laden=0.1):
    eintrag = {'modell': modell, 'wiederholung': wiederholung, 'dauer_s': dauer,
               'fehler': fehler, 'meta': {'load_s': laden}}
    if fehler is None:
        eintrag['pruefung'] = {'gueltig': gueltig, 'wahl': wahl if gueltig else None,
                               'arten': arten or {}, 'fehler': [] if gueltig else ['x']}
    return eintrag


def runde(name, antworten, vollstaendig=True):
    return {'name': name, 'vollstaendig': vollstaendig, 'antworten': antworten}


def test_alles_richtig_bei_zwoelf_runden_besteht_alle_kriterien():
    runden = [runde(f'r{i}', [antwort('m', 2, wiederholung=w,
                                      arten={'1': 'glas', '2': 'tuer_offen'})
                              for w in range(3)]) for i in range(12)]
    wahr = {f'r{i}': {'ausgaenge': [2], 'arten': {'1': 'glas', '2': 'tuer_offen'}}
            for i in range(12)}
    ergebnis = werte_aus(runden, wahr)
    assert ergebnis['vermessung']['K0-6_anteil'] == 1.0
    m = ergebnis['modelle']['m']
    assert m['K0-1_richtig'] == 12 and m['K0-1_anteil'] == 1.0
    assert m['K0-2_gefaehrliche_wahlen'] == 0
    assert m['K0-3_anteil_verworfen'] == 0.0
    assert m['K0-4_median_s'] == 8.0 and m['K0-4_max_s'] == 8.0
    assert m['K0-5_anteil_gleich'] == 1.0
    assert m['einordnung_richtig'] == m['einordnung_gesamt'] == 72
    assert all(m['bestanden'].values())
    text = bericht(ergebnis)
    assert 'richtig 12 von 12 (100 %)' in text and 'nicht bestanden' not in text


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
    assert (m['K0-1_richtig'], m['K0-1_falsch'], m['K0-1_keine_wahl']) == (1, 1, 1)
    assert m['K0-1_runden'] == 5
    assert m['K0-2_gefaehrliche_wahlen'] == 1           # einmal Glas gewählt
    assert m['ohne_antwort'] == 1 and m['fehlerarten'] == ['zeitgrenze']
    assert m['verworfen'] == 1
    assert m['K0-5_runden_mit_wiederholung'] == 2 and m['K0-5_anteil_gleich'] == 0.5
    urteile = {z['runde']: z['urteil'] for z in m['je_runde']}
    assert urteile == {'tuer': 'richtig', 'glas': 'falsch', 'keine': 'keine Wahl',
                       'verworfen': 'keine gültige Antwort',
                       'stumm': 'keine gültige Antwort'}
    b = m['bestanden']
    assert b['K0-1'] is None                            # zu wenige Runden für ein Urteil
    assert b['K0-2'] is False and b['K0-5'] is False and b['K0-6'] is False
    text = bericht(ergebnis)
    assert '1 Wahlen auf Glas oder Spiegel' in text and 'kein Urteil' in text
    assert f'mindestens {SCHWELLEN["min_runden"]} Runden' in text


def test_antwortzeit_zaehlt_nur_bei_geladenem_modell_und_modelle_getrennt():
    runden = [runde('r', [antwort('a', 1, dauer=40.0, laden=30.0),
                          antwort('a', 1, wiederholung=1, dauer=9.0),
                          antwort('a', 1, wiederholung=2, dauer=11.0),
                          antwort('b', 1, dauer=50.0)])]
    ergebnis = werte_aus(runden, {'r': {'ausgaenge': [1]}})
    assert ergebnis['modelle']['a']['K0-4_median_s'] == 10.0
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
