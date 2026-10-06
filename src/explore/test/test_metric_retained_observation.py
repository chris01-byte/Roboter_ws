"""Original B70 partial view and finite remaining work, never mission receipts."""
import copy
from dataclasses import asdict,replace
import json
import math
from pathlib import Path
import time

import numpy as np
import pytest

from explore.explore_node import ExploreNode
from explore.metric_progress import ObservationBaseline,observation_complete
from explore.metric_frontier_candidates import boundary_samples,visible_boundary_cells,lidar_view
from explore.metric_checkpoint import policy_state,restore_policy
from explore.portal_memory import PortalMapContext
from test_metric_public_cooldown import frozen
from test_metric_departure import path
from test_metric_progress import checkpoint_document

NAME='ap06_b70_after_observation'


def data(elapsed_s=0.):
    n,inputs,p=frozen(NAME,elapsed_s=elapsed_s)
    meta=json.loads((Path(__file__).parent/'data'/(NAME+'.json')).read_text())
    baselines=[]
    for stored in meta['baselines']:
        fields=dict(stored);fields['context']=PortalMapContext(**fields['context'])
        fields['points']=tuple(tuple(x) for x in fields['points'])
        baselines.append(ObservationBaseline(**fields))
    return n,inputs,p,meta,baselines


def partial_data(elapsed_s=0.):
    n,i,p,m,b=data(elapsed_s)
    assert not observation_complete(b[1],i[0],i[1],n._world_to_grid,n._grid_to_world)
    # Derive only the missing terminal classification from original evidence.
    # Counters, targets, local digests and all other recorded tasks stay intact.
    p.attempts['metric-task-4'].reason='partially_observed'
    p.attempts['metric-task-4'].completed=False
    return n,i,p,m,b


def test_b70_first_view_resolved_but_second_has_one_original_unknown_point():
    n,i,p,_,b=data()
    assert observation_complete(b[0],i[0],i[1],n._world_to_grid,n._grid_to_world)
    assert not observation_complete(b[1],i[0],i[1],n._world_to_grid,n._grid_to_world)
    unknown=[]
    for xy in b[1].points:
        col,row=n._world_to_grid(*xy,i[0].info)
        if i[0].data[row*i[0].info.width+col]<0:unknown.append(xy)
    assert len(b[1].points)==9 and len(unknown)==1
    assert math.dist(unknown[0],(1.5749999647960067,-.04499999899417162))<1e-9
    assert p.attempts['metric-task-4'].completed  # recorded faulty decision


@pytest.mark.parametrize('fault',['unknown','old','foreign','resolution','cropped','fractional'])
def test_complete_view_requires_current_aligned_original_map_points(fault):
    n,i,_,_,b=data();g=copy.deepcopy(i[0]);cor=i[1]
    if fault=='unknown':
        col,row=n._world_to_grid(*b[0].points[0],g.info);g.data[row*g.info.width+col]=-1
    if fault=='old':cor=replace(cor,source_stamp_ns=b[0].source_stamp)
    if fault=='foreign':cor=replace(cor,context=replace(cor.context,map_id='other'))
    if fault=='resolution':g.info.resolution*=2
    if fault=='cropped':g.info.origin.position.x+=100
    if fault=='fractional':g.info.origin.position.x+=.001
    assert not observation_complete(b[0],g,cor,n._world_to_grid,n._grid_to_world)


def test_b70_partial_followup_uses_unmodified_counter_history():
    # Analytically elapsed original cooldown on frozen component inputs.
    # No fresh source sample, movement permission or acceptance is implied.
    n,i,p,_,_=partial_data(elapsed_s=31.)
    before=policy_state(p,time.monotonic())
    selected=n._metric_select(i,p,.3)
    assert selected and not selected[0].requires_nav2_plan,n._frontier_rank_stats
    c=selected[0];assert c.task_id=='metric-task-4' and c.observation_points
    assert n._metric_waypoints_clear(i,c.route,c.yaw) is not None
    stop=n._metric_rollout_stop_pose(i,c.route,c.yaw)
    visible=visible_boundary_cells(i[0],n._metric_scope_mask(i),stop,n._metric_observation_view())
    assert set(c.observation_points)<={n._grid_to_world(col,row,i[0].info) for row,col in visible}
    after=policy_state(p,time.monotonic())
    assert before['tasks']==after['tasks']
    assert before['next_id']==after['next_id']
    assert n._frontier_rank_stats['bounded_public_observation']
    assert math.dist(i[2][:2],(c.x,c.y))<=.6+1e-12


