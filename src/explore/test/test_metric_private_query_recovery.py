"""Actual adaptive parent retains rejection of an unsafe private start turn."""
import copy,math
import numpy as np
import pytest
from geometry_msgs.msg import PoseStamped
from nav_msgs.msg import Path
from test_metric_progress import parent_fixture
from test_metric_map_lifecycle import status

def test_actual_private_query_rejection_is_bounded(monkeypatch):
    node,grid,clock,parent,terminal=parent_fixture(monkeypatch,'open')
    node._metric_start_strategy='adaptive';node._metric_path_validation='rpp_rollout'
    node._metric_start_egress_enabled=True;node._metric_egress=None
    node._metric_egress_identity=None;node._metric_egress_expired=False
    grid=copy.deepcopy(grid);a=np.asarray(grid.data).reshape(100,100).copy();a[18:23,8]=-1
    grid.data=a.ravel().tolist();grid.header.stamp.nanosec+=10_000_000;clock[0]+=.01
    node._on_map(grid);node._on_metric_map_status(status(grid,accepted=3,observed=3,when=100.03))
    node._max_frontier_goals=1
    queries=[];proofs=[];validate=node._metric_validate_nav_plan
    def checked(*a,**k):
        result=validate(*a,**k);proofs.append((result,node._metric_last_route_rejection));return result
    node._metric_validate_nav_plan=checked
    def planner(target,stopped):
        assert not stopped();queries.append(target)
        inputs=node._metric_inputs(active=True)
        assert node._metric_private_start_needed(inputs)
        assert all(e.valid for e in node._metric_egress)
        path=Path();path.header.frame_id='map'
        for x,y in (target.route[0],(target.route[0][0]-.5,target.route[0][1]),(target.x,target.y)):
            pose=PoseStamped();pose.pose.position.x=x;pose.pose.position.y=y
            pose.pose.orientation.z=math.sin(target.yaw/2);pose.pose.orientation.w=math.cos(target.yaw/2);path.poses.append(pose)
        return path,None
    node._metric_request_nav_plan=planner
    node._navigate_to=lambda *a,**k:pytest.fail('Unsafe start cannot move')
    node._prealign_to_goal=lambda *a,**k:pytest.fail('Unsafe start cannot align')
    result=node._execute_metric_frontier(parent,10.,.3)
    assert len(queries)==1
    assert proofs==[(None,'start_egress_in_place_turn')]
    assert not result.success and terminal==['abort']
    assert node._metric_status['first_trigger']['reason']=='nav2_plan_start_egress_in_place_turn'
    assert node._metric_status['terminal_reason']=='budget_exhausted'
    assert node._metric_status['chain'][0]['decision']=='proposal_rejected'
    assert node._metric_status['chain'][0]['child_dispatched'] is False
    assert node._metric_status['failures']==0
    assert node._metric_checkpoint['attempts']==1
