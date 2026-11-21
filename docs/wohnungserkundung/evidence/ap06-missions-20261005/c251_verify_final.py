"""Verify complete final trace bytes and terminal ownership; no result rewrite."""
import sys,json
from pathlib import Path
sys.path.insert(0,'/evidence/ap06-repo/tools/simulation')
from ap06_trace import verify_trace
root=Path('/evidence/ap06-missions-20261005');summary={}
for name in ['mission-c-v248','mission-cancel-v249','mission-gyro-v250']:
 p=root/name;meta=verify_trace(p/'events.jsonl.gz');r=json.loads((p/'result.json').read_text());m=r['metric']
 assert all(not a for a in r['action_active_at_terminal'].values())
 assert len(r['command_values_at_terminal'])==4 and all(all(v==0 for v in a) for a in r['command_values_at_terminal'].values())
 summary[name]=dict(passed=r['passed'],reason=m.get('reason'),arrivals=m.get('arrivals'),observations=m.get('observations'),
   attempts=m.get('attempts'),failures=m.get('failures'),travel_m=r['travel_m'],
   motion_binding_rejection=m.get('motion_binding_rejection'),
   chain=[{k:v for k,v in c.items() if k!='snapshot'} for c in m.get('chain',[])],
   cpu_allocation=r.get('cpu_allocation'),trace=meta,terminal_actions_empty=True,four_zero_command_chains=True)
 print(name,r['passed'],m.get('reason'),meta['uncompressed_bytes'],'verified',flush=True)
rows=[json.loads(line) for line in (root/'c248-parent-cpu.jsonl').read_text().splitlines()]
summary['cpu_accounting']={k:rows[-1][k]-rows[0][k] for k in ('nr_throttled','throttled_usec','usage_usec')}
(root/'c251-final-results.json').write_text(json.dumps(summary,indent=2)+'\n')
