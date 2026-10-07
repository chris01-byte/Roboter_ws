"""Read-only exact trace identity and retained failure/plan/source evidence."""
from pathlib import Path
import gzip,hashlib,json
root=Path('/workspace/scratch/ap06-missions-20261005');summary={}
for case in ['mission-a-v238','mission-b-v239','mission-c-v240','mission-cancel-v241','mission-gyro-v242']:
 p=root/case;h=hashlib.sha256();size=0;last_fault=None;faults=[];transitions=[];state_key=None;plans=[]
 with gzip.open(p/'events.jsonl.gz','rb') as f:
  for line in f:
   h.update(line);size+=len(line);r=json.loads(line);topic=r.get('topic');data=r.get('data',{})
   if isinstance(data,str):data=json.loads(data)
   if topic=='/base_hardware/state_json':
    fault=data.get('encoder_timing_recovery',{}).get('first_timing_rejection')
    if fault and fault!=last_fault:faults.append(dict(at=r['at'],detail=fault));last_fault=fault
   elif topic=='/fusion/hwt601/status_json':
    key=(data.get('recovery_state'),data.get('reason'),data.get('latched_fault'))
    if key!=state_key:transitions.append(dict(at=r['at'],state=key[0],reason=key[1],fault=key[2]));state_key=key
   elif topic=='/plan' and case=='mission-a-v238':plans.append(r)
 meta=json.loads((p/'events.jsonl.gz.meta.json').read_text())
 assert meta['sha256']==h.hexdigest() and meta['uncompressed_bytes']==size
 result=json.loads((p/'result.json').read_text());metric=result['metric']
 summary[case]=dict(passed=result['passed'],error=result.get('error'),travel_m=result.get('travel_m'),
    arrivals=metric.get('arrivals'),observations=metric.get('observations'),
    reference=metric.get('start_reference'),chain=[{k:v for k,v in c.items() if k!='snapshot'} for c in metric.get('chain',[])],
    transitions=transitions,source_faults=faults,plans=plans,trace_raw_sha256=h.hexdigest(),trace_raw_bytes=size)
 print(case,size,'verified',flush=True)
rows=[json.loads(line) for line in (root/'b238-parent-cpu.jsonl').read_text().splitlines()]
summary['parent_cpu']={k:rows[-1][k]-rows[0][k] for k in ('nr_throttled','throttled_usec','usage_usec')}
for case in ['mission-c-v240']:
 for fault in summary[case]['source_faults']:
  at=fault['at'];around=[r for r in rows if abs(r['at']-at)<2.]
  if around:fault['nearby_throttled_usec_delta']=around[-1]['throttled_usec']-around[0]['throttled_usec']
  source=[json.loads(line) for line in (root/case/'device_executor_latency.jsonl').read_text().splitlines()]
  fault['nearby_device_pauses']=[v for v in source if abs(v['end']-at)<2.]
(root/'b243-original-failure-summary.json').write_text(json.dumps(summary,indent=2)+'\n')
