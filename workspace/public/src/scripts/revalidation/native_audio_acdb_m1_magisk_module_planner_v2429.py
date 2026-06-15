#!/usr/bin/env python3
"""V2429 host-only M1 temporary Magisk module planner for ACDB capture.

This unit does not boot Android, install a module, run playback, or issue native
audio/calibration ioctls. It prepares a private Magisk module template that can
start the existing V2423 thread-set clone-following observer earlier in Android
boot/service lifetime if a future exact-gated live run is approved.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import stat
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import native_audio_acdb_android_measurement_planner_v2396 as v2396
import native_audio_acdb_threadset_clone_follow_planner_v2423 as v2423


RUN_ID = "V2429"
BUILD_TAG = "v2429-audio-acdb-m1-magisk-module-planner"
ROOT = v2423.ROOT
MODULE_ID = "a90_audio_acdb_m1_v2429"
DEFAULT_MODULE_OUT_DIR = ROOT / "workspace/private/builds/audio/v2429-acdb-m1-magisk-module"
DEFAULT_CC = v2423.DEFAULT_CC
DEFAULT_CAPTURE_DURATION_SEC = 120
DEFAULT_MAX_BYTES = 512
DEFAULT_PROCESS_POLL_SEC = 0.2
REMOTE_DIR = "/data/local/tmp/a90-audio-acdb-m1-v2429"
REMOTE_ARTIFACT_DIR = f"{REMOTE_DIR}/artifacts"
HELPER_NAME = "a90_acdb_ioctl_capture_threadset_v2423"
APPROVAL_PHRASE = (
    "AUD-5G-acdb-m1-magisk-module-capture go: rollbackable Android AudioTrack speaker "
    "msm_audio_cal ioctl payload capture with temporary Magisk service module, no native "
    "calibration ioctl, no native speaker write, cleanup module and rollback to V2321"
)

SOURCE_REFERENCES = [
    {
        "title": "Magisk module boot scripts",
        "url": "https://github.com/topjohnwu/Magisk/blob/master/docs/guides.md",
        "used_for": "service.sh is late_start service mode and post-fs-data is blocking",
    },
    {
        "title": "Magisk internal details",
        "url": "https://topjohnwu.github.io/Magisk/details.html",
        "used_for": "Magisk module and service paths under /data/adb",
    },
]


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path | str) -> str:
    return v2423.rel(path)


def sha256(path: Path) -> str:
    return v2396.sha256(path)


def file_state(path: Path, *, zip_magic: bool = False) -> dict[str, Any]:
    return v2396.file_state(path, zip_magic=zip_magic)


def service_sh(duration_sec: int, max_bytes: int, process_poll_sec: float) -> str:
    return f'''#!/system/bin/sh
set -eu
MODDIR="${{0%/*}}"
RUN_DIR="{REMOTE_DIR}"
OUT="{REMOTE_ARTIFACT_DIR}"
HELPER="$MODDIR/bin/{HELPER_NAME}"
DURATION="${{A90_M1_DURATION_SEC:-{duration_sec}}}"
MAX_BYTES="${{A90_M1_MAX_BYTES:-{max_bytes}}}"
PROCESS_POLL_SEC="${{A90_M1_PROCESS_POLL_SEC:-{process_poll_sec}}}"
LOCK="$RUN_DIR/service.lock"

mkdir -p "$OUT"
chmod 700 "$RUN_DIR" "$OUT" 2>/dev/null || true
if [ -e "$LOCK" ]; then
  echo "already-running lock=$LOCK" >> "$OUT/service.log"
  exit 0
fi
echo "$$" > "$LOCK"

(
  echo "A90_M1_SERVICE_BEGIN duration=$DURATION max_bytes=$MAX_BYTES process_poll_sec=$PROCESS_POLL_SEC"
  if [ ! -x "$HELPER" ]; then
    echo "A90_M1_ERROR helper-not-executable path=$HELPER"
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
    echo "$pid" >> "$SEEN_PIDS"
    [ -r "/proc/$pid/maps" ] && cat "/proc/$pid/maps" > "$OUT/proc-$pid-maps.txt" || true
    [ -d "/proc/$pid/fd" ] && ls -l "/proc/$pid/fd" > "$OUT/proc-$pid-fd.txt" 2>&1 || true
    [ -d "/proc/$pid/task" ] && ls -1 "/proc/$pid/task" > "$OUT/proc-$pid-tasks-initial.txt" 2>&1 || true
    echo "A90_M1_HELPER_START tgid=$pid remaining=$remaining mode=threadset-clone-following"
    "$HELPER" \\
      --tgid "$pid" \\
      --fd-pid "$pid" \\
      --device-substr /dev/msm_audio_cal \\
      --out "$OUT/msm-audio-cal-threadset-p${{pid}}.jsonl" \\
      --duration-sec "$remaining" \\
      --max-bytes "$MAX_BYTES" \\
      --max-events 4096 >> "$OUT/helper-$pid.log" 2>&1 &
    echo "$! $pid threadset-clone-following" >> "$OUT/helper-pids.txt"
  }}

  while [ "$(date +%s)" -lt "$END_TS" ]; do
    (pidof android.hardware.audio.service 2>/dev/null || true) > "$OUT/audio-hal-pids.txt"
    (pidof audioserver 2>/dev/null || true) > "$OUT/audioserver-pids.txt"
    for pid in $(cat "$OUT/audio-hal-pids.txt" "$OUT/audioserver-pids.txt" 2>/dev/null | tr ' ' '\\n' | sort -u); do
      start_helper_for_pid "$pid"
    done
    sleep "$PROCESS_POLL_SEC" 2>/dev/null || sleep 1
  done
  echo "A90_M1_SERVICE_END"
  rm -f "$LOCK"
) >> "$OUT/service.log" 2>&1 &

exit 0
'''


def module_files(duration_sec: int, max_bytes: int, process_poll_sec: float, *, include_helper: bool) -> dict[str, bytes]:
    module_prop = f"""id={MODULE_ID}
