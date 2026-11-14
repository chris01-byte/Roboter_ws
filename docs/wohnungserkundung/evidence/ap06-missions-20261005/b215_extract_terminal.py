from pathlib import Path
import json,gzip,hashlib,subprocess
root=Path('/workspace/scratch/ap06-missions-20261005');p=root/'mission-b-v214';tfs={};plans=[];h=hashlib.sha256();size=0
with gzip.open(p/'events.jsonl.gz','rb') as f:
 for line in f:
  h.update(line);size+=len(line);r=json.loads(line)
  if r.get('topic')=='/tf':
   t=r['transform'];tfs[t['parent']+'->'+t['child']]=t
  if r.get('topic')=='/plan':plans.append(r)
meta=json.loads((p/'events.jsonl.gz.meta.json').read_text());assert meta['sha256']==h.hexdigest() and meta['uncompressed_bytes']==size
s="from pathlib import Path;p=Path('/evidence/ap06-missions-20261005/mission-b-v214/checkpoints/amadeus');print(list(p.glob('*/state-*.json'))[0].read_text())"
state=json.loads(subprocess.check_output(['docker','exec','ap03-nav2','python3','-c',s]))
(root/'b215-terminal-public-source.json').write_text(json.dumps(dict(kind='Terminal B214 public geometry and preserved original task history; no pre-failure live health claim',transforms=tfs,checkpoint=state,plans=plans[-20:],event_raw_sha256=h.hexdigest(),event_raw_bytes=size),indent=2))
print('verified',size,'bytes;',len(plans),'actual native plans')
