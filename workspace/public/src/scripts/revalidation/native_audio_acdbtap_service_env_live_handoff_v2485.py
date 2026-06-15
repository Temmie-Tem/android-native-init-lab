#!/usr/bin/env python3
"""V2485 recoverable Android handoff for init-managed ACDB tap preload.

V2479 proved that `/data/local/tmp` is outside the vendor linker namespace for
`android.hardware.audio.service`, and V2483 proved that a parallel manual HAL
process can map the tap without handling Android audio. V2485 uses the V2484
temporary Magisk/systemless capsule to overlay the vendor HAL init rc with
`setenv LD_PRELOAD`, then proceeds only if the init-managed HAL PID maps the tap
and the private AudioTrack APK is installed.
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
import native_audio_acdbtap_live_handoff_v2477 as v2477
import native_audio_acdbtap_live_planner_v2476 as v2476
import native_audio_acdbtap_service_env_planner_v2484 as v2484
import native_audio_android_route_delta_handoff_v2365 as route


RUN_ID = "V2485"
BUILD_TAG = "v2485-audio-acdbtap-service-env-live"
ROOT = v2484.ROOT
DEFAULT_OUT_BASE = ROOT / "workspace/private/runs/audio"
DEFAULT_CAPTURE_OBSERVE_SEC = v2477.DEFAULT_CAPTURE_OBSERVE_SEC


def rel(path: Path | str) -> str:
    return v2476.rel(path)


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def default_live_out_dir() -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return DEFAULT_OUT_BASE / f"{RUN_ID.lower()}-acdbtap-service-env-live-{stamp}"


def decision_slug() -> str:
    return "v2485-acdbtap-service-env-live"


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def route_args(args: argparse.Namespace) -> argparse.Namespace:
    return v2396.android_args(args)


def adb_su(args: argparse.Namespace, script: str) -> list[str]:
    return v2476.adb_su(args, script)


def module_stage_commands(args: argparse.Namespace) -> list[tuple[str, list[str], bool]]:
    plan = v2484.command_plan(args.module_out_dir)
    steps: list[tuple[str, list[str], bool]] = [("v2485-module-stage-setup", plan["stage_setup"], True)]
    for index, command in enumerate(plan["push_files"]):
        steps.append((f"v2485-module-push-{index}", command, True))
    steps.extend([
        ("v2485-module-install-direct", plan["install_module_direct"], True),
        ("v2485-module-reboot-for-magisk-mount", plan["android_reboot_for_magisk_mount"], False),
    ])
    return steps


def module_verify_command(args: argparse.Namespace) -> list[str]:
    return v2484.command_plan(args.module_out_dir)["verify_service_env_after_reboot"]


def module_cleanup_command(args: argparse.Namespace) -> list[str]:
    return v2484.command_plan(args.module_out_dir)["cleanup_exact_module"]


def run_android_settle_with_prefix(args: argparse.Namespace, out_dir: Path, steps: list[dict[str, Any]], prefix: str) -> None:
    for index, command in enumerate(v2396.android_post_handoff_settle_commands(args)):
        if index != 2:
            steps.append(route.run_step(f"{prefix}-{index}", command, out_dir, timeout_sec=args.adb_command_timeout))
            continue
        attempts = max(1, int(getattr(args, "android_root_recheck_attempts", v2396.DEFAULT_ANDROID_ROOT_RECHECK_ATTEMPTS)))
        sleep_sec = max(0.0, float(getattr(args, "android_root_recheck_sleep_sec", v2396.DEFAULT_ANDROID_ROOT_RECHECK_SLEEP_SEC)))
        last_record: dict[str, Any] | None = None
        for attempt in range(1, attempts + 1):
            name = f"{prefix}-2" if attempt == 1 else f"{prefix}-2-retry-{attempt}"
            record = route.run_step(name, command, out_dir, timeout_sec=args.adb_command_timeout, check=False)
            steps.append(record)
            summary = v2396.android_root_recheck_summary(record)
            summary["attempt"] = attempt
            summary["max_attempts"] = attempts
            record["root_recheck"] = summary
            last_record = record
            if summary["root_ready"]:
                record["settle_decision"] = "android-root-ready"
                return
            record["settle_decision"] = summary["classification"]
            if attempt != attempts:
                time.sleep(sleep_sec)
        if last_record is not None:
            v2396.validate_android_root_recheck(last_record)
        raise RuntimeError(f"{prefix} root recheck did not run")


def step_stdout(record: dict[str, Any]) -> str:
    return v2477.step_stdout(record)


def step_stderr(record: dict[str, Any]) -> str:
    path = record.get("stderr")
    if not path:
        return ""
    try:
        return Path(path).read_text(errors="replace")
    except OSError:
        return ""


def verified_preload_candidates(record: dict[str, Any]) -> list[str]:
    stdout = step_stdout(record)
    candidates: list[str] = []
    for line in stdout.splitlines():
        tokens = line.split()
        if v2476.TAP_SHA256 not in tokens:
            continue
        for candidate in v2484.PRELOAD_CANDIDATES:
            if candidate in tokens and candidate not in candidates:
                candidates.append(candidate)
    return candidates


def selected_preload_candidate(record: dict[str, Any]) -> str | None:
    candidates = verified_preload_candidates(record)
    return candidates[0] if candidates else None


def service_preload_confirmed(record: dict[str, Any]) -> bool:
    stdout = step_stdout(record)
    return "A90_ACDBTAP_SERVICE_PRELOAD_ALL_PIDS" in stdout and "A90_ACDBTAP_SERVICE_PRELOAD_MISSING" not in stdout


def stimulus_apk_installed(record: dict[str, Any]) -> bool:
    return f"package:{route.APK_PACKAGE}" in step_stdout(record)


def playback_start_failed(record: dict[str, Any]) -> bool:
    output = f"{step_stdout(record)}\n{step_stderr(record)}"
    needles = [
        "Error type",
        "Activity class",
        "does not exist",
        "Exception occurred while executing",
    ]
    return any(needle in output for needle in needles)


def capture_setup_command(args: argparse.Namespace) -> list[str]:
    script = f"""
