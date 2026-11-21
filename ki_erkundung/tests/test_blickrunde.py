"""Aufnahmeformat, Drehwinkel aus den Scans, Bildauswahl, Rundum-Profil."""
import json
import math

import numpy as np
import pytest

import beispielrunde_erzeugen as welt
from lotse.blickrunde import (Blickrunde, bilder_waehlen, echo_statistik,
                              gier_schaetzen, profil_der_runde, profil_ursprung,
                              runden_finden, rundum_profil, stand_profil,
                              scan_als_dict, scan_felder, scan_punkte,
                              schreibe_runde)
from lotse.kandidaten import oeffnungen
from lotse.geometrie import Kamera, kamera_montage, lidar_montage


def scans_der_welt(schritt_grad=5.0, gesamt_grad=365.0, drehsinn=1, saat=2,
                   standpunkt=welt.STANDPUNKT):
    zufall = np.random.default_rng(saat)
    x, y, gier0 = standpunkt
    flaechen = welt.welt()
    wahr = [drehsinn * math.radians(k * schritt_grad)
            for k in range(int(gesamt_grad / schritt_grad) + 1)]
    return ([welt.scan(flaechen, x, y, gier0 + g, 1000.0 + i, zufall=zufall)
             for i, g in enumerate(wahr)], np.array(wahr))


def test_scan_hin_und_zurueck_mit_ungueltig_und_weit():
    scan = scan_als_dict(-1.0, 0.5, [1.0, float('nan'), float('inf'), 0.01, 30.0, 2.12345],
                         0.03, 25.0, 12.5)
    assert scan['entfernungen'] == [1.0, None, None, None, None, 2.123]
    assert scan['weit'] == [2, 4]
    json.dumps(scan)                                  # ohne NaN/Infinity speicherbar
    winkel, r = scan_felder(scan)
    assert winkel.tolist() == [-1.0, -0.5, 0.0, 0.5, 1.0, 1.5]
    assert r[0] == 1.0 and np.isnan(r[1]) and np.isinf(r[2])
    assert np.isnan(r[3]) and np.isinf(r[4]) and r[5] == 2.123


def test_scan_punkte_liegen_im_bodenrahmen_des_roboters():
    # ein Echo 2 m in LiDAR-x; das LiDAR ist um 90 Grad gedreht und 0,245 m vorn
    scan = scan_als_dict(0.0, 0.1, [2.0], 0.03, 25.0, 0.0)
    assert scan_punkte(scan, lidar_montage())[0] == pytest.approx([0.245, 2.0])


@pytest.mark.parametrize('drehsinn', [1, -1])
def test_drehwinkel_aus_den_scans_auf_ein_grad_genau(drehsinn):
    scans, wahr = scans_der_welt(drehsinn=drehsinn)
    gier, guete = gier_schaetzen(scans, lidar_montage())
    assert np.degrees(np.abs(gier - wahr)).max() < 1.0
    assert guete.min() > 0.9
    assert abs(math.degrees(gier[-1])) == pytest.approx(365.0, abs=1.0)


def test_drehwinkel_auch_bei_groben_schritten_und_anderem_standpunkt():
    scans, wahr = scans_der_welt(schritt_grad=12.0,
                                 standpunkt=(2.6, 2.2, math.radians(200.0)))
    gier, _ = gier_schaetzen(scans, lidar_montage())
    assert np.degrees(np.abs(gier - wahr)).max() < 1.0


def test_vorgabe_aus_der_odometrie_ist_nur_startwert():
    scans, wahr = scans_der_welt(schritt_grad=10.0)
    schlecht = (wahr * 1.15).tolist()                 # Odometrie 15 % daneben
    gier, _ = gier_schaetzen(scans, lidar_montage(), vorgabe_rad=schlecht)
    assert np.degrees(np.abs(gier - wahr)).max() < 1.0


def test_aufnahme_ohne_messpunkte_bekommt_guete_null():
    scans, _ = scans_der_welt(gesamt_grad=20.0)
    leer = dict(scans[2], entfernungen=[None] * len(scans[2]['entfernungen']), weit=[])
    gier, guete = gier_schaetzen([scans[0], scans[1], leer, scans[3]], lidar_montage())
    assert guete[2] == 0.0
    assert gier[2] == gier[1]
    assert guete[3] > 0.9


def test_keine_scans_ergeben_leere_felder():
    gier, guete = gier_schaetzen([], lidar_montage())
    assert len(gier) == 0 and len(guete) == 0


def test_acht_bilder_im_abstand_von_45_grad():
    gier = np.radians(np.arange(0.0, 366.0, 5.0))
    auswahl = bilder_waehlen(gier)
    assert auswahl['vollstaendig'] and auswahl['drehsinn'] == 1
    assert [b['bild'] for b in auswahl['bilder']] == list(range(1, 9))
    assert [round(math.degrees(b['gier_rad'])) for b in auswahl['bilder']] == [
        0, 45, 90, 135, 180, 225, 270, 315]
    assert auswahl['gedreht_grad'] == pytest.approx(365.0)


