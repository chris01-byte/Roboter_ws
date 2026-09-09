import math
from pathlib import Path
import sys

import yaml


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE_ROOT))

from robot_state_estimation.hwt601_shadow_core import (  # noqa: E402
    Hwt601YawShadowCore,
    hwt601_sensor_to_base,
    valid_hwt601_shadow_input,
)
from robot_state_estimation.hwt601_protocol import (  # noqa: E402
    decode_motion_registers,
)
from robot_state_estimation.quality_core import GyroBiasConfig  # noqa: E402


def _config():
    return GyroBiasConfig(
        calibration_duration_s=0.02,
        minimum_samples=3,
        maximum_stddev_radps=0.005,
        maximum_sample_magnitude_radps=0.03,
        maximum_sample_gap_s=0.05,
        stationary_adaptation_time_constant_s=0.0,
    )


def _calibrated_core(bias=(0.001, -0.002, 0.0001)):
    core = Hwt601YawShadowCore(_config(), True)
    assert not core.update(1.00, bias).publish
    assert not core.update(1.01, bias).publish
    result = core.update(1.02, bias)
    assert result.publish
    assert result.bias.calibrated
    return core, bias, 1.02


def test_measured_mount_rotation_is_right_handed_and_z_up():
    assert all(math.isclose(a, b, abs_tol=1e-12) for a, b in zip(
        hwt601_sensor_to_base((1.0, 0.0, 0.0)),
        (0.0, -1.0, 0.0)))
    assert all(math.isclose(a, b, abs_tol=1e-12) for a, b in zip(
        hwt601_sensor_to_base((0.0, 1.0, 0.0)),
        (1.0, 0.0, 0.0)))
    assert hwt601_sensor_to_base((0.0, 0.0, 1.0)) == (0.0, 0.0, 1.0)


def test_startup_requires_explicit_stationary_confirmation():
    core = Hwt601YawShadowCore(_config(), False)

    for index in range(20):
        result = core.update(1.0 + 0.01 * index, (0.001, -0.002, 0.0001))

    assert not result.publish
    assert not result.bias.calibrated
    assert result.reason == 'operator_stillstand_nicht_bestaetigt'


def test_bias_is_frozen_and_only_corrected_z_reaches_shadow_output():
    core, bias, stamp = _calibrated_core()
    initial_bias = core.bias.bias_radps

    # Large X/Y motion cannot leak into the planar yaw measurement.
    for index in range(1, 101):
        result = core.update(
            stamp + 0.01 * index,
            (bias[0] + 1.2, bias[1] - 0.7, bias[2] + 0.4),
        )
        assert result.publish
        assert math.isclose(result.yaw_rate_radps, 0.4, abs_tol=1e-12)

    assert core.bias.bias_radps == initial_bias
    assert core.bias.adaptation_samples == 0


def _integrate_angle(target_deg):
    core, bias, stamp = _calibrated_core()
    rate_degps = math.copysign(25.0, target_deg)
    rate_radps = math.radians(rate_degps)
    samples = round(abs(target_deg) / 25.0 / 0.01)
    angle = 0.0
    for index in range(1, samples + 1):
        result = core.update(
            stamp + 0.01 * index,
            (bias[0] + 0.3, bias[1] - 0.2, bias[2] + rate_radps),
        )
        assert result.publish
        angle += result.yaw_rate_radps * 0.01
    return math.degrees(angle)


def test_shadow_scale_has_no_factor_two_for_45_and_180_degrees():
    for target in (45.0, -45.0, 180.0):
        assert math.isclose(
            _integrate_angle(target), target, rel_tol=0.0, abs_tol=1e-9)


def test_raw_hwt_register_scale_reaches_shadow_without_factor_two():
    shadow_config = yaml.safe_load(
        (PACKAGE_ROOT / 'config' / 'hwt601_shadow.yaml').read_text())
    full_scale_dps = shadow_config[
        'hwt601_shadow_reader']['ros__parameters'][
            'angular_velocity_full_scale_dps']
    assert full_scale_dps == 400.0

    for target_deg in (45.0, -45.0, 180.0):
        core, _, stamp = _calibrated_core((0.0, 0.0, 0.0))
        raw_z = int(math.copysign(2048, target_deg))
        registers = (0, 0, 0, 500, 65000, raw_z & 0xFFFF)
        decoded = decode_motion_registers(
            registers, angular_velocity_full_scale_dps=full_scale_dps)
        assert math.isclose(
            math.degrees(decoded.angular_velocity_radps[2]),
            math.copysign(25.0, target_deg),
            abs_tol=1e-12,
        )

        samples = round(abs(target_deg) / 25.0 / 0.01)
        integrated_rad = 0.0
        for index in range(1, samples + 1):
            result = core.update(
                stamp + 0.01 * index,
                decoded.angular_velocity_radps,
            )
            assert result.publish
            integrated_rad += result.yaw_rate_radps * 0.01
        assert math.isclose(
            math.degrees(integrated_rad), target_deg, abs_tol=1e-9)


def test_post_calibration_gap_latches_until_fresh_startup():
    core, bias, stamp = _calibrated_core()

    gap = core.update(stamp + 0.20, bias)
    still_blocked = core.update(stamp + 0.21, bias)

    assert not gap.publish
    assert gap.reason == 'imu_datenluecke_neustart_noetig'
    assert not still_blocked.publish
    assert still_blocked.reason == gap.reason
    assert core.fault_reason == gap.reason


def test_post_calibration_non_monotonic_stamp_latches():
    core, bias, stamp = _calibrated_core()

    backwards = core.update(stamp - 0.01, bias)

    assert not backwards.publish
    assert backwards.reason == 'imu_zeitfehler_neustart_noetig'
    assert core.fault_reason == backwards.reason


def test_post_calibration_invalid_message_latches_until_process_restart():
    core, bias, stamp = _calibrated_core()

    reason = core.reject_invalid_message()
    resumed = core.update(stamp + 0.01, bias)

    assert reason == 'imu_probe_ungueltig_neustart_noetig'
    assert core.fault_reason == reason
    assert not resumed.publish
    assert resumed.reason == reason


def test_input_contract_rejects_wrong_frame_time_and_nonfinite_fields():
    values = [0.0] * 40

    assert valid_hwt601_shadow_input('hwt601_link', 1.0, values)
    assert not valid_hwt601_shadow_input('base_link', 1.0, values)
    assert not valid_hwt601_shadow_input('hwt601_link', 0.0, values)
    values[17] = float('nan')
    assert not valid_hwt601_shadow_input('hwt601_link', 1.0, values)
