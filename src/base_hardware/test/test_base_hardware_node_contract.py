#!/usr/bin/env python3
"""ROS-freie Vertragspruefungen fuer den Node-Adapter.

Die eigentliche Mathematik wird in test_encoder_odometry.py dynamisch getestet.
Hier werden sicherheitskritische Verdrahtungen geprueft, ohne rclpy zu importieren.
"""

import ast
import math
import time
from pathlib import Path
import unittest


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
NODE_PATH = PACKAGE_ROOT / 'base_hardware' / 'base_hardware_node.py'
CONFIG_PATH = PACKAGE_ROOT / 'config' / 'base_hardware_params.yaml'


def method_source(name):
    source = NODE_PATH.read_text(encoding='utf-8')
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return ast.get_source_segment(source, node)
    raise AssertionError(f'Methode {name} fehlt')


def method_class(*names):
    """Kompiliert ausgewaehlte Node-Methoden in eine ROS-freie Testklasse."""
    source = NODE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    wanted = set(names)
    methods = [
        node for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name in wanted]
    if {method.name for method in methods} != wanted:
        raise AssertionError(f'Methoden fehlen: {wanted - {m.name for m in methods}}')
    dummy = ast.ClassDef(
        name="Dummy", bases=[], keywords=[], body=methods, decorator_list=[])

    class AnnotationCommand:
        def __init__(self, *_args):
            self.v_left_mps = 0.0
            self.v_right_mps = 0.0
            self.rpm_left = 0.0
            self.rpm_right = 0.0

    class UpdateResult:
        def __init__(self, *args):
            self.args = args
    namespace = {
        'WheelCommand': AnnotationCommand, 'EncoderUpdate': UpdateResult,
        'time': time, 'math': math, 'Twist': object}
    module = ast.fix_missing_locations(ast.Module(body=[dummy], type_ignores=[]))
    exec(compile(module, str(NODE_PATH), "exec"), namespace)
    return namespace["Dummy"]


class FakeResponse:
    def __init__(self, registers, error=False):
        self.registers = registers
        self.error = error

    def isError(self):
        return self.error


class FakeClient:
    def __init__(self, accepted_keyword="device_id", registers=(1, 2, 3)):
        self.accepted_keyword = accepted_keyword
        self.registers = list(registers)
        self.calls = []

    def read_holding_registers(self, address, count=1, **kwargs):
        key = next(iter(kwargs))
        self.calls.append((address, count, key, kwargs[key]))
        if key != self.accepted_keyword:
            raise TypeError(key)
        return FakeResponse(self.registers)


class Logger:
    def error(self, *_args, **_kwargs):
        pass

    def warn(self, *_args, **_kwargs):
        pass

    def info(self, *_args, **_kwargs):
        pass


class Tracker:
    def __init__(self):
        self.initialized = True
        self.reset_calls = 0

    def reset_baseline(self):
        self.initialized = False
        self.reset_calls += 1


