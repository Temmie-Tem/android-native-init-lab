#!/usr/bin/env python3
"""V2844 live validation for standalone bundled-SET-cal audio chime.

V2843 packages the private SET-cal replay manifest and payloads into the boot
ramdisk under `/a90/audio`. This runner flashes that candidate, runs the manual
`audio chime` command, and explicitly performs no host artifact deployment. It
then rolls back to V2321 and verifies health.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Sequence

import native_audio_late_manifest_wait_live_handoff_v2808 as runner

CHIME_DEFAULT_AMPLITUDE_MILLI = 80
CHIME_DEFAULT_DURATION_MS = 1200
BUNDLED_REMOTE_ROOT = "/a90/audio/setcal/internal-speaker-safe"
BUNDLED_REMOTE_MANIFEST = "/a90/audio/manifests/audio-setcal-internal-speaker-safe.manifest"

runner.CYCLE = "V2844"
runner.REPORT_PATH = (
    runner.ROOT
    / "docs/reports/NATIVE_INIT_V2844_AUDIO_CHIME_BUNDLED_SETCAL_LIVE_2026-06-19.md"
)
runner.BUILD_MANIFEST = (
    runner.ROOT / "workspace/private/builds/native-init/v2843-audio-bundled-setcal/manifest.json"
)
runner.CANDIDATE_IMAGE = (
    runner.ROOT / "workspace/private/inputs/boot_images/boot_linux_v2843_audio_bundled_setcal.img"
)
runner.CANDIDATE_VERSION = "0.10.12"
runner.CANDIDATE_TAG = "v2843-audio-bundled-setcal"
runner.REPORT_TRACK = "post-promotion standalone audio chime validation with bundled SET-cal."
runner.DEFAULT_REMOTE_ROOT = BUNDLED_REMOTE_ROOT
runner.DEFAULT_REMOTE_MANIFEST = BUNDLED_REMOTE_MANIFEST
runner.configure_base_for_v2808()

_original_parse_args = runner.parse_args
_original_preflight_state = runner.preflight_state

_DECISION_SUFFIX = {
    "audio-late-manifest-wait-live-started": "standalone-bundled-chime-live-started",
    "late-manifest-play-start-failed-before-rollback": "standalone-bundled-chime-start-failed-before-rollback",
    "late-manifest-play-no-card-before-rollback": "standalone-bundled-chime-no-card-before-rollback",
    "late-manifest-play-failed-before-rollback": "standalone-bundled-chime-failed-before-rollback",
    "late-manifest-live-blocked": "standalone-bundled-chime-live-blocked",
    "late-manifest-play-pass-before-rollback": "standalone-bundled-chime-pass-before-rollback",
    "late-manifest-play-live-dry-run": "standalone-bundled-chime-live-dry-run",
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
        "discriminator": "audio-chime-standalone-bundled-setcal-no-host-deploy",
        "candidate_expect_version": runner.CANDIDATE_VERSION,
        "candidate_expect_tag": runner.CANDIDATE_TAG,
        "remote_native_manifest": BUNDLED_REMOTE_MANIFEST,
        "default_remote_root": BUNDLED_REMOTE_ROOT,
        "host_artifact_deploy_required": False,
        "host_artifact_deploy_forbidden_in_this_unit": True,
        "live_scope": [
            "boot partition only via native_init_flash.py",
            f"flash {runner.CANDIDATE_TAG} candidate only; no new boot artifact",
            "run native audio chime using bundled /a90/audio SET-cal manifest and payloads",
            "perform no host artifact deployment to /cache or /a90",
            "require SET-cal/route/PCM pass markers from the native worker log",
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


def chime_command(args: argparse.Namespace) -> list[str]:
    return [
        "audio",
        "chime",
        "--duration-ms",
        str(args.duration_ms),
        "--amplitude-milli",
        str(args.amplitude_milli),
        "--execute",
    ]


def run_play_sequence(args: argparse.Namespace,
                      out_dir,
                      steps: list[dict[str, Any]],
                      deploy_plan: dict[str, Any],
                      native_manifest_path) -> dict[str, Any]:
    del deploy_plan, native_manifest_path
    command = chime_command(args)
    result: dict[str, Any] = {
        "play_command": " ".join(command),
        "host_artifact_deploy_performed": False,
        "runtime_artifacts": {"installed": [], "host_deploy_performed": False},
        "remote_native_manifest": BUNDLED_REMOTE_MANIFEST,
    }

    runner.hide_auto_menu(out_dir, steps, "before-standalone-chime")
    play = runner.base.run_serial_step(
        out_dir,
        steps,
        "candidate-audio-chime-execute-standalone-bundled",
        command,
        timeout=90.0,
        retry_unsafe=False,
        allow_error=True,
    )
    play_text = runner.stdout_of(play)
    result["play_rc"] = play.get("rc")
    result["play_stdout_path"] = play.get("stdout_path")
    result["play_start_marker_loss_accepted"] = bool(
        play.get("rc") != 0 and runner.play_start_accepted(play, play_text)
    )
    if not runner.play_start_accepted(play, play_text):
        result["play_summary"] = runner.classify_play_output(play_text)
        result["play_output_pass"] = False
        result["play_start_failed"] = True
        return result

    card_wait = runner.wait_for_sound_card(out_dir, steps, count=args.card_poll_count, interval=args.card_poll_interval)
    result["card_wait_after_play_start"] = card_wait
    result["card_ready_after_play_start"] = bool(card_wait.get("ready"))
    if not result["card_ready_after_play_start"]:
        result["play_summary"] = runner.classify_play_output(play_text)
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
        "candidate-audio-standalone-chime-worker-log",
        ["run", "/bin/busybox", "cat", runner.base.REMOTE_PLAY_LOG],
        timeout=45.0,
        retry_unsafe=True,
        allow_error=True,
    )
    log_text = runner.stdout_of(log_step)
    result["worker_log_stdout_path"] = log_step.get("stdout_path")
    combined_text = "\n".join([play_text, str(worker.get("text") or ""), log_text])
    result["play_summary"] = runner.classify_play_output(combined_text)
    result["play_output_pass"] = runner.play_output_pass(result["play_summary"])
    result["status_after_play"] = runner.capture_audio_status(out_dir, steps, "after-standalone-chime")
    dmesg_tail = runner.base.run_serial_step(
        out_dir,
        steps,
        "candidate-dmesg-audio-standalone-chime-tail",
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
            "audio_chime": chime_command(args),
            "card_poll": ["audio", "adsp-status"],
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
        f"# Native Init {runner.CYCLE} Audio Chime Bundled SET-cal Live Handoff",
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
        "## Standalone Bundled Evidence",
        "",
        f"- Native command: `{result.get('play_command')}`",
        f"- Host artifact deployment performed: `{int(bool(result.get('host_artifact_deploy_performed')))}`",
        f"- Bundled manifest path: `{BUNDLED_REMOTE_MANIFEST}`",
        f"- Bundled root: `{BUNDLED_REMOTE_ROOT}`",
        f"- Card ready after play start: `{int(bool(result.get('card_ready_after_play_start')))}` after `{card_wait.get('attempts')}` polls",
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
        f"- PCM write/done: `{int(bool(play_summary.get('pcm_write_attempted')))} / {int(bool(play_summary.get('pcm_done')))}`",
        f"- Safety amplitude/duration cap: `{int(bool(play_summary.get('safety_amplitude')))} / {int(bool(play_summary.get('safety_duration')))}`",
        "",
        "## Safety",
        "",
        "- Flash path: `workspace/public/src/scripts/revalidation/native_init_flash.py`.",
        "- Only the boot partition is flashed; no runtime ACDB files are copied from the host in this unit.",
        "- No forbidden partitions are touched.",
        "- `audio chime` uses amplitude `80` milli and duration `1200` ms by default, below the source cap.",
        "- Public report is metadata-only; private raw command transcripts stay under `workspace/private/`.",
        "",
    ])


runner.decision = decision
runner.preflight_state = preflight_state
runner.parse_args = parse_args
runner.play_command = chime_command
runner.run_play_sequence = run_play_sequence
runner.dry_run_payload = dry_run_payload
runner.render_report = render_report


if __name__ == "__main__":
    raise SystemExit(runner.main())
