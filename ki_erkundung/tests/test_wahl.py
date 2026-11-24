"""Die Wahl der KI an den Fahrteil übergeben: Ort in der Karte, Prüfung, Zuordnung."""
import json
import math

import numpy as np
import pytest

import beispielrunde_erzeugen as welt
from lotse.ablauf import bereite_vor
from lotse.blickrunde import Blickrunde
from lotse.fahrziel import im_standpunktrahmen
from lotse.kandidaten import Oeffnung
from lotse.wahl import (MAX_ALTER_S, WAHL_SCHEMA, in_die_karte, standpunkt_in_der_karte,
                        wahl_aufschreiben, wahl_lesen, wahl_satz, zur_wahl)

TUER_MITTE = (4.0, 1.4)            # Flurtür der Beispielwelt, in der Karte (= Welt)
JETZT = 1_800_000_000.0


@pytest.fixture(scope='module')
def runde_mit_karte(tmp_path_factory):
    ordner = welt.erzeuge(tmp_path_factory.mktemp('wahl'), 'mit_karte', mit_karte=True)
    return Blickrunde.lade(ordner)


@pytest.fixture(scope='module')
def vorbereitung(runde_mit_karte):
    return bereite_vor(runde_mit_karte)


def _tuer(vorbereitung):
    return min(vorbereitung.oeffnungen, key=lambda o: abs(o.breite_m - 0.80)
               if o.richtung_grad < 0 else 9.0)


def _eintrag(nr, art='tuer_offen', sicherheit=0.85, **mehr):
    eintrag = {'modell': 'pruefmodell', 'dauer_s': 4.9, 'fehler': None,
               'pruefung': {'gueltig': True, 'wahl': nr, 'arten': {str(nr): art},
                            'sicherheit': {str(nr): sicherheit}, 'raum': 'Zimmer',
                            'begruendung': 'offene Tür zum Flur', 'gefahren': [],
                            'fehler': [], 'toleriert': []},
               'nachmessen': None}
    eintrag.update(mehr)
    return eintrag


def test_lage_am_ende_der_runde_ergibt_den_standpunktrahmen(runde_mit_karte, vorbereitung):
    x, y, gier = standpunkt_in_der_karte(runde_mit_karte.karte, vorbereitung.gier_ende_rad)
    sx, sy, sgier = welt.STANDPUNKT
    assert (x, y) == pytest.approx((sx, sy), abs=1e-6)
    # Blick der ersten Aufnahme: Blick am Ende, um die gemessene Drehung zurück
    assert math.degrees(gier) == pytest.approx(math.degrees(sgier), abs=1.0)


@pytest.mark.parametrize('karte, gier, warum', [
    (None, 0.1, 'keine Lage'),
    ({'rahmen': 'odom', 'basis_ende': [1, 2, 0]}, 0.1, 'anderer Rahmen'),
    ({'rahmen': 'map', 'basis_ende': [1, 2]}, 0.1, 'zu kurz'),
    ({'rahmen': 'map', 'basis_ende': [1, 'x', 0]}, 0.1, 'keine Zahl'),
    ({'rahmen': 'map', 'basis_ende': [1, float('nan'), 0]}, 0.1, 'nicht endlich'),
    ({'rahmen': 'map', 'basis_ende': [1, True, 0]}, 0.1, 'Wahrheitswert'),
    ({'rahmen': 'map', 'basis_ende': [1, 2, 0]}, None, 'Drehwinkel fehlt'),
    ({'rahmen': 'map', 'basis_ende': [1, 2, 0]}, float('inf'), 'Drehwinkel unendlich'),
])
def test_ohne_brauchbare_lage_gibt_es_keinen_standpunkt(karte, gier, warum):
    assert standpunkt_in_der_karte(karte, gier) is None, warum


def test_punkte_hin_und_zurueck():
    stand = (2.0, -1.0, math.radians(130.0))
    for punkt in [(0.0, 0.0), (1.5, 0.2), (-0.7, 2.3)]:
        karte = in_die_karte(punkt, stand)
        assert im_standpunktrahmen(karte, stand) == pytest.approx(punkt, abs=1e-9)


