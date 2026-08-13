"""ROS-unabhaengige Encoder-Odometrie fuer den Amadeus-Differentialantrieb.

Die ESS-RS-Treiber liefern ihre aktuelle Position als 32-Bit-Zaehler in den
Holding-Registern 0x000A/0x000B. Dieses Modul enthaelt nur Mathematik und
Zustandslogik. Es importiert weder ROS noch pymodbus und kann deshalb auf jedem
Entwicklungsrechner vollstaendig getestet werden.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence


UINT16_MAX = (1 << 16) - 1
UINT32_MODULUS = 1 << 32
INT32_HALF_RANGE = 1 << 31


def _validate_word(value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f'Registerwort muss int sein, erhalten: {type(value).__name__}')
    if not 0 <= value <= UINT16_MAX:
        raise ValueError(f'Registerwort ausserhalb uint16: {value}')
    return value


def decode_position_words(words: Sequence[int], high_word_first: bool) -> int:
    """Dekodiert genau zwei Modbus-Worte zu einem unsigned 32-Bit-Zaehler.

    ``high_word_first`` wird beim ESS-RS aus Register 0x0019 gelesen. Der
    unsigned Wert ist fuer eine ueberlaufsichere Delta-Bildung erforderlich;
    fuer eine menschenlesbare signed-Anzeige dient :func:`u32_to_i32`.
    """
    if len(words) != 2:
        raise ValueError(f'Genau zwei Positionsworte erwartet, erhalten: {len(words)}')
    first = _validate_word(words[0])
    second = _validate_word(words[1])
    high, low = (first, second) if high_word_first else (second, first)
    return (high << 16) | low


def u32_to_i32(value: int) -> int:
    """Interpretiert ein uint32-Zweierkomplement als signed int32."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError('32-Bit-Wert muss int sein')
    if not 0 <= value < UINT32_MODULUS:
        raise ValueError(f'Wert ausserhalb uint32: {value}')
    return value - UINT32_MODULUS if value >= INT32_HALF_RANGE else value


def decode_i16(word: int) -> int:
    """Dekodiert ein Modbus-Wort als signed int16."""
    value = _validate_word(word)
    return value - (1 << 16) if value >= (1 << 15) else value


def modular_delta_u32(previous: int, current: int) -> int:
    """Kleinste vorzeichenbehaftete Differenz zweier umlaufender uint32-Werte.

    Damit werden sowohl ``0xFFFFFFFF -> 0`` als auch der umgekehrte Ueberlauf
    korrekt als ein Count behandelt. Eine Differenz von exakt 2**31 ist
    richtungsmehrdeutig und wird abgelehnt.
    """
    for name, value in (('previous', previous), ('current', current)):
        if isinstance(value, bool) or not isinstance(value, int):
            raise TypeError(f'{name} muss int sein')
        if not 0 <= value < UINT32_MODULUS:
            raise ValueError(f'{name} ausserhalb uint32: {value}')
    raw = (current - previous) % UINT32_MODULUS
    if raw == INT32_HALF_RANGE:
        raise ValueError('32-Bit-Differenz ist bei exakt 2**31 richtungsmehrdeutig')
    return raw - UINT32_MODULUS if raw > INT32_HALF_RANGE else raw


def normalize_angle(angle: float) -> float:
    return math.atan2(math.sin(angle), math.cos(angle))


@dataclass(frozen=True)
class MotorFeedback:
    """Atomar aus 0x000A..0x000C gelesene Rueckmeldung eines Motors."""

    position_u32: int
    speed_rpm: float


@dataclass(frozen=True)
class EncoderUpdate:
    """Ergebnis genau einer vollstaendigen linken/rechten Paarmessung."""

    accepted: bool
    initialized: bool
    reason: str
    sample_dt_s: float = 0.0
    left_delta_counts: int = 0
    right_delta_counts: int = 0
    left_distance_m: float = 0.0
    right_distance_m: float = 0.0
    distance_m: float = 0.0
    heading_rad: float = 0.0
    linear_velocity_mps: float = 0.0
    angular_velocity_radps: float = 0.0


