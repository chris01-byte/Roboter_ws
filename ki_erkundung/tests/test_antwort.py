"""Prüfung der Antwort des Lotsen: verstehen oder verwerfen."""
import json

import pytest

from lotse.antwort import pruefe, wahl_nachmessen
from lotse.kandidaten import Oeffnung

ANGEBOTEN = [1, 2, 3]


def antwort(**aenderungen):
    inhalt = {
        'wahl': 2,
        'begruendung': 'Nummer 2 ist eine offene Zimmertür.',
        'kandidaten': [{'nr': 1, 'art': 'moebelspalt', 'sicherheit': 0.8},
                       {'nr': 2, 'art': 'tuer_offen', 'sicherheit': 0.9},
                       {'nr': 3, 'art': 'glas', 'sicherheit': 0.7}],
        'raum': 'Arbeitszimmer',
        'gefahren': [],
    }
    inhalt.update(aenderungen)
    return json.dumps(inhalt, ensure_ascii=False)


def test_gueltige_antwort_wird_vollstaendig_verstanden():
    p = pruefe(antwort(), ANGEBOTEN)
    assert p.gueltig and p.wahl == 2 and p.fehler == [] and p.toleriert == []
    assert p.arten == {1: 'moebelspalt', 2: 'tuer_offen', 3: 'glas'}
    assert p.sicherheit[2] == 0.9
    assert p.raum == 'Arbeitszimmer'
    assert p.als_dict()['arten'] == {'1': 'moebelspalt', '2': 'tuer_offen', '3': 'glas'}


def test_keine_wahl_ist_eine_gueltige_antwort():
    p = pruefe(antwort(wahl=None), ANGEBOTEN)
    assert p.gueltig and p.wahl is None


@pytest.mark.parametrize('text', [
    '', 'Ich wähle Nummer 2.', '[1, 2]', '{"wahl": 2', None, 12,
])
def test_kein_lesbares_json_wird_verworfen(text):
    p = pruefe(text, ANGEBOTEN)
    assert not p.gueltig and p.wahl is None and p.fehler == ['kein_json']


def test_json_in_umgebendem_text_wird_toleriert_und_gezaehlt():
    text = 'Hier meine Antwort:\n```json\n' + antwort() + '\n```\nViel Erfolg!'
    p = pruefe(text, ANGEBOTEN)
    assert p.gueltig and p.wahl == 2 and p.toleriert == ['json_umrahmt']
    # geschweifte Klammern im Freitext dürfen die Suche nicht stören
    p = pruefe('Text ' + antwort(begruendung='Tür {offen} "links"'), ANGEBOTEN)
    assert p.gueltig and p.begruendung == 'Tür {offen} "links"'


@pytest.mark.parametrize('wahl,fehler', [
    (7, 'wahl_nicht_angeboten'), (0, 'wahl_nicht_angeboten'),
    (-2, 'wahl_nicht_angeboten'), (True, 'wahl_unlesbar'),
    ('zwei', 'wahl_unlesbar'), ([2], 'wahl_unlesbar'), (2.5, 'wahl_unlesbar'),
])
def test_wahl_ausserhalb_des_angebots_wird_verworfen(wahl, fehler):
    p = pruefe(antwort(wahl=wahl), ANGEBOTEN)
    assert not p.gueltig and p.wahl is None and p.fehler == [fehler]


def test_fehlende_wahl_wird_verworfen():
    inhalt = json.loads(antwort())
    del inhalt['wahl']
    p = pruefe(json.dumps(inhalt), ANGEBOTEN)
    assert not p.gueltig and p.fehler == ['wahl_fehlt']


@pytest.mark.parametrize('wahl,vermerk', [('2', 'wahl_als_text'), (2.0, 'wahl_als_kommazahl')])
def test_wahl_als_text_oder_kommazahl_wird_toleriert(wahl, vermerk):
    p = pruefe(antwort(wahl=wahl), ANGEBOTEN)
    assert p.gueltig and p.wahl == 2 and vermerk in p.toleriert


@pytest.mark.parametrize('wahl', [1, 3])
def test_wahl_die_die_ki_selbst_nicht_als_ausgang_einordnet_wird_verworfen(wahl):
    """Nummer 1 nennt sie Möbelspalt, Nummer 3 Glas: Dann darf sie beides nicht wählen."""
    p = pruefe(antwort(wahl=wahl), ANGEBOTEN)
    assert not p.gueltig and p.wahl is None
    assert p.fehler == ['wahl_widerspricht_einordnung']
    assert p.arten[3] == 'glas'                     # die Einordnung bleibt lesbar


