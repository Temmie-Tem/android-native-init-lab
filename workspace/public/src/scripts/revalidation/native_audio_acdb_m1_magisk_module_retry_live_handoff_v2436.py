#!/usr/bin/env python3
"""V2436 source/test M1 Magisk-module retry runner.

This runner supersedes the V2430 staging command shape without mutating the
historical V2430 artifact.  It keeps the same Android-good measurement goal
but uses the V2432/V2435-proven remote shell style:

    adb shell "su -c '<script>'"

It also carries forward the V2435 cleanup discipline: exact paths, pre-residue
checks, cleanup-finally, and no `magisk --install-module` fallback by default.
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
import native_audio_acdb_m1_magisk_module_live_handoff_v2430 as v2430
import native_audio_acdb_m1_magisk_module_planner_v2429 as v2429
import native_audio_acdb_threadset_clone_follow_live_handoff_v2424 as v2424
import native_audio_android_route_delta_handoff_v2365 as route
import native_audio_magisk_cleanup_probe_live_handoff_v2434 as v2434


RUN_ID = "V2436"
BUILD_TAG = "v2436-audio-acdb-m1-magisk-module-retry"
ROOT = v2429.ROOT
DEFAULT_OUT_BASE = ROOT / "workspace/private/runs/audio"
DEFAULT_CAPTURE_DURATION_SEC = v2430.DEFAULT_CAPTURE_DURATION_SEC
REMOTE_MODULE_DIR = f"/data/adb/modules/{v2429.MODULE_ID}"
REMOTE_MODULE_UPDATE_DIR = f"/data/adb/modules_update/{v2429.MODULE_ID}"
REMOTE_STAGE_DIR = f"{v2429.REMOTE_DIR}/module-stage"
APPROVAL_PHRASE = (
    "AUD-5J-acdb-m1-magisk-module-retry go: rollbackable Android AudioTrack speaker "
    "msm_audio_cal ioctl payload capture with temporary Magisk service module, corrected "
    "su-c staging, exact cleanup, no native calibration ioctl, no native speaker write, "
    "rollback to V2321"
)


def rel(path: Path | str) -> str:
    return v2429.rel(path)


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def default_live_out_dir() -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return DEFAULT_OUT_BASE / f"{RUN_ID.lower()}-acdb-m1-magisk-module-retry-{stamp}"


def decision_slug() -> str:
    return f"{RUN_ID.lower()}-acdb-m1-magisk-module-retry"


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def args_for_v2429(args: argparse.Namespace) -> argparse.Namespace:
    return argparse.Namespace(
        dry_run=True,
        materialize_module_template=args.materialize_module_template,
        module_out_dir=args.module_out_dir,
        cc=args.cc,
        stimulus_apk=args.stimulus_apk,
        capture_duration_sec=args.capture_duration_sec,
        max_bytes=args.max_bytes,
        process_poll_sec=args.process_poll_sec,
    )


def ensure_live_approval(args: argparse.Namespace) -> None:
    if args.approval != APPROVAL_PHRASE:
        raise RuntimeError("exact AUD-5J ACDB M1 Magisk retry approval phrase is required for --run-live")


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
    return v2430.local_module_paths(args)


def remote_stage_path(name: str) -> str:
    return v2430.remote_stage_path(name)


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
RUN_DIR={shlex.quote(v2429.REMOTE_DIR)}
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
RUN_DIR={shlex.quote(v2429.REMOTE_DIR)}
STAGE_DIR={shlex.quote(REMOTE_STAGE_DIR)}
ARTIFACT_DIR={shlex.quote(v2429.REMOTE_ARTIFACT_DIR)}
echo A90_M1_STAGE_SETUP_BEGIN
mkdir -p "$STAGE_DIR/bin" "$ARTIFACT_DIR"
chmod 700 "$RUN_DIR" "$STAGE_DIR" "$STAGE_DIR/bin" "$ARTIFACT_DIR"
echo A90_M1_STAGE_SETUP_OK
"""
    return adb_su_shell(args, command)


