#!/usr/bin/env python3
"""Record a passive, directly comparable HWT601/encoder shadow run.

This observer only subscribes.  It never opens a serial device, creates a ROS
publisher, broadcasts TF or starts another process.  The recorded evidence is
kept below an explicitly supplied local output directory.
"""

from __future__ import annotations

import argparse
from bisect import bisect_left
import csv
from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
import time
from typing import Iterable, Mapping, Sequence


IMU_TOPIC = '/shadow/hwt601/imu/yaw_rate'
WHEEL_TOPIC = '/shadow/hwt601/wheel_odom_raw'
HWT_STATUS_TOPIC = '/shadow/hwt601/status_json'
HWT_RAW_STATUS_TOPIC = '/shadow/hwt601/raw_status_json'
ENCODER_STATUS_TOPIC = '/shadow/hwt601/wheel_status_json'
HWT_RAW_IMU_TOPIC = '/shadow/hwt601/imu/data_raw'

EXPECTED_GRAPH_NODES = frozenset({
    '/hwt601_encoder_shadow_stillstand_observer',
    '/hwt601_encoder_shadow_reader',
    '/hwt601_shadow',
    '/hwt601_shadow_reader',
})
EXPECTED_TOPIC_PUBLISHERS = {
    HWT_RAW_IMU_TOPIC: frozenset({'/hwt601_shadow_reader'}),
    IMU_TOPIC: frozenset({'/hwt601_shadow'}),
    WHEEL_TOPIC: frozenset({'/hwt601_encoder_shadow_reader'}),
    HWT_STATUS_TOPIC: frozenset({'/hwt601_shadow'}),
    HWT_RAW_STATUS_TOPIC: frozenset({'/hwt601_shadow_reader'}),
    ENCODER_STATUS_TOPIC: frozenset({'/hwt601_encoder_shadow_reader'}),
}
FORBIDDEN_PUBLISHER_TOPICS = (
    '/odom', '/map', '/tf', '/tf_static', '/fusion/imu',
    '/fusion/wheel_odom', '/cmd_vel', '/cmd_vel_smoothed',
)

IMU_FRAME = 'base_link'
ODOM_FRAME = 'odom'
BASE_FRAME = 'base_link'
IMU_Z_VARIANCE = 5.0e-7
UNOBSERVED_VARIANCE = 1.0e6

MAX_IMU_GAP_S = 0.10
MAX_ENCODER_GAP_S = 0.10
ENCODER_SOURCE_MAX_SAMPLE_GAP_S = 0.10
MAX_PAIR_DURATION_S = 0.05
MIN_IMU_RATE_HZ = 80.0
MIN_ENCODER_RATE_HZ = 10.0
MAX_STATIONARY_ANGLE_DEG = 1.0
MAX_STATIONARY_TRANSLATION_M = 0.001
MAX_STATIONARY_LINEAR_SPEED_MPS = 0.005
MAX_STATIONARY_ANGULAR_SPEED_RADPS = 0.005

# The configured HWT shadow has 15 s settle plus 10 s bias collection.  The
# observer may receive the first 2-Hz status just after the sources start, so a
# one-second transport allowance remains while still rejecting a late attach.
MIN_BIAS_PHASE_OBSERVED_S = 24.0
MIN_BIAS_BLOCKED_SAMPLES = 2000
MAX_BIAS_LINEAR_SPEED_MPS = 0.005
MAX_BIAS_ANGULAR_SPEED_RADPS = 0.005
MAX_BIAS_TRANSLATION_M = 0.001
MAX_BIAS_YAW_RAD = math.radians(0.1)
STATUS_MAX_AGE_S = 1.0
MAX_STATUS_GAP_S = 1.0
MAX_DURATION_CLOCK_SKEW_S = 0.5
GRAPH_CHECK_INTERVAL_S = 0.5
MAX_GRAPH_CHECK_GAP_S = 1.0
POST_WINDOW_STATUS_TIMEOUT_S = 2.0
POST_WINDOW_STATUS_SOURCES = ('hwt', 'hwt_raw', 'encoder')
SENSOR_BUFFER_DEPTH = 200


class AnalysisError(ValueError):
    """Input cannot support a fail-closed direct comparison."""


@dataclass(frozen=True)
class ImuYawSample:
    stamp_s: float
    yaw_rate_radps: float


@dataclass(frozen=True)
class WheelPoseSample:
    stamp_s: float
    x_m: float
    y_m: float
    yaw_rad: float
    linear_velocity_mps: float = 0.0
    angular_velocity_radps: float = 0.0


@dataclass(frozen=True)
class AngleComparison:
    start_stamp_s: float
    end_stamp_s: float
    duration_s: float
    imu_samples: int
    encoder_samples: int
    imu_rate_hz: float
    encoder_rate_hz: float
    maximum_imu_gap_s: float
    maximum_encoder_gap_s: float
    hwt_angle_rad: float
    encoder_angle_rad: float
    difference_rad: float
    peak_absolute_hwt_angle_rad: float
    peak_absolute_encoder_angle_rad: float
    peak_absolute_difference_rad: float
    peak_translation_from_window_start_m: float
    peak_translation_from_encoder_baseline_m: float
    peak_absolute_linear_velocity_mps: float
    peak_absolute_encoder_angular_velocity_radps: float


def normalize_angle(angle_rad: float) -> float:
    """Return one signed angular increment in [-pi, pi]."""
    return math.atan2(math.sin(angle_rad), math.cos(angle_rad))


def quaternion_to_planar_yaw(
    x: float, y: float, z: float, w: float,
    *, norm_tolerance: float = 1.0e-3,
    planar_tolerance: float = 1.0e-6,
) -> float:
    """Validate a planar unit quaternion and return its yaw."""
    values = (float(x), float(y), float(z), float(w))
    if not all(math.isfinite(value) for value in values):
        raise AnalysisError('encoder_quaternion_nicht_endlich')
    norm = math.sqrt(sum(value * value for value in values))
    if norm <= 0.0 or abs(norm - 1.0) > norm_tolerance:
        raise AnalysisError('encoder_quaternion_nicht_normiert')
    qx, qy, qz, qw = (value / norm for value in values)
    if abs(qx) > planar_tolerance or abs(qy) > planar_tolerance:
        raise AnalysisError('encoder_quaternion_nicht_planar')
    return math.atan2(
        2.0 * (qw * qz + qx * qy),
        1.0 - 2.0 * (qy * qy + qz * qz),
    )


def unwrap_encoder_yaw(samples: Sequence[WheelPoseSample]) -> list[float]:
    """Accumulate adjacent yaw increments without a +/-pi end-point trap."""
    if not samples:
        raise AnalysisError('encoderproben_fehlen')
    result = [0.0]
    previous = samples[0].yaw_rad
    if not math.isfinite(previous):
        raise AnalysisError('encoderwinkel_nicht_endlich')
    for sample in samples[1:]:
        if not math.isfinite(sample.yaw_rad):
            raise AnalysisError('encoderwinkel_nicht_endlich')
        result.append(result[-1] + normalize_angle(sample.yaw_rad - previous))
        previous = sample.yaw_rad
    return result


def _strictly_increasing_stamps(
    samples: Sequence[ImuYawSample] | Sequence[WheelPoseSample],
    label: str,
) -> tuple[float, float]:
    if len(samples) < 2:
        raise AnalysisError(f'{label}_zu_wenige_proben')
    maximum_gap = 0.0
    previous = None
    for sample in samples:
        stamp = float(sample.stamp_s)
        if not math.isfinite(stamp) or stamp <= 0.0:
            raise AnalysisError(f'{label}_zeitstempel_ungueltig')
        if previous is not None:
            gap = stamp - previous
            if gap <= 0.0:
                raise AnalysisError(f'{label}_zeitstempel_nicht_monoton')
            maximum_gap = max(maximum_gap, gap)
        previous = stamp
    duration = samples[-1].stamp_s - samples[0].stamp_s
    return duration, maximum_gap


