import math
import re
from pathlib import Path

import numpy as np
import pytest
import yaml

from selbstheilung_stillstand_pruefen import (
    NOT_SET, Ergebnis, compare_params, flatten_ros_params, height_report,
    near_field_filters, normalize_topic, row_elevations, transform_points,
    values_match)


REPO = Path(__file__).resolve().parents[2]


def _params(relative):
    return flatten_ros_params(yaml.safe_load((REPO / relative).read_text(encoding='utf-8')))


def test_profiles_flatten_to_live_parameter_names():
    explore = _params('src/explore/config/self_healing_params.yaml')['/explore_node']
    assert explore['exploration_strategy'] == 'self_healing'
    assert explore['self_healing_unknown_speed_mps'] == pytest.approx(0.06)
    overlay = _params('src/robot_navigation/config/nav2_params_self_healing.yaml')
    assert overlay['/planner_server'] == {'GridBased.allow_unknown': True}
    assert overlay['/velocity_smoother']['min_velocity'] == [-0.05, 0.0, -0.25]
    assert overlay['/behavior_server']['simulate_ahead_time'] == pytest.approx(2.0)
    assert overlay['/local_costmap/local_costmap'] == {
        'obstacle_layer.vl53_left_mark.min_obstacle_height': -0.02,
        'obstacle_layer.vl53_right_mark.min_obstacle_height': -0.02}
    assert set(overlay['/global_costmap/global_costmap']) == set(
        overlay['/local_costmap/local_costmap'])
    collision = _params('src/vl53_near_field/config/collision_monitor_self_healing_overlay.yaml')
    assert collision == {'/collision_monitor': {
        'vl53_left.min_height': -0.02, 'vl53_right.min_height': -0.02}}
    nested = _params('src/robot_navigation/config/nav2_params_real.yaml')
    assert '/local_costmap/local_costmap' in nested


def test_values_match_is_strict_about_bool_and_tolerant_for_numbers():
    assert values_match(True, True) and not values_match(True, 1)
    assert values_match(0.06, 0.060000001) and values_match(1, 1.0)
    assert not values_match(0.06, 0.08)
    assert values_match([-0.05, 0.0], [-0.05, 0.0]) and not values_match([-0.05], [0.0])
    assert not values_match('a', NOT_SET)
    rows = compare_params({'a': 1, 'b': 'x'}, {'a': 1})
    assert [(n, ok) for n, _, _, ok in rows] == [('a', True), ('b', False)]


def test_near_field_filters_find_marking_sources_and_their_height_limit():
    local = _params('src/robot_navigation/config/nav2_params_real.yaml')[
        '/local_costmap/local_costmap']
    sources = near_field_filters(local)
    marking = {k: v for k, v in sources.items() if v['marking']}
    clearing = {k: v for k, v in sources.items() if not v['marking']}
    assert marking and clearing
    assert all(v['topic'].endswith('/points') for v in marking.values())
    assert {v['min'] for v in marking.values()} == {0.05}
    monitor = _params('src/vl53_near_field/config/collision_monitor_mapping_params.yaml')[
        '/collision_monitor']
    assert {v['min'] for v in near_field_filters(monitor).values()} == {0.05}


def test_low_object_seen_by_lowest_row_is_dropped_by_the_height_filter():
    # Sensor wie montiert: 0,215 m ueber base_link, base_link 0,09 m ueber Boden.
    rows = row_elevations(60.0)
    el = rows[0]                                   # unterste Zeile, -26,25 Grad
    forward = 0.42                                 # Vorderkante des Testobjekts
    radial = forward / math.cos(el)
    sensor = np.array([[radial*math.cos(el), 0.0, radial*math.sin(el)]])
    assert radial < 0.50                           # innerhalb z_max des Treibers
    base = transform_points(sensor, (0.29, 0.095, 0.215), (0.0, 0.0, 0.0, 1.0))
    report = height_report(base, sensor, 0.05, 0.09, rows)
    hit_floor = report['hoehe_ueber_boden_min_m']
    assert 0.09 < hit_floor < 0.11                 # Objekt ~10 cm hoch wird getroffen ...
    assert report['verworfen'] == 1                # ... aber unter 0,14 m verworfen
    assert report['filter_ueber_boden_m'] == pytest.approx(0.14)
    assert report['zeilen'][0]['zeile'] == 0


def test_height_bands_count_points_by_floor_height():
    base = np.array([[0.4, 0., z - 0.09] for z in (0.03, 0.08, 0.12, 0.20)])
    report = height_report(base, base, 0.05, 0.09)
    assert report['verworfen'] == 3 and report['behalten'] == 1
    assert list(report['baender_ueber_boden'].values()) == [1, 1, 1, 1]
    assert report['naechster_behaltener_x_base_link_m'] == pytest.approx(0.4)
    # Selbstheilungsgrenze (-0,02 m ueber base_link = 0,07 m ueber Boden):
    # gleiche Baender, nur noch der 3-cm-Punkt faellt unter den Filter.
    lowered = height_report(base, base, -0.02, 0.09)
    assert lowered['baender_ueber_boden'] == report['baender_ueber_boden']
    assert lowered['verworfen'] == 1 and lowered['filter_ueber_boden_m'] == pytest.approx(0.07)


def test_transform_points_rotates_with_quaternion():
    yaw90 = (0.0, 0.0, math.sin(math.pi/4), math.cos(math.pi/4))
    moved = transform_points([[1.0, 0.0, 0.0]], (0.0, 0.0, 1.0), yaw90)
    assert moved[0] == pytest.approx([0.0, 1.0, 1.0], abs=1e-9)


def test_result_fails_only_on_false_checks():
    result = Ergebnis()
    result.add('X', 'Hinweis', None)
    result.add('X', 'ok', True)
    assert result.bestanden
    result.add('X', 'kaputt', False)
    assert not result.bestanden
    assert normalize_topic('speed_limit') == '/speed_limit'


def test_checker_stays_read_only():
    source = (Path(__file__).with_name('selbstheilung_stillstand_pruefen.py')
              .read_text(encoding='utf-8'))
    for forbidden in ('create_publisher', 'ActionClient', 'send_goal',
                      'SetParameters', 'set_parameters', 'call_async(Trigger'):
        assert forbidden not in source
    # Einzige Dienstaufrufe: GetParameters und ListParameters.
    assert set(re.findall(r'self\._call\((\w+)', source)) == {'GetParameters', 'ListParameters'}
