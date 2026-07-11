#!/usr/bin/env python3
"""Guarded S22+ V3443R corrected HIGH panic versus pinned MID control."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shlex
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import s22plus_v3440_rdx_usb_viability_gate as rdx
import s22plus_v3442_high_set_only_live_gate as high


SCHEMA = "s22plus_v3443r_high_panic_compare_v1"
SCRIPT_RELATIVE = Path(
    "workspace/public/src/scripts/revalidation/"
    "s22plus_v3443_high_panic_compare_live_gate.py"
)
POLICY_DRAFT = Path(
    "docs/operations/"
    "S22PLUS_V3443R_HIGH_PANIC_COMPARE_AGENTS_EXCEPTION_DRAFT_2026-07-11.md"
)
POLICY_MARKER = "S22+ V3443R corrected HIGH panic MID-control comparison live gate"
ACTIVE_SENTINEL = "S22PLUS_V3443R_HIGH_PANIC_COMPARE_POLICY_STATE=ACTIVE"
HIGH_PANIC_ACK_TOKEN = "S22PLUS-V3443R-HIGH-ONE-SYSRQ-PANIC"
PREAMBLE_ACK_TOKEN = "S22PLUS-V3443R-RDX-PREAMBLE-ONLY"
RECOVERY_ACK_TOKEN = "S22PLUS-V3443R-MID-RESTORE-RECOVERY"

MID_CONTROL_DIR = Path(
    "workspace/private/runs/s22plus_v3440_rdx_20260711T000711Z"
)
MID_CONTROL_RESULT_SHA256 = (
    "62a6d12adb5ab33f39d9d44078de09f6180a39980b417dadf1fe9a598acd7dbe"
)
MID_CONTROL_LAST_KMSG_SHA256 = (
    "a397d9688e740bc03bead8c4fd2fcc667910cfe98d2f92252a36b474e66a5b04"
)
MID_CONTROL_PREAMBLE_SHA256 = (
    "3a4a3980e7835ebb77c927b99863e01847086171bdb81773e81e06f2192ab60c"
)
MID_CONTROL_RUN_ID = "9ab2fb480429abf280f59583560d2d29"
PREAMBLE = b"PrEaMbLe\0"
POSITIVE_ACK = b"AcKnOwLeDgMeNt\0"
NEGATIVE_ACK = b"NeGaTiVeAcKmNt\0"
RUN_ROOT = Path("workspace/private/runs")
TIMELINE_NAMES = (
    "live_session_start",
    "candidate_flash_start",
    "candidate_flash_done",
    "candidate_boot_ready",
    "rollback_flash_start",
    "rollback_flash_done",
    "rollback_boot_ready",
    "live_session_end",
)


class GateError(RuntimeError):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def durable_write_json(path: Path, value: Any) -> None:
    high.durable_write_json(path, value)


def append_event(path: Path, events: list[dict[str, str]], name: str) -> None:
    if name not in TIMELINE_NAMES:
        raise GateError(f"unknown timeline event: {name}")
    if name in {event["name"] for event in events}:
        raise GateError(f"duplicate timeline event: {name}")
    events.append({"name": name, "timestamp_utc": utc_now()})
    durable_write_json(path, {"events": events})


def sha256_file(path: Path) -> str:
    return high.sha256_file(path)


def policy_active(root: Path) -> bool:
    text = (root / "AGENTS.md").read_text(encoding="utf-8")
    required = (
        POLICY_MARKER,
        ACTIVE_SENTINEL,
        str(SCRIPT_RELATIVE),
        sha256_file(root / SCRIPT_RELATIVE),
        HIGH_PANIC_ACK_TOKEN,
        PREAMBLE_ACK_TOKEN,
        RECOVERY_ACK_TOKEN,
        high.EXPECTED_SETTER_SHA256,
        MID_CONTROL_LAST_KMSG_SHA256,
        MID_CONTROL_PREAMBLE_SHA256,
        "PrEaMbLe\\0",
        "PrObE forbidden",
        "DaTaXfEr forbidden",
    )
    return all(item in text for item in required)


def verify_policy_draft(root: Path) -> dict[str, Any]:
    path = root / POLICY_DRAFT
    if not path.is_file():
        raise GateError("V3443R policy draft missing")
    text = path.read_text(encoding="utf-8")
    required = (
        "DRAFT_INACTIVE",
        POLICY_MARKER,
        str(SCRIPT_RELATIVE),
        sha256_file(root / SCRIPT_RELATIVE),
        HIGH_PANIC_ACK_TOKEN,
        PREAMBLE_ACK_TOKEN,
        RECOVERY_ACK_TOKEN,
        high.EXPECTED_SETTER_SHA256,
        MID_CONTROL_RESULT_SHA256,
        MID_CONTROL_LAST_KMSG_SHA256,
        MID_CONTROL_PREAMBLE_SHA256,
        "PrEaMbLe\\0",
        "PrObE forbidden",
        "DaTaXfEr forbidden",
    )
    missing = [item for item in required if item not in text]
    if missing:
        raise GateError(f"V3443R policy draft missing pins: {missing}")
    return {
        "path": str(POLICY_DRAFT),
        "sha256": sha256_file(path),
        "active": policy_active(root),
    }


def summarize_last_kmsg(data: bytes, marker: bytes) -> dict[str, Any]:
    signatures = {
        "run_marker": marker,
        "sysrq_panic": b"Kernel panic - not syncing: sysrq triggered crash",
        "rdx_locked": b"RDX is locked.",
        "upload_cause_kernel_panic": b"upload_cause = KERNEL PANIC",
        "ramdump": b"ramdump",
        "minidump": b"minidump",
        "sec_debug": b"sec_debug",
        "rst_exinfo": b"rst_exinfo",
    }
    return {
        "bytes": len(data),
        "lines": data.count(b"\n"),
        "sha256": hashlib.sha256(data).hexdigest(),
        "signature_counts": {
            name: data.count(pattern) for name, pattern in signatures.items()
        },
    }


def verify_mid_control(root: Path) -> dict[str, Any]:
    run_dir = root / MID_CONTROL_DIR
    result_path = run_dir / "result.json"
    log_path = run_dir / "post_recovery_last_kmsg.bin"
    response_path = run_dir / "sboot_preamble_response.bin"
    expected = {
        result_path: MID_CONTROL_RESULT_SHA256,
        log_path: MID_CONTROL_LAST_KMSG_SHA256,
        response_path: MID_CONTROL_PREAMBLE_SHA256,
    }
    for path, digest in expected.items():
        if not path.is_file() or sha256_file(path) != digest:
            raise GateError(f"pinned MID control missing or mismatched: {path.name}")
    result = json.loads(result_path.read_text(encoding="utf-8"))
    probe = result.get("probe", {})
    if result.get("run_id") != MID_CONTROL_RUN_ID:
        raise GateError("MID control run id mismatch")
    if result.get("verdict") != "CONTROLLED_NEGATIVE_SBOOT_NEGATIVE_ACK_PROBE_NOT_SENT":
        raise GateError("MID control verdict mismatch")
    if probe.get("probe_sent") is not False or probe.get("data_transfer_requested") is not False:
        raise GateError("MID control exceeded preamble-only comparison scope")
    if response_path.read_bytes() != NEGATIVE_ACK:
        raise GateError("MID control preamble response mismatch")
    data = log_path.read_bytes()
    summary = summarize_last_kmsg(
        data, f"S22_V3440_RDX_BEGIN run={MID_CONTROL_RUN_ID}".encode()
    )
    required = summary["signature_counts"]
    for name in ("run_marker", "sysrq_panic", "rdx_locked", "upload_cause_kernel_panic"):
        if required[name] < 1:
            raise GateError(f"MID control lacks required evidence: {name}")
    return {
        "run_dir": str(MID_CONTROL_DIR),
        "debug_level": "MID",
        "result_sha256": MID_CONTROL_RESULT_SHA256,
        "last_kmsg": summary,
        "preamble": {
            "classification": "NEGATIVE_ACK",
            "bytes": len(NEGATIVE_ACK),
            "sha256": MID_CONTROL_PREAMBLE_SHA256,
        },
    }


def classify_preamble(response: bytes) -> str:
    if response == NEGATIVE_ACK:
        return "NEGATIVE_ACK"
    if response == POSITIVE_ACK:
        return "POSITIVE_ACK_STOPPED_BEFORE_PROBE"
    return "UNEXPECTED_RESPONSE_STOPPED"


def preamble_only(run_dir: Path) -> dict[str, Any]:
    try:
        import usb.core  # type: ignore[import-not-found]
        import usb.util  # type: ignore[import-not-found]
    except ModuleNotFoundError as error:
        raise GateError("PyUSB unavailable") from error

    devices = list(
        usb.core.find(
            find_all=True,
            idVendor=rdx.SAMSUNG_RDX_ID[0],
            idProduct=rdx.SAMSUNG_RDX_ID[1],
        )
    )
    if len(devices) != 1:
        raise GateError(f"expected one Samsung RDX endpoint, found {len(devices)}")
    device = devices[0]
    interfaces = [
        item
        for item in device.get_active_configuration()
        if int(item.bInterfaceClass) == 0x0A
    ]
    if len(interfaces) != 1:
        raise GateError("expected one RDX CDC-data interface")
    interface = interfaces[0]
    number = int(interface.bInterfaceNumber)
    out_endpoint = usb.util.find_descriptor(
        interface,
        custom_match=lambda item: usb.util.endpoint_direction(item.bEndpointAddress)
        == usb.util.ENDPOINT_OUT,
    )
    in_endpoint = usb.util.find_descriptor(
        interface,
        custom_match=lambda item: usb.util.endpoint_direction(item.bEndpointAddress)
        == usb.util.ENDPOINT_IN,
    )
    if out_endpoint is None or in_endpoint is None:
        raise GateError("RDX interface lacks one IN and one OUT endpoint")
    detached = False
    claimed = False
    try:
        try:
            if device.is_kernel_driver_active(number):
                device.detach_kernel_driver(number)
                detached = True
        except (NotImplementedError, AttributeError):
            pass
        usb.util.claim_interface(device, number)
        claimed = True
        packet_size = int(out_endpoint.wMaxPacketSize)
        for offset in range(0, len(PREAMBLE), packet_size):
            written = out_endpoint.write(
                PREAMBLE[offset : offset + packet_size], timeout=1000
            )
            if written <= 0:
                raise GateError("RDX preamble write made no progress")
        response = bytes(
            in_endpoint.read(int(in_endpoint.wMaxPacketSize), timeout=1000)
        )
        rdx.durable_write_bytes(run_dir / "sboot_preamble_response.bin", response)
        return {
            "command_sent": "PrEaMbLe",
            "classification": classify_preamble(response),
            "response_bytes": len(response),
            "response_sha256": hashlib.sha256(response).hexdigest(),
            "probe_sent": False,
            "data_transfer_requested": False,
        }
    finally:
        if claimed:
            try:
                usb.util.release_interface(device, number)
            except Exception:
                pass
        if detached:
            try:
                device.attach_kernel_driver(number)
            except Exception:
                pass
        usb.util.dispose_resources(device)


def adb_connected(serial: str) -> bool:
    try:
        result = high.run(["adb", "-s", serial, "get-state"], timeout=3)
    except subprocess.TimeoutExpired:
        return False
    return result.returncode == 0 and result.stdout.strip() == "device"


def run_quoted_root_command(
    serial: str, command: str, *, timeout: float = 20
) -> subprocess.CompletedProcess[str]:
    remote_shell = f"su -c {shlex.quote(command)}"
    return high.run(
        ["adb", "-s", serial, "shell", remote_shell], timeout=timeout
    )


def verify_root_compound_shell(serial: str) -> dict[str, Any]:
    result = run_quoted_root_command(serial, "id; id")
    root_lines = [
        line for line in result.stdout.splitlines() if line.startswith("uid=0(root)")
    ]
    if result.returncode != 0 or len(root_lines) != 2 or "uid=2000(shell)" in result.stdout:
        raise GateError("quoted compound root-shell control failed")
    return {
        "command": "id; id",
        "root_line_count": 2,
        "shell_uid_present": False,
    }


def trigger_one_sysrq_panic(serial: str, run_id: str) -> None:
    marker = f"S22_V3443R_HIGH_RDX_BEGIN run={run_id}"
    command = (
        "set -eu; "
        f"printf '%s\\n' '{marker}' > /dev/kmsg; "
        "printf 1 > /proc/sys/kernel/sysrq; "
        "printf c > /proc/sysrq-trigger"
    )
    try:
        run_quoted_root_command(serial, command)
    except subprocess.TimeoutExpired:
        pass
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        if not adb_connected(serial):
            return
        time.sleep(0.25)
    raise GateError("ADB remained connected after SysRq; panic not proven")


def collect_last_kmsg(serial: str, run_dir: Path, run_id: str) -> dict[str, Any]:
    result = subprocess.run(
        ["adb", "-s", serial, "exec-out", "su", "-c", "cat /proc/last_kmsg"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=60,
        check=False,
    )
    if result.returncode != 0 or not result.stdout:
        raise GateError("failed to collect HIGH /proc/last_kmsg")
    path = run_dir / "post_recovery_last_kmsg.bin"
    rdx.durable_write_bytes(path, result.stdout)
    return summarize_last_kmsg(
        result.stdout, f"S22_V3443R_HIGH_RDX_BEGIN run={run_id}".encode()
    )


def compare_evidence(mid: dict[str, Any], high_result: dict[str, Any]) -> dict[str, Any]:
    mid_counts = mid["last_kmsg"]["signature_counts"]
    high_counts = high_result["last_kmsg"]["signature_counts"]
    return {
        "preamble_changed": (
            high_result["preamble"]["classification"]
            != mid["preamble"]["classification"]
        ),
        "last_kmsg_bytes_delta": high_result["last_kmsg"]["bytes"]
        - mid["last_kmsg"]["bytes"],
        "last_kmsg_lines_delta": high_result["last_kmsg"]["lines"]
        - mid["last_kmsg"]["lines"],
        "signature_count_delta": {
            name: high_counts[name] - mid_counts[name] for name in mid_counts
        },
        "core_evidence_present": all(
            high_counts[name] > 0
            for name in (
                "run_marker",
                "sysrq_panic",
                "rdx_locked",
                "upload_cause_kernel_panic",
            )
        ),
    }


def verify_high_state(state: dict[str, str]) -> None:
    if high.classify_high_state(state) != "HIGH_ACCEPTED":
        raise GateError("Android did not return in exact HIGH state")


def complete_timeline(path: Path, events: list[dict[str, str]]) -> None:
    for name in TIMELINE_NAMES[len(events) :]:
        append_event(path, events, name)


def live_run(root: Path, args: argparse.Namespace, control: dict[str, Any]) -> int:
    if not policy_active(root):
        raise GateError("V3443R policy inactive")
    if args.high_panic_ack != HIGH_PANIC_ACK_TOKEN:
        raise GateError("HIGH panic acknowledgement mismatch")
    if args.preamble_ack != PREAMBLE_ACK_TOKEN:
        raise GateError("preamble-only acknowledgement mismatch")
    if args.recovery_ack != RECOVERY_ACK_TOKEN:
        raise GateError("MID restoration acknowledgement mismatch")

    serial, baseline = high.require_mid_baseline()
    setter = high.resolve(root, args.setter)
    run_dir = root / RUN_ROOT / f"s22plus_v3443r_high_panic_{utc_stamp()}"
    run_dir.mkdir(parents=True, exist_ok=False)
    timeline_path = run_dir / "timeline.json"
    events: list[dict[str, str]] = []
    run_id = hashlib.sha256(os.urandom(32)).hexdigest()[:32]
    result: dict[str, Any] = {
        "schema": SCHEMA,
        "run_id": run_id,
        "baseline": baseline,
        "mid_control": control,
        "candidate_flash": False,
        "rollback_flash": False,
        "panic_attempted": False,
        "probe_sent": False,
        "data_transfer_requested": False,
        "verdict": "INCOMPLETE",
        "timeline_phase_semantics": {
            "candidate_flash_start": "HIGH dispatch; no candidate flash",
            "candidate_flash_done": "HIGH Android returned; no candidate flash",
            "candidate_boot_ready": "HIGH panic RDX observation complete",
            "rollback_flash_start": "physical RDX exit wait then MID restore",
            "rollback_flash_done": "MID dispatch transport dropped; no rollback flash",
            "rollback_boot_ready": "MID Android and hashes reverified",
        },
    }
    append_event(timeline_path, events, "live_session_start")
    durable_write_json(run_dir / "result.json", result)
    high.stage_setter(serial, setter)

    append_event(timeline_path, events, "candidate_flash_start")
    result["high_dispatch"] = high.dispatch_level(serial, "high")
    if not high.wait_adb_absent(25):
        raise GateError("HIGH dispatch did not drop ADB")
    observed = high.wait_android_any(args.android_wait_sec)
    if observed is None:
        raise GateError("HIGH Android did not return; use recovery continuation")
    high_serial, high_state = observed
    verify_high_state(high_state)
    result["high_state"] = high_state
    append_event(timeline_path, events, "candidate_flash_done")
    durable_write_json(run_dir / "result.json", result)

    result["root_compound_shell_control"] = verify_root_compound_shell(high_serial)
    result["panic_attempted"] = True
    durable_write_json(run_dir / "result.json", result)
    trigger_one_sysrq_panic(high_serial, run_id)
    try:
        classification, snapshot = rdx.wait_for_rdx_endpoint(
            run_dir, args.observe_sec
        )
        result["rdx_classification"] = classification
        result["rdx_endpoint_snapshot"] = snapshot
    except Exception as error:
        classification = "RDX_OBSERVATION_ERROR"
        result["rdx_classification"] = classification
        result["rdx_observation_error"] = (
            str(error) if isinstance(error, (GateError, rdx.GateError)) else type(error).__name__
        )
    if classification == "SAMSUNG_SBOOT_RDX_04E8_685D":
        try:
            result["preamble"] = preamble_only(run_dir)
        except Exception as error:
            result["preamble"] = {
                "classification": "PREAMBLE_IO_ERROR_STOPPED",
                "error": str(error) if isinstance(error, GateError) else type(error).__name__,
                "probe_sent": False,
                "data_transfer_requested": False,
            }
    else:
        result["preamble"] = {
            "classification": "NOT_SENT_NO_EXACT_SAMSUNG_RDX",
            "probe_sent": False,
            "data_transfer_requested": False,
        }
    append_event(timeline_path, events, "candidate_boot_ready")
    durable_write_json(run_dir / "result.json", result)

    print(
        "HIGH RDX observation complete. Operator: use physical RDX EXIT now.",
        flush=True,
    )
    append_event(timeline_path, events, "rollback_flash_start")
    recovered = high.wait_android_any(args.recovery_sec)
    if recovered is None:
        raise GateError("HIGH Android did not return after RDX EXIT; use recovery continuation")
    recovered_serial, recovered_high = recovered
    verify_high_state(recovered_high)
    high_result: dict[str, Any] | None = None
    try:
        last_kmsg = collect_last_kmsg(recovered_serial, run_dir, run_id)
        high_result = {"last_kmsg": last_kmsg, "preamble": result["preamble"]}
        result["high_result"] = high_result
        result["comparison"] = compare_evidence(control, high_result)
    except Exception as error:
        result["high_evidence_error"] = (
            str(error) if isinstance(error, GateError) else type(error).__name__
        )
    durable_write_json(run_dir / "result.json", result)

    # Evidence collection must never prevent the mandatory HIGH -> MID cleanup.
    high.stage_setter(recovered_serial, setter)
    result["mid_dispatch"] = high.dispatch_level(recovered_serial, "mid")
    if not high.wait_adb_absent(25):
        raise GateError("MID restore did not drop ADB")
    append_event(timeline_path, events, "rollback_flash_done")
    final_serial, final = high.wait_android_mid(args.recovery_sec)
    high.cleanup_setter(final_serial)
    result["final"] = final
    append_event(timeline_path, events, "rollback_boot_ready")

    preamble_class = result["preamble"]["classification"]
    if high_result is None:
        result["verdict"] = "HIGH_EVIDENCE_COLLECTION_FAILED_BUT_MID_RESTORED"
    elif preamble_class == "POSITIVE_ACK_STOPPED_BEFORE_PROBE":
        result["verdict"] = "HIGH_CHANGED_RDX_PREAMBLE_POSITIVE_STOPPED_AND_MID_RESTORED"
    elif preamble_class == "NEGATIVE_ACK":
        result["verdict"] = "HIGH_RDX_NEGATIVE_ACK_COMPARED_AND_MID_RESTORED"
    else:
        result["verdict"] = "HIGH_RDX_NO_DECISIVE_ACK_COMPARED_AND_MID_RESTORED"
    append_event(timeline_path, events, "live_session_end")
    durable_write_json(run_dir / "result.json", result)
    print(json.dumps({"run_dir": str(run_dir), "verdict": result["verdict"]}, indent=2))
    return 0 if result.get("comparison", {}).get("core_evidence_present") else 10


def emergency_recovery(root: Path, args: argparse.Namespace, from_high: bool) -> dict[str, Any]:
    if not policy_active(root) or args.recovery_ack != RECOVERY_ACK_TOKEN:
        raise GateError("V3443R recovery policy or acknowledgement missing")
    run_dir = root / RUN_ROOT / f"s22plus_v3443r_recovery_{utc_stamp()}"
    run_dir.mkdir(parents=True, exist_ok=False)
    timeline_path = run_dir / "timeline.json"
    events: list[dict[str, str]] = []
    result: dict[str, Any] = {"schema": SCHEMA, "mode": "recovery", "verdict": "INCOMPLETE"}
    for name in TIMELINE_NAMES[:4]:
        append_event(timeline_path, events, name)
    durable_write_json(run_dir / "result.json", result)
    odin = high.resolve(root, args.odin)
    log_path = run_dir / "recovery.log"
    append_event(timeline_path, events, "rollback_flash_start")
    if from_high:
        target, final = high.recover_high_via_download(
            root, odin, log_path, args.manual_wait_sec, args.recovery_sec
        )
    else:
        devices = high.odin_devices(odin, log_path, "v3443r-magisk-continuation")
        if len(devices) != 1:
            raise GateError("Magisk continuation requires exactly one Odin endpoint")
        target = high.rescue.flash_boot_rollback(root, odin, devices[0], log_path)
        if target == "magisk":
            _, final = high.wait_android_mid(args.recovery_sec)
        else:
            final = high.rescue.wait_stock_android(args.recovery_sec)
    append_event(timeline_path, events, "rollback_flash_done")
    append_event(timeline_path, events, "rollback_boot_ready")
    append_event(timeline_path, events, "live_session_end")
    result.update({"rollback_target": target, "final": final})
    result["verdict"] = (
        "PASS_EMERGENCY_MID_AND_MAGISK_RECOVERY"
        if target == "magisk"
        else "STOCK_FALLBACK_CLEANUP"
    )
    durable_write_json(run_dir / "result.json", result)
    return result


def offline_check(root: Path, args: argparse.Namespace) -> dict[str, Any]:
    setter = high.verify_setter(
        root,
        high.resolve(root, args.setter),
        high.resolve(root, args.setter_manifest),
    )
    return {
        "schema": SCHEMA,
        "verdict": "HOST_SOURCE_READY_NO_LIVE_AUTHORIZATION",
        "policy": verify_policy_draft(root),
        "setter": setter,
        "mid_control": verify_mid_control(root),
        "pyusb": rdx.verify_pyusb_runtime(root),
        "device_contact": False,
        "candidate_flash": False,
        "memory_transfer": False,
        "allowed_sboot_commands": ["PrEaMbLe"],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--offline-check", action="store_true")
    modes.add_argument("--dry-run", action="store_true")
    modes.add_argument("--live", action="store_true")
    modes.add_argument("--recover-high-from-download", action="store_true")
    modes.add_argument("--rollback-magisk-from-download", action="store_true")
    parser.add_argument("--high-panic-ack")
    parser.add_argument("--preamble-ack")
    parser.add_argument("--recovery-ack")
    parser.add_argument("--setter", type=Path, default=high.DEFAULT_SETTER)
    parser.add_argument("--setter-manifest", type=Path, default=high.DEFAULT_SETTER_MANIFEST)
    parser.add_argument("--odin", type=Path, default=high.DEFAULT_ODIN)
    parser.add_argument("--observe-sec", type=int, default=120)
    parser.add_argument("--android-wait-sec", type=int, default=180)
    parser.add_argument("--recovery-sec", type=int, default=300)
    parser.add_argument("--manual-wait-sec", type=int, default=300)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = high.repo_root()
    try:
        if args.offline_check:
            print(json.dumps(offline_check(root, args), indent=2, sort_keys=True))
            return 0
        if not policy_active(root):
            raise GateError("V3443R policy inactive")
        high.verify_setter(
            root,
            high.resolve(root, args.setter),
            high.resolve(root, args.setter_manifest),
        )
        if args.recover_high_from_download:
            print(json.dumps(emergency_recovery(root, args, True), indent=2))
            return 0
        if args.rollback_magisk_from_download:
            print(json.dumps(emergency_recovery(root, args, False), indent=2))
            return 0
        control = verify_mid_control(root)
        rdx.verify_pyusb_runtime(root)
        if args.dry_run:
            _, baseline = high.require_mid_baseline()
            print(json.dumps({"baseline": baseline, "mid_control": control}, indent=2))
            return 0
        return live_run(root, args, control)
    except (
        GateError,
        high.GateError,
        high.rescue.GateError,
        rdx.GateError,
        OSError,
        ValueError,
        json.JSONDecodeError,
        subprocess.SubprocessError,
    ) as error:
        print(f"V3443R gate error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
