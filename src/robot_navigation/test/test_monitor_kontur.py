"""KM-2: Kontur für den Kollisionsmonitor, Rückzug nur bei gerader Rückwärtsfahrt."""
import ast
import re
from pathlib import Path

import pytest
import yaml

from robot_navigation import monitor_kontur as mk
from robot_navigation.rueckfahr_kontur import STANDARD_PUNKTE, kontur_punkte

REPO = Path(__file__).parents[3]
QUELLE = (REPO/'src/robot_navigation/robot_navigation/monitor_kontur.py').read_text(encoding='utf-8')


def test_retreat_contour_only_for_a_fresh_straight_reverse_command():
    assert mk.rueckzug_erlaubt(-0.05, 0.0, 0.05) is True
    assert mk.rueckzug_erlaubt(-0.015, 0.0, 0.05) is True        # Langsam-Zone
    assert mk.rueckzug_erlaubt(-0.006, 0.0, 0.0) is True         # erster Rampenschritt des Glätters
    # Vorwärts, Stand und Drehen behalten die volle Kontur (kein Rückfall auf Variante A).
    assert mk.rueckzug_erlaubt(0.05, 0.0, 0.05) is False
    assert mk.rueckzug_erlaubt(0.0, 0.0, 0.05) is False
    assert mk.rueckzug_erlaubt(0.0, 0.25, 0.05) is False
    assert mk.rueckzug_erlaubt(0.0, -0.04, 0.05) is False        # langsames Drehen auf der Stelle
    assert mk.rueckzug_erlaubt(-0.05, 0.05, 0.05) is False       # rückwärts mit Drehung
    assert mk.rueckzug_erlaubt(-0.001, 0.0, 0.05) is False       # praktisch Stand
    # Kein oder ein alter Befehl: volle Kontur.
    assert mk.rueckzug_erlaubt(-0.05, 0.0, None) is False
    assert mk.rueckzug_erlaubt(-0.05, 0.0, 0.31) is False
    assert mk.rueckzug_erlaubt(-0.05, 0.0, -0.1) is False
    assert mk.BEFEHL_ALTER_S <= 0.3 and mk.W_GERADE_RADPS <= 0.02


def test_full_contour_is_exactly_the_padded_footprint_of_the_local_costmap():
    nav = yaml.safe_load((REPO/'src/robot_navigation/config/nav2_params_real.yaml').read_text())
    lokal = nav['local_costmap']['local_costmap']['ros__parameters']
    huelle = ast.literal_eval(lokal['footprint'])
    polster = float(lokal['footprint_padding'])
    assert polster == pytest.approx(0.02)
    erwartet = [(x + polster*(1 if x > 0 else -1), y + polster*(1 if y > 0 else -1))
                for x, y in huelle]
    assert kontur_punkte(mk.VOLL_PUNKTE) == pytest.approx(erwartet)


def test_retreat_contour_is_the_back_off_contour_and_ends_inside_the_body():
    assert kontur_punkte(STANDARD_PUNKTE)[0][0] < 0.31           # Front liegt im Gehäuse
    assert 'rueckzug_punkte\', list(STANDARD_PUNKTE)' in QUELLE
    assert max(x for x, _ in kontur_punkte(STANDARD_PUNKTE)) == pytest.approx(0.05)
    # Heck behält das Polster der vollen Kontur (Fahrtrichtung der Rückfahrt).
    assert min(x for x, _ in kontur_punkte(STANDARD_PUNKTE)) == pytest.approx(
        min(x for x, _ in kontur_punkte(mk.VOLL_PUNKTE)))


def test_node_publishes_geometry_only():
    assert len(re.findall(r'create_publisher\(', QUELLE)) == 1
    assert 'PolygonStamped, str(self.get_parameter(\'topic\').value)' in QUELLE
    for verboten in ('create_client', 'ActionClient', 'set_parameters', 'subprocess',
                     'Twist()', 'cmd_vel\', 10)'):
        assert verboten not in QUELLE
    assert "declare_parameter('befehl_topic', 'cmd_vel_smoothed')" in QUELLE
