from pathlib import Path
import json,sys,numpy as np
sys.path.insert(0,'/workspace/Roboter_ws-ap06/tools/simulation')
from ap06_world import World
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
s=Path('/workspace/scratch/ap06-missions-20261005');p=s/'mission-b-v76-capture';m=np.load(p/'selection-input-32.npz')['raw'];g=json.loads((p/'selection-geometry.json').read_text())[0];r=g['resolution'];x,y=g['origin'];w=World(.68,[-2.1,.45,0]);fig,ax=plt.subplots(figsize=(11,5));ax.imshow(np.where(m<0,.6,np.where(m>0,0,1)),origin='lower',extent=[x,x+m.shape[1]*r,y,y+m.shape[0]*r],cmap='gray',vmin=0,vmax=1)
for poly in w.obstacles:
 q=w.local(poly);q=np.vstack([q,q[0]]);ax.plot(q[:,0],q[:,1],color='#3d97c9',lw=1,ls='--')
for n in (3,4,5):
 d=json.loads((s/'b76-native-plans-passive'/('plan-'+str(n)+'.json')).read_text());q=np.array(d['points']);ax.plot(q[:,0],q[:,1],lw=2,label='Originaler Nav2-Pfad '+str(n));print(n,[(round(a,4),round(b,4)) for a,b in q if abs(a-1.5)<.06 or abs(a-2.7)<.06])
ax.set_xlim(.5,3.6);ax.set_ylim(-1.1,.25);ax.set_aspect('equal');ax.set_title('B76: Originale native Pfade auf früherem Originalraster (nicht zeitgleich)');ax.legend();fig.tight_layout();fig.savefig(s/'b76-original-native-paths.png',dpi=130)
