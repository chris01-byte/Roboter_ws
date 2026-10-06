"""Measured native start pocket: no hidden Nav2 goals or free-space changes."""
import copy
import importlib.util
import json
import math
from pathlib import Path
from types import SimpleNamespace
import time
from dataclasses import replace
import numpy as np
import pytest
from test_metric_frontier import adaptive_fixture
from explore.metric_frontier import known_safe_mask
from explore.exploration_scope import AuthorizedExplorationScope
from explore.portal_memory import Point2D
from explore.portal_source_adapter import raw_map_portal_source_from_values


def fixture():
    root = Path(__file__).resolve().parents[3]
    data = Path(__file__).parent/'data'
    arrays = np.load(data/'ap06_start_c.npz')
    metadata = json.loads((data/'ap06_start_c.json').read_text())
    node, inputs = adaptive_fixture()
    for index, field, geometry in ((0,'raw',metadata['raw_geometry']), (5,'cost',metadata['cost_geometry'])):
        g = inputs[index]; a = arrays[field]
        g.info.height, g.info.width = a.shape
        g.info.resolution = geometry['resolution']
        g.info.origin.position.x, g.info.origin.position.y = geometry['origin']
        g.data = a.ravel().tolist()
    source = raw_map_portal_source_from_values(**node._metric_grid_values(inputs[0]))
    inputs[1] = replace(inputs[1],fingerprint=source.fingerprint)
    node._metric_scope = AuthorizedExplorationScope('scope',inputs[1].context,
        tuple(Point2D(x,y) for x,y in ((-1.2,-1.4),(4.4,-1.4),(4.4,1.4),(-1.2,1.4))))
    inputs[2] = tuple(metadata['pose'])
    raw = arrays['raw']; body = (raw<0)&arrays['known']
    known,safe = known_safe_mask(raw,node._metric_scope,inputs[1],
        tuple(metadata['raw_geometry']['origin']),0.,inputs[0].info.resolution,.28,body)
    assert np.array_equal(known,arrays['known'])
    inputs[3] = known; inputs[4] = safe & (arrays['cost']>=0) & (arrays['cost']<=90)
    inputs[6] = (arrays['cost']>=0)&(arrays['cost']<100)
    node._global_costmap = inputs[5]
    node._metric_start_egress_enabled = True
    node._metric_egress = None; node._metric_egress_expired = False
    node._metric_path_validation = 'rpp_rollout'; node._prealign_handoff_tolerance = .02
    node._metric_candidate_source = 'boundary_samples'
    spec = importlib.util.spec_from_file_location('ap06_world_fixture',root/'tools/simulation/ap06_world.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    angles,ranges = module.World(.8,[-1.6,0.,0.]).laser(beams=2160)
    scan = dict(ranges=ranges,angle_min=float(angles[0]),angle_increment=float(angles[1]),
                range_min=.05,range_max=10.,frame_id='laser',key=(100,0,2160))
    node._door_lidar_scan_snapshot = lambda:dict(scan,received_at=time.monotonic())
    node._door_lidar_mount = lambda _: (.245,0.,math.pi/2)
    node._door_lidar_scan_timeout = .5; node._door_lidar_max_range = 4.
    node.get_clock = lambda:SimpleNamespace(now=lambda:SimpleNamespace(nanoseconds=100*10**9))
    return node,inputs,scan


def test_native_start_has_autonomous_proved_local_observation_without_whitening():
    node,inputs,_ = fixture(); before = copy.deepcopy(inputs[0].data)
    candidates = node._metric_candidates(inputs,.3)
    proved = [c for c in candidates if not c.requires_nav2_plan]
    assert proved, node._frontier_rank_stats
    assert all(c.route_length_m >= node._min_goal_dist_m and c.observation_points for c in proved)
    # Native RPP can stop safely in a narrow observed connection; proposals
    # must still pass the whole actual rollout, with no map changes.
    assert all(node._metric_waypoints_clear(inputs,c.route,c.yaw) for c in proved)
    assert inputs[0].data == before and not inputs[3].all()


def test_new_wall_on_departure_cannot_be_bypassed_by_start_observation():
    node,inputs,_ = fixture(); node._metric_prepare_egress(inputs)
    col,row = node._world_to_grid(.2,0.,inputs[0].info)
    for index in (0,5):
        a = np.asarray(inputs[index].data).reshape(inputs[3].shape).copy()
        a[row,col] = 100; inputs[index].data = a.ravel().tolist()
    inputs[3][row,col] = inputs[4][row,col] = inputs[6][row,col] = False
    candidates = node._metric_candidates(inputs,.3)
    assert not any(not c.requires_nav2_plan for c in candidates)


def test_missing_sensor_sight_cannot_create_start_observation():
    node,inputs,scan = fixture(); scan['ranges'][:] = np.nan
    with pytest.raises(ValueError,match='candidate_lidar_no_valid_rays'):
        node._metric_candidates(inputs,.3)


def ordinary_departure_fixture():
    """Actual second-selection rasters; no raw/cost unknown cells are changed."""
    node, inputs, scan = fixture()
    data = Path(__file__).parent/'data'
    arrays = np.load(data/'ap06_ordinary_departure.npz')
    metadata = json.loads((data/'ap06_ordinary_departure.json').read_text())
    geometries = metadata['geometry']
    for index, field, geometry in ((0, 'raw', geometries[0]), (5, 'cost', geometries[1])):
        grid = inputs[index]
        grid.info.height, grid.info.width = arrays[field].shape
        grid.info.resolution = geometry['resolution']
        grid.info.origin.position.x, grid.info.origin.position.y = geometry['origin']
        grid.data = arrays[field].ravel().tolist()
    source = raw_map_portal_source_from_values(**node._metric_grid_values(inputs[0]))
    inputs[1] = replace(inputs[1], fingerprint=source.fingerprint)
    inputs[2] = tuple(arrays['pose'])
    inputs[3], inputs[4], inputs[6] = (arrays[k].copy() for k in ('known', 'safe', 'cost_known'))
    # Apply the retained FIRST-body facts through the production integer
    # translation helper. The captured pre-fix input had dropped them solely
    # because its width grew by one column. Never recapture the current body.
    first = np.load(data/'ap06_ordinary_departure_initial.npz')
    node._metric_body_cells = (first['raw'] < 0) & first['known']
    g = inputs[0]; origin = (g.info.origin.position.x, g.info.origin.position.y, 0., 0., 0., 0., 1.)
    node._metric_body_grid_identity = (inputs[1].context, first['raw'].shape[1],
        first['raw'].shape[0], g.info.resolution, origin, 0.)
    identity = (inputs[1].context, g.info.width, g.info.height, g.info.resolution, origin, 0.)
    assert node._metric_rebase_first_body(identity)
    node._metric_body_cells &= arrays['raw'] < 0
    inputs[3], inputs[4] = known_safe_mask(arrays['raw'], node._metric_scope, inputs[1],
        origin[:2], 0., g.info.resolution, node._goal_clearance_m, node._metric_body_cells)
    cost_safe = np.zeros_like(inputs[4]); cost_safe[:, :arrays['cost'].shape[1]] = (
        arrays['cost'] >= 0) & (arrays['cost'] <= node._frontier_goal_max_cost)
    inputs[4] &= cost_safe
    node._metric_prepare_egress(inputs)
    # Restore the captured private history state. It grants no movement
    # authority; the original fixed-body facts are separately retained.
    for evidence, history in zip(node._metric_egress, metadata['history']):
        assert history['unknown_cells'] == 0
        evidence.unknown[:] = False  # original inventory retired; never recapture at current pose
        evidence.valid = history['valid']
        evidence.reason = history['reason']
    return node, inputs, scan


def test_retired_private_history_does_not_block_fully_ordinary_forward_observation():
    node, inputs, _ = ordinary_departure_fixture()
    # Exhaustive stateless geometry regression, without live task selection.
    # The separate live-selection test and product retain their 5-s deadline.
    node._map_timeout_s = 30.
    before = [copy.deepcopy(inputs[i].data) for i in (0, 5)]
    candidates = node._metric_candidates(inputs, .3)
    proved = [c for c in candidates if not c.requires_nav2_plan]
    assert proved, node._frontier_rank_stats
    assert all(c.route_length_m >= node._min_goal_dist_m for c in proved)
    for c in proved:
        assert c.observation_points
        assert node._metric_standard_waypoints_clear(inputs, c.route, c.yaw) is not None
    assert [inputs[i].data for i in (0, 5)] == before
    assert all(not e.valid and not e.unknown.any() for e in node._metric_egress)


def test_retired_private_history_grants_no_obstacle_bypass_to_forward_fallback():
    node, inputs, _ = ordinary_departure_fixture()
    col, row = node._world_to_grid(inputs[2][0]+.2, inputs[2][1], inputs[0].info)
    inputs[0].data[row*inputs[0].info.width+col] = 100
    inputs[3][row, col] = inputs[4][row, col] = False
    candidates = node._metric_candidates(inputs, .3)
    assert not any(not c.requires_nav2_plan for c in candidates)


def test_live_task_selection_proves_one_goal_and_looks_past_served_history():
    from explore.metric_frontier import MetricTaskPolicy
    node, inputs, _ = ordinary_departure_fixture()
    policy = MetricTaskPolicy(.6, 30., 2)
    first = node._metric_select(inputs, policy, .3)
    assert first and not first[0].requires_nav2_plan
    assert (node._frontier_rank_stats.get('proof_search_stopped_on_eligible_task')
            or node._frontier_rank_stats.get('bounded_start_observation')
            or node._frontier_rank_stats.get('bounded_public_observation'))
    assert node._metric_standard_waypoints_clear(inputs, first[0].route, first[0].yaw)
    policy.record(first[0], 'observed', time.monotonic(), first[0].fingerprint)
    second = node._metric_select(inputs, policy, .3)
    assert second, node._frontier_rank_stats
    assert all(c.task_id != first[0].task_id for c in second)
    assert all(node._metric_standard_waypoints_clear(inputs, c.route, c.yaw) for c in second)


def test_fixed_body_facts_survive_stationary_mask_withdrawal_but_not_observation():
    from explore.metric_frontier import StartEgressEvidence
    from explore.metric_egress_reference import ReferencedStartEgress
    node, inputs, _ = fixture()
    raw = np.asarray(inputs[0].data).reshape(inputs[3].shape)
    body = (raw < 0) & inputs[3]
    assert body.any()
    evidence = StartEgressEvidence.capture(inputs[0], raw, inputs[3],
        np.ones_like(body), inputs[2], node._metric_bounds, node._world_to_grid)
    assert evidence.valid
    assert (evidence.unknown & body).any()
    evidence = ReferencedStartEgress(evidence, (0., 0., 0.))
    # Withdraw the virtual stationary mask; only the one-shot physical
    # inventory remains, without altering raw measurement or allowed space.
    allowed = inputs[3].copy(); allowed[body] = False
    valid, reason = evidence.check_trajectory([inputs[2]], raw, allowed, node._world_to_grid)
    assert valid, reason
    observed = raw.copy(); observed[body] = 0
    evidence.refresh(inputs[0], observed, np.ones_like(body), (0., 0., 0.))
    evidence.refresh(inputs[0], raw, np.ones_like(body), (0., 0., 0.))
    assert not (evidence.unknown & body).any()
    valid, reason = evidence.check_trajectory([inputs[2]], raw, allowed, node._world_to_grid)
    assert not valid and reason == 'start_egress_new_unknown_or_obstacle'


def test_real_native_start_curve_uses_proved_rpp_departure_without_extra_turn():
    from explore.metric_frontier import rpp_trajectory, route_departure_point
    node, inputs, _ = fixture()
    data = Path(__file__).parent/'data'
    first = np.load(data/'ap06_ordinary_departure_initial.npz')
    meta = json.loads((data/'ap06_ordinary_departure.json').read_text())
    for index, key, geom in ((0,'raw',meta['geometry'][0]),(5,'cost',meta['geometry'][1])):
        grid = inputs[index]; grid.info.height, grid.info.width = first[key].shape
        grid.info.origin.position.x, grid.info.origin.position.y = geom['origin']
        grid.info.resolution = geom['resolution'];grid.data = first[key].ravel().tolist()
    inputs[2] = tuple(first['pose'])
    inputs[3], inputs[4], inputs[6] = (first[k].copy() for k in ('known','safe','cost_known'))
    route = tuple(tuple(p) for p in json.loads((data/'ap06_native_departure_path.json').read_text())['points'])
    node._metric_prepare_egress(inputs)
    before = [copy.deepcopy(inputs[i].data) for i in (0,5)]
    # The additional standstill alignment expands the private intersection.
    turned = rpp_trajectory(route,inputs[2],inputs[0].info.resolution,.02,
                           node._metric_bounds,prealign_to_first_leg=True)
    rejected = [e.check_trajectory(turned,np.asarray(g.data).reshape(mask.shape),mask,node._world_to_grid)
                for e,(g,mask) in zip(node._metric_egress,((inputs[0],inputs[3]),(inputs[5],inputs[6])))]
    assert any(not valid for valid,_ in rejected)
    assert node._metric_waypoints_clear(inputs,route,0.) is not None, node._metric_last_route_rejection
    node._prealign_to_goal = lambda *a,**k: pytest.fail('an unproved additional turn must not be emitted')
    assert node._metric_align_nav_departure(route,inputs[2],lambda:False)[0] == 'controller_owned'
    assert node._metric_align_nav_departure(route,inputs[2],lambda:True)[0] == 'interrupted'
    assert [inputs[i].data for i in (0,5)] == before
