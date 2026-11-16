import math
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
    # 8 seit 09.11.2026: /map für die Abdeckungskurve (nur lesend).
    # 9 seit 15.11.2026: HWT601-Drehraten für die Messgröße Wackeln (nur lesend).
    # 10 seit 16.11.2026: lokale Kostenkarte für das Nahbild (nur lesend).
    assert len(re.findall(r'create_subscription\(', source)) == 10


def test_coverage_curve_samples_every_30_s_only_while_driving():
    """Fahrplan §9 (09.11.2026): wann sind 85/90/95 % der Endfläche erreicht?"""
    from selbstheilung_lauf_protokoll import LaufProtokoll, flaechen
    assert flaechen([0, 0, 100, -1], 0.5) == {'frei_m2': 0.5, 'belegt_m2': 0.25, 'bekannt_m2': 0.75}
    p = LaufProtokoll(0.0)
    p.karte([0]*10, 1.0, 1.0)                     # vor der Fahrt: nichts
    assert p.abdeckung == []
    p.gestartet_um = 10.0
    for t, frei in ((10, 2), (20, 99), (40, 8), (70, 9), (100, 10), (101, 99)):
        p.karte([0]*frei + [-1]*(20-frei), 1.0, float(t))
    assert [s['fahrt_s'] for s in p.abdeckung] == [0.0, 30.0, 60.0, 90.0]
    assert [s['frei_m2'] for s in p.abdeckung] == [2.0, 8.0, 9.0, 10.0]
    zeiten = p.abdeckung_zeiten()
    assert zeiten == {'frei_ende_m2': 10.0, '85_prozent_s': 60.0,
                      '90_prozent_s': 60.0, '95_prozent_s': 90.0}
    p.beendet_um = 120.0
    p.karte([0]*20, 1.0, 200.0)                   # nach der Fahrt: nichts mehr
    assert len(p.abdeckung) == 4
    assert p.zusammenfassung()['abdeckung'] == zeiten


def _stellprobe(heals_folge, weg_bei=None):
    """Hilfsfahrt: je Sekunde ein Odometriewert; heals_folge[t] = Heilungen zu der Zeit."""
    from selbstheilung_lauf_protokoll import LaufProtokoll
    p = LaufProtokoll(0.0)
    p.explore({'self_healing': {'state': 'running', 'heals': 0, 'track_backs': 0,
                                'goals_reached': 0}}, 10.0)
    for i, heals in enumerate(heals_folge):
        t = 11.0 + i
        p.explore({'self_healing': {'state': 'running', 'heals': heals,
                                    'track_backs': min(heals, 1), 'goals_reached': 0}}, t)
        x = 5.0 if weg_bei is None or i < weg_bei else 5.0 + 0.1*(i - weg_bei + 1)
        p.stellprobe(x, 2.0, t, 0.5)
    return p


def test_stellprobe_freed_after_a_heal_counts_as_befreit():
    """MASTERPLAN §9 Regel 6 (10.11.2026): gezielte Probe statt langer Zufallsfahrt."""
    p = _stellprobe([0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1], weg_bei=4)
    urteil = p.stellprobe_ergebnis(0.5)
    assert urteil['urteil'] == 'befreit'
    assert urteil['weg']['heilungen_bis_dahin'] == 1 and urteil['weg']['rueckfahrten_bis_dahin'] == 1
    assert urteil['weg']['entfernung_m'] >= 0.5 and urteil['weg']['nach_s'] == pytest.approx(9.0)
    assert p.stellprobe_weg_um == pytest.approx(19.0)


def test_stellprobe_without_blockage_or_without_leaving_is_not_a_pass():
    weg_ohne_heilung = _stellprobe([0]*10, weg_bei=2)
    assert weg_ohne_heilung.stellprobe_ergebnis(0.5)['urteil'] == 'nicht_blockiert'
    steht = _stellprobe([0, 1, 2, 3, 4])
    urteil = steht.stellprobe_ergebnis(0.5)
    assert urteil['urteil'] == 'nicht_befreit' and urteil['weg'] is None
    assert urteil['max_entfernung_m'] == 0.0
    # Ohne Stellprobe (Schwelle 0) oder ohne Fahrt gibt es kein Urteil.
    assert steht.stellprobe_ergebnis(0.0) is None
    from selbstheilung_lauf_protokoll import LaufProtokoll
    assert LaufProtokoll(0.0).stellprobe_ergebnis(0.5) is None


