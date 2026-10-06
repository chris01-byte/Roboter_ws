"""Current boundary samples of one task share proved geometry, never budgets."""
import copy
import json
import math
from pathlib import Path

from geometry_msgs.msg import PoseStamped
from nav_msgs.msg import Path as NavPath
from explore.metric_frontier import MetricCandidate
from test_metric_public_cooldown import frozen

NAME='ap06_b102_terminal_public_task'


def test_terminal_public_view_uses_existing_task_without_changing_history():
    n,inputs,p=frozen(NAME);before=copy.deepcopy(p.attempts)
    choices=n._metric_select(inputs,p,.3)
    assert choices and choices[0].task_id=='metric-task-3'
    candidate=choices[0]
    assert not candidate.requires_nav2_plan and len(candidate.observation_points)>=1
    assert math.dist(candidate.frontier_xy,p.attempts[candidate.task_id].frontier_xy)<p.radius
    for key,attempt in before.items():assert p.attempts[key]==attempt
    assert p.attempts['metric-task-1'].tries==3 and p.attempts['metric-task-1'].completed
    assert p.attempts['metric-task-2'].tries==3
    assert p.attempts['metric-task-3'].tries==1 and not p.attempts['metric-task-3'].completed


def test_same_task_view_cannot_renew_an_exhausted_spatial_task():
    n,inputs,p=frozen(NAME);p.attempts['metric-task-3'].tries=3
    choices=n._metric_select(inputs,p,.3)
    assert all(c.task_id!='metric-task-3' for c in choices)
    assert p.attempts['metric-task-3'].tries==3 and p.attempts['metric-task-3'].failures==0


def test_actual_native_path_retains_arrival_view_and_turning_refuge():
    n,inputs,p=frozen(NAME)
    meta=json.loads((Path(__file__).parent/'data'/NAME).with_suffix('.json').read_text())
    c=meta['expected_candidate']
    target=MetricCandidate(c['task'],*c['goal'],tuple(c['frontier']),(),1.,0.,
        inputs[1].fingerprint,inputs[1].map_revision,False,tuple(tuple(v) for v in c['points']))
    planned=meta['native_plans'][0];assert not planned['error']
    path=NavPath();path.header.frame_id='map'
    for x,y in planned['points']:
        pose=PoseStamped();pose.header.frame_id='map';pose.pose.position.x=x;pose.pose.position.y=y
        pose.pose.orientation.z=math.sin(target.yaw/2);pose.pose.orientation.w=math.cos(target.yaw/2)
        path.poses.append(pose)
    route=n._metric_validate_nav_plan(inputs,path,target,public_only=True)
    assert route is not None
    assert n._metric_native_observation_ready(inputs,route,target,inputs,target.observation_points)
    stop=n._metric_rollout_stop_pose(inputs,route,target.yaw,native_plan=True)
    assert n._metric_scan_geometry_ready((inputs[0],inputs[1],stop,*inputs[3:]))
