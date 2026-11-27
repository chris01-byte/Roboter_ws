from pathlib import Path
import pickle,json,math
root=Path('/evidence/ap06-missions-20261005/mission-b-v76-capture');rows=[]
for k in range(1,33):
 d=pickle.loads((root/('selection-object-'+str(k)+'.pickle')).read_bytes());p=d['policy']
 row=dict(index=k,at=d['captured_monotonic'],pose=d['inputs'][2],tasks={key:dict(tries=a['tries'],reason=a['reason'],target=a['target_xy']) for key,a in p['tasks'].items() if a['tries']})
 rows.append(row);print(json.dumps(row),flush=True)
for p in sorted(root.glob('departure-input-*.pickle')):
 d=pickle.loads(p.read_bytes());print(p.name,d.keys());print('target',d['target'],'pose',d['inputs'][2])
Path('/evidence/ap06-missions-20261005/b76-original-inventory.json').write_text(json.dumps(rows,indent=2)+'\n')
