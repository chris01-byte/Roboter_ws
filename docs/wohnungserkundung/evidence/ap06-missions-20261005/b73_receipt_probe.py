"""Reconstruct only original measured gains, test actual observation identity.
No counters/reset/health/acceptance; original frames/scans remain frozen.
"""
import b73_selection_probe as frozen
import inspect,textwrap,types,math,time,json
from explore.metric_progress import ObservationBaseline,measured_gain
from explore.metric_frontier import MetricTaskPolicy
from explore.metric_frontier_runtime import MetricFrontierRuntime
import explore.metric_frontier as policy_module
import explore.metric_frontier_runtime as runtime
from pathlib import Path
receipts={}
for dep,before_index,after_index in ((1,1,2),(2,2,3)):
 before=frozen.pickle.loads((frozen.root/('selection-object-'+str(before_index)+'.pickle')).read_bytes());after=frozen.pickle.loads((frozen.root/('selection-object-'+str(after_index)+'.pickle')).read_bytes());d=frozen.pickle.loads((frozen.root/('departure-input-'+str(dep)+'.pickle')).read_bytes())
 n,i,p=frozen.frozen(before_index);g=i[0];q=g.info.origin.orientation;s=before['scan']
 baseline=ObservationBaseline(i[1].context,i[1].source_stamp_ns,s['key'][0]*10**9+s['key'][1],g.info.resolution,math.atan2(2*q.w*q.z,1-2*q.z*q.z),d['target'].observation_points)
 gains=measured_gain(baseline,after['inputs'][0],after['inputs'][1],after['inputs'][2],after['scan'],after['mount'],n._world_to_grid,n._grid_to_world,4.)
 receipts[d['target'].task_id]=tuple(sorted(gains))
print('Original measured receipts',json.dumps(receipts),flush=True)
rows=[]
for index in (4,5,13,14):
 for variant in ('original','actual_receipts'):
  n,i,p=frozen.frozen(index)
  if variant!='original':
   original_distinct=p._distinct_observation
   for k,points in receipts.items():p.attempts[k].observed_points=points
   def distinct(self,a,points):
    stored=getattr(a,'observed_points',())
    if not stored:return original_distinct(a,points)
    return bool(points) and all(len(x)==2 and all(math.isfinite(v) for v in x) and all(math.dist(x,y)>self.radius for y in stored) for x in points)
   p._distinct_observation=types.MethodType(distinct,p)
   source=textwrap.dedent(inspect.getsource(MetricTaskPolicy.eligible)).replace('all(math.dist(p, a.frontier_xy) > MAX_LOCAL_OBSERVATION_RADIUS_M+self.radius\n                    for p in points)','self._distinct_observation(a,points)')
   env=dict(policy_module.__dict__);exec(compile(source,'<actual-receipt-identity>','exec'),env);p.eligible=types.MethodType(env['eligible'],p)
   source=textwrap.dedent(inspect.getsource(MetricFrontierRuntime._metric_public_observation_in_pass)).replace('math.dist(p,a.frontier_xy)>MAX_LOCAL_OBSERVATION_RADIUS_M+policy.radius','policy._distinct_observation(a,(p,))')
   env=dict(runtime.__dict__);exec(compile(source,'<actual-receipt-view>','exec'),env);n._metric_public_observation_in_pass=types.MethodType(env['_metric_public_observation_in_pass'],n)
  start=time.monotonic();out=dict(index=index,variant=variant)
  try:out['candidates']=[dict(task=c.task_id,goal=[c.x,c.y,c.yaw],points=c.observation_points,native=c.requires_nav2_plan) for c in n._metric_select(i,p,.3)]
  except Exception as e:out['error']=str(e)
  out['seconds']=time.monotonic()-start;out['ranking']=n._frontier_rank_stats;rows.append(out);print(json.dumps(out),flush=True)
Path('/evidence/ap06-missions-20261005/b73-receipt-probe.json').write_text(json.dumps(dict(receipts=receipts,variants=rows),indent=2)+'\n')