def install_module_command(args: argparse.Namespace) -> list[str]:
    helper = f"{REMOTE_MODULE_DIR}/bin/{v2429.HELPER_NAME}"
    command = f"""
set -eu
MODULE_DIR={shlex.quote(REMOTE_MODULE_DIR)}
MODULE_UPDATE_DIR={shlex.quote(REMOTE_MODULE_UPDATE_DIR)}
STAGE_DIR={shlex.quote(REMOTE_STAGE_DIR)}
HELPER={shlex.quote(helper)}
echo A90_M1_INSTALL_BEGIN
if [ -e "$MODULE_DIR" ] || [ -e "$MODULE_UPDATE_DIR" ]; then
  echo A90_M1_INSTALL_RESIDUE_PRESENT
  exit 52
fi
mkdir -p "$MODULE_DIR/bin"
cp "$STAGE_DIR/module.prop" "$MODULE_DIR/module.prop"
cp "$STAGE_DIR/service.sh" "$MODULE_DIR/service.sh"
cp "$STAGE_DIR/README.md" "$MODULE_DIR/README.md"
cp "$STAGE_DIR/bin/{v2429.HELPER_NAME}" "$HELPER"
rm -f "$MODULE_DIR/disable" "$MODULE_DIR/remove"
chown -R 0:0 "$MODULE_DIR"
chmod 755 "$MODULE_DIR" "$MODULE_DIR/bin"
chmod 700 "$MODULE_DIR/service.sh" "$HELPER"
chmod 600 "$MODULE_DIR/module.prop" "$MODULE_DIR/README.md"
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
    helper = f"{REMOTE_MODULE_DIR}/bin/{v2429.HELPER_NAME}"
    return f"""
set -eu
MODULE_DIR={shlex.quote(REMOTE_MODULE_DIR)}
MODULE_UPDATE_DIR={shlex.quote(REMOTE_MODULE_UPDATE_DIR)}
RUN_DIR={shlex.quote(v2429.REMOTE_DIR)}
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
        adb_su_shell(args, f"ls -ld {shlex.quote(REMOTE_MODULE_DIR)} {shlex.quote(v2429.REMOTE_DIR)} 2>&1 || true"),
    ]


def collect_prepare_command(args: argparse.Namespace) -> list[str]:
    command = f"""
set -eu
RUN_DIR={shlex.quote(v2429.REMOTE_DIR)}
ARTIFACT_DIR={shlex.quote(v2429.REMOTE_ARTIFACT_DIR)}
if [ -d "$ARTIFACT_DIR" ]; then
  chmod -R a+rX "$RUN_DIR"
fi
ls -lR "$RUN_DIR" 2>&1 || true
"""
    return adb_su_shell(args, command)


