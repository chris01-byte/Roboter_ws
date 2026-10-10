"""FC03-only adapter and deterministic fake. Serial connection is an explicit separate context.

Register addresses in SYNTHETIC_PROFILE are test fixtures, NOT an ESS map.
The documented ESS17 profile needs explicit physical identity confirmation.
This module cannot enable or stop a motor.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class ReadError(RuntimeError):
    """No trustworthy sample available."""


@dataclass(frozen=True)
class ReadBlock:
    name: str
    address: int
    count: int


@dataclass(frozen=True)
class ReadProfile:
    profile_id: str
    motor_model: str
    firmware: str
    blocks: tuple[ReadBlock, ...]


SYNTHETIC_PROFILE = ReadProfile(
    "synthetic-v1", "SYNTHETIC-ESS", "fixture-v1",
    (ReadBlock("position_words", 0x1000, 2), ReadBlock("status_word", 0x1010, 1)),
)


@dataclass(frozen=True)
class ReadRequest:
    device_id: int
    address: int
    count: int


def validate_request(request: ReadRequest):
    if type(request.device_id) is not int or not 1 <= request.device_id <= 247:
        raise ReadError("device_id must be 1..247; broadcast is forbidden")
    if type(request.address) is not int or not 0 <= request.address <= 65535:
        raise ReadError("invalid register address")
    if type(request.count) is not int or not 1 <= request.count <= 125:
        raise ReadError("invalid FC03 register count")
    if request.address + request.count > 65536:
        raise ReadError("read crosses register address space")


def validate_words(words, count):
    if not isinstance(words, (list, tuple)) or len(words) != count:
        raise ReadError("missing or incomplete register response")
    if any(type(word) is not int or not 0 <= word <= 65535 for word in words):
        raise ReadError("register words must be unsigned 16-bit integers")
    return tuple(words)


class ReadTransport(Protocol):
    source: str

    def read(self, request: ReadRequest) -> tuple[int, ...]:
        ...


class Fc03Adapter:
    """Wrap an already supplied client; expose only exact allowlisted reads.

    Intentionally no connect(), close(), writes, API-version fallback or retries.
    The future bus owner must manage lifetime/exclusivity. This adapter by itself
    is not approval to use an arbitrary client or profile on real hardware.
    """

    source = "injected_client"

    def __init__(self, client, allowed: tuple[ReadRequest, ...]):
        if not allowed:
            raise ReadError("empty read allowlist")
        for request in allowed:
            validate_request(request)
        self._client = client
        self._allowed = frozenset(allowed)

    def read(self, request):
        validate_request(request)
        if request not in self._allowed:
            raise ReadError("request is not in the exact read allowlist")
        try:
            response = self._client.read_holding_registers(
                request.address, count=request.count, device_id=request.device_id,
            )
        except Exception as exc:
            raise ReadError(f"FC03 transaction failed: {type(exc).__name__}: {exc}") from exc
        if response is None or not callable(getattr(response, "isError", None)):
            raise ReadError("invalid Modbus response")
        try:
            if response.isError() or getattr(response, "function_code", None) != 3:
                raise ReadError("Modbus exception or unexpected function code")
            if getattr(response, "dev_id", None) != request.device_id:
                raise ReadError("response from unexpected device")
            return validate_words(getattr(response, "registers", None), request.count)
        except ReadError:
            raise
        except Exception as exc:
            raise ReadError(f"invalid response: {type(exc).__name__}") from exc


class FakeTransport:
    """Explicit synthetic fixtures; missing requests fail instead of returning zero."""

    source = "synthetic"

    def __init__(self, fixtures):
        self._fixtures = dict(fixtures)
        self.calls: list[ReadRequest] = []

    def read(self, request):
        validate_request(request)
        self.calls.append(request)
        if request not in self._fixtures:
            raise ReadError("missing synthetic fixture")
        result = self._fixtures[request]
        if isinstance(result, Exception):
            raise ReadError(f"synthetic failure: {result}") from result
        return validate_words(result, request.count)


# STEPPERONLINE Modbus Series Bus Product Function Manual V1.0, 2025-03-05,
# chapter 3.2.1 (printed p5), ESS-RS appendix 2 (printed pp66-67):
# FC03, <=16 words. Only documented RO blocks; no commands, resets or EEPROM.
ESS17_PROFILE = ReadProfile(
    "ess17-rs07-fc03-v1", "ESS17-RS07", "",
    (ReadBlock("identity", 0x0000, 4), ReadBlock("diagnostics", 0x0006, 7)),
)


def _device_path(port):
    import os
    import stat
    from pathlib import Path

    if not isinstance(port, str) or not Path(port).is_absolute():
        raise ReadError("an explicit absolute /dev serial path is required")
    resolved = os.path.realpath(port)
    if not resolved.startswith("/dev/") or not stat.S_ISCHR(os.stat(resolved).st_mode):
        raise ReadError("port must resolve to a character device under /dev")
    return resolved


class SerialReadTransport:
    """Explicit Linux serial lifetime; requires an already validated read allowlist."""

    source = "hardware"

    def __init__(self, *, port, baudrate, parity, stopbits, timeout_s, allowed):
        import math
        resolved = _device_path(port)
        if type(baudrate) is not int or baudrate not in (
                9600, 19200, 38400, 57600, 115200):
            raise ReadError("unsupported baudrate")
        if parity not in ("N", "E", "O") or type(stopbits) is not int or stopbits not in (1, 2):
            raise ReadError("invalid serial framing")
        if (type(timeout_s) not in (int, float) or not math.isfinite(timeout_s)
                or not 0.05 <= timeout_s <= 2.0):
            raise ReadError("timeout must be finite, 0.05..2 seconds")
        if not allowed:
            raise ReadError("empty read allowlist")
        for request in allowed:
            validate_request(request)
            if (request.address, request.count) not in (
                    (block.address, block.count) for block in ESS17_PROFILE.blocks):
                raise ReadError("live read outside the ESS17 RO profile")
        # Lazy import: config validation, fake runs and --help need no serial stack.
        from importlib.metadata import version
        if version("pymodbus") != "3.14.0" or version("pyserial") != "3.5":
            raise ReadError("install the pinned arm_hardware/requirements-modbus.txt")
        from pymodbus.client import ModbusSerialClient

        self._client = ModbusSerialClient(
            port=resolved, baudrate=baudrate, bytesize=8, parity=parity,
            stopbits=stopbits, timeout=timeout_s, retries=0,
        )
        self._adapter = Fc03Adapter(self._client, allowed)
        self._connected = False

    def __enter__(self):
        try:
            if not self._client.connect():
                raise ReadError("serial connection failed")
            # pymodbus 3.14.0 opens pyserial with exclusive=True on Linux.
            if getattr(self._client.socket, "exclusive", None) is not True:
                raise ReadError("exclusive serial lock not confirmed")
            self._connected = True
            return self
        except BaseException:
            self._client.close()
            raise

    def read(self, request):
        if not self._connected:
            raise ReadError("transport is not connected")
        return self._adapter.read(request)

    def __exit__(self, *_args):
        self._connected = False
        self._client.close()
