"""Selection reuse retains real escape geometry and invalidates changed proof."""
import pytest
from explore.metric_frontier import StartEgressEvidence
from test_metric_frontier import egress_fixture


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
