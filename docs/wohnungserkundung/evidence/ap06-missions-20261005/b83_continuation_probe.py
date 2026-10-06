"""Read-only original B80 native subsequent arrival plus bounded observation continuation."""
from pathlib import Path
import json,sys,math
sys.path.insert(0,'/evidence/ap06-repo/src/explore/test')
from test_metric_departure import path
from explore.metric_frontier import MetricCandidate
from explore.metric_frontier_candidates import visible_boundary_cells
import b80_frozen as recorded
n,i,p=recorded.n,recorded.inputs,recorded.policy
root=Path('/evidence/ap06-missions-20261005')
records=json.loads((root/'b81-native-corridor-probe-original/native-plans.json').read_text())
first=records[0];target=MetricCandidate('original',*first['goal'],first['goal'][:2],(),1.,0.,i[1].fingerprint,1)
r=n._metric_validate_nav_plan(i,path(first),target,public_only=True)
stop=n._metric_rollout_stop_pose(i,r,target.yaw,native_plan=True)
fi=(i[0],i[1],stop,*i[3:]);scope=n._metric_scope_mask(fi)
rows=[]
for rec in records:
 if rec.get('start_pose') is None or math.dist(rec['start_pose'][:2],stop[:2])>.0001:continue
 if rec['goal'][0]<1.8 or rec['goal'][0]>2.3:continue
 t=MetricCandidate('future',*rec['goal'],rec['goal'][:2],(),1.,0.,i[1].fingerprint,1)
 rt=n._metric_validate_nav_plan(fi,path(rec),t,public_only=True)
 if rt is None:continue
 end=n._metric_rollout_stop_pose(fi,rt,t.yaw,native_plan=True);forecast=(i[0],i[1],end,*i[3:])
 visible=visible_boundary_cells(i[0],scope,end,n._metric_observation_view())
 rows.append(dict(goal=rec['goal'],stop=end,arrival_unknown_first_hits=len(visible)))
print(json.dumps(rows,indent=2),flush=True)
(root/'b83-continuation-view.json').write_text(json.dumps(rows,indent=2))
