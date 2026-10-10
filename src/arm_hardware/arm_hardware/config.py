"""Strict, partial commissioning inventory; unknown measurements stay None."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
import re


class ConfigError(ValueError):
    """Invalid inventory, distinct from an incomplete but valid inventory."""


CALIBRATION_FIELDS = (
    "gear_ratio", "feedback_counts_per_motor_rev", "command_counts_per_motor_rev",
    "direction_sign", "home_offset_rad", "soft_lower_rad", "soft_upper_rad",
    "max_velocity_rad_s", "max_acceleration_rad_s2", "homing_direction_sign",
)
JOINT_FIELDS = (
    "name", "motor_model", "firmware", "device_id", "read_profile",
    "identity_evidence", "homing_input", "calibration",
)


def _keys(value, expected, label):
    if not isinstance(value, dict) or set(value) != set(expected):
        raise ConfigError(f"{label}: expected exactly {', '.join(expected)}")


def _text(value, label, nullable=False):
    if nullable and value is None:
        return
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(f"{label}: nonempty text required")


def _number(value, label, positive=False):
    try:
        finite = type(value) in (float, int) and math.isfinite(value)
    except OverflowError:
        finite = False
    if not finite:
        raise ConfigError(f"{label}: finite number required")
    if positive and value <= 0:
        raise ConfigError(f"{label}: must be positive")


@dataclass(frozen=True)
class Joint:
    name: str
    motor_model: str | None
    firmware: str | None
    device_id: int | None
    read_profile: str | None
    identity_evidence: str | None
    homing_input: str | None
    calibration: tuple[tuple[str, float | int | None], ...]

    def missing_measurements(self):
        missing = [key for key, value in self.calibration if value is None]
        if self.homing_input is None:
            missing.append("homing_input")
        return missing


@dataclass(frozen=True)
class ArmConfig:
    config_id: str
    environment: str
    fingerprint: str
    joints: tuple[Joint, ...]


def parse_config(data) -> ArmConfig:
    _keys(data, ("schema_version", "config_id", "environment", "joints"), "root")
    if type(data["schema_version"]) is not int or data["schema_version"] != 1:
        raise ConfigError("schema_version: expected integer 1")
    _text(data["config_id"], "config_id")
    if data["environment"] not in ("hardware", "synthetic"):
        raise ConfigError("environment: expected hardware or synthetic")
    if not isinstance(data["joints"], list) or len(data["joints"]) != 6:
        raise ConfigError("joints: exactly six entries required")
    names, addresses, joints = set(), set(), []
    positive_fields = {
        "gear_ratio", "feedback_counts_per_motor_rev", "command_counts_per_motor_rev",
        "max_velocity_rad_s", "max_acceleration_rad_s2",
    }
    for item in data["joints"]:
        _keys(item, JOINT_FIELDS, "joint")
        name = item["name"]
        _text(name, "joint.name")
        if not re.fullmatch(r"[a-zA-Z][a-zA-Z0-9_]*", name) or name in names:
            raise ConfigError("joint.name: invalid or duplicate name")
        names.add(name)
        for key in ("motor_model", "firmware", "read_profile", "identity_evidence",
                    "homing_input"):
            _text(item[key], f"{name}.{key}", nullable=True)
        device_id = item["device_id"]
        if device_id is not None:
            if type(device_id) is not int or not 1 <= device_id <= 247:
                raise ConfigError(f"{name}.device_id: integer 1..247, no broadcast")
            if device_id in addresses:
                raise ConfigError("device_id: duplicate address on the arm bus")
            addresses.add(device_id)
        calibration = item["calibration"]
        _keys(calibration, CALIBRATION_FIELDS, f"{name}.calibration")
        for key, value in calibration.items():
            if value is None:
                continue
            _number(value, f"{name}.{key}", positive=key in positive_fields)
            if key.endswith("direction_sign") and (
                    type(value) is not int or value not in (-1, 1)):
                raise ConfigError(f"{name}.{key}: integer -1 or 1 required")
        lower, upper = calibration["soft_lower_rad"], calibration["soft_upper_rad"]
        if lower is not None and upper is not None and lower >= upper:
            raise ConfigError(f"{name}: soft_lower_rad must be below soft_upper_rad")
        joints.append(Joint(
            **{key: item[key] for key in JOINT_FIELDS if key != "calibration"},
            calibration=tuple((key, calibration[key]) for key in CALIBRATION_FIELDS),
        ))
    canonical = json.dumps(data, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return ArmConfig(
        data["config_id"], data["environment"],
        hashlib.sha256(canonical.encode("utf-8")).hexdigest(), tuple(joints),
    )


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ConfigError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_config(path: str | Path) -> ArmConfig:
    try:
        data = json.loads(
            Path(path).read_text(encoding="utf-8"), object_pairs_hook=_unique_object,
            parse_constant=lambda value: (_ for _ in ()).throw(
                ConfigError(f"non-finite JSON value: {value}")),
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ConfigError(f"cannot load inventory: {exc}") from exc
    return parse_config(data)


def configuration_report(config: ArmConfig) -> dict:
    return {
        "schema_version": 1, "config_id": config.config_id,
        "config_sha256": config.fingerprint, "environment": config.environment,
        "inventory_valid": True, "motion_permitted": False,
        "hardware_probe_configured": any(
            joint.motor_model == "ESS17-RS07" and joint.device_id is not None
            and joint.read_profile == "ess17-rs07-fc03-v1"
            and joint.identity_evidence is not None for joint in config.joints
        ) and config.environment == "hardware",
        "reason": "Inventory validity and read diagnostics never authorize movement",
        "joints": [
            {
                "name": joint.name, "motor_model": joint.motor_model,
                "device_id": joint.device_id,
                "missing_identity": [
                    key for key in ("motor_model", "firmware", "device_id",
                                    "read_profile", "identity_evidence")
                    if getattr(joint, key) is None
                ],
                "missing_measurements": joint.missing_measurements(),
            }
            for joint in config.joints
        ],
    }
