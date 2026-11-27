"""Die Frage an den Lotsen."""
import json

from lotse.antwort import pruefe
from lotse.frage import (ANTWORTMUSTER, ARTEN, ARTEN_AUSGANG, antwortschema, baue_frage,
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
    # Nummer 2 steht in keinem Foto: nicht wählbar, und die Frage sagt es.
    assert frage.waehlbar == [1] and frage.schema['properties']['wahl'] == {'enum': [1, None]}
    assert 'kennt nur der Laser' in frage.text and 'wähle sie nicht' in frage.text
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


def test_antwortmuster_hat_nichts_zum_abschreiben_und_abgeschrieben_waehlt_es_nichts():
    """KI-F9, Lauf 2: Die Antwort glich in Wahl, Arten und Zahlen dem alten Beispiel
    (Wahl 2, Nr. 2 tuer_offen 0,9) – und war ein Fensterrollo."""
    frage = baue_frage([oeffnung(1, 0.8, 2.0, 0.0), oeffnung(2, 0.8, 2.0, 90.0)], 8,
                       {1: [1], 2: [3]})
    assert frage.waehlbar == [1, 2] and 'kennt nur der Laser' not in frage.text
    zeile = frage.text.strip().splitlines()[-1]
    assert zeile == ANTWORTMUSTER
    muster = json.loads(zeile)
    assert list(muster) == list(frage.schema['properties']) == frage.schema['required']
    assert muster['wahl'] is None
    assert all(k['nr'] not in frage.angeboten and k['art'] not in ARTEN
               for k in muster['kandidaten'])
    # Schreibt ein Modell das Muster ab, wird nichts gewählt.
    abgeschrieben = pruefe(zeile, frage.angeboten, frage.waehlbar)
    assert abgeschrieben.gueltig and abgeschrieben.wahl is None


def test_erst_einordnen_dann_waehlen_und_lieber_keine_wahl():
    frage = baue_frage([oeffnung(1, 0.8, 2.0, 0.0)], 8, {1: [1]})
    reihenfolge = list(frage.schema['properties'])
    assert reihenfolge.index('kandidaten') < reihenfolge.index('begruendung') \
        < reihenfolge.index('wahl')
    assert 'sicherheit' in frage.schema['properties']['kandidaten']['items']['required']
    for satz in ('Reicht die Öffnung bis zum Boden?', 'Lieber keine Wahl als eine falsche',
                 'Ein Fenster ist nie ein Ausgang.', 'von 0 (geraten) bis 1 (eindeutig)',
                 'fenster = Fenster, auch mit Rollo'):
        assert satz in frage.text, satz
    assert 'fenster' in ARTEN and 'moebel' in ARTEN
    assert 'fenster' not in ARTEN_AUSGANG and 'moebel' not in ARTEN_AUSGANG
    assert 'schlimmer als keine' in frage.system


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


def test_frage_sagt_wenn_nicht_ganz_herumgedreht_wurde():
    eine = oeffnung(1, 0.8, 2.0, 0.0)
    teil = baue_frage([eine], 3, {1: [1]}, schritt_grad=45.0, vollstaendig=False)
    assert 'nicht ganz herum' in teil.text
    assert 'B1 bis B3' in teil.text and 'je 45° weitergedreht' in teil.text
    stand = baue_frage([eine], 1, {1: [1]}, schritt_grad=45.0, vollstaendig=False)
    assert 'schaut in eine Richtung' in stand.text
    assert 'B1 ist ein Foto seiner Kamera' in stand.text
    assert 'weitergedreht' not in stand.text
    assert 'Das zweite Bild ist eine Skizze von oben.' in stand.text
    ohne_skizze = baue_frage([eine], 1, {1: [1]}, mit_skizze=False, vollstaendig=False)
    assert 'Skizze' not in ohne_skizze.text


def test_nahe_oeffnung_am_unteren_bildrand_wird_erklaert():
    """Befund KI-0N (Flur): Die Nummer stand am Bildrand vor einer Wand; die KI nahm
    den Durchgang, den sie daneben im Foto sah."""
    nah = oeffnung(1, 0.98, 0.56, 4.0)
    frage = baue_frage([nah, oeffnung(2, 0.8, 2.5, -20.0)], 1, {1: [1], 2: [1]},
                       vollstaendig=False, am_rand={1: [1]})
    assert '| geradeaus | B1 (unterer Bildrand)\n' in frage.text
    assert '| 20° rechts | B1\n' in frage.text
    assert 'näher am Roboter, als das Foto reicht' in frage.text
    assert 'Ist dort eine Wand, ist es kein Ausgang' in frage.text
    ohne = baue_frage([nah], 1, {1: [1]}, vollstaendig=False)
    assert 'unterer Bildrand' not in ohne.text


def test_wand_ist_eine_einordnung_aber_kein_ausgang():
    assert 'wand' in ARTEN and 'wand' not in ARTEN_AUSGANG
    assert 'wand = die Nummer steht auf einer Wand' in baue_frage([], 1, {}).text
