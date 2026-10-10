"""Inventory validation and bounded, read-only ESS diagnostics."""
from __future__ import annotations

import argparse
from contextlib import nullcontext
import json
import sys

from arm_hardware.config import ConfigError, configuration_report, load_config
from arm_hardware.probe import make_synthetic_transport, plan_probe, probe_snapshot
from arm_hardware.transport import ReadError, SerialReadTransport


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, help="explicit commissioning JSON path")
    parser.add_argument("--mode", choices=("validate", "fake", "readonly"), default="validate")
    parser.add_argument("--joint", action="append", help="joint name; repeat to select more")
    parser.add_argument("--samples", type=int, default=1, help="1..100 finite snapshots")
    parser.add_argument("--port", help="explicit arm adapter path; no default")
    parser.add_argument("--baudrate", type=int, choices=(9600, 19200, 38400, 57600, 115200))
    parser.add_argument("--parity", choices=("N", "E", "O"))
    parser.add_argument("--stopbits", type=int, choices=(1, 2))
    parser.add_argument("--timeout", type=float, default=0.2)
    parser.add_argument("--confirm-bus-exclusive", action="store_true",
                        help="all other masters stopped; dedicated arm bus confirmed")
    parser.add_argument("--confirm-profile-reviewed", action="store_true",
                        help="ESS17 model, address and manufacturer RO profile checked")
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if not 1 <= args.samples <= 100:
            raise ConfigError("samples must be 1..100")
        config = load_config(args.config)
        serial_options = (
            args.port is not None or args.baudrate is not None
            or args.parity is not None or args.stopbits is not None
            or args.confirm_bus_exclusive or args.confirm_profile_reviewed
        )
        if args.mode != "readonly" and serial_options:
            raise ConfigError("serial options require explicit --mode readonly")
        if args.mode == "validate":
            if args.joint or args.samples != 1:
                raise ConfigError("joint/samples selection requires fake or readonly mode")
            print(json.dumps(configuration_report(config), allow_nan=False))
            return 0
        source = "synthetic" if args.mode == "fake" else "hardware"
        selected = tuple(args.joint or ())
        if args.mode == "fake" and not selected:
            selected = tuple(joint.name for joint in config.joints)
        plan = plan_probe(config, selected, source)
        if args.mode == "readonly":
            if not args.confirm_bus_exclusive or not args.confirm_profile_reviewed:
                raise ConfigError("readonly needs both explicit confirmations")
            if any(value is None for value in (
                    args.port, args.baudrate, args.parity, args.stopbits)):
                raise ConfigError("readonly needs port, baudrate, parity and stopbits")
            transport = SerialReadTransport(
                port=args.port, baudrate=args.baudrate, parity=args.parity,
                stopbits=args.stopbits, timeout_s=args.timeout,
                allowed=plan.allowed_requests,
            )
            context = transport
        else:
            context = nullcontext(make_synthetic_transport(plan))
        with context as transport:
            for _ in range(args.samples):
                report = probe_snapshot(plan, transport)
                print(json.dumps(report, allow_nan=False), flush=True)
                if not report["probe_ok"]:
                    return 1
        return 0
    except (ConfigError, ReadError, OSError, ImportError) as exc:
        print(json.dumps({"error": str(exc), "motion_permitted": False}), file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
