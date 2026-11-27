"""Distinct finite boundaries retain task history and the original cooldown."""
import pytest
from explore.metric_frontier import MetricTaskPolicy, MetricCandidate


def served():
    policy = MetricTaskPolicy(.6,30.,2)
    key = policy.identify((0.,0.))
    c = MetricCandidate(key,0.,1.5,0.,(0.,0.),(),0.,0.,'old',1,
                        observation_points=((0.,0.),),evidence_key='old-local')
    policy.record(c,'observed',10.,'old',arrival_xy=(0.,1.5))
    return policy,key


@pytest.mark.parametrize('delta', [-.00001, .00001])
def test_distinct_current_boundary_keeps_original_cooldown_on_both_sides_of_radius(delta):
    policy,old = served()
    goal = (0.,2.1+delta); frontier=(0.,3.1); points=((0.,3.1),)
    task = policy.identify(frontier,goal,observation_points=points)
    assert task != old
    if delta<0:
        assert not policy.eligible(task,goal,39.999,'new','new-local',observation_points=points)
    assert policy.eligible(task,goal,40.,'new','new-local',observation_points=points)
    assert policy.attempts[old].completed and policy.attempts[old].tries==1
    assert policy.attempts[old].retry_after==40.
    assert policy.attempts[task].tries==0 and not policy.attempts[task].completed


@pytest.mark.parametrize('points', [(), ((0.,1.4),), ((0.,1.40001),(0.,.1)),
                                   ((0.,float('nan')),), ((0.,),)])
def test_missing_aliased_or_invalid_view_keeps_served_pose_identity(points):
    policy,old=served()
    assert policy.identify((0.,3.1),(0.,2.),observation_points=points)==old


def test_finite_new_view_cannot_renew_a_capped_neighbour_or_the_same_boundary():
    policy,old=served(); points=((0.,3.1),)
    assert policy.identify((0.,.1),(0.,2.),observation_points=points)==old
    policy.attempts[old].tries=3
    task=policy.identify((0.,3.1),(0.,2.),observation_points=points)
    assert task!=old
    assert not policy.eligible(task,(0.,2.),100.,'new','new-local',observation_points=points)
    assert policy.attempts[old].tries==3 and policy.attempts[old].completed


