"""AP-05: actual parent decisions, observation receipts and passive checkpoint IO."""
import copy
from dataclasses import replace
import json
import math
import threading
from types import SimpleNamespace

import numpy as np
import pytest
from std_msgs.msg import String

from explore.explore_node import ExploreNode
from explore.metric_frontier import MetricTaskPolicy
from explore.metric_progress import (CompletionWindow, ObservationBaseline, local_evidence,
                                     measured_gain, reachable_remainder)
from explore.metric_checkpoint import validate_checkpoint, restore_policy, policy_state
from explore.exploration_persistence import ExplorationStateRepository, MapVersionBinding, ExplorationPersistenceError
from explore.portal_memory import PortalMapContext
from explore.portal_source_adapter import PortalSourceCorrelation
from test_metric_frontier import grid, candidate
from test_metric_map_lifecycle import runtime, status, source, path_for


def scan(stamp=101_000_000_000):
    return dict(key=(stamp//10**9, stamp%10**9, 360), received_at=10., frame_id='laser_frame',
        ranges=np.full(360, 4.), angle_min=-math.pi, angle_increment=math.pi/180,
        range_min=.05, range_max=4.)


def test_newer_actual_local_scan_and_map_prove_gain_not_arrival():
    g=grid(); xy=ExploreNode._grid_to_world(25,20,g.info)
    context=PortalMapContext('metric','map-'+('a'*64),'map')
    baseline=ObservationBaseline(context,100_000_000_000,100_000_000_000,.1,0.,(xy,))
    c=PortalSourceCorrelation(context,2,'b'*64,101_000_000_000)
    gained=measured_gain(baseline,g,c,(.05,.05,0.),scan(),(0.,0.,0.),
                        ExploreNode._world_to_grid,ExploreNode._grid_to_world)
    assert gained==frozenset([xy])
    assert not measured_gain(baseline,g,c,(.05,.05,0.),scan(),(0.,0.,0.),
                            ExploreNode._world_to_grid,ExploreNode._grid_to_world,maximum_range_m=1.)
    g.data[20*80+25]=100
    assert not measured_gain(baseline,g,c,(.05,.05,0.),scan(),(0.,0.,0.),
                             ExploreNode._world_to_grid,ExploreNode._grid_to_world)
    actual=scan();actual['ranges'][180]=1.5
    assert measured_gain(baseline,g,c,(.05,.05,0.),actual,(0.,0.,0.),
                         ExploreNode._world_to_grid,ExploreNode._grid_to_world)==frozenset([xy])


@pytest.mark.parametrize('fault',['old_scan','old_map','foreign','still_unknown','wall','nan','short_range','masked',
                                  'resolution','fractional_origin','occupied_sensor','diagonal_wall'])
def test_global_growth_or_unusable_view_never_proves_local_observation(fault):
    g=grid();xy=ExploreNode._grid_to_world(25,20,g.info)
    context=PortalMapContext('metric','map-'+('a'*64),'map')
    baseline=ObservationBaseline(context,100_000_000_000,100_000_000_000,.1,0.,(xy,))
    c=PortalSourceCorrelation(context,2,'b'*64,101_000_000_000);s=scan();pose=(.05,.05,0.)
    a=np.asarray(g.data).reshape(40,80).copy()
    if fault=='old_scan':s['key']=(100,0,360)
    if fault=='old_map':c=replace(c,source_stamp_ns=100_000_000_000)
    if fault=='foreign':c=replace(c,context=replace(context,map_id='other-map'))
    if fault=='still_unknown':a[20,25]=-1
    if fault=='wall':a[20,20]=100
    if fault=='nan':s['ranges'][:]=np.nan
    if fault=='short_range':s['ranges'][:]=.2
    if fault=='masked':s['ranges'][180]=np.nan
    if fault=='resolution':g.info.resolution=.11
    if fault=='fractional_origin':g.info.origin.position.x+=.03
    if fault=='occupied_sensor':a[20,10]=100
    if fault=='diagonal_wall':
        pose=(.05,-.45,0.);a[16,11]=100
    g.data=a.ravel().tolist()
    assert not measured_gain(baseline,g,c,pose,s,(0.,0.,0.),ExploreNode._world_to_grid,ExploreNode._grid_to_world)


def test_aligned_growth_preserves_world_receipt_and_distant_edit_does_not_open_retry():
    g=grid();key=local_evidence(g,(1.5,0.),ExploreNode._grid_to_world)
    grown=copy.deepcopy(g);grown.info.width+=1;grown.info.height+=1
    grown.info.origin.position.x-=.1;grown.info.origin.position.y-=.1
    grown.data=np.pad(np.asarray(g.data).reshape(40,80),((1,0),(1,0)),constant_values=-1).ravel().tolist()
    assert local_evidence(grown,(1.5,0.),ExploreNode._grid_to_world)==key
    grown.data[-1]=100
    assert local_evidence(grown,(1.5,0.),ExploreNode._grid_to_world)==key
    p=MetricTaskPolicy(.6,30.,2);k=p.identify((1.5,0.));c=replace(candidate(k),evidence_key=key)
    p.record(c,'observed',10.,'a'*64)
    assert not p.eligible(k,(1.,0.),50.,'b'*64,key)
    for index in range(2):
        evidence=str(index+1)*64
        assert p.eligible(k,(1.,0.),50.+40*index,'c'*64,evidence)
        p.record(c,'observed',50.+40*index,'c'*64,evidence)
    assert not p.eligible(k,(1.,0.),200.,'d'*64,'f'*64)
    assert p.identify((2.,.1),target_xy=(1.1,0.))==k


def test_arrival_without_observation_stays_open_and_retry_requires_local_change_and_budget():
    p=MetricTaskPolicy(.6,30.,2);k=p.identify((1.5,0.));c=replace(candidate(k),evidence_key='a'*64)
    p.record(c,'arrival_without_observation',10.,'b'*64)
    assert not p.attempts[k].completed
    assert not p.eligible(k,(1.,0.),50.,'c'*64,'a'*64)
    assert not p.eligible(k,(1.,0.),39.,'c'*64,'d'*64)
    assert p.eligible(k,(1.,0.),40.,'c'*64,'d'*64)
    p.record(c,'arrival_without_observation',40.,'c'*64,'d'*64)
    assert not p.eligible(k,(1.,0.),100.,'e'*64,'e'*64)


def test_completion_window_requires_continuous_new_scans_and_resets_on_rest_work():
    w=CompletionWindow()
    for i in range(12):
        assert not w.observe(now=i*.25,scan_stamp=i+1,context='map',clear=True)
    assert w.observe(now=3.,scan_stamp=13,context='map',clear=True)
    assert not w.observe(now=3.25,scan_stamp=14,context='map',clear=False)
    assert not w.observe(now=3.5,scan_stamp=15,context='map',clear=True)
    assert not w.observe(now=4.5,scan_stamp=16,context='map',clear=True)
    assert w.samples==1
    for i in range(16,40):
        assert not w.observe(now=4.5+(i-16)*.1,scan_stamp=16,context='map',clear=True)
    assert w.samples==1  # duplicate callback cannot invent observations


def parent_fixture(monkeypatch, scene='known'):
    n,g=runtime(monkeypatch);clock=[10.02]
    import explore.metric_frontier_runtime as module
    monkeypatch.setattr(module.time,'monotonic',lambda:clock[0])
    monkeypatch.setattr(module.time,'sleep',lambda delay:clock.__setitem__(0,clock[0]+max(.05,delay)))
    monkeypatch.setattr(module.rclpy,'ok',lambda:True)
    g=copy.deepcopy(g);a=np.zeros((100,100),int)
    if scene=='wall':
        a[10:19,20:29]=100;a[11:18,21:28]=-1
    elif scene=='tiny':a[20,25]=-1
    elif scene=='open':a[10:30,25:]=-1
    g.data=a.ravel().tolist();g.header.stamp.nanosec=10_000_000
    n._on_map(g);n._on_metric_map_status(status(g,accepted=2,observed=2,when=100.02))
    n._metric_self_body_enabled=n._metric_start_egress_enabled=False
    n.get_clock=lambda:SimpleNamespace(now=lambda:SimpleNamespace(nanoseconds=int((100+clock[0]-10)*1e9)))
    def fresh_scan():
        s=scan(int((100+clock[0]-10)*1e9));s['received_at']=clock[0];return s
    n._door_lidar_scan_snapshot=fresh_scan;n._door_lidar_mount=lambda _:(0.,0.,0.)
    n._door_lidar_scan_timeout=.5;n._door_lidar_max_range=4.
    for name,value in dict(_overall_timeout_s=10.,_goal_timeout_s=5.,_frontier_revisit_radius=.6,
        _metric_retry_s=30.,_metric_retry_limit=2,_max_frontier_goals=20,_max_failed_goals=4,
        _initial_scan_enabled=False,_metric_start_strategy='configured_scan',_metric_candidate_source='boundary_samples',
        _blacklist=[],_visited_frontier_goals=[],_replan_period_s=.25,_hwt_hold_announced=False,
        _wohnungserkundung_active_child=None,_metric_repository=None,_visualize=False,
        _approach_dist_m=.5,_goal_search_m=.8,_min_goal_dist_m=.4,
        _frontier_forward_cone_half_angle=0.,_potential_scale=1.,_gain_scale=1.,_heading_scale=0.).items():setattr(n,name,value)
    n._wohnungserkundung_runtime_lock=threading.Lock()
    n._wohnungserkundung_hwt_hold=lambda:False;n._metric_confirm_stop=lambda *_:True
    n._metric_operating_snapshot=lambda **_:dict(safe=True,first_rejecting_predicate=None)
    n._finish_result=lambda result,count:(setattr(result,'frontiers_visited',count) or result)
    terminal=[]
    parent=SimpleNamespace(is_cancel_requested=False,publish_feedback=lambda _:None,
        abort=lambda:terminal.append('abort'),canceled=lambda:terminal.append('cancel'),succeed=lambda:terminal.append('success'))
    return n,g,clock,parent,terminal


@pytest.mark.parametrize('scene',['known','wall'])
def test_actual_parent_positive_success_including_unknown_behind_walls(monkeypatch,scene):
    n,g,clock,parent,terminal=parent_fixture(monkeypatch,scene)
    original=g.data[:]
    result=n._execute_metric_frontier(parent,10.,.3)
    assert result.success and terminal==['success']
    assert n._metric_status['outcome']=='metric_complete'
    assert not n._metric_status['semantic_complete'] and not n._metric_status['floor_coverage_verified']
    assert clock[0]>=13.02 and g.data==original
    assert n._metric_checkpoint['attempts']==0


@pytest.mark.parametrize('fault',['tiny','filtered','budget','source','cancel','no_pose','scan_stale','window_source_loss'])
def test_actual_parent_negative_endings_never_success(monkeypatch,fault):
    n,g,clock,parent,terminal=parent_fixture(monkeypatch,'tiny' if fault=='tiny' else 'known')
    if fault=='filtered':
        g=copy.deepcopy(g);g.data[20*100+25]=-1;g.header.stamp.nanosec=20_000_000
        n._on_map(g);n._on_metric_map_status(status(g,accepted=3,observed=3,when=100.03))
    if fault=='budget':n._max_frontier_goals=0
    if fault=='source':n._metric_operating_snapshot=lambda:dict(safe=False,first_rejecting_predicate='source_missing')
    if fault=='cancel':parent.is_cancel_requested=True
    if fault=='no_pose':n._robot_pose_sample=lambda:(None,None)
    if fault=='scan_stale':n._door_lidar_scan_snapshot=lambda:None
    if fault=='window_source_loss':
        actual=n._door_lidar_scan_snapshot
        n._door_lidar_scan_snapshot=lambda:actual() if clock[0]<11. else None
    result=n._execute_metric_frontier(parent,10.,20. if fault=='filtered' else .3)
    assert not result.success and terminal==(['cancel'] if fault=='cancel' else ['abort'])
    assert n._metric_status['outcome'] in ('usable_partial','blocked_help_required','error','user_canceled')
    if fault in ('tiny','filtered'):
        assert n._metric_status['outcome']=='blocked_help_required'
        assert n._metric_status['reason']=='accessible_frontier_filtered_or_blocked'


def checkpoint_document():
    p=MetricTaskPolicy(.6,30.,2);k=p.identify((1.5,0.));c=replace(candidate(k),evidence_key='c'*64)
    p.record(c,'arrival_without_observation',10.,'a'*64)
    return dict(schema_version=1,strategy='metric_frontier',resume_authorizes_motion=False,
        context=dict(session_id='metric',map_id='map-'+('a'*64),frame_id='map'),
        saved_map_id='map-'+('b'*64),fingerprint='b'*64,
        scope=dict(scope_id='scope',vertices=[[0.,0.],[3.,0.],[3.,3.],[0.,3.]]),
        remaining_s=100.,saved_wall_time=1000.,attempts=1,failures=1,arrivals=1,observations=0,
        observed_area_m2=0.,outcome='usable_partial',policy=policy_state(p,10.),
        budget_limits=dict(max_frontier_goals=20,max_failed_goals=4,goal_timeout_s=5.,completion_window_s=3.))


def test_restart_preserves_task_history_and_consumes_elapsed_total_budget():
    state=json.loads(json.dumps(checkpoint_document()))
    p,remaining=restore_policy(state,200.,1020.)
    assert remaining==80. and p.next_id==1 and p.attempts['metric-task-1'].failures==1
    assert not p.eligible('metric-task-1',(1.,0.),211.,'f'*64,'c'*64)
    assert p.eligible('metric-task-1',(1.,0.),211.,'f'*64,'e'*64)
    assert restore_policy(state,200.,1200.)[1]==0.
    with pytest.raises(ValueError,match='clock_regressed'):restore_policy(state,200.,999.)


@pytest.mark.parametrize('fault',['schema','map_id','negative_budget','task_ids','attempt_reset','bad_scope'])
def test_invalid_checkpoint_cannot_restore(fault):
    state=checkpoint_document()
    if fault=='schema':state['schema_version']=99
    if fault=='map_id':state['saved_map_id']='map-other'
    if fault=='negative_budget':state['remaining_s']=-1
    if fault=='task_ids':state['policy']['next_id']=0
    if fault=='attempt_reset':state['policy']['tasks']['metric-task-1']['tries']=0
    if fault=='bad_scope':state['scope']['vertices'][0]=[float('nan'),0.]
    with pytest.raises(ValueError):validate_checkpoint(state)


def test_atomic_checkpoint_keeps_last_valid_on_unsupported_or_interrupted_save(tmp_path,monkeypatch):
    binding=MapVersionBinding('test-map','version1','b'*64,80,40,.1,'map')
    repository=ExplorationStateRepository(tmp_path);valid=json.loads(json.dumps(checkpoint_document()))
    first=repository.save(binding,valid)
    bad=copy.deepcopy(valid);bad['schema_version']=2
    repository.save(binding,bad)
    assert repository.load(binding,validate_state=validate_checkpoint).path==first
    import explore.exploration_persistence as storage
    def interrupted(*args,**kwargs):raise OSError('synthetic interruption before publication')
    monkeypatch.setattr(storage.os,'link',interrupted)
    with pytest.raises(OSError):repository.save(binding,dict(valid,attempts=2))
    assert repository.load(binding,validate_state=validate_checkpoint).state==valid
    assert not list(first.parent.glob('.tmp-*'))
    with pytest.raises(ExplorationPersistenceError):repository.load(replace(binding,fingerprint='f'*64))


def test_metric_save_callback_binds_exact_partial_map_and_load_is_passive(tmp_path):
    from test_exploration_persistence import manager_status,BINDING
    n=ExploreNode.__new__(ExploreNode);n._metric_repository=ExplorationStateRepository(tmp_path)
    n._metric_restored=None;n._metric_checkpoint=checkpoint_document()
    n._metric_checkpoint.update(fingerprint=BINDING.fingerprint,saved_map_id='map-'+BINDING.fingerprint,
                                saved_wall_time=__import__('time').time())
    n._metric_persist_map_status(manager_status())
    assert n._metric_persistence_status['state']=='saved'
    n._metric_checkpoint=None
    n._metric_persist_map_status(manager_status(event='status'))
    assert n._metric_restored['attempts']==1 and n._metric_persistence_status['state']=='loaded_passively'
    assert n._metric_persistence_status['motion_authorized'] is False
    # A failed save cannot replace the valid sidecar or authorize a mission.
    n._metric_checkpoint=dict(n._metric_restored,fingerprint='f'*64)
    n._metric_persist_map_status(manager_status())
    assert n._metric_persistence_status['state']=='unavailable'
    assert n._metric_repository.load(BINDING,validate_state=validate_checkpoint).state['attempts']==1


def test_actual_map_repository_and_sidecar_keep_last_pair_after_interrupted_new_save(tmp_path,monkeypatch):
    from robot_map_manager.map_core import MapRepository,MapSnapshot,MapOrigin,StoragePolicy
    from datetime import datetime,timezone,timedelta
    maps=MapRepository(tmp_path/'maps',policy=StoragePolicy(minimum_save_interval_s=0.,minimum_free_space_bytes=0))
    states=ExplorationStateRepository(tmp_path/'exploration')
    raw=MapSnapshot.from_values(width=2,height=2,resolution=.1,frame_id='map',
        origin=MapOrigin(0.,0.,0.,0.,0.,0.,1.),cells=(0,0,100,-1),source_stamp_ns=1)
    first=maps.save(raw,now=datetime(2026,10,3,tzinfo=timezone.utc))
    binding=MapVersionBinding(first.name,first.version,first.fingerprint,first.width,first.height,first.resolution,first.frame_id)
    state=checkpoint_document();state.update(fingerprint=first.fingerprint,saved_map_id='map-'+first.fingerprint)
    previous=states.save(binding,state)
    # A valid new raw map alone is never advertised as a complete exploration backup.
    second=maps.save(raw,now=datetime(2026,10,3,tzinfo=timezone.utc)+timedelta(seconds=1))
    second_binding=replace(binding,version=second.version)
    import explore.exploration_persistence as storage
    monkeypatch.setattr(storage.os,'link',lambda *_,**__:(_ for _ in ()).throw(OSError('interrupted sidecar')))
    with pytest.raises(OSError):states.save(second_binding,state)
    assert states.load(binding,validate_state=validate_checkpoint).path==previous
    with pytest.raises(ExplorationPersistenceError):states.load(second_binding,validate_state=validate_checkpoint)
    assert any(m.version==first.version for m in maps.list_versions())
    assert (first.path/'occupancy.bin').exists()


@pytest.mark.parametrize('gain',['new_visible_cells','arrival_only','cancel_wait','late_cancel','gain_after_deadline','hwt_wait','join_lag','join_cancel','join_timeout','join_source_loss'])
def test_real_candidate_parent_separates_arrival_observation_and_cancel(monkeypatch,gain):
    from geometry_msgs.msg import PoseStamped
    from nav_msgs.msg import Path
    n,g,clock,parent,terminal=parent_fixture(monkeypatch,'open')
    n._max_frontier_goals=1
    chosen=[]
    def planner(target,*_):
        chosen.append(target)
        path=Path();path.header.frame_id='map';path.header.stamp.sec=100
        for x,y in target.route:
            p=PoseStamped();p.pose.position.x=x;p.pose.position.y=y;p.pose.orientation.w=1.
            path.poses.append(p)
        return path,None
    n._metric_request_nav_plan=planner
    n._prealign_to_goal=lambda *_,**__:('skipped',)
    def navigate(*_,**__):
        target=chosen[-1];clock[0]+=.1
        n._robot_pose_sample=lambda:((target.x,target.y,target.yaw),0.)
        if gain in ('new_visible_cells','gain_after_deadline','hwt_wait','join_lag','join_cancel','join_timeout','join_source_loss'):
            newer=copy.deepcopy(g)
            for xy in target.observation_points:
                col,row=n._world_to_grid(*xy,newer.info);newer.data[row*newer.info.width+col]=0
            newer.header.stamp.nanosec=100_000_000
            n._on_map(newer)
            if not gain.startswith('join_'):
                n._on_metric_map_status(status(newer,accepted=3,observed=3,when=100.1))
        if gain=='late_cancel':parent.is_cancel_requested=True
        return 'success'
    n._navigate_to=navigate
    waits=[]
    if gain=='hwt_wait':
        held=[]
        def hold():
            if chosen and clock[0]>10.1 and not held:
                held.append(True);return True
            return False
        n._wohnungserkundung_hwt_hold=hold
        def resume(*_,require_target):
            waits.append(require_target);clock[0]+=.1;return 'resumed'
        n._wohnungserkundung_wait_for_hwt_resume=resume
    if gain=='gain_after_deadline':
        import explore.metric_frontier_runtime as module
        n._metric_observation_wait_s=.04
        actual=module.measured_gain
        def processing_delay(*args,**kwargs):
            result=actual(*args,**kwargs)
            assert result  # a usable observation, rejected only by its deadline
            clock[0]+=.05
            return result
        monkeypatch.setattr(module,'measured_gain',processing_delay)
    if gain=='cancel_wait':
        import explore.metric_frontier_runtime as module
        def tick(delay):
            clock[0]+=max(.05,delay)
            if chosen:parent.is_cancel_requested=True
        monkeypatch.setattr(module.time,'sleep',tick)
    if gain.startswith('join_'):
        import explore.metric_frontier_runtime as module
        def tick(delay):
            clock[0]+=max(.05,delay)
            if chosen and n._metric_pending_since is not None:
                if gain=='join_lag':
                    latest=n._metric_raw[0]
                    n._on_metric_map_status(status(latest,accepted=3,observed=3,when=100.1))
                elif gain=='join_cancel':
                    parent.is_cancel_requested=True
                elif gain=='join_source_loss':
                    n._metric_raw=(*n._metric_raw[:2],4.)
                    n._on_metric_map_status(status(n._metric_raw[0],accepted=3,observed=3,when=100.1))
        monkeypatch.setattr(module.time,'sleep',tick)
    result=n._execute_metric_frontier(parent,10.,.3)
    assert chosen and chosen[0].observation_points
    if 'cancel' in gain:
        assert terminal==['cancel'] and n._metric_status['outcome']=='user_canceled'
        assert n._metric_status['observations']==0
    elif gain in ('join_timeout','join_source_loss'):
        assert terminal==['abort'] and not result.success
        assert n._metric_status['observations']==0
        assert n._metric_status['reason']==('map_status_join_pending' if gain=='join_timeout' else 'map_or_status_stale')
    else:
        assert terminal==['abort'] and not result.success
        assert n._metric_status['arrivals']==1
        if gain in ('new_visible_cells','hwt_wait','join_lag'):
            assert n._metric_status['observations']==1 and n._metric_status['observed_area_m2']>0
            assert n._metric_status['chain'][0]['decision']=='observed'
            if gain=='hwt_wait':
                assert waits==[False] and len(chosen)==1
                assert n._metric_checkpoint['attempts']==1
        else:
            assert n._metric_status['observations']==0
            assert n._metric_status['chain'][0]['decision']=='arrival_without_observation'


@pytest.mark.parametrize('fault',['no_pose','map_id','scope','expired','valid','no_localization',
                                 'wrong_localization_map','stale_localization','unverified'])
def test_resume_needs_explicit_binding_fresh_pose_and_remaining_budget(monkeypatch,fault):
    n,g,clock,parent,terminal=parent_fixture(monkeypatch)
    n._metric_resume_saved=True;n._metric_resume_origin_map_id=n._metric_correlation.context.map_id
    state=checkpoint_document()
    state.update(context=dict(session_id=n._metric_correlation.context.session_id,
            map_id=n._metric_resume_origin_map_id,frame_id='map'),
        fingerprint=n._metric_correlation.fingerprint,saved_map_id='map-'+n._metric_correlation.fingerprint,
        scope=dict(scope_id=n._metric_scope.scope_id,vertices=[[v.x,v.y] for v in n._metric_scope.vertices]),
        saved_wall_time=__import__('time').time(),remaining_s=4.)
    # Served task history stays served; no hidden retry/reset on reload.
    task=state['policy']['tasks']['metric-task-1'];task.update(completed=True,reason='observed',failures=0)
    state.update(failures=0,observations=1,observed_area_m2=.01)
    n._metric_restored=state
    localized=dict(schema_version=1,time=__import__('time').time(),ready=True,state='localized',
        map_fingerprint=state['fingerprint'],global_initialization_fingerprint=state['fingerprint'],
        global_initialization='completed',global_initialization_generation=1,
        global_initialization_id='c'*32,global_scan_match=dict(required=True,verified=True))
    n._on_metric_localization_status(String(data=json.dumps(localized)))
    actual_scan=n._door_lidar_scan_snapshot
    def with_localization():
        n._on_metric_localization_status(String(data=json.dumps(dict(localized,time=__import__('time').time()))))
        return actual_scan()
    n._door_lidar_scan_snapshot=with_localization
    if fault=='no_localization':n._metric_localization_status=None
    if fault=='wrong_localization_map':n._metric_localization_status[0]['map_fingerprint']='e'*64
    if fault=='stale_localization':n._metric_localization_status=(localized,clock[0]-1.)
    if fault=='unverified':n._metric_localization_status[0]['global_scan_match']['verified']=False
    if fault=='no_pose':n._robot_pose_sample=lambda:(None,None)
    if fault=='map_id':state['context']['map_id']='foreign-epoch'
    if fault=='scope':state['scope']['vertices'][0][0]+=.1
    if fault=='expired':state['saved_wall_time']-=10.
    result=n._execute_metric_frontier(parent,10.,.3)
    assert result.success==(fault=='valid')
    if fault=='valid':
        assert n._metric_checkpoint['attempts']==1
        assert n._metric_checkpoint['observations']==1
        assert n._metric_checkpoint['remaining_s']<1.
    else:assert terminal==['abort']


@pytest.mark.parametrize('outcome',['metric_complete','usable_partial','blocked_help_required','error','user_canceled'])
def test_actual_status_publishes_distinct_results_and_partial_save_without_floor_claim(outcome):
    from test_explore_contract import _status_node
    n=_status_node(False);published=[]
    n._metric_enabled=True;n._metric_scope=object();n._metric_fault=None;n._metric_checkpoint={}
    n._status_pub.publish=published.append
    n._metric_status=dict(schema_version=1,outcome=outcome,state='success' if outcome=='metric_complete' else 'partial',
        arrivals=2,observations=1,observed_area_m2=.12,semantic_complete=False,floor_coverage_verified=False)
    n._publish_status(n._metric_status['state'])
    root=json.loads(published[0].data)
    assert root['map_ready_to_save']==(outcome=='metric_complete')
    assert root['metric_exploration']['partial_map_ready_to_save'] is True
    assert root['metric_exploration']['outcome']==outcome and root['coverage_ratio']==0


def test_actual_candidate_source_reopens_served_place_only_after_useful_local_change(monkeypatch):
    from test_metric_frontier_candidates import fixture
    import explore.metric_frontier_runtime as module
    clock=[10.]
    monkeypatch.setattr(module.time,'monotonic',lambda:clock[0])
    n,inputs,_=fixture('revisit',revision=1)
    p=MetricTaskPolicy(.6,30.,2);first=n._metric_select(inputs,p,.3)[0]
    p.record(first,'observed',10.,inputs[1].fingerprint)
    clock[0]=50.
    assert all(c.task_id!=first.task_id for c in n._metric_select(inputs,p,.3))
    n,next_inputs,_=fixture('revisit',revision=2)
    next_candidates=n._metric_select(next_inputs,p,.3)
    reopened=[c for c in next_candidates if c.task_id==first.task_id]
    assert reopened and reopened[0].evidence_key!=first.evidence_key
    assert reopened[0].observation_points and p.attempts[first.task_id].tries==1


def test_new_accessible_work_during_last_completion_check_prevents_stale_success(monkeypatch):
    n,g,clock,parent,terminal=parent_fixture(monkeypatch)
    changed=[]
    def operating(**kwargs):
        if kwargs.get('require_stop') and not changed:
            changed.append(True)
            newer=copy.deepcopy(g);newer.data[20*100+25]=-1
            stamp=int((100+clock[0]-10)*1e9)
            newer.header.stamp.sec=stamp//10**9;newer.header.stamp.nanosec=stamp%10**9
            n._on_map(newer);n._on_metric_map_status(status(newer,accepted=3,observed=3,when=100+clock[0]-10))
        return dict(safe=True,first_rejecting_predicate=None)
    n._metric_operating_snapshot=operating
    result=n._execute_metric_frontier(parent,10.,20.)
    assert changed and not result.success and terminal==['abort']
    assert n._metric_status['outcome']=='blocked_help_required'


def test_observed_history_tracks_actual_early_arrival_and_rejects_unproved_pose():
    policy = MetricTaskPolicy(.6, 30., 2)
    key = policy.identify((1.5, 0.))
    goal = replace(candidate(key), x=.6, y=0., evidence_key='a'*64)
    policy.record(goal, 'observed', 10., 'b'*64, arrival_xy=(.45, 0.))
    assert policy.attempts[key].target_xy == (.45, 0.)
    assert not policy.eligible(key, (.9, 0.), 50., 'b'*64, 'a'*64)
    assert policy.eligible(key, (1.08, 0.), 50., 'b'*64, 'a'*64)
    saved = policy_state(policy, 10.)
    assert saved['tasks'][key]['target_xy'] == (.45, 0.)
    with pytest.raises(ValueError, match='metric_observed_arrival_invalid'):
        policy.record(goal, 'observed', 11., 'b'*64, arrival_xy=(.4, 0.))
    assert policy.attempts[key].tries == 1
