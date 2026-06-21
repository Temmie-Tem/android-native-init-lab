#!/usr/bin/env python3
"""V3022 same-image live checkpoint for Bad Apple + Nyan demos.

V3021 built one patch-level checkpoint image that carries the current validated
Bad Apple and Nyan demo surfaces. This runner flashes that exact image once,
validates both demos in the same resident native-init image, then rolls back to
the v2321 clean USB-identity checkpoint.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import native_av_pcm_video_corun_live_handoff_v2882 as av_live
import native_video_badapple_player_hud_av_live_handoff_v2920 as badapple_av
import native_video_badapple_player_hud_live_handoff_v2919 as badapple_hud
import native_video_gray8_stream_live_handoff_v2893 as video_live
import native_video_nyan_real_preview_live_handoff_v2975 as nyan

base = video_live.base

RUN_ID = "V3022"
BUILD_TAG = "v3022-demo-checkpoint-badapple-nyan-live"
DECISION_PREFIX = "v3022-demo-checkpoint-badapple-nyan"
REPORT_PATH = video_live.ROOT / "docs/reports/NATIVE_INIT_V3022_DEMO_CHECKPOINT_BADAPPLE_NYAN_LIVE_2026-06-21.md"

CANDIDATE_IMAGE = video_live.ROOT / "workspace/private/inputs/boot_images/boot_linux_v3021_demo_checkpoint_badapple_nyan.img"
CANDIDATE_VERSION = "0.10.72"
CANDIDATE_TAG = "v3021-demo-checkpoint-badapple-nyan"
CANDIDATE_SHA256 = "c860d604e3c906abf61fdd2c9bd9cd12d1aef2c88c05be57677b472ad36ef0f7"

TWRP_DIR = video_live.ROOT / "workspace/private/inputs/firmware/twrp"
TWRP_RECOVERY_IMG = TWRP_DIR / "recovery.img"
TWRP_RECOVERY_TAR = TWRP_DIR / "twrp_recovery.tar"

BADAPPLE_FRAMES = badapple_hud.BADAPPLE_FRAMES_TOTAL
BADAPPLE_DURATION_MS = 232_090
BADAPPLE_AMPLITUDE_MILLI = 150
BADAPPLE_PCM_GAIN_MILLI = 780
BADAPPLE_PRESENT_MODE = "setcrtc"
BADAPPLE_LAYOUT = "player-hud"

NYAN_FRAMES = nyan.NYAN_FRAMES
SYNC_STATUS_PATH = nyan.SYNC_STATUS_PATH
SYNC_WAIT_MS = nyan.SYNC_WAIT_MS
SYNC_START_OFFSET_MS = nyan.SYNC_START_OFFSET_MS
REMOTE_PLAY_LOG = nyan.REMOTE_PLAY_LOG
AUDIO_PROFILE = nyan.AUDIO_PROFILE
AUDIO_MANIFEST = nyan.AUDIO_MANIFEST

video_live.RUN_ID = RUN_ID
video_live.BUILD_TAG = BUILD_TAG
video_live.REPORT_TITLE = "Native Init V3022 Demo Checkpoint Bad Apple + Nyan Live Validation"
video_live.DECISION_PREFIX = DECISION_PREFIX
video_live.CANDIDATE_IMAGE = CANDIDATE_IMAGE
video_live.CANDIDATE_VERSION = CANDIDATE_VERSION
video_live.CANDIDATE_TAG = CANDIDATE_TAG
video_live.CANDIDATE_SHA256 = CANDIDATE_SHA256
video_live.REPORT_PATH = REPORT_PATH
video_live.REMOTE_DIR = "/mnt/sdext/a90/runtime/video/v3022"
video_live.REMOTE_MANIFEST = f"{video_live.REMOTE_DIR}/manifest.json"
video_live.REMOTE_STREAM = f"{video_live.REMOTE_DIR}/frames.a90vstr"


def now_slug() -> str:
    return datetime.now(timezone.utc).astimezone().strftime("%Y%m%d-%H%M%S")


def stdout_of(step: dict[str, Any] | None) -> str:
    if not step:
        return ""
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


def file_state(path: Path, expected_sha: str | None = None) -> dict[str, Any]:
    state: dict[str, Any] = {"path": video_live.rel(path), "exists": path.exists()}
    if path.exists():
        state["size"] = path.stat().st_size
        digest = video_live.sha256_file(path)
        state["sha256"] = digest
        if expected_sha:
            state["sha256_ok"] = digest == expected_sha
    elif expected_sha:
        state["sha256_ok"] = False
    return state


def twrp_state() -> dict[str, Any]:
    return {
        "dir": {"path": video_live.rel(TWRP_DIR), "exists": TWRP_DIR.exists()},
        "recovery_img": file_state(TWRP_RECOVERY_IMG),
        "recovery_tar": file_state(TWRP_RECOVERY_TAR),
        "available": TWRP_DIR.exists() and (TWRP_RECOVERY_IMG.exists() or TWRP_RECOVERY_TAR.exists()),
    }


def preflight_state(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "run_id": RUN_ID,
        "candidate": file_state(CANDIDATE_IMAGE, CANDIDATE_SHA256),
        "rollback": file_state(video_live.ROLLBACK_IMAGE, video_live.ROLLBACK_SHA256),
        "fallback_v2237": file_state(video_live.FALLBACK_V2237, video_live.FALLBACK_V2237_SHA256),
        "fallback_v48": file_state(video_live.FALLBACK_V48),
        "twrp": twrp_state(),
        "flash_helper": file_state(base.FLASH),
        "badapple_asset_manifest": badapple_hud.file_state(badapple_hud.LOCAL_MANIFEST),
        "badapple_asset_stream": badapple_hud.file_state(badapple_hud.LOCAL_STREAM, badapple_hud.BADAPPLE_SHA256),
        "badapple_asset_audio": badapple_hud.file_state(badapple_hud.LOCAL_AUDIO, badapple_hud.BADAPPLE_AUDIO_SHA256),
        "badapple_asset_manifest_ok": bool(badapple_hud.preflight_state(args).get("asset_manifest_ok")),
        "nyan_asset_manifest": nyan.file_state(nyan.LOCAL_MANIFEST),
        "nyan_asset_stream": nyan.file_state(nyan.LOCAL_STREAM, nyan.NYAN_SHA256),
        "nyan_asset_audio": nyan.file_state(nyan.LOCAL_AUDIO, nyan.NYAN_AUDIO_SHA256),
        "nyan_asset_manifest_ok": bool(nyan.preflight_state(args).get("asset_manifest_ok")),
        "badapple_remote_cache_dir": video_live.remote_cache_dir(badapple_hud.BADAPPLE_SHA256),
        "nyan_remote_cache_dir": video_live.remote_cache_dir(nyan.NYAN_SHA256),
        "badapple_frames": int(args.frames),
        "nyan_frames": NYAN_FRAMES,
        "badapple_audio_duration_ms": BADAPPLE_DURATION_MS,
        "badapple_audio_amplitude_milli": BADAPPLE_AMPLITUDE_MILLI,
        "badapple_audio_pcm_gain_milli": BADAPPLE_PCM_GAIN_MILLI,
        "sync_status_path": SYNC_STATUS_PATH,
        "sync_wait_ms": SYNC_WAIT_MS,
        "sync_start_offset_ms": SYNC_START_OFFSET_MS,
        "hard_boundary": [
            "boot partition only via native_init_flash.py",
            "rollback to v2321 and verify selftest fail=0",
            "same resident image must validate Bad Apple and Nyan before rollback",
            "private streams/audio and raw run logs remain untracked",
            "KMS dumb-buffer setcrtc/player-HUD path only",
            "no Venus/GPU/raw DSI/panel init/backlight/PMIC/PWM/regulator/GPIO/GDSC",
            "audio amplitude remains <=0.2",
        ],
    }


def preflight_ok(state: dict[str, Any]) -> bool:
    return bool(
        state["candidate"].get("sha256_ok")
        and state["rollback"].get("sha256_ok")
        and state["fallback_v2237"].get("sha256_ok")
        and state["fallback_v48"].get("exists")
        and state["twrp"].get("available")
        and state["flash_helper"].get("exists")
        and state["badapple_asset_stream"].get("sha256_ok")
        and state["badapple_asset_audio"].get("sha256_ok")
        and state.get("badapple_asset_manifest_ok")
        and state["nyan_asset_stream"].get("sha256_ok")
        and state["nyan_asset_audio"].get("sha256_ok")
        and state.get("nyan_asset_manifest_ok")
    )


def sync_summary_setcrtc(text: str) -> dict[str, Any]:
    requested = marker_int(text, "video.cache.play.requested_audio_sync")
    enabled = marker_int(text, "video.stream.audio_sync.enabled")
    ready = marker_int(text, "video.stream.audio_sync.ready")
    wait_ms = marker_int(text, "video.stream.audio_sync.wait_ms")
    start_offset_ms = marker_int(text, "video.stream.audio_sync.start_offset_ms")
    listen_begin_ns = marker_int(text, "video.stream.audio_sync.listen_begin_ns")
    sample_rate = marker_int(text, "video.stream.audio_sync.sample_rate")
    frame_bytes = marker_int(text, "video.stream.audio_sync.frame_bytes")
    total_frames = marker_int(text, "video.stream.audio_sync.total_frames")
    initial_drop_late_ns = marker_int(text, "video.stream.audio_sync.initial_drop_late_ns")
    return {
        "requested": requested,
        "enabled": enabled,
        "ready": ready,
        "wait_ms": wait_ms,
        "start_offset_ms": start_offset_ms,
        "listen_begin_ns": listen_begin_ns,
        "sample_rate": sample_rate,
        "frame_bytes": frame_bytes,
        "total_frames": total_frames,
        "initial_drop_late_ns": initial_drop_late_ns,
        "status_path_marker": f"video.stream.audio_sync.status_path={SYNC_STATUS_PATH}" in text,
        "drop_policy_none": "video.stream.audio_sync.drop_policy=none" in text,
        "requested_ok": requested == 1,
        "enabled_ok": enabled == 1,
        "ready_ok": ready == 1,
        "wait_ok": wait_ms == SYNC_WAIT_MS,
        "start_offset_ok": start_offset_ms == SYNC_START_OFFSET_MS,
        "listen_begin_present": listen_begin_ns is not None and listen_begin_ns > 0,
        "geometry_ok": sample_rate == 48000 and frame_bytes == 4,
        "duration_present": total_frames is not None and total_frames > 0,
        "initial_drop_late_ok": initial_drop_late_ns == 0,
    }


def sync_pass_setcrtc(summary: dict[str, Any]) -> bool:
    required = (
        "requested_ok",
        "enabled_ok",
        "ready_ok",
        "wait_ok",
        "start_offset_ok",
        "status_path_marker",
        "drop_policy_none",
        "listen_begin_present",
        "geometry_ok",
        "duration_present",
    )
    return all(bool(summary.get(key)) for key in required)


def classify_setcrtc_demo_play(
    text: str,
    *,
    preset_name: str,
    asset_id: str,
    sha256: str,
    expected_frames: int,
    expected_format: str,
    require_beat_flash: bool = False,
) -> dict[str, Any]:
    presented = marker_int(text, "video.stream.presented") or 0
    dropped = marker_int(text, "video.stream.dropped_frames")
    if dropped is None:
        dropped = -1
    frames_total = marker_int(text, "video.stream.frames_total") or 0
    flip_events = marker_int(text, "video.stream.flip_events") or 0
    elapsed_ns = marker_int(text, "video.stream.elapsed_ns") or 0
    fps_milli = marker_int(text, "video.stream.fps_milli") or 0
    bytes_seen = marker_int(text, "video.stream.bytes") or 0
    late_frames = marker_int(text, "video.stream.late_frames")
    beat_active_frames = marker_int(text, "video.stream.beat_flash.active_frames")
    accounted = presented + max(dropped, 0)
    trust = {
        "trust_cache": "video.cache.play.trust_cache=1" in text,
        "sha_checked_zero": "video.cache.verify.sha256_checked=0" in text,
        "sha_match_zero": "video.cache.verify.sha256_match=0" in text,
        "actual_not_checked": "video.cache.verify.actual_sha256=trust-cache-not-checked" in text,
        "default_verify_not_repeated": f"video.cache.verify.actual_sha256={sha256}" not in text,
    }
    preset = {
        "preset": f"video.cache.preset={preset_name}" in text,
        "asset_id": f"video.cache.preset.asset_id={asset_id}" in text,
        "sha256": f"video.cache.preset.sha256={sha256}" in text,
    }
    demo = {
        "preset": f"video.demo.preset={preset_name}" in text,
        "asset_id": f"video.demo.asset_id={asset_id}" in text,
        "storage": "video.demo.storage=sd-sha-cache" in text,
        "boot_asset_policy": "video.demo.boot_asset_policy=boot-image-carries-player-not-frames" in text,
    }
    sync = sync_summary_setcrtc(text)
    requested_present = f"video.cache.play.requested_present={BADAPPLE_PRESENT_MODE}" in text
    requested_layout = f"video.cache.play.requested_layout={BADAPPLE_LAYOUT}" in text
    stream_layout = f"video.stream.layout={BADAPPLE_LAYOUT}" in text
    present_mode = f"video.stream.present_mode={BADAPPLE_PRESENT_MODE}" in text
    path_ok = "video.stream.path=kms-dumb-buffer" in text
    pixel_format = f"video.stream.pixel_format={expected_format}" in text
    beat_ok = (beat_active_frames is not None and beat_active_frames > 0) if require_beat_flash else True
    return {
        "presented": presented,
        "dropped_frames": dropped,
        "accounted_frames": accounted,
        "expected_frames": expected_frames,
        "frames_total": frames_total,
        "flip_events": flip_events,
        "elapsed_ns": elapsed_ns,
        "fps_milli": fps_milli,
        "bytes": bytes_seen,
        "late_frames": late_frames,
        "beat_flash_active_frames": beat_active_frames,
        "frame_accounting_ok": dropped >= 0 and accounted == expected_frames and presented == expected_frames,
        "no_drops": dropped == 0,
        "setcrtc_flip_ok": flip_events == 0,
        "requested_present_cache_marker": requested_present,
        "requested_layout_cache_marker": requested_layout,
        "stream_layout_marker": stream_layout,
        "present_mode_marker": present_mode,
        "path_ok": path_ok,
        "pixel_format": pixel_format,
        "beat_flash_ok": beat_ok,
        "trust_cache": trust,
        "trust_cache_pass": all_true(trust),
        "preset": preset,
        "preset_pass": all_true(preset),
        "demo": demo,
        "demo_pass": all_true(demo),
        "sync": sync,
        "sync_pass": sync_pass_setcrtc(sync),
        "pass": bool(
            requested_present
            and requested_layout
            and stream_layout
            and present_mode
            and path_ok
            and pixel_format
            and beat_ok
            and all_true(trust)
            and all_true(preset)
            and all_true(demo)
            and sync_pass_setcrtc(sync)
            and dropped == 0
            and accounted == expected_frames
            and presented == expected_frames
            and flip_events == 0
            and elapsed_ns > 0
            and fps_milli > 0
            and bytes_seen > 0
        ),
    }


def audio_pass_summary(audio_text: str) -> dict[str, Any]:
    summary = av_live.audio_live.classify_pcm_output(audio_text)
    required = (
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
        "execute_plan_source_pcm",
        "execute_source_pcm",
        "execute_plan_waveform_file",
        "pcm_file_supported",
        "pcm_file_validated",
        "pcm_path_allowed",
    )
    return {
        "summary": summary,
        "pass": all(bool(summary.get(key)) for key in required),
        "required": list(required),
    }


def clear_audio_status(out_dir: Path, steps: list[dict[str, Any]], label: str) -> None:
    base.run_serial_step(
        out_dir,
        steps,
        label,
        ["run", "/bin/busybox", "rm", "-f", SYNC_STATUS_PATH, REMOTE_PLAY_LOG],
        timeout=45.0,
        retry_unsafe=True,
        allow_error=True,
    )


def collect_audio_result(
    out_dir: Path,
    steps: list[dict[str, Any]],
    *,
    audio_execute_text: str,
    log_label: str,
    wait_timeout: float,
) -> dict[str, Any]:
    worker = av_live.audio_live.wait_for_worker_done(out_dir, steps, wait_timeout)
    log_step = base.run_serial_step(
        out_dir,
        steps,
        log_label,
        ["run", "/bin/busybox", "cat", REMOTE_PLAY_LOG],
        timeout=45.0,
        retry_unsafe=True,
        allow_error=True,
    )
    audio_log_text = stdout_of(log_step)
    audio_text = "\n".join([audio_execute_text, str(worker.get("text") or ""), audio_log_text])
    summary = audio_pass_summary(audio_text)
    return {
        "worker_done": bool(worker.get("done")),
        "worker_attempts": worker.get("attempts"),
        "worker_status_stdout_path": worker.get("stdout_path"),
        "worker_log_stdout_path": log_step.get("stdout_path"),
        "summary": summary,
    }


def install_video_fixture(
    args: argparse.Namespace,
    out_dir: Path,
    steps: list[dict[str, Any]],
    fixture: dict[str, Any],
    *,
    decision_name: str,
) -> dict[str, Any]:
    install = video_live.install_fixture(args, out_dir, steps, fixture)
    if not (install.get("cache_hit") or install.get("cache_uploaded") or install.get("cache_adopted")):
        raise RuntimeError(f"{decision_name} stream was not available in SHA-addressed SD cache")
    return install


def validate_badapple(args: argparse.Namespace, out_dir: Path, steps: list[dict[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {"pass": False, "frames": int(args.frames)}
    fixture = badapple_hud.fixture_from_asset()
    result["fixture"] = fixture
    result["runtime_install"] = install_video_fixture(args, out_dir, steps, fixture, decision_name="Bad Apple")
    result["audio_install"] = badapple_av.install_audio_pcm(args, out_dir, steps)
    if not result["audio_install"].get("remote_sha_match"):
        raise RuntimeError("Bad Apple audio PCM remote SHA mismatch")

    base.run_serial_step(out_dir, steps, "candidate-hide-menu-before-badapple", ["hide"], timeout=45.0, allow_error=True, retry_unsafe=True)
    status_step = base.run_serial_step(
        out_dir,
        steps,
        "candidate-video-demo-badapple-status",
        ["video", "demo", badapple_hud.PRESET_NAME, "status"],
        timeout=120.0,
        allow_error=True,
        retry_unsafe=False,
    )
    status_text = stdout_of(status_step)
    result["cache_status_rc"] = status_step.get("rc")
    result["cache_status_stdout_path"] = status_step.get("stdout_path")
    result["cache_status_summary"] = badapple_hud.cache_status_summary(status_text)
    result["cache_status_preset_summary"] = badapple_hud.preset_summary(status_text)
    result["cache_status_demo_summary"] = badapple_hud.demo_summary(status_text)
    if (
        status_step.get("rc") != 0
        or not all_true(result["cache_status_summary"])
        or not all_true(result["cache_status_preset_summary"])
        or not all_true(result["cache_status_demo_summary"])
    ):
        raise RuntimeError("video demo badapple status did not emit required markers")

    verify_step = base.run_serial_step(
        out_dir,
        steps,
        "candidate-video-demo-badapple-verify",
        ["video", "demo", badapple_hud.PRESET_NAME, "verify"],
        timeout=600.0,
        allow_error=True,
        retry_unsafe=False,
    )
    verify_text = stdout_of(verify_step)
    result["cache_verify_rc"] = verify_step.get("rc")
    result["cache_verify_stdout_path"] = verify_step.get("stdout_path")
    result["cache_verify_summary"] = badapple_hud.cache_verify_summary(verify_text)
    result["cache_verify_preset_summary"] = badapple_hud.preset_summary(verify_text)
    result["cache_verify_demo_summary"] = badapple_hud.demo_summary(verify_text)
    if (
        verify_step.get("rc") != 0
        or not all_true(result["cache_verify_summary"])
        or not all_true(result["cache_verify_preset_summary"])
        or not all_true(result["cache_verify_demo_summary"])
    ):
        raise RuntimeError("video demo badapple verify did not emit required markers")

    clear_audio_status(out_dir, steps, "candidate-clear-audio-play-status-before-badapple")
    audio_step = base.run_serial_step(
        out_dir,
        steps,
        "candidate-audio-play-badapple-fullsong-pcm-execute",
        [
            "audio", "play", AUDIO_PROFILE,
            "--mode", "listen",
            "--duration-ms", str(BADAPPLE_DURATION_MS),
            "--amplitude-milli", str(BADAPPLE_AMPLITUDE_MILLI),
            "--manifest", AUDIO_MANIFEST,
            "--pcm-gain-milli", str(BADAPPLE_PCM_GAIN_MILLI),
            "--pcm-file", badapple_av.REMOTE_AUDIO_PCM,
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
        raise RuntimeError("Bad Apple full-song PCM-file worker did not start")

    play_step = base.run_serial_step(
        out_dir,
        steps,
        "candidate-video-demo-badapple-fullsong-player-hud-av-play",
        [
            "video", "demo", badapple_hud.PRESET_NAME, "play",
            "--trust-cache",
            "--frames", str(args.frames),
            "--present", BADAPPLE_PRESENT_MODE,
            "--layout", BADAPPLE_LAYOUT,
            "--sync-audio-status", SYNC_STATUS_PATH,
            "--sync-wait-ms", str(SYNC_WAIT_MS),
            "--sync-start-offset-ms", str(SYNC_START_OFFSET_MS),
        ],
        timeout=args.stream_timeout,
        allow_error=True,
        retry_unsafe=False,
    )
    play_text = stdout_of(play_step)
    result["cache_play_rc"] = play_step.get("rc")
    result["cache_play_stdout_path"] = play_step.get("stdout_path")
    result["cache_play_elapsed_sec"] = play_step.get("elapsed_sec")
    result["cache_play_summary"] = classify_setcrtc_demo_play(
        play_text,
        preset_name=badapple_hud.PRESET_NAME,
        asset_id="badapple-480x360-full-v2903",
        sha256=badapple_hud.BADAPPLE_SHA256,
        expected_frames=int(args.frames),
        expected_format=badapple_hud.BADAPPLE_FORMAT,
        require_beat_flash=True,
    )
    audio_result = collect_audio_result(
        out_dir,
        steps,
        audio_execute_text=audio_execute_text,
        log_label="candidate-badapple-audio-worker-log",
        wait_timeout=300.0,
    )
    result["audio_worker_done"] = audio_result["worker_done"]
    result["audio_worker_attempts"] = audio_result["worker_attempts"]
    result["audio_worker_status_stdout_path"] = audio_result["worker_status_stdout_path"]
    result["audio_worker_log_stdout_path"] = audio_result["worker_log_stdout_path"]
    result["audio_summary"] = audio_result["summary"]
    if (
        play_step.get("rc") != 0
        or not result["cache_play_summary"].get("pass")
        or not result["audio_summary"].get("pass")
        or not result["audio_worker_done"]
    ):
        raise RuntimeError("Bad Apple full-song Player HUD A/V run did not emit required pass markers")
    result["pass"] = True
    return result


def validate_nyan(args: argparse.Namespace, out_dir: Path, steps: list[dict[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {"pass": False, "frames": NYAN_FRAMES}
    fixture = nyan.fixture_from_asset()
    result["fixture"] = fixture
    result["runtime_install"] = install_video_fixture(args, out_dir, steps, fixture, decision_name="Nyan")
    result["audio_install"] = nyan.install_audio_pcm(args, out_dir, steps)
    if not result["audio_install"].get("remote_sha_match"):
        raise RuntimeError("Nyan audio PCM remote SHA mismatch")

    base.run_serial_step(out_dir, steps, "candidate-hide-menu-before-nyan", ["hide"], timeout=45.0, allow_error=True, retry_unsafe=True)
    status_step = base.run_serial_step(
        out_dir,
        steps,
        "candidate-video-demo-nyan-status",
        ["video", "demo", nyan.PRESET_NAME, "status"],
        timeout=120.0,
        allow_error=True,
        retry_unsafe=False,
    )
    status_text = stdout_of(status_step)
    result["cache_status_rc"] = status_step.get("rc")
    result["cache_status_stdout_path"] = status_step.get("stdout_path")
    result["cache_status_summary"] = nyan.cache_status_summary(status_text)
    result["cache_status_preset_summary"] = nyan.preset_summary(status_text)
    result["cache_status_demo_summary"] = nyan.demo_summary(status_text)
    if (
        status_step.get("rc") != 0
        or not all_true(result["cache_status_summary"])
        or not all_true(result["cache_status_preset_summary"])
        or not all_true(result["cache_status_demo_summary"])
    ):
        raise RuntimeError("video demo nyan status did not emit required markers")

    verify_step = base.run_serial_step(
        out_dir,
        steps,
        "candidate-video-demo-nyan-verify",
        ["video", "demo", nyan.PRESET_NAME, "verify"],
        timeout=420.0,
        allow_error=True,
        retry_unsafe=False,
    )
    verify_text = stdout_of(verify_step)
    result["cache_verify_rc"] = verify_step.get("rc")
    result["cache_verify_stdout_path"] = verify_step.get("stdout_path")
    result["cache_verify_summary"] = nyan.cache_verify_summary(verify_text)
    result["cache_verify_preset_summary"] = nyan.preset_summary(verify_text)
    result["cache_verify_demo_summary"] = nyan.demo_summary(verify_text)
    if (
        verify_step.get("rc") != 0
        or not all_true(result["cache_verify_summary"])
        or not all_true(result["cache_verify_preset_summary"])
        or not all_true(result["cache_verify_demo_summary"])
    ):
        raise RuntimeError("video demo nyan verify did not emit required markers")

    clear_audio_status(out_dir, steps, "candidate-clear-audio-play-status-before-nyan")
    audio_step = base.run_serial_step(
        out_dir,
        steps,
        "candidate-audio-play-nyan-pcm-execute",
        [
            "audio", "play", AUDIO_PROFILE,
            "--mode", "listen",
            "--duration-ms", str(nyan.AUDIO_DURATION_MS),
            "--amplitude-milli", str(nyan.AUDIO_AMPLITUDE_MILLI),
            "--manifest", AUDIO_MANIFEST,
            "--pcm-gain-milli", str(nyan.AUDIO_PCM_GAIN_MILLI),
            "--pcm-file", nyan.REMOTE_AUDIO_PCM,
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
        raise RuntimeError("Nyan audio PCM-file worker did not start")

    play_step = base.run_serial_step(
        out_dir,
        steps,
        "candidate-video-demo-nyan-player-hud-av-play",
        [
            "video", "demo", nyan.PRESET_NAME, "play",
            "--trust-cache",
            "--frames", str(NYAN_FRAMES),
            "--present", nyan.PRESENT_MODE,
            "--layout", nyan.LAYOUT,
            "--sync-audio-status", SYNC_STATUS_PATH,
            "--sync-wait-ms", str(SYNC_WAIT_MS),
            "--sync-start-offset-ms", str(SYNC_START_OFFSET_MS),
        ],
        timeout=max(args.stream_timeout, 180.0),
        allow_error=True,
        retry_unsafe=False,
    )
    play_text = stdout_of(play_step)
    result["cache_play_rc"] = play_step.get("rc")
    result["cache_play_stdout_path"] = play_step.get("stdout_path")
    result["cache_play_elapsed_sec"] = play_step.get("elapsed_sec")
    result["cache_play_summary"] = nyan.classify_setcrtc_play(play_text, NYAN_FRAMES)
    audio_result = collect_audio_result(
        out_dir,
        steps,
        audio_execute_text=audio_execute_text,
        log_label="candidate-nyan-audio-worker-log",
        wait_timeout=180.0,
    )
    result["audio_worker_done"] = audio_result["worker_done"]
    result["audio_worker_attempts"] = audio_result["worker_attempts"]
    result["audio_worker_status_stdout_path"] = audio_result["worker_status_stdout_path"]
    result["audio_worker_log_stdout_path"] = audio_result["worker_log_stdout_path"]
    result["audio_summary"] = audio_result["summary"]
    if (
        play_step.get("rc") != 0
        or not result["cache_play_summary"].get("pass")
        or not result["audio_summary"].get("pass")
        or not result["audio_worker_done"]
    ):
        raise RuntimeError("Nyan Player HUD A/V run did not emit required pass markers")
    result["pass"] = True
    return result


def render_demo_lines(name: str, result: dict[str, Any]) -> list[str]:
    install = result.get("runtime_install", {}) if isinstance(result.get("runtime_install"), dict) else {}
    audio_install = result.get("audio_install", {}) if isinstance(result.get("audio_install"), dict) else {}
    play = result.get("cache_play_summary", {}) if isinstance(result.get("cache_play_summary"), dict) else {}
    audio = result.get("audio_summary", {}) if isinstance(result.get("audio_summary"), dict) else {}
    return [
        f"### {name}",
        "",
        f"- Pass: `{int(bool(result.get('pass')))}`",
        f"- Video cache source: `{install.get('cache_source')}` hit=`{int(bool(install.get('cache_hit')))}` uploaded=`{int(bool(install.get('cache_uploaded')))}`",
        f"- Audio remote SHA matched: `{int(bool(audio_install.get('remote_sha_match')))}`",
        f"- Status/verify/play rc: `{result.get('cache_status_rc')}` / `{result.get('cache_verify_rc')}` / `{result.get('cache_play_rc')}`",
        f"- Frames: presented=`{play.get('presented')}` dropped=`{play.get('dropped_frames')}` expected=`{play.get('expected_frames')}` fps_milli=`{play.get('fps_milli')}`",
        f"- Present/layout/path: `{int(bool(play.get('present_mode_marker')))}` / `{int(bool(play.get('stream_layout_marker')))}` / `{int(bool(play.get('path_ok')))}`",
        f"- Sync pass: `{int(bool(play.get('sync_pass')))}`",
        f"- Audio worker done/pass: `{int(bool(result.get('audio_worker_done')))}` / `{int(bool(audio.get('pass')))}`",
        f"- Play stdout: `{result.get('cache_play_stdout_path')}`",
        "",
    ]


def render_report(result: dict[str, Any]) -> str:
    badapple = result.get("badapple", {}) if isinstance(result.get("badapple"), dict) else {}
    nyan_result = result.get("nyan", {}) if isinstance(result.get("nyan"), dict) else {}
    lines = [
        "# Native Init V3022 Demo Checkpoint Bad Apple + Nyan Live Validation",
        "",
        "## Summary",
        "",
        f"- Cycle: `{RUN_ID}`",
        "- Track: active Video playback / kept demo checkpoint before further DOOM integration.",
        f"- Decision: `{result.get('decision')}`",
        f"- Result before rollback: `{int(bool(result.get('pass')))}`",
        f"- Candidate: `{CANDIDATE_TAG}` / `{CANDIDATE_VERSION}` / `{CANDIDATE_SHA256}`",
        f"- Candidate image: `{video_live.rel(CANDIDATE_IMAGE)}`",
        f"- Same-image validation: Bad Apple pass=`{int(bool(badapple.get('pass')))}` Nyan pass=`{int(bool(nyan_result.get('pass')))}`",
        f"- Rollback attempted: `{int(bool(result.get('rollback_attempted')))}`",
        f"- Rollback health: version_ok=`{int(bool(result.get('rollback_version_ok')))}` selftest_fail0=`{int(bool(result.get('rollback_selftest_fail0')))}`",
        "",
        "## Candidate Health",
        "",
        f"- Version OK: `{int(bool(result.get('candidate_version_ok')))}`",
        f"- Status OK: `{int(bool(result.get('candidate_status_ok')))}`",
        f"- Selftest before demos fail=0: `{int(bool(result.get('candidate_selftest_fail0')))}`",
        f"- Video status markers: demo_surface=`{int(bool(result.get('candidate_video_status_demo_surface')))}` badapple=`{int(bool(result.get('candidate_video_status_badapple')))}` nyan=`{int(bool(result.get('candidate_video_status_nyan')))}` incremental_hud=`{int(bool(result.get('candidate_video_status_incremental_hud')))}`",
        f"- Audio status OK: `{int(bool(result.get('candidate_audio_status_ok')))}`",
        "",
        "## Demo Results",
        "",
    ]
    lines.extend(render_demo_lines("Bad Apple Full-Song Player HUD", badapple))
    lines.extend(render_demo_lines("Nyan Cat Player HUD Preview", nyan_result))
    lines.extend([
        "## Evidence",
        "",
        f"- Result JSON: `{result.get('result_json')}`",
        f"- Output dir: `{result.get('out_dir')}`",
        "",
        "## Safety",
        "",
        "- Only the boot partition was flashed, through `native_init_flash.py`.",
        "- The exact V3021 SHA256 was checked before flash and requested as readback identity.",
        "- Rollback target remained `v2321`; deeper fallbacks `v2237` and `v48` plus TWRP were preflighted.",
        "- Raw media, generated boot images, and command transcripts remained private/untracked.",
        "- No Wi-Fi connect/DHCP/ping, forbidden partition, Venus, GPU, raw DSI, panel init, backlight, PMIC, PWM, regulator, GPIO, or GDSC path was used.",
        "",
    ])
    if result.get("error"):
        lines.extend([
            "## Error",
            "",
            f"- Type: `{result.get('error_type')}`",
            f"- Message: `{result.get('error')}`",
            "",
        ])
    return "\n".join(lines)


def run_live(args: argparse.Namespace, out_dir: Path, state: dict[str, Any]) -> dict[str, Any]:
    steps: list[dict[str, Any]] = []
    candidate_flash_ok = False
    candidate_flash_attempted = False
    result: dict[str, Any] = {
        "decision": f"{DECISION_PREFIX}-live-started",
        "pass": False,
        "out_dir": video_live.rel(out_dir),
        "preflight": state,
        "steps": steps,
        "rollback_attempted": False,
        "rollback_version_ok": False,
        "rollback_selftest_fail0": False,
    }
    try:
        base.run_step(
            out_dir,
            steps,
            "bridge-status-before-flash",
            ["python3", video_live.rel(video_live.ROOT / "workspace/public/src/scripts/revalidation/a90_bridge.py"), "status", "--json"],
            timeout=60.0,
        )
        base.run_step(
            out_dir,
            steps,
            "verify-current-v2321",
            video_live.flash_command(video_live.ROLLBACK_IMAGE, video_live.ROLLBACK_VERSION, video_live.ROLLBACK_SHA256, from_native=False) + ["--verify-only"],
            timeout=args.flash_timeout,
        )
        candidate_flash_attempted = True
        flash = base.run_step(
            out_dir,
            steps,
            f"flash-{CANDIDATE_TAG}",
            video_live.flash_command(CANDIDATE_IMAGE, CANDIDATE_VERSION, CANDIDATE_SHA256, from_native=True),
            timeout=args.flash_timeout,
        )
        candidate_flash_ok = flash.get("rc") == 0
        version = base.run_serial_step(out_dir, steps, "candidate-version", ["version"], timeout=90.0, retry_unsafe=True)
        status = base.run_serial_step(out_dir, steps, "candidate-status", ["status"], timeout=90.0, retry_unsafe=True)
        selftest = base.run_serial_step(out_dir, steps, "candidate-selftest", ["selftest", "verbose"], timeout=120.0, retry_unsafe=True)
        video_status = base.run_serial_step(out_dir, steps, "candidate-video-status", ["video", "status"], timeout=120.0, retry_unsafe=True)
        audio_status = base.run_serial_step(out_dir, steps, "candidate-audio-status", ["audio", "status"], timeout=90.0, retry_unsafe=True)
        version_text = stdout_of(version)
        video_status_text = stdout_of(video_status)
        result["candidate_version_ok"] = f"A90 Linux init {CANDIDATE_VERSION} ({CANDIDATE_TAG})" in version_text
        result["candidate_status_ok"] = bool(status.get("ok"))
        result["candidate_selftest_fail0"] = video_live.selftest_step_ok(selftest)
        result["candidate_video_status_demo_surface"] = "video.status.next_demo=video demo [badapple|badapple-scale|nyan|doom]" in video_status_text
        result["candidate_video_status_badapple"] = (
            result["candidate_video_status_demo_surface"]
            and "video.status.player_hud_incremental_panel=1" in video_status_text
        )
        result["candidate_video_status_nyan"] = (
            result["candidate_video_status_demo_surface"]
            and "video.status.nyan_pal8_rle=1" in video_status_text
        )
        result["candidate_video_status_incremental_hud"] = "video.status.player_hud_incremental_panel=1" in video_status_text
        result["candidate_audio_status_ok"] = "audio.status.version=" in stdout_of(audio_status)
        if not (
            result["candidate_version_ok"]
            and result["candidate_status_ok"]
            and result["candidate_selftest_fail0"]
            and result["candidate_video_status_badapple"]
            and result["candidate_video_status_nyan"]
            and result["candidate_video_status_incremental_hud"]
            and result["candidate_audio_status_ok"]
        ):
            result["decision"] = f"{DECISION_PREFIX}-candidate-health-failed-before-demos"
            raise RuntimeError("candidate health/video/audio status did not pass")

        result["badapple"] = validate_badapple(args, out_dir, steps)
        after_badapple = base.run_serial_step(out_dir, steps, "candidate-selftest-after-badapple", ["selftest", "verbose"], timeout=120.0, retry_unsafe=True)
        result["candidate_selftest_after_badapple_fail0"] = video_live.selftest_step_ok(after_badapple)
        if not result["candidate_selftest_after_badapple_fail0"]:
            result["decision"] = f"{DECISION_PREFIX}-post-badapple-selftest-failed"
            raise RuntimeError("post Bad Apple selftest did not report fail=0")

        result["nyan"] = validate_nyan(args, out_dir, steps)
        after_nyan = base.run_serial_step(out_dir, steps, "candidate-selftest-after-nyan", ["selftest", "verbose"], timeout=120.0, retry_unsafe=True)
        result["candidate_selftest_after_nyan_fail0"] = video_live.selftest_step_ok(after_nyan)
        if not result["candidate_selftest_after_nyan_fail0"]:
            result["decision"] = f"{DECISION_PREFIX}-post-nyan-selftest-failed"
            raise RuntimeError("post Nyan selftest did not report fail=0")

        result["decision"] = f"{DECISION_PREFIX}-same-image-live-pass-before-rollback"
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
            rollback = base.rollback_v2321(out_dir, steps, from_native=candidate_flash_ok, timeout=args.flash_timeout)
            result["rollback_step_ok"] = bool(rollback.get("success"))
            result["rollback_attempts"] = rollback.get("attempts", [])
            result["rollback_recovery_fallback_used"] = bool(rollback.get("used_recovery_fallback"))
            if rollback.get("success"):
                rollback_version = base.run_serial_step(out_dir, steps, "rollback-version", ["version"], timeout=90.0, retry_unsafe=True, allow_error=True)
                rollback_selftest = base.run_serial_step(out_dir, steps, "rollback-selftest", ["selftest", "verbose"], timeout=120.0, retry_unsafe=True, allow_error=True)
                result["rollback_version_ok"] = video_live.ROLLBACK_VERSION in stdout_of(rollback_version)
                result["rollback_selftest_fail0"] = video_live.selftest_step_ok(rollback_selftest)
        result["result_json"] = video_live.rel(out_dir / "result.json")
        video_live.write_json(out_dir / "result.json", result)
        REPORT_PATH.write_text(render_report(result), encoding="utf-8")
    return result


def dry_run_payload(args: argparse.Namespace, state: dict[str, Any]) -> dict[str, Any]:
    return {
        "decision": f"{DECISION_PREFIX}-dry-run" if preflight_ok(state) else f"{DECISION_PREFIX}-preflight-failed",
        "ok": preflight_ok(state),
        "preflight": state,
        "commands": [
            f"verify rollback image {video_live.ROLLBACK_IMAGE}",
            f"flash {CANDIDATE_IMAGE}",
            "version/status/selftest/video status/audio status",
            f"seed Bad Apple {badapple_hud.BADAPPLE_SHA256} into {video_live.remote_cache_dir(badapple_hud.BADAPPLE_SHA256)}",
            f"audio play {AUDIO_PROFILE} --duration-ms {BADAPPLE_DURATION_MS} --amplitude-milli {BADAPPLE_AMPLITUDE_MILLI} --pcm-gain-milli {BADAPPLE_PCM_GAIN_MILLI} --pcm-file {badapple_av.REMOTE_AUDIO_PCM} --execute",
            f"video demo badapple play --trust-cache --frames {args.frames} --present {BADAPPLE_PRESENT_MODE} --layout {BADAPPLE_LAYOUT} --sync-audio-status {SYNC_STATUS_PATH} --sync-wait-ms {SYNC_WAIT_MS} --sync-start-offset-ms {SYNC_START_OFFSET_MS}",
            f"seed Nyan {nyan.NYAN_SHA256} into {video_live.remote_cache_dir(nyan.NYAN_SHA256)}",
            f"audio play {AUDIO_PROFILE} --duration-ms {nyan.AUDIO_DURATION_MS} --amplitude-milli {nyan.AUDIO_AMPLITUDE_MILLI} --pcm-gain-milli {nyan.AUDIO_PCM_GAIN_MILLI} --pcm-file {nyan.REMOTE_AUDIO_PCM} --execute",
            f"video demo nyan play --trust-cache --frames {NYAN_FRAMES} --present {nyan.PRESENT_MODE} --layout {nyan.LAYOUT} --sync-audio-status {SYNC_STATUS_PATH} --sync-wait-ms {SYNC_WAIT_MS} --sync-start-offset-ms {SYNC_START_OFFSET_MS}",
            "selftest after each demo",
            "rollback v2321 and verify selftest fail=0",
        ],
    }


def parse_args() -> argparse.Namespace:
    args = video_live.parse_args()
    args.live = bool(args.live)
    args.frames = BADAPPLE_FRAMES if args.frames == 30 else args.frames
    args.width = 480
    args.height = 360
    args.stride = 60
    args.stream_format = badapple_hud.BADAPPLE_FORMAT
    args.pattern = "checker"
    args.fps_num = 30
    args.fps_den = 1
    args.disable_cache = False
    args.adopt_legacy_cache = False
    args.require_cache_hit = False
    args.chunk_large_streams = True
    args.stream_chunk_bytes = min(int(args.stream_chunk_bytes), 64 * 1024 * 1024)
    args.stream_timeout = max(float(args.stream_timeout), 420.0)
    args.transfer_timeout = max(float(args.transfer_timeout), 900.0)
    args.flash_timeout = max(float(args.flash_timeout), 900.0)
    return args


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
        payload = {
            "decision": f"{DECISION_PREFIX}-preflight-failed-no-flash",
            "pass": False,
            "preflight": state,
            "out_dir": video_live.rel(out_dir),
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
        "badapple_pass": bool((result.get("badapple") or {}).get("pass")),
        "nyan_pass": bool((result.get("nyan") or {}).get("pass")),
        "rollback_version_ok": result.get("rollback_version_ok"),
        "rollback_selftest_fail0": result.get("rollback_selftest_fail0"),
    }, indent=2, sort_keys=True))
    return 0 if final_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
