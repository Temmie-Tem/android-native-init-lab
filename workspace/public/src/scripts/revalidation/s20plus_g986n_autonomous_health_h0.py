#!/usr/bin/env python3
"""Dormant exact-target public-health observer closure for S20+ research."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[5]
STATUS = "H0_AUTONOMOUS_PUBLIC_HEALTH_PASS_GO_NOT_ACTIVE"
HEALTH_ACTIVE = False
LIVE_AUTHORITY = False
MECHANICALLY_ACTIVATABLE = False
DURABLE_EVIDENCE_INTEGRATED = False
SCHEMA = "s20plus_g986n_autonomous_public_health_h0_v1"
TARGET = {
    "model": "SM-G986N",
    "device": "y2q",
    "product": "y2qksx",
    "build": "G986NKSS8IYC2",
}
HEX64_RE = re.compile(r"[0-9a-f]{64}\Z")
SHELL_ID_RE = re.compile(r"uid=2000\(shell\) gid=2000\(shell\)(?: [^\x00\r\n]+)?\Z")
EXPECTED_SELF_NORMALIZED_SHA256 = "4f00f4cfcf685f685f96436b3575b87c097d34e0f5282467248f23c16f81ae1b"

SOURCES = {
    "coordinator": {
        "path": ROOT / "workspace/public/src/scripts/revalidation/s20plus_g986n_autonomous_research_coordinator_h0.py",
        "size": 105_904,
        "sha256": "87ad2dcdcf28d33192ca85bca3f440c87fb7609272dadab297f5b3c6397866dd",
    },
    "inventory": {
        "path": ROOT / "workspace/public/src/scripts/revalidation/s20plus_g986n_d0_inventory.py",
        "size": 21_474,
        "sha256": "3c89eaa348ec7a3a06a3ae2a0de227c781c97238b4e8f33e62b6e0bd370eec81",
    },
}

FIXED_TRANSCRIPT = (
    {"ordinal": 1, "argv": ["ADB", "version"], "timeout_sec": 10, "max_bytes": 65536},
    {"ordinal": 2, "argv": ["ADB", "devices", "-l"], "timeout_sec": 10, "max_bytes": 65536},
    {"ordinal": 3, "argv": ["ADB", "-s", "BOUND_SERIAL", "get-devpath"], "timeout_sec": 10, "max_bytes": 65536},
    {"ordinal": 4, "argv": ["ADB", "-s", "BOUND_SERIAL", "exec-out", "sh", "-c", "FIXED_PUBLIC_SNAPSHOT"], "timeout_sec": 20, "max_bytes": 65536},
    {"ordinal": 5, "argv": ["ADB", "-s", "BOUND_SERIAL", "exec-out", "sh", "-c", "FIXED_PUBLIC_SNAPSHOT"], "timeout_sec": 20, "max_bytes": 65536},
    {"ordinal": 6, "argv": ["ADB", "devices", "-l"], "timeout_sec": 10, "max_bytes": 65536},
)


class HealthH0Error(RuntimeError):
    pass


Command = Callable[[list[str], float, int], tuple[int, bytes, bytes]]


def _require_live() -> None:
    if (
        HEALTH_ACTIVE is not True
        or LIVE_AUTHORITY is not True
        or MECHANICALLY_ACTIVATABLE is not True
        or DURABLE_EVIDENCE_INTEGRATED is not True
    ):
        raise HealthH0Error("autonomous public-health observer is dormant")


def _metadata(value: os.stat_result) -> tuple[int, ...]:
    return (
        value.st_dev,
        value.st_ino,
        value.st_mode,
        value.st_nlink,
        value.st_uid,
        value.st_gid,
        value.st_size,
        value.st_mtime_ns,
        value.st_ctime_ns,
    )


def _read_exact_source(spec: dict[str, Any], label: str) -> bytes:
    if label not in SOURCES or spec != SOURCES[label]:
        raise HealthH0Error("source request is not allowlisted")
    path = Path(spec["path"])
    descriptor = -1
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
        before = os.fstat(descriptor)
        if (
            not stat.S_ISREG(before.st_mode)
            or before.st_nlink != 1
            or before.st_size != spec["size"]
        ):
            raise HealthH0Error(f"{label} source identity differs")
        payload = bytearray()
        while len(payload) < before.st_size:
            chunk = os.read(descriptor, min(1024 * 1024, before.st_size - len(payload)))
            if not chunk:
                break
            payload.extend(chunk)
        if len(payload) != before.st_size or os.read(descriptor, 1):
            raise HealthH0Error(f"{label} source length differs")
        after = os.fstat(descriptor)
        if _metadata(before) != _metadata(after):
            raise HealthH0Error(f"{label} source changed during read")
    except OSError as exc:
        raise HealthH0Error(f"{label} source is unavailable") from exc
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    result = bytes(payload)
    if hashlib.sha256(result).hexdigest() != spec["sha256"]:
        raise HealthH0Error(f"{label} source bytes changed")
    return result


def _load_inventory() -> tuple[Callable[[], dict[str, Any]], dict[str, Any]]:
    payload = _read_exact_source(SOURCES["inventory"], "inventory")
    name = "_s20plus_autonomous_health_bound_inventory"
    spec = importlib.util.spec_from_loader(name, loader=None, origin=str(SOURCES["inventory"]["path"]))
    if spec is None:
        raise HealthH0Error("inventory module spec is unavailable")
    module = importlib.util.module_from_spec(spec)
    module.__file__ = str(SOURCES["inventory"]["path"])
    exec(compile(payload, module.__file__, "exec"), module.__dict__)
    if (
        module.EXPECTED_MODEL != TARGET["model"]
        or module.MAX_TEXT_BYTES != 64 * 1024
        or module.DEFAULT_ADB != Path("/usr/bin/adb")
    ):
        raise HealthH0Error("inventory execution contract differs")
    contract = {
        "schema": module.SCHEMA,
        "version": module.VERSION,
        "verdict": module.VERDICT,
        "property_keys": tuple(module.PROPERTY_KEYS),
        "expected_adb_path": str(module.EXPECTED_ADB_REALPATH),
    }

    def bound_observe() -> dict[str, Any]:
        _require_live()
        return module.collect(command=module.bounded_command)

    return bound_observe, contract


_BOUND_OBSERVE, INVENTORY_CONTRACT = _load_inventory()


def _self_receipt() -> dict[str, Any]:
    path = Path(__file__).resolve()
    descriptor = -1
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or before.st_size > 2 * 1024 * 1024:
            raise HealthH0Error("observer source identity differs")
        data = bytearray()
        while len(data) < before.st_size:
            chunk = os.read(descriptor, min(1024 * 1024, before.st_size - len(data)))
            if not chunk:
                break
            data.extend(chunk)
        if len(data) != before.st_size or os.read(descriptor, 1):
            raise HealthH0Error("observer source length differs")
        after = os.fstat(descriptor)
        if _metadata(before) != _metadata(after):
            raise HealthH0Error("observer source changed during read")
    except OSError as exc:
        raise HealthH0Error("observer source is unavailable") from exc
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    payload = bytes(data)
    normalized = re.sub(
        rb'EXPECTED_SELF_NORMALIZED_SHA256 = "[0-9a-f]{64}"',
        b'EXPECTED_SELF_NORMALIZED_SHA256 = "' + b"0" * 64 + b'"',
        payload,
        count=1,
    )
    normalized_sha256 = hashlib.sha256(normalized).hexdigest()
    if EXPECTED_SELF_NORMALIZED_SHA256 != "0" * 64 and normalized_sha256 != EXPECTED_SELF_NORMALIZED_SHA256:
        raise HealthH0Error("observer normalized source identity differs")
    return {
        "path": str(path),
        "size": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "normalized_sha256": normalized_sha256,
    }


def source_receipts() -> dict[str, Any]:
    result = {"observer": _self_receipt()}
    for label, spec in SOURCES.items():
        payload = _read_exact_source(spec, label)
        result[label] = {
            "path": str(spec["path"]),
            "size": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest(),
        }
    return result


def _require_hex(value: Any, label: str) -> str:
    if type(value) is not str or HEX64_RE.fullmatch(value) is None:
        raise HealthH0Error(f"{label} is not lowercase SHA-256")
    return value


def validate_health_result(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise HealthH0Error("health result is not an object")
    required = {
        "schema", "version", "mode", "target", "properties", "boot_id_sha256",
        "usb_debugging_verified", "adb_authorization_state", "host_tool",
        "host_command_count", "inventory_command_count", "selected_target_command_count",
        "other_target_command_count", "s22plus_command_count", "a90_command_count",
        "device_writes", "root_used", "reboot_requested", "mode_transition_requested",
        "payload_transfer", "partition_access", "d1_authorized", "f1_authorized", "verdict",
    }
    if set(value) != required:
        raise HealthH0Error("health result keys differ")
    if value["schema"] != INVENTORY_CONTRACT["schema"] or value["version"] != INVENTORY_CONTRACT["version"]:
        raise HealthH0Error("health result schema differs")
    if value["mode"] != "connected-read-only" or value["verdict"] != INVENTORY_CONTRACT["verdict"]:
        raise HealthH0Error("health result mode differs")
    target = value["target"]
    if not isinstance(target, dict) or set(target) != {
        "model", "adb_serial_sha256", "usb_topology_sha256", "other_serial_sha256", "inventory_sha256"
    }:
        raise HealthH0Error("health target keys differ")
    if target["model"] != TARGET["model"]:
        raise HealthH0Error("health target model differs")
    for key in ("adb_serial_sha256", "usb_topology_sha256", "inventory_sha256"):
        _require_hex(target[key], f"target.{key}")
    if not isinstance(target["other_serial_sha256"], list) or any(
        _require_hex(item, "other serial") != item for item in target["other_serial_sha256"]
    ):
        raise HealthH0Error("other serial receipts differ")
    properties = value["properties"]
    expected_property_keys = set(INVENTORY_CONTRACT["property_keys"]) - {"boot_id"}
    if not isinstance(properties, dict) or set(properties) != expected_property_keys:
        raise HealthH0Error("health property keys differ")
    fixed = {
        "model": TARGET["model"],
        "device": TARGET["device"],
        "product_name": TARGET["product"],
        "incremental": TARGET["build"],
        "boot_completed": "1",
        "bootanim": "stopped",
        "selinux": "Enforcing",
    }
    if any(properties.get(key) != expected for key, expected in fixed.items()):
        raise HealthH0Error("health property binding differs")
    if properties["build_product"] != TARGET["device"]:
        raise HealthH0Error("health build product differs")
    if (
        f"/{TARGET['product']}/{TARGET['device']}:" not in properties["fingerprint"]
        or not properties["fingerprint"].endswith(":user/release-keys")
    ):
        raise HealthH0Error("health fingerprint differs")
    if SHELL_ID_RE.fullmatch(properties["shell_identity"]) is None:
        raise HealthH0Error("health shell identity differs")
    _require_hex(value["boot_id_sha256"], "boot_id_sha256")
    if value["usb_debugging_verified"] is not True or value["adb_authorization_state"] != "device":
        raise HealthH0Error("ADB health differs")
    counts = {
        "host_command_count": 6,
        "inventory_command_count": 2,
        "selected_target_command_count": 3,
        "other_target_command_count": 0,
        "s22plus_command_count": 0,
        "a90_command_count": 0,
    }
    if any(type(value[key]) is not int or value[key] != expected for key, expected in counts.items()):
        raise HealthH0Error("health command accounting differs")
    for key in (
        "device_writes", "root_used", "reboot_requested", "mode_transition_requested",
        "payload_transfer", "partition_access", "d1_authorized", "f1_authorized",
    ):
        if value[key] is not False:
            raise HealthH0Error("health result crosses the read-only boundary")
    host_tool = value["host_tool"]
    if not isinstance(host_tool, dict) or set(host_tool) != {
        "path", "device", "inode", "mtime_ns", "size", "sha256", "version_output_sha256"
    }:
        raise HealthH0Error("health tool receipt differs")
    for key in ("device", "inode", "mtime_ns", "size"):
        if type(host_tool[key]) is not int or host_tool[key] < 0:
            raise HealthH0Error("health tool integer receipt differs")
    _require_hex(host_tool["sha256"], "host_tool.sha256")
    _require_hex(host_tool["version_output_sha256"], "host_tool.version_output_sha256")
    if host_tool["path"] != INVENTORY_CONTRACT["expected_adb_path"]:
        raise HealthH0Error("health tool path differs")
    return value


def observe_once() -> dict[str, Any]:
    _require_live()
    source_receipts()
    result = _BOUND_OBSERVE()
    return validate_health_result(result)


def render_plan() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": STATUS,
        "active": HEALTH_ACTIVE,
        "live_authority": LIVE_AUTHORITY,
        "mechanically_activatable": MECHANICALLY_ACTIVATABLE,
        "durable_evidence_integrated": DURABLE_EVIDENCE_INTEGRATED,
        "cli": ["--render-plan"],
        "target": TARGET,
        "sources": source_receipts(),
        "fixed_transcript": list(FIXED_TRANSCRIPT),
        "device_commands": [],
        "device_effects": [],
        "root_commands": [],
        "partition_transfers": [],
        "next_gates": [
            "strict-private-raw-evidence-owner",
            "campaign-read-and-byte-accounting",
            "coordinator-consumer-integration",
            "independent-review",
            "mechanical-activation",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--render-plan", action="store_true")
    args = parser.parse_args()
    if not args.render_plan:
        parser.error("only --render-plan is available while dormant")
    print(json.dumps(render_plan(), indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
