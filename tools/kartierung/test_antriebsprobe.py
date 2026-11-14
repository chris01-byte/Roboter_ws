"""Antriebsprobe AT-1: Sollwertfolgen, Grenzen und Auswertung (ohne ROS)."""
import math
import re
from pathlib import Path

import pytest

import antriebsprobe as ap

QUELLE = Path(__file__).with_name('antriebsprobe.py').read_text(encoding='utf-8')


def test_nothing_moves_without_the_exact_release_word(capsys):
    assert ap.main(['--json', '/nonexistent/x.json']) == 2
    assert ap.main(['--freigabe', 'at-1', '--json', '/nonexistent/x.json']) == 2
    assert 'Keine Bewegung' in capsys.readouterr().err
    assert ap.main(['--freigabe', 'AT-1', '--phasen', 'A,Z', '--json', '/nonexistent/x.json']) == 2


def test_tool_publishes_exactly_one_topic_and_nothing_else_that_acts():
    assert len(re.findall(r'create_publisher\(', QUELLE)) == 1
    assert "create_publisher(Twist, args.topic, 1)" in QUELLE
    for verboten in ('ActionClient', 'create_client', 'set_parameters', 'subprocess',
                     'lifecycle', 'estop_request'):
        assert verboten not in QUELLE
    assert ap.TOPIC == '/cmd_vel_smoothed'          # durch den Kollisionsmonitor


def test_setpoints_stay_within_the_released_limits():
    plan = {p[0]: p for p in ap.PHASEN}
    assert list(plan) == ['A', 'B', 'C', 'F', 'D', 'E']
    weg_max = 0.0
    for kennung, art, dauer, sollwert, _ in ap.PHASEN:
        weg, t = 0.0, 0.0
        while t < dauer:
            v, w = sollwert(t)
            assert 0.0 <= v <= 0.10 + 1e-9 and 0.0 <= w <= 0.25 + 1e-9
            assert (v == 0.0) if art == 'drehen' else (w == 0.0)
            weg += v/ap.RATE_HZ
            t += 1.0/ap.RATE_HZ
        weg_max = max(weg_max, weg)
        assert dauer <= 9.0
    # Auch bei voll umgesetzten Sollwerten bleibt jede Phase unter der Abbruchgrenze.
    assert weg_max < ap.GRENZE_VOR_M - 0.15
    assert ap.V_ZURUECK == 0.05


def test_ramp_reproduces_the_smoother_steps_and_the_stairs_switch_on_time():
    plan = {p[0]: p for p in ap.PHASEN}
    c = plan['C'][3]
    assert [round(c(k/20)[0], 3) for k in range(4)] == [0.006, 0.012, 0.018, 0.024]
    assert c(5.0)[0] == pytest.approx(0.10)
    e = plan['E'][3]
    assert [round(e(k/20)[1], 3) for k in range(3)] == [0.015, 0.03, 0.045]
    assert e(5.0)[1] == pytest.approx(0.25)
    b, f = plan['B'][3], plan['F'][3]
    assert b(3.99)[0] == 0.02 and b(4.0)[0] == 0.10
    assert f(2.99)[0] == 0.10 and f(3.0)[0] == 0.03


def test_pose_relative_to_the_start_and_abort_limits():
    start = (1.0, 2.0, math.pi/2)                       # blickt nach +y
    laengs, quer, gier = ap.lage(start, (0.8, 2.5, math.pi/2 + 0.1))
    assert laengs == pytest.approx(0.5) and quer == pytest.approx(0.2)
    assert gier == pytest.approx(0.1)
    assert ap.grenzverletzung('gerade', 0.5, 0.1) is None
    assert 'vor' in ap.grenzverletzung('gerade', 0.91, 0.0)
    assert 'hinter' in ap.grenzverletzung('drehen', -0.21, 0.0)
    assert 'Richtung' in ap.grenzverletzung('gerade', 0.3, -0.36)
    assert ap.grenzverletzung('drehen', 0.0, 1.5) is None


def _reihe(dauer, tempo_fn):
    reihe, weg, t = [], 0.0, 0.0
    while t <= dauer + 1e-9:
        reihe.append((round(t, 3), weg, 0.0))
        weg += tempo_fn(t)/20
        t += 0.05
    return reihe


def test_evaluation_confirms_the_hypothesis_when_only_the_first_setpoint_counts():
    """Antrieb bleibt beim ersten Sollwert nach dem Anfahren (wie in SH-8b vermutet)."""
    phasen = {
        'A': ap.auswertung('A', 'gerade', _reihe(5, lambda t: 0.10), [(3.5, 0.10, 0.0)]),
        'B': ap.auswertung('B', 'gerade', _reihe(9, lambda t: 0.02), [(8.0, 0.10, 0.0)]),
        'C': ap.auswertung('C', 'gerade', _reihe(6, lambda t: 0.012), [(5.0, 0.10, 0.0)]),
        'F': ap.auswertung('F', 'gerade', _reihe(7, lambda t: 0.10), [(6.0, 0.03, 0.0)]),
    }
    b = phasen['B']['abschnitte']
    assert b['stufe_1']['ist_zu_soll'] == pytest.approx(1.0, abs=0.02)
    assert b['stufe_2']['ist_zu_soll'] == pytest.approx(0.2, abs=0.02)
    assert b['stufe_2']['an_der_basis_mps'] == 0.10
    urteil = ap.urteil(phasen)
    assert urteil['hypothese_sollwert_nur_beim_anfahren'] == 'bestaetigt'
    assert urteil['rampe_ist_zu_soll'] == pytest.approx(0.12, abs=0.01)
    assert urteil['treppe_abwaerts_stufe_2_ist_zu_soll'] > 3.0      # fährt weiter mit 0,10


def test_evaluation_refutes_or_stays_open_otherwise():
    gut = {
        'A': ap.auswertung('A', 'gerade', _reihe(5, lambda t: 0.10), []),
        'B': ap.auswertung('B', 'gerade', _reihe(9, lambda t: 0.02 if t < 4 else 0.10), []),
        'C': ap.auswertung('C', 'gerade', _reihe(6, lambda t: min(0.10, 0.12*t)), []),
    }
    assert ap.urteil(gut)['hypothese_sollwert_nur_beim_anfahren'] == 'widerlegt'
    halb = dict(gut, C=ap.auswertung('C', 'gerade', _reihe(6, lambda t: 0.05), []))
    assert ap.urteil(halb)['hypothese_sollwert_nur_beim_anfahren'] == 'unklar'
    assert ap.urteil({'A': gut['A']})['hypothese_sollwert_nur_beim_anfahren'] == 'nicht_auswertbar'
    # Zu kurze Messreihe: kein Tempo, kein Urteil.
    assert ap.auswertung('A', 'gerade', [(0.0, 0.0, 0.0)], [])['abschnitte']['ende'][
        'ist_zu_soll'] is None


def test_rotation_phase_is_measured_in_yaw():
    reihe = [(round(k*0.05, 3), 0.0, 0.25*k*0.05) for k in range(121)]
    d = ap.auswertung('D', 'drehen', reihe, [(5.0, 0.0, 0.25)])
    assert d['abschnitte']['ende']['ist_radps'] == pytest.approx(0.25, abs=1e-3)
    assert d['abschnitte']['ende']['an_der_basis_radps'] == 0.25
    assert d['gier_rad'] == pytest.approx(1.5)
