#!/usr/bin/env python3
"""V2920 live validation for Bad Apple Player HUD with bounded PCM-file audio.

V2919 proved the full-song 480x360 Bad Apple stream can be played from the
SHA-addressed SD cache using the Player HUD layout. This unit keeps the already
resident V2917 image, uploads the matching private 48 kHz stereo S16LE audio
asset to the native audio runtime prefix, starts bounded native PCM-file
playback, then plays a 10 second Player HUD slice anchored to the audio worker
status file.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import native_audio_tinyalsa_inventory_live_handoff_v2349 as tiny_live
import native_av_pcm_video_corun_live_handoff_v2882 as av_live
import native_video_badapple_player_hud_live_handoff_v2919 as hud
import native_video_cache_av_sync_live_handoff_v2909 as av_sync

video_live = hud.video_live
base = video_live.base

RUN_ID = "V2920"
BUILD_TAG = "v2920-badapple-player-hud-av-live"
DECISION_PREFIX = "v2920-badapple-player-hud-av"
REPORT_PATH = video_live.ROOT / "docs/reports/NATIVE_INIT_V2920_BADAPPLE_PLAYER_HUD_AV_LIVE_2026-06-20.md"

CANDIDATE_VERSION = hud.CANDIDATE_VERSION
CANDIDATE_TAG = hud.CANDIDATE_TAG
PRESET_NAME = hud.PRESET_NAME
BADAPPLE_SHA256 = hud.BADAPPLE_SHA256
BADAPPLE_AUDIO_SHA256 = hud.BADAPPLE_AUDIO_SHA256
BADAPPLE_PLAY_FRAMES = 300
BADAPPLE_FORMAT = "mono1"

SYNC_STATUS_PATH = av_sync.SYNC_STATUS_PATH
SYNC_WAIT_MS = av_sync.SYNC_WAIT_MS
AUDIO_PROFILE = av_live.PROFILE
AUDIO_MANIFEST = av_live.BUNDLED_REMOTE_MANIFEST
AUDIO_DURATION_MS = 10000
AUDIO_AMPLITUDE_MILLI = 200
REMOTE_PLAY_LOG = av_live.REMOTE_PLAY_LOG
REMOTE_AUDIO_DIR = "/cache/a90-runtime/pkg/av/v2920/audio"
REMOTE_AUDIO_PCM = f"{REMOTE_AUDIO_DIR}/badapple.s16le"

video_live.RUN_ID = RUN_ID
video_live.BUILD_TAG = BUILD_TAG
video_live.REPORT_TITLE = "Native Init V2920 Bad Apple Player HUD A/V Live Validation"
video_live.DECISION_PREFIX = DECISION_PREFIX
video_live.CANDIDATE_VERSION = CANDIDATE_VERSION
video_live.CANDIDATE_TAG = CANDIDATE_TAG
video_live.REPORT_PATH = REPORT_PATH
video_live.REMOTE_DIR = "/mnt/sdext/a90/runtime/video/v2920"
video_live.REMOTE_MANIFEST = f"{video_live.REMOTE_DIR}/manifest.json"
video_live.REMOTE_STREAM = f"{video_live.REMOTE_DIR}/frames.a90vstr"
av_live.audio_live.REMOTE_DIR = REMOTE_AUDIO_DIR
av_live.audio_live.REMOTE_PCM = REMOTE_AUDIO_PCM


def now_slug() -> str:
    return datetime.now(timezone.utc).astimezone().strftime("%Y%m%d-%H%M%S")


def stdout_of(step: dict[str, Any] | None) -> str:
    return video_live.stdout_of(step)


def all_true(mapping: dict[str, Any]) -> bool:
    return all(bool(value) for value in mapping.values())


def preflight_state(args: argparse.Namespace) -> dict[str, Any]:
    state = hud.preflight_state(args)
    state.update({
        "run_id": RUN_ID,
        "resident_required": f"A90 Linux init {CANDIDATE_VERSION} ({CANDIDATE_TAG})",
        "remote_audio_dir": REMOTE_AUDIO_DIR,
        "remote_audio_pcm": REMOTE_AUDIO_PCM,
        "audio_duration_ms": AUDIO_DURATION_MS,
        "audio_amplitude_milli": AUDIO_AMPLITUDE_MILLI,
        "sync_status_path": SYNC_STATUS_PATH,
        "sync_wait_ms": SYNC_WAIT_MS,
        "play_frames": int(args.frames),
        "hard_boundary": [
            "no flash in this unit; V2917 must already be resident",
            "boot partition untouched",
            "Bad Apple raw frames/audio remain private and untracked",
            "audio PCM-file source is read-only and bounded to 10 seconds",
            "audio amplitude cap remains <=0.2",
            "KMS dumb-buffer/page-flip path only",
            "no Venus/GPU/raw DSI/backlight/PMIC/PWM/regulator/GPIO/GDSC writes",
        ],
    })
    return state


def preflight_ok(state: dict[str, Any]) -> bool:
    return bool(hud.preflight_ok(state))


def install_audio_pcm(args: argparse.Namespace,
                      out_dir: Path,
                      steps: list[dict[str, Any]]) -> dict[str, Any]:
    readiness = tiny_live.probe_transfer_readiness(args, out_dir, steps)
    selected = str(readiness.get("selected_transport") or "")
    control_channel = "tcpctl" if selected == "tcpctl" else "bridge"
    result: dict[str, Any] = {
        "transfer_readiness": readiness,
        "selected_transport": selected,
        "control_channel": control_channel,
        "remote": REMOTE_AUDIO_PCM,
        "expected_sha256": BADAPPLE_AUDIO_SHA256,
        "cache_hit": False,
        "uploaded": False,
        "remote_sha_match": False,
    }
    base.run_serial_step(
        out_dir,
        steps,
        "resident-create-remote-audio-dir",
        ["run", "/bin/toybox", "mkdir", "-p", REMOTE_AUDIO_DIR],
        timeout=45.0,
        retry_unsafe=True,
    )
    probe = base.run_serial_step(
        out_dir,
        steps,
        "resident-audio-pcm-sha256-before-upload",
        ["run", "/bin/toybox", "sha256sum", REMOTE_AUDIO_PCM],
        timeout=60.0,
        retry_unsafe=True,
        allow_error=True,
    )
    result["pre_upload_sha_stdout_path"] = probe.get("stdout_path")
    if BADAPPLE_AUDIO_SHA256 in stdout_of(probe):
        result["cache_hit"] = True
        result["remote_sha_match"] = True
        return result

    install = base.run_step(
        out_dir,
        steps,
        "install-badapple-audio-pcm",
        tiny_live.install_command(
            args,
            hud.LOCAL_AUDIO,
            REMOTE_AUDIO_PCM,
            args.transfer_port + 7,
            control_channel=control_channel,
        ),
        timeout=args.transfer_timeout + 120.0,
    )
    result["install_stdout_path"] = install.get("stdout_path")
    result["uploaded"] = bool(install.get("ok"))
    remote_sha = base.run_serial_step(
        out_dir,
        steps,
        "resident-audio-pcm-sha256-after-upload",
        ["run", "/bin/toybox", "sha256sum", REMOTE_AUDIO_PCM],
        timeout=90.0,
        retry_unsafe=True,
        allow_error=True,
    )
    result["post_upload_sha_stdout_path"] = remote_sha.get("stdout_path")
    result["remote_sha_match"] = BADAPPLE_AUDIO_SHA256 in stdout_of(remote_sha)
    return result


def classify_play_with_sync(text: str, expected_frames: int) -> dict[str, Any]:
    summary = hud.classify_play(text, expected_frames)
    sync = av_sync.sync_summary(text)
    sync_ok = av_sync.sync_pass(sync)
    summary["sync"] = sync
    summary["sync_pass"] = sync_ok
    summary["pass_without_sync"] = bool(summary.get("pass"))
    summary["pass"] = bool(summary.get("pass")) and sync_ok
    return summary


def audio_pass_summary(audio_text: str) -> dict[str, Any]:
    summary = av_live.audio_live.classify_pcm_output(audio_text)
    return {
        "summary": summary,
        "pass": av_live.audio_live.pcm_output_pass(summary),
    }


def render_report(result: dict[str, Any]) -> str:
    install = result.get("runtime_install", {}) if isinstance(result.get("runtime_install"), dict) else {}
    audio_install = result.get("audio_install", {}) if isinstance(result.get("audio_install"), dict) else {}
    status = result.get("cache_status_summary", {}) if isinstance(result.get("cache_status_summary"), dict) else {}
    verify = result.get("cache_verify_summary", {}) if isinstance(result.get("cache_verify_summary"), dict) else {}
    play = result.get("cache_play_summary", {}) if isinstance(result.get("cache_play_summary"), dict) else {}
    sync = play.get("sync", {}) if isinstance(play.get("sync"), dict) else {}
    audio = result.get("audio_summary", {}) if isinstance(result.get("audio_summary"), dict) else {}
    audio_markers = audio.get("summary", {}) if isinstance(audio.get("summary"), dict) else {}
    return "\n".join([
        "# Native Init V2920 Bad Apple Player HUD A/V Live Validation",
        "",
        "## Summary",
        "",
        f"- Decision: `{result.get('decision')}`",
        f"- Result: `{int(bool(result.get('pass')))}`",
        f"- Resident candidate: `{CANDIDATE_VERSION}` / `{CANDIDATE_TAG}`",
        f"- Video SHA256: `{BADAPPLE_SHA256}`",
        f"- Audio SHA256: `{BADAPPLE_AUDIO_SHA256}`",
        f"- Slice: `{result.get('play_frames')}` frames / `{AUDIO_DURATION_MS}` ms audio",
        "- Device flash: `no` in this unit; V2917 was already resident.",
        "- Rollback: not required; no boot partition change was performed.",
        "",
        "## Runtime Assets",
        "",
        f"- Video cache dir: `{install.get('cache_dir')}`",
        f"- Video cache hit before upload: `{int(bool(install.get('cache_hit')))}`",
        f"- Video cache uploaded: `{int(bool(install.get('cache_uploaded')))}`",
        f"- Audio remote PCM: `{REMOTE_AUDIO_PCM}`",
        f"- Audio cache hit before upload: `{int(bool(audio_install.get('cache_hit')))}`",
        f"- Audio uploaded: `{int(bool(audio_install.get('uploaded')))}`",
        f"- Audio remote SHA matched: `{int(bool(audio_install.get('remote_sha_match')))}`",
        f"- Audio transfer: `{audio_install.get('selected_transport')}` control=`{audio_install.get('control_channel')}`",
        "",
        "## Command Results",
        "",
        f"- `video demo badapple status`: rc=`{result.get('cache_status_rc')}` summary=`{status}`",
        f"- `video demo badapple verify`: rc=`{result.get('cache_verify_rc')}` summary=`{verify}`",
        f"- `audio play --pcm-file`: rc=`{result.get('audio_execute_rc')}` worker_done=`{int(bool(result.get('audio_worker_done')))}` pass=`{int(bool(audio.get('pass')))}`",
        f"- `video demo badapple play --layout player-hud --sync-audio-status`: rc=`{result.get('cache_play_rc')}` pass=`{int(bool(play.get('pass')))}`",
        f"- Frame accounting: presented=`{play.get('presented')}` dropped=`{play.get('dropped_frames')}` accounted=`{play.get('accounted_frames')}`",
        f"- Layout markers: cache=`{int(bool(play.get('requested_layout_cache_marker')))}` stream=`{int(bool(play.get('stream_layout_marker')))}`",
        f"- Sync markers: `{sync}`",
        "",
        "## Audio Markers",
        "",
        *[f"- `{key}`: `{int(bool(value))}`" for key, value in sorted(audio_markers.items())],
        "",
        "## Evidence",
        "",
        f"- Result JSON: `{result.get('result_json')}`",
        f"- Output dir: `{result.get('out_dir')}`",
        f"- Cache play stdout: `{result.get('cache_play_stdout_path')}`",
        f"- Audio execute stdout: `{result.get('audio_execute_stdout_path')}`",
        f"- Audio worker status stdout: `{result.get('audio_worker_status_stdout_path')}`",
        f"- Audio worker log stdout: `{result.get('audio_worker_log_stdout_path')}`",
        "",
        "## Safety",
        "",
        "- Raw frames/audio remain private and untracked.",
        "- Audio uses the promoted internal-speaker-safe route with source-enforced amplitude/duration caps.",
        "- Video uses the existing KMS dumb-buffer/page-flip path and Player HUD layout.",
        "- No boot flash, forbidden partition write, Venus/GPU/raw DSI/backlight/PMIC/PWM/regulator/GPIO/GDSC path was used.",
        "",
    ])


def run_live(args: argparse.Namespace, out_dir: Path, state: dict[str, Any]) -> dict[str, Any]:
    steps: list[dict[str, Any]] = []
    result: dict[str, Any] = {
        "decision": f"{DECISION_PREFIX}-live-started",
        "pass": False,
        "out_dir": video_live.rel(out_dir),
        "preflight": state,
        "play_frames": int(args.frames),
        "steps": steps,
    }
    try:
        version = base.run_serial_step(out_dir, steps, "resident-version", ["version"], timeout=90.0, retry_unsafe=True)
        status = base.run_serial_step(out_dir, steps, "resident-status", ["status"], timeout=90.0, retry_unsafe=True)
        selftest = base.run_serial_step(out_dir, steps, "resident-selftest", ["selftest", "verbose"], timeout=120.0, retry_unsafe=True)
        video_status = base.run_serial_step(out_dir, steps, "resident-video-status", ["video", "status"], timeout=90.0, retry_unsafe=True)
        audio_status = base.run_serial_step(out_dir, steps, "resident-audio-status", ["audio", "status"], timeout=90.0, retry_unsafe=True)
        result["resident_version_ok"] = f"A90 Linux init {CANDIDATE_VERSION} ({CANDIDATE_TAG})" in stdout_of(version)
        result["resident_status_ok"] = bool(status.get("ok"))
        result["resident_selftest_fail0"] = video_live.selftest_step_ok(selftest)
        result["resident_video_status_player_hud"] = "--layout full|player-hud" in stdout_of(video_status)
        result["resident_video_status_sync"] = "--sync-audio-status" in stdout_of(video_status)
        result["resident_audio_status_ok"] = "audio.status.version=" in stdout_of(audio_status)
        if not (
            result["resident_version_ok"]
            and result["resident_status_ok"]
            and result["resident_selftest_fail0"]
            and result["resident_video_status_player_hud"]
            and result["resident_video_status_sync"]
            and result["resident_audio_status_ok"]
        ):
            result["decision"] = f"{DECISION_PREFIX}-resident-preflight-failed"
            raise RuntimeError("resident V2917 Player HUD/audio-sync health failed")

        fixture = hud.fixture_from_asset()
        result["fixture"] = fixture
        result["runtime_install"] = video_live.install_fixture(args, out_dir, steps, fixture)
        install = result["runtime_install"]
        if not (install.get("cache_hit") or install.get("cache_uploaded") or install.get("cache_adopted")):
            result["decision"] = f"{DECISION_PREFIX}-video-cache-seed-failed"
            raise RuntimeError("V2903 stream was not available in SHA-addressed SD cache")

        result["audio_install"] = install_audio_pcm(args, out_dir, steps)
        if not result["audio_install"].get("remote_sha_match"):
            result["decision"] = f"{DECISION_PREFIX}-audio-transfer-sha-mismatch"
            raise RuntimeError("Bad Apple audio PCM remote SHA mismatch")

        base.run_serial_step(out_dir, steps, "resident-hide-menu-before-badapple-av", ["hide"], timeout=45.0, allow_error=True, retry_unsafe=True)
        status_step = base.run_serial_step(out_dir, steps, "resident-video-demo-badapple-status", ["video", "demo", PRESET_NAME, "status"], timeout=120.0, allow_error=True, retry_unsafe=False)
        status_text = stdout_of(status_step)
        result["cache_status_rc"] = status_step.get("rc")
        result["cache_status_stdout_path"] = status_step.get("stdout_path")
        result["cache_status_summary"] = hud.cache_status_summary(status_text)
        result["cache_status_preset_summary"] = hud.preset_summary(status_text)
        result["cache_status_demo_summary"] = hud.demo_summary(status_text)
        if status_step.get("rc") != 0 or not all_true(result["cache_status_summary"]) or not all_true(result["cache_status_preset_summary"]) or not all_true(result["cache_status_demo_summary"]):
            result["decision"] = f"{DECISION_PREFIX}-cache-status-failed"
            raise RuntimeError("video demo badapple status did not emit required markers")

        verify_step = base.run_serial_step(out_dir, steps, "resident-video-demo-badapple-verify", ["video", "demo", PRESET_NAME, "verify"], timeout=600.0, allow_error=True, retry_unsafe=False)
        verify_text = stdout_of(verify_step)
        result["cache_verify_rc"] = verify_step.get("rc")
        result["cache_verify_stdout_path"] = verify_step.get("stdout_path")
        result["cache_verify_summary"] = hud.cache_verify_summary(verify_text)
        result["cache_verify_preset_summary"] = hud.preset_summary(verify_text)
        result["cache_verify_demo_summary"] = hud.demo_summary(verify_text)
        if verify_step.get("rc") != 0 or not all_true(result["cache_verify_summary"]) or not all_true(result["cache_verify_preset_summary"]) or not all_true(result["cache_verify_demo_summary"]):
            result["decision"] = f"{DECISION_PREFIX}-cache-verify-failed"
            raise RuntimeError("video demo badapple verify did not emit required markers")

        base.run_serial_step(
            out_dir,
            steps,
            "resident-clear-audio-play-status-before-badapple-av",
            ["run", "/bin/busybox", "rm", "-f", SYNC_STATUS_PATH, REMOTE_PLAY_LOG],
            timeout=45.0,
            retry_unsafe=True,
            allow_error=True,
        )
        audio_step = base.run_serial_step(
            out_dir,
            steps,
            "resident-audio-play-badapple-pcm-execute",
            [
                "audio", "play", AUDIO_PROFILE,
                "--mode", "listen",
                "--duration-ms", str(AUDIO_DURATION_MS),
                "--amplitude-milli", str(AUDIO_AMPLITUDE_MILLI),
                "--manifest", AUDIO_MANIFEST,
                "--pcm-file", REMOTE_AUDIO_PCM,
                "--execute",
            ],
            timeout=120.0,
            retry_unsafe=False,
            allow_error=True,
        )
        audio_execute_text = stdout_of(audio_step)
        result["audio_execute_rc"] = audio_step.get("rc")
        result["audio_execute_stdout_path"] = audio_step.get("stdout_path")
        result["audio_execute_elapsed_sec"] = audio_step.get("elapsed_sec")
        if audio_step.get("rc") != 0 or "audio.play.worker.started=1" not in audio_execute_text:
            result["decision"] = f"{DECISION_PREFIX}-audio-start-failed-before-video"
            raise RuntimeError("Bad Apple audio PCM-file worker did not start")

        play_step = base.run_serial_step(
            out_dir,
            steps,
            "resident-video-demo-badapple-player-hud-av-play",
            [
                "video", "demo", PRESET_NAME, "play",
                "--trust-cache",
                "--frames", str(args.frames),
                "--present", "pageflip",
                "--layout", "player-hud",
                "--sync-audio-status", SYNC_STATUS_PATH,
                "--sync-wait-ms", str(SYNC_WAIT_MS),
            ],
            timeout=args.stream_timeout,
            allow_error=True,
            retry_unsafe=False,
        )
        play_text = stdout_of(play_step)
        result["cache_play_rc"] = play_step.get("rc")
        result["cache_play_stdout_path"] = play_step.get("stdout_path")
        result["cache_play_elapsed_sec"] = play_step.get("elapsed_sec")
        result["cache_play_summary"] = classify_play_with_sync(play_text, int(args.frames))

        worker = av_live.audio_live.wait_for_worker_done(out_dir, steps, 180.0)
        result["audio_worker_done"] = bool(worker.get("done"))
        result["audio_worker_attempts"] = worker.get("attempts")
        result["audio_worker_status_stdout_path"] = worker.get("stdout_path")
        log_step = base.run_serial_step(out_dir, steps, "resident-audio-worker-log", ["run", "/bin/busybox", "cat", REMOTE_PLAY_LOG], timeout=45.0, retry_unsafe=True, allow_error=True)
        audio_log_text = stdout_of(log_step)
        result["audio_worker_log_stdout_path"] = log_step.get("stdout_path")
        audio_text = "\n".join([audio_execute_text, str(worker.get("text") or ""), audio_log_text])
        result["audio_summary"] = audio_pass_summary(audio_text)

        if (
            play_step.get("rc") != 0
            or not result["cache_play_summary"].get("pass")
            or not result["audio_summary"].get("pass")
            or not result["audio_worker_done"]
        ):
            result["decision"] = f"{DECISION_PREFIX}-marker-failed"
            raise RuntimeError("Bad Apple Player HUD A/V run did not emit required pass markers")

        after = base.run_serial_step(out_dir, steps, "resident-selftest-after-badapple-av", ["selftest", "verbose"], timeout=120.0, retry_unsafe=True)
        result["resident_selftest_after_badapple_av_fail0"] = video_live.selftest_step_ok(after)
        if not result["resident_selftest_after_badapple_av_fail0"]:
            result["decision"] = f"{DECISION_PREFIX}-post-play-selftest-failed"
            raise RuntimeError("post Bad Apple A/V selftest did not report fail=0")
        result["decision"] = f"{DECISION_PREFIX}-live-pass"
        result["pass"] = True
    except Exception as exc:
        result.setdefault("decision", f"{DECISION_PREFIX}-live-blocked")
        if result["decision"] == f"{DECISION_PREFIX}-live-started":
            result["decision"] = f"{DECISION_PREFIX}-live-blocked"
        result["error_type"] = type(exc).__name__
        result["error"] = str(exc)
    finally:
        result["result_json"] = video_live.rel(out_dir / "result.json")
        video_live.write_json(out_dir / "result.json", result)
        REPORT_PATH.write_text(render_report(result), encoding="utf-8")
    return result


def parse_args() -> argparse.Namespace:
    parser = hud.parse_args()
    parser.frames = BADAPPLE_PLAY_FRAMES if parser.frames == hud.BADAPPLE_PLAY_FRAMES else parser.frames
    parser.width = 480
    parser.height = 360
    parser.stride = 60
    parser.stream_format = BADAPPLE_FORMAT
    parser.pattern = "checker"
    parser.fps_num = 30
    parser.fps_den = 1
    parser.disable_cache = False
    parser.adopt_legacy_cache = False
    parser.require_cache_hit = False
    parser.chunk_large_streams = True
    parser.stream_chunk_bytes = min(int(parser.stream_chunk_bytes), 64 * 1024 * 1024)
    parser.stream_timeout = max(float(parser.stream_timeout), 180.0)
    parser.transfer_timeout = max(float(parser.transfer_timeout), 900.0)
    return parser


def dry_run_payload(args: argparse.Namespace, state: dict[str, Any]) -> dict[str, Any]:
    return {
        "decision": f"{DECISION_PREFIX}-dry-run" if preflight_ok(state) else f"{DECISION_PREFIX}-preflight-failed",
        "ok": preflight_ok(state),
        "preflight": state,
        "commands": [
            "version/status/selftest/video status/audio status",
            f"seed {BADAPPLE_SHA256} into {video_live.remote_cache_dir(BADAPPLE_SHA256)}",
            f"install {hud.LOCAL_AUDIO} to {REMOTE_AUDIO_PCM}",
            f"video demo {PRESET_NAME} status",
            f"video demo {PRESET_NAME} verify",
            f"audio play {AUDIO_PROFILE} --duration-ms {AUDIO_DURATION_MS} --amplitude-milli {AUDIO_AMPLITUDE_MILLI} --pcm-file {REMOTE_AUDIO_PCM} --execute",
            f"video demo {PRESET_NAME} play --trust-cache --frames {args.frames} --present pageflip --layout player-hud --sync-audio-status {SYNC_STATUS_PATH} --sync-wait-ms {SYNC_WAIT_MS}",
        ],
    }


def main() -> int:
    args = parse_args()
    out_dir = video_live.ROOT / f"workspace/private/runs/video/{BUILD_TAG}-{now_slug()}"
    out_dir.mkdir(parents=True, exist_ok=True)
    state = preflight_state(args)
    if not args.live:
        payload = dry_run_payload(args, state)
        video_live.write_json(out_dir / "dry_run.json", payload)
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0 if payload["ok"] else 1
    if not preflight_ok(state):
        payload = {"decision": f"{DECISION_PREFIX}-preflight-failed", "pass": False, "preflight": state, "out_dir": video_live.rel(out_dir)}
        video_live.write_json(out_dir / "result.json", payload)
        REPORT_PATH.write_text(render_report(payload), encoding="utf-8")
        print(json.dumps({"decision": payload["decision"], "pass": False, "out_dir": video_live.rel(out_dir)}, indent=2, sort_keys=True))
        return 1
    result = run_live(args, out_dir, state)
    print(json.dumps({
        "decision": result.get("decision"),
        "pass": bool(result.get("pass")),
        "out_dir": video_live.rel(out_dir),
        "resident_selftest_after_badapple_av_fail0": result.get("resident_selftest_after_badapple_av_fail0"),
    }, indent=2, sort_keys=True))
    return 0 if result.get("pass") else 1


if __name__ == "__main__":
    raise SystemExit(main())
