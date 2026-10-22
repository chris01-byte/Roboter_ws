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
