import copy
import json
import math

import pytest

from robot_state_estimation.hwt601_fusion_health import Hwt601FusionHealth
from robot_state_estimation.hwt601_shadow_core import Hwt601YawShadowCore
from robot_state_estimation.quality_core import GyroBiasConfig


def ready_health(active=True, now=10.0, development=False):
    health = Hwt601FusionHealth(active, development_contract=development)
    for key in ('raw', 'yaw', 'wheel'):
        health.sample(key, now, now, now)
    health.status('raw', {
        'ready': True, 'raw_data_ready': True, 'port': '/dev/ttyUSB_HWT601',
        'sensor_write_commands': False, 'consecutive_errors': 0, 'age_s': 0.0,
        'state': 'bereit', 'reconnects': 0,
    }, now)
    health.status('yaw', {
        'ready': True, 'operator_stationary_confirmed': True,
        'bias_frozen_after_startup': True, 'latched_fault': None, 'age_s': 0.0,
        'bias': {'calibrated': True, 'stable': True, 'adaptation_samples': 0},
    }, now)
    wheel = {
        'dry_run': False, 'allow_rs485': True, 'rs485_ready': True,
        'odometry_source': 'encoder_position', 'encoder_feedback_ok': True,
        'encoder_stale': False, 'encoder_config_fault_latched': False,
        'encoder_feedback_age_s': 0.0,
    } if active else {
        'ready': True, 'source': 'ess23_absolute_fc03', 'synthetic': False,
        'command_derived': False, 'read_only': True, 'actuator_output': False,
        'fault_latched': False, 'last_feedback_age_s': 0.0,
    }
    health.status('wheel', wheel, now)
    return health


def test_actual_inputs_ready_and_readonly_never_authorizes_motion():
    assert ready_health().motion_failure(10.05) is None
    readonly = ready_health(False)
    assert readonly.source_failure(10.05) is None
    assert readonly.motion_failure(10.05) == 'readonly_preflight_no_motion'


def test_readonly_freshness_allows_only_the_profiled_180ms_window():
    health = ready_health(False)
    health.statuses['wheel'][0]['last_feedback_age_s'] = 0.18
    assert health.source_failure(10.17) is None

    too_old = ready_health(False)
    too_old.statuses['wheel'][0]['last_feedback_age_s'] = 0.181
    assert too_old.source_failure(10.17) == 'wheel_not_real_or_not_ready'


def test_active_drive_encoder_freshness_remains_300ms():
    healthy = ready_health(True)
    healthy.statuses['wheel'][0]['encoder_feedback_age_s'] = 0.30
    assert healthy.source_failure(10.0) is None

    stale = ready_health(True)
    stale.statuses['wheel'][0]['encoder_feedback_age_s'] = 0.301
    assert stale.source_failure(10.0) == 'wheel_not_real_or_not_ready'


@pytest.mark.parametrize('missing', ['raw', 'yaw', 'wheel'])
def test_prediction_cannot_mask_missing_raw_input(missing):
    health = ready_health()
    assert health.motion_failure(10.0) is None
    # EKF may keep predicting forever. It is intentionally not in the contract.
    for key in ('raw', 'yaw', 'wheel'):
        if key != missing:
            health.sample(key, 10.5, 10.5, 10.5)
    assert health.motion_failure(10.5) == missing + '_missing_stale_or_invalid'
    health.sample(missing, 10.51, 10.51, 10.51)
    assert health.motion_failure(10.51) == missing + '_missing_stale_or_invalid'


@pytest.mark.parametrize('key', ['raw', 'yaw', 'wheel'])
@pytest.mark.parametrize('mode', ['future', 'old_header', 'repeat', 'invalid', 'nan'])
def test_received_packet_is_not_necessarily_a_fresh_valid_measurement(key, mode):
    h = ready_health()
    stamp, observed, valid = 10.01, 10.01, True
    if mode == 'future':
        observed = 11.0
    elif mode == 'old_header':
        observed = 8.0
    elif mode == 'repeat':
        stamp = 10.0
    elif mode == 'invalid':
        valid = False
    elif mode == 'nan':
        stamp = math.nan
    h.sample(key, stamp, 10.01, observed, valid)
    assert h.motion_failure(10.02) == key + '_missing_stale_or_invalid'


@pytest.mark.parametrize('key', ['raw', 'yaw', 'wheel'])
def test_overtaken_callback_cannot_replace_newer_valid_sample(key):
    h = ready_health()
    assert h.motion_failure(10.0) is None
    h.sample(key, 10.03, 10.03, 10.03)
    # The older callback entered before the newer one but reached Health last.
    h.sample(key, 10.01, 10.01, 10.01)
    assert h.samples[key] == (10.03, 10.03, 10.03, True)
    assert h.motion_failure(10.04) is None
    assert h.first_fault_snapshot() is None


