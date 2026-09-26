"""Strikt lesender ESS-RS-Encoderpfad fuer die HWT601-Schattenfusion.

Dieses Modul enthaelt den produktiven Modbus-Transport und die ROS-freie
Zustandslogik. Der Transport kennt absichtlich nur Modbus FC03
(``read_holding_registers``). Fahr- und Konfigurationsregister koennen ueber
diese Schnittstelle nicht beschrieben werden.
"""

from __future__ import annotations

import math
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from .encoder_odometry import (
    EncoderOdometry,
    EncoderUpdate,
    MotorFeedback,
    decode_i16,
    decode_position_words,
)


BASE_ALIAS = '/dev/ttyUSB_BASE'
HWT601_ALIAS = '/dev/ttyUSB_HWT601'
BASE_USB_VENDOR_ID = '0403'
BASE_USB_PRODUCT_ID = '6001'
BASE_USB_SERIAL = 'BG03R8RZ'
FC03_READ_WHITELIST = frozenset({
    (0x000A, 3),  # Position high/low und Ist-Drehzahl als atomarer Motorblock
    (0x0011, 1),  # Segment/Subdivision
    (0x0019, 1),  # 32-Bit-Wortfolge
    (0x0101, 1),  # Encoderaufloesung
})


class EncoderShadowError(RuntimeError):
    """Fehler, nach dem keine Encoder-Odometrie publiziert werden darf."""


@dataclass(frozen=True)
class EncoderConfiguration:
    segment: int
    high_word_first: bool
    resolution: int


@dataclass(frozen=True)
class EncoderPair:
    left: MotorFeedback
    right: MotorFeedback


@dataclass(frozen=True)
class EncoderShadowResult:
    """Ergebnis genau einer vollstaendigen linken/rechten Paarprobe."""

    publish: bool
    reason: str
    update: EncoderUpdate


def validate_base_alias(
    port: str,
    *,
    required_alias: str = BASE_ALIAS,
    forbidden_alias: str = HWT601_ALIAS,
    exists: Callable[[str], bool] = os.path.exists,
    realpath: Callable[[str], str] = os.path.realpath,
) -> str:
    """Prueft den festen Motoralias und dessen Trennung vom HWT601-Port.

    Ein beliebiger ``/dev/ttyUSB*``-Name ist absichtlich nicht zulaessig: Ein
    neu nummerierter Adapter darf nie versehentlich als Motorbus gelesen
    werden. Der Rueckgabewert ist das zum Pruefzeitpunkt aufgeloeste Geraet.
    """
    if not isinstance(port, str) or port != required_alias:
        raise EncoderShadowError(
            f'Nur der feste Basisalias {required_alias} ist zulaessig')
    if not exists(required_alias):
        raise EncoderShadowError(f'Basisalias fehlt: {required_alias}')

    resolved = realpath(required_alias)
    if not resolved or resolved == required_alias or not exists(resolved):
        raise EncoderShadowError(
            f'Basisalias ist nicht sicher aufloesbar: {required_alias}')
    if not resolved.startswith('/dev/tty'):
        raise EncoderShadowError(
            f'Basisalias zeigt nicht auf ein TTY-Geraet: {resolved}')

    if not exists(forbidden_alias):
        raise EncoderShadowError(
            f'HWT601-Alias fehlt; Porttrennung nicht pruefbar: '
            f'{forbidden_alias}')
    forbidden_resolved = realpath(forbidden_alias)
    if (
        not forbidden_resolved
        or forbidden_resolved == forbidden_alias
        or not exists(forbidden_resolved)
        or not forbidden_resolved.startswith('/dev/tty')
    ):
        raise EncoderShadowError(
            f'HWT601-Alias ist nicht sicher aufloesbar: {forbidden_alias}')
    if forbidden_resolved == resolved:
        raise EncoderShadowError(
            'Basis- und HWT601-Alias zeigen auf dasselbe Geraet')
    return resolved


