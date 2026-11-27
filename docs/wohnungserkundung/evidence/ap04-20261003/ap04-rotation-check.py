import sys,json,math
sys.path.insert(0,'/evidence/ap04-repo/tools/analysis/frontier_comparison')
from compare import load_fixture,external_frontiers
n,i,s=load_fixture(__import__('pathlib').Path('/evidence/ap04-repo')).fixture('long',rotation=math.pi/2)
fs,reason=external_frontiers(__import__('pathlib').Path('/evidence/ap04-probe-build/ap04_frontier_probe'),n,i)
assert not fs and reason=='unsupported_origin_rotation'
cs=n._metric_candidates(i,.3)
assert cs
print(json.dumps(dict(upstream=reason,corrected_own_accepted=len(cs),origin_yaw=math.pi/2)))
