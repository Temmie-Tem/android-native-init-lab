#!/usr/bin/env python3
"""V2396 host-only Android/Magisk ACDB measurement planner.

This is a dry-run-only planner for the V2395 Branch-A discriminator.  It does
not boot Android, install a Magisk module, start playback, touch ADSP, open
/dev/snd, write mixer controls, or call ACDB ioctls.  It builds a future command
plan that reuses the proven Android handoff and V2321 rollback path, then
captures the vendor HAL/ACDB/App-Type sequence under normal Android AudioTrack
speaker playback.

Magisk is treated as a private Android-side delivery/observability mechanism
only.  The default plan uses a transient Magisk-style module directory invoked
through `su -c`; it does not install a persistent module with Magisk's module
manager.  Any generated module template is written under workspace/private and
must not be committed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import native_audio_android_route_delta_handoff_v2365 as route


RUN_ID = "V2396"
BUILD_TAG = "v2396-audio-acdb-android-magisk-measurement-planner"
ROOT = Path(__file__).resolve().parents[5]
DEFAULT_MODULE_OUT_DIR = ROOT / "workspace/private/builds/audio/v2396-acdb-magisk-measurement-module"
DEFAULT_STIMULUS_APK = ROOT / "workspace/private/builds/audio/v2373-android-route-stimulus-apk/A90AudioRouteStimulus.apk"
REMOTE_DIR = "/data/local/tmp/a90-audio-acdb-v2396"
REMOTE_TINYMIX = f"{REMOTE_DIR}/tinymix"
REMOTE_MODULE_DIR = f"{REMOTE_DIR}/module"
REMOTE_PROBE = f"{REMOTE_MODULE_DIR}/system/bin/a90_acdb_probe.sh"
REMOTE_SERVICE_SH = f"{REMOTE_MODULE_DIR}/service.sh"
REMOTE_ARTIFACT_DIR = "/cache/a90-audio-acdb-v2396"
MODULE_ID = "a90_audio_acdb_probe_v2396"
APPROVAL_PHRASE = (
    "AUD-5A-android-acdb-magisk-measurement go: rollbackable Android AudioTrack "
    "speaker ACDB/AppType capture, transient Magisk-root observer only, no native "
    "speaker write, rollback to V2321"
)
DEFAULT_DURATION_MS = 2000
DEFAULT_SAMPLE_RATE = 48000
DEFAULT_AMPLITUDE = 0.05
LOG_FILTER_REGEX = (
    "ACDB|acdb|audio_hw|platform|adm|afe|q6asm|app_type|App Type|AudioFlinger|"
    "AudioTrack|A90_AUDIO_STIMULUS|msm_audio_cal|send_afe_cal|q6asm_send_cal|adm_open"
)


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


def android_args(args: argparse.Namespace) -> argparse.Namespace:
    """Create a namespace compatible with the V2365 route-delta planner helpers."""

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


def adb_shell(args: argparse.Namespace, command: str) -> list[str]:
    return adb_base(args) + ["shell", command]


def adb_root_shell(args: argparse.Namespace, command: str) -> list[str]:
    return adb_base(args) + ["shell", "su", "-c", command]


def adb_push(args: argparse.Namespace, source: str, destination: str) -> list[str]:
    return adb_base(args) + ["push", source, destination]


def file_state(path: Path, *, expected_sha256: str | None = None, zip_magic: bool = False) -> dict[str, Any]:
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
    if zip_magic:
        state["zip_magic"] = path.read_bytes()[:4] == b"PK\x03\x04"
    state["ok"] = bool(
        state["size"] > 0
        and not state["group_or_world_writable"]
        and state.get("sha256_ok", True)
        and state.get("zip_magic", True)
    )
    return state


def module_files() -> dict[str, str]:
    helper = r'''#!/system/bin/sh
set -eu
PHASE="${1:-manual}"
OUT="/cache/a90-audio-acdb-v2396"
TINYMIX="${A90_V2396_TINYMIX:-/data/local/tmp/a90-audio-acdb-v2396/tinymix}"
mkdir -p "$OUT"
chmod 700 "$OUT" 2>/dev/null || true
stamp="$(date +%Y%m%d-%H%M%S 2>/dev/null || echo unknown)"
echo "phase=$PHASE stamp=$stamp" > "$OUT/${PHASE}-meta.txt"
(getprop | grep -Ei 'audio|acdb|vendor\.audio|media|qcom' || true) > "$OUT/${PHASE}-getprop-audio.txt"
(ps -A 2>/dev/null || ps 2>/dev/null || true) > "$OUT/${PHASE}-ps.txt"
(pidof android.hardware.audio.service 2>/dev/null || true) > "$OUT/${PHASE}-audio-hal-pids.txt"
for pid in $(cat "$OUT/${PHASE}-audio-hal-pids.txt" 2>/dev/null); do
  [ -r "/proc/$pid/maps" ] && cat "/proc/$pid/maps" > "$OUT/${PHASE}-audio-hal-$pid-maps.txt" || true
  [ -r "/proc/$pid/fd" ] && ls -l "/proc/$pid/fd" > "$OUT/${PHASE}-audio-hal-$pid-fd.txt" 2>&1 || true
done
(ls -l /dev/msm_audio_cal /dev/ion /dev/snd 2>&1 || true) > "$OUT/${PHASE}-devnodes.txt"
(cat /proc/asound/cards /proc/asound/pcm 2>&1 || true) > "$OUT/${PHASE}-proc-asound.txt"
if [ -x "$TINYMIX" ]; then
  "$TINYMIX" -D 0 --all-values > "$OUT/${PHASE}-tinymix-all-values.txt" 2>&1 || true
fi
(dmesg | tail -n 400 2>&1 || true) > "$OUT/${PHASE}-dmesg-tail.txt"
exit 0
'''
    service = r'''#!/system/bin/sh
MODDIR="${0%/*}"
A90_V2396_TINYMIX="/data/local/tmp/a90-audio-acdb-v2396/tinymix" \
  "$MODDIR/system/bin/a90_acdb_probe.sh" boot-observe >> /cache/a90-audio-acdb-v2396/service.log 2>&1
exit 0
'''
    module_prop = """id=a90_audio_acdb_probe_v2396
