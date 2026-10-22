import re
from pathlib import Path

import pytest

from selbstheilung_lauf_protokoll import LaufProtokoll


def _sh(state, goals=0, heals=0, outcome='in_progress', reason=None, waiting=None, **extra):
    return {'self_healing': dict(state=state, outcome=outcome, reason=reason,
                                 waiting_for=waiting, goals_reached=goals, heals=heals,
                                 deferred_goals=0, track_backs=0, look_arounds=0, **extra),
            'hwt_recovery_state': 'HEALTHY', 'map_ready_to_save': state in ('partial', 'blocked')}


def test_run_with_help_required_end_meets_the_automatic_stage1_criteria():
    p = LaufProtokoll(0.0)
    p.explore(_sh('idle'), 1.0)
    p.estop_wert(False, 1.0)
    assert not p.faehrt()
    p.explore(_sh('running'), 2.0)
    for t in (2.1, 2.3, 2.5):
        p.vl53(t)
    p.cmd_vel(0.06, 0.0)
    p.odom(0.0, 0.0)
    p.odom(0.3, 0.4)                       # 0,5 m Sprung -> nicht addiert
    p.odom(0.3, 0.5)
    p.explore(_sh('running', goals=1), 30.0)
    p.vl53(31.5)                           # 29 s Lücke während der Fahrt
    p.explore(_sh('waiting', goals=1, waiting='vl53_status_missing_stale_or_invalid'), 32.0)
    p.explore(_sh('running', goals=2, heals=1), 40.0)
    p.tempo(0.06, 41.0)
    p.explore(_sh('blocked', goals=2, heals=8, outcome='blocked_help_required',
                  reason='help_required:no_progress'), 90.0)
    s = p.zusammenfassung()
    assert s['dauer_s'] == pytest.approx(88.0)
    assert s['kriterien_automatisch'] == {
        'fahrt_begonnen': True, 'fahrt_beendet': True, 'mehrere_ziele_erreicht': True,
        'sauberes_ende': True, 'kein_not_aus_waehrend_fahrt': True}
    assert s['automatisch_erfuellt'] is True
    assert s['strecke_odom_m'] == pytest.approx(0.1)
    assert s['vl53_luecken']['anzahl'] == 1
    assert s['fahrbefehle']['max_v'] == pytest.approx(0.06)
    arten = [e['art'] for e in s['ereignisse']]
    assert arten.count('selbstheilung') == 6 and 'tempolimit' in arten and 'vl53_luecke' in arten


def test_estop_error_end_and_single_goal_fail_the_automatic_criteria():
    p = LaufProtokoll(0.0)
    p.explore(_sh('running'), 1.0)
    p.estop_wert(True, 5.0)
    p.explore(_sh('failed', goals=1, outcome='error', reason='estop_active'), 6.0)
    k = p.kriterien()
    assert k['kein_not_aus_waehrend_fahrt'] is False
    assert k['sauberes_ende'] is False and k['mehrere_ziele_erreicht'] is False
    assert p.zusammenfassung()['automatisch_erfuellt'] is False


def test_previous_terminal_state_does_not_count_as_a_new_run():
    p = LaufProtokoll(0.0)
    p.explore(_sh('blocked', goals=3, outcome='blocked_help_required'), 1.0)
    assert p.gestartet_um is None and p.beendet_um is None
    p.vl53(1.0)
    p.vl53(5.0)                            # vor dem Start: keine Lücke zählen
    assert p.vl53_luecken == 0
    assert p.kriterien()['fahrt_begonnen'] is False


def test_hwt_recovery_transitions_are_recorded():
    p = LaufProtokoll(0.0)
    status = _sh('running')
    p.explore(status, 1.0)
    p.explore(dict(status, hwt_recovery_state='HOLD'), 2.0)
    p.explore(dict(status, hwt_recovery_state='HEALTHY'), 3.0)
    hwt = [e for e in p.ereignisse if e['art'] == 'hwt']
    assert [e['zustand'] for e in hwt] == ['HEALTHY', 'HOLD', 'HEALTHY']


def test_protocol_tool_stays_read_only():
    source = Path(__file__).with_name('selbstheilung_lauf_protokoll.py').read_text(encoding='utf-8')
    for forbidden in ('create_publisher', 'create_client', 'ActionClient', 'send_goal'):
        assert forbidden not in source
    assert len(re.findall(r'create_subscription\(', source)) == 7
