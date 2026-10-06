import ast, pytest
from pathlib import Path
import explore.metric_frontier_runtime as runtime
import explore.explore_node as owning
from explore.explore_node import ExploreNode
for module, filename, method in [(runtime,'95e82db-metric_frontier_runtime.py','_execute_metric_frontier'),(owning,'95e82db-explore_node.py','_scan_in_place')]:
 tree=ast.parse(Path('/evidence/ap06-missions-20261005',filename).read_text())
 node=next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name==method)
 namespace=dict(module.__dict__)
 exec(compile(ast.fix_missing_locations(ast.Module(body=[node],type_ignores=[])),filename,'exec'),namespace)
 setattr(ExploreNode,method,namespace[method])
raise SystemExit(pytest.main(['-q','/evidence/ap06-repo/src/explore/test/test_metric_scan_join.py']))