def _bracketed_value(samples: Sequence[ImuYawSample], stamp_s: float) -> float:
    """Linearly interpolate only between two real surrounding IMU samples."""
    stamps = [sample.stamp_s for sample in samples]
    left, right = _bracketing_indices(stamps, stamp_s)
    if left == right:
        # An exact first or last sample is itself real boundary evidence and
        # needs neither interpolation nor extrapolation.
        return samples[left].yaw_rate_radps
    before = samples[left]
    after = samples[right]
    if not before.stamp_s <= stamp_s <= after.stamp_s:
        raise AnalysisError('imu_randprobe_ohne_echte_klammer')
    width = after.stamp_s - before.stamp_s
    if width <= 0.0:
        raise AnalysisError('imu_zeitstempel_nicht_monoton')
    fraction = (stamp_s - before.stamp_s) / width
    return before.yaw_rate_radps + fraction * (
        after.yaw_rate_radps - before.yaw_rate_radps)


def _bracketing_indices(
    stamps: Sequence[float], stamp_s: float,
) -> tuple[int, int]:
    """Return real sample indices bracketing ``stamp_s`` without extrapolation."""
    exact_or_right = bisect_left(stamps, stamp_s)
    if (
        exact_or_right < len(stamps)
        and stamps[exact_or_right] == stamp_s
    ):
        return exact_or_right, exact_or_right
    if exact_or_right <= 0 or exact_or_right >= len(stamps):
        raise AnalysisError('imu_randprobe_ohne_echte_klammer')
    return exact_or_right - 1, exact_or_right


def _integration_nodes(
    samples: Sequence[ImuYawSample], start_s: float, end_s: float,
) -> list[ImuYawSample]:
    if not math.isfinite(start_s) or not math.isfinite(end_s) or end_s <= start_s:
        raise AnalysisError('vergleichsintervall_ungueltig')
    start_value = _bracketed_value(samples, start_s)
    end_value = _bracketed_value(samples, end_s)
    nodes = [ImuYawSample(start_s, start_value)]
    nodes.extend(sample for sample in samples if start_s < sample.stamp_s < end_s)
    nodes.append(ImuYawSample(end_s, end_value))
    return nodes


def _trapezoid_prefix(
    nodes: Sequence[ImuYawSample],
) -> tuple[list[float], float]:
    prefix = [0.0]
    peak = 0.0
    for before, after in zip(nodes, nodes[1:]):
        dt = after.stamp_s - before.stamp_s
        if dt <= 0.0:
            raise AnalysisError('imu_zeitstempel_nicht_monoton')
        area = 0.5 * (before.yaw_rate_radps + after.yaw_rate_radps) * dt
        start_integral = prefix[-1]
        end_integral = start_integral + area
        peak = max(peak, abs(start_integral), abs(end_integral))

        # The integral of linearly interpolated rate can have an interior
        # extremum exactly where the rate crosses zero.
        delta_rate = after.yaw_rate_radps - before.yaw_rate_radps
        if delta_rate != 0.0:
            fraction = -before.yaw_rate_radps / delta_rate
            if 0.0 < fraction < 1.0:
                local_dt = fraction * dt
                zero_crossing_integral = start_integral + (
                    before.yaw_rate_radps * local_dt
                    + 0.5 * delta_rate / dt * local_dt * local_dt)
                peak = max(peak, abs(zero_crossing_integral))
        prefix.append(end_integral)
    return prefix, peak


def _integral_at(
    nodes: Sequence[ImuYawSample], prefix: Sequence[float], stamp_s: float,
) -> float:
    stamps = [node.stamp_s for node in nodes]
    exact = bisect_left(stamps, stamp_s)
    if exact < len(stamps) and stamps[exact] == stamp_s:
        return prefix[exact]
    right = exact
    left = right - 1
    if left < 0 or right >= len(nodes):
        raise AnalysisError('vergleichszeit_ausserhalb_imu_intervall')
    before = nodes[left]
    after = nodes[right]
    dt = after.stamp_s - before.stamp_s
    local_dt = stamp_s - before.stamp_s
    rate = before.yaw_rate_radps + (
        (after.yaw_rate_radps - before.yaw_rate_radps) * local_dt / dt)
    return prefix[left] + 0.5 * (before.yaw_rate_radps + rate) * local_dt


def compare_angles(
    imu_samples: Sequence[ImuYawSample],
    encoder_samples: Sequence[WheelPoseSample],
    *,
    maximum_imu_gap_s: float = MAX_IMU_GAP_S,
    maximum_encoder_gap_s: float = MAX_ENCODER_GAP_S,
) -> AngleComparison:
    """Compare unwrapped encoder yaw with the same bracketed HWT interval."""
    imu_duration, imu_gap = _strictly_increasing_stamps(imu_samples, 'imu')
    encoder_duration, encoder_gap = _strictly_increasing_stamps(
        encoder_samples, 'encoder')
    if imu_gap > maximum_imu_gap_s:
        raise AnalysisError('imu_datenluecke')
    if encoder_gap > maximum_encoder_gap_s:
        raise AnalysisError('encoder_datenluecke')
    if not all(
        math.isfinite(sample.yaw_rate_radps) for sample in imu_samples
    ):
        raise AnalysisError('imu_rate_nicht_endlich')

    start_s = encoder_samples[0].stamp_s
    end_s = encoder_samples[-1].stamp_s
    nodes = _integration_nodes(imu_samples, start_s, end_s)
    prefix, peak_hwt = _trapezoid_prefix(nodes)
    encoder_angles = unwrap_encoder_yaw(encoder_samples)
    first_encoder = encoder_samples[0]
    hwt_at_encoder = [
        _integral_at(nodes, prefix, sample.stamp_s)
        for sample in encoder_samples
    ]
    differences = [
        hwt - encoder
        for hwt, encoder in zip(hwt_at_encoder, encoder_angles)
    ]
    hwt_angle = prefix[-1]
    encoder_angle = encoder_angles[-1]
    return AngleComparison(
        start_stamp_s=start_s,
        end_stamp_s=end_s,
        duration_s=encoder_duration,
        imu_samples=sum(start_s <= sample.stamp_s <= end_s for sample in imu_samples),
        encoder_samples=len(encoder_samples),
        # The two real samples bracketing each encoder boundary intentionally
        # lie just outside the exact comparison interval.  Rate is therefore
        # measured over the complete validated IMU sequence rather than by a
        # boundary-dependent inclusive sample count.
        imu_rate_hz=(len(imu_samples) - 1) / imu_duration,
        encoder_rate_hz=(len(encoder_samples) - 1) / encoder_duration,
        maximum_imu_gap_s=max(
            after.stamp_s - before.stamp_s
            for before, after in zip(nodes, nodes[1:])),
        maximum_encoder_gap_s=encoder_gap,
        hwt_angle_rad=hwt_angle,
        encoder_angle_rad=encoder_angle,
        difference_rad=hwt_angle - encoder_angle,
        peak_absolute_hwt_angle_rad=peak_hwt,
        peak_absolute_encoder_angle_rad=max(abs(value) for value in encoder_angles),
        peak_absolute_difference_rad=max(abs(value) for value in differences),
        peak_translation_from_window_start_m=max(
            math.hypot(
                sample.x_m - first_encoder.x_m,
                sample.y_m - first_encoder.y_m,
            )
            for sample in encoder_samples
        ),
        peak_translation_from_encoder_baseline_m=max(
            math.hypot(sample.x_m, sample.y_m)
            for sample in encoder_samples
        ),
        peak_absolute_linear_velocity_mps=max(
            abs(sample.linear_velocity_mps) for sample in encoder_samples),
        peak_absolute_encoder_angular_velocity_radps=max(
            abs(sample.angular_velocity_radps) for sample in encoder_samples),
    )