set -eu
rm -rf {shlex.quote(v2476.REMOTE_STAGE_DIR)} {shlex.quote(v2476.REMOTE_CAPTURE_DIR)}
mkdir -p {shlex.quote(v2476.REMOTE_STAGE_DIR)} {shlex.quote(v2476.REMOTE_CAPTURE_DIR)}
chmod 755 {shlex.quote(v2476.REMOTE_STAGE_DIR)}
chmod 777 {shlex.quote(v2476.REMOTE_CAPTURE_DIR)}
ls -lZ {shlex.quote(v2476.AUDIO_BINARY)} {' '.join(shlex.quote(path) for path in v2484.PRELOAD_CANDIDATES)} {shlex.quote(v2476.REMOTE_CAPTURE_DIR)} 2>&1 || true
echo A90_ACDBTAP_V2485_CAPTURE_SETUP_OK
""".strip()
    return adb_su(args, script)


def preflight_vendor_hal_command(args: argparse.Namespace, preload_path: str) -> list[str]:
    script = f"""
set -eu
pidof {shlex.quote(v2476.AUDIO_PROCESS)} 2>/dev/null || true
getprop init.svc.{shlex.quote(v2476.AUDIO_SERVICE)} 2>/dev/null || true
ls -lZ {shlex.quote(v2476.AUDIO_BINARY)} {shlex.quote(preload_path)} {shlex.quote(v2476.REMOTE_CAPTURE_DIR)}
sha256sum {shlex.quote(preload_path)} 2>/dev/null || toybox sha256sum {shlex.quote(preload_path)}
echo A90_ACDBTAP_V2485_PREFLIGHT_OK preload={shlex.quote(preload_path)}
""".strip()
    return adb_su(args, script)


def service_restart_with_preload_command(args: argparse.Namespace, preload_path: str) -> list[str]:
    script = f"""
