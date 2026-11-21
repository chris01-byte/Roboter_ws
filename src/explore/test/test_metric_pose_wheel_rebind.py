"""New actual wheel/TF pair cannot retain a body mask for an older pose."""
import time
import math

import numpy as np
import pytest
from nav_msgs.msg import OccupancyGrid

from explore.metric_frontier_runtime import MetricInputs
from explore.metric_frontier import self_body_unknown_mask
from test_metric_tf_receipt import actual_pair


@pytest.mark.parametrize('body_expired', [False, True])
def test_actual_new_pair_withdraws_departed_initial_cells_without_reanchoring(actual_pair, body_expired):
    node, consumer, executor, halt, worker, sent = actual_pair
    g = OccupancyGrid()
    g.info.width, g.info.height, g.info.resolution = 200, 100, .01
    g.info.origin.position.x, g.info.origin.position.y = -1., -.5
    g.info.origin.orientation.w = 1.
    pose, age, reference = node._metric_pose_and_reference()
    motion = node._metric_measured_motion(pose, reference)
    mount = (.245,0.,math.pi/2)
    unknown = self_body_unknown_mask(g, -np.ones((100,200), int), pose, mount)
    assert unknown.any()
    occupancy = np.zeros((100,200), int)
    occupancy[unknown] = -1
    g.data = occupancy.ravel().tolist()
    known = np.ones((100,200), bool)
    safe = known.copy()
    inputs = MetricInputs((g,None,pose,known,safe,g,occupancy>=0),reference,motion)
    initial = unknown.copy()
    node._metric_self_body_enabled = True
    node._metric_body_anchor_expired = body_expired
    node._metric_body_cells = initial.copy()
    # Marker represents the immutable original fact; refresh must not replace it.
    node._metric_body_anchor = ('original', pose)
    original_anchor = node._metric_body_anchor
    node._goal_clearance_m = .01
    subscriptions = tuple(consumer.subscriptions)
    time.sleep(.3)
    halt.set()
    worker.join(1.)
    with pytest.raises(ValueError, match='start_motion_wheel_tf_disagreement'):
        node._metric_measured_motion(pose, reference)
    refreshed, checked, new_age = node._metric_rebind_motion_geometry(inputs,occupancy,mount)
    assert refreshed[2][0] > pose[0]+.02
    assert refreshed[2] == pytest.approx(refreshed.physical_motion[0])
    assert refreshed.physical_motion[3] > motion[3]
    assert 0 <= new_age < .5
    assert checked <= time.monotonic()
    assert node._metric_body_anchor is original_anchor
    assert node._metric_body_anchor_expired == body_expired
    assert np.all(refreshed[3] <= known) and np.all(refreshed[4] <= safe)
    assert np.any(known & ~refreshed[3])
    if body_expired:
        assert not np.any(refreshed[3] & unknown)
    else:
        assert np.all(node._metric_body_cells <= initial)
        assert np.any(initial & ~node._metric_body_cells)
        assert np.array_equal(refreshed[3] & unknown,node._metric_body_cells)
    assert tuple(consumer.subscriptions) == subscriptions
    assert refreshed[0] is g and refreshed[5] is g
    # The input stamp/content/epoch is retained; only permission is withdrawn.
    assert np.array_equal(np.asarray(g.data).reshape(occupancy.shape),occupancy)


def test_actual_new_wheel_is_selected_after_body_withdrawal(actual_pair, monkeypatch):
    """Actual DDS wheel/TF receipts, with slow pure withdrawal arithmetic."""
    node, _, _, _, _, _ = actual_pair
    import explore.metric_frontier_runtime as runtime
    g = OccupancyGrid()
    g.info.width, g.info.height, g.info.resolution = 200, 100, .01
    g.info.origin.position.x, g.info.origin.position.y = -1., -.5
    g.info.origin.orientation.w = 1.
    pose, _, reference = node._metric_pose_and_reference()
    old = node._metric_measured_motion(pose, reference)
    occupancy = np.zeros((100, 200), int)
    known = np.ones(occupancy.shape, bool)
    node._metric_self_body_enabled = True
    node._metric_body_anchor_expired = False
    node._metric_body_cells = self_body_unknown_mask(g, -np.ones_like(occupancy), pose,
                                                    (.245, 0., math.pi/2))
    original = runtime.self_body_unknown_mask
    entered = []
    def slow_withdrawal(*args):
        entered.append(time.time())
        time.sleep(.10)
        return original(*args)
    monkeypatch.setattr(runtime, 'self_body_unknown_mask', slow_withdrawal)
    inputs = MetricInputs((g, None, pose, known, known.copy(), g, known), reference, old)
    time.sleep(.05)  # both orders have a genuinely newer receipt available
    refreshed, _, _ = node._metric_rebind_motion_geometry(inputs, occupancy, (.245, 0., math.pi/2))
    assert len(entered) == 1
    # Same real TF pair and unchanged agreement limit, but a later actual
    # wheel receipt. The old order selected it BEFORE the slow withdrawal.
    assert refreshed.physical_motion[3] > entered[0]+.04
    assert refreshed.physical_motion[3] > old[3]
    assert time.monotonic()-refreshed.physical_motion[2] < .18
    assert np.all(refreshed[3] <= known) and np.all(refreshed[4] <= known)
