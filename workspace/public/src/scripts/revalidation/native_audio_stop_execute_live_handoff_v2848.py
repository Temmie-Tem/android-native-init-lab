#!/usr/bin/env python3
"""V2848 live validation for V2847 bounded audio stop execute.

This flashes the V2847 stop-execute candidate, lets the bundled boot-chime
worker settle, runs `audio stop internal-speaker-safe --execute`, verifies that
the command performs only the bounded core route reset cleanup, and rolls back
to V2321.
"""

from __future__ import annotations

import argparse
import json
from typing import Any, Sequence

import native_audio_late_manifest_wait_live_handoff_v2808 as runner

BOOT_CHIME_LAUNCH_LOG = "/cache/a90-audio-play/boot-chime-launch.log"
BUNDLED_REMOTE_ROOT = "/a90/audio/setcal/internal-speaker-safe"
BUNDLED_REMOTE_MANIFEST = "/a90/audio/manifests/audio-setcal-internal-speaker-safe.manifest"
STOP_COMMAND = ["audio", "stop", "internal-speaker-safe", "--execute"]

runner.CYCLE = "V2848"
runner.REPORT_PATH = (
    runner.ROOT
    / "docs/reports/NATIVE_INIT_V2848_AUDIO_STOP_EXECUTE_LIVE_2026-06-19.md"
)
runner.BUILD_MANIFEST = (
    runner.ROOT / "workspace/private/builds/native-init/v2847-audio-stop-execute/manifest.json"
)
runner.CANDIDATE_IMAGE = (
    runner.ROOT / "workspace/private/inputs/boot_images/boot_linux_v2847_audio_stop_execute.img"
)
runner.CANDIDATE_VERSION = "0.10.14"
runner.CANDIDATE_TAG = "v2847-audio-stop-execute"
runner.REPORT_TRACK = "post-promotion bounded audio stop execute validation."
runner.DEFAULT_REMOTE_ROOT = BUNDLED_REMOTE_ROOT
runner.DEFAULT_REMOTE_MANIFEST = BUNDLED_REMOTE_MANIFEST
runner.configure_base_for_v2808()

_original_parse_args = runner.parse_args
_original_preflight_state = runner.preflight_state

_DECISION_SUFFIX = {
    "audio-late-manifest-wait-live-started": "stop-execute-live-started",
    "late-manifest-play-start-failed-before-rollback": "stop-execute-start-failed-before-rollback",
    "late-manifest-play-no-card-before-rollback": "stop-execute-no-card-before-rollback",
    "late-manifest-play-failed-before-rollback": "stop-execute-failed-before-rollback",
    "late-manifest-live-blocked": "stop-execute-live-blocked",
    "late-manifest-play-pass-before-rollback": "stop-execute-pass-before-rollback",
    "late-manifest-play-live-dry-run": "stop-execute-live-dry-run",
}


def _has_option(argv: Sequence[str], name: str) -> bool:
    return name in argv or any(item.startswith(name + "=") for item in argv)


def decision(suffix: str) -> str:
    return f"{runner.cycle_slug()}-{_DECISION_SUFFIX.get(suffix, suffix)}"


def preflight_state() -> dict[str, Any]:
    state = _original_preflight_state()
    state.update({
        "cycle": runner.CYCLE,
        "report_path": runner.rel(runner.REPORT_PATH),
        "discriminator": "audio-stop-execute-bounded-core-route-reset",
        "candidate_expect_version": runner.CANDIDATE_VERSION,
        "candidate_expect_tag": runner.CANDIDATE_TAG,
        "remote_native_manifest": BUNDLED_REMOTE_MANIFEST,
        "default_remote_root": BUNDLED_REMOTE_ROOT,
        "boot_chime_launch_log": BOOT_CHIME_LAUNCH_LOG,
        "host_artifact_deploy_required": False,
        "host_artifact_deploy_forbidden_in_this_unit": True,
        "stop_command": " ".join(STOP_COMMAND),
        "live_scope": [
            "boot partition only via native_init_flash.py",
            f"flash {runner.CANDIDATE_TAG} candidate only; no new boot artifact",
            "let the bundled boot-chime worker settle before stop execute",
            "run exactly one native audio stop --execute command",
            "require bounded no-active PCM/SET-cal markers and core route reset markers",
            "perform no host artifact deployment to /cache or /a90",
            "no PCM playback command is issued by this runner",
            "rollback to v2321 and verify selftest fail=0",
        ],
    })
    return state


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    raw = list(argv or [])
    args = _original_parse_args(argv)
    if not _has_option(raw, "--play-timeout"):
        args.play_timeout = 260.0
    if not _has_option(raw, "--card-poll-count"):
        args.card_poll_count = 35
    if not _has_option(raw, "--card-poll-interval"):
        args.card_poll_interval = 2.0
    return args


