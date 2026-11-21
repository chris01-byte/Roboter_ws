"""An endpoint check must not replay the unexempted start, AP-06 counterexample."""
from explore.metric_frontier import footprint_clear
from test_metric_frontier import egress_fixture


def fixture():
    node, inputs = egress_fixture()
    node._metric_path_validation = 'rpp_rollout'
    node._prealign_handoff_tolerance = .02
    return node, inputs


def test_known_endpoint_and_checked_escape_do_not_require_start_unknown_free():
    node, inputs = fixture()
    target = (.75, .05)
    # The start remains genuinely unknown in part of its reserved rear contour.
    assert not footprint_clear(*inputs[2], inputs[0], inputs[3], node._world_to_grid,
        node._grid_to_world, node._metric_bounds, heading_half_angle=.05, center_deviation_m=.02)
    # A one-point route checks only this actual endpoint; it commands no motion.
    assert node._metric_standard_waypoints_clear(inputs, (target,), 0.) is not None
    # Unexempted travel still rejects the start; the coupled inventory proof is required.
    assert node._metric_standard_waypoints_clear(inputs, (inputs[2][:2], target), 0.) is None
    assert node._metric_waypoints_clear(inputs, (inputs[2][:2], target), 0.) is not None


def test_endpoint_obstacle_and_rotation_into_unknown_remain_rejected():
    node, inputs = fixture()
    target = (.75, .05)
    assert node._metric_waypoints_clear(inputs, (inputs[2][:2], target), 0.) is not None
    inputs[3][:, 20] = False
    assert node._metric_standard_waypoints_clear(inputs, (target,), 0.) is None
    assert node._metric_waypoints_clear(inputs, (inputs[2][:2], target), 0.) is None
    assert node._metric_waypoints_clear(inputs, (inputs[2][:2], (.05, .75)), 0.) is None
