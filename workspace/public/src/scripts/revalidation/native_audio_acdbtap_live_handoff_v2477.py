#!/usr/bin/env python3
"""V2477 recoverable Android handoff runner for the V2475 ACDB tap.

Default mode is host-only dry-run.  Live mode is intentionally gated by the
explicit --run-live flag, but not by a separate human approval phrase: GOAL.md
currently pre-authorizes recoverable-envelope Android/Magisk measurement actions.
"""

from __future__ import annotations

import argparse
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import native_audio_acdb_android_measurement_planner_v2396 as v2396
import native_audio_acdbtap_live_planner_v2476 as v2476
import native_audio_android_route_delta_handoff_v2365 as route


RUN_ID = "V2477"
BUILD_TAG = "v2477-audio-acdbtap-live-handoff"
ROOT = v2476.ROOT
DEFAULT_OUT_BASE = ROOT / "workspace/private/runs/audio"
DEFAULT_CAPTURE_OBSERVE_SEC = 8.0


def rel(path: Path | str) -> str:
    return v2476.rel(path)


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def default_live_out_dir() -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return DEFAULT_OUT_BASE / f"{RUN_ID.lower()}-acdbtap-live-handoff-{stamp}"


def decision_slug() -> str:
    return "v2477-acdbtap-live-handoff"


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def planner_args(args: argparse.Namespace) -> argparse.Namespace:
    return argparse.Namespace(
        adb=args.adb,
        serial=args.serial,
        stage_private_inputs=False,
        stage_dir=args.stage_dir,
    )


def route_args(args: argparse.Namespace) -> argparse.Namespace:
    return v2396.android_args(args)


def stage_commands(args: argparse.Namespace) -> list[tuple[str, list[str], bool]]:
    plan = v2476.live_command_plan(planner_args(args))["commands"]
    return [
        ("acdbtap-setup-dirs", plan["setup_dirs"], True),
        ("acdbtap-push-lib", plan["push_libacdbtap"], True),
        ("acdbtap-install-lib", plan["install_libacdbtap"], True),
        ("acdbtap-preflight-audio-hal", plan["preflight_audio_hal"], True),
        ("acdbtap-logcat-clear", plan["logcat_clear"], False),
        ("acdbtap-manual-start-preload", plan["manual_stop_and_reexec_hal_with_preload"], False),
    ]


def verify_command(args: argparse.Namespace) -> list[str]:
    return v2476.live_command_plan(planner_args(args))["commands"]["verify_capture_and_avc"]


def cleanup_command(args: argparse.Namespace) -> list[str]:
    return v2476.live_command_plan(planner_args(args))["commands"]["cleanup_restore_init_service"]


def collect_prepare_command(args: argparse.Namespace) -> list[str]:
    script = f"""
set -eu
if [ -d {v2476.REMOTE_CAPTURE_DIR} ]; then chmod -R a+rX {v2476.REMOTE_CAPTURE_DIR}; fi
if [ -d {v2476.REMOTE_STAGE_DIR} ]; then chmod -R a+rX {v2476.REMOTE_STAGE_DIR}; fi
ls -lR {v2476.REMOTE_CAPTURE_DIR} {v2476.REMOTE_STAGE_DIR} 2>&1 || true
echo A90_ACDBTAP_COLLECT_PREPARE_DONE
""".strip()
    return v2476.adb_su(args, script)


def pull_capture_command(args: argparse.Namespace, destination: str) -> list[str]:
    return v2476.adb_base(args) + ["pull", v2476.REMOTE_CAPTURE_DIR, destination]


def pull_stage_command(args: argparse.Namespace, destination: str) -> list[str]:
    return v2476.adb_base(args) + ["pull", v2476.REMOTE_STAGE_DIR, destination]


def step_stdout(record: dict[str, Any]) -> str:
    path = record.get("stdout")
    if not isinstance(path, str):
        return ""
    full = ROOT / path if not Path(path).is_absolute() else Path(path)
    try:
        return full.read_text(errors="replace")
    except OSError:
        return ""


def preload_confirmed(record: dict[str, Any]) -> bool:
    return "A90_ACDBTAP_PRELOAD_CONFIRMED" in step_stdout(record)


def parse_hex_or_int(value: Any) -> int | None:
    if isinstance(value, int):
        return value
    if not isinstance(value, str):
        return None
    try:
        return int(value, 0)
    except ValueError:
        return None


