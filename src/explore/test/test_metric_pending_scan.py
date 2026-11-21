"""Actual B216: a proved pending public scan must not starve behind new goals."""
import copy
import json
from pathlib import Path
import pytest
from test_metric_public_cooldown import frozen


def recorded():
    node,inputs,policy=frozen('ap06_b216_pending_scan')
    meta=json.loads((Path(__file__).parent/'data/ap06_b216_pending_scan.json').read_text())
    node._metric_status.update(observations=meta['observations'],arrivals=meta['arrivals'])
    return node,inputs,policy


def test_observed_departure_uses_real_public_scan_before_another_goal_search():
    node,inputs,policy=recorded()
    assert node._metric_scan_geometry_ready(node._metric_public_inputs(inputs))
    assert node._metric_status['observations']==2
    before=copy.deepcopy(policy.attempts)
    maps=[list(inputs[i].data) for i in (0,5)]
    ledgers=node._metric_egress
    def no_search(*_):
        pytest.fail('Already proved one-shot observation must not wait for a new goal search')
    node._metric_select=no_search
    decision,candidates=node._metric_start_decision(inputs,policy,.3,True)
    assert decision['selected_motion']=='full_scan' and not candidates
    assert decision['scan_admissible'] and decision['scan_useful']
    assert decision['scan_priority']=='public_after_observed_departure'
    assert node._metric_egress is ledgers and all(not e.valid for e in ledgers)
    assert policy.attempts==before and [list(inputs[i].data) for i in (0,5)]==maps


@pytest.mark.parametrize('fault', ['not_observed','not_pending','raw_unknown','virtual_only','cost_blocked','no_boundary'])
def test_pending_scan_priority_requires_measured_progress_and_public_geometry(fault):
    node,inputs,policy=recorded();pending=True
    if fault=='not_observed':node._metric_status['observations']=0
    elif fault=='not_pending':pending=False
    elif fault in ('raw_unknown','virtual_only'):
        col,row=node._world_to_grid(*inputs[2][:2],inputs[0].info)
        inputs[0].data[row*inputs[0].info.width+col]=-1
        if fault=='raw_unknown':inputs[3][row,col]=False
    elif fault=='cost_blocked':
        col,row=node._world_to_grid(*inputs[2][:2],inputs[5].info)
        inputs[5].data[row*inputs[5].info.width+col]=100;inputs[6][row,col]=False
    elif fault=='no_boundary':
        inputs[0].data=[100 if x<0 else x for x in inputs[0].data]
    calls=[]
    node._metric_select=lambda *_: calls.append(True) or []
    decision,_=node._metric_start_decision(inputs,policy,.3,pending)
    assert calls and 'scan_priority' not in decision
    if fault in ('not_pending','raw_unknown','cost_blocked','no_boundary'):
        assert decision['selected_motion']!='full_scan'
