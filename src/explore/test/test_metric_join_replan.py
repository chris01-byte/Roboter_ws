"""Real parent/correlator: stop a child before bounded exact-map revalidation."""
import copy
from geometry_msgs.msg import PoseStamped
from nav_msgs.msg import Path
import pytest
from test_metric_progress import parent_fixture
from test_metric_map_lifecycle import status


@pytest.mark.parametrize('fault',['none','epoch','retry_budget','deferred_scan','planning_after_join'])
def test_raw_first_drive_stop_replans_same_task_without_reset(monkeypatch,fault):
    n,g,clock,parent,terminal=parent_fixture(monkeypatch,'open')
    n._max_frontier_goals=2 if fault!='retry_budget' else 5
    if fault=='retry_budget':n._metric_retry_limit=1
    if fault=='planning_after_join':n._max_failed_goals=1
    if fault == 'deferred_scan':
        n._initial_scan_enabled = True; n._metric_start_strategy = 'adaptive'
        g = copy.deepcopy(g)
        g.data[20*g.info.width+6] = -1  # behind the forward body, inside its full rotation
        clock[0] += .02; g.header.stamp.nanosec = int((clock[0]-10)*1e9)
        n._on_map(g); n._on_metric_map_status(status(g, accepted=3, observed=3, when=100+clock[0]-10))
        n._scan_in_place = lambda **_: pytest.fail('a pending observation task must not enter its deferred scan')
    planned=[];starts=[];stops=[]
    def planner(target,*_):
        planned.append(target)
        path=Path();path.header.frame_id='map';path.header.stamp.sec=100
        route = target.route
        if fault == 'planning_after_join' and len(planned) > 1:
            route = (target.route[0], (3., .05), (target.x, target.y))
        for x,y in route:
            p=PoseStamped();p.pose.position.x=x;p.pose.position.y=y;p.pose.orientation.w=1.
            path.poses.append(p)
        return path,None
    n._metric_request_nav_plan=planner
    n._prealign_to_goal=lambda *_,**__:('skipped',)
    def navigate(*_,stop_requested,**__):
        target=planned[-1];starts.append(clock[0]);clock[0]+=.1
        if len(starts)==1 or fault=='retry_budget':
            newer=copy.deepcopy(g)
            for xy in target.observation_points:
                col,row=n._world_to_grid(*xy,newer.info)
                newer.data[row*newer.info.width+col]=0
            # Change real content each attempt, and give its original stamp.
            newer.data[80*newer.info.width+80]=len(starts)*10
            newer.header.stamp.nanosec=int((clock[0]-10)*1e9)
            n._on_map(newer)
            stops.append(stop_requested())
            n._on_metric_map_status(status(newer,accepted=2+len(starts)+(fault=='deferred_scan'),
                observed=2+len(starts)+(fault=='deferred_scan'),when=100+clock[0]-10))
            if fault=='epoch':n._metric_fault='map_epoch_changed'
            return 'canceled'  # terminal peer result; no moving old child
        stops.append(stop_requested())
        n._robot_pose_sample=lambda:((target.x,target.y,target.yaw),0.)
        return 'success'
    n._navigate_to=navigate
    result=n._execute_metric_frontier(parent,10.,.3)
    assert terminal==['abort'] and not result.success
    assert stops and stops[0] is True, n._metric_status
    if fault in ('none', 'deferred_scan'):
        assert stops==[True,False] and len(planned)==2
        assert planned[0].task_id==planned[1].task_id
        assert n._metric_status['attempts']==2
        assert n._metric_status['arrivals']==n._metric_status['observations']==1
        assert n._metric_status['chain'][0]['decision']=='map_join_revalidate'
        assert n._metric_status['chain'][1]['decision']=='observed'
        assert n._metric_checkpoint['policy']['tasks'][planned[0].task_id]['tries']==2
    elif fault=='planning_after_join':
        assert stops == [True] and len(planned) == 2
        assert planned[0].task_id == planned[1].task_id
        assert n._metric_status['reason'] == 'failure_budget_exhausted'
        assert n._metric_status['failures'] == 1
        assert n._metric_status['chain'][-1]['decision'] == 'route_invalidated'
        task = n._metric_checkpoint['policy']['tasks'][planned[0].task_id]
        assert task['tries'] == 2 and task['failures'] == 1
        assert not task['completed']
    elif fault=='epoch':
        assert len(planned)==1 and n._metric_status['reason']=='map_epoch_changed'
        assert n._metric_status['observations']==0
    else:
        assert stops==[True,True] and len(planned)==2
        assert planned[0].task_id==planned[1].task_id
        assert n._metric_status['reason']=='map_status_join_retry_budget_exhausted'
        assert n._metric_status['observations']==0
