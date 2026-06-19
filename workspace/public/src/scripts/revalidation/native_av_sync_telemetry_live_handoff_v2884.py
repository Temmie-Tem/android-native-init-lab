#!/usr/bin/env python3
"""V2884 live validation for V2883 A/V sync telemetry.

This reuses the V2882 PCM-file audio + page-flip video co-run envelope, but
flashes the V2883 candidate and requires audio timeline markers in the worker
status/log. It proves the next sync unit has both inputs: audio listen_begin_ns
with sample/frame geometry and DRM page-flip event telemetry.
"""

from __future__ import annotations

import json
import re
from typing import Any

import native_av_pcm_video_corun_live_handoff_v2882 as v2882

RUN_ID = "V2884"
CANDIDATE_IMAGE = v2882.ROOT / "workspace/private/inputs/boot_images/boot_linux_v2883_av_sync_telemetry.img"
CANDIDATE_VERSION = "0.10.27"
CANDIDATE_TAG = "v2883-av-sync-telemetry"
CANDIDATE_SHA256 = "8bd3931850850aaa871a5765a0c22aa851e8c2a2c4efd815dfb61c7b5ff64c53"
REPORT_PATH = v2882.ROOT / "docs/reports/NATIVE_INIT_V2884_AV_SYNC_TELEMETRY_LIVE_2026-06-19.md"
REMOTE_AV_ROOT = "/cache/a90-runtime/pkg/av/v2884"
REMOTE_VIDEO_DIR = f"{REMOTE_AV_ROOT}/video"
REMOTE_VIDEO_MANIFEST = f"{REMOTE_VIDEO_DIR}/manifest.json"
REMOTE_VIDEO_STREAM = f"{REMOTE_VIDEO_DIR}/frames.a90vstr"
REMOTE_AUDIO_DIR = f"{REMOTE_AV_ROOT}/audio"
REMOTE_AUDIO_PCM = f"{REMOTE_AUDIO_DIR}/tone.s16le"


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


def classify_timeline(text: str, video_text: str, duration_ms: int, expected_frames: int) -> dict[str, Any]:
    sample_rate = marker_int(text, "audio.play.worker.sample_rate")
    channels = marker_int(text, "audio.play.worker.channels")
    bit_width = marker_int(text, "audio.play.worker.bit_width")
    frame_bytes = marker_int(text, "audio.play.worker.frame_bytes")
    total_frames = marker_int(text, "audio.play.worker.total_frames")
    total_bytes = marker_int(text, "audio.play.worker.total_bytes")
    frames_done = marker_int(text, "audio.play.worker.frames_done")
    bytes_done = marker_int(text, "audio.play.worker.bytes_done")
    begin_ns = marker_int(text, "audio.play.worker.listen_begin_ns")
    end_ns = marker_int(text, "audio.play.worker.listen_end_ns")
    expected_duration_ns = marker_int(text, "audio.play.worker.expected_duration_ns")
    video_timestamp_us = marker_int(video_text, "video.stream.last_timestamp_us")
    expected_audio_frames = (48000 * duration_ms) // 1000
    timeline_elapsed_ns = (end_ns - begin_ns) if begin_ns is not None and end_ns is not None else None
    return {
        "timeline_version": "audio.play.worker.timeline.version=1" in text,
        "sample_rate": sample_rate,
        "channels": channels,
        "bit_width": bit_width,
        "frame_bytes": frame_bytes,
        "total_frames": total_frames,
        "total_bytes": total_bytes,
        "frames_done": frames_done,
        "bytes_done": bytes_done,
        "listen_begin_ns": begin_ns,
        "listen_end_ns": end_ns,
        "timeline_elapsed_ns": timeline_elapsed_ns,
        "expected_duration_ns": expected_duration_ns,
        "expected_audio_frames": expected_audio_frames,
        "video_last_timestamp_us": video_timestamp_us,
        "video_expected_frames": expected_frames,
        "begin_valid": begin_ns is not None and begin_ns > 0,
        "end_valid": end_ns is not None and begin_ns is not None and end_ns >= begin_ns,
        "geometry_ok": sample_rate == 48000 and channels == 2 and bit_width == 16 and frame_bytes == 4,
        "frame_count_ok": total_frames == expected_audio_frames and frames_done == expected_audio_frames,
        "byte_count_ok": total_bytes == expected_audio_frames * 4 and bytes_done == expected_audio_frames * 4,
        "duration_marker_ok": expected_duration_ns == (expected_audio_frames * 1000000000) // 48000,
        "video_flip_clock_present": video_timestamp_us is not None and video_timestamp_us >= 0,
    }


def timeline_pass(timeline: dict[str, Any]) -> bool:
    return bool(
        timeline.get("timeline_version")
        and timeline.get("begin_valid")
        and timeline.get("end_valid")
        and timeline.get("geometry_ok")
        and timeline.get("frame_count_ok")
        and timeline.get("byte_count_ok")
        and timeline.get("duration_marker_ok")
        and timeline.get("video_flip_clock_present")
    )