def test_stellprobe_ignores_motion_before_the_mission_starts():
    from selbstheilung_lauf_protokoll import LaufProtokoll
    p = LaufProtokoll(0.0)
    p.stellprobe(0.0, 0.0, 1.0, 0.5)
    p.stellprobe(3.0, 0.0, 2.0, 0.5)             # vor dem Start (z. B. Hinstellen)
    assert p.stellprobe_start is None and p.stellprobe_weg is None


def test_each_reverse_drive_is_recorded_with_its_odometry_distance():
    """SH-8: 7 von 8 Rückfahrten liefen in die Zeitgrenze; wie weit kam er?"""
    p = LaufProtokoll(start=0.0)
    p.odom(0.0, 0.0, 1.0)
    p.cmd_vel(0.05, 0.0, 1.5)                  # vorwärts zählt nicht
    for i in range(30):                        # 30 s mit -0,015 m/s
        t = 2.0 + i
        p.cmd_vel(-0.015, 0.0, t)
        p.odom(-0.005*(i + 1), 0.0, t + 0.5)   # real nur 0,005 m/s
    p.cmd_vel(0.0, 0.0, 31.5)                  # 0,5 s ohne v < 0: noch dieselbe Fahrt
    p.odom(-0.15, 0.0, 33.5)                   # 2,5 s ohne v < 0: beendet
    p.cmd_vel(-0.015, 0.0, 40.0)               # zweite, kurze Rückfahrt
    p.odom(-0.16, 0.0, 40.5)
    zusammenfassung = p.zusammenfassung()      # offene Fahrt wird abgeschlossen
    assert zusammenfassung['rueckfahrten'] == [
        dict(t_s=2.0, dauer_s=29.0, v_min=-0.015, befehle=30, strecke_odom_m=0.15),
        dict(t_s=40.0, dauer_s=0.0, v_min=-0.015, befehle=1, strecke_odom_m=0.01)]
    assert [e['art'] for e in zusammenfassung['ereignisse']].count('rueckfahrt') == 2


def test_reverse_drive_without_any_command_at_the_base_leaves_no_entry():
    """SH-8 s3a: unter „approach“ kam kein Befehl ungleich null an."""
    p = LaufProtokoll(start=0.0)
    for i in range(30):
        p.cmd_vel(0.0, 0.0, float(i))
        p.odom(0.19, -0.19, i + 0.5)
    assert p.zusammenfassung()['rueckfahrten'] == []


def _fahrt(p, tempo_anteil, dreh_anteil=1.0):
    """Mission mit 10 s Fahrt bei 0,10 m/s und 4 s Drehen bei 0,25 rad/s (20 Hz)."""
    p.explore(_sh('running'), 1.0)
    x, gier = 0.0, 0.0
    p.odom(x, 0.0, 1.0, gier)
    for k in range(200):
        t = 1.0 + k*0.05
        p.cmd_vel(0.10, 0.0, t)
        x += 0.10*tempo_anteil*0.05
        p.odom(x, 0.0, t + 0.01, gier)
    for k in range(80):
        t = 11.0 + k*0.05
        p.cmd_vel(0.0, 0.25, t)
        gier += 0.25*dreh_anteil*0.05
        p.odom(x, 0.0, t + 0.01, gier)
    p.cmd_vel(0.0, 0.0, 15.0)


