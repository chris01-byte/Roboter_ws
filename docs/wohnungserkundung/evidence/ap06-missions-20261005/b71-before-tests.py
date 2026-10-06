import importlib.util,sys,pytest
print('Component countercheck: only candidate/runtime modules from b8189a9; current policy and exact B70 evidence-derived partial classification retained.')
for module in ['metric_frontier_candidates','metric_frontier_runtime']:
 path='/evidence/ap06-missions-20261005/b71-before-'+module+'.py'
 spec=importlib.util.spec_from_file_location('explore.'+module,path)
 target=importlib.util.module_from_spec(spec);sys.modules[spec.name]=target;spec.loader.exec_module(target)
raise SystemExit(pytest.main(['-q','src/explore/test/test_metric_retained_observation.py::test_b70_partial_followup_uses_unmodified_counter_history']))
