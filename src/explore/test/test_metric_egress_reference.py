"""AP-06: fresh raster proof against the same first physical inventory."""
import copy
import math
import numpy as np
import pytest
from dataclasses import replace

from test_metric_frontier import egress_fixture
from test_metric_start_observation import fixture as native_fixture


def referenced_fixture(native=False):
    node, inputs = native_fixture()[:2] if native else egress_fixture()
    node._metric_egress = None
    node._metric_body_anchor_expired = False
    node._metric_input_reference = (0., 0., 0.)
    node._metric_prepare_egress(inputs)
    return node, inputs


def shift(node, inputs, dx, dy=0., travel=.05, growth=False, yaw=0.):
    inputs = list(inputs)
    old = (inputs[0], inputs[5])
    for index, mask_index in ((0, 3), (5, 6)):
        g = copy.deepcopy(inputs[index])
        o = g.info.origin.position
        o.x, o.y = dx+math.cos(yaw)*o.x-math.sin(yaw)*o.y, dy+math.sin(yaw)*o.x+math.cos(yaw)*o.y
        g.info.origin.orientation.z, g.info.origin.orientation.w = math.sin(yaw/2), math.cos(yaw/2)
        if growth:
            a = np.asarray(g.data).reshape(g.info.height, g.info.width)
            g.info.height += 1
            g.data = np.pad(a, ((0, 1), (0, 0)), constant_values=-1).ravel().tolist()
            inputs[mask_index] = np.pad(inputs[mask_index], ((0, 1), (0, 0)), constant_values=False)
            if index == 0:
                inputs[4] = np.pad(inputs[4], ((0, 1), (0, 0)), constant_values=False)
        inputs[index] = g
    node._metric_raster_transition(old[0], inputs[0], raw=True)
    node._metric_raster_transition(old[1], inputs[5])
    x, y, angle = inputs[2]
    inputs[2] = (dx+math.cos(yaw)*(x+travel)-math.sin(yaw)*y,
                 dy+math.sin(yaw)*(x+travel)+math.cos(yaw)*y, angle+yaw)
    node._metric_input_reference = (dx, dy, yaw)
    node._metric_prepare_egress(inputs)
    return inputs


@pytest.mark.parametrize('dx,dy,yaw,growth', [(-.00198534484739743,-.00006557910150495,0.,False),
    (.11,-.07,0.,True), (.12,-.08,.03,True)])
def test_native_measured_start_survives_rigid_slam_correction_with_fresh_proof(dx,dy,yaw,growth):
    node, inputs = referenced_fixture(native=True)
    inventory = node._metric_egress
    before = copy.deepcopy(inputs[0].data)
    inputs = shift(node, inputs, dx, dy, yaw=yaw, growth=growth)
    assert node._metric_egress is inventory and not node._metric_egress_expired
    assert all(e.valid for e in inventory)
    target = (dx+math.cos(yaw)*.39, dy+math.sin(yaw)*.39)
    assert node._metric_waypoints_clear(inputs, (inputs[2][:2], target), yaw) is not None
    assert before == inputs[0].data[:len(before)]


def test_slam_correction_does_not_erase_departure_or_allow_physical_reentry():
    node, inputs = referenced_fixture()
    inputs[2] = (.15,.05,0.)
    node._metric_prepare_egress(inputs)
    committed = dict(node._metric_egress[0].remaining_area)
    updated = shift(node, inputs, .002, travel=0.)
    assert all(e.valid for e in node._metric_egress)
    assert node._metric_egress[0].remaining_area == pytest.approx(committed)
    updated[2] = (.052,.05,0.)
    node._metric_prepare_egress(updated)
    assert not node._metric_egress[0].valid
    assert node._metric_egress[0].reason == 'start_egress_reentry_or_added_cell_area'


@pytest.mark.parametrize('value', [-1, 100])
def test_new_unknown_or_occupied_departure_cell_is_never_added_after_correction(value):
    node, inputs = referenced_fixture()
    updated = shift(node, inputs, .002)
    # A fully observed endpoint makes this a departure-sweep regression,
    # independent of which order the endpoint and route guards run in.
    a = np.asarray(updated[0].data).reshape(updated[3].shape).copy()
    a[:,25:30] = 0
    updated[0].data = a.ravel().tolist()
    updated[3][:,25:30] = True
    route = (updated[2][:2], (1.202,.05))
    assert node._metric_waypoints_clear(updated,route) is not None
    row, col = 20, 15
    a[row,col] = value
    updated[0].data = a.ravel().tolist()
    updated[3][row,col] = False
    assert node._metric_waypoints_clear(updated,route) is None
    assert not node._metric_egress_expired
    assert node._metric_last_route_rejection == 'start_egress_new_unknown_or_obstacle'


