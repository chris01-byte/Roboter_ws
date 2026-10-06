import importlib.util, sys, pytest
path='/evidence/ap06-missions-20261005/native-status-v19-head-metric_frontier.py'
spec=importlib.util.spec_from_file_location('explore.metric_frontier',path)
module=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=module
spec.loader.exec_module(module)
print('Component countercheck: only metric_frontier loaded from b8189a9; installed product unchanged.')
raise SystemExit(pytest.main(['-q','src/explore/test/test_metric_proposal_alternatives.py']))