class BiasPhaseGuard:
    """Prove that real wheel odometry was still for the whole HWT bias phase."""

    def __init__(self) -> None:
        self.saw_uncalibrated_status = False
        self.completed = False
        self.fault_reason: str | None = None
        self.first_wheel: WheelPoseSample | None = None
        self.last_wheel: WheelPoseSample | None = None
        self._previous_yaw: float | None = None
        self.accumulated_yaw_rad = 0.0
        self.peak_translation_m = 0.0
        self.peak_yaw_rad = 0.0
        self.observed_duration_s = 0.0
        self.end_stamp_s: float | None = None

    def _latch(self, reason: str) -> None:
        if self.fault_reason is None:
            self.fault_reason = reason

    def observe_wheel(self, sample: WheelPoseSample) -> None:
        if self.completed or self.fault_reason is not None:
            return
        if self.first_wheel is None:
            self.first_wheel = sample
            self._previous_yaw = sample.yaw_rad
            # EncoderShadowReader starts its real pose at the FC03 baseline.
            # A late observer must therefore not silently redefine a moved
            # first pose as zero: absolute displacement from that reader
            # baseline is already evidence from the unobserved bias window.
            self.accumulated_yaw_rad = normalize_angle(sample.yaw_rad)
        else:
            assert self._previous_yaw is not None
            self.accumulated_yaw_rad += normalize_angle(
                sample.yaw_rad - self._previous_yaw)
            self._previous_yaw = sample.yaw_rad
        self.peak_translation_m = max(
            self.peak_translation_m, math.hypot(sample.x_m, sample.y_m))
        self.peak_yaw_rad = max(
            self.peak_yaw_rad, abs(self.accumulated_yaw_rad))
        self.last_wheel = sample
        if (
            abs(sample.linear_velocity_mps) > MAX_BIAS_LINEAR_SPEED_MPS
            or abs(sample.angular_velocity_radps) > MAX_BIAS_ANGULAR_SPEED_RADPS
            or self.peak_translation_m > MAX_BIAS_TRANSLATION_M
            or self.peak_yaw_rad > MAX_BIAS_YAW_RAD
        ):
            self._latch('bewegung_waehrend_hwt_biasphase')

    def observe_hwt_status(self, status: Mapping[str, object]) -> None:
        if self.completed or self.fault_reason is not None:
            return
        bias = status.get('bias')
        if not isinstance(bias, Mapping):
            self._latch('hwt_biasstatus_fehlt')
            return
        calibrated = bias.get('calibrated')
        ready = status.get('ready')
        if type(calibrated) is not bool or type(ready) is not bool:
            self._latch('hwt_biasstatus_ungueltig')
            return
        if not calibrated and not ready:
            self.saw_uncalibrated_status = True
            return
        if not (calibrated and ready and bias.get('stable') is True):
            self._latch('hwt_biasstatus_widerspruechlich')
            return
        if not self.saw_uncalibrated_status:
            self._latch('hwt_biasphase_nicht_vollstaendig_beobachtet')
            return
        if self.first_wheel is None or self.last_wheel is None:
            self._latch('encoder_fuer_hwt_biasphase_fehlt')
            return
        self.observed_duration_s = (
            self.last_wheel.stamp_s - self.first_wheel.stamp_s)
        blocked = status.get('blocked')
        if (
            self.observed_duration_s < MIN_BIAS_PHASE_OBSERVED_S
            or type(blocked) is not int
            or blocked < MIN_BIAS_BLOCKED_SAMPLES
        ):
            self._latch('hwt_biasphase_nicht_vollstaendig_beobachtet')
            return
        self.completed = True
        self.end_stamp_s = self.last_wheel.stamp_s


class StatusContinuityGuard:
    """Latch status gaps or counter resets that could hide a node restart."""

    def __init__(self) -> None:
        self.fault_reason: str | None = None
        self.first_received_s: dict[str, float] = {}
        self.last_received_s: dict[str, float] = {}
        self.maximum_gap_s: dict[str, float] = {}
        self.counters: dict[tuple[str, str], int] = {}

    def _latch(self, reason: str) -> None:
        if self.fault_reason is None:
            self.fault_reason = reason

    def observe(
        self,
        source: str,
        received_s: float,
        counters: Mapping[str, object],
    ) -> None:
        if self.fault_reason is not None:
            return
        if not math.isfinite(received_s):
            self._latch(f'{source}_status_empfangszeit_ungueltig')
            return
        previous_received = self.last_received_s.get(source)
        if previous_received is not None:
            gap = received_s - previous_received
            if gap <= 0.0:
                self._latch(f'{source}_status_empfangszeit_nicht_monoton')
                return
            self.maximum_gap_s[source] = max(
                self.maximum_gap_s.get(source, 0.0), gap)
            if gap > MAX_STATUS_GAP_S:
                self._latch(f'{source}_status_datenluecke')
                return
        else:
            self.first_received_s[source] = received_s
            self.maximum_gap_s[source] = 0.0
        self.last_received_s[source] = received_s

        for name, value in counters.items():
            if type(value) is not int or value < 0:
                self._latch(f'{source}_statuszaehler_{name}_ungueltig')
                return
            key = (source, name)
            previous = self.counters.get(key)
            if previous is not None and value < previous:
                self._latch(f'{source}_statuszaehler_{name}_zurueckgesetzt')
                return
            self.counters[key] = value


class PostWindowStatusGuard:
    """Require fresh status receipts after the final selected measurement."""

    def __init__(self, timeout_s: float = POST_WINDOW_STATUS_TIMEOUT_S) -> None:
        if not math.isfinite(timeout_s) or timeout_s <= 0.0:
            raise ValueError('Abschlussstatus-Timeout muss endlich und > 0 sein')
        self.timeout_s = float(timeout_s)
        self.measurement_end_received_s: float | None = None
        self.deadline_s: float | None = None
        self.status_received_s: dict[str, float] = {}
        self.completed = False
        self.fault_reason: str | None = None

    def start(self, measurement_end_received_s: float) -> None:
        if self.measurement_end_received_s is not None:
            return
        if not math.isfinite(measurement_end_received_s):
            self.fault_reason = 'messende_empfangszeit_ungueltig'
            return
        self.measurement_end_received_s = float(measurement_end_received_s)
        self.deadline_s = (
            self.measurement_end_received_s + self.timeout_s)

    def update(
        self,
        now_s: float,
        received_times: Mapping[str, float | None],
    ) -> bool:
        if self.completed or self.fault_reason is not None:
            return self.completed
        if self.measurement_end_received_s is None or self.deadline_s is None:
            return False
        if not math.isfinite(now_s):
            self.fault_reason = 'abschlussstatus_pruefzeit_ungueltig'
            return False

        for source in POST_WINDOW_STATUS_SOURCES:
            if source in self.status_received_s:
                continue
            received_s = received_times.get(source)
            if received_s is None:
                continue
            if not math.isfinite(received_s):
                self.fault_reason = (
                    f'{source}_abschlussstatus_empfangszeit_ungueltig')
                return False
            if (
                self.measurement_end_received_s < received_s
                <= self.deadline_s
            ):
                self.status_received_s[source] = float(received_s)
        if len(self.status_received_s) == len(POST_WINDOW_STATUS_SOURCES):
            self.completed = True
            return True
        if now_s >= self.deadline_s:
            self.fault_reason = 'abschlussstatus_nach_messende_timeout'
        return False


def _is_zero_counter(value: object) -> bool:
    return type(value) is int and value == 0


def _qualified_node_name(name: str, namespace: str) -> str:
    namespace = namespace.rstrip('/')
    return f'{namespace}/{name}' if namespace else f'/{name}'


def validate_pre_window_coverage(
    measurement_start_received_s: float,
    first_status_received_s: Mapping[str, float],
    first_graph_check_s: float | None,
) -> str | None:
    """Prove that status and graph provenance predate selected samples."""
    if (
        type(measurement_start_received_s) not in (int, float)
        or not math.isfinite(measurement_start_received_s)
    ):
        return 'messstart_empfangszeit_ungueltig'
    for source in POST_WINDOW_STATUS_SOURCES:
        received_s = first_status_received_s.get(source)
        if (
            type(received_s) not in (int, float)
            or not math.isfinite(received_s)
        ):
            return f'{source}_erster_status_fehlt'
        if received_s >= measurement_start_received_s:
            return f'{source}_erster_status_nach_messstart'
    if (
        type(first_graph_check_s) not in (int, float)
        or not math.isfinite(first_graph_check_s)
    ):
        return 'ros_graph_erster_check_fehlt'
    if first_graph_check_s >= measurement_start_received_s:
        return 'ros_graph_erster_check_nach_messstart'
    return None


