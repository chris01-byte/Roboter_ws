"""Fahrziel: aus der gewählten Öffnung zwei Punkte für die Etappenfahrt."""
import json
import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'werkzeuge'))

from fahrziel_senden import (  # noqa: E402
    lage_text, lies_punkt, protokoll_text, tabelle, waehle_oeffnung,
)

from lotse.fahrziel import (  # noqa: E402
    aufstellung, aufstellung_hinweise, botschaft, durch_die_tuer, geradeaus,
    im_kartenrahmen, pruefe_grenzen, punkt_relativ, tuer_punkte,
)
from lotse.kandidaten import Oeffnung  # noqa: E402


def oeffnung(nr, richtung_grad, breite=0.85, entfernung=2.0, befahrbar=True):
    r = math.radians(richtung_grad)
    mitte = (entfernung * math.cos(r), entfernung * math.sin(r))
    quer = (-math.sin(r) * breite / 2, math.cos(r) * breite / 2)
    pfosten = ((mitte[0] - quer[0], mitte[1] - quer[1]),
               (mitte[0] + quer[0], mitte[1] + quer[1]))
    return Oeffnung(nr, breite, mitte, pfosten, richtung_grad, entfernung, 1.5, befahrbar)


def test_vorpunkt_und_auslaufpunkt_liegen_auf_der_tuerachse():
    # Tür in der Wand x = 2, von y = -0,4 bis 0,45; der Roboter steht bei x = 0
    vor, hinter = tuer_punkte(((2.0, -0.40), (2.0, 0.45)))
    assert vor == pytest.approx((0.90, 0.025))          # 1,1 m vor der Türlinie
    assert hinter == pytest.approx((2.60, 0.025))
    vor, hinter = tuer_punkte(((2.0, -0.40), (2.0, 0.45)), vor_m=0.7, hinter_m=0.45)
    assert vor == pytest.approx((1.30, 0.025)) and hinter == pytest.approx((2.45, 0.025))
    vor, hinter = tuer_punkte(((2.0, -0.40), (2.0, 0.45)))
    # Reihenfolge der Pfosten ist gleichgültig
    assert tuer_punkte(((2.0, 0.45), (2.0, -0.40))) == (pytest.approx(vor), pytest.approx(hinter))


def test_die_achse_zeigt_immer_vom_standpunkt_weg():
    vor, hinter = tuer_punkte(((2.0, -0.4), (2.0, 0.4)), standpunkt=(3.5, 0.0))
    assert vor == pytest.approx((3.1, 0.0)) and hinter == pytest.approx((1.4, 0.0))


def test_schraege_tuer_die_achse_steht_senkrecht_auf_der_tuerlinie():
    a, b = (1.5, 0.5), (2.1, 1.1)                       # 45° schräge Wand
    vor, hinter = tuer_punkte((a, b), vor_m=0.5, hinter_m=0.5)
    mitte = (1.8, 0.8)
    for punkt in (vor, hinter):
        # senkrecht auf der Pfostenlinie: Skalarprodukt mit der Türrichtung ist null
        assert ((punkt[0] - mitte[0]) * (b[0] - a[0])
                + (punkt[1] - mitte[1]) * (b[1] - a[1])) == pytest.approx(0.0, abs=1e-9)
        assert math.hypot(punkt[0] - mitte[0], punkt[1] - mitte[1]) == pytest.approx(0.5)
    assert math.hypot(*vor) < math.hypot(*hinter)       # der Vorpunkt liegt auf unserer Seite


@pytest.mark.parametrize('pfosten, standpunkt, grund', [
    (((2.0, -0.2), (2.0, 0.2)), (0.0, 0.0), '0.40 m breit'),
    (((2.0, -0.4), (2.0, 0.4)), (2.0, 0.0), 'in der Türlinie'),
    (((2.0, float('nan')), (2.0, 0.4)), (0.0, 0.0), 'endlich'),
])
def test_unbrauchbare_oeffnung_wird_abgelehnt(pfosten, standpunkt, grund):
    with pytest.raises(ValueError, match=grund):
        tuer_punkte(pfosten, standpunkt)


