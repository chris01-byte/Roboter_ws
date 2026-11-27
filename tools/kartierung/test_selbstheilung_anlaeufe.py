import re
from pathlib import Path

import pytest

from selbstheilung_anlaeufe import auswerten, zeilen, zusammenfassung

ROS = """\
[bt_navigator-9] [INFO] [1794610100.000000000] [bt_navigator]: Begin navigating from current location (0.00, 0.00) to (0.30, -0.40)
[collision_monitor-3] [INFO] [1794610102.000000000] [collision_monitor]: Robot to slowdown for 30.000000 percents due to SlowZone polygon
[collision_monitor-3] [INFO] [1794610142.000000000] [collision_monitor]: Robot to continue normal operation
[bt_navigator-9] [INFO] [1794610170.000000000] [bt_navigator]: Goal succeeded
[bt_navigator-9] [INFO] [1794610171.000000000] [bt_navigator]: Begin navigating from current location (0.30, -0.40) to (1.30, -0.40)
[collision_monitor-3] [INFO] [1794610180.000000000] [collision_monitor]: Robot to approach for 2.000000 seconds away from collision
[bt_navigator-9] [ERROR] [1794610210.000000000] [bt_navigator]: Goal failed
[bt_navigator-9] [INFO] [1794610212.000000000] [bt_navigator]: Begin navigating from current location (0.30, -0.40) to (0.30, 0.80)
[bt_navigator-9] [INFO] [1794610220.000000000] [bt_navigator]: Goal canceled
"""


def test_attempts_distances_durations_and_monitor_shares_from_a_ros_log():
    anlaeufe, zeiten = auswerten(list(zeilen(ROS)))
    assert [(a['ausgang'], a['entfernung_m'], a['dauer_s']) for a in anlaeufe] == [
        ('erreicht', 0.5, 70.0), ('gescheitert', 1.0, 39.0), ('abgebrochen', 1.2, 8.0)]
    assert zeiten == dict(dauer_s=120.0, fahrbefehle=None, langsam_s=40.0, approach_s=40.0)
    z = zusammenfassung(anlaeufe, zeiten)
    assert z['anlaeufe'] == 3 and z['erreicht'] == 1
    assert z['ziel_entfernung_median_m'] == 1.0 and z['ziele_unter_0.5_m'] == 0
    assert z['zeit_in_erreichten_s'] == 70.0 and z['zeit_in_nicht_erreichten_s'] == 47.0
    assert z['anteil_langsam_zone'] == pytest.approx(0.33)
    assert z['anteil_approach'] == pytest.approx(0.33)
    assert z['fahrbefehle'] is None and 'vorwaerts_s' not in anlaeufe[0]


def test_clock_excerpts_like_ablauf_txt_are_read_too_also_across_midnight():
    text = """\
23:59:50 bt_navigator: Begin navigating from current location (0.00, 0.00) to (0.09, -0.35)
00:00:31 bt_navigator: Goal failed
"""
    anlaeufe, zeiten = auswerten(list(zeilen(text)))
    assert anlaeufe[0]['dauer_s'] == 41.0 and anlaeufe[0]['entfernung_m'] == 0.36
    assert zeiten['dauer_s'] == 41.0


def test_empty_log_gives_an_empty_summary():
    anlaeufe, zeiten = auswerten([])
    z = zusammenfassung(anlaeufe, zeiten)
    assert z['anlaeufe'] == 0 and z['ziel_entfernung_median_m'] is None
    assert z['anteil_langsam_zone'] is None


def test_tool_reads_files_only():
    quelle = Path(__file__).with_name('selbstheilung_anlaeufe.py').read_text(encoding='utf-8')
    assert not re.search(r'\brclpy\b|subprocess|create_publisher|socket', quelle)


def _basis(t, modus, v, w):
    return (f'[base_hardware_node-5] [INFO] [{t:.9f}] [base_hardware]: {modus}: v={v:+.3f} m/s '
            f'w={w:+.3f} rad/s | Rad L=+0.0 R=+0.0 rpm | Motor L=+0 R=+0 rpm')


def test_base_commands_show_what_the_robot_was_asked_to_do_in_each_attempt():
    """Sollte die Basis langsam fahren, drehen, stehen, oder kam kein Befehl an?"""
    t0 = 1794610100.0
    log = [f'[bt_navigator-9] [INFO] [{t0:.9f}] [bt_navigator]: Begin navigating from current '
           'location (0.00, 0.00) to (0.50, 0.00)']
    befehle = ([('CMD', 0.0, 0.25)]*10 + [('CMD', 0.03, 0.0)]*20 + [('TIMEOUT-STOP', 0.03, 0.0)]*5
               + [('CMD', 0.0, 0.0)]*5 + [('CMD', -0.015, 0.0)]*10)
    for i, (modus, v, w) in enumerate(befehle):
        log.append(_basis(t0 + 0.5 + i, modus, v, w))
    log.append(f'[bt_navigator-9] [INFO] [{t0+50.4:.9f}] [bt_navigator]: Goal succeeded')
    # Nach dem Anlauf: Befehle zählen nicht mehr mit.
    log += [_basis(t0 + 51 + i, 'TIMEOUT-STOP', 0.0, 0.0) for i in range(30)]
    anlaeufe, zeiten = auswerten(list(zeilen('\n'.join(log))))
    a = anlaeufe[0]
    assert (a['drehen_s'], a['vorwaerts_s'], a['ohne_befehl_s'], a['stehen_s'],
            a['rueckwaerts_s']) == (10.0, 20.0, 5.0, 5.0, 9.9)   # endet mit dem Anlauf
    assert a['v_mittel_mps'] == 0.03 and '_t' not in a and '_v' not in a
    block = zusammenfassung(anlaeufe, zeiten)['fahrbefehle']
    assert block['in_anlaeufen_s'] == dict(vorwaerts_s=20.0, drehen_s=10.0, rueckwaerts_s=9.9,
                                           stehen_s=5.0, ohne_befehl_s=5.0)
    assert block['anteile'] == dict(vorwaerts=0.4, drehen=0.2, rueckwaerts=0.2, stehen=0.1,
                                    ohne_befehl=0.1)
    assert block['v_vorwaerts_median_mps'] == 0.03 and block['w_drehen_median_radps'] == 0.25
    assert block['befohlener_weg_vorwaerts_m'] == pytest.approx(0.6)
    assert block['erreicht_vorwaerts_s'] == 20.0 and block['erreicht_drehen_s'] == 10.0
    assert block['erreicht_stehen_oder_ohne_befehl_s'] == 10.0


def test_gaps_between_base_lines_count_at_most_two_seconds():
    t0 = 1794610100.0
    log = [f'[x] [INFO] [{t0:.9f}] [bt_navigator]: Begin navigating from current location '
           '(0.00, 0.00) to (1.00, 0.00)',
           _basis(t0 + 1, 'CMD', 0.05, 0.0), _basis(t0 + 31, 'CMD', 0.05, 0.0),
           f'[x] [INFO] [{t0+40:.9f}] [bt_navigator]: Goal canceled']
    anlaeufe, _ = auswerten(list(zeilen('\n'.join(log))))
    assert anlaeufe[0]['vorwaerts_s'] == 3.0       # 2 s (Lücke gekappt) + 1 s (letzter Eintrag)
