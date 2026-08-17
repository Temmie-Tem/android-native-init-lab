#!/usr/bin/env python3
"""Focused stock read-only PART_DISPLAY pivot for S22+ FYG8 P2.57."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import stat
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import device_action_d0_v2 as d0
import device_action_f1_v2 as f1
import device_action_raw_capture_v1 as raw_capture


VERSION = "s22plus-fyg8-p257-stock-pivot-d0-v1"
RESULT_SCHEMA = "s22plus_fyg8_p257_stock_pivot_d0_result_v1"
PLAN_SCHEMA = "s22plus_fyg8_p257_stock_pivot_d0_plan_v1"
PROFILE_ID = "s22plus-fyg8"
DEFAULT_PROFILE = Path(
    "workspace/public/src/device-action/profiles/s22plus_fyg8.json"
)
DEFAULT_RUN_ROOT = Path(
    "workspace/private/runs/s22plus-fyg8-p257-stock-pivot-d0"
)
DISPLAY_PATH = "/sys/devices/soc0/display"
SUBSET_PARTS_PATH = "/sys/devices/soc0/subset_parts"
MAX_REMOTE_BYTES = 32
DISPLAY_RE = re.compile(rb"0x[0-9a-f]{1,8}\n")
SUBSET_PARTS_RE = re.compile(rb"[0-9a-f]{1,8}\n")
ENABLED_VERDICT = "PASS_P257_DISPLAY_ENABLED_STOCK_D0"
CONTRADICTION_VERDICT = "TARGET_CONTRADICTION"
INCONSISTENT_VERDICT = "INCONSISTENT"
INCONCLUSIVE_VERDICT = "INCONCLUSIVE"


class PivotError(RuntimeError):
    pass


@dataclass(frozen=True)
class _ProfileView:
    profile: dict[str, Any]


RemoteReader = Callable[[str, str, Path, str], raw_capture.RawCaptureHandle]


def repo_root() -> Path:
    return Path(__file__).resolve().parents[5]


def _resolve_from_root(root: Path, path: Path) -> Path:
    return path if path.is_absolute() else root / path


def load_profile(root: Path, path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    profile, receipt = f1.load_json(
        _resolve_from_root(root, path), "P2.57 target profile"
    )
    f1.validate_profile(profile)
    if profile["profile_id"] != PROFILE_ID:
        raise PivotError("P2.57 stock pivot requires the S22+ FYG8 profile")
    return profile, receipt


def parse_display(payload: bytes) -> int:
    if not isinstance(payload, bytes) or DISPLAY_RE.fullmatch(payload) is None:
        raise PivotError("display value is malformed")
    return int(payload[2:-1], 16)


def parse_subset_parts(payload: bytes) -> int:
    if not isinstance(payload, bytes) or SUBSET_PARTS_RE.fullmatch(payload) is None:
        raise PivotError("subset_parts value is malformed")
    return int(payload[:-1], 16)


def evaluate_reads(
    display_reads: tuple[bytes, bytes],
    subset_reads: tuple[bytes, bytes],
) -> dict[str, Any]:
    if (
        not isinstance(display_reads, tuple)
        or len(display_reads) != 2
        or not isinstance(subset_reads, tuple)
        or len(subset_reads) != 2
        or any(not isinstance(value, bytes) for value in (*display_reads, *subset_reads))
    ):
        raise PivotError("pivot reads have an invalid shape")
    if display_reads[0] != display_reads[1]:
        return _evaluation("INCONCLUSIVE", "display-read-changed")
    if subset_reads[0] != subset_reads[1]:
        return _evaluation("INCONCLUSIVE", "subset-parts-read-changed")
    try:
        display = parse_display(display_reads[0])
    except PivotError:
        return _evaluation("INCONCLUSIVE", "display-malformed")
    try:
        subset_parts = parse_subset_parts(subset_reads[0])
    except PivotError:
        return _evaluation("INCONCLUSIVE", "subset-parts-malformed")

    bit_set = bool(subset_parts & 0x10)
    if bool(display) != bit_set:
        return _evaluation(
            "INCONSISTENT",
            "display-subset-polarity-mismatch",
            display=display,
            subset_parts=subset_parts,
        )
    if display == 0:
        return _evaluation(
            "DISPLAY_ENABLED_VERIFIED",
            "source-polarity-display-enabled",
            display=display,
            subset_parts=subset_parts,
        )
    return _evaluation(
        "NO_DISPLAY_SUBSET_VERIFIED",
        "source-polarity-no-display-subset",
        display=display,
        subset_parts=subset_parts,
    )


def _evaluation(
    source_decision: str,
    reason: str,
    *,
    display: int | None = None,
    subset_parts: int | None = None,
) -> dict[str, Any]:
    if source_decision == "DISPLAY_ENABLED_VERIFIED":
        verdict = ENABLED_VERDICT
        target_sanity = "DISPLAY_CAPABLE_CONSISTENT"
        promotion_eligible = True
    elif source_decision == "NO_DISPLAY_SUBSET_VERIFIED":
        verdict = CONTRADICTION_VERDICT
        target_sanity = "TARGET_CONTRADICTION"
        promotion_eligible = False
    elif source_decision == "INCONSISTENT":
        verdict = INCONSISTENT_VERDICT
        target_sanity = "UNRESOLVED"
        promotion_eligible = False
    else:
        verdict = INCONCLUSIVE_VERDICT
        target_sanity = "UNRESOLVED"
        promotion_eligible = False
    return {
        "source_decision": source_decision,
        "reason": reason,
        "display_value": display,
        "subset_parts_value": subset_parts,
        "display_bit_set": (
            None if subset_parts is None else bool(subset_parts & 0x10)
        ),
        "target_sanity": target_sanity,
        "promotion_eligible": promotion_eligible,
        "verdict": verdict,
    }


def read_remote_exact(
    adb: Path,
    serial: str,
    source: str,
    capture_dir: Path,
    name: str,
) -> raw_capture.RawCaptureHandle:
    if source not in {DISPLAY_PATH, SUBSET_PARTS_PATH}:
        raise PivotError("remote pivot path is not allowlisted")
    try:
        handle = raw_capture.acquire_command(
            [str(adb), "-s", serial, "exec-out", "cat", source],
            capture_dir,
            name,
            timeout=10,
            stdout_maximum=MAX_REMOTE_BYTES,
            stderr_maximum=d0.MAX_TEXT_OUTPUT,
            stdout_name=f"{name}.bin",
            stderr_name=f"{name}.bin.stderr",
        )
        raw_capture.require_success(handle)
    except raw_capture.RawCaptureError as exc:
        raise PivotError(
            f"remote pivot raw capture failed: {Path(source).name}: {exc}"
        ) from exc
    return handle


def _fsync_dir(path: Path) -> None:
    descriptor = os.open(
        path,
        os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_NOFOLLOW", 0),
    )
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def evaluate_capture_handles(
    display: tuple[raw_capture.RawCaptureHandle, raw_capture.RawCaptureHandle],
    subset_parts: tuple[
        raw_capture.RawCaptureHandle, raw_capture.RawCaptureHandle
    ],
) -> tuple[dict[str, Any], tuple[tuple[bytes, bytes], tuple[bytes, bytes]]]:
    handles = (*display, *subset_parts)
    if any(not isinstance(handle, raw_capture.RawCaptureHandle) for handle in handles):
        raise PivotError("pivot parser input is not a raw capture handle")
    try:
        payloads = tuple(
            raw_capture.read_stdout(handle, maximum=MAX_REMOTE_BYTES)
            for handle in handles
        )
    except raw_capture.RawCaptureError as exc:
        raise PivotError("pivot raw handle cannot be parsed") from exc
    if any(not payload for payload in payloads):
        raise PivotError("remote pivot read is empty")
    display_payloads = (payloads[0], payloads[1])
    subset_payloads = (payloads[2], payloads[3])
    return (
        evaluate_reads(display_payloads, subset_payloads),
        (display_payloads, subset_payloads),
    )


def durable_create_bytes(path: Path, payload: bytes) -> dict[str, Any]:
    if not isinstance(payload, bytes) or not 1 <= len(payload) <= MAX_REMOTE_BYTES:
        raise PivotError("raw pivot payload is outside its bound")
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
                raise PivotError("short raw pivot write")
            offset += written
        os.fsync(descriptor)
        metadata = os.fstat(descriptor)
        if (
            not stat.S_ISREG(metadata.st_mode)
            or stat.S_IMODE(metadata.st_mode) != 0o400
            or metadata.st_size != len(payload)
        ):
            raise PivotError("raw pivot receipt is not sealed")
    finally:
        os.close(descriptor)
    _fsync_dir(path.parent)
    return {
        "path": str(path),
        "bytes": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
    }


def allocate_run_dir(root: Path, requested: Path | None) -> Path:
    base = (root / DEFAULT_RUN_ROOT).resolve()
    base.mkdir(parents=True, exist_ok=True)
    candidate = requested or base / (
        "pivot-"
        + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
        + f"-{time.time_ns()}"
    )
    candidate = candidate if candidate.is_absolute() else root / candidate
    resolved = candidate.resolve()
    try:
        resolved.relative_to(base)
    except ValueError as exc:
        raise PivotError("pivot run directory is outside the private run root") from exc
    resolved.mkdir(mode=0o700)
    _fsync_dir(resolved.parent)
    return resolved


def _target_evidence(
    profile: dict[str, Any],
    properties: dict[str, str],
    serial: str,
    topology: str,
) -> dict[str, Any]:
    evidence = {
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
    f1.validate_target_evidence(profile, evidence)
    return evidence


def collect_connected(
    profile: dict[str, Any],
    profile_receipt: dict[str, Any],
    run_dir: Path,
    client: d0.ReadOnlyClient,
    usb_root: Path,
    remote_reader: RemoteReader,
) -> dict[str, Any]:
    if isinstance(client, d0.AdbReadOnlyClient):
        client.bind_raw_capture_dir(run_dir)
    capture_dir = raw_capture.prepare_capture_dir(run_dir, "raw-pivot-d0")
    host_tool = client.receipt()
    download = profile["target"]["download"]
    initial_usb = d0.usb_snapshot(usb_root, download)
    if not initial_usb["enumerated_devices"]:
        raise PivotError("host USB inventory is unexpectedly empty")
    if initial_usb["download_endpoint_count"]:
        raise PivotError("Download endpoint is present before pivot collection")

    serial = client.one_serial()
    topology = client.topology(serial)
    first_properties = client.properties(serial)
    root_health = client.root_health(serial)
    health = d0.validate_health(
        _ProfileView(profile), first_properties, root_health, True
    )

    raw: dict[str, list[dict[str, Any]]] = {"display": [], "subset_parts": []}
    display_reads: list[raw_capture.RawCaptureHandle] = []
    subset_reads: list[raw_capture.RawCaptureHandle] = []
    for name, source, destination in (
        ("display", DISPLAY_PATH, display_reads),
        ("display", DISPLAY_PATH, display_reads),
        ("subset_parts", SUBSET_PARTS_PATH, subset_reads),
        ("subset_parts", SUBSET_PARTS_PATH, subset_reads),
    ):
        ordinal = len(raw[name]) + 1
        capture_name = f"{name}-read-{ordinal}"
        handle = remote_reader(serial, source, capture_dir, capture_name)
        destination.append(handle)
        raw[name].append(
            {
                "path": str(handle.stdout_path),
                "bytes": int(handle.stdout["size"]),
                "sha256": str(handle.stdout["sha256"]),
                "capture_receipt": {
                    "path": str(handle.receipt_path),
                    "bytes": handle.receipt_path.stat().st_size,
                    "sha256": hashlib.sha256(
                        handle.receipt_path.read_bytes()
                    ).hexdigest(),
                },
            }
        )

    evaluation, _payloads = evaluate_capture_handles(
        (display_reads[0], display_reads[1]),
        (subset_reads[0], subset_reads[1]),
    )
    final_serial = client.one_serial()
    final_topology = client.topology(final_serial)
    final_properties = client.properties(final_serial)
    final_usb = d0.usb_snapshot(usb_root, download)
    if (
        final_serial != serial
        or final_topology != topology
        or final_properties != first_properties
    ):
        raise PivotError("connected target changed during pivot collection")
    if (
        not final_usb["enumerated_devices"]
        or final_usb["download_endpoint_count"]
    ):
        raise PivotError("host USB state changed during pivot collection")

    result = {
        "schema": RESULT_SCHEMA,
        "version": VERSION,
        "mode": "connected-read-only",
        "profile_id": profile["profile_id"],
        "profile": profile_receipt,
        "target_evidence": _target_evidence(
            profile, first_properties, serial, topology
        ),
        "health": health,
        "measurement": {
            "paths": {
                "display": DISPLAY_PATH,
                "subset_parts": SUBSET_PARTS_PATH,
            },
            "raw_receipts": raw,
            **evaluation,
        },
        "usb": {"initial": initial_usb, "final": final_usb},
        "host_tool": host_tool,
        "verdict": evaluation["verdict"],
        "device_contact": True,
        "device_writes": False,
        "root_used_for_pivot_reads": False,
        "reboot_requested": False,
        "download_transition_requested": False,
        "odin_invoked": False,
        "partition_transfer": False,
        "f1_authorized": False,
        "live_authorized": False,
    }
    validate_result(result, profile)
    d0.durable_create(run_dir / "result.json", result)
    return result


def validate_result(result: dict[str, Any], profile: dict[str, Any]) -> None:
    if result.get("schema") != RESULT_SCHEMA or result.get("version") != VERSION:
        raise PivotError("pivot result header is invalid")
    if result.get("profile_id") != profile["profile_id"]:
        raise PivotError("pivot result profile mismatch")
    f1.validate_target_evidence(profile, result.get("target_evidence"))
    measurement = result.get("measurement")
    if not isinstance(measurement, dict) or measurement.get("verdict") != result.get(
        "verdict"
    ):
        raise PivotError("pivot result measurement is invalid")
    eligible = measurement.get("promotion_eligible")
    if (result["verdict"] == ENABLED_VERDICT) != (eligible is True):
        raise PivotError("pivot promotion contract is inconsistent")
    for key in (
        "device_writes",
        "root_used_for_pivot_reads",
        "reboot_requested",
        "download_transition_requested",
        "odin_invoked",
        "partition_transfer",
        "f1_authorized",
        "live_authorized",
    ):
        if result.get(key) is not False:
            raise PivotError(f"pivot result contains forbidden authority: {key}")
    if result.get("device_contact") is not True:
        raise PivotError("pivot result does not prove connected collection")


def render_plan(
    profile: dict[str, Any],
    profile_receipt: dict[str, Any],
    adb: Path,
) -> dict[str, Any]:
    return {
        "schema": PLAN_SCHEMA,
        "version": VERSION,
        "profile_id": profile["profile_id"],
        "profile": profile_receipt,
        "adb": d0._hash_regular_file(adb.resolve(strict=True)),
        "reads": [
            "exact target identity and Android/root health",
            "host USB Download-endpoint absence",
            f"{DISPLAY_PATH} twice, 32-byte bound",
            f"{SUBSET_PARTS_PATH} twice, 32-byte bound",
        ],
        "device_contact": False,
        "device_writes": False,
        "root_used_for_pivot_reads": False,
        "reboot_requested": False,
        "download_transition_requested": False,
        "odin_invoked": False,
        "partition_transfer": False,
        "f1_authorized": False,
        "live_authorized": False,
    }


def default_adb() -> Path:
    value = shutil.which("adb")
    if value is None:
        raise PivotError("adb is unavailable")
    return Path(value)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--validate", action="store_true")
    modes.add_argument("--render-plan", action="store_true")
    modes.add_argument("--connected-read-only", action="store_true")
    parser.add_argument("--profile", type=Path, default=DEFAULT_PROFILE)
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--adb", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = repo_root()
    try:
        profile, profile_receipt = load_profile(root, args.profile)
        adb = args.adb or default_adb()
        plan = render_plan(profile, profile_receipt, adb)
        if args.validate:
            result = {
                **plan,
                "schema": "s22plus_fyg8_p257_stock_pivot_d0_offline_v1",
                "verdict": "PASS_P257_STOCK_PIVOT_H0_READY",
            }
        elif args.render_plan:
            result = plan
        else:
            run_dir = allocate_run_dir(root, args.run_dir)
            resolved_adb = adb.resolve(strict=True)
            result = collect_connected(
                profile,
                profile_receipt,
                run_dir,
                d0.AdbReadOnlyClient(resolved_adb),
                d0.DEFAULT_USB_ROOT,
                lambda serial, source, capture_dir, name: read_remote_exact(
                    resolved_adb, serial, source, capture_dir, name
                ),
            )
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result.get("verdict") in {
            "PASS_P257_STOCK_PIVOT_H0_READY",
            ENABLED_VERDICT,
        } else 3
    except (PivotError, d0.D0Error, f1.F1V2Error, OSError) as exc:
        print(f"P2.57 stock pivot error: {exc}", file=os.sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
