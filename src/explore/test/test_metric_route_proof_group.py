"""Actual pure proposals share a binding until the full final content audit."""
import inspect
from dataclasses import replace

import pytest

from test_metric_public_cooldown import frozen


def test_recorded_selector_reduces_repeated_signature_reads_without_changing_target(monkeypatch):
    node, inputs, policy = frozen('ap06_b13_budget_history')
    original = node._metric_grid_geometry
    full_reads = []
    def geometry(grid):
        if inspect.currentframe().f_back.f_code.co_name == '_metric_selection_memo':
            full_reads.append(True)
        return original(grid)
    monkeypatch.setattr(node, '_metric_grid_geometry', geometry)
    selected = node._metric_select(inputs, policy, .3)
    assert len(selected) == 1 and selected[0].requires_nav2_plan
    assert (selected[0].x, selected[0].y, selected[0].yaw) == (
        1.4849999668076634, -0.48499998915940523, 0.)
    assert len(selected[0].observation_points) == 90
    assert selected[0].evidence_key == '5c36088224972a4448398e223180b698796d450a5eeffa3dcc02bc9e85478365'
    assert len(full_reads) < 80  # repeated content reads are pure per-pass work


@pytest.mark.parametrize('change', ['raw', 'costmap', 'known', 'safe', 'reference',
                                    'physical_motion', 'egress', 'bounds', 'scope',
                                    'path_validation', 'cost_known', 'generation',
                                    'body_expired', 'egress_expired', 'clearance'])
def test_change_during_actual_route_rejects_whole_selection_and_releases_group(monkeypatch, change):
    node, inputs, policy = frozen('ap06_b13_budget_history')
    original = node._metric_standard_waypoints_clear
    changed = []
    def checked(*args, **kwargs):
        result = original(*args, **kwargs)
        if not changed:
            changed.append(True)
            if change == 'raw':
                inputs[0].data[0] = 100 if inputs[0].data[0] != 100 else 0
            elif change == 'costmap':
                inputs[5].data[0] = 100 if inputs[5].data[0] != 100 else 0
            elif change == 'known':
                inputs[3][0, 0] = not inputs[3][0, 0]
            elif change == 'safe':
                inputs[4][0, 0] = not inputs[4][0, 0]
            elif change == 'cost_known':
                inputs[6][0, 0] = not inputs[6][0, 0]
            elif change == 'reference':
                inputs.map_odom_reference = (1., 0., 0.)
            elif change == 'physical_motion':
                inputs.physical_motion = ((1., 0., 0.), 1.)
            elif change == 'egress':
                node._metric_egress[0].valid = False
                node._metric_egress[0].reason = 'changed_during_route'
            elif change == 'generation':
                node._metric_egress[0].generation += 1
            elif change == 'body_expired':
                node._metric_body_anchor_expired = True
            elif change == 'egress_expired':
                node._metric_egress_expired = True
            elif change == 'clearance':
                node._goal_clearance_m += .01
            elif change == 'scope':
                node._metric_scope = replace(node._metric_scope, scope_id='changed-during-route')
            elif change == 'path_validation':
                node._metric_path_validation = 'conservative'
            else:
                node._metric_bounds = (-.13, .33, -.26, .26)
        return result
    monkeypatch.setattr(node, '_metric_standard_waypoints_clear', checked)
    with pytest.raises(ValueError, match='frontier_evidence_changed_during_processing'):
        node._metric_select(inputs, policy, .3)
    assert changed
    assert node._metric_selection_cache.memo is None
    assert getattr(node._metric_selection_cache, 'route_proof_group', None) is None


def test_actual_selection_exception_releases_binding_before_new_pass(monkeypatch):
    node, inputs, policy = frozen('ap06_b13_budget_history')
    actual = node._metric_standard_waypoints_clear
    def interrupted(*args, **kwargs):
        actual(*args, **kwargs)
        assert node._metric_selection_cache.route_proof_group is not None
        raise ValueError('interrupted_pure_proposal')
    monkeypatch.setattr(node, '_metric_standard_waypoints_clear', interrupted)
    with pytest.raises(ValueError, match='interrupted_pure_proposal'):
        node._metric_select(inputs, policy, .3)
    assert node._metric_selection_cache.memo is None
    assert node._metric_selection_cache.route_proof_group is None
    monkeypatch.setattr(node, '_metric_standard_waypoints_clear', actual)
    selected = node._metric_select(inputs, policy, .3)
    assert len(selected) == 1 and len(selected[0].observation_points) == 90
    assert selected[0].evidence_key == '5c36088224972a4448398e223180b698796d450a5eeffa3dcc02bc9e85478365'
