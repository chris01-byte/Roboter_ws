import importlib.util
import math
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).parent))
spec = importlib.util.spec_from_file_location(
    'sh_welt', Path(__file__).with_name('sh_robustheit_welt.py'))
welt = importlib.util.module_from_spec(spec)
spec.loader.exec_module(welt)


def _unterste_zeile(az_deg=0.):
    """Mittelstrahl der untersten VL53-Zeile (-26,25 Grad), Basisrahmen."""
    el, az = math.radians(-26.25), math.radians(az_deg)
    return np.array([[math.cos(el)*math.cos(az), math.cos(el)*math.sin(az), math.sin(el)]])


def test_low_obstacle_is_seen_by_vl53_but_not_by_the_lidar():
    w = welt.RobustheitsWelt(.8, [-1.9, -.45, 0.])
    mount = (.290, .095, .215)
    leer = w.cone_returns(mount, _unterste_zeile())[0]
    # Ohne Objekt trifft die unterste Zeile den Boden bei 0,69 m; der
    # VL53-Knoten verwirft das wegen z_max 0,50 m (wie am Jetson gemessen).
    assert leer == pytest.approx(.305/math.sin(math.radians(26.25)), abs=1e-3)
    # Box 10 cm hoch, Vorderkante 0,42 m vor dem Sensor (x_base 0,71 m).
    w.setze_niedriges_hindernis((-1.9+.71+.15, -.45+.095), .3, .10)
    treffer = w.cone_returns(mount, _unterste_zeile())[0]
    assert 0.40 < treffer < 0.50                  # Oberseite der Box, innerhalb z_max
    _, vorher = welt.World(.8, [-1.9, -.45, 0.]).laser(beams=8, mask=False)
    _, nachher = w.laser(beams=8, mask=False)
    assert np.allclose(vorher, nachher)           # LiDAR in 0,66 m Höhe unverändert


def test_closed_door_blocks_the_ray_through_the_opening():
    w = welt.RobustheitsWelt(.8, [-1.9, 0., 0.])
    offen = w.raycast([-1., 0.], np.array([0.]))[0]
    w.schliesse_tuer('links')
    zu = w.raycast([-1., 0.], np.array([0.]))[0]
    assert zu == pytest.approx(.36) and offen > 1.0


def test_late_timer_is_integrated_in_small_steps_and_recorded():
    w = welt.RobustheitsWelt(.8, [-1.9, -.45, 0.])
    for _ in range(50):
        w.integrate((.1, 0.), .01)
    x = w.pose[0]
    w.integrate((.1, 0.), .2)                     # 200-ms-Lücke unter Last
    assert w.pose[0] == pytest.approx(x+.02, abs=2e-3)
    assert w.verspaetungen == [.2]


def test_driving_into_a_low_obstacle_is_a_collision():
    w = welt.RobustheitsWelt(.8, [-1.9, -.45, 0.])
    box = w.setze_niedriges_hindernis((-1.9+.6, -.45), .2, .05)
    assert w.frei(box)
    for _ in range(600):
        w.integrate((.1, 0.), .01)
    assert w.collision is True


def test_placement_check_rejects_boxes_in_walls_or_under_the_robot():
    w = welt.RobustheitsWelt(.8, [-1.9, -.45, 0.])
    assert not w.frei(welt.rectangle(-2.9, -2.7, 0., .2))      # in der Außenwand
    assert not w.frei(welt.rectangle(-2.0, -1.8, -.5, -.4))    # unter dem Roboter


def test_point_distance_and_map_frame_match_the_world_geometry():
    w = welt.RobustheitsWelt(.8, [-1.9, -.45, 0.])
    # Mitte der Verbindung: 0,42 m bis zu den Wänden bei y = ±0,42.
    assert w.punkt_abstand((0., 0.)) == pytest.approx(.42)
    # Diagonal vor der Ecke des rechten unteren Türpfostens (0,64 / -0,40).
    assert w.punkt_abstand((.64+.3, -.4+.4)) == pytest.approx(.5)
    # Karte = Startpose als Ursprung; World.local ist die Umkehrung.
    punkt = np.array([[1.3, .2]])
    assert np.allclose(w.local(w.karte_zu_welt(punkt)), punkt)
    gedreht = welt.RobustheitsWelt(.8, [-1.9, -.45, .7])
    assert np.allclose(gedreht.local(gedreht.karte_zu_welt(punkt)), punkt)


def test_closest_point_records_time_and_centre_distance():
    w = welt.RobustheitsWelt(.8, [-1.9, -.45, 0.])
    w.zeit_s = 12.5
    w.integrate((.1, 0.), .01)
    assert w.engste_stelle['t_s'] == 12.5
    assert w.engste_stelle['mitte_abstand_m'] == pytest.approx(w.punkt_abstand(w.pose[:2]), abs=1e-4)
    assert w.mitte_min['abstand_m'] == w.engste_stelle['mitte_abstand_m']


def test_reachable_coverage_excludes_the_room_behind_a_closed_door():
    w = welt.RobustheitsWelt(.8, [-1.9, -.45, 0.])
    res = .05
    # Ideale Karte im Kartenrahmen: alles frei, was die Welt frei kennt.
    # Welt x -2,8..2,8 / y -1,4..1,4 liegt im Kartenrahmen bei x -0,9..4,7 / y -0,95..1,85.
    ys, xs = np.mgrid[-1.2:2.0:res, -1.0:5.0:res]
    karte = np.zeros(xs.shape, dtype=int)
    voll = w.abdeckung_erreichbar(karte, res, (-1.0, -1.2))
    assert voll['erreichbar_anteil'] == pytest.approx(1.)
    w.schliesse_tuer('rechts')
    zu = w.abdeckung_erreichbar(karte, res, (-1.0, -1.2))
    assert zu['erreichbar_zellen'] < .6*voll['erreichbar_zellen']   # rechter Raum fällt weg
    karte[:, :] = -1                                                  # nichts gesehen
    assert w.abdeckung_erreichbar(karte, res, (-1.0, -1.2))['erreichbar_anteil'] == 0.
