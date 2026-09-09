"""ROS-independent startup calibration for the HWT601 yaw shadow path."""

from dataclasses import dataclass
import math
from typing import Optional

from .quality_core import (
    GyroBiasConfig,
    GyroBiasEstimator,
    GyroBiasResult,
    Vector3,
    rotate_vector_by_quaternion,
)


# Measured mounting axes: X_sensor points right, Y_sensor forward, Z_sensor up.
# Thus Rz(-90 deg) maps them to REP-103 X_base forward, Y_base left, Z_base up.
_SENSOR_TO_BASE_QUATERNION = (
    0.0,
    0.0,
    -math.sqrt(0.5),
    math.sqrt(0.5),
)


def valid_hwt601_shadow_input(
        frame_id: str, stamp_s: float, values,
        expected_frame: str = 'hwt601_link') -> bool:
    """Validate the complete upstream IMU message as a pure predicate."""
    return (
        frame_id == expected_frame
        and math.isfinite(stamp_s)
        and stamp_s > 0.0
        and all(math.isfinite(value) for value in values))


@dataclass(frozen=True)
class Hwt601YawShadowResult:
    """One fail-closed decision from the shadow calibration path."""

    publish: bool
    reason: str
    yaw_rate_radps: float
    bias: GyroBiasResult


class Hwt601YawShadowCore:
    """Calibrate once at declared standstill, then freeze and expose yaw rate.

    The operator declaration is used only for the startup calibration window.
    Once calibrated, samples are explicitly marked as non-stationary for the
    bias estimator, so later robot motion can never be learned as bias.
    """

    def __init__(
            self, bias_config: GyroBiasConfig,
            operator_stationary_confirmed: bool):
        self.bias_estimator = GyroBiasEstimator(bias_config)
        self.operator_stationary_confirmed = bool(
            operator_stationary_confirmed)
        self.maximum_sample_gap_s = bias_config.maximum_sample_gap_s
        self._last_stamp_s: Optional[float] = None
        self._fault_reason: Optional[str] = None

    @property
    def bias(self) -> GyroBiasResult:
        return self.bias_estimator.result

    @property
    def fault_reason(self) -> Optional[str]:
        """A post-calibration data-contract fault requires a fresh startup."""
        return self._fault_reason

    def reject_invalid_message(self) -> str:
        """Latch a complete-message contract violation after calibration."""
        if (
                self._fault_reason is None
                and self.bias_estimator.result.calibrated):
            self._fault_reason = 'imu_probe_ungueltig_neustart_noetig'
        return self._fault_reason or 'imu_probe_ungueltig'

    def update(
            self, stamp_s: float,
            angular_velocity_radps: Vector3) -> Hwt601YawShadowResult:
        if self._fault_reason is not None:
            return Hwt601YawShadowResult(
                False, self._fault_reason, 0.0, self.bias_estimator.result)
        was_calibrated = self.bias_estimator.result.calibrated
        gap_s = (
            None if self._last_stamp_s is None
            else stamp_s - self._last_stamp_s)
        finite = (
            math.isfinite(stamp_s)
            and stamp_s > 0.0
            and len(angular_velocity_radps) == 3
            and all(math.isfinite(value) for value in angular_velocity_radps))
        monotonic = (
            self._last_stamp_s is None
            or (math.isfinite(stamp_s) and stamp_s > self._last_stamp_s))

        # Let the shared estimator apply its fail-closed reset/latch behaviour
        # for malformed time or values as well.
        stationary = (
            self.operator_stationary_confirmed
            and not self.bias_estimator.result.calibrated)
        bias = self.bias_estimator.update(
            stamp_s, angular_velocity_radps, stationary)

        if finite and monotonic:
            self._last_stamp_s = stamp_s
        if not finite:
            return Hwt601YawShadowResult(
                False,
                self.reject_invalid_message(),
                0.0,
                bias,
            )
        if not monotonic:
            if was_calibrated:
                self._fault_reason = 'imu_zeitfehler_neustart_noetig'
            return Hwt601YawShadowResult(
                False,
                self._fault_reason or 'imu_zeit_nicht_monoton',
                0.0,
                bias,
            )
        if gap_s is not None and gap_s > self.maximum_sample_gap_s:
            if was_calibrated:
                self._fault_reason = 'imu_datenluecke_neustart_noetig'
            return Hwt601YawShadowResult(
                False,
                self._fault_reason or 'imu_datenluecke',
                0.0,
                bias,
            )
        if not self.operator_stationary_confirmed and not bias.calibrated:
            return Hwt601YawShadowResult(
                False, 'operator_stillstand_nicht_bestaetigt', 0.0, bias)
        if not bias.calibrated or not bias.stable:
            return Hwt601YawShadowResult(
                False, bias.reason, 0.0, bias)

        corrected_sensor = self.bias_estimator.correct(
            angular_velocity_radps)
        corrected_base = rotate_vector_by_quaternion(
            corrected_sensor, _SENSOR_TO_BASE_QUATERNION)
        return Hwt601YawShadowResult(
            True, 'shadow_yaw_bereit', corrected_base[2], bias)


def hwt601_sensor_to_base(vector: Vector3) -> Vector3:
    """Expose the measured mounting rotation for focused regression tests."""
    return rotate_vector_by_quaternion(
        vector, _SENSOR_TO_BASE_QUATERNION)
