"""Read-only serial transport for HWT601 Modbus RTU."""

from typing import Optional

from .hwt601_protocol import (
    MOTION_REGISTER_COUNT,
    MOTION_REGISTER_START,
    build_read_holding_registers,
    parse_read_holding_response,
)


class Hwt601TransportError(IOError):
    """The serial link did not return one complete Modbus frame."""


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
        self.device_address = device_address
        self._serial_factory = serial_factory
        self._serial: Optional[object] = None

    @property
    def is_open(self) -> bool:
        return bool(self._serial is not None and self._serial.is_open)

    def open(self) -> None:
        if self.is_open:
            return
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

    def _read_exactly(self, length: int) -> bytes:
        if not self.is_open:
            raise Hwt601TransportError(
                'serielle Schnittstelle ist geschlossen')
        result = bytearray()
        while len(result) < length:
            chunk = self._serial.read(length - len(result))
            if not chunk:
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
        try:
            self._serial.reset_input_buffer()
            written = self._serial.write(request)
            self._serial.flush()
        except Exception as error:
            raise Hwt601TransportError(
                f'Sende-/Empfangsfehler: {error}') from error
        if written != len(request):
            raise Hwt601TransportError(
                f'unvollstaendige Modbus-Anfrage: '
                f'{written}/{len(request)} Bytes')

        header = self._read_exactly(3)
        if header[1] & 0x80:
            frame = header + self._read_exactly(2)
        else:
            frame = header + self._read_exactly(header[2] + 2)
        return parse_read_holding_response(
            frame, self.device_address, MOTION_REGISTER_COUNT)

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, _exc_type, _exc_value, _traceback):
        self.close()
