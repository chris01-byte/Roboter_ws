"""Narrow future-departure experiment; no ROS nodes or live graph required."""
import json
import sys
from types import ModuleType, SimpleNamespace

import pytest

import ap06_departure_probe as probe


@pytest.fixture
def invocation(tmp_path):
    node = SimpleNamespace(_metric_status={'departure_plan_rejection': 'previous'},
        _metric_last_route_rejection='previous_query', _metric_path_validation='rpp_rollout',
        _metric_controller_contract=lambda stop: True)
    inputs = ('raw', 'correlation', (1., 2., .1), 'known', 'safe', 'cost', 'cost_known')
    route = ((1., 2.), (1.5, 2.))
    target = SimpleNamespace(x=1.5, y=2., yaw=.1, task_id=7)
    return node, inputs, route, target, tmp_path/'departure_assessments.jsonl'


def read_record(path):
    rows = path.read_text().splitlines()
    assert len(rows) == 1
    return json.loads(rows[0])


def test_original_true_passes_unchanged_without_new_permission(invocation):
    node, inputs, route, target, journal = invocation
    original_calls = []
    def original(*args):
        original_calls.append(args)
        return True
    checked = probe.make_departure_probe(original, journal, lambda *_: pytest.fail('unnecessary body check'))
    stop = lambda: pytest.fail('original True must pass through without extra stop call')
    assert checked(node, inputs, route, target, stop) is True
    assert original_calls == [(node, inputs, route, target, stop)]
    row = read_record(journal)
    assert row['original_decision'] is True and not row['deferred']
    assert row['prior_departure_rejection'] == row['departure_rejection_at_original_return'] == 'previous'
    assert row['stop_after_prediction'] is None


def test_only_future_failure_is_deferred_with_current_checks_and_exact_journal(invocation):
    node, inputs, route, target, journal = invocation
    calls = []
    def original(*args):
        calls.append('prediction')
        node._metric_status['departure_plan_rejection'] = 'footprint_sweep_invalid'
        node._metric_last_route_rejection = 'future_query_geometry'
        return False
    def stopped():
        calls.append('stop')
        return False
    def controller(stop):
        assert stop is stopped
        calls.append('controller')
        return True
    def body(at_node, at_inputs):
        assert at_node is node and at_inputs is inputs
        calls.append('body')
        return True
    node._metric_controller_contract = controller
    checked = probe.make_departure_probe(original, journal, body)
    assert checked(node, inputs, route, target, stopped) is True
    assert calls == ['prediction', 'stop', 'controller', 'body', 'stop']
    assert node._metric_status == {'departure_plan_rejection': 'footprint_sweep_invalid'}
    row = read_record(journal)
    assert row['original_decision'] is False and row['deferred'] and row['returned']
    assert row['controller_contract'] and row['public_current_body']
    assert not row['stop_after_prediction'] and not row['stop_after_checks']
    assert row['prior_departure_rejection'] == 'previous'
    assert row['departure_rejection_at_original_return'] == 'footprint_sweep_invalid'
    assert row['last_route_rejection_at_original_return'] == 'future_query_geometry'
    assert row['pose'] == list(inputs[2]) and row['target'] == dict(x=1.5, y=2., yaw=.1)
    assert row['entered_monotonic'] <= row['original_returned_monotonic'] <= row['finished_monotonic']
    assert row['original_qualification'] is False


@pytest.mark.parametrize('stops', [(True,), (False, True)])
def test_source_cancel_or_deadline_stop_is_never_deferred(invocation, stops):
    node, inputs, route, target, journal = invocation
    answers = iter(stops)
    checked = probe.make_departure_probe(lambda *args: False, journal, lambda *args: True)
    assert checked(node, inputs, route, target, lambda: next(answers)) is False
    row = read_record(journal)
    assert row['original_decision'] is False and not row['deferred'] and row['returned'] is False
    assert row['stop_after_prediction'] or row['stop_after_checks']


@pytest.mark.parametrize('controller, body, expected', [
    (False, True, 'actual_controller_contract_invalid'),
    (True, False, 'current_padded_body_not_public')])
def test_controller_mismatch_and_private_or_occupied_body_remain_denied(invocation, controller, body, expected):
    node, inputs, route, target, journal = invocation
    node._metric_controller_contract = lambda stop: controller
    checked = probe.make_departure_probe(lambda *args: False, journal, lambda *args: body)
    assert checked(node, inputs, route, target, lambda: False) is False
    row = read_record(journal)
    assert row['experiment_rejection'] == expected and not row['deferred']


