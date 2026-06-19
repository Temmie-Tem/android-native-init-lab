#!/usr/bin/env python3
"""V2893 live handoff for V2892 gray8 video streams.

This runner flashes the V2892 candidate, generates a compact full-resolution gray8 A90VSTR1 stream, reuses or populates the SHA-addressed SD-card fixture cache, runs the bounded `video stream --manifest ... --video-only --present pageflip` command, records DRM page-flip interval telemetry, then rolls back to v2321 and verifies selftest fail=0.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from _workspace_bootstrap import repo_root
import native_audio_tinyalsa_inventory_live_handoff_v2349 as tiny_live
import native_audio_v2798_readiness_replay_live_handoff_v2801 as base

ROOT = repo_root()
RUN_ID = "V2893"
BUILD_TAG = "v2893-video-gray8-stream-live"
REPORT_TITLE = "Native Init V2893 Video Gray8 Stream Live Validation"
DECISION_PREFIX = "v2893-video-gray8-stream"
CANDIDATE_IMAGE = ROOT / "workspace/private/inputs/boot_images/boot_linux_v2892_video_gray8_stream.img"
CANDIDATE_VERSION = "0.10.31"
CANDIDATE_TAG = "v2892-video-gray8-stream"
CANDIDATE_SHA256 = "148c85164cdad87585a88c8dc4c257c4efb80619c1515e3663dec5f723bef81f"
ROLLBACK_VERSION = "0.9.285"
ROLLBACK_IMAGE = ROOT / "workspace/private/inputs/boot_images/boot_linux_v2321_usb_clean_identity_rodata.img"
ROLLBACK_SHA256 = "ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb"
FALLBACK_V2237 = ROOT / "workspace/private/inputs/boot_images/boot_linux_v2237_supplicant_terminate_poll.img"
FALLBACK_V2237_SHA256 = "b2ea2d26d160b7702ce7d4438b84367788eea26c6a5bbe4ed93f3d270292ac7f"
FALLBACK_V48 = ROOT / "workspace/private/inputs/boot_images/boot_linux_v48.img"
REPORT_PATH = ROOT / "docs/reports/NATIVE_INIT_V2893_VIDEO_GRAY8_STREAM_LIVE_2026-06-19.md"
PREPARE_STREAM = ROOT / "workspace/public/src/scripts/revalidation/prepare_video_stream_v2874.py"
REMOTE_DIR = "/mnt/sdext/a90/runtime/video/v2893"
REMOTE_CACHE_ROOT = "/mnt/sdext/a90/runtime/video/cache"
LEGACY_REMOTE_DIRS = ()
REMOTE_MANIFEST = f"{REMOTE_DIR}/manifest.json"
REMOTE_STREAM = f"{REMOTE_DIR}/frames.a90vstr"
SELFTEST_FAIL0_RE = re.compile(r"\bfail=0\b")
PRESENTED_RE = re.compile(r"video\.stream\.presented=(\d+)")
FLIP_EVENTS_RE = re.compile(r"video\.stream\.flip_events=(\d+)")
FLIP_DELTA_COUNT_RE = re.compile(r"video\.stream\.flip_delta_count=(\d+)")
FLIP_DELTA_MIN_RE = re.compile(r"video\.stream\.flip_delta_min_us=(\d+)")
FLIP_DELTA_MAX_RE = re.compile(r"video\.stream\.flip_delta_max_us=(\d+)")
FLIP_DELTA_AVG_RE = re.compile(r"video\.stream\.flip_delta_avg_us=(\d+)")
FLIP_DELTA_TARGET_RE = re.compile(r"video\.stream\.flip_delta_target_us=(\d+)")
SHA256_LINE_RE = re.compile(r"(?m)^([0-9a-fA-F]{64})\s+")


def rel(path: Path) -> str:
    return base.rel(path)


def now_slug() -> str:
    return datetime.now(timezone.utc).astimezone().strftime("%Y%m%d-%H%M%S")


def read_text(path: Path, limit: int = 1_000_000) -> str:
    try:
        return path.read_bytes()[:limit].decode("utf-8", errors="replace")
    except FileNotFoundError:
        return ""


def sha256_file(path: Path) -> str:
    return base.sha256_file(path)


def write_json(path: Path, payload: Any) -> None:
    base.write_json(path, payload)


def stdout_of(step: dict[str, Any]) -> str:
    return base.stdout_of(step)


def file_state(path: Path, expected_sha: str | None = None) -> dict[str, Any]:
    state: dict[str, Any] = {"path": rel(path), "exists": path.exists()}
    if path.exists():
        state["size"] = path.stat().st_size
        digest = sha256_file(path)
        state["sha256"] = digest
        if expected_sha:
            state["sha256_ok"] = digest == expected_sha
    elif expected_sha:
        state["sha256_ok"] = False
    return state


def remote_cache_dir(digest: str) -> str:
    safe_digest = re.sub(r"[^0-9a-fA-F]", "", digest).lower()
    if len(safe_digest) != 64:
        raise ValueError(f"invalid fixture sha256 for cache path: {digest!r}")
    return f"{REMOTE_CACHE_ROOT}/sha256-{safe_digest}"


def remote_file_sha256(out_dir: Path,
                       steps: list[dict[str, Any]],
                       label: str,
                       remote_path: str,
                       expected_sha: str) -> dict[str, Any]:
    step = base.run_serial_step(
        out_dir,
        steps,
        label,
        ["run", "/bin/toybox", "sha256sum", remote_path],
        timeout=120.0,
        allow_error=True,
        retry_unsafe=True,
    )
    text = stdout_of(step)
    match = SHA256_LINE_RE.search(text)
    digest = match.group(1).lower() if match else ""
    return {
        "path": remote_path,
        "stdout_path": step.get("stdout_path"),
        "rc": step.get("rc"),
        "sha256": digest,
        "expected_sha256": expected_sha,
        "ok": bool(step.get("ok")) and digest == expected_sha,
    }


def copy_remote_file(out_dir: Path,
                     steps: list[dict[str, Any]],
                     label: str,
                     source: str,
                     destination: str) -> dict[str, Any]:
    step = base.run_serial_step(
        out_dir,
        steps,
        label,
        ["run", "/bin/toybox", "cp", source, destination],
        timeout=180.0,
        allow_error=True,
        retry_unsafe=True,
    )
    return {
        "source": source,
        "destination": destination,
        "stdout_path": step.get("stdout_path"),
        "rc": step.get("rc"),
        "ok": bool(step.get("ok")),
    }


def selftest_step_ok(step: dict[str, Any]) -> bool:
    return bool(SELFTEST_FAIL0_RE.search(stdout_of(step))) or base.protocol_selftest_ok(step)


def flash_command(image: Path, expect_version: str, expect_sha: str, *, from_native: bool) -> list[str]:
    command = [
        "python3",
        rel(base.FLASH),
        rel(image),
        "--expect-version",
        expect_version,
        "--expect-sha256",
        expect_sha,
        "--expect-readback-sha256",
        expect_sha,
        "--verify-protocol",
        "selftest",
        "--bridge-timeout",
        "300",
        "--recovery-timeout",
        "300",
    ]
    if from_native:
        command.append("--from-native")
    return command


def preflight_state(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "run_id": RUN_ID,
        "candidate": file_state(CANDIDATE_IMAGE, CANDIDATE_SHA256),
        "rollback": file_state(ROLLBACK_IMAGE, ROLLBACK_SHA256),
        "fallback_v2237": file_state(FALLBACK_V2237, FALLBACK_V2237_SHA256),
        "fallback_v48": file_state(FALLBACK_V48),
        "flash_helper": file_state(base.FLASH),
        "prepare_stream": file_state(PREPARE_STREAM),
        "remote_dir": REMOTE_DIR,
        "remote_cache_root": REMOTE_CACHE_ROOT,
        "legacy_remote_dirs": list(LEGACY_REMOTE_DIRS) if args.adopt_legacy_cache else [],
        "remote_manifest": REMOTE_MANIFEST,
        "remote_stream": REMOTE_STREAM,
        "cache_enabled": not args.disable_cache,
        "adopt_legacy_cache": bool(args.adopt_legacy_cache),
        "fixture_frames": args.frames,
        "cadence_target": f"{args.fps_num}/{args.fps_den}fps full-resolution {args.stream_format} page-flip stream",
        "fixture_fps_num": args.fps_num,
        "fixture_fps_den": args.fps_den,
        "fixture_pattern": args.pattern,
        "fixture_format": args.stream_format,
        "hard_boundary": [
            "boot partition only via native_init_flash.py",
            "rollback to v2321 and verify selftest fail=0",
            "KMS dumb-buffer path only",
            "no Venus/KGSL/raw DSI/panel init/backlight/PMIC/PWM/regulator/GPIO/GDSC",
            "private generated frame stream not committed",
            "SD-card cache stores generated fixture by SHA only under runtime video cache",
        ],
    }


def preflight_ok(state: dict[str, Any]) -> bool:
    return bool(
        state["candidate"].get("sha256_ok")
        and state["rollback"].get("sha256_ok")
        and state["fallback_v2237"].get("sha256_ok")
        and state["fallback_v48"].get("exists")
        and state["flash_helper"].get("exists")
        and state["prepare_stream"].get("exists")
    )


def generate_fixture(args: argparse.Namespace, out_dir: Path, steps: list[dict[str, Any]]) -> dict[str, Any]:
    fixture_dir = out_dir / "fixture"
    step = base.run_step(
        out_dir,
        steps,
        "generate-synthetic-a90vstr",
        [
            "python3",
            rel(PREPARE_STREAM),
            "--out-dir",
            rel(fixture_dir),
            "--width",
            str(args.width),
            "--height",
            str(args.height),
            "--stride",
            str(args.stride),
            "--frames",
            str(args.frames),
            "--fps-num",
            str(args.fps_num),
            "--fps-den",
            str(args.fps_den),
            "--pattern",
            args.pattern,
            "--format",
            args.stream_format,
        ],
        timeout=240.0,
    )
    payload = json.loads(stdout_of(step))
    payload["manifest_path"] = rel(fixture_dir / "manifest.json")
    payload["stream_path"] = rel(fixture_dir / "frames.a90vstr")
    return payload


def install_fixture(args: argparse.Namespace,
                    out_dir: Path,
                    steps: list[dict[str, Any]],
                    fixture: dict[str, Any]) -> dict[str, Any]:
    manifest_path = ROOT / fixture["manifest_path"]
    stream_path = ROOT / fixture["stream_path"]
    manifest_sha = sha256_file(manifest_path)
    stream_sha = str(fixture["sha256"])
    cache_dir = remote_cache_dir(stream_sha)
    cache_manifest = f"{cache_dir}/manifest.json"
    cache_stream = f"{cache_dir}/frames.a90vstr"
    target_manifest = cache_manifest if not args.disable_cache else REMOTE_MANIFEST
    target_stream = cache_stream if not args.disable_cache else REMOTE_STREAM
    result: dict[str, Any] = {
        "cache_enabled": not args.disable_cache,
        "cache_dir": cache_dir if not args.disable_cache else "",
        "remote_manifest": target_manifest,
        "remote_stream": target_stream,
        "manifest_sha256": manifest_sha,
        "stream_sha256": stream_sha,
        "selected_transport": "none",
        "control_channel": "serial",
        "cache_source": "disabled",
        "cache_hit": False,
        "cache_adopted": False,
        "cache_uploaded": False,
        "installed": [],
    }
    if not args.disable_cache:
        base.run_serial_step(
            out_dir,
            steps,
            "candidate-create-remote-video-cache-dir",
            ["run", "/bin/toybox", "mkdir", "-p", cache_dir],
            timeout=45.0,
            retry_unsafe=True,
        )
        manifest_probe = remote_file_sha256(out_dir, steps, "candidate-cache-manifest-sha256", cache_manifest, manifest_sha)
        stream_probe = remote_file_sha256(out_dir, steps, "candidate-cache-stream-sha256", cache_stream, stream_sha)
        result["cache_manifest_probe"] = manifest_probe
        result["cache_stream_probe"] = stream_probe
        if manifest_probe["ok"] and stream_probe["ok"]:
            result["cache_source"] = "hit"
            result["cache_hit"] = True
            return result
        if args.adopt_legacy_cache:
            for index, legacy_dir in enumerate(LEGACY_REMOTE_DIRS):
                legacy_manifest = f"{legacy_dir}/manifest.json"
                legacy_stream = f"{legacy_dir}/frames.a90vstr"
                legacy_manifest_probe = remote_file_sha256(
                    out_dir,
                    steps,
                    f"candidate-legacy-{index}-manifest-sha256",
                    legacy_manifest,
                    manifest_sha,
                )
                legacy_stream_probe = remote_file_sha256(
                    out_dir,
                    steps,
                    f"candidate-legacy-{index}-stream-sha256",
                    legacy_stream,
                    stream_sha,
                )
                result.setdefault("legacy_probes", []).append({
                    "dir": legacy_dir,
                    "manifest": legacy_manifest_probe,
                    "stream": legacy_stream_probe,
                })
                if legacy_manifest_probe["ok"] and legacy_stream_probe["ok"]:
                    copy_manifest = copy_remote_file(
                        out_dir,
                        steps,
                        f"candidate-adopt-legacy-{index}-manifest",
                        legacy_manifest,
                        cache_manifest,
                    )
                    copy_stream = copy_remote_file(
                        out_dir,
                        steps,
                        f"candidate-adopt-legacy-{index}-stream",
                        legacy_stream,
                        cache_stream,
                    )
                    adopted_manifest_probe = remote_file_sha256(
                        out_dir,
                        steps,
                        f"candidate-adopted-{index}-manifest-sha256",
                        cache_manifest,
                        manifest_sha,
                    )
                    adopted_stream_probe = remote_file_sha256(
                        out_dir,
                        steps,
                        f"candidate-adopted-{index}-stream-sha256",
                        cache_stream,
                        stream_sha,
                    )
                    result["adopt_copy"] = {"manifest": copy_manifest, "stream": copy_stream}
                    result["adopted_manifest_probe"] = adopted_manifest_probe
                    result["adopted_stream_probe"] = adopted_stream_probe
                    if copy_manifest["ok"] and copy_stream["ok"] and adopted_manifest_probe["ok"] and adopted_stream_probe["ok"]:
                        result["cache_source"] = "adopted-legacy"
                        result["cache_adopted"] = True
                        return result
                    break
    readiness = tiny_live.probe_transfer_readiness(args, out_dir, steps)
    selected = str(readiness["selected_transport"])
    control_channel = "tcpctl" if selected == "tcpctl" else "bridge"
    result["transfer_readiness"] = readiness
    result["selected_transport"] = selected
    result["control_channel"] = control_channel
    base.run_serial_step(
        out_dir,
        steps,
        "candidate-create-remote-video-target-dir",
        ["run", "/bin/toybox", "mkdir", "-p", cache_dir if not args.disable_cache else REMOTE_DIR],
        timeout=45.0,
        retry_unsafe=True,
    )
    for name, local_path, remote_path, port in (
        ("manifest", manifest_path, target_manifest, args.transfer_port),
        ("stream", stream_path, target_stream, args.transfer_port + 1),
    ):
        step = base.run_step(
            out_dir,
            steps,
            f"install-video-{name}",
            tiny_live.install_command(
                args,
                local_path,
                remote_path,
                port,
                control_channel=control_channel,
            ),
            timeout=args.transfer_timeout + 90.0,
        )
        result["installed"].append({
            "name": name,
            "local": rel(local_path),
            "remote": remote_path,
            "stdout_path": step.get("stdout_path"),
            "ok": bool(step.get("ok")),
        })
    if not args.disable_cache:
        uploaded_manifest_probe = remote_file_sha256(out_dir, steps, "candidate-uploaded-manifest-sha256", target_manifest, manifest_sha)
        uploaded_stream_probe = remote_file_sha256(out_dir, steps, "candidate-uploaded-stream-sha256", target_stream, stream_sha)
        result["uploaded_manifest_probe"] = uploaded_manifest_probe
        result["uploaded_stream_probe"] = uploaded_stream_probe
        result["cache_uploaded"] = bool(uploaded_manifest_probe["ok"] and uploaded_stream_probe["ok"])
        result["cache_source"] = "uploaded" if result["cache_uploaded"] else "upload-failed"
    else:
        result["cache_uploaded"] = True
    return result


def classify_stream_output(text: str, expected_frames: int, expected_format: str = "gray8") -> dict[str, Any]:
    expected_pixel_format = "xbgr8888" if expected_format == "raw" else expected_format
    match = PRESENTED_RE.search(text)
    presented = int(match.group(1)) if match else 0
    flip_match = FLIP_EVENTS_RE.search(text)
    flip_events = int(flip_match.group(1)) if flip_match else 0
    delta_count_match = FLIP_DELTA_COUNT_RE.search(text)
    delta_min_match = FLIP_DELTA_MIN_RE.search(text)
    delta_max_match = FLIP_DELTA_MAX_RE.search(text)
    delta_avg_match = FLIP_DELTA_AVG_RE.search(text)
    delta_target_match = FLIP_DELTA_TARGET_RE.search(text)
    delta_count = int(delta_count_match.group(1)) if delta_count_match else -1
    delta_min_us = int(delta_min_match.group(1)) if delta_min_match else 0
    delta_max_us = int(delta_max_match.group(1)) if delta_max_match else 0
    delta_avg_us = int(delta_avg_match.group(1)) if delta_avg_match else 0
    delta_target_us = int(delta_target_match.group(1)) if delta_target_match else 0
    sha256_match = "video.stream.sha256_match=1" in text
    sha256_checked = "video.stream.sha256_checked=1" in text
    pixel_format = f"video.stream.pixel_format={expected_pixel_format}" in text
    requested_pageflip = "video.stream.requested_present=pageflip" in text
    present_pageflip = "video.stream.present_mode=pageflip" in text
    path_ok = "video.stream.path=kms-dumb-buffer-pageflip" in text
    cadence_present = delta_count == max(expected_frames - 1, 0) and delta_min_us > 0 and delta_avg_us > 0 and delta_max_us > 0
    target_present = delta_target_us > 0
    jitter_span_us = delta_max_us - delta_min_us if delta_max_us >= delta_min_us else 0
    avg_error_us = abs(delta_avg_us - delta_target_us) if target_present else 0
    return {
        "presented": presented,
        "flip_events": flip_events,
        "expected_frames": expected_frames,
        "flip_delta_count": delta_count,
        "flip_delta_min_us": delta_min_us,
        "flip_delta_max_us": delta_max_us,
        "flip_delta_avg_us": delta_avg_us,
        "flip_delta_target_us": delta_target_us,
        "flip_delta_jitter_span_us": jitter_span_us,
        "flip_delta_avg_error_us": avg_error_us,
        "cadence_present": cadence_present,
        "cadence_target_present": target_present,
        "sha256_match": sha256_match,
        "sha256_checked": sha256_checked,
        "pixel_format": pixel_format,
        "expected_pixel_format": expected_pixel_format,
        "requested_pageflip": requested_pageflip,
        "present_pageflip": present_pageflip,
        "path_ok": path_ok,
        "pass": presented == expected_frames
        and flip_events == expected_frames
        and cadence_present
        and target_present
        and sha256_match
        and sha256_checked
        and pixel_format
        and requested_pageflip
        and present_pageflip
        and path_ok,
    }


def render_report(result: dict[str, Any]) -> str:
    preflight = result.get("preflight", {}) if isinstance(result.get("preflight"), dict) else {}
    fixture = result.get("fixture", {}) if isinstance(result.get("fixture"), dict) else {}
    stream_summary = result.get("stream_summary", {}) if isinstance(result.get("stream_summary"), dict) else {}
    install = result.get("runtime_install", {}) if isinstance(result.get("runtime_install"), dict) else {}
    installed = install.get("installed", []) if isinstance(install.get("installed"), list) else []
    installed_lines = [
        f"- `{item.get('name')}` -> `{item.get('remote')}` ok=`{int(bool(item.get('ok')))}`"
        for item in installed
    ] or ["- none"]
    return "\n".join([
        f"# {REPORT_TITLE}",
        "",
        "## Summary",
        "",
        f"- Cycle: `{RUN_ID}`",
        "- Track: active Video playback pipeline on the existing KMS display.",
        f"- Decision: `{result.get('decision')}`",
        f"- Result: `{'PASS' if result.get('pass') else 'FAIL'}`",
        f"- Candidate: `{CANDIDATE_TAG}` / `{CANDIDATE_VERSION}`",
        f"- Candidate image: `{rel(CANDIDATE_IMAGE)}`",
        f"- Candidate SHA256: `{CANDIDATE_SHA256}`",
        f"- Rollback attempted: `{int(bool(result.get('rollback_attempted')))}`",
        f"- Rollback health: version_ok=`{int(bool(result.get('rollback_version_ok')))}` selftest_fail0=`{int(bool(result.get('rollback_selftest_fail0')))}`",
        "",
        "## Fixture",
        "",
        f"- Manifest: `{fixture.get('manifest_path')}`",
        f"- Stream: `{fixture.get('stream_path')}`",
        f"- SHA256: `{fixture.get('sha256')}`",
        f"- Frame bytes: `{fixture.get('frame_bytes')}`",
        f"- Stream bytes: `{fixture.get('stream_bytes')}`",
        f"- Format: `{preflight.get('fixture_format')}`",
        f"- Frames/FPS: `{preflight.get('fixture_frames')}` @ `{preflight.get('fixture_fps_num')}/{preflight.get('fixture_fps_den')}`",
        f"- Cache root: `{preflight.get('remote_cache_root')}` enabled=`{int(bool(preflight.get('cache_enabled')))}`",
        "",
        "## Runtime Install",
        "",
        f"- Selected transport: `{install.get('selected_transport')}`",
        f"- Control channel: `{install.get('control_channel')}`",
        f"- Cache source: `{install.get('cache_source')}` hit=`{int(bool(install.get('cache_hit')))}` adopted=`{int(bool(install.get('cache_adopted')))}` uploaded=`{int(bool(install.get('cache_uploaded')))}`",
        f"- Remote manifest used: `{install.get('remote_manifest')}`",
        f"- Remote stream used: `{install.get('remote_stream')}`",
        *installed_lines,
        "",
        "## Stream Result",
        "",
        f"- Presented frames: `{stream_summary.get('presented')}` / `{stream_summary.get('expected_frames')}`",
        f"- Flip events: `{stream_summary.get('flip_events')}` / `{stream_summary.get('expected_frames')}`",
        f"- Flip delta count: `{stream_summary.get('flip_delta_count')}`",
        f"- Flip delta min/avg/max/target us: `{stream_summary.get('flip_delta_min_us')}` / `{stream_summary.get('flip_delta_avg_us')}` / `{stream_summary.get('flip_delta_max_us')}` / `{stream_summary.get('flip_delta_target_us')}`",
        f"- Flip delta avg error / jitter span us: `{stream_summary.get('flip_delta_avg_error_us')}` / `{stream_summary.get('flip_delta_jitter_span_us')}`",
        f"- Present mode markers: requested=`{int(bool(stream_summary.get('requested_pageflip')))}` active=`{int(bool(stream_summary.get('present_pageflip')))}`",
        f"- SHA checked/match: `{int(bool(stream_summary.get('sha256_checked')))}` / `{int(bool(stream_summary.get('sha256_match')))}`",
        f"- Pixel format marker: `{int(bool(stream_summary.get('pixel_format')))}`",
        f"- KMS page-flip path marker: `{int(bool(stream_summary.get('path_ok')))}`",
        f"- Stream stdout: `{result.get('stream_stdout_path')}`",
        "",
        "## Safety",
        "",
        "- Flash path: `workspace/public/src/scripts/revalidation/native_init_flash.py`.",
        "- Only the boot partition was flashed; candidate was rolled back to `v2321` after validation.",
        "- Generated frame payloads and raw command transcripts remain private under `workspace/private/`.",
        "- No Venus, KGSL, raw DSI, panel init, backlight, PMIC, PWM, regulator, GPIO, or GDSC path was used.",
        "",
    ])


def dry_run_payload(args: argparse.Namespace, state: dict[str, Any]) -> dict[str, Any]:
    return {
        "decision": f"{DECISION_PREFIX}-live-dry-run" if preflight_ok(state) else f"{DECISION_PREFIX}-live-blocked",
        "ok": preflight_ok(state),
        "preflight": state,
        "commands": {
            "verify_current": flash_command(ROLLBACK_IMAGE, ROLLBACK_VERSION, ROLLBACK_SHA256, from_native=False) + ["--verify-only"],
            "flash_candidate": flash_command(CANDIDATE_IMAGE, CANDIDATE_VERSION, CANDIDATE_SHA256, from_native=True),
            "video_status": ["video", "status"],
            "stream": ["video", "stream", "--manifest", f"{REMOTE_CACHE_ROOT}/sha256-<fixture-sha256>/manifest.json", "--video-only", "--frames", str(args.frames), "--present", "pageflip"],
            "rollback": flash_command(ROLLBACK_IMAGE, ROLLBACK_VERSION, ROLLBACK_SHA256, from_native=True),
        },
    }


def run_live(args: argparse.Namespace, out_dir: Path, state: dict[str, Any]) -> dict[str, Any]:
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
        fixture = generate_fixture(args, out_dir, steps)
        result["fixture"] = fixture
        base.run_step(
            out_dir,
            steps,
            "verify-current-v2321",
            flash_command(ROLLBACK_IMAGE, ROLLBACK_VERSION, ROLLBACK_SHA256, from_native=False) + ["--verify-only"],
            timeout=args.flash_timeout,
        )
        candidate_flash_attempted = True
        flash = base.run_step(
            out_dir,
            steps,
            f"flash-{CANDIDATE_TAG}",
            flash_command(CANDIDATE_IMAGE, CANDIDATE_VERSION, CANDIDATE_SHA256, from_native=True),
            timeout=args.flash_timeout,
        )
        candidate_flash_ok = flash.get("rc") == 0
        version = base.run_serial_step(out_dir, steps, "candidate-version", ["version"], timeout=90.0, retry_unsafe=True)
        status = base.run_serial_step(out_dir, steps, "candidate-status", ["status"], timeout=90.0, retry_unsafe=True)
        selftest = base.run_serial_step(out_dir, steps, "candidate-selftest", ["selftest", "verbose"], timeout=120.0, retry_unsafe=True)
        video_status = base.run_serial_step(out_dir, steps, "candidate-video-status", ["video", "status"], timeout=90.0, retry_unsafe=True)
        base.run_serial_step(out_dir, steps, "candidate-hide-menu", ["hide"], timeout=45.0, allow_error=True, retry_unsafe=True)
        result["candidate_version_ok"] = CANDIDATE_VERSION in stdout_of(version)
        result["candidate_status_path"] = status.get("stdout_path")
        result["candidate_selftest_fail0"] = selftest_step_ok(selftest)
        video_status_text = stdout_of(video_status)
        result["candidate_video_status_stream_marker"] = "video.status.next_stream=" in video_status_text
        result["candidate_video_status_basic_marker"] = (
            "video.status.next=" in video_status_text and "video.status.kms.initialized=1" in video_status_text
        )
        result["candidate_video_status_ok"] = bool(
            result["candidate_video_status_stream_marker"] or result["candidate_video_status_basic_marker"]
        )
        if not (result["candidate_version_ok"] and result["candidate_selftest_fail0"] and result["candidate_video_status_ok"]):
            result["decision"] = f"{DECISION_PREFIX}-candidate-health-failed-before-stream"
            raise RuntimeError("candidate health/video status did not pass")
        result["runtime_install"] = install_fixture(args, out_dir, steps, fixture)
        stream_manifest = str(result["runtime_install"].get("remote_manifest") or REMOTE_MANIFEST)
        stream = base.run_serial_step(
            out_dir,
            steps,
            "candidate-video-stream",
            ["video", "stream", "--manifest", stream_manifest, "--video-only", "--frames", str(args.frames), "--present", "pageflip"],
            timeout=args.stream_timeout,
            allow_error=True,
            retry_unsafe=False,
        )
        stream_text = stdout_of(stream)
        result["stream_rc"] = stream.get("rc")
        result["stream_stdout_path"] = stream.get("stdout_path")
        result["stream_summary"] = classify_stream_output(stream_text, args.frames, args.stream_format)
        if stream.get("rc") != 0 or not result["stream_summary"].get("pass"):
            result["decision"] = f"{DECISION_PREFIX}-stream-failed-before-rollback"
            raise RuntimeError("video stream command did not emit required pass markers")
        after = base.run_serial_step(out_dir, steps, "candidate-selftest-after-stream", ["selftest", "verbose"], timeout=120.0, retry_unsafe=True)
        result["candidate_selftest_after_stream_fail0"] = selftest_step_ok(after)
        if not result["candidate_selftest_after_stream_fail0"]:
            result["decision"] = f"{DECISION_PREFIX}-post-stream-selftest-failed"
            raise RuntimeError("candidate post-stream selftest did not report fail=0")
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
            rollback = base.rollback_v2321(out_dir, steps, from_native=candidate_flash_ok, timeout=args.flash_timeout)
            result["rollback_step_ok"] = bool(rollback.get("success"))
            result["rollback_attempts"] = rollback.get("attempts", [])
            result["rollback_recovery_fallback_used"] = bool(rollback.get("used_recovery_fallback"))
            if rollback.get("success"):
                rollback_version = base.run_serial_step(out_dir, steps, "rollback-version", ["version"], timeout=90.0, retry_unsafe=True, allow_error=True)
                rollback_selftest = base.run_serial_step(out_dir, steps, "rollback-selftest", ["selftest", "verbose"], timeout=120.0, retry_unsafe=True, allow_error=True)
                result["rollback_version_ok"] = ROLLBACK_VERSION in stdout_of(rollback_version)
                result["rollback_selftest_fail0"] = selftest_step_ok(rollback_selftest)
        write_json(out_dir / "result.json", result)
        REPORT_PATH.write_text(render_report(result), encoding="utf-8")
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--bridge-host", default="127.0.0.1")
    parser.add_argument("--bridge-port", type=int, default=54321)
    parser.add_argument("--device-ip", default="192.168.7.2")
    parser.add_argument("--host-ip", default="192.168.7.1")
    parser.add_argument("--host-prefix", type=int, default=24)
    parser.add_argument("--tcp-port", type=int, default=2325)
    parser.add_argument("--transfer-port", type=int, default=18120)
    parser.add_argument("--transfer-timeout", type=float, default=600.0)
    parser.add_argument("--transfer-delay", type=float, default=0.05)
    parser.add_argument("--command-timeout", type=float, default=90.0)
    parser.add_argument("--tcp-timeout", type=float, default=60.0)
    parser.add_argument("--stream-timeout", type=float, default=240.0)
    parser.add_argument("--flash-timeout", type=float, default=900.0)
    parser.add_argument("--device-toolbox", default="/bin/toybox")
    parser.add_argument("--ncm-setup-sudo", default="sudo")
    parser.add_argument("--ncm-interface-timeout", type=float, default=60.0)
    parser.add_argument("--ncm-setup-timeout", type=float, default=90.0)
    parser.add_argument("--repair-host-ncm", action="store_true", default=True)
    parser.add_argument("--inventory-transport", choices=("auto", "tcpctl", "serial"), default="auto")
    parser.add_argument("--width", type=int, default=1080)
    parser.add_argument("--height", type=int, default=2400)
    parser.add_argument("--stride", type=int, default=1080)
    parser.add_argument("--frames", type=int, default=30)
    parser.add_argument("--fps-num", type=int, default=30)
    parser.add_argument("--fps-den", type=int, default=1)
    parser.add_argument("--pattern", choices=("bars", "checker", "pulse"), default="checker")
    parser.add_argument("--stream-format", choices=("raw", "gray8", "mono1"), default="gray8")
    parser.add_argument("--disable-cache", action="store_true", help="stage this run under the per-run remote directory instead of the SHA-addressed SD cache")
    parser.add_argument("--adopt-legacy-cache", action=argparse.BooleanOptionalAction, default=True, help="copy a matching legacy V2890 remote fixture into the SHA cache before uploading")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    out_dir = ROOT / f"workspace/private/runs/video/{BUILD_TAG}-{now_slug()}"
    out_dir.mkdir(parents=True, exist_ok=True)
    state = preflight_state(args)
    if not args.live:
        payload = dry_run_payload(args, state)
        write_json(out_dir / "dry_run.json", payload)
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0 if payload["ok"] else 1
    if not preflight_ok(state):
        payload = {
            "decision": f"{DECISION_PREFIX}-live-preflight-failed-no-flash",
            "pass": False,
            "preflight": state,
        }
        write_json(out_dir / "result.json", payload)
        REPORT_PATH.write_text(render_report(payload), encoding="utf-8")
        print(json.dumps({"decision": payload["decision"], "pass": False, "out_dir": rel(out_dir)}, indent=2, sort_keys=True))
        return 1
    result = run_live(args, out_dir, state)
    print(json.dumps({
        "decision": result.get("decision"),
        "pass": bool(result.get("pass")) and bool(result.get("rollback_version_ok")) and bool(result.get("rollback_selftest_fail0")),
        "out_dir": rel(out_dir),
        "rollback_version_ok": result.get("rollback_version_ok"),
        "rollback_selftest_fail0": result.get("rollback_selftest_fail0"),
    }, indent=2, sort_keys=True))
    return 0 if result.get("pass") and result.get("rollback_version_ok") and result.get("rollback_selftest_fail0") else 1


if __name__ == "__main__":
    raise SystemExit(main())
