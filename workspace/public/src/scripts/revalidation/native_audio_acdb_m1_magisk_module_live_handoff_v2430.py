#!/usr/bin/env python3
"""V2430 exact-gated live handoff for the V2429 ACDB M1 Magisk module.

This runner activates the private V2429 temporary Magisk `service.sh` module
under stock Android, reboots once so Magisk starts it in late_start service
mode, launches the bounded AudioTrack speaker stimulus, pulls only private
artifacts, removes the module, and rolls back to V2321.

It does not issue native calibration ioctls, does not write native mixer/PCM
state, does not call `magisk --install-module`, and does not make Magisk a
native-init runtime dependency.
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
import native_audio_acdb_m1_magisk_module_planner_v2429 as v2429
import native_audio_acdb_threadset_clone_follow_live_handoff_v2424 as v2424
import native_audio_android_route_delta_handoff_v2365 as route


RUN_ID = "V2430"
BUILD_TAG = "v2430-audio-acdb-m1-magisk-module-live"
ROOT = v2429.ROOT
APPROVAL_PHRASE = v2429.APPROVAL_PHRASE
DEFAULT_OUT_BASE = ROOT / "workspace/private/runs/audio"
DEFAULT_CAPTURE_DURATION_SEC = 180
REMOTE_MODULE_DIR = f"/data/adb/modules/{v2429.MODULE_ID}"
REMOTE_MODULE_UPDATE_DIR = f"/data/adb/modules_update/{v2429.MODULE_ID}"
REMOTE_STAGE_DIR = f"{v2429.REMOTE_DIR}/module-stage"


def rel(path: Path | str) -> str:
    return v2429.rel(path)


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def default_live_out_dir() -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return DEFAULT_OUT_BASE / f"{RUN_ID.lower()}-acdb-m1-magisk-module-capture-{stamp}"


def decision_slug() -> str:
    return f"{RUN_ID.lower()}-acdb-m1-magisk-module-capture"


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
        raise RuntimeError("exact AUD-5G ACDB M1 Magisk-module capture approval phrase is required for --run-live")


def adb_subcommand(command: list[str]) -> str | None:
    if not command or command[0] != "adb":
        return None
    index = 1
    if len(command) > 3 and command[index] == "-s":
        index += 2
    if index >= len(command):
        return None
    return command[index]


def needs_adb_wait(command: list[str]) -> bool:
    return adb_subcommand(command) in {"push", "install"}


def stage_wait_command(args: argparse.Namespace) -> list[str]:
    return v2396.adb_base(args) + ["wait-for-device"]


def local_module_paths(args: argparse.Namespace) -> dict[str, Path]:
    return {
        "module.prop": args.module_out_dir / "module.prop",
        "service.sh": args.module_out_dir / "service.sh",
        "README.md": args.module_out_dir / "README.md",
        v2429.HELPER_NAME: args.module_out_dir / "bin" / v2429.HELPER_NAME,
    }


def remote_stage_path(name: str) -> str:
    if name == v2429.HELPER_NAME:
        return f"{REMOTE_STAGE_DIR}/bin/{v2429.HELPER_NAME}"
    return f"{REMOTE_STAGE_DIR}/{name}"


def setup_stage_command(args: argparse.Namespace) -> list[str]:
    command = (
        f"rm -rf {shlex.quote(v2429.REMOTE_DIR)} "
        f"{shlex.quote(REMOTE_MODULE_DIR)} {shlex.quote(REMOTE_MODULE_UPDATE_DIR)}; "
        f"mkdir -p {shlex.quote(REMOTE_STAGE_DIR)}/bin "
        f"{shlex.quote(v2429.REMOTE_ARTIFACT_DIR)}; "
        f"chmod 700 {shlex.quote(v2429.REMOTE_DIR)} "
        f"{shlex.quote(REMOTE_STAGE_DIR)} {shlex.quote(REMOTE_STAGE_DIR)}/bin "
        f"{shlex.quote(v2429.REMOTE_ARTIFACT_DIR)}"
    )
    return v2396.adb_root_shell(args, command)


def install_module_command(args: argparse.Namespace) -> list[str]:
    helper = f"{REMOTE_MODULE_DIR}/bin/{v2429.HELPER_NAME}"
    command = (
        f"rm -rf {shlex.quote(REMOTE_MODULE_DIR)} {shlex.quote(REMOTE_MODULE_UPDATE_DIR)}; "
        f"mkdir -p {shlex.quote(REMOTE_MODULE_DIR)}/bin; "
        f"cp {shlex.quote(REMOTE_STAGE_DIR)}/module.prop {shlex.quote(REMOTE_MODULE_DIR)}/module.prop; "
        f"cp {shlex.quote(REMOTE_STAGE_DIR)}/service.sh {shlex.quote(REMOTE_MODULE_DIR)}/service.sh; "
        f"cp {shlex.quote(REMOTE_STAGE_DIR)}/README.md {shlex.quote(REMOTE_MODULE_DIR)}/README.md; "
        f"cp {shlex.quote(REMOTE_STAGE_DIR)}/bin/{v2429.HELPER_NAME} {shlex.quote(helper)}; "
        f"rm -f {shlex.quote(REMOTE_MODULE_DIR)}/disable {shlex.quote(REMOTE_MODULE_DIR)}/remove; "
        f"chown -R 0:0 {shlex.quote(REMOTE_MODULE_DIR)}; "
        f"chmod 755 {shlex.quote(REMOTE_MODULE_DIR)} {shlex.quote(REMOTE_MODULE_DIR)}/bin; "
        f"chmod 700 {shlex.quote(REMOTE_MODULE_DIR)}/service.sh {shlex.quote(helper)}; "
        f"chmod 600 {shlex.quote(REMOTE_MODULE_DIR)}/module.prop {shlex.quote(REMOTE_MODULE_DIR)}/README.md; "
        f"ls -l {shlex.quote(REMOTE_MODULE_DIR)} {shlex.quote(REMOTE_MODULE_DIR)}/bin"
    )
    return v2396.adb_root_shell(args, command)


def stage_commands(args: argparse.Namespace) -> list[list[str]]:
    commands: list[list[str]] = [setup_stage_command(args)]
    for name, path in local_module_paths(args).items():
        commands.append(v2396.adb_push(args, rel(path), remote_stage_path(name)))
    commands.append(v2396.adb_base(args) + ["install", "-r", rel(args.stimulus_apk)])
    commands.append(install_module_command(args))
    return commands


def cleanup_commands(args: argparse.Namespace) -> list[list[str]]:
    return [
        v2396.adb_base(args) + ["wait-for-device"],
        v2396.adb_base(args) + ["uninstall", route.APK_PACKAGE],
        v2396.adb_root_shell(
            args,
            f"rm -rf {shlex.quote(REMOTE_MODULE_DIR)} {shlex.quote(REMOTE_MODULE_UPDATE_DIR)} "
            f"{shlex.quote(v2429.REMOTE_DIR)}",
        ),
        v2396.adb_root_shell(args, f"ls -ld {shlex.quote(REMOTE_MODULE_DIR)} {shlex.quote(v2429.REMOTE_DIR)} 2>&1 || true"),
    ]


def collect_prepare_command(args: argparse.Namespace) -> list[str]:
    command = (
        f"if [ -d {shlex.quote(v2429.REMOTE_ARTIFACT_DIR)} ]; then "
        f"chmod -R a+rX {shlex.quote(v2429.REMOTE_DIR)}; "
        "fi; "
        f"ls -lR {shlex.quote(v2429.REMOTE_DIR)} 2>&1 || true"
    )
    return v2396.adb_root_shell(args, command)


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
    }
    findings = [{"name": name, "needle": needle} for name, needle in forbidden.items() if needle in flat]
    required = [
        REMOTE_MODULE_DIR,
        "service.sh",
        v2429.HELPER_NAME,
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
        },
        "commands": commands,
        "stage_adb_waits": stage_wait_plan(args),
        "hard_boundary": [
            "temporary Android-side measurement module only",
            "no native-init Magisk dependency",
            "no native calibration ioctl issue",
            "no native speaker write, tinymix set, tinyplay, Wi-Fi, DHCP, route, or ping",
            "cleanup module/artifacts before V2321 rollback",
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
        blockers.append("V2430 command safety failed")
    payload["future_live_blockers"] = blockers
    payload["ok"] = bool(module_plan.get("ok") and safety.get("ok"))
    return payload


def run_live(args: argparse.Namespace) -> dict[str, Any]:
    ensure_live_approval(args)
    args.materialize_module_template = True
    route_args = v2396.android_args(args)
    plan = dry_run(args)
    if not plan.get("future_live_ready"):
        raise RuntimeError(f"V2430 live inputs are not ready: {plan.get('future_live_blockers')}")
    if not plan.get("command_safety", {}).get("ok"):
        raise RuntimeError(f"V2430 command safety failed: {plan.get('command_safety')}")

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
        logcat_capture["record"]["name"] = "acdb-m1-magisk-module-logcat"
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
    mode.add_argument("--dry-run", action="store_true", help="emit the V2430 live plan; no device action")
    mode.add_argument("--run-live", action="store_true", help="run the exact-gated V2430 M1 Magisk-module capture")
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
