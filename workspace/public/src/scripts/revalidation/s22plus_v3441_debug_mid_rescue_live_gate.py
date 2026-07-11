#!/usr/bin/env python3
"""Guarded S22+ V3441 boot-only debug-level MID rescue live gate.

The candidate is a recovery tool, not the HIGH experiment.  It makes one raw
PID1 reboot(2) request for ``debug0x494d`` and may loop until the operator
enters Download mode.  The helper then restores the pinned Magisk boot AP and
requires Android, root, MID, boot, DTBO, and stock recovery identities.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import s22plus_twrp_magisk_restore_window as stock_evidence
from s22plus_m3_observable_live_gate import (
    DEFAULT_MAGISK_ROLLBACK_AP,
    DEFAULT_ODIN,
    EXPECTED_MAGISK_AP_SHA256,
    EXPECTED_MEMBER,
    append_log,
    flash_ap,
    odin_devices,
    repo_root,
    resolve,
    sha256_file,
    tar_members,
    wait_for_odin,
)


SCHEMA = "s22plus_v3441_debug_mid_rescue_live_gate_v1"
SCRIPT_RELATIVE = Path(
    "workspace/public/src/scripts/revalidation/"
    "s22plus_v3441_debug_mid_rescue_live_gate.py"
)
POLICY_DRAFT = Path(
    "docs/operations/"
    "S22PLUS_V3441_DEBUG_MID_RESCUE_AGENTS_EXCEPTION_DRAFT_2026-07-11.md"
)
POLICY_MARKER = "S22+ V3441 debug MID rescue boot-only live gate"
ACTIVE_SENTINEL = "S22PLUS_V3441_DEBUG_MID_RESCUE_POLICY_STATE=ACTIVE"
LIVE_ACK_TOKEN = "S22PLUS-V3441-DEBUG-MID-RESCUE-LIVE"
ROLLBACK_ACK_TOKEN = "S22PLUS-V3441-DEBUG-MID-RESCUE-ROLLBACK"

EXPECTED_TARGET = "SM-S906N/g0q/S906NKSS7FYG8"
EXPECTED_BOOT_SHA256 = (
    "2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e"
)
EXPECTED_DTBO_SHA256 = (
    "97a4864fee4e61892d733962d1ec76f8d14b52bc19e6f47440bc27d9dfc4bd0c"
)
EXPECTED_RECOVERY_SHA256 = (
    "93fac06ca79bf4b365b25a8d49902bc41aba112ea253c30880c90e314d7895d4"
)
EXPECTED_DEBUG_MID = "18765"
EXPECTED_STOCK_BOOT_SHA256 = (
    "4150b962314e6136acba61b20f471d6ee1c418b83cf8c3ee4d9cf7c91a3640ae"
)
EXPECTED_AP_SHA256 = (
    "25a8a5b5cfdeeebd47525c236d975561da8492bb08df5716cfa9da15e00ecfd6"
)
EXPECTED_BOOT_IMAGE_SHA256 = (
    "a41fa0be63628f04b8a832ab9c54cb943ed2ab379a4a58da79ef17904dff2295"
)
EXPECTED_RAW_INIT_SHA256 = (
    "ea25969efca9308a28f18d8702465651205d7ee7503413ea40ab4396f01e6dda"
)
EXPECTED_SOURCE_SHA256 = (
    "15996f265610964c8ea9768a9af84d549819e8bde9fb371d4b438a47f6398075"
)
EXPECTED_KERNEL_SHA256 = (
    "bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff"
)
EXPECTED_REBOOT_ARG = "debug0x494d"
EXPECTED_STOCK_BOOT_AP_SHA256 = (
    "2f6a8ac093587a0f03c423d8e21f65c6fe3a8d2ce9915297170cdaa2cac37c94"
)

DEFAULT_AP = Path(
    "workspace/private/outputs/s22plus_native_init/"
    "v3441_debug_mid_rescue_v0_1/odin4/AP.tar.md5"
)
DEFAULT_MANIFEST = Path(
    "workspace/private/outputs/s22plus_native_init/"
    "v3441_debug_mid_rescue_v0_1/manifest.json"
)
DEFAULT_STOCK_ROLLBACK_AP = Path(
    "workspace/private/outputs/s22plus_native_init/"
    "odin4_stock_rollback_fyg8_raw_repacked_20260709/AP.tar.md5"
)
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
SERIAL_RE = re.compile(r"\b[A-Z0-9]{10,16}\b")


class GateError(RuntimeError):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def redact(text: str) -> str:
    return SERIAL_RE.sub("<S22_SERIAL_REDACTED>", text)


def durable_write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    with temporary.open("w", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)
    directory_fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)


def append_event(path: Path, events: list[dict[str, str]], name: str) -> None:
    if name not in TIMELINE_NAMES:
        raise GateError(f"unknown timeline event: {name}")
    if name in {event["name"] for event in events}:
        raise GateError(f"duplicate timeline event: {name}")
    events.append({"name": name, "timestamp_utc": utc_now()})
    durable_write_json(path, {"events": events})


def run(command: list[str], timeout: float = 30.0) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout,
        check=False,
    )


def adb_serial() -> str:
    result = run(["adb", "devices"])
    if result.returncode != 0:
        raise GateError("adb devices failed")
    rows = [line.split()[0] for line in result.stdout.splitlines()[1:] if line.strip().endswith("\tdevice")]
    if len(rows) != 1:
        raise GateError(f"expected one authorized Android device, found {len(rows)}")
    return rows[0]


def adb_shell(serial: str, command: str, root: bool = False, timeout: float = 30.0) -> str:
    argv = ["adb", "-s", serial, "shell"]
    if root:
        argv.extend(["su", "-c", command])
    else:
        argv.append(command)
    result = run(argv, timeout=timeout)
    if result.returncode != 0:
        raise GateError(f"adb shell failed: {command.split()[0]}")
    return result.stdout.strip()


def current_android() -> tuple[str, dict[str, str]]:
    serial = adb_serial()
    values = {
        "model": adb_shell(serial, "getprop ro.product.model"),
        "device": adb_shell(serial, "getprop ro.product.device"),
        "bootloader": adb_shell(serial, "getprop ro.boot.bootloader"),
        "boot_completed": adb_shell(serial, "getprop sys.boot_completed"),
        "root": adb_shell(serial, "id", root=True),
        "debug_level": adb_shell(
            serial, "cat /sys/module/sec_debug/parameters/debug_level", root=True
        ),
        "boot_sha256": adb_shell(
            serial, "sha256sum /dev/block/by-name/boot", root=True
        ).split()[0],
        "dtbo_sha256": adb_shell(
            serial, "sha256sum /dev/block/by-name/dtbo", root=True
        ).split()[0],
        "recovery_sha256": adb_shell(
            serial, "sha256sum /dev/block/by-name/recovery", root=True
        ).split()[0],
    }
    expected = {
        "model": "SM-S906N",
        "device": "g0q",
        "bootloader": "S906NKSS7FYG8",
        "boot_completed": "1",
        "debug_level": EXPECTED_DEBUG_MID,
        "boot_sha256": EXPECTED_BOOT_SHA256,
        "dtbo_sha256": EXPECTED_DTBO_SHA256,
        "recovery_sha256": EXPECTED_RECOVERY_SHA256,
    }
    for key, expected_value in expected.items():
        if values[key] != expected_value:
            raise GateError(f"Android baseline mismatch: {key}")
    if "uid=0(root)" not in values["root"]:
        raise GateError("Magisk root missing")
    values["root"] = "uid=0(root)"
    return serial, values


def verify_manifest(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") != "s22plus_v3441_debug_mid_rescue_build_v1":
        raise GateError("manifest schema mismatch")
    hashes = data.get("hashes", {})
    expected_hashes = {
        "ap_tar_md5": EXPECTED_AP_SHA256,
        "boot_img": EXPECTED_BOOT_IMAGE_SHA256,
        "raw_mid_rescue_init": EXPECTED_RAW_INIT_SHA256,
        "source": EXPECTED_SOURCE_SHA256,
        "base_boot": EXPECTED_BOOT_SHA256,
        "nochange_repack_boot": EXPECTED_BOOT_SHA256,
        "kernel": EXPECTED_KERNEL_SHA256,
    }
    for key, expected in expected_hashes.items():
        if hashes.get(key) != expected:
            raise GateError(f"manifest hash mismatch: {key}")
    safety = data.get("safety", {})
    required_safety = {
        "boot_only": True,
        "live_flash_authorized": False,
        "first_candidate_action": "raw-reboot-debug0x494d-syscall",
        "reboot_request": EXPECTED_REBOOT_ARG,
        "libc": False,
        "intended_syscalls": ["reboot"],
        "intended_syscall_count": 1,
        "block_write": False,
        "marker_write": False,
        "on_reboot_syscall_return": "infinite-park",
    }
    for key, expected in required_safety.items():
        if safety.get(key) != expected:
            raise GateError(f"manifest safety mismatch: {key}")
    if data.get("tar_members") != [EXPECTED_MEMBER]:
        raise GateError("manifest AP member mismatch")
    return data


def policy_active(root: Path) -> bool:
    text = (root / "AGENTS.md").read_text(encoding="utf-8")
    source_sha = sha256_file(root / SCRIPT_RELATIVE)
    required = (
        POLICY_MARKER,
        ACTIVE_SENTINEL,
        str(SCRIPT_RELATIVE),
        source_sha,
        LIVE_ACK_TOKEN,
        ROLLBACK_ACK_TOKEN,
        EXPECTED_AP_SHA256,
        EXPECTED_BOOT_IMAGE_SHA256,
        EXPECTED_RAW_INIT_SHA256,
        EXPECTED_BOOT_SHA256,
        EXPECTED_REBOOT_ARG,
    )
    return all(item in text for item in required)


def verify_policy_draft(root: Path) -> dict[str, Any]:
    path = root / POLICY_DRAFT
    if not path.is_file():
        raise GateError("V3441 policy draft missing")
    text = path.read_text(encoding="utf-8")
    source_sha = sha256_file(root / SCRIPT_RELATIVE)
    required = (
        "DRAFT_INACTIVE",
        POLICY_MARKER,
        str(SCRIPT_RELATIVE),
        source_sha,
        LIVE_ACK_TOKEN,
        ROLLBACK_ACK_TOKEN,
        EXPECTED_AP_SHA256,
        EXPECTED_BOOT_IMAGE_SHA256,
        EXPECTED_RAW_INIT_SHA256,
        EXPECTED_REBOOT_ARG,
    )
    missing = [item for item in required if item not in text]
    if missing:
        raise GateError(f"policy draft missing pins: {missing}")
    return {"path": str(POLICY_DRAFT), "sha256": sha256_file(path), "active": policy_active(root)}


def verify_artifacts(root: Path, ap: Path, manifest: Path) -> dict[str, Any]:
    if sha256_file(ap) != EXPECTED_AP_SHA256:
        raise GateError("candidate AP SHA mismatch")
    if tar_members(ap) != [EXPECTED_MEMBER]:
        raise GateError("candidate AP is not boot-only")
    data = verify_manifest(manifest)
    magisk = resolve(root, DEFAULT_MAGISK_ROLLBACK_AP)
    stock = resolve(root, DEFAULT_STOCK_ROLLBACK_AP)
    if sha256_file(magisk) != EXPECTED_MAGISK_AP_SHA256 or tar_members(magisk) != [EXPECTED_MEMBER]:
        raise GateError("Magisk rollback AP mismatch")
    if sha256_file(stock) != EXPECTED_STOCK_BOOT_AP_SHA256 or tar_members(stock) != [EXPECTED_MEMBER]:
        raise GateError("stock fallback AP mismatch")
    try:
        stock_evidence.verify_full_firmware_evidence(
            root / stock_evidence.DEFAULT_FULL_FW,
            root / stock_evidence.DEFAULT_FULL_FW_DIR,
            Path(os.devnull),
        )
    except SystemExit as error:
        raise GateError(f"full FYG8 stock evidence failed: {error}") from error
    return {
        "candidate_ap_sha256": EXPECTED_AP_SHA256,
        "manifest_schema": data["schema"],
        "magisk_rollback_ap_sha256": EXPECTED_MAGISK_AP_SHA256,
        "stock_fallback_ap_sha256": EXPECTED_STOCK_BOOT_AP_SHA256,
        "full_fyg8_stock_evidence": True,
    }


def wait_odin_absent(
    odin: Path, log_path: Path, label: str, seconds: int
) -> bool:
    deadline = time.monotonic() + seconds
    while True:
        devices = odin_devices(odin, log_path, label)
        if not devices:
            append_log(log_path, f"{label}_odin_absent=1")
            return True
        if len(devices) > 1:
            raise GateError(
                f"refusing ambiguous Odin devices while waiting for disconnect: {devices}"
            )
        if time.monotonic() >= deadline:
            append_log(log_path, f"{label}_odin_absent=0 still_present={devices}")
            return False
        time.sleep(0.5)


def wait_android(seconds: int) -> tuple[str, dict[str, str]]:
    deadline = time.monotonic() + seconds
    last = ""
    while time.monotonic() < deadline:
        try:
            return current_android()
        except (GateError, subprocess.SubprocessError) as error:
            last = str(error)
            time.sleep(2)
    raise GateError(f"Android did not return: {last}")


def current_stock_android() -> dict[str, str]:
    serial = adb_serial()
    values = {
        "model": adb_shell(serial, "getprop ro.product.model"),
        "device": adb_shell(serial, "getprop ro.product.device"),
        "bootloader": adb_shell(serial, "getprop ro.boot.bootloader"),
        "boot_completed": adb_shell(serial, "getprop sys.boot_completed"),
        "verified_boot_state": adb_shell(
            serial, "getprop ro.boot.verifiedbootstate"
        ),
    }
    expected = {
        "model": "SM-S906N",
        "device": "g0q",
        "bootloader": "S906NKSS7FYG8",
        "boot_completed": "1",
        "verified_boot_state": "orange",
    }
    for key, expected_value in expected.items():
        if values[key] != expected_value:
            raise GateError(f"stock Android fallback mismatch: {key}")
    values["expected_flashed_stock_boot_sha256"] = EXPECTED_STOCK_BOOT_SHA256
    return values


def wait_stock_android(seconds: int) -> dict[str, str]:
    deadline = time.monotonic() + seconds
    last = ""
    while time.monotonic() < deadline:
        try:
            return current_stock_android()
        except (GateError, subprocess.SubprocessError) as error:
            last = str(error)
            time.sleep(2)
    raise GateError(f"stock Android fallback did not return: {last}")


def flash_exact(
    odin: Path, ap: Path, device: str, log_path: Path, label: str
) -> None:
    rc = flash_ap(odin, ap, device, log_path, label)
    if rc != 0:
        raise GateError(f"{label} Odin flash failed rc={rc}")


def flash_boot_rollback(
    root: Path,
    odin: Path,
    device: str,
    log_path: Path,
) -> str:
    try:
        flash_exact(
            odin,
            resolve(root, DEFAULT_MAGISK_ROLLBACK_AP),
            device,
            log_path,
            "magisk-rollback",
        )
        rollback_target = "magisk"
    except GateError:
        fallback_devices = odin_devices(odin, log_path, "v3441-stock-fallback")
        if len(fallback_devices) != 1:
            raise
        flash_exact(
            odin,
            resolve(root, DEFAULT_STOCK_ROLLBACK_AP),
            fallback_devices[0],
            log_path,
            "stock-fallback",
        )
        rollback_target = "stock"
    return rollback_target


def wait_rollback_android(
    rollback_target: str, android_wait_sec: int
) -> tuple[dict[str, str], str, int]:
    if rollback_target == "stock":
        state = wait_stock_android(android_wait_sec)
        verdict = "STOCK_FALLBACK_CLEANUP_MAGISK_BASELINE_NOT_RESTORED"
        rc = 30
    else:
        _, state = wait_android(android_wait_sec)
        verdict = "PASS_MAGISK_ROLLBACK"
        rc = 0
    return state, verdict, rc


def rollback_from_download(root: Path, odin: Path, run_dir: Path) -> dict[str, Any]:
    timeline: list[dict[str, str]] = []
    timeline_path = run_dir / "timeline.json"
    result: dict[str, Any] = {
        "schema": SCHEMA,
        "mode": "rollback-from-download",
        "timeline_phase_semantics": {
            "candidate_flash_start": "recovery-only-session-no-candidate-flash",
            "candidate_flash_done": "recovery-only-session-no-candidate-flash",
            "candidate_boot_ready": "operator-entered-download-before-session",
        },
        "verdict": "INCOMPLETE",
    }
    append_event(timeline_path, timeline, "live_session_start")
    append_event(timeline_path, timeline, "candidate_flash_start")
    append_event(timeline_path, timeline, "candidate_flash_done")
    append_event(timeline_path, timeline, "candidate_boot_ready")
    durable_write_json(run_dir / "result.json", result)
    devices = odin_devices(odin, run_dir / "rollback.log", "v3441-rollback")
    if len(devices) != 1:
        raise GateError(f"rollback requires exactly one Odin device, got {len(devices)}")
    append_event(timeline_path, timeline, "rollback_flash_start")
    rollback_target = flash_boot_rollback(
        root, odin, devices[0], run_dir / "rollback.log"
    )
    append_event(timeline_path, timeline, "rollback_flash_done")
    state, verdict, _ = wait_rollback_android(rollback_target, 300)
    if rollback_target == "magisk":
        verdict = "PASS_MAGISK_ROLLBACK_FROM_DOWNLOAD"
    append_event(timeline_path, timeline, "rollback_boot_ready")
    append_event(timeline_path, timeline, "live_session_end")
    result.update({"target": rollback_target, "android": state, "verdict": verdict})
    durable_write_json(run_dir / "result.json", result)
    return result


def live_run(root: Path, args: argparse.Namespace, artifacts: dict[str, Any]) -> int:
    if not policy_active(root):
        raise GateError("V3441 rescue policy is inactive")
    if args.ack != LIVE_ACK_TOKEN:
        raise GateError("live acknowledgement mismatch")
    serial, baseline = current_android()
    run_dir = root / RUN_ROOT / f"s22plus_v3441_debug_mid_rescue_{utc_stamp()}"
    run_dir.mkdir(parents=True, exist_ok=False)
    result = {
        "schema": SCHEMA,
        "baseline": baseline,
        "artifacts": artifacts,
        "candidate_flash_attempted": False,
        "verdict": "INCOMPLETE",
    }
    timeline: list[dict[str, str]] = []
    timeline_path = run_dir / "timeline.json"
    log_path = run_dir / "live.log"
    append_event(timeline_path, timeline, "live_session_start")
    durable_write_json(run_dir / "result.json", result)

    reboot = run(["adb", "-s", serial, "reboot", "download"], timeout=20)
    if reboot.returncode != 0:
        raise GateError("Android failed to request Download mode")
    odin_device = wait_for_odin(resolve(root, args.odin), run_dir / "live.log", "v3441-candidate", 120)
    if odin_device is None:
        raise GateError("Download mode did not appear")
    append_event(timeline_path, timeline, "candidate_flash_start")
    result["candidate_flash_attempted"] = True
    durable_write_json(run_dir / "result.json", result)
    try:
        flash_exact(
            resolve(root, args.odin),
            resolve(root, args.ap),
            odin_device,
            log_path,
            "candidate",
        )
    except GateError as error:
        result["candidate_flash_error"] = str(error)
        append_event(timeline_path, timeline, "candidate_flash_done")
        result["candidate_boot_ready_semantics"] = (
            "candidate transfer failed; original Odin retained for immediate rollback"
        )
        append_event(timeline_path, timeline, "candidate_boot_ready")
        rollback_devices = odin_devices(
            resolve(root, args.odin), log_path, "v3441-candidate-failed-rollback"
        )
        if len(rollback_devices) != 1:
            durable_write_json(run_dir / "result.json", result)
            raise
        append_event(timeline_path, timeline, "rollback_flash_start")
        target = flash_boot_rollback(
            root,
            resolve(root, args.odin),
            rollback_devices[0],
            log_path,
        )
        append_event(timeline_path, timeline, "rollback_flash_done")
        final, rollback_verdict, rollback_rc = wait_rollback_android(
            target, args.android_wait_sec
        )
        append_event(timeline_path, timeline, "rollback_boot_ready")
        result.update(
            {
                "final": final,
                "rollback_target": target,
                "verdict": f"CANDIDATE_FLASH_FAILED_{rollback_verdict}",
            }
        )
        append_event(timeline_path, timeline, "live_session_end")
        durable_write_json(run_dir / "result.json", result)
        return rollback_rc or 31
    append_event(timeline_path, timeline, "candidate_flash_done")
    if not wait_odin_absent(
        resolve(root, args.odin),
        log_path,
        "v3441-candidate-disconnect",
        30,
    ):
        result["candidate_boot_ready_semantics"] = (
            "original Odin retained; candidate boot not proven; immediate rollback"
        )
        append_event(timeline_path, timeline, "candidate_boot_ready")
        rollback_devices = odin_devices(
            resolve(root, args.odin), log_path, "v3441-odin-stayed-rollback"
        )
        if len(rollback_devices) != 1:
            durable_write_json(run_dir / "result.json", result)
            raise GateError("original Odin stayed but exact rollback target is unavailable")
        append_event(timeline_path, timeline, "rollback_flash_start")
        target = flash_boot_rollback(
            root,
            resolve(root, args.odin),
            rollback_devices[0],
            log_path,
        )
        append_event(timeline_path, timeline, "rollback_flash_done")
        final, rollback_verdict, rollback_rc = wait_rollback_android(
            target, args.android_wait_sec
        )
        append_event(timeline_path, timeline, "rollback_boot_ready")
        result.update(
            {
                "final": final,
                "rollback_target": target,
                "verdict": f"NO_PROOF_ORIGINAL_ODIN_STAYED_{rollback_verdict}",
            }
        )
        append_event(timeline_path, timeline, "live_session_end")
        durable_write_json(run_dir / "result.json", result)
        return rollback_rc or 32
    append_event(timeline_path, timeline, "candidate_boot_ready")
    result["candidate_boot_ready_semantics"] = "original Odin disconnected; raw MID rescue boot window started"
    durable_write_json(run_dir / "result.json", result)

    print(
        "V3441 rescue candidate is running. Operator: enter physical Download mode now; "
        "a reboot loop is expected.",
        flush=True,
    )
    rollback_device = wait_for_odin(
        resolve(root, args.odin), run_dir / "live.log", "v3441-manual-rollback", args.manual_wait_sec
    )
    if rollback_device is None:
        result["verdict"] = "MANUAL_DOWNLOAD_REQUIRED_FOR_ROLLBACK"
        durable_write_json(run_dir / "result.json", result)
        return 20
    append_event(timeline_path, timeline, "rollback_flash_start")
    rollback_target = flash_boot_rollback(
        root,
        resolve(root, args.odin),
        rollback_device,
        log_path,
    )
    append_event(timeline_path, timeline, "rollback_flash_done")
    final, rollback_verdict, rc = wait_rollback_android(
        rollback_target, args.android_wait_sec
    )
    if rollback_target == "magisk":
        verdict = "PASS_RESCUE_BOOT_AND_MAGISK_ROLLBACK_MID"
    else:
        verdict = rollback_verdict
    append_event(timeline_path, timeline, "rollback_boot_ready")
    result["final"] = final
    result["rollback_target"] = rollback_target
    result["verdict"] = verdict
    append_event(timeline_path, timeline, "live_session_end")
    durable_write_json(run_dir / "result.json", result)
    print(json.dumps({"run_dir": str(run_dir), "verdict": result["verdict"], "final": final}, indent=2))
    return rc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--offline-check", action="store_true")
    modes.add_argument("--dry-run", action="store_true")
    modes.add_argument("--live", action="store_true")
    modes.add_argument("--rollback-from-download", action="store_true")
    parser.add_argument("--ack")
    parser.add_argument("--ap", type=Path, default=DEFAULT_AP)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--odin", type=Path, default=DEFAULT_ODIN)
    parser.add_argument("--manual-wait-sec", type=int, default=180)
    parser.add_argument("--android-wait-sec", type=int, default=300)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = repo_root()
    try:
        artifacts = verify_artifacts(root, resolve(root, args.ap), resolve(root, args.manifest))
        draft = verify_policy_draft(root)
        if args.offline_check:
            print(json.dumps({"schema": SCHEMA, "artifacts": artifacts, "policy": draft, "device_contact": False}, indent=2))
            return 0
        if not policy_active(root):
            raise GateError("V3441 rescue policy is inactive")
        if args.rollback_from_download:
            if args.ack != ROLLBACK_ACK_TOKEN:
                raise GateError("rollback acknowledgement mismatch")
            run_dir = root / RUN_ROOT / f"s22plus_v3441_rollback_{utc_stamp()}"
            run_dir.mkdir(parents=True, exist_ok=False)
            print(json.dumps(rollback_from_download(root, resolve(root, args.odin), run_dir), indent=2))
            return 0
        if args.dry_run:
            _, baseline = current_android()
            print(json.dumps({"artifacts": artifacts, "baseline": baseline, "policy_active": True}, indent=2))
            return 0
        return live_run(root, args, artifacts)
    except (
        GateError,
        OSError,
        ValueError,
        json.JSONDecodeError,
        subprocess.SubprocessError,
    ) as error:
        print(f"V3441 gate error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
