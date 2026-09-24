"""The real producer's decision before filtering points for the near window."""

import ast
import math
from pathlib import Path
import sys
import time
from types import SimpleNamespace

import numpy as np
import pytest
from builtin_interfaces.msg import Time
from robot_interfaces.msg import NearFieldStatus
from sensor_msgs_py import point_cloud2
from std_msgs.msg import Header

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE_ROOT))

from vl53_near_field.measurement_quality import (  # noqa: E402
    assess_frame, INVALID, PARTIAL, UNKNOWN, VALID_FAR, VALID_NEAR,
)


def frame(distance=800, status=5):
    return {
        'distance_mm': [distance] * 64,
        'target_status': [status] * 64,
        'nb_target_detected': [1] * 64,
        'sigma_mm': [10] * 64,
    }


def assess(data):
    return assess_frame(data, 8, 8, [5], True, 0., 50., .01, .50)


def test_valid_near_and_valid_far_have_distinct_status_with_full_coverage():
    near, valid, columns, quality = assess(frame(240))
    assert quality == VALID_NEAR and columns == 255 and valid.all()
    assert np.nanmin(near) == pytest.approx(.24)
    far, valid, columns, quality = assess(frame(800))
    assert quality == VALID_FAR and columns == 255 and valid.all()
    assert np.nanmin(far) == pytest.approx(.8)


def test_missing_or_bad_quality_does_not_certify_empty_near_cloud():
    missing = frame()
    del missing['target_status']
    assert assess(missing)[3] == UNKNOWN
    assert assess(frame(240, 255))[3] == INVALID
    invalid = frame()
    invalid['sigma_mm'] = [99] * 64
    assert assess(invalid)[3] == INVALID
    partial = frame()
    partial['target_status'][0] = 255
    _, valid, columns, quality = assess(partial)
    assert quality == PARTIAL and columns != 255 and valid.sum() == 63
    huge = frame(1_000_000_000)
    assert assess(huge)[3] == INVALID
    negative_sigma = frame()
    negative_sigma['sigma_mm'] = [-1] * 64
    assert assess(negative_sigma)[3] == INVALID
    malformed = frame()
    malformed['target_status'] = 5
    assert assess(malformed)[3] == UNKNOWN


def test_costmap_does_not_clear_unobserved_column_or_past_far_return():
    source = (PACKAGE_ROOT / 'vl53_near_field' /
              'vl53_near_field_node.py').read_text()
    cls = next(node for node in ast.parse(source).body
               if isinstance(node, ast.ClassDef)
               and node.name == 'Vl53NearField')
    method = next(node for node in cls.body
                  if isinstance(node, ast.FunctionDef)
                  and node.name == '_matrix_to_costmap_cloud')
    scope = {'np': np, 'math': math, 'Header': Header,
             'point_cloud2': point_cloud2}
    exec(compile(ast.Module(body=[method], type_ignores=[]),
                 '<producer-method>', 'exec'), scope)
    producer = SimpleNamespace(GC=8, col_az=np.zeros(8),
                               costmap_clear_range=.6)
    measured = np.full((8, 8), .8)
    measured[:, 0] = .55
    valid = np.ones((8, 8), dtype=bool)
    valid[0, 1] = False
    cloud = scope['_matrix_to_costmap_cloud'](
        producer, measured, valid, 'vl53_left_link', Header().stamp)
    points = list(point_cloud2.read_points(cloud, field_names=('x', 'y', 'z')))
    assert len(points) == 7
    assert points[0][0] == pytest.approx(.55)
    assert max(point[0] for point in points) == pytest.approx(.6)


def test_partial_frame_preserves_near_obstacle_in_original_cloud():
    methods = _producer_methods('_build_matrix', '_matrix_to_cloud',
                                '_matrix_to_costmap_cloud')
    producer = SimpleNamespace(
        GR=8, GC=8, z_min=.01, z_max=.50, require_nb=True,
        valid_statuses=[5], min_sps=0., max_sigma=50.,
        row_el=np.zeros(8), col_az=np.zeros(8), costmap_clear_range=.60)
    sample = frame(800, 255)
    sample['distance_mm'][0] = 240
    sample['target_status'][0] = 5
    _, valid, columns, quality = assess(sample)
    assert quality == PARTIAL and columns == 0 and valid.sum() == 1
    near = methods['_build_matrix'](producer, sample)
    original = methods['_matrix_to_cloud'](
        producer, near, 'vl53_left_link', Header().stamp)
    clearing = methods['_matrix_to_costmap_cloud'](
        producer, np.where(valid, .24, np.nan), valid,
        'vl53_left_link', Header().stamp)
    assert original.width == 1
    assert clearing.width == 0