def collect_command(args: argparse.Namespace, destination: str = "<private-run-dir>/device-artifacts") -> list[str]:
    return v2396.adb_base(args) + ["pull", v2429.REMOTE_ARTIFACT_DIR, destination]


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
        v2429.HELPER_NAME,
        "su -c",
        "su -mm -c",
        "A90_M1_RESIDUE_CHECK_OK",
        "A90_M1_INSTALL_OK",
        "A90_M1_CLEANUP_OK",
        "adb\", \"reboot",
        route.APK_PACKAGE,
        "rollback_v2321",
        v2429.REMOTE_ARTIFACT_DIR,
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
    module_plan = v2429.dry_run_payload(args_for_v2429(args))
    route_args = v2396.android_args(args)
    commands = {
        "flash_android": route.flash_android_command(route_args, "<private-run-dir>/android_boot_0600.img"),
        "android_post_handoff_settle": v2396.android_post_handoff_settle_commands(args),
        "stage_module_and_apk": stage_commands(args),
        "android_reboot_for_magisk_service": android_reboot_command(args),
        "android_post_module_reboot_settle": v2396.android_post_handoff_settle_commands(args),
        "logcat_clear_before_stimulus": route.logcat_clear_command(route_args),
        "logcat_capture_full": route.logcat_capture_command(route_args),
        "playback_start_background": route.playback_start_command(route_args),
        "playback_result": route.stimulus_result_commands(route_args),
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
            "module_id": v2429.MODULE_ID,
            "remote_module_dir": REMOTE_MODULE_DIR,
            "remote_module_update_dir": REMOTE_MODULE_UPDATE_DIR,
            "remote_stage_dir": REMOTE_STAGE_DIR,
            "activation": "manual /data/adb/modules staging followed by one Android reboot",
            "cleanup_required_before_rollback": True,
            "native_runtime_dependency": False,
            "uses_magisk_install_module": False,
            "corrected_remote_shell": "adb shell \"su -c '<script>'\"",
            "v2435_cleanup_discipline": True,
        },
        "commands": commands,
        "stage_adb_waits": stage_wait_plan(args),
        "hard_boundary": [
            "temporary Android-side measurement module only",
            "no native-init Magisk dependency",
            "no native calibration ioctl issue",
            "no native speaker write, tinymix set, tinyplay, Wi-Fi, DHCP, route, or ping",
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
        blockers.append(f"V2429 module plan not live-ready: {module_plan.get('future_live_blockers')}")
    if not safety.get("ok"):
        blockers.append("V2436 command safety failed")
    payload["future_live_blockers"] = blockers
    payload["ok"] = bool(module_plan.get("ok") and safety.get("ok"))
    return payload


def run_live(args: argparse.Namespace) -> dict[str, Any]:
    ensure_live_approval(args)
    args.materialize_module_template = True
    route_args = v2396.android_args(args)
    plan = dry_run(args)
    if not plan.get("future_live_ready"):
        raise RuntimeError(f"V2436 live inputs are not ready: {plan.get('future_live_blockers')}")
    if not plan.get("command_safety", {}).get("ok"):
        raise RuntimeError(f"V2436 command safety failed: {plan.get('command_safety')}")

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
        v2396.run_android_post_handoff_settle(args, out_dir, steps)

        steps.append(route.run_step("logcat-clear-before-stimulus", route.logcat_clear_command(route_args), out_dir, timeout_sec=args.adb_command_timeout, check=False))
        logcat_capture = route.start_logcat_capture(route_args, out_dir)
        logcat_capture["record"]["name"] = "acdb-m1-magisk-module-retry-logcat"
        logcat_capture["record"]["filter_regex_offline"] = v2396.LOG_FILTER_REGEX
        steps.append(logcat_capture["record"])

        steps.append(route.run_step("playback-start-background", route.playback_start_command(route_args), out_dir, timeout_sec=args.adb_command_timeout))
        wait_sec = max(float(args.capture_observe_sec), (args.duration_ms / 1000.0) + args.post_delay_sec + 1.0)
        time.sleep(wait_sec)
        for index, command in enumerate(route.stimulus_result_commands(route_args)):
            steps.append(route.run_step(f"playback-result-{index}", command, out_dir, timeout_sec=args.adb_command_timeout, check=False))

        steps.append(route.run_step("prepare-private-artifacts-for-pull", collect_prepare_command(args), out_dir, timeout_sec=args.adb_command_timeout, check=False))
        steps.append(route.run_step(
            "collect-private-artifacts",
            collect_command(args, str(out_dir / "device-artifacts")),
            out_dir,
            timeout_sec=args.adb_command_timeout,
            check=False,
        ))
        result["payload_capture_summary"] = v2424.summarize_capture_artifacts(out_dir)

        for index, command in enumerate(cleanup_commands(args)):
            steps.append(route.run_step(f"cleanup-{index}", command, out_dir, timeout_sec=args.adb_command_timeout, check=False))

        classification = result["payload_capture_summary"].get("classification")
        if classification == "captured-msm-audio-cal-payload-events":
            result["decision"] = f"{decision_slug()}-events-before-rollback"
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
    mode.add_argument("--dry-run", action="store_true", help="emit the V2436 live plan; no device action")
    mode.add_argument("--run-live", action="store_true", help="run the exact-gated V2436 M1 Magisk-module retry")
    parser.add_argument("--materialize-module-template", action="store_true", help="compile and write private V2429 module template")
    parser.add_argument("--module-out-dir", type=Path, default=v2429.DEFAULT_MODULE_OUT_DIR)
    parser.add_argument("--cc", default=v2429.DEFAULT_CC)
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
    parser.add_argument("--max-bytes", type=int, default=v2429.DEFAULT_MAX_BYTES)
    parser.add_argument("--process-poll-sec", type=float, default=v2429.DEFAULT_PROCESS_POLL_SEC)
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
