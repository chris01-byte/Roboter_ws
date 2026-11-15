"""Ablaufauswertung: Ziele, Abbrüche, Warten, Verlauf je Minute (ohne ROS)."""
import re
from pathlib import Path

import pytest

import selbstheilung_ablauf as ab

T0 = 1794768000.0


def _log(zeilen):
    return '\n'.join(f'[{knoten}-7] [{stufe}] [{T0 + t:.3f}] [{knoten}]: {meldung}'
                     for t, stufe, knoten, meldung in zeilen)


def _fahrt():
    """Wie W-1 w2 im Kleinen: zwei Ziele, eines davon viermal, Abbrüche durch Warten."""
    nav = lambda t, x, y: (t, 'INFO', 'bt_navigator',
                           f'Begin navigating from current location (0.00, 0.00) to ({x:.2f}, {y:.2f})')
    log = [
        nav(12, 1.0, 0.5), (30, 'INFO', 'bt_navigator', 'Goal succeeded'),
        nav(31, 2.02, -1.01),
        (40, 'WARN', 'controller_server', 'RegulatedPurePursuitController detected collision ahead!'),
        (41, 'ERROR', 'controller_server', 'Controller patience exceeded'),
        (45, 'INFO', 'bt_navigator', 'Goal canceled'),
        nav(50, 2.05, -1.04),                                   # dasselbe Ziel im 0,25-m-Raster
        (70, 'WARN', 'controller_server',
         'Lookup would require extrapolation into the future.  Requested time 1794768070.12 but the latest data is at time 1794768070.01'),
        (71, 'WARN', 'controller_server',
         'Lookup would require extrapolation into the future.  Requested time 1794768071.33 but the latest data is at time 1794768071.20'),
        (75, 'ERROR', 'bt_navigator', 'Goal failed'),
        nav(80, 2.00, -1.00), (95, 'INFO', 'bt_navigator', 'Goal canceled'),
        nav(130, 2.00, -1.00), (285, 'INFO', 'bt_navigator', 'Goal canceled'),   # Zielzeit
        nav(290, 1.0, 0.5), (300, 'INFO', 'bt_navigator', 'Goal canceled'),      # erreichtes Ziel erneut
    ]
    sh = lambda t, state, goals, warten=None: dict(
        t_s=t, art='selbstheilung', state=state, outcome='in_progress', reason=None,
        waiting_for=warten, goals_reached=goals, heals=0, deferred_goals=0, track_backs=0,
        look_arounds=0)
    protokoll = dict(
        ereignisse=[
            sh(5.0, 'idle', 0), sh(20.0, 'running', 0), sh(40.0, 'running', 1),   # Versatz -10 s
            sh(54.0, 'waiting', 1, 'vl53_status_missing_stale_or_invalid'), sh(58.0, 'running', 1),
            dict(t_s=104.0, art='hwt', zustand='HOLD', vorher='HEALTHY'),
            dict(t_s=110.0, art='hwt', zustand='HEALTHY', vorher='HOLD'),
            sh(311.0, 'running', 1)],
        abdeckungskurve=[dict(t_s=21.0, fahrt_s=1.0, frei_m2=3.0), dict(t_s=50.0, fahrt_s=30.0, frei_m2=15.0),
                         dict(t_s=140.0, fahrt_s=120.0, frei_m2=17.0), dict(t_s=300.0, fahrt_s=280.0, frei_m2=17.6)],
        wackeln=dict(staerkste_sekunden=[dict(t_s=80.0, radps=0.31, v=0.0, w=0.0, lage='steht'),
                                         dict(t_s=81.0, radps=0.22, v=0.0, w=0.0, lage='steht'),
                                         dict(t_s=200.0, radps=0.05, v=0.1, w=0.0, lage='fahrt')]))
    return _log(log), protokoll


def test_goals_are_grouped_and_repeats_counted_without_coordinates():
    log, protokoll = _fahrt()
    e = ab.auswerten(log, protokoll, tuer=(2.0, -1.05))
    u = e['ziele_uebersicht']
    assert u == dict(anlaeufe=6, verschiedene_ziele=2, wiederholte_anlaeufe=4,
                     meistversuchtes_ziel=4, anteil_der_drei_haeufigsten=1.0,
                     ziele_nie_erreicht=1, zeit_in_nie_erreichten_zielen_s=209.0)
    erstes, zweites = e['ziele']
    assert (erstes['versuche'], erstes['erreicht'], erstes['gescheitert'], erstes['abgebrochen']) == (4, 0, 1, 3)
    assert erstes['abstand_tuer_m'] == pytest.approx(0.05, abs=0.03)
    assert zweites['nach_erreichen_erneut'] == 1                 # erreichtes Ziel noch einmal angefahren
    assert e['ausgaenge'] == dict(erreicht=1, abgebrochen=4, gescheitert=1)
    # Kein Zielpunkt in der Ausgabe.
    ausgabe = ab.text(e)
    assert '2.02' not in ausgabe and '-1.01' not in ausgabe and '(1.00, 0.50)' not in ausgabe
    assert not re.search(r'\(\s*-?\d+\.\d+,\s*-?\d+\.\d+\s*\)', ausgabe)