def validate_graph_contract(
    node_names: Iterable[tuple[str, str]],
    publishers: Mapping[str, Iterable[str]],
) -> list[str]:
    """Validate exact source provenance and absence of production outputs."""
    faults: list[str] = []
    qualified_nodes = [
        _qualified_node_name(name, namespace)
        for name, namespace in node_names
    ]
    if (
        len(qualified_nodes) != len(EXPECTED_GRAPH_NODES)
        or frozenset(qualified_nodes) != EXPECTED_GRAPH_NODES
    ):
        faults.append('ros_graph_nodes_unerwartet')
    for topic, expected in EXPECTED_TOPIC_PUBLISHERS.items():
        actual = tuple(publishers.get(topic, ()))
        if len(actual) != len(expected) or frozenset(actual) != expected:
            faults.append(f'ros_graph_publisher_unerwartet:{topic}')
    for topic in FORBIDDEN_PUBLISHER_TOPICS:
        if tuple(publishers.get(topic, ())):
            faults.append(f'produktiver_publisher_unerwartet:{topic}')
    return faults


class GraphContinuityGuard:
    """Latch graph violations and any publisher endpoint-instance change."""

    def __init__(self) -> None:
        self.fault_reason: str | None = None
        self.first_check_s: float | None = None
        self.last_check_s: float | None = None
        self.maximum_check_gap_s = 0.0
        self.endpoint_baseline: dict[str, tuple[str, ...]] | None = None

    def _latch(self, reason: str) -> None:
        if self.fault_reason is None:
            self.fault_reason = reason

    def observe(
        self,
        received_s: float,
        node_names: Iterable[tuple[str, str]],
        publishers: Mapping[str, Iterable[str]],
        endpoint_ids: Mapping[str, Iterable[str]],
    ) -> None:
        if self.fault_reason is not None:
            return
        if not math.isfinite(received_s):
            self._latch('ros_graph_pruefzeit_ungueltig')
            return
        if self.last_check_s is not None:
            gap = received_s - self.last_check_s
            if gap <= 0.0:
                self._latch('ros_graph_pruefzeit_nicht_monoton')
                return
            self.maximum_check_gap_s = max(self.maximum_check_gap_s, gap)
            if gap > MAX_GRAPH_CHECK_GAP_S:
                self._latch('ros_graph_pruefluecke')
                return
        else:
            self.first_check_s = received_s
        self.last_check_s = received_s

        violations = validate_graph_contract(node_names, publishers)
        if violations:
            self._latch(violations[0])
            return
        current = {
            topic: tuple(sorted(endpoint_ids.get(topic, ())))
            for topic in EXPECTED_TOPIC_PUBLISHERS
        }
        if any(len(values) != 1 for values in current.values()):
            self._latch('ros_graph_endpoint_id_ungueltig')
            return
        if self.endpoint_baseline is None:
            self.endpoint_baseline = current
        elif current != self.endpoint_baseline:
            self._latch('ros_graph_publisher_instanz_gewechselt')


def validate_hwt_status(
    status: Mapping[str, object], *, require_ready: bool,
) -> str | None:
    """Return the first HWT status-contract violation, if any."""
    bias = status.get('bias')
    if not isinstance(bias, Mapping):
        return 'hwt_biasstatus_fehlt'
    if status.get('shadow_only') is not True:
        return 'hwt_status_nicht_shadow_only'
    if status.get('fusion_ready') is not False:
        return 'hwt_fusion_ready_unerwartet'
    if status.get('actuator_output') is not False:
        return 'hwt_aktorausgabe_unerwartet'
    if status.get('publishes_tf') is not False:
        return 'hwt_tf_ausgabe_unerwartet'
    exact = {
        'operator_stationary_confirmed': True,
        'stationary_source': 'operator_declared_startup_only',
        'bias_frozen_after_startup': True,
        'scale_validation': 'external_180_observer_confirmed',
        'sensor_to_base_axes': 'x_b=y_s,y_b=-x_s,z_b=z_s',
        'input_topic': HWT_RAW_IMU_TOPIC,
        'input_frame': 'hwt601_link',
        'output_topic': IMU_TOPIC,
        'output_frame': IMU_FRAME,
        'output_qos': 'reliable_keep_last_200',
    }
    for key, expected in exact.items():
        if status.get(key) != expected:
            return f'hwt_status_{key}_ungueltig'
    if status.get('latched_fault') is not None:
        return 'hwt_fehler_verriegelt'
    if not _is_zero_counter(status.get('rejected')):
        return 'hwt_verworfene_proben'
    if not _is_zero_counter(bias.get('adaptation_samples')):
        return 'hwt_bias_nachgefuehrt'
    if require_ready and not (
        status.get('ready') is True
        and bias.get('calibrated') is True
        and bias.get('stable') is True
    ):
        return 'hwt_status_nicht_bereit'
    return None


def validate_encoder_status(
    status: Mapping[str, object], *, require_ready: bool,
) -> str | None:
    """Return the first real-FC03 encoder status violation, if any."""
    exact = {
        'source': 'ess23_absolute_fc03',
        'synthetic': False,
        'command_derived': False,
        'shadow_only': True,
        'fusion_ready': False,
        'read_only': True,
        'modbus_function_code': 3,
        'sensor_write_commands': False,
        'actuator_output': False,
        'cmd_vel_subscription': False,
        'publishes_tf': False,
        'port': '/dev/ttyUSB_BASE',
        'left_motor_id': 1,
        'right_motor_id': 2,
        'topic': WHEEL_TOPIC,
        'output_qos': 'reliable_keep_last_10',
        'odom_frame_id': ODOM_FRAME,
        'base_frame_id': BASE_FRAME,
        'wheel_radius_m': 0.0624,
        'wheel_separation_m': 0.3845,
        'gear_ratio': 10.0,
        'counts_per_motor_revolution': 1000.0,
        'invert_left': False,
        'invert_right': True,
        'position_register': 0x000A,
        'segment_register': 0x0011,
        'word_order_register': 0x0019,
        'resolution_register': 0x0101,
        'expected_segment': 1000,
        'expected_word_order': 0,
        'expected_resolution': 4000,
        'rpm_scale': 1.0,
        'poll_rate_hz': 20.0,
        'max_pair_read_duration_s': MAX_PAIR_DURATION_S,
        'max_sample_gap_s': ENCODER_SOURCE_MAX_SAMPLE_GAP_S,
    }
    for key, expected in exact.items():
        if status.get(key) != expected or (
            isinstance(expected, bool) and type(status.get(key)) is not bool
        ):
            return f'encoder_status_{key}_ungueltig'
    for key in ('rejected', 'reconnects', 'rebases'):
        if not _is_zero_counter(status.get(key)):
            return f'encoder_status_{key}_nicht_null'
    connections = status.get('successful_connections')
    if type(connections) is not int or connections not in (0, 1):
        return 'encoder_status_verbindungszaehler_ungueltig'
    if status.get('fault_latched') is not False:
        return 'encoder_fehler_verriegelt'
    if status.get('fault_reason') is not None:
        return 'encoder_fehlergrund_gesetzt'
    maximum_pair = status.get('maximum_pair_duration_s')
    if maximum_pair is not None and (
        type(maximum_pair) not in (int, float)
        or not math.isfinite(float(maximum_pair))
        or float(maximum_pair) < 0.0
        or float(maximum_pair) > MAX_PAIR_DURATION_S
    ):
        return 'encoderpaar_zeitfenster_ueberschritten'
    if require_ready and not (
        status.get('ready') is True
        and status.get('connected') is True
        and status.get('configuration_valid') is True
        and connections == 1
        and type(maximum_pair) in (int, float)
    ):
        return 'encoder_status_nicht_bereit'
    return None


