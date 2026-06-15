#!/usr/bin/env python3
"""V2421 host-only clone-following ACDB payload observer planner.

This unit is source/build/test only. It prepares a future Android/Magisk-root M0
observer that attaches to the audio HAL process before playback and follows
newly-created worker threads with PTRACE_O_TRACECLONE. It does not boot Android,
install a Magisk module, run playback, or issue native calibration ioctls.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import native_audio_acdb_payload_capture_planner_v2415 as v2415
import native_audio_acdb_android_measurement_planner_v2396 as v2396

RUN_ID = "V2421"
BUILD_TAG = "v2421-audio-acdb-clone-follow-observer"
ROOT = v2415.ROOT
HELPER_SOURCE = ROOT / "workspace/public/src/android/acdb_payload_capture/a90_acdb_ioctl_capture_clone_v2421.c"
DEFAULT_HELPER_OUT_DIR = ROOT / "workspace/private/builds/audio/v2421-acdb-clone-follow-helper"
DEFAULT_CC = v2415.DEFAULT_CC
DEFAULT_REMOTE_DIR = "/data/local/tmp/a90-audio-acdb-v2421"
REMOTE_HELPER = f"{DEFAULT_REMOTE_DIR}/a90_acdb_ioctl_capture_clone_v2421"
REMOTE_SCRIPT = f"{DEFAULT_REMOTE_DIR}/a90_acdb_clone_follow_capture.sh"
REMOTE_ARTIFACT_DIR = f"{DEFAULT_REMOTE_DIR}/artifacts"
DEFAULT_DURATION_SEC = 8
DEFAULT_MAX_BYTES = 512
DEFAULT_PROCESS_POLL_SEC = 0.2
APPROVAL_PHRASE = (
    "AUD-5E-acdb-clone-follow-capture go: rollbackable Android AudioTrack speaker "
    "msm_audio_cal ioctl payload capture with clone-following ptrace observer, "
    "transient Magisk-root helper only, no native calibration ioctl, no native speaker write, rollback to V2321"
)


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path | str) -> str:
    return v2415.rel(path)


def file_state(path: Path, *, expected_sha256: str | None = None, require_private: bool = False) -> dict[str, Any]:
    return v2415.file_state(path, expected_sha256=expected_sha256, require_private=require_private)


def source_state() -> dict[str, Any]:
    state = file_state(HELPER_SOURCE, require_private=False)
    if HELPER_SOURCE.exists():
        text = HELPER_SOURCE.read_text(errors="replace")
        state.update({
            "contains_ptrace_attach": "PTRACE_ATTACH" in text,
            "contains_ptrace_traceclone": "PTRACE_O_TRACECLONE" in text,
            "contains_geteventmsg": "PTRACE_GETEVENTMSG" in text,
            "contains_wait_wall": "__WALL" in text,
            "contains_process_vm_readv": "process_vm_readv" in text,
            "contains_ioctl_syscall_filter": "__NR_ioctl" in text,
            "opens_msm_audio_cal": "open(\"/dev/msm_audio_cal" in text or "open('/dev/msm_audio_cal" in text,
            "issues_audio_calibration_ioctl": "AUDIO_SET_CALIBRATION" in text or "AUDIO_ALLOCATE_CALIBRATION" in text,
            "trace_mode": "clone-following",
        })
    return state


def build_capture_helper(out_dir: Path, *, cc: str = DEFAULT_CC) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    os.chmod(out_dir, 0o700)
    output = out_dir / "a90_acdb_ioctl_capture_clone_v2421"
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


def capture_shell_script(duration_sec: int, max_bytes: int, process_poll_sec: float = DEFAULT_PROCESS_POLL_SEC) -> str:
    return f'''#!/system/bin/sh
set -eu
OUT="${{A90_V2421_OUT:-{REMOTE_ARTIFACT_DIR}}}"
HELPER="${{A90_V2421_HELPER:-{REMOTE_HELPER}}}"
DURATION="${{A90_V2421_DURATION:-{duration_sec}}}"
MAX_BYTES="${{A90_V2421_MAX_BYTES:-{max_bytes}}}"
PROCESS_POLL_SEC="${{A90_V2421_PROCESS_POLL_SEC:-{process_poll_sec}}}"
mkdir -p "$OUT"
chmod 700 "$OUT" 2>/dev/null || true
START_TS="$(date +%s)"
END_TS="$((START_TS + DURATION))"
echo "A90_V2421_CAPTURE_BEGIN duration=$DURATION max_bytes=$MAX_BYTES process_poll_sec=$PROCESS_POLL_SEC mode=clone-following" > "$OUT/capture-controller.log"
(ps -A 2>/dev/null || ps 2>/dev/null || true) > "$OUT/ps-before.txt"
HELPER_PIDS=""
SEEN_PIDS="$OUT/seen-pids.txt"
: > "$SEEN_PIDS"
: > "$OUT/helper-pids.txt"

start_helper_for_pid() {{
  pid="$1"
  [ -n "$pid" ] || return 0
  if grep -qx "$pid" "$SEEN_PIDS" 2>/dev/null; then
    return 0
  fi
  now_ts="$(date +%s)"
  remaining="$((END_TS - now_ts))"
  [ "$remaining" -gt 0 ] || return 0
  echo "$pid" >> "$SEEN_PIDS"
  if [ -r "/proc/$pid/maps" ]; then
    cat "/proc/$pid/maps" > "$OUT/proc-$pid-maps.txt" || true
  fi
  if [ -d "/proc/$pid/fd" ]; then
    ls -l "/proc/$pid/fd" > "$OUT/proc-$pid-fd.txt" 2>&1 || true
  fi
  if [ -d "/proc/$pid/task" ]; then
    ls -1 "/proc/$pid/task" > "$OUT/proc-$pid-tasks-initial.txt" 2>&1 || true
  fi
  echo "A90_V2421_HELPER_START pid=$pid remaining=$remaining mode=clone-following" >> "$OUT/capture-controller.log"
  "$HELPER" --pid "$pid" --fd-pid "$pid" --out "$OUT/msm-audio-cal-clone-p${{pid}}.jsonl" --duration-sec "$remaining" --max-bytes "$MAX_BYTES" >> "$OUT/capture-controller.log" 2>&1 &
  helper_pid="$!"
  echo "$helper_pid $pid clone-following" >> "$OUT/helper-pids.txt"
  HELPER_PIDS="$HELPER_PIDS $helper_pid"
}}

while [ "$(date +%s)" -lt "$END_TS" ]; do
  (pidof android.hardware.audio.service 2>/dev/null || true) > "$OUT/audio-hal-pids.txt"
  (pidof audioserver 2>/dev/null || true) > "$OUT/audioserver-pids.txt"
  for pid in $(cat "$OUT/audio-hal-pids.txt" "$OUT/audioserver-pids.txt" 2>/dev/null | tr ' ' '\n' | sort -u); do
    [ -n "$pid" ] || continue
    [ -d "/proc/$pid" ] || continue
    start_helper_for_pid "$pid"
  done
  sleep "$PROCESS_POLL_SEC" 2>/dev/null || sleep 1
done

for helper_pid in $HELPER_PIDS; do
  wait "$helper_pid" || true
done
echo "A90_V2421_CAPTURE_END" >> "$OUT/capture-controller.log"
exit 0
'''


def materialize_capture_bundle(out_dir: Path, *, cc: str, duration_sec: int, max_bytes: int, process_poll_sec: float) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    os.chmod(out_dir, 0o700)
    script_path = out_dir / "a90_acdb_clone_follow_capture.sh"
    script_path.write_text(capture_shell_script(duration_sec, max_bytes, process_poll_sec))
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
        build = materialize_capture_bundle(
            args.helper_out_dir,
            cc=args.cc,
            duration_sec=args.capture_duration_sec,
            max_bytes=args.max_bytes,
            process_poll_sec=args.process_poll_sec,
        )
        state["build"] = build
        state["ok"] = bool(build.get("ok"))
    else:
        binary = args.helper_out_dir / "a90_acdb_ioctl_capture_clone_v2421"
        script = args.helper_out_dir / "a90_acdb_clone_follow_capture.sh"
        state["binary"] = file_state(binary)
        state["controller_script"] = file_state(script)
        state["ok"] = bool(state["source"].get("ok") and state["binary"].get("ok") and state["controller_script"].get("ok"))
        state["reason"] = "clone-follow helper not materialized; rerun with --materialize-capture-helper for future live readiness"
    return state


def adb_base(args: argparse.Namespace) -> list[str]:
    command = [args.adb]
    if args.serial:
        command += ["-s", args.serial]
    return command


def adb_root_shell(args: argparse.Namespace, shell: str) -> list[str]:
    return adb_base(args) + ["shell", "su", "-c", shell]


def adb_push(args: argparse.Namespace, local: str, remote: str) -> list[str]:
    return adb_base(args) + ["push", local, remote]


def stage_commands(args: argparse.Namespace, bundle: dict[str, Any]) -> list[list[str]]:
    binary_path = bundle.get("build", {}).get("binary", {}).get("path") or rel(args.helper_out_dir / "a90_acdb_ioctl_capture_clone_v2421")
    script_path = bundle.get("build", {}).get("controller_script", {}).get("path") or rel(args.helper_out_dir / "a90_acdb_clone_follow_capture.sh")
    return [
        adb_root_shell(args, f"rm -rf {DEFAULT_REMOTE_DIR} && mkdir -p {DEFAULT_REMOTE_DIR} {REMOTE_ARTIFACT_DIR} && chmod 700 {DEFAULT_REMOTE_DIR} {REMOTE_ARTIFACT_DIR}"),
        adb_push(args, binary_path, REMOTE_HELPER),
        adb_push(args, script_path, REMOTE_SCRIPT),
        adb_root_shell(args, f"chmod 700 {REMOTE_HELPER} {REMOTE_SCRIPT} && chmod 700 {REMOTE_ARTIFACT_DIR}"),
    ]


def capture_start_command(args: argparse.Namespace) -> list[str]:
    env = (
        f"A90_V2421_OUT={REMOTE_ARTIFACT_DIR} A90_V2421_DURATION={args.capture_duration_sec} "
        f"A90_V2421_MAX_BYTES={args.max_bytes} A90_V2421_PROCESS_POLL_SEC={args.process_poll_sec}"
    )
    return adb_root_shell(args, f"{env} nohup {REMOTE_SCRIPT} > {REMOTE_ARTIFACT_DIR}/nohup.log 2>&1 & echo $!")


def collect_command(args: argparse.Namespace) -> list[str]:
    return adb_base(args) + ["pull", REMOTE_ARTIFACT_DIR, "<private-run-dir>/device-artifacts"]


def cleanup_commands(args: argparse.Namespace) -> list[list[str]]:
    return [
        adb_root_shell(args, f"rm -rf {DEFAULT_REMOTE_DIR}"),
        adb_base(args) + ["uninstall", "com.a90.nativeinit.audio"],
    ]


def command_safety(plan: dict[str, Any]) -> dict[str, Any]:
    flat = json.dumps(plan.get("commands", {}), sort_keys=True)
    forbidden = {
        "persistent_magisk_install": "magisk --install-module",
        "native_calibration_ioctl": "AUDIO_SET_CALIBRATION",
        "native_allocate_calibration": "AUDIO_ALLOCATE_CALIBRATION",
        "native_tinyplay": "tinyplay",
        "tinymix_set": "tinymix set",
        "raw_partition_write": " dd ",
        "fastboot": "fastboot",
    }
    findings = [name for name, needle in forbidden.items() if needle in flat]
    required = [
        "native_init_flash.py",
        "--post-flash-target",
        "android-adb",
        REMOTE_HELPER,
        REMOTE_SCRIPT,
        "PTRACE_O_TRACECLONE",
        "A90AudioRouteStimulusActivity",
        "rollback_v2321",
    ]
    combined = flat + json.dumps(plan.get("capture_contract", {}), sort_keys=True)
    missing = [needle for needle in required if needle not in combined]
    return {
        "ok": not findings and not missing,
        "findings": findings,
        "missing_required_needles": missing,
        "allowed_observer_tokens": ["PTRACE_O_TRACECLONE", "PTRACE_GETEVENTMSG", "process_vm_readv", "/dev/msm_audio_cal fd match"],
        "forbidden": sorted(forbidden),
    }


def magisk_strategy() -> dict[str, Any]:
    base = v2415.magisk_strategy()
    return {
        "precedent": base["precedent"],
        "default_tier": "M0-clone-following-transient-helper",
        "native_runtime_dependency": False,
        "persistent_install": False,
        "wifi_pattern_applied": "Android/Magisk observes the stock-good producer path; native init receives only bounded reviewed facts",
        "single_observer_semantics": "M0 and any future M1 use the same clone-following ptrace observer; M1 changes delivery timing only, not capture semantics",
        "tiers": [
            {
                "tier": "M0-clone-following-transient-helper",
                "default": True,
                "mechanism": "stage one ptrace observer per audio process under /data/local/tmp; attach before playback and follow new worker TIDs with PTRACE_O_TRACECLONE",
                "addresses_v2420": "stops newly-created worker threads at birth instead of polling /proc/<pid>/task after they already ran",
                "why_first": "lowest-risk Wi-Fi-style measurement capsule: Android boots stock-good, Magisk su runs a transient helper, rollback removes state",
            },
            {
                "tier": "M1-temporary-boot-module",
                "default": False,
                "mechanism": "temporary Magisk post-fs-data.sh/service.sh packaging of the same clone-following observer",
                "gate": "new exact approval and separate V-iteration only if clone-following M0 cannot attach early enough after Android handoff or must exist before the audio HAL process starts",
                "allowed_scope": "early payload observation only; no native runtime dependency; removed by Android-to-V2321 rollback",
                "package_shape": {
                    "module_prop": "private generated metadata only; no repository commit of packaged module",
                    "service_sh": "wait for target audio process, exec clone-following helper, write JSONL under /data/local/tmp or /data/adb/a90-acdb private scratch",
                    "post_fs_data_sh": "optional minimal directory preparation only; no vendor partition writes",
                    "cleanup": "rollback to V2321 plus explicit Android-side rm -rf of scratch paths",
                },
            },
            {
                "tier": "M2-vendor-wrapper",
                "default": False,
                "mechanism": "targeted Android-side vendor process wrapper/probe",
                "gate": "defer unless both clone-following M0 and M1 fail to expose one identified payload edge",
            },
        ],
    }


def dry_run_payload(args: argparse.Namespace) -> dict[str, Any]:
    route_args = v2415.android_args(args)
    android_boot = v2415.route.select_android_boot_candidate()
    rollback = v2415.route.file_state(v2415.route.ROLLBACK_IMAGE, expected_sha256=v2415.route.ROLLBACK_SHA256)
    stimulus = v2415.route.stimulus_apk_state(args.stimulus_apk)
    v2420_report = file_state(ROOT / "docs/reports/NATIVE_INIT_V2420_AUDIO_ACDB_DYNAMIC_M0_LIVE_RERUN_2026-06-15.md", require_private=False)
    bundle = helper_bundle_state(args)
    sealed_boot = "<private-run-dir>/android_boot_0600.img"
    commands = {
        "flash_android": v2415.route.flash_android_command(route_args, sealed_boot),
        "android_post_handoff_settle": v2396.android_post_handoff_settle_commands(args),
        "stage_clone_follow_helper_and_stimulus": stage_commands(args, bundle),
        "baseline_process_inventory": adb_root_shell(args, f"ps -A > {REMOTE_ARTIFACT_DIR}/baseline-ps.txt 2>&1 || true; ls -l /dev/msm_audio_cal > {REMOTE_ARTIFACT_DIR}/baseline-msm-audio-cal.txt 2>&1 || true"),
        "capture_start_background": capture_start_command(args),
        "logcat": {
            "clear": v2415.route.logcat_clear_command(route_args),
            "capture_full": v2415.route.logcat_capture_command(route_args),
            "filter_regex_offline": v2396.LOG_FILTER_REGEX,
            "private_stdout": "<private-run-dir>/clone-follow-logcat.stdout.txt",
        },
        "playback_start_background": v2415.route.playback_start_command(route_args),
        "post_capture_wait_sec": args.capture_duration_sec + 1,
        "collect_private_artifacts": collect_command(args),
        "cleanup": cleanup_commands(args),
        "android_reboot_recovery_for_rollback": v2415.route.android_reboot_recovery_command(route_args),
        "rollback_v2321": v2415.route.rollback_command(route_args),
    }
    plan: dict[str, Any] = {
        "run_id": RUN_ID,
        "build_tag": BUILD_TAG,
        "decision": "v2421-acdb-clone-follow-observer-dry-run",
        "generated_at": now_iso(),
        "host_only": True,
        "device_action": "none",
        "future_live_run_id": "V2422",
        "approval_phrase_required_for_future_live": APPROVAL_PHRASE,
        "v2420_boundary_report": v2420_report,
        "android_boot": android_boot,
        "rollback": rollback,
        "stimulus_apk": stimulus,
        "capture_helper": bundle,
        "capture_contract": {
            "target_device": "/dev/msm_audio_cal",
            "target_processes": ["android.hardware.audio.service", "audioserver"],
            "max_bytes_per_ioctl": args.max_bytes,
            "duration_sec": args.capture_duration_sec,
            "watcher": {
                "mode": "process-attach-plus-PTRACE_O_TRACECLONE",
                "process_poll_env": "A90_V2421_PROCESS_POLL_SEC",
                "default_process_poll_sec": args.process_poll_sec,
                "trace_events": ["PTRACE_EVENT_CLONE"],
                "child_tid_source": "PTRACE_GETEVENTMSG",
                "per_process_output": "msm-audio-cal-clone-p<PID>.jsonl",
            },
            "raw_payload_storage": "workspace/private only",
            "public_report_allowed": ["command numbers", "return codes", "decoded headers", "payload lengths", "payload sha256"],
            "public_report_forbidden": ["raw bytes", "unredacted private Android logs"],
            "native_replay_allowed": False,
        },
        "magisk_strategy": magisk_strategy(),
        "commands": commands,
        "hard_boundary": [
            "V2421 is host-only",
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
    for item_name, item in (
        ("android_boot", android_boot),
        ("rollback", rollback),
        ("stimulus_apk", stimulus),
        ("capture_helper", bundle),
        ("command_safety", safety),
    ):
        if not item.get("ok"):
            blockers.append(f"{item_name} not ready")
    plan["ok"] = bool(v2420_report.get("ok") and source_state().get("ok") and safety.get("ok"))
    plan["future_live_ready"] = not blockers
    plan["future_live_blockers"] = blockers
    return plan


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="emit the V2421 host-only plan; no device action")
    parser.add_argument("--materialize-capture-helper", action="store_true", help="compile private AArch64 clone-follow observer and controller script")
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
    parser.add_argument("--process-poll-sec", type=float, default=DEFAULT_PROCESS_POLL_SEC)
    parser.add_argument("--from-native", action=argparse.BooleanOptionalAction, default=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = dry_run_payload(args)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