name=A90 Audio ACDB Probe V2396
version=0.1
versionCode=2396
author=A90 native-init project
description=Temporary Android-side ACDB/AppType measurement helper. Private only; not a native-init runtime dependency.
"""
    readme = """# A90 Audio ACDB Probe V2396

Private transient Magisk-style module template for Android-side measurement only.
Default V2396 live planning invokes `service.sh` manually through `su -c`; it does not require a persistent Magisk module install.
Do not commit generated zips, logs, or device artifacts.
"""
    return {
        "module.prop": module_prop,
        "service.sh": service,
        "system/bin/a90_acdb_probe.sh": helper,
        "README.md": readme,
    }


def write_module_template(out_dir: Path) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    os.chmod(out_dir, 0o700)
    written: list[dict[str, Any]] = []
    for relative, content in module_files().items():
        path = out_dir / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        mode = 0o700 if relative.endswith(".sh") else 0o600
        os.chmod(path, mode)
        written.append({"path": rel(path), "mode": oct(mode), "sha256": sha256(path)})
    for directory in [out_dir, *(path for path in out_dir.rglob("*") if path.is_dir())]:
        os.chmod(directory, 0o700)

    zip_path = out_dir / f"{MODULE_ID}.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for relative in module_files():
            path = out_dir / relative
            info = zipfile.ZipInfo(relative)
            file_mode = 0o700 if relative.endswith(".sh") else 0o600
            info.external_attr = (stat.S_IFREG | file_mode) << 16
            zf.writestr(info, path.read_bytes())
    os.chmod(zip_path, 0o600)
    manifest = {
        "generated_at": now_iso(),
        "module_id": MODULE_ID,
        "module_out_dir": rel(out_dir),
        "zip": file_state(zip_path, zip_magic=True),
        "files": written,
    }
    manifest_path = out_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    os.chmod(manifest_path, 0o600)
    manifest["manifest"] = file_state(manifest_path)
    return manifest


def module_state(args: argparse.Namespace) -> dict[str, Any]:
    state: dict[str, Any] = {
        "module_id": MODULE_ID,
        "mode": "transient-magisk-root-helper",
        "native_runtime_dependency": False,
        "persistent_magisk_install_default": False,
        "out_dir": rel(args.module_out_dir),
        "materialize_requested": bool(args.materialize_module_template),
    }
    if args.materialize_module_template:
        state.update(write_module_template(args.module_out_dir))
    else:
        zip_path = args.module_out_dir / f"{MODULE_ID}.zip"
        state["zip"] = file_state(zip_path, zip_magic=True)
        state["planned_files"] = sorted(module_files())
        state["reason"] = "module template not materialized; rerun with --materialize-module-template for future live readiness"
    return state


def stage_commands(args: argparse.Namespace, route_args: argparse.Namespace, module: dict[str, Any], tinymix: dict[str, Any]) -> list[list[str]]:
    zip_path = module.get("zip", {}).get("path") or rel(args.module_out_dir / f"{MODULE_ID}.zip")
    return [
        adb_root_shell(args, f"rm -rf {REMOTE_DIR} {REMOTE_ARTIFACT_DIR} && mkdir -p {REMOTE_DIR} {REMOTE_MODULE_DIR}/system/bin && chmod 700 {REMOTE_DIR} {REMOTE_ARTIFACT_DIR}"),
        adb_push(args, tinymix.get("path") or "<tinymix>", REMOTE_TINYMIX),
        adb_push(args, rel(args.module_out_dir / "module.prop"), f"{REMOTE_MODULE_DIR}/module.prop"),
        adb_push(args, rel(args.module_out_dir / "service.sh"), REMOTE_SERVICE_SH),
        adb_push(args, rel(args.module_out_dir / "system/bin/a90_acdb_probe.sh"), REMOTE_PROBE),
        adb_push(args, zip_path, f"{REMOTE_DIR}/{MODULE_ID}.zip"),
        adb_push(args, rel(args.stimulus_apk), f"{REMOTE_DIR}/A90AudioRouteStimulus.apk"),
        adb_base(args) + ["install", "-r", f"{REMOTE_DIR}/A90AudioRouteStimulus.apk"],
        adb_root_shell(args, f"chmod 700 {REMOTE_TINYMIX} {REMOTE_SERVICE_SH} {REMOTE_PROBE} && chmod 600 {REMOTE_MODULE_DIR}/module.prop {REMOTE_DIR}/{MODULE_ID}.zip"),
    ]


def probe_command(args: argparse.Namespace, phase: str) -> list[str]:
    return adb_root_shell(args, f"A90_V2396_TINYMIX={REMOTE_TINYMIX} {REMOTE_PROBE} {phase}")


def collect_command(args: argparse.Namespace) -> list[str]:
    return adb_base(args) + ["pull", REMOTE_ARTIFACT_DIR, "<private-run-dir>/device-artifacts"]


def cleanup_commands(args: argparse.Namespace) -> list[list[str]]:
    return [
        adb_base(args) + ["uninstall", route.APK_PACKAGE],
        adb_root_shell(args, f"rm -rf {REMOTE_DIR} {REMOTE_ARTIFACT_DIR}"),
    ]


def optional_strace_plan(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "enabled_by_default": False,
        "reason": "ptrace may perturb audio timing; use only if logcat/dmesg do not reveal ACDB ioctl sequence",
        "command_template": adb_root_shell(
            args,
            "pid=$(pidof android.hardware.audio.service | awk '{print $1}'); "
            "[ -n \"$pid\" ] && timeout 5 strace -ff -tt -s 256 -e trace=openat,ioctl -p $pid "
            "> /cache/a90-audio-acdb-v2396/strace-audio-hal.txt 2>&1",
        ),
    }


def command_safety(plan: dict[str, Any]) -> dict[str, Any]:
    flat = json.dumps(plan.get("commands", plan), sort_keys=True)
    forbidden = {
        "tinyplay": "tinyplay",
        "native_speaker_pilot": "speaker_pilot",
        "tinymix_set_token": " tinymix set ",
        "direct_block_write": " dd if=",
        "fastboot": "fastboot",
        "persistent_magisk_install": "magisk --install-module",
        "svc_audio_policy_mutation": "cmd audio",
        "settings_put": "settings put",
    }
    findings = [{"name": name, "needle": needle} for name, needle in forbidden.items() if needle in flat]
    required = [
        "native_init_flash.py",
        "--post-flash-target",
        "android-adb",
        "su",
        REMOTE_PROBE,
        "logcat",
        "A90AudioRouteStimulusActivity",
        "rollback_v2321",
    ]
    missing = [needle for needle in required if needle not in flat]
    return {
        "ok": not findings and not missing,
        "findings": findings,
        "missing_required_needles": missing,
        "default_delivery": "transient Magisk-root helper; no persistent module install",
        "forbidden": sorted(forbidden),
    }


def dry_run_payload(args: argparse.Namespace) -> dict[str, Any]:
    route_args = android_args(args)
    android_boot = route.select_android_boot_candidate()
    rollback = route.file_state(route.ROLLBACK_IMAGE, expected_sha256=route.ROLLBACK_SHA256)
    tinymix = route.tinymix_state()
    stimulus = route.stimulus_apk_state(args.stimulus_apk)
    module = module_state(args)
    sealed_boot = "<private-run-dir>/android_boot_0600.img"
    commands = {
        "flash_android": route.flash_android_command(route_args, sealed_boot),
        "stage_transient_module_and_stimulus": stage_commands(args, route_args, module, tinymix),
        "baseline_probe": probe_command(args, "baseline"),
        "logcat": {
            "clear": route.logcat_clear_command(route_args),
            "capture_full": route.logcat_capture_command(route_args),
            "filter_regex_offline": LOG_FILTER_REGEX,
            "private_stdout": "<private-run-dir>/acdb-logcat.stdout.txt",
            "private_stderr": "<private-run-dir>/acdb-logcat.stderr.txt",
        },
        "playback_start_background": route.playback_start_command(route_args),
        "active_probe": probe_command(args, "active"),
        "post_probe": probe_command(args, "post"),
        "collect_private_artifacts": collect_command(args),
        "cleanup": cleanup_commands(args),
        "android_reboot_recovery_for_rollback": route.android_reboot_recovery_command(route_args),
        "rollback_v2321": route.rollback_command(route_args),
        "optional_strace_disabled": optional_strace_plan(args),
    }
    plan = {
        "run_id": RUN_ID,
        "build_tag": BUILD_TAG,
        "decision": "v2396-audio-acdb-android-magisk-planner-dry-run",
        "generated_at": now_iso(),
        "host_only": True,
        "device_action": "none",
        "approval_phrase_required_for_future_live": APPROVAL_PHRASE,
        "android_boot": android_boot,
        "rollback": rollback,
        "tinymix": tinymix,
        "stimulus_apk": stimulus,
        "magisk_module": module,
        "measurement_focus": {
            "speaker_acdb_id": 15,
            "expected_app_type": 69941,
            "sample_rate": args.sample_rate,
            "amplitude": args.amplitude,
            "duration_ms": args.duration_ms,
            "log_filter_regex": LOG_FILTER_REGEX,
        },
        "commands": commands,
        "hard_boundary": [
            "dry-run-only in V2396",
            "no Android boot or Magisk install in this unit",
            "future live path must rollback to V2321",
            "Magisk is Android-side observability/staging only",
            "no native-init runtime dependency on Magisk or Android services",
            "no native speaker write, tinyplay, /dev/snd open, or mixer set",
            "raw Android logs and generated module artifacts stay under workspace/private",
        ],
        "future_decision_output": [
            "bounded native ACDB bootstrap candidate if a small call/file/devnode sequence is observed",
            "HAL-dependent classification if the sequence requires broad Android service state",
        ],
    }
    safety = command_safety(plan)
    module_ready = bool(module.get("zip", {}).get("ok") and args.materialize_module_template)
    plan["command_safety"] = safety
    plan["future_live_ready"] = bool(
        android_boot.get("ok")
        and rollback.get("ok")
        and tinymix.get("ok")
        and stimulus.get("ok")
        and module_ready
        and safety.get("ok")
    )
    blockers: list[str] = []
    for name, item in (("android_boot", android_boot), ("rollback", rollback), ("tinymix", tinymix), ("stimulus_apk", stimulus)):
        if not item.get("ok"):
            blockers.append(f"{name} not ready")
    if not module_ready:
        blockers.append("module template not materialized or zip not private-ready")
    if not safety.get("ok"):
        blockers.append("command safety failed")
    plan["future_live_blockers"] = blockers
    plan["ok"] = bool(android_boot.get("ok") and rollback.get("ok") and tinymix.get("ok") and stimulus.get("ok") and safety.get("ok"))
    return plan


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="emit the V2396 plan; no device action")
    parser.add_argument("--materialize-module-template", action="store_true", help="write private Magisk-style module template files and zip")
    parser.add_argument("--module-out-dir", type=Path, default=DEFAULT_MODULE_OUT_DIR)
    parser.add_argument("--stimulus-apk", type=Path, default=DEFAULT_STIMULUS_APK)
    parser.add_argument("--adb", default="adb")
    parser.add_argument("--serial")
    parser.add_argument("--android-timeout", type=float, default=420.0)
    parser.add_argument("--adb-command-timeout", type=float, default=120.0)
    parser.add_argument("--flash-timeout", type=float, default=900.0)
    parser.add_argument("--duration-ms", type=int, default=DEFAULT_DURATION_MS)
    parser.add_argument("--sample-rate", type=int, default=DEFAULT_SAMPLE_RATE)
    parser.add_argument("--amplitude", type=float, default=DEFAULT_AMPLITUDE)
    parser.add_argument("--active-delay-sec", type=float, default=0.75)
    parser.add_argument("--post-delay-sec", type=float, default=1.0)
    parser.add_argument("--from-native", action=argparse.BooleanOptionalAction, default=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = dry_run_payload(args)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