def test_observation_cannot_regrow_as_unknown_on_a_later_slam_raster():
    node, inputs = referenced_fixture()
    a = np.asarray(inputs[0].data).reshape(inputs[3].shape).copy()
    a[18:23,8] = 0
    inputs[0].data = a.ravel().tolist()
    inputs[3][18:23,8] = True
    node._metric_prepare_egress(inputs)
    assert not node._metric_egress[0].unknown.any()
    a[18:23,8] = -1
    inputs[0].data = a.ravel().tolist()
    inputs[3][18:23,8] = False
    updated = shift(node, inputs, .002, travel=0.)
    assert not node._metric_egress[0].unknown.any()
    assert not node._metric_egress[0].valid


@pytest.mark.parametrize('change', ['resolution', 'session', 'frame'])
def test_incompatible_context_still_permanently_expires_reference(change):
    node, inputs = referenced_fixture()
    old = copy.deepcopy(inputs[0])
    if change == 'resolution':
        inputs[0].info.resolution = .11
    elif change == 'frame':
        inputs[0].header.frame_id = 'foreign'
    else:
        inputs[1] = replace(inputs[1], context=replace(inputs[1].context, session_id='foreign'))
    node._metric_raster_transition(old, inputs[0], raw=True)
    node._metric_prepare_egress(inputs)
    assert node._metric_egress_expired and not node._metric_egress[0].valid


def test_subcell_resampling_cannot_expand_inventory_into_previously_free_area():
    node, inputs = referenced_fixture()
    original = node._metric_egress[0]
    updated = shift(node, inputs, .001, travel=0.)
    # Change only the raster origin relative to odometry. These new unknown
    # squares straddle initial free space: a nearest-cell copy would widen it.
    node._metric_input_reference = (0.,0.,0.)
    node._metric_prepare_egress(updated)
    assert node._metric_egress[0] is original
    assert not original.unknown.any()
    assert not original.valid


def test_lost_reference_never_falls_back_to_old_projection():
    node, inputs = referenced_fixture()
    node._metric_input_reference = None
    node._metric_body_reference = lambda: None
    node._metric_prepare_egress(inputs)
    assert node._metric_egress_expired and not node._metric_egress[0].valid


def test_another_input_read_cannot_replace_the_pose_correlated_reference():
    from explore.metric_frontier_runtime import MetricInputs
    node, inputs = referenced_fixture()
    frozen = MetricInputs(inputs, (0.,0.,0.))
    node._metric_input_reference = (.2,0.,0.)  # a concurrent/newer snapshot
    node._metric_prepare_egress(frozen)
    assert all(e.valid for e in node._metric_egress)
    assert node._metric_egress[0].current_reference == (0.,0.,0.)


def test_reference_projection_work_does_not_extend_original_source_freshness(monkeypatch):
    import explore.metric_frontier_runtime as module
    from test_metric_map_lifecycle import runtime
    node, _ = runtime(monkeypatch)
    clock = [10.02]
    monkeypatch.setattr(module.time, 'monotonic', lambda: clock[0])
    prepare = node._metric_prepare_egress
    def delayed(inputs):
        prepare(inputs)
        clock[0] = 15.01
    node._metric_prepare_egress = delayed
    with pytest.raises(ValueError, match='stale_after_processing'):
        node._metric_inputs()


def test_invalid_departure_history_stays_invalid_when_raster_later_grows():
    node, inputs = referenced_fixture()
    inputs[2] = (.15,.05,0.)
    node._metric_prepare_egress(inputs)
    inputs[2] = (.05,.05,0.)
    node._metric_prepare_egress(inputs)
    assert not node._metric_egress[0].valid
    updated = shift(node, inputs, .002, travel=0., growth=True)
    assert not node._metric_egress[0].valid
    assert node._metric_egress[0].unknown.shape == updated[3].shape
    assert not node._metric_egress[0].unknown.any()
    assert np.array_equal(node._metric_seed_mask(updated), updated[4])
