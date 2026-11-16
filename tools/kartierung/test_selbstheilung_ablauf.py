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


def test_attempts_in_order_show_where_each_began_relative_to_the_door():
    nav = lambda t, x0, y0, x1, y1: (t, 'INFO', 'bt_navigator',
        f'Begin navigating from current location ({x0:.2f}, {y0:.2f}) to ({x1:.2f}, {y1:.2f})')
    ende = lambda t, wie: (t, 'INFO', 'bt_navigator', f'Goal {wie}')
    log = _log([
        nav(10, 0.0, 0.0, 1.0, 1.0), ende(30, 'succeeded'),          # im Raum, erreicht
        nav(31, 1.0, 1.0, 3.0, 0.0), ende(60, 'failed'),             # Ziel 1 m hinter der Tür
        nav(62, 1.7, 0.1, 3.0, 0.0), ende(70, 'failed'),             # Start 0,32 m vor der Tür
        nav(72, 1.8, 0.0, 1.6, 0.4), ende(80, 'succeeded'),          # Ziel an der Tür, davor
    ])
    e = ab.auswerten(log, None, tuer=(2.0, 0.0))
    zeilen = e['anlaeufe']
    assert [z['nr'] for z in zeilen] == [1, 2, 3, 4]
    assert [z['ziel'] for z in zeilen] == [2, 1, 1, 3]              # Ziel 1 = das zweimal versuchte
    assert [z['ausgang'] for z in zeilen] == ['erreicht', 'gescheitert', 'gescheitert', 'erreicht']
    assert [z['start_tuer_m'] for z in zeilen] == [2.0, 1.41, 0.32, 0.2]
    assert zeilen[1]['ziel_tuer_m'] == 1.0 and zeilen[1]['ziel_hinter_tuer_m'] == 1.0
    assert zeilen[0]['ziel_hinter_tuer_m'] == -1.0 and zeilen[3]['ziel_hinter_tuer_m'] == -0.4
    t = e['tuerbezug']
    assert t['startplatz_zur_tuer_m'] == 2.0 and t['kleinster_abstand_eines_starts_m'] == 0.2
    assert t['anlaeufe_mit_start_an_der_tuer'] == dict(
        anzahl=2, ausgang=dict(gescheitert=1, erreicht=1))
    assert t['anlaeufe_mit_ziel_hinter_der_tuer'] == dict(anzahl=2, ausgang=dict(gescheitert=2))
    assert t['anlaeufe_mit_ziel_an_der_tuer_davor'] == dict(anzahl=1, ausgang=dict(erreicht=1))
    assert t['anlaeufe_mit_ziel_woanders'] == dict(anzahl=1, ausgang=dict(erreicht=1))
    assert t['zeit_mit_start_an_der_tuer_s'] == 16.0
    ausgabe = ab.text(e)
    assert 'Anläufe der Reihe nach' in ausgabe and 'Ziel hinter der Tür' in ausgabe
    assert not re.search(r'\(\s*-?\d+\.\d+,\s*-?\d+\.\d+\s*\)', ausgabe)
    # Ohne Tür: dieselbe Liste ohne Türspalten, kein Türbezug.
    ohne = ab.auswerten(log, None)
    assert 'start_tuer_m' not in ohne['anlaeufe'][0] and ohne['tuerbezug'] is None
    assert 'Start→Tür' not in ab.text(ohne)


def test_canceled_attempts_carry_their_reason_in_the_sequence():
    log, protokoll = _fahrt()
    e = ab.auswerten(log, protokoll, tuer=(2.0, -1.05))
    gruende = [z['grund'] for z in e['anlaeufe']]
    assert gruende == [None, 'warten:vl53_status_missing_stale_or_invalid', None, 'hwt:HOLD',
                       'zielzeit_abgelaufen', 'kein_warten_im_fenster']
    assert 'hwt:HOLD' in ab.text(e)


