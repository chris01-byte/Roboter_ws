"""Original C scenario with affinity bounded by the observed outer CPU quota."""
import json,subprocess,time,os
from pathlib import Path
root=Path('/workspace/scratch/ap06-missions-20261005')
quota=Path('/sys/fs/cgroup/cpu.max').read_text().strip();assert quota=='400000 100000',quota
assert {0,1,3,4}.issubset(os.sched_getaffinity(0))
command=['docker','exec','ap03-nav2','bash','-c',
 'source /evidence/ap06-missions-20261005/old-whole-setup.sh && export ROS_DOMAIN_ID=187 && taskset -c 0,1,3,4 python3 /evidence/ap06-repo/tools/simulation/ap06_closed_product.py --repo /evidence/ap06-repo --output /evidence/ap06-missions-20261005/mission-c-v245 --case door80_start_c --tf-probe /evidence/ap06-tf-probe-build/tf_ownership_probe --manifest /evidence/ap06-repo/tools/simulation/ap06_product_scenarios.json --save-partial']
(root/'c245-execution-allocation.json').write_text(json.dumps(dict(observed_parent_quota=quota,
 affinity=[0,1,3,4],reason='No five simultaneously runnable CPUs against the observed four-CPU quota; no source timestamp, period or guard changed'),indent=2)+'\n')
with (root/'mission-c-v245.log').open('w') as log,(root/'c245-parent-cpu.jsonl').open('w',buffering=1) as stats:
 child=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT)
 while child.poll() is None:
  values=dict(line.split() for line in Path('/sys/fs/cgroup/cpu.stat').read_text().splitlines())
  stats.write(json.dumps(dict(at=time.monotonic(),**{k:int(v) for k,v in values.items()}))+'\n')
  time.sleep(.05)
 print('original_C_exit',child.returncode,flush=True)
