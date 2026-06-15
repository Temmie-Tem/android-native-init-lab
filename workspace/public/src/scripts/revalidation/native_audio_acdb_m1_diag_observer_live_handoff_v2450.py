#!/usr/bin/env python3
"""V2450 exact-gated live handoff for the V2449 ACDB M1 diagnostic observer.

This runner uses the V2449 temporary Magisk service module to measure the
Android-good `/dev/msm_audio_cal` edge with added syscall/ioctl/fd diagnostics.
It preserves the V2446 Android handoff, corrected su-c staging, post-module ADB
wait budget, exact cleanup, and checked rollback model, but changes the module
identity, helper, artifact names, and classification contract to V2449.

It does not issue native calibration ioctls, does not write native mixer/PCM
state, does not call `magisk --install-module`, and does not make Magisk a
native-init runtime dependency.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shlex
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import native_audio_acdb_android_measurement_planner_v2396 as v2396
import native_audio_acdb_m1_magisk_module_live_handoff_v2430 as v2430
import native_audio_acdb_m1_diag_observer_planner_v2449 as v2449
import native_audio_android_route_delta_handoff_v2365 as route
import native_audio_magisk_cleanup_probe_live_handoff_v2434 as v2434


RUN_ID = "V2450"
BUILD_TAG = "v2450-audio-acdb-m1-diag-live"
ROOT = v2449.ROOT
DEFAULT_OUT_BASE = ROOT / "workspace/private/runs/audio"
DEFAULT_CAPTURE_DURATION_SEC = v2449.DEFAULT_CAPTURE_DURATION_SEC
REMOTE_MODULE_DIR = f"/data/adb/modules/{v2449.MODULE_ID}"
REMOTE_MODULE_UPDATE_DIR = f"/data/adb/modules_update/{v2449.MODULE_ID}"
REMOTE_INCOMING_DIR = f"{v2449.REMOTE_DIR}/incoming"
ANDROID_SHELL_UID = 2000
ANDROID_SHELL_GID = 2000
DEFAULT_POST_MODULE_ROOT_RETRY_ATTEMPTS = 8
DEFAULT_POST_MODULE_ROOT_RETRY_SLEEP_SEC = 3.0
DEFAULT_POST_MODULE_ADB_WAIT_TIMEOUT_SEC = 300.0
DEFAULT_HELPER_COMPLETION_TIMEOUT_SEC = 300.0
APPROVAL_PHRASE = v2449.APPROVAL_PHRASE


def rel(path: Path | str) -> str:
    return v2449.rel(path)


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def default_live_out_dir() -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return DEFAULT_OUT_BASE / f"{RUN_ID.lower()}-acdb-m1-diag-observer-{stamp}"


def decision_slug() -> str:
    return f"{RUN_ID.lower()}-acdb-m1-diag-observer"


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def args_for_v2449(args: argparse.Namespace) -> argparse.Namespace:
    return argparse.Namespace(
        dry_run=True,
        materialize_module_template=args.materialize_module_template,
        module_out_dir=args.module_out_dir,
        cc=args.cc,
        stimulus_apk=args.stimulus_apk,
        capture_duration_sec=args.capture_duration_sec,
        max_bytes=args.max_bytes,
        process_poll_sec=args.process_poll_sec,
        max_unmatched_samples=args.max_unmatched_samples,
    )


def ensure_live_approval(args: argparse.Namespace) -> None:
    if args.approval != APPROVAL_PHRASE:
        raise RuntimeError("exact AUD-5K ACDB M1 diagnostic observer approval phrase is required for --run-live")


def adb_shell(args: argparse.Namespace, command: str) -> list[str]:
    return v2396.adb_base(args) + ["shell", command]


def adb_su_shell(args: argparse.Namespace, command: str) -> list[str]:
    return adb_shell(args, f"su -c {shlex.quote(command)}")


def adb_su_mm_shell(args: argparse.Namespace, command: str) -> list[str]:
    return adb_shell(args, f"su -mm -c {shlex.quote(command)}")


def adb_subcommand(command: list[str]) -> str | None:
    return v2430.adb_subcommand(command)


def needs_adb_wait(command: list[str]) -> bool:
    return adb_subcommand(command) in {"push", "install"}


def stage_wait_command(args: argparse.Namespace) -> list[str]:
    return v2396.adb_base(args) + ["wait-for-device"]


def local_module_paths(args: argparse.Namespace) -> dict[str, Path]:
    return {
        "module.prop": args.module_out_dir / "module.prop",
        "service.sh": args.module_out_dir / "service.sh",
        "README.md": args.module_out_dir / "README.md",
        v2449.HELPER_NAME: args.module_out_dir / "bin" / v2449.HELPER_NAME,
    }


def remote_stage_path(name: str) -> str:
    if name == v2449.HELPER_NAME:
        return f"{REMOTE_INCOMING_DIR}/bin/{v2449.HELPER_NAME}"
    return f"{REMOTE_INCOMING_DIR}/{name}"


def local_module_manifest(args: argparse.Namespace) -> dict[str, dict[str, Any]]:
    manifest: dict[str, dict[str, Any]] = {}
    for name, path in local_module_paths(args).items():
        entry: dict[str, Any] = {
            "local_path": rel(path),
            "remote_path": remote_stage_path(name),
            "exists": path.exists(),
        }
        if path.exists():
            entry["sha256"] = v2449.sha256(path)
            entry["size"] = path.stat().st_size
        else:
            entry["sha256"] = f"<missing:{rel(path)}>"
            entry["size"] = None
        manifest[name] = entry
    return manifest


def namespace_readonly_commands(args: argparse.Namespace) -> list[list[str]]:
    return [
        adb_su_shell(args, v2434.root_readonly_probe_script()),
        adb_su_mm_shell(args, v2434.root_readonly_probe_script()),
    ]


def pre_residue_check_command(args: argparse.Namespace) -> list[str]:
    command = f"""
