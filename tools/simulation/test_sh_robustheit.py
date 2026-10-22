import importlib.util
import json
import sys
from pathlib import Path

import pytest

HIER = Path(__file__).parent
sys.path.insert(0, str(HIER))
spec = importlib.util.spec_from_file_location('sh', HIER/'sh_robustheit.py')
sh = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sh)
REPO = HIER.parents[1]


def test_product_parameters_keep_product_values_and_only_rename_jazzy_classes():
    p = sh.produktparameter(REPO)
    # Selbstheilungs-Overlay wirkt (Planung durch Unbekanntes, VL53-Grenze).
    assert p['planner_server']['ros__parameters']['GridBased']['allow_unknown'] is True
    layer = p['local_costmap']['local_costmap']['ros__parameters']['obstacle_layer']
    assert layer['vl53_left_mark']['min_obstacle_height'] == -0.02
    assert layer['vl53_left_mark']['topic'] == '/near_field/left/points'      # Basis erhalten
    assert p['velocity_smoother']['ros__parameters']['min_velocity'][0] == -0.05
    assert p['collision_monitor']['ros__parameters']['vl53_left']['min_height'] == -0.02
    # Nur die Klassennamen sind Jazzy-spezifisch.
    assert p['planner_server']['ros__parameters']['GridBased']['plugin'] == \
        'nav2_navfn_planner::NavfnPlanner'
    assert p['behavior_server']['ros__parameters']['backup']['plugin'] == 'nav2_behaviors::BackUp'
    jazzy = (HIER/'sh_robustheit_jazzy.yaml').read_text(encoding='utf-8')
    assert 'allow_unknown' not in jazzy and 'velocity' not in jazzy and 'min_' not in jazzy
    slow = p['collision_monitor']['ros__parameters']['SlowZone']['points']
    assert json.loads(slow) == [[.8, .25], [.8, -.25], [.3, -.25], [.3, .25]]   # gleiche Werte
    bt = p['bt_navigator']['ros__parameters']['default_nav_to_pose_bt_xml']
    assert bt.endswith('navigate_to_pose_self_healing.xml')
    assert p['slam_toolbox']['ros__parameters']['scan_topic'] == '/scan_normiert'


def test_triggers_require_every_declared_condition():
    a = {'ziele_erreicht': 1, 'faehrt': True}
    assert not sh.ausloeser_erfuellt(a, 0, (0., 0., 0.), .1, 10.)
    assert not sh.ausloeser_erfuellt(a, 1, (0., 0., 0.), 0., 10.)
    assert sh.ausloeser_erfuellt(a, 1, (0., 0., 0.), .1, 10.)
    assert not sh.ausloeser_erfuellt({'x_ueber_m': -.5}, 0, (-.6, 0., 0.), 0., 0.)
    assert sh.ausloeser_erfuellt({'x_ueber_m': -.5}, 0, (-.4, 0., 0.), 0., 0.)
    assert sh.ausloeser_erfuellt(None, 0, (0., 0., 0.), 0., 0.)


def _zusammenfassung(outcome, ziele, warten=None):
    return {'endzustand': {'outcome': outcome, 'goals_reached': ziele},
            'kriterien_automatisch': {'fahrt_beendet': True},
            'ereignisse': [{'art': 'selbstheilung', 'waiting_for': warten}]}


def test_evaluation_follows_the_declared_acceptance():
    manifest = json.loads((HIER/'sh_robustheit_szenarien.json').read_text(encoding='utf-8'))
    abnahme = manifest['abnahme']
    luecke = next(s for s in manifest['szenarien'] if s['id'] == 'sensorluecke')
    stoerung = {'ausgeloest_s': 30., 'ziele_bei_ausloesung': 1}
    ok, k = sh.bewerte(abnahme, luecke, _zusammenfassung(
        'exploration_complete', 3, 'vl53_status_missing_stale_or_invalid'), stoerung, False, [])
    assert ok and k['heilung_beobachtet'] and k['ziele_nach_stoerung']
    # Hilfe statt Heilung ist in Stufe 2 kein sauberes Ende.
    ok, k = sh.bewerte(abnahme, luecke, _zusammenfassung(
        'blocked_help_required', 3, 'vl53_x'), stoerung, False, [])
    assert not ok and not k['sauberes_ende']
    # Störung bemerkt, aber nie gewartet -> Heilung nicht belegt.
    ok, k = sh.bewerte(abnahme, luecke, _zusammenfassung('exploration_complete', 3), stoerung,
                       False, [])
    assert not ok and not k['heilung_beobachtet']
    tuer = next(s for s in manifest['szenarien'] if s['id'] == 'gesperrte_tuer')
    ok, k = sh.bewerte(abnahme, tuer, _zusammenfassung('usable_partial', 2),
                       {'ausgeloest_s': 50., 'ziele_bei_ausloesung': 2}, False, [])
    assert ok                                   # 0 Ziele nach dem Schließen genügen hier
    ok, k = sh.bewerte(abnahme, tuer, _zusammenfassung('usable_partial', 2),
                       {'ausgeloest_s': 50., 'ziele_bei_ausloesung': 2}, True, ['explorer'])
    assert not k['keine_kollision'] and not k['kein_prozessabsturz']


