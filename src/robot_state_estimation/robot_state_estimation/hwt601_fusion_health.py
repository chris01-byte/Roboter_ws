"""Raw-input contract for the existing HWT mapping profile, not an EKF health proxy."""

import math
import threading
import time


def fresh(now, then, limit):
    return (isinstance(then, (int, float)) and math.isfinite(then)
            and math.isfinite(now) and 0.0 <= now - then <= limit)


def age_valid(value, limit):
    return (type(value) in (int, float) and math.isfinite(value)
            and 0.0 <= value <= limit)


class Hwt601FusionHealth:
    """Check real inputs; once ready, source loss requires a stopped restart.

    Limits are from hwt601_shadow.yaml (raw .20, corrected .35),
    base_hardware_params.yaml (.30), the read-only encoder shadow profile
    (.18), and the historical 1 s status heartbeat contract. EKF output is
    NOT an input.
    """

    def __init__(self, active_drive):
        self.active_drive = active_drive is True
        self.samples = {}
        self.statuses = {}
        self.was_ready = False
        self.latched_fault = None
        self.lock = threading.RLock()

    def sample(self, name, stamp, received, observed, valid=True):
        with self.lock:
            previous = self.samples.get(name)
            valid = (valid and math.isfinite(stamp) and stamp > 0
                     and (previous is None or stamp > previous[0]))
            self.samples[name] = (stamp, received, observed, valid)

    def status(self, name, payload, received):
        with self.lock:
            self.statuses[name] = (payload if isinstance(payload, dict) else {}, received)

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

    def source_failure(self, now=None):
        with self.lock:
            # Snapshot time after acquiring the same lock as callbacks.
            # A concurrently received sample must not appear future-dated.
            if now is None:
                now = time.monotonic()
            if self.latched_fault is not None:
                return self.latched_fault
            reason = self._failure(now)
            if reason is None:
                self.was_ready = True
            elif self.was_ready:
                self.latched_fault = reason
            return reason

    def motion_failure(self, now=None):
        return self.source_failure(now) or (
            None if self.active_drive else 'readonly_preflight_no_motion')
