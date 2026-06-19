#!/usr/bin/env python3
"""V2912 live validation for named SD video-cache preset playback with audio sync.

V2910 added ``video cache preset badapple-scale`` and V2911 built it
into a flashable image. This runner flashes V2911, verifies the existing
V2900 Bad-Apple-scale SD cache through the named preset, starts bounded
native audio playback, then plays a 10 second page-flip slice from the
trusted preset cache anchored to the audio worker status file. It then
rolls back to v2321.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import native_av_pcm_video_corun_live_handoff_v2882 as av_live
import native_video_cache_command_live_handoff_v2906 as v2906

video_live = v2906.video_live
base = video_live.base

RUN_ID = "V2912"
BUILD_TAG = "v2912-video-cache-preset-live"
REPORT_TITLE = "Native Init V2912 Video Cache Preset Live Validation"
DECISION_PREFIX = "v2912-video-cache-preset"
CANDIDATE_IMAGE = video_live.ROOT / "workspace/private/inputs/boot_images/boot_linux_v2911_video_cache_preset.img"
CANDIDATE_VERSION = "0.10.36"
CANDIDATE_TAG = "v2911-video-cache-preset"
CANDIDATE_SHA256 = "6a91bb594f3208dbb41440e82a8a60cd86515fa2fddfaddb433f29c122292da3"
REPORT_PATH = video_live.ROOT / "docs/reports/NATIVE_INIT_V2912_VIDEO_CACHE_PRESET_LIVE_2026-06-20.md"

FIXTURE_SHA256 = v2906.FIXTURE_SHA256
FIXTURE_FRAMES_TOTAL = v2906.FIXTURE_FRAMES
FIXTURE_SYNC_FRAMES = 300
FIXTURE_FORMAT = "mono1"
PRESET_NAME = "badapple-scale"
SYNC_STATUS_PATH = "/cache/a90-audio-play/status.txt"
SYNC_WAIT_MS = 90000
AUDIO_PROFILE = av_live.PROFILE
AUDIO_MANIFEST = av_live.BUNDLED_REMOTE_MANIFEST
AUDIO_DURATION_MS = 10000
AUDIO_AMPLITUDE_MILLI = 80
REMOTE_PLAY_LOG = av_live.REMOTE_PLAY_LOG


def configure_globals() -> None:
    video_live.RUN_ID = RUN_ID
    video_live.BUILD_TAG = BUILD_TAG
    video_live.REPORT_TITLE = REPORT_TITLE
    video_live.DECISION_PREFIX = DECISION_PREFIX
    video_live.CANDIDATE_IMAGE = CANDIDATE_IMAGE
    video_live.CANDIDATE_VERSION = CANDIDATE_VERSION
    video_live.CANDIDATE_TAG = CANDIDATE_TAG
    video_live.CANDIDATE_SHA256 = CANDIDATE_SHA256
    video_live.REPORT_PATH = REPORT_PATH
    video_live.REMOTE_DIR = "/mnt/sdext/a90/runtime/video/v2912"
    video_live.REMOTE_MANIFEST = f"{video_live.REMOTE_DIR}/manifest.json"
    video_live.REMOTE_STREAM = f"{video_live.REMOTE_DIR}/frames.a90vstr"


def stdout_of(step: dict[str, Any]) -> str:
    return video_live.stdout_of(step)


def marker_int(text: str, marker: str) -> int | None:
    match = re.search(rf"(?:^|\b){re.escape(marker)}=(-?\d+)\b", text, re.MULTILINE)
    if not match:
        return None
    try:
        return int(match.group(1))
    except ValueError:
        return None


def all_true(mapping: dict[str, Any]) -> bool:
    return all(bool(value) for value in mapping.values())


def trust_cache_summary(text: str) -> dict[str, Any]:
    return {
        "trust_cache": "video.cache.play.trust_cache=1" in text,
        "sha_checked_zero": "video.cache.verify.sha256_checked=0" in text,
        "sha_match_zero": "video.cache.verify.sha256_match=0" in text,
        "actual_not_checked": "video.cache.verify.actual_sha256=trust-cache-not-checked" in text,
        "default_verify_not_repeated": f"video.cache.verify.actual_sha256={FIXTURE_SHA256}" not in text,
    }


def preset_summary(text: str) -> dict[str, Any]:
    return {
        "preset": f"video.cache.preset={PRESET_NAME}" in text,
        "asset_id": "video.cache.preset.asset_id=v2874-synthetic-mono1-checker-6501f" in text,
        "sha256": f"video.cache.preset.sha256={FIXTURE_SHA256}" in text,
    }


def sync_summary(text: str) -> dict[str, Any]:
    requested = marker_int(text, "video.cache.play.requested_audio_sync")
    enabled = marker_int(text, "video.stream.audio_sync.enabled")
    ready = marker_int(text, "video.stream.audio_sync.ready")
    wait_ms = marker_int(text, "video.stream.audio_sync.wait_ms")
    ready_elapsed_ms = marker_int(text, "video.stream.audio_sync.ready_elapsed_ms")
    listen_begin_ns = marker_int(text, "video.stream.audio_sync.listen_begin_ns")
    anchor_age_ns = marker_int(text, "video.stream.audio_sync.anchor_age_ns")
    sample_rate = marker_int(text, "video.stream.audio_sync.sample_rate")
    frame_bytes = marker_int(text, "video.stream.audio_sync.frame_bytes")
    total_frames = marker_int(text, "video.stream.audio_sync.total_frames")
    expected_duration_ns = marker_int(text, "video.stream.audio_sync.expected_duration_ns")
    first_presented_frame = marker_int(text, "video.stream.audio_sync.first_presented_frame")
    initial_drop_late_ns = marker_int(text, "video.stream.audio_sync.initial_drop_late_ns")
    return {
        "requested": requested,
        "enabled": enabled,
        "ready": ready,
        "wait_ms": wait_ms,
        "ready_elapsed_ms": ready_elapsed_ms,
        "listen_begin_ns": listen_begin_ns,
        "anchor_age_ns": anchor_age_ns,
        "sample_rate": sample_rate,
        "frame_bytes": frame_bytes,
        "total_frames": total_frames,
        "expected_duration_ns": expected_duration_ns,
        "first_presented_frame": first_presented_frame,
        "initial_drop_late_ns": initial_drop_late_ns,
        "status_path_marker": f"video.stream.audio_sync.status_path={SYNC_STATUS_PATH}" in text,
        "drop_policy_marker": "video.stream.audio_sync.drop_policy=late-frame-skip" in text,
        "requested_ok": requested == 1,
        "enabled_ok": enabled == 1,
        "ready_ok": ready == 1,
        "wait_ok": wait_ms == SYNC_WAIT_MS,
        "listen_begin_present": listen_begin_ns is not None and listen_begin_ns > 0,
        "anchor_age_present": anchor_age_ns is not None and anchor_age_ns >= 0,
        "geometry_ok": sample_rate == 48000 and frame_bytes == 4,
        "duration_present": expected_duration_ns is not None and expected_duration_ns > 0 and total_frames is not None and total_frames > 0,
        "first_presented_frame_present": first_presented_frame is not None and first_presented_frame >= 0,
        "initial_drop_late_present": initial_drop_late_ns is not None and initial_drop_late_ns >= 0,
    }


def sync_pass(summary: dict[str, Any]) -> bool:
    required = (
        "requested_ok",
        "enabled_ok",
        "ready_ok",
        "wait_ok",
        "status_path_marker",
        "drop_policy_marker",
        "listen_begin_present",
        "anchor_age_present",
        "geometry_ok",
        "duration_present",
        "first_presented_frame_present",
        "initial_drop_late_present",
    )
    return all(bool(summary.get(key)) for key in required)


def classify_cache_play(text: str) -> dict[str, Any]:
    stream = video_live.classify_stream_output(text, FIXTURE_SYNC_FRAMES, FIXTURE_FORMAT)
    presented = marker_int(text, "video.stream.presented") or 0
    dropped = marker_int(text, "video.stream.dropped_frames")
    flip_events = marker_int(text, "video.stream.flip_events") or 0
    if dropped is None:
        dropped = -1
    accounted = presented + max(dropped, 0)
    trust = trust_cache_summary(text)
    preset = preset_summary(text)
    sync = sync_summary(text)
    requested_present = "video.cache.play.requested_present=pageflip" in text
    stream.update({
        "presented": presented,
        "dropped_frames": dropped,
        "accounted_frames": accounted,
        "frame_accounting_ok": dropped >= 0 and accounted == FIXTURE_SYNC_FRAMES and presented >= 1,
        "flip_accounting_ok": flip_events == presented,
        "requested_present_cache_marker": requested_present,
        "trust_cache": trust,
        "trust_cache_pass": all_true(trust),
        "preset": preset,
        "preset_pass": all_true(preset),
        "sync": sync,
        "sync_pass": sync_pass(sync),
        "pass": bool(
            requested_present
            and all_true(preset)
            and all_true(trust)
            and sync_pass(sync)
            and dropped >= 0
            and accounted == FIXTURE_SYNC_FRAMES
            and presented >= 1
            and flip_events == presented
            and stream.get("cadence_target_present")
            and stream.get("pixel_format")
            and stream.get("present_pageflip")
            and stream.get("path_ok")
        ),
    })
    return stream


def audio_pass_summary(audio_text: str) -> dict[str, Any]:
    summary = av_live.audio_live.classify_pcm_output(audio_text)
    generic_required = (
        "worker_started",
        "worker_done",
        "integrated_done",
        "pcm_done",
        "listen_begin",
        "listen_end",
        "pcm_write_attempted",
        "route_apply_ok",
        "route_reset_ok",
        "safety_amplitude",
        "safety_duration",
        "setcal_all_set",
        "setcal_deallocated",
    )
    return {
        "summary": summary,
        "pass": all(bool(summary.get(key)) for key in generic_required),
        "required": list(generic_required),
    }


def render_report(result: dict[str, Any]) -> str:
    status = result.get("cache_status_summary", {}) if isinstance(result.get("cache_status_summary"), dict) else {}
    verify = result.get("cache_verify_summary", {}) if isinstance(result.get("cache_verify_summary"), dict) else {}
    play = result.get("cache_play_summary", {}) if isinstance(result.get("cache_play_summary"), dict) else {}
    sync = play.get("sync", {}) if isinstance(play.get("sync"), dict) else {}
    trust = play.get("trust_cache", {}) if isinstance(play.get("trust_cache"), dict) else {}
    audio = result.get("audio_summary", {}) if isinstance(result.get("audio_summary"), dict) else {}
    classifier_fix = result.get("posthoc_classifier_fix", {}) if isinstance(result.get("posthoc_classifier_fix"), dict) else {}
    classifier_lines = [
        "## Classifier Note",
        "",
        f"- Posthoc classifier fix applied: `{int(bool(classifier_fix))}`",
        f"- Reason: `{classifier_fix.get('reason', 'n/a')}`",
        f"- Cache/audio pass after fix: `{int(bool(classifier_fix.get('cache_play_pass')))}` / `{int(bool(classifier_fix.get('audio_pass')))}`",
        "",
    ] if classifier_fix else []
    return "\n".join([
        "# Native Init V2912 Video Cache Preset Live Validation",
        "",
        "## Summary",
        "",
        f"- Decision: `{result.get('decision')}`",
        f"- Result before rollback: `{int(bool(result.get('pass')))}`",
        f"- Candidate: `{CANDIDATE_TAG}` / `{CANDIDATE_VERSION}` / `{CANDIDATE_SHA256}`",
        f"- Preset: `{PRESET_NAME}`",
        f"- Resolved cache SHA: `{FIXTURE_SHA256}`",
        f"- Slice frames: `{FIXTURE_SYNC_FRAMES}` of `{FIXTURE_FRAMES_TOTAL}`",
        f"- Rollback attempted: `{int(bool(result.get('rollback_attempted')))}`",
        f"- Rollback health: version_ok=`{int(bool(result.get('rollback_version_ok')))}` selftest_fail0=`{int(bool(result.get('rollback_selftest_fail0')))}`",
        "",
        "## Command Results",
        "",
        f"- `video cache preset {PRESET_NAME} status`: rc=`{result.get('cache_status_rc')}`, summary=`{status}`",
        f"- `video cache preset {PRESET_NAME} verify`: rc=`{result.get('cache_verify_rc')}`, summary=`{verify}`",
        f"- `audio play`: rc=`{result.get('audio_execute_rc')}`, worker_done=`{int(bool(result.get('audio_worker_done')))}`, pass=`{int(bool(audio.get('pass')))}`",
        f"- `video cache preset {PRESET_NAME} play --trust-cache --sync-audio-status`: rc=`{result.get('cache_play_rc')}`, pass=`{int(bool(play.get('pass')))}`",
        f"- Preset markers: `{play.get('preset', {})}`",
        f"- Trust markers: `{trust}`",
        f"- Sync markers: `{sync}`",
        f"- Frame accounting: presented=`{play.get('presented')}` dropped=`{play.get('dropped_frames')}` accounted=`{play.get('accounted_frames')}`",
        "",
        "## Evidence Paths",
        "",
        f"- Result JSON: `{result.get('result_json', 'workspace/private run dir')}`",
        f"- Cache status stdout: `{result.get('cache_status_stdout_path')}`",
        f"- Cache verify stdout: `{result.get('cache_verify_stdout_path')}`",
        f"- Audio execute stdout: `{result.get('audio_execute_stdout_path')}`",
        f"- Audio worker status stdout: `{result.get('audio_worker_status_stdout_path')}`",
        f"- Audio worker log stdout: `{result.get('audio_worker_log_stdout_path')}`",
        f"- Cache play stdout: `{result.get('cache_play_stdout_path')}`",
        "",
        "## Interpretation",
        "",
        "- This validates the intended fast repeat-test pattern through a named preset: full cache SHA verify once, then explicit trusted preset playback for the A/V-sync slice.",
        "- `--trust-cache` is accepted only because `video cache preset badapple-scale verify` succeeded earlier in the same run; the playback log must show preset markers, `sha256_checked=0`, and `trust-cache-not-checked`.",
        "- Video remains the existing KMS dumb-buffer/page-flip path; audio remains the bounded internal-speaker-safe route.",
        "",
        *classifier_lines,
        "## Safety",
        "",
        "- Flash path: `workspace/public/src/scripts/revalidation/native_init_flash.py`.",
        "- Persistent write scope: boot partition only; runtime audio/video files remain temporary/private.",
        "- No Venus/GPU/raw DSI/panel init/backlight/PMIC/PWM/regulator/GPIO/GDSC path was used.",
        "- Rollback target: `v2321-usb-clean-identity-rodata`.",
        "",
    ])


def run_live(args: Any, out_dir: Path, state: dict[str, Any]) -> dict[str, Any]:
    steps: list[dict[str, Any]] = []
    candidate_flash_attempted = False
    candidate_flash_ok = False
    result: dict[str, Any] = {
        "decision": f"{DECISION_PREFIX}-live-started",
        "pass": False,
        "preflight": state,
        "steps": steps,
        "rollback_attempted": False,
        "rollback_version_ok": False,
        "rollback_selftest_fail0": False,
    }
    try:
        fixture = v2906.generate_cached_fixture(args, out_dir, steps)
        result["fixture"] = fixture
        video_live.base.run_step(
            out_dir,
            steps,
            "verify-current-v2321",
            video_live.flash_command(video_live.ROLLBACK_IMAGE, video_live.ROLLBACK_VERSION, video_live.ROLLBACK_SHA256, from_native=False) + ["--verify-only"],
            timeout=args.flash_timeout,
        )
        candidate_flash_attempted = True
        flash = video_live.base.run_step(
            out_dir,
            steps,
            f"flash-{CANDIDATE_TAG}",
            video_live.flash_command(CANDIDATE_IMAGE, CANDIDATE_VERSION, CANDIDATE_SHA256, from_native=True),
            timeout=args.flash_timeout,
        )
        candidate_flash_ok = flash.get("rc") == 0
        version = video_live.base.run_serial_step(out_dir, steps, "candidate-version", ["version"], timeout=90.0, retry_unsafe=True)
        video_live.base.run_serial_step(out_dir, steps, "candidate-status", ["status"], timeout=90.0, retry_unsafe=True)
        selftest = video_live.base.run_serial_step(out_dir, steps, "candidate-selftest", ["selftest", "verbose"], timeout=120.0, retry_unsafe=True)
        video_status = video_live.base.run_serial_step(out_dir, steps, "candidate-video-status", ["video", "status"], timeout=90.0, retry_unsafe=True)
        audio_status = video_live.base.run_serial_step(out_dir, steps, "candidate-audio-status", ["audio", "status"], timeout=90.0, retry_unsafe=True)
        result["candidate_version_ok"] = CANDIDATE_VERSION in stdout_of(version)
        result["candidate_selftest_fail0"] = video_live.selftest_step_ok(selftest)
        result["candidate_video_status_trust_marker"] = "--trust-cache" in stdout_of(video_status)
        result["candidate_audio_status_ok"] = "audio.status.core.native_play_gate=closed" in stdout_of(audio_status)
        if not (result["candidate_version_ok"] and result["candidate_selftest_fail0"] and result["candidate_video_status_trust_marker"] and result["candidate_audio_status_ok"]):
            result["decision"] = f"{DECISION_PREFIX}-candidate-health-failed-before-cache-av"
            raise RuntimeError("candidate health/video/audio status did not pass")

        result["runtime_install"] = video_live.install_fixture(args, out_dir, steps, fixture)
        if not result["runtime_install"].get("cache_hit"):
            result["decision"] = f"{DECISION_PREFIX}-required-cache-hit-missing-before-cache-av"
            raise RuntimeError("required SHA-addressed video cache hit was missing")

        video_live.base.run_serial_step(out_dir, steps, "candidate-hide-menu-before-cache-av", ["hide"], timeout=45.0, allow_error=True, retry_unsafe=True)
        status = video_live.base.run_serial_step(out_dir, steps, "candidate-video-cache-preset-status", ["video", "cache", "preset", PRESET_NAME, "status"], timeout=120.0, allow_error=True, retry_unsafe=False)
        status_text = stdout_of(status)
        result["cache_status_rc"] = status.get("rc")
        result["cache_status_stdout_path"] = status.get("stdout_path")
        result["cache_status_summary"] = v2906.cache_status_summary(status_text)
        result["cache_status_preset_summary"] = preset_summary(status_text)
        if status.get("rc") != 0 or not all_true(result["cache_status_summary"]) or not all_true(result["cache_status_preset_summary"]):
            result["decision"] = f"{DECISION_PREFIX}-cache-status-failed-before-rollback"
            raise RuntimeError("video cache preset status did not emit required markers")

        verify = video_live.base.run_serial_step(out_dir, steps, "candidate-video-cache-preset-verify", ["video", "cache", "preset", PRESET_NAME, "verify"], timeout=420.0, allow_error=True, retry_unsafe=False)
        verify_text = stdout_of(verify)
        result["cache_verify_rc"] = verify.get("rc")
        result["cache_verify_stdout_path"] = verify.get("stdout_path")
        result["cache_verify_summary"] = v2906.cache_verify_summary(verify_text)
        result["cache_verify_preset_summary"] = preset_summary(verify_text)
        if verify.get("rc") != 0 or not all_true(result["cache_verify_summary"]) or not all_true(result["cache_verify_preset_summary"]):
            result["decision"] = f"{DECISION_PREFIX}-cache-verify-failed-before-rollback"
            raise RuntimeError("video cache preset verify did not emit required markers")

        video_live.base.run_serial_step(out_dir, steps, "candidate-clear-audio-play-status-before-cache-av", ["run", "/bin/busybox", "rm", "-f", SYNC_STATUS_PATH, REMOTE_PLAY_LOG], timeout=45.0, retry_unsafe=True, allow_error=True)
        audio_command = [
            "audio", "play", AUDIO_PROFILE,
            "--mode", "listen",
            "--duration-ms", str(AUDIO_DURATION_MS),
            "--amplitude-milli", str(AUDIO_AMPLITUDE_MILLI),
            "--manifest", AUDIO_MANIFEST,
            "--execute",
        ]
        audio_step = video_live.base.run_serial_step(out_dir, steps, "candidate-audio-play-execute", audio_command, timeout=120.0, retry_unsafe=False, allow_error=True)
        audio_execute_text = stdout_of(audio_step)
        result["audio_execute_rc"] = audio_step.get("rc")
        result["audio_execute_stdout_path"] = audio_step.get("stdout_path")
        result["audio_execute_elapsed_sec"] = audio_step.get("elapsed_sec")
        if audio_step.get("rc") != 0 or "audio.play.worker.started=1" not in audio_execute_text:
            result["decision"] = f"{DECISION_PREFIX}-audio-start-failed-before-video"
            raise RuntimeError("audio worker did not start")

        play = video_live.base.run_serial_step(
            out_dir,
            steps,
            "candidate-video-cache-preset-play-trust-audio-sync",
            [
                "video", "cache", "preset", PRESET_NAME, "play",
                "--trust-cache",
                "--frames", str(FIXTURE_SYNC_FRAMES),
                "--present", "pageflip",
                "--sync-audio-status", SYNC_STATUS_PATH,
                "--sync-wait-ms", str(SYNC_WAIT_MS),
            ],
            timeout=args.stream_timeout,
            allow_error=True,
            retry_unsafe=False,
        )
        play_text = stdout_of(play)
        result["cache_play_rc"] = play.get("rc")
        result["cache_play_stdout_path"] = play.get("stdout_path")
        result["cache_play_elapsed_sec"] = play.get("elapsed_sec")
        result["cache_play_summary"] = classify_cache_play(play_text)

        worker = av_live.audio_live.wait_for_worker_done(out_dir, steps, 180.0)
        result["audio_worker_done"] = bool(worker.get("done"))
        result["audio_worker_attempts"] = worker.get("attempts")
        result["audio_worker_status_stdout_path"] = worker.get("stdout_path")
        log_step = video_live.base.run_serial_step(out_dir, steps, "candidate-audio-worker-log", ["run", "/bin/busybox", "cat", REMOTE_PLAY_LOG], timeout=45.0, retry_unsafe=True, allow_error=True)
        audio_log_text = stdout_of(log_step)
        result["audio_worker_log_stdout_path"] = log_step.get("stdout_path")
        audio_text = "\n".join([audio_execute_text, str(worker.get("text") or ""), audio_log_text])
        result["audio_summary"] = audio_pass_summary(audio_text)

        if play.get("rc") != 0 or not result["cache_play_summary"].get("pass") or not result["audio_summary"].get("pass") or not result["audio_worker_done"]:
            result["decision"] = f"{DECISION_PREFIX}-cache-av-sync-marker-failed-before-rollback"
            raise RuntimeError("trusted cache A/V sync run did not emit required pass markers")

        after = video_live.base.run_serial_step(out_dir, steps, "candidate-selftest-after-cache-av", ["selftest", "verbose"], timeout=120.0, retry_unsafe=True)
        result["candidate_selftest_after_cache_av_fail0"] = video_live.selftest_step_ok(after)
        if not result["candidate_selftest_after_cache_av_fail0"]:
            result["decision"] = f"{DECISION_PREFIX}-post-cache-av-selftest-failed"
            raise RuntimeError("candidate post-cache-av selftest did not report fail=0")
        result["decision"] = f"{DECISION_PREFIX}-live-pass-before-rollback"
        result["pass"] = True
    except Exception as exc:
        result.setdefault("decision", f"{DECISION_PREFIX}-live-blocked")
        if result["decision"] == f"{DECISION_PREFIX}-live-started":
            result["decision"] = f"{DECISION_PREFIX}-live-blocked"
        result["error_type"] = type(exc).__name__
        result["error"] = str(exc)
    finally:
        if candidate_flash_attempted:
            result["rollback_attempted"] = True
            rollback = video_live.base.rollback_v2321(out_dir, steps, from_native=candidate_flash_ok, timeout=args.flash_timeout)
            result["rollback_step_ok"] = bool(rollback.get("success"))
            result["rollback_attempts"] = rollback.get("attempts", [])
            result["rollback_recovery_fallback_used"] = bool(rollback.get("used_recovery_fallback"))
            if rollback.get("success"):
                rollback_version = video_live.base.run_serial_step(out_dir, steps, "rollback-version", ["version"], timeout=90.0, retry_unsafe=True, allow_error=True)
                rollback_selftest = video_live.base.run_serial_step(out_dir, steps, "rollback-selftest", ["selftest", "verbose"], timeout=120.0, retry_unsafe=True, allow_error=True)
                result["rollback_version_ok"] = video_live.ROLLBACK_VERSION in stdout_of(rollback_version)
                result["rollback_selftest_fail0"] = video_live.selftest_step_ok(rollback_selftest)
        result["result_json"] = video_live.rel(out_dir / "result.json")
        video_live.write_json(out_dir / "result.json", result)
        REPORT_PATH.write_text(render_report(result), encoding="utf-8")
    return result


def configure_args(args: Any) -> Any:
    args.stream_format = "mono1"
    args.pattern = "checker"
    args.width = 1080
    args.height = 2400
    args.stride = 135
    args.frames = FIXTURE_SYNC_FRAMES
    args.fps_num = 30
    args.fps_den = 1
    args.require_cache_hit = True
    args.disable_cache = False
    args.adopt_legacy_cache = False
    args.chunk_large_streams = False
    args.stream_timeout = max(args.stream_timeout, 180.0)
    return args


def dry_run_payload(args: Any, state: dict[str, Any]) -> dict[str, Any]:
    return {
        "decision": f"{DECISION_PREFIX}-live-dry-run" if video_live.preflight_ok(state) else f"{DECISION_PREFIX}-live-preflight-failed-no-flash",
        "ok": video_live.preflight_ok(state),
        "preflight": state,
        "fixed_cache": {
            "stream_sha256": FIXTURE_SHA256,
            "frames_total": FIXTURE_FRAMES_TOTAL,
            "slice_frames": FIXTURE_SYNC_FRAMES,
            "trust_cache_requires_prior_verify": True,
        },
        "commands": [
            f"video cache preset {PRESET_NAME} status",
            f"video cache preset {PRESET_NAME} verify",
            f"audio play {AUDIO_PROFILE} --mode listen --duration-ms {AUDIO_DURATION_MS} --amplitude-milli {AUDIO_AMPLITUDE_MILLI} --manifest {AUDIO_MANIFEST} --execute",
            f"video cache preset {PRESET_NAME} play --trust-cache --frames {FIXTURE_SYNC_FRAMES} --present pageflip --sync-audio-status {SYNC_STATUS_PATH} --sync-wait-ms {SYNC_WAIT_MS}",
        ],
    }


def main() -> int:
    configure_globals()
    args = configure_args(video_live.parse_args())
    out_dir = video_live.ROOT / f"workspace/private/runs/video/{BUILD_TAG}-{video_live.now_slug()}"
    out_dir.mkdir(parents=True, exist_ok=True)
    state = video_live.preflight_state(args)
    if not args.live:
        payload = dry_run_payload(args, state)
        video_live.write_json(out_dir / "dry_run.json", payload)
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0 if payload["ok"] else 1
    if not video_live.preflight_ok(state):
        payload = {
            "decision": f"{DECISION_PREFIX}-live-preflight-failed-no-flash",
            "pass": False,
            "preflight": state,
        }
        video_live.write_json(out_dir / "result.json", payload)
        REPORT_PATH.write_text(render_report(payload), encoding="utf-8")
        print(json.dumps({"decision": payload["decision"], "pass": False, "out_dir": video_live.rel(out_dir)}, indent=2, sort_keys=True))
        return 1
    result = run_live(args, out_dir, state)
    final_pass = bool(result.get("pass")) and bool(result.get("rollback_version_ok")) and bool(result.get("rollback_selftest_fail0"))
    print(json.dumps({
        "decision": result.get("decision"),
        "pass": final_pass,
        "out_dir": video_live.rel(out_dir),
        "rollback_version_ok": result.get("rollback_version_ok"),
        "rollback_selftest_fail0": result.get("rollback_selftest_fail0"),
    }, indent=2, sort_keys=True))
    return 0 if final_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
