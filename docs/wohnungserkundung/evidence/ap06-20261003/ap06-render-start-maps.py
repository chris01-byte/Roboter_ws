import json,sys
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
sys.path.insert(0,'/workspace/Roboter_ws-ap06/tools/simulation')
from ap06_world import World,chassis
root=Path('/workspace/scratch/ap06-runs')
fig,axes=plt.subplots(1,3,figsize=(14,4),constrained_layout=True)
for ax,name in zip(axes,['complete-a','complete-b','complete-c']):
 p=root/name; result=json.loads((p/'result.json').read_text()); case=result['case']
 world=World(case['door_m'],case['start']); raw=np.load(p/'final_slam_map.npy'); geom=json.loads((p/'final_slam_map_geometry.json').read_text())
 origin=np.asarray(geom['origin'])+world.start[:2]; res=geom['resolution']; extent=[origin[0],origin[0]+res*raw.shape[1],origin[1],origin[1]+res*raw.shape[0]]
 shown=np.where(raw<0,0,np.where(raw<65,1,2));ax.imshow(shown,origin='lower',extent=extent,cmap=ListedColormap(['#b8bcc3','#ffffff','#30343b']),vmin=0,vmax=2)
 for wall in world.obstacles:
  closed=np.vstack((wall,wall[0]));ax.plot(closed[:,0],closed[:,1],color='#a24ab4',linewidth=.8)
 first=chassis(world.start);first=np.vstack((first,first[0]));ax.plot(first[:,0],first[:,1],'--',color='#1372b6',linewidth=1)
 last=json.loads((p/'plant.jsonl').read_text().splitlines()[-1])[1:4];body=chassis(last);body=np.vstack((body,body[0]));ax.plot(body[:,0],body[:,1],color='#d56800',linewidth=1.5)
 for task in result['metric'].get('chain',[]):
  if 'target' in task:
   goal=np.asarray(task['target'])+world.start[:2];ax.plot(*goal,'+',color='#268124',markersize=9)
 ax.set(xlim=(-2.95,2.95),ylim=(-1.55,1.55),aspect='equal',xlabel='Referenzwelt x [m]',ylabel='y [m]',title=f'{case["id"]}\n{result["travel_m"]*100:.1f} cm, 0 Zielankünfte')
fig.suptitle('AP-06: synthetische SLAM-Ausgaben / unabhängige violette Referenzwände\nGrau unbekannt; blau Startkontur, orange Haltkontur, grün autonomes Ziel – 0/3 Gesamtmissionen bestanden',fontsize=11)
out=Path('/workspace/Roboter_ws-ap06/docs/wohnungserkundung/evidence/ap06-20261003/start_maps.png');fig.savefig(out,dpi=150);print(out)
