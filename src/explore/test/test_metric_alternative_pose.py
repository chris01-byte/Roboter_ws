"""A recorded unresolved C32 boundary needs another pose, never path bypass."""
import json
import math
from dataclasses import replace
from pathlib import Path
import time
import numpy as np
from geometry_msgs.msg import PoseStamped
from nav_msgs.msg import Path as NavPath
from explore.metric_frontier import known_safe_mask
from explore.explore_node import Frontier
from explore.metric_frontier_candidates import LidarView
from explore.metric_checkpoint import restore_policy
from explore.portal_memory import PortalMapContext, Point2D
from explore.portal_source_adapter import raw_map_portal_source_from_values
from explore.exploration_scope import AuthorizedExplorationScope
from test_metric_frontier import adaptive_fixture


def fixture():
    data=Path(__file__).parent/'data'
    arrays=np.load(data/'ap06_remaining_frontier.npz')
    meta=json.loads((data/'ap06_remaining_frontier.json').read_text())
    node,inputs=adaptive_fixture()
    for index,name in ((0,'raw'),(5,'cost')):
        grid=inputs[index];geometry=meta[name+'_geometry'];array=arrays[name]
        grid.info.height,grid.info.width=array.shape;grid.info.resolution=geometry['resolution']
        grid.info.origin.position.x,grid.info.origin.position.y=geometry['origin']
        grid.data=array.ravel().tolist()
    state=meta['checkpoint'];context=PortalMapContext(**state['context'])
    source=raw_map_portal_source_from_values(**node._metric_grid_values(inputs[0]))
    assert source.fingerprint==state['fingerprint']
    inputs[1]=replace(inputs[1],context=context,fingerprint=source.fingerprint)
    inputs[2]=tuple(meta['pose'])
    node._metric_scope=AuthorizedExplorationScope(state['scope']['scope_id'],context,
        tuple(Point2D(*xy) for xy in state['scope']['vertices']))
    origin=meta['raw_geometry']['origin']
    inputs[3],inputs[4]=known_safe_mask(arrays['raw'],node._metric_scope,inputs[1],origin,0.,
        inputs[0].info.resolution,node._goal_clearance_m)
    inputs[6]=(arrays['cost']>=0)&(arrays['cost']<100)
    node._global_costmap=inputs[5]
    node._metric_start_egress_enabled=False;node._metric_nav_path=None
    node._metric_candidate_source='boundary_samples';node._metric_path_validation='rpp_rollout'
    # Given finite angular coverage from the real C27 synthetic scan. It is
    # geometry input only, never a C32 observation receipt or health proof.
    node._metric_observation_view=lambda:LidarView((.245,0.,math.pi/2),arrays['angles'],4.,.05)
    policy,_=restore_policy(state,time.monotonic(),state['saved_wall_time'])
    return node,inputs,policy


def test_remaining_real_boundary_yields_safe_pose_and_still_requires_native_path():
    node,inputs,policy=fixture()
    before=[bytes(np.asarray(inputs[i].data,dtype=np.int8)) for i in (0,5)]
    candidates=node._metric_select(inputs,policy,.3)
    assert candidates, node._frontier_rank_stats
    candidate=candidates[0]
    assert candidate.requires_nav2_plan and candidate.observation_points
    assert node._frontier_rank_stats['alternative_approach_pose_requires_native_plan']
    # The original local .3-m approach search remains the entire search.
    assert (candidate.x,candidate.y) in node._frontier_approach_goal(
        Frontier(candidate.frontier_xy,1),
        inputs[2][:2],inputs[0],search_mask=inputs[4],approach_direction=(0.,-1.),return_choices=True)
    assert node._metric_nav2_proposal(inputs,(candidate.x,candidate.y),candidate.yaw)
    assert node._metric_waypoints_clear(inputs,candidate.route,candidate.yaw) is None
    path=NavPath();path.header.frame_id='map'
    for x,y in candidate.route:
        pose=PoseStamped();pose.pose.position.x=x;pose.pose.position.y=y
        pose.pose.orientation.z=math.sin(candidate.yaw/2);pose.pose.orientation.w=math.cos(candidate.yaw/2)
        path.poses.append(pose)
    assert node._metric_validate_nav_plan(inputs,path,candidate) is None
    assert [bytes(np.asarray(inputs[i].data,dtype=np.int8)) for i in (0,5)]==before