def test_speed_tracking_shows_whether_the_drive_does_what_is_commanded():
    """Bis AT-2 (15.11.2026) setzte der Antrieb nur etwa ein Fünftel um."""
    folgt = LaufProtokoll(0.0)
    _fahrt(folgt, 1.0)
    f = folgt.zusammenfassung()['tempo_folge']
    assert f['befohlener_weg_m'] == pytest.approx(1.0, abs=0.02)
    assert f['weg_gefahren_zu_befohlen'] == pytest.approx(1.0, abs=0.03)
    assert f['drehung_gedreht_zu_befohlen'] == pytest.approx(1.0, abs=0.03)
    kriecht = LaufProtokoll(0.0)
    _fahrt(kriecht, 0.2, 0.11)
    f = kriecht.zusammenfassung()['tempo_folge']
    assert f['weg_gefahren_zu_befohlen'] == pytest.approx(0.2, abs=0.02)
    assert f['drehung_gedreht_zu_befohlen'] == pytest.approx(0.11, abs=0.02)
    # Vor der Mission zählt nichts, und ohne nennenswerten Befehl gibt es kein Verhältnis.
    leer = LaufProtokoll(0.0)
    leer.cmd_vel(0.10, 0.0, 1.0)
    leer.cmd_vel(0.10, 0.0, 2.0)
    leer.odom(0.0, 0.0, 1.0, 0.0)
    leer.odom(0.1, 0.0, 2.0, 0.0)
    f = leer.zusammenfassung()['tempo_folge']
    assert f['befohlener_weg_m'] == 0.0 and f['weg_gefahren_zu_befohlen'] is None


def test_commands_older_than_the_base_watchdog_do_not_count_as_commanded_way():
    p = LaufProtokoll(0.0)
    p.explore(_sh('running'), 1.0)
    p.cmd_vel(0.10, 0.0, 1.0)
    p.cmd_vel(0.10, 0.0, 6.0)                 # 5 s Lücke: die Basis hielt nach 0,25 s
    assert p.tempo_folge()['befohlener_weg_m'] == pytest.approx(0.03, abs=0.006)


def test_wobble_is_measured_at_rest_and_while_driving_with_its_context():
    """AT-2: Christopher sah Ruckeln beim Anfahren; dafür gab es keine Messgröße."""
    p = LaufProtokoll(0.0)
    for k in range(50):                        # Ruhe vor der Mission
        p.imu(0.003, 0.004, 0.2 + k*0.01)
    p.explore(_sh('running'), 1.0)
    p.cmd_vel(0.0, 0.0, 1.0)
    p.imu(0.004, 0.003, 1.5)                   # steht
    p.cmd_vel(0.05, 0.0, 2.0)                  # fährt an
    p.imu(0.06, 0.08, 2.3)                     # Spitze beim Anfahren: 0,10 rad/s
    p.cmd_vel(0.10, 0.0, 4.0)
    p.imu(0.012, 0.016, 5.2)                   # ruhige Fahrt: 0,02 rad/s
    p.cmd_vel(0.0, 0.0, 8.0)                   # hält an
    p.imu(0.03, 0.04, 8.4)                     # Spitze beim Anhalten: 0,05 rad/s
    w = p.zusammenfassung()['wackeln']
    assert w['ruhe_vor_der_mission'] == {'messwerte': 50, 'rms_radps': 0.005, 'max_radps': 0.005}
    assert w['waehrend_der_mission']['max_radps'] == pytest.approx(0.10)
    assert w['staerkste_je_lage_radps'] == {
        'anfahren': 0.1, 'anhalten': 0.05, 'fahrt': 0.02, 'steht': 0.005}
    erste = w['staerkste_sekunden'][0]
    assert erste['lage'] == 'anfahren' and erste['v'] == 0.05 and erste['radps'] == 0.1
    assert [e['lage'] for e in w['staerkste_sekunden']] == ['anfahren', 'anhalten', 'fahrt', 'steht']


def test_wobble_without_imu_data_is_reported_as_missing_not_as_calm():
    p = LaufProtokoll(0.0)
    _fahrt(p, 1.0)
    assert p.zusammenfassung()['wackeln'] == {'daten': 'keine Daten'}
    p.imu(float('nan'), 0.0, 3.0)
    assert p.zusammenfassung()['wackeln'] == {'daten': 'keine Daten'}