def test_gewaehlte_tuer_landet_an_ihrem_ort_in_der_karte(runde_mit_karte, vorbereitung):
    tuer = _tuer(vorbereitung)
    stand = standpunkt_in_der_karte(runde_mit_karte.karte, vorbereitung.gier_ende_rad)
    wahl = wahl_aufschreiben(vorbereitung, _eintrag(tuer.nr), stand, jetzt_s=JETZT)
    assert wahl['schema'] == WAHL_SCHEMA and wahl['art'] == 'ki_wahl' and wahl['quelle'] == 'ki'
    assert wahl['nr'] == tuer.nr and wahl['einordnung'] == 'tuer_offen'
    assert wahl['rahmen'] == 'map' and wahl['runde'] == 'mit_karte'
    assert math.hypot(wahl['mitte'][0] - TUER_MITTE[0], wahl['mitte'][1] - TUER_MITTE[1]) < 0.05
    assert wahl['tuerbreit'] and wahl['sicherheit'] == 0.85
    # Vom Roboter am Ende der Runde aus (Blick 95°) liegt die Tür rechts.
    assert wahl['richtung_ende_grad'] == pytest.approx(-97.7, abs=2.0)
    # Die Datei lässt sich lesen, solange sie frisch ist.
    assert wahl_lesen(json.dumps(wahl), jetzt_s=JETZT + 60.0)['nr'] == tuer.nr


def test_satz_fuer_den_menschen_nennt_nur_masse_vom_roboter_aus(runde_mit_karte, vorbereitung):
    tuer = _tuer(vorbereitung)
    stand = standpunkt_in_der_karte(runde_mit_karte.karte, vorbereitung.gier_ende_rad)
    wahl = wahl_aufschreiben(vorbereitung, _eintrag(tuer.nr), stand, jetzt_s=JETZT)
    satz = wahl_satz(wahl)
    assert satz.startswith(f'Die KI wählt Nr. {tuer.nr}: offene Tür, ')
    assert 'sicher zu' not in satz
    assert ' m breit, ' in satz and ' m entfernt, ' in satz and '° rechts von seiner' in satz
    for zahl in wahl['mitte']:
        assert f'{zahl:.2f}'.replace('.', ',') not in satz
        assert f'{zahl:.2f}' not in satz
    zu_breit = dict(wahl, tuerbreit=False, breite_m=1.25, richtung_ende_grad=1.0,
                    sicherheit=None, einordnung='durchgang')
    satz = wahl_satz(zu_breit)
    assert 'Durchgang, 1,25 m breit' in satz and 'geradeaus' in satz
    assert 'nur 0,65 bis 0,95 m' in satz and 'sicher zu' not in satz


@pytest.mark.parametrize('eintrag, grund', [
    ({'fehler': 'zeitgrenze'}, 'keine Antwort der KI (zeitgrenze)'),
    ({'fehler': None, 'pruefung': {'gueltig': False, 'fehler': ['kein_json']}},
     'Antwort der KI verworfen (kein_json)'),
    (_eintrag(None), 'die KI nennt keinen geeigneten Ausgang'),
    (_eintrag(1, nachmessen='zu_schmal'), 'die Vermessung spricht gegen die Wahl (zu_schmal)'),
    (_eintrag(7), 'Nummer 7 ist nicht vermessen'),
])
def test_ohne_brauchbare_wahl_wird_nichts_uebergeben(vorbereitung, eintrag, grund):
    with pytest.raises(ValueError, match=grund.replace('(', r'\(').replace(')', r'\)')):
        wahl_aufschreiben(vorbereitung, eintrag, (0.0, 0.0, 0.0), jetzt_s=JETZT)


def test_ohne_lage_in_der_karte_wird_nichts_uebergeben(vorbereitung):
    with pytest.raises(ValueError, match='Lage der Runde in der Karte fehlt'):
        wahl_aufschreiben(vorbereitung, _eintrag(_tuer(vorbereitung).nr), None, jetzt_s=JETZT)


def _gueltige_wahl(**aenderung):
    wahl = {'schema': WAHL_SCHEMA, 'art': 'ki_wahl', 'quelle': 'ki', 'rahmen': 'map',
            'nr': 2, 'mitte': [4.0, 1.4], 'erzeugt_s': JETZT}
    wahl.update(aenderung)
    return json.dumps(wahl)


