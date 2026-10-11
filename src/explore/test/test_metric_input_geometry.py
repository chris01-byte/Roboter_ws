"""Pure geometry reuse must preserve cells and every current input rejection."""
import copy
import math
from dataclasses import replace

import numpy as np
import pytest

from explore.metric_frontier import self_body_unknown_mask, known_safe_mask
from test_metric_frontier import grid, adaptive_fixture
from test_metric_map_lifecycle import runtime


def full_body_oracle(g, occupancy, pose):
    """Original complete raster arithmetic, independent of the cropped window."""
    rows, cols = np.indices(occupancy.shape)
    q = g.info.origin.orientation
    yaw = math.atan2(2*(q.w*q.z+q.x*q.y), 1-2*(q.y*q.y+q.z*q.z))
    res = g.info.resolution
    lx, ly = (cols+.5)*res, (rows+.5)*res
    dx = g.info.origin.position.x+math.cos(yaw)*lx-math.sin(yaw)*ly-pose[0]
    dy = g.info.origin.position.y+math.sin(yaw)*lx+math.cos(yaw)*ly-pose[1]
    x = math.cos(pose[2])*dx+math.sin(pose[2])*dy
    y = -math.sin(pose[2])*dx+math.cos(pose[2])*dy
    reserve = res/2*(abs(math.cos(yaw-pose[2]))+abs(math.sin(yaw-pose[2])))
    return ((occupancy < 0) & (-.11+reserve <= x) & (x <= .31-reserve)
            & (abs(y) <= .23-reserve))


@pytest.mark.parametrize('resolution', [.005, .01, .1, 1.])
@pytest.mark.parametrize('grid_yaw', [0., .03, math.pi/2])
def test_cropped_body_is_bit_identical_at_boundaries_and_rotated_rasters(resolution, grid_yaw):
    g = grid(); g.info.width, g.info.height = 563, 283
    g.info.resolution = resolution
    g.info.origin.orientation.z, g.info.origin.orientation.w = math.sin(grid_yaw/2), math.cos(grid_yaw/2)
    rng = np.random.default_rng(601)
    a = rng.choice([-1, 0, 100], size=(283, 563))
    points = [(0., 0.), (-1., -2.), (563*resolution-1., 283*resolution-2.),
              (100., -100.), (.31, .23), (.31+1e-12, .23-1e-12)]
    for x, y in points:
        for heading in (0., .17, math.pi/2, -math.pi):
            pose = (x, y, heading)
            actual = self_body_unknown_mask(g, a, pose, (.245, 0., math.pi/2))
            np.testing.assert_array_equal(actual, full_body_oracle(g, a, pose))


@pytest.mark.parametrize('change', ['cells', 'body', 'scope', 'context', 'origin', 'yaw', 'resolution', 'clearance'])
def test_known_geometry_reuse_withdraws_changes_and_never_reuses_mutated_output(change):
    n, inputs = adaptive_fixture()
    g, correlation = inputs[:2]
    a = np.asarray(g.data).reshape(40, 80).copy()
    scope, origin, yaw, res, body = n._metric_scope, (-1., -2.), 0., .1, np.zeros(a.shape, bool)
    before = n._metric_known_geometry(a, scope, correlation, origin, yaw, res, body)
    cache = n._metric_known_geometry_cache
    before[0][:] = before[1][:] = False  # caller mutation cannot alter the entry
    repeat = n._metric_known_geometry(a, scope, correlation, origin, yaw, res, body)
    assert n._metric_known_geometry_cache is cache and repeat[0].any()
    if change == 'cells': a[20, 10] = 100
    if change == 'body': a[20, 10] = -1; body[20, 10] = True
    if change == 'scope': scope = replace(scope, scope_id='changed')
    if change == 'context':
        correlation = replace(correlation, context=replace(correlation.context, session_id='new'))
        scope = replace(scope, context=correlation.context)
    if change == 'origin': origin = (-.9, -2.)
    if change == 'yaw': yaw = .03
    if change == 'resolution': res = .09
    if change == 'clearance': n._goal_clearance_m += .1
    actual = n._metric_known_geometry(a, scope, correlation, origin, yaw, res, body)
    expected = known_safe_mask(a, scope, correlation, origin, yaw, res, n._goal_clearance_m, body)
    assert n._metric_known_geometry_cache is not cache
    for x, y in zip(actual, expected): np.testing.assert_array_equal(x, y)


@pytest.mark.parametrize('fault', ['map', 'costmap', 'pose', 'scan', 'epoch'])
def test_geometry_hit_never_hides_real_input_age_or_context_failure(monkeypatch, fault):
    n, _ = runtime(monkeypatch)
    n._metric_inputs()  # same pure geometry is now reusable
    if fault == 'map': n._metric_raw = (*n._metric_raw[:2], 4.)
    if fault == 'costmap': n._global_costmap_received_at = 4.
    if fault == 'pose': n._robot_pose_sample = lambda: ((.05, .05, 0.), 2.)
    if fault == 'scan': n._door_lidar_scan_snapshot = lambda: dict(received_at=9., frame_id='laser_frame')
    if fault == 'epoch': n._metric_fault = 'map_epoch_changed'
    with pytest.raises(ValueError): n._metric_inputs()