def test_rechtsherum_gedreht_zaehlt_im_uhrzeigersinn():
    auswahl = bilder_waehlen(-np.radians(np.arange(0.0, 366.0, 5.0)))
    assert auswahl['vollstaendig'] and auswahl['drehsinn'] == -1
    assert round(math.degrees(auswahl['bilder'][1]['gier_rad'])) == -45


def test_unvollstaendige_drehung_wird_als_unvollstaendig_gemeldet():
    auswahl = bilder_waehlen(np.radians(np.arange(0.0, 201.0, 5.0)))
    assert not auswahl['vollstaendig']
    assert [b['bild'] for b in auswahl['bilder']] == [1, 2, 3, 4, 5]
    assert bilder_waehlen([]) == {'bilder': [], 'vollstaendig': False, 'drehsinn': 0,
                                  'gedreht_grad': 0.0, 'ende_grad': 0.0}


def test_bei_gleicher_lage_gewinnt_die_ruhigste_aufnahme():
    # um 45 Grad: erst schnell vorbei (44 Grad), dann stehend (46, 46, 46 Grad)
    gier = np.radians([0, 20, 44, 46, 46, 46, 70, 90, 135, 180, 225, 270, 315, 360])
    auswahl = bilder_waehlen(gier)
    assert auswahl['bilder'][1]['aufnahme'] == 4


def test_rundum_profil_kennt_den_mastsektor_erst_nach_der_drehung():
    scans, wahr = scans_der_welt()
    _, nur_einer = rundum_profil(scans[:1], wahr[:1], lidar_montage())
    unbeobachtet = np.isnan(nur_einer).mean() * 360.0
    assert 55.0 < unbeobachtet < 80.0                 # 68 Grad Mast
    winkel, alle = rundum_profil(scans, wahr, lidar_montage())
    assert not np.isnan(alle).any()
    assert len(winkel) == len(alle) == 720
    # Standpunkt (1,8 / 1,5), Blick nach Norden: links die Westwand in 1,8 m,
    # genau hinten die Glastür; dort misst das LiDAR die Brüstung in 2,7 m.
    links = alle[np.abs(winkel - math.pi / 2) < math.radians(4)]
    assert np.median(links) == pytest.approx(1.8, abs=0.1)
    hinten = alle[np.abs(np.abs(winkel) - math.pi) < math.radians(4)]
    assert np.median(hinten) == pytest.approx(2.7, abs=0.1)


def test_blickrunde_schreiben_und_laden(tmp_path):
    kamera = Kamera.aus_oeffnungswinkel(640, 360, 69.0)
    scans, _ = scans_der_welt(gesamt_grad=10.0)
    ordner = schreibe_runde(tmp_path / 'r1', 'flur_mitte', kamera,
                            [b'jpeg0', b'jpeg1', b'jpeg2'], scans, [1.0, 1.5, 2.0],
                            tiefen=[b'png0', None, b'png2'],
                            gier_odom=[0.0, 0.1, 0.2],
                            boden_kamera=kamera_montage(), boden_lidar=lidar_montage())
    assert runden_finden(tmp_path) == [ordner]
    assert runden_finden(ordner) == [ordner]
    runde = Blickrunde.lade(ordner)
    assert runde.name == 'flur_mitte'
    assert len(runde.aufnahmen) == 3
    assert runde.bild_bytes(1) == b'jpeg1'
    assert runde.aufnahmen[0]['tiefe'] == 'tiefe_000.png'
    assert 'tiefe' not in runde.aufnahmen[1]
    assert runde.scan(2)['t'] == scans[2]['t']
    assert runde.kamera() == kamera
    assert np.allclose(runde.boden_lidar(), lidar_montage())
    assert runde.vorgabe_gier() == [0.0, 0.1, 0.2]


def test_fehlende_montage_faellt_auf_die_projektvorgaben_zurueck(tmp_path):
    kamera = Kamera.aus_oeffnungswinkel(640, 360, 69.0)
    ordner = schreibe_runde(tmp_path / 'r', 'x', kamera, [b'a'], [None], [0.0])
    runde = Blickrunde.lade(ordner)
    assert np.allclose(runde.boden_kamera(), kamera_montage())
    assert np.allclose(runde.boden_lidar(), lidar_montage())
    assert runde.scan(0) is None
    assert runde.vorgabe_gier() is None