@pytest.mark.parametrize('key', ['raw', 'yaw', 'wheel'])
def test_timestamp_regression_after_newer_callback_remains_hard_fault(key):
    h = ready_health()
    assert h.motion_failure(10.0) is None
    h.sample(key, 10.03, 10.03, 10.03)
    h.sample(key, 10.01, 10.04, 10.01)
    assert h.motion_failure(10.05) == key + '_missing_stale_or_invalid'
    assert h.recovery_state == 'TERMINAL_FAULT'


def test_overtaken_raw_callback_does_not_extend_measurement_freshness():
    h = ready_health()
    assert h.motion_failure(10.0) is None
    h.sample('raw', 10.03, 10.03, 10.03)
    h.sample('raw', 10.01, 10.01, 10.01)
    h.sample('yaw', 10.24, 10.24, 10.24)
    h.sample('wheel', 10.24, 10.24, 10.24)
    assert h.motion_failure(10.24) == 'raw_missing_stale_or_invalid'


def test_overtaken_invalid_raw_callback_cannot_overwrite_newer_measurement():
    h = ready_health()
    assert h.motion_failure(10.0) is None
    h.sample('raw', 10.03, 10.03, 10.03)
    h.sample('raw', 10.01, 10.01, 10.01, valid=False)
    assert h.motion_failure(10.04) is None
    assert h.ignored_older_callbacks['raw']==1
    h.sample('raw', 10.04, 10.04, 10.04, valid=False)
    assert h.motion_failure(10.05) == 'raw_missing_stale_or_invalid'


@pytest.mark.parametrize('field,value', [
    ('operator_stationary_confirmed', False), ('bias_frozen_after_startup', False),
    ('latched_fault', 'imu_datenluecke_neustart_noetig'), ('ready', False),
    ('bias', {'calibrated': False, 'stable': True, 'adaptation_samples': 0}),
    ('bias', {'calibrated': True, 'stable': True, 'adaptation_samples': 1}),
    ('age_s', math.nan),
])
def test_calibration_and_fault_contract_not_replaceable_by_fresh_yaw(field, value):
    h = ready_health()
    payload = copy.deepcopy(h.statuses['yaw'][0])
    payload[field] = value
    h.status('yaw', payload, 10.0)
    assert h.motion_failure(10.0) == 'yaw_uncalibrated_or_faulted'


def test_yaw_continuity_pending_is_a_bounded_hold_not_a_hard_latch():
    h = ready_health()
    assert h.motion_failure(10.0) is None
    yaw = copy.deepcopy(h.statuses['yaw'][0])
    yaw.update(ready=False, data_continuity_pending=True)
    h.status('yaw', yaw, 10.21)
    for key in ('raw', 'wheel'):
        h.sample(key, 10.21, 10.21, 10.21)
    assert h.motion_failure(10.21) == 'yaw_data_continuity_pending'
    assert h.recovery_state == 'HOLD'
    assert h.latched_fault is None
    for key in ('raw', 'wheel'):
        h.sample(key, 10.36, 10.36, 10.36)
    assert h.motion_failure(10.36) == 'yaw_data_continuity_pending'
    assert h.recovery_state == 'HOLD'
    h.sample('yaw', 10.37, 10.37, 10.37)
    assert h.motion_failure(10.37) == 'yaw_data_continuity_pending'
    yaw.update(ready=True, data_continuity_pending=False)
    h.status('yaw', yaw, 10.38)
    _recovery_samples(h, 10.38, 11.8)
    assert h.recovery_state == 'HEALTHY'


def test_yaw_pending_flag_cannot_hide_real_bias_or_latch_fault():
    for change in ({'latched_fault': 'imu_zeitfehler_neustart_noetig'},
                   {'bias': {'calibrated': False, 'stable': True,
                             'adaptation_samples': 0}}):
        h = ready_health()
        assert h.motion_failure(10.0) is None
        yaw = copy.deepcopy(h.statuses['yaw'][0])
        yaw.update(ready=False, data_continuity_pending=True, **change)
        h.status('yaw', yaw, 10.01)
        assert h.motion_failure(10.01) == 'yaw_uncalibrated_or_faulted'
        assert h.recovery_state == 'TERMINAL_FAULT'


@pytest.mark.parametrize('pending', [True, 'true', 1])
def test_yaw_ready_cannot_contradict_continuity_pending(pending):
    h = ready_health()
    assert h.motion_failure(10.0) is None
    yaw = copy.deepcopy(h.statuses['yaw'][0])
    yaw['data_continuity_pending'] = pending
    h.status('yaw', yaw, 10.01)
    assert h.motion_failure(10.01) == 'yaw_calibration_or_identity_fault'
    assert h.recovery_state == 'TERMINAL_FAULT'


