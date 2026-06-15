#!/usr/bin/env python3
"""V2449 host-only M1 diagnostic observer planner for ACDB capture.

V2447 proved the temporary Magisk service module can start the thread-set
observer early enough to attach the Android audio HAL worker thread that logs
the speaker ACDB edge.  It did not prove a clean negative for
`/dev/msm_audio_cal`, because the helper artifacts were collected before the
long-running helpers emitted terminal `stop` records and the helper only
recorded fd-matched ioctls.

This unit is source/build/test only.  It prepares a diagnostic M1 service module
that adds syscall/ioctl/fd counters, bounded unmatched-ioctl metadata samples,
wall/monotonic timestamps, and an explicit helper-completion wait before
collection.  It does not boot Android, install a Magisk module, run playback,
or issue native calibration ioctls.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import stat
import subprocess
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import native_audio_acdb_android_measurement_planner_v2396 as v2396
import native_audio_acdb_payload_capture_planner_v2415 as v2415


RUN_ID = "V2449"
BUILD_TAG = "v2449-audio-acdb-m1-diag-observer"
ROOT = v2415.ROOT
HELPER_SOURCE = ROOT / "workspace/public/src/android/acdb_payload_capture/a90_acdb_ioctl_capture_diag_v2449.c"
HELPER_NAME = "a90_acdb_ioctl_capture_diag_v2449"
MODULE_ID = "a90_audio_acdb_m1_diag_v2449"
DEFAULT_MODULE_OUT_DIR = ROOT / "workspace/private/builds/audio/v2449-acdb-m1-diag-observer"
DEFAULT_CC = v2415.DEFAULT_CC
DEFAULT_CAPTURE_DURATION_SEC = 180
DEFAULT_MAX_BYTES = 512
DEFAULT_PROCESS_POLL_SEC = 0.2
DEFAULT_MAX_UNMATCHED_SAMPLES = 32
DEFAULT_MAX_DMABUF_BYTES = 65536
HELPER_MAX_DURATION_SEC = 120
REMOTE_DIR = "/data/local/tmp/a90-audio-acdb-m1-diag-v2449"
REMOTE_ARTIFACT_DIR = f"{REMOTE_DIR}/artifacts"
REMOTE_MODULE_DIR = f"/data/adb/modules/{MODULE_ID}"
APPROVAL_PHRASE = (
    "AUD-5K-acdb-m1-diagnostic-observer go: rollbackable Android AudioTrack speaker "
    "msm_audio_cal diagnostic ioctl capture with temporary Magisk service module, "
    "helper-completion wait, no native calibration ioctl, no native speaker write, "
    "rollback to V2321"
)


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path | str) -> str:
    return v2415.rel(path)


def sha256(path: Path) -> str:
    return v2396.sha256(path)


def file_state(path: Path, *, zip_magic: bool = False) -> dict[str, Any]:
    state = v2415.file_state(path, require_private=path.is_relative_to(ROOT / "workspace/private") if path.is_absolute() else False)
    if zip_magic and path.exists():
        state["zip_magic"] = path.read_bytes().startswith(b"PK\x03\x04")
        state["ok"] = bool(state.get("ok") and state["zip_magic"])
    return state


def source_state() -> dict[str, Any]:
    state = file_state(HELPER_SOURCE)
    if HELPER_SOURCE.exists():
        text = HELPER_SOURCE.read_text(errors="replace")
        forbidden = {
            "opens_msm_audio_cal": "open(\"/dev/msm_audio_cal" in text or "open('/dev/msm_audio_cal" in text,
            "issues_audio_set_calibration": "AUDIO_SET_CALIBRATION" in text,
            "issues_audio_allocate_calibration": "AUDIO_ALLOCATE_CALIBRATION" in text,
            "uses_tinyplay": "tinyplay" in text,
            "uses_tinymix_set": "tinymix set" in text,
        }
        state.update({
            "contains_ptrace_attach": "PTRACE_ATTACH" in text,
            "contains_ptrace_traceclone": "PTRACE_O_TRACECLONE" in text,
            "contains_ptrace_syscall": "PTRACE_SYSCALL" in text,
            "contains_ioctl_syscall_filter": "__NR_ioctl" in text,
            "contains_compat_arm_ioctl_filter": "A90_COMPAT_ARM_NR_IOCTL" in text and "54UL" in text,
            "contains_regset_len_abi_detection": "regset_len" in text and "A90_COMPAT_ARM_GPR_BYTES" in text,
            "contains_abi_metadata": "\"abi\\\":\\\"" in text and "aarch32" in text and "aarch64" in text,
            "contains_task_enumeration": "/proc/%ld/task" in text,
            "contains_fd_owner_option": "--fd-pid" in text,
            "contains_unmatched_ioctl_event": "ioctl_unmatched" in text,
            "contains_stop_counters": "syscall_stop_count" in text and "ioctl_any_entry_count" in text,
            "contains_fd_miss_counters": "ioctl_fd_miss_count" in text and "fd_readlink_error_count" in text,
            "contains_unmatched_sample_limit": "max_unmatched_samples" in text,
            "contains_dmabuf_capture": "--dmabuf-out-dir" in text and "dmabuf_capture" in text and "mmap(" in text,
            "contains_mmap_lifecycle_capture": "mmap_entry" in text and "mmap_exit" in text and "A90_COMPAT_ARM_NR_MMAP2" in text,
            "contains_signed_mmap_fd_filter": "mmap_fd_arg" in text and "(int32_t)((uint32_t)frame->args[4])" in text,
            "contains_remote_mmap_fallback": "ok-remote-mmap" in text and "find_recent_mmap_record" in text,
            "contains_targeted_set_cal_constants_without_forbidden_symbol": "A90_CAL_CMD_SET_COMPAT" in text and "A90_CORE_CUSTOM_TOPOLOGIES_CAL_TYPE" in text,
            "contains_monotonic_ts": "CLOCK_MONOTONIC" in text,
            "contains_wall_ts": "wall_ms" in text,
            "forbidden": forbidden,
            "forbidden_ok": not any(forbidden.values()),
        })
        state["ok"] = bool(state.get("ok") and state["forbidden_ok"])
    return state


def build_capture_helper(out_dir: Path, *, cc: str = DEFAULT_CC) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    os.chmod(out_dir, 0o700)
    output = out_dir / HELPER_NAME
    command = [cc, "-O2", "-static", "-s", "-Wall", "-Wextra", "-o", str(output), str(HELPER_SOURCE)]
    completed = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=120,
    )
    state: dict[str, Any] = {
        "command": [rel(part) if part.startswith(str(ROOT)) else part for part in command],
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "out_dir": rel(out_dir),
    }
    if output.exists():
        os.chmod(output, 0o700)
        file_completed = subprocess.run(
            ["file", str(output)],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=30,
        )
        state["binary"] = file_state(output)
        state["file"] = file_completed.stdout.strip()
        state["aarch64_static"] = "ARM aarch64" in state["file"] and "statically linked" in state["file"]
    else:
        state["binary"] = file_state(output)
        state["file"] = ""
        state["aarch64_static"] = False
    state["ok"] = bool(completed.returncode == 0 and state["binary"].get("ok") and state["aarch64_static"])
    return state


def service_sh(duration_sec: int, max_bytes: int, process_poll_sec: float, max_unmatched_samples: int) -> str:
    return f'''#!/system/bin/sh
set -eu
MODDIR="${{0%/*}}"
RUN_DIR="{REMOTE_DIR}"
OUT="{REMOTE_ARTIFACT_DIR}"
HELPER="$MODDIR/bin/{HELPER_NAME}"
DURATION="${{A90_M1_DIAG_DURATION_SEC:-{duration_sec}}}"
MAX_BYTES="${{A90_M1_DIAG_MAX_BYTES:-{max_bytes}}}"
PROCESS_POLL_SEC="${{A90_M1_DIAG_PROCESS_POLL_SEC:-{process_poll_sec}}}"
MAX_UNMATCHED_SAMPLES="${{A90_M1_DIAG_MAX_UNMATCHED_SAMPLES:-{max_unmatched_samples}}}"
MAX_DMABUF_BYTES="${{A90_M1_DIAG_MAX_DMABUF_BYTES:-{DEFAULT_MAX_DMABUF_BYTES}}}"
HELPER_MAX_DURATION_SEC="{HELPER_MAX_DURATION_SEC}"
LOCK="$RUN_DIR/service.lock"

mkdir -p "$OUT"
chmod 700 "$RUN_DIR" "$OUT" 2>/dev/null || true
if [ -e "$LOCK" ]; then
  echo "already-running lock=$LOCK" >> "$OUT/service.log"
  exit 0
fi
echo "$$" > "$LOCK"

(
  echo "A90_M1_DIAG_SERVICE_BEGIN wall_s=$(date +%s) duration=$DURATION max_bytes=$MAX_BYTES process_poll_sec=$PROCESS_POLL_SEC max_unmatched_samples=$MAX_UNMATCHED_SAMPLES"
  if [ ! -x "$HELPER" ]; then
    echo "A90_M1_DIAG_ERROR helper-not-executable path=$HELPER"
    rm -f "$LOCK"
    exit 0
  fi
  START_TS="$(date +%s)"
  END_TS="$((START_TS + DURATION))"
  SEEN_PIDS="$OUT/seen-pids.txt"
  : > "$SEEN_PIDS"
  : > "$OUT/helper-pids.txt"
  (ps -A 2>/dev/null || ps 2>/dev/null || true) > "$OUT/boot-ps-initial.txt"
  (ls -l /dev/msm_audio_cal /dev/snd 2>&1 || true) > "$OUT/boot-devnodes.txt"

  start_helper_for_pid() {{
    pid="$1"
    [ -n "$pid" ] || return 0
    [ -d "/proc/$pid" ] || return 0
    if grep -qx "$pid" "$SEEN_PIDS" 2>/dev/null; then
      return 0
    fi
    now_ts="$(date +%s)"
    remaining="$((END_TS - now_ts))"
    [ "$remaining" -gt 0 ] || return 0
    helper_duration="$remaining"
    if [ "$helper_duration" -gt "$HELPER_MAX_DURATION_SEC" ]; then
      helper_duration="$HELPER_MAX_DURATION_SEC"
    fi
    echo "$pid" >> "$SEEN_PIDS"
    [ -r "/proc/$pid/maps" ] && cat "/proc/$pid/maps" > "$OUT/proc-$pid-maps.txt" || true
    [ -d "/proc/$pid/fd" ] && ls -l "/proc/$pid/fd" > "$OUT/proc-$pid-fd.txt" 2>&1 || true
    [ -d "/proc/$pid/task" ] && ls -1 "/proc/$pid/task" > "$OUT/proc-$pid-tasks-initial.txt" 2>&1 || true
    echo "A90_M1_DIAG_HELPER_START wall_s=$(date +%s) tgid=$pid remaining=$remaining helper_duration=$helper_duration mode=threadset-clone-following-diagnostic"
    "$HELPER" \\
      --tgid "$pid" \\
      --fd-pid "$pid" \\
      --device-substr /dev/msm_audio_cal \\
      --out "$OUT/msm-audio-cal-diag-threadset-p${{pid}}.jsonl" \\
      --duration-sec "$helper_duration" \\
      --max-bytes "$MAX_BYTES" \\
      --max-events 4096 \\
      --dmabuf-out-dir "$OUT/dmabuf" \\
      --max-dmabuf-bytes "$MAX_DMABUF_BYTES" \\
      --max-unmatched-samples "$MAX_UNMATCHED_SAMPLES" >> "$OUT/helper-$pid.log" 2>&1 &
    echo "$! $pid threadset-clone-following-diagnostic" >> "$OUT/helper-pids.txt"
  }}

  while [ "$(date +%s)" -lt "$END_TS" ]; do
    (pidof android.hardware.audio.service 2>/dev/null || true) > "$OUT/audio-hal-pids.txt"
    (pidof audioserver 2>/dev/null || true) > "$OUT/audioserver-pids.txt"
    for pid in $(cat "$OUT/audio-hal-pids.txt" "$OUT/audioserver-pids.txt" 2>/dev/null | tr ' ' '\\n' | sort -u); do
      start_helper_for_pid "$pid"
    done
    sleep "$PROCESS_POLL_SEC" 2>/dev/null || sleep 1
  done

  echo "A90_M1_DIAG_HELPER_WAIT_BEGIN wall_s=$(date +%s)"
  while read -r helper_pid target_pid helper_mode; do
    [ -n "$helper_pid" ] || continue
    wait_rc=0
    wait "$helper_pid" || wait_rc="$?"
    echo "A90_M1_DIAG_HELPER_WAIT_DONE wall_s=$(date +%s) helper_pid=$helper_pid target_pid=$target_pid mode=$helper_mode rc=$wait_rc"
  done < "$OUT/helper-pids.txt"
  echo "A90_M1_DIAG_SERVICE_END wall_s=$(date +%s)"
  rm -f "$LOCK"
) >> "$OUT/service.log" 2>&1 &

exit 0
'''


def module_files(duration_sec: int, max_bytes: int, process_poll_sec: float, max_unmatched_samples: int, *, include_helper: bool) -> dict[str, bytes]:
    module_prop = f"""id={MODULE_ID}
