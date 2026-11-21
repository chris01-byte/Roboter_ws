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
                            'entfernung_m', 'tiefe_m', 'befahrbar', 'schluss'}
    assert eintrag['schluss'] == 'sprung'
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


# ---------------------------------------------------------------- Türblatt
# Befund KI-0 am 21.11.2026: Von der Seite wurde die 85-cm-Labortür 1,22 m
# breit vermessen, die Nummer stand neben der Tür. Ursache im Nachstellen:
# Die sichtbare Lücke endet an der Spitze des offenen Türblatts.

def blatt(grad, laenge=0.8, scharnier=(2.0, 0.4)):
    """Türblatt am Pfosten ``scharnier``; 0° = zu, 90° = rechtwinklig im Zimmer."""
    w = math.radians(grad)
    return (scharnier[0], scharnier[1],
            scharnier[0] - math.sin(w) * laenge, scharnier[1] - math.cos(w) * laenge)


def test_offenes_tuerblatt_verdeckt_den_pfosten_die_tuer_wird_trotzdem_richtig_vermessen():
    stand = (0.0, 0.8)                    # Scharnierseite, Blick an der Blattspitze vorbei
    welt = zimmer() + [blatt(90)]
    ohne_regel = oeffnungen(*profil(welt, ursprung=stand), blatt_min_m=9.0)
    assert len(ohne_regel) == 1
    assert ohne_regel[0].breite_m == pytest.approx(1.13, abs=0.05)     # Spitze bis Pfosten
    assert ohne_regel[0].mitte[0] + stand[0] == pytest.approx(1.6, abs=0.05)   # vor der Tür

    gefunden = oeffnungen(*profil(welt, ursprung=stand))
    assert len(gefunden) == 1
    o = gefunden[0]
    assert o.schluss == 'blatt'
    assert o.breite_m == pytest.approx(0.8, abs=0.05)
    assert (o.mitte[0] + stand[0], o.mitte[1] + stand[1]) == pytest.approx((2.0, 0.0), abs=0.05)
    # Die Nummer steht auf dem sichtbaren Stück der Schwelle (von y = -0,4 bis 0,13)
    assert o.marke is not None
    marke = (o.marke[0] + stand[0], o.marke[1] + stand[1])
    assert marke == pytest.approx((2.0, -0.13), abs=0.06)
    assert o.als_dict()['marke'] == [round(o.marke[0], 2), round(o.marke[1], 2)]


@pytest.mark.parametrize('grad', [80, 90, 100])
def test_tuerblatt_bei_verschiedenen_winkeln_und_von_der_anderen_seite(grad):
    welt = zimmer() + [blatt(grad)]
    for stand in ((0.0, 0.8), (-0.6, 0.9)):
        gefunden = oeffnungen(*profil(welt, ursprung=stand))
        tueren = [o for o in gefunden
                  if abs(o.mitte[0] + stand[0] - 2.0) < 0.1 and abs(o.mitte[1] + stand[1]) < 0.1]
        assert len(tueren) == 1, (grad, stand, gefunden)
        if tueren[0].schluss == 'blatt':
            assert tueren[0].breite_m == pytest.approx(
                0.8 * min(1.0, math.sin(math.radians(grad))), abs=0.06)
        else:
            # Blatt fast von der Kante gesehen: Es ist nicht zu verfolgen, der
            # zweite Pfosten ist das Lot der Blattspitze auf die Wand. Bei 100°
            # liegt es 14 cm hinter dem Scharnier; die Tür wird so viel zu breit.
            assert (grad, stand, tueren[0].schluss) == (100, (-0.6, 0.9), 'lot')
            assert tueren[0].breite_m == pytest.approx(0.8 + 0.14, abs=0.06)
    # Von der anderen Seite liegt das Blatt hinter der Öffnung und stört nicht.
    drueben = oeffnungen(*profil(welt, ursprung=(0.0, -0.8)))
    assert [o.schluss for o in drueben] == ['sprung']
    assert drueben[0].breite_m == pytest.approx(0.8, abs=0.05)


def test_tuerblatt_das_im_weg_steht_macht_die_tuer_unpassierbar():
    protokoll = []
    stand = (0.5, -0.2)
    gefunden = oeffnungen(*profil(zimmer() + [blatt(30)], ursprung=stand), protokoll=protokoll)
    assert gefunden == []                 # lichte Breite 0,8 m * sin(30°) = 0,40 m
    assert any(z['ergebnis'] == 'blatt_im_weg' for z in protokoll)


def test_moebelseite_neben_der_luecke_zaehlt_wie_ein_blatt():
    """Ein Schrank, der neben der Tür von der Wand absteht: Die Tür reicht bis zur Wand."""
    schrank = _kasten(1.4, 0.4, 2.0, 1.4)             # 60 cm tief, Seite am Türpfosten
    gefunden = oeffnungen(*profil(zimmer() + schrank, ursprung=(0.0, 0.9)))
    tuer = [o for o in gefunden if abs(o.mitte[1] + 0.9) < 0.15 and abs(o.mitte[0] - 2.0) < 0.15]
    assert len(tuer) == 1
    assert tuer[0].breite_m == pytest.approx(0.8, abs=0.06)


