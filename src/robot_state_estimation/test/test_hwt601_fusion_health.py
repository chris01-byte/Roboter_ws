import copy
import math

import pytest

from robot_state_estimation.hwt601_fusion_health import Hwt601FusionHealth


def ready_health(active=True, now=10.0):
    health = Hwt601FusionHealth(active)
    for key in ('raw', 'yaw', 'wheel'):
        health.sample(key, now, now, now)
    health.status('raw', {
        'ready': True, 'raw_data_ready': True, 'port': '/dev/ttyUSB_HWT601',
        'sensor_write_commands': False, 'consecutive_errors': 0, 'age_s': 0.0,
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
