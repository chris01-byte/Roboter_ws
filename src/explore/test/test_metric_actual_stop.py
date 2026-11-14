"""C119 public terminal geometry; no live health or mission acceptance claim."""
import json
import math
from pathlib import Path

import pytest
from geometry_msgs.msg import PoseStamped
from nav_msgs.msg import Path as NavPath
from explore.metric_frontier import MetricCandidate, footprint_poses_clear
from test_metric_public_cooldown import frozen

NAME = 'ap06_c119_terminal_native_stop'


def actual():
    node, inputs, policy = frozen(NAME)
    meta = json.loads((Path(__file__).parent/'data'/NAME).with_suffix('.json').read_text())
    c = meta['expected_candidate']
    candidate = MetricCandidate(c['task'], *c['goal'], tuple(c['frontier']), (), 1., 0.,
                               inputs[1].fingerprint, inputs[1].map_revision, True)
    planned = meta['native_plans'][0]
    assert not planned['error'] and not c['points']
    path = NavPath(); path.header.frame_id = 'map'
    for x, y in planned['points']:
        pose = PoseStamped(); pose.header.frame_id = 'map'
        pose.pose.position.x = x; pose.pose.position.y = y; pose.pose.orientation.w = 1.
        path.poses.append(pose)
    return node, inputs, policy, candidate, path


def test_native_stops_before_unvisited_ideal_body_and_retains_full_scan_reserve():
    n, inputs, policy, c, path = actual()
    assert not footprint_poses_clear([(c.x, c.y, c.yaw)], inputs[0], inputs[3],
        n._world_to_grid, n._metric_bounds, heading_half_angle=.05, center_deviation_m=.02)
    route = n._metric_validate_nav_plan(inputs, path, c, public_only=True)
    assert route is not None
    stop = n._metric_rollout_stop_pose(inputs, route, c.yaw, native_plan=True)
    assert 0.14 < math.dist(stop[:2], (c.x, c.y)) <= .15
    assert n._metric_scan_geometry_ready((inputs[0], inputs[1], stop, *inputs[3:]))
    # The saved policy is never rewritten to approve this counterexample.
    assert policy.attempts['metric-task-1'].failures == 1
    assert policy.attempts['metric-task-2'].tries == 3
    assert n._metric_nav2_proposal(inputs, (c.x, c.y), c.yaw) is None
    assert n._metric_nav2_proposal(inputs, (c.x, c.y), c.yaw, native_stop=True) is not None
    assert n._metric_waypoints_clear(inputs, ((c.x, c.y),), c.yaw) is None
    n._metric_path_validation = 'conservative'
    assert n._metric_validate_nav_plan(inputs, path, c, public_only=True) is None


@pytest.mark.parametrize('source', [3, 6])
def test_actual_swept_body_unknown_remains_forbidden(source):
    n, inputs, _, c, path = actual()
    col, row = n._world_to_grid(1.8, .2, inputs[0 if source == 3 else 5].info)
    inputs[source][row, col] = False
    assert n._metric_validate_nav_plan(inputs, path, c, public_only=True) is None


def test_readonly_endpoint_center_must_be_known_in_current_costmap():
    n, inputs, _, c, _ = actual()
    col, row = n._world_to_grid(c.x, c.y, inputs[5].info)
    inputs[6][row, col] = False
    assert n._metric_nav2_proposal(inputs, (c.x, c.y), c.yaw, native_stop=True) is None