def _producer_methods(*names):
    source = (PACKAGE_ROOT / 'vl53_near_field' /
              'vl53_near_field_node.py').read_text()
    cls = next(node for node in ast.parse(source).body
               if isinstance(node, ast.ClassDef)
               and node.name == 'Vl53NearField')
    selected = [node for node in cls.body
                if isinstance(node, ast.FunctionDef) and node.name in names]
    scope = {'np': np, 'math': math, 'time': time, 'Header': Header,
             'point_cloud2': point_cloud2, 'NearFieldStatus': NearFieldStatus,
             'assess_frame': assess_frame}
    exec(compile(ast.Module(body=selected, type_ignores=[]),
                 '<real-producer-methods>', 'exec'), scope)
    return scope


def test_real_producer_tick_pairs_quality_and_clouds_without_devices():
    methods = _producer_methods(
        '_tick', '_build_matrix', '_matrix_to_cloud',
        '_matrix_to_costmap_cloud', '_nanmin')
    producer = type('Producer', (), {name: methods[name] for name in (
        '_tick', '_build_matrix', '_matrix_to_cloud',
        '_matrix_to_costmap_cloud', '_nanmin')})()
    producer.GR = producer.GC = 8
    producer.valid_statuses = [5]
    producer.require_nb = True
    producer.min_sps = 0.0
    producer.max_sigma = 50.0
    producer.z_min = .01
    producer.z_max = .50
    producer.flipx_left = True
    producer.flipx_right = False
    producer.inner = 4
    producer.thresh = .25
    producer.costmap_clear_range = .60
    producer.col_az = np.zeros(8)
    producer.row_el = np.zeros(8)
    producer.frame_left = 'vl53_left_link'
    producer.frame_right = 'vl53_right_link'
    producer.publish_costmap_cloud = True
    producer.ch_left = 0
    producer.ch_right = 1
    producer.sL = object()
    producer.sR = object()
    producer.frames = {0: frame(240), 1: frame(800)}
    producer._get_data_safe = lambda _sensor, channel: producer.frames[channel]
    producer.get_clock = lambda: SimpleNamespace(
        now=lambda: SimpleNamespace(to_msg=lambda: Time(sec=10)))
    output = {name: [] for name in ('status', 'left', 'right', 'left_cm', 'right_cm')}
    for name in output:
        setattr(producer, f'pub_{name}', SimpleNamespace(
            publish=lambda message, key=name: output[key].append(message)))

    producer._tick()
    status = output['status'][-1]
    assert (status.left_quality, status.right_quality) == (
        VALID_NEAR, VALID_FAR)
    assert status.left_observed_columns == status.right_observed_columns == 255
    assert output['left'][-1].width == 64 and output['right'][-1].width == 0
    assert output['left_cm'][-1].width == output['right_cm'][-1].width == 8
    assert all(messages[-1].header.stamp == status.header.stamp
               for name, messages in output.items() if name != 'status')

    producer.frames[1] = None
    producer._tick()
    assert output['status'][-1].right_quality == UNKNOWN
    assert len(output['right']) == 1 and len(output['right_cm']) == 1

    producer.frames[1] = frame(800)
    producer.frames[1]['sigma_mm'] = [99] * 64
    producer._tick()
    assert output['status'][-1].right_quality == INVALID
    assert output['right'][-1].width == output['right_cm'][-1].width == 0


def test_real_driver_range_sigma_field_is_used_for_quality():
    get_data = _producer_methods('_get_data_safe')['_get_data_safe']
    sensor = SimpleNamespace(
        check_data_ready=lambda: True,
        get_ranging_data=lambda: SimpleNamespace(
            distance_mm=[800] * 64, target_status=[5] * 64,
            nb_target_detected=[1] * 64, range_sigma_mm=[10] * 64,
            signal_per_spad=[100] * 64))
    node = SimpleNamespace(_mux_select=lambda _channel: None,
                           bad={0: 0}, GR=8, GC=8, max_bad=3)
    data = get_data(node, sensor, 0)
    assert data['sigma_mm'] == [10] * 64
    assert assess(data)[3] == VALID_FAR