def test_position_jitter_does_not_add_up_to_driven_way():
    """SH-8c s1a meldete 2,35-mal so viel Weg wie befohlen. Der Weg zählt deshalb in
    Schritten ab 5 mm; die rohe Summe steht daneben und zeigt das Zittern."""
    p = LaufProtokoll(0.0)
    p.explore(_sh('running'), 1.0)
    for k in range(600):                       # 20 s Stand mit ±0,3 mm und ±1 mrad Zittern
        t = 1.0 + k/30
        p.cmd_vel(0.0, 0.0, t)
        p.odom(0.0003*(-1)**k, 0.0, t, 0.001*(-1)**k)
    for k in range(200):                       # dann 10 s Fahrt mit 0,10 m/s
        t = 21.0 + k*0.05
        p.cmd_vel(0.10, 0.0, t)
        p.odom(0.10*(k + 1)*0.05, 0.0, t + 0.01, 0.0)
    p.cmd_vel(0.0, 0.0, 31.0)
    f = p.zusammenfassung()['tempo_folge']
    assert f['gefahrener_weg_m'] == pytest.approx(1.0, abs=0.02)
    assert f['weg_gefahren_zu_befohlen'] == pytest.approx(1.0, abs=0.03)
    assert f['gefahrener_weg_roh_m'] > 1.3     # das Zittern steckt in der rohen Summe
    assert f['gedrehte_drehung_rad'] == 0.0 and f['gedrehte_drehung_roh_rad'] > 1.0


def test_default_imu_topic_is_the_one_of_the_running_hwt_stack():
    import selbstheilung_lauf_protokoll as modul
    assert modul.IMU_TOPIC == '/shadow/hwt601/imu/data_raw'
    start = Path(__file__).parents[2] / 'src/robot_state_estimation/launch/hwt601_shadow.launch.py'
    assert "'imu_topic': '/shadow/hwt601/imu/data_raw'" in start.read_text(encoding='utf-8')
    quelle = Path(modul.__file__).read_text(encoding='utf-8')
    assert 'Messquelle Wackeln' in quelle and 'count_publishers(args.imu_topic)' in quelle


