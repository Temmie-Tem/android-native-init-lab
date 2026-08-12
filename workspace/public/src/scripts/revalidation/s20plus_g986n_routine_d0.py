#!/usr/bin/env python3
"""Reusable bounded public-property D0 for the exact SM-G986N/y2q target."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import time
from typing import Any, Callable

import s20plus_g986n_d0_inventory as base


VERSION = "s20plus-g986n-routine-d0-v1"
SCHEMA = "s20plus_g986n_routine_d0_result_v1"
VERDICT = "PASS_S20PLUS_G986N_ROUTINE_D0_READ_ONLY"
EXPECTED_MODEL = "SM-G986N"
EXPECTED_ADB_MODEL = "model:SM_G986N"
EXPECTED_DEVICE = "y2q"
EXPECTED_PRODUCT = "y2qksx"
EXPECTED_INCREMENTAL = "G986NKSS8IYC2"
DEFAULT_RUN_ROOT = Path("workspace/private/runs/s20plus-g986n-routine-d0")
MAX_TEXT_BYTES = 32 * 1024
SAFE_VALUE_RE = re.compile(r"[^\x00\r\n]{0,4096}")

PROPERTY_KEYS = (
    "model",
    "device",
    "product_name",
    "incremental",
    "fingerprint",
    "carrier_id",
    "boot_sales_code",
    "csc_sales_code",
    "ril_sales_code",
    "omc_code",
    "omcnw_code",
    "omc_path",
    "omc_etcpath",
    "boot_completed",
    "bootanim",
    "verified_boot_state",
    "flash_locked",
    "vbmeta_device_state",
)

REMOTE_SNAPSHOT = """set -eu
emit_prop() {
    printf '%s=' "$1"
    getprop "$2"
}
emit_prop model ro.product.model
emit_prop device ro.product.device
emit_prop product_name ro.product.name
emit_prop incremental ro.build.version.incremental
emit_prop fingerprint ro.build.fingerprint
emit_prop carrier_id ro.boot.carrierid
emit_prop boot_sales_code ro.boot.sales_code
emit_prop csc_sales_code ro.csc.sales_code
emit_prop ril_sales_code ril.sales_code
emit_prop omc_code ro.csc.omc_code
emit_prop omcnw_code ro.csc.omcnw_code
emit_prop omc_path persist.sys.omc_path
emit_prop omc_etcpath persist.sys.omc_etcpath
emit_prop boot_completed sys.boot_completed
emit_prop bootanim init.svc.bootanim
emit_prop verified_boot_state ro.boot.verifiedbootstate
emit_prop flash_locked ro.boot.flash.locked
emit_prop vbmeta_device_state ro.boot.vbmeta.device_state
"""

CSC_MAP = {
    "KOO": "KOO",
    "KTC": "KTC",
    "KT": "KTC",
    "KTT": "KTC",
    "SKC": "SKC",
    "SKT": "SKC",
    "LUC": "LUC",
    "LGT": "LUC",
    "LGU": "LUC",
}


class RoutineD0Error(RuntimeError):
    pass


Command = Callable[[list[str], float, int], tuple[int, bytes, bytes]]


class CommandRecorder:
    def __init__(self, command: Command):
        self.command = command
        self.host_command_count = 0
        self.inventory_command_count = 0
        self.selected_target_command_count = 0

    def run(self, argv: list[str], timeout: float, maximum: int):
        self.host_command_count += 1
        if argv[-2:] == ["devices", "-l"]:
            self.inventory_command_count += 1
        if "-s" in argv:
            self.selected_target_command_count += 1
        return self.command(argv, timeout, maximum)

    def evidence(self) -> dict[str, int]:
        return {
            "host_command_count": self.host_command_count,
            "inventory_command_count": self.inventory_command_count,
            "selected_target_command_count": self.selected_target_command_count,
            "other_target_command_count": 0,
            "s22plus_command_count": 0,
            "a90_command_count": 0,
        }


def parse_snapshot(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    allowed = set(PROPERTY_KEYS)
    for line in text.splitlines():
        if "=" not in line:
            raise RoutineD0Error("property snapshot contains a malformed line")
        key, value = line.split("=", 1)
        if key not in allowed or key in values or SAFE_VALUE_RE.fullmatch(value) is None:
            raise RoutineD0Error(f"property snapshot contains an invalid field: {key}")
        values[key] = value
    if set(values) != allowed:
        raise RoutineD0Error("property snapshot fields are incomplete")
    expected = {
        "model": EXPECTED_MODEL,
        "device": EXPECTED_DEVICE,
        "product_name": EXPECTED_PRODUCT,
        "incremental": EXPECTED_INCREMENTAL,
        "boot_completed": "1",
        "bootanim": "stopped",
    }
    for key, value in expected.items():
        if values[key] != value:
            raise RoutineD0Error(f"selected target property mismatch: {key}")
    if not values["fingerprint"]:
        raise RoutineD0Error("selected target fingerprint is empty")
    return values


def resolve_csc(values: dict[str, str]) -> dict[str, Any]:
    evidence: dict[str, list[str]] = {}
    mapped: set[str] = set()
    for key in (
        "carrier_id",
        "boot_sales_code",
        "csc_sales_code",
        "ril_sales_code",
        "omc_code",
        "omcnw_code",
        "omc_path",
        "omc_etcpath",
    ):
        value = values[key].upper()
        tokens = sorted(set(re.findall(r"[A-Z0-9]{2,4}", value)))
        matches = sorted({CSC_MAP[token] for token in tokens if token in CSC_MAP})
        evidence[key] = matches
        mapped.update(matches)
    if len(mapped) == 1:
        return {
            "status": "EXACT",
            "csc": next(iter(mapped)),
            "mapped_evidence": evidence,
        }
    if not mapped:
        return {"status": "NO_PROOF", "csc": None, "mapped_evidence": evidence}
    return {
        "status": "CONFLICT",
        "csc": None,
        "candidates": sorted(mapped),
        "mapped_evidence": evidence,
    }


def decode(result: tuple[int, bytes, bytes], label: str) -> str:
    return base.decode_command(result, label)


def sanitized_inventory(rows: tuple[dict[str, Any], ...]) -> tuple[dict[str, Any], ...]:
    return base.sanitized_inventory(rows)


def select_exact_target(rows: tuple[dict[str, Any], ...]) -> dict[str, Any]:
    required = {
        EXPECTED_ADB_MODEL,
        f"device:{EXPECTED_DEVICE}",
        f"product:{EXPECTED_PRODUCT}",
    }
    plausible = [row for row in rows if required & row["metadata"]]
    if len(plausible) != 1:
        raise RoutineD0Error(
            f"expected exactly one plausible {EXPECTED_MODEL}/{EXPECTED_DEVICE}/{EXPECTED_PRODUCT} row"
        )
    selected = plausible[0]
    if selected["state"] != "device" or not required <= selected["metadata"]:
        raise RoutineD0Error("plausible target row does not have exact healthy identity")
    return selected


def collect(command: Command = base.bounded_command) -> dict[str, Any]:
    receipt = base.tool_receipt(base.DEFAULT_ADB)
    exact_adb = receipt["path"]
    recorder = CommandRecorder(command)

    first_text = decode(
        recorder.run([exact_adb, "devices", "-l"], 10, MAX_TEXT_BYTES),
        "initial ADB inventory",
    )
    first_rows = base.parse_inventory(first_text)
    selected = select_exact_target(first_rows)
    serial = selected["serial"]

    devpath = decode(
        recorder.run([exact_adb, "-s", serial, "get-devpath"], 10, MAX_TEXT_BYTES),
        "selected target devpath",
    )
    if base.DEVPATH_RE.fullmatch(devpath) is None:
        raise RoutineD0Error("selected target USB topology is malformed")

    values = parse_snapshot(
        decode(
            recorder.run(
                [exact_adb, "-s", serial, "exec-out", "sh", "-c", REMOTE_SNAPSHOT],
                20,
                MAX_TEXT_BYTES,
            ),
            "selected target public-property snapshot",
        )
    )
    base.validate_snapshot_binding(values, selected)

    final_text = decode(
        recorder.run([exact_adb, "devices", "-l"], 10, MAX_TEXT_BYTES),
        "final ADB inventory",
    )
    final_rows = base.parse_inventory(final_text)
    final_selected = select_exact_target(final_rows)
    if serial != final_selected["serial"] or sanitized_inventory(first_rows) != sanitized_inventory(final_rows):
        raise RoutineD0Error("selected target or ADB inventory changed during collection")
    if base.tool_receipt(Path(exact_adb)) != receipt:
        raise RoutineD0Error("ADB tool changed during collection")

    counts = recorder.evidence()
    if counts != {
        "host_command_count": 4,
        "inventory_command_count": 2,
        "selected_target_command_count": 2,
        "other_target_command_count": 0,
        "s22plus_command_count": 0,
        "a90_command_count": 0,
    }:
        raise RoutineD0Error("routine D0 command counts do not match the fixed plan")

    return {
        "schema": SCHEMA,
        "version": VERSION,
        "mode": "connected-read-only",
        "target": {
            "model": EXPECTED_MODEL,
            "device": EXPECTED_DEVICE,
            "product_name": EXPECTED_PRODUCT,
            "incremental": EXPECTED_INCREMENTAL,
            "adb_serial_sha256": base.sha256_text(serial),
            "usb_topology_sha256": base.sha256_text(devpath),
            "other_serial_sha256": sorted(
                base.sha256_text(row["serial"])
                for row in first_rows
                if row["serial"] != serial
            ),
        },
        "properties": values,
        "csc_resolution": resolve_csc(values),
        "host_tool": receipt,
        **counts,
        "device_writes": False,
        "root_used": False,
        "reboot_requested": False,
        "mode_transition_requested": False,
        "payload_transfer": False,
        "partition_access": False,
        "d1_authorized": False,
        "f1_authorized": False,
        "verdict": VERDICT,
    }


def _fsync_dir(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def allocate_run_dir(root: Path, requested: Path | None) -> Path:
    base_dir = (root / DEFAULT_RUN_ROOT).resolve()
    base_dir.mkdir(parents=True, exist_ok=True)
    candidate = requested or base_dir / (
        "d0-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + f"-{time.time_ns()}"
    )
    candidate = candidate if candidate.is_absolute() else root / candidate
    resolved = candidate.resolve()
    try:
        resolved.relative_to(base_dir)
    except ValueError as exc:
        raise RoutineD0Error("run directory is outside the private routine D0 root") from exc
    resolved.mkdir(mode=0o700)
    _fsync_dir(resolved.parent)
    return resolved


def failure_result(recorder: CommandRecorder, exc: Exception) -> dict[str, Any]:
    signature = f"{type(exc).__name__}:{exc}"
    return {
        "schema": "s20plus_g986n_routine_d0_failure_v1",
        "version": VERSION,
        "failure_class": type(exc).__name__,
        "failure_signature_sha256": hashlib.sha256(signature.encode()).hexdigest(),
        **recorder.evidence(),
        "device_writes": False,
        "root_used": False,
        "reboot_requested": False,
        "mode_transition_requested": False,
        "payload_transfer": False,
        "partition_access": False,
        "d1_authorized": False,
        "f1_authorized": False,
        "verdict": "FAIL_S20PLUS_G986N_ROUTINE_D0_READ_CLOSED",
    }


def dry_run_plan() -> dict[str, Any]:
    return {
        "schema": "s20plus_g986n_routine_d0_plan_v1",
        "version": VERSION,
        "mode": "dry-run-device-hidden",
        "expected_target": f"{EXPECTED_MODEL}/{EXPECTED_DEVICE}/{EXPECTED_INCREMENTAL}",
        "host_command_count": 4,
        "selected_target_command_count": 2,
        "other_target_command_count": 0,
        "device_writes": False,
        "root_used": False,
        "reboot_requested": False,
        "mode_transition_requested": False,
        "payload_transfer": False,
        "partition_access": False,
        "live_authorized": False,
    }


def repo_root() -> Path:
    return Path(__file__).resolve().parents[5]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--connected", action="store_true")
    parser.add_argument("--run-dir", type=Path)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if not args.connected:
        print(json.dumps(dry_run_plan(), indent=2, sort_keys=True))
        return 0
    run_dir = allocate_run_dir(repo_root(), args.run_dir)
    recorder = CommandRecorder(base.bounded_command)
    try:
        result = collect(recorder.run)
        base.durable_write(run_dir / "result.json", result)
    except Exception as exc:
        base.durable_write(run_dir / "failure.json", failure_result(recorder, exc))
        print("FAIL_S20PLUS_G986N_ROUTINE_D0_READ_CLOSED")
        print(f"failure={run_dir / 'failure.json'}")
        return 1
    print(VERDICT)
    print(f"result={run_dir / 'result.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
