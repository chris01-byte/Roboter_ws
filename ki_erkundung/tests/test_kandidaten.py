"""Vermessene Vorschläge: Öffnungen im Rundum-Profil."""
import math

import numpy as np
import pytest

from beispielrunde_erzeugen import _kasten, _strahlen
from lotse.kandidaten import lecks_schliessen, oeffnungen


def profil(strecken, ursprung=(0.0, 0.0), bins=720, unbekannt=None):
    """Rundum-Profil einer ausgedachten Welt aus Strecken (x1, y1, x2, y2)."""
    schritt = 2 * math.pi / bins
    winkel = -math.pi + (np.arange(bins) + 0.5) * schritt
    richtungen = np.column_stack([np.cos(winkel), np.sin(winkel)])
    r = _strahlen(np.asarray(ursprung, dtype=float), richtungen, np.asarray(strecken, dtype=float))
    if unbekannt is not None:
        von, bis = (math.radians(v) for v in unbekannt)
        r[(winkel >= von) & (winkel <= bis)] = np.nan
    return winkel, r


def zimmer(tuer=(-0.4, 0.4), tiefe_dahinter=3.0, wand_x=2.0):
    """Zimmer 4 x 4 m um den Ursprung; in der Wand bei x = wand_x eine Tür."""
    strecken = [(-2, -2, wand_x, -2), (-2, 2, wand_x, 2), (-2, -2, -2, 2)]
    if tuer is None:
        strecken.append((wand_x, -2, wand_x, 2))
    else:
        strecken += [(wand_x, -2, wand_x, tuer[0]), (wand_x, tuer[1], wand_x, 2)]
        hinten = wand_x + tiefe_dahinter          # Raum hinter der Tür
        strecken += [(wand_x, -2, hinten, -2), (hinten, -2, hinten, 2),
                     (hinten, 2, wand_x, 2)]
    return strecken


def test_tuer_geradeaus_wird_mit_breite_und_lage_gefunden():
    gefunden = oeffnungen(*profil(zimmer()))
    assert len(gefunden) == 1
    o = gefunden[0]
    assert o.nr == 1
    assert o.breite_m == pytest.approx(0.8, abs=0.02)
    assert o.mitte[0] == pytest.approx(2.0, abs=0.03)
    assert o.mitte[1] == pytest.approx(0.0, abs=0.03)
    assert o.richtung_grad == pytest.approx(0.0, abs=1.5)
    assert o.entfernung_m == pytest.approx(2.0, abs=0.03)
    assert o.tiefe_m >= 2.5
    assert o.befahrbar


def test_tuer_schraeg_gesehen_wird_gefunden():
    gefunden = oeffnungen(*profil(zimmer(tuer=(1.0, 1.8)), ursprung=(-1.0, -1.2)))
    assert len(gefunden) == 1
    assert gefunden[0].breite_m == pytest.approx(0.8, abs=0.06)
    # Mitte der Tür im Rahmen des Standpunkts
    assert gefunden[0].mitte == pytest.approx((3.0, 2.6), abs=0.06)


def test_geschlossene_wand_hat_keine_oeffnung():
    assert oeffnungen(*profil(zimmer(tuer=None))) == []


def test_raum_in_l_form_hat_keine_oeffnung():
    """Eine vorspringende Ecke verdeckt einen Teil des Raums; das ist keine Tür."""
    l_form = [(-2, -2, 2, -2), (2, -2, 2, 0), (2, 0, 0.5, 0), (0.5, 0, 0.5, 2),
              (0.5, 2, -2, 2), (-2, 2, -2, -2)]
    for ursprung in ((-1.0, -1.0), (1.2, -1.0), (-0.8, 1.2)):
        assert oeffnungen(*profil(l_form, ursprung=ursprung)) == [], ursprung


def test_tuer_schraeg_gesehen_auch_von_der_anderen_seite():
    gefunden = oeffnungen(*profil(zimmer(tuer=(-1.8, -1.0)), ursprung=(-1.0, 1.2)))
    assert len(gefunden) == 1
    assert gefunden[0].breite_m == pytest.approx(0.8, abs=0.06)
    assert gefunden[0].mitte == pytest.approx((3.0, -2.6), abs=0.06)


def test_flache_nische_zaehlt_nicht():
    """30 cm tiefe Nische: dahinter geht es nicht 0,5 m frei weiter."""
    assert oeffnungen(*profil(zimmer(tiefe_dahinter=0.3))) == []


def test_nische_von_50_cm_zaehlt_nicht_eine_von_einem_meter_schon():
    """Das Gehäuse ist 0,42 m lang; 50 cm Tiefe reichen ihm nicht."""
    assert oeffnungen(*profil(zimmer(tiefe_dahinter=0.5))) == []
    # auch schräg gesehen nicht: Die Tiefe zählt quer zur Lücke
    assert oeffnungen(*profil(zimmer(tiefe_dahinter=0.5), ursprung=(-1.0, -1.5))) == []
    tief = oeffnungen(*profil(zimmer(tiefe_dahinter=1.0)))
    assert len(tief) == 1
    assert tief[0].tiefe_m == pytest.approx(1.0, abs=0.05)