# ------------------------------------------------- Tür hinter einer Möbellücke
# Befund KI-0 am 21.11.2026: Eine offene Tür in 4–5 m wurde nicht angeboten,
# nur die 2,25 m breite Lücke zwischen Möbeln davor.

def test_tuer_hinter_einer_breiten_moebelluecke_wird_angeboten():
    moebel = _kasten(0.2, 0.9, 0.7, 1.6) + _kasten(0.2, -1.6, 0.7, -0.9)
    stand = (-1.2, 0.0)
    alt = oeffnungen(*profil(zimmer() + moebel, ursprung=stand), tuerbreit_m=10.0)
    assert not any(o.breite_m < 1.0 and abs(o.mitte[0] + stand[0] - 2.0) < 0.1 for o in alt)

    gefunden = oeffnungen(*profil(zimmer() + moebel, ursprung=stand))
    tuer = [o for o in gefunden if abs(o.mitte[0] + stand[0] - 2.0) < 0.1]
    assert len(tuer) == 1
    assert tuer[0].breite_m == pytest.approx(0.8, abs=0.05)
    assert tuer[0].entfernung_m == pytest.approx(3.2, abs=0.05)
    # die breite Lücke davor wird nicht zusätzlich angeboten
    assert not any(o.breite_m > 1.3 and abs(o.richtung_grad) < 20 for o in gefunden)


def test_tuer_durch_eine_tuer_gesehen_die_naehere_bleibt():
    welt = [(-2, -2, 2, -2), (-2, 2, 2, 2), (-2, -2, -2, 2),
            (2, -2, 2, -0.4), (2, 0.4, 2, 2),                     # nahe Tür, 80 cm
            (2, -2, 3.5, -2), (2, 2, 3.5, 2),
            (3.5, -2, 3.5, -0.3), (3.5, 0.35, 3.5, 2),            # ferne Tür, 65 cm
            (3.5, -2, 6, -2), (6, -2, 6, 2), (6, 2, 3.5, 2)]
    gefunden = oeffnungen(*profil(welt))
    assert len(gefunden) == 1
    assert gefunden[0].entfernung_m == pytest.approx(2.0, abs=0.05)
    assert gefunden[0].breite_m == pytest.approx(0.8, abs=0.03)


# ------------------------------------------------------ Protokoll und Ursprung

def test_protokoll_nennt_angebotene_und_abgelehnte_luecken_mit_grund():
    nische = zimmer(tiefe_dahinter=0.45)              # hinter der Lücke nur 45 cm frei
    protokoll = []
    assert oeffnungen(*profil(nische), protokoll=protokoll) == []
    assert protokoll and {z['ergebnis'] for z in protokoll} == {'zu_flach'}
    zeile = protokoll[0]
    assert zeile['breite_m'] == pytest.approx(0.8, abs=0.03)
    assert zeile['tiefe_m'] == pytest.approx(0.45, abs=0.03)
    assert zeile['anteil_tief'] == 0.0 and zeile['nr'] is None

    protokoll = []
    gefunden = oeffnungen(*profil(zimmer()), protokoll=protokoll)
    angeboten = [z for z in protokoll if z['ergebnis'] == 'angeboten']
    assert [z['nr'] for z in angeboten] == [o.nr for o in gefunden] == [1]
    assert angeboten[0]['schluss'] == 'sprung'
    assert angeboten[0]['richtung_grad'] == pytest.approx(0.0, abs=1.5)
    # dieselbe Tür aus der zweiten Durchlaufrichtung ist als überdeckt vermerkt
    assert any(z['ergebnis'] == 'ueberdeckt' for z in protokoll)
    assert all(set(z) == {'ergebnis', 'nr', 'schluss', 'breite_m', 'richtung_grad',
                          'entfernung_m', 'strahlen', 'tiefe_m', 'anteil_tief',
                          'anteil_davor', 'blatt'} for z in protokoll)


def test_profil_von_einem_anderen_punkt_ergibt_dieselbe_lage_im_standpunktrahmen():
    lidar = (0.245, 0.0)
    von_dort = oeffnungen(*profil(zimmer(), ursprung=lidar), ursprung=lidar)
    assert len(von_dort) == 1
    assert von_dort[0].mitte == pytest.approx((2.0, 0.0), abs=0.03)
    assert von_dort[0].entfernung_m == pytest.approx(2.0, abs=0.03)
    assert von_dort[0].pfosten[0][0] == pytest.approx(2.0, abs=0.03)
    ohne_angabe = oeffnungen(*profil(zimmer(), ursprung=lidar))
    assert ohne_angabe[0].mitte[0] == pytest.approx(1.755, abs=0.03)
