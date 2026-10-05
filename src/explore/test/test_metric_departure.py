"""Recorded native routes distinguish a dead end from a narrow throughway.

Fixtures are synthetic component geometry, never full-mission acceptance.
Only missing action peers are doubled; body/stop/turn proofs are product code.
"""
import json
import math
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
from geometry_msgs.msg import PoseStamped
from nav_msgs.msg import Path as NavPath

from explore.metric_frontier import MetricCandidate, known_safe_mask
from explore.portal_memory import Point2D
from explore.portal_source_adapter import raw_map_portal_source_from_values
from test_metric_frontier import adaptive_fixture


def fixture(name):
    folder = Path(__file__).parent/'data'
    meta = json.loads((folder/(name+'.json')).read_text())
    arrays = np.load(folder/(name+'.npz'))
    node, inputs = adaptive_fixture()
    for index, label in ((0, 'raw'), (5, 'cost')):
        grid = inputs[index]; geometry = meta[label+'_geometry']; array = arrays[label]
        grid.info.height, grid.info.width = array.shape
        grid.info.resolution = geometry['resolution']
        grid.info.origin.position.x, grid.info.origin.position.y = geometry['origin']
        grid.data = array.ravel().tolist()
    source = raw_map_portal_source_from_values(**node._metric_grid_values(inputs[0]))
    inputs[1] = replace(inputs[1], fingerprint=source.fingerprint)
    node._metric_scope = replace(node._metric_scope,
        vertices=tuple(Point2D(*xy) for xy in meta['scope']['vertices']))
    inputs[2] = tuple(meta['pose'])
    inputs[3], inputs[4] = known_safe_mask(arrays['raw'], node._metric_scope, inputs[1],
        tuple(meta['raw_geometry']['origin']), 0., inputs[0].info.resolution, .28)
    inputs[6] = (arrays['cost'] >= 0) & (arrays['cost'] < 100)
    node._metric_path_validation = 'rpp_rollout'
    node._metric_status = {}
    node._metric_active = object(); node._metric_nav_path = object()
    node.get_clock = lambda: SimpleNamespace(now=lambda: SimpleNamespace(nanoseconds=123))
    # Forecast geometry must never touch or retire actual first-body facts.
    node._metric_prepare_egress = lambda *_: pytest.fail('forecast changed private egress')
    return node, inputs, meta


def path(record):
    result = NavPath(); result.header.frame_id = 'map'
    for x, y in record['points']:
        pose = PoseStamped(); pose.pose.position.x = x; pose.pose.position.y = y
        pose.pose.orientation.z = math.sin(record['goal'][2]/2)
        pose.pose.orientation.w = math.cos(record['goal'][2]/2)
        result.poses.append(pose)
    return result


@pytest.mark.parametrize('name,index,expected', (
    ('ap06_dead_end', 0, False), ('ap06_dead_end', 2, True),
    ('ap06_corridor_departure', 0, True)))
def test_known_forward_departure_keeps_throughway_and_rejects_stranded_goal(name,index,expected):
    node, inputs, meta = fixture(name)
    records = meta['plans']; first = records[index]
    target = MetricCandidate('actual-component', *first['goal'], tuple(first['goal'][:2]),
        (), 1., 0., inputs[1].fingerprint, 1)
    route = node._metric_validate_nav_plan(inputs, path(first), target, public_only=True)
    assert route is not None
    before = [bytes(np.asarray(inputs[i].data, dtype=np.int8)) for i in (0, 5)]
    active = node._metric_active; calls = []
    def planner(candidate, stopped, *, start_pose):
        assert node._metric_active is None
        assert not stopped()
        calls.append((candidate, start_pose))
        record = records[index+len(calls)]
        assert np.allclose(start_pose, record['start_pose'], atol=1e-8)
        assert np.allclose((candidate.x,candidate.y,candidate.yaw),record['goal'],atol=1e-8)
        return path(record), record['error']
    node._metric_request_nav_plan = planner
    assert node._metric_departure_plan_ready(inputs, route, target, lambda: False) is expected
    assert node._metric_active is active and node._metric_nav_path is None
    assert node._metric_plan_after_ns == 123
    assert [bytes(np.asarray(inputs[i].data,dtype=np.int8)) for i in (0,5)] == before
    if not expected:
        assert node._metric_status['departure_plan_rejection'] == 'footprint_sweep_invalid'
    else:
        assert 'departure_plan_rejection' not in node._metric_status


def test_departure_forecast_cannot_ignore_source_stop_or_mutate_actual_path():
    node, inputs, meta = fixture('ap06_dead_end')
    first = meta['plans'][0]
    target = MetricCandidate('stop',*first['goal'],tuple(first['goal'][:2]),(),1.,0.,inputs[1].fingerprint,1)
    node._metric_request_nav_plan = lambda *_args, **_kw: pytest.fail('stopped query was sent')
    original = node._metric_nav_path
    assert not node._metric_departure_plan_ready(inputs, (), target, lambda: True)
    assert node._metric_nav_path is original
