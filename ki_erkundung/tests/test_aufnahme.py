"""Aufnahme einer Blickrunde: Zuordnung nach Zeit, Ablageort, Schreiben."""
import math
import subprocess

import pytest

import beispielrunde_erzeugen as welt
from blickrunde_aufnehmen import (Sammler, VORGABE_ZIEL, gier_aus_quaternion,
                                  im_repository, main, schreibe)
from lotse.ablauf import bereite_vor
from lotse.blickrunde import Blickrunde
from lotse.geometrie import Kamera, kamera_montage, lidar_montage

KAMERA = Kamera.aus_oeffnungswinkel(640, 360, 69.0)


def test_bild_wird_mit_dem_zeitlich_naechsten_scan_zur_aufnahme():
    sammler = Sammler()
    for i in range(10):                                   # Scans mit 10 Hz
        sammler.scan(100.0 + 0.1 * i, {'t': 100.0 + 0.1 * i})
        if i == 3:
            sammler.tiefe(100.31, b'tiefe')
            sammler.gier(100.30, 0.5)
            sammler.bild(100.32, b'bild')
    assert len(sammler.aufnahmen) == 1
    aufnahme = sammler.aufnahmen[0]
    assert aufnahme['scan']['t'] == pytest.approx(100.3)
    assert aufnahme['tiefe'] == b'tiefe' and aufnahme['gier_odom'] == 0.5
    assert aufnahme['bild'] == b'bild' and aufnahme['t'] == 100.32


def test_bild_wartet_auf_den_naeheren_spaeteren_scan():
    sammler = Sammler()
    sammler.scan(100.00, {'t': 100.00})
    sammler.bild(100.09, b'bild')
    assert sammler.aufnahmen == []                        # der Scan bei 100,10 fehlt noch
    sammler.scan(100.10, {'t': 100.10})
    assert sammler.aufnahmen == []
    sammler.scan(100.30, {'t': 100.30})                   # jetzt kommt kein näherer mehr
    assert sammler.aufnahmen[0]['scan']['t'] == 100.10


def test_bild_ohne_passenden_scan_wird_verworfen_und_gezaehlt():
    sammler = Sammler()
    sammler.scan(100.0, {'t': 100.0})
    sammler.bild(100.5, b'allein')                        # nächster Scan 0,5 s entfernt
    sammler.scan(101.0, {'t': 101.0})
    assert sammler.abschliessen() == []
    assert sammler.verworfen_ohne_scan == 1


def test_zu_dicht_folgende_bilder_werden_uebersprungen():
    sammler = Sammler(min_abstand_s=0.35)
    for i in range(40):
        sammler.scan(100.0 + 0.05 * i, {'t': 100.0 + 0.05 * i})
    for t in (100.0, 100.1, 100.2, 100.5, 100.6, 101.0):
        sammler.bild(t, b'x')
    sammler.scan(102.0, {})
    assert [a['t'] for a in sammler.abschliessen()] == [100.0, 100.5, 101.0]
    assert sammler.uebersprungen_zu_dicht == 3


def test_aufnahme_ohne_tiefe_und_odometrie_bleibt_gueltig():
    sammler = Sammler()
    sammler.scan(100.0, {'t': 100.0})
    sammler.bild(100.02, b'x')
    aufnahme = sammler.abschliessen()[0]
    assert aufnahme['tiefe'] is None and aufnahme['gier_odom'] is None
    assert sammler.gedreht_grad() is None


def test_gedrehter_winkel_laut_odometrie_laeuft_ueber_180_grad_hinweg():
    sammler = Sammler()
    for i in range(37):                                   # 360 Grad in 10-Grad-Schritten
        t = 100.0 + i
        sammler.scan(t, {'t': t})
        gier = math.radians(10.0 * i)
        sammler.gier(t, math.atan2(math.sin(gier), math.cos(gier)))
        sammler.bild(t, b'x')
    sammler.abschliessen()
    assert sammler.gedreht_grad() == pytest.approx(360.0, abs=0.5)
    assert gier_aus_quaternion(0.0, 0.0, math.sin(0.4), math.cos(0.4)) == pytest.approx(0.8)


def test_geschriebene_aufnahme_laeuft_durch_den_trockenlauf(tmp_path):
    """Echte Bilder und Scans der Beispielwelt, durch den Sammler geschickt."""
    flaechen = welt.welt()
    x, y, gier0 = welt.STANDPUNKT
    sammler = Sammler()
    for k in range(75):
        gier = gier0 + math.radians(5.0 * k)
        t = 500.0 + 0.5 * k
        sammler.scan(t - 0.04, welt.scan(flaechen, x, y, gier, t - 0.04))
        sammler.gier(t, gier - gier0)
        sammler.bild(t, welt.foto(flaechen, KAMERA, x, y, gier))
        sammler.scan(t + 0.06, welt.scan(flaechen, x, y, gier, t + 0.06))
    ordner = schreibe(sammler, tmp_path / 'r', 'beispiel', KAMERA,
                      kamera_montage(), lidar_montage(), {'scan_topic': '/scan'})
    runde = Blickrunde.lade(ordner)
    assert len(runde.aufnahmen) == 75
    assert runde.meta['montage']['quelle'] == 'tf'
    assert runde.meta['quelle']['verworfen_ohne_scan'] == 0
    assert runde.vorgabe_gier() is not None
    vorbereitung = bereite_vor(runde)
    assert vorbereitung.auswahl['vollstaendig'] and len(vorbereitung.oeffnungen) == 2


def test_ohne_aufnahmen_oder_ohne_kameradaten_wird_nichts_geschrieben(tmp_path, capsys):
    assert schreibe(Sammler(), tmp_path / 'leer', 'x', KAMERA, None, None, {}) is None
    assert 'Keine vollständige Aufnahme' in capsys.readouterr().err
    sammler = Sammler()
    sammler.scan(1.0, {'t': 1.0})
    sammler.bild(1.0, b'x')
    assert schreibe(sammler, tmp_path / 'ohne', 'x', None, None, None, {}) is None
    assert 'camera_info' in capsys.readouterr().err
    assert not (tmp_path / 'leer').exists() and not (tmp_path / 'ohne').exists()


def test_montage_ohne_tf_wird_als_vorgabe_vermerkt(tmp_path):
    sammler = Sammler()
    sammler.scan(1.0, {'t': 1.0})
    sammler.bild(1.0, b'x')
    ordner = schreibe(sammler, tmp_path / 'r', 'x', KAMERA, None, lidar_montage(), {})
    assert Blickrunde.lade(ordner).meta['montage']['quelle'] == 'vorgabe'


def test_ziel_im_repository_wird_abgelehnt(tmp_path, capsys):
    """Aufnahmen der Wohnung gehören nicht ins Repository (AGENTS §2.5)."""
    lager = tmp_path / 'lager'
    lager.mkdir()
    subprocess.run(['git', 'init', '-q', str(lager)], check=True)
    assert im_repository(lager / 'daten' / 'runden')
    assert not im_repository(tmp_path / 'woanders')
    assert main(['--name', 'labor_mitte', '--ausgabe', str(lager / 'daten')]) == 2
    assert 'gehören nicht ins Repository' in capsys.readouterr().err
    assert main(['--name', '../boese', '--ausgabe', str(tmp_path / 'x')]) == 2
    assert '.local/share/amadeus/ki_erkundung/blickrunden' in str(VORGABE_ZIEL)