def test_small_retained_boundary_still_requires_a_prior_partial_task_and_current_scope():
    n,i,p,_,_=partial_data();mask=n._metric_scope_mask(i)
    ordinary=boundary_samples(i[0],mask,n._grid_to_world,.3)
    retained=boundary_samples(i[0],mask,n._grid_to_world,.3,
        retained_anchors=(p.attempts['metric-task-4'].frontier_xy,))
    assert len(retained)>len(ordinary)
    assert all(x in retained for x in ordinary)
    assert boundary_samples(i[0],np.zeros_like(mask),n._grid_to_world,.3,
        retained_anchors=(p.attempts['metric-task-4'].frontier_xy,))==[]
    assert boundary_samples(i[0],mask,n._grid_to_world,.3,retained_anchors=((100.,100.),))==ordinary


@pytest.mark.parametrize('fault',['cooldown','exhausted','no_finite_view'])
def test_partial_followup_cannot_bypass_original_limits_or_sight(fault):
    n,i,p,_,_=partial_data(elapsed_s=0. if fault=='cooldown' else 31.)
    if fault=='exhausted':p.attempts['metric-task-4'].tries=3
    if fault=='no_finite_view':
        v=n._metric_observation_view()
        def invalid_view():
            now=time.monotonic()
            return lidar_view(dict(received_at=now,ranges=np.full(2160,np.nan),
                angle_min=-math.pi,angle_increment=2*math.pi/2160,range_min=.05,range_max=10.),
                v.mount,now,.5,v.range_m)
        n._metric_observation_view=invalid_view
    before=copy.deepcopy(p.attempts)
    if fault=='no_finite_view':
        with pytest.raises(ValueError,match='candidate_lidar_no_valid_rays'):
            n._metric_select(i,p,.3)
        assert p.attempts==before
        return
    selected=n._metric_select(i,p,.3)
    assert not any(c.task_id=='metric-task-4' for c in selected)
    assert all(p.attempts[k]==v for k,v in before.items())


def test_actual_native_b70_followup_path_preserves_arrival_and_departure():
    n,i,_,meta,_=partial_data(elapsed_s=31.)
    from explore.metric_frontier import MetricCandidate
    record=meta['native_plans'][0]
    c=MetricCandidate('recorded-native',*record['goal'],(1.5149999661371112,-.10499999765306711),
        (),1.,0.,i[1].fingerprint,1)
    route=n._metric_validate_nav_plan(i,path(record),c,public_only=True)
    assert route is not None
    assert n._metric_departure_plan_ready(i,route,c,lambda:False)


def test_partial_checkpoint_retains_original_attempts_and_elapsed_cooldown():
    n,i,p,_,_=partial_data();state=checkpoint_document();saved=policy_state(p,time.monotonic())
    state.update(context=asdict(i[1].context),fingerprint=i[1].fingerprint,
        saved_map_id='map-'+i[1].fingerprint,policy=saved,attempts=sum(a.tries for a in p.attempts.values()),
        failures=0,arrivals=2,observations=2,remaining_s=600.,saved_wall_time=100.)
    restored,remaining=restore_policy(state,50.,105.)
    a=restored.attempts['metric-task-4'];original=p.attempts['metric-task-4']
    assert a.reason=='partially_observed' and not a.completed
    assert (a.tries,a.failures)==(original.tries,original.failures)==(1,0)
    assert remaining==595. and restored.next_id==p.next_id
    assert a.retry_after==50.+max(0.,saved['tasks']['metric-task-4']['retry_remaining_s']-5.)
