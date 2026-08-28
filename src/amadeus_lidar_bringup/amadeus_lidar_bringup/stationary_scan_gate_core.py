"""ROS-unabhaengige Zustandslogik fuer eine Stillstands-Scanfreigabe."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math
from typing import Optional


class GateState(str, Enum):
    WAIT_STABLE = 'wait_stable'
    CAPTURING = 'capturing'
    WAIT_MOVEMENT = 'wait_movement'


@dataclass(frozen=True)
class GateParameters:
    settle_duration_s: float = 1.2
    capture_duration_s: float = 2.0
    sensor_max_age_s: float = 0.35
    maximum_linear_speed_m_s: float = 0.01
    maximum_angular_speed_rad_s: float = 0.025
    maximum_imu_angular_speed_rad_s: float = 0.08
    gravity_m_s2: float = 9.80665
    maximum_acceleration_deviation_m_s2: float = 0.8
    rearm_motion_duration_s: float = 0.15
    rearm_translation_m: float = 0.08
    rearm_rotation_rad: float = 0.08

    def validate(self) -> None:
        positive = {
            'settle_duration_s': self.settle_duration_s,
            'capture_duration_s': self.capture_duration_s,
            'sensor_max_age_s': self.sensor_max_age_s,
            'maximum_linear_speed_m_s': self.maximum_linear_speed_m_s,
            'maximum_angular_speed_rad_s': self.maximum_angular_speed_rad_s,
            'maximum_imu_angular_speed_rad_s': (
                self.maximum_imu_angular_speed_rad_s),
            'gravity_m_s2': self.gravity_m_s2,
            'maximum_acceleration_deviation_m_s2': (
                self.maximum_acceleration_deviation_m_s2),
            'rearm_motion_duration_s': self.rearm_motion_duration_s,
            'rearm_translation_m': self.rearm_translation_m,
            'rearm_rotation_rad': self.rearm_rotation_rad,
        }
        invalid = [name for name, value in positive.items()
                   if not math.isfinite(value) or value <= 0.0]
        if invalid:
            raise ValueError(
                'Parameter muessen endlich und groesser null sein: '
                + ', '.join(invalid))


@dataclass(frozen=True)
class ImuObservation:
    received_s: float
    angular_speed_rad_s: float
    acceleration_norm_m_s2: float
    valid: bool


@dataclass(frozen=True)
class OdomObservation:
    received_s: float
    linear_speed_m_s: float
    angular_speed_rad_s: float
    x_m: float
    y_m: float
    yaw_rad: float
    valid: bool


@dataclass(frozen=True)
class GateDecision:
    forward_scan: bool
    state: GateState
    reason: str
    capture_index: int


def angular_distance(first: float, second: float) -> float:
    """Kleinster Betrag zwischen zwei Winkeln."""
    return abs(math.atan2(
        math.sin(first - second), math.cos(first - second)))


class StationaryScanGate:
    """Laesst pro nachgewiesenem Stillstand genau ein Scanfenster durch."""

    def __init__(self, parameters: GateParameters) -> None:
        parameters.validate()
        self.parameters = parameters
        self.state = GateState.WAIT_STABLE
        self.reason = 'missing_imu'
        self.imu: Optional[ImuObservation] = None
        self.odom: Optional[OdomObservation] = None
        self.stable_since_s: Optional[float] = None
        self.capture_started_s: Optional[float] = None
        self.motion_started_s: Optional[float] = None
        self.last_capture_pose: Optional[tuple[float, float, float]] = None
        self.capture_index = 0
        self.capture_scan_count = 0
        self.total_forwarded_scans = 0
        self.total_dropped_scans = 0
        self.interrupted_captures = 0

    def update_imu(
        self,
        received_s: float,
        angular_velocity: tuple[float, float, float],
        acceleration: tuple[float, float, float],
    ) -> None:
        values = (received_s, *angular_velocity, *acceleration)
        valid = all(math.isfinite(value) for value in values)
        self.imu = ImuObservation(
            received_s=received_s,
            angular_speed_rad_s=(
                math.sqrt(sum(value * value for value in angular_velocity))
                if valid else math.nan),
            acceleration_norm_m_s2=(
                math.sqrt(sum(value * value for value in acceleration))
                if valid else math.nan),
            valid=valid,
        )

    def update_odom(
        self,
        received_s: float,
        linear_velocity: tuple[float, float],
        angular_speed_rad_s: float,
        pose: tuple[float, float, float],
    ) -> None:
        values = (received_s, *linear_velocity, angular_speed_rad_s, *pose)
        valid = all(math.isfinite(value) for value in values)
        self.odom = OdomObservation(
            received_s=received_s,
            linear_speed_m_s=(
                math.hypot(*linear_velocity) if valid else math.nan),
            angular_speed_rad_s=(
                abs(angular_speed_rad_s) if valid else math.nan),
            x_m=pose[0],
            y_m=pose[1],
            yaw_rad=pose[2],
            valid=valid,
        )

    def _sensor_stability(self, now_s: float) -> tuple[bool, str]:
        if self.imu is None:
            return False, 'missing_imu'
        if not self.imu.valid:
            return False, 'invalid_imu'
        if now_s - self.imu.received_s > self.parameters.sensor_max_age_s:
            return False, 'stale_imu'
        if self.odom is None:
            return False, 'missing_odom'
        if not self.odom.valid:
            return False, 'invalid_odom'
        if now_s - self.odom.received_s > self.parameters.sensor_max_age_s:
            return False, 'stale_odom'
        if (self.odom.linear_speed_m_s
                > self.parameters.maximum_linear_speed_m_s):
            return False, 'odom_linear_motion'
        if (self.odom.angular_speed_rad_s
                > self.parameters.maximum_angular_speed_rad_s):
            return False, 'odom_angular_motion'
        if (self.imu.angular_speed_rad_s
                > self.parameters.maximum_imu_angular_speed_rad_s):
            return False, 'imu_angular_motion'
        acceleration_error = abs(
            self.imu.acceleration_norm_m_s2 - self.parameters.gravity_m_s2)
        if (acceleration_error
                > self.parameters.maximum_acceleration_deviation_m_s2):
            return False, 'imu_acceleration_unstable'
        return True, 'stable'

    def _pose_moved_enough(self) -> bool:
        if self.odom is None or not self.odom.valid:
            return False
        if self.last_capture_pose is None:
            return False
        old_x, old_y, old_yaw = self.last_capture_pose
        translation = math.hypot(self.odom.x_m - old_x, self.odom.y_m - old_y)
        rotation = angular_distance(self.odom.yaw_rad, old_yaw)
        return (
            translation >= self.parameters.rearm_translation_m
            or rotation >= self.parameters.rearm_rotation_rad)

    def _motion_rearms(self, now_s: float) -> bool:
        if self.odom is None or not self.odom.valid:
            self.motion_started_s = None
            return False
        moving = (
            self.odom.linear_speed_m_s
            > self.parameters.maximum_linear_speed_m_s
            or self.odom.angular_speed_rad_s
            > self.parameters.maximum_angular_speed_rad_s)
        if moving:
            if self.motion_started_s is None:
                self.motion_started_s = now_s
            if (now_s - self.motion_started_s
                    >= self.parameters.rearm_motion_duration_s):
                return True
        else:
            self.motion_started_s = None
        return self._pose_moved_enough()

    def _drop(self, reason: str) -> GateDecision:
        self.reason = reason
        self.total_dropped_scans += 1
        return GateDecision(
            False, self.state, reason, self.capture_index)

    def process_scan(self, now_s: float) -> GateDecision:
        """Entscheidet bei Ankunft eines frischen Scans fail-closed."""
        if not math.isfinite(now_s):
            return self._drop('invalid_scan_time')

        stable, stability_reason = self._sensor_stability(now_s)

        if self.state == GateState.WAIT_MOVEMENT:
            if self._motion_rearms(now_s):
                self.state = GateState.WAIT_STABLE
                self.stable_since_s = None
                self.capture_started_s = None
            else:
                return self._drop(
                    'wait_movement' if stable else stability_reason)

        if self.state == GateState.CAPTURING:
            if not stable:
                self.state = GateState.WAIT_STABLE
                self.stable_since_s = None
                self.capture_started_s = None
                self.interrupted_captures += 1
                return self._drop(stability_reason)
            assert self.capture_started_s is not None
            if (now_s - self.capture_started_s
                    >= self.parameters.capture_duration_s):
                self.state = GateState.WAIT_MOVEMENT
                self.last_capture_pose = (
                    (self.odom.x_m, self.odom.y_m, self.odom.yaw_rad)
                    if self.odom is not None else None)
                self.capture_started_s = None
                self.motion_started_s = None
                return self._drop('capture_complete')

            self.reason = 'capturing'
            self.capture_scan_count += 1
            self.total_forwarded_scans += 1
            return GateDecision(
                True, self.state, self.reason, self.capture_index)

        if not stable:
            self.stable_since_s = None
            return self._drop(stability_reason)

        if self.stable_since_s is None:
            self.stable_since_s = now_s
        if now_s - self.stable_since_s < self.parameters.settle_duration_s:
            return self._drop('settling')

        self.state = GateState.CAPTURING
        self.capture_started_s = now_s
        self.capture_index += 1
        self.capture_scan_count = 1
        self.reason = 'capturing'
        self.total_forwarded_scans += 1
        return GateDecision(True, self.state, self.reason, self.capture_index)

    @staticmethod
    def _age(now_s: float, received_s: Optional[float]) -> Optional[float]:
        if received_s is None:
            return None
        return max(0.0, now_s - received_s)

    def snapshot(self, now_s: float) -> dict[str, object]:
        stable, stability_reason = self._sensor_stability(now_s)
        settled_for = (
            max(0.0, now_s - self.stable_since_s)
            if self.stable_since_s is not None else 0.0)
        capture_remaining = (
            max(0.0, self.parameters.capture_duration_s
                - (now_s - self.capture_started_s))
            if self.capture_started_s is not None else 0.0)
        capture_active = (
            self.state == GateState.CAPTURING
            and stable
            and self.capture_started_s is not None
            and now_s - self.capture_started_s
            < self.parameters.capture_duration_s)
        return {
            'state': self.state.value,
            'gate_open': capture_active,
            'reason': self.reason,
            'stability_reason': stability_reason,
            'sensors_stable': stable,
            'settled_for_s': round(settled_for, 3),
            'capture_remaining_s': round(capture_remaining, 3),
            'capture_index': self.capture_index,
            'capture_scan_count': self.capture_scan_count,
            'total_forwarded_scans': self.total_forwarded_scans,
            'total_dropped_scans': self.total_dropped_scans,
            'interrupted_captures': self.interrupted_captures,
            'imu_age_s': self._age(
                now_s, self.imu.received_s if self.imu else None),
            'odom_age_s': self._age(
                now_s, self.odom.received_s if self.odom else None),
            'imu_angular_speed_rad_s': (
                self.imu.angular_speed_rad_s if self.imu else None),
            'acceleration_norm_m_s2': (
                self.imu.acceleration_norm_m_s2 if self.imu else None),
            'odom_linear_speed_m_s': (
                self.odom.linear_speed_m_s if self.odom else None),
            'odom_angular_speed_rad_s': (
                self.odom.angular_speed_rad_s if self.odom else None),
        }
