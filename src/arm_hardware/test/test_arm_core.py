"""Offline contracts: no ROS, no motor and no serial device required."""
import copy
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from arm_hardware.config import ConfigError, configuration_report, load_config, parse_config
from arm_hardware.probe import make_synthetic_transport, plan_probe, probe_snapshot
from arm_hardware.transport import (
    ESS17_PROFILE, FakeTransport, Fc03Adapter, ReadError, ReadRequest,
    SerialReadTransport,
)

CONFIG_DIR = Path(__file__).resolve().parents[2] / "arm_bringup" / "config"


def inventory(filename="synthetic_arm.json"):
    return json.loads((CONFIG_DIR / filename).read_text())


def live_inventory():
    data = inventory("arm_inventory.json")
    data["joints"][0].update(
        motor_model="ESS17-RS07", device_id=17, read_profile="ess17-rs07-fc03-v1",
        identity_evidence="Synthetic unit-test evidence; never a hardware release",
    )
    return data


class InventoryTests(unittest.TestCase):
    def test_unknown_hardware_is_valid_but_not_motion_ready(self):
        config = parse_config(inventory("arm_inventory.json"))
        report = configuration_report(config)
        self.assertTrue(report["inventory_valid"])
        self.assertFalse(report["motion_permitted"])
        self.assertFalse(report["hardware_probe_configured"])
        self.assertEqual(len(report["joints"]), 6)
        self.assertTrue(all(j["missing_measurements"] for j in report["joints"]))
        with self.assertRaises(ConfigError):
            plan_probe(config, ("joint1",), "hardware")

    def test_invalid_addresses_and_duplicate_names_are_rejected(self):
        for address in (0, 248, -1, True, 1.0, "1"):
            with self.subTest(address=address):
                data = inventory()
                data["joints"][0]["device_id"] = address
                with self.assertRaises(ConfigError):
                    parse_config(data)
        for field in ("name", "device_id"):
            data = inventory()
            data["joints"][1][field] = data["joints"][0][field]
            with self.assertRaises(ConfigError):
                parse_config(data)

    def test_invalid_measurements_are_not_silently_defaulted(self):
        for key, value in (
            ("gear_ratio", 0), ("gear_ratio", -1),
            ("feedback_counts_per_motor_rev", True),
            ("command_counts_per_motor_rev", float("nan")),
            ("home_offset_rad", float("inf")), ("direction_sign", 0),
            ("direction_sign", 1.0), ("homing_direction_sign", True),
        ):
            with self.subTest(key=key, value=value):
                data = inventory()
                data["joints"][0]["calibration"][key] = value
                with self.assertRaises(ConfigError):
                    parse_config(data)
        data = inventory()
        data["joints"][0]["calibration"].update(soft_lower_rad=1, soft_upper_rad=1)
        with self.assertRaises(ConfigError):
            parse_config(data)

    def test_typo_keys_empty_evidence_and_wrong_shape_fail(self):
        for mutate in (
            lambda d: d.update(schema_version=True),
            lambda d: d.update(extra="typo"),
            lambda d: d.update(joints=d["joints"][:5]),
            lambda d: d["joints"][0].update(identity_evidence=" "),
            lambda d: d["joints"][0]["calibration"].update(gear_ration=50),
        ):
            data = inventory()
            mutate(data)
            with self.assertRaises(ConfigError):
                parse_config(data)

    def test_duplicate_json_keys_and_nonfinite_json_fail(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "inventory.json"
            for content in ('{"schema_version":1,"schema_version":1}',
                            '{"schema_version":NaN}'):
                path.write_text(content)
                with self.assertRaises(ConfigError):
                    load_config(path)

    def test_fingerprint_stable_across_key_order_but_tracks_measurements(self):
        data = inventory()
        first = parse_config(data)
        reordered = dict(reversed(list(data.items())))
        self.assertEqual(first.fingerprint, parse_config(reordered).fingerprint)
        data["joints"][0]["calibration"]["gear_ratio"] = 10
        self.assertNotEqual(first.fingerprint, parse_config(data).fingerprint)

    def test_live_raw_inventory_does_not_require_counts_or_firmware(self):
        config = parse_config(live_inventory())
        plan = plan_probe(config, ("joint1",), "hardware")
        self.assertEqual(plan.allowed_requests, (
            ReadRequest(17, 0, 4), ReadRequest(17, 6, 7),
        ))
        self.assertIsNone(config.joints[0].firmware)
        self.assertFalse(configuration_report(config)["motion_permitted"])

    def test_unknown_nema23_and_fake_hardware_profile_are_rejected(self):
        for model, profile in (
            ("ESS23-UNKNOWN", ESS17_PROFILE.profile_id),
            ("ESS17-RS07", "synthetic-v1"),
            ("SYNTHETIC-ESS", ESS17_PROFILE.profile_id),
        ):
            data = live_inventory()
            data["joints"][0].update(motor_model=model, read_profile=profile)
            with self.assertRaises(ConfigError):
                plan_probe(parse_config(data), ("joint1",), "hardware")
        with self.assertRaises(ConfigError):
            plan_probe(parse_config(inventory()), ("joint1",), "hardware")

    def test_entire_selection_validated_before_io(self):
        config = parse_config(live_inventory())
        for selection in ((), ("joint7",), ("joint1", "joint1"), ("joint1", "joint2")):
            with self.subTest(selection=selection), self.assertRaises(ConfigError):
                plan_probe(config, selection, "hardware")


class AdapterTests(unittest.TestCase):
    def setUp(self):
        self.request = ReadRequest(17, 0, 4)
        # A client with only FC03: write/connect/execute APIs cannot be called.
        self.client = Mock(spec=["read_holding_registers"])
        self.response = SimpleNamespace(
            registers=[0, 1, 17, 3], function_code=3, dev_id=17, isError=lambda: False)
        self.client.read_holding_registers.return_value = self.response
        self.adapter = Fc03Adapter(self.client, (self.request,))

    def test_exact_fc03_device_id_api(self):
        self.assertEqual(self.adapter.read(self.request), (0, 1, 17, 3))
        self.client.read_holding_registers.assert_called_once_with(
            0, count=4, device_id=17)

    def test_unapproved_blocks_and_broadcast_rejected_before_client_call(self):
        for request in (
            ReadRequest(0, 0, 4), ReadRequest(18, 0, 4), ReadRequest(17, 0, 11),
            ReadRequest(17, 0x27, 1), ReadRequest(True, 0, 4),
            ReadRequest(17, 65535, 2), ReadRequest(17, 0, 0),
        ):
            with self.subTest(request=request), self.assertRaises(ReadError):
                self.adapter.read(request)
        self.client.read_holding_registers.assert_not_called()

    def test_timeout_has_no_retry_or_api_fallback(self):
        for error in (TimeoutError("timeout"), TypeError("wrong API")):
            self.client.reset_mock()
            self.client.read_holding_registers.side_effect = error
            with self.assertRaises(ReadError):
                self.adapter.read(self.request)
            self.assertEqual(self.client.read_holding_registers.call_count, 1)

    def test_error_wrong_function_wrong_id_short_and_invalid_words_fail(self):
        cases = [
            None, object(),
            SimpleNamespace(isError=lambda: True),
            SimpleNamespace(isError=lambda: False, function_code=4),
        ]
        for update in (
            {"registers": [1]}, {"dev_id": 18},
            {"registers": [0, 1, -1, 3]}, {"registers": [0, 1, 65536, 3]},
            {"registers": [0, 1, True, 3]}, {"registers": [0, 1, 2.0, 3]},
        ):
            response = copy.copy(self.response)
            response.__dict__.update(update)
            cases.append(response)
        for response in cases:
            with self.subTest(response=response), self.assertRaises(ReadError):
                self.client.read_holding_registers.return_value = response
                self.adapter.read(self.request)

    def test_pinned_pymodbus_response_contract(self):
        from importlib.metadata import version
        from pymodbus.pdu.register_message import ReadHoldingRegistersResponse
        self.assertEqual(version("pymodbus"), "3.14.0")
        self.client.read_holding_registers.return_value = ReadHoldingRegistersResponse(
            registers=[0, 1, 17, 3], dev_id=17)
        self.assertEqual(self.adapter.read(self.request), (0, 1, 17, 3))


class ProbeTests(unittest.TestCase):
    def setUp(self):
        self.plan = plan_probe(parse_config(inventory()), ("joint1", "joint2"), "synthetic")

    def test_synthetic_result_is_labelled_and_never_motion_ready(self):
        fake = make_synthetic_transport(self.plan)
        report = probe_snapshot(self.plan, fake)
        self.assertTrue(report["probe_ok"])
        self.assertEqual(report["state"], "SIMULATED")
        self.assertEqual(report["source"], "synthetic")
        self.assertFalse(report["motion_permitted"])
        self.assertEqual(len(fake.calls), 4)
        self.assertNotIn("joint_angles", report)
        json.dumps(report, allow_nan=False)

    def test_failure_stops_snapshot_and_never_reuses_a_previous_word(self):
        fake = make_synthetic_transport(self.plan)
        self.assertTrue(probe_snapshot(self.plan, fake)["probe_ok"])
        for result in (TimeoutError("bus"), (), [True, 1]):
            fixtures = {self.plan.allowed_requests[0]: result}
            failed = FakeTransport(fixtures)
            report = probe_snapshot(self.plan, failed)
            self.assertFalse(report["probe_ok"])
            self.assertEqual(report["state"], "DIAGNOSTIC_ERROR")
            self.assertIsNone(report["samples"][0]["words"])
            self.assertEqual(len(failed.calls), 1)

    def test_missing_fixture_does_not_become_zero_feedback(self):
        report = probe_snapshot(self.plan, FakeTransport({}))
        self.assertFalse(report["probe_ok"])
        self.assertIsNone(report["samples"][0]["words"])

    def test_monotonic_duration_is_recorded(self):
        times = iter([1.0, 1.025, 2.0, 2.025, 3.0, 3.025, 4.0, 4.025])
        report = probe_snapshot(
            self.plan, make_synthetic_transport(self.plan), clock=lambda: next(times))
        self.assertAlmostEqual(report["samples"][0]["read_duration_ms"], 25.0)

    def test_hardware_cannot_fall_back_to_fake(self):
        live = plan_probe(parse_config(live_inventory()), ("joint1",), "hardware")
        with self.assertRaises(ConfigError):
            make_synthetic_transport(live)
        with self.assertRaises(ConfigError):
            probe_snapshot(live, FakeTransport({}))


class SerialLifetimeTests(unittest.TestCase):
    def make_transport(self):
        return SerialReadTransport(
            port="/dev/ttyARM_TEST", baudrate=115200, parity="N", stopbits=1,
            timeout_s=0.2, allowed=(ReadRequest(17, 0, 4),))

    def test_no_connect_until_context_and_close_on_success_or_exception(self):
        with patch("arm_hardware.transport._device_path", return_value="/dev/ttyARM_TEST"), \
                patch("pymodbus.client.ModbusSerialClient") as factory:
            client = factory.return_value
            client.connect.return_value = True
            client.socket.exclusive = True
            transport = self.make_transport()
            client.connect.assert_not_called()
            with self.assertRaises(ReadError):
                transport.read(ReadRequest(17, 0, 4))
            for fail in (False, True):
                client.close.reset_mock()
                try:
                    with transport:
                        if fail:
                            raise RuntimeError("caller failed")
                except RuntimeError:
                    pass
                client.close.assert_called_once()
            self.assertEqual(factory.call_args.kwargs["retries"], 0)

    def test_connect_failure_or_missing_exclusivity_closes_client(self):
        with patch("arm_hardware.transport._device_path", return_value="/dev/ttyARM_TEST"), \
                patch("pymodbus.client.ModbusSerialClient") as factory:
            for connected, exclusive in ((False, True), (True, False)):
                client = factory.return_value
                client.connect.return_value = connected
                client.socket.exclusive = exclusive
                client.close.reset_mock()
                with self.assertRaises(ReadError):
                    with self.make_transport():
                        self.fail("must not enter")
                client.close.assert_called_once()

    def test_non_device_port_and_non_profile_block_rejected(self):
        with self.assertRaises(ReadError):
            SerialReadTransport(port="ttyUSB0", baudrate=115200, parity="N",
                                stopbits=1, timeout_s=0.2,
                                allowed=(ReadRequest(17, 0, 4),))
        with patch("arm_hardware.transport._device_path", return_value="/dev/ttyARM_TEST"), \
                patch("pymodbus.client.ModbusSerialClient") as factory:
            for kwargs in (
                {"timeout_s": float("nan")}, {"baudrate": True},
                {"allowed": (ReadRequest(17, 0, 11),)},
            ):
                values = dict(port="/dev/ttyARM_TEST", baudrate=115200, parity="N",
                              stopbits=1, timeout_s=0.2, allowed=(ReadRequest(17, 0, 4),))
                values.update(kwargs)
                with self.assertRaises(ReadError):
                    SerialReadTransport(**values)
            factory.assert_not_called()


if __name__ == "__main__":
    unittest.main()
