"""Safe CDR/NPZ terminal public-source fixture; no executable pickle in Git."""
from pathlib import Path
from dataclasses import asdict
import json,pickle,numpy as np
from rclpy.serialization import serialize_message
from b208_frozen import frozen
root=Path('/evidence/ap06-missions-20261005');n,i,p=frozen();record=json.loads((root/'b208-terminal-public-source.json').read_text());template=pickle.loads((root/'mission-b-v95-profile/selection-object-1.pickle').read_bytes());attrs={key:getattr(n,key,None) for key in template['attributes']};attrs.pop('_metric_egress_identity')
view=n._metric_observation_view();meta=dict(kind='Own terminal B207 public rasters, recorded actual TF/finite scan and original complete saved task history; not a pre-failure live input, health receipt or qualification',pose=i[2],correlation=asdict(i[1]),scope=asdict(n._metric_scope),reference=i.map_odom_reference,physical_motion=None,attributes=attrs,identity=[asdict(i[1].context),[n._metric_grid_geometry(i[0]),n._metric_grid_geometry(i[5])]],policy=record['checkpoint']['state']['policy'],mount=view.mount,minimum_range=view.minimum_range_m,maximum_range=view.range_m,evidence=[],event_raw_sha256=record['event_raw_sha256'],expected_candidate=[2.734999938867986,-0.42499999050050974,0.])
arrays=dict(raw_cdr=np.frombuffer(serialize_message(i[0]),dtype=np.uint8),cost_cdr=np.frombuffer(serialize_message(i[5]),dtype=np.uint8),known=i[3],safe=i[4],cost_known=i[6],angles=view.angles)
out=Path('/evidence/ap06-repo/src/explore/test/data/ap06_b207_terminal_selection');np.savez_compressed(out.with_suffix('.npz'),**arrays);out.with_suffix('.json').write_text(json.dumps(meta,indent=2,default=lambda x:x.item()));print(out)