def test_unbekannte_fassung_und_kaputte_montage_werden_abgelehnt(tmp_path):
    kamera = Kamera.aus_oeffnungswinkel(640, 360, 69.0)
    ordner = schreibe_runde(tmp_path / 'r', 'x', kamera, [b'a'], [None], [0.0])
    meta = json.loads((ordner / 'meta.json').read_text(encoding='utf-8'))
    meta['schema_version'] = 99
    (ordner / 'meta.json').write_text(json.dumps(meta), encoding='utf-8')
    with pytest.raises(ValueError, match='schema_version'):
        Blickrunde.lade(ordner)
    meta['schema_version'] = 1
    meta['montage']['boden_lidar'] = [[1, 0], [0, 1]]
    (ordner / 'meta.json').write_text(json.dumps(meta), encoding='utf-8')
    with pytest.raises(ValueError, match='4x4'):
        Blickrunde.lade(ordner).boden_lidar()


def test_profil_ursprung_ist_im_stand_das_lidar_und_nach_drehung_die_antriebsmitte():
    lidar = lidar_montage()
    assert profil_ursprung([0.0, 0.001, -0.002], lidar) == pytest.approx((0.245, 0.0), abs=1e-3)
    assert profil_ursprung(np.radians([0, 20, 45, 90]), lidar) == pytest.approx((0.0, 0.0))
    assert profil_ursprung([], lidar) == pytest.approx((0.0, 0.0))
    # Der Stand zählt in der Blickrichtung, in der gestanden wurde.
    assert profil_ursprung([math.pi / 2] * 3, lidar) == pytest.approx((0.0, 0.245), abs=1e-3)


def test_im_stand_entsteht_von_der_antriebsmitte_aus_eine_scheinoeffnung_vom_lidar_aus_nicht():
    """Hinter jeder nahen Kante liegt ein Keil, den das LiDAR nie gesehen hat.

    Standpunkt dicht am Schrank: Von der Antriebsmitte aus gerechnet wirkt
    die 50 cm tiefe Schranknische wie eine Öffnung, weil der Strahl an der
    Schrankecke vorbei in den nie gesehenen Keil läuft. Vom Ort des LiDAR
    aus gerechnet gibt es den Keil nicht.
    """
    zufall = np.random.default_rng(3)
    stand = (2.3, 2.3, 0.0)
    flaechen = welt.welt()
    scans = [welt.scan(flaechen, *stand, 1000.0 + 0.5 * k, zufall=zufall) for k in range(16)]
    lidar = lidar_montage()
    gier, _ = gier_schaetzen(scans, lidar)
    spalt = np.array([1.55, 3.15]) - np.array(stand[:2])       # Mitte der Schranknische

    def in_der_nische(gefunden):
        return [o for o in gefunden if np.hypot(*(np.array(o.mitte) - spalt)) < 0.4]

    von_der_mitte = oeffnungen(*rundum_profil(scans, gier, lidar))
    assert len(in_der_nische(von_der_mitte)) == 1
    ursprung = profil_ursprung(gier, lidar)
    vom_lidar = oeffnungen(*rundum_profil(scans, gier, lidar, ursprung=ursprung),
                           ursprung=ursprung)
    assert in_der_nische(vom_lidar) == []
    # Tür und Glastür bleiben dieselben.
    assert len(vom_lidar) == 2 and len(von_der_mitte) == 3


def test_echo_statistik_zeigt_ruhige_waende_und_unruhige_oder_stumme_richtungen():
    """Glas und gestreifte Kanten geben mal ein nahes, mal ein fernes, mal kein Echo."""
    lidar = lidar_montage()
    winkel = -math.pi + (2 * math.pi / 720) * np.arange(720)
    scans = []
    for k in range(10):
        r = np.full(720, 3.0)
        r[100:140] = 1.5 if k % 2 else 4.0            # unruhig: springt zwischen den Aufnahmen
        r[300:340] = np.nan                           # stumm: nie ein Echo
        scans.append(scan_als_dict(float(winkel[0]), 2 * math.pi / 720, r, 0.03, 25.0, k))
    ursprung = profil_ursprung(np.zeros(10), lidar)
    anteil, spanne = echo_statistik(scans, np.zeros(10), lidar, ursprung)
    assert anteil.shape == spanne.shape == (720,)
    unruhig = np.nan_to_num(spanne) > 0.3
    with np.errstate(invalid='ignore'):
        stumm = anteil < 0.5                              # nan (kein Strahl) zählt nicht
    assert 30 <= unruhig.sum() <= 45 and 30 <= stumm.sum() <= 45
    assert not (unruhig & stumm).any()
    ruhig = ~unruhig & ~stumm & ~np.isnan(anteil)
    assert ruhig.sum() >= 500 and float(np.nanmax(spanne[ruhig])) < 0.05


