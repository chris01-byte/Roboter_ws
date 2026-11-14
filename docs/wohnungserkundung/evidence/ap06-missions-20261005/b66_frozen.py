import sys,math,json,numpy as np
from pathlib import Path
from rclpy.serialization import deserialize_message
from nav_msgs.msg import OccupancyGrid,Path as NavPath
from geometry_msgs.msg import PoseStamped
sys.path.insert(0,'/evidence/ap06-repo/src/explore/test')
from test_metric_frontier import adaptive_fixture
from explore.metric_frontier import known_safe_mask,MetricCandidate,rpp_trajectory,footprint_cells,footprint_poses_clear
from explore.portal_memory import PortalMapContext,Point2D
from explore.portal_source_adapter import PortalSourceCorrelation,raw_map_portal_source_from_values
from explore.exploration_scope import AuthorizedExplorationScope
r=Path('/evidence/ap06-missions-20261005');b=r/'mission-b-v66';d=json.loads((b/'result.json').read_text());m=d['metric'];s=json.loads(Path(m['persistence']['path']).read_text())['state']
n,_=adaptive_fixture();ctx=PortalMapContext(**s['context']);n._metric_scope=AuthorizedExplorationScope(s['scope']['scope_id'],ctx,tuple(Point2D(*xy) for xy in s['scope']['vertices']))
raw=deserialize_message((b/'final_raw_map.cdr').read_bytes(),OccupancyGrid);cost=deserialize_message((b/'final_costmap.cdr').read_bytes(),OccupancyGrid)
a=np.asarray(raw.data).reshape(raw.info.height,raw.info.width);ca=np.asarray(cost.data).reshape(cost.info.height,cost.info.width)
source=raw_map_portal_source_from_values(**n._metric_grid_values(raw));cor=PortalSourceCorrelation(ctx,1,source.fingerprint,source.source_stamp_ns)
known,safe=known_safe_mask(a,n._metric_scope,cor,(raw.info.origin.position.x,raw.info.origin.position.y),0.,raw.info.resolution,.28)
n._metric_path_validation='rpp_rollout';n._prealign_handoff_tolerance=.02;n._metric_start_egress_enabled=False
pose=tuple(m['arrival_check']['pose']);inputs=(raw,cor,pose,known,safe,cost,(ca>=0)&(ca<100));
from explore.metric_checkpoint import restore_policy
policy,_=restore_policy(s, __import__('time').monotonic(),s['saved_wall_time'])
n._metric_scope=n._metric_scope;n._global_costmap=cost;n._metric_nav_path=None;n._metric_status={}
