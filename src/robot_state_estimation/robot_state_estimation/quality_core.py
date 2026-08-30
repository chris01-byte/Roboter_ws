"""ROS-independent quality logic for portable sensor fusion.

The classes in this module deliberately know nothing about ROS messages or
Amadeus hardware.  A successor robot can therefore reuse them with different
drivers, topics and sensor mounting frames.
"""

from dataclasses import dataclass
import math
from typing import Optional, Sequence, Tuple


Vector3 = Tuple[float, float, float]


def _finite_vector(values: Sequence[float], length: int) -> bool:
    return len(values) == length and all(math.isfinite(value) for value in values)


def _norm(vector: Vector3) -> float:
    return math.sqrt(sum(value * value for value in vector))


def _unit(vector: Vector3) -> Vector3:
    magnitude = _norm(vector)
    if not math.isfinite(magnitude) or magnitude <= 1e-9:
        raise ValueError('Vektor kann nicht normiert werden')
    return tuple(value / magnitude for value in vector)  # type: ignore[return-value]


def _angle_between(first: Vector3, second: Vector3) -> float:
    product = sum(a * b for a, b in zip(first, second))
    return math.acos(max(-1.0, min(1.0, product)))


def rotate_vector_by_quaternion(
    vector: Vector3, quaternion_xyzw: Tuple[float, float, float, float]
) -> Vector3:
    """Rotate a vector using a normalized ``(x, y, z, w)`` quaternion."""
    if not _finite_vector(vector, 3) or not _finite_vector(quaternion_xyzw, 4):
        raise ValueError('Vektor und Quaternion muessen endlich sein')
    x, y, z, w = quaternion_xyzw
    magnitude = math.sqrt(x * x + y * y + z * z + w * w)
    if magnitude <= 1e-9:
        raise ValueError('Quaternion darf nicht null sein')
    x, y, z, w = (value / magnitude for value in (x, y, z, w))
    vx, vy, vz = vector

    # q * v * conjugate(q), expanded to avoid another dependency.
    tx = 2.0 * (y * vz - z * vy)
    ty = 2.0 * (z * vx - x * vz)
    tz = 2.0 * (x * vy - y * vx)
    return (
        vx + w * tx + (y * tz - z * ty),
        vy + w * ty + (z * tx - x * tz),
        vz + w * tz + (x * ty - y * tx),
    )


@dataclass(frozen=True)
class GyroBiasConfig:
    calibration_duration_s: float = 2.0
    minimum_samples: int = 300
    maximum_stddev_radps: float = 0.02
    maximum_sample_magnitude_radps: float = 0.20

    def validate(self) -> None:
        values = (
            self.calibration_duration_s,
            self.maximum_stddev_radps,
            self.maximum_sample_magnitude_radps,
        )
        if not all(math.isfinite(value) and value > 0.0 for value in values):
            raise ValueError('Gyro-Kalibriergrenzen muessen positiv sein')
        if self.minimum_samples < 2:
            raise ValueError('Gyro-Kalibrierung braucht mindestens zwei Proben')


@dataclass(frozen=True)
class GyroBiasResult:
    calibrated: bool
    reason: str
    samples: int
    bias_radps: Vector3
    stddev_radps: Vector3


