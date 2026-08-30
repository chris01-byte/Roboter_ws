from robot_state_estimation.hwt601_protocol import append_crc
from robot_state_estimation.hwt601_transport import Hwt601SerialTransport


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
        pass

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
