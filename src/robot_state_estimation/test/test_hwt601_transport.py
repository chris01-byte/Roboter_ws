import pytest

from robot_state_estimation.hwt601_protocol import (
    append_crc, Hwt601ModbusException, Hwt601ProtocolError)
from robot_state_estimation.hwt601_transport import (
    Hwt601SerialTransport, Hwt601TransportError)


class FakeSerial:
    instances = []

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.is_open = True
        self.written = []
        registers = (1, 2, 3, 4, 5, 6)
        payload = bytearray((0x50, 0x03, len(registers) * 2))
        for register in registers:
            payload.extend((register >> 8, register & 0xFF))
        self.response = bytearray(append_crc(bytes(payload)))
        self.__class__.instances.append(self)

    def reset_input_buffer(self):
        pass

    def write(self, payload):
        self.written.append(payload)
        return len(payload)

    def flush(self):
        raise AssertionError('Unbounded tcdrain must not be called')

    def read(self, length):
        result = bytes(self.response[:length])
        del self.response[:length]
        return result

    def close(self):
        self.is_open = False


def test_transport_opens_exclusively_and_only_sends_read_request():
    FakeSerial.instances.clear()
    transport = Hwt601SerialTransport(
        '/dev/ttyUSB_HWT601', 115200, 0.03, 0x50,
        serial_factory=FakeSerial)

    transport.open()
    registers = transport.read_motion_registers()
    serial_port = FakeSerial.instances[-1]

    assert serial_port.kwargs['exclusive'] is True
    assert serial_port.kwargs['port'] == '/dev/ttyUSB_HWT601'
    assert serial_port.written == [bytes.fromhex('50 03 00 34 00 06 89 87')]
    assert serial_port.written[0][1] == 0x03
    assert registers == (1, 2, 3, 4, 5, 6)


@pytest.fixture
def link():
    with Hwt601SerialTransport('/dev/ttyUSB_HWT601', 115200, 0.03, 0x50,
                              serial_factory=FakeSerial) as transport:
        yield transport


def test_fragmented_reply_is_reassembled(link):
    original = link._serial.read
    link._serial.read = lambda length: original(min(length, 1))
    assert link.read_motion_registers() == (1, 2, 3, 4, 5, 6)


@pytest.mark.parametrize('header', [b'\x50\x03\xff', b'\x01\x03\x0c',
                                   b'\x55\x51\x00', b'\x50\x84\x01'])
def test_bad_header_rejected_before_reading_payload(link, header):
    link._serial.response = bytearray(header + b'untouched')
    with pytest.raises(Hwt601TransportError):
        link.read_motion_registers()
    assert link._serial.response == b'untouched'


def test_truncated_crc_and_device_exception(link):
    link._serial.response = bytearray(b'\x50\x03\x0c\x00')
    with pytest.raises(Hwt601TransportError):
        link.read_motion_registers()
    link._serial.response = bytearray(append_crc(b'\x50\x83\x02'))
    with pytest.raises(Hwt601ModbusException):
        link.read_motion_registers()
    link._serial.response = bytearray(b'\x50\x03\x0c' + b'\x00' * 14)
    with pytest.raises(Hwt601ProtocolError, match='CRC'):
        link.read_motion_registers()


def test_total_deadline_also_bounds_slow_fragment_stream(link, monkeypatch):
    from robot_state_estimation import hwt601_transport as module
    now = [100.0]
    monkeypatch.setattr(module.time, 'monotonic', lambda: now[0])
    original = link._serial.read

    def slow_read(length):
        now[0] += 0.02
        return original(1)

    link._serial.read = slow_read
    with pytest.raises(Hwt601TransportError):
        link.read_motion_registers()
    assert now[0] < 100.05  # No timeout reset for each of the 17 bytes.


def test_io_and_short_write_fail_closed(link):
    def failed_read(_length):
        raise OSError('USB disconnected')

    link._serial.read = failed_read
    with pytest.raises(Hwt601TransportError, match='Lesefehler'):
        link.read_motion_registers()
    link._serial.write = lambda payload: 2
    with pytest.raises(Hwt601TransportError, match='unvollstaendige'):
        link.read_motion_registers()


@pytest.mark.parametrize('timeout', [0, -1, float('nan'), float('inf')])
def test_bad_timeout_is_rejected(timeout):
    with pytest.raises(ValueError):
        Hwt601SerialTransport('/dev/ttyUSB_HWT601', 115200, timeout, 0x50)


def test_motor_is_refused_before_serial_factory_is_called():
    before = len(FakeSerial.instances)
    link = Hwt601SerialTransport('/dev/ttyUSB_BASE', 115200, 0.03, 0x50,
                                serial_factory=FakeSerial)
    with pytest.raises(Hwt601TransportError, match='Motor'):
        link.open()
    assert len(FakeSerial.instances) == before


def test_known_motor_serial_is_blocked_even_without_alias(tmp_path, monkeypatch):
    from pathlib import Path
    from robot_state_estimation import hwt601_transport as module
    device = tmp_path / 'ttyUSB9/device'
    device.mkdir(parents=True)
    (device / 'serial').write_text('BG03R8RZ\n')
    monkeypatch.setattr(module, 'Path', lambda value: (
        tmp_path if value == '/sys/class/tty' else Path(value)))
    with pytest.raises(Hwt601TransportError, match='Seriennummer'):
        module.check_not_motor_port('/dev/ttyUSB9')
