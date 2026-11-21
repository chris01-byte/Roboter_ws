"""Conservative connected cells and early original task bounds."""
import copy
import math
import time
from collections import deque
import numpy as np
import pytest
from explore.explore_node import connected_mask, Frontier
from test_metric_frontier import adaptive_fixture
from test_metric_public_cooldown import frozen


@pytest.mark.parametrize('seed', [(0,0),(4,4),(5,4),(-1,0),(10,10)])
@pytest.mark.parametrize('layout', ['diagonal','random','full'])
def test_compiled_component_keeps_four_neighbour_topology(seed, layout):
    mask=np.ones((10,10),bool) if layout=='full' else (
        np.eye(10,dtype=bool) if layout=='diagonal' else np.random.default_rng(7).random((10,10))>.3)
    mask=mask[:,::-1]  # non-contiguous input is also authoritative
    expected=np.zeros_like(mask)
    queue=deque([seed])
    while queue:
        r,c=queue.popleft()
        if 0<=r<10 and 0<=c<10 and mask[r,c] and not expected[r,c]:
            expected[r,c]=True
            queue.extend(((r-1,c),(r+1,c),(r,c-1),(r,c+1)))
    assert np.array_equal(connected_mask(mask,seed),expected)


@pytest.mark.parametrize('angle', [0., .17, -1.4])
@pytest.mark.parametrize('local', [True, False])
def test_batched_approach_keeps_all_cells_and_exact_scalar_ranking(angle, local):
    node,inputs=adaptive_fixture();g=inputs[0]
    g.info.origin.orientation.z=math.sin(angle/2);g.info.origin.orientation.w=math.cos(angle/2)
    mask=np.zeros((g.info.height,g.info.width),bool);mask[5:20,5:20]=True
    robot=node._grid_to_world(10,10,g.info)
    xy=node._grid_to_world(10 if local else 35,10,g.info)
    frontier=Frontier(xy,10)
    desired=(xy[0]+node._approach_dist_m,xy[1])
    col,row=node._world_to_grid(*desired,g.info)
    span=math.ceil(node._goal_search_m/g.info.resolution)
    expected=[]
    for r in range(5,20):
        for c in range(5,20):
            if row-span<=r<=row+span and col-span<=c<=col+span:
                x,y=node._grid_to_world(c,r,g.info)
                expected.append((math.hypot(x-desired[0],y-desired[1]),x,y))
    actual=node._frontier_approach_goal(frontier,robot,g,search_mask=mask,
        approach_direction=(1.,0.),return_choices=True)
    assert actual==tuple((x,y) for _,x,y in sorted(expected))


def test_recorded_public_selection_keeps_capped_history_and_finds_native_query():
    node,inputs,policy=frozen('ap06_b207_terminal_selection')
    before=copy.deepcopy(policy.attempts)
    chosen=node._metric_select(inputs,policy,.3)
    assert len(chosen)==1 and chosen[0].requires_nav2_plan
    assert (chosen[0].x,chosen[0].y,chosen[0].yaw)==pytest.approx((2.734999938867986,-.42499999050050974,0.))
    for key,attempt in before.items():
        assert policy.attempts[key]==attempt  # no history reset/implicit attempt
    assert policy.attempts['metric-task-7'].tries==3


@pytest.mark.parametrize('blocked', [True, False])
def test_side_query_respects_cooldown_before_expensive_geometry(monkeypatch, blocked):
    node,inputs,policy=frozen('ap06_b207_terminal_selection')
    attempt=policy.attempts['metric-task-3']
    attempt.retry_after=time.monotonic()+(30. if blocked else -1.)
    frontier=Frontier(attempt.frontier_xy,10)
    goal=attempt.target_xy
    node._frontier_approach_goal=lambda *_,**__: (goal,)
    calls=[]
    node._metric_route=lambda *_,**__: calls.append(True)
    node._metric_robot_side_observation(inputs,frontier,policy,node._metric_scope_mask(inputs),time.monotonic())
    assert bool(calls) is not blocked
    assert attempt.tries==1 and attempt.reason=='proposal_rejected'
