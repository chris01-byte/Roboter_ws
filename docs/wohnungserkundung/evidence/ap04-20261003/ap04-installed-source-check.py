from pathlib import Path
import hashlib
import importlib
import sys
repo=Path('/evidence/ap04-repo')
for prefix in ('/evidence/ap04-current-install','/evidence/ap04-native-product-install'):
 for name in ('explore_node','metric_frontier_runtime','metric_frontier_candidates','metric_frontier'):
  source=repo/'src/explore/explore'/f'{name}.py'
  installed=Path(prefix)/'explore/lib/python3.10/site-packages/explore'/f'{name}.py'
  assert source.read_bytes()==installed.read_bytes(),(source,installed)
  print(prefix,name,hashlib.sha256(source.read_bytes()).hexdigest())
print('all checked product sources byte-identical')