def frozen(name='ap06_b60_selection', *, elapsed_s=0.):
    import json,time
    from pathlib import Path
    import numpy as np
    from rclpy.serialization import deserialize_message
    from nav_msgs.msg import OccupancyGrid
    from shapely import wkb
    from explore.metric_frontier import MetricAttempt,StartEgressEvidence
    from explore.metric_egress_reference import ReferencedStartEgress
    from explore.metric_frontier_runtime import MetricInputs
    from explore.metric_frontier_candidates import LidarView
    from explore.portal_memory import PortalMapContext,Point2D
    from explore.portal_source_adapter import PortalSourceCorrelation
    from explore.exploration_scope import AuthorizedExplorationScope
    from test_metric_frontier import adaptive_fixture
    path=Path(__file__).parent/'data'/name
    meta=json.loads(path.with_suffix('.json').read_text())
    arrays=np.load(path.with_suffix('.npz'))
    def grid(key):return deserialize_message(arrays[key].tobytes(),OccupancyGrid)
    n,_=adaptive_fixture()
    for k,v in meta['attributes'].items():setattr(n,k,tuple(v) if isinstance(v,list) else v)
    c=dict(meta['correlation']);c['context']=PortalMapContext(**c['context'])
    cor=PortalSourceCorrelation(**c)
    scope=meta['scope'];n._metric_scope=AuthorizedExplorationScope(scope['scope_id'],cor.context,
        tuple(Point2D(**xy) for xy in scope['vertices']))
    ref=tuple(meta['reference']);n._metric_body_reference=lambda:ref
    n._metric_egress_identity=(cor.context,tuple(tuple(g) for g in meta['identity'][1]))
    evidence=[]
    for i,data in enumerate(meta['evidence']):
        fixed=StartEgressEvidence(grid(f'fixed_cdr_{i}'),tuple(data['pose']),tuple(data['bounds']),
            arrays[f'fixed_unknown_{i}'].copy(),tuple(tuple(p) for p in data['initial_polygon']),
            data['valid'],data['reason'],{(r,c):v for r,c,v in data['remaining_area']},
            {(r,c):v for r,c,v in data['departed_distance']},arrays[f'fixed_scope_{i}'].copy())
        e=ReferencedStartEgress(fixed,tuple(data['reference']))
        e.current_reference=tuple(data['current_reference']);e.generation=data['generation']
        e.unknown=arrays[f'projected_unknown_{i}'].copy();e.scope_mask=arrays[f'projected_scope_{i}'].copy()
        e.retained_region=wkb.loads(data['retained_wkb'],hex=True);e._whole_cells=data['whole_cells']
        evidence.append(e)
    n._metric_egress=tuple(evidence)
    inputs=MetricInputs((grid('raw_cdr'),cor,tuple(meta['pose']),arrays['known'].copy(),
        arrays['safe'].copy(),grid('cost_cdr'),arrays['cost_known'].copy()),ref,
        tuple(tuple(v) if isinstance(v,list) else v for v in meta['physical_motion'])
        if meta.get('physical_motion') is not None else None)
    n._global_costmap=inputs[5];n._metric_nav_path=None;n._metric_status={}
    # Frozen finite view is component geometry, never a new live scan/health receipt.
    view=LidarView(tuple(meta['mount']),arrays['angles'],meta['maximum_range'],meta['minimum_range'])
    n._metric_observation_view=lambda:view
    data=meta['policy'];p=MetricTaskPolicy(data['radius'],data['cooldown_s'],data['retry_limit'])
    p.next_id=data['next_id'];now=time.monotonic()
    for key,stored in data['tasks'].items():
        d=dict(stored);d['retry_after']=now+d.pop('retry_remaining_s')-elapsed_s
        d['target_xy']=tuple(d['target_xy']);d['frontier_xy']=tuple(d['frontier_xy'])
        p.attempts[key]=MetricAttempt(**d)
    return n,inputs,p


def test_actual_b60_current_view_waits_before_unproved_distant_work():
    from explore.metric_progress import reachable_remainder
    n,inputs,p=frozen()
    # Isolate the original .3-m option from the larger .45/.6-m options.
    # This stricter component search makes cooldown the sole remaining bar;
    # full missions keep the original .3-m search extension unchanged.
    n._goal_search_m=0.
    assert not n._metric_egress_expired and all(not e.valid for e in n._metric_egress)
    before={k:(a.tries,a.failures,a.completed,a.retry_after) for k,a in p.attempts.items()}
    def distant(*_,**__):pytest.fail('Proved public view with only cooldown remaining must wait before distant work')
    n._frontier_approach_goal=distant
    assert n._metric_select(inputs,p,.3)==[]
    assert n._frontier_rank_stats['bounded_public_observation_wait_s']>0
    assert reachable_remainder(inputs[0],n._metric_scope_mask(inputs),inputs[2],n._world_to_grid)>0
    assert before=={k:(a.tries,a.failures,a.completed,a.retry_after) for k,a in p.attempts.items() if k in before}


def test_actual_b60_after_original_cooldown_rechecks_a_fully_public_view(monkeypatch):
    import time
    import explore.metric_frontier_runtime as module
    n,inputs,p=frozen();now=time.monotonic()
    n._goal_search_m=0.
    monkeypatch.setattr(module.time,'monotonic',lambda:now+31.)
    # Counterexample clock advances the ORIGINAL pause; no mission state is reset.
    n._global_costmap_received_at=now+31.
    choices=n._metric_select(inputs,p,.3)
    assert choices and choices[0].task_id!='metric-task-1'
    assert choices[0].observation_points and not choices[0].requires_nav2_plan
    assert n._metric_waypoints_clear(inputs,choices[0].route,choices[0].yaw) is not None
    assert p.attempts['metric-task-1'].completed and p.attempts['metric-task-1'].tries==1
    assert p.attempts[choices[0].task_id].tries==0