def validate_base_usb_identity(
    resolved_port: str,
    *,
    sysfs_tty_root: str = '/sys/class/tty',
) -> None:
    """Verify the exact commissioned FTDI adapter through Linux sysfs."""
    tty_name = Path(resolved_port).name
    if not tty_name.startswith('tty'):
        raise EncoderShadowError('Basisgeraet hat keinen gueltigen TTY-Namen')
    try:
        device_path = (
            Path(sysfs_tty_root) / tty_name / 'device'
        ).resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise EncoderShadowError(
            f'Basis-USB-Identitaet ist nicht aufloesbar: {exc}') from exc

    identity = None
    for candidate in (device_path, *device_path.parents):
        vendor_path = candidate / 'idVendor'
        product_path = candidate / 'idProduct'
        if vendor_path.is_file() and product_path.is_file():
            try:
                identity = (
                    vendor_path.read_text(encoding='ascii').strip().lower(),
                    product_path.read_text(encoding='ascii').strip().lower(),
                    (candidate / 'serial').read_text(
                        encoding='ascii').strip(),
                )
            except OSError as exc:
                raise EncoderShadowError(
                    f'Basis-USB-Identitaet ist unvollstaendig: {exc}') from exc
            break
    if identity is None:
        raise EncoderShadowError(
            'Basis-USB-Identitaet fehlt im sysfs-Elternpfad')
    expected = (
        BASE_USB_VENDOR_ID, BASE_USB_PRODUCT_ID, BASE_USB_SERIAL)
    if identity != expected:
        raise EncoderShadowError(
            'Basisalias ist nicht der abgenommene FTDI-Adapter')


