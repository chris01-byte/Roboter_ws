import importlib.util
import sys
import json
from pathlib import Path
# Load only the comparison fixture's new pure visibility helper. Explorer and
# all route/mission functions still resolve to the unchanged AP-03 installation.
path=Path('/evidence/ap04-repo/src/explore/explore/metric_frontier_candidates.py')
spec=importlib.util.spec_from_file_location('explore.metric_frontier_candidates',path)
module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module)
sys.path.insert(0,'/evidence/ap04-repo/src/explore/test')
from test_metric_frontier_candidates import fixture
from explore.explore_node import ExploreNode
from explore.metric_frontier import MetricTaskPolicy
import explore.explore_node as product
assert product.__file__.startswith('/evidence/ap03-current-install/')
rows=[]
for case in ('ring','concave','long','blocked','growth','revisit','no_semantics'):
 n,inputs,scan=fixture(case)
 cs=n._metric_select(inputs,MetricTaskPolicy(.6,30.,2),.3)
 rows.append(dict(case=case,accepted=len(cs),rejections=n._frontier_rank_stats))
print(json.dumps(dict(original_product=product.__file__,rows=rows),indent=2))
assert rows[0]['accepted']==0
