"""Independent visualization of original synthetic evidence, no product input."""
from pathlib import Path
import sys,json,numpy as np
sys.path.insert(0,'/workspace/Roboter_ws-ap06/tools/simulation')
from ap06_world import World
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
p=Path('/workspace/scratch/ap06-missions-20261005/mission-b-v75');m=np.load(p/'final_slam_map.npy');g=json.loads((p/'final_slam_map_geometry.json').read_text());result=json.loads((p/'result.json').read_text());w=World(.68,[-2.1,.45,0])
fig,ax=plt.subplots(figsize=(10,5))
a=np.where(m<0,.6,np.where(m>0,.0,1.));r=g['resolution'];x,y=g['origin'];ax.imshow(a,origin='lower',extent=[x,x+m.shape[1]*r,y,y+m.shape[0]*r],cmap='gray',vmin=0,vmax=1)
for poly in w.obstacles:
 q=w.local(poly);q=np.vstack([q,q[0]]);ax.plot(q[:,0],q[:,1],color='#3796c8',lw=1.1,ls='--')
rows=np.asarray([json.loads(line) for line in (p/'plant.jsonl').read_text().splitlines()]);q=w.local(rows[:,1:3]);ax.plot(q[:,0],q[:,1],color='#e46d00',lw=2,label='Gemessene Modellfahrt');ax.scatter(q[[0,-1],0],q[[0,-1],1],c=['#14733a','#be2424'],s=45,zorder=4)
ax.set(title='B75: 2 Ankünfte / 2 Beobachtungen – keine Passage, Gesamtmission negativ',xlabel='x im ursprünglichen Startbezug [m]',ylabel='y [m]');ax.legend(loc='lower right');ax.set_aspect('equal');fig.tight_layout();fig.savefig(p.parent/'b75-observed-map-and-travel.png',dpi=130)
print(p.parent/'b75-observed-map-and-travel.png')
