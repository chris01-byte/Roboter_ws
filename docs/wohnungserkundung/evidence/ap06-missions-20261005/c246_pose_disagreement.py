"""Read-only original C245 time-tagged TF/encoder evidence; no invented join."""
import gzip,json,hashlib,math
from pathlib import Path
root=Path('/workspace/scratch/ap06-missions-20261005');p=root/'mission-c-v245';tf=[];wheel=[];failure=None;digest=hashlib.sha256();size=0
for line in gzip.open(p/'events.jsonl.gz','rb'):
 digest.update(line);size+=len(line);r=json.loads(line);topic=r['topic'];data=r.get('data',{})
 if isinstance(data,str):data=json.loads(data)
 if topic=='/tf':tf.append(r)
 elif topic=='/base_hardware/state_json':
  wheel.append(dict(at=r['at'],pose=[data.get(k) for k in ('x','y','yaw')],stamp_sec=data.get('stamp_sec'),
     age=data.get('encoder_feedback_age_s'),sample_dt_s=data.get('encoder_sample_dt_s'),
     left=data.get('encoder_position_left_i32'),right=data.get('encoder_position_right_i32')))
 elif topic=='/explore/status_json' and failure is None and 'start_motion_wheel_tf_disagreement' in str(data):failure=r['at']
meta=json.loads((p/'events.jsonl.gz.meta.json').read_text());assert meta['sha256']==digest.hexdigest() and meta['uncompressed_bytes']==size
if failure is None:raise RuntimeError('Original failure status missing')
near_tf=[r for r in tf if failure-8.<r['at']<failure+.25];near_wheel=[r for r in wheel if failure-8.<r['at']<failure+.25]
comparisons=[]
for w in near_wheel:
 candidates=[r for r in tf if r['transform']['parent']=='odom' and r['transform']['child']=='base_link' and r['at']<=w['at']]
 if not candidates:continue
 t=candidates[-1];q=t['transform']['rotation'];xy=t['transform']['translation'];yaw=math.atan2(2*q[3]*q[2],1-2*q[2]*q[2]);stamp=t['transform']['stamp'];
 comparisons.append(dict(wheel_received_at=w['at'],tf_received_at=t['at'],wheel_pose=w['pose'],tf_pose=[*xy[:2],yaw],
  received_time_difference_s=w['at']-t['at'],position_difference_m=math.dist(w['pose'][:2],xy[:2]),
  wheel_state_stamp_sec=w['stamp_sec'],tf_source_stamp_sec=stamp[0]+stamp[1]/1e9,
  NOT_exact_product_selected_pair=True))
result=dict(kind='Original C245 observer time series; exact internally selected wheel/TF pair was not recorded',failure_observed_at=failure,
 trace_raw_sha256=digest.hexdigest(),trace_raw_bytes=size,tf=near_tf,wheel=near_wheel,latest_received_comparisons= comparisons)
(root/'c246-pose-disagreement.json').write_text(json.dumps(result,indent=2)+'\n')
print('verified',size,'bytes; failure',failure)
for r in comparisons[-8:]:print(r)
