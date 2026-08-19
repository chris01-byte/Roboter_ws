#!/usr/bin/env python3
"""ESS23-RS-Encoderposition strikt lesend pruefen.

Das Werkzeug sendet ausschliesslich Modbus-FC03-Leseabfragen. Es schreibt
keine Register, startet keinen Motor und publiziert keine ROS-Fahrbefehle.

Vorher den gesamten Amadeus-Stack beenden, insbesondere ``base_hardware``.
Zwei Modbus-Master duerfen den RS485-Port niemals gemeinsam benutzen.

Live-Anzeige::

    python3 tools/kartierung/encoder_position_pruefen.py \
      --confirm-stack-stopped

Exakte Radumdrehung messen::

    python3 tools/kartierung/encoder_position_pruefen.py \
      --confirm-stack-stopped --measure-wheel 1 --turns 1 --gear-ratio 10

Beim Handtest Roboter sichern und Raeder frei heben. Nicht gegen das Haltemoment
eines aktiven Motors zwingen. Dieses Werkzeug gibt den Motor absichtlich NICHT
per Software frei.
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
import time
from typing import IO, Optional, Sequence

try:
    from pymodbus.client import ModbusSerialClient
except Exception:  # pragma: no cover - Entwicklungsrechner ohne pymodbus
    ModbusSerialClient = None  # type: ignore[assignment,misc]


POSITION_REGISTER = 0x000A
SEGMENT_REGISTER = 0x0011
WORD_ORDER_REGISTER = 0x0019
ENCODER_RESOLUTION_REGISTER = 0x0101


class ReadError(RuntimeError):
    """Eine Leseantwort fehlt, ist fehlerhaft oder unvollstaendig."""


@dataclass(frozen=True)
class MotorConfig:
    motor_id: int
    segment_count: int
    word_order: int
    encoder_resolution: int


@dataclass(frozen=True)
class PositionSample:
    timestamp_utc: str
    monotonic_s: float
    motor_id: int
    position_word_0: int
    position_word_1: int
    position_raw_u32: int
    position_signed_i32: int
    delta_counts: Optional[int]
    speed_raw_u16: int
    speed_rpm: int
    word_order: int
    segment_count: int
    encoder_resolution: int
    read_latency_ms: float


@dataclass(frozen=True)
class RevolutionResult:
    mode: str
    motor_id: int
    turns: float
    gear_ratio: float
    delta_counts: int
    counts_per_measured_revolution: float
    counts_per_motor_revolution: float
    counts_per_wheel_revolution: float


def read_holding_registers_compat(client, address: int, count: int,
                                  motor_id: int) -> tuple[int, ...]:
    """FC03 lesen; pymodbus ``device_id``, ``slave`` und ``unit`` stuetzen."""
    last_type_error = None
    response = None
    for keyword in ('device_id', 'slave', 'unit'):
        try:
            response = client.read_holding_registers(
                address, count=count, **{keyword: motor_id})
            break
        except TypeError as exc:
            last_type_error = exc
    else:
        raise ReadError('Unbekannte pymodbus-API') from last_type_error

    error_method = getattr(response, 'isError', None)
    is_error = bool(error_method()) if callable(error_method) else False
    if response is None or is_error:
        raise ReadError(
            f'Modbus-Lesefehler Motor {motor_id}, Register 0x{address:04X}')
    registers = getattr(response, 'registers', None)
    if registers is None or len(registers) != count:
        actual = 'keine' if registers is None else str(len(registers))
        raise ReadError(
            f'Unvollstaendige Antwort Motor {motor_id}, 0x{address:04X}: '
            f'erwartet {count}, erhalten {actual}')
    return tuple(int(value) & 0xFFFF for value in registers)


def decode_position(words: Sequence[int], word_order: int) -> int:
    """Zwei Worte gemaess ESS23-RS-Register 0x0019 zu uint32 dekodieren."""
    if len(words) != 2:
        raise ValueError('Position braucht genau zwei Registerworte')
    if word_order == 0:  # 0x000A high, 0x000B low
        high, low = words
    elif word_order == 1:
        low, high = words
    else:
        raise ValueError(f'0x0019={word_order}; erwartet 0 oder 1')
    return ((int(high) & 0xFFFF) << 16) | (int(low) & 0xFFFF)


def signed_i32(value: int) -> int:
    value &= 0xFFFFFFFF
    return value - 0x100000000 if value >= 0x80000000 else value


def signed_i16(value: int) -> int:
    value &= 0xFFFF
    return value - 0x10000 if value >= 0x8000 else value


def delta_u32(previous: int, current: int) -> int:
    """Kleinste signed Differenz, auch ueber den uint32-Ueberlauf."""
    return ((current - previous + 0x80000000) & 0xFFFFFFFF) - 0x80000000


def read_motor_config(client, motor_id: int) -> MotorConfig:
    segment = read_holding_registers_compat(client, SEGMENT_REGISTER, 1, motor_id)[0]
    order = read_holding_registers_compat(client, WORD_ORDER_REGISTER, 1, motor_id)[0]
    resolution = read_holding_registers_compat(
        client, ENCODER_RESOLUTION_REGISTER, 1, motor_id)[0]
    if order not in (0, 1):
        raise ReadError(f'Motor {motor_id}: 0x0019={order}; erwartet 0 oder 1')
    if segment <= 0 or resolution <= 0:
        raise ReadError(
            f'Motor {motor_id}: 0x0011={segment}, 0x0101={resolution} unplausibel')
    return MotorConfig(motor_id, segment, order, resolution)


def read_position_sample(client, config: MotorConfig,
                         previous_raw: Optional[int] = None) -> PositionSample:
    """Position und Ist-Drehzahl gemeinsam per FC03 0x000A count=3 lesen."""
    started = time.monotonic()
    words = read_holding_registers_compat(
        client, POSITION_REGISTER, 3, config.motor_id)
    finished = time.monotonic()
    raw = decode_position(words[:2], config.word_order)
    return PositionSample(
        datetime.now(timezone.utc).isoformat(timespec='milliseconds'),
        (started + finished) / 2.0,
        config.motor_id,
        words[0], words[1], raw, signed_i32(raw),
        None if previous_raw is None else delta_u32(previous_raw, raw),
        words[2], signed_i16(words[2]), config.word_order,
        config.segment_count, config.encoder_resolution,
        (finished - started) * 1000.0,
    )


def calculate_revolution_result(mode: str, motor_id: int, turns: float,
                                gear_ratio: float,
                                delta_counts: int) -> RevolutionResult:
    if mode not in ('motor', 'wheel'):
        raise ValueError('mode muss motor oder wheel sein')
    if turns <= 0.0 or gear_ratio <= 0.0:
        raise ValueError('turns und gear_ratio muessen > 0 sein')
    per_measured = abs(delta_counts) / turns
    if mode == 'motor':
        per_motor, per_wheel = per_measured, per_measured * gear_ratio
    else:
        per_motor, per_wheel = per_measured / gear_ratio, per_measured
    return RevolutionResult(
        mode, motor_id, turns, gear_ratio, delta_counts,
        per_measured, per_motor, per_wheel)


class SampleFiles:
    """Optionale CSV- und JSON-Lines-Ausgabe."""

    def __init__(self, csv_path: Optional[str], json_path: Optional[str]):
        self.csv_file: Optional[IO[str]] = None
        self.json_file: Optional[IO[str]] = None
        self.csv_writer = None
        if csv_path:
            self.csv_file = open(csv_path, 'w', newline='', encoding='utf-8')
            self.csv_writer = csv.DictWriter(
                self.csv_file, fieldnames=list(PositionSample.__dataclass_fields__))
            self.csv_writer.writeheader()
        if json_path:
            self.json_file = open(json_path, 'w', encoding='utf-8')

    def write(self, sample: PositionSample) -> None:
        record = asdict(sample)
        if self.csv_writer and self.csv_file:
            self.csv_writer.writerow(record)
            self.csv_file.flush()
        if self.json_file:
            self.json_file.write(json.dumps(record, ensure_ascii=False) + '\n')
            self.json_file.flush()

    def close(self) -> None:
        for handle in (self.csv_file, self.json_file):
            if handle:
                handle.close()

    def __enter__(self):
        return self

    def __exit__(self, _kind, _value, _traceback):
        self.close()


def processes_using_port(port: str) -> list[tuple[int, str]]:
    """Unter Linux vorhandene Besitzer des aufgeloesten Geraetepfads finden."""
    proc = Path('/proc')
    if not proc.is_dir():
        return []
    target = os.path.realpath(port)
    owners = []
    for process in proc.iterdir():
        if not process.name.isdigit() or int(process.name) == os.getpid():
            continue
        try:
            in_use = any(
                os.path.realpath(str(fd)) == target for fd in (process / 'fd').iterdir())
        except (OSError, PermissionError):
            continue
        if not in_use:
            continue
        try:
            command = (process / 'cmdline').read_bytes().replace(
                b'\0', b' ').decode('utf-8', 'replace').strip()
        except OSError:
            command = '<unbekannt>'
        owners.append((int(process.name), command))
    return sorted(owners)


def print_safety_notice() -> None:
    print(
        'SICHERHEIT / BUS-EXKLUSIVITAET:\n'
        '  - Gesamten Amadeus-Stack beenden, insbesondere base_hardware.\n'
        '  - Kein zweites Programm darf den RS485-Port benutzen.\n'
        '  - Dieses Werkzeug liest nur FC03 und sendet keine Motorbefehle.\n'
        '  - Roboter sichern; nicht gegen aktives Haltemoment drehen.\n')


def open_client(args):
    if ModbusSerialClient is None:
        raise RuntimeError('pymodbus fehlt')
    client = ModbusSerialClient(
        port=args.port, baudrate=args.baudrate, bytesize=8, parity='N',
        stopbits=1, timeout=args.timeout, retries=0)
    if not client.connect():
        client.close()
        raise RuntimeError(f'RS485-Port nicht erreichbar: {args.port}')
    return client


def print_config(config: MotorConfig) -> None:
    order = 'high/low' if config.word_order == 0 else 'low/high'
    print(
        f'Motor {config.motor_id}: 0x0011={config.segment_count}, '
        f'0x0019={config.word_order} ({order}), '
        f'0x0101={config.encoder_resolution}')


def print_sample(sample: PositionSample) -> None:
    delta = 'Basis' if sample.delta_counts is None else f'{sample.delta_counts:+d}'
    print(
        f'{sample.timestamp_utc} M{sample.motor_id} '
        f'words={sample.position_word_0:04X}:{sample.position_word_1:04X} '
        f'raw={sample.position_raw_u32:10d} '
        f'signed={sample.position_signed_i32:+11d} '
        f'delta={delta:>11} speed={sample.speed_rpm:+5d} rpm '
        f'FC03={sample.read_latency_ms:5.1f} ms')


def live_loop(client, configs: Sequence[MotorConfig], interval: float,
              sample_limit: int, outputs: SampleFiles) -> None:
    previous: dict[int, int] = {}
    rounds = 0
    while sample_limit == 0 or rounds < sample_limit:
        started = time.monotonic()
        for config in configs:
            sample = read_position_sample(client, config, previous.get(config.motor_id))
            previous[config.motor_id] = sample.position_raw_u32
            print_sample(sample)
            outputs.write(sample)
        rounds += 1
        time.sleep(max(0.0, interval - (time.monotonic() - started)))


def measurement_mode(client, config: MotorConfig, mode: str, turns: float,
                     gear_ratio: float, outputs: SampleFiles,
                     input_fn=input) -> RevolutionResult:
    name = 'Motorwelle' if mode == 'motor' else 'Rad'
    input_fn(f'{name} markieren; fuer STARTPOSITION Enter druecken.')
    start = read_position_sample(client, config)
    print_sample(start)
    outputs.write(start)
    input_fn(f'{name} exakt {turns:g} Umdrehung(en) drehen; dann Enter.')
    end = read_position_sample(client, config, start.position_raw_u32)
    print_sample(end)
    outputs.write(end)
    result = calculate_revolution_result(
        mode, config.motor_id, turns, gear_ratio, end.delta_counts or 0)
    print('\nMESSERGEBNIS (Vorzeichen = Drehrichtung):')
    print(f'  Delta                     : {result.delta_counts:+d} Counts')
    print(f'  Counts/Motorumdrehung     : {result.counts_per_motor_revolution:.3f}')
    print(f'  Counts/Radumdrehung       : {result.counts_per_wheel_revolution:.3f}')
    print('In Gegenrichtung wiederholen; beide Betraege muessen uebereinstimmen.')
    return result


def parse_args(argv: Optional[Sequence[str]] = None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', default='/dev/ttyUSB_BASE')
    parser.add_argument('--baudrate', type=int, default=115200)
    parser.add_argument('--timeout', type=float, default=0.1)
    parser.add_argument('--motor-ids', type=int, nargs='+', default=[1, 2])
    parser.add_argument('--interval', type=float, default=0.1)
    parser.add_argument('--samples', type=int, default=0,
                        help='Leserunden; 0 = bis Strg-C')
    parser.add_argument('--csv', help='optionale CSV-Datei')
    parser.add_argument('--json', help='optionale JSON-Lines-Datei')
    parser.add_argument('--confirm-stack-stopped', action='store_true',
                        help='bestaetigt Stack aus und Port exklusiv frei')
    measure = parser.add_mutually_exclusive_group()
    measure.add_argument('--measure-motor', type=int, metavar='ID')
    measure.add_argument('--measure-wheel', type=int, metavar='ID')
    parser.add_argument('--turns', type=float, default=1.0)
    parser.add_argument('--gear-ratio', type=float, default=10.0)
    args = parser.parse_args(argv)
    if args.timeout <= 0 or args.interval <= 0 or args.samples < 0:
        parser.error('timeout/interval > 0 und samples >= 0 erforderlich')
    if args.turns <= 0 or args.gear_ratio <= 0:
        parser.error('turns und gear-ratio muessen > 0 sein')
    ids = list(args.motor_ids)
    measurement_id = args.measure_motor or args.measure_wheel
    if measurement_id is not None:
        ids.append(measurement_id)
    if any(not 1 <= motor_id <= 247 for motor_id in ids):
        parser.error('Motor-ID muss 1..247 sein')
    return args


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    print_safety_notice()
    if not args.confirm_stack_stopped:
        print('ABBRUCH: Erst Stack stoppen, dann --confirm-stack-stopped.',
              file=sys.stderr)
        return 2
    owners = processes_using_port(args.port)
    if owners:
        print(f'ABBRUCH: {args.port} ist bereits geoeffnet:', file=sys.stderr)
        for pid, command in owners:
            print(f'  PID {pid}: {command}', file=sys.stderr)
        return 2

    measurement_id = args.measure_motor or args.measure_wheel
    motor_ids = [measurement_id] if measurement_id else args.motor_ids
    client = None
    try:
        client = open_client(args)
        configs = [read_motor_config(client, motor_id) for motor_id in motor_ids]
        for config in configs:
            print_config(config)
        with SampleFiles(args.csv, args.json) as outputs:
            if measurement_id:
                mode = 'motor' if args.measure_motor is not None else 'wheel'
                measurement_mode(
                    client, configs[0], mode, args.turns, args.gear_ratio, outputs)
            else:
                live_loop(client, configs, args.interval, args.samples, outputs)
    except KeyboardInterrupt:
        print('\nLesen beendet.')
    except (OSError, RuntimeError, ReadError, ValueError) as exc:
        print(f'FEHLER: {exc}', file=sys.stderr)
        return 1
    finally:
        if client is not None:
            client.close()
    return 0


if __name__ == '__main__':
    sys.exit(main())
