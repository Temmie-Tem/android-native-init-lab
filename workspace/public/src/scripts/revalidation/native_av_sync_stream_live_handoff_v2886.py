#!/usr/bin/env python3
"""V2886 live validation for V2885 audio-anchored video stream scheduling.

This reuses the V2882 PCM-file audio + page-flip video co-run envelope, but
flashes the V2885 candidate and passes ``video stream --sync-audio-status`` so
video frame deadlines are anchored to the audio PCM worker's listen_begin_ns.
It validates the scheduling path, not human-perceptual A/V sync quality.
"""

from __future__ import annotations

import json
import re
import sys
from typing import Any

import native_av_pcm_video_corun_live_handoff_v2882 as v2882
import native_av_sync_telemetry_live_handoff_v2884 as v2884

RUN_ID = "V2886"
CANDIDATE_IMAGE = v2882.ROOT / "workspace/private/inputs/boot_images/boot_linux_v2885_av_sync_stream.img"
CANDIDATE_VERSION = "0.10.28"
CANDIDATE_TAG = "v2885-av-sync-stream"
CANDIDATE_SHA256 = "80317b1fe1972c0bb28afec23714c6d959caa4e5454a6c9b79bbb21a807236d4"
REPORT_PATH = v2882.ROOT / "docs/reports/NATIVE_INIT_V2886_AV_SYNC_STREAM_LIVE_2026-06-19.md"
REMOTE_AV_ROOT = "/mnt/sdext/a90/runtime/av/v2886"
REMOTE_VIDEO_DIR = f"{REMOTE_AV_ROOT}/video"
REMOTE_VIDEO_MANIFEST = f"{REMOTE_VIDEO_DIR}/manifest.json"
REMOTE_VIDEO_STREAM = f"{REMOTE_VIDEO_DIR}/frames.a90vstr"
REMOTE_AUDIO_DIR = "/cache/a90-runtime/pkg/av/v2886/audio"
REMOTE_AUDIO_PCM = f"{REMOTE_AUDIO_DIR}/tone.s16le"
SYNC_STATUS_PATH = "/cache/a90-audio-play/status.txt"
SYNC_WAIT_MS = 90000
DEFAULT_SYNC_FRAMES = 2


def patch_base_module() -> None:
    v2882.RUN_ID = RUN_ID
    v2882.CANDIDATE_IMAGE = CANDIDATE_IMAGE
    v2882.CANDIDATE_VERSION = CANDIDATE_VERSION
    v2882.CANDIDATE_TAG = CANDIDATE_TAG
    v2882.CANDIDATE_SHA256 = CANDIDATE_SHA256
    v2882.REPORT_PATH = REPORT_PATH
    v2882.REMOTE_AV_ROOT = REMOTE_AV_ROOT
    v2882.REMOTE_VIDEO_DIR = REMOTE_VIDEO_DIR
    v2882.REMOTE_VIDEO_MANIFEST = REMOTE_VIDEO_MANIFEST
    v2882.REMOTE_VIDEO_STREAM = REMOTE_VIDEO_STREAM
    v2882.REMOTE_AUDIO_DIR = REMOTE_AUDIO_DIR
    v2882.REMOTE_AUDIO_PCM = REMOTE_AUDIO_PCM
    v2882.VIDEO_EXTRA_ARGS = ["--sync-audio-status", SYNC_STATUS_PATH, "--sync-wait-ms", str(SYNC_WAIT_MS)]
    v2882.classify_av_result = classify_av_result
    v2882.render_report = render_report


def marker_int(text: str, marker: str) -> int | None:
    match = re.search(rf"(?:^|\b){re.escape(marker)}=(-?\d+)\b", text, re.MULTILINE)
    if not match:
        return None
    try:
        return int(match.group(1))
    except ValueError:
        return None


