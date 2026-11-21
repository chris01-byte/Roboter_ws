"""B70 finite synthetic local geometry survey, component only."""
exec(open('/evidence/ap06-missions-20261005/b71_selection_probe.py').read().split('results=[]')[0])
from explore.metric_frontier_candidates import visible_boundary_cells
from explore.explore_node import Frontier
n,_=adaptive_fixture()
for key,value in record['attributes'].items():setattr(n,key,copy.deepcopy(value))
n._metric_egress=copy.deepcopy(record['evidence']);n._metric_scope=record['scope'];n._metric_body_reference=lambda:record['reference'];n._metric_nav_path=None;n._metric_status={};n._visualize=False
view=lidar_view(record['scan'],record['mount'],record['captured_monotonic'],n._door_lidar_scan_timeout,n._door_lidar_max_range);n._metric_observation_view=lambda:view
inputs=MetricInputs(copy.deepcopy(record['inputs']),record['reference'],record['physical_motion']);n._global_costmap=inputs[5];n._metric_prepare_egress(inputs);inputs=n._metric_public_inputs(inputs)
p=record['policy'];policy=MetricTaskPolicy(p['radius'],p['cooldown_s'],p['retry_limit']);policy.next_id=p['next_id'];now=time.monotonic()
for key,stored in p['tasks'].items():
 fields=dict(stored);fields['retry_after']=now+fields.pop('retry_remaining_s')-31;policy.attempts[key]=MetricAttempt(**fields)
policy.attempts['metric-task-4'].completed=False;policy.attempts['metric-task-4'].reason='partially_observed'

raw=inputs[0];cost=inputs[5];m={}
