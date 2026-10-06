"""An existing public child may retain old exact evidence with fewer permits.

Real raw/status callbacks and full body guards remain active. Unpaired raw
cells may withdraw old free space, never grant new space or a receipt.
"""
import copy
import numpy as np
import pytest
from explore.metric_frontier import StartEgressEvidence
from test_metric_map_lifecycle import runtime, status


def fixture(monkeypatch):
    node, grid = runtime(monkeypatch)
    node._metric_self_body_enabled = node._metric_start_egress_enabled = False
    node._metric_egress = None
    node._metric_path_validation = 'rpp_rollout'
    node._wohnungserkundung_active_child = object()
    grid = copy.deepcopy(grid)
    grid.data = [0]*10000; grid.data[25*100+40] = -1
    grid.header.stamp.nanosec = 10_000_000
    node._on_map(grid)
    node._on_metric_map_status(status(grid, accepted=2, observed=2, when=100.02))
    before = node._metric_inputs(active=True)
    return node, grid, before


@pytest.mark.parametrize('change', ['gain', 'obstacle', 'unknown', 'growth'])
def test_active_old_join_retains_original_identity_and_only_withdraws(change, monkeypatch):
    node, grid, before = fixture(monkeypatch)
    newer = copy.deepcopy(grid); newer.header.stamp.nanosec = 20_000_000
    newer.data[25*100+40] = 0
    if change in ('obstacle', 'unknown'):
        newer.data[20*100+11] = 100 if change == 'obstacle' else -1
    if change == 'growth':
        newer.info.width += 1; newer.info.origin.position.x -= grid.info.resolution
        newer.data = np.pad(np.asarray(newer.data).reshape(100,100),
                            ((0,0),(1,0)),constant_values=-1).ravel().tolist()
    raw_bytes = list(grid.data)
    node._on_map(newer)
    assert not node._metric_matches_status(node._metric_raw[1])
    current = node._metric_inputs(active=True)
    assert current[0] is grid and list(grid.data) == raw_bytes
    assert current[1].fingerprint == before[1].fingerprint
    assert current[1].source_stamp_ns == before[1].source_stamp_ns
    assert current[1].map_revision == before[1].map_revision
    assert not current[3][25,40]  # newer unknown-to-free is NOT granted
    assert not np.any(current[3] & ~before[3])
    if change in ('obstacle', 'unknown'):
        assert not current[3][20,11]
        assert node._metric_waypoints_clear(current, ((.05,.05),(.65,.05)), 0.) is None
    else:
        assert node._metric_waypoints_clear(current, ((.05,.05),(.65,.05)), 0.) is not None
    # Terminal observation/selection still requires the genuine exact pair.
    node._wohnungserkundung_active_child = None
    with pytest.raises(ValueError, match='map_status_join_pending'):
        node._metric_inputs(active=True)
    with pytest.raises(ValueError, match='map_status_join_pending'):
        node._metric_inputs()
    node._on_metric_map_status(status(newer, accepted=3, observed=3, when=100.03))
    exact = node._metric_inputs()
    assert exact[0] is newer and exact[1].source_stamp_ns > before[1].source_stamp_ns


@pytest.mark.parametrize('fault', ['no_child', 'selection', 'private', 'deadline',
    'future', 'fractional', 'status_ahead', 'resolution', 'epoch', 'conservative',
    'old_raw_age', 'old_status_age'])
def test_pending_withdrawal_never_heals_original_binding_or_source_guards(fault, monkeypatch):
    node, grid, before = fixture(monkeypatch)
    newer = copy.deepcopy(grid); newer.header.stamp.nanosec = 20_000_000
    newer.data[25*100+40] = 0
    if fault == 'future': newer.header.stamp.sec = 200
    if fault == 'fractional': newer.info.origin.position.x += .03
    if fault == 'resolution': newer.info.resolution = .11
    node._on_map(newer)
    if fault == 'no_child': node._wohnungserkundung_active_child = None
    if fault == 'private':
        node._metric_egress = (StartEgressEvidence.capture(grid,
            np.asarray(grid.data).reshape(100,100), before[3], np.ones((100,100),bool),
            before[2], node._metric_bounds, node._world_to_grid),)
        assert node._metric_egress[0].valid
    if fault == 'deadline': node._metric_pending_since = 8.
    if fault == 'status_ahead':
        accepted = copy.deepcopy(newer); accepted.header.stamp.nanosec += 10_000_000
        accepted.data[-1] = 100
        node._on_metric_map_status(status(accepted, accepted=3, observed=3, when=100.03))
    if fault == 'epoch': node._metric_fault = 'map_epoch_changed'
    if fault == 'conservative': node._metric_path_validation = 'conservative'
    if fault in ('old_raw_age', 'old_status_age'):
        raw, correlation, at = node._metric_joined
        if fault == 'old_raw_age': raw = (*raw[:2], 4.)
        else: at = 4.
        node._metric_joined = (raw, correlation, at)
    with pytest.raises(ValueError):
        node._metric_inputs(active=fault != 'selection')