set -eu
MODULE_DIR={shlex.quote(REMOTE_MODULE_DIR)}
MODULE_UPDATE_DIR={shlex.quote(REMOTE_MODULE_UPDATE_DIR)}
RUN_DIR={shlex.quote(v2449.REMOTE_DIR)}
echo A90_M1_RESIDUE_CHECK_BEGIN
id
id -Z
for path in "$MODULE_DIR" "$MODULE_UPDATE_DIR"; do
  if [ -e "$path" ]; then
    echo A90_M1_RESIDUE_PRESENT "$path"
    exit 50
  fi
done
if find /data/adb/modules -maxdepth 1 -type d -name '.a90_v2433_cleanup_probe_*' -print 2>/dev/null | grep -q .; then
  echo A90_M1_CLEANUP_PROBE_RESIDUE_PRESENT
  exit 51
fi
rm -rf "$RUN_DIR"
echo A90_M1_RESIDUE_CHECK_OK
"""
    return adb_su_shell(args, command)


def setup_stage_command(args: argparse.Namespace) -> list[str]:
    command = f"""
set -eu
RUN_DIR={shlex.quote(v2449.REMOTE_DIR)}
INCOMING_DIR={shlex.quote(REMOTE_INCOMING_DIR)}
ARTIFACT_DIR={shlex.quote(v2449.REMOTE_ARTIFACT_DIR)}
echo A90_M1_STAGE_SETUP_BEGIN
rm -rf "$INCOMING_DIR"
mkdir -p "$INCOMING_DIR/bin" "$ARTIFACT_DIR"
chown {ANDROID_SHELL_UID}:{ANDROID_SHELL_GID} "$INCOMING_DIR" "$INCOMING_DIR/bin"
chmod 711 "$RUN_DIR"
chmod 700 "$INCOMING_DIR" "$INCOMING_DIR/bin" "$ARTIFACT_DIR"
echo A90_M1_INCOMING_READY
echo A90_M1_STAGE_SETUP_OK
"""
    return adb_su_shell(args, command)


def install_module_command(args: argparse.Namespace) -> list[str]:
    helper = f"{REMOTE_MODULE_DIR}/bin/{v2449.HELPER_NAME}"
    manifest = local_module_manifest(args)
    required_checks = "\n".join(
        f"check_file {shlex.quote(entry['remote_path'])} {shlex.quote(entry['sha256'])} {shlex.quote(name)}"
        for name, entry in manifest.items()
    )
    command = f"""