def sync_summary(video_text: str, audio_timeline: dict[str, Any]) -> dict[str, Any]:
    video_begin = marker_int(video_text, "video.stream.audio_sync.listen_begin_ns")
    audio_begin = audio_timeline.get("listen_begin_ns")
    sample_rate = marker_int(video_text, "video.stream.audio_sync.sample_rate")
    frame_bytes = marker_int(video_text, "video.stream.audio_sync.frame_bytes")
    total_frames = marker_int(video_text, "video.stream.audio_sync.total_frames")
    expected_duration_ns = marker_int(video_text, "video.stream.audio_sync.expected_duration_ns")
    requested = marker_int(video_text, "video.stream.requested_audio_sync")
    enabled = marker_int(video_text, "video.stream.audio_sync.enabled")
    ready = marker_int(video_text, "video.stream.audio_sync.ready")
    wait_ms = marker_int(video_text, "video.stream.audio_sync.wait_ms")
    requested_wait_ms = marker_int(video_text, "video.stream.requested_audio_sync_wait_ms")
    ready_elapsed_ms = marker_int(video_text, "video.stream.audio_sync.ready_elapsed_ms")
    anchor_age_ns = marker_int(video_text, "video.stream.audio_sync.anchor_age_ns")
    begin_match = isinstance(audio_begin, int) and isinstance(video_begin, int) and audio_begin == video_begin
    return {
        "requested": requested,
        "enabled": enabled,
        "ready": ready,
        "wait_ms": wait_ms,
        "requested_wait_ms": requested_wait_ms,
        "ready_elapsed_ms": ready_elapsed_ms,
        "listen_begin_ns": video_begin,
        "audio_timeline_listen_begin_ns": audio_begin,
        "listen_begin_matches_audio": begin_match,
        "anchor_age_ns": anchor_age_ns,
        "sample_rate": sample_rate,
        "frame_bytes": frame_bytes,
        "total_frames": total_frames,
        "expected_duration_ns": expected_duration_ns,
        "status_path_marker": f"video.stream.audio_sync.status_path={SYNC_STATUS_PATH}" in video_text,
        "requested_status_path_marker": f"video.stream.requested_audio_sync_status={SYNC_STATUS_PATH}" in video_text,
        "geometry_ok": sample_rate == 48000 and frame_bytes == 4 and total_frames == 144000,
        "duration_ok": expected_duration_ns == 3000000000,
        "wait_ok": wait_ms == SYNC_WAIT_MS and requested_wait_ms == SYNC_WAIT_MS,
        "anchor_age_present": anchor_age_ns is not None and anchor_age_ns >= 0,
    }


def sync_stream_pass(sync: dict[str, Any]) -> bool:
    return bool(
        sync.get("requested") == 1
        and sync.get("enabled") == 1
        and sync.get("ready") == 1
        and sync.get("status_path_marker")
        and sync.get("requested_status_path_marker")
        and sync.get("listen_begin_matches_audio")
        and sync.get("geometry_ok")
        and sync.get("duration_ok")
        and sync.get("wait_ok")
        and sync.get("anchor_age_present")
    )


def classify_av_result(video_text: str, audio_text: str, expected_frames: int) -> dict[str, Any]:
    base_summary = v2882.audio_live.classify_pcm_output(audio_text)
    video_summary = v2882.video_live.classify_stream_output(video_text, expected_frames)
    duration_ms = marker_int(audio_text, "audio.play.worker.duration_ms") or 3000
    timeline = v2884.classify_timeline(audio_text, video_text, duration_ms, expected_frames)
    sync = sync_summary(video_text, timeline)
    audio_pass = v2882.audio_live.pcm_output_pass(base_summary)
    video_pass = bool(video_summary.get("pass"))
    timeline_pass = v2884.timeline_pass(timeline)
    sync_pass = audio_pass and video_pass and timeline_pass and sync_stream_pass(sync)
    return {
        "video": video_summary,
        "audio": base_summary,
        "timeline": timeline,
        "sync_stream": sync,
        "video_pass": video_pass,
        "audio_pass": audio_pass,
        "timeline_pass": timeline_pass,
        "sync_stream_pass": sync_pass,
        "corun_smoke_pass": audio_pass and video_pass and timeline_pass and sync_stream_pass(sync),
    }


