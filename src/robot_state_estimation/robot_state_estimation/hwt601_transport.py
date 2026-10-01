"""Read-only serial transport for HWT601 Modbus RTU."""

import math
import os
from pathlib import Path
import time
from typing import Optional

from .hwt601_protocol import (
    MOTION_REGISTER_COUNT,
    MOTION_REGISTER_START,
    build_read_holding_registers,
    parse_read_holding_response,
)


class Hwt601TransportError(IOError):
    """The serial link did not return one complete Modbus frame."""

    def __init__(self, message, *, kind='io_or_identity', diagnostic=None):
        super().__init__(message)
        self.kind = kind
        self.diagnostic = dict(diagnostic or {})
        self.hard_fault = kind != 'response_deadline'


def check_not_motor_port(port: str) -> None:
    """Recheck on every reconnect, including when the motor alias is missing."""
    resolved = os.path.realpath(port)
    if port == '/dev/ttyUSB_BASE' or resolved == os.path.realpath(
            '/dev/ttyUSB_BASE'):
        raise Hwt601TransportError('Motor-RS485 ist fuer die IMU gesperrt')
    device = Path('/sys/class/tty') / Path(resolved).name / 'device'
    if device.exists():
        for parent in (device.resolve(), *device.resolve().parents):
            serial_file = parent / 'serial'
            if (serial_file.is_file()
                    and serial_file.read_text().strip() == 'BG03R8RZ'):
                raise Hwt601TransportError('Motor-USB-Seriennummer gesperrt')


class Hwt601SerialTransport:
    """Own one serial port and issue only function-0x03 read requests."""

    def __init__(
            self,
            port: str,
            baud: int,
            timeout_s: float,
            device_address: int,
            serial_factory=None):
        self.port = port
        self.baud = baud
        self.timeout_s = timeout_s
        if not math.isfinite(timeout_s) or timeout_s <= 0.0:
            raise ValueError('timeout_s muss endlich und positiv sein')
        self.device_address = device_address
        self._serial_factory = serial_factory
        self._serial: Optional[object] = None
        self.last_transaction = {}
        self.last_reply_received_monotonic_s = None
        self._bound_identity = None

    def _identity(self):
        path = os.path.realpath(self.port)
        try:
            stat = os.stat(path)
            device = (stat.st_rdev, stat.st_ino)
        except FileNotFoundError:
            device = None
        return path, device

    @property
    def is_open(self) -> bool:
        return bool(self._serial is not None and self._serial.is_open)

    def open(self) -> None:
        if self.is_open:
            return
        check_not_motor_port(self.port)
        factory = self._serial_factory
        if factory is None:
            try:
                import serial
            except ImportError as error:
                raise Hwt601TransportError(
                    'python3-serial fehlt; Paket auf dem Jetson installieren'
                ) from error
            factory = serial.Serial
        try:
            self._serial = factory(
                port=self.port,
                baudrate=self.baud,
                bytesize=8,
                parity='N',
                stopbits=1,
                timeout=self.timeout_s,
                write_timeout=self.timeout_s,
                exclusive=True,
            )
            self._bound_identity = self._identity()
        except Exception as error:
            self._serial = None
            raise Hwt601TransportError(
                f'serielle Schnittstelle {self.port} nicht verfuegbar: '
                f'{error}') from error

    def close(self) -> None:
        serial_port = self._serial
        self._serial = None
        if serial_port is not None:
            try:
                serial_port.close()
            except Exception:
                pass

    def _read_exactly(self, length: int, deadline: float, phase='payload') -> bytes:
        if not self.is_open:
            raise Hwt601TransportError(
                'serielle Schnittstelle ist geschlossen')
        result = bytearray()
        def deadline_error(classification):
            diagnostic = dict(self.last_transaction, phase=phase,
                phase_expected_bytes=length, phase_received_bytes=len(result),
                classification=classification, observed_monotonic_s=time.monotonic())
            self.last_transaction = diagnostic
            return Hwt601TransportError(
                f'Zeitueberschreitung nach {len(result)}/{length} Bytes',
                kind='response_deadline', diagnostic=diagnostic)
        while len(result) < length:
            remaining = deadline - time.monotonic()
            if remaining <= 0.0:
                raise deadline_error('header_missing' if phase == 'header' and not result
                    else 'payload_missing' if not result else 'partial_response')
            self._serial.timeout = remaining
            try:
                chunk = self._serial.read(length - len(result))
            except Exception as error:
                raise Hwt601TransportError(f'Lesefehler: {error}') from error
            result.extend(chunk)
            self.last_transaction[phase + '_received_bytes'] = len(result)
            returned = time.monotonic()
            if returned > deadline or not chunk:
                raise deadline_error(('complete_header_after_deadline' if phase == 'header'
                    else 'complete_response_after_deadline') if len(result) == length
                    else 'header_missing' if phase == 'header' and not result
                    else 'payload_missing' if not result else 'partial_response')
        return bytes(result)

    def read_motion_registers(self):
        if not self.is_open:
            raise Hwt601TransportError(
                'serielle Schnittstelle ist geschlossen')
        if self._identity() != self._bound_identity:
            raise Hwt601TransportError('HWT-Portidentitaet hat sich geaendert')
        request = build_read_holding_registers(
            self.device_address,
            MOTION_REGISTER_START,
            MOTION_REGISTER_COUNT,
        )
        started = time.monotonic()
        deadline = started + self.timeout_s
        self.last_reply_received_monotonic_s = None
        self.last_transaction = dict(started_monotonic_s=started,
            deadline_monotonic_s=deadline, timeout_s=self.timeout_s,
            header_received_bytes=0, payload_received_bytes=0,
            identity_intact=True)
        try:
            self._serial.reset_input_buffer()
            written = self._serial.write(request)
            # No tcdrain()/flush(): it can block without a write timeout.
            # Reading the reply inherently waits for this tiny request to send.
        except Exception as error:
            raise Hwt601TransportError(
                f'Sende-/Empfangsfehler: {error}') from error
        if written != len(request):
            raise Hwt601TransportError(
                f'unvollstaendige Modbus-Anfrage: '
                f'{written}/{len(request)} Bytes')

        header = self._read_exactly(3, deadline, 'header')
        if header[0] != self.device_address or header[1] not in (0x03, 0x83):
            raise Hwt601TransportError('Fremde Adresse/Protokoll im Antwortkopf')
        if header[1] == 0x83:
            frame = header + self._read_exactly(2, deadline)
        else:
            if header[2] != MOTION_REGISTER_COUNT * 2:
                raise Hwt601TransportError('Unerwartete Modbus-Nutzdatenlaenge')
            frame = header + self._read_exactly(header[2] + 2, deadline)
        received = time.monotonic()
        if self._identity() != self._bound_identity:
            raise Hwt601TransportError('HWT-Portidentitaet waehrend Antwort geaendert')
        self.last_reply_received_monotonic_s = received
        registers = parse_read_holding_response(
            frame, self.device_address, MOTION_REGISTER_COUNT)
        finished = time.monotonic()
        self.last_transaction.update(reply_received_monotonic_s=received,
            finished_monotonic_s=finished, frame_bytes=len(frame),
            classification='processing_after_deadline' if finished > deadline else 'complete_on_time')
        if finished > deadline:
            raise Hwt601TransportError('Antwortverarbeitung nach Gesamtfrist',
                kind='response_deadline', diagnostic=self.last_transaction)
        return registers

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, _exc_type, _exc_value, _traceback):
        self.close()
