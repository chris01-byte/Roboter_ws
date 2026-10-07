"""Original native and whole matrix plus read-only parent CPU accounting."""
import json,subprocess,time
from pathlib import Path
root=Path('/workspace/scratch/ap06-missions-20261005')
command=['docker','exec','ap03-nav2','bash','/evidence/ap06-missions-20261005/b238_native_and_matrix.sh']
with (root/'b238-native-and-matrix.log').open('w') as log, (root/'b238-parent-cpu.jsonl').open('w',buffering=1) as stats:
 child=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT)
 while child.poll() is None:
  values=dict(line.split() for line in Path('/sys/fs/cgroup/cpu.stat').read_text().splitlines())
  stats.write(json.dumps(dict(at=time.monotonic(),**{k:int(v) for k,v in values.items()}))+'\n')
  time.sleep(.05)
 print('diagnostic_exit',child.returncode)