class NodeSafetyContractTests(unittest.TestCase):

    def test_node_source_is_valid_python(self):
        ast.parse(NODE_PATH.read_text(encoding='utf-8'))

    def test_real_update_reads_encoder_before_motion_write(self):
        source = method_source('_update')
        self.assertLess(
            source.index('self._poll_encoder_feedback()'),
            source.index('self._send_rs485_velocity(self.active_wheel_cmd)'),
        )
        self.assertIn('motion_allowed = self._encoder_motion_allowed()', source)

    def test_real_encoder_mode_never_integrates_command(self):
        source = method_source('_update')
        encoder_branch = source.split(
            'elif self.odometry_source == "encoder_position":', 1)[1].split(
                'elif self.feedback_ok', 1)[0]
        self.assertNotIn('_integrate_odom', encoder_branch)
        self.assertIn('_encoder_twist()', encoder_branch)

    def test_position_and_speed_are_one_fc03_block(self):
        source = method_source('_read_motor_feedback')
        self.assertIn(
            'self._read_registers(motor_id, self.encoder_position_register, 3)',
            source,
        )
        read_source = method_source('_read_registers')
        self.assertIn('read_holding_registers', read_source)
        self.assertNotIn('write_register', read_source)

    def test_node_fc03_adapter_supports_all_pymodbus_keywords(self):
        adapter = method_class("_read_registers")
        for keyword in ("device_id", "slave", "unit"):
            with self.subTest(keyword=keyword):
                node = adapter()
                node.modbus_client = FakeClient(keyword, (10, 20, 30))
                node.rs485_ready = True
                node.encoder_connection_initialized = True
                node.encoder_feedback_ok = True
                node.feedback_ok = True
                node.meas_v = 0.0
                node.meas_w = 0.0
                node.encoder_last_failure_reason = ''
                node.modbus_read_failures = 0
                node.encoder_failure_stop_count = 5
                node._handle_bus_read_failure = lambda _reason: None
                self.assertEqual(
                    node._read_registers(2, 0x000A, 3), [10, 20, 30])
                self.assertEqual(
                    node.modbus_client.calls[-1], (0x000A, 3, keyword, 2))

    def test_node_fc03_adapter_rejects_short_response(self):
        adapter = method_class("_read_registers", "_note_modbus_read_failure")
        node = adapter()
        node.modbus_client = FakeClient("device_id", (10, 20))
        node.rs485_ready = True
        node.encoder_connection_initialized = True
        node.encoder_feedback_ok = True
        node.feedback_ok = True
        node.meas_v = 0.0
        node.meas_w = 0.0
        node.encoder_last_failure_reason = ''
        node.modbus_read_failures = 0
        node.encoder_failure_stop_count = 5
        escalated = []
        node._handle_bus_read_failure = escalated.append
        self.assertIsNone(node._read_registers(1, 0x000A, 3))
        self.assertTrue(node.rs485_ready)
        self.assertEqual(node.modbus_read_failures, 1)
        self.assertEqual(escalated, [])

    def test_stop_failure_is_not_recorded_as_success(self):
        adapter = method_class(
            '_stop_both_motors', '_write_motor_stop', '_mark_bus_fault')
        node = adapter()
        node.rs485_ready = True
        node.left_motor_id = 1
        node.right_motor_id = 2
        node.command_register = 0x0027
        node.stop_value = 0x0100
        node.last_sent_left_rpm = 10.0
        node.last_sent_right_rpm = 10.0
        node.encoder_connection_initialized = True
        node.encoder_feedback_ok = True
        node.feedback_ok = True
        node.meas_v = 0.1
        node.meas_w = 0.0
        node.encoder_last_failure_reason = ''
        node.get_logger = lambda: Logger()
        node._write_register = lambda *_args: False

        self.assertFalse(node._stop_both_motors())
        self.assertFalse(node.rs485_ready)
        self.assertNotEqual(node.last_sent_left_rpm, 0.0)
        self.assertNotEqual(node.last_sent_right_rpm, 0.0)
        self.assertEqual(node.encoder_last_failure_reason, 'stop_nicht_bestaetigt')

    def test_setpoints_for_both_motors_precede_any_start(self):
        adapter = method_class(
            '_send_rs485_velocity', '_write_motor_setpoint',
            '_write_motor_start', '_quantize_motor_rpm', '_clamp')
        node = adapter()
        node.rs485_ready = True
        node.last_modbus_write = 0.0
        node.modbus_write_period_s = 0.0
        node.gear_ratio = 1.0
        node.max_motor_rpm = 700.0
        node.left_motor_id = 1
        node.right_motor_id = 2
        node.rpm_scale = 1.0
        node.rpm_register = 0x001D
        node.command_register = 0x0027
        node.velocity_start_value = 2
        node.last_sent_left_rpm = None
        node.last_sent_right_rpm = None
        node._handle_drive_write_failure = lambda stage: self.fail(stage)
        node._command_timed_out = lambda: False  # vor und zwischen Starts
        calls = []
        node._write_register = lambda motor, address, value: (
            calls.append((motor, address, value)) or True)
        command = type('Command', (), {'rpm_left': 10.0, 'rpm_right': 20.0})()

        self.assertTrue(node._send_rs485_velocity(command))
        self.assertEqual(
            [(motor, address) for motor, address, _ in calls],
            [(1, 0x001D), (2, 0x001D), (1, 0x0027), (2, 0x0027)],
        )

    def test_failed_setpoint_never_sends_a_start(self):
        adapter = method_class(
            '_send_rs485_velocity', '_write_motor_setpoint',
            '_write_motor_start', '_quantize_motor_rpm', '_clamp')
        node = adapter()
        node.rs485_ready = True
        node.last_modbus_write = 0.0
        node.modbus_write_period_s = 0.0
        node.gear_ratio = 1.0
        node.max_motor_rpm = 700.0
        node.left_motor_id = 1
        node.right_motor_id = 2
        node.rpm_scale = 1.0
        node.rpm_register = 0x001D
        node.command_register = 0x0027
        node.velocity_start_value = 2
        node.last_sent_left_rpm = None
        node.last_sent_right_rpm = None
        failures = []
        node._command_timed_out = lambda: False
        node._handle_drive_write_failure = failures.append
        calls = []
        node._write_register = lambda motor, address, value: (
            calls.append((motor, address, value)) or False)
        command = type('Command', (), {'rpm_left': 10.0, 'rpm_right': 20.0})()

        self.assertFalse(node._send_rs485_velocity(command))
        self.assertEqual(calls, [(1, 0x001D, 10)])
        self.assertEqual(failures, ['sollwert_links'])

    def test_command_expiring_during_setpoint_writes_never_starts(self):
        adapter = method_class(
            '_send_rs485_velocity', '_write_motor_setpoint',
            '_write_motor_start', '_quantize_motor_rpm', '_clamp')
        node = adapter()
        node.rs485_ready = True
        node.last_modbus_write = 0.0
        node.modbus_write_period_s = 0.0
        node.gear_ratio = 1.0
        node.max_motor_rpm = 700.0
        node.left_motor_id = 1
        node.right_motor_id = 2
        node.rpm_scale = 1.0
        node.rpm_register = 0x001D
        node.command_register = 0x0027
        node.velocity_start_value = 2
        node.last_sent_left_rpm = None
        node.last_sent_right_rpm = None
        node._handle_drive_write_failure = lambda stage: self.fail(stage)
        calls = []
        node._write_register = lambda motor, address, value: (
            calls.append((motor, address, value)) or True)
        stop_calls = []
        node._stop_both_motors = lambda force=False: (
            stop_calls.append(force) or True)
        node._command_timed_out = lambda: True
        command = type('Command', (), {
            'rpm_left': 10.0, 'rpm_right': 20.0})()

        self.assertFalse(node._send_rs485_velocity(command))
        self.assertEqual(
            [(motor, address) for motor, address, _ in calls],
            [(1, 0x001D), (2, 0x001D)],
        )
        self.assertEqual(stop_calls, [True])

        source = method_source('_send_rs485_velocity')
        second_setpoint = source.index(
            'self._write_motor_setpoint(self.right_motor_id, right_rpm)')
        timeout_check = source.index('self._command_timed_out()', second_setpoint)
        self.assertLess(timeout_check, source.index(
            'self._write_motor_start(self.left_motor_id)'))

    def test_command_expiring_between_motor_starts_stops_both(self):
        adapter = method_class(
            '_send_rs485_velocity', '_write_motor_setpoint',
            '_write_motor_start', '_quantize_motor_rpm', '_clamp')
        node = adapter()
        node.rs485_ready = True
        node.last_modbus_write = 0.0
        node.modbus_write_period_s = 0.0
        node.gear_ratio = 1.0
        node.max_motor_rpm = 700.0
        node.left_motor_id = 1
        node.right_motor_id = 2
        node.rpm_scale = 1.0
        node.rpm_register = 0x001D
        node.command_register = 0x0027
        node.velocity_start_value = 2
        node.last_sent_left_rpm = None
        node.last_sent_right_rpm = None
        node._handle_drive_write_failure = lambda stage: self.fail(stage)
        calls = []
        node._write_register = lambda motor, address, value: (
            calls.append((motor, address, value)) or True)
        stop_calls = []
        node._stop_both_motors = lambda force=False: (
            stop_calls.append(force) or True)
        timeout_results = iter((False, True))
        node._command_timed_out = lambda: next(timeout_results)
        command = type('Command', (), {
            'rpm_left': 10.0, 'rpm_right': 20.0})()

        self.assertFalse(node._send_rs485_velocity(command))
        self.assertEqual(
            [(motor, address) for motor, address, _ in calls],
            [(1, 0x001D), (2, 0x001D), (1, 0x0027)],
        )
        self.assertEqual(stop_calls, [True])

        source = method_source('_send_rs485_velocity')
        left_start = source.index('self._write_motor_start(self.left_motor_id)')
        timeout_check = source.index('self._command_timed_out()', left_start)
        self.assertLess(timeout_check, source.index(
            'self._write_motor_start(self.right_motor_id)'))

    def test_partial_client_is_closed_when_connect_raises(self):
        adapter = method_class('_connect_modbus')

        class ExplodingClient:
            instances = []

            def __init__(self, **_kwargs):
                self.closed = False
                self.__class__.instances.append(self)

            def connect(self):
                raise RuntimeError('serial open failed')

            def close(self):
                self.closed = True

        adapter._connect_modbus.__globals__['ModbusSerialClient'] = ExplodingClient
        node = adapter()
        node.modbus_client = None
        node.rs485_port = '/dev/test'
        node.baudrate = 115200
        node.modbus_timeout_s = 0.1
        node.modbus_retries = 0
        node._prepare_encoder_reconnect = lambda: None
        faults = []
        node._mark_bus_fault = faults.append
        node.get_logger = lambda: Logger()

        node._connect_modbus()
        self.assertEqual(len(ExplodingClient.instances), 1)
        self.assertTrue(ExplodingClient.instances[0].closed)
        self.assertEqual(faults, ['rs485_connect_exception'])

    def test_semantic_encoder_config_fault_is_latched_without_reconnect(self):
        adapter = method_class('_latch_encoder_config_fault')

        class ClosableClient:
            def __init__(self):
                self.closed = False

            def close(self):
                self.closed = True

        node = adapter()
        client = ClosableClient()
        node.modbus_client = client
        node.rs485_ready = True
        node.encoder_config_fault_latched = False
        encoder_failures = []
        stops = []
        bus_faults = []
        node._encoder_failure = encoder_failures.append
        node._stop_both_motors = lambda force=False: stops.append(force) or True
        node._mark_bus_fault = bus_faults.append
        node.get_logger = lambda: Logger()

        reason = 'segmentierung_abweichend_von_abnahme'
        node._latch_encoder_config_fault(reason)
        self.assertTrue(node.encoder_config_fault_latched)
        self.assertEqual(encoder_failures, [reason])
        self.assertEqual(stops, [True])
        self.assertEqual(bus_faults, [reason])
        self.assertTrue(client.closed)
        self.assertIsNone(node.modbus_client)
        ensure_source = method_source('_ensure_rs485')
        self.assertLess(
            ensure_source.index('self.encoder_config_fault_latched'),
            ensure_source.index('self._connect_modbus()'),
        )

    def test_watchdog_rechecks_age_after_blocking_bus_work(self):
        adapter = method_class('_command_timed_out')
        clock = type('MonotonicClock', (), {'value': 10.24})()
        adapter._command_timed_out.__globals__['time'] = type(
            'FakeTime', (), {'monotonic': staticmethod(lambda: clock.value)})
        node = adapter()
        node.last_cmd_monotonic = 10.0
        node.cmd_timeout = 0.25
        self.assertFalse(node._command_timed_out())
        clock.value = 10.251
        self.assertTrue(node._command_timed_out())

        update_source = method_source('_update')
        first = update_source.index('self._command_timed_out()')
        second = update_source.index('self._command_timed_out()', first + 1)
        self.assertGreater(second, update_source.index('self._poll_encoder_feedback()'))
        self.assertLess(
            second,
            update_source.index(
                'self._send_rs485_velocity(self.active_wheel_cmd)'),
        )

    def test_manifest_declares_direct_rcl_interfaces_dependency(self):
        manifest = (PACKAGE_ROOT / 'package.xml').read_text(encoding='utf-8')
        self.assertIn('<depend>rcl_interfaces</depend>', manifest)

    def test_verified_ramp_configuration_is_fail_closed(self):
        config = CONFIG_PATH.read_text(encoding='utf-8')
        self.assertIn('accel_ms: 2000', config)
        self.assertIn('decel_ms: 400', config)
        self.assertIn('start_speed_rpm: 5', config)

        ramp_source = method_source('_write_ramps')
        self.assertIn(
            'self._write_register(motor_id, register, value)', ramp_source)
        self.assertIn('return False', ramp_source)
        connect_source = method_source('_connect_modbus')
        self.assertIn('if not self._write_ramps():', connect_source)
        self.assertIn(
            "self._mark_bus_fault('rampen_nicht_bestaetigt')", connect_source)

    def test_new_client_epoch_resets_encoder_baseline(self):
        adapter = method_class('_prepare_encoder_reconnect')
        node = adapter()
        node.encoder_tracker = Tracker()
        node.encoder_connection_initialized = True
        node.encoder_feedback_ok = True
        node.encoder_last_success = 1.0
        node.encoder_last_update = object()
        node.encoder_last_failure_reason = ''
        node.encoder_left_high_word_first = True
        node.encoder_right_high_word_first = True
        node.meas_v = 0.1
        node.meas_w = 0.0
        node.feedback_ok = True

        node._prepare_encoder_reconnect()
        self.assertEqual(node.encoder_tracker.reset_calls, 1)
        self.assertFalse(node.encoder_tracker.initialized)
        self.assertFalse(node.encoder_connection_initialized)
        self.assertIsNone(node.encoder_last_success)
        self.assertIsNone(node.encoder_left_high_word_first)
        self.assertIsNone(node.meas_v)

    def test_encoder_init_returns_feedback_status_not_old_baseline(self):
        source = method_source('_initialize_encoder_feedback')
        self.assertIn('return self.encoder_connection_initialized', source)
        self.assertNotIn('return self.encoder_tracker.initialized', source)

    def test_zero_command_is_routed_to_stop_not_start(self):
        source = method_source('_update')
        self.assertIn('motion_requested', source)
        self.assertLess(
            source.index('not motion_requested'),
            source.index('self._send_rs485_velocity(self.active_wheel_cmd)'),
        )

    def test_repeated_read_errors_escalate_at_configured_threshold(self):
        adapter = method_class('_note_modbus_read_failure')
        node = adapter()
        node.modbus_read_failures = 0
        node.encoder_failure_stop_count = 3
        escalated = []
        node._handle_bus_read_failure = escalated.append

        node._note_modbus_read_failure('read')
        node._note_modbus_read_failure('read')
        self.assertEqual(escalated, [])
        node._note_modbus_read_failure('read')
        self.assertEqual(escalated, ['read'])

    def test_read_transport_fault_attempts_stop_before_reconnect(self):
        source = method_source('_handle_bus_read_failure')
        self.assertIn('self._stop_both_motors(force=True)', source)
        self.assertLess(
            source.index('self._stop_both_motors(force=True)'),
            source.index('self._mark_bus_fault(reason)'),
        )

    def test_encoder_odom_is_only_published_for_new_measurement(self):
        source = method_source('_update')
        self.assertIn('publish_odom = self.encoder_new_measurement', source)
        self.assertIn('self.encoder_new_measurement = False', source)
        self.assertIn('if publish_odom:', source)

    def test_odom_covariance_is_not_falsely_perfect(self):
        source = method_source('_publish_odom')
        self.assertIn('msg.pose.covariance[0]', source)
        self.assertIn('msg.pose.covariance[35]', source)
        self.assertIn('msg.twist.covariance[0]', source)
        self.assertIn('msg.twist.covariance[35]', source)

    def test_primitive_read_does_not_reset_pair_failure_counter(self):
        source = method_source('_read_registers')
        self.assertNotIn('self.modbus_read_failures = 0', source)
        encoder_source = method_source('_poll_encoder_feedback')
        speed_source = method_source('_poll_speed_feedback')
        self.assertIn('self.modbus_read_failures = 0', encoder_source)
        self.assertIn('self.modbus_read_failures = 0', speed_source)

    def test_speed_rollback_is_fail_closed_on_missing_pair(self):
        source = method_source('_update')
        self.assertIn('motion_allowed = self.feedback_ok', source)

    def test_nonfinite_command_is_fail_closed(self):
        source = method_source('_on_cmd_vel')
        self.assertIn('math.isfinite(raw_v)', source)
        self.assertIn('math.isfinite(raw_w)', source)
        self.assertIn('self.active_wheel_cmd = WheelCommand()', source)
        self.assertIn('self.invalid_cmd_count += 1', source)

    def test_motor_deadband_uses_quantized_register_values(self):
        source = method_source('_update')
        self.assertIn('self._quantize_motor_rpm(', source)
        self.assertNotIn('math.isclose(', source)

    def test_watchdog_uses_monotonic_time_and_latest_only_qos(self):
        source = method_source('_update')
        self.assertIn('self._command_timed_out()', source)
        watchdog_source = method_source('_command_timed_out')
        self.assertIn('time.monotonic() - self.last_cmd_monotonic', watchdog_source)
        self.assertLess(source.index('self._send_stop_if_needed()'),
                        source.index('if dt <= 0.0:'))
        validation = method_source('_validate_parameters')
        self.assertIn('self.use_sim_time', validation)
        constructor = method_source('__init__')
        subscription = constructor.split('self.cmd_sub = self.create_subscription', 1)[1]
        self.assertIn('self._on_cmd_vel, 1)', subscription)

    def test_runtime_sim_time_switch_is_rejected_when_motors_are_live(self):
        source = method_source('_guard_runtime_parameters')
        self.assertIn("parameter.name == 'use_sim_time'", source)
        self.assertIn('successful=False', source)
        constructor = method_source('__init__')
        self.assertIn('add_on_set_parameters_callback', constructor)

    def test_zero_command_stop_precedes_feedback_reads(self):
        source = method_source('_update')
        self.assertLess(
            source.index('if not motion_requested:'),
            source.index('self._poll_encoder_feedback()'),
        )

    def test_nonfinite_command_runtime_stops_for_all_nonfinite_inputs(self):
        adapter = method_class('_on_cmd_vel')
        for raw_v, raw_w in (
                (math.nan, 0.0), (math.inf, 0.0), (-math.inf, 0.0),
                (0.0, math.nan), (0.0, math.inf), (0.0, -math.inf)):
            with self.subTest(raw_v=raw_v, raw_w=raw_w):
                node = adapter()
                node.invalid_cmd_count = 0
                node.cmd_v = 1.0
                node.cmd_w = 1.0
                node.get_clock = lambda: type(
                    'Clock', (), {'now': lambda _self: object()})()
                node.get_logger = lambda: Logger()
                message = type('Message', (), {
                    'linear': type('Linear', (), {'x': raw_v})(),
                    'angular': type('Angular', (), {'z': raw_w})(),
                })()
                node._on_cmd_vel(message)
                self.assertEqual(node.invalid_cmd_count, 1)
                self.assertEqual(node.cmd_v, 0.0)
                self.assertEqual(node.cmd_w, 0.0)
                self.assertEqual(node.active_wheel_cmd.rpm_left, 0.0)
                self.assertEqual(node.active_wheel_cmd.rpm_right, 0.0)

    def test_quantized_sub_rpm_command_is_zero(self):
        adapter = method_class('_quantize_motor_rpm', '_clamp')
        node = adapter()
        node.rpm_scale = 1.0
        self.assertEqual(node._quantize_motor_rpm(0.49), 0)
        self.assertEqual(node._quantize_motor_rpm(-0.49), 0)
        self.assertEqual(node._quantize_motor_rpm(0.51), 1)
        self.assertEqual(node._quantize_motor_rpm(-0.51), -1)

    def test_unknown_counts_fail_closed(self):
        source = NODE_PATH.read_text(encoding='utf-8')
        self.assertIn('encoder_counts_per_motor_revolution <= 0.0', source)
        self.assertIn('retries=self.modbus_retries', source)
        self.assertIn('self.encoder_expected_segment <= 0', source)
        self.assertIn('self.encoder_expected_resolution <= 0', source)
        self.assertIn('Zuerst encoder_position_pruefen.py read-only ausfuehren', source)
        config = CONFIG_PATH.read_text(encoding='utf-8')
        self.assertIn('odometry_source: "encoder_position"', config)
        # Bis zum 13.08.2026 standen hier die Inbetriebnahme-Nullen, die den
        # Encoderpfad absichtlich verriegelten. H2 ist seitdem am realen
        # Motorpaar bestanden (aufgebockt, beide Richtungen, vom Nutzer mit
        # genau 5 Radumdrehungen bestaetigt), deshalb stehen jetzt die
        # gemessenen Werte hier. Die fail-closed-Logik im Node oben bleibt
        # unveraendert scharf: Traegt jemand wieder 0 ein, sperrt der Knoten.
        # Diese Zusicherungen nageln das Messergebnis fest - wer die Werte
        # aendert, muss H2 erneut fahren.
        self.assertIn('encoder_counts_per_motor_revolution: 1000.0', config)
        self.assertIn('encoder_expected_segment: 1000', config)
        self.assertIn('encoder_expected_resolution: 4000', config)

    def test_diagnostic_contract_is_visible(self):
        source = method_source('_publish_state')
        for field in (
                'odometry_source', 'encoder_feedback_ok', 'encoder_stale',
                'encoder_position_left_u32', 'encoder_position_right_u32',
                'encoder_delta_left', 'encoder_delta_right',
                'encoder_consecutive_failures', 'encoder_rejected_updates'):
            self.assertIn(repr(field), source)


if __name__ == '__main__':
    unittest.main(verbosity=2)