def boot_chime_started(text: str) -> bool:
    required = (
        "audio.boot_chime.child_started=1",
        "audio.chime.version=1",
        "audio.chime.execute_requested=1",
        "audio.chime.boot_autoplay_default=1",
    )
    return all(marker in text for marker in required)


def classify_stop_output(text: str, rc: int | None) -> dict[str, Any]:
    summary = {
        "rc_zero": rc == 0,
        "execute_supported": "audio.stop.execute_supported=1" in text,
        "execute_requested": "audio.stop.execute_requested=1" in text,
        "playback_no_active": "audio.stop.playback_stop_reason=no-active-pcm-handle" in text,
        "setcal_no_active": "audio.stop.setcal_deallocate_reason=no-active-setcal-session" in text,
        "route_write_attempted": "audio.stop.route_write_attempted=1" in text,
        "ioctl_attempted": "audio.stop.ioctl_attempted=1" in text,
        "route_reset_mode": "audio.route.mode=reset" in text,
        "route_core_layer": "audio.route.layer=core" in text,
        "route_write_attempted_inner": "audio.route.write_attempted=1" in text,
        "route_write_done": "audio.route.write_done count=" in text and "layer=core mode=reset" in text,
        "route_reset_rc0": "audio.stop.route_reset_rc=0" in text,
        "stop_done": "audio.stop.done=1 rc=0" in text,
        "refused": "audio.stop.refused=" in text or "audio.route.refused=" in text,
        "error": "audio.stop.error=" in text or "audio.route.error=" in text,
        "write_failed": "audio.route.write_failed" in text,
    }
    summary["pass"] = all(
        bool(summary[key])
        for key in (
            "rc_zero",
            "execute_supported",
            "execute_requested",
            "playback_no_active",
            "setcal_no_active",
            "route_write_attempted",
            "ioctl_attempted",
            "route_reset_mode",
            "route_core_layer",
            "route_write_attempted_inner",
            "route_write_done",
            "route_reset_rc0",
            "stop_done",
        )
    ) and not any(bool(summary[key]) for key in ("refused", "error", "write_failed"))
    return summary


