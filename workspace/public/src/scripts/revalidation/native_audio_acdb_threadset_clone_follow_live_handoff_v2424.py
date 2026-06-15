#!/usr/bin/env python3
"""V2424 exact-gated thread-set clone-following Android msm_audio_cal capture.

This runner executes the V2423 hybrid thread-set observer plan under the checked
Android handoff model. It boots the pinned stock Android image, verifies Magisk
root, stages the private thread-set clone-following observer, captures
fd-filtered /dev/msm_audio_cal ioctl metadata around bounded Android AudioTrack
speaker playback, pulls private artifacts, cleans up, reboots to recovery, and
rolls back to V2321.

It does not run under native init, does not issue calibration ioctls, does not
write native mixer controls, and does not install a persistent Magisk module.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import native_audio_acdb_android_measurement_planner_v2396 as v2396
import native_audio_acdb_threadset_clone_follow_planner_v2423 as v2423
import native_audio_android_route_delta_handoff_v2365 as route


RUN_ID = "V2424"
BUILD_TAG = "v2424-audio-acdb-threadset-clone-follow-live"
ROOT = v2423.ROOT
APPROVAL_PHRASE = v2423.APPROVAL_PHRASE
DEFAULT_OUT_BASE = ROOT / "workspace/private/runs/audio"
DEFAULT_CAPTURE_WARMUP_SEC = 0.75


def rel(path: Path | str) -> str:
    return v2423.rel(path)


def default_live_out_dir() -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return DEFAULT_OUT_BASE / f"{RUN_ID.lower()}-acdb-threadset-clone-follow-capture-{stamp}"


def decision_slug() -> str:
    return f"{RUN_ID.lower()}-acdb-threadset-clone-follow-capture"


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def args_for_v2423(args: argparse.Namespace) -> argparse.Namespace:
    return argparse.Namespace(
        dry_run=True,
        materialize_capture_helper=args.materialize_capture_helper,
        helper_out_dir=args.helper_out_dir,
        cc=args.cc,
        stimulus_apk=args.stimulus_apk,
        adb=args.adb,
        serial=args.serial,
        android_timeout=args.android_timeout,
        adb_command_timeout=args.adb_command_timeout,
        flash_timeout=args.flash_timeout,
        duration_ms=args.duration_ms,
        sample_rate=args.sample_rate,
        amplitude=args.amplitude,
        active_delay_sec=args.active_delay_sec,
        post_delay_sec=args.post_delay_sec,
        capture_duration_sec=args.capture_duration_sec,
        max_bytes=args.max_bytes,
        process_poll_sec=args.process_poll_sec,
        from_native=args.from_native,
    )


def ensure_live_approval(args: argparse.Namespace) -> None:
    if args.approval != APPROVAL_PHRASE:
        raise RuntimeError("exact AUD-5F thread-set clone-follow ACDB payload capture approval phrase is required for --run-live")


def adb_subcommand(command: list[str]) -> str | None:
    if not command or command[0] != "adb":
        return None
    index = 1
    if len(command) > 3 and command[index] == "-s":
        index += 2
    if index >= len(command):
        return None
    return command[index]


def needs_stage_adb_wait(command: list[str]) -> bool:
    return adb_subcommand(command) in {"push", "install"}


def stage_wait_command(args: argparse.Namespace) -> list[str]:
    return v2423.adb_base(args) + ["wait-for-device"]


def stage_wait_plan(args: argparse.Namespace, stage_commands: list[list[str]]) -> list[dict[str, Any]]:
    return [
        {
            "before_stage_index": index,
            "reason": f"stabilize ADB before adb {adb_subcommand(command)}",
            "command": stage_wait_command(args),
        }
        for index, command in enumerate(stage_commands)
        if needs_stage_adb_wait(command)
    ]


def payload_sha256(bytes_hex: str) -> str | None:
    if not bytes_hex:
        return None
    try:
        return hashlib.sha256(bytes.fromhex(bytes_hex)).hexdigest()
    except ValueError:
        return None


def summarize_capture_artifacts(out_dir: Path) -> dict[str, Any]:
    artifact_root = out_dir / "device-artifacts"
    summary: dict[str, Any] = {
        "artifact_root": rel(artifact_root),
        "artifact_root_exists": artifact_root.exists(),
        "jsonl_files": [],
        "target_pids": [],
        "task_snapshots": [],
        "helper_starts": 0,
        "tracee_adds": 0,
        "clone_events": 0,
        "helper_errors": [],
        "ioctl_entries": 0,
        "ioctl_exits": 0,
        "requests": [],
        "payload_hashes": [],
        "raw_payload_in_summary": False,
    }
    if not artifact_root.exists():
        summary["classification"] = "artifact-pull-missing"
        return summary

    for pid_file in sorted(artifact_root.rglob("*pids.txt")):
        text = pid_file.read_text(errors="replace").strip()
        if text:
            summary["target_pids"].append({"path": rel(pid_file), "text": text})

    for task_file in sorted(artifact_root.rglob("proc-*-tasks-initial.txt")):
        text = task_file.read_text(errors="replace").strip()
        summary["task_snapshots"].append({
            "path": rel(task_file),
            "line_count": len(text.splitlines()) if text else 0,
        })

    seen_requests: set[str] = set()
    seen_hashes: set[str] = set()
    for jsonl_path in sorted(artifact_root.rglob("msm-audio-cal-threadset-p*.jsonl")):
        file_info: dict[str, Any] = {
            "path": rel(jsonl_path),
            "events": 0,
            "tracee_adds": 0,
            "clone_events": 0,
            "ioctl_entries": 0,
            "ioctl_exits": 0,
            "stop_events": 0,
        }
        summary["jsonl_files"].append(file_info)
        for line in jsonl_path.read_text(errors="replace").splitlines():
            if not line.strip():
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                file_info.setdefault("decode_errors", 0)
                file_info["decode_errors"] += 1
                continue
            file_info["events"] += 1
            kind = event.get("event")
            if kind == "start":
                summary["helper_starts"] += 1
                file_info["tgid"] = event.get("tgid")
                file_info["fd_pid"] = event.get("fd_pid")
            elif kind == "tracee-add":
                summary["tracee_adds"] += 1
                file_info["tracee_adds"] += 1
            elif kind == "clone":
                summary["clone_events"] += 1
                file_info["clone_events"] += 1
            elif kind == "error":
                summary["helper_errors"].append({
                    "path": rel(jsonl_path),
                    "where": event.get("where"),
                    "tid": event.get("tid"),
                    "errno": event.get("errno"),
                    "strerror": event.get("strerror"),
                })
            elif kind == "ioctl_entry":
                summary["ioctl_entries"] += 1
                file_info["ioctl_entries"] += 1
                request = str(event.get("request"))
                if request not in seen_requests:
                    seen_requests.add(request)
                    summary["requests"].append(request)
                digest = payload_sha256(str(event.get("bytes_hex", "")))
                if digest and digest not in seen_hashes:
                    seen_hashes.add(digest)
                    summary["payload_hashes"].append({
                        "request": request,
                        "read_len": event.get("read_len"),
                        "sha256": digest,
                    })
            elif kind == "ioctl_exit":
                summary["ioctl_exits"] += 1
                file_info["ioctl_exits"] += 1
            elif kind == "stop":
                file_info["stop_events"] += 1
                file_info["captured_entries"] = event.get("captured_entries")
                file_info["tracees"] = event.get("tracees")
                file_info["timed_out"] = event.get("timed_out")

    if summary["ioctl_entries"]:
        summary["classification"] = "captured-msm-audio-cal-payload-events"
    elif summary["tracee_adds"] > summary["helper_starts"]:
        summary["classification"] = "threadset-attached-no-msm-audio-cal-ioctl"
    elif summary["clone_events"]:
        summary["classification"] = "clone-events-observed-no-msm-audio-cal-ioctl"
    elif summary["helper_starts"]:
        summary["classification"] = "threadset-helper-started-no-msm-audio-cal-ioctl"
    elif summary["target_pids"]:
        summary["classification"] = "target-pids-found-helper-did-not-start"
    else:
        summary["classification"] = "no-target-audio-pids"
    return summary


def run_live(args: argparse.Namespace) -> dict[str, Any]:
    ensure_live_approval(args)
    args.materialize_capture_helper = True
    route_args = v2423.v2415.android_args(args)
    plan = v2423.dry_run_payload(args_for_v2423(args))
    if not plan.get("future_live_ready"):
        raise RuntimeError(f"V2424 live inputs are not ready: {plan.get('future_live_blockers')}")
    if not plan.get("command_safety", {}).get("ok"):
        raise RuntimeError(f"V2424 command safety failed: {plan.get('command_safety')}")

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

    sealed = route.copy_sealed_android_boot(plan["android_boot"]["selected"], out_dir)
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

        for index, command in enumerate(plan["commands"]["stage_threadset_clone_follow_helper_and_stimulus"]):
            if needs_stage_adb_wait(command):
                subcommand = adb_subcommand(command) or "unknown"
                steps.append(route.run_step(
                    f"stage-{index}-adb-wait-before-{subcommand}",
                    stage_wait_command(args),
                    out_dir,
                    timeout_sec=args.adb_command_timeout,
                    check=False,
                ))
            steps.append(route.run_step(f"stage-{index}", command, out_dir, timeout_sec=args.adb_command_timeout))

        steps.append(route.run_step("baseline-process-inventory", plan["commands"]["baseline_process_inventory"], out_dir, timeout_sec=args.adb_command_timeout, check=False))
        steps.append(route.run_step("logcat-clear-before-stimulus", route.logcat_clear_command(route_args), out_dir, timeout_sec=args.adb_command_timeout, check=False))
        logcat_capture = route.start_logcat_capture(route_args, out_dir)
        logcat_capture["record"]["name"] = "threadset-clone-follow-payload-capture-logcat"
        logcat_capture["record"]["filter_regex_offline"] = v2396.LOG_FILTER_REGEX
        steps.append(logcat_capture["record"])

        steps.append(route.run_step("payload-capture-start-background", v2423.capture_start_command(args), out_dir, timeout_sec=args.adb_command_timeout))
        time.sleep(args.capture_warmup_sec)
        steps.append(route.run_step("playback-start-background", route.playback_start_command(route_args), out_dir, timeout_sec=args.adb_command_timeout))
        wait_sec = max(float(args.capture_duration_sec) + 1.0, (args.duration_ms / 1000.0) + args.post_delay_sec + args.capture_warmup_sec)
        time.sleep(wait_sec)
        for index, command in enumerate(route.stimulus_result_commands(route_args)):
            steps.append(route.run_step(f"playback-result-{index}", command, out_dir, timeout_sec=args.adb_command_timeout, check=False))

        steps.append(route.run_step("prepare-private-artifacts-for-pull", v2423.prepare_collect_command(args), out_dir, timeout_sec=args.adb_command_timeout, check=False))
        steps.append(route.run_step(
            "collect-private-artifacts",
            v2423.collect_command(args)[:-1] + [str(out_dir / "device-artifacts")],
            out_dir,
            timeout_sec=args.adb_command_timeout,
            check=False,
        ))
        result["payload_capture_summary"] = summarize_capture_artifacts(out_dir)

        for index, command in enumerate(v2423.cleanup_commands(args)):
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


def dry_run(args: argparse.Namespace) -> dict[str, Any]:
    namespace = args_for_v2423(args)
    namespace.materialize_capture_helper = args.materialize_capture_helper
    payload = v2423.dry_run_payload(namespace)
    stage_commands = payload["commands"].get("stage_threadset_clone_follow_helper_and_stimulus", [])
    payload.update({
        "run_id": RUN_ID,
        "build_tag": BUILD_TAG,
        "decision": f"{decision_slug()}-live-dry-run",
        "host_only": True,
        "device_action": "none",
        "live_runner": rel(ROOT / "workspace/public/src/scripts/revalidation/native_audio_acdb_threadset_clone_follow_live_handoff_v2424.py"),
        "approval_phrase_required_for_live": APPROVAL_PHRASE,
        "stage_adb_waits": stage_wait_plan(args, stage_commands),
    })
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="emit the V2424 live plan; no device action")
    mode.add_argument("--run-live", action="store_true", help="run the exact-gated V2424 thread-set clone-following capture")
    parser.add_argument("--materialize-capture-helper", action="store_true", help="compile private AArch64 thread-set observer for dry-run/live readiness")
    parser.add_argument("--helper-out-dir", type=Path, default=v2423.DEFAULT_HELPER_OUT_DIR)
    parser.add_argument("--cc", default=v2423.DEFAULT_CC)
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
    parser.add_argument("--capture-duration-sec", type=int, default=v2423.DEFAULT_DURATION_SEC)
    parser.add_argument("--capture-warmup-sec", type=float, default=DEFAULT_CAPTURE_WARMUP_SEC)
    parser.add_argument("--max-bytes", type=int, default=v2423.DEFAULT_MAX_BYTES)
    parser.add_argument("--process-poll-sec", type=float, default=v2423.DEFAULT_PROCESS_POLL_SEC)
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
