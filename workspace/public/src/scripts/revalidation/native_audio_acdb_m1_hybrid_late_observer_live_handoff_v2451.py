#!/usr/bin/env python3
"""V2451 host-only hybrid M1 late-observer handoff for ACDB payload capture.

V2450 proved the V2449 diagnostic helper can trace Android audio processes, but
also proved the temporary Magisk boot service can age out before host-triggered
AudioTrack playback after the long post-module Android ADB/root settle.  This
unit keeps that boot service as an optional early observer and adds a
host-coordinated late observer that starts from the already staged Magisk module
helper after post-module settle and immediately before playback.

The late observer is still Android-good measurement only.  It does not issue
native calibration ioctls, does not write native mixer/PCM state, does not call
`magisk --install-module`, and does not make Magisk a native-init runtime
dependency.
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import native_audio_acdb_android_measurement_planner_v2396 as v2396
import native_audio_acdb_m1_diag_observer_live_handoff_v2450 as v2450
import native_audio_acdb_m1_diag_observer_planner_v2449 as v2449
import native_audio_android_route_delta_handoff_v2365 as route


RUN_ID = "V2451"
BUILD_TAG = "v2451-audio-acdb-m1-hybrid-late-observer"
ROOT = v2450.ROOT
DEFAULT_OUT_BASE = ROOT / "workspace/private/runs/audio"
DEFAULT_LATE_CAPTURE_DURATION_SEC = 60
DEFAULT_LATE_HELPER_COMPLETION_TIMEOUT_SEC = 150.0
DEFAULT_POST_MODULE_BOOT_COMPLETE_TIMEOUT_SEC = 180.0
DEFAULT_STAGE_ADB_RETRY_ATTEMPTS = 3
DEFAULT_STAGE_ADB_RETRY_SLEEP_SEC = 2.0
TRANSIENT_STAGE_ADB_FAILURE_MARKERS = (
    "error: closed",
    "adb: no devices/emulators found",
    "no devices/emulators found",
    "device offline",
    "failed to get feature set",
    "protocol fault",
)
SEMANTIC_STAGE_FAILURE_MARKERS = (
    "A90_M1_RESIDUE_PRESENT",
    "A90_M1_CLEANUP_PROBE_RESIDUE_PRESENT",
    "A90_M1_INSTALL_RESIDUE_PRESENT",
    "A90_M1_INCOMING_FILE_MISSING",
    "A90_M1_INCOMING_SHA_MISMATCH",
    "A90_M1_INCOMING_FILE_COUNT_MISMATCH",
)
APPROVAL_PHRASE = (
    "AUD-5L-acdb-m1-hybrid-late-observer go: rollbackable Android AudioTrack speaker "
    "msm_audio_cal diagnostic ioctl capture with temporary Magisk service module plus "
    "host-coordinated late observer, helper-completion wait, no native calibration ioctl, "
    "no native speaker write, rollback to V2321"
)


def rel(path: Path | str) -> str:
    return v2450.rel(path)


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def default_live_out_dir() -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return DEFAULT_OUT_BASE / f"{RUN_ID.lower()}-acdb-m1-hybrid-late-observer-{stamp}"


def decision_slug() -> str:
    return f"{RUN_ID.lower()}-acdb-m1-hybrid-late-observer"


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def ensure_live_approval(args: argparse.Namespace) -> None:
    if args.approval != APPROVAL_PHRASE:
        raise RuntimeError("exact AUD-5L ACDB M1 hybrid late-observer approval phrase is required for --run-live")


def late_helper_path() -> str:
    return f"{v2450.REMOTE_MODULE_DIR}/bin/{v2449.HELPER_NAME}"


def late_observer_start_command(args: argparse.Namespace) -> list[str]:
    duration = min(int(args.late_capture_duration_sec), v2449.HELPER_MAX_DURATION_SEC)
    max_events = int(args.late_max_events)
    command = f"""
