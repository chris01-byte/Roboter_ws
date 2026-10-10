"""Pinned Modbus/pyserial integration on a Linux pseudo-terminal, no hardware."""
import os
import select
import threading
import unittest

from arm_hardware.transport import ReadRequest, SerialReadTransport


def crc16(data):
    crc = 0xFFFF
    for value in data:
        crc ^= value
        for _ in range(8):
            crc = (crc >> 1) ^ 0xA001 if crc & 1 else crc >> 1
    return crc.to_bytes(2, "little")


@unittest.skipUnless(hasattr(os, "openpty"), "Linux/POSIX pseudo-terminal required")
class SerialPtyTests(unittest.TestCase):
    def test_real_pymodbus_fc03_framing_and_exclusive_port_lifetime(self):
        import serial

        master, slave = os.openpty()
        port = os.ttyname(slave)
        received, errors = [], []

        def peer():
            try:
                frame = b""
                while len(frame) < 8:
                    if not select.select([master], [], [], 3.0)[0]:
                        raise TimeoutError("no test request")
                    frame += os.read(master, 8 - len(frame))
                received.append(frame)
                if frame[:6] != bytes([17, 3, 0, 0, 0, 4]):
                    raise AssertionError(f"unexpected request: {frame!r}")
                if frame[6:] != crc16(frame[:6]):
                    raise AssertionError("bad request CRC")
                data = bytes([17, 3, 8, 0, 5, 0, 2, 0, 17, 0, 0])
                os.write(master, data + crc16(data))
            except Exception as exc:
                errors.append(exc)

        worker = threading.Thread(target=peer, daemon=True)
        worker.start()
        try:
            request = ReadRequest(17, 0, 4)
            with SerialReadTransport(
                    port=port, baudrate=115200, parity="N", stopbits=1,
                    timeout_s=1.0, allowed=(request,)) as transport:
                with self.assertRaises(serial.SerialException):
                    with serial.Serial(port, exclusive=True):
                        pass
                self.assertEqual(transport.read(request), (5, 2, 17, 0))
            with serial.Serial(port, exclusive=True):
                pass
            worker.join(timeout=4.0)
            self.assertFalse(worker.is_alive())
            self.assertFalse(errors, errors)
            self.assertEqual(len(received), 1)
        finally:
            os.close(master)
            os.close(slave)
            worker.join(timeout=4.0)


if __name__ == "__main__":
    unittest.main()