class GyroBiasEstimator:
    """Estimate a fixed startup gyro bias only during confirmed standstill."""

    def __init__(self, config: Optional[GyroBiasConfig] = None):
        self.config = config or GyroBiasConfig()
        self.config.validate()
        self._calibrated = False
        self._first_stamp_s: Optional[float] = None
        self._last_stamp_s: Optional[float] = None
        self._samples = 0
        self._mean = [0.0, 0.0, 0.0]
        self._m2 = [0.0, 0.0, 0.0]
        self._result = GyroBiasResult(
            calibrated=False,
            reason='warte_auf_bestaetigten_stillstand',
            samples=0,
            bias_radps=(0.0, 0.0, 0.0),
            stddev_radps=(float('inf'),) * 3,
        )

    @property
    def result(self) -> GyroBiasResult:
        return self._result

    def reset(self, reason: str) -> GyroBiasResult:
        if self._calibrated:
            return self._result
        self._first_stamp_s = None
        self._last_stamp_s = None
        self._samples = 0
        self._mean = [0.0, 0.0, 0.0]
        self._m2 = [0.0, 0.0, 0.0]
        self._result = GyroBiasResult(
            calibrated=False,
            reason=reason,
            samples=0,
            bias_radps=(0.0, 0.0, 0.0),
            stddev_radps=(float('inf'),) * 3,
        )
        return self._result

    def update(
            self, stamp_s: float, angular_velocity_radps: Vector3,
            stationary: bool) -> GyroBiasResult:
        if self._calibrated:
            return self._result
        if (
                not math.isfinite(stamp_s)
                or not _finite_vector(angular_velocity_radps, 3)):
            return self.reset('gyro_probe_ungueltig')
        if not stationary:
            return self.reset('warte_auf_bestaetigten_stillstand')
        if self._last_stamp_s is not None and stamp_s <= self._last_stamp_s:
            return self.reset('gyro_zeit_nicht_monoton')
        if _norm(angular_velocity_radps) > self.config.maximum_sample_magnitude_radps:
            return self.reset('gyro_bewegung_waehrend_kalibrierung')
        if self._first_stamp_s is None:
            self._first_stamp_s = stamp_s
        self._last_stamp_s = stamp_s
        self._samples += 1
        for index, value in enumerate(angular_velocity_radps):
            delta = value - self._mean[index]
            self._mean[index] += delta / self._samples
            self._m2[index] += delta * (value - self._mean[index])
        stddev = tuple(
            math.sqrt(value / max(1, self._samples - 1))
            for value in self._m2)
        elapsed = stamp_s - self._first_stamp_s
        enough = (
            elapsed >= self.config.calibration_duration_s
            and self._samples >= self.config.minimum_samples)
        if enough and max(stddev) > self.config.maximum_stddev_radps:
            return self.reset('gyro_kalibrierung_zu_unruhig')
        if enough:
            self._calibrated = True
            self._result = GyroBiasResult(
                calibrated=True,
                reason='gyro_bias_kalibriert',
                samples=self._samples,
                bias_radps=tuple(self._mean),  # type: ignore[arg-type]
                stddev_radps=stddev,  # type: ignore[arg-type]
            )
            return self._result
        self._result = GyroBiasResult(
            calibrated=False,
            reason='gyro_bias_warmup',
            samples=self._samples,
            bias_radps=tuple(self._mean),  # type: ignore[arg-type]
            stddev_radps=stddev,  # type: ignore[arg-type]
        )
        return self._result

    def correct(self, angular_velocity_radps: Vector3) -> Vector3:
        if not self._result.calibrated:
            raise RuntimeError('Gyro-Bias ist noch nicht kalibriert')
        return tuple(
            value - bias
            for value, bias in zip(
                angular_velocity_radps, self._result.bias_radps)
        )  # type: ignore[return-value]


@dataclass(frozen=True)
class ImuStabilityConfig:
    """Limits for detecting a temporarily invalid planar LiDAR scan."""

    gravity_mps2: float = 9.80665
    minimum_acceleration_mps2: float = 7.0
    maximum_acceleration_mps2: float = 12.5
    maximum_gravity_direction_change_rad: float = math.radians(3.0)
    maximum_roll_pitch_rate_radps: float = math.radians(14.0)
    baseline_time_constant_s: float = 4.0
    warmup_s: float = 0.6
    settle_s: float = 0.45

    def validate(self) -> None:
        positive = (
            self.gravity_mps2,
            self.minimum_acceleration_mps2,
            self.maximum_acceleration_mps2,
            self.maximum_gravity_direction_change_rad,
            self.maximum_roll_pitch_rate_radps,
            self.baseline_time_constant_s,
            self.warmup_s,
            self.settle_s,
        )
        if not all(math.isfinite(value) and value > 0.0 for value in positive):
            raise ValueError('IMU-Grenzen muessen endlich und positiv sein')
        if self.minimum_acceleration_mps2 >= self.maximum_acceleration_mps2:
            raise ValueError('Beschleunigungsgrenzen sind vertauscht')
        if not (
                self.minimum_acceleration_mps2
                < self.gravity_mps2
                < self.maximum_acceleration_mps2):
            raise ValueError('Erdbeschleunigung muss innerhalb der Grenzen liegen')


