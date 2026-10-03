"""The escape proof follows the actual first Nav2 leg and arrival heading."""
import math
import numpy as np
from test_metric_frontier import egress_fixture


def fixture():
    node, inputs = egress_fixture()
    node._metric_path_validation = 'rpp_rollout'
    node._prealign_handoff_tolerance = .02
    # Newly observed forward room, while the reserved original rear stays unknown.
    raw = np.asarray(inputs[0].data).reshape(inputs[3].shape).copy()
    raw[1:-1, 25:40] = 0
    inputs[0].data = raw.ravel().tolist()
    inputs[3][1:-1, 25:40] = True
    return node, inputs


def test_straight_escape_then_later_turn_uses_actual_first_leg():
    node, inputs = fixture()
    route = (inputs[2][:2], (1.3, .05), (2., .75))
    assert node._metric_waypoints_clear(inputs, route, math.pi/4) is not None
    assert not inputs[3][20, 8]  # no whitening of the original unknown inventory


def test_turn_before_abandoning_rear_inventory_remains_rejected():
    node, inputs = fixture()
    route = (inputs[2][:2], (.15, .05), (.15, .75))
    assert node._metric_waypoints_clear(inputs, route, math.pi/2) is None
    assert node._metric_last_route_rejection == 'start_egress_in_place_turn'