class ReadOnlyModbusTransport:
    """Exklusiver serieller Transport mit ausschliesslich FC03-Lesezugriff.

    ``pymodbus`` oeffnet den seriellen Port in der verwendeten Version mit
    ``exclusive=True``. Vor und direkt nach dem Oeffnen wird die Aliasbindung
    erneut geprueft, damit ein udev-Wechsel nicht unbemerkt auf den HWT-Port
    fuehrt.
    """

    def __init__(
        self,
        *,
        port: str,
        baudrate: int,
        timeout_s: float,
        retries: int,
        client_factory: Callable[..., Any],
        required_alias: str = BASE_ALIAS,
        forbidden_alias: str = HWT601_ALIAS,
        exists: Callable[[str], bool] = os.path.exists,
        realpath: Callable[[str], str] = os.path.realpath,
        identity_validator: Callable[[str], None] = (
            validate_base_usb_identity),
    ) -> None:
        self.port = port
        self.baudrate = int(baudrate)
        self.timeout_s = float(timeout_s)
        self.retries = int(retries)
        self._client_factory = client_factory
        self.required_alias = required_alias
        self.forbidden_alias = forbidden_alias
        self._exists = exists
        self._realpath = realpath
        self._identity_validator = identity_validator
        self._client: Any | None = None
        self.resolved_port: str | None = None
        self.successful_connections = 0
        self.reconnects = 0

    @property
    def connected(self) -> bool:
        if self._client is None:
            return False
        serial_socket = getattr(self._client, 'socket', None)
        return bool(
            serial_socket is not None
            and getattr(serial_socket, 'is_open', None) is True
            and getattr(serial_socket, 'exclusive', None) is True
        )

    def connect(self) -> str:
        if self._client is not None:
            if self.connected and self.resolved_port is not None:
                return self.resolved_port
            # Pymodbus reconnects implicitly from read_holding_registers().
            # The shadow path must instead latch and restart from a fresh,
            # explicitly checked process after any lost serial connection.
            raise EncoderShadowError(
                'Bestehende Basisverbindung ist nicht mehr sicher offen')

        before = validate_base_alias(
            self.port,
            required_alias=self.required_alias,
            forbidden_alias=self.forbidden_alias,
            exists=self._exists,
            realpath=self._realpath,
        )
        self._identity_validator(before)
        client = None
        try:
            client = self._client_factory(
                port=self.port,
                baudrate=self.baudrate,
                bytesize=8,
                parity='N',
                stopbits=1,
                timeout=self.timeout_s,
                retries=self.retries,
            )
            if not client.connect():
                raise EncoderShadowError(
                    f'Basisport nicht exklusiv oeffnbar: {self.port}')
            serial_socket = getattr(client, 'socket', None)
            if (serial_socket is None
                    or getattr(serial_socket, 'is_open', None) is not True
                    or getattr(serial_socket, 'exclusive', None) is not True):
                raise EncoderShadowError(
                    'Basisport wurde nicht nachweislich exklusiv geoeffnet')
            after = validate_base_alias(
                self.port,
                required_alias=self.required_alias,
                forbidden_alias=self.forbidden_alias,
                exists=self._exists,
                realpath=self._realpath,
            )
            self._identity_validator(after)
            if after != before:
                raise EncoderShadowError(
                    'Basisalias wechselte waehrend des Verbindungsaufbaus')
        except Exception as exc:
            if client is not None:
                try:
                    client.close()
                except Exception:
                    pass
            self._client = None
            self.resolved_port = None
            if isinstance(exc, EncoderShadowError):
                raise
            raise EncoderShadowError(
                f'Basisport-Verbindungsfehler: {exc}') from exc

        self._client = client
        self.resolved_port = after
        if self.successful_connections:
            self.reconnects += 1
        self.successful_connections += 1
        return after

    def close(self) -> None:
        client = self._client
        self._client = None
        self.resolved_port = None
        if client is not None:
            client.close()

    def read_holding_registers(
        self, motor_id: int, address: int, count: int,
    ) -> tuple[int, ...]:
        """Liest exakt ``count`` Holding-Register mit Modbus FC03."""
        if not self.connected:
            raise EncoderShadowError('Modbus-Transport ist nicht verbunden')
        current_port = validate_base_alias(
            self.port,
            required_alias=self.required_alias,
            forbidden_alias=self.forbidden_alias,
            exists=self._exists,
            realpath=self._realpath,
        )
        if current_port != self.resolved_port:
            raise EncoderShadowError(
                'Basisalias wechselte nach dem Verbindungsaufbau')
        self._identity_validator(current_port)
        if isinstance(motor_id, bool) or not 1 <= int(motor_id) <= 247:
            raise EncoderShadowError('Motor-ID muss im Bereich 1..247 liegen')
        if isinstance(address, bool) or not 0 <= int(address) <= 0xFFFF:
            raise EncoderShadowError('Registeradresse muss uint16 sein')
        if isinstance(count, bool) or int(count) < 1:
            raise EncoderShadowError('Registeranzahl muss positiv sein')
        if int(address) + int(count) - 1 > 0xFFFF:
            raise EncoderShadowError('Registerbereich ueberschreitet uint16')
        if (int(address), int(count)) not in FC03_READ_WHITELIST:
            raise EncoderShadowError(
                'FC03-Adresse nicht freigegeben: '
                f'0x{int(address):04X}/{count}')

        response = None
        try:
            # Check immediately before the Pymodbus call.  Its public read API
            # otherwise reconnects automatically when ``socket`` is missing.
            if not self.connected:
                raise EncoderShadowError(
                    'Basisverbindung vor FC03-Lesezugriff verloren')
            for keyword in ('device_id', 'slave', 'unit'):
                try:
                    response = self._client.read_holding_registers(
                        int(address),
                        count=int(count),
                        **{keyword: int(motor_id)},
                    )
                except TypeError:
                    continue
                break
            else:
                raise EncoderShadowError(
                    'Unbekannte pymodbus-Adressierungs-API')
        except EncoderShadowError:
            raise
        except Exception as exc:
            raise EncoderShadowError(f'FC03-Leseexception: {exc}') from exc

        if not self.connected:
            raise EncoderShadowError(
                'Basisverbindung waehrend FC03-Lesezugriff verloren')
        try:
            if response is None or response.isError():
                raise EncoderShadowError('Fehlerhafte FC03-Antwort')
            words = tuple(response.registers)
        except EncoderShadowError:
            raise
        except Exception as exc:
            raise EncoderShadowError(
                f'Ungueltige FC03-Antwortstruktur: {exc}') from exc
        if len(words) != int(count):
            raise EncoderShadowError(
                f'Unvollstaendige FC03-Antwort: {len(words)} statt {count}')
        if any(
            isinstance(word, bool) or not isinstance(word, int)
            or not 0 <= word <= 0xFFFF
            for word in words
        ):
            raise EncoderShadowError('Ungueltiges uint16 in FC03-Antwort')
        return words


