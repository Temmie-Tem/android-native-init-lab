#!/usr/bin/env python3
"""V2415 host-only planner for Android-good msm_audio_cal ioctl payload capture.

This unit does not boot Android and does not execute a live capture.  It turns
V2414's N3 boundary into source-controlled support for the next safe step:
compile/stage a private Android-side ptrace observer, run it only under a future
exact-gated M0 Android/Magisk handoff, capture /dev/msm_audio_cal ioctl request
metadata and private raw hex, then roll back to V2321.

Magisk remains measurement-only.  The helper observes Android's stock-good audio
HAL path; it is not a native-init runtime dependency and it never sends audio
calibration ioctls itself.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import native_audio_acdb_android_measurement_planner_v2396 as v2396
import native_audio_android_route_delta_handoff_v2365 as route


RUN_ID = "V2415"
BUILD_TAG = "v2415-audio-acdb-payload-capture-planner"
NEXT_LIVE_RUN_ID = "V2416"
ROOT = Path(__file__).resolve().parents[5]
HELPER_SOURCE = ROOT / "workspace/public/src/android/acdb_payload_capture/a90_acdb_ioctl_capture_v2415.c"
DEFAULT_HELPER_OUT_DIR = ROOT / "workspace/private/builds/audio/v2415-acdb-payload-capture-helper"
DEFAULT_REMOTE_DIR = "/data/local/tmp/a90-audio-acdb-v2415"
REMOTE_HELPER = f"{DEFAULT_REMOTE_DIR}/a90_acdb_ioctl_capture_v2415"
REMOTE_SCRIPT = f"{DEFAULT_REMOTE_DIR}/a90_acdb_payload_capture.sh"
REMOTE_ARTIFACT_DIR = f"{DEFAULT_REMOTE_DIR}/artifacts"
APPROVAL_PHRASE = (
    "AUD-5D-acdb-payload-capture go: rollbackable Android AudioTrack speaker "
    "msm_audio_cal ioctl payload capture, transient Magisk-root observer only, "
    "no native calibration ioctl, no native speaker write, rollback to V2321"
)
DEFAULT_CC = "aarch64-linux-gnu-gcc"
DEFAULT_DURATION_SEC = 8
DEFAULT_MAX_BYTES = 512


def rel(path: Path | str) -> str:
    candidate = Path(path)
    try:
        return str(candidate.relative_to(ROOT))
    except ValueError:
        return str(path)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fp:
        for chunk in iter(lambda: fp.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def file_state(path: Path, *, expected_sha256: str | None = None, require_private: bool = True) -> dict[str, Any]:
    state: dict[str, Any] = {"path": rel(path), "exists": path.exists()}
    if not path.exists():
        state["ok"] = False
        return state
    mode = path.stat().st_mode
    state.update({
        "size": path.stat().st_size,
        "mode": oct(mode & 0o777),
        "group_or_world_writable": bool(mode & 0o022),
        "sha256": sha256(path),
    })
    if expected_sha256:
        state["expected_sha256"] = expected_sha256
        state["sha256_ok"] = state["sha256"] == expected_sha256
    private_ok = (not state["group_or_world_writable"]) if require_private else True
    state["ok"] = bool(state["size"] > 0 and private_ok and state.get("sha256_ok", True))
    return state


def source_state() -> dict[str, Any]:
    state = file_state(HELPER_SOURCE, require_private=False)
    if HELPER_SOURCE.exists():
        text = HELPER_SOURCE.read_text(errors="replace")
        state["contains_ptrace_attach"] = "PTRACE_ATTACH" in text
        state["contains_process_vm_readv"] = "process_vm_readv" in text
        state["contains_ioctl_syscall_filter"] = "__NR_ioctl" in text
        state["opens_msm_audio_cal"] = "open(\"/dev/msm_audio_cal" in text or "open('/dev/msm_audio_cal" in text
        state["issues_audio_calibration_ioctl"] = "AUDIO_SET_CALIBRATION" in text or "AUDIO_ALLOCATE_CALIBRATION" in text
        state["ok"] = bool(
            state["ok"]
            and state["contains_ptrace_attach"]
            and state["contains_process_vm_readv"]
            and state["contains_ioctl_syscall_filter"]
            and not state["opens_msm_audio_cal"]
            and not state["issues_audio_calibration_ioctl"]
        )
    return state


def build_capture_helper(out_dir: Path, *, cc: str = DEFAULT_CC) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    os.chmod(out_dir, 0o700)
    output = out_dir / "a90_acdb_ioctl_capture_v2415"
    command = [cc, "-O2", "-static", "-s", "-Wall", "-Wextra", "-o", str(output), str(HELPER_SOURCE)]
    completed = subprocess.run(command, cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, timeout=120)
    state: dict[str, Any] = {
        "command": [rel(part) if part.startswith(str(ROOT)) else part for part in command],
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "out_dir": rel(out_dir),
        "binary": file_state(output),
    }
    if output.exists():
        os.chmod(output, 0o700)
        state["binary"] = file_state(output)
        file_completed = subprocess.run(["file", str(output)], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, timeout=30)
        state["file"] = file_completed.stdout.strip()
        state["aarch64_static"] = "ARM aarch64" in state["file"] and "statically linked" in state["file"]
    else:
        state["file"] = ""
        state["aarch64_static"] = False
    state["ok"] = bool(completed.returncode == 0 and state["binary"].get("ok") and state["aarch64_static"])
    return state


def capture_shell_script(duration_sec: int, max_bytes: int) -> str:
    return f'''#!/system/bin/sh
set -eu
OUT="${{A90_V2415_OUT:-{REMOTE_ARTIFACT_DIR}}}"
HELPER="${{A90_V2415_HELPER:-{REMOTE_HELPER}}}"
DURATION="${{A90_V2415_DURATION:-{duration_sec}}}"
MAX_BYTES="${{A90_V2415_MAX_BYTES:-{max_bytes}}}"
mkdir -p "$OUT"
chmod 700 "$OUT" 2>/dev/null || true
echo "A90_V2415_CAPTURE_BEGIN duration=$DURATION max_bytes=$MAX_BYTES" > "$OUT/capture-controller.log"
(ps -A 2>/dev/null || ps 2>/dev/null || true) > "$OUT/ps-before.txt"
(pidof android.hardware.audio.service 2>/dev/null || true) > "$OUT/audio-hal-pids.txt"
(pidof audioserver 2>/dev/null || true) > "$OUT/audioserver-pids.txt"
for pid in $(cat "$OUT/audio-hal-pids.txt" "$OUT/audioserver-pids.txt" 2>/dev/null | tr ' ' '\n' | sort -u); do
  [ -n "$pid" ] || continue
  [ -r "/proc/$pid/maps" ] && cat "/proc/$pid/maps" > "$OUT/proc-$pid-maps.txt" || true
  [ -r "/proc/$pid/fd" ] && ls -l "/proc/$pid/fd" > "$OUT/proc-$pid-fd.txt" 2>&1 || true
  "$HELPER" --pid "$pid" --out "$OUT/msm-audio-cal-ioctl-$pid.jsonl" --duration-sec "$DURATION" --max-bytes "$MAX_BYTES" >> "$OUT/capture-controller.log" 2>&1 || true
done
echo "A90_V2415_CAPTURE_END" >> "$OUT/capture-controller.log"
exit 0
'''


def materialize_capture_bundle(out_dir: Path, *, cc: str, duration_sec: int, max_bytes: int) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    os.chmod(out_dir, 0o700)
    script_path = out_dir / "a90_acdb_payload_capture.sh"
    script_path.write_text(capture_shell_script(duration_sec, max_bytes))
    os.chmod(script_path, 0o700)
    build = build_capture_helper(out_dir, cc=cc)
    manifest = {
        "generated_at": now_iso(),
        "run_id": RUN_ID,
        "source": source_state(),
        "controller_script": file_state(script_path),
        "build": build,
        "private_only": True,
        "note": "Generated helper binary and future raw JSONL payload captures must not be committed.",
    }
    manifest_path = out_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    os.chmod(manifest_path, 0o600)
    manifest["manifest"] = file_state(manifest_path)
    manifest["ok"] = bool(manifest["controller_script"].get("ok") and build.get("ok") and manifest["manifest"].get("ok"))
    return manifest


def helper_bundle_state(args: argparse.Namespace) -> dict[str, Any]:
    state: dict[str, Any] = {
        "out_dir": rel(args.helper_out_dir),
        "materialize_requested": bool(args.materialize_capture_helper),
        "source": source_state(),
        "remote_helper": REMOTE_HELPER,
        "remote_script": REMOTE_SCRIPT,
        "remote_artifact_dir": REMOTE_ARTIFACT_DIR,
    }
    if args.materialize_capture_helper:
        state.update(materialize_capture_bundle(
            args.helper_out_dir,
            cc=args.cc,
            duration_sec=args.capture_duration_sec,
            max_bytes=args.max_bytes,
        ))
    else:
        binary = args.helper_out_dir / "a90_acdb_ioctl_capture_v2415"
        script = args.helper_out_dir / "a90_acdb_payload_capture.sh"
        state["binary"] = file_state(binary)
        state["controller_script"] = file_state(script)
        state["ok"] = bool(state["source"].get("ok") and state["binary"].get("ok") and state["controller_script"].get("ok"))
        state["reason"] = "capture helper not materialized; rerun with --materialize-capture-helper for future live readiness"
    return state


def android_args(args: argparse.Namespace) -> argparse.Namespace:
    return argparse.Namespace(
        adb=args.adb,
        serial=args.serial,
        android_timeout=args.android_timeout,
        from_native=args.from_native,
        stimulus_mode="apk",
        stimulus_dex=None,
        stimulus_apk=args.stimulus_apk,
        duration_ms=args.duration_ms,
        sample_rate=args.sample_rate,
        amplitude=args.amplitude,
        active_delay_sec=args.active_delay_sec,
        post_delay_sec=args.post_delay_sec,
        adb_command_timeout=args.adb_command_timeout,
        flash_timeout=args.flash_timeout,
        approval=None,
        out_dir=None,
    )


def adb_base(args: argparse.Namespace) -> list[str]:
    command = [args.adb]
    if args.serial:
        command.extend(["-s", args.serial])
    return command


def adb_root_shell(args: argparse.Namespace, command: str) -> list[str]:
    return adb_base(args) + ["shell", "su", "-c", command]


def adb_push(args: argparse.Namespace, source: str, destination: str) -> list[str]:
    return adb_base(args) + ["push", source, destination]


def stage_commands(args: argparse.Namespace, bundle: dict[str, Any]) -> list[list[str]]:
    binary_path = bundle.get("build", {}).get("binary", {}).get("path") or rel(args.helper_out_dir / "a90_acdb_ioctl_capture_v2415")
    script_path = bundle.get("controller_script", {}).get("path") or rel(args.helper_out_dir / "a90_acdb_payload_capture.sh")
    return [
        adb_root_shell(args, f"rm -rf {DEFAULT_REMOTE_DIR} && mkdir -p {DEFAULT_REMOTE_DIR} {REMOTE_ARTIFACT_DIR} && chmod 700 {DEFAULT_REMOTE_DIR} {REMOTE_ARTIFACT_DIR}"),
        adb_push(args, binary_path, REMOTE_HELPER),
        adb_push(args, script_path, REMOTE_SCRIPT),
        adb_base(args) + ["install", "-r", rel(args.stimulus_apk)],
        adb_root_shell(args, f"chmod 700 {REMOTE_HELPER} {REMOTE_SCRIPT} && chmod 700 {REMOTE_ARTIFACT_DIR}"),
    ]


def capture_start_command(args: argparse.Namespace) -> list[str]:
    return adb_root_shell(
        args,
        f"A90_V2415_OUT={REMOTE_ARTIFACT_DIR} A90_V2415_DURATION={args.capture_duration_sec} "
        f"A90_V2415_MAX_BYTES={args.max_bytes} nohup {REMOTE_SCRIPT} > {REMOTE_ARTIFACT_DIR}/nohup.log 2>&1 & echo $!",
    )


def collect_command(args: argparse.Namespace) -> list[str]:
    return adb_base(args) + ["pull", REMOTE_ARTIFACT_DIR, "<private-run-dir>/device-artifacts"]


def cleanup_commands(args: argparse.Namespace) -> list[list[str]]:
    return [
        adb_base(args) + ["uninstall", route.APK_PACKAGE],
        adb_root_shell(args, f"rm -rf {DEFAULT_REMOTE_DIR}"),
    ]


def command_safety(plan: dict[str, Any]) -> dict[str, Any]:
    flat = json.dumps(plan.get("commands", plan), sort_keys=True)
    forbidden = {
        "native_calibration_ioctl": "AUDIO_SET_CALIBRATION",
        "native_allocate_calibration": "AUDIO_ALLOCATE_CALIBRATION",
        "persistent_magisk_install": "magisk --install-module",
        "native_tinyplay": "tinyplay",
        "tinymix_set": " tinymix set ",
        "raw_partition_write": " dd if=",
        "fastboot": "fastboot",
    }
    findings = [{"name": name, "needle": needle} for name, needle in forbidden.items() if needle in flat]
    required = [
        "native_init_flash.py",
        "--post-flash-target",
        "android-adb",
        "su",
        REMOTE_HELPER,
        REMOTE_SCRIPT,
        "A90AudioRouteStimulusActivity",
        "rollback_v2321",
    ]
    missing = [needle for needle in required if needle not in flat]
    return {
        "ok": not findings and not missing,
        "findings": findings,
        "missing_required_needles": missing,
        "allowed_observer_tokens": ["ptrace", "process_vm_readv", "ioctl metadata capture", "/dev/msm_audio_cal fd match"],
        "forbidden": sorted(forbidden),
    }


def magisk_strategy() -> dict[str, Any]:
    base = v2396.magisk_strategy()
    return {
        "precedent": base["precedent"],
        "default_tier": "M0-transient-helper",
        "native_runtime_dependency": False,
        "persistent_install": False,
        "wifi_pattern_applied": "Android/Magisk observes the stock-good producer path; native init receives only bounded reviewed facts",
        "tiers": [
            {
                "tier": "M0-transient-helper",
                "default": True,
                "mechanism": "stage the ptrace ioctl observer under /data/local/tmp and run it with adb shell su -c after Android ADB/root settle",
                "captures": [
                    "/dev/msm_audio_cal fd-filtered ioctl command order",
                    "ioctl return codes",
                    "private request-buffer raw hex for offline decoding",
                    "public-safe payload length/hash metadata",
                ],
                "current_unit": "V2416 should use this first",
            },
            {
                "tier": "M1-temporary-boot-module",
                "default": False,
                "mechanism": "temporary post-fs-data.sh/service.sh Magisk module that starts the same observer earlier in Android boot",
                "gate": "new exact approval and separate V-iteration only if M0 classifies missed-early-payload",
                "allowed_scope": "early payload observation only; no native runtime dependency; removed by Android-to-V2321 rollback",
            },
            {
                "tier": "M2-vendor-wrapper",
                "default": False,
                "mechanism": "targeted Android-side vendor process wrapper/probe",
                "gate": "defer unless both M0 and M1 fail to expose the one identified payload edge",
            },
        ],
    }


def dry_run_payload(args: argparse.Namespace) -> dict[str, Any]:
    route_args = android_args(args)
    android_boot = route.select_android_boot_candidate()
    rollback = route.file_state(route.ROLLBACK_IMAGE, expected_sha256=route.ROLLBACK_SHA256)
    stimulus = route.stimulus_apk_state(args.stimulus_apk)
    v2414_report = file_state(ROOT / "docs/reports/NATIVE_INIT_V2414_AUDIO_ACDB_PAYLOAD_REPLAY_DESIGN_2026-06-15.md", require_private=False)
    bundle = helper_bundle_state(args)
    sealed_boot = "<private-run-dir>/android_boot_0600.img"
    commands = {
        "flash_android": route.flash_android_command(route_args, sealed_boot),
        "android_post_handoff_settle": v2396.android_post_handoff_settle_commands(args),
        "stage_capture_helper_and_stimulus": stage_commands(args, bundle),
        "baseline_process_inventory": adb_root_shell(args, f"ps -A > {REMOTE_ARTIFACT_DIR}/baseline-ps.txt 2>&1 || true; ls -l /dev/msm_audio_cal > {REMOTE_ARTIFACT_DIR}/baseline-msm-audio-cal.txt 2>&1 || true"),
        "capture_start_background": capture_start_command(args),
        "logcat": {
            "clear": route.logcat_clear_command(route_args),
            "capture_full": route.logcat_capture_command(route_args),
            "filter_regex_offline": v2396.LOG_FILTER_REGEX,
            "private_stdout": "<private-run-dir>/payload-capture-logcat.stdout.txt",
        },
        "playback_start_background": route.playback_start_command(route_args),
        "post_capture_wait_sec": args.capture_duration_sec + 1,
        "collect_private_artifacts": collect_command(args),
        "cleanup": cleanup_commands(args),
        "android_reboot_recovery_for_rollback": route.android_reboot_recovery_command(route_args),
        "rollback_v2321": route.rollback_command(route_args),
    }
    plan: dict[str, Any] = {
        "run_id": RUN_ID,
        "build_tag": BUILD_TAG,
        "decision": "v2415-acdb-payload-capture-planner-dry-run",
        "generated_at": now_iso(),
        "host_only": True,
        "device_action": "none",
        "future_live_run_id": NEXT_LIVE_RUN_ID,
        "approval_phrase_required_for_future_live": APPROVAL_PHRASE,
        "v2414_boundary_report": v2414_report,
        "android_boot": android_boot,
        "rollback": rollback,
        "stimulus_apk": stimulus,
        "capture_helper": bundle,
        "capture_contract": {
            "target_device": "/dev/msm_audio_cal",
            "target_processes": ["android.hardware.audio.service", "audioserver"],
            "max_bytes_per_ioctl": args.max_bytes,
            "duration_sec": args.capture_duration_sec,
            "raw_payload_storage": "workspace/private only",
            "public_report_allowed": ["command numbers", "return codes", "decoded headers", "payload lengths", "payload sha256"],
            "public_report_forbidden": ["raw bytes", "unredacted private Android logs"],
            "native_replay_allowed": False,
        },
        "magisk_strategy": magisk_strategy(),
        "commands": commands,
        "hard_boundary": [
            "V2415 is host-only",
            "future live capture is Android/Magisk measurement only",
            "no native calibration ioctl",
            "no native speaker write",
            "no persistent Magisk install",
            "raw JSONL bytes remain private",
        ],
    }
    safety = command_safety(plan)
    plan["command_safety"] = safety
    blockers: list[str] = []
    for name, item in (
        ("v2414_boundary_report", v2414_report),
        ("android_boot", android_boot),
        ("rollback", rollback),
        ("stimulus_apk", stimulus),
        ("capture_helper", bundle),
    ):
        if not item.get("ok"):
            blockers.append(f"{name} not ready")
    if not safety.get("ok"):
        blockers.append("command safety failed")
    plan["future_live_ready"] = not blockers
    plan["future_live_blockers"] = blockers
    plan["ok"] = bool(v2414_report.get("ok") and android_boot.get("ok") and rollback.get("ok") and stimulus.get("ok") and safety.get("ok"))
    return plan


def ensure_live_approval(args: argparse.Namespace) -> None:
    if args.approval != APPROVAL_PHRASE:
        raise RuntimeError("exact AUD-5D payload capture approval phrase is required for --run-live")


def run_live_placeholder(args: argparse.Namespace) -> dict[str, Any]:
    ensure_live_approval(args)
    plan = dry_run_payload(args)
    return {
        "run_id": RUN_ID,
        "decision": "v2415-live-not-executed-source-only-capture-plan-ready",
        "ok": True,
        "host_only": True,
        "device_action": "none",
        "approval_phrase_matched": True,
        "future_live_ready": plan.get("future_live_ready"),
        "future_live_blockers": plan.get("future_live_blockers"),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="emit the V2415 host-only plan")
    mode.add_argument("--run-live", action="store_true", help="source-only placeholder; real live capture is future V2416")
    parser.add_argument("--materialize-capture-helper", action="store_true", help="compile private AArch64 capture helper and controller script")
    parser.add_argument("--helper-out-dir", type=Path, default=DEFAULT_HELPER_OUT_DIR)
    parser.add_argument("--cc", default=DEFAULT_CC)
    parser.add_argument("--stimulus-apk", type=Path, default=v2396.DEFAULT_STIMULUS_APK)
    parser.add_argument("--adb", default="adb")
    parser.add_argument("--serial")
    parser.add_argument("--android-timeout", type=float, default=420.0)
    parser.add_argument("--adb-command-timeout", type=float, default=120.0)
    parser.add_argument("--flash-timeout", type=float, default=900.0)
    parser.add_argument("--duration-ms", type=int, default=v2396.DEFAULT_DURATION_MS)
    parser.add_argument("--sample-rate", type=int, default=v2396.DEFAULT_SAMPLE_RATE)
    parser.add_argument("--amplitude", type=float, default=v2396.DEFAULT_AMPLITUDE)
    parser.add_argument("--active-delay-sec", type=float, default=0.75)
    parser.add_argument("--post-delay-sec", type=float, default=1.0)
    parser.add_argument("--capture-duration-sec", type=int, default=DEFAULT_DURATION_SEC)
    parser.add_argument("--max-bytes", type=int, default=DEFAULT_MAX_BYTES)
    parser.add_argument("--from-native", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--approval")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.run_live:
        try:
            payload = run_live_placeholder(args)
        except RuntimeError as error:
            print(str(error), file=os.sys.stderr)
            return 1
    else:
        payload = dry_run_payload(args)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