set -eu
ARTIFACT_DIR={shlex.quote(v2449.REMOTE_ARTIFACT_DIR)}
HELPER={shlex.quote(late_helper_path())}
DURATION_SEC={duration}
MAX_BYTES={int(args.max_bytes)}
MAX_EVENTS={max_events}
MAX_UNMATCHED={int(args.max_unmatched_samples)}
MAX_DMABUF_BYTES={v2449.DEFAULT_MAX_DMABUF_BYTES}
LOG="$ARTIFACT_DIR/late-observer.log"
mkdir -p "$ARTIFACT_DIR"
: > "$LOG"
(
  echo A90_M1_LATE_DIAG_BEGIN wall="$(date +%s)" duration_sec="$DURATION_SEC"
  if [ ! -x "$HELPER" ]; then
    echo A90_M1_LATE_DIAG_ERROR helper_not_executable "$HELPER"
    echo A90_M1_LATE_DIAG_END status=helper-missing
    exit 0
  fi
  (ps -A -T -o PID,PPID,TID,USER,NAME,ARGS 2>/dev/null || ps -A 2>/dev/null || true) > "$ARTIFACT_DIR/late-ps-before.txt"
  : > "$ARTIFACT_DIR/late-helper-pids.txt"
  pids=""
  for name in android.hardware.audio.service audioserver; do
    found="$(pidof "$name" 2>/dev/null || true)"
    if [ -n "$found" ]; then
      pids="$pids $found"
    fi
  done
  helper_count=0
  for pid in $pids; do
    case "$pid" in ''|*[!0-9]*) continue ;; esac
    if [ ! -d "/proc/$pid" ]; then
      echo A90_M1_LATE_DIAG_PID_GONE tgid="$pid"
      continue
    fi
    target_dir="$ARTIFACT_DIR/late-proc-$pid"
    mkdir -p "$target_dir"
    cat "/proc/$pid/status" > "$target_dir/status.txt" 2>/dev/null || true
    ls -l "/proc/$pid/fd" > "$target_dir/fd.txt" 2>&1 || true
    ls "/proc/$pid/task" > "$target_dir/task.txt" 2>&1 || true
    "$HELPER" \
      --tgid "$pid" \
      --fd-pid "$pid" \
      --device-substr /dev/msm_audio_cal \
      --out "$ARTIFACT_DIR/msm-audio-cal-diag-threadset-p${{pid}}-late.jsonl" \
      --duration-sec "$DURATION_SEC" \
      --max-bytes "$MAX_BYTES" \
      --max-events "$MAX_EVENTS" \
      --dmabuf-out-dir "$ARTIFACT_DIR/dmabuf-late" \
      --max-dmabuf-bytes "$MAX_DMABUF_BYTES" \
      --max-unmatched-samples "$MAX_UNMATCHED" \
      > "$ARTIFACT_DIR/late-helper-$pid.log" 2>&1 &
    helper_pid="$!"
    helper_count="$((helper_count + 1))"
    echo "$helper_pid $pid late-diagnostic" >> "$ARTIFACT_DIR/late-helper-pids.txt"
    echo A90_M1_LATE_DIAG_HELPER_START tgid="$pid" helper_pid="$helper_pid"
  done
  echo A90_M1_LATE_DIAG_HELPER_COUNT count="$helper_count"
  if [ "$helper_count" = "0" ]; then
    echo A90_M1_LATE_DIAG_END status=no-target-pids
    exit 0
  fi
  echo A90_M1_LATE_DIAG_HELPER_WAIT_BEGIN
  while read -r helper_pid target_pid mode; do
    [ -n "$helper_pid" ] || continue
    rc=0
    wait "$helper_pid" || rc="$?"
    echo A90_M1_LATE_DIAG_HELPER_WAIT_DONE tgid="$target_pid" helper_pid="$helper_pid" rc="$rc" mode="$mode"
  done < "$ARTIFACT_DIR/late-helper-pids.txt"
  echo A90_M1_LATE_DIAG_END status=complete
) >> "$LOG" 2>&1 &
echo A90_M1_LATE_DIAG_SUPERVISOR_STARTED log="$LOG"
"""
    return v2450.adb_su_shell(args, command)


def late_helper_completion_wait_command(args: argparse.Namespace) -> list[str]:
    timeout = int(args.late_helper_completion_timeout_sec)
    command = f"""
set -eu
ARTIFACT_DIR={shlex.quote(v2449.REMOTE_ARTIFACT_DIR)}
LOG="$ARTIFACT_DIR/late-observer.log"
TIMEOUT_SEC={timeout}
DEADLINE="$(( $(date +%s) + TIMEOUT_SEC ))"
echo A90_M1_LATE_DIAG_WAIT_BEGIN timeout_sec="$TIMEOUT_SEC"
while [ "$(date +%s)" -le "$DEADLINE" ]; do
  late_jsonl_count=0
  late_stop_count=0
  for path in "$ARTIFACT_DIR"/msm-audio-cal-diag-threadset-p*-late.jsonl; do
    [ -f "$path" ] || continue
    late_jsonl_count="$((late_jsonl_count + 1))"
    if grep -q '"event":"stop"' "$path" 2>/dev/null; then
      late_stop_count="$((late_stop_count + 1))"
    fi
  done
  if [ -f "$LOG" ] && grep -q 'A90_M1_LATE_DIAG_END' "$LOG"; then
    if [ "$late_jsonl_count" = "$late_stop_count" ]; then
      echo A90_M1_LATE_DIAG_WAIT_OK jsonl_count="$late_jsonl_count" stop_count="$late_stop_count"
    else
      echo A90_M1_LATE_DIAG_WAIT_PARTIAL jsonl_count="$late_jsonl_count" stop_count="$late_stop_count"
    fi
    exit 0
  fi
  sleep 1
