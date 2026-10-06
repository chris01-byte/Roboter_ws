"""Read-only geometry variant; source-derived Nav2 weights, no product application."""
from pathlib import Path
import sys,json,copy,numpy as np
sys.path.insert(0,'/evidence/ap06-repo/src/explore/test')
from test_metric_departure import path
from explore.metric_frontier import MetricCandidate
import b73_local_frozen as recorded
n,inputs,p=recorded.n,recorded.inputs,recorded.policy
b=Path('/evidence/ap06-missions-20261005');original=json.loads((b/'b77-native-local-probe-original/native-plans.json').read_text())[0];rows=[]
for refinements in (1,5):
 data=np.array(original['points']);steps=[]
 for repeat in range(refinements):
  q=data.copy()
  for iteration in range(1000):
   change=0
   for i in range(1,len(q)-1):
    old=q[i].copy();q[i]+=.2*(data[i]-q[i])+.3*(q[i-1]+q[i+1]-2*q[i]);change+=abs(q[i]-old).sum()
   if change<1e-10:break
  data=q;steps.append(iteration)
 record=copy.deepcopy(original);record['points']=data.tolist();target=MetricCandidate('original-probe',*record['goal'],(1.304999970830977,.13499999698251486),(),1.,0.,inputs[1].fingerprint,1)
 route=n._metric_validate_nav_plan(inputs,path(record),target,public_only=True)
 row=dict(refinements=refinements,valid=route is not None,rejection=n._metric_last_route_rejection,iterations=steps)
 rows.append(row);print(json.dumps(row),flush=True)
 (b/('b77-smoothed-path-'+str(refinements)+'.json')).write_text(json.dumps(record,indent=2)+'\n')
(b/'b77-smoothing-probe.json').write_text(json.dumps(rows,indent=2)+'\n')