def validate_raw_hwt_status(
    status: Mapping[str, object], *, require_ready: bool,
) -> str | None:
    """Validate the upstream serial reader, including reconnect evidence."""
    exact = {
        'fusion_ready': False,
        'sensor_write_commands': False,
        'actuator_output': False,
        'port': '/dev/ttyUSB_HWT601',
        'baud': 115200,
        'device_address': 80,
        'frame_id': 'hwt601_link',
        'topic': HWT_RAW_IMU_TOPIC,
        'host_receive_timestamp': True,
        'scale_validation_pending': True,
    }
    for key, expected in exact.items():
        if status.get(key) != expected or (
            isinstance(expected, bool) and type(status.get(key)) is not bool
        ):
            return f'hwt_raw_status_{key}_ungueltig'
    for key in ('rejected', 'reconnects', 'consecutive_errors'):
        if not _is_zero_counter(status.get(key)):
            return f'hwt_raw_status_{key}_nicht_null'
    connections = status.get('successful_connections')
    if type(connections) is not int or connections not in (0, 1):
        return 'hwt_raw_status_verbindungszaehler_ungueltig'
    if require_ready and not (
        status.get('ready') is True
        and status.get('raw_data_ready') is True
        and connections == 1
    ):
        return 'hwt_raw_status_nicht_bereit'
    return None


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as file:
        for block in iter(lambda: file.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def _finite(values: Iterable[float]) -> bool:
    return all(math.isfinite(float(value)) for value in values)


def _passed(summary: Mapping[str, object]) -> bool:
    """Apply the fixed 600-s stationary acceptance contract."""
    comparison = summary.get('comparison')
    bias_phase = summary.get('bias_phase')
    statuses = summary.get('statuses')
    graph = summary.get('graph')
    runtime = summary.get('runtime')
    status_continuity = summary.get('status_continuity')
    post_window_status = summary.get('post_window_status')
    if not isinstance(comparison, Mapping):
        return False
    if (
        not isinstance(bias_phase, Mapping)
        or not isinstance(statuses, Mapping)
        or not isinstance(graph, Mapping)
        or not isinstance(runtime, Mapping)
        or not isinstance(status_continuity, Mapping)
        or not isinstance(post_window_status, Mapping)
    ):
        return False
    hwt_status = statuses.get('hwt')
    hwt_raw_status = statuses.get('hwt_raw')
    encoder_status = statuses.get('encoder')
    if not all(isinstance(value, Mapping) for value in (
        hwt_status, hwt_raw_status, encoder_status,
    )):
        return False
    degrees = (
        comparison.get('hwt_angle_deg'),
        comparison.get('encoder_angle_deg'),
        comparison.get('difference_deg'),
        comparison.get('peak_absolute_hwt_angle_deg'),
        comparison.get('peak_absolute_encoder_angle_deg'),
        comparison.get('peak_absolute_difference_deg'),
    )
    if not all(type(value) in (int, float) and math.isfinite(value) for value in degrees):
        return False
    monotonic_duration = runtime.get('monotonic_duration_s')
    duration_skew = runtime.get('duration_clock_skew_s')
    measurement_start_received = runtime.get(
        'measurement_start_received_monotonic_s')
    if not all(
        type(value) in (int, float) and math.isfinite(value)
        for value in (
            monotonic_duration, duration_skew, measurement_start_received)
    ):
        return False
    first_status_receipts = status_continuity.get('first_received_s')
    if not isinstance(first_status_receipts, Mapping):
        return False
    if validate_pre_window_coverage(
        measurement_start_received,
        first_status_receipts,
        graph.get('first_check_monotonic_s'),
    ) is not None:
        return False
    measurement_end_received = post_window_status.get(
        'measurement_end_received_monotonic_s')
    post_status_deadline = post_window_status.get('deadline_monotonic_s')
    post_status_timeout = post_window_status.get('timeout_s')
    post_status_receipts = post_window_status.get(
        'status_received_monotonic_s')
    if (
        type(measurement_end_received) not in (int, float)
        or not math.isfinite(measurement_end_received)
        or type(post_status_deadline) not in (int, float)
        or not math.isfinite(post_status_deadline)
        or post_status_deadline <= measurement_end_received
        or type(post_status_timeout) not in (int, float)
        or not math.isfinite(post_status_timeout)
        or not math.isclose(
            post_status_timeout,
            POST_WINDOW_STATUS_TIMEOUT_S,
            rel_tol=0.0,
            abs_tol=1.0e-12,
        )
        or not math.isclose(
            post_status_deadline,
            measurement_end_received + post_status_timeout,
            rel_tol=0.0,
            abs_tol=1.0e-9,
        )
        or not isinstance(post_status_receipts, Mapping)
    ):
        return False
    for source in POST_WINDOW_STATUS_SOURCES:
        received_s = post_status_receipts.get(source)
        if (
            type(received_s) not in (int, float)
            or not math.isfinite(received_s)
            or received_s <= measurement_end_received
            or received_s > post_status_deadline
        ):
            return False
    return bool(
        summary.get('complete') is True
        and summary.get('faults') == []
        and type(summary.get('requested_duration_s')) in (int, float)
        and summary['requested_duration_s'] >= 600.0
        and comparison.get('duration_s', 0.0)
        >= summary['requested_duration_s'] - 0.05
        and comparison.get('imu_rate_hz', 0.0) >= MIN_IMU_RATE_HZ
        and comparison.get('encoder_rate_hz', 0.0) >= MIN_ENCODER_RATE_HZ
        and comparison.get('maximum_imu_gap_s', math.inf) <= MAX_IMU_GAP_S
        and comparison.get('maximum_encoder_gap_s', math.inf) <= MAX_ENCODER_GAP_S
        and all(abs(float(value)) < MAX_STATIONARY_ANGLE_DEG for value in degrees)
        and comparison.get(
            'peak_translation_from_window_start_m', math.inf,
        ) < MAX_STATIONARY_TRANSLATION_M
        and comparison.get(
            'peak_translation_from_encoder_baseline_m', math.inf,
        ) < MAX_STATIONARY_TRANSLATION_M
        and comparison.get(
            'peak_absolute_linear_velocity_mps', math.inf,
        ) < MAX_STATIONARY_LINEAR_SPEED_MPS
        and comparison.get(
            'peak_absolute_encoder_angular_velocity_radps', math.inf,
        ) < MAX_STATIONARY_ANGULAR_SPEED_RADPS
        and bias_phase.get('complete') is True
        and bias_phase.get('movement_detected') is False
        and bias_phase.get('observed_duration_s', 0.0)
        >= MIN_BIAS_PHASE_OBSERVED_S
        and statuses.get('hwt_valid') is True
        and statuses.get('hwt_raw_valid') is True
        and statuses.get('encoder_valid') is True
        and graph.get('valid') is True
        and monotonic_duration >= summary['requested_duration_s'] - 0.05
        and abs(duration_skew) <= MAX_DURATION_CLOCK_SKEW_S
        and status_continuity.get('valid') is True
        and post_window_status.get('complete') is True
        and post_window_status.get('fault_reason') is None
        and validate_hwt_status(hwt_status, require_ready=True) is None
        and validate_raw_hwt_status(
            hwt_raw_status, require_ready=True) is None
        and validate_encoder_status(
            encoder_status, require_ready=True) is None
    )


def _comparison_dict(comparison: AngleComparison) -> dict[str, object]:
    return {
        'start_stamp_s': comparison.start_stamp_s,
        'end_stamp_s': comparison.end_stamp_s,
        'duration_s': comparison.duration_s,
        'imu_samples': comparison.imu_samples,
        'encoder_samples': comparison.encoder_samples,
        'imu_rate_hz': comparison.imu_rate_hz,
        'encoder_rate_hz': comparison.encoder_rate_hz,
        'maximum_imu_gap_s': comparison.maximum_imu_gap_s,
        'maximum_encoder_gap_s': comparison.maximum_encoder_gap_s,
        'hwt_angle_deg': math.degrees(comparison.hwt_angle_rad),
        'encoder_angle_deg': math.degrees(comparison.encoder_angle_rad),
        'difference_deg': math.degrees(comparison.difference_rad),
        'peak_absolute_hwt_angle_deg': math.degrees(
            comparison.peak_absolute_hwt_angle_rad),
        'peak_absolute_encoder_angle_deg': math.degrees(
            comparison.peak_absolute_encoder_angle_rad),
        'peak_absolute_difference_deg': math.degrees(
            comparison.peak_absolute_difference_rad),
        'peak_translation_from_window_start_m': (
            comparison.peak_translation_from_window_start_m),
        'peak_translation_from_encoder_baseline_m': (
            comparison.peak_translation_from_encoder_baseline_m),
        'peak_absolute_linear_velocity_mps': (
            comparison.peak_absolute_linear_velocity_mps),
        'peak_absolute_encoder_angular_velocity_radps': (
            comparison.peak_absolute_encoder_angular_velocity_radps),
    }


def _run(duration_s: float, output: Path) -> int:
    # ROS imports remain outside the pure analysis layer so its regression
    # tests do not need a running daemon or a sourced ROS graph.
    import rclpy
    from nav_msgs.msg import Odometry
    from rclpy.node import Node
    from rclpy.qos import (
        DurabilityPolicy,
        HistoryPolicy,
        QoSProfile,
        ReliabilityPolicy,
    )
    from sensor_msgs.msg import Imu
    from std_msgs.msg import String

    output.mkdir(parents=True, exist_ok=False)
    csv_path = output / 'samples.csv'
    summary_path = output / 'summary.json'
    sensor_buffer_qos = QoSProfile(
        history=HistoryPolicy.KEEP_LAST,
        depth=SENSOR_BUFFER_DEPTH,
        reliability=ReliabilityPolicy.RELIABLE,
        durability=DurabilityPolicy.VOLATILE,
    )

    class DirectObserver(Node):
        def __init__(self, writer: csv.writer) -> None:
            super().__init__('hwt601_encoder_shadow_stillstand_observer')
            self.writer = writer
            self.imu_samples: list[ImuYawSample] = []
            self.wheel_samples: list[WheelPoseSample] = []
            self.imu_received_monotonic: list[float] = []
            self.wheel_received_monotonic: list[float] = []
            self.bias_guard = BiasPhaseGuard()
            self.status_guard = StatusContinuityGuard()
            self.graph_guard = GraphContinuityGuard()
            self.post_window_status_guard = PostWindowStatusGuard()
            self.hwt_status: dict[str, object] | None = None
            self.hwt_raw_status: dict[str, object] | None = None
            self.encoder_status: dict[str, object] | None = None
            self.hwt_status_received_at: float | None = None
            self.hwt_raw_status_received_at: float | None = None
            self.encoder_status_received_at: float | None = None
            self.faults: list[str] = []
            self.measurement_start_index: int | None = None
            self.measurement_end_index: int | None = None
            self.measurement_start_imu_index: int | None = None
            self.measurement_end_imu_index: int | None = None
            self.measurement_start_received_s: float | None = None
            self.maximum_observed_stamp_gap_s = {
                'imu': 0.0,
                'encoder': 0.0,
            }
            self.maximum_observed_receive_gap_s = {
                'imu': 0.0,
                'encoder': 0.0,
            }
            self.gap_fault_detail: dict[str, object] | None = None
            self.graph_nodes: list[tuple[str, str]] = []
            self.graph_publishers: dict[str, list[str]] = {}
            self.graph_endpoint_ids: dict[str, list[str]] = {}
            self.create_subscription(
                Imu, IMU_TOPIC, self._on_imu, sensor_buffer_qos)
            self.create_subscription(
                Odometry, WHEEL_TOPIC, self._on_wheel,
                sensor_buffer_qos)
            self.create_subscription(
                String, HWT_STATUS_TOPIC, self._on_hwt_status, 10)
            self.create_subscription(
                String, HWT_RAW_STATUS_TOPIC, self._on_hwt_raw_status, 10)
            self.create_subscription(
                String, ENCODER_STATUS_TOPIC, self._on_encoder_status, 10)

        def latch(self, reason: str) -> None:
            if reason not in self.faults:
                self.faults.append(reason)

        @staticmethod
        def status_payload(message: String) -> dict[str, object] | None:
            try:
                payload = json.loads(message.data)
            except (json.JSONDecodeError, TypeError):
                return None
            return payload if isinstance(payload, dict) else None

        def _on_hwt_status(self, message: String) -> None:
            received_at = time.monotonic()
            payload = self.status_payload(message)
            if payload is None:
                self.latch('hwt_status_json_ungueltig')
                return
            violation = validate_hwt_status(payload, require_ready=False)
            if violation is not None:
                self.latch(violation)
            self.hwt_status = payload
            self.hwt_status_received_at = received_at
            bias = payload.get('bias')
            bias = bias if isinstance(bias, Mapping) else {}
            self.status_guard.observe('hwt', received_at, {
                'raw_received': payload.get('raw_received'),
                'published': payload.get('published'),
                'blocked': payload.get('blocked'),
                'rejected': payload.get('rejected'),
                'bias_samples': bias.get('samples'),
                'bias_adaptation_samples': bias.get('adaptation_samples'),
            })
            if self.status_guard.fault_reason is not None:
                self.latch(self.status_guard.fault_reason)
            self.bias_guard.observe_hwt_status(payload)
            if self.bias_guard.fault_reason is not None:
                self.latch(self.bias_guard.fault_reason)

        def _on_hwt_raw_status(self, message: String) -> None:
            received_at = time.monotonic()
            payload = self.status_payload(message)
            if payload is None:
                self.latch('hwt_raw_status_json_ungueltig')
                return
            violation = validate_raw_hwt_status(
                payload, require_ready=False)
            if violation is not None:
                self.latch(violation)
            self.hwt_raw_status = payload
            self.hwt_raw_status_received_at = received_at
            self.status_guard.observe('hwt_raw', received_at, {
                'accepted': payload.get('accepted'),
                'rejected': payload.get('rejected'),
                'successful_connections': payload.get(
                    'successful_connections'),
                'reconnects': payload.get('reconnects'),
                'consecutive_errors': payload.get('consecutive_errors'),
            })
            if self.status_guard.fault_reason is not None:
                self.latch(self.status_guard.fault_reason)

        def _on_encoder_status(self, message: String) -> None:
            received_at = time.monotonic()
            payload = self.status_payload(message)
            if payload is None:
                self.latch('encoder_status_json_ungueltig')
                return
            violation = validate_encoder_status(payload, require_ready=False)
            if violation is not None:
                self.latch(violation)
            self.encoder_status = payload
            self.encoder_status_received_at = received_at
            self.status_guard.observe('encoder', received_at, {
                'complete_pair_count': payload.get('complete_pair_count'),
                'published_count': payload.get('published_count'),
                'baseline_count': payload.get('baseline_count'),
                'rejected': payload.get('rejected'),
                'successful_connections': payload.get(
                    'successful_connections'),
                'reconnects': payload.get('reconnects'),
                'rebases': payload.get('rebases'),
            })
            if self.status_guard.fault_reason is not None:
                self.latch(self.status_guard.fault_reason)

        def _on_imu(self, message: Imu) -> None:
            received_at = time.monotonic()
            stamp_s = float(message.header.stamp.sec) + 1.0e-9 * float(
                message.header.stamp.nanosec)
            values = (
                stamp_s,
                message.angular_velocity.x,
                message.angular_velocity.y,
                message.angular_velocity.z,
                *message.orientation_covariance,
                *message.angular_velocity_covariance,
                *message.linear_acceleration_covariance,
            )
            valid = (
                message.header.frame_id == IMU_FRAME
                and _finite(values)
                and stamp_s > 0.0
                and message.orientation_covariance[0] == -1.0
                and message.linear_acceleration_covariance[0] == -1.0
                and math.isclose(
                    message.angular_velocity_covariance[0],
                    UNOBSERVED_VARIANCE, rel_tol=0.0, abs_tol=1.0e-6)
                and math.isclose(
                    message.angular_velocity_covariance[4],
                    UNOBSERVED_VARIANCE, rel_tol=0.0, abs_tol=1.0e-6)
                and math.isclose(
                    message.angular_velocity_covariance[8],
                    IMU_Z_VARIANCE, rel_tol=0.0, abs_tol=1.0e-15)
            )
            if not valid:
                self.latch('imu_frame_zeit_wert_oder_kovarianz_ungueltig')
                return
            if self.imu_samples:
                gap = stamp_s - self.imu_samples[-1].stamp_s
                receive_gap = received_at - self.imu_received_monotonic[-1]
                self.maximum_observed_stamp_gap_s['imu'] = max(
                    self.maximum_observed_stamp_gap_s['imu'], gap)
                self.maximum_observed_receive_gap_s['imu'] = max(
                    self.maximum_observed_receive_gap_s['imu'], receive_gap)
                if gap <= 0.0:
                    self.latch('imu_zeitstempel_nicht_monoton')
                    return
                if gap > MAX_IMU_GAP_S:
                    self.gap_fault_detail = {
                        'source': 'imu',
                        'stamp_gap_s': gap,
                        'receive_gap_s': receive_gap,
                        'maximum_allowed_gap_s': MAX_IMU_GAP_S,
                    }
                    self.latch('imu_datenluecke')
                    return
            sample = ImuYawSample(stamp_s, float(message.angular_velocity.z))
            self.imu_samples.append(sample)
            self.imu_received_monotonic.append(received_at)
            self.writer.writerow((
                'imu', received_at, stamp_s, '', '', '',
                sample.yaw_rate_radps, '', '',
            ))

        def _on_wheel(self, message: Odometry) -> None:
            received_at = time.monotonic()
            stamp_s = float(message.header.stamp.sec) + 1.0e-9 * float(
                message.header.stamp.nanosec)
            pose = message.pose.pose
            twist = message.twist.twist
            values = (
                stamp_s, pose.position.x, pose.position.y, pose.position.z,
                pose.orientation.x, pose.orientation.y,
                pose.orientation.z, pose.orientation.w,
                twist.linear.x, twist.linear.y, twist.linear.z,
                twist.angular.x, twist.angular.y, twist.angular.z,
                *message.pose.covariance, *message.twist.covariance,
            )
            covariance_valid = (
                message.pose.covariance[0] > 0.0
                and message.pose.covariance[7] > 0.0
                and message.pose.covariance[35] > 0.0
                and message.twist.covariance[0] > 0.0
                and message.twist.covariance[35] > 0.0
            )
            if not (
                message.header.frame_id == ODOM_FRAME
                and message.child_frame_id == BASE_FRAME
                and _finite(values)
                and stamp_s > 0.0
                and covariance_valid
            ):
                self.latch('encoder_frame_zeit_wert_oder_kovarianz_ungueltig')
                return
            try:
                yaw = quaternion_to_planar_yaw(
                    pose.orientation.x, pose.orientation.y,
                    pose.orientation.z, pose.orientation.w)
            except AnalysisError as error:
                self.latch(str(error))
                return
            if self.wheel_samples:
                gap = stamp_s - self.wheel_samples[-1].stamp_s
                receive_gap = received_at - self.wheel_received_monotonic[-1]
                self.maximum_observed_stamp_gap_s['encoder'] = max(
                    self.maximum_observed_stamp_gap_s['encoder'], gap)
                self.maximum_observed_receive_gap_s['encoder'] = max(
                    self.maximum_observed_receive_gap_s['encoder'],
                    receive_gap,
                )
                if gap <= 0.0:
                    self.latch('encoder_zeitstempel_nicht_monoton')
                    return
                if gap > MAX_ENCODER_GAP_S:
                    self.gap_fault_detail = {
                        'source': 'encoder',
                        'stamp_gap_s': gap,
                        'receive_gap_s': receive_gap,
                        'maximum_allowed_gap_s': MAX_ENCODER_GAP_S,
                    }
                    self.latch('encoder_datenluecke')
                    return
            sample = WheelPoseSample(
                stamp_s=stamp_s,
                x_m=float(pose.position.x),
                y_m=float(pose.position.y),
                yaw_rad=yaw,
                linear_velocity_mps=float(twist.linear.x),
                angular_velocity_radps=float(twist.angular.z),
            )
            self.wheel_samples.append(sample)
            self.wheel_received_monotonic.append(received_at)
            self.bias_guard.observe_wheel(sample)
            if self.bias_guard.fault_reason is not None:
                self.latch(self.bias_guard.fault_reason)
            self.writer.writerow((
                'encoder', received_at, stamp_s,
                sample.x_m, sample.y_m, sample.yaw_rad, '',
                sample.linear_velocity_mps, sample.angular_velocity_radps,
            ))

        def _imu_bracket(self, stamp_s: float) -> tuple[int, int] | None:
            if len(self.imu_samples) < 2:
                return None
            stamps = [sample.stamp_s for sample in self.imu_samples]
            try:
                return _bracketing_indices(stamps, stamp_s)
            except AnalysisError:
                return None

        def _status_receipt_times(self) -> dict[str, float | None]:
            return {
                'hwt': self.hwt_status_received_at,
                'hwt_raw': self.hwt_raw_status_received_at,
                'encoder': self.encoder_status_received_at,
            }

        def wait_for_post_window_statuses(self) -> bool:
            complete = self.post_window_status_guard.update(
                time.monotonic(), self._status_receipt_times())
            if self.post_window_status_guard.fault_reason is not None:
                self.latch(self.post_window_status_guard.fault_reason)
            return complete

        def select_window(self) -> bool:
            if not self.bias_guard.completed or self.bias_guard.end_stamp_s is None:
                return False
            if self.measurement_start_index is None:
                for index, sample in enumerate(self.wheel_samples):
                    imu_bracket = self._imu_bracket(sample.stamp_s)
                    if (
                        sample.stamp_s < self.bias_guard.end_stamp_s
                        or imu_bracket is None
                    ):
                        continue
                    selected_start_received = min(
                        self.wheel_received_monotonic[index],
                        self.imu_received_monotonic[imu_bracket[0]],
                        self.imu_received_monotonic[imu_bracket[1]],
                    )
                    coverage_violation = validate_pre_window_coverage(
                        selected_start_received,
                        self.status_guard.first_received_s,
                        self.graph_guard.first_check_s,
                    )
                    if (
                        coverage_violation is None
                        and self.graph_guard.endpoint_baseline is not None
                    ):
                        self.measurement_start_index = index
                        self.measurement_start_imu_index = imu_bracket[0]
                        self.measurement_start_received_s = (
                            selected_start_received)
                        break
            if self.measurement_start_index is None:
                return False
            start = self.wheel_samples[self.measurement_start_index].stamp_s
            for index in range(
                self.measurement_start_index + 1, len(self.wheel_samples)
            ):
                sample = self.wheel_samples[index]
                imu_bracket = self._imu_bracket(sample.stamp_s)
                if (
                    sample.stamp_s - start >= duration_s
                    and self.wheel_received_monotonic[index]
                    - self.wheel_received_monotonic[
                        self.measurement_start_index] >= duration_s
                    and imu_bracket is not None
                ):
                    self.measurement_end_index = index
                    self.measurement_end_imu_index = imu_bracket[1]
                    last_sample_received = max(
                        self.wheel_received_monotonic[index],
                        self.imu_received_monotonic[imu_bracket[1]],
                    )
                    self.post_window_status_guard.start(
                        last_sample_received)
                    return True
            return False

        @staticmethod
        def _endpoint_token(info) -> str:
            try:
                gid = bytes(info.endpoint_gid).hex()
            except (TypeError, ValueError, AttributeError) as error:
                raise AnalysisError(
                    'ros_graph_endpoint_gid_ungueltig') from error
            if not gid:
                raise AnalysisError('ros_graph_endpoint_gid_ungueltig')
            return (
                f'{_qualified_node_name(info.node_name, info.node_namespace)}'
                f'@{gid}'
            )

        def check_graph(self, *, force: bool = False) -> None:
            # Source status can only arrive after all three source nodes have
            # joined.  Before that point the observer is intentionally alone.
            if not force and not all((
                self.hwt_status is not None,
                self.hwt_raw_status is not None,
                self.encoder_status is not None,
            )):
                return
            now = time.monotonic()
            if (
                not force
                and self.graph_guard.last_check_s is not None
                and now - self.graph_guard.last_check_s
                < GRAPH_CHECK_INTERVAL_S
            ):
                return
            graph_topics = (
                tuple(EXPECTED_TOPIC_PUBLISHERS)
                + FORBIDDEN_PUBLISHER_TOPICS
            )
            try:
                self.graph_nodes = list(self.get_node_names_and_namespaces())
                self.graph_publishers = {}
                self.graph_endpoint_ids = {}
                for topic in graph_topics:
                    infos = list(self.get_publishers_info_by_topic(topic))
                    self.graph_publishers[topic] = [
                        _qualified_node_name(
                            info.node_name, info.node_namespace)
                        for info in infos
                    ]
                    self.graph_endpoint_ids[topic] = [
                        self._endpoint_token(info) for info in infos
                    ]
                self.graph_guard.observe(
                    now,
                    self.graph_nodes,
                    self.graph_publishers,
                    self.graph_endpoint_ids,
                )
            except Exception as error:
                self.graph_guard._latch(
                    f'ros_graph_nicht_pruefbar:{type(error).__name__}')
            if self.graph_guard.fault_reason is not None:
                self.latch(self.graph_guard.fault_reason)

    rclpy.init()
    node = None
    comparison = None
    deadline = time.monotonic() + duration_s + 90.0
    next_progress = time.monotonic() + 60.0
    with csv_path.open('x', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow((
            'kind', 'received_monotonic_s', 'stamp_s', 'x_m', 'y_m',
            'yaw_rad', 'yaw_rate_radps', 'linear_velocity_mps',
            'angular_velocity_radps',
        ))
        node = DirectObserver(writer)
        while time.monotonic() < deadline and not node.faults:
            rclpy.spin_once(node, timeout_sec=0.1)
            node.check_graph()
            node.select_window()
            if (
                node.measurement_end_index is not None
                and node.wait_for_post_window_statuses()
            ):
                break
            if time.monotonic() >= next_progress:
                observed = 0.0
                if node.measurement_start_index is not None:
                    observed = (
                        node.wheel_samples[-1].stamp_s
                        - node.wheel_samples[node.measurement_start_index].stamp_s
                    )
                print(
                    f'Fortschritt {observed:.1f}/{duration_s:.1f} s; '
                    f'IMU={len(node.imu_samples)}, '
                    f'Encoder={len(node.wheel_samples)}',
                    flush=True,
                )
                next_progress += 60.0

        if not node.faults and node.measurement_end_index is None:
            node.latch('aufnahmezeitlimit_oder_randklammer_fehlt')
        if (
            not node.faults
            and not node.post_window_status_guard.completed
        ):
            node.latch('abschlussstatus_nach_messende_fehlt')
        if not node.faults:
            assert node.measurement_start_index is not None
            assert node.measurement_end_index is not None
            assert node.measurement_start_imu_index is not None
            assert node.measurement_end_imu_index is not None
            assert node.measurement_start_received_s is not None
            try:
                comparison = compare_angles(
                    node.imu_samples[
                        node.measurement_start_imu_index:
                        node.measurement_end_imu_index + 1
                    ],
                    node.wheel_samples[
                        node.measurement_start_index:
                        node.measurement_end_index + 1
                    ],
                )
            except AnalysisError as error:
                node.latch(str(error))

    assert node is not None
    now = time.monotonic()
    hwt_valid = False
    hwt_raw_valid = False
    encoder_valid = False
    node.check_graph(force=True)
    if node.hwt_status is None:
        node.latch('hwt_status_fehlt')
    elif (
        node.hwt_status_received_at is None
        or now - node.hwt_status_received_at > STATUS_MAX_AGE_S
    ):
        node.latch('hwt_status_veraltet')
    else:
        violation = validate_hwt_status(node.hwt_status, require_ready=True)
        if violation is None:
            hwt_valid = True
        else:
            node.latch(violation)
    if node.hwt_raw_status is None:
        node.latch('hwt_raw_status_fehlt')
    elif (
        node.hwt_raw_status_received_at is None
        or now - node.hwt_raw_status_received_at > STATUS_MAX_AGE_S
    ):
        node.latch('hwt_raw_status_veraltet')
    else:
        violation = validate_raw_hwt_status(
            node.hwt_raw_status, require_ready=True)
        if violation is None:
            hwt_raw_valid = True
        else:
            node.latch(violation)
    if node.encoder_status is None:
        node.latch('encoder_status_fehlt')
    elif (
        node.encoder_status_received_at is None
        or now - node.encoder_status_received_at > STATUS_MAX_AGE_S
    ):
        node.latch('encoder_status_veraltet')
    else:
        violation = validate_encoder_status(
            node.encoder_status, require_ready=True)
        if violation is None:
            encoder_valid = True
        else:
            node.latch(violation)

    movement_detected = (
        node.bias_guard.fault_reason == 'bewegung_waehrend_hwt_biasphase')
    monotonic_duration_s = None
    duration_clock_skew_s = None
    if (
        comparison is not None
        and node.measurement_start_index is not None
        and node.measurement_end_index is not None
    ):
        monotonic_duration_s = (
            node.wheel_received_monotonic[node.measurement_end_index]
            - node.wheel_received_monotonic[node.measurement_start_index]
        )
        duration_clock_skew_s = monotonic_duration_s - comparison.duration_s
    summary: dict[str, object] = {
        'complete': comparison is not None,
        'requested_duration_s': duration_s,
        'observer_only': True,
        'topics': {
            'imu': IMU_TOPIC,
            'encoder': WHEEL_TOPIC,
            'hwt_status': HWT_STATUS_TOPIC,
            'hwt_raw_status': HWT_RAW_STATUS_TOPIC,
            'encoder_status': ENCODER_STATUS_TOPIC,
        },
        'bias_phase': {
            'complete': node.bias_guard.completed,
            'saw_uncalibrated_status': (
                node.bias_guard.saw_uncalibrated_status),
            'observed_duration_s': node.bias_guard.observed_duration_s,
            'movement_detected': movement_detected,
            'peak_translation_m': node.bias_guard.peak_translation_m,
            'peak_yaw_deg': math.degrees(node.bias_guard.peak_yaw_rad),
            'fault_reason': node.bias_guard.fault_reason,
        },
        'comparison': (
            None if comparison is None else _comparison_dict(comparison)),
        'runtime': {
            'measurement_start_received_monotonic_s': (
                node.measurement_start_received_s),
            'monotonic_duration_s': monotonic_duration_s,
            'ros_stamp_duration_s': (
                None if comparison is None else comparison.duration_s),
            'duration_clock_skew_s': duration_clock_skew_s,
            'maximum_allowed_clock_skew_s': MAX_DURATION_CLOCK_SKEW_S,
        },
        'stream_timing': {
            'maximum_observed_stamp_gap_s': (
                node.maximum_observed_stamp_gap_s),
            'maximum_observed_receive_gap_s': (
                node.maximum_observed_receive_gap_s),
            'gap_fault_detail': node.gap_fault_detail,
        },
        'status_continuity': {
            'valid': node.status_guard.fault_reason is None,
            'fault_reason': node.status_guard.fault_reason,
            'first_received_s': node.status_guard.first_received_s,
            'maximum_gap_s': node.status_guard.maximum_gap_s,
            'maximum_allowed_gap_s': MAX_STATUS_GAP_S,
        },
        'post_window_status': {
            'complete': node.post_window_status_guard.completed,
            'fault_reason': node.post_window_status_guard.fault_reason,
            'measurement_end_received_monotonic_s': (
                node.post_window_status_guard.measurement_end_received_s),
            'deadline_monotonic_s': node.post_window_status_guard.deadline_s,
            'timeout_s': node.post_window_status_guard.timeout_s,
            'status_received_monotonic_s': (
                node.post_window_status_guard.status_received_s),
        },
        'statuses': {
            'hwt_valid': hwt_valid,
            'hwt_raw_valid': hwt_raw_valid,
            'encoder_valid': encoder_valid,
            'hwt': node.hwt_status,
            'hwt_raw': node.hwt_raw_status,
            'encoder': node.encoder_status,
        },
        'graph': {
            'valid': node.graph_guard.fault_reason is None,
            'fault_reason': node.graph_guard.fault_reason,
            'first_check_monotonic_s': node.graph_guard.first_check_s,
            'maximum_check_gap_s': node.graph_guard.maximum_check_gap_s,
            'maximum_allowed_check_gap_s': MAX_GRAPH_CHECK_GAP_S,
            'nodes': sorted(
                _qualified_node_name(name, namespace)
                for name, namespace in node.graph_nodes
            ),
            'publishers': node.graph_publishers,
            'endpoint_ids': node.graph_endpoint_ids,
            'endpoint_baseline': node.graph_guard.endpoint_baseline,
        },
        'faults': node.faults,
        'samples_sha256': _sha256(csv_path),
    }
    summary['passed'] = _passed(summary)
    summary_path.write_text(
        json.dumps(summary, indent=2, allow_nan=False) + '\n',
        encoding='utf-8',
    )
    print(json.dumps(summary, indent=2, allow_nan=False), flush=True)
    node.destroy_node()
    if rclpy.ok():
        rclpy.shutdown()
    return 0 if summary['passed'] else 1


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--duration', type=float, default=600.0)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    if not math.isfinite(args.duration) or args.duration < 10.0:
        parser.error('--duration muss endlich und mindestens 10 s sein')
    return _run(args.duration, args.output)


if __name__ == '__main__':
    raise SystemExit(main())