@dataclass(frozen=True)
class ImuStabilityResult:
    ready: bool
    stable: bool
    reason: str
    gravity_direction_change_rad: float
    roll_pitch_rate_radps: float
    acceleration_norm_mps2: float


class ImuStabilityMonitor:
    """Detect short roll/pitch and impact events without assuming level mounting.

    The first stable acceleration vector becomes a local gravity reference.
    This is important for Amadeus because the OAK camera is deliberately
    pitched.  A slow low-pass update follows a genuinely sloped floor, while a
    tile joint or threshold remains a transient event and starts a settling
    interval.
    """

    def __init__(self, config: Optional[ImuStabilityConfig] = None):
        self.config = config or ImuStabilityConfig()
        self.config.validate()
        self._baseline: Optional[Vector3] = None
        self._first_stamp_s: Optional[float] = None
        self._last_stamp_s: Optional[float] = None
        self._unstable_until_s = float('-inf')
        self._last_result = ImuStabilityResult(
            ready=False,
            stable=False,
            reason='imu_noch_nicht_empfangen',
            gravity_direction_change_rad=float('inf'),
            roll_pitch_rate_radps=float('inf'),
            acceleration_norm_mps2=float('nan'),
        )

    @property
    def last_result(self) -> ImuStabilityResult:
        return self._last_result

    @property
    def last_stamp_s(self) -> Optional[float]:
        return self._last_stamp_s

    def reset(self, reason: str = 'imu_reset') -> ImuStabilityResult:
        self._baseline = None
        self._first_stamp_s = None
        self._last_stamp_s = None
        self._unstable_until_s = float('-inf')
        self._last_result = ImuStabilityResult(
            ready=False,
            stable=False,
            reason=reason,
            gravity_direction_change_rad=float('inf'),
            roll_pitch_rate_radps=float('inf'),
            acceleration_norm_mps2=float('nan'),
        )
        return self._last_result

    def update(
            self, stamp_s: float, angular_velocity_radps: Vector3,
            linear_acceleration_mps2: Vector3) -> ImuStabilityResult:
        if (
                not math.isfinite(stamp_s)
                or not _finite_vector(angular_velocity_radps, 3)
                or not _finite_vector(linear_acceleration_mps2, 3)):
            return self.reset('imu_ungueltige_werte')
        if self._last_stamp_s is not None and stamp_s <= self._last_stamp_s:
            return self.reset('imu_zeit_nicht_monoton')

        acceleration_norm = _norm(linear_acceleration_mps2)
        if acceleration_norm <= 1e-9:
            return self.reset('imu_beschleunigung_null')
        gravity_direction = _unit(linear_acceleration_mps2)
        if self._baseline is None:
            self._baseline = gravity_direction
            self._first_stamp_s = stamp_s
            self._last_stamp_s = stamp_s
            self._last_result = ImuStabilityResult(
                ready=False,
                stable=False,
                reason='imu_warmup',
                gravity_direction_change_rad=0.0,
                roll_pitch_rate_radps=math.hypot(
                    angular_velocity_radps[0], angular_velocity_radps[1]),
                acceleration_norm_mps2=acceleration_norm,
            )
            return self._last_result

        assert self._first_stamp_s is not None
        assert self._last_stamp_s is not None
        dt = stamp_s - self._last_stamp_s
        direction_change = _angle_between(self._baseline, gravity_direction)
        roll_pitch_rate = math.hypot(
            angular_velocity_radps[0], angular_velocity_radps[1])
        acceleration_valid = (
            self.config.minimum_acceleration_mps2
            <= acceleration_norm
            <= self.config.maximum_acceleration_mps2)
        raw_stable = (
            acceleration_valid
            and direction_change
            <= self.config.maximum_gravity_direction_change_rad
            and roll_pitch_rate <= self.config.maximum_roll_pitch_rate_radps)

        if not raw_stable:
            self._unstable_until_s = max(
                self._unstable_until_s, stamp_s + self.config.settle_s)
        else:
            alpha = min(
                1.0,
                dt / (self.config.baseline_time_constant_s + dt))
            blended = tuple(
                (1.0 - alpha) * old + alpha * new
                for old, new in zip(self._baseline, gravity_direction))
            self._baseline = _unit(blended)  # type: ignore[arg-type]

        ready = stamp_s - self._first_stamp_s >= self.config.warmup_s
        stable = ready and raw_stable and stamp_s >= self._unstable_until_s
        if not acceleration_valid:
            reason = 'beschleunigungsstoss'
        elif direction_change > self.config.maximum_gravity_direction_change_rad:
            reason = 'kippwinkel'
        elif roll_pitch_rate > self.config.maximum_roll_pitch_rate_radps:
            reason = 'roll_nick_rate'
        elif not ready:
            reason = 'imu_warmup'
        elif stamp_s < self._unstable_until_s:
            reason = 'beruhigungszeit'
        else:
            reason = 'stabil'

        self._last_stamp_s = stamp_s
        self._last_result = ImuStabilityResult(
            ready=ready,
            stable=stable,
            reason=reason,
            gravity_direction_change_rad=direction_change,
            roll_pitch_rate_radps=roll_pitch_rate,
            acceleration_norm_mps2=acceleration_norm,
        )
        return self._last_result

    def is_fresh(self, now_s: float, timeout_s: float) -> bool:
        return (
            self._last_stamp_s is not None
            and math.isfinite(now_s)
            and math.isfinite(timeout_s)
            and timeout_s > 0.0
            and 0.0 <= now_s - self._last_stamp_s <= timeout_s)