def test_manifest_declares_five_faults_plus_reference():
    manifest = json.loads((HIER/'sh_robustheit_szenarien.json').read_text(encoding='utf-8'))
    arten = [(s['stoerung'] or {}).get('art') for s in manifest['szenarien']]
    assert arten == [None, 'vl53_pause', 'lidar_pause_und_alte_karte', 'cpu_last',
                     'niedriges_hindernis', 'tuer_schliessen']
    assert manifest['abnahme']['erlaubte_enden'] == ['exploration_complete', 'usable_partial']


def test_harness_publishes_only_sensor_data_and_the_app_command():
    source = (HIER/'sh_robustheit.py').read_text(encoding='utf-8')
    topics = sorted(set(__import__('re').findall(r"create_publisher\(\w+, '([^']+)'", source)))
    assert topics == ['/map', '/mission_manager/command_json', '/near_field/left/points',
                      '/near_field/left/points_costmap', '/near_field/right/points',
                      '/near_field/right/points_costmap', '/near_field/status', '/odom', '/scan']
    # /map nur für die eine alte Karte im Kartenrennen, kein Wahrheitskartenpublisher.
    assert source.count('karten_pub.publish(') == 1
    assert 'NavigateToPose' not in source and 'send_goal' not in source


def test_plan_bottleneck_keeps_the_narrowest_plan_and_counts_tight_plans():
    import numpy as np
    stand = sh.plan_engstelle(None, np.array([.5, .3]), np.array([[0., 0.], [1., 1.]]), 3., .28)
    assert stand['abstand_m'] == .3 and stand['punkt'] == [1., 1.] and stand['t_s'] == 3.
    stand = sh.plan_engstelle(stand, np.array([.26]), np.array([[2., 0.]]), 4., .28)
    assert stand['abstand_m'] == .26 and stand['plaene'] == 2
    assert stand['plaene_unter_robot_radius'] == 1
    stand = sh.plan_engstelle(stand, [], np.zeros((0, 2)), 5., .28)
    assert stand['plaene'] == 3 and stand['abstand_m'] == .26


def test_experiment_flag_is_never_an_acceptance():
    source = (HIER/'sh_robustheit.py').read_text(encoding='utf-8')
    assert "ergebnis['qualifikation'] = 'experiment_keine_abnahme'" in source


def test_plan_bottleneck_near_the_robot_ignores_far_plan_sections():
    import numpy as np
    punkte = np.array([[0., 0.], [.5, 0.], [3., 0.]])
    stand = sh.plan_engstelle(None, np.array([.4, .25, .05]), punkte, 7., .28, roboter=(0., 0., 0.))
    assert stand['abstand_m'] == .05                     # ganzer Plan: ferner Abschnitt
    assert stand['nah_abstand_m'] == .25 and stand['nah_punkt'] == [.5, 0.]
    assert stand['nah_unter_robot_radius'] == [{'t_s': 7., 'abstand_m': .25, 'punkt': [.5, 0.]}]


def test_local_costmap_snapshot_counts_cells_over_the_obstacle():
    import numpy as np
    werte = np.zeros((20, 20), dtype=np.int16)
    werte[5:7, 5:7] = 100                      # zwei mal zwei tödliche Zellen
    werte[7, 5] = -1
    karte = (werte, .05, -.5, -.5)             # Ursprung (-0,5 / -0,5)
    ecken = [(-.24, -.24), (-.14, -.24), (-.14, -.12), (-.24, -.12)]   # Spalten 5-7, Zeilen 5-7
    stand = sh.kostenkarte_ueber(karte, ecken)
    assert stand['toedlich'] == 4 and stand['unbekannt'] == 1 and stand['zellen'] == 9
    assert sh.kostenkarte_ueber(karte, [(5., 5.), (6., 6.)]) == {'zellen': 0, 'im_fenster': False}
    assert sh.kostenkarte_ueber(None, ecken) is None