def test_prolonged_raw_gap_remains_terminal_after_real_yaw_output_returns():
    core = Hwt601YawShadowCore(GyroBiasConfig(
        calibration_duration_s=0.02, minimum_samples=3,
        maximum_stddev_radps=0.005, maximum_sample_magnitude_radps=0.03,
        maximum_sample_gap_s=0.10,
        stationary_adaptation_time_constant_s=0.0), True)
    bias = (0.001, -0.002, 0.0001)
    for stamp in (9.97, 9.98, 9.99, 10.0):
        result = core.update(stamp, bias)
    assert result.publish
    h = ready_health(now=10.0)
    assert h.motion_failure(10.0) is None
    h.sample('wheel', 10.21, 10.21, 10.21)
    assert h.motion_failure(10.21) == 'raw_missing_stale_or_invalid'
    # The real shadow has no corrected sample during a prolonged outage.
    # Once its 0.35-s output freshness expires, its status becomes unready.
    yaw = copy.deepcopy(h.statuses['yaw'][0])
    yaw.update(ready=False, age_s=0.50, data_continuity_pending=False)
    h.status('yaw', yaw, 10.50)
    h.sample('wheel', 10.50, 10.50, 10.50)
    terminal_reason = h.motion_failure(10.50)
    assert terminal_reason == 'raw_missing_stale_or_invalid'
    assert h.recovery_state == 'TERMINAL_FAULT'
    assert not core.update(10.51, bias).publish
    assert core.update(10.52, bias).publish
    for key in ('raw', 'yaw', 'wheel'):
        h.sample(key, 10.52, 10.52, 10.52)
    yaw.update(ready=True, age_s=0.0, data_continuity_pending=False)
    h.status('yaw', yaw, 10.52)
    assert h.motion_failure(10.52) == terminal_reason


@pytest.mark.parametrize('field,value', [
    ('dry_run', True), ('allow_rs485', False), ('rs485_ready', False),
    ('odometry_source', 'speed'), ('encoder_feedback_ok', False),
    ('encoder_stale', True), ('encoder_config_fault_latched', True),
    ('encoder_feedback_age_s', 0.31),
])
def test_synthetic_or_faulted_base_is_never_measurement(field, value):
    h = ready_health()
    h.statuses['wheel'][0][field] = value
    assert h.motion_failure(10.0) == 'wheel_not_real_or_not_ready'


@pytest.mark.parametrize('key', ['raw', 'yaw', 'wheel'])
def test_missing_status_is_fail_closed_despite_samples(key):
    h = ready_health()
    del h.statuses[key]
    assert h.motion_failure(10.0) == key + '_status_missing_or_stale'


def test_empty_start_is_blocked_but_can_complete_calibration():
    assert Hwt601FusionHealth(True).motion_failure(1.0) == 'raw_missing_stale_or_invalid'


def test_fresh_wrong_driver_or_invalid_json_does_not_authorize():
    h = ready_health()
    h.statuses['raw'][0]['port'] = '/dev/ttyUSB_BASE'
    assert h.motion_failure(10.0) == 'raw_driver_not_ready'
    h.status('yaw', [], 10.0)
    h.statuses['raw'][0]['port'] = '/dev/ttyUSB_HWT601'
    assert h.motion_failure(10.0) == 'yaw_uncalibrated_or_faulted'


@pytest.mark.parametrize('field,value', [
    ('ready', False), ('raw_data_ready', False),
    ('port', '/dev/ttyUSB_BASE'), ('sensor_write_commands', True),
    ('consecutive_errors', 1), ('age_s', 0.201),
])
def test_first_fault_records_each_raw_predicate_without_changing_latch(field, value):
    h = ready_health(now=10.0)
    assert h.motion_failure(10.0) is None
    raw = copy.deepcopy(h.statuses['raw'][0])
    raw.update(accepted=12, rejected=3, successful_connections=2,
               reconnects=1, last_error='read_timeout')
    raw[field] = value
    h.status('raw', raw, 10.04)
    assert h.motion_failure(10.05) == 'raw_driver_not_ready'
    finding = h.first_fault_snapshot()
    assert finding['component'] == 'Hwt601FusionHealth'
    assert finding['aggregate_reason'] == 'raw_driver_not_ready'
    assert finding['violations'] == [field]
    entry = next(item for item in finding['raw_conditions']
                 if item['field'] == field)
    assert entry['actual'] == value
    assert entry['actual_type'] == type(value).__name__
    assert entry['passed'] is False
    assert finding['raw_status'] == raw
    assert finding['driver_counters']['rejected']['actual'] == 3
    assert finding['raw_status_receive_age_s'] == pytest.approx(0.01)
    assert finding['last_valid_raw_measurement']['stamp_s'] == 10.0
    assert finding['last_valid_raw_measurement']['age_at_fault_s'] == pytest.approx(0.05)


