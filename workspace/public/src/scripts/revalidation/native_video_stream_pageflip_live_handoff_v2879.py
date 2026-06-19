#!/usr/bin/env python3
"""V2879 live handoff for the V2878 A90VSTR1 page-flip stream mode.

This runner flashes the V2878 candidate, stages a private synthetic full-geometry
A90VSTR1 stream under /cache/a90-runtime/pkg/video/v2879, runs the bounded
`video stream --manifest ... --video-only --present pageflip` command, then rolls back to v2321 and
verifies selftest fail=0.
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
RUN_ID = "V2879"
BUILD_TAG = "v2879-video-stream-pageflip-live"
CANDIDATE_IMAGE = ROOT / "workspace/private/inputs/boot_images/boot_linux_v2878_video_stream_pageflip.img"
CANDIDATE_VERSION = "0.10.25"
CANDIDATE_TAG = "v2878-video-stream-pageflip"
CANDIDATE_SHA256 = "5f33038c1812dabd6f46fa724dddee39b8ddaf346b96f53155ab42c84cd29587"
ROLLBACK_VERSION = "0.9.285"
ROLLBACK_IMAGE = ROOT / "workspace/private/inputs/boot_images/boot_linux_v2321_usb_clean_identity_rodata.img"
ROLLBACK_SHA256 = "ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb"
FALLBACK_V2237 = ROOT / "workspace/private/inputs/boot_images/boot_linux_v2237_supplicant_terminate_poll.img"
FALLBACK_V2237_SHA256 = "b2ea2d26d160b7702ce7d4438b84367788eea26c6a5bbe4ed93f3d270292ac7f"
FALLBACK_V48 = ROOT / "workspace/private/inputs/boot_images/boot_linux_v48.img"
REPORT_PATH = ROOT / "docs/reports/NATIVE_INIT_V2879_VIDEO_STREAM_PAGEFLIP_LIVE_2026-06-19.md"
PREPARE_STREAM = ROOT / "workspace/public/src/scripts/revalidation/prepare_video_stream_v2874.py"
REMOTE_DIR = "/cache/a90-runtime/pkg/video/v2879"
REMOTE_MANIFEST = f"{REMOTE_DIR}/manifest.json"
REMOTE_STREAM = f"{REMOTE_DIR}/frames.a90vstr"
SELFTEST_FAIL0_RE = re.compile(r"\bfail=0\b")
PRESENTED_RE = re.compile(r"video\.stream\.presented=(\d+)")
FLIP_EVENTS_RE = re.compile(r"video\.stream\.flip_events=(\d+)")


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
        "remote_manifest": REMOTE_MANIFEST,
        "remote_stream": REMOTE_STREAM,
        "fixture_frames": args.frames,
        "fixture_fps_num": args.fps_num,
        "fixture_fps_den": args.fps_den,
        "fixture_pattern": args.pattern,
        "hard_boundary": [
            "boot partition only via native_init_flash.py",
            "rollback to v2321 and verify selftest fail=0",
            "KMS dumb-buffer path only",
            "no Venus/KGSL/raw DSI/panel init/backlight/PMIC/PWM/regulator/GPIO/GDSC",
            "private generated frame stream not committed",
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
    readiness = tiny_live.probe_transfer_readiness(args, out_dir, steps)
    selected = str(readiness["selected_transport"])
    control_channel = "tcpctl" if selected == "tcpctl" else "bridge"
    manifest_path = ROOT / fixture["manifest_path"]
    stream_path = ROOT / fixture["stream_path"]
    result: dict[str, Any] = {
        "transfer_readiness": readiness,
        "selected_transport": selected,
        "control_channel": control_channel,
        "installed": [],
    }
    base.run_serial_step(
        out_dir,
        steps,
        "candidate-create-remote-video-dir",
        ["run", "/bin/toybox", "mkdir", "-p", REMOTE_DIR],
        timeout=45.0,
        retry_unsafe=True,
    )
    for name, local_path, remote_path, port in (
        ("manifest", manifest_path, REMOTE_MANIFEST, args.transfer_port),
        ("stream", stream_path, REMOTE_STREAM, args.transfer_port + 1),
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
    return result


def classify_stream_output(text: str, expected_frames: int) -> dict[str, Any]:
    match = PRESENTED_RE.search(text)
    presented = int(match.group(1)) if match else 0
    flip_match = FLIP_EVENTS_RE.search(text)
    flip_events = int(flip_match.group(1)) if flip_match else 0
    sha256_match = "video.stream.sha256_match=1" in text
    sha256_checked = "video.stream.sha256_checked=1" in text
    pixel_format = "video.stream.pixel_format=xbgr8888" in text
    requested_pageflip = "video.stream.requested_present=pageflip" in text
    present_pageflip = "video.stream.present_mode=pageflip" in text
    path_ok = "video.stream.path=kms-dumb-buffer-pageflip" in text
    return {
        "presented": presented,
        "flip_events": flip_events,
        "expected_frames": expected_frames,
        "sha256_match": sha256_match,
        "sha256_checked": sha256_checked,
        "pixel_format": pixel_format,
        "requested_pageflip": requested_pageflip,
        "present_pageflip": present_pageflip,
        "path_ok": path_ok,
        "pass": presented == expected_frames
        and flip_events == expected_frames
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
        "# Native Init V2879 Video Stream Page-Flip Live Validation",
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
        f"- Frames/FPS: `{preflight.get('fixture_frames')}` @ `{preflight.get('fixture_fps_num')}/{preflight.get('fixture_fps_den')}`",
        "",
        "## Runtime Install",
        "",
        f"- Selected transport: `{install.get('selected_transport')}`",
        f"- Control channel: `{install.get('control_channel')}`",
        *installed_lines,
        "",
        "## Stream Result",
        "",
        f"- Presented frames: `{stream_summary.get('presented')}` / `{stream_summary.get('expected_frames')}`",
        f"- Flip events: `{stream_summary.get('flip_events')}` / `{stream_summary.get('expected_frames')}`",
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
        "decision": "v2879-video-stream-pageflip-live-dry-run" if preflight_ok(state) else "v2879-video-stream-pageflip-live-blocked",
        "ok": preflight_ok(state),
        "preflight": state,
        "commands": {
            "verify_current": flash_command(ROLLBACK_IMAGE, ROLLBACK_VERSION, ROLLBACK_SHA256, from_native=False) + ["--verify-only"],
            "flash_candidate": flash_command(CANDIDATE_IMAGE, CANDIDATE_VERSION, CANDIDATE_SHA256, from_native=True),
            "video_status": ["video", "status"],
            "stream": ["video", "stream", "--manifest", REMOTE_MANIFEST, "--video-only", "--frames", str(args.frames), "--present", "pageflip"],
            "rollback": flash_command(ROLLBACK_IMAGE, ROLLBACK_VERSION, ROLLBACK_SHA256, from_native=True),
        },
    }


def run_live(args: argparse.Namespace, out_dir: Path, state: dict[str, Any]) -> dict[str, Any]:
    steps: list[dict[str, Any]] = []
    candidate_flash_attempted = False
    candidate_flash_ok = False
    result: dict[str, Any] = {
        "decision": "v2879-video-stream-pageflip-live-started",
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
            "flash-v2878-video-stream-pageflip",
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
        result["candidate_video_status_ok"] = "video.status.next_stream=" in stdout_of(video_status)
        if not (result["candidate_version_ok"] and result["candidate_selftest_fail0"] and result["candidate_video_status_ok"]):
            result["decision"] = "v2879-video-stream-pageflip-candidate-health-failed-before-stream"
            raise RuntimeError("candidate health/video status did not pass")
        result["runtime_install"] = install_fixture(args, out_dir, steps, fixture)
        stream = base.run_serial_step(
            out_dir,
            steps,
            "candidate-video-stream",
            ["video", "stream", "--manifest", REMOTE_MANIFEST, "--video-only", "--frames", str(args.frames), "--present", "pageflip"],
            timeout=args.stream_timeout,
            allow_error=True,
            retry_unsafe=False,
        )
        stream_text = stdout_of(stream)
        result["stream_rc"] = stream.get("rc")
        result["stream_stdout_path"] = stream.get("stdout_path")
        result["stream_summary"] = classify_stream_output(stream_text, args.frames)
        if stream.get("rc") != 0 or not result["stream_summary"].get("pass"):
            result["decision"] = "v2879-video-stream-pageflip-stream-failed-before-rollback"
            raise RuntimeError("video stream command did not emit required pass markers")
        after = base.run_serial_step(out_dir, steps, "candidate-selftest-after-stream", ["selftest", "verbose"], timeout=120.0, retry_unsafe=True)
        result["candidate_selftest_after_stream_fail0"] = selftest_step_ok(after)
        if not result["candidate_selftest_after_stream_fail0"]:
            result["decision"] = "v2879-video-stream-pageflip-post-stream-selftest-failed"
            raise RuntimeError("candidate post-stream selftest did not report fail=0")
        result["decision"] = "v2879-video-stream-pageflip-live-pass-before-rollback"
        result["pass"] = True
    except Exception as exc:
        result.setdefault("decision", "v2879-video-stream-pageflip-live-blocked")
        if result["decision"] == "v2879-video-stream-pageflip-live-started":
            result["decision"] = "v2879-video-stream-pageflip-live-blocked"
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
    parser.add_argument("--transfer-timeout", type=float, default=240.0)
    parser.add_argument("--transfer-delay", type=float, default=0.05)
    parser.add_argument("--command-timeout", type=float, default=90.0)
    parser.add_argument("--tcp-timeout", type=float, default=60.0)
    parser.add_argument("--stream-timeout", type=float, default=180.0)
    parser.add_argument("--flash-timeout", type=float, default=900.0)
    parser.add_argument("--device-toolbox", default="/bin/toybox")
    parser.add_argument("--ncm-setup-sudo", default="sudo")
    parser.add_argument("--ncm-interface-timeout", type=float, default=60.0)
    parser.add_argument("--ncm-setup-timeout", type=float, default=90.0)
    parser.add_argument("--repair-host-ncm", action="store_true", default=True)
    parser.add_argument("--inventory-transport", choices=("auto", "tcpctl", "serial"), default="auto")
    parser.add_argument("--width", type=int, default=1080)
    parser.add_argument("--height", type=int, default=2400)
    parser.add_argument("--stride", type=int, default=4352)
    parser.add_argument("--frames", type=int, default=6)
    parser.add_argument("--fps-num", type=int, default=6)
    parser.add_argument("--fps-den", type=int, default=1)
    parser.add_argument("--pattern", choices=("bars", "checker", "pulse"), default="checker")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    out_dir = ROOT / f"workspace/private/runs/video/v2879-video-stream-pageflip-live-{now_slug()}"
    out_dir.mkdir(parents=True, exist_ok=True)
    state = preflight_state(args)
    if not args.live:
        payload = dry_run_payload(args, state)
        write_json(out_dir / "dry_run.json", payload)
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0 if payload["ok"] else 1
    if not preflight_ok(state):
        payload = {
            "decision": "v2879-video-stream-pageflip-live-preflight-failed-no-flash",
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
