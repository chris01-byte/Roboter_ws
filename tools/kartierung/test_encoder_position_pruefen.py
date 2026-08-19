#!/usr/bin/env python3
"""Offline-Tests fuer das strikt lesende ESS23-RS-Pruefwerkzeug."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from encoder_position_pruefen import (
    ENCODER_RESOLUTION_REGISTER, POSITION_REGISTER, SEGMENT_REGISTER,
    WORD_ORDER_REGISTER, MotorConfig, ReadError, SampleFiles,
    calculate_revolution_result, decode_position, delta_u32,
    read_holding_registers_compat, read_motor_config, read_position_sample,
    signed_i16, signed_i32,
)


class Response:
    def __init__(self, registers):
        self.registers = registers

    def isError(self):
        return False


class ReadOnlyClient:
    def __init__(self, values, accepted_keyword='device_id'):
        self.values = values
        self.accepted_keyword = accepted_keyword
        self.calls = []

    def read_holding_registers(self, address, count=1, **kwargs):
        self.calls.append((address, count, kwargs))
        if set(kwargs) != {self.accepted_keyword}:
            raise TypeError('falsches Slave-Schluesselwort')
        return Response(self.values[(kwargs[self.accepted_keyword], address, count)])


class DecodeTests(unittest.TestCase):
    def test_manual_example_position_5000(self):
        self.assertEqual(decode_position((0x0000, 0x1388), 0), 5000)

    def test_reversed_word_order(self):
        self.assertEqual(decode_position((0x5678, 0x1234), 1), 0x12345678)

    def test_signed_values(self):
        self.assertEqual(signed_i32(0xFFFFFFFF), -1)
        self.assertEqual(signed_i32(0x80000000), -2147483648)
        self.assertEqual(signed_i16(0xFFF0), -16)

    def test_delta_handles_wrap_in_both_directions(self):
        self.assertEqual(delta_u32(0xFFFFFFFE, 0x00000003), 5)
        self.assertEqual(delta_u32(0x00000003, 0xFFFFFFFE), -5)

    def test_invalid_word_order_is_never_guessed(self):
        with self.assertRaises(ValueError):
            decode_position((1, 2), 7)


class ModbusReadTests(unittest.TestCase):
    def test_current_pymodbus_device_id(self):
        client = ReadOnlyClient({(2, POSITION_REGISTER, 3): [0, 5, 0]})
        self.assertEqual(
            read_holding_registers_compat(client, POSITION_REGISTER, 3, 2),
            (0, 5, 0))
        self.assertEqual(client.calls, [(POSITION_REGISTER, 3, {'device_id': 2})])

    def test_falls_back_to_slave_and_unit_apis(self):
        values = {(1, POSITION_REGISTER, 3): [0, 5, 0]}
        for accepted, expected in (
                ('slave', ['device_id', 'slave']),
                ('unit', ['device_id', 'slave', 'unit'])):
            client = ReadOnlyClient(values, accepted)
            read_holding_registers_compat(client, POSITION_REGISTER, 3, 1)
            self.assertEqual([next(iter(call[2])) for call in client.calls], expected)

    def test_incomplete_response_is_rejected(self):
        client = ReadOnlyClient({(1, POSITION_REGISTER, 3): [0, 5]})
        with self.assertRaises(ReadError):
            read_holding_registers_compat(client, POSITION_REGISTER, 3, 1)

    def test_config_and_sample_are_only_fc03_reads(self):
        values = {
            (1, SEGMENT_REGISTER, 1): [1000],
            (1, WORD_ORDER_REGISTER, 1): [0],
            (1, ENCODER_RESOLUTION_REGISTER, 1): [4000],
            (1, POSITION_REGISTER, 3): [0, 0x1388, 0xFFF0],
        }
        client = ReadOnlyClient(values)
        config = read_motor_config(client, 1)
        sample = read_position_sample(client, config, 4990)
        self.assertEqual(config, MotorConfig(1, 1000, 0, 4000))
        self.assertEqual(sample.position_raw_u32, 5000)
        self.assertEqual(sample.delta_counts, 10)
        self.assertEqual(sample.speed_rpm, -16)
        self.assertEqual(
            [(address, count) for address, count, _ in client.calls],
            [(SEGMENT_REGISTER, 1), (WORD_ORDER_REGISTER, 1),
             (ENCODER_RESOLUTION_REGISTER, 1), (POSITION_REGISTER, 3)])
        self.assertFalse(hasattr(client, 'write_register'))


class MeasurementAndOutputTests(unittest.TestCase):
    def test_wheel_revolution_converts_through_gearbox(self):
        result = calculate_revolution_result('wheel', 1, 2.0, 10.0, -80000)
        self.assertEqual(result.counts_per_wheel_revolution, 40000.0)
        self.assertEqual(result.counts_per_motor_revolution, 4000.0)

    def test_motor_revolution_converts_to_wheel(self):
        result = calculate_revolution_result('motor', 1, 1.0, 10.0, 4000)
        self.assertEqual(result.counts_per_motor_revolution, 4000.0)
        self.assertEqual(result.counts_per_wheel_revolution, 40000.0)

    def test_csv_and_json_lines_contain_sample(self):
        sample = read_position_sample(
            ReadOnlyClient({(1, POSITION_REGISTER, 3): [0, 5, 0]}),
            MotorConfig(1, 1000, 0, 4000))
        with TemporaryDirectory() as directory:
            csv_path = str(Path(directory) / 'sample.csv')
            json_path = str(Path(directory) / 'sample.jsonl')
            with SampleFiles(csv_path, json_path) as outputs:
                outputs.write(sample)
            csv_text = Path(csv_path).read_text(encoding='utf-8')
            record = json.loads(Path(json_path).read_text(encoding='utf-8'))
            self.assertIn('position_raw_u32', csv_text)
            self.assertIn(',5,', csv_text)
            self.assertEqual(record['position_raw_u32'], 5)


if __name__ == '__main__':
    unittest.main()
