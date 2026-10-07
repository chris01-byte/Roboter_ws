"""Original diagnostic initial selection plus read-only parent CPU accounting."""
import json,subprocess,time
from pathlib import Path
root=Path('/workspace/scratch/ap06-missions-20261005')
command=['docker','exec','ap03-nav2','bash','-c',
 'source /evidence/ap06-missions-20261005/old-whole-setup.sh && export ROS_DOMAIN_ID=187 && python3 /evidence/ap06-repo/tools/simulation/ap06_closed_product.py --repo /evidence/ap06-repo --output /evidence/ap06-missions-20261005/mission-a-v227-selection --case door68_start_a --tf-probe /evidence/ap06-tf-probe-build/tf_ownership_probe --manifest /evidence/ap06-repo/tools/simulation/ap06_product_scenarios.json --save-partial --capture-decisions']
with (root/'mission-a-v227-selection.log').open('w') as log, (root/'a227-parent-cpu.jsonl').open('w',buffering=1) as stats:
 child=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT)
 while child.poll() is None:
  values=dict(line.split() for line in Path('/sys/fs/cgroup/cpu.stat').read_text().splitlines())
  stats.write(json.dumps(dict(at=time.monotonic(),**{k:int(v) for k,v in values.items()}))+'\n')
  time.sleep(.05)
 print('diagnostic_exit',child.returncode)