class EncoderOdometry:
    """Integriert absolute Motorzaehler zu einer Differential-Odometrie.

    Die erste Paarprobe setzt nur die Baseline. Fehlende/partielle Proben
    werden nicht an :meth:`update` uebergeben; dadurch bleibt die Baseline
    stehen und die naechste gueltige Probe holt die Bewegung der Luecke nach.
    """

    def __init__(
        self,
        *,
        wheel_radius_m: float,
        wheel_separation_m: float,
        gear_ratio: float,
        counts_per_motor_revolution: float,
        invert_left: bool = False,
        invert_right: bool = False,
        max_motor_rpm: float,
        max_delta_factor: float = 1.5,
        quantization_margin_counts: int = 8,
        max_recovery_gap_s: float = 2.0,
    ) -> None:
        positive_values = {
            'wheel_radius_m': wheel_radius_m,
            'wheel_separation_m': wheel_separation_m,
            'gear_ratio': gear_ratio,
            'counts_per_motor_revolution': counts_per_motor_revolution,
            'max_motor_rpm': max_motor_rpm,
            'max_delta_factor': max_delta_factor,
            'max_recovery_gap_s': max_recovery_gap_s,
        }
        for name, value in positive_values.items():
            if not math.isfinite(float(value)) or float(value) <= 0.0:
                raise ValueError(f'{name} muss endlich und > 0 sein')
        if quantization_margin_counts < 0:
            raise ValueError('quantization_margin_counts muss >= 0 sein')

        self.wheel_radius_m = float(wheel_radius_m)
        self.wheel_separation_m = float(wheel_separation_m)
        self.gear_ratio = float(gear_ratio)
        self.counts_per_motor_revolution = float(counts_per_motor_revolution)
        self.invert_left = bool(invert_left)
        self.invert_right = bool(invert_right)
        self.max_motor_rpm = float(max_motor_rpm)
        self.max_delta_factor = float(max_delta_factor)
        self.quantization_margin_counts = int(quantization_margin_counts)
        self.max_recovery_gap_s = float(max_recovery_gap_s)

        self.x_m = 0.0
        self.y_m = 0.0
        self.yaw_rad = 0.0
        self._left_position_u32: int | None = None
        self._right_position_u32: int | None = None
        self._sample_time_s: float | None = None
        self.accepted_update_count = 0
        self.rejected_update_count = 0
        self.rebase_count = 0

    @property
    def initialized(self) -> bool:
        return self._left_position_u32 is not None

    def set_pose(self, x_m: float, y_m: float, yaw_rad: float) -> None:
        """Setzt nur die Pose; die Encoderbaseline bleibt bewusst erhalten."""
        if not all(math.isfinite(v) for v in (x_m, y_m, yaw_rad)):
            raise ValueError('Posewerte muessen endlich sein')
        self.x_m = float(x_m)
        self.y_m = float(y_m)
        self.yaw_rad = normalize_angle(float(yaw_rad))

    def reset_baseline(self) -> None:
        """Verwirft die Zaehlerbaseline, nicht aber die bisherige Pose."""
        self._left_position_u32 = None
        self._right_position_u32 = None
        self._sample_time_s = None

    def update(self, left_position_u32: int, right_position_u32: int,
               sample_time_s: float) -> EncoderUpdate:
        self._validate_position(left_position_u32)
        self._validate_position(right_position_u32)
        if not math.isfinite(sample_time_s):
            return self._reject('ungueltiger_zeitstempel')

        if not self.initialized:
            self._rebase(left_position_u32, right_position_u32, sample_time_s, count=False)
            return EncoderUpdate(False, True, 'baseline_initialisiert')

        assert self._sample_time_s is not None
        assert self._left_position_u32 is not None
        assert self._right_position_u32 is not None
        dt = sample_time_s - self._sample_time_s
        if dt <= 0.0:
            return self._reject('nicht_monotoner_zeitstempel')
        if dt > self.max_recovery_gap_s:
            self._rebase(left_position_u32, right_position_u32, sample_time_s)
            return EncoderUpdate(False, True, 'luecke_zu_lang_rebaseline', sample_dt_s=dt)

        try:
            left_raw_delta = modular_delta_u32(
                self._left_position_u32, left_position_u32)
            right_raw_delta = modular_delta_u32(
                self._right_position_u32, right_position_u32)
        except ValueError as exc:
            self._rebase(left_position_u32, right_position_u32, sample_time_s)
            return EncoderUpdate(False, True, f'mehrdeutiges_delta:{exc}', sample_dt_s=dt)

        max_counts = (
            self.max_motor_rpm * dt / 60.0
            * self.counts_per_motor_revolution * self.max_delta_factor
            + self.quantization_margin_counts
        )
        if abs(left_raw_delta) > max_counts or abs(right_raw_delta) > max_counts:
            self._rebase(left_position_u32, right_position_u32, sample_time_s)
            return EncoderUpdate(
                False, True,
                f'unplausibles_delta:max={max_counts:.1f}',
                sample_dt_s=dt,
                left_delta_counts=left_raw_delta,
                right_delta_counts=right_raw_delta,
            )

        # Erst nach allen Paarpruefungen fortschreiben: Ein unvollstaendiges
        # Paar darf die Baseline keines einzelnen Motors verschieben.
        self._left_position_u32 = left_position_u32
        self._right_position_u32 = right_position_u32
        self._sample_time_s = sample_time_s

        left_delta = -left_raw_delta if self.invert_left else left_raw_delta
        right_delta = -right_raw_delta if self.invert_right else right_raw_delta
        metres_per_motor_count = (
            2.0 * math.pi * self.wheel_radius_m
            / (self.counts_per_motor_revolution * self.gear_ratio)
        )
        left_distance = left_delta * metres_per_motor_count
        right_distance = right_delta * metres_per_motor_count
        distance = (left_distance + right_distance) / 2.0
        heading = (right_distance - left_distance) / self.wheel_separation_m

        if abs(heading) < 1e-12:
            dx_body = distance
            dy_body = 0.0
        else:
            turn_radius = distance / heading
            dx_body = turn_radius * math.sin(heading)
            dy_body = turn_radius * (1.0 - math.cos(heading))

        cos_yaw = math.cos(self.yaw_rad)
        sin_yaw = math.sin(self.yaw_rad)
        self.x_m += cos_yaw * dx_body - sin_yaw * dy_body
        self.y_m += sin_yaw * dx_body + cos_yaw * dy_body
        self.yaw_rad = normalize_angle(self.yaw_rad + heading)
        self.accepted_update_count += 1

        return EncoderUpdate(
            True,
            True,
            'ok',
            sample_dt_s=dt,
            left_delta_counts=left_delta,
            right_delta_counts=right_delta,
            left_distance_m=left_distance,
            right_distance_m=right_distance,
            distance_m=distance,
            heading_rad=heading,
            linear_velocity_mps=distance / dt,
            angular_velocity_radps=heading / dt,
        )

    @staticmethod
    def _validate_position(value: int) -> None:
        if isinstance(value, bool) or not isinstance(value, int):
            raise TypeError('Encoderposition muss int sein')
        if not 0 <= value < UINT32_MODULUS:
            raise ValueError(f'Encoderposition ausserhalb uint32: {value}')

    def _reject(self, reason: str) -> EncoderUpdate:
        self.rejected_update_count += 1
        return EncoderUpdate(False, self.initialized, reason)

    def _rebase(self, left: int, right: int, timestamp: float,
                *, count: bool = True) -> None:
        self._left_position_u32 = left
        self._right_position_u32 = right
        self._sample_time_s = timestamp
        if count:
            self.rejected_update_count += 1
            self.rebase_count += 1