def test_cancellations_are_attributed_to_what_the_explorer_waited_for():
    log, protokoll = _fahrt()
    e = ab.auswerten(log, protokoll)
    assert e['zeitzuordnung'] == '1 erreichte Ziele'
    # 45 s Log = 55 s Protokoll: Wartephase ab 54 s; 95 s Log = 105 s: HWT HOLD ab 104 s;
    # 285 s: nach 155 s Zielzeit; 300 s: nichts in der Nähe.
    assert e['abbruchgruende'] == {'warten:vl53_status_missing_stale_or_invalid': 1,
                                   'hwt:HOLD': 1, 'zielzeit_abgelaufen': 1,
                                   'kein_warten_im_fenster': 1}
    assert e['warten'] == {'vl53_status_missing_stale_or_invalid':
                           dict(anzahl=1, summe_s=4.0, laengste_s=4.0)}
    assert e['hwt_nicht_gesund'] == {'HOLD': dict(anzahl=1, summe_s=6.0, laengste_s=6.0)}
    assert e['warten_gesamt_s'] == 4.0


def test_minutes_show_where_the_time_went():
    log, protokoll = _fahrt()
    e = ab.auswerten(log, protokoll)
    assert e['dauer_s'] == pytest.approx(291.0)
    erste = e['minuten'][0]                                    # Mission beginnt bei 10 s Logzeit
    assert (erste['begonnen'], erste['erreicht'], erste['abgebrochen']) == (3, 1, 1)
    assert erste['warten_s'] == 4.0 and erste['frei_m2'] == 15.0
    assert erste['kollision_voraus'] == 1 and erste['geduld_regler'] == 1
    assert e['minuten'][1]['tf_zukunft'] == 2 and e['minuten'][1]['gescheitert'] == 1
    assert sum(m['begonnen'] for m in e['minuten']) == 6
    n = e['nach_dem_erfassen']
    assert n['raum_zu_85_prozent_erfasst_nach_s'] == 30.0
    assert n['anlaeufe_danach'] == 4 and n['davon_erreicht'] == 0
    assert n['flaeche_danach_m2'] == pytest.approx(2.6)


def test_frequent_messages_and_excerpts_hide_numbers_and_coordinates():
    log, protokoll = _fahrt()
    e = ab.auswerten(log, protokoll)
    tf = next(m for m in e['haeufigste_meldungen'] if 'extrapolation' in m['meldung'])
    assert tf['anzahl'] == 2 and tf['stufe'] == 'WARN' and '1794768070' not in tf['meldung']
    assert '#' in tf['meldung']
    anlaesse = [a['anlass'] for a in e['auszuege']]
    assert anlaesse[0].startswith('Abbruch bei 35.0 s (warten:vl53')
    assert sum(a.startswith('Wackelspitze') for a in anlaesse) == 1      # 80 s und 81 s: eine Stelle
    assert any('Wackelspitze 0.31 rad/s bei 60.0 s' in a for a in anlaesse)
    for a in e['auszuege']:
        for zeile in a['zeilen']:
            assert not re.search(r'\(\s*-?\d+\.\d+,\s*-?\d+\.\d+\s*\)', zeile)
    assert ab.auszug([(T0, 'INFO', 'x', 'to (1.50, -2.25) now')], T0) == \
        [' +0.00 s [INFO] x: to (…) now']


def test_works_without_protocol_and_stays_read_only():
    log, _ = _fahrt()
    e = ab.auswerten(log, None)
    assert e['zeitzuordnung'] == 'keine Zuordnung'
    assert e['abbruchgruende'] == {'nicht_zuordenbar': 3, 'zielzeit_abgelaufen': 1}
    assert e['ziele_uebersicht']['anlaeufe'] == 6 and e['minuten']
    quelle = Path(ab.__file__).read_text(encoding='utf-8')
    for verboten in ('rclpy', 'subprocess', 'socket', 'create_publisher', 'os.remove'):
        assert verboten not in quelle
    assert quelle.count("open(") == 3 and "'w'" in quelle       # zwei Eingaben, ein lokales JSON
