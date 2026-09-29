"""Raw-input contract for the existing HWT mapping profile, not an EKF health proxy."""

import copy
import math
import threading
import time


_RAW_EXPECTATIONS = (
    ('ready', True, lambda value: value is True),
    ('raw_data_ready', True, lambda value: value is True),
    ('port', '/dev/ttyUSB_HWT601',
     lambda value: value == '/dev/ttyUSB_HWT601'),
    ('sensor_write_commands', False, lambda value: value is False),
    ('consecutive_errors', 0, lambda value: value == 0),
    ('age_s', 'finite number in [0.0, 0.20] s',
     lambda value: age_valid(value, 0.20)),
)


def _json_value(value):
    """Copy a parsed status value without emitting nonstandard JSON numbers."""
    if value is None or type(value) in (str, bool, int):
        return value
    if type(value) is float:
        return value if math.isfinite(value) else {'nonfinite_float': str(value)}
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    return {'unsupported_type': type(value).__name__}


def _typed_field(payload, name, expected, passed, expected_type=None):
    present = name in payload
    value = payload.get(name)
    return {
        'field': name,
        'present': present,
        'actual': _json_value(value) if present else None,
        'actual_type': type(value).__name__ if present else 'missing',
        'expected': expected,
        'type_matches_expected': (
            type(value) in expected_type if present and expected_type else None),
        'passed': bool(passed),
    }


def _elapsed(now, then):
    if type(now) not in (int, float) or type(then) not in (int, float):
        return None
    return _json_value(now - then)


def fresh(now, then, limit):
    return (isinstance(then, (int, float)) and math.isfinite(then)
            and math.isfinite(now) and 0.0 <= now - then <= limit)


def age_valid(value, limit):
    return (type(value) in (int, float) and math.isfinite(value)
            and 0.0 <= value <= limit)


