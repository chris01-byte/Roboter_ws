"""Fahrziel: aus der gewählten Öffnung zwei Punkte für die Etappenfahrt."""
import json
import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'werkzeuge'))

from fahrziel_senden import lies_punkt, tabelle, waehle_oeffnung  # noqa: E402

from lotse.fahrziel import (  # noqa: E402
    botschaft, durch_die_tuer, geradeaus, im_kartenrahmen, pruefe_grenzen,
    punkt_relativ, tuer_punkte,
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
    assert vor == pytest.approx((1.30, 0.025))
    assert hinter == pytest.approx((2.60, 0.025))
    # Reihenfolge der Pfosten ist gleichgültig
    assert tuer_punkte(((2.0, 0.45), (2.0, -0.40))) == (pytest.approx(vor), pytest.approx(hinter))


def test_die_achse_zeigt_immer_vom_standpunkt_weg():
    vor, hinter = tuer_punkte(((2.0, -0.4), (2.0, 0.4)), standpunkt=(3.5, 0.0))
    assert vor == pytest.approx((2.7, 0.0)) and hinter == pytest.approx((1.4, 0.0))


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
    assert punkte == [pytest.approx((10.0, 6.3)), pytest.approx((10.0, 7.6))]
    # der Roboter steht schon 0,7 m vor der Tür auf der Achse: nur der Auslaufpunkt
    nah = ((0.7, -0.4), (0.7, 0.4))
    assert durch_die_tuer(nah, (0.0, 0.0, 0.0)) == [pytest.approx((1.3, 0.0))]


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
