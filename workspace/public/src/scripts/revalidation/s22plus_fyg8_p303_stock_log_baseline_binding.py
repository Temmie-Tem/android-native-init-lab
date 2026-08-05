#!/usr/bin/env python3
"""Bind one complete working-stock HS-PHY log snapshot to P3.03."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import stat
from typing import Any, Mapping

import s22plus_fyg8_p303_stock_log_baseline as parser
import s22plus_fyg8_p303_telemetry_spec as spec


SCHEMA = "s22plus_fyg8_p303_bound_stock_log_baseline_v1"
VERDICT = "PASS_P303_BOUND_STOCK_HSPHY_LOG_BASELINE_D0"
TARGET = "SM-S906N/g0q/S906NKSS7FYG8"
PROFILE_ID = "s22plus-fyg8"
MANIFEST_ID = "s22plus-fyg8-p303-campaign-1"
LIVE_RUN_ID = "s22plus-fyg8-p303-attempt-1"
RAW_SOURCE = "android-root-dmesg-kernel-ring-snapshot"
CAPTURE_COMMAND = ["adb", "-s", "<exact-s22plus>", "exec-out", "su", "-c", "dmesg"]
MODULE_PATH = "/vendor_dlkm/lib/modules/phy-msm-snps-hs.ko"
MODULE_SHA256 = spec.MODULE_SHA256
MAX_RAW = 16 * 1024 * 1024
MAX_BOOT_START_USEC = 1_000_000
PREFIX = Path("workspace/public/src/scripts/revalidation")
PRODUCER_PATH = PREFIX / "s22plus_fyg8_p303_stock_log_d0.py"
BINDING_PATH = PREFIX / "s22plus_fyg8_p303_stock_log_baseline_binding.py"
PARSER_PATH = PREFIX / "s22plus_fyg8_p303_stock_log_baseline.py"
TIMESTAMP = re.compile(rb"(?m)^(?:<\d+>)?\[\s*(\d+)\.(\d{6})\]")


class BindingError(ValueError):
    pass


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("ascii")


def receipt(payload: bytes) -> dict[str, Any]:
    return {"size": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}


def _read_regular(path: Path, label: str, maximum: int) -> bytes:
    metadata = path.lstat()
    if path.is_symlink() or not stat.S_ISREG(metadata.st_mode):
        raise BindingError(f"{label} is indirect or not regular")
    if metadata.st_size <= 0 or metadata.st_size > maximum:
        raise BindingError(f"{label} size is invalid")
    payload = path.read_bytes()
    after = path.stat()
    if (
        len(payload) != metadata.st_size
        or after.st_dev != metadata.st_dev
        or after.st_ino != metadata.st_ino
        or after.st_size != metadata.st_size
        or after.st_mtime_ns != metadata.st_mtime_ns
        or after.st_ctime_ns != metadata.st_ctime_ns
    ):
        raise BindingError(f"{label} changed while reading")
    return payload


def _source_receipt(root: Path, relative: Path) -> dict[str, Any]:
    return {"path": relative.as_posix(), **receipt(_read_regular(root / relative, relative.name, 1024 * 1024))}


def _relative_private_path(root: Path, path: Path, label: str) -> str:
    absolute = path.absolute()
    try:
        relative = absolute.relative_to(root)
    except ValueError as exc:
        raise BindingError(f"{label} is outside the repository") from exc
    if not relative.parts[:2] == ("workspace", "private"):
        raise BindingError(f"{label} is outside workspace/private")
    return relative.as_posix()


def _timestamps(payload: bytes) -> tuple[list[int], int]:
    values = [
        int(match.group(1)) * 1_000_000 + int(match.group(2))
        for match in TIMESTAMP.finditer(payload)
    ]
    if not values or values != sorted(values):
        raise BindingError("stock dmesg timestamps are absent or nonmonotonic")
    normal_times: list[int] = []
    for line in payload.splitlines():
        if parser.NORMAL_PATH not in line:
            continue
        match = TIMESTAMP.match(line)
        if match is None:
            raise BindingError("stock normal-path marker has no monotonic timestamp")
        normal_times.append(
            int(match.group(1)) * 1_000_000 + int(match.group(2))
        )
    if not normal_times:
        raise BindingError("stock normal-path marker is absent")
    return values, normal_times[0]


def summarize_raw(payload: bytes) -> dict[str, Any]:
    if not 1 <= len(payload) <= MAX_RAW:
        raise BindingError("stock dmesg payload size is invalid")
    values, normal_first = _timestamps(payload)
    if values[0] > MAX_BOOT_START_USEC or values[0] > normal_first:
        raise BindingError("stock dmesg does not retain the HS-PHY boot window start")
    normalized = parser.parse(payload)
    return {
        "first_timestamp_usec": values[0],
        "last_timestamp_usec": values[-1],
        "normal_path_first_timestamp_usec": normal_first,
        "earliest_boot_record_retained": True,
        "read_to_eof": True,
        "ring_overwrite_before_hsphy_excluded": True,
        "normal_path_seen": True,
        "normalized": normalized,
    }


def build_result(
    root: Path,
    raw_path: Path,
    raw_payload: bytes,
    *,
    target_evidence: Mapping[str, Any],
    health: Mapping[str, Any],
    adb_receipt: Mapping[str, Any],
    module_observation: Mapping[str, Any],
) -> dict[str, Any]:
    relative = _relative_private_path(root, raw_path, "stock dmesg")
    raw = {"path": relative, **receipt(raw_payload)}
    summary = summarize_raw(raw_payload)
    normalized = {**summary.pop("normalized"), "input": raw}
    value = {
        "schema": SCHEMA,
        "verdict": VERDICT,
        "target": TARGET,
        "profile_id": PROFILE_ID,
        "campaign_binding": {
            "manifest_id": MANIFEST_ID,
            "live_run_id": LIVE_RUN_ID,
        },
        "source": {
            "kind": RAW_SOURCE,
            "command": CAPTURE_COMMAND,
            "producer": _source_receipt(root, PRODUCER_PATH),
            "binding": _source_receipt(root, BINDING_PATH),
            "parser": _source_receipt(root, PARSER_PATH),
        },
        "target_evidence": dict(target_evidence),
        "health": dict(health),
        "module": {
            "path": MODULE_PATH,
            "expected_sha256": MODULE_SHA256,
            **dict(module_observation),
        },
        "capture": {
            "raw": raw,
            "returncode": 0,
            "stderr_bytes": 0,
            "target_stable": True,
            "boot_id_stable": True,
            "boot_id_sha256": health.get("boot_id_sha256"),
            "initial_final_boot_id_equal": True,
            "boot_ring_snapshot_complete_for_hsphy": True,
            **summary,
        },
        "baseline": normalized,
        "adb": dict(adb_receipt),
        "safety": {
            "tier": "D0",
            "device_contact": True,
            "device_write": False,
            "reboot_requested": False,
            "download_requested": False,
            "odin_invoked": False,
            "partition_transfer": False,
            "eud_write": False,
            "a90_commands": 0,
        },
    }
    value["result_sha256"] = hashlib.sha256(_canonical(value)).hexdigest()
    return value


def verify_payloads(
    root: Path,
    raw_payload: bytes,
    result_payload: bytes,
    *,
    expected_raw_path: str,
) -> dict[str, Any]:
    try:
        value = json.loads(result_payload.decode("ascii"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise BindingError("bound stock baseline result is not ASCII JSON") from exc
    if not isinstance(value, dict):
        raise BindingError("bound stock baseline result is not an object")
    unsigned = dict(value)
    claimed_hash = unsigned.pop("result_sha256", None)
    if claimed_hash != hashlib.sha256(_canonical(unsigned)).hexdigest():
        raise BindingError("bound stock baseline result hash differs")
    if (
        value.get("schema") != SCHEMA
        or value.get("verdict") != VERDICT
        or value.get("target") != TARGET
        or value.get("profile_id") != PROFILE_ID
        or value.get("campaign_binding")
        != {"manifest_id": MANIFEST_ID, "live_run_id": LIVE_RUN_ID}
    ):
        raise BindingError("bound stock baseline identity differs")
    module = value.get("module")
    if (
        not isinstance(module, dict)
        or module.get("path") != MODULE_PATH
        or module.get("expected_sha256") != MODULE_SHA256
        or module.get("observed_sha256") != MODULE_SHA256
        or module.get("verified") is not True
        or not isinstance(module.get("sha256sum_stdout"), dict)
        or not re.fullmatch(
            r"[0-9a-f]{64}", str(module["sha256sum_stdout"].get("sha256", ""))
        )
        or not isinstance(module["sha256sum_stdout"].get("size"), int)
        or module["sha256sum_stdout"]["size"] <= 0
    ):
        raise BindingError("bound stock baseline module observation differs")
    source = value.get("source")
    expected_source = {
        "kind": RAW_SOURCE,
        "command": CAPTURE_COMMAND,
        "producer": _source_receipt(root, PRODUCER_PATH),
        "binding": _source_receipt(root, BINDING_PATH),
        "parser": _source_receipt(root, PARSER_PATH),
    }
    if source != expected_source:
        raise BindingError("bound stock baseline producer closure differs")
    summary = summarize_raw(raw_payload)
    raw = {"path": expected_raw_path, **receipt(raw_payload)}
    normalized = {**summary.pop("normalized"), "input": raw}
    health = value.get("health")
    if not isinstance(health, dict):
        raise BindingError("bound stock baseline health evidence differs")
    capture = value.get("capture")
    if not isinstance(capture, dict) or capture != {
        "raw": raw,
        "returncode": 0,
        "stderr_bytes": 0,
        "target_stable": True,
        "boot_id_stable": True,
        "boot_id_sha256": health.get("boot_id_sha256"),
        "initial_final_boot_id_equal": True,
        "boot_ring_snapshot_complete_for_hsphy": True,
        **summary,
    }:
        raise BindingError("bound stock baseline completeness evidence differs")
    if value.get("baseline") != normalized:
        raise BindingError("bound stock baseline normalization differs")
    target = value.get("target_evidence")
    safety = value.get("safety")
    if (
        not isinstance(target, dict)
        or target.get("schema") != "device_action_f1_target_evidence_v2"
        or not isinstance(target.get("targets"), list)
        or len(target["targets"]) != 1
        or target["targets"][0].get("model") != "SM-S906N"
        or target["targets"][0].get("device") != "g0q"
        or target["targets"][0].get("firmware_incremental") != "S906NKSS7FYG8"
        or target.get("odin_endpoint_absent") is not True
        or not isinstance(health, dict)
        or health.get("android_boot_completed") is not True
        or health.get("root_verified") is not True
        or not re.fullmatch(
            r"[0-9a-f]{64}", str(health.get("boot_id_sha256", ""))
        )
        or not isinstance(safety, dict)
        or safety.get("tier") != "D0"
        or safety.get("device_contact") is not True
        or any(
            safety.get(key) is not False
            for key in (
                "device_write",
                "reboot_requested",
                "download_requested",
                "odin_invoked",
                "partition_transfer",
                "eud_write",
            )
        )
        or safety.get("a90_commands") != 0
    ):
        raise BindingError("bound stock baseline D0 provenance differs")
    return {
        "schema": SCHEMA,
        "verdict": VERDICT,
        "raw": raw,
        "baseline": normalized,
        "producer_closure": expected_source,
        "campaign_binding": value["campaign_binding"],
        "boot_window_complete": True,
        "verified": True,
    }
