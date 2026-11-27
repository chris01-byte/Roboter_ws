import math
from pathlib import Path
import sys


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE_ROOT))

from robot_state_estimation.quality_core import (  # noqa: E402
    GyroBiasConfig,
    GyroBiasEstimator,
    ImuStabilityConfig,
    ImuStabilityMonitor,
    MotionConsistencyConfig,
    MotionConsistencyMonitor,
    rotate_vector_by_quaternion,
)


def test_quaternion_rotation_transforms_sensor_vector_to_base():
    half = math.sin(math.pi / 4.0)
    rotated = rotate_vector_by_quaternion(
        (1.0, 0.0, 0.0), (0.0, 0.0, half, half))

    assert math.isclose(rotated[0], 0.0, abs_tol=1e-9)
    assert math.isclose(rotated[1], 1.0, abs_tol=1e-9)
    assert math.isclose(rotated[2], 0.0, abs_tol=1e-9)


def test_gyro_bias_is_measured_only_during_confirmed_standstill():
    estimator = GyroBiasEstimator(GyroBiasConfig(
        calibration_duration_s=0.2,
        minimum_samples=3,
        maximum_stddev_radps=0.01,
    ))
    bias = (0.004, -0.006, 0.003)

    estimator.update(1.0, bias, True)
    moving = estimator.update(1.1, bias, False)
    assert not moving.calibrated
    assert moving.samples == 0

    estimator.update(2.0, bias, True)
    estimator.update(2.1, bias, True)
    calibrated = estimator.update(2.25, bias, True)

    assert calibrated.calibrated
    assert calibrated.stable
    assert calibrated.bias_radps == bias
    assert all(abs(value) <= 1e-12 for value in estimator.correct(bias))


def test_gyro_bias_waits_for_initial_settle_before_collecting():
    estimator = GyroBiasEstimator(GyroBiasConfig(
        initial_settle_s=0.3,
        calibration_duration_s=0.2,
        minimum_samples=3,
        maximum_sample_gap_s=0.2,
    ))
    bias = (0.004, -0.006, 0.003)

    first = estimator.update(1.0, bias, True)
    settling = estimator.update(1.2, bias, True)
    collecting = estimator.update(1.31, bias, True)
    estimator.update(1.41, bias, True)
    calibrated = estimator.update(1.52, bias, True)

    assert first.reason == 'gyro_bias_einlaufzeit'
    assert settling.samples == 0
    assert collecting.samples == 1
    assert calibrated.calibrated
    assert calibrated.samples == 3


def test_gyro_bias_tracks_drift_only_at_confirmed_standstill_and_recovers():
    estimator = GyroBiasEstimator(GyroBiasConfig(
        calibration_duration_s=0.02,
        minimum_samples=3,
        maximum_sample_gap_s=0.05,
        stationary_adaptation_time_constant_s=0.05,
        stationary_residual_time_constant_s=0.02,
        maximum_stationary_residual_radps=0.003,
        stationary_recovery_s=0.03,
    ))
    initial_bias = (0.004, -0.006, 0.003)
    shifted_bias = (0.014, -0.006, 0.003)

    estimator.update(1.00, initial_bias, True)
    estimator.update(1.01, initial_bias, True)
    calibrated = estimator.update(1.02, initial_bias, True)
    unstable = estimator.update(1.03, shifted_bias, True)

    assert calibrated.stable
    assert not unstable.stable
    assert unstable.reason == 'gyro_bias_restoffset_zu_gross'

    recovered = unstable
    for index in range(1, 51):
        recovered = estimator.update(
            1.03 + index * 0.01, shifted_bias, True)

    assert recovered.stable
    assert recovered.adaptation_samples == 51
    assert abs(estimator.correct(shifted_bias)[0]) < 0.001

    adapted_bias = recovered.bias_radps
    moving = estimator.update(1.54, (0.10, -0.006, 0.003), False)

    assert moving.stable
    assert moving.reason == 'gyro_bias_fixiert_bewegung'
    assert moving.bias_radps == adapted_bias


def _monitor():
    return ImuStabilityMonitor(ImuStabilityConfig(
        warmup_s=0.2,
        settle_s=0.3,
        baseline_time_constant_s=2.0,
        maximum_gravity_direction_change_rad=math.radians(3.0),
        maximum_roll_pitch_rate_radps=math.radians(15.0),
    ))


def test_imu_gate_allows_planar_yaw_after_warmup():
    monitor = _monitor()
    first = monitor.update(1.0, (0.0, 0.0, 0.4), (0.0, 0.0, 9.80665))
    ready = monitor.update(1.25, (0.0, 0.0, 0.4), (0.0, 0.0, 9.80665))

    assert not first.ready
    assert ready.ready
    assert ready.stable
    assert ready.reason == 'stabil'


def test_imu_gate_rejects_roll_event_and_waits_for_settling():
    monitor = _monitor()
    monitor.update(1.0, (0.0, 0.0, 0.0), (0.0, 0.0, 9.80665))
    monitor.update(1.25, (0.0, 0.0, 0.0), (0.0, 0.0, 9.80665))

    impact = monitor.update(1.30, (0.5, 0.0, 0.0), (0.0, 0.0, 9.80665))
    settling = monitor.update(1.40, (0.0, 0.0, 0.0), (0.0, 0.0, 9.80665))
    recovered = monitor.update(1.65, (0.0, 0.0, 0.0), (0.0, 0.0, 9.80665))

    assert not impact.stable
    assert impact.reason == 'roll_nick_rate'
    assert not settling.stable
    assert settling.reason == 'beruhigungszeit'
    assert recovered.stable


def test_imu_gate_rejects_gravity_direction_jump():
    monitor = _monitor()
    monitor.update(1.0, (0.0, 0.0, 0.0), (0.0, 0.0, 9.80665))
    monitor.update(1.25, (0.0, 0.0, 0.0), (0.0, 0.0, 9.80665))

    tilted = monitor.update(
        1.30, (0.0, 0.0, 0.0), (1.0, 0.0, 9.75))

    assert not tilted.stable
    assert tilted.reason == 'kippwinkel'


def test_motion_disagreement_latches_and_recovers_with_hysteresis():
    monitor = MotionConsistencyMonitor(MotionConsistencyConfig(
        bad_samples_to_latch=2,
        good_samples_to_recover=3,
        suspect_covariance_scale=10.0,
        slip_covariance_scale=100.0,
    ))

    first = monitor.update(0.20, 0.0, 0.0, 0.0, 0.01)
    second = monitor.update(0.20, 0.0, 0.0, 0.0, 0.01)

    assert first.state == 'suspect'
    assert first.covariance_scale == 10.0
    assert second.state == 'slip'
    assert second.covariance_scale == 100.0

    for _ in range(2):
        still_latched = monitor.update(0.10, 0.0, 0.10, 0.0, 0.01)
        assert still_latched.state == 'slip'
    recovered = monitor.update(0.10, 0.0, 0.10, 0.0, 0.01)
    assert recovered.state == 'nominal'
    assert recovered.covariance_scale == 1.0


def test_motion_monitor_does_not_compare_unsynchronised_sources():
    monitor = MotionConsistencyMonitor()

    result = monitor.update(0.2, 0.0, 0.0, 0.0, 1.0)

    assert not result.evaluated
    assert result.state == 'unverified'
    assert result.covariance_scale == 1.0
