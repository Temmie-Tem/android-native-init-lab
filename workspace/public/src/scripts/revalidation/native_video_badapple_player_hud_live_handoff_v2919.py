#!/usr/bin/env python3
"""V2919 live validation for the real Bad Apple Player HUD SD-cache path.

This unit assumes the V2917 feature image is already resident. It does not flash.
It seeds the private V2903 full-song Bad Apple A90VSTR1 stream into the
SHA-addressed SD video cache, verifies the cache through the native `video demo
badapple` shortcut, then plays a bounded Player HUD slice.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import native_video_cache_command_live_handoff_v2906 as v2906
import native_video_gray8_stream_live_handoff_v2893 as video_live

base = video_live.base

RUN_ID = "V2919"
BUILD_TAG = "v2919-badapple-player-hud-live"
DECISION_PREFIX = "v2919-badapple-player-hud"
REPORT_PATH = video_live.ROOT / "docs/reports/NATIVE_INIT_V2919_BADAPPLE_PLAYER_HUD_LIVE_2026-06-20.md"

CANDIDATE_VERSION = "0.10.38"
CANDIDATE_TAG = "v2917-badapple-player-hud"
ASSET_ROOT = video_live.ROOT / "workspace/private/demo-assets/video/v2903-badapple-480x360-full"
LOCAL_MANIFEST = ASSET_ROOT / "video-stream/manifest.json"
LOCAL_STREAM = ASSET_ROOT / "video-stream/frames.a90vstr"
LOCAL_AUDIO = ASSET_ROOT / "audio/audio.s16le"

BADAPPLE_SHA256 = "9e938aa83ef40aa692d0f42080821dc21a627f1dddd90cc9c2696aafe6ac6eb0"
BADAPPLE_AUDIO_SHA256 = "b96d2e0bc4bb6b0ada0da6e63e40168115e3818d72c386dd8764162e85238a75"
BADAPPLE_FRAMES_TOTAL = 6962
BADAPPLE_PLAY_FRAMES = 300
BADAPPLE_FORMAT = "mono1"
PRESET_NAME = "badapple"

video_live.REMOTE_DIR = "/mnt/sdext/a90/runtime/video/v2919"
video_live.REMOTE_MANIFEST = f"{video_live.REMOTE_DIR}/manifest.json"
video_live.REMOTE_STREAM = f"{video_live.REMOTE_DIR}/frames.a90vstr"


def now_slug() -> str:
    return datetime.now(timezone.utc).astimezone().strftime("%Y%m%d-%H%M%S")


def marker_int(text: str, marker: str) -> int | None:
    match = re.search(rf"(?:^|\b){re.escape(marker)}=(-?\d+)\b", text, re.MULTILINE)
    if not match:
        return None
    try:
        return int(match.group(1))
    except ValueError:
        return None


def stdout_of(step: dict[str, Any]) -> str:
    return video_live.stdout_of(step)


def all_true(mapping: dict[str, Any]) -> bool:
    return all(bool(value) for value in mapping.values())


def read_asset_manifest() -> dict[str, Any]:
    return json.loads(LOCAL_MANIFEST.read_text(encoding="utf-8"))


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


def preflight_state(args: argparse.Namespace) -> dict[str, Any]:
    asset_manifest: dict[str, Any] = {}
    asset_manifest_ok = False
    try:
        asset_manifest = read_asset_manifest()
        video = asset_manifest.get("video", {}) if isinstance(asset_manifest.get("video"), dict) else {}
        asset_manifest_ok = bool(
            video.get("sha256") == BADAPPLE_SHA256
            and int(video.get("frame_count", -1)) == BADAPPLE_FRAMES_TOTAL
            and video.get("format") == BADAPPLE_FORMAT
            and int(video.get("width", -1)) == 480
            and int(video.get("height", -1)) == 360
        )
    except Exception as exc:  # noqa: BLE001 - report preflight failure in JSON
        asset_manifest = {"error": f"{type(exc).__name__}: {exc}"}
    return {
        "run_id": RUN_ID,
        "candidate_required": f"A90 Linux init {CANDIDATE_VERSION} ({CANDIDATE_TAG})",
        "asset_manifest": file_state(LOCAL_MANIFEST),
        "asset_stream": file_state(LOCAL_STREAM, BADAPPLE_SHA256),
        "asset_audio": file_state(LOCAL_AUDIO, BADAPPLE_AUDIO_SHA256),
        "asset_manifest_ok": asset_manifest_ok,
        "asset_manifest_payload": asset_manifest,
        "remote_cache_root": video_live.REMOTE_CACHE_ROOT,
        "remote_cache_dir": video_live.remote_cache_dir(BADAPPLE_SHA256),
        "play_frames": int(args.frames),
        "chunk_large_streams": True,
        "stream_chunk_bytes": int(args.stream_chunk_bytes),
        "hard_boundary": [
            "no flash in this unit; V2917 must already be resident",
            "boot partition untouched",
            "private raw frames/audio remain untracked",
            "video playback only in this unit; full PCM audio file integration remains parked",
            "KMS dumb-buffer/page-flip path only",
            "no Venus/GPU/raw DSI/backlight/PMIC/PWM/regulator/GPIO/GDSC writes",
        ],
    }


def preflight_ok(state: dict[str, Any]) -> bool:
    return bool(
        state["asset_manifest"].get("exists")
        and state["asset_stream"].get("sha256_ok")
        and state["asset_audio"].get("sha256_ok")
        and state.get("asset_manifest_ok")
    )


def fixture_from_asset() -> dict[str, Any]:
    manifest = read_asset_manifest()
    video = manifest["video"]
    return {
        "asset_id": "badapple-480x360-full-v2903",
        "manifest_path": video_live.rel(LOCAL_MANIFEST),
        "stream_path": video_live.rel(LOCAL_STREAM),
        "sha256": BADAPPLE_SHA256,
        "format": video["format"],
        "frames": int(video["frame_count"]),
        "width": int(video["width"]),
        "height": int(video["height"]),
        "stride": int(video["stride"]),
        "frame_bytes": int(video["frame_bytes"]),
        "manifest_sha256": video_live.sha256_file(LOCAL_MANIFEST),
        "stream_size": LOCAL_STREAM.stat().st_size,
    }


def cache_status_summary(text: str) -> dict[str, Any]:
    return {
        "manifest_ok": "video.cache.manifest_ok=1" in text,
        "stream_exists": "video.cache.stream_exists=1" in text,
        "stream_size_match": "video.cache.stream_size_match=1" in text,
        "frames_ok": f"video.cache.frames={BADAPPLE_FRAMES_TOTAL}" in text,
        "format_ok": "video.cache.format=mono1" in text,
        "sha_ok": f"video.cache.sha256={BADAPPLE_SHA256}" in text,
        "size_ok": "video.cache.size=480x360" in text,
        "frame_bytes_ok": "video.cache.frame_bytes=21600" in text,
    }


def cache_verify_summary(text: str) -> dict[str, Any]:
    return {
        "sha_checked": "video.cache.verify.sha256_checked=1" in text,
        "sha_match": "video.cache.verify.sha256_match=1" in text,
        "expected_sha": f"video.cache.verify.expected_sha256={BADAPPLE_SHA256}" in text,
        "actual_sha": f"video.cache.verify.actual_sha256={BADAPPLE_SHA256}" in text,
    }


def preset_summary(text: str) -> dict[str, Any]:
    return {
        "preset": f"video.cache.preset={PRESET_NAME}" in text,
        "asset_id": "video.cache.preset.asset_id=badapple-480x360-full-v2903" in text,
        "sha256": f"video.cache.preset.sha256={BADAPPLE_SHA256}" in text,
    }


def demo_summary(text: str) -> dict[str, Any]:
    return {
        "preset": f"video.demo.preset={PRESET_NAME}" in text,
        "asset_id": "video.demo.asset_id=badapple-480x360-full-v2903" in text,
        "storage": "video.demo.storage=sd-sha-cache" in text,
        "boot_asset_policy": "video.demo.boot_asset_policy=boot-image-carries-player-not-frames" in text,
    }


def trust_cache_summary(text: str) -> dict[str, Any]:
    return {
        "trust_cache": "video.cache.play.trust_cache=1" in text,
        "sha_checked_zero": "video.cache.verify.sha256_checked=0" in text,
        "sha_match_zero": "video.cache.verify.sha256_match=0" in text,
        "actual_not_checked": "video.cache.verify.actual_sha256=trust-cache-not-checked" in text,
        "default_verify_not_repeated": f"video.cache.verify.actual_sha256={BADAPPLE_SHA256}" not in text,
    }


def classify_play(text: str, expected_frames: int) -> dict[str, Any]:
    stream = video_live.classify_stream_output(text, expected_frames, BADAPPLE_FORMAT)
    presented = marker_int(text, "video.stream.presented") or 0
    dropped = marker_int(text, "video.stream.dropped_frames")
    if dropped is None:
        dropped = -1
    flip_events = marker_int(text, "video.stream.flip_events") or 0
    accounted = presented + max(dropped, 0)
    preset = preset_summary(text)
    demo = demo_summary(text)
    trust = trust_cache_summary(text)
    requested_present = "video.cache.play.requested_present=pageflip" in text
    requested_layout = "video.cache.play.requested_layout=player-hud" in text
    stream_layout = "video.stream.layout=player-hud" in text
    stream_requested_layout = None
    stream.update({
        "presented": presented,
        "dropped_frames": dropped,
        "accounted_frames": accounted,
        "frame_accounting_ok": dropped >= 0 and accounted == expected_frames and presented >= 1,
        "flip_accounting_ok": flip_events == presented,
        "requested_present_cache_marker": requested_present,
        "requested_layout_cache_marker": requested_layout,
        "stream_layout_marker": stream_layout,
        "stream_requested_layout_marker": stream_requested_layout,
        "stream_requested_layout_marker_required": False,
        "preset": preset,
        "preset_pass": all_true(preset),
        "demo": demo,
        "demo_pass": all_true(demo),
        "trust_cache": trust,
        "trust_cache_pass": all_true(trust),
        "pass": bool(
            requested_present
            and requested_layout
            and stream_layout
            and all_true(preset)
            and all_true(demo)
            and all_true(trust)
            and dropped >= 0
            and accounted == expected_frames
            and presented >= 1
            and flip_events == presented
            and stream.get("cadence_target_present")
            and stream.get("pixel_format")
            and stream.get("present_pageflip")
            and stream.get("path_ok")
        ),
    })
    return stream


def render_report(result: dict[str, Any]) -> str:
    install = result.get("runtime_install", {}) if isinstance(result.get("runtime_install"), dict) else {}
    status = result.get("cache_status_summary", {}) if isinstance(result.get("cache_status_summary"), dict) else {}
    verify = result.get("cache_verify_summary", {}) if isinstance(result.get("cache_verify_summary"), dict) else {}
    play = result.get("cache_play_summary", {}) if isinstance(result.get("cache_play_summary"), dict) else {}
    return "\n".join([
        "# Native Init V2919 Bad Apple Player HUD Live Validation",
        "",
        "## Summary",
        "",
        f"- Decision: `{result.get('decision')}`",
        f"- Result: `{int(bool(result.get('pass')))}`",
        f"- Resident candidate: `{CANDIDATE_VERSION}` / `{CANDIDATE_TAG}`",
        f"- Asset SHA256: `{BADAPPLE_SHA256}`",
        f"- Play slice: `{result.get('play_frames')}` frames",
        "- Device flash: `no` in this unit; V2917 was already resident.",
        "- Rollback: not required; no boot partition change was performed.",
        "",
        "## SD Cache Seed",
        "",
        f"- Cache dir: `{install.get('cache_dir')}`",
        f"- Cache source: `{install.get('cache_source')}`",
        f"- Cache hit before upload: `{int(bool(install.get('cache_hit')))}`",
        f"- Cache uploaded: `{int(bool(install.get('cache_uploaded')))}`",
        f"- Selected transport: `{install.get('selected_transport')}` control=`{install.get('control_channel')}`",
        f"- Stream chunks: `{install.get('installed', [{}])[-1].get('chunks', 'n/a') if install.get('installed') else 'n/a'}`",
        "",
        "## Command Results",
        "",
        f"- `video demo badapple status`: rc=`{result.get('cache_status_rc')}` summary=`{status}`",
        f"- `video demo badapple verify`: rc=`{result.get('cache_verify_rc')}` summary=`{verify}`",
        f"- `video demo badapple play --trust-cache --layout player-hud`: rc=`{result.get('cache_play_rc')}` pass=`{int(bool(play.get('pass')))}`",
        f"- Frame accounting: presented=`{play.get('presented')}` dropped=`{play.get('dropped_frames')}` accounted=`{play.get('accounted_frames')}`",
        f"- Layout markers: cache=`{int(bool(play.get('requested_layout_cache_marker')))}` stream=`{int(bool(play.get('stream_layout_marker')))}` requested_marker_required=`{int(bool(play.get('stream_requested_layout_marker_required')))}`",
        "",
        "## Safety",
        "",
        "- Raw frames/audio remained private and untracked.",
        "- No boot flash, forbidden partition write, Venus/GPU/raw DSI/backlight/PMIC/PWM/regulator/GPIO/GDSC path was used.",
        "- This unit validates video-only Player HUD rendering. Full Bad Apple PCM-file launch remains a later bounded audio-file policy unit.",
        "",
        "## Evidence",
        "",
        f"- Result JSON: `{result.get('result_json')}`",
        f"- Output dir: `{result.get('out_dir')}`",
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
        result["resident_version_ok"] = f"A90 Linux init {CANDIDATE_VERSION} ({CANDIDATE_TAG})" in stdout_of(version)
        result["resident_status_ok"] = bool(status.get("ok"))
        result["resident_selftest_fail0"] = video_live.selftest_step_ok(selftest)
        result["resident_video_status_player_hud"] = "--layout full|player-hud" in stdout_of(video_status) and "video demo [badapple|badapple-scale]" in stdout_of(video_status)
        if not (result["resident_version_ok"] and result["resident_status_ok"] and result["resident_selftest_fail0"] and result["resident_video_status_player_hud"]):
            result["decision"] = f"{DECISION_PREFIX}-resident-preflight-failed"
            raise RuntimeError("resident V2917 Player HUD health failed")

        fixture = fixture_from_asset()
        result["fixture"] = fixture
        result["runtime_install"] = video_live.install_fixture(args, out_dir, steps, fixture)
        install = result["runtime_install"]
        if not (install.get("cache_hit") or install.get("cache_uploaded") or install.get("cache_adopted")):
            result["decision"] = f"{DECISION_PREFIX}-cache-seed-failed"
            raise RuntimeError("V2903 stream was not available in SHA-addressed SD cache")

        base.run_serial_step(out_dir, steps, "resident-hide-menu-before-badapple", ["hide"], timeout=45.0, allow_error=True, retry_unsafe=True)
        status_step = base.run_serial_step(out_dir, steps, "resident-video-demo-badapple-status", ["video", "demo", PRESET_NAME, "status"], timeout=120.0, allow_error=True, retry_unsafe=False)
        status_text = stdout_of(status_step)
        result["cache_status_rc"] = status_step.get("rc")
        result["cache_status_stdout_path"] = status_step.get("stdout_path")
        result["cache_status_summary"] = cache_status_summary(status_text)
        result["cache_status_preset_summary"] = preset_summary(status_text)
        result["cache_status_demo_summary"] = demo_summary(status_text)
        if status_step.get("rc") != 0 or not all_true(result["cache_status_summary"]) or not all_true(result["cache_status_preset_summary"]) or not all_true(result["cache_status_demo_summary"]):
            result["decision"] = f"{DECISION_PREFIX}-cache-status-failed"
            raise RuntimeError("video demo badapple status did not emit required markers")

        verify_step = base.run_serial_step(out_dir, steps, "resident-video-demo-badapple-verify", ["video", "demo", PRESET_NAME, "verify"], timeout=600.0, allow_error=True, retry_unsafe=False)
        verify_text = stdout_of(verify_step)
        result["cache_verify_rc"] = verify_step.get("rc")
        result["cache_verify_stdout_path"] = verify_step.get("stdout_path")
        result["cache_verify_summary"] = cache_verify_summary(verify_text)
        result["cache_verify_preset_summary"] = preset_summary(verify_text)
        result["cache_verify_demo_summary"] = demo_summary(verify_text)
        if verify_step.get("rc") != 0 or not all_true(result["cache_verify_summary"]) or not all_true(result["cache_verify_preset_summary"]) or not all_true(result["cache_verify_demo_summary"]):
            result["decision"] = f"{DECISION_PREFIX}-cache-verify-failed"
            raise RuntimeError("video demo badapple verify did not emit required markers")

        play_step = base.run_serial_step(
            out_dir,
            steps,
            "resident-video-demo-badapple-player-hud-play",
            ["video", "demo", PRESET_NAME, "play", "--trust-cache", "--frames", str(args.frames), "--present", "pageflip", "--layout", "player-hud"],
            timeout=args.stream_timeout,
            allow_error=True,
            retry_unsafe=False,
        )
        play_text = stdout_of(play_step)
        result["cache_play_rc"] = play_step.get("rc")
        result["cache_play_stdout_path"] = play_step.get("stdout_path")
        result["cache_play_elapsed_sec"] = play_step.get("elapsed_sec")
        result["cache_play_summary"] = classify_play(play_text, int(args.frames))
        if play_step.get("rc") != 0 or not result["cache_play_summary"].get("pass"):
            result["decision"] = f"{DECISION_PREFIX}-player-hud-play-failed"
            raise RuntimeError("video demo badapple Player HUD play did not emit required markers")

        after = base.run_serial_step(out_dir, steps, "resident-selftest-after-player-hud", ["selftest", "verbose"], timeout=120.0, retry_unsafe=True)
        result["resident_selftest_after_player_hud_fail0"] = video_live.selftest_step_ok(after)
        if not result["resident_selftest_after_player_hud_fail0"]:
            result["decision"] = f"{DECISION_PREFIX}-post-play-selftest-failed"
            raise RuntimeError("post Player HUD selftest did not report fail=0")
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
    parser = video_live.parse_args()
    parser.live = bool(parser.live)
    parser.frames = BADAPPLE_PLAY_FRAMES if parser.frames == 30 else parser.frames
    parser.width = 480
    parser.height = 360
    parser.stride = 60
    parser.stream_format = "mono1"
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
            "version/status/selftest/video status",
            f"seed {BADAPPLE_SHA256} into {video_live.remote_cache_dir(BADAPPLE_SHA256)}",
            f"video demo {PRESET_NAME} status",
            f"video demo {PRESET_NAME} verify",
            f"video demo {PRESET_NAME} play --trust-cache --frames {args.frames} --present pageflip --layout player-hud",
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
        "resident_selftest_after_player_hud_fail0": result.get("resident_selftest_after_player_hud_fail0"),
    }, indent=2, sort_keys=True))
    return 0 if result.get("pass") else 1


if __name__ == "__main__":
    raise SystemExit(main())