done
echo A90_M1_LATE_DIAG_WAIT_TIMEOUT
if [ -f "$LOG" ]; then tail -80 "$LOG" 2>/dev/null || true; fi
exit 0
"""
    return v2450.adb_su_shell(args, command)


def needs_stage_adb_wait(command: list[str]) -> bool:
    return v2450.adb_subcommand(command) in {"shell", "push", "install"}


def stage_wait_plan(args: argparse.Namespace) -> list[dict[str, Any]]:
    waits: list[dict[str, Any]] = []
    for index, command in enumerate(v2450.stage_commands(args)):
        subcommand = v2450.adb_subcommand(command)
        if subcommand and needs_stage_adb_wait(command):
            waits.append(
                {
                    "before_stage_index": index,
                    "reason": f"stabilize ADB before staged adb {subcommand}",
                    "command": v2450.stage_wait_command(args),
                    "stage_subcommand": subcommand,
                }
            )
    return waits


def stage_adb_retry_attempts(args: argparse.Namespace) -> int:
    return max(1, int(getattr(args, "stage_adb_retry_attempts", DEFAULT_STAGE_ADB_RETRY_ATTEMPTS)))


def stage_adb_retry_sleep_sec(args: argparse.Namespace) -> float:
    return max(0.0, float(getattr(args, "stage_adb_retry_sleep_sec", DEFAULT_STAGE_ADB_RETRY_SLEEP_SEC)))


def stage_adb_retry_plan(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "enabled": stage_adb_retry_attempts(args) > 1,
        "attempts": stage_adb_retry_attempts(args),
        "sleep_sec": stage_adb_retry_sleep_sec(args),
        "scope": "staged adb shell/push/install only, before module reboot/playback",
        "retry_markers": list(TRANSIENT_STAGE_ADB_FAILURE_MARKERS),
        "semantic_stop_markers": list(SEMANTIC_STAGE_FAILURE_MARKERS),
        "v2464_gap": "stage-2 failed with adb 'error: closed' after wait-for-device returned",
    }


def step_output_text(step: dict[str, Any]) -> str:
    parts: list[str] = []
    for key in ("stdout", "stderr"):
        value = step.get(key)
        if not isinstance(value, str) or not value:
            continue
        path = Path(value)
        if not path.is_absolute():
            path = ROOT / path
        try:
            parts.append(path.read_text(errors="replace"))
        except OSError:
            continue
    return "\n".join(parts)


def stage_step_has_semantic_failure(step: dict[str, Any]) -> bool:
    text = step_output_text(step)
    return any(marker in text for marker in SEMANTIC_STAGE_FAILURE_MARKERS)


def stage_step_has_transient_adb_failure(step: dict[str, Any]) -> bool:
    if step.get("ok"):
        return False
    if stage_step_has_semantic_failure(step):
        return False
    lower_text = step_output_text(step).lower()
    return any(marker.lower() in lower_text for marker in TRANSIENT_STAGE_ADB_FAILURE_MARKERS)


def checked_stage_failure_message(index: int, step: dict[str, Any]) -> str:
    rc = step.get("rc", "unknown")
    return f"stage-{index} failed rc={rc}; see {step.get('stdout')} {step.get('stderr')}"


def run_stage_command_with_adb_retry(
    args: argparse.Namespace,
    index: int,
    command: list[str],
    out_dir: Path,
    steps: list[dict[str, Any]],
) -> dict[str, Any]:
    attempts = stage_adb_retry_attempts(args)
    sleep_sec = stage_adb_retry_sleep_sec(args)
    subcommand = v2450.adb_subcommand(command) or "unknown"
    last_step: dict[str, Any] | None = None
    for attempt in range(1, attempts + 1):
        if needs_stage_adb_wait(command):
            steps.append(route.run_step(
                f"stage-{index}-attempt-{attempt}-adb-wait-before-{subcommand}",
                v2450.stage_wait_command(args),
                out_dir,
                timeout_sec=args.adb_command_timeout,
                check=False,
            ))
        step = route.run_step(
            f"stage-{index}-attempt-{attempt}",
            command,
            out_dir,
            timeout_sec=args.adb_command_timeout,
            check=False,
        )
        steps.append(step)
        last_step = step
        if step.get("ok"):
            return step
        if not stage_step_has_transient_adb_failure(step):
            raise RuntimeError(checked_stage_failure_message(index, step))
        if attempt < attempts:
            time.sleep(sleep_sec)
    assert last_step is not None
    raise RuntimeError(
        f"stage-{index} transient ADB transport failure persisted after {attempts} attempts; "
        f"see {last_step.get('stdout')} {last_step.get('stderr')}"
    )


def post_module_boot_complete_soft_command(args: argparse.Namespace) -> list[str]:
    timeout = int(args.post_module_boot_complete_timeout_sec)
    command = f"""
set -eu
TIMEOUT_SEC={timeout}
DEADLINE="$(( $(date +%s) + TIMEOUT_SEC ))"
sys=""
dev=""
echo A90_POST_MODULE_BOOT_COMPLETE_WAIT_BEGIN timeout_sec="$TIMEOUT_SEC"
while [ "$(date +%s)" -le "$DEADLINE" ]; do
  sys="$(getprop sys.boot_completed 2>/dev/null || true)"
  dev="$(getprop dev.bootcomplete 2>/dev/null || true)"
  if [ "$sys" = "1" ] || [ "$dev" = "1" ]; then
    echo A90_POST_MODULE_BOOT_COMPLETE_READY sys="$sys" dev="$dev"
    exit 0
  fi
  sleep 1