def test_manifest_v2_replaces_goal_counts_by_reachable_coverage():
    v1 = json.loads((HIER/'sh_robustheit_szenarien.json').read_text(encoding='utf-8'))
    v2 = json.loads((HIER/'sh_robustheit_szenarien_v2.json').read_text(encoding='utf-8'))
    # Welt, Sensoren, Budgets und Störungen unverändert; nur die Abnahme ist neu.
    for teil in ('welt', 'sensor', 'budgets'):
        assert v2[teil] == v1[teil]
    assert [s['stoerung'] for s in v2['szenarien']] == [s['stoerung'] for s in v1['szenarien']]
    a = v2['abnahme']
    assert 'min_ziele' not in a and a['min_abdeckung_erreichbar'] == .95
    luecke = next(s for s in v2['szenarien'] if s['id'] == 'sensorluecke')
    stoerung = {'ausgeloest_s': 30., 'ziele_bei_ausloesung': 1}
    # Vollständige Karte mit nur einem gezählten Ziel besteht jetzt.
    zus = _zusammenfassung('exploration_complete', 1, 'vl53_status_missing_stale_or_invalid')
    ok, k = sh.bewerte(a, luecke, zus, stoerung, False, [], {'erreichbar_anteil': .98})
    assert ok and 'mindestens_ziele' not in k and 'ziele_nach_stoerung' not in k
    ok, k = sh.bewerte(a, luecke, zus, stoerung, False, [], {'erreichbar_anteil': .80})
    assert not ok and not k['abdeckung_oder_teilende']
    # Sauberes Teilende genügt (Entscheidung D), Kontakt und Hilfe weiterhin nicht.
    tuer = next(s for s in v2['szenarien'] if s['id'] == 'gesperrte_tuer')
    ok, _ = sh.bewerte(a, tuer, _zusammenfassung('usable_partial', 0), stoerung, False, [], None)
    assert ok
    ok, k = sh.bewerte(a, tuer, _zusammenfassung('usable_partial', 2), stoerung, True, [], None)
    assert not ok and not k['keine_kollision']
    ok, k = sh.bewerte(a, luecke, _zusammenfassung('blocked_help_required', 3, 'vl53_x'),
                       stoerung, False, [], {'erreichbar_anteil': 1.})
    assert not ok and not k['sauberes_ende']


def test_manifest_v3_requires_coverage_and_a_plausible_map_without_partial_exception():
    v2 = json.loads((HIER/'sh_robustheit_szenarien_v2.json').read_text(encoding='utf-8'))
    v3 = json.loads((HIER/'sh_robustheit_szenarien_v3.json').read_text(encoding='utf-8'))
    for teil in ('welt', 'sensor', 'budgets'):
        assert v3[teil] == v2[teil]
    a = v3['abnahme']
    assert 'teilende_genuegt' not in a and a['max_kartenfehler_m'] == .10
    luecke = next(s for s in v3['szenarien'] if s['id'] == 'sensorluecke')
    stoerung = {'ausgeloest_s': 30., 'ziele_bei_ausloesung': 1}
    zus = _zusammenfassung('usable_partial', 3, 'vl53_status_missing_stale_or_invalid')
    # Fall aus v2: Teilende mit verbogener Karte (3,3 m) und 74 % Fläche besteht nicht mehr.
    ok, k = sh.bewerte(a, luecke, zus, stoerung, False, [], {'erreichbar_anteil': .74},
                       {'maximum_occupied_wall_error_m': 3.31})
    assert not ok and not k['abdeckung_erreichbar'] and not k['karte_plausibel']
    ok, k = sh.bewerte(a, luecke, _zusammenfassung('exploration_complete', 1, 'vl53_x'), stoerung,
                       False, [], {'erreichbar_anteil': .98}, {'maximum_occupied_wall_error_m': .04})
    assert ok and set(k) >= {'abdeckung_erreichbar', 'karte_plausibel', 'heilung_beobachtet'}
    ok, _ = sh.bewerte(a, luecke, _zusammenfassung('exploration_complete', 1, 'vl53_x'), stoerung,
                       False, [], {'erreichbar_anteil': .98}, None)
    assert not ok                                # ohne Kartenvergleich kein Bestehen


def test_asymmetric_experiment_world_only_adds_furniture():
    v3 = json.loads((HIER/'sh_robustheit_szenarien_v3.json').read_text(encoding='utf-8'))
    x = json.loads((HIER/'experimente'/'manifest_asymmetrisch.json').read_text(encoding='utf-8'))
    assert x['qualifikation'].startswith('experiment')
    assert {k: v for k, v in x['welt'].items() if k != 'zusatz_hindernisse'} == v3['welt']
    assert x['abnahme'] == v3['abnahme'] and x['szenarien'] == v3['szenarien']
    assert len(x['welt']['zusatz_hindernisse']) == 4