def test_first_fault_keeps_all_violations_and_original_snapshot_after_recovery():
    h = ready_health(now=10.0)
    assert h.source_failure(10.0) is None
    faulty = copy.deepcopy(h.statuses['raw'][0])
    faulty.update(ready=False, port='/wrong', consecutive_errors=4,
                  age_s=0.19)
    h.status('raw', faulty, 10.02)
    assert h.source_failure(10.03) == 'raw_driver_not_ready'
    original = h.first_fault_snapshot()
    assert original['violations'] == ['ready', 'port', 'consecutive_errors']
    h.status('raw', ready_health().statuses['raw'][0], 10.04)
    h.sample('raw', 10.04, 10.04, 10.04)
    assert h.source_failure(10.05) == 'raw_driver_not_ready'
    h.statuses['raw'][0]['ready'] = False
    h.statuses['raw'][0]['age_s'] = 5.0
    assert h.source_failure(10.06) == 'raw_driver_not_ready'
    changed_copy = h.first_fault_snapshot()
    changed_copy['raw_status']['port'] = 'tampered'
    assert h.first_fault_snapshot() == original


@pytest.mark.parametrize('field,value', [
    ('ready', None), ('raw_data_ready', 'true'), ('port', 123),
    ('sensor_write_commands', 0), ('consecutive_errors', '0'),
    ('age_s', '0.1'), ('age_s', math.nan), ('age_s', math.inf),
    ('age_s', -0.01),
])
def test_missing_or_wrong_type_and_nonfinite_raw_values_are_explained(field, value):
    h = ready_health(now=10.0)
    assert h.source_failure(10.0) is None
    raw = copy.deepcopy(h.statuses['raw'][0])
    raw[field] = value
    h.status('raw', raw, 10.01)
    assert h.source_failure(10.02) == 'raw_driver_not_ready'
    finding = h.first_fault_snapshot()
    assert field in finding['violations']
    assert next(item for item in finding['raw_conditions']
                if item['field'] == field)['actual_type'] == type(value).__name__
    json.dumps(finding, allow_nan=False)


@pytest.mark.parametrize('field', [
    'ready', 'raw_data_ready', 'port', 'sensor_write_commands',
    'consecutive_errors', 'age_s',
])
def test_missing_raw_field_is_explicit(field):
    h = ready_health(now=10.0)
    assert h.source_failure(10.0) is None
    raw = copy.deepcopy(h.statuses['raw'][0])
    del raw[field]
    h.status('raw', raw, 10.01)
    assert h.source_failure(10.02) == 'raw_driver_not_ready'
    entry = next(item for item in h.first_fault_snapshot()['raw_conditions']
                 if item['field'] == field)
    assert entry['present'] is False
    assert entry['actual_type'] == 'missing'


def test_status_age_measurement_age_and_driver_age_remain_distinct():
    h = ready_health(now=10.0)
    assert h.source_failure(10.0) is None
    raw = copy.deepcopy(h.statuses['raw'][0])
    raw['age_s'] = 0.15
    raw['ready'] = False
    h.status('raw', raw, 10.08)
    assert h.source_failure(10.10) == 'raw_driver_not_ready'
    finding = h.first_fault_snapshot()
    assert finding['raw_status_receive_age_s'] == pytest.approx(0.02)
    assert finding['last_valid_raw_measurement']['age_at_fault_s'] == pytest.approx(0.10)
    assert finding['raw_status_age_field_s'] == pytest.approx(0.15)


@pytest.mark.parametrize('received', [9.0, 11.0, math.nan, 'invalid'])
def test_bad_status_receive_time_remains_fail_closed_and_serializable(received):
    h = ready_health(now=10.0)
    assert h.source_failure(10.0) is None
    h.status('raw', copy.deepcopy(h.statuses['raw'][0]), received)
    now = 10.05
    if received == 9.0:
        # Old callback is ignored. The genuinely aged last selected status
        # still stops once its actual heartbeat expires.
        now = 11.05
        for key in ('raw','yaw','wheel'):
            h.sample(key,now,now,now)
        for key in ('yaw','wheel'):
            h.status(key,h.statuses[key][0],now)
        assert h.statuses['raw'][1] == 10.0
    assert h.source_failure(now) == 'raw_status_missing_or_stale'
    finding = h.first_fault_snapshot()
    assert 'raw_status_missing_or_stale' in finding['violations']
    assert finding['raw_status_age_field_s'] == 0.0
    json.dumps(finding, allow_nan=False)


def test_type_anomaly_is_visible_without_changing_existing_predicate():
    h = ready_health(now=10.0)
    assert h.source_failure(10.0) is None
    raw = copy.deepcopy(h.statuses['raw'][0])
    raw['consecutive_errors'] = False  # Existing Python equality accepts this.
    raw['port'] = '/wrong'
    h.status('raw', raw, 10.01)
    assert h.source_failure(10.02) == 'raw_driver_not_ready'
    entry = next(item for item in h.first_fault_snapshot()['raw_conditions']
                 if item['field'] == 'consecutive_errors')
    assert entry['passed'] is True
    assert entry['type_matches_expected'] is False


