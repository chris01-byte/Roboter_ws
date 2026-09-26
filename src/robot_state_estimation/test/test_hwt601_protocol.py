import math

import pytest

from robot_state_estimation.hwt601_protocol import (
    Hwt601ModbusException,
    Hwt601ProtocolError,
    append_crc,
    build_read_holding_registers,
    crc16_modbus,
    decode_motion_registers,
    parse_read_holding_response,
)


def _response(address, registers):
    payload = bytearray((address, 0x03, len(registers) * 2))
    for register in registers:
        payload.extend(((register >> 8) & 0xFF, register & 0xFF))
    return append_crc(bytes(payload))


def test_crc_matches_published_modbus_rtu_reference_vector():
    payload = bytes.fromhex('01 03 00 00 00 0a')

    assert crc16_modbus(payload) == 0xCDC5
    assert append_crc(payload) == bytes.fromhex('01 03 00 00 00 0a c5 cd')


def test_hwt601_motion_request_is_exact_and_read_only():
    request = build_read_holding_registers(0x50, 0x34, 6)

    assert request == bytes.fromhex('50 03 00 34 00 06 89 87')
    assert request[1] == 0x03


def test_response_parsing_and_si_conversion_preserve_sensor_axes():
    registers = (0x4000, 0xC000, 0x0000, 0x2000, 0xE000, 0x0000)
    parsed = parse_read_holding_response(
        _response(0x50, registers), 0x50, len(registers))
    sample = decode_motion_registers(parsed)

    assert sample.raw_acceleration == (16384, -16384, 0)
    assert sample.raw_angular_velocity == (8192, -8192, 0)
    assert sample.linear_acceleration_mps2 == pytest.approx(
        (2.0 * 9.80665, -2.0 * 9.80665, 0.0))
    assert sample.angular_velocity_radps == pytest.approx(
        (math.radians(100.0), math.radians(-100.0), 0.0))
    assert sample.saturated() is False


def test_crc_address_length_and_exception_errors_fail_closed():
    valid = _response(0x50, (1, 2, 3, 4, 5, 6))
    bad_crc = valid[:-1] + bytes((valid[-1] ^ 0x01,))
    with pytest.raises(Hwt601ProtocolError, match='CRC'):
        parse_read_holding_response(bad_crc, 0x50, 6)
    with pytest.raises(Hwt601ProtocolError, match='Adresse'):
        parse_read_holding_response(valid, 0x51, 6)
    with pytest.raises(Hwt601ProtocolError, match='Nutzdatenlaenge'):
        parse_read_holding_response(valid, 0x50, 5)

    exception = append_crc(bytes((0x50, 0x83, 0x02)))
    with pytest.raises(Hwt601ModbusException, match='0x02'):
        parse_read_holding_response(exception, 0x50, 6)


def test_saturation_and_invalid_scale_are_not_silently_accepted():
    sample = decode_motion_registers((0x7FFF, 0, 0, 0, 0, 0))
    assert sample.saturated() is True

    with pytest.raises(Hwt601ProtocolError, match='Skalen'):
        decode_motion_registers((0, 0, 0, 0, 0, 0),
                                acceleration_full_scale_g=0.0)
    with pytest.raises(Hwt601ProtocolError, match='6 Bewegungsregister'):
        decode_motion_registers((0, 0, 0))