class Hwt601FusionHealth:
    """Check real inputs and bound post-readiness recovery without motion.

    Limits are from hwt601_shadow.yaml (raw .20, corrected .35),
    base_hardware_params.yaml (.30), the read-only encoder shadow profile
    (.18), and the historical 1 s status heartbeat contract. EKF output is
    NOT an input.
    """

    def __init__(self, active_drive, observer='unspecified'):
        self.active_drive = active_drive is True
        self.observer = str(observer)
        self.samples = {}
        self.statuses = {}
        self.was_ready = False
        self.latched_fault = None
        self._first_fault = None
        self._last_valid_raw_sample = None
        self.recovery_state = 'STARTUP'
        self._hold_since = None
        self._healthy_since = None
        self._hold_reason = None
        self._raw_samples_since_hold = 0
        self._raw_statuses_since_hold = 0
        self._last_healthy_reconnects = None
        self.recovery_events = []
        self.recovery_attempts = 0
        # The driver reconnects after its third consecutive read error.
        # This profile permits at most two completed/started transient holds
        # per Health lifetime; a third requires stopped human inspection.
        self.recovery_attempt_limit = 2
        # 100 Hz raw source, 2 Hz status and 1 s status-heartbeat contract:
        # require >=20 new raw samples, >=2 new status frames and 1 s healthy.
        # The 5 s total includes the existing 3 s Nav2 cancel bound plus two
        # status-heartbeat intervals; it never relaxes motion freshness.
        self.recovery_window_s = 1.0
        self.recovery_budget_s = 5.0
        self.lock = threading.RLock()

    def sample(self, name, stamp, received, observed, valid=True):
        with self.lock:
            previous = self.samples.get(name)
            # Reentrant ROS callbacks can enter in sensor order but reach this
            # lock in reverse order. An older callback must not overwrite an
            # already accepted, newer measurement. A timestamp regression in
            # callback entry order remains invalid and fail-closed.
            if (previous is not None and previous[3] and valid
                    and type(stamp) in (int, float) and math.isfinite(stamp)
                    and type(received) in (int, float) and math.isfinite(received)
                    and type(observed) in (int, float) and math.isfinite(observed)
                    and stamp < previous[0] and received < previous[1]
                    and observed < previous[2]):
                return
            valid = (valid and math.isfinite(stamp) and stamp > 0
                     and (previous is None or stamp > previous[0]))
            self.samples[name] = (stamp, received, observed, valid)
            if name == 'raw' and self._hold_since is not None and valid:
                self._raw_samples_since_hold += 1
            if (name == 'raw' and valid
                    and type(received) in (int, float)
                    and type(observed) in (int, float)
                    and fresh(received, observed, 0.20)):
                self._last_valid_raw_sample = (stamp, received, observed)

    def status(self, name, payload, received):
        with self.lock:
            self.statuses[name] = (payload if isinstance(payload, dict) else {}, received)
            if name == 'raw' and self._hold_since is not None:
                self._raw_statuses_since_hold += 1

    def _raw_identity_intact(self):
        entry = self.statuses.get('raw')
        if entry is None:
            return False
        raw = entry[0]
        reconnects = raw.get('reconnects')
        return (raw.get('port') == '/dev/ttyUSB_HWT601'
                and raw.get('sensor_write_commands') is False
                and (raw.get('ready') is True
                     or (raw.get('ready') is False
                         and raw.get('state') == 'degradiert'))
                and type(raw.get('raw_data_ready')) is bool
                and raw['ready'] is raw['raw_data_ready']
                and type(raw.get('consecutive_errors')) is int
                and 0 <= raw['consecutive_errors'] < 3
                and type(reconnects) is int
                and reconnects == self._last_healthy_reconnects
                and type(raw.get('age_s')) in (int, float)
                and math.isfinite(raw['age_s'])
                and raw['age_s'] >= 0.0)

    def _hard_status_failure(self):
        """Check hard invariants even if _failure found a stale sample first."""
        if not self._raw_identity_intact():
            return 'raw_identity_or_configuration_fault'
        yaw_entry = self.statuses.get('yaw')
        wheel_entry = self.statuses.get('wheel')
        if yaw_entry is None or wheel_entry is None:
            return 'required_status_missing'
        yaw = yaw_entry[0]
        bias = yaw.get('bias')
        pending = yaw.get('data_continuity_pending', False)
        yaw_ready_or_gap = (
            (yaw.get('ready') is True and pending is False)
            or (yaw.get('ready') is False and pending is True))
        if not (type(pending) is bool and yaw_ready_or_gap
                and yaw.get('operator_stationary_confirmed') is True
                and yaw.get('bias_frozen_after_startup') is True
                and 'latched_fault' in yaw and yaw['latched_fault'] is None
                and isinstance(bias, dict)
                and bias.get('calibrated') is True
                and bias.get('stable') is True
                and bias.get('adaptation_samples') == 0
                and type(yaw.get('age_s')) in (int, float)
                and math.isfinite(yaw['age_s']) and yaw['age_s'] >= 0.0):
            return 'yaw_calibration_or_identity_fault'
        wheel = wheel_entry[0]
        if self.active_drive:
            valid = (wheel.get('dry_run') is False
                     and wheel.get('allow_rs485') is True
                     and wheel.get('rs485_ready') is True
                     and wheel.get('odometry_source') == 'encoder_position'
                     and wheel.get('encoder_feedback_ok') is True
                     and wheel.get('encoder_stale') is False
                     and wheel.get('encoder_config_fault_latched') is False
                     and type(wheel.get('encoder_feedback_age_s')) in (int, float)
                     and math.isfinite(wheel['encoder_feedback_age_s'])
                     and wheel['encoder_feedback_age_s'] >= 0.0)
        else:
            valid = (wheel.get('ready') is True
                     and wheel.get('source') == 'ess23_absolute_fc03'
                     and wheel.get('synthetic') is False
                     and wheel.get('command_derived') is False
                     and wheel.get('read_only') is True
                     and wheel.get('actuator_output') is False
                     and wheel.get('fault_latched') is False
                     and type(wheel.get('last_feedback_age_s')) in (int, float)
                     and math.isfinite(wheel['last_feedback_age_s'])
                     and wheel['last_feedback_age_s'] >= 0.0)
        return None if valid else 'wheel_identity_or_configuration_fault'

    def _recoverable(self, reason, now):
        if self._hard_status_failure() is not None:
            return False
        if reason in ('raw_missing_stale_or_invalid',
                      'yaw_missing_stale_or_invalid'):
            name = reason.split('_', 1)[0]
            sample = self.samples.get(name)
            return (sample is None or
                    (sample[3] and all(
                        type(value) in (int, float) and math.isfinite(value)
                        for value in sample[:3])
                     and now >= sample[1] >= sample[2]))
        if reason == 'raw_driver_not_ready':
            raw = self.statuses['raw'][0]
            return (raw['raw_data_ready'] is False
                    or 0 < raw['consecutive_errors'] < 3
                    or raw['age_s'] > 0.20)
        if reason == 'yaw_data_continuity_pending':
            yaw = self.statuses['yaw'][0]
            return (yaw.get('ready') is False
                    and yaw.get('data_continuity_pending') is True)
        return False

    def _event(self, now, state, reason):
        self.recovery_events.append({
            'state': state, 'reason': reason, 'monotonic_s': now})

    def _terminal(self, now, reason):
        self.recovery_state = 'TERMINAL_FAULT'
        self.latched_fault = reason
        self._event(now, self.recovery_state, reason)
        return reason

    def _failure(self, now):
        wheel_limit = 0.30 if self.active_drive else 0.18
        for name, limit in (('raw', 0.20), ('yaw', 0.35), ('wheel', wheel_limit)):
            sample = self.samples.get(name)
            if (sample is None or not sample[3]
                    or not fresh(now, sample[1], limit)
                    or not fresh(now, sample[2], limit)):
                return name + '_missing_stale_or_invalid'
        for name in ('raw', 'yaw', 'wheel'):
            status = self.statuses.get(name)
            if status is None or not fresh(now, status[1], 1.0):
                return name + '_status_missing_or_stale'

        raw = self.statuses['raw'][0]
        if not (raw.get('ready') is True and raw.get('raw_data_ready') is True
                and raw.get('port') == '/dev/ttyUSB_HWT601'
                and raw.get('sensor_write_commands') is False
                and raw.get('consecutive_errors') == 0
                and age_valid(raw.get('age_s'), 0.20)):
            return 'raw_driver_not_ready'
        yaw = self.statuses['yaw'][0]
        bias = yaw.get('bias')
        if (yaw.get('ready') is False
                and yaw.get('data_continuity_pending') is True
                and yaw.get('latched_fault') is None
                and isinstance(bias, dict)
                and bias.get('calibrated') is True
                and bias.get('stable') is True
                and bias.get('adaptation_samples') == 0):
            return 'yaw_data_continuity_pending'
        if not (yaw.get('ready') is True
                and yaw.get('operator_stationary_confirmed') is True
                and yaw.get('bias_frozen_after_startup') is True
                and 'latched_fault' in yaw and yaw['latched_fault'] is None
                and isinstance(bias, dict)
                and bias.get('calibrated') is True and bias.get('stable') is True
                and bias.get('adaptation_samples') == 0
                and age_valid(yaw.get('age_s'), 0.35)):
            return 'yaw_uncalibrated_or_faulted'
        wheel = self.statuses['wheel'][0]
        if self.active_drive:
            valid = (wheel.get('dry_run') is False
                     and wheel.get('allow_rs485') is True
                     and wheel.get('rs485_ready') is True
                     and wheel.get('odometry_source') == 'encoder_position'
                     and wheel.get('encoder_feedback_ok') is True
                     and wheel.get('encoder_stale') is False
                     and wheel.get('encoder_config_fault_latched') is False
                     and age_valid(wheel.get('encoder_feedback_age_s'), wheel_limit))
        else:
            valid = (wheel.get('ready') is True
                     and wheel.get('source') == 'ess23_absolute_fc03'
                     and wheel.get('synthetic') is False
                     and wheel.get('command_derived') is False
                     and wheel.get('read_only') is True
                     and wheel.get('actuator_output') is False
                     and wheel.get('fault_latched') is False
                     and age_valid(wheel.get('last_feedback_age_s'), wheel_limit))
        return None if valid else 'wheel_not_real_or_not_ready'

    def _capture_first_fault(self, now, reason):
        """Snapshot only the first post-readiness fault; never drive a decision."""
        raw_status = self.statuses.get('raw')
        raw = raw_status[0] if raw_status is not None else {}
        conditions = []
        expected_types = {
            'ready': (bool,), 'raw_data_ready': (bool,),
            'port': (str,), 'sensor_write_commands': (bool,),
            'consecutive_errors': (int,), 'age_s': (int, float),
        }
        for name, expected, check in _RAW_EXPECTATIONS:
            value = raw.get(name)
            conditions.append(_typed_field(
                raw, name, expected, name in raw and check(value),
                expected_types[name]))
        violations = [entry['field'] for entry in conditions
                      if not entry['passed']]
        source_checks = []
        for name, limit in (('raw', 0.20), ('yaw', 0.35),
                            ('wheel', 0.30 if self.active_drive else 0.18)):
            sample = self.samples.get(name)
            status = self.statuses.get(name)
            sample_ok = (sample is not None and sample[3]
                         and fresh(now, sample[1], limit)
                         and fresh(now, sample[2], limit))
            status_ok = status is not None and fresh(now, status[1], 1.0)
            source_checks.append({
                'source': name,
                'sample_stamp_s':
                    _json_value(sample[0]) if sample is not None else None,
                'sample_received_monotonic_s':
                    _json_value(sample[1]) if sample is not None else None,
                'sample_observed_monotonic_s':
                    _json_value(sample[2]) if sample is not None else None,
                'sample_age_s':
                    _elapsed(now, sample[2]) if sample is not None else None,
                'sample_valid': bool(sample[3]) if sample is not None else None,
                'sample_fresh_and_valid': bool(sample_ok),
                'sample_limit_s': limit,
                'status_received_monotonic_s':
                    _json_value(status[1]) if status is not None else None,
                'status_receive_age_s':
                    _elapsed(now, status[1]) if status is not None else None,
                'status_fresh': bool(status_ok),
                'status_limit_s': 1.0,
            })
            if not sample_ok:
                violations.append(name + '_sample_missing_stale_or_invalid')
            if not status_ok:
                violations.append(name + '_status_missing_or_stale')
        last = self._last_valid_raw_sample
        raw_received = raw_status[1] if raw_status is not None else None
        return {
            'component': 'Hwt601FusionHealth',
            'observer': self.observer,
            'aggregate_reason': reason,
            'active_drive': self.active_drive,
            'evaluation_monotonic_s': _json_value(now),
            'evaluation_unix_s': _json_value(time.time()),
            'raw_status_received_monotonic_s': _json_value(raw_received),
            'raw_status_received_type': (
                type(raw_received).__name__ if raw_status is not None else 'missing'),
            'raw_status_receive_age_s': _elapsed(now, raw_received),
            'raw_status_age_field_s': _json_value(raw.get('age_s')),
            'last_valid_raw_measurement': None if last is None else {
                'stamp_s': _json_value(last[0]),
                'received_monotonic_s': _json_value(last[1]),
                'observed_monotonic_s': _json_value(last[2]),
                'age_at_fault_s': _elapsed(now, last[2]),
            },
            'raw_conditions': conditions,
            'violations': violations,
            'source_checks': source_checks,
            'raw_status': _json_value(raw),
            'driver_counters': {
                key: _typed_field(raw, key, 'observed only', key in raw)
                for key in ('accepted', 'rejected', 'successful_connections',
                            'reconnects', 'consecutive_errors', 'last_error')
            },
        }

    def first_fault_snapshot(self):
        with self.lock:
            return copy.deepcopy(self._first_fault)

    def source_failure(self, now=None):
        with self.lock:
            # Snapshot time after acquiring the same lock as callbacks.
            # A concurrently received sample must not appear future-dated.
            if now is None:
                now = time.monotonic()
            if self.latched_fault is not None:
                return self.latched_fault
            reason = self._failure(now)
            if reason is None and not self.was_ready:
                self.was_ready = True
                self.recovery_state = 'HEALTHY'
                reconnects = self.statuses['raw'][0].get('reconnects')
                self._last_healthy_reconnects = (
                    reconnects if type(reconnects) is int else None)
                return None
            if not self.was_ready:
                return reason
            hard = self._hard_status_failure()
            observed_reason = reason or hard
            if observed_reason is not None and self._first_fault is None:
                try:
                    self._first_fault = self._capture_first_fault(
                        now, observed_reason)
                except Exception as exc:
                    # Diagnostic formatting must never affect the stop.
                    self._first_fault = {
                        'component': 'Hwt601FusionHealth',
                        'aggregate_reason': observed_reason,
                        'capture_error': type(exc).__name__,
                    }
            if hard is not None:
                return self._terminal(now, observed_reason)
            if self.recovery_state == 'HEALTHY':
                if reason is None:
                    return None
                if not self._recoverable(reason, now):
                    return self._terminal(now, reason)
                if self.recovery_attempts >= self.recovery_attempt_limit:
                    return self._terminal(now, 'hwt_recovery_attempt_limit')
                self.recovery_attempts += 1
                self.recovery_state = 'HOLD'
                self._hold_since = now
                self._hold_reason = reason
                self._raw_samples_since_hold = 0
                self._raw_statuses_since_hold = 0
                self._event(now, 'HOLD', reason)
                return reason
            if now - self._hold_since >= self.recovery_budget_s:
                return self._terminal(now, 'hwt_recovery_budget_exhausted')
            if reason is not None:
                if not self._recoverable(reason, now):
                    return self._terminal(now, reason)
                if self.recovery_state == 'RECOVERY_VALIDATION':
                    self.recovery_state = 'HOLD'
                    self._healthy_since = None
                    self._raw_samples_since_hold = 0
                    self._raw_statuses_since_hold = 0
                    self._event(now, 'HOLD', reason)
                return self._hold_reason
            if self.recovery_state == 'HOLD':
                self.recovery_state = 'RECOVERY_VALIDATION'
                self._healthy_since = now
                self._event(now, 'RECOVERY_VALIDATION', self._hold_reason)
            if (now - self._healthy_since >= self.recovery_window_s
                    and self._raw_samples_since_hold >= 20
                    and self._raw_statuses_since_hold >= 2):
                self.recovery_state = 'HEALTHY'
                self._hold_since = None
                self._healthy_since = None
                self._event(now, 'HEALTHY', 'recovered')
                return None
            return self._hold_reason

    def motion_failure(self, now=None):
        return self.source_failure(now) or (
            None if self.active_drive else 'readonly_preflight_no_motion')
