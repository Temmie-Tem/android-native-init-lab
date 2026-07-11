#!/usr/bin/env python3
"""Guarded S22+ V3442 HIGH set-only discriminator and MID restoration gate."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import s22plus_v3441_debug_mid_rescue_live_gate as rescue
from s22plus_m3_observable_live_gate import (
    DEFAULT_MAGISK_ROLLBACK_AP,
    DEFAULT_ODIN,
    EXPECTED_MAGISK_AP_SHA256,
    odin_devices,
    repo_root,
    resolve,
    sha256_file,
    wait_for_odin,
)


SCHEMA = "s22plus_v3442_high_set_only_live_gate_v1"
SCRIPT_RELATIVE = Path(
    "workspace/public/src/scripts/revalidation/s22plus_v3442_high_set_only_live_gate.py"
)
POLICY_DRAFT = Path(
    "docs/operations/S22PLUS_V3442_HIGH_SET_ONLY_AGENTS_EXCEPTION_DRAFT_2026-07-11.md"
)
POLICY_MARKER = "S22+ V3442 HIGH set-only live gate"
ACTIVE_SENTINEL = "S22PLUS_V3442_HIGH_SET_ONLY_POLICY_STATE=ACTIVE"
LIVE_ACK_TOKEN = "S22PLUS-V3442-HIGH-SET-ONLY-LIVE"
RECOVERY_ACK_TOKEN = "S22PLUS-V3442-HIGH-RECOVERY-FROM-DOWNLOAD"
MAGISK_ACK_TOKEN = "S22PLUS-V3442-MAGISK-ROLLBACK-FROM-DOWNLOAD"

TARGET = "SM-S906N/g0q/S906NKSS7FYG8"
DEBUG_HIGH_DECIMAL = "18760"
DEBUG_MID_DECIMAL = "18765"
DEBUG_LOW_DECIMAL = "20300"
EXPECTED_SETTER_SHA256 = (
    "5bc230b87d090dcb694cd5eb68eb7e24a0ba5d8d9062cfada817953e5cc6f346"
)
EXPECTED_SETTER_SOURCE_SHA256 = (
    "288cbc53851ee6a29a9b0579d6868aa1cf1fbcb1c7a62cb2b10da9255ccd6339"
)
DEFAULT_SETTER = Path(
    "workspace/private/outputs/s22plus_native_init/"
    "v3442_debug_level_setter_v0_1/s22plus_v3442_debug_level_setter"
)
DEFAULT_SETTER_MANIFEST = Path(
    "workspace/private/outputs/s22plus_native_init/"
    "v3442_debug_level_setter_v0_1/manifest.json"
)
DEFAULT_RESCUE_AP = rescue.DEFAULT_AP
REMOTE_SETTER = "/data/local/tmp/s22plus_v3442_debug_level_setter"
RUN_ROOT = Path("workspace/private/runs")
TIMELINE_NAMES = rescue.TIMELINE_NAMES


class GateError(RuntimeError):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def durable_write_json(path: Path, value: Any) -> None:
    rescue.durable_write_json(path, value)


def append_event(path: Path, events: list[dict[str, str]], name: str) -> None:
    rescue.append_event(path, events, name)


def run(command: list[str], timeout: float = 30.0) -> subprocess.CompletedProcess[str]:
    return rescue.run(command, timeout=timeout)


def adb_serial() -> str:
    return rescue.adb_serial()


def adb_shell(serial: str, command: str, root: bool = False, timeout: float = 30.0) -> str:
    return rescue.adb_shell(serial, command, root=root, timeout=timeout)


def common_android_state() -> tuple[str, dict[str, str]]:
    serial = adb_serial()
    state = {
        "model": adb_shell(serial, "getprop ro.product.model"),
        "device": adb_shell(serial, "getprop ro.product.device"),
        "bootloader": adb_shell(serial, "getprop ro.boot.bootloader"),
        "boot_completed": adb_shell(serial, "getprop sys.boot_completed"),
        "root": adb_shell(serial, "id", root=True),
        "debug_level": adb_shell(
            serial, "cat /sys/module/sec_debug/parameters/debug_level", root=True
        ),
        "boot_debug_level": adb_shell(serial, "getprop ro.boot.debug_level"),
        "boot_reason": adb_shell(serial, "getprop ro.boot.bootreason"),
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
        "boot_sha256": rescue.EXPECTED_BOOT_SHA256,
        "dtbo_sha256": rescue.EXPECTED_DTBO_SHA256,
        "recovery_sha256": rescue.EXPECTED_RECOVERY_SHA256,
    }
    for key, expected_value in expected.items():
        if state[key] != expected_value:
            raise GateError(f"Android identity mismatch: {key}")
    if "uid=0(root)" not in state["root"]:
        raise GateError("Magisk root missing")
    state["root"] = "uid=0(root)"
    return serial, state


def require_mid_baseline() -> tuple[str, dict[str, str]]:
    serial, state = common_android_state()
    if state["debug_level"] != DEBUG_MID_DECIMAL:
        raise GateError("V3442 requires MID baseline")
    return serial, state


def wait_android_any(seconds: int) -> tuple[str, dict[str, str]] | None:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        try:
            return common_android_state()
        except (GateError, rescue.GateError, OSError, subprocess.SubprocessError):
            time.sleep(2)
    return None


def wait_android_mid(seconds: int) -> tuple[str, dict[str, str]]:
    deadline = time.monotonic() + seconds
    last = ""
    while time.monotonic() < deadline:
        try:
            serial, state = common_android_state()
            boot_level = state["boot_debug_level"].strip().lower()
            if (
                state["debug_level"] == DEBUG_MID_DECIMAL
                and "4948" not in boot_level
            ):
                return serial, state
            last = f"debug_level={state['debug_level']}"
        except (
            GateError,
            rescue.GateError,
            OSError,
            subprocess.SubprocessError,
        ) as error:
            last = str(error)
        time.sleep(2)
    raise GateError(f"MID Android did not return: {last}")


def adb_present() -> bool:
    result = run(["adb", "devices"], timeout=10)
    return any(line.strip().endswith("\tdevice") for line in result.stdout.splitlines()[1:])


def wait_adb_absent(seconds: int) -> bool:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if not adb_present():
            return True
        time.sleep(0.5)
    return False


def verify_setter(root: Path, setter: Path, manifest: Path) -> dict[str, Any]:
    if sha256_file(setter) != EXPECTED_SETTER_SHA256:
        raise GateError("V3442 setter SHA mismatch")
    data = json.loads(manifest.read_text(encoding="utf-8"))
    if data.get("schema") != "s22plus_v3442_debug_level_setter_build_v1":
        raise GateError("V3442 setter manifest schema mismatch")
    hashes = data.get("hashes", {})
    if hashes.get("setter") != EXPECTED_SETTER_SHA256:
        raise GateError("V3442 manifest setter hash mismatch")
    if hashes.get("source") != EXPECTED_SETTER_SOURCE_SHA256:
        raise GateError("V3442 manifest source hash mismatch")
    safety = data.get("safety", {})
    expected_safety = {
        "live_authorized": False,
        "valid_arguments": ["high", "mid"],
        "high_reboot_arg": "debug0x4948",
        "mid_reboot_arg": "debug0x494d",
        "valid_path_first_syscall": "reboot",
        "filesystem_syscalls": False,
        "block_write": False,
        "flash": False,
        "panic": False,
        "rdx_protocol": False,
    }
    for key, expected in expected_safety.items():
        if safety.get(key) != expected:
            raise GateError(f"V3442 setter safety mismatch: {key}")
    rescue_artifacts = rescue.verify_artifacts(
        root,
        resolve(root, DEFAULT_RESCUE_AP),
        resolve(root, rescue.DEFAULT_MANIFEST),
    )
    return {
        "setter_sha256": EXPECTED_SETTER_SHA256,
        "setter_source_sha256": EXPECTED_SETTER_SOURCE_SHA256,
        "rescue": rescue_artifacts,
    }


def policy_active(root: Path) -> bool:
    text = (root / "AGENTS.md").read_text(encoding="utf-8")
    required = (
        POLICY_MARKER,
        ACTIVE_SENTINEL,
        str(SCRIPT_RELATIVE),
        sha256_file(root / SCRIPT_RELATIVE),
        LIVE_ACK_TOKEN,
        RECOVERY_ACK_TOKEN,
        MAGISK_ACK_TOKEN,
        EXPECTED_SETTER_SHA256,
        rescue.EXPECTED_AP_SHA256,
        EXPECTED_MAGISK_AP_SHA256,
        "debug0x4948",
        "debug0x494d",
    )
    return all(item in text for item in required)


def verify_policy_draft(root: Path) -> dict[str, Any]:
    path = root / POLICY_DRAFT
    if not path.is_file():
        raise GateError("V3442 policy draft missing")
    text = path.read_text(encoding="utf-8")
    required = (
        "DRAFT_INACTIVE",
        POLICY_MARKER,
        str(SCRIPT_RELATIVE),
        sha256_file(root / SCRIPT_RELATIVE),
        LIVE_ACK_TOKEN,
        RECOVERY_ACK_TOKEN,
        MAGISK_ACK_TOKEN,
        EXPECTED_SETTER_SHA256,
        rescue.EXPECTED_AP_SHA256,
        EXPECTED_MAGISK_AP_SHA256,
    )
    missing = [item for item in required if item not in text]
    if missing:
        raise GateError(f"V3442 policy draft missing pins: {missing}")
    return {"path": str(POLICY_DRAFT), "sha256": sha256_file(path), "active": policy_active(root)}


def stage_setter(serial: str, setter: Path) -> None:
    adb_shell(serial, f"rm -f {REMOTE_SETTER}", root=True)
    pushed = run(["adb", "-s", serial, "push", str(setter), REMOTE_SETTER], timeout=30)
    if pushed.returncode != 0:
        raise GateError("failed to push V3442 setter")
    adb_shell(serial, f"chmod 700 {REMOTE_SETTER}", root=True)
    remote_sha = adb_shell(serial, f"sha256sum {REMOTE_SETTER}", root=True).split()[0]
    if remote_sha != EXPECTED_SETTER_SHA256:
        raise GateError("remote V3442 setter SHA mismatch")


def dispatch_level(serial: str, level: str) -> dict[str, Any]:
    if level not in ("high", "mid"):
        raise GateError("invalid V3442 level")
    try:
        result = run(
            ["adb", "-s", serial, "shell", "su", "-c", f"{REMOTE_SETTER} {level}"],
            timeout=20,
        )
        return {"returncode": result.returncode, "output": result.stdout[-1000:]}
    except subprocess.TimeoutExpired:
        return {"returncode": "timeout-after-dispatch", "output": ""}


def classify_high_state(state: dict[str, str]) -> str:
    level = state["debug_level"]
    boot_level = state["boot_debug_level"].strip().lower()
    if level == DEBUG_HIGH_DECIMAL and "4948" in boot_level:
        return "HIGH_ACCEPTED"
    if level == DEBUG_HIGH_DECIMAL or "4948" in boot_level:
        return "HIGH_PARTIAL_OR_MIXED_ACCEPTANCE"
    if level == DEBUG_MID_DECIMAL:
        return "HIGH_CLAMPED_OR_REJECTED_TO_MID"
    if level == DEBUG_LOW_DECIMAL:
        return "HIGH_CLAMPED_OR_REJECTED_TO_LOW"
    return "HIGH_RESULT_UNKNOWN_LEVEL"


def cleanup_setter(serial: str) -> None:
    try:
        adb_shell(serial, f"rm -f {REMOTE_SETTER}", root=True)
    except (GateError, rescue.GateError, OSError, subprocess.SubprocessError):
        pass


def recover_high_via_download(
    root: Path,
    odin: Path,
    log_path: Path,
    manual_wait_sec: int,
    android_wait_sec: int,
) -> tuple[str, dict[str, str]]:
    print(
        "HIGH Android did not return. Enter physical Download mode for V3441 MID rescue.",
        flush=True,
    )
    first = wait_for_odin(odin, log_path, "v3442-high-recovery", manual_wait_sec)
    if first is None:
        raise GateError("physical Download required for V3441 HIGH recovery")
    rescue.flash_exact(odin, resolve(root, DEFAULT_RESCUE_AP), first, log_path, "v3441-mid-rescue")
    if not rescue.wait_odin_absent(odin, log_path, "v3442-rescue-disconnect", 30):
        raise GateError("V3441 rescue Odin endpoint did not disconnect")
    print(
        "V3441 MID rescue is running. Enter physical Download mode again for Magisk rollback.",
        flush=True,
    )
    second = wait_for_odin(odin, log_path, "v3442-magisk-rollback", manual_wait_sec)
    if second is None:
        raise GateError("second physical Download required for Magisk rollback")
    target = rescue.flash_boot_rollback(root, odin, second, log_path)
    if target != "magisk":
        state = rescue.wait_stock_android(android_wait_sec)
        return "stock", state
    serial, state = wait_android_mid(android_wait_sec)
    cleanup_setter(serial)
    return "magisk", state


def complete_no_reboot_timeline(
    timeline_path: Path, events: list[dict[str, str]], result: dict[str, Any]
) -> None:
    result["timeline_phase_semantics"] = {
        "rollback_flash_start": "no-flash-mid-already-retained",
        "rollback_flash_done": "no-flash-mid-already-retained",
    }
    append_event(timeline_path, events, "rollback_flash_start")
    append_event(timeline_path, events, "rollback_flash_done")
    append_event(timeline_path, events, "rollback_boot_ready")
    append_event(timeline_path, events, "live_session_end")


def emergency_recovery(
    root: Path, args: argparse.Namespace, from_high: bool
) -> dict[str, Any]:
    expected_ack = RECOVERY_ACK_TOKEN if from_high else MAGISK_ACK_TOKEN
    if not policy_active(root) or args.ack != expected_ack:
        raise GateError("V3442 emergency recovery policy or acknowledgement missing")
    run_dir = root / RUN_ROOT / f"s22plus_v3442_emergency_{utc_stamp()}"
    run_dir.mkdir(parents=True, exist_ok=False)
    log_path = run_dir / "recovery.log"
    timeline_path = run_dir / "timeline.json"
    events: list[dict[str, str]] = []
    result: dict[str, Any] = {
        "schema": SCHEMA,
        "mode": "recover-high-from-download" if from_high else "rollback-magisk-from-download",
        "timeline_phase_semantics": {
            "candidate_flash_start": "emergency continuation; no HIGH redispatch",
            "candidate_flash_done": "emergency continuation; no HIGH redispatch",
            "candidate_boot_ready": "operator entered Download before continuation",
        },
        "verdict": "INCOMPLETE",
    }
    append_event(timeline_path, events, "live_session_start")
    append_event(timeline_path, events, "candidate_flash_start")
    append_event(timeline_path, events, "candidate_flash_done")
    append_event(timeline_path, events, "candidate_boot_ready")
    durable_write_json(run_dir / "result.json", result)
    odin = resolve(root, args.odin)
    devices = odin_devices(odin, log_path, "v3442-emergency-start")
    if len(devices) != 1:
        raise GateError(f"emergency recovery requires one Odin device, got {len(devices)}")
    append_event(timeline_path, events, "rollback_flash_start")
    rollback_device = devices[0]
    if from_high:
        rescue.flash_exact(
            odin,
            resolve(root, DEFAULT_RESCUE_AP),
            rollback_device,
            log_path,
            "v3441-mid-rescue",
        )
        if not rescue.wait_odin_absent(
            odin, log_path, "v3442-emergency-rescue-disconnect", 30
        ):
            raise GateError("V3441 rescue endpoint did not disconnect")
        print(
            "V3441 MID rescue is running. Enter Download mode again for Magisk rollback.",
            flush=True,
        )
        rollback_device = wait_for_odin(
            odin, log_path, "v3442-emergency-magisk", args.manual_wait_sec
        )
        if rollback_device is None:
            raise GateError("second Download required for Magisk rollback")
    target = rescue.flash_boot_rollback(root, odin, rollback_device, log_path)
    append_event(timeline_path, events, "rollback_flash_done")
    if target == "magisk":
        serial, state = wait_android_mid(args.android_wait_sec)
        cleanup_setter(serial)
        verdict = "PASS_EMERGENCY_MID_AND_MAGISK_RECOVERY"
    else:
        state = rescue.wait_stock_android(args.android_wait_sec)
        verdict = "STOCK_FALLBACK_CLEANUP_MAGISK_BASELINE_NOT_RESTORED"
    append_event(timeline_path, events, "rollback_boot_ready")
    append_event(timeline_path, events, "live_session_end")
    result.update({"rollback_target": target, "final": state, "verdict": verdict})
    durable_write_json(run_dir / "result.json", result)
    return result


def live_run(root: Path, args: argparse.Namespace, artifacts: dict[str, Any]) -> int:
    if not policy_active(root) or args.ack != LIVE_ACK_TOKEN:
        raise GateError("V3442 live policy or acknowledgement missing")
    serial, baseline = require_mid_baseline()
    setter = resolve(root, args.setter)
    run_dir = root / RUN_ROOT / f"s22plus_v3442_high_set_only_{utc_stamp()}"
    run_dir.mkdir(parents=True, exist_ok=False)
    log_path = run_dir / "live.log"
    timeline_path = run_dir / "timeline.json"
    events: list[dict[str, str]] = []
    result: dict[str, Any] = {
        "schema": SCHEMA,
        "baseline": baseline,
        "artifacts": artifacts,
        "verdict": "INCOMPLETE",
        "high_dispatch_attempted": False,
        "panic": False,
        "rdx_protocol": False,
    }
    append_event(timeline_path, events, "live_session_start")
    durable_write_json(run_dir / "result.json", result)
    stage_setter(serial, setter)

    append_event(timeline_path, events, "candidate_flash_start")
    result["timeline_phase_semantics"] = {
        "candidate_flash_start": "HIGH-set dispatch; no candidate flash",
        "candidate_flash_done": "HIGH-set dispatch returned or transport dropped; no candidate flash",
    }
    result["high_dispatch_attempted"] = True
    durable_write_json(run_dir / "result.json", result)
    result["high_dispatch"] = dispatch_level(serial, "high")
    append_event(timeline_path, events, "candidate_flash_done")

    if not wait_adb_absent(25):
        _, state = require_mid_baseline()
        append_event(timeline_path, events, "candidate_boot_ready")
        result["high_observation"] = state
        result["verdict"] = "HIGH_REBOOT_SYSCALL_RETURNED_OR_REQUEST_REJECTED"
        complete_no_reboot_timeline(timeline_path, events, result)
        cleanup_setter(serial)
        durable_write_json(run_dir / "result.json", result)
        return 10

    observed = wait_android_any(args.high_android_wait_sec)
    if observed is None:
        append_event(timeline_path, events, "candidate_boot_ready")
        result["high_classification"] = "HIGH_ANDROID_DID_NOT_RETURN"
        durable_write_json(run_dir / "result.json", result)
        append_event(timeline_path, events, "rollback_flash_start")
        target, final = recover_high_via_download(
            root,
            resolve(root, args.odin),
            log_path,
            args.manual_wait_sec,
            args.android_wait_sec,
        )
        append_event(timeline_path, events, "rollback_flash_done")
        append_event(timeline_path, events, "rollback_boot_ready")
        result["rollback_target"] = target
        result["final"] = final
        result["verdict"] = (
            "HIGH_ANDROID_TIMEOUT_V3441_RESCUE_AND_MAGISK_ROLLBACK_PASS"
            if target == "magisk"
            else "HIGH_ANDROID_TIMEOUT_STOCK_FALLBACK_CLEANUP"
        )
        append_event(timeline_path, events, "live_session_end")
        durable_write_json(run_dir / "result.json", result)
        return 20 if target == "magisk" else 30

    high_serial, high_state = observed
    append_event(timeline_path, events, "candidate_boot_ready")
    classification = classify_high_state(high_state)
    result["high_observation"] = high_state
    result["high_classification"] = classification
    durable_write_json(run_dir / "result.json", result)

    if (
        high_state["debug_level"] == DEBUG_MID_DECIMAL
        and "4948" not in high_state["boot_debug_level"].strip().lower()
    ):
        result["verdict"] = classification
        complete_no_reboot_timeline(timeline_path, events, result)
        cleanup_setter(high_serial)
        result["final"] = high_state
        durable_write_json(run_dir / "result.json", result)
        return 0

    append_event(timeline_path, events, "rollback_flash_start")
    result["timeline_phase_semantics"]["rollback_flash_start"] = (
        "MID-restore dispatch; no rollback flash"
    )
    stage_setter(high_serial, setter)
    result["mid_dispatch"] = dispatch_level(high_serial, "mid")
    if not wait_adb_absent(25):
        raise GateError("MID restore reboot syscall returned or transport stayed")
    append_event(timeline_path, events, "rollback_flash_done")
    result["timeline_phase_semantics"]["rollback_flash_done"] = (
        "MID-restore transport dropped; no rollback flash"
    )
    final_serial, final = wait_android_mid(args.android_wait_sec)
    cleanup_setter(final_serial)
    append_event(timeline_path, events, "rollback_boot_ready")
    result["final"] = final
    result["verdict"] = f"{classification}_AND_MID_RESTORED"
    append_event(timeline_path, events, "live_session_end")
    durable_write_json(run_dir / "result.json", result)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--offline-check", action="store_true")
    modes.add_argument("--dry-run", action="store_true")
    modes.add_argument("--live", action="store_true")
    modes.add_argument("--recover-high-from-download", action="store_true")
    modes.add_argument("--rollback-magisk-from-download", action="store_true")
    parser.add_argument("--ack")
    parser.add_argument("--setter", type=Path, default=DEFAULT_SETTER)
    parser.add_argument("--setter-manifest", type=Path, default=DEFAULT_SETTER_MANIFEST)
    parser.add_argument("--odin", type=Path, default=DEFAULT_ODIN)
    parser.add_argument("--high-android-wait-sec", type=int, default=120)
    parser.add_argument("--manual-wait-sec", type=int, default=300)
    parser.add_argument("--android-wait-sec", type=int, default=300)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = repo_root()
    try:
        artifacts = verify_setter(
            root, resolve(root, args.setter), resolve(root, args.setter_manifest)
        )
        draft = verify_policy_draft(root)
        if args.offline_check:
            print(
                json.dumps(
                    {"schema": SCHEMA, "artifacts": artifacts, "policy": draft, "device_contact": False},
                    indent=2,
                )
            )
            return 0
        if not policy_active(root):
            raise GateError("V3442 policy inactive")
        if args.recover_high_from_download:
            print(json.dumps(emergency_recovery(root, args, True), indent=2))
            return 0
        if args.rollback_magisk_from_download:
            print(json.dumps(emergency_recovery(root, args, False), indent=2))
            return 0
        if args.dry_run:
            _, baseline = require_mid_baseline()
            print(json.dumps({"artifacts": artifacts, "baseline": baseline}, indent=2))
            return 0
        return live_run(root, args, artifacts)
    except (
        GateError,
        rescue.GateError,
        OSError,
        ValueError,
        json.JSONDecodeError,
        subprocess.SubprocessError,
    ) as error:
        print(f"V3442 gate error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