set -eu
MODULE_DIR={shlex.quote(REMOTE_MODULE_DIR)}
MODULE_UPDATE_DIR={shlex.quote(REMOTE_MODULE_UPDATE_DIR)}
INCOMING_DIR={shlex.quote(REMOTE_INCOMING_DIR)}
HELPER={shlex.quote(helper)}
echo A90_M1_INSTALL_BEGIN
if [ -e "$MODULE_DIR" ] || [ -e "$MODULE_UPDATE_DIR" ]; then
  echo A90_M1_INSTALL_RESIDUE_PRESENT
  exit 52
fi
sha256_file() {{
  if command -v sha256sum >/dev/null 2>&1; then
    line="$(sha256sum "$1")"
  else
    line="$(/system/bin/toybox sha256sum "$1")"
  fi
  echo "${{line%% *}}"
}}
check_file() {{
  path="$1"
  expected="$2"
  label="$3"
  if [ ! -f "$path" ]; then
    echo A90_M1_INCOMING_FILE_MISSING "$label" "$path"
    exit 54
  fi
  actual="$(sha256_file "$path")"
  if [ "$actual" != "$expected" ]; then
    echo A90_M1_INCOMING_SHA_MISMATCH "$label" "$actual" "$expected"
    exit 55
  fi
  echo A90_M1_INCOMING_SHA_OK "$label" "$actual"
}}
set -- $(find "$INCOMING_DIR" -type f | wc -l)
if [ "$1" != "4" ]; then
  echo A90_M1_INCOMING_FILE_COUNT_MISMATCH "$1"
  find "$INCOMING_DIR" -type f -print 2>/dev/null || true
  exit 56
fi
{required_checks}
echo A90_M1_INCOMING_HASH_OK
mkdir -p "$MODULE_DIR/bin"
cp "$INCOMING_DIR/module.prop" "$MODULE_DIR/module.prop"
cp "$INCOMING_DIR/service.sh" "$MODULE_DIR/service.sh"
cp "$INCOMING_DIR/README.md" "$MODULE_DIR/README.md"
cp "$INCOMING_DIR/bin/{v2449.HELPER_NAME}" "$HELPER"
rm -f "$MODULE_DIR/disable" "$MODULE_DIR/remove"
chown -R 0:0 "$MODULE_DIR"
chmod 755 "$MODULE_DIR" "$MODULE_DIR/bin"
chmod 700 "$MODULE_DIR/service.sh" "$HELPER"
chmod 600 "$MODULE_DIR/module.prop" "$MODULE_DIR/README.md"
rm -rf "$INCOMING_DIR"
ls -lZ "$MODULE_DIR" "$MODULE_DIR/bin"
echo A90_M1_INSTALL_OK
"""
    return adb_su_shell(args, command)


def stage_commands(args: argparse.Namespace) -> list[list[str]]:
    commands: list[list[str]] = []
    commands.extend(namespace_readonly_commands(args))
    commands.append(pre_residue_check_command(args))
    commands.append(setup_stage_command(args))
    for name, path in local_module_paths(args).items():
        commands.append(v2396.adb_push(args, rel(path), remote_stage_path(name)))
    commands.append(v2396.adb_base(args) + ["install", "-r", rel(args.stimulus_apk)])
    commands.append(install_module_command(args))
    return commands


def cleanup_script() -> str:
    helper = f"{REMOTE_MODULE_DIR}/bin/{v2449.HELPER_NAME}"
    return f"""
set -eu
MODULE_DIR={shlex.quote(REMOTE_MODULE_DIR)}
MODULE_UPDATE_DIR={shlex.quote(REMOTE_MODULE_UPDATE_DIR)}
RUN_DIR={shlex.quote(v2449.REMOTE_DIR)}
HELPER={shlex.quote(helper)}
echo A90_M1_CLEANUP_BEGIN
rm -f "$MODULE_DIR/module.prop" "$MODULE_DIR/service.sh" "$MODULE_DIR/README.md" \
  "$MODULE_DIR/disable" "$MODULE_DIR/remove" "$HELPER" 2>/dev/null || true