def test_sample_fault_snapshots_last_valid_measurement_and_status_heartbeat():
    h = ready_health(now=10.0)
    assert h.source_failure(10.0) is None
    h.sample('raw', 10.01, 10.01, 11.0)
    assert h.source_failure(10.02) == 'raw_missing_stale_or_invalid'
    finding = h.first_fault_snapshot()
    assert 'raw_sample_missing_stale_or_invalid' in finding['violations']
    assert finding['last_valid_raw_measurement']['stamp_s'] == 10.0
    assert finding['source_checks'][0]['sample_age_s'] == pytest.approx(-0.98)
    json.dumps(finding, allow_nan=False)


def test_diagnostic_exception_never_changes_existing_fail_closed_decision():
    h = ready_health(now=10.0)
    assert h.source_failure(10.0) is None
    h.statuses['raw'][0]['ready'] = False
    h._capture_first_fault = lambda now, reason: 1 / 0
    assert h.motion_failure(10.01) == 'raw_driver_not_ready'
    assert h.latched_fault == 'raw_driver_not_ready'
    assert h.first_fault_snapshot()['capture_error'] == 'ZeroDivisionError'


def test_startup_failure_is_not_mistaken_for_first_post_ready_fault():
    h = Hwt601FusionHealth(True)
    assert h.source_failure(1.0) == 'raw_missing_stale_or_invalid'
    assert h.first_fault_snapshot() is None


def _recovery_samples(health, start, end, *, faulty_raw=None):
    """Synthetic 100 Hz HWT / 2 Hz status, with no ROS or serial device."""
    step = int(round(start * 100))
    last = int(round(end * 100))
    for index in range(step, last + 1):
        now = index / 100.0
        for name in ('raw', 'yaw', 'wheel'):
            health.sample(name, now, now, now)
        if index % 50 == 0:
            raw = copy.deepcopy(health.statuses['raw'][0])
            raw.update(ready=True, raw_data_ready=True, state='bereit',
                       consecutive_errors=0, age_s=0.0)
            if faulty_raw is not None:
                raw.update(faulty_raw(index))
            health.status('raw', raw, now)
            for name in ('yaw', 'wheel'):
                health.status(name, copy.deepcopy(health.statuses[name][0]), now)
        health.source_failure(now)


@pytest.mark.parametrize('fault', ['raw_gap', 'raw_not_ready', 'read_error'])
def test_transient_fault_holds_then_resumes_after_stable_new_sources(fault):
    h = ready_health(now=10.0)
    assert h.motion_failure(10.0) is None
    if fault == 'raw_gap':
        h.sample('yaw', 10.21, 10.21, 10.21)
        h.sample('wheel', 10.21, 10.21, 10.21)
        assert h.motion_failure(10.21) == 'raw_missing_stale_or_invalid'
    else:
        raw = copy.deepcopy(h.statuses['raw'][0])
        raw.update(ready=False, raw_data_ready=False, state='degradiert')
        if fault == 'read_error':
            raw['consecutive_errors'] = 1
        h.status('raw', raw, 10.01)
        assert h.motion_failure(10.01) == 'raw_driver_not_ready'
    assert h.recovery_state == 'HOLD'
    first = h.first_fault_snapshot()
    assert h.latched_fault is None
    _recovery_samples(h, 10.22, 11.8)
    assert h.recovery_state == 'HEALTHY'
    assert h.motion_failure(11.8) is None
    assert h.first_fault_snapshot() == first
    assert [event['state'] for event in h.recovery_events] == [
        'HOLD', 'RECOVERY_VALIDATION', 'HEALTHY']


def test_single_good_sample_cannot_release_motion_or_erase_first_fault():
    h = ready_health(now=10.0)
    h.source_failure(10.0)
    raw = copy.deepcopy(h.statuses['raw'][0])
    raw.update(ready=False, raw_data_ready=False, state='degradiert')
    h.status('raw', raw, 10.01)
    assert h.motion_failure(10.01) == 'raw_driver_not_ready'
    h.sample('raw', 10.02, 10.02, 10.02)
    h.status('raw', ready_health().statuses['raw'][0], 10.02)
    assert h.motion_failure(10.02) == 'raw_driver_not_ready'
    assert h.recovery_state == 'RECOVERY_VALIDATION'
    assert h.first_fault_snapshot() is not None


