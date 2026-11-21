import ast,pytest
from pathlib import Path
import explore.metric_frontier_runtime as module
from explore.explore_node import ExploreNode
name='_metric_robot_side_observation';filename='/evidence/ap06-missions-20261005/7778771-metric_frontier_runtime.py'
tree=ast.parse(Path(filename).read_text());node=next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name==name);namespace=dict(module.__dict__)
exec(compile(ast.fix_missing_locations(ast.Module(body=[node],type_ignores=[])),filename,'exec'),namespace)
setattr(ExploreNode,name,namespace[name]);raise SystemExit(pytest.main(['-q','/evidence/ap06-repo/src/explore/test/test_metric_side_work_budget.py']))