def _gitter(toedlich, n=120, aufloesung=0.05, ursprung=(-3.0, -3.0)):
    """Lokale Kostenkarte 6 m x 6 m; ``toedlich`` sind Weltpunkte, deren Zelle 100 bekommt."""
    werte = [0]*(n*n)
    for x, y in toedlich:
        i = int((x - ursprung[0])//aufloesung)
        j = int((y - ursprung[1])//aufloesung)
        werte[j*n + i] = 100
    return werte, n, n, aufloesung, ursprung


def test_near_picture_gives_cells_in_robot_coordinates_and_the_width_of_the_place():
    """W-1N (16.11.2026): an der Tür fehlte das Bild dessen, was den Regler anhielt."""
    from selbstheilung_lauf_protokoll import nahbild, kontur_seite
    # Zwei Türpfosten links und rechts neben dem Roboter, Zellmitten bei y = +-0,425 m.
    pfosten = [(0.11, 0.41), (0.11, -0.41)]
    bild = nahbild(*_gitter(pfosten), (0.0, 0.0, 0.0))
    rechts, links = sorted(bild['zellen'], key=lambda z: z[1])      # Zentimeter, vor / links
    assert abs(rechts[0] - 12.5) <= 0.5 and abs(rechts[1] + 42.5) <= 0.5
    assert abs(links[0] - 12.5) <= 0.5 and abs(links[1] - 42.5) <= 0.5
    assert bild['in_kontur'] == 0 and bild['in_kontur_ohne_polster'] == 0
    assert bild['links_m'] == pytest.approx(0.17, abs=0.01)         # 0,425 - 0,23 - 0,02
    assert bild['rechts_m'] == pytest.approx(0.17, abs=0.01)
    assert bild['breite_m'] == pytest.approx(0.85, abs=0.02)        # Zellmitte zu Zellmitte
    assert bild['naechste_m'] == pytest.approx(0.17, abs=0.01)
    assert bild['seite'] in ('links', 'rechts')
    # Um 90 Grad gedreht liegt ein Punkt in Welt-y vor dem Roboter.
    gedreht = nahbild(*_gitter([(0.01, 0.51)]), (0.0, 0.0, math.pi/2))
    (vor, quer), = gedreht['zellen']
    assert abs(vor - 52.5) <= 0.5 and abs(quer + 2.5) <= 0.5 and gedreht['seite'] == 'vorn'
    assert gedreht['links_m'] is None and gedreht['breite_m'] is None
    # Eine Zelle im Gehäuse und eine nur im 2-cm-Polster.
    innen = nahbild(*_gitter([(0.21, 0.01), (0.32, 0.01)]), (0.0, 0.0, 0.0))
    assert innen['in_kontur'] == 2 and innen['in_kontur_ohne_polster'] == 1
    assert innen['naechste_m'] == 0.0 and innen['seite'] == 'vorn'
    # Weit weg oder nichts: kein Fehler, leeres Bild.
    leer = nahbild(*_gitter([(2.0, 2.0)]), (0.0, 0.0, 0.0))
    assert leer['zellen'] == [] and leer['naechste_m'] is None and leer['seite'] is None
    assert nahbild([0]*10, 120, 120, 0.05, (-3.0, -3.0), (0.0, 0.0, 0.0)) is None
    assert kontur_seite(0.40, 0.30) == (pytest.approx(math.hypot(0.07, 0.05)), 'vorn links')
    assert kontur_seite(-0.20, 0.0) == (pytest.approx(0.07), 'hinten')
    assert kontur_seite(0.0, -0.24) == (0.0, 'rechts')


def test_near_pictures_are_taken_once_a_second_only_while_driving():
    p = LaufProtokoll(0.0)
    karte = _gitter([(0.11, 0.41), (0.11, -0.41)])
    p.odom(0.0, 0.0, 0.5, 0.0)
    p.lokale_karte(*karte, 0.6)                                  # vor der Mission: nichts
    assert p.nahbilder == []
    p.explore(_sh('running'), 1.0)
    p.cmd_vel(0.0, 0.25, 1.9)
    p.odom(0.0, 0.0, 1.9, 0.0)
    p.lokale_karte(*karte, 2.0)
    p.lokale_karte(*karte, 2.5)                                  # zu früh
    p.lokale_karte(*karte, 3.6)                                  # letzter Befehl 1,7 s alt
    p.explore(_sh('blocked', outcome='blocked_help_required', reason='help_required:x'), 5.0)
    p.lokale_karte(*karte, 6.0)                                  # nach der Mission: nichts
    s = p.zusammenfassung()
    assert [b['fahrt_s'] for b in s['nahbilder']] == [1.0, 2.6]
    assert s['nahbilder'][0]['befehl'] == [0.0, 0.25] and s['nahbilder'][1]['befehl'] is None
    assert s['nahbilder'][0]['breite_m'] == pytest.approx(0.85, abs=0.02)
    assert s['nahbild'] == dict(bilder=2, mit_zellen_in_gepolsterter_kontur=0,
                                mit_zellen_in_kontur_ohne_polster=0,
                                engste_breite_am_roboter_m=pytest.approx(0.85, abs=0.02),
                                bilder_mit_breite_unter_0_9_m=2)
    assert s['schema_version'] == 3
    ohne = LaufProtokoll(0.0)
    assert ohne.zusammenfassung()['nahbild'] is None


def test_search_counters_of_ek1_are_kept_in_the_summary():
    p = LaufProtokoll(0.0)
    p.explore(_sh('running', scans=0, shallow_frontiers=0), 1.0)
    p.explore(_sh('success', goals=3, outcome='exploration_complete', reason='exploration_complete',
                  scans=2, shallow_frontiers=41, visited_without_gain=1), 60.0)
    assert p.zusammenfassung()['suche'] == dict(scans=2, shallow_frontiers=41, visited_without_gain=1)
    alt = LaufProtokoll(0.0)
    alt.explore(_sh('running'), 1.0)
    assert alt.zusammenfassung()['suche'] == dict(scans=None, shallow_frontiers=None,
                                                  visited_without_gain=None)