name=A90 Audio ACDB M1 Diagnostic Probe V2449
version=0.1
versionCode=2449
author=A90 native-init project
description=Temporary Android-side diagnostic ACDB ioctl observer. Measurement only; not a native-init runtime dependency.
"""
    readme = """# A90 Audio ACDB M1 Diagnostic Probe V2449

Private temporary Magisk service module for Android-side measurement only.

It launches the V2449 diagnostic thread-set clone-following observer from
`service.sh`, records syscall/ioctl/fd counters and bounded unmatched ioctl
metadata samples, captures matching ACDB dmabuf payloads only into private
binary artifacts, and can fall back to a traced-process mmap record when
`/proc/<tgid>/fd/<mem_handle>` cannot be opened. It then waits for helper
completion before artifacts are pulled.
It intentionally omits the Magisk early-boot hook and does not install a
persistent module baseline.
"""
    files: dict[str, bytes] = {
        "module.prop": module_prop.encode(),
        "service.sh": service_sh(duration_sec, max_bytes, process_poll_sec, max_unmatched_samples).encode(),
        "README.md": readme.encode(),
    }
    if include_helper:
        files[f"bin/{HELPER_NAME}"] = b""
    return files


def write_private_file(path: Path, data: bytes, mode: int) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    os.chmod(path, mode)
    return {"path": rel(path), "mode": oct(mode), "sha256": sha256(path), "size": path.stat().st_size}


def write_module_template(out_dir: Path, *, cc: str, duration_sec: int, max_bytes: int, process_poll_sec: float, max_unmatched_samples: int) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    os.chmod(out_dir, 0o700)
    helper_build_dir = out_dir / "helper-build"
    helper = build_capture_helper(helper_build_dir, cc=cc)
    helper_target = out_dir / "bin" / HELPER_NAME
    if helper.get("ok") and (helper_build_dir / HELPER_NAME).exists():
        helper_target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(helper_build_dir / HELPER_NAME, helper_target)
        os.chmod(helper_target, 0o700)

    written: list[dict[str, Any]] = []
    for relative, content in module_files(duration_sec, max_bytes, process_poll_sec, max_unmatched_samples, include_helper=False).items():
        mode = 0o700 if relative.endswith(".sh") else 0o600
        written.append(write_private_file(out_dir / relative, content, mode))

    zip_path = out_dir / f"{MODULE_ID}.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for relative in module_files(duration_sec, max_bytes, process_poll_sec, max_unmatched_samples, include_helper=True):
            path = out_dir / relative
            if not path.exists():
                continue
            mode = 0o700 if relative.endswith(".sh") or relative.startswith("bin/") else 0o600
            info = zipfile.ZipInfo(relative)
            info.external_attr = (stat.S_IFREG | mode) << 16
            zf.writestr(info, path.read_bytes())
    os.chmod(zip_path, 0o600)

    manifest = {
        "generated_at": now_iso(),
        "run_id": RUN_ID,
        "module_id": MODULE_ID,
        "module_out_dir": rel(out_dir),
        "helper": helper,
        "helper_module_binary": file_state(helper_target),
        "files": written,
        "zip": file_state(zip_path, zip_magic=True),
        "private_only": True,
    }
    manifest_path = out_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    os.chmod(manifest_path, 0o600)
    manifest["manifest"] = file_state(manifest_path)
    manifest["ok"] = bool(helper.get("ok") and manifest["helper_module_binary"].get("ok") and manifest["zip"].get("ok") and manifest["manifest"].get("ok"))
    return manifest


def module_state(args: argparse.Namespace) -> dict[str, Any]:
    state: dict[str, Any] = {
        "module_id": MODULE_ID,
        "mode": "M1-temporary-magisk-service-module-diagnostic",
        "native_runtime_dependency": False,
        "persistent_module_baseline": False,
        "uses_post_fs_data": False,
        "uses_service_sh": True,
        "out_dir": rel(args.module_out_dir),
        "remote_module_dir": REMOTE_MODULE_DIR,
        "remote_artifact_dir": REMOTE_ARTIFACT_DIR,
        "materialize_requested": bool(args.materialize_module_template),
    }
    if args.materialize_module_template:
        state.update(write_module_template(
            args.module_out_dir,
            cc=args.cc,
            duration_sec=args.capture_duration_sec,
            max_bytes=args.max_bytes,
            process_poll_sec=args.process_poll_sec,
            max_unmatched_samples=args.max_unmatched_samples,
        ))
    else:
        zip_path = args.module_out_dir / f"{MODULE_ID}.zip"
        state["zip"] = file_state(zip_path, zip_magic=True)
        state["planned_files"] = sorted(module_files(args.capture_duration_sec, args.max_bytes, args.process_poll_sec, args.max_unmatched_samples, include_helper=True))
        state["reason"] = "diagnostic M1 module template not materialized; rerun with --materialize-module-template for future live readiness"
        state["ok"] = False
    return state


def planned_future_live_sequence() -> dict[str, Any]:
    return {
        "host_only_in_v2449": True,
        "future_gate": APPROVAL_PHRASE,
        "commands_are_templates_only": True,
        "activation_model": "temporary /data/adb/modules service.sh module, activated by one Android reboot, removed before V2321 rollback",
        "collection_contract": {
            "must_wait_for_service_helper_completion": True,
            "must_poll_jsonl_terminal_stop_before_pull": True,
            "missing_terminal_stop_classification": "partial-helper-still-running",
            "no_repeat_of_v2447_early_pull": True,
        },
        "sequence": [
            "flash pinned Android boot via checked helper",
            "verify Android ADB and Magisk su root",
            f"remove stale {REMOTE_MODULE_DIR} and {REMOTE_DIR}",
            f"stage private V2449 module files to {REMOTE_MODULE_DIR}",
            "reboot Android once so service.sh starts the diagnostic observer",
            "wait for Android ADB/root after reboot",
            "launch bounded AudioTrack speaker stimulus",
            "wait for service.sh helper-completion markers and JSONL terminal stop records",
            f"pull private artifacts from {REMOTE_ARTIFACT_DIR}",
            f"remove {REMOTE_MODULE_DIR} and {REMOTE_DIR}",
            "reboot Android to recovery and checked-rollback to V2321",
        ],
    }


def command_safety(payload: dict[str, Any]) -> dict[str, Any]:
    module_text = "\n".join(
        data.decode(errors="replace")
        for data in module_files(DEFAULT_CAPTURE_DURATION_SEC, DEFAULT_MAX_BYTES, DEFAULT_PROCESS_POLL_SEC, DEFAULT_MAX_UNMATCHED_SAMPLES, include_helper=False).values()
    )
    helper_text = HELPER_SOURCE.read_text(errors="replace") if HELPER_SOURCE.exists() else ""
    flat = json.dumps(payload.get("planned_live", {}), sort_keys=True) + "\n" + module_text + "\n" + helper_text
    forbidden = {
        "persistent_magisk_install": "magisk --install-module",
        "post_fs_data": "post-fs-data.sh",
        "native_calibration_ioctl_symbol": "AUDIO_SET_CALIBRATION",
        "native_allocate_calibration_symbol": "AUDIO_ALLOCATE_CALIBRATION",
        "native_playback": "tinyplay",
        "native_mixer_set": "tinymix set",
        "raw_partition_write": " dd ",
        "fastboot": "fastboot",
        "helper_open_msm_audio_cal": "open(\"/dev/msm_audio_cal",
    }
    findings = [{"name": name, "needle": needle} for name, needle in forbidden.items() if needle in flat]
    required = [
        "service.sh",
        HELPER_NAME,
        "--tgid",
        "--fd-pid",
        "--device-substr /dev/msm_audio_cal",
        "--max-unmatched-samples",
        "--dmabuf-out-dir",
        "dmabuf_capture",
        "mmap_entry",
        "mmap_exit",
        "mmap_fd_arg",
        "ok-remote-mmap",
        "ioctl_unmatched",
        "syscall_stop_count",
        "ioctl_any_entry_count",
        "partial-helper-still-running",
        "helper-completion",
        "checked-rollback to V2321",
    ]
    missing = [needle for needle in required if needle not in flat]
    return {
        "ok": not findings and not missing,
        "findings": findings,
        "missing_required_needles": missing,
        "forbidden": sorted(forbidden),
        "required": required,
    }


def dry_run_payload(args: argparse.Namespace) -> dict[str, Any]:
    source = source_state()
    module = module_state(args)
    android_boot = v2396.route.select_android_boot_candidate()
    rollback = v2396.route.file_state(v2396.route.ROLLBACK_IMAGE, expected_sha256=v2396.route.ROLLBACK_SHA256)
    stimulus = v2396.route.stimulus_apk_state(args.stimulus_apk)
    payload: dict[str, Any] = {
        "run_id": RUN_ID,
        "build_tag": BUILD_TAG,
        "decision": "v2449-acdb-m1-diagnostic-observer-dry-run",
        "generated_at": now_iso(),
        "host_only": True,
        "device_action": "none",
        "approval_phrase_required_for_future_live": APPROVAL_PHRASE,
        "source": source,
        "module": module,
        "android_boot": android_boot,
        "rollback": rollback,
        "stimulus_apk": stimulus,
        "planned_live": planned_future_live_sequence(),
        "diagnostic_contract": {
            "fixes_v2447_capture_gap": True,
            "adds_syscall_ioctl_fd_counters": True,
            "adds_bounded_unmatched_ioctl_samples": True,
            "adds_monotonic_and_wall_timestamps": True,
            "adds_private_dmabuf_payload_capture": True,
            "adds_mmap_lifecycle_fallback": True,
            "requires_terminal_stop_before_collection": True,
            "private_raw_payload_policy": "raw bytes only for fd-matched /dev/msm_audio_cal ioctls; unmatched samples metadata-only",
            "dmabuf_capture_policy": "matching custom-topology set-cal dmabuf bytes are stored only in private binary artifacts; public summaries may include length and SHA-256 only; if proc-fd duplication fails, V2467 may copy from a previously observed traced-process mmap of the same fd",
        },
        "boundaries": [
            "M1 is Android-good measurement packaging only, matching the prior Wi-Fi-style temporary helper pattern",
            "no native-init runtime dependency on Magisk",
            "no helper-open of /dev/msm_audio_cal",
            "no calibration ioctl issued by helper",
            "no native replay, mixer write, tinyplay, DHCP, routes, or Wi-Fi action",
            "module activation/removal is a future exact-gated live step, not performed in V2449",
        ],
    }
    safety = command_safety(payload)
    payload["command_safety"] = safety
    module_ready = bool(module.get("ok") and args.materialize_module_template)
    payload["future_live_ready"] = bool(
        source.get("ok")
        and android_boot.get("ok")
        and rollback.get("ok")
        and stimulus.get("ok")
        and module_ready
        and safety.get("ok")
    )
    blockers: list[str] = []
    for name, item in (("source", source), ("android_boot", android_boot), ("rollback", rollback), ("stimulus_apk", stimulus)):
        if not item.get("ok"):
            blockers.append(f"{name} not ready")
    if not module_ready:
        blockers.append("diagnostic M1 module template not materialized or private zip/helper not ready")
    if not safety.get("ok"):
        blockers.append("command safety failed")
    payload["future_live_blockers"] = blockers
    payload["ok"] = bool(source.get("ok") and android_boot.get("ok") and rollback.get("ok") and stimulus.get("ok") and safety.get("ok"))
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="emit the host-only diagnostic M1 plan")
    parser.add_argument("--materialize-module-template", action="store_true", help="write private diagnostic M1 module template and zip")
    parser.add_argument("--module-out-dir", type=Path, default=DEFAULT_MODULE_OUT_DIR)
    parser.add_argument("--cc", default=DEFAULT_CC)
    parser.add_argument("--stimulus-apk", type=Path, default=v2396.DEFAULT_STIMULUS_APK)
    parser.add_argument("--capture-duration-sec", type=int, default=DEFAULT_CAPTURE_DURATION_SEC)
    parser.add_argument("--max-bytes", type=int, default=DEFAULT_MAX_BYTES)
    parser.add_argument("--process-poll-sec", type=float, default=DEFAULT_PROCESS_POLL_SEC)
    parser.add_argument("--max-unmatched-samples", type=int, default=DEFAULT_MAX_UNMATCHED_SAMPLES)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = dry_run_payload(args)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
