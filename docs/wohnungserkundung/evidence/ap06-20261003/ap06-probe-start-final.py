exec(open('/evidence/ap06-probe-start.py').read().split('out=[]')[0])
p=Path('/evidence/ap06-runs/product-c-05')
raw=np.load(p/'final_slam_map.npy');cost=np.load(p/'final_global_costmap.npy')
assert np.array_equal(raw,a['raw'])
inputs[5].data=cost.ravel().tolist();inputs[6]=(cost>=0)&(cost<100)
# Recompute the same safe-cell cost predicate; raw known inventory is exact
# measured first-pass data at the same stationary pose and unchanged geometry.
from explore.metric_frontier import known_safe_mask
body=(raw<0)&inputs[3]
known,safe=known_safe_mask(raw,n._metric_scope,inputs[1],tuple(geometry[0]['origin']),0.,inputs[0].info.resolution,n._goal_clearance_m,body)
assert np.array_equal(known,inputs[3])
inputs[4]=safe & (cost>=0) & (cost<=n._frontier_goal_max_cost)
out=[]
for d in [.30,.33,.36,.39,.42,.45,.48,.51,.54]:
 route=n._metric_route(inputs,(d,0.),0.)
 out.append(dict(forward_distance_m=d,accepted=route is not None,rejection=n._metric_last_route_rejection,route=route))
print(json.dumps(dict(kind='offline_measured_same_raw_pose_geometry_new_native_costmap',source_run=p.name,probes=out),indent=2))
