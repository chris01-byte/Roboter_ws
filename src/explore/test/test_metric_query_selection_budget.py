"""A valid read-only query must reach its planner before needless extra work."""
import math
from pathlib import Path
import numpy as np

from explore.metric_frontier import MetricTaskPolicy
from explore.metric_frontier_candidates import LidarView
from explore.metric_frontier_candidates import boundary_samples
from test_metric_departure import fixture


def test_live_selection_returns_first_eligible_query_within_original_deadline(monkeypatch):
    # C36 later stopped pose/rasters, with recorded C38 finite angular
    # coverage as a component input (not a C36 observation receipt).
    node, inputs, _ = fixture('ap06_c36_selection')
    arrays = np.load(Path(__file__).parent/'data/ap06_c36_selection.npz')
    node._metric_observation_view = lambda: LidarView(
        (.245, 0., math.pi/2), arrays['angles'], 4., .05)
    node._metric_candidate_source = 'boundary_samples'
    node._metric_start_egress_enabled = True
    node._metric_egress_expired = True  # ordinary public geometry, no recapture
    node._metric_egress = None
    node._metric_prepare_egress = type(node)._metric_prepare_egress.__get__(node)
    # Candidate input order is variable; all samples still come from the
    # actual detector on these raw rasters. Put its eligible query first to
    # expose needless processing of the remaining real rejected samples.
    monkeypatch.setattr('explore.metric_frontier_runtime.boundary_samples',
        lambda *a, **kw: list(reversed(boundary_samples(*a, **kw))))
    began = node._global_costmap_received_at
    clock = [began]
    monkeypatch.setattr('explore.metric_frontier_runtime.time.monotonic', lambda: clock[0])
    proposal = node._metric_nav2_proposal
    approach = node._frontier_approach_goal
    ready = [False]
    def timed_proposal(*args, **kwargs):
        result = proposal(*args, **kwargs)
        if result is not None and not ready[0]:
            # Synthetic processing clock only; the actual proposal decision
            # and all contour/scope/sight/reachability checks run unchanged.
            ready[0] = True; clock[0] = began+4.9
        return result
    def timed_approach(*args, **kwargs):
        result = approach(*args, **kwargs)
        if ready[0]:
            clock[0] += .2
        return result
    node._metric_nav2_proposal = timed_proposal
    node._frontier_approach_goal = timed_approach
    before = [list(inputs[i].data) for i in (0, 5)]
    candidates = node._metric_select(inputs, MetricTaskPolicy(.6, 30., 2), .3)
    assert len(candidates) == 1 and candidates[0].requires_nav2_plan
    assert candidates[0].observation_points
    assert clock[0]-began < node._map_timeout_s == 5.
    assert [list(inputs[i].data) for i in (0, 5)] == before