def test_schmaler_spalt_zaehlt_nicht_und_knapper_wird_als_zu_schmal_gezeigt():
    assert oeffnungen(*profil(zimmer(tuer=(-0.2, 0.2)))) == []
    knapp = oeffnungen(*profil(zimmer(tuer=(-0.285, 0.285))))
    assert len(knapp) == 1
    assert knapp[0].breite_m == pytest.approx(0.57, abs=0.02)
    assert not knapp[0].befahrbar


def test_sehr_breite_oeffnung_ist_kein_vorschlag():
    assert oeffnungen(*profil(zimmer(tuer=(-1.8, 1.8)))) == []


def test_keine_oeffnung_ueber_unbeobachtetes_hinweg():
    winkel, r = profil(zimmer(), unbekannt=(-3.0, 3.0))
    assert oeffnungen(winkel, r) == []


def test_kein_echo_hinter_der_tuer_gilt_als_frei():
    winkel, r = profil([(-2, -2, 2, -2), (-2, 2, 2, 2), (-2, -2, -2, 2),
                        (2, -2, 2, -0.4), (2, 0.4, 2, 2)])
    assert np.isinf(r).any()
    gefunden = oeffnungen(winkel, r)
    assert len(gefunden) == 1
    assert gefunden[0].breite_m == pytest.approx(0.8, abs=0.04)


def test_moebelkante_und_tuerpfosten_ergeben_keine_breite_scheinoeffnung():
    """Ein Schrank neben der Tür: Es bleibt bei der einen, schmalen Öffnung."""
    strecken = zimmer(tuer=(-0.4, 0.4)) + _kasten(1.0, 1.2, 1.6, 2.0)
    for ursprung in ((0.0, 0.0), (-0.5, -0.8), (0.3, -1.0)):
        gefunden = oeffnungen(*profil(strecken, ursprung=ursprung))
        assert len(gefunden) == 1, (ursprung, [o.als_dict() for o in gefunden])
        assert gefunden[0].breite_m == pytest.approx(0.8, abs=0.06)


def test_nummern_laufen_gegen_den_uhrzeigersinn_ab_vorn():
    strecken = [
        (2, -2, 2, -0.4), (2, 0.4, 2, 2),                 # Tür vorn (0 Grad)
        (-2, 2, -0.4, 2), (0.4, 2, 2, 2),                 # Tür links (90 Grad)
        (-2, -2, -0.4, -2), (0.4, -2, 2, -2),             # Tür rechts (-90 Grad)
        (-2, -2, -2, 2),
    ]
    gefunden = oeffnungen(*profil(strecken))
    assert [o.nr for o in gefunden] == [1, 2, 3]
    assert [round(o.richtung_grad / 90.0) for o in gefunden] == [0, 1, -1]


def test_hoechstens_max_anzahl_vorschlaege():
    strecken = []
    for k in range(12):                                   # zwölf Säulen im Kreis
        mitte = 2.5 * np.array([math.cos(k * math.pi / 6), math.sin(k * math.pi / 6)])
        strecken += _kasten(mitte[0] - 0.2, mitte[1] - 0.2, mitte[0] + 0.2, mitte[1] + 0.2)
    alle = oeffnungen(*profil(strecken), max_anzahl=20)
    assert len(alle) == 12
    begrenzt = oeffnungen(*profil(strecken), max_anzahl=5)
    assert [o.nr for o in begrenzt] == [1, 2, 3, 4, 5]


def test_als_dict_enthaelt_keine_langen_kommazahlen():
    eintrag = oeffnungen(*profil(zimmer()))[0].als_dict()
    assert set(eintrag) == {'nr', 'breite_m', 'mitte', 'pfosten', 'richtung_grad',
                            'entfernung_m', 'tiefe_m', 'befahrbar'}
    assert eintrag['breite_m'] == round(eintrag['breite_m'], 2)


def test_lecks_schliessen_entfernt_einzelne_ausreisser_aber_keine_oeffnung():
    winkel, r = profil(zimmer())
    vorher = oeffnungen(winkel, r)
    mit_leck = r.copy()
    stelle = int(np.argmin(np.abs(winkel - math.radians(120))))
    mit_leck[stelle] = np.inf
    geschlossen = lecks_schliessen(mit_leck)
    assert np.isfinite(geschlossen[stelle])
    assert geschlossen[stelle] == pytest.approx(max(r[stelle - 1], r[stelle + 1]))
    nachher = oeffnungen(winkel, geschlossen)
    assert len(nachher) == len(vorher) == 1
    assert nachher[0].breite_m == pytest.approx(vorher[0].breite_m, abs=0.01)


def test_kurze_oder_ungleich_lange_eingaben_ergeben_nichts():
    assert oeffnungen([0.0, 0.1], [1.0, 1.0]) == []
    assert oeffnungen(np.linspace(-3, 3, 100), np.ones(50)) == []