@dataclass(frozen=True)
class MotionConsistencyConfig:
    """Limits for comparing wheel motion with an independent source."""

    maximum_linear_velocity_error_mps: float = 0.10
    maximum_angular_velocity_error_radps: float = 0.22
    minimum_evaluation_speed_mps: float = 0.025
    minimum_evaluation_rate_radps: float = 0.08
    maximum_stamp_skew_s: float = 0.16
    bad_samples_to_latch: int = 2
    good_samples_to_recover: int = 5
    suspect_covariance_scale: float = 10.0
    slip_covariance_scale: float = 100.0

    def validate(self) -> None:
        values = (
            self.maximum_linear_velocity_error_mps,
            self.maximum_angular_velocity_error_radps,
            self.minimum_evaluation_speed_mps,
            self.minimum_evaluation_rate_radps,
            self.maximum_stamp_skew_s,
            self.suspect_covariance_scale,
            self.slip_covariance_scale,
        )
        if not all(math.isfinite(value) and value > 0.0 for value in values):
            raise ValueError('Konsistenzgrenzen muessen endlich und positiv sein')
        if self.bad_samples_to_latch < 1 or self.good_samples_to_recover < 1:
            raise ValueError('Hysteresenzaehler muessen mindestens eins sein')
        if self.suspect_covariance_scale < 1.0:
            raise ValueError('Verdacht darf Kovarianz nicht verkleinern')
        if self.slip_covariance_scale < self.suspect_covariance_scale:
            raise ValueError('Schlupfskalierung muss mindestens Verdacht entsprechen')


@dataclass(frozen=True)
class MotionConsistencyResult:
    evaluated: bool
    state: str
    reason: str
    covariance_scale: float
    linear_velocity_error_mps: float
    angular_velocity_error_radps: float
    consecutive_bad: int
    consecutive_good: int


