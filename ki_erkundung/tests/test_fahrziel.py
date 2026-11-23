"""Fahrziel: aus der gewählten Öffnung zwei Punkte für die Etappenfahrt."""
import json
import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'werkzeuge'))

from fahrziel_senden import (  # noqa: E402
    anfahrt_zeile, lage_text, lies_punkt, protokoll_text, tabelle, waehle_oeffnung, weg_text,
)

from lotse.fahrziel import (  # noqa: E402
    DREHKREIS_M, anfahrt, anfahrt_im_kartenrahmen, anfahrt_text, aufstellung,
    aufstellung_hinweise, botschaft, durch_die_tuer, frei_gesehen, frei_um, freiraum,
    freiraum_hinweise, gerade_durch_die_tuer, gerade_linie, geradeaus, im_kartenrahmen,
    kostenkarte_text, kostenkarte_voraus, pruefe_grenzen, punkt_relativ, tuer_punkte,
    wandrichtung,
)
from lotse.fahrziel import (  # noqa: E402
    FREI_NEBEN_DER_LINIE_M, achse_aus_karte, ende_botschaft, tuer_merken, wiederfinden,
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


# ---------------- gerade Linie durch die Türmitte (seit KI-F2) ----------------
def kif2():
    """Die Lage vom 22.11.2026 (KI-F2), aus den Maßen des Berichts.

    Türkanten bei -10,0°/1,90 m und +12,7°/1,97 m; das Türblatt steht am
    linken Pfosten 85° zur Türöffnung in den Raum, 0,85 m lang.
    """
    rechts = (1.90 * math.cos(math.radians(-10.0)), 1.90 * math.sin(math.radians(-10.0)))
    links = (1.97 * math.cos(math.radians(12.7)), 1.97 * math.sin(math.radians(12.7)))
    breite = math.hypot(links[0] - rechts[0], links[1] - rechts[1])
    achse = ((links[1] - rechts[1]) / breite, -(links[0] - rechts[0]) / breite)
    hinein = (-(links[0] - rechts[0]) / breite, -(links[1] - rechts[1]) / breite)
    w = math.radians(85.0)
    richtung = (math.cos(w) * hinein[0] - math.sin(w) * achse[0],
                math.cos(w) * hinein[1] - math.sin(w) * achse[1])
    blatt = [(links[0] + 0.85 * t / 40 * richtung[0], links[1] + 0.85 * t / 40 * richtung[1])
             for t in range(41)]
    wand = ([(rechts[0], rechts[1] - 0.02 * i) for i in range(40)]
            + [(links[0], links[1] + 0.02 * i) for i in range(40)])
    return (rechts, links), blatt, wand


def test_gerade_linie_geht_vom_standplatz_durch_die_tuermitte():
    pfosten = ((2.0, -0.425), (2.0, 0.425))
    assert gerade_linie(pfosten) == [pytest.approx((0.8, 0.0)), pytest.approx((2.6, 0.0))]
    # seitlich versetzt: alle Punkte liegen auf der Linie durch die Türmitte
    pfosten = ((2.0, -0.225), (2.0, 0.625))            # Türmitte bei y = 0,2
    punkte = gerade_linie(pfosten, hinter_m=0.45)
    for x, y in punkte:
        assert y == pytest.approx(0.1 * x)             # Steigung 0,2 / 2,0
    assert punkte[0][0] == pytest.approx(0.8) and punkte[1][0] == pytest.approx(2.45)
    # nah vor der Tür entfällt der Zwischenpunkt
    assert gerade_linie(((1.5, -0.425), (1.5, 0.425))) == [pytest.approx((2.1, 0.0))]
    assert len(gerade_linie(((1.6, -0.425), (1.6, 0.425)))) == 2


def test_gerade_linie_lehnt_zu_schraege_und_zu_schmale_durchfahrten_ab():
    with pytest.raises(ValueError, match='schräg durch die Tür, erlaubt 10°'):
        gerade_linie(((2.0, 0.1), (2.0, 0.95)))        # Türmitte 0,525 m seitlich: 15°
    with pytest.raises(ValueError, match='0.40 m breit'):
        gerade_linie(((2.0, -0.2), (2.0, 0.2)))
    with pytest.raises(ValueError, match='Türlinie'):
        gerade_linie(((0.0, -0.4), (0.0, 0.4)))


def test_gerade_linie_im_kartenrahmen_und_innerhalb_der_grenzen_des_erkunders():
    pfosten = ((2.5, -0.425), (2.5, 0.425))
    punkte = gerade_durch_die_tuer(pfosten, (10.0, 5.0, math.pi / 2), hinter_m=0.45)
    assert punkte == [pytest.approx((10.0, 6.3)), pytest.approx((10.0, 7.95))]
    assert pruefe_grenzen(punkte, (10.0, 5.0)) == pytest.approx(2.95)


def test_kif2_die_alte_linie_fuehrte_an_der_blattspitze_vorbei_die_gerade_nicht():
    pfosten, blatt, wand = kif2()
    # alter Plan: zuerst zum Vorpunkt auf der Türachse, 1,1 m vor der Türlinie
    vorpunkt, _ = tuer_punkte(pfosten, vor_m=1.1, hinter_m=0.45)
    peilung = math.degrees(math.atan2(vorpunkt[1], vorpunkt[0]))
    assert peilung == pytest.approx(8.9, abs=0.3)             # Bericht: +8,6°
    # Auf dieser Strecke (bis die Vorderkante am Vorpunkt steht) liegt die
    # Blattspitze 0,245 m neben der Fahrlinie: im Streifen des Nahbereichs-Halts
    # (0,255 m) und 1,5 cm neben dem Gehäuse (0,23 m)
    alt = freiraum(blatt, vorpunkt)
    assert alt['links_m'] == pytest.approx(0.245, abs=0.01)
    assert alt['links_m'] < 0.255
    assert alt['links_voraus_m'] == pytest.approx(1.12, abs=0.03)
    # neue Linie: gerade durch die Türmitte, 38 cm frei auf beiden Seiten
    linie = gerade_linie(pfosten, hinter_m=0.45)
    neu = freiraum(blatt + wand, linie[-1])
    assert neu['links_m'] == pytest.approx(0.38, abs=0.01)
    assert neu['rechts_m'] == pytest.approx(0.38, abs=0.01)
    assert freiraum_hinweise(neu) == []


def test_freiraum_misst_links_und_rechts_neben_der_linie():
    frei = freiraum([(1.0, 0.4), (1.5, -0.35), (0.5, 0.9), (3.0, 0.1), (0.1, 0.05)], (2.0, 0.0))
    assert frei['links_m'] == pytest.approx(0.4) and frei['links_voraus_m'] == pytest.approx(1.0)
    assert frei['rechts_m'] == pytest.approx(0.35) and frei['laenge_m'] == pytest.approx(2.0)
    # hinter dem Ziel zählt nur noch, was die Vorderkante erreicht (0,33 m)
    assert freiraum([(2.3, 0.1)], (2.0, 0.0))['links_m'] == pytest.approx(0.1)
    assert freiraum([(2.4, 0.1)], (2.0, 0.0))['links_m'] == math.inf
    # schräge Linie
    frei = freiraum([(1.0, 1.0 + 0.3 * math.sqrt(2))], (2.0, 2.0))
    assert frei['links_m'] == pytest.approx(0.3)
    with pytest.raises(ValueError, match='fallen zusammen'):
        freiraum([], (0.0, 0.0))


def test_hinweise_zum_freiraum_nennen_seite_mass_und_versatz():
    frei = freiraum([(1.0, 0.22), (2.0, -0.4)], (2.5, 0.0))
    hinweise = freiraum_hinweise(frei)
    assert hinweise == ['links neben der Fahrlinie sind nur 0.22 m frei (1.0 m voraus), '
                        'nötig 0.26 m: bitte etwa 10 cm nach rechts versetzen']
    # ein Hindernis an der Tür selbst lässt sich durch Versetzen nicht umgehen
    hinweise = freiraum_hinweise(freiraum([(2.3, -0.2)], (2.5, 0.0)))
    assert hinweise == ['rechts neben der Fahrlinie sind nur 0.20 m frei (2.3 m voraus), '
                        'nötig 0.26 m: von hier ist die Durchfahrt zu knapp']
    assert freiraum_hinweise(freiraum([(1.0, 0.31), (1.0, -0.6)], (2.5, 0.0))) == []


def test_weg_in_einem_satz_fuer_die_lage_von_kif2():
    pfosten, blatt, wand = kif2()
    o = Oeffnung(1, 0.77, (1.896, 0.052), pfosten, 1.6, 1.90, 1.6, True)
    text, passt = weg_text(o, blatt + wand, 1.2, 0.45)
    assert passt is True
    assert text == ('Fahrlinie: gerade durch die Türmitte, 2.35 m; frei neben der Linie '
                    'links 0.38 m, rechts 0.38 m (nötig 0.26 m) – Weg passt.')
    # ragt die Blattspitze 14 cm weiter herein, passt der Weg nicht mehr
    text, passt = weg_text(o, blatt + wand + [(1.07, 0.25)], 1.2, 0.45)
    assert passt is False
    assert ('links neben der Fahrlinie sind nur 0.22 m frei (1.1 m voraus), nötig 0.26 m: '
            'bitte etwa 10 cm nach rechts versetzen') in text
    # ist die Tür selbst zu eng vermessen, hilft Versetzen nicht (mit 0,26 m je
    # Seite braucht es mindestens 0,52 m; das Blatt ragt hier 25 cm herein)
    eng = [(x, y - 0.25) for x, y in blatt]
    text, passt = weg_text(o, eng + wand, 1.2, 0.45)
    assert passt is False and 'von hier ist die Durchfahrt zu knapp' in text


# ----------------------- Kostenkarte vor dem Roboter -----------------------
def karte(belegt, breite=300, hoehe=300, zelle=0.01, ursprung=(-1.505, -1.505)):
    """Kostenkarte, deren Zellmitten auf vollen Zentimetern liegen."""
    import numpy as np
    daten = np.zeros(breite * hoehe, dtype=np.int8)
    for x, y in belegt:
        spalte = int(round((x - ursprung[0]) / zelle - 0.5))
        zeile = int(round((y - ursprung[1]) / zelle - 0.5))
        daten[zeile * breite + spalte] = 100
    return daten, breite, hoehe, zelle, ursprung


def test_kostenkarte_nennt_die_naechste_belegte_zelle_im_streifen_und_daneben():
    sicht = kostenkarte_voraus(*karte([(0.58, 0.24), (0.90, 0.40), (1.20, -0.30)]),
                               (0.0, 0.0, 0.0))
    assert sicht['im_streifen'] == pytest.approx((0.58, 0.24), abs=0.001)
    assert sicht['links_daneben'] == pytest.approx((0.90, 0.40), abs=0.001)
    assert sicht['rechts_daneben'] == pytest.approx((1.20, -0.30), abs=0.001)
    text = kostenkarte_text(sicht)
    assert 'im Fahrstreifen 0.25 m vor der Vorderkante, 0.24 m links der Mitte' in text
    assert 'so nah hält der Erkunder an' in text
    assert 'links daneben 0.57 m vor der Vorderkante, 0.40 m links der Mitte' in text
    assert 'rechts daneben 0.87 m vor der Vorderkante, 0.30 m rechts der Mitte' in text


def test_kostenkarte_ohne_hindernis_und_mit_gedrehtem_roboter():
    leer = kostenkarte_voraus(*karte([]), (0.0, 0.0, 0.0))
    assert leer['im_streifen'] is None and leer['zellen'] == 0
    assert 'im Fahrstreifen nichts; links daneben nichts; rechts daneben nichts.' in (
        kostenkarte_text(leer))
    # Hindernis bei (0, 0,8): mit Blick nach +y liegt es voraus im Streifen
    sicht = kostenkarte_voraus(*karte([(0.0, 0.8)]), (0.0, 0.0, math.pi / 2))
    assert sicht['im_streifen'][0] == pytest.approx(0.80, abs=0.001)
    assert 'so nah hält' not in kostenkarte_text(sicht)       # 0,47 m vor der Vorderkante
    # unter dem Roboter und hinter ihm zählt nichts
    assert kostenkarte_voraus(*karte([(0.1, 0.0), (-0.5, 0.0)]),
                              (0.0, 0.0, 0.0))['im_streifen'] is None
    with pytest.raises(ValueError, match='Größe'):
        kostenkarte_voraus([0, 0, 0], 2, 2, 0.01, (0.0, 0.0), (0.0, 0.0, 0.0))


# --- Anfahrt: der Roboter stellt sich selbst vor die Tür -------------------

def tuerwand(pose, blatt=False, dazu=()):
    """Ein Raum mit Tür, gesehen vom Roboter an ``pose`` (x, y, Gier im Raum).

    Raum 4,3 m × 4,3 m; die Tür (0,80 m) liegt in der Wand x = 4,3 zwischen
    y = 1,6 und 2,4. Rückgabe: Pfosten und Laserpunkte im Standpunktrahmen.
    """
    punkte = []
    for i in range(216):
        t = 0.02 * i
        if not 1.6 < t < 2.4:
            punkte.append((4.3, t))
        punkte += [(0.0, t), (t, 0.0), (t, 4.3)]
    if blatt:                                # 85° offen, am Pfosten y = 2,4, 0,85 m lang
        for i in range(43):
            t = 0.02 * i
            punkte.append((4.3 - t * math.cos(math.radians(5)),
                           2.4 - t * math.sin(math.radians(5))))
    punkte += list(dazu)
    x, y, gier = pose
    c, s_ = math.cos(gier), math.sin(gier)

    def hin(q):
        return (c * (q[0] - x) + s_ * (q[1] - y), -s_ * (q[0] - x) + c * (q[1] - y))

    return (hin((4.3, 1.6)), hin((4.3, 2.4))), [hin(q) for q in punkte]


def im_raum(punkt, pose):
    return im_kartenrahmen(punkt, pose)


def test_anfahrt_aus_der_raummitte_endet_mittig_vor_der_tuer_mit_blick_zur_tuer():
    pose = (2.0, 2.9, -0.3)                  # 0,9 m neben der Türachse, schräg
    pfosten, laser = tuerwand(pose, blatt=True)
    assert aufstellung_hinweise(aufstellung(pfosten))        # von Hand passte das nicht
    weg = anfahrt(pfosten, laser)
    assert len(weg['punkte']) == 2
    vorpunkt, ende = (im_raum(q, pose) for q in weg['punkte'])
    # beide Punkte auf der Türachse y = 2,0; das Ende 1,6 bis 2,1 m vor der Türlinie
    assert vorpunkt[1] == pytest.approx(2.0, abs=1e-6) and ende[1] == pytest.approx(2.0, abs=1e-6)
    assert 4.3 - ende[0] == pytest.approx(weg['vor_m']) and 1.6 <= weg['vor_m'] <= 2.1
    assert ende[0] - vorpunkt[0] == pytest.approx(0.45)      # das letzte Stück zur Tür hin
    assert weg['schraeg_grad'] == pytest.approx(0.0, abs=1e-6)
    # so, wie er danach steht, passt die Aufstellung für die Durchfahrt
    danach = (ende[0], ende[1], 0.0)
    assert aufstellung_hinweise(aufstellung(tuerwand(danach)[0])) == []
    assert pruefe_grenzen(anfahrt_im_kartenrahmen(weg, pose), pose[:2]) < 4.0
    text = anfahrt_text(weg)
    assert text.startswith('Anfahrt: ') and 'nach rechts drehen' in text
    assert 'mittig vor der Tür' in text and 'nötig 0.26 m' in text


def test_anfahrt_auf_der_achse_braucht_keinen_vorpunkt():
    pose = (1.0, 2.0, 0.0)                   # 3,3 m vor der Tür, schon auf der Achse
    pfosten, laser = tuerwand(pose)
    weg = anfahrt(pfosten, laser)
    assert len(weg['punkte']) == 1 and weg['drehen_grad'] == [pytest.approx(0.0, abs=1e-6)]
    assert weg['strecken_m'][0] == pytest.approx(3.3 - weg['vor_m'])
    assert 'drehen' not in anfahrt_text(weg).split(';')[0]


def test_anfahrt_waehlt_den_weg_mit_dem_wenigsten_drehen():
    pose = (2.2, 2.0, math.pi / 2)           # auf der Achse, aber quer zur Tür
    pfosten, laser = tuerwand(pose)
    weg = anfahrt(pfosten, laser)
    assert len(weg['punkte']) == 1
    assert weg['drehen_grad'][0] == pytest.approx(-90.0)


def test_anfahrt_lehnt_ab_wenn_neben_dem_weg_etwas_steht():
    pose = (2.0, 2.9, -0.3)
    # eine Stange quer zwischen dem Roboter und der Türachse, 0,55 m vor ihm
    stange = [(1.5 + 0.02 * i, 2.35) for i in range(55)]
    pfosten, laser = tuerwand(pose, dazu=stange)
    with pytest.raises(ValueError, match='Anfahrt: auf Strecke 1 sind .* nur 0\\.\\d\\d m frei'):
        anfahrt(pfosten, laser)


def test_anfahrt_lehnt_ab_wenn_vor_der_tuer_kein_platz_zum_drehen_ist():
    pose = (2.0, 2.9, -0.3)
    # eine Stange längs neben der Türachse, 0,35 m daneben, vor der ganzen Tür
    stange = [(1.5 + 0.02 * i, 1.65) for i in range(70)]
    pfosten, laser = tuerwand(pose, dazu=stange)
    with pytest.raises(ValueError, match='Anfahrt: zum Drehen ist am Punkt vor der Tür nicht '
                                         'genug Platz \\(0\\.35 m frei, nötig 0\\.37 m\\)'):
        anfahrt(pfosten, laser)


def test_frei_gesehen_nur_wenn_der_laser_bis_zum_punkt_freie_sicht_hatte():
    winkel = [math.radians(-179.75 + 0.5 * i) for i in range(720)]
    profil = [3.0] * 720
    sicht = {'ursprung': (0.245, 0.0), 'winkel': winkel, 'profil': profil}
    assert frei_gesehen(sicht, (2.0, 0.0)) and frei_gesehen(sicht, (0.3, 0.0))
    assert not frei_gesehen(sicht, (3.5, 0.0))               # hinter der Wand
    assert frei_gesehen(sicht, (3.28, 0.0))                  # 5 cm Spiel an der Wand
    profil[359] = profil[360] = 1.0                          # etwas steht 1 m voraus
    assert not frei_gesehen(sicht, (2.0, 0.0))
    profil[359] = profil[360] = math.nan                     # dorthin nicht gemessen
    assert not frei_gesehen(sicht, (2.0, 0.0))
    profil[359] = profil[360] = math.inf                     # kein Echo: nichts im Weg
    assert frei_gesehen(sicht, (2.0, 0.0))
    assert frei_gesehen(None, (2.0, 0.0))                    # ohne Profil keine Prüfung


def test_anfahrt_lehnt_ab_was_der_laser_von_hier_nicht_einsieht():
    pose = (2.0, 2.9, -0.3)
    pfosten, laser = tuerwand(pose)
    winkel = [math.radians(-179.75 + 0.5 * i) for i in range(720)]
    # ein Schirm 0,6 m vor dem Laser verdeckt alles voraus und seitlich
    sicht = {'ursprung': (0.245, 0.0), 'winkel': winkel, 'profil': [0.6] * 720}
    with pytest.raises(ValueError, match='sieht der Laser von hier nicht'):
        anfahrt(pfosten, laser, sicht)
    frei = {'ursprung': (0.245, 0.0), 'winkel': winkel, 'profil': [6.0] * 720}
    assert len(anfahrt(pfosten, laser, frei)['punkte']) == 2


def test_frei_um_nennt_den_naechsten_laserpunkt():
    assert frei_um([(1.0, 0.0), (0.0, 0.3)], (0.0, 0.0)) == pytest.approx(0.3)
    assert frei_um([], (0.0, 0.0)) == math.inf
    assert DREHKREIS_M == pytest.approx(0.37)       # Gehäuseecken 0,355 m


def test_anfahrt_in_einem_satz_fuer_das_werkzeug():
    pose = (2.0, 2.9, -0.3)
    pfosten, laser = tuerwand(pose, blatt=True)
    o = Oeffnung(1, 0.80, (0.0, 0.0), pfosten, 0.0, 2.4, 1.5, True)
    text, weg, noetig = anfahrt_zeile(o, laser, None)
    assert noetig and weg is not None and text.endswith(' – Anfahrt passt.')
    # steht er schon passend, ist keine Anfahrt nötig
    pfosten, laser = tuerwand((2.4, 2.0, 0.0))
    o = Oeffnung(1, 0.80, (0.0, 0.0), pfosten, 0.0, 1.9, 1.5, True)
    text, weg, noetig = anfahrt_zeile(o, laser, None)
    assert not noetig and weg is None and 'nicht nötig' in text
    # passt sie nicht, steht der Grund im Satz
    stange = [(1.5 + 0.02 * i, 2.35) for i in range(55)]
    pfosten, laser = tuerwand((2.0, 2.9, -0.3), dazu=stange)
    o = Oeffnung(1, 0.80, (0.0, 0.0), pfosten, 0.0, 2.4, 1.5, True)
    text, weg, noetig = anfahrt_zeile(o, laser, None)
    assert noetig and weg is None and text.startswith('Anfahrt passt nicht: auf Strecke 1')
    assert lage_text(o, mit_hinweisen=False).endswith('Blickrichtung.')


def test_wandrichtung_kommt_aus_der_wand_neben_der_tuer_nicht_aus_den_kanten():
    pose = (2.2, 1.0, 1.0)                   # schräg von rechts
    pfosten, laser = tuerwand(pose, blatt=True)
    # Schräg gesehen liegt die ferne Kante 8 cm tiefer (hintere Ecke der Laibung)
    c, s_ = math.cos(pose[2]), math.sin(pose[2])
    fern = (c * (4.38 - pose[0]) + s_ * (2.4 - pose[1]),
            -s_ * (4.38 - pose[0]) + c * (2.4 - pose[1]))
    schief = (pfosten[0], fern)
    wand = wandrichtung(schief, laser)
    assert wand is not None and wand['punkte'] >= 12 and wand['laenge_m'] >= 0.4
    # die Wand läuft im Raum entlang y; im Roboterrahmen ist das die Richtung (sin, cos)
    richtung = (c * 0.0 + s_ * 1.0, -s_ * 0.0 + c * 1.0)
    assert abs(wand['richtung'][0] * richtung[0] + wand['richtung'][1] * richtung[1]) \
        == pytest.approx(1.0, abs=1e-3)
    # Mit der Wand als Bezug endet die Anfahrt auf der wahren Türachse …
    weg = anfahrt(schief, laser)
    assert weg['achse_aus'][0] == 'wand'
    ende = im_raum(weg['punkte'][-1], pose)
    assert ende[1] == pytest.approx(2.0, abs=0.01)
    assert 'Türachse aus der Wand neben der Tür' in anfahrt_text(weg)
    # … nur aus den verdrehten Kanten läge sie über 10 cm daneben.
    ohne_wand = [q for q in laser if abs(im_raum(q, pose)[0] - 4.3) > 0.01
                 or 1.5 < im_raum(q, pose)[1] < 2.5]
    weg = anfahrt(schief, ohne_wand)
    assert weg['achse_aus'][0] == 'kanten'
    assert abs(im_raum(weg['punkte'][-1], pose)[1] - 2.0) > 0.10
    assert 'nur aus den zwei Türkanten' in anfahrt_text(weg)


def test_wandrichtung_ohne_wand_oder_mit_querstehendem_blatt():
    assert wandrichtung(((2.0, -0.4), (2.0, 0.4)), []) is None
    # nur ein Türblatt quer zur Wand: keine Linie entlang der Türkanten
    blatt = [(2.0 - 0.02 * i, 0.43) for i in range(40)]
    assert wandrichtung(((2.0, -0.4), (2.0, 0.4)), blatt) is None
    # eine Wand auf einer Seite genügt
    wand = [(2.0, -0.45 - 0.02 * i) for i in range(40)]
    fund = wandrichtung(((2.0, -0.4), (2.0, 0.4)), wand + blatt)
    assert fund is not None and abs(fund['richtung'][1]) == pytest.approx(1.0, abs=1e-6)


# --- Kostenkarte auf dem ganzen Weg und Herkunft einer belegten Stelle --------

from lotse.fahrziel import (  # noqa: E402
    NAHHALT_BIS_M, belegt_auf_dem_weg, herkunft, herkunft_text, in_den_boden, nah_text,
    weg_belegt_text, wolke_xyz, zellen_im_streifen,
)
from lotse.geometrie import aus_tf  # noqa: E402


def raster(belegt, breite=400, hoehe=200, zelle=0.01, ursprung=(-0.5, -1.0)):
    """Kostenkarte im Kartenrahmen; ``belegt`` sind Orte (x, y) in Metern."""
    daten = [0] * (breite * hoehe)
    for x, y in belegt:
        i = int((x - ursprung[0]) / zelle)
        j = int((y - ursprung[1]) / zelle)
        daten[j * breite + i] = 100
    return daten, breite, hoehe, zelle, ursprung


def test_der_nahbereichs_halt_reicht_so_weit_wie_im_erkunder():
    assert NAHHALT_BIS_M == pytest.approx(0.58)


def test_streifen_entlang_einer_richtung():
    daten, b, h, z, u = raster([(1.0, 0.1), (1.0, 0.4), (0.2, 0.0), (2.5, 0.0)])
    zellen = zellen_im_streifen(daten, b, h, z, u, (0.0, 0.0), 0.0, von_m=0.33, bis_m=2.0)
    assert len(zellen) == 1 and zellen[0] == pytest.approx((1.005, 0.105), abs=1e-6)
    # dieselbe Zelle in einem um 90° gedrehten Streifen liegt seitlich daneben
    assert len(zellen_im_streifen(daten, b, h, z, u, (0.0, 0.0), math.pi / 2,
                                  von_m=0.33, bis_m=2.0)) == 0


def test_kif3b_die_stelle_vor_der_tuer_lag_jenseits_der_alten_15_m():
    # Start 1,87 m vor der Türlinie; belegt 0,26 m vor der Türlinie, 6 cm links
    daten, b, h, z, u = raster([(1.61, 0.06)])
    pose = (0.0, 0.0, 0.0)
    punkte = [(0.67, 0.0), (2.32, 0.0)]
    befund = belegt_auf_dem_weg(daten, b, h, z, u, pose, punkte)
    assert befund is not None and befund['strecke'] == 2      # erste Strecke reicht bis 1,25 m
    assert befund['ab_start_m'] == pytest.approx(1.615, abs=0.01)
    assert befund['seitlich_m'] == pytest.approx(0.065, abs=0.01)
    assert befund['ort'] == pytest.approx((1.615, 0.065), abs=0.01)
    assert weg_belegt_text(befund, 2.32) == (
        'Kostenkarte auf dem Weg: belegt 1.62 m voraus (Strecke 2), 0.06 m links der Linie '
        '– Kostenkarte passt nicht: dort hielte der Erkunder an.')
    # frei, wenn die Stelle neben dem Streifen oder hinter dem letzten Nahbereich liegt
    for ort in ((1.61, 0.30), (2.32 + 0.60, 0.0), (0.20, 0.0)):
        daten, b, h, z, u = raster([ort])
        assert belegt_auf_dem_weg(daten, b, h, z, u, pose, punkte) is None
    assert weg_belegt_text(None, 2.32).endswith('frei – Kostenkarte passt.')


def test_der_weg_knickt_an_der_anfahrt():
    # erst 1 m nach links (y), dann 1 m geradeaus (x): Stelle auf der zweiten Strecke
    daten, b, h, z, u = raster([(0.6, 0.98)])
    befund = belegt_auf_dem_weg(daten, b, h, z, u, (0.0, 0.0, 0.0), [(0.0, 1.0), (1.0, 1.0)])
    assert befund['strecke'] == 2
    assert befund['ab_start_m'] == pytest.approx(1.0 + 0.605, abs=0.01)


def wolke_bytes(punkte, schritt=16):
    import struct
    roh = b''
    for x, y, zz in punkte:
        roh += struct.pack('<fff', x, y, zz) + b'\0' * (schritt - 12)
    return roh


def test_punktwolke_lesen_ohne_ungueltige_punkte():
    felder = {'x': (0, 7), 'y': (4, 7), 'z': (8, 7)}
    roh = wolke_bytes([(0.3, 0.1, -0.05), (float('nan'), 0.0, 0.0), (0.5, -0.2, 0.0)])
    punkte = wolke_xyz(roh, felder, 16, 3)
    assert punkte.shape == (2, 3)
    assert punkte[0] == pytest.approx((0.3, 0.1, -0.05), abs=1e-6)
    assert wolke_xyz(b'', felder, 16, 0).shape == (0, 3)
    with pytest.raises(ValueError, match='zu wenige Daten'):
        wolke_xyz(roh[:20], felder, 16, 3)
    with pytest.raises(ValueError, match='Feld oder Datentyp fehlt'):
        wolke_xyz(roh, {'x': (0, 7), 'y': (4, 7)}, 16, 3)


def test_nahsensor_punkte_in_den_bodenrahmen():
    # Sensor 0,29 m voraus, 0,095 m links, 0,215 m über base_link, waagerecht
    boden = aus_tf([0.29, 0.095, 0.215], [0.0, 0.0, 0.0, 1.0], 0.09)
    punkte = in_den_boden([(0.30, 0.0, -0.10)], boden)
    assert punkte[0] == pytest.approx((0.59, 0.095, 0.205), abs=1e-6)
    assert in_den_boden([], boden).shape == (0, 3)


def test_herkunft_nennt_die_quelle_mit_hoehe():
    stelle = (0.58, 0.09)
    nah = {'links': [(0.585, 0.08, 0.20), (0.59, 0.10, 0.23), (0.40, -0.2, 0.1)],
           'rechts': []}
    befund = herkunft(stelle, karte=[(1.5, 0.0)], nah=nah, laser=[(2.0, 0.4)])
    assert befund['karte'] == 0 and befund['laser'] == 0
    assert befund['nah']['links'][0] == 2 and befund['nah']['rechts'][0] == 0
    text = herkunft_text(befund)
    assert text.startswith('Herkunft der Stelle 0.25 m vor der Vorderkante (31 cm vor dem '
                           'Gehäuse), 0.09 m links der Mitte: Karte (SLAM) frei; Nahsensor '
                           'links 2 Punkt(e), 20 bis 23 cm')
    assert 'Nahsensor rechts sieht dort nichts; Laser sieht dort nichts.' in text
    assert 'ältere Markierung' not in text
    # sieht keine Quelle etwas, ist es eine ältere Markierung
    leer = herkunft_text(herkunft(stelle, karte=[], nah={'links': [], 'rechts': []}, laser=[]))
    assert 'keine Quelle sieht dort jetzt etwas' in leer and 'ab 0,45 m' in leer
    # Karte belegt
    karte = herkunft_text(herkunft(stelle, karte=[(0.59, 0.09)], nah=None, laser=None))
    assert 'Karte (SLAM) belegt' in karte and 'Laser nicht empfangen' in karte


def test_nahsensoren_im_fahrstreifen_in_einem_satz():
    text = nah_text({'links': [(0.60, 0.09, 0.21), (0.62, 0.10, 0.25), (0.60, 0.40, 0.3)],
                     'rechts': None})
    assert text == ('Nahsensoren im Fahrstreifen: links 2 Punkt(e), der nächste 0.27 m vor der '
                    'Vorderkante (33 cm vor dem Gehäuse), 0.09 m links der Mitte, Höhe 21 bis 25 '
                    'cm über dem Boden; rechts nicht empfangen.')
    assert nah_text(None) == 'Nahsensoren im Fahrstreifen: nicht empfangen.'
    assert nah_text({'links': [], 'rechts': []}).endswith('links nichts; rechts nichts.')


# --- KI-F5: eine Türkante falsch, Achse aus der Wand; selbst entscheiden ------

from fahrziel_senden import ENTSCHEIDUNG_TEXT, entscheidung, vorschlag  # noqa: E402
from lotse.fahrziel import achse_text, tuerachse  # noqa: E402


def kif5_messung():
    """Die Kanten aus dem Bericht KI-F5 (23.11.2026), dazu die Wand neben der Tür.

    Am 22.11. stand Amadeus am selben Platz; die linke Kante lag auf 2 cm
    genauso, die rechte 7 cm weiter weg. Die Wand liegt quer vor ihm wie am
    22.11. (dort: Tür 1° gedreht).
    """
    def polar(w, r):
        return (r * math.cos(math.radians(w)), r * math.sin(math.radians(w)))
    rechts, links = polar(-10.0, 1.83), polar(13.1, 1.95)
    wand = [(1.89, -0.40 - 0.02 * i) for i in range(50)]           # rechts der Tür
    wand += [(1.89, 0.46 + 0.02 * i) for i in range(50)]           # links der Tür
    return (rechts, links), wand


def test_kif5_eine_kante_kippt_die_achse_die_wand_nicht():
    pfosten, wand = kif5_messung()
    # nur aus den Kanten: 7° gekippt, „30 cm daneben“ – so meldete es das Werkzeug
    nur_kanten = aufstellung(pfosten)
    assert nur_kanten['seitlich_m'] == pytest.approx(-0.296, abs=0.005)
    assert nur_kanten['winkel_grad'] == pytest.approx(-7.3, abs=0.2)
    assert any('nach links versetzen' in h for h in aufstellung_hinweise(nur_kanten))
    # aus der Wand: er steht mittig, wie Christopher sagte
    achse = tuerachse(pfosten, wand)
    assert achse['quelle'] == 'wand' and achse['punkte'] >= 12
    lage = aufstellung(pfosten, achse=achse['normal'])
    assert abs(lage['seitlich_m']) < 0.08 and abs(lage['winkel_grad']) < 1.0
    assert aufstellung_hinweise(lage) == []
    assert achse_text(achse).startswith('Türachse aus der Wand neben der Tür (')
    # die gerade Linie ist dann kaum schräg und geht durch die Türmitte
    linie = gerade_linie(pfosten, hinter_m=0.45, achse=achse['normal'])
    assert len(linie) == 2 and abs(linie[-1][1]) < 0.15


def test_ohne_wand_bleibt_es_bei_den_kanten():
    pfosten, _ = kif5_messung()
    achse = tuerachse(pfosten, [])
    assert achse['quelle'] == 'kanten'
    assert aufstellung(pfosten, achse=achse['normal']) == pytest.approx(aufstellung(pfosten))
    assert 'nur aus den zwei Türkanten' in achse_text(achse)


def test_entscheidung_zur_tuer():
    assert entscheidung(True, True, True) == 'durchfahrt'
    assert entscheidung(True, True, False) == 'durchfahrt'
    assert entscheidung(False, True, True) == 'anfahrt'
    assert entscheidung(False, False, True) == 'anfahrt'
    assert entscheidung(False, True, False) == 'nichts'
    # steht er passend, aber die Linie ist nicht frei, hilft keine Anfahrt
    assert entscheidung(True, False, True) == 'nichts'
    assert ENTSCHEIDUNG_TEXT['anfahrt'].startswith('Entscheidung: Anfahrt')


def test_vorschlag_ist_die_tiefste_tuerbreite_oeffnung():
    tuer = Oeffnung(1, 0.77, (1.85, 0.06), ((1.8, -0.3), (1.9, 0.4)), 2.0, 1.85, 1.62, True)
    luecke = Oeffnung(2, 0.82, (1.0, -1.0), ((0.6, -1.0), (1.4, -0.9)), -43.0, 1.43, 0.67, True)
    assert vorschlag([luecke, tuer]) is tuer
    assert vorschlag([]) is None


# ------------------------------- Ein Ablauf: Anfahrt und Durchfahrt (KI-F8) -------------

def test_grenzen_vom_23_11():
    """Projektinhaber nach KI-F7: Gehäuse 0,23 m je Seite plus 3 cm; Drehen 0,355 m plus 1,5 cm."""
    assert FREI_NEBEN_DER_LINIE_M == pytest.approx(0.26)
    assert DREHKREIS_M == pytest.approx(0.37)
    assert math.hypot(0.27, 0.23) < DREHKREIS_M


def test_fahrziel_mit_folgeziel_und_ende():
    mit = json.loads(botschaft([(1.0, 0.0)], kennung='a', quelle='mensch', zeit_s=5.0,
                               weiter=True))
    assert mit['weiter'] is True
    ohne = json.loads(botschaft([(1.0, 0.0)], kennung='a', quelle='mensch', zeit_s=5.0))
    assert 'weiter' not in ohne
    ende = json.loads(ende_botschaft(kennung='e', quelle='mensch', zeit_s=7.0))
    assert ende == {'ende': True, 'kennung': 'e', 'quelle': 'mensch', 'frame': 'map',
                    'zeit_s': 7.0}
    with pytest.raises(ValueError):
        ende_botschaft(kennung='e', quelle='regel', zeit_s=7.0)


def test_die_tuer_wird_nach_der_anfahrt_wiedergefunden_und_die_achse_mitgenommen():
    # erste Messung: Tür 2,5 m voraus, 1 m rechts, Achse aus der Wand (schräg 10°)
    pose1 = (1.0, 2.0, 0.3)
    pfosten1 = ((2.5, -1.4), (2.5, -0.6))
    n = (math.cos(math.radians(10)), math.sin(math.radians(10)))
    gemerkt = tuer_merken(pfosten1, {'normal': n, 'quelle': 'wand', 'punkte': 30,
                                     'laenge_m': 1.2}, pose1)
    # Mitte in der Karte
    c, s = math.cos(0.3), math.sin(0.3)
    assert gemerkt['mitte'] == pytest.approx((1.0 + c * 2.5 - s * -1.0, 2.0 + s * 2.5 + c * -1.0))

    # nach der Anfahrt steht er woanders und anders gedreht
    pose2 = (2.2, 1.0, -0.4)
    mitte2 = (lambda dx, dy: (math.cos(-0.4) * dx + math.sin(-0.4) * dy,
                              -math.sin(-0.4) * dx + math.cos(-0.4) * dy))(
        gemerkt['mitte'][0] - pose2[0], gemerkt['mitte'][1] - pose2[1])
    tuer = Oeffnung(3, 0.78, mitte2, ((mitte2[0], mitte2[1] - 0.39),
                                      (mitte2[0], mitte2[1] + 0.39)), 1.5, 1.6, 1.5, True)
    andere = Oeffnung(4, 0.80, (mitte2[0], mitte2[1] + 1.5),
                      ((mitte2[0], mitte2[1] + 1.1), (mitte2[0], mitte2[1] + 1.9)),
                      1.5, 1.6, 1.5, True)
    assert wiederfinden([andere, tuer], gemerkt, pose2) is tuer
    assert wiederfinden([andere], gemerkt, pose2) is None

    # die Achse zeigt in der Karte weiter in dieselbe Richtung
    achse = achse_aus_karte(gemerkt, pose2)
    assert achse['quelle'] == 'karte'
    winkel_karte = math.atan2(gemerkt['normal'][1], gemerkt['normal'][0])
    assert math.atan2(achse['normal'][1], achse['normal'][0]) == pytest.approx(
        winkel_karte - pose2[2])
    assert winkel_karte == pytest.approx(math.radians(10) + 0.3)
    assert 'gemessen vor der Anfahrt (30 Laserpunkte über 1.20 m)' in achse_text(achse)


# ------------------- Tür hinter dem offenen Türblatt (Blattseite, 23.11.2026) ----------

from fahrziel_senden import richtung_passt, tuer_aus_blatt  # noqa: E402
from lotse.fahrziel import blatt_text, gerade_stuecke, tuer_hinter_blatt  # noqa: E402


def _kasten(x0, x1, y0, y1):
    return [((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)), ((x1, y1), (x0, y1)),
            ((x0, y1), (x0, y0))]


def _laborwelt(blatt=True):
    """Laborraum der Simulation: Tür in der Wand x = 4,3 bei y = 1,6 bis 2,4,
    Scharnier oben, Blatt 0,90 m lang und 85° offen in den Raum, dazu Möbel."""
    s = [((0, 0), (4.3, 0)), ((0, 4.3), (4.3, 4.3)), ((0, 0), (0, 4.3)),
         ((4.3, 0), (4.3, 1.6)), ((4.3, 2.4), (4.3, 4.3)),
         ((5.85, 0), (5.85, 4.3)), ((4.3, 0.2), (5.85, 0.2)), ((4.3, 4.2), (5.85, 4.2))]
    s += _kasten(0, 0.4, 0.6, 2.2) + _kasten(1.3, 3.0, 3.65, 4.3) + _kasten(3.3, 4.3, 0, 0.45)
    if blatt:
        w = math.radians(85)
        d = (-math.sin(w), -math.cos(w))
        a = (4.3, 2.416)
        b = (a[0] + 0.9 * d[0], a[1] + 0.9 * d[1])
        n = (-d[1] * 0.02, d[0] * 0.02)
        s += [((a[0] + n[0], a[1] + n[1]), (b[0] + n[0], b[1] + n[1])),
              ((a[0] - n[0], a[1] - n[1]), (b[0] - n[0], b[1] - n[1])),
              ((b[0] + n[0], b[1] + n[1]), (b[0] - n[0], b[1] - n[1]))]
    return s


def _laserbild(segmente, pose, schritt_grad=0.5, rauschen_m=0.01, saat=1):
    """Was der Laser vom Standplatz ``pose`` sieht: Punkte im Standpunktrahmen."""
    import numpy as np
    zufall = np.random.default_rng(saat)
    x, y, gier = pose
    punkte = []
    for k in range(int(360 / schritt_grad)):
        w = math.radians(-180 + k * schritt_grad)
        dx, dy = math.cos(gier + w), math.sin(gier + w)
        naechste = math.inf
        for (ax, ay), (bx, by) in segmente:
            ex, ey = bx - ax, by - ay
            nenner = dx * ey - dy * ex
            if abs(nenner) < 1e-12:
                continue
            t = ((ax - x) * ey - (ay - y) * ex) / nenner
            u = ((ax - x) * dy - (ay - y) * dx) / nenner
            if t > 0.05 and 0.0 <= u <= 1.0:
                naechste = min(naechste, t)
        if naechste < 12.0:
            r = naechste + zufall.normal(0.0, rauschen_m)
            punkte.append((r * math.cos(w), r * math.sin(w)))
    return punkte


def _in_der_welt(q, pose):
    x, y, gier = pose
    c, s = math.cos(gier), math.sin(gier)
    return (x + c * q[0] - s * q[1], y + s * q[0] + c * q[1])


def test_gerade_stuecke_teilen_an_ecken_und_nicht_am_rauschen():
    # eine Ecke: 1 m Wand, dann 0,8 m senkrecht dazu, 1 cm Rauschen
    import numpy as np
    zufall = np.random.default_rng(3)
    wand = [(2.0, -0.5 + 0.02 * i) for i in range(50)]
    blatt = [(2.0 - 0.02 * i, 0.5) for i in range(1, 41)]
    punkte = [(px + zufall.normal(0, 0.01), py + zufall.normal(0, 0.01))
              for px, py in wand + blatt]
    stuecke = [s for s in gerade_stuecke(punkte) if s['laenge_m'] > 0.3]
    assert [round(s['laenge_m'], 1) for s in stuecke] == [1.0, 0.8]


@pytest.mark.parametrize('pose', [(2.6, 3.1, -0.9), (3.0, 3.3, -0.3), (2.2, 2.9, -0.5),
                                  (3.6, 3.4, -1.4), (1.0, 3.0, -0.5)])
def test_von_der_blattseite_wird_die_tuer_aus_blatt_und_wand_geschaetzt(pose):
    fund = tuer_hinter_blatt(_laserbild(_laborwelt(), pose))
    assert fund is not None
    scharnier, fern = (_in_der_welt(q, pose) for q in fund['pfosten'])
    assert scharnier == pytest.approx((4.3, 2.44), abs=0.03)
    assert fern[0] == pytest.approx(4.3, abs=0.03)
    mitte_y = 0.5 * (scharnier[1] + fern[1])
    assert mitte_y == pytest.approx(2.0, abs=0.06)          # echte Mitte der Tür
    assert fund['winkel_grad'] == pytest.approx(85, abs=3)
    assert 'die Öffnung dahinter verdeckt es' in blatt_text(fund)


@pytest.mark.parametrize('pose', [(2.2, 1.0, 1.0), (2.45, 2.0, 0.0), (3.0, 1.2, 0.5),
                                  (1.5, 2.0, 0.0), (2.0, 0.9, 0.3), (3.5, 1.0, 0.8)])
def test_ohne_blick_auf_die_blattrueckseite_wird_nichts_geschaetzt(pose):
    """Von vorn oder von der anderen Seite: kein Fund (Schrank, Werkbank und
    Raumecken gelten nicht als Blatt)."""
    assert tuer_hinter_blatt(_laserbild(_laborwelt(), pose)) is None


def test_ohne_tuerblatt_wird_nichts_geschaetzt():
    for pose in [(2.6, 3.1, -0.9), (3.6, 3.4, -1.4)]:
        assert tuer_hinter_blatt(_laserbild(_laborwelt(blatt=False), pose)) is None


def test_die_geschaetzte_tuer_wird_eine_oeffnung_mit_achse_aus_der_wand():
    pose = (2.6, 3.1, -0.9)
    o, achse, _ = tuer_aus_blatt(_laserbild(_laborwelt(), pose), 7)
    assert o.nr == 7 and o.schluss == 'blatt_geschaetzt' and o.befahrbar
    assert 0.80 <= o.breite_m <= 0.95
    assert achse['quelle'] == 'wand'
    # die Achse steht senkrecht auf der Wand x = 4,3 (in der Welt: entlang x)
    nx, ny = achse['normal']
    c, s = math.cos(pose[2]), math.sin(pose[2])
    assert abs(c * nx - s * ny) == pytest.approx(1.0, abs=0.01)
    assert richtung_passt(o, o.richtung_grad + 8, 10) and not richtung_passt(o, 60.0, 10)
    # die Anfahrt vor diese Tür ist am Laserbild geprüft möglich
    weg = anfahrt(o.pfosten, _laserbild(_laborwelt(), pose))
    ende = _in_der_welt(weg['punkte'][-1], pose)
    assert ende[1] == pytest.approx(2.0, abs=0.08) and 2.1 <= ende[0] <= 2.8


# ------------------- Wahl der KI übernehmen (23.11.2026, abends) -------------------------

import fahrziel_senden  # noqa: E402
from fahrziel_senden import blatt_passt_zur_wahl, oeffnung_zur_wahl  # noqa: E402


def _o(nr, mitte, breite):
    mx, my = mitte
    return Oeffnung(nr=nr, breite_m=breite, mitte=(mx, my),
                    pfosten=((mx, my - breite / 2), (mx, my + breite / 2)),
                    richtung_grad=math.degrees(math.atan2(my, mx)),
                    entfernung_m=math.hypot(mx, my), tiefe_m=1.5, befahrbar=True)


def test_wahl_der_ki_findet_die_tuerbreite_oeffnung_an_ihrer_stelle():
    pose = (1.0, 2.0, 0.0)
    tuer, durchgang = _o(1, (2.0, 0.05), 0.80), _o(2, (1.5, 2.0), 1.20)
    o, abstand = oeffnung_zur_wahl([tuer, durchgang], [tuer], {'mitte': [3.0, 2.0]}, pose)
    assert o is tuer and abstand == pytest.approx(0.05, abs=1e-6)


def test_wahl_der_ki_auf_einer_nicht_tuerbreiten_oeffnung_wird_mit_mass_genannt():
    pose = (1.0, 2.0, 0.0)
    tuer, durchgang = _o(1, (2.0, 0.0), 0.80), _o(2, (1.5, 2.0), 1.20)
    with pytest.raises(ValueError, match='Öffnung 2 vermessen, 1.20 m breit – nicht türbreit'):
        oeffnung_zur_wahl([tuer, durchgang], [tuer], {'mitte': [2.5, 4.0]}, pose)
    with pytest.raises(ValueError, match='keine türbreite Öffnung vermessen'):
        oeffnung_zur_wahl([tuer, durchgang], [tuer], {'mitte': [1.0, -2.0]}, pose)


def test_geschaetzte_tuer_hinter_dem_blatt_passt_nur_zur_wahl_an_ihrer_stelle():
    pose = (2.6, 3.1, -0.9)                  # Karte = Welt der Laborsimulation
    o, _, _ = tuer_aus_blatt(_laserbild(_laborwelt(), pose), 7)
    assert blatt_passt_zur_wahl(o, {'mitte': [4.3, 2.0]}, pose)
    assert blatt_passt_zur_wahl(o, {'mitte': [4.25, 2.3]}, pose)
    assert not blatt_passt_zur_wahl(o, {'mitte': [0.4, 3.0]}, pose)
    assert not blatt_passt_zur_wahl(o, {'mitte': [4.3, 1.2]}, pose)


@pytest.mark.parametrize('argumente, grund', [
    (['--tuer', '--wahl', 'w.json'], '--wahl nur mit --zur-tuer'),
    (['--zur-tuer', '--wahl', 'w.json', '--nummer', '2'], '--wahl ersetzt --nummer'),
    (['--zur-tuer', '--wahl', 'w.json', '--richtung', '20'], '--wahl ersetzt --nummer'),
    (['--zur-tuer', '--wahl', 'w.json', '--quelle', 'mensch'], 'Quelle ki'),
    (['--ende', '--geradeaus', '0.5'], 'not allowed with argument'),
])
def test_wahl_und_ende_nur_in_sinnvoller_verbindung(argumente, grund, capsys):
    with pytest.raises(SystemExit) as ende:
        fahrziel_senden.main(argumente)
    assert ende.value.code == 2 and grund in capsys.readouterr().err