class EncoderPairReader:
    """Liest ESS-RS-Konfiguration und Encoderwerte als vollstaendige Paare."""

    def __init__(
        self,
        transport: ReadOnlyModbusTransport,
        *,
        left_motor_id: int,
        right_motor_id: int,
        position_register: int,
        segment_register: int,
        word_order_register: int,
        resolution_register: int,
        rpm_scale: float,
    ) -> None:
        self.transport = transport
        self.left_motor_id = int(left_motor_id)
        self.right_motor_id = int(right_motor_id)
        self.position_register = int(position_register)
        self.segment_register = int(segment_register)
        self.word_order_register = int(word_order_register)
        self.resolution_register = int(resolution_register)
        self.rpm_scale = float(rpm_scale)
        self.left_configuration: EncoderConfiguration | None = None
        self.right_configuration: EncoderConfiguration | None = None
        self._left_first = True
        self.last_read_order: list[int] = []
        self.last_read_durations_s: dict[int, float] = {}

    def read_and_validate_configuration(
        self,
        *,
        expected_segment: int,
        expected_word_order: int,
        expected_resolution: int,
    ) -> tuple[EncoderConfiguration, EncoderConfiguration]:
        if expected_word_order not in (0, 1):
            raise EncoderShadowError(
                'Erwartete Encoder-Wortfolge ist ungueltig')
        configurations = []
        for motor_id in (self.left_motor_id, self.right_motor_id):
            segment = self.transport.read_holding_registers(
                motor_id, self.segment_register, 1)[0]
            word_order = self.transport.read_holding_registers(
                motor_id, self.word_order_register, 1)[0]
            resolution = self.transport.read_holding_registers(
                motor_id, self.resolution_register, 1)[0]
            if word_order not in (0, 1):
                raise EncoderShadowError('Ungueltige Encoder-Wortfolge')
            configurations.append(EncoderConfiguration(
                segment=segment,
                high_word_first=(word_order == 0),
                resolution=resolution,
            ))

        left, right = configurations
        if left.segment != right.segment:
            raise EncoderShadowError('Segmentierung links/rechts abweichend')
        if left.high_word_first != right.high_word_first:
            raise EncoderShadowError(
                'Encoder-Wortfolge links/rechts abweichend')
        if left.resolution != right.resolution:
            raise EncoderShadowError(
                'Encoderaufloesung links/rechts abweichend')
        if left.segment != expected_segment:
            raise EncoderShadowError('Segmentierung weicht von H2-Abnahme ab')
        if left.high_word_first != (expected_word_order == 0):
            raise EncoderShadowError(
                'Encoder-Wortfolge weicht von H1-Abnahme ab')
        if left.resolution != expected_resolution:
            raise EncoderShadowError(
                'Encoderaufloesung weicht von H2-Abnahme ab')
        self.left_configuration = left
        self.right_configuration = right
        return left, right

    def read_complete_pair(self) -> EncoderPair:
        if self.left_configuration is None or self.right_configuration is None:
            raise EncoderShadowError(
                'Encoderkonfiguration ist nicht validiert')
        order = (
            (self.left_motor_id, self.left_configuration),
            (self.right_motor_id, self.right_configuration),
        )
        if not self._left_first:
            order = tuple(reversed(order))
        self._left_first = not self._left_first

        samples: dict[int, MotorFeedback] = {}
        self.last_read_order = []
        self.last_read_durations_s = {}
        for motor_id, configuration in order:
            self.last_read_order.append(motor_id)
            read_started = time.monotonic()
            try:
                words = self.transport.read_holding_registers(
                    motor_id, self.position_register, 3)
            finally:
                self.last_read_durations_s[motor_id] = (
                    time.monotonic() - read_started)
            try:
                samples[motor_id] = MotorFeedback(
                    position_u32=decode_position_words(
                        words[:2], configuration.high_word_first),
                    speed_rpm=float(decode_i16(words[2])) / self.rpm_scale,
                )
            except (TypeError, ValueError) as exc:
                raise EncoderShadowError(
                    f'Ungueltige Encoderantwort Motor {motor_id}: '
                    f'{exc}') from exc

        if set(samples) != {self.left_motor_id, self.right_motor_id}:
            raise EncoderShadowError('Encoderpaar ist unvollstaendig')
        return EncoderPair(
            left=samples[self.left_motor_id],
            right=samples[self.right_motor_id],
        )


