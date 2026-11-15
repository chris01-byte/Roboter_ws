"""Das Antriebsmodell muss die Messungen wiedergeben, aus denen es stammt."""
import pytest

import antriebsmodell as am
import antriebsprobe as ap

PLAN = {p[0]: p for p in ap.PHASEN}
# AT-1b, 15.11.2026, Probe 1: Tempo je Sekunde (m/s bzw. rad/s), Rampenzeit 2000 ms.
AT1B = {
    'A': [0.0182, 0.0694, 0.1017, 0.1023, 0.1008],
    'B': [0.0038, 0.0141, 0.0208, 0.0204, 0.035, 0.0755, 0.1016, 0.0995, 0.0992],
    'C': [0.0013, 0.004, 0.0059, 0.0079, 0.01, 0.0119],
    'F': [0.0178, 0.0686, 0.1005, 0.0558, 0.03, 0.0303, 0.0296],
    'D': [0.0461, 0.1738, 0.2604, 0.2567, 0.2529, 0.2557],
    'E': [0.0006, 0.0104, 0.0163, 0.0217, 0.0271, 0.0309],
}


def _modell(kennung, accel_ms):
    _, art, dauer, sollwert, _ = PLAN[kennung]
    if art == 'gerade':
        soll, je_rpm = (lambda t: am.motor_rpm(sollwert(max(0.0, t))[0])), am.MPS_JE_RPM
    else:
        soll = lambda t: round(sollwert(max(0.0, t))[1]/am.RADPS_JE_RPM)
        je_rpm = am.RADPS_JE_RPM
    return am.tempo_je_sekunde(am.simuliere(soll, dauer, accel_ms), je_rpm)


@pytest.mark.parametrize('kennung', sorted(AT1B))
def test_model_reproduces_every_at1b_phase(kennung):
    gemessen = AT1B[kennung]
    gerechnet = _modell(kennung, 2000)
    assert len(gerechnet) == len(gemessen)
    voll = 0.10 if PLAN[kennung][1] == 'gerade' else 0.25
    for g, m in zip(gerechnet, gemessen):
        assert g == pytest.approx(m, abs=0.05*voll)       # je Sekunde auf 5 % des Vollwerts


def test_model_reproduces_the_sh8b_reverse_distance_without_fitting():
    """SH-8b: 30,1 s lang −1,5 cm/s an der Basis, dreimal genau 0,151 m gefahren."""
    verlauf = am.simuliere(am.rampe_rpm(0.015, 0.0018), 30.1, 2000)
    assert am.weg_m(verlauf) == pytest.approx(0.151, abs=0.006)


def test_jump_is_followed_but_a_fine_ramp_is_not_at_2000_ms():
    sprung = _modell('A', 2000)
    rampe = _modell('C', 2000)
    assert sprung[-1] == pytest.approx(0.10, abs=0.002)
    assert rampe[-1] < 0.015                               # nach 6 s noch Kriechtempo


def test_prediction_for_a_short_ramp_time_is_marked_as_prediction():
    """Mit 100 ms folgt der Antrieb der Nav2-Rampe (Vorhersage, nicht gemessen)."""
    rampe = _modell('C', 100)
    assert rampe[3] == pytest.approx(0.10, abs=0.002)      # ab der vierten Sekunde voll
    drehen = _modell('E', 100)
    assert drehen[3] == pytest.approx(0.25, abs=0.005)
    verlauf = am.simuliere(am.rampe_rpm(0.015, 0.0018), 30.1, 100)
    assert am.weg_m(verlauf) > 0.40                        # Rückfahrt erreicht 0,3 m in rund 20 s
    assert 'Vorhersage' in am.__doc__
