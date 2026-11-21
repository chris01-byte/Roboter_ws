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


def test_direct_base_topic_needs_its_own_release_word(capsys):
    """Direkt an die Basis heißt ohne Kollisionsmonitor: eigenes Freigabewort."""
    assert ap.FREIGABEN == {'/cmd_vel_smoothed': ('AT-1',), '/cmd_vel': ('AT-1b', 'AT-2')}
    assert ap.main(['--topic', '/cmd_vel', '--freigabe', 'AT-1',
                    '--json', '/nonexistent/x.json']) == 2
    assert 'AT-1b' in capsys.readouterr().err
    assert ap.main(['--topic', '/cmd_vel_smoothed', '--freigabe', 'AT-1b',
                    '--json', '/nonexistent/x.json']) == 2
    # Mit dem richtigen Wort scheitert es erst an der unbekannten Phase, nicht am Wort.
    assert ap.main(['--topic', '/cmd_vel', '--freigabe', 'AT-1b', '--phasen', 'Z',
                    '--json', '/nonexistent/x.json']) == 2
    assert 'Unbekannte Phase' in capsys.readouterr().err
    with pytest.raises(SystemExit):                     # kein drittes Topic
        ap.main(['--topic', '/cmd_vel_nav', '--freigabe', 'AT-1', '--json', '/x.json'])


def test_tool_publishes_exactly_one_topic_and_nothing_else_that_acts():
    assert len(re.findall(r'create_publisher\(', QUELLE)) == 1
    assert "create_publisher(Twist, args.topic, 1)" in QUELLE
    for verboten in ('ActionClient', 'create_client', 'set_parameters', 'subprocess',
                     'lifecycle', 'estop_request'):
        assert verboten not in QUELLE
    assert ap.TOPIC == '/cmd_vel_smoothed'          # durch den Kollisionsmonitor


def test_setpoints_stay_within_the_released_limits():
    plan = {p[0]: p for p in ap.PHASEN}
    assert list(plan) == ['A', 'B', 'C', 'F', 'D', 'E', 'G', 'R', 'S']
    weg_max, weg_min = 0.0, 0.0
    for kennung, art, dauer, sollwert, _ in ap.PHASEN:
        weg, t = 0.0, 0.0
        while t < dauer:
            v, w = sollwert(t)
            assert -0.015 - 1e-9 <= v <= 0.10 + 1e-9 and 0.0 <= w <= 0.25 + 1e-9
            assert (v == 0.0) if art == 'drehen' else (w == 0.0)
            assert v >= 0.0 or kennung == 'R'            # rückwärts nur die langsame Rückfahrt
            weg += v/ap.RATE_HZ
            t += 1.0/ap.RATE_HZ
        weg_max, weg_min = max(weg_max, weg), min(weg_min, weg)
        assert dauer <= 9.0
    # Auch bei voll umgesetzten Sollwerten bleibt jede Phase klar in den Abbruchgrenzen.
    assert weg_max < ap.GRENZE_VOR_M - 0.15
    assert weg_min > -ap.GRENZE_ZURUECK_M + 0.05
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
    an_a, an_b, an_c = [(3.5, 0.10, 0.0)], [(3.0, 0.02, 0.0), (8.0, 0.10, 0.0)], [(5.0, 0.10, 0.0)]
    gut = {
        'A': ap.auswertung('A', 'gerade', _reihe(5, lambda t: 0.10), an_a),
        'B': ap.auswertung('B', 'gerade', _reihe(9, lambda t: 0.02 if t < 4 else 0.10), an_b),
        'C': ap.auswertung('C', 'gerade', _reihe(6, lambda t: min(0.10, 0.12*t)), an_c),
    }
    assert not any(a['gestoert'] for p in gut.values() for a in p['abschnitte'].values())
    assert ap.urteil(gut)['hypothese_sollwert_nur_beim_anfahren'] == 'widerlegt'
    halb = dict(gut, C=ap.auswertung('C', 'gerade', _reihe(6, lambda t: 0.05), an_c))
    assert ap.urteil(halb)['hypothese_sollwert_nur_beim_anfahren'] == 'unklar'
    assert ap.urteil({'A': gut['A']})['hypothese_sollwert_nur_beim_anfahren'] == 'nicht_auswertbar'
    # Zu kurze Messreihe: kein Tempo, kein Urteil.
    assert ap.auswertung('A', 'gerade', [(0.0, 0.0, 0.0)], [])['abschnitte']['ende'][
        'ist_zu_soll'] is None