def test_wahl_ohne_einordnung_gilt_als_unklar_und_wird_verworfen():
    p = pruefe(antwort(kandidaten=[]), ANGEBOTEN)
    assert not p.gueltig and p.fehler == ['wahl_widerspricht_einordnung']
    assert p.arten == {1: 'unklar', 2: 'unklar', 3: 'unklar'}
    inhalt = json.loads(antwort(wahl=None))
    del inhalt['kandidaten']
    p = pruefe(json.dumps(inhalt), ANGEBOTEN)
    assert p.gueltig and 'kandidaten_fehlen' in p.toleriert


def test_unbekannte_art_und_fremde_nummern_werden_hingenommen():
    kandidaten = [{'nr': 1, 'art': 'vorhang'}, {'nr': 2, 'art': 'durchgang', 'sicherheit': 7},
                  {'nr': 9, 'art': 'tuer_offen'}, 'unsinn', {'nr': '3', 'art': 'spiegel'}]
    p = pruefe(antwort(kandidaten=kandidaten), ANGEBOTEN)
    assert p.gueltig and p.wahl == 2
    assert p.arten == {1: 'unklar', 2: 'durchgang', 3: 'spiegel'}
    assert p.sicherheit == {2: 1.0}
    assert set(p.toleriert) == {'art_unbekannt', 'fremde_nummer_eingeordnet',
                                'kandidat_unlesbar'}
    assert not pruefe(antwort(kandidaten='keine'), ANGEBOTEN).gueltig


def test_freitext_wird_begrenzt_und_bereinigt():
    p = pruefe(antwort(begruendung='x' * 1000, raum='  ' + 'Wohnzimmer' * 20,
                       gefahren=['Kabel am Boden', '', 5, 'Treppe'] + ['Glas'] * 10), ANGEBOTEN)
    assert len(p.begruendung) == 400
    assert len(p.raum) == 40 and p.raum.startswith('Wohnzimmer')
    assert p.gefahren[:2] == ['Kabel am Boden', 'Treppe'] and len(p.gefahren) == 5
    p = pruefe(antwort(raum=None, begruendung=3, gefahren='keine'), ANGEBOTEN)
    assert p.gueltig and p.raum is None and p.begruendung == '' and p.gefahren == []


def test_ohne_angebot_ist_nur_keine_wahl_gueltig():
    assert pruefe(antwort(wahl=None, kandidaten=[]), []).gueltig
    assert not pruefe(antwort(wahl=1, kandidaten=[]), []).gueltig


def test_wahl_nachmessen_haelt_die_wahl_gegen_die_vermessung():
    def oeffnung(nr, befahrbar):
        return Oeffnung(nr=nr, breite_m=0.8 if befahrbar else 0.57, mitte=(2.0, 0.0),
                        pfosten=((2.0, -0.4), (2.0, 0.4)), richtung_grad=0.0,
                        entfernung_m=2.0, tiefe_m=1.0, befahrbar=befahrbar)
    liste = [oeffnung(1, True), oeffnung(2, False)]
    assert wahl_nachmessen(None, liste) is None
    assert wahl_nachmessen(1, liste) is None
    assert wahl_nachmessen(2, liste) == 'zu_schmal'
    assert wahl_nachmessen(5, liste) == 'nicht_vermessen'


def test_wahl_einer_nummer_die_in_keinem_foto_steht_wird_verworfen():
    """Was nur der Laser kennt, kann die KI nicht beurteilen (KI-0N, 21.11.2026)."""
    p = pruefe(antwort(wahl=2), ANGEBOTEN, waehlbar=[1])
    assert not p.gueltig and p.fehler == ['wahl_nicht_im_foto'] and p.wahl is None
    assert pruefe(antwort(wahl=2), ANGEBOTEN, waehlbar=[1, 2]).gueltig
    assert pruefe(antwort(wahl=None), ANGEBOTEN, waehlbar=[]).gueltig
    assert pruefe(antwort(wahl=2), ANGEBOTEN).gueltig              # ohne Angabe wie bisher


def test_wand_als_einordnung_macht_die_wahl_ungueltig():
    kandidaten = [{'nr': 1, 'art': 'wand'}, {'nr': 2, 'art': 'tuer_offen'}]
    p = pruefe(antwort(wahl=1, kandidaten=kandidaten), ANGEBOTEN)
    assert not p.gueltig and p.fehler == ['wahl_widerspricht_einordnung']
    assert pruefe(antwort(wahl=2, kandidaten=kandidaten), ANGEBOTEN).arten[1] == 'wand'