rmdir "$MODULE_DIR/bin" 2>/dev/null || true
rmdir "$MODULE_DIR" 2>/dev/null || true
rm -rf "$MODULE_UPDATE_DIR" "$RUN_DIR"
if [ -e "$MODULE_DIR" ] || [ -e "$MODULE_UPDATE_DIR" ]; then
  echo A90_M1_CLEANUP_RESIDUE_PRESENT
  ls -la "$MODULE_DIR" "$MODULE_UPDATE_DIR" 2>&1 || true
  exit 53
fi
echo A90_M1_CLEANUP_OK
"""


def cleanup_commands(args: argparse.Namespace) -> list[list[str]]:
    return [
        v2396.adb_base(args) + ["wait-for-device"],
        v2396.adb_base(args) + ["uninstall", route.APK_PACKAGE],
        adb_su_shell(args, cleanup_script()),
        adb_su_shell(args, f"ls -ld {shlex.quote(REMOTE_MODULE_DIR)} {shlex.quote(v2449.REMOTE_DIR)} 2>&1 || true"),
    ]


def collect_prepare_command(args: argparse.Namespace) -> list[str]:
    command = f"""
set -eu
RUN_DIR={shlex.quote(v2449.REMOTE_DIR)}
ARTIFACT_DIR={shlex.quote(v2449.REMOTE_ARTIFACT_DIR)}
if [ -d "$ARTIFACT_DIR" ]; then
  chmod -R a+rX "$RUN_DIR"
fi
ls -lR "$RUN_DIR" 2>&1 || true
"""
    return adb_su_shell(args, command)


def collect_command(args: argparse.Namespace, destination: str = "<private-run-dir>/device-artifacts") -> list[str]:
    return v2396.adb_base(args) + ["pull", v2449.REMOTE_ARTIFACT_DIR, destination]


def diag_helper_completion_wait_command(args: argparse.Namespace) -> list[str]:
    command = f"""
set -eu
ARTIFACT_DIR={shlex.quote(v2449.REMOTE_ARTIFACT_DIR)}
SERVICE_LOG="$ARTIFACT_DIR/service.log"
TIMEOUT_SEC={int(args.helper_completion_timeout_sec)}
DEADLINE="$(( $(date +%s) + TIMEOUT_SEC ))"
echo A90_M1_DIAG_WAIT_BEGIN timeout_sec="$TIMEOUT_SEC"
while [ "$(date +%s)" -le "$DEADLINE" ]; do
  jsonl_count=0
  stop_count=0
  for path in "$ARTIFACT_DIR"/msm-audio-cal-diag-threadset-p*.jsonl; do
    [ -f "$path" ] || continue
    jsonl_count="$((jsonl_count + 1))"
    if grep -q '"event":"stop"' "$path" 2>/dev/null; then
      stop_count="$((stop_count + 1))"
    fi
  done
  if [ -f "$SERVICE_LOG" ] && grep -q 'A90_M1_DIAG_SERVICE_END' "$SERVICE_LOG"; then
    if [ "$jsonl_count" = "$stop_count" ]; then
      echo A90_M1_DIAG_WAIT_OK jsonl_count="$jsonl_count" stop_count="$stop_count"
    else
      echo A90_M1_DIAG_WAIT_PARTIAL jsonl_count="$jsonl_count" stop_count="$stop_count"
    fi
    exit 0
  fi
  sleep 1