def classify_av_result(video_text: str, audio_text: str, expected_frames: int) -> dict[str, Any]:
    base_summary = v2882.audio_live.classify_pcm_output(audio_text)
    video_summary = v2882.video_live.classify_stream_output(video_text, expected_frames)
    duration_ms = marker_int(audio_text, "audio.play.worker.duration_ms") or 3000
    timeline = classify_timeline(audio_text, video_text, duration_ms, expected_frames)
    audio_pass = v2882.audio_live.pcm_output_pass(base_summary)
    video_pass = bool(video_summary.get("pass"))
    sync_pass = audio_pass and video_pass and timeline_pass(timeline)
    return {
        "video": video_summary,
        "audio": base_summary,
        "timeline": timeline,
        "video_pass": video_pass,
        "audio_pass": audio_pass,
        "timeline_pass": timeline_pass(timeline),
        "sync_telemetry_pass": sync_pass,
        "corun_smoke_pass": audio_pass and video_pass,
    }


def render_report(result: dict[str, Any]) -> str:
    fixtures = result.get("fixtures") or {}
    video_fixture = fixtures.get("video") or {}
    audio_fixture = fixtures.get("audio") or {}
    install = result.get("runtime_install") or {}
    av = result.get("av_summary") or {}
    video_summary = av.get("video") or {}
    audio_summary = av.get("audio") or {}
    timeline = av.get("timeline") or {}
    installed = install.get("installed", []) if isinstance(install.get("installed"), list) else []
    installed_lines = [
        f"- `{item.get('name')}` -> `{item.get('remote')}` ok=`{int(bool(item.get('ok')))}`"
        for item in installed
    ] or ["- none"]
    audio_lines = [f"- `{key}`: `{int(bool(value))}`" for key, value in sorted(audio_summary.items())]
    timeline_lines = [
        f"- `{key}`: `{value}`" for key, value in sorted(timeline.items())
    ] or ["- No timeline summary recorded."]
    return "\n".join([
        "# Native Init V2884 A/V Sync Telemetry Live Handoff",
        "",
        "## Summary",
        "",
        f"- Cycle: `{RUN_ID}`",
        "- Track: active Video playback pipeline on existing KMS display.",
        f"- Decision: `{result.get('decision')}`",
        f"- Result: `{'PASS' if result.get('pass') and av.get('sync_telemetry_pass') else 'FAIL'}`",
        f"- Candidate: `{CANDIDATE_TAG}` / `{CANDIDATE_VERSION}`",
        f"- Candidate SHA256: `{CANDIDATE_SHA256}`",
        f"- Rollback attempted: `{int(bool(result.get('rollback_attempted')))}`",
        f"- Rollback health: version_ok=`{int(bool(result.get('rollback_version_ok')))}` selftest_fail0=`{int(bool(result.get('rollback_selftest_fail0')))}`",
        "",
        "## Scope",
        "",
        "- This is still an A/V co-run smoke, not exact sync playback.",
        "- The new claim is narrower: audio timeline markers and video page-flip markers are both present in the same boot/run.",
        "- That closes the telemetry prerequisite for a future native sync loop that schedules frames from audio position.",
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
        f"- Audio peak absolute sample: `{audio_fixture.get('peak_abs_sample')}`",
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
        f"- Video page-flip path marker: `{int(bool(video_summary.get('path_ok')))}`",
        f"- Audio pass: `{int(bool(av.get('audio_pass')))}`",
        f"- Video pass: `{int(bool(av.get('video_pass')))}`",
        f"- Timeline pass: `{int(bool(av.get('timeline_pass')))}`",
        f"- Sync telemetry pass: `{int(bool(av.get('sync_telemetry_pass')))}`",
        "",
        "## Timeline Markers",
        "",
        *timeline_lines,
        "",
        "## Audio Markers",
        "",
        *(audio_lines or ["- No audio marker summary recorded."]),
        "",
        "## Safety",
        "",
        "- Flash path: `workspace/public/src/scripts/revalidation/native_init_flash.py`.",
        "- Only the boot partition is flashed, then rolled back to `v2321`.",
        f"- Runtime payloads stay under `{REMOTE_AV_ROOT}`; generated fixture bytes stay private.",
        "- Before staging, stale V2884 runtime payloads are removed to avoid partial-transfer cache exhaustion.",
        "- Audio amplitude and duration remain within source-enforced profile caps.",
        "- Video uses the existing KMS dumb-buffer page-flip path only.",
        "- No Venus, KGSL, raw DSI, panel init, backlight, PMIC, PWM, regulator, GPIO, or GDSC path is used.",
        "",
    ])


def normalize_decision(result: dict[str, Any]) -> None:
    decision = result.get("decision")
    if isinstance(decision, str) and decision.startswith("v2882-"):
        result["decision"] = decision.replace("v2882-", "v2884-", 1)


def main() -> int:
    patch_base_module()
    v2882.patch_child_module_paths()
    args = v2882.parse_args()
    state = v2882.preflight_state(args)
    if args.dry_run:
        payload = v2882.dry_run_payload(args, state)
        payload["run_id"] = RUN_ID
        payload["candidate_tag"] = CANDIDATE_TAG
        payload["timeline_required"] = True
        if isinstance(payload.get("decision"), str):
            payload["decision"] = str(payload["decision"]).replace("v2882-", "v2884-", 1)
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
        result.get("decision") == "v2884-av-corun-live-pass-before-rollback"
        and result.get("rollback_selftest_fail0")
        and av.get("sync_telemetry_pass")
    ) else 1


if __name__ == "__main__":
    raise SystemExit(main())