def run_play_sequence(args: argparse.Namespace,
                      out_dir,
                      steps: list[dict[str, Any]],
                      deploy_plan: dict[str, Any],
                      native_manifest_path) -> dict[str, Any]:
    del deploy_plan, native_manifest_path
    result: dict[str, Any] = {
        "play_command": " ".join(STOP_COMMAND),
        "stop_command": " ".join(STOP_COMMAND),
        "host_artifact_deploy_performed": False,
        "runtime_artifacts": {"installed": [], "host_deploy_performed": False},
        "remote_native_manifest": BUNDLED_REMOTE_MANIFEST,
        "boot_chime_launch_log": BOOT_CHIME_LAUNCH_LOG,
    }

    runner.hide_auto_menu(out_dir, steps, "before-stop-execute")
    launch_log_step = runner.base.run_serial_step(
        out_dir,
        steps,
        "candidate-audio-boot-chime-launch-log-before-stop",
        ["run", "/bin/busybox", "cat", BOOT_CHIME_LAUNCH_LOG],
        timeout=45.0,
        retry_unsafe=True,
        allow_error=True,
    )
    launch_log_text = runner.stdout_of(launch_log_step)
    result["boot_chime_launch_log_stdout_path"] = launch_log_step.get("stdout_path")
    result["boot_chime_started"] = boot_chime_started(launch_log_text)

    worker = runner.base.wait_for_worker_done(out_dir, steps, args.play_timeout)
    result["worker_status_done_before_stop"] = bool(worker.get("done"))
    result["worker_status_attempts_before_stop"] = worker.get("attempts")
    result["worker_status_stdout_path"] = worker.get("stdout_path")
    worker_log = runner.base.run_serial_step(
        out_dir,
        steps,
        "candidate-audio-worker-log-before-stop",
        ["run", "/bin/busybox", "cat", runner.base.REMOTE_PLAY_LOG],
        timeout=45.0,
        retry_unsafe=True,
        allow_error=True,
    )
    result["worker_log_stdout_path"] = worker_log.get("stdout_path")

    card_wait = runner.wait_for_sound_card(
        out_dir,
        steps,
        count=args.card_poll_count,
        interval=args.card_poll_interval,
    )
    result["card_wait_after_play_start"] = card_wait
    result["card_ready_after_play_start"] = bool(card_wait.get("ready"))
    if not result["card_ready_after_play_start"]:
        result["play_summary"] = {"pass": False, "reason": "sound-card-not-ready-before-stop"}
        result["stop_summary"] = result["play_summary"]
        result["play_output_pass"] = False
        result["card_not_ready_after_play_start"] = True
        return result

    stop = runner.base.run_serial_step(
        out_dir,
        steps,
        "candidate-audio-stop-execute",
        STOP_COMMAND,
        timeout=120.0,
        retry_unsafe=False,
        allow_error=True,
    )
    stop_text = runner.stdout_of(stop)
    stop_summary = classify_stop_output(stop_text, stop.get("rc"))
    result["stop_rc"] = stop.get("rc")
    result["stop_stdout_path"] = stop.get("stdout_path")
    result["stop_summary"] = stop_summary
    result["play_summary"] = stop_summary
    result["play_output_pass"] = bool(stop_summary.get("pass"))
    result["status_after_play"] = runner.capture_audio_status(out_dir, steps, "after-stop-execute")
    dmesg_tail = runner.base.run_serial_step(
        out_dir,
        steps,
        "candidate-dmesg-audio-stop-execute-tail",
        ["run", "/bin/busybox", "sh", "-c", "dmesg | tail -n 260"],
        timeout=90.0,
        retry_unsafe=True,
        allow_error=True,
    )
    result["dmesg_audio_tail_stdout_path"] = dmesg_tail.get("stdout_path")
    return result


def dry_run_payload(args: argparse.Namespace, state: dict[str, Any]) -> dict[str, Any]:
    return {
        "decision": decision("late-manifest-play-live-dry-run"),
        "preflight_ok": runner.preflight_ok(state),
        "preflight": state,
        "commands": {
            "verify_current": runner.base.flash_command(
                runner.base.ROLLBACK_IMAGE,
                runner.base.ROLLBACK_VERSION,
                runner.base.ROLLBACK_SHA256,
                from_native=False,
            ) + ["--verify-only"],
            "flash_candidate": runner.base.flash_command(
                runner.base.CANDIDATE_IMAGE,
                runner.base.CANDIDATE_VERSION,
                str(state["candidate"].get("sha256") or ""),
                from_native=True,
            ),
            "boot_chime_launch_log": ["run", "/bin/busybox", "cat", BOOT_CHIME_LAUNCH_LOG],
            "wait_worker_done": ["audio", "play-status"],
            "audio_stop_execute": STOP_COMMAND,
            "host_artifact_deploy_count": 0,
            "rollback": runner.base.flash_command(
                runner.base.ROLLBACK_IMAGE,
                runner.base.ROLLBACK_VERSION,
                runner.base.ROLLBACK_SHA256,
                from_native=True,
            ),
        },
    }


