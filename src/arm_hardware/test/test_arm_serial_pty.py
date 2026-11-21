"""Pinned Modbus/pyserial integration on a Linux pseudo-terminal, no hardware."""
import os
import select
import threading
import time
from types import SimpleNamespace
from unittest.mock import Mock, patch
import unittest

from arm_hardware.transport import ReadError, ReadRequest, SerialReadTransport, _make_serial_client


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


    def test_continuous_foreign_frames_cannot_extend_transaction_deadline(self):
        master, slave = os.openpty()
        port = os.ttyname(slave)
        stop = threading.Event()
        received, errors = [], []

        def peer():
            try:
                if not select.select([master], [], [], 2.0)[0]:
                    raise TimeoutError("no test request")
                received.append(os.read(master, 8))
                # A valid frame for the wrong slave must not reset the read budget.
                payload = bytes([18, 3, 8, 0, 5, 0, 2, 0, 18, 0, 0])
                frame = payload + crc16(payload)
                until = time.monotonic() + 1.5
                while not stop.is_set() and time.monotonic() < until:
                    os.write(master, frame)
                    stop.wait(0.005)
            except Exception as exc:
                errors.append(exc)

        worker = threading.Thread(target=peer, daemon=True)
        worker.start()
        try:
            request = ReadRequest(17, 0, 4)
            with SerialReadTransport(
                    port=port, baudrate=115200, parity="N", stopbits=1,
                    timeout_s=0.12, allowed=(request,)) as transport:
                started = time.monotonic()
                with self.assertRaisesRegex(ReadError, "deadline"):
                    transport.read(request)
                elapsed = time.monotonic() - started
                self.assertLess(elapsed, 1.0)
                self.assertIsNone(transport._client.socket)
                with self.assertRaisesRegex(ReadError, "not connected"):
                    transport.read(request)
            stop.set()
            worker.join(timeout=2.0)
            self.assertFalse(worker.is_alive())
            self.assertFalse(errors, errors)
            self.assertEqual(len(received), 1)
        finally:
            stop.set()
            worker.join(timeout=2.0)
            os.close(master)
            os.close(slave)

    def test_silent_peer_times_out_and_releases_exclusive_lock(self):
        import serial
        master, slave = os.openpty()
        port = os.ttyname(slave)
        try:
            request = ReadRequest(17, 0, 4)
            with SerialReadTransport(
                    port=port, baudrate=115200, parity="N", stopbits=1,
                    timeout_s=0.05, allowed=(request,)) as transport:
                started = time.monotonic()
                with self.assertRaisesRegex(ReadError, "deadline"):
                    transport.read(request)
                self.assertLess(time.monotonic() - started, 1.0)
                with serial.Serial(port, exclusive=True):
                    pass
        finally:
            os.close(master)
            os.close(slave)

    def test_lost_socket_is_not_reopened_by_pymodbus(self):
        master, slave = os.openpty()
        port = os.ttyname(slave)
        try:
            request = ReadRequest(17, 0, 4)
            with SerialReadTransport(
                    port=port, baudrate=115200, parity="N", stopbits=1,
                    timeout_s=0.05, allowed=(request,)) as transport:
                transport._client.close()
                with patch("serial.serial_for_url") as reopen:
                    with self.assertRaises(ReadError):
                        transport.read(request)
                    reopen.assert_not_called()
        finally:
            os.close(master)
            os.close(slave)

    def test_blocked_write_receives_finite_budget_and_no_retry(self):
        import serial
        client = _make_serial_client(port="/dev/UNOPENED_TEST_ONLY", timeout=0.05, retries=0)
        socket = SimpleNamespace(
            is_open=True, in_waiting=0, write_timeout=None, close=Mock(),
        )

        def blocked_write(_request):
            self.assertGreater(socket.write_timeout, 0)
            self.assertLessEqual(socket.write_timeout, 0.05)
            raise serial.SerialTimeoutException("synthetic blocked write")

        socket.write = Mock(side_effect=blocked_write)
        client.socket = socket
        client.begin_transaction(0.05)
        try:
            with self.assertRaises(serial.SerialTimeoutException):
                client.send(b"test")
            socket.write.assert_called_once_with(b"test")
        finally:
            client.end_transaction()
            client.close()


if __name__ == "__main__":
    unittest.main()