def test_punkte_wandern_mit_der_lage_des_roboters_in_die_karte():
    assert im_kartenrahmen((1.0, 0.0), (2.0, 3.0, math.pi / 2)) == pytest.approx((2.0, 4.0))
    assert im_kartenrahmen((1.0, 0.5), (0.0, 0.0, math.pi)) == pytest.approx((-1.0, -0.5))
    assert geradeaus(0.5, (1.0, 1.0, math.pi / 2)) == [pytest.approx((1.0, 1.5))]
    with pytest.raises(ValueError, match='außerhalb'):
        geradeaus(3.0, (0.0, 0.0, 0.0))


def test_durch_die_tuer_zwei_punkte_in_der_karte_oder_einer_wenn_man_schon_davor_steht():
    pfosten = ((2.0, -0.4), (2.0, 0.4))
    punkte = durch_die_tuer(pfosten, (10.0, 5.0, math.pi / 2))
    assert punkte == [pytest.approx((10.0, 5.9)), pytest.approx((10.0, 7.6))]
    # der Roboter steht schon am Vorpunkt oder näher, auf der Achse: nur der Auslaufpunkt
    for abstand in (1.1, 0.7):
        nah = ((abstand, -0.4), (abstand, 0.4))
        assert durch_die_tuer(nah, (0.0, 0.0, 0.0)) == [pytest.approx((abstand + 0.6, 0.0))]
    # so nah und dazu neben der Achse: kein Ziel (zurück wird nicht gefahren)
    with pytest.raises(ValueError, match='zu nah an der Tür .0.70 m. und 0.30 m neben'):
        durch_die_tuer(((0.7, -0.1), (0.7, 0.7)), (0.0, 0.0, 0.0))


def test_grenzen_werden_mit_mass_genannt():
    assert pruefe_grenzen([(1.3, 0.0), (2.6, 0.0)], (0.0, 0.0)) == pytest.approx(2.6)
    with pytest.raises(ValueError, match='Strecke 1 ist 3.10 m lang, erlaubt 2.5 m'):
        pruefe_grenzen([(3.1, 0.0)], (0.0, 0.0))
    with pytest.raises(ValueError, match='zusammen 4.40 m, erlaubt 4.0 m'):
        pruefe_grenzen([(2.2, 0.0), (4.4, 0.0)], (0.0, 0.0))
    with pytest.raises(ValueError, match='Strecke 2 ist nur 0.05 m'):
        pruefe_grenzen([(1.0, 0.0), (1.05, 0.0)], (0.0, 0.0))
    with pytest.raises(ValueError, match='0 Punkte'):
        pruefe_grenzen([], (0.0, 0.0))


def test_botschaft_nennt_wer_gewaehlt_hat_und_passt_zum_erkunder():
    text = botschaft([(1.23456, 2.0), (2.5, 2.0)], kennung='tuer-1', quelle='ki',
                     zeit_s=1_800_000_000.0, bemerkung='Öffnung 2')
    daten = json.loads(text)
    assert daten == {'kennung': 'tuer-1', 'quelle': 'ki', 'frame': 'map',
                     'zeit_s': 1_800_000_000.0, 'punkte': [[1.235, 2.0], [2.5, 2.0]],
                     'bemerkung': 'Öffnung 2'}
    with pytest.raises(ValueError, match='Quelle'):
        botschaft([(1.0, 0.0)], kennung='x', quelle='regel', zeit_s=0.0)
    with pytest.raises(ValueError, match='Kennung'):
        botschaft([(1.0, 0.0)], kennung='', quelle='ki', zeit_s=0.0)