done
echo A90_POST_MODULE_BOOT_COMPLETE_NOT_READY sys="$sys" dev="$dev"
exit 1
"""
    return v2396.adb_shell(args, command)


def post_module_reboot_settle_plan(args: argparse.Namespace) -> dict[str, Any]:
    commands = v2396.android_post_handoff_settle_commands(args)
    return {
        "initial_wait_for_device": commands[0],
        "boot_complete_soft_recheck": post_module_boot_complete_soft_command(args),
        "boot_complete_soft_gate": True,
        "boot_complete_timeout_sec": args.post_module_boot_complete_timeout_sec,
        "root_check": commands[2],
        "root_check_hard_gate": True,
        "root_retry_attempts": args.post_module_root_retry_attempts,
        "root_retry_sleep_sec": args.post_module_root_retry_sleep_sec,
        "adb_wait_timeout_sec": args.post_module_adb_wait_timeout,
        "v2454_observed_wait_for_device_sec": 207.631,
        "classification": (
            "V2455 keeps long post-module ADB reacquire, records boot-complete as "
            "soft telemetry, and still requires Magisk uid=0 before late observer/playback"
        ),
    }


def run_post_module_reboot_settle(
    args: argparse.Namespace,
    out_dir: Path,
    steps: list[dict[str, Any]],
) -> None:
    commands = v2396.android_post_handoff_settle_commands(args)
    steps.append(route.run_step(
        "android-post-module-reboot-settle-0-wait-for-device",
        commands[0],
        out_dir,
        timeout_sec=args.post_module_adb_wait_timeout,
    ))
    boot_record = route.run_step(
        "android-post-module-reboot-settle-1-boot-complete-soft",
        post_module_boot_complete_soft_command(args),
        out_dir,
        timeout_sec=float(args.post_module_boot_complete_timeout_sec) + 10.0,
        check=False,
    )
    boot_record["soft_gate"] = True
    boot_record["boot_complete_ready"] = boot_record.get("rc") == 0
    steps.append(boot_record)

    last_record: dict[str, Any] | None = None
    attempts = max(1, int(args.post_module_root_retry_attempts))
    for attempt in range(1, attempts + 1):
        wait_record = route.run_step(
            f"android-post-module-reboot-root-wait-{attempt}",
            commands[0],
            out_dir,
            timeout_sec=args.post_module_adb_wait_timeout,
            check=False,
        )
        steps.append(wait_record)
        root_record = route.run_step(
            f"android-post-module-reboot-root-check-{attempt}",
            commands[2],
            out_dir,
            timeout_sec=args.adb_command_timeout,
            check=False,
        )
        steps.append(root_record)
        last_record = root_record
        summary = v2396.android_root_recheck_summary(root_record)
        summary["attempt"] = attempt
        summary["max_attempts"] = attempts
        root_record["root_recheck"] = summary
        root_record["root_ready"] = summary["root_ready"]
        if summary["root_ready"]:
            root_record["settle_decision"] = "post-module-root-ready"
            return
        root_record["settle_decision"] = summary["classification"]
        if attempt != attempts:
            time.sleep(float(args.post_module_root_retry_sleep_sec))

    raise RuntimeError(
        "post-module Android root recheck did not report uid=0 after "
        f"{attempts} attempts; classification="
        f"{last_record.get('root_recheck', {}).get('classification') if last_record else 'no-root-attempt'}; "
        f"see {last_record.get('stdout') if last_record else 'no root attempt'} "
        f"{last_record.get('stderr') if last_record else ''}"
    )


def summarize_late_subset(out_dir: Path) -> dict[str, Any]:
    artifact_root = out_dir / "device-artifacts"
    late_logs = sorted(artifact_root.rglob("late-observer.log")) if artifact_root.exists() else []
    late_jsonl_files = sorted(artifact_root.rglob("msm-audio-cal-diag-threadset-p*-late.jsonl")) if artifact_root.exists() else []
    summary: dict[str, Any] = {
        "late_logs": [rel(path) for path in late_logs],
        "late_jsonl_files": [rel(path) for path in late_jsonl_files],
        "late_jsonl_file_count": len(late_jsonl_files),
        "helper_starts": 0,
        "helper_count_markers": [],
        "wait_done_markers": [],
        "wait_markers": [],
        "missing_stop_files": [],
        "ioctl_entries": 0,
        "ioctl_any_entry_count": 0,
        "ioctl_fd_match_count": 0,
        "ioctl_fd_miss_count": 0,
        "fd_readlink_error_count": 0,
        "mmap_entry_count": 0,
        "mmap_success_count": 0,
        "mmap_error_count": 0,
        "mmap_record_count": 0,
        "mmap_events": [],
        "syscall_stop_count": 0,
        "payload_hashes": [],
        "dmabuf_payload_hashes": [],
        "dmabuf_capture_events": [],
        "raw_payload_in_summary": False,
        "raw_dmabuf_in_summary": False,
    }
    for log in late_logs:
        for line in log.read_text(errors="replace").splitlines():
            if "A90_M1_LATE_DIAG_" in line:
                summary["wait_markers"].append(line[:240])
            if "A90_M1_LATE_DIAG_HELPER_START" in line:
                summary["helper_starts"] += 1
            if "A90_M1_LATE_DIAG_HELPER_COUNT" in line:
                summary["helper_count_markers"].append(line[:240])
            if "A90_M1_LATE_DIAG_HELPER_WAIT_DONE" in line:
                summary["wait_done_markers"].append(line[:240])

    for path in late_jsonl_files:
        has_stop = False
        for event in v2450.parse_jsonl(path):
            kind = event.get("event")
            if kind == "ioctl_entry":
                summary["ioctl_entries"] += 1
                digest = v2450.payload_sha256(str(event.get("bytes_hex", "")))
                if digest:
                    summary["payload_hashes"].append(
                        {
                            "file": rel(path),
                            "seq": event.get("seq"),
                            "request": str(event.get("request", "")),
                            "read_len": event.get("read_len"),
                            "sha256": digest,
                        }
                    )
            elif kind == "dmabuf_capture":
                if len(summary["dmabuf_capture_events"]) < 16:
                    summary["dmabuf_capture_events"].append(
                        {
                            "file": rel(path),
                            "seq": event.get("seq"),
                            "status": event.get("status"),
                            "cal_type": event.get("cal_type"),
                            "cal_size": event.get("cal_size"),
                            "mem_handle": event.get("mem_handle"),
                            "capture_len": event.get("capture_len"),
                            "written_len": event.get("written_len"),
                            "open_errno": event.get("open_errno"),
                            "mmap_errno": event.get("mmap_errno"),
                            "write_errno": event.get("write_errno"),
                        }
                    )
            elif kind in {"mmap_entry", "mmap_exit"}:
                if len(summary["mmap_events"]) < 24:
                    summary["mmap_events"].append(
                        {
                            "file": rel(path),
                            "event": kind,
                            "seq": event.get("seq"),
                            "fd": event.get("fd"),
                            "length": event.get("length"),
                            "ret": event.get("ret"),
                            "status": event.get("status"),
                            "fd_target": event.get("fd_target"),
                        }
                    )
            elif kind == "stop":
                has_stop = True
                for key in (
                    "syscall_stop_count",
                    "ioctl_any_entry_count",
                    "ioctl_fd_match_count",
                    "ioctl_fd_miss_count",
                    "fd_readlink_error_count",
                    "mmap_entry_count",
                    "mmap_success_count",
                    "mmap_error_count",
                    "mmap_record_count",
                ):
                    value = event.get(key)
                    if isinstance(value, int):
                        summary[key] += value
        if not has_stop:
            summary["missing_stop_files"].append(rel(path))

    summary["payload_hashes"] = summary["payload_hashes"][:64]
    summary["dmabuf_payload_hashes"] = v2450.summarize_dmabuf_payload_files(artifact_root)[:64]
    summary["dmabuf_payload_count"] = len(summary["dmabuf_payload_hashes"])
    if summary["dmabuf_payload_hashes"]:
        classification = "late-msm-audio-cal-dmabuf-payload-captured"
    elif summary["ioctl_entries"] > 0:
        classification = "late-msm-audio-cal-payload-captured"
    elif summary["missing_stop_files"]:
        classification = "late-partial-helper-still-running"
    elif summary["ioctl_any_entry_count"] > 0 and summary["ioctl_fd_match_count"] == 0 and summary["ioctl_fd_miss_count"] > 0:
        classification = "late-ioctl-any-but-fd-miss"
    elif summary["syscall_stop_count"] > 0 and summary["ioctl_any_entry_count"] == 0:
        classification = "late-syscall-stops-no-ioctl"
    elif summary["helper_starts"] > 0:
        classification = "late-helper-started-no-syscall-evidence"
    elif late_logs:
        classification = "late-observer-started-no-target-pids"
    else:
        classification = "late-observer-artifact-missing"
    summary["classification"] = classification
    return summary


def summarize_hybrid_capture_artifacts(out_dir: Path) -> dict[str, Any]:
    summary = v2450.summarize_diag_capture_artifacts(out_dir)
    summary["late_observer"] = summarize_late_subset(out_dir)
    late_classification = summary["late_observer"].get("classification")
    if late_classification in {
        "late-msm-audio-cal-payload-captured",
        "late-msm-audio-cal-dmabuf-payload-captured",
    }:
        summary["classification"] = late_classification
    elif summary.get("classification") == "partial-helper-still-running" and late_classification:
        summary["classification"] = f"hybrid-{late_classification}"
    return summary


def command_safety(payload: dict[str, Any]) -> dict[str, Any]:
    flat = json.dumps(payload.get("commands", payload), sort_keys=True)
    forbidden = {
        "magisk_install_module": "magisk --install-module",
        "post_fs_data": "post-fs-data.sh",
        "native_tinyplay": "tinyplay",
        "native_tinymix_set": "tinymix set",
        "native_calibration_ioctl_symbol": "AUDIO_SET_CALIBRATION",
        "fastboot": "fastboot",
        "raw_partition_write": " dd ",
        "broad_modules_rm_rf": "rm -rf /data/adb/modules",
        "broad_modules_rm_r": "rm -r /data/adb/modules",
    }
    findings = [{"name": name, "needle": needle} for name, needle in forbidden.items() if needle in flat]
    required = [
        v2450.REMOTE_MODULE_DIR,
        v2449.HELPER_NAME,
        "su -c",
        "su -mm -c",
        "A90_M1_RESIDUE_CHECK_OK",
        "A90_M1_INSTALL_OK",
        "A90_M1_LATE_DIAG_BEGIN",
        "A90_M1_LATE_DIAG_SUPERVISOR_STARTED",
        "A90_M1_LATE_DIAG_WAIT",
        "msm-audio-cal-diag-threadset-p${pid}-late.jsonl",
        "--fd-pid",
        "/dev/msm_audio_cal",
        "A90_M1_CLEANUP_OK",
        "adb\", \"reboot",
        "rollback_v2321",
        v2449.REMOTE_ARTIFACT_DIR,
    ]
    missing = [needle for needle in required if needle not in flat]
    return {
        "ok": not findings and not missing,
        "findings": findings,
        "missing_required_needles": missing,
        "forbidden": sorted(forbidden),
        "required": required,
    }


def dry_run(args: argparse.Namespace) -> dict[str, Any]:
    args.materialize_module_template = bool(args.materialize_module_template)
    base = v2450.dry_run(args)
    route_args = v2396.android_args(args)
    commands = dict(base["commands"])
    commands["android_post_module_reboot_settle"] = post_module_reboot_settle_plan(args)
    commands["start_late_diag_observer_after_post_module_settle"] = late_observer_start_command(args)
    commands["wait_for_late_diag_helper_completion"] = late_helper_completion_wait_command(args)
    commands["playback_order"] = [
        "post-module ADB/root settle",
        "start late observer supervisor",
        "clear/start logcat",
        "launch AudioTrack playback",
        "wait for playback result",
        "wait for late observer terminal stop",
        "pull private artifacts",
        "cleanup module",
        "rollback_v2321",
    ]
    base["commands"] = commands
    base["stage_adb_waits"] = stage_wait_plan(args)
    base["stage_adb_retry"] = stage_adb_retry_plan(args)
    base.update(
        {
            "run_id": RUN_ID,
            "build_tag": BUILD_TAG,
            "decision": f"{decision_slug()}-live-dry-run",
            "approval_phrase_required_for_live": APPROVAL_PHRASE,
            "v2450_base_approval_phrase": v2450.APPROVAL_PHRASE,
        }
    )
    base["module_lifecycle"].update(
        {
            "v2451_hybrid_late_observer": True,
            "v2451_boot_service_role": "optional early observer only",
            "v2451_late_observer_start": "after post-module Android ADB/root settle and before AudioTrack playback",
            "v2451_late_helper_duration_sec": min(int(args.late_capture_duration_sec), v2449.HELPER_MAX_DURATION_SEC),
            "v2451_late_helper_completion_timeout_sec": args.late_helper_completion_timeout_sec,
            "v2455_post_module_boot_complete_soft_gate": True,
            "v2455_post_module_boot_complete_timeout_sec": args.post_module_boot_complete_timeout_sec,
            "v2455_post_module_root_hard_gate": True,
            "native_runtime_dependency": False,
        }
    )
    base["magisk_strategy"] = {
        "classification": "Wi-Fi-style Android-good measurement capsule",
        "boot_service": "temporary M1 module service for early observation only",
        "late_observer": "host-coordinated su-c supervisor from staged module helper",
        "native_init_dependency": False,
        "post_module_settle": "boot-complete is telemetry; Magisk uid=0 root remains the hard gate before late observer/playback",
        "final_native_audio_path": "blocked until payload order, headers, hashes, mem-handle policy, and cleanup policy are pinned",
    }
    base["android_root_recheck"] = {
        "hard_gate": "uid=0 required before module staging, late observer, and playback",
        "initial_handoff_attempts": max(1, int(getattr(args, "android_root_recheck_attempts", v2396.DEFAULT_ANDROID_ROOT_RECHECK_ATTEMPTS))),
        "initial_handoff_sleep_sec": max(0.0, float(getattr(args, "android_root_recheck_sleep_sec", v2396.DEFAULT_ANDROID_ROOT_RECHECK_SLEEP_SEC))),
        "post_module_attempts": max(1, int(args.post_module_root_retry_attempts)),
        "post_module_sleep_sec": max(0.0, float(args.post_module_root_retry_sleep_sec)),
        "classifications": [
            "root-ready",
            "root-output-empty",
            "root-command-failed",
            "root-no-uid0",
        ],
        "v2457_gap": "V2456 rc0 plus empty stdout/stderr is retried and reported as root-output-empty, not treated as root-ready",
    }
    base["hard_boundary"] = list(base.get("hard_boundary", [])) + [
        "late observer is Android-good measurement only",
        "late observer uses the staged Magisk module helper but starts under host control after ADB/root settle",
        "boot service partial/missing-stop artifacts must not dominate late-observer classification",
    ]
    safety = command_safety(base)
    base["command_safety"] = safety
    module_ready = bool(base.get("module_plan", {}).get("future_live_ready"))
    base["future_live_ready"] = bool(module_ready and safety.get("ok"))
    blockers: list[str] = []
    if not module_ready:
        blockers.append(f"V2449 diagnostic module plan not live-ready: {base.get('module_plan', {}).get('future_live_blockers')}")
    if not safety.get("ok"):
        blockers.append("V2451 command safety failed")
    base["future_live_blockers"] = blockers
    base["ok"] = bool(base.get("module_plan", {}).get("ok") and safety.get("ok"))
    base["commands"]["logcat_capture_full"] = route.logcat_capture_command(route_args)
    return base


def run_live(args: argparse.Namespace) -> dict[str, Any]:
    ensure_live_approval(args)
    args.materialize_module_template = True
    route_args = v2396.android_args(args)
    plan = dry_run(args)
    if not plan.get("future_live_ready"):
        raise RuntimeError(f"V2451 live inputs are not ready: {plan.get('future_live_blockers')}")
    if not plan.get("command_safety", {}).get("ok"):
        raise RuntimeError(f"V2451 command safety failed: {plan.get('command_safety')}")

    out_dir = args.out_dir or default_live_out_dir()
    out_dir.mkdir(parents=True, exist_ok=False)
    os.chmod(out_dir, 0o700)

    steps: list[dict[str, Any]] = []
    result: dict[str, Any] = {
        "run_id": RUN_ID,
        "build_tag": BUILD_TAG,
        "decision": f"{decision_slug()}-live-started",
        "out_dir": rel(out_dir),
        "approval_ok": True,
        "plan": plan,
        "steps": steps,
        "rolled_back": False,
        "ok": False,
    }
    write_json(out_dir / "result.json", result)

    sealed = route.copy_sealed_android_boot(plan["module_plan"]["android_boot"]["selected"], out_dir)
    result["sealed_android_boot"] = sealed
    write_json(out_dir / "result.json", result)

    rollback_needed = False
    logcat_capture: dict[str, Any] | None = None
    try:
        rollback_needed = True
        steps.append(route.run_step(
            "flash-android",
            route.flash_android_command(route_args, str(out_dir / "android_boot_0600.img")),
            out_dir,
            timeout_sec=args.flash_timeout,
        ))
        v2396.run_android_post_handoff_settle(args, out_dir, steps)

        for index, command in enumerate(v2450.stage_commands(args)):
            run_stage_command_with_adb_retry(args, index, command, out_dir, steps)

        steps.append(route.run_step("android-reboot-for-magisk-service", v2450.android_reboot_command(args), out_dir, timeout_sec=args.adb_command_timeout, check=False))
        run_post_module_reboot_settle(args, out_dir, steps)

        steps.append(route.run_step(
            "start-late-diag-observer-after-post-module-settle",
            late_observer_start_command(args),
            out_dir,
            timeout_sec=args.adb_command_timeout,
        ))
        steps.append(route.run_step("logcat-clear-before-stimulus", route.logcat_clear_command(route_args), out_dir, timeout_sec=args.adb_command_timeout, check=False))
        logcat_capture = route.start_logcat_capture(route_args, out_dir)
        logcat_capture["record"]["name"] = "acdb-m1-hybrid-late-observer-logcat"
        logcat_capture["record"]["filter_regex_offline"] = v2396.LOG_FILTER_REGEX
        steps.append(logcat_capture["record"])

        steps.append(route.run_step("playback-start-background", route.playback_start_command(route_args), out_dir, timeout_sec=args.adb_command_timeout))
        wait_sec = max(float(args.capture_observe_sec), (args.duration_ms / 1000.0) + args.post_delay_sec + 1.0)
        time.sleep(wait_sec)
        for index, command in enumerate(route.stimulus_result_commands(route_args)):
            steps.append(route.run_step(f"playback-result-{index}", command, out_dir, timeout_sec=args.adb_command_timeout, check=False))

        steps.append(route.run_step(
            "wait-for-late-diag-helper-completion",
            late_helper_completion_wait_command(args),
            out_dir,
            timeout_sec=args.late_helper_completion_timeout_sec + 30.0,
            check=False,
        ))
        steps.append(route.run_step("prepare-private-artifacts-for-pull", v2450.collect_prepare_command(args), out_dir, timeout_sec=args.adb_command_timeout, check=False))
        steps.append(route.run_step(
            "collect-private-artifacts",
            v2450.collect_command(args, str(out_dir / "device-artifacts")),
            out_dir,
            timeout_sec=args.adb_command_timeout,
            check=False,
        ))
        result["payload_capture_summary"] = summarize_hybrid_capture_artifacts(out_dir)

        for index, command in enumerate(v2450.cleanup_commands(args)):
            steps.append(route.run_step(f"cleanup-{index}", command, out_dir, timeout_sec=args.adb_command_timeout, check=False))

        classification = result["payload_capture_summary"].get("classification")
        if classification in {
            "msm-audio-cal-payload-captured",
            "late-msm-audio-cal-payload-captured",
            "msm-audio-cal-dmabuf-payload-captured",
            "late-msm-audio-cal-dmabuf-payload-captured",
        }:
            result["decision"] = f"{decision_slug()}-payload-captured-before-rollback"
        else:
            result["decision"] = f"{decision_slug()}-{classification}-before-rollback"
        result["ok"] = True
    except Exception as error:
        result["decision"] = f"{decision_slug()}-failed-before-rollback"
        result["error"] = str(error)
        result["ok"] = False
    finally:
        route.stop_logcat_capture(logcat_capture)
        if rollback_needed:
            try:
                if not any(step.get("name", "").startswith("cleanup-") for step in steps):
                    for index, command in enumerate(v2450.cleanup_commands(args)):
                        steps.append(route.run_step(f"cleanup-finally-{index}", command, out_dir, timeout_sec=args.adb_command_timeout, check=False))
                v2396.rollback_to_v2321_with_android_recovery(args, route_args, out_dir, steps, result)
                if result.get("ok"):
                    suffix = "rollback-pass"
                    if result.get("rollback_fallback"):
                        suffix = f"rollback-pass-{result['rollback_fallback']}"
                    result["decision"] = f"{result['decision']}-{suffix}"
            except Exception as rollback_error:
                result["rollback_fallback_error"] = str(rollback_error)
                write_json(out_dir / "result.json", result)
                raise
            finally:
                write_json(out_dir / "result.json", result)
        else:
            write_json(out_dir / "result.json", result)
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="emit the V2451 hybrid late-observer live plan; no device action")
    mode.add_argument("--run-live", action="store_true", help="run the exact-gated V2451 hybrid M1 late observer")
    parser.add_argument("--materialize-module-template", action="store_true", help="compile and write private V2449 module template")
    parser.add_argument("--module-out-dir", type=Path, default=v2449.DEFAULT_MODULE_OUT_DIR)
    parser.add_argument("--cc", default=v2449.DEFAULT_CC)
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
    parser.add_argument("--capture-duration-sec", type=int, default=v2450.DEFAULT_CAPTURE_DURATION_SEC)
    parser.add_argument("--capture-observe-sec", type=float, default=6.0)
    parser.add_argument("--android-root-recheck-attempts", type=int, default=v2396.DEFAULT_ANDROID_ROOT_RECHECK_ATTEMPTS)
    parser.add_argument("--android-root-recheck-sleep-sec", type=float, default=v2396.DEFAULT_ANDROID_ROOT_RECHECK_SLEEP_SEC)
    parser.add_argument("--post-module-root-retry-attempts", type=int, default=v2450.DEFAULT_POST_MODULE_ROOT_RETRY_ATTEMPTS)
    parser.add_argument("--post-module-root-retry-sleep-sec", type=float, default=v2450.DEFAULT_POST_MODULE_ROOT_RETRY_SLEEP_SEC)
    parser.add_argument("--post-module-adb-wait-timeout", type=float, default=v2450.DEFAULT_POST_MODULE_ADB_WAIT_TIMEOUT_SEC)
    parser.add_argument("--stage-adb-retry-attempts", type=int, default=DEFAULT_STAGE_ADB_RETRY_ATTEMPTS)
    parser.add_argument("--stage-adb-retry-sleep-sec", type=float, default=DEFAULT_STAGE_ADB_RETRY_SLEEP_SEC)
    parser.add_argument("--post-module-boot-complete-timeout-sec", type=float, default=DEFAULT_POST_MODULE_BOOT_COMPLETE_TIMEOUT_SEC)
    parser.add_argument("--helper-completion-timeout-sec", type=float, default=v2450.DEFAULT_HELPER_COMPLETION_TIMEOUT_SEC)
    parser.add_argument("--late-capture-duration-sec", type=int, default=DEFAULT_LATE_CAPTURE_DURATION_SEC)
    parser.add_argument("--late-helper-completion-timeout-sec", type=float, default=DEFAULT_LATE_HELPER_COMPLETION_TIMEOUT_SEC)
    parser.add_argument("--late-max-events", type=int, default=4096)
    parser.add_argument("--max-bytes", type=int, default=v2449.DEFAULT_MAX_BYTES)
    parser.add_argument("--process-poll-sec", type=float, default=v2449.DEFAULT_PROCESS_POLL_SEC)
    parser.add_argument("--max-unmatched-samples", type=int, default=v2449.DEFAULT_MAX_UNMATCHED_SAMPLES)
    parser.add_argument("--from-native", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--approval")
    parser.add_argument("--out-dir", type=Path, help="private live output directory")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.run_live:
        try:
            payload = run_live(args)
        except RuntimeError as error:
            payload = {
                "run_id": RUN_ID,
                "build_tag": BUILD_TAG,
                "decision": f"{decision_slug()}-live-refused",
                "ok": False,
                "rolled_back": False,
                "reason": str(error),
            }
            print(json.dumps(payload, indent=2, sort_keys=True))
            return 1
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0 if payload.get("ok") and payload.get("rolled_back") else 1

    payload = dry_run(args)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
