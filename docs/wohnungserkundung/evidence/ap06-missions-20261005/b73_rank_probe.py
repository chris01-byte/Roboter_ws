"""Original B73 selections, unchanged policy and geometry; component only."""
import copy,pickle,sys,time,json,inspect,textwrap,types
from pathlib import Path
sys.path.insert(0,'/evidence/ap06-repo/src/explore/test')
from test_metric_frontier import adaptive_fixture
from explore.metric_frontier import MetricTaskPolicy,MetricAttempt
from explore.metric_frontier_runtime import MetricInputs,MetricFrontierRuntime
from explore.metric_frontier_candidates import lidar_view
import explore.metric_frontier_runtime as runtime
root=Path('/evidence/ap06-missions-20261005/mission-b-v73-capture')
def frozen(index):
 record=pickle.loads((root/('selection-object-'+str(index)+'.pickle')).read_bytes())
 n,_=adaptive_fixture()
 for k,v in record['attributes'].items():setattr(n,k,copy.deepcopy(v))
 n._metric_egress=copy.deepcopy(record['evidence']);n._metric_scope=record['scope'];n._metric_body_reference=lambda:record['reference'];n._metric_nav_path=None;n._metric_status={};n._visualize=False
 view=lidar_view(record['scan'],record['mount'],record['captured_monotonic'],n._door_lidar_scan_timeout,n._door_lidar_max_range);n._metric_observation_view=lambda:view
 inputs=MetricInputs(copy.deepcopy(record['inputs']),record['reference'],record['physical_motion']);n._global_costmap=inputs[5]
 p=record['policy'];policy=MetricTaskPolicy(p['radius'],p['cooldown_s'],p['retry_limit']);policy.next_id=p['next_id'];now=time.monotonic()
 for k,a in p['tasks'].items():
  d=dict(a);d['retry_after']=now+d.pop('retry_remaining_s');policy.attempts[k]=MetricAttempt(**d)
 return n,inputs,policy
if __name__=='__main__':
 rows=[]
 for index in (4,5,13,14):
  for variant in ('original','rank_within_same_budget'):
   n,i,p=frozen(index)
   if variant!='original':
    source=textwrap.dedent(inspect.getsource(MetricFrontierRuntime._metric_public_observation_in_pass)).replace('fallback = None','fallback = None\n    refuge = None').replace('return fallback','return refuge or fallback').replace('return candidate','if refuge is None or candidate.cost < refuge.cost:\n                            refuge = candidate\n                        continue')
    env=dict(runtime.__dict__);exec(compile(source,'<component-variant>','exec'),env);n._metric_public_observation_in_pass=types.MethodType(env['_metric_public_observation_in_pass'],n)
   before={k:(a.tries,a.failures,a.completed) for k,a in p.attempts.items()}
   now=time.monotonic();out=dict(index=index,variant=variant)
   try:
    c=n._metric_select(i,p,.3);out['candidates']=[dict(task=a.task_id,goal=[a.x,a.y,a.yaw],points=a.observation_points,native=a.requires_nav2_plan) for a in c]
   except Exception as e:out['error']=str(e)
   out['seconds']=time.monotonic()-now;out['ranking']=n._frontier_rank_stats;out['counter_changes']={k:(a.tries,a.failures,a.completed) for k,a in p.attempts.items() if k in before and before[k]!=(a.tries,a.failures,a.completed)}
   rows.append(out);print(json.dumps(out),flush=True)
 Path('/evidence/ap06-missions-20261005/b73-rank-probe.json').write_text(json.dumps(rows,indent=2)+'\n')