def scans_im_stand(stand, tuerblatt_grad=None, rauschen_m=0.02, strahlen=2160, anzahl=16,
                   flur_breite_m=2.2, saat=5):
    """Aufnahmen wie am echten Gerät: 2160 Strahlen je Umlauf, 2 cm Rauschen."""
    zufall = np.random.default_rng(saat)
    flaechen = welt.welt(tuerblatt_grad, flur_breite_m)
    return [welt.scan(flaechen, *stand, 1000.0 + 0.1 * k, rauschen_m=rauschen_m,
                      strahlen=strahlen, zufall=zufall) for k in range(anzahl)]


def tuer_in(gefunden, stand):
    """Die Öffnung, deren Mitte an der Flurtür des Beispielzimmers liegt (oder None)."""
    mitte, _, _ = welt.tuer_im_standpunktrahmen(stand)
    nah = [o for o in gefunden if np.hypot(*(np.array(o.mitte) - mitte)) < 0.15]
    return nah[0] if len(nah) == 1 else None


def test_im_stand_misst_der_median_genauer_als_das_raster_und_findet_das_tuerblatt():
    """Befund KI-0N (21.11.2026), nachgestellt mit dem Rauschen des echten LiDAR.

    Mit Raster: An der echten Tür stand „keine Wandlinie“, die Tür blieb
    1,24 m breit mit der Nummer neben der Tür. Im künstlichen Zimmer ergibt
    dasselbe Vorgehen bei 2 cm Rauschen 1,22 m. Der Median je Richtung
    vermisst sie richtig.
    """
    lidar = lidar_montage()
    stand = (1.6, 2.4, math.radians(-20.0))            # Scharnierseite, Blatt bei 90 Grad
    scans = scans_im_stand(stand, tuerblatt_grad=90.0)
    gier, _ = gier_schaetzen(scans, lidar)
    ursprung = profil_ursprung(gier, lidar)

    mit_raster = oeffnungen(*rundum_profil(scans, gier, lidar, ursprung=ursprung),
                            ursprung=ursprung)
    assert tuer_in(mit_raster, stand) is None
    zu_breit = [o for o in mit_raster if abs(o.richtung_grad) < 15 and o.breite_m > 1.1]
    assert len(zu_breit) == 1 and zu_breit[0].schluss == 'sprung'

    winkel, entfernung, wieder = profil_der_runde(scans, gier, lidar)
    assert wieder == pytest.approx(ursprung)
    tuer = tuer_in(oeffnungen(winkel, entfernung, ursprung=ursprung), stand)
    assert tuer is not None and tuer.schluss == 'blatt'
    assert tuer.breite_m == pytest.approx(0.80, abs=0.04)


@pytest.mark.parametrize('stand', [(2.0, 1.4, 0.0), (1.6, 2.4, math.radians(-20.0)),
                                   (0.9, 1.4, 0.0)])
def test_im_stand_stimmt_die_tuerbreite_auf_wenige_zentimeter(stand):
    """Von vorn wurde die 85-cm-Labortür mit Raster 0,72 bis 0,75 m breit vermessen."""
    lidar = lidar_montage()
    scans = scans_im_stand(stand, rauschen_m=0.03)
    gier, _ = gier_schaetzen(scans, lidar)
    winkel, entfernung, ursprung = profil_der_runde(scans, gier, lidar)
    tuer = tuer_in(oeffnungen(winkel, entfernung, ursprung=ursprung), stand)
    assert tuer is not None
    assert tuer.breite_m == pytest.approx(0.80, abs=0.04)


def test_stand_profil_kennt_unbeobachtet_kein_echo_und_groebere_scans():
    lidar = lidar_montage()
    schritt = 2 * math.pi / 360                        # halb so viele Strahlen wie Fächer
    winkel = -math.pi + schritt * np.arange(360)
    r = np.full(360, 2.0)
    r[40:60] = np.nan                                  # nie ein Echo, nie eine Messung
    r[100:120] = np.inf                                # frei bis zur Reichweite
    r[200] = 9.5                                       # jenseits der Reichweite: frei
    scans = [scan_als_dict(float(winkel[0]), schritt, r, 0.03, 25.0, k) for k in range(6)]
    richtung, profil = stand_profil(scans, np.zeros(6), lidar)
    assert richtung.shape == profil.shape == (720,)
    assert np.isnan(profil).sum() == pytest.approx(40, abs=3)
    # 20 Strahlen ohne Echo und der eine jenseits der Reichweite, je zwei Fächer breit
    assert np.isinf(profil).sum() == pytest.approx(43, abs=3)
    gemessen = profil[np.isfinite(profil)]
    assert gemessen.size >= 630 and np.all(gemessen == 2.0)
    # nach einer Drehung nimmt profil_der_runde das Raster und die Antriebsmitte
    gedreht, wahr = scans_der_welt(schritt_grad=15.0)
    _, _, ursprung = profil_der_runde(gedreht, wahr, lidar)
    assert ursprung == pytest.approx((0.0, 0.0))
