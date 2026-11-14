import json,yaml,rclpy
from rclpy.parameter import Parameter
from explore.explore_node import ExploreNode
values={}
for file in ('metric_frontier_params.yaml','metric_frontier_simulation_params.yaml'):
    values.update(yaml.safe_load(open('/repo/src/explore/config/'+file))['explore_node']['ros__parameters'])
values.update(wohnungserkundung_accessible_scope_verified=True,wohnungserkundung_scope_id='synthetic-init',wohnungserkundung_scope_polygon_xy=[-1.,-1.,3.,-1.,3.,3.,-1.,3.],metric_session_id='ap03-init',metric_scope_map_fingerprint='a'*64,region_graph_shadow_enabled=False,behavior_tree='/fake/no_recovery.xml',overall_timeout_s=60.)
rclpy.init(args=['--ros-args',*[a for k,v in values.items() for a in ('-p',k+':='+json.dumps(v))]])
try:
    node=ExploreNode();assert node._metric_path_validation=='rpp_rollout'
    print('actual ExploreNode constructor: opt-in model with 0.02-rad enabled prealignment')
    result=node.set_parameters([Parameter('metric_path_validation',value='conservative')])[0]
    assert not result.successful;print('runtime switch rejected:',result.reason)
    assert node._metric_start_egress_enabled and node._metric_self_body_enabled
    print('private body/egress enabled; default remains conservative; no mission or motion submitted')
    node.destroy_node()
finally:rclpy.shutdown()