def test_persistent_or_repeated_fault_exhausts_one_bounded_budget():
    h = ready_health(now=10.0)
    h.source_failure(10.0)
    raw = copy.deepcopy(h.statuses['raw'][0])
    raw.update(ready=False, raw_data_ready=False, state='degradiert')
    h.status('raw', raw, 10.01)
    assert h.motion_failure(10.01) == 'raw_driver_not_ready'
    h.status('raw', ready_health().statuses['raw'][0], 10.02)
    _recovery_samples(h, 10.02, 10.45)
    assert h.recovery_state == 'RECOVERY_VALIDATION'
    h.status('raw', raw, 10.46)
    assert h.motion_failure(10.46) == 'raw_driver_not_ready'
    assert h.recovery_state == 'HOLD'
    assert h._raw_samples_since_hold == 0
    assert h._raw_statuses_since_hold == 0
    h.status('raw', ready_health().statuses['raw'][0], 10.47)
    _recovery_samples(h, 10.47, 10.70)
    assert h.recovery_state == 'RECOVERY_VALIDATION'
    # A second good interval does not reset the original deadline.
    assert h.motion_failure(15.01) == 'hwt_recovery_budget_exhausted'
    assert h.recovery_state == 'TERMINAL_FAULT'
    assert h.latched_fault == 'hwt_recovery_budget_exhausted'


@pytest.mark.parametrize('field,value', [
    ('port', '/dev/ttyUSB_BASE'),
    ('sensor_write_commands', True),
    ('reconnects', 1),
    ('age_s', math.nan),
])
def test_hard_raw_fault_never_auto_resumes(field, value):
    h = ready_health(now=10.0)
    h.source_failure(10.0)
    raw = copy.deepcopy(h.statuses['raw'][0])
    raw[field] = value
    h.status('raw', raw, 10.01)
    assert h.motion_failure(10.01) is not None
    assert h.recovery_state == 'TERMINAL_FAULT'
    _recovery_samples(h, 10.02, 11.8)
    assert h.motion_failure(11.8) == h.latched_fault


def test_bias_loss_remains_terminal_even_with_recovered_raw_data():
    h = ready_health(now=10.0)
    h.source_failure(10.0)
    yaw = copy.deepcopy(h.statuses['yaw'][0])
    yaw['bias']['stable'] = False
    h.status('yaw', yaw, 10.01)
    assert h.motion_failure(10.01) == 'yaw_uncalibrated_or_faulted'
    assert h.recovery_state == 'TERMINAL_FAULT'


def test_repeated_separate_transient_holds_have_no_endless_retry():
    h = ready_health(now=10.0)
    h.source_failure(10.0)
    for fault_at, recovered_at in ((10.01, 11.8), (11.81, 13.5)):
        raw = copy.deepcopy(h.statuses['raw'][0])
        raw.update(ready=False, raw_data_ready=False, state='degradiert')
        h.status('raw', raw, fault_at)
        assert h.motion_failure(fault_at) == 'raw_driver_not_ready'
        _recovery_samples(h, fault_at + 0.01, recovered_at)
        assert h.recovery_state == 'HEALTHY'
    assert h.recovery_attempts == 2
    raw = copy.deepcopy(h.statuses['raw'][0])
    raw.update(ready=False, raw_data_ready=False, state='degradiert')
    h.status('raw', raw, 13.51)
    assert h.motion_failure(13.51) == 'hwt_recovery_attempt_limit'
    assert h.recovery_state == 'TERMINAL_FAULT'


def pending_wheel(h,now=10.):
    w=h.statuses['wheel'][0]
    w.update(ready=False,state='timing_recovery',timing_recovery_pending=True,
             connected=True,configuration_valid=True,port='/dev/ttyUSB_BASE',
             continuity_max_gap_s=.18,timing_recovery_valid_pairs=0,
             odometry_continuity_valid=True,timing_recovery_budget_s=2.,
             timing_recovery_attempt_limit=2,timing_recovery_count=1,
             timing_recovery_deadline_s=now+2.)
    h.status('wheel',w,now)


def test_passive_timing_validation_uses_hold_without_a_second_latch():
    h=ready_health(False);assert h.source_failure(10.) is None
    pending_wheel(h)
    assert h.source_failure(10.05)=='wheel_timing_recovery_pending'
    assert h.recovery_state=='HOLD' and h.latched_fault is None
    w=h.statuses['wheel'][0];w.update(ready=True,state='ready',timing_recovery_pending=False)
    for i in range(1,90):
        now=10.05+i*.02
        for key in ['raw','yaw','wheel']:
            h.sample(key,now,now,now);h.status(key,h.statuses[key][0],now)
        h.source_failure(now)
    assert h.recovery_state=='HEALTHY' and h.latched_fault is None
    assert h.motion_failure(now)=='readonly_preflight_no_motion'