def test_at1_disturbance_is_named_instead_of_an_open_verdict():
    """AT-1, 15.11.2026: Glätter-Nullen im Wechsel mit dem Sollwert, an der Basis
    kam im Mittel die Hälfte an, gefahren wurden 8–15 %. Das ist keine Aussage
    über den Antrieb und darf nicht als „unklar“ durchgehen."""
    wechsel = [(3.0 + k*0.025, 0.10 if k % 2 else 0.0, 0.0) for k in range(80)]
    wechsel_b = [(7.0 + k*0.025, 0.10 if k % 2 else 0.0, 0.0) for k in range(80)]
    wechsel_c = [(4.0 + k*0.025, 0.10 if k % 2 else 0.0, 0.0) for k in range(80)]
    at1 = {
        'A': ap.auswertung('A', 'gerade', _reihe(5, lambda t: 0.013), wechsel),
        'B': ap.auswertung('B', 'gerade', _reihe(9, lambda t: 0.008), wechsel_b),
        'C': ap.auswertung('C', 'gerade', _reihe(6, lambda t: 0.008), wechsel_c),
    }
    assert at1['A']['abschnitte']['ende']['an_der_basis_mps'] == pytest.approx(0.05, abs=0.002)
    assert at1['A']['abschnitte']['ende']['gestoert'] is True
    urteil = ap.urteil(at1)
    assert urteil['hypothese_sollwert_nur_beim_anfahren'] == 'gestoert'
    assert urteil['gestoerte_abschnitte'] == ['A/ende', 'B/stufe_2', 'C/ende']
    # Kommt an der Basis gar nichts an (Kollisionsmonitor hält), gilt dasselbe.
    assert ap.basis_gestoert(0.10, None) is True
    # Langsam-Zone (×0,3) zählt ebenfalls als Störung, 10 % Abweichung nicht.
    assert ap.basis_gestoert(0.10, 0.03) is True
    assert ap.basis_gestoert(0.10, 0.091) is False
    assert ap.basis_gestoert(0.25, 0.25) is False


def test_foreign_sender_is_detected_before_and_during_the_run():
    assert ap.fremde_nachrichten(100, 100) == 0
    assert ap.fremde_nachrichten(97, 100) == 0          # eigene dürfen fehlen
    assert ap.fremde_nachrichten(140, 100) == 40
    assert ap.FREMD_MAX <= 5 and ap.LAUSCHEN_S >= 2.0
    # Erst lauschen, dann der erste eigene Befehl.
    lauschen = QUELLE.index("ergebnis['vor_dem_start_fremde_nachrichten']")
    assert lauschen < QUELLE.index('halt(PAUSE_S)\n            for kennung in gewaehlt')
    assert "zustand['gesendet'] += 1" in QUELLE


def test_rotation_phase_is_measured_in_yaw():
    reihe = [(round(k*0.05, 3), 0.0, 0.25*k*0.05) for k in range(121)]
    d = ap.auswertung('D', 'drehen', reihe, [(5.0, 0.0, 0.25)])
    assert d['abschnitte']['ende']['ist_radps'] == pytest.approx(0.25, abs=1e-3)
    assert d['abschnitte']['ende']['an_der_basis_radps'] == 0.25
    assert d['gier_rad'] == pytest.approx(1.5)


def test_speed_per_second_shows_whether_the_drive_follows_or_sticks():
    folgt = ap.auswertung('B', 'gerade', _reihe(9, lambda t: 0.02 if t < 4 else 0.10), [])
    assert folgt['tempo_je_s'][:3] == pytest.approx([0.02]*3, abs=1e-3)
    assert folgt['tempo_je_s'][5:] == pytest.approx([0.10]*4, abs=1e-3)
    klebt = ap.auswertung('C', 'gerade', _reihe(6, lambda t: 0.006), [])
    assert klebt['tempo_je_s'] == pytest.approx([0.006]*6, abs=1e-4)
    assert ap.tempo_je_sekunde([], 'weg') == []


