"""Recorded B70 selection, original vs evidence-derived partial classification.
A component query after original cooldown; no live health or mission receipt.
"""
import copy,pickle,time,sys,json
from pathlib import Path
sys.path.insert(0,'/evidence/ap06-repo/src/explore/test')
from test_metric_frontier import adaptive_fixture
from explore.metric_frontier import MetricTaskPolicy,MetricAttempt
from explore.metric_frontier_runtime import MetricInputs
from explore.metric_frontier_candidates import lidar_view
record=pickle.loads(Path('/evidence/ap06-missions-20261005/mission-b-v70-capture/selection-object-5.pickle').read_bytes())
results=[]
for partial in (False,True):
 n,_=adaptive_fixture()
 for key,value in record['attributes'].items():setattr(n,key,copy.deepcopy(value))
 n._metric_egress=copy.deepcopy(record['evidence']);n._metric_scope=record['scope'];n._metric_body_reference=lambda:record['reference'];n._metric_nav_path=None;n._metric_status={};n._visualize=False
 view=lidar_view(record['scan'],record['mount'],record['captured_monotonic'],n._door_lidar_scan_timeout,n._door_lidar_max_range);n._metric_observation_view=lambda:view
 inputs=MetricInputs(copy.deepcopy(record['inputs']),record['reference'],record['physical_motion']);n._global_costmap=inputs[5]
 p=record['policy'];policy=MetricTaskPolicy(p['radius'],p['cooldown_s'],p['retry_limit']);policy.next_id=p['next_id'];now=time.monotonic()
 for key,stored in p['tasks'].items():
  fields=dict(stored);fields['retry_after']=now+fields.pop('retry_remaining_s')-31
  policy.attempts[key]=MetricAttempt(**fields)
 if partial:
  task=policy.attempts['metric-task-4'];task.completed=False;task.reason='partially_observed'
 before={k:(a.tries,a.failures,a.completed) for k,a in policy.attempts.items()}
 start=time.monotonic();candidates=n._metric_select(inputs,policy,.3)
 out={'partial_classification':partial,'kind':'Original finite synthetic inputs, analytically elapsed original cooldown; no acceptance','seconds':time.monotonic()-start,'ranking':n._frontier_rank_stats,'candidates':[dict(task=c.task_id,goal=[c.x,c.y,c.yaw],points=c.observation_points,requires_native=c.requires_nav2_plan) for c in candidates],'counter_changes':{k:(a.tries,a.failures,a.completed) for k,a in policy.attempts.items() if k in before and before[k]!=(a.tries,a.failures,a.completed)}}
 print(json.dumps(out),flush=True);results.append(out)
Path('/evidence/ap06-missions-20261005/b71-selection-probe.json').write_text(json.dumps(results,indent=2))