def test_der_erkunder_nimmt_genau_diese_botschaft_an():
    """Dieselbe Prüfung wie im Erkunder, gegen dessen Quelltext gelesen."""
    quelle = (Path(__file__).resolve().parents[2] / 'src' / 'explore' / 'explore'
              / 'stage_drive.py')
    namen = {}
    exec(compile(quelle.read_text(encoding='utf-8'), str(quelle), 'exec'), namen)
    text = botschaft(durch_die_tuer(((2.0, -0.4), (2.0, 0.45)), (0.0, 0.0, 0.0)),
                     kennung='tuer-1', quelle='ki', zeit_s=1000.0)
    ziel = namen['parse_stage_target'](
        text, frame='map', now_s=1001.0, start_xy=(0.0, 0.0),
        limits=namen['StageLimits']())
    assert ziel.quelle == 'ki' and len(ziel.punkte) == 2
    assert ziel.laenge_m == pytest.approx(2.6, abs=0.01)
    # die Grenzen beider Seiten sind dieselben
    from lotse import fahrziel
    grenzen = namen['StageLimits']()
    assert (grenzen.max_points, grenzen.min_leg_m, grenzen.max_leg_m, grenzen.max_total_m) == (
        fahrziel.MAX_PUNKTE, fahrziel.MIN_STRECKE_M, fahrziel.MAX_STRECKE_M,
        fahrziel.MAX_GESAMT_M)


def test_wahl_der_oeffnung_nach_nummer_richtung_oder_wenn_es_nur_eine_gibt():
    liste = [oeffnung(1, -60.0), oeffnung(2, 15.0), oeffnung(3, 120.0, breite=2.0),
             oeffnung(4, 40.0, befahrbar=False)]
    assert waehle_oeffnung(liste, nummer=2).nr == 2
    assert waehle_oeffnung(liste, richtung_grad=20.0).nr == 2
    assert waehle_oeffnung(liste, richtung_grad=-50.0).nr == 1
    assert waehle_oeffnung([oeffnung(1, -60.0)]).nr == 1
    assert waehle_oeffnung(liste, richtung_grad=110.0, nur_tuergross=False).nr == 3
    # über die Nahtstelle bei ±180° hinweg
    assert waehle_oeffnung([oeffnung(1, 175.0)], richtung_grad=-175.0).nr == 1


@pytest.mark.parametrize('kw, grund', [
    (dict(nummer=3), 'Nummer 3 ist keine befahrbare, türgroße Öffnung'),
    (dict(nummer=4), 'Nummer 4 ist keine befahrbare'),
    (dict(nummer=9), 'Nummer 9'),
    (dict(), '2 Öffnungen kommen in Frage'),
    (dict(richtung_grad=90.0), 'keine Öffnung innerhalb von 25°'),
])
def test_ohne_eindeutige_oeffnung_wird_nichts_gewaehlt(kw, grund):
    liste = [oeffnung(1, -60.0), oeffnung(2, 15.0), oeffnung(3, 120.0, breite=2.0),
             oeffnung(4, 40.0, befahrbar=False)]
    with pytest.raises(ValueError, match=grund):
        waehle_oeffnung(liste, **kw)


def test_zwei_gleich_nahe_oeffnungen_sind_nicht_eindeutig():
    liste = [oeffnung(1, 10.0), oeffnung(2, 22.0)]
    with pytest.raises(ValueError, match='gleich nah'):
        waehle_oeffnung(liste, richtung_grad=15.0)
    assert waehle_oeffnung(liste, richtung_grad=8.0).nr == 1
    with pytest.raises(ValueError, match='keine befahrbare'):
        waehle_oeffnung([oeffnung(1, 0.0, befahrbar=False)])


def test_tabelle_nennt_nur_masse():
    text = tabelle([oeffnung(1, -60.0), oeffnung(2, 15.0, befahrbar=False)])
    assert text.splitlines()[0].startswith('Nr  Breite  Richtung')
    assert ' 1   0.85 m    -60.0°      2.00 m         ja  sprung' in text
    assert 'nein' in text.splitlines()[2]


