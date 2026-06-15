#!/usr/bin/env python3
"""V2434 exact-gated Magisk module namespace cleanup-probe runner.

This is the source/test-only implementation for the V2433 design.  Live mode,
when explicitly run later, boots pinned Android, performs one inert exact-path
create/remove probe under /data/adb/modules, proves no residue, then rolls back
to V2321.  It does not install a Magisk module, create activation files, reboot
before cleanup, run playback, or touch calibration ioctls.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import native_audio_acdb_android_measurement_planner_v2396 as v2396
import native_audio_android_route_delta_handoff_v2365 as route


RUN_ID = "V2434"
BUILD_TAG = "v2434-audio-magisk-cleanup-probe"
ROOT = v2396.ROOT
DEFAULT_OUT_BASE = ROOT / "workspace/private/runs/audio"
APPROVAL_PHRASE = (
    "AUD-5I-magisk-cleanup-probe go: rollbackable Android Magisk module namespace "
    "create-remove probe, inert unique directory only, no module.prop, no service.sh, "
    "no reboot before cleanup, rollback to V2321"
)
PROBE_PREFIX = ".a90_v2433_cleanup_probe_"
MODULES_DIR = "/data/adb/modules"
TAG_RE = re.compile(r"^[A-Za-z0-9._-]{1,48}$")


def rel(path: Path | str) -> str:
    return v2396.rel(path)


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def default_live_out_dir() -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return DEFAULT_OUT_BASE / f"{RUN_ID.lower()}-magisk-cleanup-probe-{stamp}"


def decision_slug() -> str:
    return f"{RUN_ID.lower()}-magisk-cleanup-probe"


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def route_args(args: argparse.Namespace) -> argparse.Namespace:
    return v2396.android_args(args)


def ensure_live_approval(args: argparse.Namespace) -> None:
    if args.approval != APPROVAL_PHRASE:
        raise RuntimeError("exact AUD-5I Magisk cleanup-probe approval phrase is required for --run-live")


def safe_probe_tag(value: str) -> str:
    if not TAG_RE.fullmatch(value):
        raise ValueError(f"unsafe probe tag: {value!r}")
    if "/" in value or value in {".", ".."}:
        raise ValueError(f"unsafe probe tag: {value!r}")
    return value


def default_probe_tag() -> str:
    return "v2434_" + datetime.now().strftime("%Y%m%d_%H%M%S")


def probe_path(tag: str) -> str:
    return f"{MODULES_DIR}/{PROBE_PREFIX}{safe_probe_tag(tag)}"


def adb_shell(args: argparse.Namespace, command: str) -> list[str]:
    return v2396.adb_base(args) + ["shell", command]


def adb_su_shell(args: argparse.Namespace, command: str) -> list[str]:
    return adb_shell(args, f"su -c {shlex.quote(command)}")


def adb_su_mm_shell(args: argparse.Namespace, command: str) -> list[str]:
    return adb_shell(args, f"su -mm -c {shlex.quote(command)}")


def root_readonly_probe_script() -> str:
    return r'''
echo A90_MAGISK_CLEANUP_READONLY_BEGIN
id 2>&1 || true
id -Z 2>&1 || true
command -v magisk 2>&1 || true
magisk -v 2>&1 || true
ls -ldZ /data/adb /data/adb/modules /data/adb/service.d 2>&1 || true
stat /data/adb /data/adb/modules /data/adb/service.d 2>&1 || true
echo A90_MAGISK_CLEANUP_READONLY_END
'''


def cleanup_probe_script(tag: str) -> str:
    path = probe_path(tag)
    marker_text = f"A90_V2434_CLEANUP_PROBE {safe_probe_tag(tag)}"
    return f'''
set -eu
PROBE_DIR={shlex.quote(path)}
MARKER="$PROBE_DIR/.probe"
A90_CLEANUP_CREATED=0
cleanup_on_exit() {{
  if [ "$A90_CLEANUP_CREATED" = "1" ]; then
    rm -f "$MARKER" 2>/dev/null || true
    rmdir "$PROBE_DIR" 2>/dev/null || true
  fi
}}
trap cleanup_on_exit EXIT
echo A90_MAGISK_CLEANUP_BEGIN
id
id -Z
echo A90_CLEANUP_TARGET "$PROBE_DIR"
echo A90_CLEANUP_PRE_MODULES
ls -ldZ /data/adb /data/adb/modules
PRE_RESIDUE="$(find /data/adb/modules -maxdepth 1 -type d -name '{PROBE_PREFIX}*' -print 2>&1 || true)"
if [ -n "$PRE_RESIDUE" ]; then
  echo A90_CLEANUP_RESIDUE_PRE_BEGIN
  printf '%s\\n' "$PRE_RESIDUE"
  echo A90_CLEANUP_RESIDUE_PRE_END
  exit 40
fi
mkdir "$PROBE_DIR"
A90_CLEANUP_CREATED=1
printf '%s\\n' {shlex.quote(marker_text)} > "$MARKER"
echo A90_CLEANUP_CREATED "$PROBE_DIR"
ls -ldZ "$PROBE_DIR"
stat "$PROBE_DIR" "$MARKER"
echo A90_CLEANUP_MARKER_BEGIN
cat "$MARKER"
echo A90_CLEANUP_MARKER_END
rm -f "$MARKER"
rmdir "$PROBE_DIR"
A90_CLEANUP_CREATED=0
trap - EXIT
echo A90_CLEANUP_REMOVED "$PROBE_DIR"
if [ -e "$PROBE_DIR" ]; then
  echo A90_CLEANUP_STILL_PRESENT "$PROBE_DIR"
  exit 41
fi
POST_RESIDUE="$(find /data/adb/modules -maxdepth 1 -type d -name '{PROBE_PREFIX}*' -print 2>&1 || true)"
if [ -n "$POST_RESIDUE" ]; then
  echo A90_CLEANUP_RESIDUE_POST_BEGIN
  printf '%s\\n' "$POST_RESIDUE"
  echo A90_CLEANUP_RESIDUE_POST_END
  exit 42
fi
echo A90_CLEANUP_NO_RESIDUE
echo A90_MAGISK_CLEANUP_OK
'''


def cleanup_commands(args: argparse.Namespace, tag: str) -> list[dict[str, Any]]:
    return [
        {
            "name": "root-readonly-probe",
            "mode": "su-c",
            "command": adb_su_shell(args, root_readonly_probe_script()),
        },
        {
            "name": "root-mount-master-readonly-probe",
            "mode": "su-mm-c",
            "command": adb_su_mm_shell(args, root_readonly_probe_script()),
        },
        {
            "name": "magisk-cleanup-create-remove",
            "mode": "su-c",
            "probe_path": probe_path(tag),
            "command": adb_su_shell(args, cleanup_probe_script(tag)),
        },
    ]


def command_safety(payload: dict[str, Any]) -> dict[str, Any]:
    commands = payload.get("commands", payload)
    flat = json.dumps(commands, sort_keys=True)
    forbidden = {
        "magisk_install_module": "--install-module",
        "magisk_remove_modules": "--remove-modules",
        "module_prop": "module.prop",
        "service_sh": "service.sh",
        "post_fs_data": "post-fs-data.sh",
        "system_prop": "system.prop",
        "sepolicy_rule": "sepolicy.rule",
        "chmod_exec": "chmod +x",
        "broad_modules_rm_rf": "rm -rf /data/adb/modules",
        "broad_modules_rm_r": "rm -r /data/adb/modules",
        "playback_activity": "am start",
        "tinyplay": "tinyplay",
        "tinymix": "tinymix",
        "calibration_ioctl": "msm_audio_cal ioctl",
        "msm_audio_cal": "/dev/msm_audio_cal",
        "fastboot": "fastboot",
        "raw_partition_write": " dd ",
    }
    findings = [{"name": name, "needle": needle} for name, needle in forbidden.items() if needle in flat]
    required = {
        "probe_prefix": [PROBE_PREFIX],
        "mkdir_probe_dir": ["mkdir", "$PROBE_DIR"],
        "remove_marker": ["rm -f", "$MARKER"],
        "rmdir_probe_dir": ["rmdir", "$PROBE_DIR"],
        "success_marker": ["A90_MAGISK_CLEANUP_OK"],
        "mount_master_probe": ["su -mm -c"],
        "rollback_v2321": ["rollback_v2321"],
    }
    missing = [name for name, needles in required.items() if not all(needle in flat for needle in needles)]
    return {
        "ok": not findings and not missing,
        "findings": findings,
        "missing_required_needles": missing,
        "forbidden": sorted(forbidden),
        "required": required,
    }


def dry_run(args: argparse.Namespace) -> dict[str, Any]:
    tag = safe_probe_tag(args.probe_tag or "v2434_dry_run")
    rargs = route_args(args)
    android_boot = route.select_android_boot_candidate()
    rollback = route.file_state(route.ROLLBACK_IMAGE, expected_sha256=route.ROLLBACK_SHA256)
    commands = {
        "flash_android": route.flash_android_command(rargs, "<private-run-dir>/android_boot_0600.img"),
        "android_post_handoff_settle": v2396.android_post_handoff_settle_commands(args),
        "cleanup_probe": cleanup_commands(args, tag),
        "android_wait_device_before_rollback": v2396.adb_base(args) + ["wait-for-device"],
        "android_reboot_recovery_for_rollback": route.android_reboot_recovery_command(rargs),
        "rollback_v2321": route.rollback_command(rargs),
    }
    payload: dict[str, Any] = {
        "run_id": RUN_ID,
        "build_tag": BUILD_TAG,
        "decision": f"{decision_slug()}-live-dry-run",
        "generated_at": now_iso(),
        "host_only": True,
        "device_action": "none",
        "approval_phrase_required_for_live": APPROVAL_PHRASE,
        "android_boot": android_boot,
        "rollback": rollback,
        "probe_tag": tag,
        "probe_path": probe_path(tag),
        "commands": commands,
        "hard_boundary": [
            "one inert exact-path create/remove probe only",
            "no module.prop, service.sh, post-fs-data.sh, system.prop, or sepolicy.rule",
            "no magisk install-module/remove-modules",
            "no reboot before cleanup proof",
            "no playback, mixer, PCM, ACDB, or calibration ioctl",
            "rollback to V2321 after cleanup proof",
        ],
    }
    safety = command_safety(payload)
    payload["command_safety"] = safety
    payload["future_live_ready"] = bool(android_boot.get("ok") and rollback.get("ok") and safety.get("ok"))
    blockers: list[str] = []
    if not android_boot.get("ok"):
        blockers.append("android boot candidate not ready")
    if not rollback.get("ok"):
        blockers.append("rollback image not ready")
    if not safety.get("ok"):
        blockers.append("command safety failed")
    payload["future_live_blockers"] = blockers
    payload["ok"] = bool(android_boot.get("ok") and rollback.get("ok") and safety.get("ok"))
    return payload


def summarize_live_outputs(out_dir: Path, steps: list[dict[str, Any]]) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "root_readonly_ok": False,
        "root_mount_master_readonly_ok": False,
        "cleanup_step_ok": False,
        "created_marker_seen": False,
        "removed_marker_seen": False,
        "no_residue_seen": False,
        "permission_denied_lines": [],
        "residue_lines": [],
    }
    for step in steps:
        name = step.get("name", "")
        stdout_path = ROOT / step.get("stdout", "")
        text = stdout_path.read_text(errors="replace") if stdout_path.exists() else ""
        if name == "root-readonly-probe" and "uid=0(root)" in text and "A90_MAGISK_CLEANUP_READONLY_END" in text:
            summary["root_readonly_ok"] = True
        if name == "root-mount-master-readonly-probe" and "uid=0(root)" in text and "A90_MAGISK_CLEANUP_READONLY_END" in text:
            summary["root_mount_master_readonly_ok"] = True
        if name == "magisk-cleanup-create-remove":
            summary["cleanup_step_ok"] = bool(step.get("ok") and "A90_MAGISK_CLEANUP_OK" in text)
            summary["created_marker_seen"] = "A90_CLEANUP_CREATED" in text
            summary["removed_marker_seen"] = "A90_CLEANUP_REMOVED" in text
            summary["no_residue_seen"] = "A90_CLEANUP_NO_RESIDUE" in text
        for line in text.splitlines():
            lowered = line.lower()
            if "permission denied" in lowered:
                summary["permission_denied_lines"].append({"step": name, "line": line[:240]})
            if "a90_cleanup_residue" in lowered or "a90_cleanup_still_present" in lowered:
                summary["residue_lines"].append({"step": name, "line": line[:240]})
    if (
        summary["root_readonly_ok"]
        and summary["root_mount_master_readonly_ok"]
        and summary["cleanup_step_ok"]
        and summary["created_marker_seen"]
        and summary["removed_marker_seen"]
        and summary["no_residue_seen"]
        and not summary["permission_denied_lines"]
        and not summary["residue_lines"]
    ):
        summary["classification"] = "cleanup-probe-ok"
    elif summary["residue_lines"]:
        summary["classification"] = "cleanup-residue-detected"
    elif summary["permission_denied_lines"]:
        summary["classification"] = "cleanup-permission-denied"
    else:
        summary["classification"] = "cleanup-probe-incomplete"
    return summary


def run_live(args: argparse.Namespace) -> dict[str, Any]:
    ensure_live_approval(args)
    tag = safe_probe_tag(args.probe_tag or default_probe_tag())
    plan = dry_run(argparse.Namespace(**{**vars(args), "probe_tag": tag}))
    if not plan.get("future_live_ready"):
        raise RuntimeError(f"V2434 live inputs are not ready: {plan.get('future_live_blockers')}")
    if not plan.get("command_safety", {}).get("ok"):
        raise RuntimeError(f"V2434 command safety failed: {plan.get('command_safety')}")

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
        "probe_tag": tag,
        "probe_path": probe_path(tag),
        "steps": steps,
        "rolled_back": False,
        "ok": False,
    }
    write_json(out_dir / "result.json", result)

    rargs = route_args(args)
    sealed = route.copy_sealed_android_boot(plan["android_boot"]["selected"], out_dir)
    result["sealed_android_boot"] = sealed
    write_json(out_dir / "result.json", result)

    rollback_needed = False
    try:
        rollback_needed = True
        steps.append(route.run_step(
            "flash-android",
            route.flash_android_command(rargs, str(out_dir / "android_boot_0600.img")),
            out_dir,
            timeout_sec=args.flash_timeout,
        ))
        v2396.run_android_post_handoff_settle(args, out_dir, steps)
        for item in cleanup_commands(args, tag):
            steps.append(route.run_step(
                item["name"],
                item["command"],
                out_dir,
                timeout_sec=args.adb_command_timeout,
                check=False,
            ))
        result["cleanup_summary"] = summarize_live_outputs(out_dir, steps)
        result["decision"] = f"{decision_slug()}-{result['cleanup_summary']['classification']}-before-rollback"
        result["ok"] = result["cleanup_summary"]["classification"] == "cleanup-probe-ok"
    except Exception as error:
        result["decision"] = f"{decision_slug()}-failed-before-rollback"
        result["error"] = str(error)
        result["ok"] = False
    finally:
        if rollback_needed:
            try:
                v2396.rollback_to_v2321_with_android_recovery(args, rargs, out_dir, steps, result)
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
    mode.add_argument("--dry-run", action="store_true", help="emit the V2434 cleanup-probe plan; no device action")
    mode.add_argument("--run-live", action="store_true", help="run the exact-gated V2434 cleanup probe")
    parser.add_argument("--adb", default="adb")
    parser.add_argument("--serial")
    parser.add_argument("--stimulus-apk", type=Path, default=v2396.DEFAULT_STIMULUS_APK, help="compatibility field for shared Android helper; not installed or launched")
    parser.add_argument("--android-timeout", type=float, default=420.0)
    parser.add_argument("--adb-command-timeout", type=float, default=120.0)
    parser.add_argument("--flash-timeout", type=float, default=900.0)
    parser.add_argument("--duration-ms", type=int, default=v2396.DEFAULT_DURATION_MS)
    parser.add_argument("--sample-rate", type=int, default=v2396.DEFAULT_SAMPLE_RATE)
    parser.add_argument("--amplitude", type=float, default=v2396.DEFAULT_AMPLITUDE)
    parser.add_argument("--active-delay-sec", type=float, default=0.75)
    parser.add_argument("--post-delay-sec", type=float, default=1.0)
    parser.add_argument("--from-native", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--approval")
    parser.add_argument("--probe-tag", help="safe test override for the generated probe tag")
    parser.add_argument("--out-dir", type=Path, help="private live output directory")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        if args.run_live:
            payload = run_live(args)
        else:
            payload = dry_run(args)
    except (RuntimeError, ValueError) as error:
        payload = {
            "run_id": RUN_ID,
            "build_tag": BUILD_TAG,
            "decision": f"{decision_slug()}-live-refused" if args.run_live else f"{decision_slug()}-dry-run-refused",
            "ok": False,
            "rolled_back": False,
            "reason": str(error),
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 1
    print(json.dumps(payload, indent=2, sort_keys=True))
    if args.run_live:
        return 0 if payload.get("ok") and payload.get("rolled_back") else 1
    return 0 if payload.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
