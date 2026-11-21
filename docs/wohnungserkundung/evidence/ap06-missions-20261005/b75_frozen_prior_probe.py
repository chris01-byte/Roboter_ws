from b73_selection_probe import frozen
import time,json,copy
from pathlib import Path
rows=[]
for index in (4,5,13,14):
 n,i,p=frozen(index);before=copy.deepcopy(p.attempts);started=time.monotonic();row={'original_index':index}
 try:
  c=n._metric_select(i,p,.3);row['candidates']=[dict(task=a.task_id,goal=[a.x,a.y,a.yaw],points=len(a.observation_points),native=a.requires_nav2_plan) for a in c]
 except Exception as ex:row['error']=str(ex)
 row['seconds']=time.monotonic()-started;row['pose']=i[2];row['ranking']=n._frontier_rank_stats;row['counter_changes']={k:(a.tries,a.failures,a.completed) for k,a in p.attempts.items() if k in before and before[k]!=a}
 rows.append(row);print(json.dumps(row),flush=True)
Path('/evidence/ap06-missions-20261005/b75-frozen-prior-probe.json').write_text(json.dumps(rows,indent=2)+'\n')
