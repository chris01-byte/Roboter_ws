"""Die Frage an den Lotsen."""
import json

from lotse.frage import (ARTEN, ARTEN_AUSGANG, antwortschema, baue_frage,
                         richtung_text)
from lotse.kandidaten import Oeffnung


def oeffnung(nr, breite, entfernung, richtung, befahrbar=True):
    return Oeffnung(nr=nr, breite_m=breite, mitte=(entfernung, 0.0),
                    pfosten=((entfernung, -breite / 2), (entfernung, breite / 2)),
                    richtung_grad=richtung, entfernung_m=entfernung, tiefe_m=1.5,
                    befahrbar=befahrbar)


def test_frage_nennt_jede_nummer_mit_massen_und_bildern():
    frage = baue_frage([oeffnung(1, 0.78, 2.44, 35.0), oeffnung(2, 0.57, 1.2, -120.0, False)],
                       8, {1: [1, 2]})
    assert frage.angeboten == [1, 2]
    assert '1 | 0,78 m | 2,4 m | 35° links | B1, B2' in frage.text
    assert ('2 | 0,57 m (zu schmal für den Roboter) | 1,2 m | 120° rechts, schräg hinten '
            '| keinem Foto') in frage.text
    assert 'B1 bis B8' in frage.text and 'je 45° weitergedreht' in frage.text
    assert 'gegen den Uhrzeigersinn' in frage.text
    assert '46 cm' in frage.text
    for art in ARTEN:
        assert art in frage.text
    assert 'Bisheriger Verlauf an diesem Standpunkt: keiner.' in frage.text
    assert 'Motoren' in frage.system


def test_frage_ohne_oeffnung_im_uhrzeigersinn_mit_verlauf_und_mosaik():
    frage = baue_frage([], 6, {}, drehsinn=-1,
                       verlauf=['Nr. 2: zweimal nicht erreicht'], als_mosaik=True)
    assert frage.angeboten == []
    assert 'Der Laser hat keine Öffnung vermessen.' in frage.text
    assert 'im Uhrzeigersinn' in frage.text and 'je 60° weitergedreht' in frage.text
    assert 'ein Blatt mit 6 Fotos' in frage.text
    assert 'Nr. 2: zweimal nicht erreicht' in frage.text


def test_antwortmuster_in_der_frage_ist_selbst_gueltiges_json():
    frage = baue_frage([oeffnung(1, 0.8, 2.0, 0.0), oeffnung(2, 0.8, 2.0, 90.0)], 8, {})
    muster = json.loads(frage.text.strip().splitlines()[-1])
    assert set(muster) == set(frage.schema['required'])
    assert all(k['art'] in ARTEN for k in muster['kandidaten'])


def test_schema_laesst_nur_angebotene_nummern_oder_null_zu():
    schema = antwortschema([2, 5])
    assert schema['properties']['wahl'] == {'enum': [2, 5, None]}
    assert schema['properties']['kandidaten']['items']['properties']['art']['enum'] == list(ARTEN)
    assert antwortschema([])['properties']['wahl'] == {'enum': [None]}
    json.dumps(schema)
    assert set(ARTEN_AUSGANG) <= set(ARTEN)


def test_richtung_in_worten():
    assert richtung_text(3.0) == 'geradeaus'
    assert richtung_text(-35.4) == '35° rechts'
    assert richtung_text(90.0) == '90° links'
    assert richtung_text(150.0) == '150° links, schräg hinten'
    assert richtung_text(-178.0) == 'genau hinter dem Roboter'
