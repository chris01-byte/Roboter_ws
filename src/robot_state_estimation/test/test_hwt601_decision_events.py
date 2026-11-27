"""Original decision evidence across recovery; no devices or actuators."""
import copy
import json
import pytest
from test_hwt601_fusion_health import ready_health, _recovery_samples


@pytest.mark.parametrize('active', [False, True])
def test_recovered_hwt_then_wheel_fault_has_two_original_decisions(active):
    h = ready_health(active)
    assert h.source_failure(10.) is None
    raw = copy.deepcopy(h.statuses['raw'][0])
    raw.update(ready=False, raw_data_ready=False, state='degradiert')
    h.status('raw', raw, 10.01)
    assert h.source_failure(10.01) == 'raw_driver_not_ready'
    first = h.first_fault_snapshot()
    original_hold = copy.deepcopy(h.recovery_events[0])
    _recovery_samples(h, 10.02, 11.8)
    assert h.recovery_state == 'HEALTHY'
    original = {'stamp_sec': 123, 'stamp_nanosec': 4, 'twist': [0., 0., 0., 0., 0., 0.]}
    h.sample('wheel', 11.81, 11.81, 11.81, details=original)
    limit = .30 if active else .18
    now = 11.81 + limit + .001
    for name in ('raw', 'yaw'):
        h.sample(name, now, now, now)
        h.status(name, h.statuses[name][0], now)
    h.status('wheel', h.statuses['wheel'][0], now)
    assert h.source_failure(now) == 'wheel_missing_stale_or_invalid'
    last = h.fault_snapshot()
    assert last['state_before'] == 'HEALTHY'
    assert last['state_after'] == 'TERMINAL_FAULT'
    assert last['event_id'] > original_hold['event_id']
    assert last['previous_successful_recovery']['reason'] == 'recovered'
    wheel = next(x for x in last['source_checks'] if x['source'] == 'wheel')
    assert wheel['original_message_and_clock_pair'] == original
    assert wheel['first_rejecting_predicate'] == 'callback_receive_age_out_of_bounds'
    assert wheel['sample_age_s'] == pytest.approx(limit + .001)
    assert h.first_fault_snapshot() == first
    assert h.recovery_events[0] == original_hold
    h.sample('wheel', now+.01, now+.01, now+.01, details={'stamp_sec': 456})
    assert h.fault_snapshot() == last
    json.dumps(last, allow_nan=False)


@pytest.mark.parametrize('mode,predicate', [
    ('missing', 'missing_message'), ('invalid', 'invalid_content_or_measurement_order'),
    ('old_measurement', 'measurement_age_out_of_bounds')])
def test_wheel_rejections_preserve_the_first_actual_predicate(mode, predicate):
    h = ready_health(False)
    assert h.source_failure(10.) is None
    if mode == 'missing':
        del h.samples['wheel']
    else:
        h.sample('wheel', 10.01, 10.01, 9. if mode == 'old_measurement' else 10.01,
                 valid=mode != 'invalid', details={'content_valid': mode != 'invalid'})
    assert h.source_failure(10.02) == 'wheel_missing_stale_or_invalid'
    check = h.fault_snapshot()['source_checks'][2]
    assert check['first_rejecting_predicate'] == predicate


def test_status_callback_entry_order_preserves_newest_original_status():
    h=ready_health(False);assert h.source_failure(10.) is None
    new=dict(h.statuses['wheel'][0],complete_pair_count=101)
    h.status('wheel',new,10.03)
    h.status('wheel',dict(new,ready=False,complete_pair_count=99),10.01)
    assert h.statuses['wheel']==(new,10.03)
    assert h.source_failure(10.04) is None
    h.status('wheel',dict(new,ready=False,complete_pair_count=102),10.04)
    assert h.source_failure(10.05)=='wheel_not_real_or_not_ready'
    assert h.fault_snapshot()['wheel_status']['complete_pair_count']==102