class EncoderShadowCore:
    """Fail-closed Adapter zwischen Paarleser und ``EncoderOdometry``."""

    def __init__(
        self,
        tracker: EncoderOdometry,
        *,
        max_pair_read_duration_s: float,
    ) -> None:
        if (not math.isfinite(max_pair_read_duration_s)
                or max_pair_read_duration_s <= 0.0):
            raise ValueError(
                'max_pair_read_duration_s muss endlich und > 0 sein')
        self.tracker = tracker
        self.max_pair_read_duration_s = float(max_pair_read_duration_s)
        self.fault_reason: str | None = None
        self.complete_pair_count = 0
        self.published_count = 0
        self.baseline_count = 0
        self.last_pair_duration_s: float | None = None
        self.maximum_pair_duration_s: float | None = None
        self.last_rejected_pair_duration_s: float | None = None
        self.maximum_attempted_pair_duration_s: float | None = None
        self.last_sample_time_s: float | None = None
        self.last_update = EncoderUpdate(False, False, 'noch_keine_probe')
        self.last_pair: EncoderPair | None = None

    @property
    def ready(self) -> bool:
        return self.fault_reason is None and self.tracker.initialized

    def latch_fault(self, reason: str) -> None:
        if self.fault_reason is None:
            self.fault_reason = str(reason)

    def accept_pair(
        self,
        pair: EncoderPair | None,
        *,
        sample_time_s: float,
        pair_read_duration_s: float,
    ) -> EncoderShadowResult:
        if self.fault_reason is not None:
            return EncoderShadowResult(
                False, self.fault_reason, self.last_update)
        if pair is None:
            self.latch_fault('encoderpaar_unvollstaendig')
            return EncoderShadowResult(
                False, self.fault_reason, self.last_update)
        if not math.isfinite(sample_time_s):
            self.latch_fault('ungueltiger_zeitstempel')
            return EncoderShadowResult(
                False, self.fault_reason, self.last_update)
        if math.isfinite(pair_read_duration_s) and pair_read_duration_s >= 0.0:
            if (self.maximum_attempted_pair_duration_s is None
                    or pair_read_duration_s > self.maximum_attempted_pair_duration_s):
                self.maximum_attempted_pair_duration_s = pair_read_duration_s
        if (not math.isfinite(pair_read_duration_s)
                or pair_read_duration_s < 0.0
                or pair_read_duration_s > self.max_pair_read_duration_s):
            self.last_rejected_pair_duration_s = (
                pair_read_duration_s if math.isfinite(pair_read_duration_s)
                else None)
            self.latch_fault('encoderpaar_zeitfenster_ueberschritten')
            return EncoderShadowResult(
                False, self.fault_reason, self.last_update)
        if (self.last_sample_time_s is not None
                and sample_time_s <= self.last_sample_time_s):
            self.latch_fault('nicht_monotoner_zeitstempel')
            return EncoderShadowResult(
                False, self.fault_reason, self.last_update)

        update = self.tracker.update(
            pair.left.position_u32,
            pair.right.position_u32,
            sample_time_s,
        )
        self.last_pair_duration_s = pair_read_duration_s
        if (self.maximum_pair_duration_s is None
                or pair_read_duration_s > self.maximum_pair_duration_s):
            self.maximum_pair_duration_s = pair_read_duration_s
        self.last_sample_time_s = sample_time_s
        self.last_update = update
        self.last_pair = pair
        self.complete_pair_count += 1
        if update.reason == 'baseline_initialisiert':
            self.baseline_count += 1
            return EncoderShadowResult(False, update.reason, update)
        if not update.accepted:
            self.latch_fault(update.reason)
            return EncoderShadowResult(False, self.fault_reason, update)

        self.published_count += 1
        return EncoderShadowResult(True, 'ok', update)