@pytest.mark.parametrize('phase', ['original_prediction', 'stop_after_prediction', 'controller_contract', 'public_current_body'])
def test_exceptions_are_journaled_and_propagated_without_permission(invocation, phase):
    node, inputs, route, target, journal = invocation
    def broken(*args):
        raise ValueError('original source or proof failure')
    if phase == 'controller_contract':
        node._metric_controller_contract = broken
    checked = probe.make_departure_probe(broken if phase == 'original_prediction' else lambda *args: False,
        journal, broken if phase == 'public_current_body' else lambda *args: True)
    with pytest.raises(ValueError, match='original source or proof failure'):
        checked(node, inputs, route, target, broken if phase == 'stop_after_prediction' else lambda: False)
    row = read_record(journal)
    assert row['exception']['phase'] == phase
    assert not row['deferred'] and row['returned'] is None


@pytest.mark.parametrize('malformed', [None, 0, 1, 'False'])
def test_non_bool_predictor_is_never_reinterpreted(invocation, malformed):
    node, inputs, route, target, journal = invocation
    checked = probe.make_departure_probe(lambda *args: malformed, journal, lambda *args: True)
    with pytest.raises(TypeError, match='must return bool'):
        checked(node, inputs, route, target, lambda: False)
    assert not read_record(journal)['deferred']


def test_conservative_controller_model_never_receives_ablation(invocation):
    node, inputs, route, target, journal = invocation
    node._metric_path_validation = 'conservative'
    checked = probe.make_departure_probe(lambda *args: False, journal, lambda *args: True)
    assert checked(node, inputs, route, target, lambda: False) is False
    assert read_record(journal)['experiment_rejection'] == 'unsupported_controller_model'


@pytest.mark.parametrize('override', [dict(ideal_lidar=False), dict(profile_selection=True),
    dict(capture_decisions=True), dict(capture_geometry=True), dict(diagnostic_beams=2160)])
def test_profile_rejects_undeclared_combinations(monkeypatch, override):
    monkeypatch.setattr(probe, 'require_isolation', lambda: None)
    values = dict(ideal_lidar=True, profile_selection=False, capture_decisions=False,
                  capture_geometry=False, diagnostic_beams=None)
    values.update(override)
    with pytest.raises(ValueError):
        probe.validate_experiment_options(SimpleNamespace(**values))


def test_install_rejects_unisolated_use_before_importing_ros_or_writing_journal(tmp_path, monkeypatch):
    def reject():
        raise ValueError('device-free container required')
    monkeypatch.setattr(probe, 'require_isolation', reject)
    journal = tmp_path/'departure_assessments.jsonl'
    with pytest.raises(ValueError, match='device-free'):
        probe.install_departure_probe(journal)
    assert not journal.exists()


def test_existing_assessment_journal_is_not_overwritten(invocation):
    *_, journal = invocation
    journal.write_text('preserved original evidence\n')
    with pytest.raises(FileExistsError):
        probe.make_departure_probe(lambda *args: False, journal)
    assert journal.read_text() == 'preserved original evidence\n'


@pytest.mark.parametrize('raw_public, cost_public', [(True, True), (False, True), (True, False)])
def test_public_body_uses_stripped_masks_and_unchanged_tracking_reserves(monkeypatch, raw_public, cost_public):
    package = ModuleType('explore')
    module = ModuleType('explore.metric_frontier')
    checked = []
    def footprint(x, y, yaw, grid, mask, world_to_grid, grid_to_world, bounds, **reserves):
        checked.append((grid, mask, reserves))
        assert (x, y, yaw) == (1., 2., .1)
        assert bounds == (-.13, .33, -.25, .25)
        assert reserves == dict(heading_half_angle=.05, center_deviation_m=.02)
        return mask
    module.footprint_clear = footprint
    monkeypatch.setitem(sys.modules, 'explore', package)
    monkeypatch.setitem(sys.modules, 'explore.metric_frontier', module)
    original_inputs = ('raw', 'c', (1., 2., .1), True, True, 'cost', True)
    public_inputs = ('raw', 'c', (1., 2., .1), raw_public, True, 'cost', cost_public)
    node = SimpleNamespace(_metric_public_inputs=lambda at: public_inputs,
        _world_to_grid=object(), _grid_to_world=object(), _metric_bounds=(-.13, .33, -.25, .25))
    assert probe.public_current_body(node, original_inputs) is (raw_public and cost_public)
    assert checked[0][1] is raw_public
    if raw_public:
        assert checked[1][1] is cost_public
