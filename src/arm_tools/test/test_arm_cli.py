"""CLI opt-in, JSON and lifecycle contracts; never touches a serial device."""
from contextlib import redirect_stderr, redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from arm_hardware.transport import ReadError
from arm_tools.cli import main

CONFIG_DIR = Path(__file__).resolve().parents[2] / "arm_bringup" / "config"


class CliTests(unittest.TestCase):
    def invoke(self, args):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = main(args)
        return code, out.getvalue(), err.getvalue()

    def test_default_validation_and_fake_never_create_a_serial_transport(self):
        with patch("arm_tools.cli.SerialReadTransport") as serial:
            code, out, _ = self.invoke(["--config", str(CONFIG_DIR / "arm_inventory.json")])
            self.assertEqual(code, 0)
            self.assertFalse(json.loads(out)["motion_permitted"])
            code, out, _ = self.invoke([
                "--config", str(CONFIG_DIR / "synthetic_arm.json"),
                "--mode", "fake", "--samples", "2"])
            self.assertEqual(code, 0)
            self.assertEqual(len(out.splitlines()), 2)
            self.assertTrue(all(json.loads(line)["source"] == "synthetic"
                                for line in out.splitlines()))
            serial.assert_not_called()

    def test_fake_rejects_real_inventory_and_serial_flags(self):
        with patch("arm_tools.cli.SerialReadTransport") as serial:
            for args in (
                ["--config", str(CONFIG_DIR / "arm_inventory.json"), "--mode", "fake"],
                ["--config", str(CONFIG_DIR / "synthetic_arm.json"),
                 "--mode", "fake", "--port", "/dev/ttyARM_TEST"],
                ["--config", str(CONFIG_DIR / "arm_inventory.json"), "--samples", "0"],
            ):
                code, out, err = self.invoke(args)
                self.assertEqual(code, 2)
                self.assertEqual(out, "")
                self.assertFalse(json.loads(err)["motion_permitted"])
            serial.assert_not_called()

    def test_readonly_unknown_inventory_rejected_before_serial_creation(self):
        with patch("arm_tools.cli.SerialReadTransport") as serial:
            code, _, _ = self.invoke([
                "--config", str(CONFIG_DIR / "arm_inventory.json"), "--mode", "readonly",
                "--joint", "joint1", "--port", "/dev/ttyARM_TEST", "--baudrate", "115200",
                "--parity", "N", "--stopbits", "1", "--confirm-bus-exclusive",
                "--confirm-profile-reviewed"])
            self.assertEqual(code, 2)
            serial.assert_not_called()

    def test_every_live_optin_is_required_and_errors_close_transport(self):
        data = json.loads((CONFIG_DIR / "arm_inventory.json").read_text())
        data["joints"][0].update(
            motor_model="ESS17-RS07", device_id=17, read_profile="ess17-rs07-fc03-v1",
            identity_evidence="Test fixture only")
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "live.json"
            path.write_text(json.dumps(data))
            base = ["--config", str(path), "--mode", "readonly"]
            options = [
                ["--joint", "joint1"], ["--port", "/dev/ttyARM_TEST"],
                ["--baudrate", "115200"], ["--parity", "N"], ["--stopbits", "1"],
                ["--confirm-bus-exclusive"], ["--confirm-profile-reviewed"],
            ]
            with patch("arm_tools.cli.SerialReadTransport") as serial:
                for missing in range(len(options)):
                    args = base + [item for i, pair in enumerate(options)
                                   if i != missing for item in pair]
                    code, _, _ = self.invoke(args)
                    self.assertEqual(code, 2, missing)
                serial.assert_not_called()
                transport = serial.return_value.__enter__.return_value
                transport.source = "hardware"
                transport.read.side_effect = ReadError("timeout")
                code, out, _ = self.invoke(base + [item for pair in options for item in pair])
                self.assertEqual(code, 1)
                self.assertFalse(json.loads(out)["probe_ok"])
                serial.return_value.__exit__.assert_called_once()

    def test_help_does_not_create_serial_transport(self):
        with patch("arm_tools.cli.SerialReadTransport") as serial, \
                redirect_stdout(io.StringIO()), self.assertRaises(SystemExit) as stopped:
            main(["--help"])
        self.assertEqual(stopped.exception.code, 0)
        serial.assert_not_called()


if __name__ == "__main__":
    unittest.main()