def test_wait_phases_and_backups_are_listed_with_the_reason_for_a_canceled_backup():
    log, protokoll = _fahrt()
    log += '\n' + _log([
        (100, 'INFO', 'behavior_server', 'Running backup'),
        (103, 'WARN', 'behavior_server', 'Canceling backup'),        # 113 s Protokoll: HOLD seit 104 s? nein
        (200, 'INFO', 'behavior_server', 'Running backup'),
        (206, 'INFO', 'behavior_server', 'backup completed successfully'),
        (92, 'INFO', 'behavior_server', 'Running backup'),
        (96, 'WARN', 'behavior_server', 'Canceling backup'),         # 102–106 s Protokoll: HOLD ab 104 s
    ])
    e = ab.auswerten(log, protokoll)
    assert e['phasen'] == [dict(beginn_s=34.0, dauer_s=4.0, was='warten:vl53_status_missing_stale_or_invalid'),
                           dict(beginn_s=84.0, dauer_s=6.0, was='hwt:HOLD')]
    assert e['rueckfahrten'] == [
        dict(beginn_s=82.0, dauer_s=4.0, ausgang='abgebrochen', grund='hwt:HOLD'),
        dict(beginn_s=90.0, dauer_s=3.0, ausgang='abgebrochen', grund='kein_warten_im_zeitraum'),
        dict(beginn_s=190.0, dauer_s=6.0, ausgang='vollständig', grund=None)]
    ausgabe = ab.text(e)
    assert 'Rückfahrten' in ausgabe and 'Warte- und HWT-Phasen der Reihe nach (2;' in ausgabe
    ohne = ab.auswerten(log, None)                                  # ohne Protokoll: keine Zuordnung
    assert ohne['phasen'] == [] and ohne['rueckfahrten'][0]['grund'] == 'nicht_zuordenbar'


def test_controller_stops_are_shown_with_the_near_picture_and_narrow_places_are_listed():
    log, protokoll = _fahrt()                       # Reglerhalt im Log bei 41 s = 51 s Protokoll
    bild = lambda t, breite, innen=0, seite='links', links=0.1, rechts=0.1: dict(
        t_s=t, fahrt_s=t - 20.0, befehl=None, in_kontur=innen, in_kontur_ohne_polster=0,
        naechste_m=0.0 if innen else 0.05, seite=seite, links_m=links, rechts_m=rechts,
        breite_m=breite, zellen=[[10, 30]])
    protokoll['nahbilder'] = [bild(48.0, 1.6), bild(49.0, 0.74), bild(50.0, 0.72, 2, 'vorn links'),
                              bild(51.2, 0.70, 3, 'vorn links', 0.02, 0.18), bild(52.0, 0.71),
                              bild(60.0, None), bild(200.0, 0.8)]
    protokoll['nahbild'] = dict(bilder=7, mit_zellen_in_gepolsterter_kontur=2)
    e = ab.auswerten(log, protokoll)
    (halt,) = e['reglerhalte']
    assert halt == dict(halt_s=31.0, nahbild=True, in_kontur=3, in_kontur_ohne_polster=0,
                        naechste_m=0.0, seite='vorn links', links_m=0.02, rechts_m=0.18,
                        breite_m=0.70)
    assert e['engstellen'] == [
        dict(beginn_s=29.0, bilder=4, engste_breite_m=0.70, meiste_zellen_in_kontur=3, dauer_s=3.0),
        dict(beginn_s=180.0, bilder=1, engste_breite_m=0.8, meiste_zellen_in_kontur=0, dauer_s=0.0)]
    ausgabe = ab.text(e)
    assert 'Reglerhalte' in ausgabe and 'vorn links' in ausgabe and 'Engstellen' in ausgabe
    assert '[10, 30]' not in ausgabe                               # die Zellen bleiben im Protokoll
    # Ohne Nahbilder (ältere Protokolle): der Halt wird genannt, ohne Bild.
    alt = ab.auswerten(*_fahrt())
    assert alt['reglerhalte'] == [dict(halt_s=31.0, nahbild=False)] and alt['engstellen'] == []
    assert 'keine Daten' in ab.text(alt) and 'kein Nahbild in der Nähe' in ab.text(alt)


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