set -eu
PRELOAD_PATH={shlex.quote(preload_path)}
setprop ctl.stop {shlex.quote(v2476.AUDIO_SERVICE)}
i=0
while pidof {shlex.quote(v2476.AUDIO_PROCESS)} >/dev/null 2>&1; do
  if [ "$i" -ge 40 ]; then
    echo A90_ACDBTAP_SERVICE_STALE_PIDS "$(pidof {shlex.quote(v2476.AUDIO_PROCESS)} 2>/dev/null || true)"
    exit 63
  fi
  i=$((i + 1))
  sleep 0.25
done
setprop ctl.start {shlex.quote(v2476.AUDIO_SERVICE)}
i=0
PIDS=""
while [ -z "$PIDS" ]; do
  PIDS="$(pidof {shlex.quote(v2476.AUDIO_PROCESS)} 2>/dev/null || true)"
  if [ "$i" -ge 60 ]; then
    echo A90_ACDBTAP_SERVICE_NO_PID
    exit 64
  fi
  i=$((i + 1))
  sleep 0.25
done
echo A90_ACDBTAP_SERVICE_HAL_PIDS "$PIDS"
missing=0
for pid in $PIDS; do
  if grep -q "$PRELOAD_PATH" /proc/$pid/maps 2>/dev/null || grep -q libacdbtap /proc/$pid/maps 2>/dev/null; then
    echo A90_ACDBTAP_SERVICE_PRELOAD_CONFIRMED pid=$pid path="$PRELOAD_PATH"
  else
    echo A90_ACDBTAP_SERVICE_PRELOAD_MISSING pid=$pid path="$PRELOAD_PATH"
    missing=1
  fi
done
if [ "$missing" -ne 0 ]; then
  exit 65
fi
echo A90_ACDBTAP_SERVICE_PRELOAD_ALL_PIDS
""".strip()
    return adb_su(args, script)


def capture_cleanup_command(args: argparse.Namespace) -> list[str]:
    script = f"""