@pytest.mark.parametrize('change',['stale','port','fault','connection','config','motion','bound'])
def test_pending_wheel_cannot_mask_hard_faults(change):
    h=ready_health(False);assert h.source_failure(10.) is None
    pending_wheel(h);w=h.statuses['wheel'][0];now=10.05
    if change=='stale':now=12.01
    if change=='port':w['port']='/dev/ttyUSB_HWT601'
    if change=='fault':w['fault_latched']=True
    if change=='connection':w['connected']=False
    if change=='config':w['configuration_valid']=False
    if change=='motion':w['actuator_output']=True
    if change=='bound':w['continuity_max_gap_s']=.181
    assert h.source_failure(now) is not None
    assert h.recovery_state=='TERMINAL_FAULT'


def test_passive_timing_recovery_status_never_relaxes_active_driver_contract():
    h=ready_health(True);assert h.source_failure(10.) is None
    pending_wheel(h)
    h.statuses['wheel'][0]['encoder_feedback_ok']=False
    assert h.source_failure(10.05)=='wheel_not_real_or_not_ready'
    assert h.recovery_state=='TERMINAL_FAULT'


def test_stale_wheel_with_verified_pending_read_blocks_motion_but_preserves_parent():
    h=ready_health(False);assert h.source_failure(10.) is None
    pending_wheel(h,10.19)
    # Raw/yaw remain current while the original wheel ages beyond 180 ms.
    for name in ('raw','yaw'):
        h.sample(name,10.19,10.19,10.19);h.status(name,h.statuses[name][0],10.19)
    reason=h.motion_failure(10.19)
    assert reason=='wheel_missing_stale_or_invalid'
    assert h.recovery_state=='HOLD' and h.latched_fault is None
    assert h.samples['wheel'][2]==10.  # original measurement unchanged
    assert h.wheel_recovery_attempts==1


def test_hwt_recovery_then_wheel_hold_has_separate_original_event_and_budget():
    h=ready_health(False);assert h.source_failure(10.) is None
    for key in ('yaw','wheel'):
        h.sample(key,10.21,10.21,10.21);h.status(key,h.statuses[key][0],10.21)
    assert h.source_failure(10.21)=='raw_missing_stale_or_invalid'
    for i in range(1,90):
        now=10.21+i*.02
        for key in ('raw','yaw','wheel'):
            h.sample(key,now,now,now);h.status(key,h.statuses[key][0],now)
        h.source_failure(now)
    assert h.recovery_state=='HEALTHY' and h.recovery_attempts==1
    pending_wheel(h,now)
    assert h.source_failure(now)=='wheel_timing_recovery_pending'
    assert h.wheel_recovery_attempts==1 and h.recovery_attempts==1
    assert h.last_fault['aggregate_reason']=='wheel_timing_recovery_pending'
    assert h.fault_snapshot()['aggregate_reason']=='wheel_timing_recovery_pending'
    assert h.first_fault_snapshot()['aggregate_reason']=='raw_missing_stale_or_invalid'


def test_read_in_flight_heartbeat_can_hold_before_pair_deadline_result_arrives():
    h=ready_health(False);assert h.source_failure(10.) is None
    w=h.statuses['wheel'][0]
    w.update(ready=False,state='initializing',connected=True,configuration_valid=True,
             port='/dev/ttyUSB_BASE',baseline_count=1,complete_pair_count=20,
             odometry_continuity_valid=True,timing_recovery_budget_s=2.,
             timing_recovery_attempt_limit=2,last_feedback_age_s=.181)
    h.status('wheel',w,10.181)
    for key in ('raw','yaw'):
        h.sample(key,10.181,10.181,10.181);h.status(key,h.statuses[key][0],10.181)
    assert h.motion_failure(10.181)=='wheel_missing_stale_or_invalid'
    assert h.recovery_state=='HOLD' and h.samples['wheel'][2]==10.
    w['fault_latched']=True;h.status('wheel',w,10.19)
    assert h.source_failure(10.19) is not None and h.recovery_state=='TERMINAL_FAULT'


def development_health(now=10.):
    h=ready_health(now=now,development=True)
    h.statuses['raw'][0].update(contract='metric_development_v1',identity_intact=True,
        terminal_fault=None,data_valid=True,data_fresh=True,transport_ok=True,
        transport_degraded=False,response_timeout_s=.05,sensor_timeout_s=.30)
    assert h.source_failure(now) is None
    return h


def development_raw_gap(h,now):
    for source in ('yaw','wheel'):
        h.sample(source,now,now,now)
        h.status(source,copy.deepcopy(h.statuses[source][0]),now)
    raw=copy.deepcopy(h.statuses['raw'][0]);raw.update(ready=False,raw_data_ready=False,
        data_fresh=False,transport_ok=False,transport_degraded=True,
        consecutive_errors=7,age_s=.31,state='degradiert')
    h.status('raw',raw,now)
    assert h.source_failure(now)=='raw_missing_stale_or_invalid'
    assert h.recovery_state=='HOLD'
    h.statuses['raw'][0].update(transport_ok=True,transport_degraded=False,data_fresh=True)
    _recovery_samples(h,now+.01,now+1.6)
    assert h.recovery_state=='HEALTHY'


