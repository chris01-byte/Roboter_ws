"""Use actual HWT health samples; encoder measurement is no new owner."""
import math
from types import SimpleNamespace
import pytest
from robot_state_estimation.hwt601_fusion_health import Hwt601FusionHealth
from explore.explore_node import ExploreNode


@pytest.mark.parametrize('fault',['none','stale','invalid','foreign','nan','quaternion','position_disagreement','yaw_disagreement'])
def test_motion_binding_requires_original_fresh_valid_wheel_and_tf_agreement(monkeypatch,fault):
    import explore.metric_frontier_runtime as runtime
    monkeypatch.setattr(runtime.time,'monotonic',lambda:10.)
    health=Hwt601FusionHealth(active_drive=True,development_contract=True)
    details=dict(frame_id='odom',child_frame_id='base_link',position=[.04,0.,0.],orientation=[0.,0.,0.,1.])
    if fault=='foreign':details['frame_id']='map'
    if fault=='nan':details['position'][0]=float('nan')
    if fault=='quaternion':details['orientation'][3]=2.
    if fault=='position_disagreement':details['position'][0]=.07
    if fault=='yaw_disagreement':details['orientation']=[0.,0.,math.sin(.06/2),math.cos(.06/2)]
    health.sample('wheel',100.,9.9 if fault!='stale' else 9.7,9.9,fault!='invalid',details=details)
    node=ExploreNode.__new__(ExploreNode);node._hwt_guard=SimpleNamespace(health=health)
    node._metric_path_validation='rpp_rollout';node._metric_start_egress_enabled=True
    if fault=='none':
        motion=node._metric_measured_motion((.05,0.,0.),(.01,0.,0.))
        assert motion==((.04,0.,0.),9.9,9.9,100.)
    else:
        with pytest.raises(ValueError,match='start_motion_wheel_'):
            node._metric_measured_motion((.05,0.,0.),(.01,0.,0.))


def test_only_private_escape_geometry_needs_bound_encoder_history(monkeypatch):
    import explore.metric_frontier_runtime as runtime
    from test_metric_motion_geometry import door_inputs
    monkeypatch.setattr(runtime.time,'monotonic',lambda:10.)
    node,inputs=door_inputs()
    health=Hwt601FusionHealth(active_drive=True,development_contract=True)
    health.sample('wheel',100.,9.7,9.7,True,details=dict(frame_id='odom',
        child_frame_id='base_link',position=[-.9,0.,0.],orientation=[0.,0.,0.,1.]))
    node._hwt_guard=SimpleNamespace(health=health)
    node._metric_start_egress_enabled=True
    assert node._metric_motion_binding_for_geometry(inputs,(0.,0.,0.)) is None
    # Nothing refreshes the stale measurement or weakens the live guard.
    assert health.samples['wheel'][1:3]==(9.7,9.7)
    assert health._sample_rejection('wheel',10.,.18) is not None
    col,row=node._world_to_grid(-.65,0.,inputs[0].info)
    inputs[3][row,col]=False
    with pytest.raises(ValueError,match='start_motion_wheel_missing_stale_or_invalid'):
        node._metric_motion_binding_for_geometry(inputs,(0.,0.,0.))
