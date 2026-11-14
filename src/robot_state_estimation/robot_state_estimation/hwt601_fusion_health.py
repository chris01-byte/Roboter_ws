"""Raw-input contract for the existing HWT mapping profile, not an EKF health proxy."""

import copy
from collections import deque
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

    def __init__(self, active_drive, observer='unspecified', development_contract=False):
        self.active_drive = active_drive is True
        self.development_contract = development_contract is True
        self.raw_max_age_s = .30 if self.development_contract else .20
        self.hwt_recovery_interval_s = 60.0 if self.development_contract else None
        self.hwt_hold_times = deque()
        self.observer = str(observer)
        self.samples = {}
        self.sample_details = {}
        self.sample_validation = {}
        self.ignored_older_callbacks = {}
        self._event_sequence = 0
        self._last_event_state = 'STARTUP'
        self.last_successful_recovery = None
        self.last_fault = None
        self._startup_reason = None
        self.last_source_failure = 'startup_not_evaluated'
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
        self.wheel_recovery_attempts = 0
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

    def sample(self, name, stamp, received, observed, valid=True, details=None):
        with self.lock:
            previous = self.samples.get(name)
            # Reentrant ROS callbacks can enter in sensor order but reach this
            # lock in reverse order. An older callback must not overwrite an
            # already accepted, newer measurement. A timestamp regression in
            # callback entry order remains invalid and fail-closed.
            if (previous is not None
                    and type(stamp) in (int, float) and math.isfinite(stamp)
                    and type(received) in (int, float) and math.isfinite(received)
                    and type(observed) in (int, float) and math.isfinite(observed)
                    and stamp < previous[0] and received < previous[1]):
                self.ignored_older_callbacks[name] = self.ignored_older_callbacks.get(name, 0)+1
                return
            self.sample_validation[name] = {
                'content_valid': bool(valid),
                'stamp_finite_positive': bool(math.isfinite(stamp) and stamp > 0),
                'previous_stamp_s': _json_value(previous[0]) if previous else None,
                'strictly_newer_stamp': previous is None or stamp > previous[0],
            }
            valid = (valid and math.isfinite(stamp) and stamp > 0
                     and (previous is None or stamp > previous[0]))
            self.samples[name] = (stamp, received, observed, valid)
            self.sample_details[name] = _json_value(details or {})
            if name == 'raw' and self._hold_since is not None and valid:
                self._raw_samples_since_hold += 1
            if (name == 'raw' and valid
                    and type(received) in (int, float)
                    and type(observed) in (int, float)
                    and fresh(received, observed, self.raw_max_age_s)):
                self._last_valid_raw_sample = (stamp, received, observed)

    def status(self, name, payload, received):
        with self.lock:
            previous = self.statuses.get(name)
            if (previous is not None and type(received) in (int,float)
                    and type(previous[1]) in (int,float) and received < previous[1]):
                return
            self.statuses[name] = (payload if isinstance(payload, dict) else {}, received)
            if name == 'raw' and self._hold_since is not None:
                self._raw_statuses_since_hold += 1

    def _raw_identity_intact(self):
        entry = self.statuses.get('raw')
        if entry is None:
            return False
        raw = entry[0]
        reconnects = raw.get('reconnects')
        if self.development_contract:
            return self._development_raw_contract(raw) and reconnects == self._last_healthy_reconnects
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

    def _development_raw_contract(self, raw):
        return (raw.get('contract') == 'metric_development_v1'
                and raw.get('port') == '/dev/ttyUSB_HWT601'
                and raw.get('sensor_write_commands') is False
                and raw.get('identity_intact') is True
                and raw.get('terminal_fault') is None
                and raw.get('data_valid') is True
                and type(raw.get('data_fresh')) is bool
                and type(raw.get('ready')) is bool
                and raw.get('ready') is raw.get('raw_data_ready')
                and type(raw.get('transport_ok')) is bool
                and type(raw.get('transport_degraded')) is bool
                and raw['transport_ok'] is not raw['transport_degraded']
                and type(raw.get('consecutive_errors')) is int
                and raw['consecutive_errors'] >= 0
                and type(raw.get('reconnects')) is int
                and raw['reconnects'] >= 0
                and raw.get('response_timeout_s') == .05
                and raw.get('sensor_timeout_s') == .30
                and age_valid(raw.get('age_s'), float('inf')))

    def hwt_attempts_in_window(self, now):
        if not self.development_contract:
            return self.recovery_attempts
        while self.hwt_hold_times and now - self.hwt_hold_times[0] > self.hwt_recovery_interval_s:
            self.hwt_hold_times.popleft()
        return len(self.hwt_hold_times)

    def contract_diagnostics(self, now):
        with self.lock:
            raw = self.statuses.get('raw', ({}, None))[0]
            sample = self.samples.get('raw')
            valid = sample is not None and sample[3]
            current = valid and fresh(now, sample[2], self.raw_max_age_s)
            return dict(contract='metric_development_v1' if self.development_contract else 'legacy',
                transport_ok=raw.get('transport_ok'),
                transport_degraded=raw.get('transport_degraded'),
                data_valid=bool(valid), data_fresh=bool(current),
                raw_max_age_s=self.raw_max_age_s,
                hold_required=self.recovery_state != 'HEALTHY' or not current,
                recovery_pending=self.recovery_state in ('HOLD', 'RECOVERY_VALIDATION'),
                terminal_fault=self.latched_fault,
                hwt_recovery_interval_s=self.hwt_recovery_interval_s,
                hwt_attempts_in_window=self.hwt_attempts_in_window(now),
                hwt_lifetime_attempts=self.recovery_attempts)

    def _wheel_timing_pending(self):
        """Verified bounded diagnosis; stale wheel still blocks motion.

        A pending diagnosis is permission to HOLD, never permission to use
        stale odometry. The fixed reader deadline (2 s) and Health's absolute
        5 s cancel/validation budget cannot extend the 180 ms integration gap.
        """
        entry = self.statuses.get('wheel')
        if entry is None:
            return False
        outer = entry[0]
        w = outer.get('encoder_timing_recovery', {}) if self.active_drive else outer
        owner = (outer.get('dry_run') is False and outer.get('allow_rs485') is True
                 and outer.get('rs485_ready') is True
                 and outer.get('odometry_source') == 'encoder_position'
                 and outer.get('encoder_config_fault_latched') is False
                 and w.get('read_only') is False and w.get('actuator_output') is True
                 if self.active_drive else
                 w.get('read_only') is True and w.get('actuator_output') is False)
        return (owner and w.get('ready') is False and w.get('timing_recovery_pending') is True
                and w.get('state') == 'timing_recovery'
                and w.get('source') == 'ess23_absolute_fc03'
                and w.get('synthetic') is False and w.get('command_derived') is False
                and w.get('fault_latched') is False
                and w.get('connected') is True and w.get('configuration_valid') is True
                and w.get('port') == '/dev/ttyUSB_BASE'
                and type(w.get('odometry_continuity_valid')) is bool
                and w.get('timing_recovery_budget_s') == 2.0
                and w.get('timing_recovery_attempt_limit') == 2
                and type(w.get('timing_recovery_count')) is int
                and 1 <= w['timing_recovery_count'] <= 2
                and type(w.get('timing_recovery_deadline_s')) in (int, float)
                and math.isfinite(w['timing_recovery_deadline_s'])
                and type(w.get('continuity_max_gap_s')) in (int, float)
                and 0 < w['continuity_max_gap_s'] <= .18
                and type(w.get('timing_recovery_valid_pairs')) is int
                and 0 <= w['timing_recovery_valid_pairs'] < 2)

    def _wheel_read_in_flight(self):
        entry = self.statuses.get('wheel')
        if entry is None:
            return False
        outer = entry[0]
        w = outer.get('encoder_timing_recovery', {}) if self.active_drive else outer
        owner = (outer.get('dry_run') is False and outer.get('allow_rs485') is True
                 and outer.get('rs485_ready') is True
                 and outer.get('odometry_source') == 'encoder_position'
                 and outer.get('encoder_config_fault_latched') is False
                 and w.get('read_only') is False and w.get('actuator_output') is True
                 if self.active_drive else
                 w.get('read_only') is True and w.get('actuator_output') is False)
        return (owner and w.get('source') == 'ess23_absolute_fc03'
                and w.get('synthetic') is False and w.get('command_derived') is False
                and w.get('port') == '/dev/ttyUSB_BASE'
                and w.get('timing_recovery_budget_s') == 2.0
                and w.get('timing_recovery_attempt_limit') == 2
                and w.get('odometry_continuity_valid') is True
                and w.get('connected') is True and w.get('configuration_valid') is True
                and w.get('fault_latched') is False and w.get('baseline_count') == 1
                and type(w.get('complete_pair_count')) is int
                and w['complete_pair_count'] >= 20)

    def _hard_status_failure(self, now=None):
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
            or (yaw.get('ready') is False and (pending is True or
                (self.development_contract and type(yaw.get('age_s')) in (int, float)
                 and yaw['age_s'] > .35))))
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
        contract = wheel.get('encoder_timing_recovery', {}) if self.active_drive else wheel
        if now is not None and (self._wheel_timing_pending() or self._wheel_read_in_flight()):
            if not fresh(now, wheel_entry[1], 1.0):
                return 'wheel_status_missing_or_stale'
            if self._wheel_timing_pending() and now >= contract['timing_recovery_deadline_s']:
                return 'wheel_recovery_deadline_expired'
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
        return None if valid or self._wheel_timing_pending() or self._wheel_read_in_flight() else 'wheel_identity_or_configuration_fault'

    def _recoverable(self, reason, now):
        if self._hard_status_failure(now) is not None:
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
                    or raw['age_s'] > self.raw_max_age_s)
        if reason in ('wheel_timing_recovery_pending', 'wheel_missing_stale_or_invalid',
                      'wheel_not_real_or_not_ready'):
            entry = self.statuses.get('wheel')
            sample = self.samples.get('wheel')
            w = (entry[0].get('encoder_timing_recovery', {}) if self.active_drive
                 else entry[0]) if entry is not None else {}
            in_flight = self._wheel_read_in_flight()
            return ((self._wheel_timing_pending() or in_flight) and entry is not None
                    and fresh(now, entry[1], 1.0)
                    and sample is not None and sample[3]
                    and now >= sample[1] >= sample[2])
        if reason == 'yaw_data_continuity_pending':
            yaw = self.statuses['yaw'][0]
            return (yaw.get('ready') is False
                    and yaw.get('data_continuity_pending') is True)
        return False

    def _sample_rejection(self, name, now, limit):
        sample = self.samples.get(name)
        if sample is None:
            return 'missing_message'
        if not sample[3]:
            return 'invalid_content_or_measurement_order'
        if not fresh(now, sample[1], limit):
            return 'callback_receive_age_out_of_bounds'
        if not fresh(now, sample[2], limit):
            return 'measurement_age_out_of_bounds'
        return None

    def _event(self, now, state, reason):
        # Called while holding the decision lock: sample, status and recovery
        # belong to this exact transition. No logger or I/O on this path.
        self._event_sequence += 1
        event = {'event_id': self._event_sequence,
                 'component': 'Hwt601FusionHealth', 'observer': self.observer,
                 'state_before': self._last_event_state, 'state_after': state,
                 'state': state, 'reason': reason, 'monotonic_s': now}
        if state in ('STARTUP', 'HOLD', 'TERMINAL_FAULT'):
            try:
                snapshot = self._capture_first_fault(now, reason)
                snapshot.update(event)
                snapshot['previous_successful_recovery'] = copy.deepcopy(
                    self.last_successful_recovery)
                event['decision_snapshot'] = snapshot
                self.last_fault = snapshot
            except Exception as exc:
                event['decision_snapshot'] = dict(event, capture_error=type(exc).__name__)
                self.last_fault = event['decision_snapshot']
        if state == 'HEALTHY' and reason == 'recovered':
            self.last_successful_recovery = dict(event)
        if (self._first_fault is not None and 'event_id' not in self._first_fault
                and self._first_fault.get('evaluation_monotonic_s') == now):
            self._first_fault.update({key: value for key, value in event.items()
                                      if key != 'decision_snapshot'})
        self._last_event_state = state
        self.recovery_events.append(event)
        # Bounded lifetime journal; first_fault is kept separately forever.
        del self.recovery_events[:-16]

    def fault_snapshot(self):
        with self.lock:
            return copy.deepcopy(self.last_fault)

    def _terminal(self, now, reason):
        self.recovery_state = 'TERMINAL_FAULT'
        self.latched_fault = reason
        self._event(now, self.recovery_state, reason)
        return reason

    def _wheel_limit(self):
        wheel = self.statuses.get('wheel', ({}, None))[0]
        return .18 if not self.active_drive or 'encoder_timing_recovery' in wheel else .30

    def _failure(self, now):
        wheel_limit = self._wheel_limit()
        for name, limit in (('raw', self.raw_max_age_s), ('yaw', 0.35), ('wheel', wheel_limit)):
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
        if self.development_contract:
            if not (self._development_raw_contract(raw)
                    and raw['ready'] is True and raw['data_fresh'] is True
                    and age_valid(raw.get('age_s'), self.raw_max_age_s)):
                return 'raw_driver_not_ready'
        elif not (raw.get('ready') is True and raw.get('raw_data_ready') is True
                and raw.get('port') == '/dev/ttyUSB_HWT601'
                and raw.get('sensor_write_commands') is False
                and raw.get('consecutive_errors') == 0
                and age_valid(raw.get('age_s'), self.raw_max_age_s)):
            return 'raw_driver_not_ready'
        yaw = self.statuses['yaw'][0]
        bias = yaw.get('bias')
        if (self.development_contract and yaw.get('ready') is False
                and age_valid(yaw.get('age_s'), float('inf')) and yaw['age_s'] > .35):
            return 'yaw_missing_stale_or_invalid'
        if (yaw.get('ready') is False
                and yaw.get('data_continuity_pending') is True
                and yaw.get('latched_fault') is None
                and isinstance(bias, dict)
                and bias.get('calibrated') is True
                and bias.get('stable') is True
                and bias.get('adaptation_samples') == 0
                and not self.development_contract):
            return 'yaw_data_continuity_pending'
        # A boundary sample is intentionally not published by the yaw core.
        # In the explicit development contract the preceding ORIGINAL yaw
        # sample is still usable within .35 s, while raw is valid within .30.
        # Both actual sample ages were checked above; no gap is integrated,
        # timestamp changed, or frozen calibration weakened here.
        usable_yaw=(yaw.get('ready') is True or (
            self.development_contract and yaw.get('ready') is False
            and yaw.get('data_continuity_pending') is True))
        if not (usable_yaw
                and yaw.get('operator_stationary_confirmed') is True
                and yaw.get('bias_frozen_after_startup') is True
                and 'latched_fault' in yaw and yaw['latched_fault'] is None
                and isinstance(bias, dict)
                and bias.get('calibrated') is True and bias.get('stable') is True
                and bias.get('adaptation_samples') == 0
                and age_valid(yaw.get('age_s'), 0.35)):
            return 'yaw_uncalibrated_or_faulted'
        wheel = self.statuses['wheel'][0]
        if self._wheel_timing_pending():
            return 'wheel_timing_recovery_pending'
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
        """Capture current decision inputs; assignment preserves first and later faults."""
        raw_status = self.statuses.get('raw')
        raw = raw_status[0] if raw_status is not None else {}
        conditions = []
        expected_types = {
            'ready': (bool,), 'raw_data_ready': (bool,),
            'port': (str,), 'sensor_write_commands': (bool,),
            'consecutive_errors': (int,), 'age_s': (int, float),
        }
        expectations = list(_RAW_EXPECTATIONS)
        if self.development_contract:
            expectations[4] = ('consecutive_errors', 'diagnostic only; nonnegative integer', lambda v: type(v) is int and v >= 0)
            expectations[5] = ('age_s', 'finite number in [0.0, 0.30] s', lambda v: age_valid(v, self.raw_max_age_s))
        for name, expected, check in expectations:
            value = raw.get(name)
            conditions.append(_typed_field(
                raw, name, expected, name in raw and check(value),
                expected_types[name]))
        violations = [entry['field'] for entry in conditions
                      if not entry['passed']]
        source_checks = []
        for name, limit in (('raw', self.raw_max_age_s), ('yaw', 0.35),
                            ('wheel', self._wheel_limit())):
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
                'sample_validation': copy.deepcopy(self.sample_validation.get(name)),
                'sample_fresh_and_valid': bool(sample_ok),
                'sample_limit_s': limit,
                'first_rejecting_predicate': self._sample_rejection(name, now, limit),
                'ignored_older_callbacks': self.ignored_older_callbacks.get(name, 0),
                'original_message_and_clock_pair': copy.deepcopy(self.sample_details.get(name)),
                'callback_receive_age_s':
                    _elapsed(now, sample[1]) if sample is not None else None,
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
            'wheel_status': _json_value(self.statuses.get('wheel', ({}, None))[0]),
            'clock_basis': 'monotonic evaluation; ROS measurement stamp converted at callback',
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
            self.last_source_failure = self._source_failure(now)
            return self.last_source_failure

    def _source_failure(self, now=None):
        with self.lock:
            # Snapshot time after acquiring the same lock as callbacks.
            # A concurrently received sample must not appear future-dated.
            if now is None:
                now = time.monotonic()
            if self.latched_fault is not None:
                return self.latched_fault
            if self.development_contract:
                raw = self.statuses.get('raw', ({}, None))[0]
                if raw.get('terminal_fault') is not None:
                    return self._terminal(now, 'raw_terminal_fault')
            reason = self._failure(now)
            if reason is None and not self.was_ready:
                self.was_ready = True
                self.recovery_state = 'HEALTHY'
                self._last_event_state = 'HEALTHY'
                reconnects = self.statuses['raw'][0].get('reconnects')
                self._last_healthy_reconnects = (
                    reconnects if type(reconnects) is int else None)
                return None
            if not self.was_ready:
                if reason != self._startup_reason:
                    self._startup_reason = reason
                    self._event(now, 'STARTUP', reason)
                return reason
            hard = self._hard_status_failure(now)
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
                wheel_hold = reason.startswith('wheel_')
                count = self.wheel_recovery_attempts if wheel_hold else self.hwt_attempts_in_window(now)
                if count >= self.recovery_attempt_limit:
                    return self._terminal(now, 'wheel_recovery_attempt_limit' if wheel_hold
                                          else 'hwt_recovery_attempt_limit')
                if wheel_hold:
                    self.wheel_recovery_attempts += 1
                else:
                    self.recovery_attempts += 1
                    if self.development_contract:
                        self.hwt_hold_times.append(now)
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