set -eu
setprop ctl.start {shlex.quote(v2476.AUDIO_SERVICE)} || true
sleep 2
rm -rf {shlex.quote(v2476.REMOTE_STAGE_DIR)} {shlex.quote(v2476.REMOTE_CAPTURE_DIR)}
getprop init.svc.{shlex.quote(v2476.AUDIO_SERVICE)} 2>/dev/null || true
echo A90_ACDBTAP_CLEANUP_OK
""".strip()
    return adb_su(args, script)


def install_stimulus_apk_command(args: argparse.Namespace) -> list[str]:
    return route.adb_install_command(route_args(args), rel(args.stimulus_apk))


def verify_stimulus_apk_command(args: argparse.Namespace) -> list[str]:
    return route.android_shell(route_args(args), f"cmd package path {route.APK_PACKAGE}")


def uninstall_stimulus_apk_command(args: argparse.Namespace) -> list[str]:
    return route.adb_uninstall_command(route_args(args))


def collect_prepare_command(args: argparse.Namespace) -> list[str]:
    return v2477.collect_prepare_command(args)


def pull_capture_command(args: argparse.Namespace, destination: str) -> list[str]:
    return v2477.pull_capture_command(args, destination)


def pull_stage_command(args: argparse.Namespace, destination: str) -> list[str]:
    return v2477.pull_stage_command(args, destination)


def command_safety(payload: dict[str, Any]) -> dict[str, Any]:
    command_flat = json.dumps(payload.get("commands", payload), sort_keys=True)
    required_flat = json.dumps(payload, sort_keys=True)
    forbidden = {
        "native_cal_set_symbol": "AUDIO_SET_CALIBRATION",
        "native_cal_allocate_symbol": "AUDIO_ALLOCATE_CALIBRATION",
        "native_tinyplay": "tinyplay",
        "native_tinymix_set": "tinymix set",
        "fastboot": "fastboot",
        "raw_dd": " dd ",
        "silent_permissive": "setenforce 0",
        "magisk_install_module": "magisk --install-module",
        "service_script": "service.sh",
        "post_fs_data": "post-fs-data.sh",
        "sepolicy_rule": "sepolicy.rule",
        "own_process_loader_guess": "acdb_loader_init_v4",
        "broad_modules_delete": "rm -rf /data/adb/modules",
    }
    findings = [{"name": name, "needle": needle} for name, needle in forbidden.items() if needle in command_flat]
    required = [
        v2484.MODULE_ID,
        v2484.MODULE_LIB_REL,
        "/vendor/lib/libacdbtap.so",
        "/system/vendor/lib/libacdbtap.so",
        "LD_PRELOAD",
        "A90_ACDBTAP_SERVICE_PRELOAD_ALL_PIDS",
        v2484.RC_MARKER,
        "setenv LD_PRELOAD",
        "cmd package path",
        "AudioTrack",
        "rollback_v2321",
        "cleanup_exact_module",
        "A90_ACDBTAP_CLEANUP_OK",
        v2476.REMOTE_CAPTURE_DIR,
    ]
    missing = [needle for needle in required if needle not in required_flat]
    return {"ok": not findings and not missing, "findings": findings, "missing_required_needles": missing, "forbidden": sorted(forbidden), "required": required}


def dry_run_payload(args: argparse.Namespace) -> dict[str, Any]:
    module = v2484.materialize_module(args.module_out_dir) if args.materialize_module else {"ok": False, "reason": "not materialized"}
    module_plan = v2484.command_plan(args.module_out_dir)
    module_safety = v2484.command_safety({"command_plan": module_plan, "module": module})
    android_boot = route.select_android_boot_candidate()
    stimulus_apk = route.stimulus_apk_state(args.stimulus_apk)
    rollback = route.file_state(route.ROLLBACK_IMAGE, expected_sha256=route.ROLLBACK_SHA256)
    r_args = route_args(args)
    commands = {
        "flash_android": route.flash_android_command(r_args, "<private-run-dir>/android_boot_0600.img"),
        "android_post_handoff_settle": v2396.android_post_handoff_settle_commands(args),
        "module_stage": [command for _, command, _ in module_stage_commands(args)],
        "post_module_android_settle": v2396.android_post_handoff_settle_commands(args),
        "module_verify_service_env": module_verify_command(args),
        "capture_setup": capture_setup_command(args),
        "preflight_vendor_hal": preflight_vendor_hal_command(args, "<verified-service-env-candidate>"),
        "service_restart_with_preload": service_restart_with_preload_command(args, "<verified-service-env-candidate>"),
        "install_stimulus_apk": install_stimulus_apk_command(args),
        "verify_stimulus_apk": verify_stimulus_apk_command(args),
        "verify_before_playback": v2477.verify_command(args),
        "playback_start_background": route.playback_start_command(r_args),
        "playback_result": route.stimulus_result_commands(r_args),
        "collect_prepare": collect_prepare_command(args),
        "pull_capture": pull_capture_command(args, "<private-run-dir>/acdbtap-device-artifacts"),
        "pull_stage": pull_stage_command(args, "<private-run-dir>/acdbtap-stage-artifacts"),
        "capture_cleanup": capture_cleanup_command(args),
        "uninstall_stimulus_apk": uninstall_stimulus_apk_command(args),
        "cleanup_exact_module": module_cleanup_command(args),
        "android_reboot_recovery_for_rollback": route.android_reboot_recovery_command(r_args),
        "rollback_v2321": route.rollback_command(r_args),
    }
    payload: dict[str, Any] = {
        "run_id": RUN_ID,
        "build_tag": BUILD_TAG,
        "decision": f"{decision_slug()}-dry-run",
        "generated_at": now_iso(),
        "host_only": True,
        "device_action": "none",
        "approval_policy": "recoverable-envelope preauthorized by GOAL.md; --run-live flag remains required",
        "module": module,
        "module_safety": module_safety,
        "android_boot": android_boot,
        "rollback": rollback,
        "stimulus_apk": stimulus_apk,
        "commands": commands,
        "partial_success_policy": "captured-acdbtap-full-outbuf-set-no-4916 remains operator-valuable partial success and does not count as fails-twice dead run",
        "hard_stops": [
            "abort before playback if no service env preload candidate has the V2475 SHA",
            "abort before playback if the init-managed audio HAL service does not map libacdbtap in every PID",
            "abort before playback if the AudioTrack APK package path is absent",
            "abort after am start if Android reports Error type / Activity class missing",
            "capture linker/SELinux denial evidence, then stop; do not silently relax policy",
            "do not issue native calibration ioctl",
            "do not guess acdb_loader_init_v4 fallback",
            "cleanup exact Magisk module path before V2321 rollback",
        ],
    }
    safety = command_safety(payload)
    blockers: list[str] = []
    if not module.get("ok"):
        blockers.append(f"V2484 module materialization failed: {module.get('reason')}")
    if not module_safety.get("ok"):
        blockers.append(f"V2484 module command safety failed: {module_safety}")
    if not android_boot.get("ok"):
        blockers.append("Android boot candidate missing or SHA/magic invalid")
    if not rollback.get("ok"):
        blockers.append("V2321 rollback image missing or SHA invalid")
    if not stimulus_apk.get("ok"):
        blockers.append(stimulus_apk.get("reason", "stimulus APK unavailable"))
    if not safety.get("ok"):
        blockers.append("V2485 command safety failed")
    payload["command_safety"] = safety
    payload["future_live_ready"] = not blockers
    payload["future_live_blockers"] = blockers
    payload["ok"] = bool(module.get("ok") and module_safety.get("ok") and safety.get("ok"))
    return payload


def run_live(args: argparse.Namespace) -> dict[str, Any]:
    plan = dry_run_payload(args)
    if not plan.get("future_live_ready"):
        raise RuntimeError(f"V2485 live inputs are not ready: {plan.get('future_live_blockers')}")
    if not plan.get("command_safety", {}).get("ok"):
        raise RuntimeError(f"V2485 command safety failed: {plan.get('command_safety')}")

    out_dir = args.out_dir or default_live_out_dir()
    out_dir.mkdir(parents=True, exist_ok=False)
    os.chmod(out_dir, 0o700)
    steps: list[dict[str, Any]] = []
    result: dict[str, Any] = {
        "run_id": RUN_ID,
        "build_tag": BUILD_TAG,
        "decision": f"{decision_slug()}-live-started",
        "out_dir": rel(out_dir),
        "preauthorized_by_goal": True,
        "plan": plan,
        "steps": steps,
        "rolled_back": False,
        "ok": False,
    }
    write_json(out_dir / "result.json", result)

    r_args = route_args(args)
    sealed = route.copy_sealed_android_boot(plan["android_boot"]["selected"], out_dir)
    result["sealed_android_boot"] = sealed
    write_json(out_dir / "result.json", result)

    rollback_needed = False
    module_stage_started = False
    capture_cleanup_done = False
    module_cleanup_done = False
    logcat_capture: dict[str, Any] | None = None
    try:
        rollback_needed = True
        steps.append(route.run_step("flash-android", route.flash_android_command(r_args, str(out_dir / "android_boot_0600.img")), out_dir, timeout_sec=args.flash_timeout))
        run_android_settle_with_prefix(args, out_dir, steps, "android-post-handoff-settle")

        module_stage_started = True
        for name, command, check in module_stage_commands(args):
            steps.append(route.run_step(name, command, out_dir, timeout_sec=args.adb_command_timeout, check=check))

        run_android_settle_with_prefix(args, out_dir, steps, "android-post-module-settle")
        verify_record = route.run_step("v2485-module-verify-service-env", module_verify_command(args), out_dir, timeout_sec=args.adb_command_timeout, check=False)
        steps.append(verify_record)
        preload_path = selected_preload_candidate(verify_record)
        result["verified_preload_candidates"] = verified_preload_candidates(verify_record)
        if not preload_path:
            result["decision"] = f"{decision_slug()}-service-env-candidate-not-verified-before-rollback"
            raise RuntimeError("no vendor-visible libacdbtap candidate matched the V2475 SHA; aborting before playback")
        result["selected_preload_candidate"] = preload_path

        steps.append(route.run_step("acdbtap-v2485-capture-setup", capture_setup_command(args), out_dir, timeout_sec=args.adb_command_timeout))
        steps.append(route.run_step("acdbtap-v2485-preflight-vendor-hal", preflight_vendor_hal_command(args, preload_path), out_dir, timeout_sec=args.adb_command_timeout, check=False))
        service_restart_record = route.run_step("acdbtap-v2485-service-restart-with-preload", service_restart_with_preload_command(args, preload_path), out_dir, timeout_sec=args.adb_command_timeout, check=False)
        steps.append(service_restart_record)

        steps.append(route.run_step("acdbtap-verify-before-playback", v2477.verify_command(args), out_dir, timeout_sec=args.adb_command_timeout, check=False))
        if not service_preload_confirmed(service_restart_record):
            result["decision"] = f"{decision_slug()}-service-preload-not-confirmed-before-rollback"
            raise RuntimeError("libacdbtap preload was not confirmed in every init-managed audio HAL PID; aborting before playback")

        steps.append(route.run_step("install-stimulus-apk", install_stimulus_apk_command(args), out_dir, timeout_sec=args.adb_command_timeout))
        verify_apk_record = route.run_step("verify-stimulus-apk", verify_stimulus_apk_command(args), out_dir, timeout_sec=args.adb_command_timeout, check=False)
        steps.append(verify_apk_record)
        if not stimulus_apk_installed(verify_apk_record):
            result["decision"] = f"{decision_slug()}-stimulus-apk-not-installed-before-rollback"
            raise RuntimeError("AudioTrack stimulus APK package path is absent; aborting before playback")

        steps.append(route.run_step("logcat-clear-before-stimulus", route.logcat_clear_command(r_args), out_dir, timeout_sec=args.adb_command_timeout, check=False))
        logcat_capture = route.start_logcat_capture(r_args, out_dir)
        logcat_capture["record"]["name"] = "acdbtap-v2485-live-logcat"
        steps.append(logcat_capture["record"])

        playback_start_record = route.run_step("playback-start-background", route.playback_start_command(r_args), out_dir, timeout_sec=args.adb_command_timeout)
        steps.append(playback_start_record)
        if playback_start_failed(playback_start_record):
            result["decision"] = f"{decision_slug()}-stimulus-start-failed-before-rollback"
            raise RuntimeError("AudioTrack stimulus start reported an Android Activity/start error; aborting capture wait")
        wait_sec = max(float(args.capture_observe_sec), (args.duration_ms / 1000.0) + args.post_delay_sec + 1.0)
        time.sleep(wait_sec)
        for index, command in enumerate(route.stimulus_result_commands(r_args)):
            steps.append(route.run_step(f"playback-result-{index}", command, out_dir, timeout_sec=args.adb_command_timeout, check=False))

        steps.append(route.run_step("acdbtap-verify-after-playback", v2477.verify_command(args), out_dir, timeout_sec=args.adb_command_timeout, check=False))
        steps.append(route.run_step("acdbtap-collect-prepare", collect_prepare_command(args), out_dir, timeout_sec=args.adb_command_timeout, check=False))
        steps.append(route.run_step("acdbtap-pull-capture", pull_capture_command(args, str(out_dir / "acdbtap-device-artifacts")), out_dir, timeout_sec=args.adb_command_timeout, check=False))
        steps.append(route.run_step("acdbtap-pull-stage", pull_stage_command(args, str(out_dir / "acdbtap-stage-artifacts")), out_dir, timeout_sec=args.adb_command_timeout, check=False))

        summary = v2477.summarize_acdbtap_artifacts(out_dir)
        result["acdbtap_summary"] = summary
        result["decision"] = f"{decision_slug()}-{summary['classification']}-before-rollback"
        result["ok"] = bool(summary.get("operator_valuable"))
        result["partial_success"] = bool(summary.get("partial_success"))
        result["target_4916_success"] = bool(summary.get("full_success"))
        result["counts_toward_fails_twice"] = bool(summary.get("counts_toward_fails_twice", True))

        steps.append(route.run_step("acdbtap-v2485-capture-cleanup", capture_cleanup_command(args), out_dir, timeout_sec=args.adb_command_timeout, check=False))
        capture_cleanup_done = True
        steps.append(route.run_step("uninstall-stimulus-apk", uninstall_stimulus_apk_command(args), out_dir, timeout_sec=args.adb_command_timeout, check=False))
        steps.append(route.run_step("v2485-module-cleanup-exact", module_cleanup_command(args), out_dir, timeout_sec=args.adb_command_timeout, check=False))
        module_cleanup_done = True
    except Exception as error:
        result.setdefault("decision", f"{decision_slug()}-failed-before-rollback")
        result["error"] = str(error)
        if result.get("decision") == f"{decision_slug()}-live-started":
            result["decision"] = f"{decision_slug()}-failed-before-rollback"
    finally:
        route.stop_logcat_capture(logcat_capture)
        if rollback_needed:
            try:
                if not capture_cleanup_done:
                    steps.append(route.run_step("acdbtap-v2485-capture-cleanup-finally", capture_cleanup_command(args), out_dir, timeout_sec=args.adb_command_timeout, check=False))
                    steps.append(route.run_step("uninstall-stimulus-apk-finally", uninstall_stimulus_apk_command(args), out_dir, timeout_sec=args.adb_command_timeout, check=False))
                if module_stage_started and not module_cleanup_done:
                    steps.append(route.run_step("v2485-module-cleanup-exact-finally", module_cleanup_command(args), out_dir, timeout_sec=args.adb_command_timeout, check=False))
                v2396.rollback_to_v2321_with_android_recovery(args, r_args, out_dir, steps, result)
                result["decision"] = f"{result['decision']}-rollback-pass"
            except Exception as rollback_error:
                result["rollback_fallback_error"] = str(rollback_error)
                write_json(out_dir / "result.json", result)
                raise
        write_json(out_dir / "result.json", result)
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-live", action="store_true")
    parser.add_argument("--adb", default="adb")
    parser.add_argument("--serial")
    parser.add_argument("--out-dir", type=Path)
    parser.add_argument("--module-out-dir", type=Path, default=v2484.DEFAULT_MODULE_OUT_DIR)
    parser.add_argument("--materialize-module", action="store_true", default=True)
    parser.add_argument("--stage-dir", type=Path, default=v2476.DEFAULT_STAGE_DIR)
    parser.add_argument("--stimulus-apk", type=Path, default=v2396.DEFAULT_STIMULUS_APK)
    parser.add_argument("--duration-ms", type=int, default=route.DEFAULT_DURATION_MS)
    parser.add_argument("--sample-rate", type=int, default=route.DEFAULT_SAMPLE_RATE)
    parser.add_argument("--amplitude", type=float, default=route.DEFAULT_AMPLITUDE)
    parser.add_argument("--active-delay-sec", type=float, default=route.DEFAULT_ACTIVE_DELAY_SEC)
    parser.add_argument("--post-delay-sec", type=float, default=route.DEFAULT_POST_DELAY_SEC)
    parser.add_argument("--capture-observe-sec", type=float, default=DEFAULT_CAPTURE_OBSERVE_SEC)
    parser.add_argument("--android-timeout", type=float, default=240.0)
    parser.add_argument("--adb-command-timeout", type=float, default=45.0)
    parser.add_argument("--flash-timeout", type=float, default=240.0)
    parser.add_argument("--from-native", action="store_true")
    parser.add_argument("--android-root-recheck-attempts", type=int, default=v2396.DEFAULT_ANDROID_ROOT_RECHECK_ATTEMPTS)
    parser.add_argument("--android-root-recheck-sleep-sec", type=float, default=v2396.DEFAULT_ANDROID_ROOT_RECHECK_SLEEP_SEC)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = run_live(args) if args.run_live else dry_run_payload(args)
    print(json.dumps({
        "decision": result.get("decision"),
        "ok": result.get("ok"),
        "future_live_ready": result.get("future_live_ready"),
        "future_live_blockers": result.get("future_live_blockers"),
        "out_dir": result.get("out_dir"),
        "partial_success": result.get("partial_success"),
        "counts_toward_fails_twice": result.get("counts_toward_fails_twice"),
    }, indent=2, sort_keys=True))
    return 0 if result.get("ok") or (not args.run_live and result.get("command_safety", {}).get("ok")) else 1


if __name__ == "__main__":
    raise SystemExit(main())
