"""A newer actual wheel sample needs a new proof, never a rewritten stamp."""
from types import SimpleNamespace
import numpy as np
import pytest
from robot_state_estimation.hwt601_fusion_health import Hwt601FusionHealth
from test_metric_map_lifecycle import runtime


def delayed_inputs(monkeypatch, fault='none'):
    import explore.metric_frontier_runtime as module
    node, grid = runtime(monkeypatch, body_reference=(0.,0.,0.))
    clock = [10.02]
    monkeypatch.setattr(module.time, 'monotonic', lambda: clock[0])
    node._metric_self_body_enabled = False
    node._metric_path_validation = 'rpp_rollout'
    node._tf_buffer = object()
    node._metric_pose_and_reference = lambda: ((.05,.05,0.),0.,(0.,0.,0.))
    health = Hwt601FusionHealth(active_drive=True, development_contract=True)
    node._hwt_guard = SimpleNamespace(health=health)
    def sample(stamp, valid=True, x=.05, frame='odom'):
        health.sample('wheel',stamp,clock[0],clock[0],valid,details=dict(
            frame_id=frame,child_frame_id='base_link',position=[x,.05,0.],
            orientation=[0.,0.,0.,1.]))
    sample(100.1)
    prepare = node._metric_prepare_egress
    proofs = []
    def delayed(inputs):
        prepare(inputs)
        proofs.append(inputs.physical_motion)
        if len(proofs)==1:
            clock[0] += .21
            if fault!='unchanged':
                sample(100.1 if fault=='duplicate' else 100.31,
                       valid=fault!='invalid', x=.09 if fault=='disagreement' else .05,
                       frame='foreign' if fault=='frame' else 'odom')
        else:
            clock[0] += .19 if fault=='slow_recheck' else .005
    node._metric_prepare_egress = delayed
    return node, health, proofs


def test_expired_processing_uses_new_actual_sample_only_after_full_revalidation(monkeypatch):
    node, health, proofs = delayed_inputs(monkeypatch)
    identity = node._metric_egress
    initial = [e.fixed.unknown.copy() for e in identity]
    result = node._metric_inputs()
    assert len(proofs)==2
    assert proofs[0][3]==100.1 and proofs[1][3]==100.31
    assert result.physical_motion==proofs[1]
    assert result.physical_motion[1:3]==(10.23,10.23)
    assert health.samples['wheel'][:3]==(100.31,10.23,10.23)
    assert node._metric_egress is identity
    assert all(e.valid for e in identity)
    assert all(np.array_equal(before,e.fixed.unknown) for before,e in zip(initial,identity))


@pytest.mark.parametrize('fault',['unchanged','duplicate','invalid','disagreement','frame','slow_recheck'])
def test_fresh_binding_never_heals_missing_invalid_or_expired_evidence(monkeypatch,fault):
    node,health,proofs = delayed_inputs(monkeypatch,fault)
    with pytest.raises(ValueError,match='start_motion_wheel_'):
        node._metric_inputs()
    assert len(proofs)<=2  # bounded; no polling or second refresh


def test_new_sample_does_not_resurrect_invalid_departure_inventory(monkeypatch):
    node,health,proofs = delayed_inputs(monkeypatch)
    for e in node._metric_egress:
        e.valid=False;e.reason='start_egress_reentry'
    node._metric_inputs()
    assert len(proofs)==2
    assert all(not e.valid and e.reason=='start_egress_reentry' for e in node._metric_egress)


@pytest.mark.parametrize('correction', [0., .01])
def test_moving_recheck_binds_new_tf_reference_and_preserves_departure_history(monkeypatch, correction):
    node, health, proofs = delayed_inputs(monkeypatch, 'disagreement')
    calls = []
    def actual_tf_selection():
        calls.append(True)
        return ((.05,.05,0.),0.,(0.,0.,0.)) if len(calls)==1 else (
            (.09+correction,.05,0.),0.,(correction,0.,0.))
    node._metric_pose_and_reference = actual_tf_selection
    identity = node._metric_egress
    initial = [e.fixed.unknown.copy() for e in identity]
    result = node._metric_inputs()
    assert len(calls)==2 and len(proofs)==2
    assert result[2] == (.09+correction,.05,0.)
    assert result.map_odom_reference == (correction,0.,0.)
    assert result.physical_motion[0] == (.09,.05,0.)
    assert result.physical_motion[1:3] == (10.23,10.23)
    assert result.physical_motion[3] == 100.31
    assert node._metric_egress is identity
    assert all(e.valid for e in identity)
    assert all(np.all(e.fixed.unknown <= old) for e,old in zip(identity,initial))
