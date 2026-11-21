"""Montage von Kamera und LiDAR, Projektion ins Bild."""
import math

import numpy as np
import pytest

from lotse.geometrie import (KAMERA_HOEHE_M, KAMERA_NEIGUNG_RAD, KAMERA_X_M,
                             Kamera, aus_tf, drehung_z, invertiere,
                             kamera_montage, lidar_montage,
                             standpunkt_nach_kamera, transformiere,
                             winkel_normieren)

KAMERA = Kamera.aus_oeffnungswinkel(640, 360, 69.0)


def test_kameramontage_ist_eine_starre_rechtshaendige_drehung():
    t = kamera_montage()
    r = t[:3, :3]
    assert np.allclose(r @ r.T, np.eye(3), atol=1e-12)
    assert np.isclose(np.linalg.det(r), 1.0)
    assert np.allclose(t[:3, 3], [KAMERA_X_M, 0.0, KAMERA_HOEHE_M])
    # Blickrichtung: nach vorn und um die Neigung nach unten
    blick = r[:, 2]
    assert np.isclose(math.degrees(math.atan2(-blick[2], blick[0])),
                      math.degrees(KAMERA_NEIGUNG_RAD))


def test_bodenpunkt_geradeaus_liegt_in_der_bildmitte_spalte():
    weite = 3.0
    im_kamerarahmen = standpunkt_nach_kamera([[weite, 0.0, 0.0]], 0.0, kamera_montage())
    uv, vorn = KAMERA.projiziere(im_kamerarahmen)
    assert vorn[0]
    assert uv[0, 0] == pytest.approx(KAMERA.cx, abs=1e-6)
    unter_achse = math.atan2(KAMERA_HOEHE_M, weite - KAMERA_X_M) - KAMERA_NEIGUNG_RAD
    assert uv[0, 1] == pytest.approx(KAMERA.cy + KAMERA.fy * math.tan(unter_achse), abs=1e-6)


def test_die_kamera_sieht_den_boden_erst_ab_etwa_1_6_m():
    """Rechnung aus KONZEPT §5: 640 x 360, 69 Grad breit, 18,94 Grad geneigt."""
    waagerecht, senkrecht = KAMERA.oeffnungswinkel_grad()
    assert waagerecht == pytest.approx(69.0)
    assert senkrecht == pytest.approx(42.3, abs=0.1)
    weiten = np.arange(1.0, 4.0, 0.01)
    punkte = np.column_stack([weiten + KAMERA_X_M, np.zeros_like(weiten),
                              np.zeros_like(weiten)])
    uv, vorn = KAMERA.projiziere(standpunkt_nach_kamera(punkte, 0.0, kamera_montage()))
    im_bild = vorn & (uv[:, 1] <= KAMERA.hoehe - 1)
    assert weiten[im_bild][0] == pytest.approx(1.6, abs=0.05)
    # nach oben reicht das Bild nur knapp über die Waagerechte
    oben = math.degrees(math.atan(KAMERA.cy / KAMERA.fy)) - math.degrees(KAMERA_NEIGUNG_RAD)
    assert 1.5 < oben < 3.0


def test_ein_punkt_links_steht_nach_linksdrehung_in_der_bildmitte():
    links = [[0.0, 3.0, 0.0]]
    _, vorn = KAMERA.projiziere(standpunkt_nach_kamera(links, 0.0, kamera_montage()))
    assert not vorn[0]
    uv, vorn = KAMERA.projiziere(
        standpunkt_nach_kamera(links, math.pi / 2, kamera_montage()))
    assert vorn[0]
    assert uv[0, 0] == pytest.approx(KAMERA.cx, abs=1e-6)


def test_links_im_raum_ist_links_im_bild():
    uv, vorn = KAMERA.projiziere(
        standpunkt_nach_kamera([[3.0, 0.5, 0.0], [3.0, -0.5, 0.0]], 0.0, kamera_montage()))
    assert vorn.all()
    assert uv[0, 0] < KAMERA.cx < uv[1, 0]


def test_punkte_hinter_der_kamera_und_weit_ausserhalb_gelten_nicht_als_vorn():
    _, vorn = KAMERA.projiziere([[0.0, 0.0, -1.0], [50.0, 0.0, 1.0], [0.0, 0.0, 2.0]])
    assert vorn.tolist() == [False, False, True]


def test_verzeichnung_null_aendert_nichts_und_k1_verschiebt_nach_aussen():
    punkt = [[0.3, 0.1, 1.0]]
    ohne, _ = KAMERA.projiziere(punkt)
    null, _ = Kamera(640, 360, KAMERA.fx, KAMERA.fy, KAMERA.cx, KAMERA.cy,
                     (0.0,) * 5).projiziere(punkt)
    assert np.allclose(ohne, null)
    tonne, _ = Kamera(640, 360, KAMERA.fx, KAMERA.fy, KAMERA.cx, KAMERA.cy,
                      (0.1, 0.0, 0.0, 0.0, 0.0)).projiziere(punkt)
    assert tonne[0, 0] > ohne[0, 0] and tonne[0, 1] > ohne[0, 1]


def test_kamera_aus_info_und_zurueck():
    info = KAMERA.als_info()
    assert Kamera.aus_info(info) == KAMERA
    with pytest.raises(ValueError):
        Kamera.aus_info({'breite': 640, 'hoehe': 360, 'k': [0.0] * 9})


def test_lidar_montage_und_tf():
    t = lidar_montage()
    # ein Punkt 1 m vor dem LiDAR (dessen x zeigt wegen 90 Grad Gier nach links)
    assert np.allclose(transformiere(t, [[1.0, 0.0, 0.0]])[0], [0.245, 1.0, 0.75])
    halb = math.sqrt(0.5)
    aus = aus_tf([0.245, 0.0, 0.66], [0.0, 0.0, halb, halb])     # 90 Grad um z
    assert np.allclose(aus, t, atol=1e-9)
    with pytest.raises(ValueError):
        aus_tf([0, 0, 0], [0, 0, 0, 0])


def test_invertiere_und_winkel_normieren():
    t = kamera_montage(gier_rad=0.4)
    assert np.allclose(invertiere(t) @ t, np.eye(4), atol=1e-12)
    assert np.allclose(drehung_z(0.3) @ drehung_z(-0.3), np.eye(3))
    assert winkel_normieren(3 * math.pi / 2) == pytest.approx(-math.pi / 2)
    assert winkel_normieren(-math.pi) == pytest.approx(-math.pi)
