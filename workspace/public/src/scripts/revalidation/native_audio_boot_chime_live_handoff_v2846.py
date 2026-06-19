#!/usr/bin/env python3
"""V2846 live validation for V2845 best-effort audio boot chime.

V2845 enables the bounded `audio chime` preset from PID1 at boot. This runner
flashes that candidate, does not send a manual playback command, waits for the
boot-started worker to finish, captures boot-chime logs, and rolls back to V2321.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Sequence

import native_audio_late_manifest_wait_live_handoff_v2808 as runner

CHIME_DEFAULT_AMPLITUDE_MILLI = 80
CHIME_DEFAULT_DURATION_MS = 1200
BOOT_CHIME_LAUNCH_LOG = "/cache/a90-audio-play/boot-chime-launch.log"
BUNDLED_REMOTE_ROOT = "/a90/audio/setcal/internal-speaker-safe"
BUNDLED_REMOTE_MANIFEST = "/a90/audio/manifests/audio-setcal-internal-speaker-safe.manifest"

runner.CYCLE = "V2846"
runner.REPORT_PATH = (
    runner.ROOT
    / "docs/reports/NATIVE_INIT_V2846_AUDIO_BOOT_CHIME_LIVE_2026-06-19.md"
)
runner.BUILD_MANIFEST = (
    runner.ROOT / "workspace/private/builds/native-init/v2845-audio-boot-chime/manifest.json"
)
runner.CANDIDATE_IMAGE = (
    runner.ROOT / "workspace/private/inputs/boot_images/boot_linux_v2845_audio_boot_chime.img"
)
runner.CANDIDATE_VERSION = "0.10.13"
runner.CANDIDATE_TAG = "v2845-audio-boot-chime"
runner.REPORT_TRACK = "post-promotion best-effort audio boot chime validation."
runner.DEFAULT_REMOTE_ROOT = BUNDLED_REMOTE_ROOT
runner.DEFAULT_REMOTE_MANIFEST = BUNDLED_REMOTE_MANIFEST
runner.configure_base_for_v2808()

_original_parse_args = runner.parse_args
_original_preflight_state = runner.preflight_state

_DECISION_SUFFIX = {
    "audio-late-manifest-wait-live-started": "boot-chime-live-started",
    "late-manifest-play-start-failed-before-rollback": "boot-chime-start-failed-before-rollback",
    "late-manifest-play-no-card-before-rollback": "boot-chime-no-card-before-rollback",
    "late-manifest-play-failed-before-rollback": "boot-chime-failed-before-rollback",
    "late-manifest-live-blocked": "boot-chime-live-blocked",
    "late-manifest-play-pass-before-rollback": "boot-chime-pass-before-rollback",
    "late-manifest-play-live-dry-run": "boot-chime-live-dry-run",
}


def _argv_list(argv: list[str] | None) -> list[str]:
    return list(sys.argv[1:] if argv is None else argv)


def _has_option(argv: Sequence[str], name: str) -> bool:
    return name in argv or any(item.startswith(name + "=") for item in argv)


def decision(suffix: str) -> str:
    return f"{runner.cycle_slug()}-{_DECISION_SUFFIX.get(suffix, suffix)}"


def preflight_state() -> dict[str, Any]:
    state = _original_preflight_state()
    state.update({
        "cycle": runner.CYCLE,
        "report_path": runner.rel(runner.REPORT_PATH),
        "discriminator": "audio-boot-chime-autoplay-bundled-setcal",
        "candidate_expect_version": runner.CANDIDATE_VERSION,
        "candidate_expect_tag": runner.CANDIDATE_TAG,
        "remote_native_manifest": BUNDLED_REMOTE_MANIFEST,
        "default_remote_root": BUNDLED_REMOTE_ROOT,
        "boot_chime_launch_log": BOOT_CHIME_LAUNCH_LOG,
        "host_artifact_deploy_required": False,
        "host_artifact_deploy_forbidden_in_this_unit": True,
        "live_scope": [
            "boot partition only via native_init_flash.py",
            f"flash {runner.CANDIDATE_TAG} candidate only; no new boot artifact",
            "do not issue manual audio play/chime command; validate PID1 boot chime only",
            "capture boot-chime launch log and existing worker log/status",
            "perform no host artifact deployment to /cache or /a90",
            "require SET-cal/route/PCM pass markers from the boot-started native worker",
            "low-amplitude profile cap is enforced by native-init source",
            "rollback to v2321 and verify selftest fail=0",
        ],
    })
    return state


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    raw = _argv_list(argv)
    args = _original_parse_args(argv)
    if not _has_option(raw, "--amplitude-milli"):
        args.amplitude_milli = CHIME_DEFAULT_AMPLITUDE_MILLI
    if not _has_option(raw, "--duration-ms"):
        args.duration_ms = CHIME_DEFAULT_DURATION_MS
    return args


def boot_chime_command(_args: argparse.Namespace) -> list[str]:
    return ["boot-autoplay", "audio", "chime"]


def boot_chime_started(text: str) -> bool:
    required = (
        "audio.boot_chime.child_started=1",
        "audio.chime.version=1",
        "audio.chime.execute_requested=1",
        "audio.chime.boot_autoplay_default=1",
    )
    return all(marker in text for marker in required)


def run_play_sequence(args: argparse.Namespace,
                      out_dir,
                      steps: list[dict[str, Any]],
                      deploy_plan: dict[str, Any],
                      native_manifest_path) -> dict[str, Any]:
    del deploy_plan, native_manifest_path
    result: dict[str, Any] = {
        "play_command": "boot-autoplay audio chime",
        "host_artifact_deploy_performed": False,
        "runtime_artifacts": {"installed": [], "host_deploy_performed": False},
        "remote_native_manifest": BUNDLED_REMOTE_MANIFEST,
        "boot_chime_launch_log": BOOT_CHIME_LAUNCH_LOG,
    }

    runner.hide_auto_menu(out_dir, steps, "before-boot-chime-observe")
    launch_log_step = runner.base.run_serial_step(
        out_dir,
        steps,
        "candidate-audio-boot-chime-launch-log",
        ["run", "/bin/busybox", "cat", BOOT_CHIME_LAUNCH_LOG],
        timeout=45.0,
        retry_unsafe=True,
        allow_error=True,
    )
    launch_log_text = runner.stdout_of(launch_log_step)
    result["boot_chime_launch_log_stdout_path"] = launch_log_step.get("stdout_path")
    result["boot_chime_launch_log_rc"] = launch_log_step.get("rc")
    result["boot_chime_started"] = boot_chime_started(launch_log_text)
    if not result["boot_chime_started"]:
        result["play_summary"] = runner.classify_play_output(launch_log_text)
        result["play_output_pass"] = False
        result["play_start_failed"] = True
        return result

    card_wait = runner.wait_for_sound_card(
        out_dir,
        steps,
        count=args.card_poll_count,
        interval=args.card_poll_interval,
    )
    result["card_wait_after_play_start"] = card_wait
    result["card_ready_after_play_start"] = bool(card_wait.get("ready"))
    if not result["card_ready_after_play_start"]:
        result["play_summary"] = runner.classify_play_output(launch_log_text)
        result["play_output_pass"] = False
        result["card_not_ready_after_play_start"] = True
        return result

    worker = runner.base.wait_for_worker_done(out_dir, steps, args.play_timeout)
    result["worker_status_done"] = bool(worker.get("done"))
    result["worker_status_attempts"] = worker.get("attempts")
    result["worker_status_stdout_path"] = worker.get("stdout_path")
    log_step = runner.base.run_serial_step(
        out_dir,
        steps,
        "candidate-audio-boot-chime-worker-log",
        ["run", "/bin/busybox", "cat", runner.base.REMOTE_PLAY_LOG],
        timeout=45.0,
        retry_unsafe=True,
        allow_error=True,
    )
    worker_log_text = runner.stdout_of(log_step)
    result["worker_log_stdout_path"] = log_step.get("stdout_path")
    combined_text = "\n".join([launch_log_text, str(worker.get("text") or ""), worker_log_text])
    result["play_summary"] = runner.classify_play_output(combined_text)
    result["play_output_pass"] = runner.play_output_pass(result["play_summary"])
    result["status_after_play"] = runner.capture_audio_status(out_dir, steps, "after-boot-chime")
    dmesg_tail = runner.base.run_serial_step(
        out_dir,
        steps,
        "candidate-dmesg-audio-boot-chime-tail",
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
            "manual_audio_command": None,
            "boot_chime_launch_log": ["run", "/bin/busybox", "cat", BOOT_CHIME_LAUNCH_LOG],
            "play_status": ["audio", "play-status"],
            "worker_log": ["run", "/bin/busybox", "cat", runner.base.REMOTE_PLAY_LOG],
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
    play_summary = result.get("play_summary") or {}
    card_wait = result.get("card_wait_after_play_start") or {}
    return "\n".join([
        f"# Native Init {runner.CYCLE} Audio Boot Chime Live Handoff",
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
        f"- Operator audible confirmation: `{result.get('operator_audible_confirmation', 'not-recorded-in-runner')}`",
        "",
        "## Boot Chime Evidence",
        "",
        "- Manual audio command sent: `0`",
        f"- Boot chime launch log: `{BOOT_CHIME_LAUNCH_LOG}`",
        f"- Boot chime launch log stdout: `{result.get('boot_chime_launch_log_stdout_path')}`",
        f"- Boot chime started markers: `{int(bool(result.get('boot_chime_started')))}`",
        f"- Host artifact deployment performed: `{int(bool(result.get('host_artifact_deploy_performed')))}`",
        f"- Bundled manifest path: `{BUNDLED_REMOTE_MANIFEST}`",
        f"- Bundled root: `{BUNDLED_REMOTE_ROOT}`",
        f"- Card ready after boot chime start: `{int(bool(result.get('card_ready_after_play_start')))}` after `{card_wait.get('attempts')}` polls",
        f"- Card poll last summary: `{json.dumps((card_wait.get('last') or {}).get('summary') or {}, ensure_ascii=False, sort_keys=True)}`",
        f"- Manifest wait started/ready/timeout: `{int(bool(play_summary.get('manifest_wait_started')))} / {int(bool(play_summary.get('manifest_ready')))} / {int(bool(play_summary.get('manifest_timeout')))}`",
        "",
        "## Playback Evidence",
        "",
        f"- Worker status done/attempts: `{int(bool(result.get('worker_status_done')))}` / `{result.get('worker_status_attempts')}`",
        f"- Worker status stdout: `{result.get('worker_status_stdout_path')}`",
        f"- Worker log stdout: `{result.get('worker_log_stdout_path')}`",
        f"- Worker started/done: `{int(bool(play_summary.get('worker_started')))}` / `{int(bool(play_summary.get('worker_done')))}`",
        f"- Integrated done: `{int(bool(play_summary.get('integrated_done')))}`",
        f"- Sound-control ready/timeout: `{int(bool(play_summary.get('sound_control_wait_ready')))}` / `{int(bool(play_summary.get('sound_control_wait_timeout')))}`",
        f"- SET-cal hold/all-set/dealloc: `{int(bool(play_summary.get('setcal_hold_active')))} / {int(bool(play_summary.get('setcal_all_set')))} / {int(bool(play_summary.get('setcal_deallocated')))}`",
        f"- Route apply/reset OK: `{int(bool(play_summary.get('route_apply_ok')))} / {int(bool(play_summary.get('route_reset_ok')))}`",
        f"- PCM write/done: `{int(bool(play_summary.get('pcm_write_attempted')))}` / `{int(bool(play_summary.get('pcm_done')))}`",
        f"- Safety amplitude/duration cap: `{int(bool(play_summary.get('safety_amplitude')))} / {int(bool(play_summary.get('safety_duration')))}`",
        "",
        "## Safety",
        "",
        "- Flash path: `workspace/public/src/scripts/revalidation/native_init_flash.py`.",
        "- Only the boot partition is flashed; no runtime ACDB files are copied from the host in this unit.",
        "- No manual `audio play` or `audio chime` command is sent; this validates PID1 boot autoplay only.",
        "- No forbidden partitions are touched.",
        "- Boot chime uses amplitude `80` milli and duration `1200` ms by default, below the source cap.",
        "- Public report is metadata-only; private raw command transcripts stay under `workspace/private/`.",
        "",
    ])


runner.decision = decision
runner.preflight_state = preflight_state
runner.parse_args = parse_args
runner.play_command = boot_chime_command
runner.run_play_sequence = run_play_sequence
runner.dry_run_payload = dry_run_payload
runner.render_report = render_report


if __name__ == "__main__":
    raise SystemExit(runner.main())
