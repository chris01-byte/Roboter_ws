import os,sys,json,time,cProfile,pstats,math
from pathlib import Path
import numpy as np
from rclpy.serialization import deserialize_message
from nav_msgs.msg import OccupancyGrid
from sensor_msgs.msg import LaserScan
sys.path.insert(0,'/evidence/ap06-repo/src/explore/test')
from test_metric_frontier import adaptive_fixture
from explore.metric_frontier import known_safe_mask
from explore.metric_frontier_candidates import LidarView
from explore.metric_checkpoint import restore_policy
from explore.portal_memory import PortalMapContext,Point2D
from explore.exploration_scope import AuthorizedExplorationScope
from explore.portal_source_adapter import PortalSourceCorrelation,raw_map_portal_source_from_values
base=Path('/evidence/ap06-missions-20261005/mission-c-v44');out=Path('/evidence/ap06-missions-20261005/c44-offline-selection');out.mkdir(exist_ok=True)
r=json.loads((base/'result.json').read_text());s=json.loads(Path(r['checkpoint_after_save']['path']).read_text())['state']
policy,_=restore_policy(s,time.monotonic(),s['saved_wall_time'])
raw=deserialize_message((base/'final_raw_map.cdr').read_bytes(),OccupancyGrid);cost=deserialize_message((base/'final_costmap.cdr').read_bytes(),OccupancyGrid)
scan=deserialize_message((base/'final_scan.cdr').read_bytes(),LaserScan)
n,_=adaptive_fixture();ctx=PortalMapContext(**s['context']);source=raw_map_portal_source_from_values(**n._metric_grid_values(raw));c=PortalSourceCorrelation(ctx,1,source.fingerprint,source.source_stamp_ns)
scope=AuthorizedExplorationScope(s['scope']['scope_id'],ctx,tuple(Point2D(*xy) for xy in s['scope']['vertices']))
a=np.asarray(raw.data).reshape(raw.info.height,raw.info.width);known,safe=known_safe_mask(a,scope,c,(raw.info.origin.position.x,raw.info.origin.position.y),0.,raw.info.resolution,.28)
ca=np.asarray(cost.data).reshape(cost.info.height,cost.info.width);pose=tuple(r['metric']['arrival_check']['pose']);inputs=[raw,c,pose,known,safe,cost,(ca>=0)&(ca<100)]
finite=np.isfinite(scan.ranges)&(np.asarray(scan.ranges)>=scan.range_min)&(np.asarray(scan.ranges)<=scan.range_max)
view=LidarView((.245,0.,math.pi/2),scan.angle_min+np.flatnonzero(finite)*scan.angle_increment,4.,scan.range_min)
n._metric_scope=scope;n._global_costmap=cost;n._metric_observation_view=lambda:view
n._metric_candidate_source='boundary_samples';n._metric_path_validation='rpp_rollout';n._prealign_handoff_tolerance=.02
n._metric_start_egress_enabled=True;n._metric_egress_expired=True;n._metric_egress=None;n._metric_body_reference=lambda:None
n._metric_body_anchor_expired=True;n._metric_nav_path=None
p=cProfile.Profile();began=time.monotonic()
try:
 candidates=p.runcall(n._metric_select,inputs,policy,.3)
 print('CANDIDATES',[(q.task_id,q.x,q.y,q.yaw) for q in candidates])
except Exception as e:print('ERROR',repr(e))
finally:
 p.dump_stats(str(out/'selection.prof'));print('SECONDS',time.monotonic()-began,'RANKING',n._frontier_rank_stats)
 pstats.Stats(p).sort_stats('cumulative').print_stats(35)
 (out/'metadata.json').write_text(json.dumps(dict(kind='actual later C44 terminal rasters, finite actual last scan angles and saved policy; offline geometry only, no health or whole-mission claim',pose=pose,fingerprint=source.fingerprint,saved_fingerprint=s['fingerprint']),indent=2))