def test_punkt_vom_roboter_aus_voraus_und_links():
    assert punkt_relativ(0.40, 0.25, (0.0, 0.0, 0.0)) == [pytest.approx((0.40, 0.25))]
    # der Roboter blickt nach +y: „links“ ist dann -x
    assert punkt_relativ(0.40, 0.25, (1.0, 1.0, math.pi / 2)) == [pytest.approx((0.75, 1.40))]
    assert punkt_relativ(0.40, -0.25, (0.0, 0.0, 0.0)) == [pytest.approx((0.40, -0.25))]
    with pytest.raises(ValueError, match='vor dem Roboter'):
        punkt_relativ(-0.3, 0.2, (0.0, 0.0, 0.0))
    with pytest.raises(ValueError, match='erlaubt'):
        punkt_relativ(3.0, 0.0, (0.0, 0.0, 0.0))
    with pytest.raises(ValueError, match='erlaubt'):
        punkt_relativ(0.05, 0.0, (0.0, 0.0, 0.0))


def test_punkt_aus_der_befehlszeile():
    assert lies_punkt('0.40,0.25') == (0.40, 0.25)
    assert lies_punkt('0.5,-0.2') == (0.5, -0.2)
    for text in ('0.4', '0.4;0.2', 'a,b', '0.4,0.2,0.1'):
        with pytest.raises(ValueError, match='Punkt'):
            lies_punkt(text)


def test_aufstellung_abstand_versatz_und_winkel_zur_tuerachse():
    # genau davor, Blick durch die Tür
    lage = aufstellung(((2.0, -0.425), (2.0, 0.425)))
    assert lage == pytest.approx(
        {'breite_m': 0.85, 'abstand_m': 2.0, 'seitlich_m': 0.0, 'winkel_grad': 0.0})
    # die Türmitte liegt 0,3 m rechts vom Roboter: er steht links der Achse
    lage = aufstellung(((2.0, -0.725), (2.0, 0.125)))
    assert lage['seitlich_m'] == pytest.approx(0.3) and lage['abstand_m'] == pytest.approx(2.0)
    # Tür in einer Wand, die 30° gedreht ist: die Achse liegt 30° links
    c, s_ = math.cos(math.radians(30)), math.sin(math.radians(30))
    mitte = (2.0 * c, 2.0 * s_)
    quer = (-s_ * 0.425, c * 0.425)
    pfosten = ((mitte[0] - quer[0], mitte[1] - quer[1]), (mitte[0] + quer[0], mitte[1] + quer[1]))
    lage = aufstellung(pfosten)
    assert lage['winkel_grad'] == pytest.approx(30.0)
    assert lage['abstand_m'] == pytest.approx(2.0) and lage['seitlich_m'] == pytest.approx(0.0)
    # dieselbe Tür, der Roboter blickt schon 30° nach links
    assert aufstellung(pfosten, blick_rad=math.radians(30))['winkel_grad'] == pytest.approx(0.0)
    # Reihenfolge der Pfosten gleichgültig
    assert aufstellung(pfosten[::-1]) == pytest.approx(lage)


def test_hinweise_sagen_was_an_der_aufstellung_zu_aendern_ist():
    assert aufstellung_hinweise(aufstellung(((2.0, -0.425), (2.0, 0.425)))) == []
    assert aufstellung_hinweise(aufstellung(((2.0, -0.60), (2.0, 0.25)))) == []   # 17 cm daneben
    zu_nah = aufstellung_hinweise(aufstellung(((1.2, -0.425), (1.2, 0.425))))
    assert zu_nah == ['zu nah an der Tür (1.20 m bis zur Türlinie): bitte auf '
                      '1.5 bis 2.6 m zurückstellen']
    zu_weit = aufstellung_hinweise(aufstellung(((3.0, -0.425), (3.0, 0.425))))
    assert 'zu weit von der Tür (3.00 m' in zu_weit[0]
    links = aufstellung_hinweise(aufstellung(((2.0, -0.925), (2.0, -0.075))))
    assert links == ['steht 0.50 m links neben der Türmitte: bitte etwa 50 cm nach '
                     'rechts versetzen']
    rechts = aufstellung_hinweise(aufstellung(((2.0, 0.075), (2.0, 0.925))))
    assert 'rechts neben der Türmitte' in rechts[0] and 'nach links versetzen' in rechts[0]
    gedreht = aufstellung_hinweise(
        aufstellung(((2.0, -0.425), (2.0, 0.425)), blick_rad=math.radians(40)))
    assert gedreht == ['die Tür liegt 40° rechts von seiner Blickrichtung: bitte nach '
                       'rechts zur Tür drehen']