def render_report(result: dict[str, Any]) -> str:
    fixtures = result.get("fixtures") or {}
    video_fixture = fixtures.get("video") or {}
    audio_fixture = fixtures.get("audio") or {}
    install = result.get("runtime_install") or {}
    av = result.get("av_summary") or {}
    video_summary = av.get("video") or {}
    timeline = av.get("timeline") or {}
    sync = av.get("sync_stream") or {}
    installed = install.get("installed", []) if isinstance(install.get("installed"), list) else []
    installed_lines = [
        f"- `{item.get('name')}` -> `{item.get('remote')}` ok=`{int(bool(item.get('ok')))}`"
        for item in installed
    ] or ["- none"]
    timeline_lines = [f"- `{key}`: `{value}`" for key, value in sorted(timeline.items())]
    sync_lines = [f"- `{key}`: `{value}`" for key, value in sorted(sync.items())]
    return "\n".join([
        "# Native Init V2886 A/V Sync Stream Live Handoff",
        "",
        "## Summary",
        "",
        f"- Cycle: `{RUN_ID}`",
        "- Track: active Video playback pipeline on existing KMS display.",
        f"- Decision: `{result.get('decision')}`",
        f"- Result: `{'PASS' if result.get('pass') and av.get('sync_stream_pass') else 'FAIL'}`",
        f"- Candidate: `{CANDIDATE_TAG}` / `{CANDIDATE_VERSION}`",
        f"- Candidate SHA256: `{CANDIDATE_SHA256}`",
        f"- Rollback attempted: `{int(bool(result.get('rollback_attempted')))}`",
        f"- Rollback health: version_ok=`{int(bool(result.get('rollback_version_ok')))}` selftest_fail0=`{int(bool(result.get('rollback_selftest_fail0')))}`",
        "",
        "## Scope",
        "",
        "- This validates audio-anchored video scheduling, not subjective lip-sync quality.",
        "- The video stream waits for the audio worker status file and anchors frame deadlines to `listen_begin_ns`.",
        "- Operator visual observation during this class of run: full-screen checkerboard alternated quickly, matching the page-flip test pattern.",
        "- No Venus, KGSL, raw DSI, panel init, backlight, PMIC, PWM, regulator, GPIO, or GDSC path is used.",
        "",
        "## Fixtures",
        "",
        f"- Video manifest: `{video_fixture.get('manifest_path')}`",
        f"- Video stream: `{video_fixture.get('stream_path')}`",
        f"- Video SHA256: `{video_fixture.get('sha256')}`",
        f"- Video frame bytes / stream bytes: `{video_fixture.get('frame_bytes')}` / `{video_fixture.get('stream_bytes')}`",
        f"- Audio PCM: `{audio_fixture.get('path')}`",
        f"- Audio SHA256: `{audio_fixture.get('sha256')}`",
        f"- Audio duration / amplitude: `{audio_fixture.get('duration_ms')}` ms / `{audio_fixture.get('amplitude_milli')}` milli",
        "",
        "## Runtime Install",
        "",
        f"- Selected transport/control: `{install.get('selected_transport')}` / `{install.get('control_channel')}`",
        f"- Remote audio SHA matched: `{int(bool(install.get('remote_audio_sha_match')))}`",
        *installed_lines,
        "",
        "## Co-run Evidence",
        "",
        f"- Audio execute stdout: `{result.get('audio_execute_stdout_path')}`",
        f"- Video stream stdout: `{result.get('video_stream_stdout_path')}`",
        f"- Audio worker status stdout: `{result.get('audio_worker_status_stdout_path')}`",
        f"- Audio worker log stdout: `{result.get('audio_worker_log_stdout_path')}`",
        f"- Audio command elapsed seconds: `{result.get('audio_execute_elapsed_sec')}`",
        f"- Video stream elapsed seconds: `{result.get('video_stream_elapsed_sec')}`",
        f"- Audio worker done/attempts: `{int(bool(result.get('audio_worker_done')))}` / `{result.get('audio_worker_attempts')}`",
        f"- Video presented/expected: `{video_summary.get('presented')}` / `{video_summary.get('expected_frames')}`",
        f"- Video flip events/expected: `{video_summary.get('flip_events')}` / `{video_summary.get('expected_frames')}`",
        f"- Audio pass: `{int(bool(av.get('audio_pass')))}`",
        f"- Video pass: `{int(bool(av.get('video_pass')))}`",
        f"- Timeline pass: `{int(bool(av.get('timeline_pass')))}`",
        f"- Sync-stream pass: `{int(bool(av.get('sync_stream_pass')))}`",
        "",
        "## Sync Stream Markers",
        "",
        *sync_lines,
        "",
        "## Timeline Markers",
        "",
        *timeline_lines,
        "",
        "## Safety",
        "",
        "- Flash path: `workspace/public/src/scripts/revalidation/native_init_flash.py`.",
        "- Only the boot partition is flashed, then rolled back to `v2321`.",
        f"- Video runtime payloads stage under `{REMOTE_AV_ROOT}` to avoid `/cache` saturation.",
        f"- Audio PCM stages under `{REMOTE_AUDIO_DIR}` because native `audio play --pcm-file` allows the cache runtime path.",
        "- Generated fixture bytes stay private and are cleaned from the device after validation.",
        "- Audio amplitude and duration remain within source-enforced profile caps.",
        "- Video uses the existing KMS dumb-buffer page-flip path only.",
        "",
    ])


def normalize_decision(result: dict[str, Any]) -> None:
    decision = result.get("decision")
    if isinstance(decision, str) and decision.startswith("v2882-"):
        result["decision"] = decision.replace("v2882-", "v2886-", 1)


def main() -> int:
    patch_base_module()
    v2882.patch_child_module_paths()
    args = v2882.parse_args()
    if "--frames" not in sys.argv:
        args.frames = DEFAULT_SYNC_FRAMES
    state = v2882.preflight_state(args)
    if args.dry_run:
        payload = v2882.dry_run_payload(args, state)
        payload["run_id"] = RUN_ID
        payload["candidate_tag"] = CANDIDATE_TAG
        payload["sync_stream_required"] = True
        payload["sync_status_path"] = SYNC_STATUS_PATH
        payload["sync_wait_ms"] = SYNC_WAIT_MS
        if isinstance(payload.get("decision"), str):
            payload["decision"] = str(payload["decision"]).replace("v2882-", "v2886-", 1)
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        return 0 if v2882.preflight_ok(state) else 2
    result = v2882.live_run(args, state)
    normalize_decision(result)
    out_dir_value = result.get("out_dir")
    if isinstance(out_dir_value, str) and out_dir_value:
        out_dir = v2882.ROOT / out_dir_value
        v2882.write_json(out_dir / "result.json", result)
    REPORT_PATH.write_text(render_report(result), encoding="utf-8")
    av = result.get("av_summary") or {}
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if (
        result.get("decision") == "v2886-av-corun-live-pass-before-rollback"
        and result.get("rollback_selftest_fail0")
        and av.get("sync_stream_pass")
    ) else 1


if __name__ == "__main__":
    raise SystemExit(main())