done
echo A90_M1_DIAG_WAIT_TIMEOUT
if [ -f "$SERVICE_LOG" ]; then tail -40 "$SERVICE_LOG" 2>/dev/null || true; fi
exit 0
"""
    return adb_su_shell(args, command)


def payload_sha256(bytes_hex: str) -> str | None:
    if not bytes_hex:
        return None
    try:
        return hashlib.sha256(bytes.fromhex(bytes_hex)).hexdigest()
    except ValueError:
        return hashlib.sha256(bytes_hex.encode()).hexdigest()


def parse_jsonl(path: Path) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for line in path.read_text(errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            item = {"event": "json-decode-error", "raw_prefix": line[:160]}
        events.append(item)
    return events


def summarize_diag_capture_artifacts(out_dir: Path) -> dict[str, Any]:
    artifact_root = out_dir / "device-artifacts"
    service_logs = sorted(artifact_root.rglob("service.log")) if artifact_root.exists() else []
    jsonl_files = sorted(artifact_root.rglob("msm-audio-cal-diag-threadset-p*.jsonl")) if artifact_root.exists() else []
    summary: dict[str, Any] = {
        "artifact_root": rel(artifact_root),
        "artifact_root_exists": artifact_root.exists(),
        "jsonl_files": [rel(path) for path in jsonl_files],
        "jsonl_file_count": len(jsonl_files),
        "service_logs": [rel(path) for path in service_logs],
        "target_pids": [],
        "helper_starts": 0,
        "tracee_adds": 0,
        "clone_events": 0,
        "helper_errors": 0,
        "ioctl_entries": 0,
        "ioctl_exits": 0,
        "ioctl_unmatched": 0,
        "syscall_stop_count": 0,
        "syscall_entry_count": 0,
        "ioctl_any_entry_count": 0,
        "ioctl_fd_match_count": 0,
        "ioctl_fd_miss_count": 0,
        "fd_readlink_error_count": 0,
        "unmatched_samples": [],
        "requests": {},
        "payload_hashes": [],
        "raw_payload_in_summary": False,
        "missing_stop_files": [],
        "wait_markers": [],
    }

    for service_log in service_logs:
        text = service_log.read_text(errors="replace")
        for line in text.splitlines():
            if "A90_M1_DIAG_" in line:
                summary["wait_markers"].append(line[:240])
            if "A90_M1_DIAG_HELPER_START" in line:
                summary["helper_starts"] += 1
                for token in line.split():
                    if token.startswith("tgid="):
                        try:
                            summary["target_pids"].append(int(token.split("=", 1)[1]))
                        except ValueError:
                            pass
            if "A90_M1_DIAG_ERROR" in line:
                summary["helper_errors"] += 1

    for path in jsonl_files:
        events = parse_jsonl(path)
        has_stop = False
        for event in events:
            kind = event.get("event")
            if kind == "tracee-add":
                summary["tracee_adds"] += 1
            elif kind == "clone":
                summary["clone_events"] += 1
            elif kind == "error":
                summary["helper_errors"] += 1
            elif kind == "ioctl_entry":
                summary["ioctl_entries"] += 1
                request = str(event.get("request", ""))
                if request:
                    summary["requests"][request] = int(summary["requests"].get(request, 0)) + 1
                digest = payload_sha256(str(event.get("bytes_hex", "")))
                if digest:
                    summary["payload_hashes"].append(
                        {
                            "file": rel(path),
                            "seq": event.get("seq"),
                            "request": request,
                            "read_len": event.get("read_len"),
                            "sha256": digest,
                        }
                    )
            elif kind == "ioctl_exit":
                summary["ioctl_exits"] += 1
            elif kind == "ioctl_unmatched":
                summary["ioctl_unmatched"] += 1
                if len(summary["unmatched_samples"]) < 16:
                    summary["unmatched_samples"].append(
                        {
                            "file": rel(path),
                            "sample": event.get("sample"),
                            "request": event.get("request"),
                            "fd": event.get("fd"),
                            "readlink_errno": event.get("readlink_errno"),
                            "fd_target": event.get("fd_target"),
                        }
                    )
            elif kind == "stop":
                has_stop = True
                for key in (
                    "syscall_stop_count",
                    "syscall_entry_count",
                    "ioctl_any_entry_count",
                    "ioctl_fd_match_count",
                    "ioctl_fd_miss_count",
                    "fd_readlink_error_count",
                    "unmatched_samples",
                ):
                    value = event.get(key)
                    if isinstance(value, int):
                        if key == "unmatched_samples":
                            summary["unmatched_sample_count"] = int(summary.get("unmatched_sample_count", 0)) + value
                        else:
                            summary[key] += value
        if not has_stop:
            summary["missing_stop_files"].append(rel(path))

    summary["target_pids"] = sorted(set(summary["target_pids"]))
    summary["payload_hashes"] = summary["payload_hashes"][:64]
    summary["wait_marker_count"] = len(summary["wait_markers"])
    if not summary["artifact_root_exists"]:
        classification = "artifact-pull-missing"
    elif summary["ioctl_entries"] > 0:
        classification = "msm-audio-cal-payload-captured"
    elif summary["missing_stop_files"]:
        classification = "partial-helper-still-running"
    elif summary["ioctl_any_entry_count"] > 0 and summary["fd_readlink_error_count"] > 0 and summary["ioctl_fd_match_count"] == 0:
        classification = "fd-readlink-miss"
    elif summary["ioctl_any_entry_count"] > 0 and summary["ioctl_fd_miss_count"] > 0 and summary["ioctl_fd_match_count"] == 0:
        classification = "ioctl-any-but-fd-miss"
    elif summary["syscall_stop_count"] > 0 and summary["ioctl_any_entry_count"] == 0:
        classification = "syscall-stops-no-ioctl"
    elif summary["helper_starts"] > 0 and summary["syscall_stop_count"] == 0:
        classification = "no-syscall-stops"
    elif summary["tracee_adds"] > summary["helper_starts"]:
        classification = "threadset-attached-no-diagnostic-ioctl"
    elif summary["helper_starts"] > 0:
        classification = "diagnostic-helper-started-no-syscall-evidence"
    elif summary["target_pids"]:
        classification = "target-pids-found-helper-did-not-start"
    else:
        classification = "no-target-audio-pids"
    summary["classification"] = classification
    return summary


def android_reboot_command(args: argparse.Namespace) -> list[str]:
    return v2396.adb_base(args) + ["reboot"]


def stage_wait_plan(args: argparse.Namespace) -> list[dict[str, Any]]:
    return [
        {
            "before_stage_index": index,
            "reason": f"stabilize ADB before adb {adb_subcommand(command)}",
            "command": stage_wait_command(args),
        }
        for index, command in enumerate(stage_commands(args))
        if needs_adb_wait(command)
    ]


def post_module_reboot_settle_plan(args: argparse.Namespace) -> dict[str, Any]:
    commands = v2396.android_post_handoff_settle_commands(args)
    return {
        "initial_wait_for_device": commands[0],
        "boot_complete_recheck": commands[1],
        "root_check": commands[2],
        "root_retry_attempts": args.post_module_root_retry_attempts,
        "root_retry_sleep_sec": args.post_module_root_retry_sleep_sec,
        "adb_wait_timeout_sec": args.post_module_adb_wait_timeout,
        "v2450_observed_v2445_adb_return_sec": 206.359,
        "classification": "bounded adb reacquire plus Magisk-root retry after module activation reboot with V2450 extended wait budget",
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
    steps.append(route.run_step(
        "android-post-module-reboot-settle-1-boot-complete",
        commands[1],
        out_dir,
        timeout_sec=args.adb_command_timeout,
    ))

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
        stdout = v2396.step_stdout(root_record)
        root_record["root_ready"] = "uid=0" in stdout
        if root_record["root_ready"]:
            root_record["settle_decision"] = "post-module-root-ready"
            return
        root_record["settle_decision"] = "post-module-root-not-ready"
        if attempt != attempts:
            time.sleep(float(args.post_module_root_retry_sleep_sec))

    raise RuntimeError(
        "post-module Android root recheck did not report uid=0 after "
        f"{attempts} attempts; see {last_record.get('stdout') if last_record else 'no root attempt'} "
        f"{last_record.get('stderr') if last_record else ''}"
    )


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
        REMOTE_MODULE_DIR,
        "service.sh",
        v2449.HELPER_NAME,
        "su -c",
        "su -mm -c",
        "A90_M1_RESIDUE_CHECK_OK",
        "A90_M1_INCOMING_READY",
        "A90_M1_INCOMING_HASH_OK",
        "A90_M1_INSTALL_OK",
        "A90_M1_DIAG_WAIT",
        "A90_M1_CLEANUP_OK",
        REMOTE_INCOMING_DIR,
        "adb\", \"reboot",
        route.APK_PACKAGE,
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
    module_plan = v2449.dry_run_payload(args_for_v2449(args))
    route_args = v2396.android_args(args)
    commands = {
        "flash_android": route.flash_android_command(route_args, "<private-run-dir>/android_boot_0600.img"),
        "android_post_handoff_settle": v2396.android_post_handoff_settle_commands(args),
        "stage_module_and_apk": stage_commands(args),
        "android_reboot_for_magisk_service": android_reboot_command(args),
        "android_post_module_reboot_settle": post_module_reboot_settle_plan(args),
        "logcat_clear_before_stimulus": route.logcat_clear_command(route_args),
        "logcat_capture_full": route.logcat_capture_command(route_args),
        "playback_start_background": route.playback_start_command(route_args),
        "playback_result": route.stimulus_result_commands(route_args),
        "wait_for_diag_helper_completion": diag_helper_completion_wait_command(args),
        "prepare_private_artifacts_for_pull": collect_prepare_command(args),
        "collect_private_artifacts": collect_command(args),
        "cleanup": cleanup_commands(args),
        "android_wait_device_before_rollback": v2396.adb_base(args) + ["wait-for-device"],
        "android_reboot_recovery_for_rollback": route.android_reboot_recovery_command(route_args),
        "rollback_v2321": route.rollback_command(route_args),
    }
    payload: dict[str, Any] = {
        "run_id": RUN_ID,
        "build_tag": BUILD_TAG,
        "decision": f"{decision_slug()}-live-dry-run",
        "generated_at": now_iso(),
        "host_only": True,
        "device_action": "none",
        "approval_phrase_required_for_live": APPROVAL_PHRASE,
        "module_plan": module_plan,
        "module_lifecycle": {
            "module_id": v2449.MODULE_ID,
            "remote_module_dir": REMOTE_MODULE_DIR,
            "remote_module_update_dir": REMOTE_MODULE_UPDATE_DIR,
            "remote_incoming_dir": REMOTE_INCOMING_DIR,
            "incoming_owner": f"{ANDROID_SHELL_UID}:{ANDROID_SHELL_GID}",
            "incoming_transfer": "adb push as shell into shell-owned /data/local/tmp incoming dir",
            "install_validation": "Magisk root validates exact SHA-256 values before final module copy",
            "local_module_manifest": local_module_manifest(args),
            "activation": "manual /data/adb/modules staging followed by one Android reboot",
            "cleanup_required_before_rollback": True,
            "diagnostic_helper": v2449.HELPER_NAME,
            "max_unmatched_samples": args.max_unmatched_samples,
            "collection_contract": module_plan.get("planned_live", {}).get("collection_contract"),
            "native_runtime_dependency": False,
            "uses_magisk_install_module": False,
            "corrected_remote_shell": "adb shell \"su -c '<script>'\"",
            "v2435_cleanup_discipline": True,
            "v2450_post_module_adb_wait_budget": True,
            "v2450_helper_completion_wait": True,
        },
        "commands": commands,
        "stage_adb_waits": stage_wait_plan(args),
        "hard_boundary": [
            "temporary Android-side measurement module only",
            "no native-init Magisk dependency",
            "no native calibration ioctl issue",
            "no native speaker write, tinymix set, tinyplay, Wi-Fi, DHCP, route, or ping",
            "bounded post-module-reboot ADB/root retry before capture",
            "exact cleanup before V2321 rollback",
            "magisk install-module remains deferred",
        ],
    }
    safety = command_safety(payload)
    payload["command_safety"] = safety
    module_ready = bool(module_plan.get("future_live_ready"))
    payload["future_live_ready"] = bool(module_ready and safety.get("ok"))
    blockers: list[str] = []
    if not module_ready:
        blockers.append(f"V2449 diagnostic module plan not live-ready: {module_plan.get('future_live_blockers')}")
    if not safety.get("ok"):
        blockers.append("V2450 command safety failed")
    payload["future_live_blockers"] = blockers
    payload["ok"] = bool(module_plan.get("ok") and safety.get("ok"))
    return payload


def run_live(args: argparse.Namespace) -> dict[str, Any]:
    ensure_live_approval(args)
    args.materialize_module_template = True
    route_args = v2396.android_args(args)
    plan = dry_run(args)
    if not plan.get("future_live_ready"):
        raise RuntimeError(f"V2450 live inputs are not ready: {plan.get('future_live_blockers')}")
    if not plan.get("command_safety", {}).get("ok"):
        raise RuntimeError(f"V2450 command safety failed: {plan.get('command_safety')}")

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

        for index, command in enumerate(stage_commands(args)):
            if needs_adb_wait(command):
                subcommand = adb_subcommand(command) or "unknown"
                steps.append(route.run_step(
                    f"stage-{index}-adb-wait-before-{subcommand}",
                    stage_wait_command(args),
                    out_dir,
                    timeout_sec=args.adb_command_timeout,
                    check=False,
                ))
            steps.append(route.run_step(f"stage-{index}", command, out_dir, timeout_sec=args.adb_command_timeout))

        steps.append(route.run_step("android-reboot-for-magisk-service", android_reboot_command(args), out_dir, timeout_sec=args.adb_command_timeout, check=False))
        run_post_module_reboot_settle(args, out_dir, steps)

        steps.append(route.run_step("logcat-clear-before-stimulus", route.logcat_clear_command(route_args), out_dir, timeout_sec=args.adb_command_timeout, check=False))
        logcat_capture = route.start_logcat_capture(route_args, out_dir)
        logcat_capture["record"]["name"] = "acdb-m1-diag-observer-logcat"
        logcat_capture["record"]["filter_regex_offline"] = v2396.LOG_FILTER_REGEX
        steps.append(logcat_capture["record"])

        steps.append(route.run_step("playback-start-background", route.playback_start_command(route_args), out_dir, timeout_sec=args.adb_command_timeout))
        wait_sec = max(float(args.capture_observe_sec), (args.duration_ms / 1000.0) + args.post_delay_sec + 1.0)
        time.sleep(wait_sec)
        for index, command in enumerate(route.stimulus_result_commands(route_args)):
            steps.append(route.run_step(f"playback-result-{index}", command, out_dir, timeout_sec=args.adb_command_timeout, check=False))

        steps.append(route.run_step(
            "wait-for-diag-helper-completion",
            diag_helper_completion_wait_command(args),
            out_dir,
            timeout_sec=args.helper_completion_timeout_sec + 30.0,
            check=False,
        ))
        steps.append(route.run_step("prepare-private-artifacts-for-pull", collect_prepare_command(args), out_dir, timeout_sec=args.adb_command_timeout, check=False))
        steps.append(route.run_step(
            "collect-private-artifacts",
            collect_command(args, str(out_dir / "device-artifacts")),
            out_dir,
            timeout_sec=args.adb_command_timeout,
            check=False,
        ))
        result["payload_capture_summary"] = summarize_diag_capture_artifacts(out_dir)

        for index, command in enumerate(cleanup_commands(args)):
            steps.append(route.run_step(f"cleanup-{index}", command, out_dir, timeout_sec=args.adb_command_timeout, check=False))

        classification = result["payload_capture_summary"].get("classification")
        if classification == "msm-audio-cal-payload-captured":
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
                    for index, command in enumerate(cleanup_commands(args)):
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
    mode.add_argument("--dry-run", action="store_true", help="emit the V2450 live plan; no device action")
    mode.add_argument("--run-live", action="store_true", help="run the exact-gated V2450 M1 Magisk-module retry")
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
    parser.add_argument("--capture-duration-sec", type=int, default=DEFAULT_CAPTURE_DURATION_SEC)
    parser.add_argument("--capture-observe-sec", type=float, default=6.0)
    parser.add_argument("--post-module-root-retry-attempts", type=int, default=DEFAULT_POST_MODULE_ROOT_RETRY_ATTEMPTS)
    parser.add_argument("--post-module-root-retry-sleep-sec", type=float, default=DEFAULT_POST_MODULE_ROOT_RETRY_SLEEP_SEC)
    parser.add_argument("--post-module-adb-wait-timeout", type=float, default=DEFAULT_POST_MODULE_ADB_WAIT_TIMEOUT_SEC)
    parser.add_argument("--helper-completion-timeout-sec", type=float, default=DEFAULT_HELPER_COMPLETION_TIMEOUT_SEC)
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
