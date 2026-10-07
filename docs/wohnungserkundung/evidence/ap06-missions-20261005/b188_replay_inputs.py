"""Same recorded B186 decision inputs; geometry/timing only, no live health."""
import sys
sys.path.insert(0, '/evidence/ap06-repo/src/explore')
import base64,cProfile,hashlib,io,json,pstats,time
from pathlib import Path
import numpy as np
from rclpy.serialization import deserialize_message
from nav_msgs.msg import OccupancyGrid
from explore.explore_node import ExploreNode
from explore.metric_frontier_runtime import MetricInputs
from explore.portal_memory import PortalMapContext,Point2D
from explore.exploration_scope import AuthorizedExplorationScope
from explore.portal_source_adapter import PortalSourceCorrelation

root=Path('/evidence/ap06-missions-20261005')
source=root/'mission-b-v186-acquisition/input-decisions.jsonl'
records=[json.loads(l) for l in source.read_text().splitlines()]
node=ExploreNode.__new__(ExploreNode)
context=PortalMapContext('diagnostic','b186','map')
node._metric_scope=AuthorizedExplorationScope('b186',context,tuple(Point2D(*p) for p in records[0]['scope']))
node._metric_bounds=tuple(records[0]['bounds'])
node._metric_start_egress_enabled=True;node._metric_egress=None
node._metric_egress_expired=False;node._metric_body_anchor_expired=False
node._wohnungserkundung_evidence_max_cells=1000000;node._metric_status={}
results=[];profile=cProfile.Profile()
for index,row in enumerate(records):
 if 'raw_cdr' not in row:continue
 raw,cost=[deserialize_message(base64.b64decode(row[k]),OccupancyGrid) for k in ('raw_cdr','cost_cdr')]
 a=np.asarray(raw.data).reshape(raw.info.height,raw.info.width)
 b=np.asarray(cost.data).reshape(cost.info.height,cost.info.width)
 values=MetricInputs((raw,PortalSourceCorrelation(context,0,'diagnostic',1),tuple(row['pose']),a==0,np.zeros_like(a,bool),cost,(b>=0)&(b<100)),row['reference'],row['physical_motion'])
 began=time.perf_counter();profile.enable();node._metric_prepare_egress(values);profile.disable();elapsed=time.perf_counter()-began
 results.append(dict(index=index,elapsed_s=elapsed,original_full_inputs_s=row['duration_s'],reference=row['reference'],pose=row['pose'],
  valid=[e.valid for e in node._metric_egress],unknown=[int(e.unknown.sum()) for e in node._metric_egress],
  retained=[int(e.fixed.unknown.sum()) for e in node._metric_egress],reasons=[e.reason for e in node._metric_egress]))
stream=io.StringIO();pstats.Stats(profile,stream=stream).sort_stats('cumulative').print_stats(25)
(root/'b188-profile.txt').write_text(stream.getvalue())
(root/'b188-result.json').write_text(json.dumps(dict(source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),rows=results),indent=2)+'\n')
print(stream.getvalue());print(json.dumps(results))
