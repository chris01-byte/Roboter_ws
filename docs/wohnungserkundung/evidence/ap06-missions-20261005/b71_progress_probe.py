"""Own synthetic B70 component data; no source health or motion authority."""
import json,math,pickle,sys
from pathlib import Path
import numpy as np
from explore.explore_node import ExploreNode
from explore.metric_progress import ObservationBaseline,observation_complete
p=Path('/evidence/ap06-missions-20261005/mission-b-v70-capture')
dep=[pickle.loads((p/f'departure-input-{i}.pickle').read_bytes()) for i in (1,2)]
records=[]
for i in range(1,6):
 x=pickle.loads((p/f'selection-object-{i}.pickle').read_bytes());g,c=x['inputs'][:2]
 row={'selection':i,'stamp':c.source_stamp_ns,'pose':x['inputs'][2], 'tasks':{k:{z:v.get(z) for z in ['reason','completed','tries','target_xy']} for k,v in x['policy']['tasks'].items()},'original_views':[]}
 for j,y in enumerate(dep,1):
  target=y['target'];before,cor=y['inputs'][:2];q=before.info.origin.orientation
  baseline=ObservationBaseline(cor.context,cor.source_stamp_ns,0,before.info.resolution,math.atan2(2*q.w*q.z,1-2*q.z*q.z),target.observation_points)
  cells=[]
  for xy in target.observation_points:
   col,r=ExploreNode._world_to_grid(*xy,g.info)
   inside=0<=col<g.info.width and 0<=r<g.info.height
   cells.append({'xy':xy,'occupancy':int(g.data[r*g.info.width+col]) if inside else None,'alignment_m':math.dist(xy,ExploreNode._grid_to_world(col,r,g.info))})
  row['original_views'].append({'departure':j,'task':target.task_id,'points':len(cells),'newer':c.source_stamp_ns>cor.source_stamp_ns,'complete':observation_complete(baseline,g,c,ExploreNode._world_to_grid,ExploreNode._grid_to_world),'unknown':sum(z['occupancy']==-1 for z in cells),'outside':sum(z['occupancy'] is None for z in cells),'cells':cells})
 records.append(row)
print(json.dumps(records,indent=2))