def test_development_poll_timeout_with_fresh_data_does_not_spend_hold_budget():
    h=development_health();raw=h.statuses['raw'][0]
    raw.update(consecutive_errors=1,state='transport_degraded',transport_ok=False,
        transport_degraded=True,age_s=.037327,last_error='Zeitueberschreitung nach 0/14 Bytes')
    assert h.source_failure(10.037327) is None
    assert h.recovery_attempts==0 and not h.hwt_hold_times
    assert h.contract_diagnostics(10.037327)['transport_degraded'] is True
    # Do not restamp the old raw message when the transport errors continue.
    for source in ('yaw','wheel'):h.sample(source,10.29,10.29,10.29)
    raw.update(consecutive_errors=5,age_s=.29)
    assert h.source_failure(10.29) is None
    for source in ('yaw','wheel'):h.sample(source,10.301,10.301,10.301)
    assert h.source_failure(10.301)=='raw_missing_stale_or_invalid'
    assert h.recovery_state=='HOLD' and h.recovery_attempts==1


def test_development_three_recovered_holds_minutes_apart_are_not_lifetime_terminal():
    h=development_health()
    previous = 10.0
    for now in (10.31,172.718,411.729):
        _recovery_samples(h, previous + .01, now - .31)
        development_raw_gap(h,now)
        previous = now + 1.6
    assert h.recovery_attempts==3 and h.hwt_attempts_in_window(413.4)==1
    assert h.latched_fault is None


def test_development_third_hold_in_sliding_60_seconds_is_terminal():
    h=development_health()
    development_raw_gap(h,10.31);development_raw_gap(h,20.31)
    for source in ('yaw','wheel'):h.sample(source,30.31,30.31,30.31)
    h.status('raw',copy.deepcopy(h.statuses['raw'][0]),30.31)
    assert h.source_failure(30.31)=='hwt_recovery_attempt_limit'
    assert h.recovery_state=='TERMINAL_FAULT'


def test_development_recovery_remains_absolute_five_seconds():
    h=development_health()
    for source in ('yaw','wheel'):h.sample(source,10.31,10.31,10.31)
    assert h.source_failure(10.31)=='raw_missing_stale_or_invalid'
    for step in range(1,502):
        now=10.31+step*.01
        for source in ('yaw','wheel'):h.sample(source,now,now,now)
        for source in ('raw','yaw','wheel'):h.status(source,copy.deepcopy(h.statuses[source][0]),now)
        h.source_failure(now)
    assert h.latched_fault=='hwt_recovery_budget_exhausted'


@pytest.mark.parametrize('change',[{'port':'/dev/ttyUSB_BASE'}, {'identity_intact':False},
    {'terminal_fault':'CRC'}, {'data_valid':False}, {'sensor_timeout_s':.31},
    {'contract':'legacy'}, {'response_timeout_s':.06}])
def test_development_hard_identity_data_protocol_contract_failure_never_recovers(change):
    h=development_health();h.statuses['raw'][0].update(change)
    assert h.source_failure(10.01) is not None
    assert h.recovery_state=='TERMINAL_FAULT'
    h.statuses['raw'][0].update(data_valid=True,identity_intact=True,terminal_fault=None)
    assert h.source_failure(10.02) is not None


def test_development_yaw_boundary_preserves_still_fresh_original_sample():
    health=development_health();assert health.source_failure(10.) is None
    # A 200-ms input gap: the core discards its boundary sample. Its last
    # ORIGINAL corrected measurement is still inside the existing 350 ms.
    health.sample('raw',10.2,10.2,10.2);health.sample('wheel',10.2,10.2,10.2)
    health.statuses['yaw'][0].update(ready=False,data_continuity_pending=True,age_s=.2)
    original=health.samples['yaw']
    assert health.source_failure(10.2) is None
    assert health.recovery_attempts==0 and health.samples['yaw']==original
    health.sample('wheel',10.511,10.511,10.511)
    assert health.source_failure(10.511)=='raw_missing_stale_or_invalid'
    assert health.recovery_state=='HOLD' and health.recovery_attempts==1


def test_development_yaw_boundary_does_not_hide_invalid_or_unfrozen_original():
    for field,value in [('bias_frozen_after_startup',False),('latched_fault','imu_zeitfehler')]:
        health=development_health();assert health.source_failure(10.) is None
        health.statuses['yaw'][0].update(ready=False,data_continuity_pending=True,age_s=.02)
        health.statuses['yaw'][0][field]=value
        assert health.source_failure(10.02) is not None
        assert health.recovery_state=='TERMINAL_FAULT'