class MotionConsistencyMonitor:
    """Hysteretic disagreement detector; it never invents replacement motion."""

    def __init__(self, config: Optional[MotionConsistencyConfig] = None):
        self.config = config or MotionConsistencyConfig()
        self.config.validate()
        self._latched = False
        self._bad = 0
        self._good = 0
        self._last = MotionConsistencyResult(
            evaluated=False,
            state='unverified',
            reason='referenz_noch_nicht_verfuegbar',
            covariance_scale=1.0,
            linear_velocity_error_mps=float('nan'),
            angular_velocity_error_radps=float('nan'),
            consecutive_bad=0,
            consecutive_good=0,
        )

    @property
    def last_result(self) -> MotionConsistencyResult:
        return self._last

    def update(
            self, wheel_linear_mps: float, wheel_angular_radps: float,
            reference_linear_mps: float, reference_angular_radps: float,
            stamp_skew_s: float) -> MotionConsistencyResult:
        values = (
            wheel_linear_mps,
            wheel_angular_radps,
            reference_linear_mps,
            reference_angular_radps,
            stamp_skew_s,
        )
        if not all(math.isfinite(value) for value in values):
            return self._unevaluated('nicht_endliche_bewegungswerte')
        if abs(stamp_skew_s) > self.config.maximum_stamp_skew_s:
            return self._unevaluated('zeitversatz_zu_gross')

        linear_error = abs(wheel_linear_mps - reference_linear_mps)
        angular_error = abs(wheel_angular_radps - reference_angular_radps)
        informative = (
            max(abs(wheel_linear_mps), abs(reference_linear_mps))
            >= self.config.minimum_evaluation_speed_mps
            or max(abs(wheel_angular_radps), abs(reference_angular_radps))
            >= self.config.minimum_evaluation_rate_radps)
        if not informative:
            return self._record_good(
                linear_error, angular_error, 'beide_quellen_im_stillstand')

        agrees = (
            linear_error <= self.config.maximum_linear_velocity_error_mps
            and angular_error
            <= self.config.maximum_angular_velocity_error_radps)
        if agrees:
            return self._record_good(
                linear_error, angular_error, 'bewegung_konsistent')
        return self._record_bad(
            linear_error, angular_error, 'bewegung_widerspricht_referenz')

    def _unevaluated(self, reason: str) -> MotionConsistencyResult:
        scale = (
            self.config.slip_covariance_scale if self._latched else 1.0)
        self._last = MotionConsistencyResult(
            evaluated=False,
            state='slip' if self._latched else 'unverified',
            reason=reason,
            covariance_scale=scale,
            linear_velocity_error_mps=float('nan'),
            angular_velocity_error_radps=float('nan'),
            consecutive_bad=self._bad,
            consecutive_good=self._good,
        )
        return self._last

    def _record_bad(
            self, linear_error: float, angular_error: float,
            reason: str) -> MotionConsistencyResult:
        self._bad += 1
        self._good = 0
        if self._bad >= self.config.bad_samples_to_latch:
            self._latched = True
        state = 'slip' if self._latched else 'suspect'
        scale = (
            self.config.slip_covariance_scale
            if self._latched else self.config.suspect_covariance_scale)
        self._last = MotionConsistencyResult(
            evaluated=True,
            state=state,
            reason=reason,
            covariance_scale=scale,
            linear_velocity_error_mps=linear_error,
            angular_velocity_error_radps=angular_error,
            consecutive_bad=self._bad,
            consecutive_good=0,
        )
        return self._last

    def _record_good(
            self, linear_error: float, angular_error: float,
            reason: str) -> MotionConsistencyResult:
        self._good += 1
        self._bad = 0
        if self._latched and self._good >= self.config.good_samples_to_recover:
            self._latched = False
        state = 'slip' if self._latched else 'nominal'
        scale = self.config.slip_covariance_scale if self._latched else 1.0
        self._last = MotionConsistencyResult(
            evaluated=True,
            state=state,
            reason=reason if not self._latched else 'schlupf_hysterese',
            covariance_scale=scale,
            linear_velocity_error_mps=linear_error,
            angular_velocity_error_radps=angular_error,
            consecutive_bad=0,
            consecutive_good=self._good,
        )
        return self._last
