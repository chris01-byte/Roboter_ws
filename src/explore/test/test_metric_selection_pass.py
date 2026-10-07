"""Selection reuse retains real escape geometry and invalidates changed proof."""
import pytest
import threading
import numpy as np
from explore.metric_frontier import StartEgressEvidence
from test_metric_frontier import egress_fixture
from explore.metric_progress import local_evidence


@pytest.mark.parametrize('change', ['raw', 'origin', 'mask', 'new_pass'])
def test_local_policy_evidence_reuse_requires_unchanged_current_selection(monkeypatch, change):
    node, inputs = egress_fixture()
    node._metric_selection_cache = threading.local()
    node._metric_selection_cache.memo = {'inputs': inputs}
    anchor = inputs[2][:2]
    reads = []
    def measured(*args, **kwargs):
        reads.append(True)
        return local_evidence(*args, **kwargs)
    monkeypatch.setattr('explore.metric_frontier_runtime.local_evidence', measured)
    original = node._metric_local_evidence(inputs, anchor)
    assert original == node._metric_local_evidence(inputs, anchor)
    assert len(reads) == 1
    if change == 'raw':
        col, row = node._world_to_grid(*anchor, inputs[0].info)
        inputs[0].data[row*inputs[0].info.width+col] = 100
    elif change == 'origin':
        inputs[0].info.origin.position.x += .01
    elif change == 'mask':
        inputs[3][0, 0] = not inputs[3][0, 0]
    else:
        node._metric_selection_cache.memo = {'inputs': inputs}
    current = node._metric_local_evidence(inputs, anchor)
    assert current == local_evidence(inputs[0], anchor, node._grid_to_world)
    assert len(reads) == 2
    if change in ('raw', 'origin'):
        assert current != original
    # Outside a selection pass, no receipt/health or digest survives.
    node._metric_selection_cache.memo = None
    assert node._metric_local_evidence(inputs, anchor) == current
    assert len(reads) == 3


def test_many_candidate_routes_commit_same_stationary_inventory_once_per_pass(monkeypatch):
    node, inputs = egress_fixture()
    original = StartEgressEvidence.check_trajectory
    commits = []
    def checked(self, *args, **kwargs):
        if kwargs.get('commit'):
            commits.append(self)
        return original(self, *args, **kwargs)
    monkeypatch.setattr(StartEgressEvidence, 'check_trajectory', checked)
    first = node._metric_candidates(inputs, .3)
    assert first
    assert len(commits) == 2  # raw and actual costmap inventory
    second = node._metric_candidates(inputs, .3)
    assert second == first
    assert len(commits) == 4  # a new pass always evaluates current evidence
    assert node._metric_selection_cache.memo is None


def test_reference_invalidation_during_selection_cannot_reuse_healthy_inventory(monkeypatch):
    node, inputs = egress_fixture()
    approach = node._frontier_approach_goal
    def changed(*args, **kwargs):
        goal = approach(*args, **kwargs)
        node._metric_egress[0].valid = False
        node._metric_egress[0].reason = 'reference_changed_during_pass'
        return goal
    monkeypatch.setattr(node, '_frontier_approach_goal', changed)
    with pytest.raises(ValueError, match='frontier_evidence_changed_during_processing'):
        node._metric_candidates(inputs, .3)
    assert node._metric_selection_cache.memo is None


def test_new_obstacle_on_same_mutable_grid_rejects_previously_safe_candidates():
    node, inputs = egress_fixture()
    assert node._metric_candidates(inputs, .3)
    # Same message and mask objects, new obstacle across the entire route.
    grid, known, safe = inputs[0], inputs[3], inputs[4]
    for row in range(grid.info.height):
        grid.data[row*grid.info.width+12] = 100
    known[:, 12] = False
    safe[:, 12] = False
    assert not node._metric_candidates(inputs, .3)


def test_cached_start_connections_match_uncached_targets_and_reject_new_wall(monkeypatch):
    node, inputs = egress_fixture()
    col, row = node._world_to_grid(*inputs[2][:2], inputs[5].info)
    # High inflated start cost disallows a centre seed, while remaining
    # nonlethal in the actual full-contour check.
    inputs[5].data[row*inputs[5].info.width+col] = 91
    targets = ((.75, .35), (.85, .4))
    expected = [node._metric_route(inputs, target) for target in targets]
    node._metric_selection_cache = threading.local()
    node._metric_selection_cache.memo = {'inputs': inputs}
    calls = []
    original = node._metric_grid_line_clear
    def checked(*args):
        if np.array_equal(args[0], inputs[3] | node._metric_egress[0].unknown):
            calls.append(1)
        return original(*args)
    monkeypatch.setattr(node, '_metric_grid_line_clear', checked)
    first = node._metric_route(inputs, targets[0])
    count = len(calls)
    assert count > 0
    second = node._metric_route(inputs, targets[1])
    assert (first, second) == tuple(expected)
    assert len(calls) == count
    # Even within the same pass, a new wall invalidates all saved connections.
    for row in range(inputs[0].info.height):
        inputs[0].data[row*inputs[0].info.width+12] = 100
    inputs[3][:, 12] = False
    inputs[4][:, 12] = False
    assert node._metric_route(inputs, targets[0]) is None