def render_report(result: dict[str, Any]) -> str:
    stop_summary = result.get("stop_summary") or {}
    card_wait = result.get("card_wait_after_play_start") or {}
    return "\n".join([
        f"# Native Init {runner.CYCLE} Audio Stop Execute Live Handoff",
        "",
        "## Summary",
        "",
        f"- Cycle: `{runner.CYCLE}`",
        f"- Track: {runner.REPORT_TRACK}",
        f"- Decision: `{result.get('decision')}`",
        f"- Result directory: `{result.get('out_dir')}`",
        f"- Candidate tag/version: `{runner.base.CANDIDATE_TAG}` / `{runner.base.CANDIDATE_VERSION}`",
        f"- Candidate image SHA256: `{result.get('candidate_sha256')}`",
        f"- Rollback attempted: `{int(bool(result.get('rollback_attempted')))}`",
        f"- Rollback recovery fallback used: `{int(bool(result.get('rollback_recovery_fallback_used')))}`",
        f"- Rollback health: version_ok=`{int(bool(result.get('rollback_version_ok')))}` selftest_fail0=`{int(bool(result.get('rollback_selftest_fail0')))}`",
        "",
        "## Stop Execute Evidence",
        "",
        f"- Command: `{result.get('stop_command')}`",
        f"- Stop rc: `{result.get('stop_rc')}`",
        f"- Stop stdout: `{result.get('stop_stdout_path')}`",
        f"- Execute supported/requested: `{int(bool(stop_summary.get('execute_supported')))}` / `{int(bool(stop_summary.get('execute_requested')))}`",
        f"- No-active playback/SET-cal markers: `{int(bool(stop_summary.get('playback_no_active')))}` / `{int(bool(stop_summary.get('setcal_no_active')))}`",
        f"- Route reset mode/core/write-done: `{int(bool(stop_summary.get('route_reset_mode')))}` / `{int(bool(stop_summary.get('route_core_layer')))}` / `{int(bool(stop_summary.get('route_write_done')))}`",
        f"- Stop done/pass: `{int(bool(stop_summary.get('stop_done')))}` / `{int(bool(stop_summary.get('pass')))}`",
        f"- Refused/error/write-failed: `{int(bool(stop_summary.get('refused')))}` / `{int(bool(stop_summary.get('error')))}` / `{int(bool(stop_summary.get('write_failed')))}`",
        "",
        "## Boot Chime Settle",
        "",
        f"- Boot chime launch log: `{BOOT_CHIME_LAUNCH_LOG}`",
        f"- Boot chime launch log stdout: `{result.get('boot_chime_launch_log_stdout_path')}`",
        f"- Boot chime started markers: `{int(bool(result.get('boot_chime_started')))}`",
        f"- Worker done before stop/attempts: `{int(bool(result.get('worker_status_done_before_stop')))}` / `{result.get('worker_status_attempts_before_stop')}`",
        f"- Worker status stdout: `{result.get('worker_status_stdout_path')}`",
        f"- Worker log stdout: `{result.get('worker_log_stdout_path')}`",
        f"- Card ready before stop: `{int(bool(result.get('card_ready_after_play_start')))}` after `{card_wait.get('attempts')}` polls",
        f"- Card poll last summary: `{json.dumps((card_wait.get('last') or {}).get('summary') or {}, ensure_ascii=False, sort_keys=True)}`",
        "",
        "## Safety",
        "",
        "- Flash path: `workspace/public/src/scripts/revalidation/native_init_flash.py`.",
        "- Only the boot partition is flashed; no host runtime artifacts are copied in this unit.",
        "- The runner issues no PCM playback command; the only active command is one `audio stop --execute`.",
        "- Stop execute is expected to write only the already-reviewed core route reset controls.",
        "- No ACDB deallocate or fake PCM stop is attempted without an active native session.",
        "- Public report is metadata-only; private raw command transcripts stay under `workspace/private/`.",
        "",
    ])


runner.decision = decision
runner.preflight_state = preflight_state
runner.parse_args = parse_args
runner.run_play_sequence = run_play_sequence
runner.dry_run_payload = dry_run_payload
runner.render_report = render_report


if __name__ == "__main__":
    raise SystemExit(runner.main())
