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
    assert all(.3<=c.x<=.6 and abs(c.y)<1e-6 and c.observation_points for c in proved)
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