def test_at2_programme_contains_only_commands_as_nav2_sends_them(capsys):
    """AT-2: keine Sprünge aus dem Stand; jede Änderung begrenzt wie im Glätter,
    mit einer einzigen gewollten Stufe (S, wie beim Verlassen der Langsam-Zone)."""
    assert ap.PROGRAMME['AT-2'] == 'C,G,R,E,S' and ap.SANFT == ('AT-2',)
    assert ap.main(['--topic', '/cmd_vel', '--freigabe', 'AT-2', '--phasen', 'A',
                    '--json', '/nonexistent/x.json']) == 2
    assert 'C, G, R, E, S' in capsys.readouterr().err
    assert ap.main(['--topic', '/cmd_vel_smoothed', '--freigabe', 'AT-2',
                    '--json', '/nonexistent/x.json']) == 2
    assert ap.main(['--topic', '/cmd_vel', '--freigabe', 'AT-1b', '--phasen', 'G',
                    '--json', '/nonexistent/x.json']) == 2       # G gehört nicht zu AT-1b
    plan = {p[0]: p for p in ap.PHASEN}
    stufen = 0
    for kennung in ap.PROGRAMME['AT-2'].split(','):
        _, art, dauer, sollwert, _ = plan[kennung]
        index = 0 if art == 'gerade' else 1
        auf, ab = (ap.A_LIN, ap.B_LIN) if art == 'gerade' else (ap.A_ROT, ap.B_ROT)
        vorher = 0.0
        for k in range(int(dauer*ap.RATE_HZ)):
            wert = sollwert(k/ap.RATE_HZ)[index]
            schritt = abs(wert) - abs(vorher)
            if schritt > auf/ap.RATE_HZ + 1e-9:
                stufen += 1
                assert kennung == 'S' and wert == ap.V_SPRUNG and vorher == pytest.approx(0.03)
            assert schritt >= -ab/ap.RATE_HZ - 1e-9
            vorher = wert
    assert stufen == 1
    g = plan['G'][3]
    assert g(2.9)[0] == pytest.approx(0.10) and g(5.0)[0] == pytest.approx(0.04)
    assert g(8.0)[0] == pytest.approx(0.08)
    r = plan['R'][3]
    assert [round(r(k/20)[0], 4) for k in range(3)] == [-0.0018, -0.0036, -0.0054]
    assert r(7.0)[0] == pytest.approx(-0.015)
    # Rückwege fahren im sanften Programm als Rampe an.
    assert 'rampe(V_ZURUECK, A_LIN, t) if sanft else V_ZURUECK' in QUELLE
    assert 'rampe(W_SPRUNG, A_ROT, t) if sanft else W_SPRUNG' in QUELLE


def _at2(c, g, r, e, an=None):
    """Phasen C, G, R, E mit gegebenem Ist/Soll je Abschnitt."""
    def phase(kennung, art, anteile):
        abschnitte = ap.ABSCHNITTE[kennung]
        def tempo_fn(t):
            for (name, von, bis, soll), anteil in zip(abschnitte, anteile):
                if t <= bis:
                    return soll*anteil
            return 0.0
        dauer = abschnitte[-1][2]
        if art == 'gerade':
            reihe = _reihe(dauer, tempo_fn)
        else:
            reihe, gier, t = [], 0.0, 0.0
            while t <= dauer + 1e-9:
                reihe.append((round(t, 3), 0.0, gier))
                gier += tempo_fn(t)/20
                t += 0.05
        befehle = [((von + bis)/2, (an or soll) if art == 'gerade' else 0.0,
                    0.0 if art == 'gerade' else (an or soll))
                   for _, von, bis, soll in abschnitte]
        return ap.auswertung(kennung, art, reihe, befehle)
    return {'C': phase('C', 'gerade', c), 'G': phase('G', 'gerade', g),
            'R': phase('R', 'gerade', r), 'E': phase('E', 'drehen', e)}


def test_at2_verdict_follows_the_rules_fixed_in_advance():
    ja = ap.urteil_rampen(_at2([1.0], [0.98, 1.05, 1.0], [0.95], [1.0]))
    assert ja['antrieb_folgt_rampen'] == 'ja' and ja['ausserhalb_0_8_bis_1_2'] == []
    assert ja['ist_zu_soll']['R/ende'] == pytest.approx(0.95, abs=0.02)   # rückwärts positiv
    # Wie AT-1b mit 2000 ms: beide Rampen unter 0,4.
    nein = ap.urteil_rampen(_at2([0.11], [0.1, 0.4, 0.2], [0.1], [0.11]))
    assert nein['antrieb_folgt_rampen'] == 'nein'
    # Folgt beim Schnellerwerden, bremst aber auf der Rampe nicht mit (Ist über Soll).
    teil = ap.urteil_rampen(_at2([1.0], [1.0, 1.8, 1.0], [1.0], [1.0]))
    assert teil['antrieb_folgt_rampen'] == 'teilweise'
    assert teil['ausserhalb_0_8_bis_1_2'] == ['G/unten']
    # Fehlt eine Phase oder kam an der Basis nicht der Sollwert an: kein Urteil.
    assert ap.urteil_rampen({'C': _at2([1], [1, 1, 1], [1], [1])['C']})[
        'antrieb_folgt_rampen'] == 'nicht_auswertbar'
    gestoert = ap.urteil_rampen(_at2([1.0], [1.0, 1.0, 1.0], [1.0], [1.0], an=0.001))
    assert gestoert['antrieb_folgt_rampen'] == 'gestoert'
    assert (ap.FOLGT_VON, ap.FOLGT_BIS) == (0.8, 1.2)
