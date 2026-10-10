"""Finite sequential diagnostic snapshots; never commands or joint angles."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import time

from .config import ArmConfig, ConfigError
from .transport import (
    ESS17_PROFILE, FakeTransport, ReadError, ReadRequest, SYNTHETIC_PROFILE,
    validate_words,
)


@dataclass(frozen=True)
class ProbePlan:
    config: ArmConfig
    source: str
    # Joint name, profile id, block name, exact request.
    reads: tuple[tuple[str, str, str, ReadRequest], ...]

    @property
    def allowed_requests(self):
        return tuple(row[3] for row in self.reads)


def plan_probe(config: ArmConfig, selected: tuple[str, ...], source: str) -> ProbePlan:
    if source not in ("hardware", "synthetic") or config.environment != source:
        raise ConfigError("probe source and inventory environment must match")
    if not selected or len(set(selected)) != len(selected):
        raise ConfigError("select at least one distinct joint")
    by_name = {joint.name: joint for joint in config.joints}
    if any(name not in by_name for name in selected):
        raise ConfigError("unknown joint in selection")
    reads = []
    profile = SYNTHETIC_PROFILE if source == "synthetic" else ESS17_PROFILE
    # Validate the entire selection before any port is opened or transaction sent.
    for name in selected:
        joint = by_name[name]
        if (joint.device_id is None or joint.read_profile != profile.profile_id
                or joint.motor_model != profile.motor_model
                or joint.identity_evidence is None):
            raise ConfigError(f"{name}: incomplete identity or unsupported read profile")
        if source == "synthetic" and joint.firmware != profile.firmware:
            raise ConfigError(f"{name}: incompatible synthetic firmware")
        # A real firmware value may be unknown: discovering it is the purpose of M1A.
        for block in profile.blocks:
            reads.append((name, profile.profile_id, block.name,
                          ReadRequest(joint.device_id, block.address, block.count)))
    return ProbePlan(config, source, tuple(reads))


def make_synthetic_transport(plan: ProbePlan) -> FakeTransport:
    if plan.source != "synthetic":
        raise ConfigError("fake data require an explicitly synthetic inventory")
    return FakeTransport({
        request: (0, 100 + index) if request.count == 2 else (0,)
        for index, (_name, _profile, _block, request) in enumerate(plan.reads)
    })


def probe_snapshot(plan: ProbePlan, transport, clock=time.monotonic) -> dict:
    if transport.source != plan.source:
        raise ConfigError("transport source does not match probe plan")
    result = {
        "schema_version": 1, "config_id": plan.config.config_id,
        "config_sha256": plan.config.fingerprint,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "source": transport.source,
        "state": "SIMULATED" if plan.source == "synthetic" else "READ_ONLY",
        "motion_permitted": False, "probe_ok": True, "samples": [],
    }
    for name, profile_id, block_name, request in plan.reads:
        started = clock()
        row = {
            "joint": name, "device_id": request.device_id,
            "profile_id": profile_id, "block": block_name,
            "function_code": 3, "address": request.address, "count": request.count,
            "words": None, "ok": False, "error": None,
        }
        try:
            row["words"] = list(validate_words(transport.read(request), request.count))
            row["ok"] = True
        except ReadError as exc:
            row["error"] = str(exc)
            result["probe_ok"] = False
        row["read_duration_ms"] = max(0.0, (clock() - started) * 1000)
        result["samples"].append(row)
        # A failed transaction ends this snapshot. No stale or invented values.
        if not row["ok"]:
            result["state"] = "DIAGNOSTIC_ERROR"
            return result
    return result