@pytest.mark.parametrize('text, jetzt, grund', [
    ('kein json', JETZT, 'kein JSON'),
    ('[1, 2]', JETZT, 'keine Wahl der KI'),
    (_gueltige_wahl(art='fahrziel'), JETZT, 'keine Wahl der KI'),
    (_gueltige_wahl(schema=2), JETZT, 'unbekanntes Schema'),
    (_gueltige_wahl(quelle='mensch'), JETZT, 'Quelle ist nicht die KI'),
    (_gueltige_wahl(rahmen='odom'), JETZT, "Rahmen 'odom' statt 'map'"),
    (_gueltige_wahl(nr=True), JETZT, 'Nummer fehlt'),
    (_gueltige_wahl(nr='2'), JETZT, 'Nummer fehlt'),
    (_gueltige_wahl(mitte=[4.0]), JETZT, 'Ort in der Karte fehlt'),
    (_gueltige_wahl(mitte=[4.0, None]), JETZT, 'Ort in der Karte fehlt'),
    (_gueltige_wahl(erzeugt_s='gestern'), JETZT, 'Zeit fehlt'),
    (_gueltige_wahl(), JETZT - 60.0, 'Zukunft'),
    (_gueltige_wahl(), JETZT + MAX_ALTER_S + 1.0, 'gilt höchstens 900 s'),
])
def test_wahl_datei_wird_streng_gelesen(text, jetzt, grund):
    with pytest.raises(ValueError, match=grund):
        wahl_lesen(text, jetzt_s=jetzt)


def _oeffnung(nr, mitte, breite=0.80):
    (mx, my) = mitte
    return Oeffnung(nr=nr, breite_m=breite, mitte=(mx, my),
                    pfosten=((mx, my - breite / 2), (mx, my + breite / 2)),
                    richtung_grad=math.degrees(math.atan2(my, mx)),
                    entfernung_m=math.hypot(mx, my), tiefe_m=1.5, befahrbar=True)


def test_neu_vermessene_tuer_wird_der_wahl_zugeordnet():
    pose = (1.0, 1.0, math.radians(90.0))           # Roboter blickt in der Karte nach +y
    wahl = {'mitte': [0.9, 3.1]}                     # 2,1 m voraus, 0,1 m rechts
    nah, fern = _oeffnung(1, (2.05, 0.08)), _oeffnung(2, (1.0, -1.5))
    gewaehlt, abstand = zur_wahl([fern, nah], wahl, pose)
    assert gewaehlt is nah and abstand == pytest.approx(math.hypot(0.05, 0.02), abs=1e-6)


def test_ohne_passende_tuer_oder_bei_zwei_gleich_nahen_keine_zuordnung():
    pose = (0.0, 0.0, 0.0)
    with pytest.raises(ValueError, match='keine türbreite Öffnung vermessen; die nächste liegt'):
        zur_wahl([_oeffnung(1, (2.0, 1.0))], {'mitte': [2.0, 0.0]}, pose)
    with pytest.raises(ValueError, match=r'2,0 m entfernt, \+0°\) ist keine'):
        zur_wahl([], {'mitte': [2.0, 0.0]}, pose)
    zwei = [_oeffnung(1, (2.0, 0.30)), _oeffnung(2, (2.0, -0.32))]
    with pytest.raises(ValueError, match='Nummern 1 und 2'):
        zur_wahl(zwei, {'mitte': [2.0, 0.0]}, pose)
    # Liegt die zweite klar weiter weg, gilt die nähere.
    klar = [_oeffnung(1, (2.0, 0.05)), _oeffnung(2, (2.0, -0.38))]
    assert zur_wahl(klar, {'mitte': [2.0, 0.0]}, pose)[0].nr == 1


def test_wahl_aus_runde_findet_die_tuer_in_einer_neuen_messung_wieder(runde_mit_karte,
                                                                      vorbereitung):
    """Wie am Roboter: Runde -> Wahl-Datei -> neue Messung von einem anderen Platz."""
    tuer = _tuer(vorbereitung)
    stand = standpunkt_in_der_karte(runde_mit_karte.karte, vorbereitung.gier_ende_rad)
    wahl = wahl_lesen(json.dumps(wahl_aufschreiben(vorbereitung, _eintrag(tuer.nr), stand,
                                                   jetzt_s=JETZT)), jetzt_s=JETZT + 30.0)
    # Neuer Platz 1,2 m vor der Tür, Blick zur Tür; dort vermessen: Tür und Glastür.
    pose = (2.8, 1.45, 0.0)
    tuer_neu = _oeffnung(5, im_standpunktrahmen(TUER_MITTE, pose), 0.78)
    glas_neu = _oeffnung(6, im_standpunktrahmen((1.45, 0.0), pose), 0.88)
    gewaehlt, abstand = zur_wahl([glas_neu, tuer_neu], wahl, pose)
    assert gewaehlt.nr == 5 and abstand < 0.05
    assert np.isfinite(abstand)