def test_die_lage_von_kif1_schraeg_vor_der_tuer_wird_als_unpassend_gemeldet():
    # KI-F1: „Tür“ 1,25 m breit, 32° rechts, 1,59 m entfernt (falsch vermessen)
    o = oeffnung(1, -31.9, breite=1.25, entfernung=1.59)
    with pytest.raises(ValueError, match='keine Öffnung ist türbreit vermessen .0.65 bis '
                                         '0.95 m.; vermessen: 1.25 m'):
        waehle_oeffnung([o], richtung_grad=-31.9, breite_von_m=0.65, breite_bis_m=0.95)
    # ohne das Fenster wäre sie gewählt worden
    assert waehle_oeffnung([o], richtung_grad=-31.9).nr == 1
    # eine richtig vermessene Tür daneben wird genommen
    tuer = oeffnung(2, 4.0, breite=0.77, entfernung=2.0)
    assert waehle_oeffnung([o, tuer], breite_von_m=0.65, breite_bis_m=0.95).nr == 2


def test_lage_in_einem_satz():
    text = lage_text(oeffnung(1, 0.0, breite=0.80, entfernung=2.0))
    assert text == ('Nr. 1: 2.00 m vor der Türlinie, 0.00 m rechts neben der Türmitte, '
                    'Tür 0° rechts von der Blickrichtung – Aufstellung passt.')
    text = lage_text(oeffnung(3, -32.0, breite=0.80, entfernung=1.6))
    assert 'Aufstellung passt nicht' in text and 'bitte nach rechts zur Tür drehen' in text


def test_protokoll_nennt_nur_masse_vom_roboter_aus():
    protokoll = [
        {'pfosten': [[-52.0, 1.2], [-12.3, 2.1]], 'ergebnis': 'angeboten', 'nr': 1,
         'schluss': 'sprung', 'breite_m': 1.25, 'richtung_grad': -31.9, 'entfernung_m': 1.59,
         'strahlen': 80, 'tiefe_m': 1.6, 'anteil_tief': 1.0, 'anteil_davor': 0.0,
         'blatt': None},
        {'pfosten': [[10.0, 1.9], [26.0, 1.9]], 'ergebnis': 'zu_flach', 'nr': None,
         'schluss': 'linie', 'breite_m': 0.55, 'richtung_grad': 18.0, 'entfernung_m': 1.9,
         'strahlen': 30, 'tiefe_m': 0.11, 'anteil_tief': 0.0, 'anteil_davor': 0.0,
         'blatt': 'wand_krumm_0.024'},
        {'pfosten': [[100.0, 3.0], [160.0, 3.0]], 'ergebnis': 'zu_flach', 'nr': None,
         'schluss': 'sprung', 'breite_m': 3.0, 'richtung_grad': 130.0, 'entfernung_m': 2.6,
         'strahlen': 90, 'tiefe_m': None, 'anteil_tief': None, 'anteil_davor': None,
         'blatt': None},
    ]
    zeilen = protokoll_text(protokoll).splitlines()
    assert zeilen[0] == 'Protokoll der Vermessung (Maße vom Roboter aus):'
    assert zeilen[1] == ('  angeboten  1.25 m   -31.9°  1.59 m  sprung Kanten -52.0°/1.20 m · '
                         '-12.3°/2.10 m  tief 1.60 m (100 %), davor 0 %  Vermerk –')
    assert 'zu_flach' in zeilen[2] and 'Vermerk wand_krumm_0.024' in zeilen[2]
    assert len(zeilen) == 3                              # die 3 m breite Lücke fehlt
