"""Small, strict Modbus decoder for the HWT601-AGV-485 motion registers.

Only Modbus function 0x03 (read holding registers) is implemented.  Keeping
write functions out of this module is intentional: commissioning the IMU must
not alter its persistent configuration or calibration.
"""

from dataclasses import dataclass
import math
from typing import Sequence, Tuple


DEFAULT_DEVICE_ADDRESS = 0x50
MOTION_REGISTER_START = 0x34
MOTION_REGISTER_COUNT = 6
READ_HOLDING_REGISTERS = 0x03
STANDARD_GRAVITY_MPS2 = 9.80665


class Hwt601ProtocolError(ValueError):
    """A request or response violates the expected HWT601 Modbus contract."""


class Hwt601ModbusException(Hwt601ProtocolError):
    """The sensor returned a Modbus exception response."""


def crc16_modbus(payload: bytes) -> int:
    """Return the standard Modbus RTU CRC-16 value for *payload*."""

    crc = 0xFFFF
    for byte in payload:
        crc ^= byte
        for _ in range(8):
            if crc & 0x0001:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    return crc


def append_crc(payload: bytes) -> bytes:
    crc = crc16_modbus(payload)
    return payload + bytes((crc & 0xFF, (crc >> 8) & 0xFF))


def build_read_holding_registers(
        device_address: int,
        start_register: int,
        register_count: int) -> bytes:
    if not 1 <= device_address <= 247:
        raise Hwt601ProtocolError(
            'Modbus-Adresse muss zwischen 1 und 247 liegen')
    if not 0 <= start_register <= 0xFFFF:
        raise Hwt601ProtocolError('Startregister liegt ausserhalb von uint16')
    if not 1 <= register_count <= 125:
        raise Hwt601ProtocolError(
            'Registeranzahl muss zwischen 1 und 125 liegen')
    payload = bytes((
        device_address,
        READ_HOLDING_REGISTERS,
        (start_register >> 8) & 0xFF,
        start_register & 0xFF,
        (register_count >> 8) & 0xFF,
        register_count & 0xFF,
    ))
    return append_crc(payload)


def parse_read_holding_response(
        frame: bytes,
        expected_address: int,
        expected_register_count: int) -> Tuple[int, ...]:
    if len(frame) < 5:
        raise Hwt601ProtocolError('Modbus-Antwort ist zu kurz')
    received_crc = frame[-2] | (frame[-1] << 8)
    calculated_crc = crc16_modbus(frame[:-2])
    if received_crc != calculated_crc:
        raise Hwt601ProtocolError(
            f'CRC ungueltig: empfangen=0x{received_crc:04x}, '
            f'erwartet=0x{calculated_crc:04x}')
    if frame[0] != expected_address:
        raise Hwt601ProtocolError(
            f'falsche Modbus-Adresse {frame[0]}, erwartet {expected_address}')
    if frame[1] == (READ_HOLDING_REGISTERS | 0x80):
        if len(frame) != 5:
            raise Hwt601ProtocolError('ungueltige Modbus-Ausnahmeantwort')
        raise Hwt601ModbusException(
            f'HWT601 meldet Modbus-Ausnahme 0x{frame[2]:02x}')
    if frame[1] != READ_HOLDING_REGISTERS:
        raise Hwt601ProtocolError(
            f'unerwartete Modbus-Funktion 0x{frame[1]:02x}')
    expected_bytes = expected_register_count * 2
    if frame[2] != expected_bytes:
        raise Hwt601ProtocolError(
            f'falsche Nutzdatenlaenge {frame[2]}, erwartet {expected_bytes}')
    if len(frame) != expected_bytes + 5:
        raise Hwt601ProtocolError(
            f'falsche Rahmenlaenge {len(frame)}, '
            f'erwartet {expected_bytes + 5}')
    payload = frame[3:-2]
    return tuple(
        (payload[index] << 8) | payload[index + 1]
        for index in range(0, len(payload), 2))


def signed_int16(value: int) -> int:
    if not 0 <= value <= 0xFFFF:
        raise Hwt601ProtocolError('Registerwert liegt ausserhalb von uint16')
    return value - 0x10000 if value & 0x8000 else value


@dataclass(frozen=True)
class Hwt601Sample:
    raw_acceleration: Tuple[int, int, int]
    raw_angular_velocity: Tuple[int, int, int]
    linear_acceleration_mps2: Tuple[float, float, float]
    angular_velocity_radps: Tuple[float, float, float]

    def saturated(self, margin_counts: int = 8) -> bool:
        limit = 32768 - margin_counts
        return any(
            abs(value) >= limit
            for value in self.raw_acceleration + self.raw_angular_velocity)


def decode_motion_registers(
        registers: Sequence[int],
        acceleration_full_scale_g: float = 4.0,
        angular_velocity_full_scale_dps: float = 400.0,
        gravity_mps2: float = STANDARD_GRAVITY_MPS2) -> Hwt601Sample:
    """Decode AX..AZ and GX..GZ into SI units without rotating the axes.

    The HWT601 data sheet states +/-4 g and 0.0122 deg/s per LSB (equivalent
    to a 400 deg/s signed full scale).  Both scales remain parameters because
    they must be confirmed on the delivered firmware before fusion.
    """

    if len(registers) != MOTION_REGISTER_COUNT:
        raise Hwt601ProtocolError(
            f'{MOTION_REGISTER_COUNT} Bewegungsregister erwartet, '
            f'{len(registers)} erhalten')
    scales = (
        acceleration_full_scale_g,
        angular_velocity_full_scale_dps,
        gravity_mps2,
    )
    if not all(math.isfinite(value) and value > 0.0 for value in scales):
        raise Hwt601ProtocolError('Skalen muessen endlich und positiv sein')

    raw = tuple(signed_int16(int(value)) for value in registers)
    acceleration_factor = (
        acceleration_full_scale_g * gravity_mps2 / 32768.0)
    angular_factor = math.radians(angular_velocity_full_scale_dps) / 32768.0
    return Hwt601Sample(
        raw_acceleration=raw[:3],
        raw_angular_velocity=raw[3:],
        linear_acceleration_mps2=tuple(
            value * acceleration_factor for value in raw[:3]),
        angular_velocity_radps=tuple(
            value * angular_factor for value in raw[3:]),
    )