name=A90 Audio ACDB M1 Probe V2429
version=0.1
versionCode=2429
author=A90 native-init project
description=Temporary Android-side ACDB ioctl observer. Measurement only; not a native-init runtime dependency.
"""
    readme = """# A90 Audio ACDB M1 Probe V2429

Private temporary Magisk service module for Android-side measurement only.

It uses `service.sh` late_start mode to launch the existing V2423 thread-set clone-following
observer earlier than ADB staging. It intentionally omits the post-fs-data hook because that
mode is blocking and too early for this measurement. Do not commit generated zips, raw JSONL,
device logs, or helper binaries.
"""
    files: dict[str, bytes] = {
        "module.prop": module_prop.encode(),
        "service.sh": service_sh(duration_sec, max_bytes, process_poll_sec).encode(),
        "README.md": readme.encode(),
    }
    if include_helper:
        files[f"bin/{HELPER_NAME}"] = b""
    return files


def write_bytes_private(path: Path, data: bytes, mode: int) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    os.chmod(path, mode)
    return {"path": rel(path), "mode": oct(mode), "sha256": sha256(path), "size": path.stat().st_size}


def build_helper_for_module(out_dir: Path, cc: str) -> dict[str, Any]:
    helper_build_dir = out_dir / "helper-build"
    build = v2423.build_capture_helper(helper_build_dir, cc=cc)
    source = helper_build_dir / HELPER_NAME
    target = out_dir / "bin" / HELPER_NAME
    if build.get("ok") and source.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        os.chmod(target, 0o700)
    return {
        "source_build": build,
        "module_binary": file_state(target),
        "ok": bool(build.get("ok") and target.exists() and file_state(target).get("ok")),
    }


def write_module_template(out_dir: Path, *, cc: str, duration_sec: int, max_bytes: int, process_poll_sec: float) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    os.chmod(out_dir, 0o700)
    helper = build_helper_for_module(out_dir, cc)
    written: list[dict[str, Any]] = []
    for relative, content in module_files(duration_sec, max_bytes, process_poll_sec, include_helper=False).items():
        mode = 0o700 if relative.endswith(".sh") else 0o600
        written.append(write_bytes_private(out_dir / relative, content, mode))

    for directory in [out_dir, *(path for path in out_dir.rglob("*") if path.is_dir())]:
        os.chmod(directory, 0o700)

    zip_path = out_dir / f"{MODULE_ID}.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for relative in module_files(duration_sec, max_bytes, process_poll_sec, include_helper=True):
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
        "files": written,
        "zip": file_state(zip_path, zip_magic=True),
        "private_only": True,
    }
    manifest_path = out_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    os.chmod(manifest_path, 0o600)
    manifest["manifest"] = file_state(manifest_path)
    manifest["ok"] = bool(helper.get("ok") and manifest["zip"].get("ok") and manifest["manifest"].get("ok"))
    return manifest


def module_state(args: argparse.Namespace) -> dict[str, Any]:
    state: dict[str, Any] = {
        "module_id": MODULE_ID,
        "mode": "M1-temporary-magisk-service-module",
        "native_runtime_dependency": False,
        "persistent_module_baseline": False,
        "uses_post_fs_data": False,
        "uses_service_sh": True,
        "out_dir": rel(args.module_out_dir),
        "materialize_requested": bool(args.materialize_module_template),
        "remote_artifact_dir": REMOTE_ARTIFACT_DIR,
    }
    if args.materialize_module_template:
        state.update(write_module_template(
            args.module_out_dir,
            cc=args.cc,
            duration_sec=args.capture_duration_sec,
            max_bytes=args.max_bytes,
            process_poll_sec=args.process_poll_sec,
        ))
    else:
        zip_path = args.module_out_dir / f"{MODULE_ID}.zip"
        state["zip"] = file_state(zip_path, zip_magic=True)
        state["planned_files"] = sorted(module_files(args.capture_duration_sec, args.max_bytes, args.process_poll_sec, include_helper=True))
        state["reason"] = "M1 module template not materialized; rerun with --materialize-module-template for future live readiness"
        state["ok"] = False
    return state


def planned_live_sequence(args: argparse.Namespace) -> dict[str, Any]:
    module_dir = f"/data/adb/modules/{MODULE_ID}"
    return {
        "host_only_in_v2429": True,
        "future_gate": APPROVAL_PHRASE,
        "activation_model": "temporary /data/adb/modules service.sh module, activated by one Android reboot, then removed before rollback",
        "commands_are_templates_only": True,
        "sequence": [
            "flash pinned Android boot via checked helper",
            "verify Android ADB and Magisk su root",
            f"remove stale {module_dir} and {REMOTE_DIR}",
            f"stage private module files to {module_dir}: module.prop, service.sh, bin/{HELPER_NAME}",
            "chmod module files; reboot Android once so service.sh starts",
            "wait for Android ADB/root after reboot",
            "launch existing bounded AudioTrack stimulus APK",
            f"pull private artifacts from {REMOTE_ARTIFACT_DIR}",
            f"remove {module_dir} and {REMOTE_DIR}",
            "reboot Android to recovery and checked-rollback to V2321",
        ],
        "required_cleanup": [
            f"rm -rf {module_dir}",
            f"rm -rf {REMOTE_DIR}",
            "uninstall com.a90.nativeinit.audio",
        ],
    }


def command_safety(payload: dict[str, Any]) -> dict[str, Any]:
    module_text = "\n".join(
        data.decode(errors="replace")
        for data in module_files(DEFAULT_CAPTURE_DURATION_SEC, DEFAULT_MAX_BYTES, DEFAULT_PROCESS_POLL_SEC, include_helper=False).values()
    )
    flat = json.dumps(payload.get("planned_live", {}), sort_keys=True) + "\n" + module_text
    forbidden = {
        "persistent_magisk_install": "magisk --install-module",
        "native_calibration_ioctl_symbol": "AUDIO_SET_CALIBRATION",
        "native_allocate_calibration_symbol": "AUDIO_ALLOCATE_CALIBRATION",
        "native_playback": "tinyplay",
        "native_mixer_set": "tinymix set",
        "raw_partition_write": " dd ",
        "fastboot": "fastboot",
        "post_fs_data": "post-fs-data.sh",
        "helper_open_msm_audio_cal": "open(\"/dev/msm_audio_cal",
    }
    findings = [{"name": name, "needle": needle} for name, needle in forbidden.items() if needle in flat]
    required = [
        "service.sh",
        "--tgid",
        "--fd-pid",
        "--device-substr /dev/msm_audio_cal",
        "threadset-clone-following",
        "cleanup",
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
    module = module_state(args)
    android_boot = v2396.route.select_android_boot_candidate()
    rollback = v2396.route.file_state(v2396.route.ROLLBACK_IMAGE, expected_sha256=v2396.route.ROLLBACK_SHA256)
    stimulus = v2396.route.stimulus_apk_state(args.stimulus_apk)
    payload: dict[str, Any] = {
        "run_id": RUN_ID,
        "build_tag": BUILD_TAG,
        "decision": "v2429-acdb-m1-magisk-module-planner-dry-run",
        "generated_at": now_iso(),
        "host_only": True,
        "device_action": "none",
        "approval_phrase_required_for_future_live": APPROVAL_PHRASE,
        "source_references": SOURCE_REFERENCES,
        "m1_reason": "V2428 fixed staged/running M0 observer still missed a logcat-proven /dev/msm_audio_cal ACDB edge",
        "module": module,
        "android_boot": android_boot,
        "rollback": rollback,
        "stimulus_apk": stimulus,
        "planned_live": planned_live_sequence(args),
        "boundaries": [
            "M1 is Android-good measurement packaging only",
            "no native-init runtime dependency on Magisk",
            "no helper-open of /dev/msm_audio_cal",
            "no calibration ioctl issued by helper",
            "no native replay, mixer write, tinyplay, DHCP, routes, or Wi-Fi action",
            "module activation/removal is a future exact-gated live step, not performed in V2429",
        ],
    }
    safety = command_safety(payload)
    payload["command_safety"] = safety
    module_ready = bool(module.get("ok") and args.materialize_module_template)
    payload["future_live_ready"] = bool(
        android_boot.get("ok")
        and rollback.get("ok")
        and stimulus.get("ok")
        and module_ready
        and safety.get("ok")
    )
    blockers: list[str] = []
    for name, item in (("android_boot", android_boot), ("rollback", rollback), ("stimulus_apk", stimulus)):
        if not item.get("ok"):
            blockers.append(f"{name} not ready")
    if not module_ready:
        blockers.append("M1 module template not materialized or private zip/helper not ready")
    if not safety.get("ok"):
        blockers.append("command safety failed")
    payload["future_live_blockers"] = blockers
    payload["ok"] = bool(android_boot.get("ok") and rollback.get("ok") and stimulus.get("ok") and safety.get("ok"))
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="emit the host-only M1 plan")
    parser.add_argument("--materialize-module-template", action="store_true", help="write private M1 Magisk module template and zip")
    parser.add_argument("--module-out-dir", type=Path, default=DEFAULT_MODULE_OUT_DIR)
    parser.add_argument("--cc", default=DEFAULT_CC)
    parser.add_argument("--stimulus-apk", type=Path, default=v2396.DEFAULT_STIMULUS_APK)
    parser.add_argument("--capture-duration-sec", type=int, default=DEFAULT_CAPTURE_DURATION_SEC)
    parser.add_argument("--max-bytes", type=int, default=DEFAULT_MAX_BYTES)
    parser.add_argument("--process-poll-sec", type=float, default=DEFAULT_PROCESS_POLL_SEC)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = dry_run_payload(args)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
