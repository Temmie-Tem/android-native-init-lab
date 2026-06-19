#!/usr/bin/env python3
"""V2906 live handoff for the native `video cache` command surface.

V2904 added `video cache status|verify|play SHA256`; V2905 built it into a
flashable image. This runner flashes V2905, requires the existing V2900 Bad
Apple-scale SHA-addressed SD cache hit, runs status/verify/play by SHA, then
rolls back to v2321.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import native_video_gray8_stream_live_handoff_v2893 as video_live

video_live.RUN_ID = "V2906"
video_live.BUILD_TAG = "v2906-video-cache-command-live"
video_live.REPORT_TITLE = "Native Init V2906 Video Cache Command Live Validation"
video_live.DECISION_PREFIX = "v2906-video-cache-command"
video_live.CANDIDATE_IMAGE = (
    video_live.ROOT / "workspace/private/inputs/boot_images/boot_linux_v2905_video_cache_command.img"
)
video_live.CANDIDATE_VERSION = "0.10.34"
video_live.CANDIDATE_TAG = "v2905-video-cache-command"
video_live.CANDIDATE_SHA256 = "e57b48bb4c6e5a7139c2630c9ed88a7a5d9c0461e6aebef8b9a056704347c62f"
video_live.REPORT_PATH = (
    video_live.ROOT / "docs/reports/NATIVE_INIT_V2906_VIDEO_CACHE_COMMAND_LIVE_2026-06-20.md"
)
video_live.REMOTE_DIR = "/mnt/sdext/a90/runtime/video/v2906"
video_live.REMOTE_MANIFEST = f"{video_live.REMOTE_DIR}/manifest.json"
video_live.REMOTE_STREAM = f"{video_live.REMOTE_DIR}/frames.a90vstr"

FIXTURE_SHA256 = "878dd867d63141eb6c9ce45a936d0454778ac91031e929b8da1c873c1c901890"
FIXTURE_MANIFEST_SHA256 = "4d437373995d54d26f294571b3e49ea5ae476e7531f007652ff2e80a6732faa6"
FIXTURE_STREAM_BYTES = 2106428092
FIXTURE_FRAME_BYTES = 324000
FIXTURE_FRAMES = 6501


def stdout_of(step: dict[str, Any]) -> str:
    return video_live.stdout_of(step)


def fixed_badapple_manifest() -> dict[str, Any]:
    return {
        "version": 1,
        "asset_id": "v2874-synthetic-mono1-checker-6501f",
        "video": {
            "path": "frames.a90vstr",
            "format": "mono1",
            "width": 1080,
            "height": 2400,
            "stride": 135,
            "frame_bytes": FIXTURE_FRAME_BYTES,
            "visible_row_bytes": 135,
            "fps_num": 30,
            "fps_den": 1,
            "frame_count": FIXTURE_FRAMES,
            "sha256": FIXTURE_SHA256,
        },
    }


def generate_cached_fixture(args: Any, out_dir: Path, steps: list[dict[str, Any]]) -> dict[str, Any]:
    del args, steps
    fixture_dir = out_dir / "fixture"
    fixture_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = fixture_dir / "manifest.json"
    manifest_path.write_text(json.dumps(fixed_badapple_manifest(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest_sha = video_live.sha256_file(manifest_path)
    if manifest_sha != FIXTURE_MANIFEST_SHA256:
        raise RuntimeError(f"unexpected fixed manifest sha256: {manifest_sha}")
    return {
        "manifest_path": video_live.rel(manifest_path),
        "stream_path": video_live.rel(fixture_dir / "frames.a90vstr.cache-hit-only-not-generated"),
        "sha256": FIXTURE_SHA256,
        "frame_bytes": FIXTURE_FRAME_BYTES,
        "stream_bytes": FIXTURE_STREAM_BYTES,
        "cache_hit_only": True,
        "local_stream_generated": False,
    }


def cache_status_summary(text: str) -> dict[str, Any]:
    return {
        "manifest_ok": "video.cache.manifest_ok=1" in text,
        "stream_exists": "video.cache.stream_exists=1" in text,
        "stream_size_match": "video.cache.stream_size_match=1" in text,
        "frames_ok": f"video.cache.frames={FIXTURE_FRAMES}" in text,
        "format_ok": "video.cache.format=mono1" in text,
        "sha_ok": f"video.cache.sha256={FIXTURE_SHA256}" in text,
    }


def cache_verify_summary(text: str) -> dict[str, Any]:
    return {
        "sha_checked": "video.cache.verify.sha256_checked=1" in text,
        "sha_match": "video.cache.verify.sha256_match=1" in text,
        "expected_sha": f"video.cache.verify.expected_sha256={FIXTURE_SHA256}" in text,
        "actual_sha": f"video.cache.verify.actual_sha256={FIXTURE_SHA256}" in text,
    }


def all_true(mapping: dict[str, Any]) -> bool:
    return all(bool(value) for value in mapping.values())


def cache_play_stream_ok(summary: dict[str, Any], requested_present: bool) -> bool:
    return bool(
        summary.get("presented") == FIXTURE_FRAMES
        and summary.get("flip_events") == FIXTURE_FRAMES
        and summary.get("flip_delta_count") == FIXTURE_FRAMES - 1
        and summary.get("cadence_present")
        and summary.get("cadence_target_present")
        and summary.get("pixel_format")
        and summary.get("present_pageflip")
        and summary.get("path_ok")
        and requested_present
    )


def configure_args(args: Any) -> Any:
    args.stream_format = "mono1"
    args.pattern = "checker"
    args.width = 1080
    args.height = 2400
    args.stride = 135
    args.frames = FIXTURE_FRAMES
    args.fps_num = 30
    args.fps_den = 1
    args.require_cache_hit = True
    args.disable_cache = False
    args.adopt_legacy_cache = False
    args.chunk_large_streams = False
    args.stream_timeout = max(args.stream_timeout, 720.0)
    return args


def render_report(result: dict[str, Any]) -> str:
    cache_status = result.get("cache_status_summary", {}) if isinstance(result.get("cache_status_summary"), dict) else {}
    cache_verify = result.get("cache_verify_summary", {}) if isinstance(result.get("cache_verify_summary"), dict) else {}
    cache_play_verify = result.get("cache_play_verify_summary", {}) if isinstance(result.get("cache_play_verify_summary"), dict) else {}
    stream_summary = result.get("cache_play_stream_summary", {}) if isinstance(result.get("cache_play_stream_summary"), dict) else {}
    return "\n".join([
        "# Native Init V2906 Video Cache Command Live Validation",
        "",
        "## Summary",
        "",
        f"- Decision: `{result.get('decision')}`",
        f"- Pass before rollback: `{int(bool(result.get('pass')))}`",
        f"- Candidate: `{video_live.CANDIDATE_TAG}` / `{video_live.CANDIDATE_VERSION}` / `{video_live.CANDIDATE_SHA256}`",
        f"- Cache SHA: `{FIXTURE_SHA256}`",
        f"- Cache hit: `{int(bool(result.get('runtime_install', {}).get('cache_hit')) if isinstance(result.get('runtime_install'), dict) else 0)}`",
        f"- Rollback attempted: `{int(bool(result.get('rollback_attempted')))}`",
        f"- Rollback health: version_ok=`{int(bool(result.get('rollback_version_ok')))}` selftest_fail0=`{int(bool(result.get('rollback_selftest_fail0')))}`",
        "",
        "## Command Results",
        "",
        f"- `video cache status`: rc=`{result.get('cache_status_rc')}`, summary=`{cache_status}`",
        f"- `video cache verify`: rc=`{result.get('cache_verify_rc')}`, summary=`{cache_verify}`",
        f"- `video cache play`: rc=`{result.get('cache_play_rc')}`, stream_ok=`{int(bool(result.get('cache_play_stream_ok')))}`, verify=`{cache_play_verify}`, stream=`{stream_summary}`",
        "",
        "## Evidence Paths",
        "",
        f"- Result JSON: `{result.get('result_json', 'workspace/private run dir')}`",
        f"- Cache status stdout: `{result.get('cache_status_stdout_path')}`",
        f"- Cache verify stdout: `{result.get('cache_verify_stdout_path')}`",
        f"- Cache play stdout: `{result.get('cache_play_stdout_path')}`",
        "",
        "## Interpretation",
        "",
        "- This validates the direct native cache command path over the existing V2900 SD cache: no frame regeneration, no large upload, no alternate display stack.",
        "- `status` is the cheap cache check; `verify` and `play` perform full stream SHA validation before playback.",
        "- Playback remains the existing KMS dumb-buffer/pageflip `A90VSTR1` stream path.",
        "- The imported direct `video stream` classifier's inner `pass` field is not used for the wrapper command because `video cache play` emits cache-level SHA/request markers; V2906 gates on `cache_play_stream_ok` plus cache SHA verification.",
        "",
        "## Safety",
        "",
        "- Flash path: `workspace/public/src/scripts/revalidation/native_init_flash.py`.",
        "- Persistent write scope: boot partition only; generated run evidence and private boot image remain under `workspace/private`.",
        "- No Venus/GPU/raw DSI/panel init/backlight/PMIC/PWM/regulator/GPIO/GDSC path was used.",
        "- Rollback target: `v2321-usb-clean-identity-rodata`.",
        "",
    ])


def run_live(args: Any, out_dir: Path, state: dict[str, Any]) -> dict[str, Any]:
    steps: list[dict[str, Any]] = []
    candidate_flash_attempted = False
    candidate_flash_ok = False
    result: dict[str, Any] = {
        "decision": f"{video_live.DECISION_PREFIX}-live-started",
        "pass": False,
        "preflight": state,
        "steps": steps,
        "rollback_attempted": False,
        "rollback_version_ok": False,
        "rollback_selftest_fail0": False,
    }
    try:
        fixture = generate_cached_fixture(args, out_dir, steps)
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
            f"flash-{video_live.CANDIDATE_TAG}",
            video_live.flash_command(video_live.CANDIDATE_IMAGE, video_live.CANDIDATE_VERSION, video_live.CANDIDATE_SHA256, from_native=True),
            timeout=args.flash_timeout,
        )
        candidate_flash_ok = flash.get("rc") == 0
        version = video_live.base.run_serial_step(out_dir, steps, "candidate-version", ["version"], timeout=90.0, retry_unsafe=True)
        video_live.base.run_serial_step(out_dir, steps, "candidate-status", ["status"], timeout=90.0, retry_unsafe=True)
        selftest = video_live.base.run_serial_step(out_dir, steps, "candidate-selftest", ["selftest", "verbose"], timeout=120.0, retry_unsafe=True)
        video_status = video_live.base.run_serial_step(out_dir, steps, "candidate-video-status", ["video", "status"], timeout=90.0, retry_unsafe=True)
        video_live.base.run_serial_step(out_dir, steps, "candidate-hide-menu", ["hide"], timeout=45.0, allow_error=True, retry_unsafe=True)
        result["candidate_version_ok"] = video_live.CANDIDATE_VERSION in stdout_of(version)
        result["candidate_selftest_fail0"] = video_live.selftest_step_ok(selftest)
        result["candidate_video_status_cache_marker"] = "video.status.next_cache=video cache" in stdout_of(video_status)
        if not (result["candidate_version_ok"] and result["candidate_selftest_fail0"] and result["candidate_video_status_cache_marker"]):
            result["decision"] = f"{video_live.DECISION_PREFIX}-candidate-health-failed-before-cache-command"
            raise RuntimeError("candidate health/video cache status marker did not pass")
        result["runtime_install"] = video_live.install_fixture(args, out_dir, steps, fixture)
        if not result["runtime_install"].get("cache_hit"):
            result["decision"] = f"{video_live.DECISION_PREFIX}-required-cache-hit-missing-before-cache-command"
            raise RuntimeError("required SHA-addressed video cache hit was missing")

        status = video_live.base.run_serial_step(
            out_dir,
            steps,
            "candidate-video-cache-status",
            ["video", "cache", "status", FIXTURE_SHA256],
            timeout=120.0,
            allow_error=True,
            retry_unsafe=False,
        )
        status_text = stdout_of(status)
        result["cache_status_rc"] = status.get("rc")
        result["cache_status_stdout_path"] = status.get("stdout_path")
        result["cache_status_summary"] = cache_status_summary(status_text)
        if status.get("rc") != 0 or not all_true(result["cache_status_summary"]):
            result["decision"] = f"{video_live.DECISION_PREFIX}-cache-status-failed-before-rollback"
            raise RuntimeError("video cache status did not emit required markers")

        verify = video_live.base.run_serial_step(
            out_dir,
            steps,
            "candidate-video-cache-verify",
            ["video", "cache", "verify", FIXTURE_SHA256],
            timeout=420.0,
            allow_error=True,
            retry_unsafe=False,
        )
        verify_text = stdout_of(verify)
        result["cache_verify_rc"] = verify.get("rc")
        result["cache_verify_stdout_path"] = verify.get("stdout_path")
        result["cache_verify_summary"] = cache_verify_summary(verify_text)
        if verify.get("rc") != 0 or not all_true(result["cache_verify_summary"]):
            result["decision"] = f"{video_live.DECISION_PREFIX}-cache-verify-failed-before-rollback"
            raise RuntimeError("video cache verify did not emit required markers")

        play = video_live.base.run_serial_step(
            out_dir,
            steps,
            "candidate-video-cache-play",
            ["video", "cache", "play", FIXTURE_SHA256, "--frames", str(FIXTURE_FRAMES), "--present", "pageflip"],
            timeout=args.stream_timeout,
            allow_error=True,
            retry_unsafe=False,
        )
        play_text = stdout_of(play)
        result["cache_play_rc"] = play.get("rc")
        result["cache_play_stdout_path"] = play.get("stdout_path")
        result["cache_play_verify_summary"] = cache_verify_summary(play_text)
        result["cache_play_stream_summary"] = video_live.classify_stream_output(play_text, FIXTURE_FRAMES, "mono1")
        result["cache_play_requested_present"] = "video.cache.play.requested_present=pageflip" in play_text
        result["cache_play_stream_ok"] = cache_play_stream_ok(
            result["cache_play_stream_summary"],
            bool(result["cache_play_requested_present"]),
        )
        if (play.get("rc") != 0 or
                not all_true(result["cache_play_verify_summary"]) or
                not result["cache_play_stream_ok"]):
            result["decision"] = f"{video_live.DECISION_PREFIX}-cache-play-failed-before-rollback"
            raise RuntimeError("video cache play did not emit required pass markers")

        after = video_live.base.run_serial_step(out_dir, steps, "candidate-selftest-after-cache-play", ["selftest", "verbose"], timeout=120.0, retry_unsafe=True)
        result["candidate_selftest_after_cache_play_fail0"] = video_live.selftest_step_ok(after)
        if not result["candidate_selftest_after_cache_play_fail0"]:
            result["decision"] = f"{video_live.DECISION_PREFIX}-post-cache-play-selftest-failed"
            raise RuntimeError("candidate post-cache-play selftest did not report fail=0")
        result["decision"] = f"{video_live.DECISION_PREFIX}-live-pass-before-rollback"
        result["pass"] = True
    except Exception as exc:
        result.setdefault("decision", f"{video_live.DECISION_PREFIX}-live-blocked")
        if result["decision"] == f"{video_live.DECISION_PREFIX}-live-started":
            result["decision"] = f"{video_live.DECISION_PREFIX}-live-blocked"
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
        video_live.REPORT_PATH.write_text(render_report(result), encoding="utf-8")
    return result


def main() -> int:
    args = configure_args(video_live.parse_args())
    out_dir = video_live.ROOT / f"workspace/private/runs/video/{video_live.BUILD_TAG}-{video_live.now_slug()}"
    out_dir.mkdir(parents=True, exist_ok=True)
    state = video_live.preflight_state(args)
    if not args.live:
        payload = video_live.dry_run_payload(args, state)
        payload["fixed_cache"] = {
            "stream_sha256": FIXTURE_SHA256,
            "manifest_sha256": FIXTURE_MANIFEST_SHA256,
            "stream_bytes": FIXTURE_STREAM_BYTES,
            "local_stream_generated": False,
            "commands": [
                f"video cache status {FIXTURE_SHA256}",
                f"video cache verify {FIXTURE_SHA256}",
                f"video cache play {FIXTURE_SHA256} --frames {FIXTURE_FRAMES} --present pageflip",
            ],
        }
        video_live.write_json(out_dir / "dry_run.json", payload)
        print(video_live.json.dumps(payload, indent=2, sort_keys=True))
        return 0 if payload["ok"] else 1
    if not video_live.preflight_ok(state):
        payload = {
            "decision": f"{video_live.DECISION_PREFIX}-live-preflight-failed-no-flash",
            "pass": False,
            "preflight": state,
        }
        video_live.write_json(out_dir / "result.json", payload)
        video_live.REPORT_PATH.write_text(render_report(payload), encoding="utf-8")
        print(video_live.json.dumps({
            "decision": payload["decision"],
            "pass": False,
            "out_dir": video_live.rel(out_dir),
        }, indent=2, sort_keys=True))
        return 1
    result = run_live(args, out_dir, state)
    final_pass = bool(result.get("pass")) and bool(result.get("rollback_version_ok")) and bool(result.get("rollback_selftest_fail0"))
    print(video_live.json.dumps({
        "decision": result.get("decision"),
        "pass": final_pass,
        "out_dir": video_live.rel(out_dir),
        "rollback_version_ok": result.get("rollback_version_ok"),
        "rollback_selftest_fail0": result.get("rollback_selftest_fail0"),
    }, indent=2, sort_keys=True))
    return 0 if final_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
