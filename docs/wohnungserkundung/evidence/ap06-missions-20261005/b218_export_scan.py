"""Export our frozen synthetic snapshot without executable pickle fixtures."""
import pickle, json
from dataclasses import asdict
from pathlib import Path
import numpy as np
from rclpy.serialization import serialize_message
from explore.metric_frontier_candidates import lidar_view

r=pickle.loads(Path('/evidence/ap06-missions-20261005/mission-b-v216-selection/selection-object-2.pickle').read_bytes())
out=Path('/evidence/ap06-repo/src/explore/test/data/ap06_b216_pending_scan')
arrays={k:r['inputs'][i] for k,i in [('known',3),('safe',4),('cost_known',6)]}
for k,i in [('raw_cdr',0),('cost_cdr',5)]: arrays[k]=np.frombuffer(serialize_message(r['inputs'][i]),dtype=np.uint8)
view=lidar_view(r['scan'],r['mount'],r['captured_monotonic'],r['attributes']['_door_lidar_scan_timeout'],r['attributes']['_door_lidar_max_range'])
arrays['angles']=view.angles
attrs=dict(r['attributes']); identity=attrs.pop('_metric_egress_identity')
meta=dict(kind='Actual B216 diagnostic selection-entry rasters, private ledger and policy; geometry component only, no health or acceptance receipt',
    pose=r['inputs'][2],correlation=asdict(r['inputs'][1]),scope=asdict(r['scope']),
    reference=r['reference'],physical_motion=r['physical_motion'],attributes=attrs,
    identity=[asdict(identity[0]),identity[1]],policy=r['policy'],mount=view.mount,
    minimum_range=view.minimum_range_m,maximum_range=view.range_m,evidence=[])
for i,e in enumerate(r['evidence']):
    f=e.fixed
    arrays[f'fixed_cdr_{i}']=np.frombuffer(serialize_message(f.grid),dtype=np.uint8)
    arrays[f'fixed_unknown_{i}']=f.unknown; arrays[f'fixed_scope_{i}']=f.scope_mask
    arrays[f'projected_unknown_{i}']=e.unknown;arrays[f'projected_scope_{i}']=e.scope_mask
    meta['evidence'].append(dict(pose=f.pose,bounds=f.bounds,initial_polygon=f.initial_polygon,
        valid=f.valid,reason=f.reason,remaining_area=[[*k,v] for k,v in f.remaining_area.items()],
        departed_distance=[[*k,v] for k,v in f.departed_distance.items()],
        reference=e.reference,current_reference=e.current_reference,generation=e.generation,
        retained_wkb=e.retained_region.wkb_hex,whole_cells=e._whole_cells))

meta['observations']=r['observations'];meta['arrivals']=r['arrivals']
np.savez_compressed(out.with_suffix('.npz'),**arrays)
out.with_suffix('.json').write_text(json.dumps(meta,indent=2,default=lambda v:v.item()))
print(out,flush=True)
