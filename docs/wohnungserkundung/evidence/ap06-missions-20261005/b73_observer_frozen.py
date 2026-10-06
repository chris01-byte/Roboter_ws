"""Actual B73 selection 14; current small remainder retained, component only."""
import b73_selection_probe as frozen
import explore.metric_frontier_runtime as runtime
n,inputs,policy=frozen.frozen(13)
original=runtime.boundary_samples
def sampled(grid,scope,to_world,minimum,**kwargs):
 kwargs['retained_anchors']=(*kwargs.get('retained_anchors',()),inputs[2][:2])
 kwargs['retained_radius_m']=.8+n._min_goal_dist_m+n._goal_search_m
 return original(grid,scope,to_world,minimum,**kwargs)
runtime.boundary_samples=sampled