def summarize_acdbtap_artifacts(out_dir: Path) -> dict[str, Any]:
    event_files = sorted(out_dir.rglob("acdbtap-events.jsonl"))
    rows: list[dict[str, Any]] = []
    malformed = 0
    for path in event_files:
        for line in path.read_text(errors="replace").splitlines():
            if not line.strip():
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                malformed += 1
                continue
            public_item = {
                "seq": item.get("seq"),
                "cmd": item.get("cmd"),
                "in_len": item.get("in_len"),
                "out_len": item.get("out_len"),
                "ret": item.get("ret"),
                "sha256": item.get("sha256"),
                "raw_written": item.get("raw_written"),
                "is_target_4916": item.get("is_target_4916"),
                "is_size_query_4": item.get("is_size_query_4"),
            }
            rows.append(public_item)
    target = [row for row in rows if row.get("is_target_4916") is True or parse_hex_or_int(row.get("out_len")) == v2476.TARGET_OUT_LEN]
    size_query = [row for row in rows if row.get("is_size_query_4") is True or parse_hex_or_int(row.get("out_len")) == 4]
    raw_files = sorted(path for path in out_dir.rglob("acdbtap-*.bin") if path.is_file())
    raw_complete = bool(rows) and malformed == 0 and len(raw_files) >= len(rows)
    if not rows:
        classification = "no-acdbtap-events"
    elif malformed:
        classification = "acdbtap-events-malformed"
    elif not raw_complete:
        classification = "acdbtap-metadata-with-missing-raw"
    elif target:
        classification = "captured-acdbtap-full-outbuf-set-with-4916"
    else:
        classification = "captured-acdbtap-full-outbuf-set-no-4916"
    return {
        "event_file_count": len(event_files),
        "event_count": len(rows),
        "malformed_event_lines": malformed,
        "target_4916_count": len(target),
        "size_query_4_count": len(size_query),
        "raw_file_count": len(raw_files),
        "raw_complete": raw_complete,
        "ordered_events": rows,
        "target_events": target[:16],
        "size_query_events": size_query[:16],
        "all_events_preview": rows[:16],
        "classification": classification,
    }


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
        "own_process_loader_guess": "acdb_loader_init_v4",
    }
    findings = [{"name": name, "needle": needle} for name, needle in forbidden.items() if needle in command_flat]
    required = [
        "LD_PRELOAD",
        "A90_ACDBTAP_PRELOAD_CONFIRMED",
        "AudioTrack",
        "rollback_v2321",
        "A90_ACDBTAP_CLEANUP_OK",
        v2476.REMOTE_CAPTURE_DIR,
    ]
    missing = [needle for needle in required if needle not in required_flat]
    return {
        "ok": not findings and not missing,
        "findings": findings,
        "missing_required_needles": missing,
        "forbidden": sorted(forbidden),
        "required": required,
    }


def dry_run_payload(args: argparse.Namespace) -> dict[str, Any]:
    base_plan = v2476.build_payload(planner_args(args))
    r_args = route_args(args)
    android_boot = route.select_android_boot_candidate()
    stimulus_apk = route.stimulus_apk_state(args.stimulus_apk)
    rollback = route.file_state(route.ROLLBACK_IMAGE, expected_sha256=route.ROLLBACK_SHA256)
    commands = {
        "flash_android": route.flash_android_command(r_args, "<private-run-dir>/android_boot_0600.img"),
        "android_post_handoff_settle": v2396.android_post_handoff_settle_commands(args),
        "stage_acdbtap": [command for _, command, _ in stage_commands(args)],
        "verify_before_playback": verify_command(args),
        "playback_start_background": route.playback_start_command(r_args),
        "playback_result": route.stimulus_result_commands(r_args),
        "collect_prepare": collect_prepare_command(args),
        "pull_capture": pull_capture_command(args, "<private-run-dir>/acdbtap-device-artifacts"),
        "pull_stage": pull_stage_command(args, "<private-run-dir>/acdbtap-stage-artifacts"),
        "cleanup": cleanup_command(args),
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
        "v2476_plan": base_plan,
        "android_boot": android_boot,
        "rollback": rollback,
        "stimulus_apk": stimulus_apk,
        "commands": commands,
        "hard_stops": [
            "abort before playback if libacdbtap is not confirmed in audio HAL maps",
            "capture SELinux/linker denial evidence, then stop; do not silently relax policy",
            "do not issue native calibration ioctl",
            "do not guess acdb_loader_init_v4 fallback",
            "cleanup temporary Android state before V2321 rollback",
        ],
    }
    safety = command_safety(payload)
    payload["command_safety"] = safety
    blockers: list[str] = []
    if not base_plan.get("future_live_ready"):
        blockers.append(f"V2476 planner not live-ready: {base_plan.get('future_live_blockers')}")
    if not android_boot.get("ok"):
        blockers.append("Android boot candidate missing or SHA/magic invalid")
    if not rollback.get("ok"):
        blockers.append("V2321 rollback image missing or SHA invalid")
    if not stimulus_apk.get("ok"):
        blockers.append(stimulus_apk.get("reason", "stimulus APK unavailable"))
    if not safety.get("ok"):
        blockers.append("command safety failed")
    payload["future_live_ready"] = not blockers
    payload["future_live_blockers"] = blockers
    payload["ok"] = bool(base_plan.get("ok") and safety.get("ok"))
    return payload


