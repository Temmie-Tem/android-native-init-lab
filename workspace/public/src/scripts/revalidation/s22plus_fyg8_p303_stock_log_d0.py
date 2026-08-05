#!/usr/bin/env python3
"""Capture one complete working-stock HS-PHY dmesg baseline from exact S22+."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
import time
from typing import Any

import device_action_d0_v2 as d0
import device_action_f1_v2 as f1
import s22plus_fyg8_p303_stock_log_baseline_binding as binding


VERSION = "s22plus-fyg8-p303-stock-log-d0-v1"
DEFAULT_PROFILE = Path("workspace/public/src/device-action/profiles/s22plus_fyg8.json")
DEFAULT_RUN_ROOT = Path("workspace/private/runs/s22plus-fyg8-p303-stock-log-d0")
DEFAULT_ADB = Path("/usr/bin/adb")
RESULT_NAME = "stock-hsphy-baseline.json"
RAW_NAME = "stock-dmesg.bin"


class CaptureError(RuntimeError):
    pass


@dataclass(frozen=True)
class _ProfileView:
    profile: dict[str, Any]


def repo_root() -> Path:
    return Path(__file__).resolve().parents[5]


def _resolve(root: Path, value: Path) -> Path:
    return value if value.is_absolute() else root / value


def _fsync_dir(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _durable_bytes(path: Path, payload: bytes) -> None:
    descriptor = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC | os.O_NOFOLLOW,
        0o400,
    )
    try:
        offset = 0
        while offset < len(payload):
            written = os.write(descriptor, payload[offset:])
            if written <= 0:
                raise CaptureError("short P3.03 stock-log write")
            offset += written
        os.fsync(descriptor)
        metadata = os.fstat(descriptor)
        if (
            not stat.S_ISREG(metadata.st_mode)
            or stat.S_IMODE(metadata.st_mode) != 0o400
            or metadata.st_size != len(payload)
        ):
            raise CaptureError("P3.03 stock-log durable identity differs")
    finally:
        os.close(descriptor)
    _fsync_dir(path.parent)


def _allocate(root: Path, requested: Path | None) -> Path:
    base = (root / DEFAULT_RUN_ROOT).resolve()
    base.mkdir(parents=True, exist_ok=True)
    name = (
        "d0-"
        + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
        + f"-{time.time_ns()}"
    )
    value = requested or base / name
    path = value if value.is_absolute() else root / value
    resolved = path.resolve()
    try:
        resolved.relative_to(base)
    except ValueError as exc:
        raise CaptureError("P3.03 stock-log run directory escaped private root") from exc
    resolved.mkdir(mode=0o700)
    _fsync_dir(resolved.parent)
    return resolved


def _target_evidence(
    profile: dict[str, Any], properties: dict[str, str], serial: str, topology: str
) -> dict[str, Any]:
    value = {
        "schema": f1.TARGET_EVIDENCE_SCHEMA,
        "targets": [
            {
                "model": properties["model"],
                "device": properties["device"],
                "firmware_incremental": properties["incremental"],
                "android_transport": "adb",
                "adb_serial_sha256": hashlib.sha256(serial.encode()).hexdigest(),
                "usb_topology_sha256": hashlib.sha256(topology.encode()).hexdigest(),
            }
        ],
        "odin_endpoint_absent": True,
    }
    f1.validate_target_evidence(profile, value)
    return value


def _exact_identity(profile: dict[str, Any], properties: dict[str, str]) -> None:
    target = profile["target"]
    expected = {
        "model": target["model"],
        "device": target["device"],
        "incremental": target["firmware_incremental"],
    }
    if any(properties.get(name) != value for name, value in expected.items()):
        raise CaptureError("connected target is not exact S22+ FYG8")
    if properties.get("boot_completed") != "1" or properties.get("bootanim") != "stopped":
        raise CaptureError("exact S22+ Android boot is not complete")


def _root_command(adb: Path, serial: str, command: str, maximum: int) -> bytes:
    result = d0.bounded_command(
        [str(adb), "-s", serial, "exec-out", "su", "-c", command],
        timeout=60,
        maximum=maximum,
    )
    if result.returncode != 0 or result.stderr:
        raise CaptureError("P3.03 stock-log root read failed or produced stderr")
    if not result.stdout:
        raise CaptureError("P3.03 stock-log root read is empty")
    return result.stdout


def _exact_serial_from_inventory(text: str) -> tuple[str, int]:
    rows: list[tuple[str, str, set[str]]] = []
    for line in text.splitlines():
        if not line or line.startswith("List of devices attached"):
            continue
        fields = line.split()
        if len(fields) < 2:
            raise CaptureError("ADB inventory contains a malformed row")
        rows.append((fields[0], fields[1], set(fields[2:])))
    matches = [
        serial
        for serial, state, metadata in rows
        if state == "device"
        and "model:SM_S906N" in metadata
        and "device:g0q" in metadata
    ]
    if len(matches) != 1:
        raise CaptureError(
            f"expected exactly one connected FYG8 S22+, found {len(matches)}"
        )
    return matches[0], len(rows)


def _select_exact_serial(adb: Path) -> tuple[str, int]:
    result = d0.bounded_command(
        [str(adb), "devices", "-l"], timeout=10, maximum=d0.MAX_TEXT_OUTPUT
    )
    if result.returncode != 0 or result.stderr:
        raise CaptureError("ADB inventory failed or produced stderr")
    try:
        text = result.stdout.decode("utf-8", "strict")
    except UnicodeDecodeError as exc:
        raise CaptureError("ADB inventory is not UTF-8") from exc
    return _exact_serial_from_inventory(text)


def _final_target_snapshot(
    client: d0.AdbReadOnlyClient,
    adb: Path,
    initial_serial: str,
    initial_inventory_count: int,
) -> tuple[str, str, dict[str, str]]:
    final_serial, final_inventory_count = _select_exact_serial(adb)
    if (
        final_serial != initial_serial
        or final_inventory_count != initial_inventory_count
    ):
        raise CaptureError("exact S22+ ADB selection changed during capture")
    return (
        final_serial,
        client.topology(final_serial),
        client.properties(final_serial),
    )


def collect(root: Path, profile_path: Path, adb_path: Path, run_dir: Path) -> dict[str, Any]:
    profile, _ = f1.load_json(profile_path, "P3.03 target profile")
    f1.validate_profile(profile)
    if profile.get("profile_id") != binding.PROFILE_ID:
        raise CaptureError("P3.03 requires the S22+ FYG8 profile")
    client = d0.AdbReadOnlyClient(adb_path)
    host_tool = client.receipt()
    initial_usb = d0.usb_snapshot(d0.DEFAULT_USB_ROOT, profile["target"]["download"])
    if not initial_usb["enumerated_devices"] or initial_usb["download_endpoint_count"]:
        raise CaptureError("initial USB inventory is not stable Android")
    serial, inventory_count = _select_exact_serial(adb_path)
    topology = client.topology(serial)
    first = client.properties(serial)
    _exact_identity(profile, first)

    raw = _root_command(adb_path, serial, "dmesg", binding.MAX_RAW)
    binding.summarize_raw(raw)
    raw_path = run_dir / RAW_NAME
    _durable_bytes(raw_path, raw)

    module_output = _root_command(
        adb_path,
        serial,
        f"sha256sum {binding.MODULE_PATH}",
        d0.MAX_TEXT_OUTPUT,
    )
    module_fields = module_output.decode("ascii", "strict").strip().split()
    if (
        len(module_fields) < 2
        or module_fields[0] != binding.MODULE_SHA256
        or module_fields[1] != binding.MODULE_PATH
    ):
        raise CaptureError("on-device P3.03 HS-PHY module identity differs")

    root_health = client.root_health(serial)
    health = d0.validate_health(_ProfileView(profile), first, root_health, True)
    final_serial, final_topology, final = _final_target_snapshot(
        client, adb_path, serial, inventory_count
    )
    final_usb = d0.usb_snapshot(d0.DEFAULT_USB_ROOT, profile["target"]["download"])
    if (
        final_serial != serial
        or final_topology != topology
        or final != first
        or not final_usb["enumerated_devices"]
        or final_usb["download_endpoint_count"]
    ):
        raise CaptureError("exact S22+ changed during P3.03 D0 capture")

    value = binding.build_result(
        root,
        raw_path,
        raw,
        target_evidence=_target_evidence(profile, first, serial, topology),
        health=health,
        adb_receipt=host_tool,
        module_observation={
            "observed_sha256": module_fields[0],
            "sha256sum_stdout": binding.receipt(module_output),
            "verified": True,
        },
    )
    result_path = run_dir / RESULT_NAME
    payload = json.dumps(value, indent=2, sort_keys=True, allow_nan=False).encode("ascii") + b"\n"
    _durable_bytes(result_path, payload)
    binding.verify_payloads(
        root,
        raw,
        payload,
        expected_raw_path=raw_path.relative_to(root).as_posix(),
    )
    return {
        "schema": "s22plus_fyg8_p303_stock_log_d0_completion_v1",
        "verdict": binding.VERDICT,
        "run_dir": run_dir.relative_to(root).as_posix(),
        "raw": {"path": raw_path.relative_to(root).as_posix(), **binding.receipt(raw)},
        "result": {"path": result_path.relative_to(root).as_posix(), **binding.receipt(payload)},
        "module_sha256": binding.MODULE_SHA256,
        "adb_inventory_count": inventory_count,
        "usb": {"initial": initial_usb, "final": final_usb},
        "device_contact": True,
        "device_write": False,
        "a90_commands": 0,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", type=Path, default=DEFAULT_PROFILE)
    parser.add_argument("--adb", type=Path, default=DEFAULT_ADB)
    parser.add_argument("--run-dir", type=Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    try:
        output = collect(
            root,
            _resolve(root, args.profile),
            _resolve(root, args.adb),
            _allocate(root, args.run_dir),
        )
    except (CaptureError, binding.BindingError, d0.D0Error, f1.F1V2Error, OSError) as exc:
        print(f"P3.03 stock-log D0 error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(output, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
