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