@pytest.mark.parametrize('fault', ['none', 'obstacle', 'deadline', 'source', 'epoch'])
def test_actual_parent_keeps_one_child_or_stops_on_withdrawn_authority(monkeypatch, fault):
    import math
    from geometry_msgs.msg import PoseStamped
    from nav_msgs.msg import Path
    from test_metric_progress import parent_fixture
    node, grid, clock, parent, terminal = parent_fixture(monkeypatch, 'open')
    node._metric_path_validation = 'rpp_rollout'
    node._max_frontier_goals = 1
    node._metric_egress = None  # this leg uses public free space only
    chosen = []; children = []; stops = []
    def planner(target, *_, **kwargs):
        chosen.append(target)
        path = Path(); path.header.frame_id = 'map'
        start = kwargs.get('start_pose', node._robot_pose_sample()[0])
        for x,y in (start[:2], (target.x,target.y)):
            p = PoseStamped(); p.pose.position.x=x; p.pose.position.y=y
            p.pose.orientation.z=math.sin(target.yaw/2)
            p.pose.orientation.w=math.cos(target.yaw/2); path.poses.append(p)
        return path, None
    node._metric_request_nav_plan = planner
    node._prealign_to_goal = lambda *_, **__: ('skipped',)
    def navigate(*_, stop_requested, **__):
        target=chosen[-1]; children.append(target)
        assert node._wohnungserkundung_active_child is target
        latest = copy.deepcopy(grid)
        for index in range(3):
            clock[0]+=.1; latest=copy.deepcopy(latest)
            latest.header.stamp.nanosec=int((clock[0]-10)*1e9)
            latest.data[80*latest.info.width+80] = (index+1)*10
            if fault == 'obstacle': latest.data[20*latest.info.width+10] = 100
            node._on_map(latest)
            if fault == 'deadline': node._metric_pending_since=clock[0]-2
            if fault == 'source':
                raw,cor,at=node._metric_joined
                node._metric_joined=((*raw[:2],4.),cor,at)
            if fault == 'epoch': node._metric_fault='map_epoch_changed'
            stops.append(stop_requested())
            node._on_metric_map_status(status(latest,accepted=3+index,observed=3+index,
                                             when=100+clock[0]-10))
            if stops[-1]: return 'canceled'
        node._robot_pose_sample=lambda:((target.x,target.y,target.yaw),0.)
        clock[0]+=.1; latest=copy.deepcopy(latest)
        for xy in target.observation_points:
            col,row=node._world_to_grid(*xy,latest.info)
            latest.data[row*latest.info.width+col]=0
        latest.header.stamp.nanosec=int((clock[0]-10)*1e9)
        node._on_map(latest)
        node._on_metric_map_status(status(latest,accepted=6,observed=6,when=100+clock[0]-10))
        return 'success'
    node._navigate_to=navigate
    result=node._execute_metric_frontier(parent,10.,.3)
    assert terminal and not result.success  # original total limit, no whole claim
    assert len(children)==1 and node._wohnungserkundung_active_child is None
    assert node._metric_status['attempts']==1
    if fault == 'none':
        assert stops==[False,False,False]
        assert node._metric_status['arrivals']==node._metric_status['observations']==1
        assert node._metric_status['chain'][0]['decision']=='observed'
        assert node._metric_checkpoint['policy']['tasks'][children[0].task_id]['tries']==1
    else:
        assert stops==[True]
        assert node._metric_status['arrivals']==node._metric_status['observations']==0