def shadow_status_payload(
    core: EncoderShadowCore,
    *,
    connected: bool,
    configuration_valid: bool,
    port: str,
    resolved_port: str | None,
    left_motor_id: int,
    right_motor_id: int,
    last_feedback_age_s: float | None,
    max_feedback_age_s: float,
    successful_connections: int = 0,
    reconnects: int = 0,
) -> dict[str, Any]:
    """Erzeugt den stabilen Sicherheits-/Diagnosevertrag des Shadow-Nodes."""
    ready = bool(
        connected and configuration_valid and core.ready
        and last_feedback_age_s is not None
        and last_feedback_age_s <= max_feedback_age_s
    )
    return {
        'state': 'fault_latched' if core.fault_reason else (
            'ready' if ready else 'initializing'),
        'ready': ready,
        'source': 'ess23_absolute_fc03',
        'synthetic': False,
        'command_derived': False,
        'shadow_only': True,
        'fusion_ready': False,
        'read_only': True,
        'modbus_function_code': 3,
        'sensor_write_commands': False,
        'actuator_output': False,
        'cmd_vel_subscription': False,
        'publishes_tf': False,
        'connected': bool(connected),
        'configuration_valid': bool(configuration_valid),
        'fault_latched': core.fault_reason is not None,
        'fault_reason': core.fault_reason,
        'port': port,
        'resolved_port': resolved_port,
        'left_motor_id': int(left_motor_id),
        'right_motor_id': int(right_motor_id),
        'complete_pair_count': core.complete_pair_count,
        'published_count': core.published_count,
        'baseline_count': core.baseline_count,
        'rejected': core.tracker.rejected_update_count,
        'successful_connections': int(successful_connections),
        'reconnects': int(reconnects),
        'rebases': core.tracker.rebase_count,
        'x_m': core.tracker.x_m,
        'y_m': core.tracker.y_m,
        'yaw_rad': core.tracker.yaw_rad,
        'last_pair_duration_s': core.last_pair_duration_s,
        'maximum_pair_duration_s': core.maximum_pair_duration_s,
        'last_rejected_pair_duration_s': core.last_rejected_pair_duration_s,
        'maximum_attempted_pair_duration_s': core.maximum_attempted_pair_duration_s,
        'last_feedback_age_s': last_feedback_age_s,
        'max_feedback_age_s': max_feedback_age_s,
        'last_reason': core.last_update.reason,
        'sample_dt_s': core.last_update.sample_dt_s,
        'linear_velocity_mps': core.last_update.linear_velocity_mps,
        'angular_velocity_radps': core.last_update.angular_velocity_radps,
        'left_delta_counts': core.last_update.left_delta_counts,
        'right_delta_counts': core.last_update.right_delta_counts,
        'left_position_u32': (
            core.last_pair.left.position_u32 if core.last_pair else None),
        'right_position_u32': (
            core.last_pair.right.position_u32 if core.last_pair else None),
        'left_speed_rpm': (
            core.last_pair.left.speed_rpm if core.last_pair else None),
        'right_speed_rpm': (
            core.last_pair.right.speed_rpm if core.last_pair else None),
    }
