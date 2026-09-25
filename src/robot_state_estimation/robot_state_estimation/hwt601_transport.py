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

    def _read_exactly(self, length: int, deadline: float) -> bytes:
        if not self.is_open:
            raise Hwt601TransportError(
                'serielle Schnittstelle ist geschlossen')
        result = bytearray()
        while len(result) < length:
            remaining = deadline - time.monotonic()
            if remaining <= 0.0:
                raise Hwt601TransportError('Modbus-Gesamtfrist abgelaufen')
            self._serial.timeout = remaining
            try:
                chunk = self._serial.read(length - len(result))
            except Exception as error:
                raise Hwt601TransportError(f'Lesefehler: {error}') from error
            if not chunk or time.monotonic() > deadline:
                raise Hwt601TransportError(
                    f'Zeitueberschreitung nach {len(result)}/{length} Bytes')
            result.extend(chunk)
        return bytes(result)

    def read_motion_registers(self):
        if not self.is_open:
            raise Hwt601TransportError(
                'serielle Schnittstelle ist geschlossen')
        request = build_read_holding_registers(
            self.device_address,
            MOTION_REGISTER_START,
            MOTION_REGISTER_COUNT,
        )
        deadline = time.monotonic() + self.timeout_s
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

        header = self._read_exactly(3, deadline)
        if header[0] != self.device_address or header[1] not in (0x03, 0x83):
            raise Hwt601TransportError('Fremde Adresse/Protokoll im Antwortkopf')
        if header[1] == 0x83:
            frame = header + self._read_exactly(2, deadline)
        else:
            if header[2] != MOTION_REGISTER_COUNT * 2:
                raise Hwt601TransportError('Unerwartete Modbus-Nutzdatenlaenge')
            frame = header + self._read_exactly(header[2] + 2, deadline)
        return parse_read_holding_response(
            frame, self.device_address, MOTION_REGISTER_COUNT)

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, _exc_type, _exc_value, _traceback):
        self.close()