def run_live(args: argparse.Namespace) -> dict[str, Any]:
    plan = dry_run_payload(args)
    if not plan.get("future_live_ready"):
        raise RuntimeError(f"V2477 live inputs are not ready: {plan.get('future_live_blockers')}")
    if not plan.get("command_safety", {}).get("ok"):
        raise RuntimeError(f"V2477 command safety failed: {plan.get('command_safety')}")

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
    logcat_capture: dict[str, Any] | None = None
    cleanup_done = False
    try:
        rollback_needed = True
        steps.append(route.run_step("flash-android", route.flash_android_command(r_args, str(out_dir / "android_boot_0600.img")), out_dir, timeout_sec=args.flash_timeout))
        v2396.run_android_post_handoff_settle(args, out_dir, steps)

        manual_start_record: dict[str, Any] | None = None
        for name, command, check in stage_commands(args):
            record = route.run_step(name, command, out_dir, timeout_sec=args.adb_command_timeout, check=check)
            steps.append(record)
            if name == "acdbtap-manual-start-preload":
                manual_start_record = record

        steps.append(route.run_step("acdbtap-verify-before-playback", verify_command(args), out_dir, timeout_sec=args.adb_command_timeout, check=False))
        if not manual_start_record or not preload_confirmed(manual_start_record):
            result["decision"] = f"{decision_slug()}-preload-not-confirmed-before-rollback"
            raise RuntimeError("libacdbtap preload was not confirmed in audio HAL maps; aborting before playback")

        steps.append(route.run_step("logcat-clear-before-stimulus", route.logcat_clear_command(r_args), out_dir, timeout_sec=args.adb_command_timeout, check=False))
        logcat_capture = route.start_logcat_capture(r_args, out_dir)
        logcat_capture["record"]["name"] = "acdbtap-live-logcat"
        steps.append(logcat_capture["record"])

        steps.append(route.run_step("playback-start-background", route.playback_start_command(r_args), out_dir, timeout_sec=args.adb_command_timeout))
        wait_sec = max(float(args.capture_observe_sec), (args.duration_ms / 1000.0) + args.post_delay_sec + 1.0)
        time.sleep(wait_sec)
        for index, command in enumerate(route.stimulus_result_commands(r_args)):
            steps.append(route.run_step(f"playback-result-{index}", command, out_dir, timeout_sec=args.adb_command_timeout, check=False))

        steps.append(route.run_step("acdbtap-verify-after-playback", verify_command(args), out_dir, timeout_sec=args.adb_command_timeout, check=False))
        steps.append(route.run_step("acdbtap-collect-prepare", collect_prepare_command(args), out_dir, timeout_sec=args.adb_command_timeout, check=False))
        steps.append(route.run_step("acdbtap-pull-capture", pull_capture_command(args, str(out_dir / "acdbtap-device-artifacts")), out_dir, timeout_sec=args.adb_command_timeout, check=False))
        steps.append(route.run_step("acdbtap-pull-stage", pull_stage_command(args, str(out_dir / "acdbtap-stage-artifacts")), out_dir, timeout_sec=args.adb_command_timeout, check=False))

        summary = summarize_acdbtap_artifacts(out_dir)
        result["acdbtap_summary"] = summary
        result["decision"] = f"{decision_slug()}-{summary['classification']}-before-rollback"
        result["ok"] = bool(summary["raw_complete"] and summary["target_4916_count"] > 0)

        steps.append(route.run_step("acdbtap-cleanup", cleanup_command(args), out_dir, timeout_sec=args.adb_command_timeout, check=False))
        cleanup_done = True
    except Exception as error:
        result.setdefault("decision", f"{decision_slug()}-failed-before-rollback")
        result["error"] = str(error)
        if result.get("decision") == f"{decision_slug()}-live-started":
            result["decision"] = f"{decision_slug()}-failed-before-rollback"
    finally:
        route.stop_logcat_capture(logcat_capture)
        if rollback_needed:
            try:
                if not cleanup_done:
                    steps.append(route.run_step("acdbtap-cleanup-finally", cleanup_command(args), out_dir, timeout_sec=args.adb_command_timeout, check=False))
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
    if args.run_live:
        result = run_live(args)
    else:
        result = dry_run_payload(args)
    print(json.dumps({
        "decision": result.get("decision"),
        "ok": result.get("ok"),
        "future_live_ready": result.get("future_live_ready"),
        "future_live_blockers": result.get("future_live_blockers"),
        "out_dir": result.get("out_dir"),
    }, indent=2, sort_keys=True))
    return 0 if result.get("ok") or (not args.run_live and result.get("command_safety", {}).get("ok")) else 1


if __name__ == "__main__":
    raise SystemExit(main())
