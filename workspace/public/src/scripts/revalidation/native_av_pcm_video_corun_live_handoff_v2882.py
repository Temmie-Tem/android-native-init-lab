#!/usr/bin/env python3
"""V2882 live A/V co-run smoke for V2880 PCM-file audio + page-flip video.

This is deliberately a smoke/integration step, not a precise sync claim. It
flashes the already-validated V2880 candidate, stages one private raw S16LE PCM
fixture and one private A90VSTR1 page-flip video stream, starts audio playback
from the PCM file, immediately runs the page-flip video stream, then verifies
both command paths and rolls back to v2321.
"""

from __future__ import annotations

import argparse
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from _workspace_bootstrap import repo_root
import native_audio_pcm_file_live_handoff_v2881 as audio_live
import native_audio_tinyalsa_inventory_live_handoff_v2349 as tiny_live
import native_audio_v2798_readiness_replay_live_handoff_v2801 as base
import native_video_stream_pageflip_live_handoff_v2879 as video_live

ROOT = repo_root()
RUN_ID = "V2882"
CANDIDATE_IMAGE = ROOT / "workspace/private/inputs/boot_images/boot_linux_v2880_audio_pcm_file.img"
CANDIDATE_VERSION = "0.10.26"
CANDIDATE_TAG = "v2880-audio-pcm-file"
CANDIDATE_SHA256 = "674c7ff223f295be0e53e3fd4636b2dd4f54a6c9615a7b6fa8833951fdf3dc44"
ROLLBACK_VERSION = "0.9.285"
ROLLBACK_IMAGE = ROOT / "workspace/private/inputs/boot_images/boot_linux_v2321_usb_clean_identity_rodata.img"
ROLLBACK_SHA256 = "ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb"
FALLBACK_V2237 = ROOT / "workspace/private/inputs/boot_images/boot_linux_v2237_supplicant_terminate_poll.img"
FALLBACK_V2237_SHA256 = "b2ea2d26d160b7702ce7d4438b84367788eea26c6a5bbe4ed93f3d270292ac7f"
FALLBACK_V48 = ROOT / "workspace/private/inputs/boot_images/boot_linux_v48.img"
REPORT_PATH = ROOT / "docs/reports/NATIVE_INIT_V2882_AV_PCM_VIDEO_CORUN_LIVE_2026-06-19.md"
PREPARE_STREAM = ROOT / "workspace/public/src/scripts/revalidation/prepare_video_stream_v2874.py"

PROFILE = "internal-speaker-safe"
BUNDLED_REMOTE_MANIFEST = "/a90/audio/manifests/audio-setcal-internal-speaker-safe.manifest"
REMOTE_AV_ROOT = "/cache/a90-runtime/pkg/av/v2882"
REMOTE_VIDEO_DIR = f"{REMOTE_AV_ROOT}/video"
REMOTE_VIDEO_MANIFEST = f"{REMOTE_VIDEO_DIR}/manifest.json"
REMOTE_VIDEO_STREAM = f"{REMOTE_VIDEO_DIR}/frames.a90vstr"
REMOTE_AUDIO_DIR = f"{REMOTE_AV_ROOT}/audio"
REMOTE_AUDIO_PCM = f"{REMOTE_AUDIO_DIR}/tone.s16le"
REMOTE_PLAY_LOG = "/cache/a90-audio-play/worker.log"
SELFTEST_FAIL0_RE = re.compile(r"\bfail=0\b")


def rel(path: Path) -> str:
    return base.rel(path)


def now_slug() -> str:
    return datetime.now(timezone.utc).astimezone().strftime("%Y%m%d-%H%M%S")


def stdout_of(step: dict[str, Any]) -> str:
    return base.stdout_of(step)


def write_json(path: Path, payload: Any) -> None:
    base.write_json(path, payload)


def sha256_file(path: Path) -> str:
    return base.sha256_file(path)


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


def patch_child_module_paths() -> None:
    video_live.REMOTE_DIR = REMOTE_VIDEO_DIR
    video_live.REMOTE_MANIFEST = REMOTE_VIDEO_MANIFEST
    video_live.REMOTE_STREAM = REMOTE_VIDEO_STREAM
    audio_live.REMOTE_DIR = REMOTE_AUDIO_DIR
    audio_live.REMOTE_PCM = REMOTE_AUDIO_PCM


def preflight_state(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "run_id": RUN_ID,
        "candidate": file_state(CANDIDATE_IMAGE, CANDIDATE_SHA256),
        "rollback": file_state(ROLLBACK_IMAGE, ROLLBACK_SHA256),
        "fallback_v2237": file_state(FALLBACK_V2237, FALLBACK_V2237_SHA256),
        "fallback_v48": file_state(FALLBACK_V48),
        "flash_helper": file_state(base.FLASH),
        "prepare_stream": file_state(PREPARE_STREAM),
        "profile": PROFILE,
        "remote_av_root": REMOTE_AV_ROOT,
        "remote_audio_pcm": REMOTE_AUDIO_PCM,
        "remote_video_manifest": REMOTE_VIDEO_MANIFEST,
        "remote_video_stream": REMOTE_VIDEO_STREAM,
        "audio_duration_ms": args.duration_ms,
        "audio_amplitude_milli": args.amplitude_milli,
        "video_frames": args.frames,
        "video_fps_num": args.fps_num,
        "video_fps_den": args.fps_den,
        "hard_boundary": [
            "boot partition only via native_init_flash.py",
            "rollback to v2321 and verify selftest fail=0",
            "A/V co-run only; no exact sync claim in this unit",
            "generated PCM and frame streams are private runtime artifacts",
            "use existing KMS dumb-buffer page-flip and existing bounded audio route only",
            "no Venus/KGSL/raw DSI/panel init/backlight/PMIC/PWM/regulator/GPIO/GDSC",
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


def generate_fixtures(args: argparse.Namespace, out_dir: Path, steps: list[dict[str, Any]]) -> dict[str, Any]:
    patch_child_module_paths()
    video_fixture = video_live.generate_fixture(args, out_dir, steps)
    audio_fixture = audio_live.generate_pcm_fixture(args, out_dir)
    return {
        "video": video_fixture,
        "audio": audio_fixture,
    }


def install_fixtures(args: argparse.Namespace,
                     out_dir: Path,
                     steps: list[dict[str, Any]],
                     fixtures: dict[str, Any]) -> dict[str, Any]:
    readiness = tiny_live.probe_transfer_readiness(args, out_dir, steps)
    selected = str(readiness["selected_transport"])
    control_channel = "tcpctl" if selected == "tcpctl" else "bridge"
    video_fixture = fixtures["video"]
    audio_fixture = fixtures["audio"]
    installs: list[dict[str, Any]] = []
    base.run_serial_step(
        out_dir,
        steps,
        "candidate-clean-remote-av-root",
        ["run", "/bin/toybox", "rm", "-rf", REMOTE_AV_ROOT],
        timeout=90.0,
        retry_unsafe=True,
    )
    base.run_serial_step(
        out_dir,
        steps,
        "candidate-create-remote-av-dirs",
        ["run", "/bin/toybox", "mkdir", "-p", REMOTE_VIDEO_DIR, REMOTE_AUDIO_DIR],
        timeout=45.0,
        retry_unsafe=True,
    )
    transfer_items = [
        ("video-manifest", ROOT / video_fixture["manifest_path"], REMOTE_VIDEO_MANIFEST, args.transfer_port),
        ("video-stream", ROOT / video_fixture["stream_path"], REMOTE_VIDEO_STREAM, args.transfer_port + 1),
        ("audio-pcm", ROOT / audio_fixture["path"], REMOTE_AUDIO_PCM, args.transfer_port + 2),
    ]
    for name, local_path, remote_path, port in transfer_items:
        step = base.run_step(
            out_dir,
            steps,
            f"install-{name}",
            tiny_live.install_command(
                args,
                local_path,
                remote_path,
                port,
                control_channel=control_channel,
            ),
            timeout=args.transfer_timeout + 120.0,
        )
        installs.append({
            "name": name,
            "local": rel(local_path),
            "remote": remote_path,
            "stdout_path": step.get("stdout_path"),
            "ok": bool(step.get("ok")),
        })
    remote_audio_sha = base.run_serial_step(
        out_dir,
        steps,
        "candidate-remote-audio-pcm-sha256",
        ["run", "/bin/toybox", "sha256sum", REMOTE_AUDIO_PCM],
        timeout=45.0,
        retry_unsafe=True,
    )
    return {
        "transfer_readiness": readiness,
        "selected_transport": selected,
        "control_channel": control_channel,
        "installed": installs,
        "remote_audio_sha_stdout_path": remote_audio_sha.get("stdout_path"),
        "remote_audio_sha_match": audio_fixture["sha256"] in stdout_of(remote_audio_sha),
    }


def classify_av_result(video_text: str, audio_text: str, expected_frames: int) -> dict[str, Any]:
    video_summary = video_live.classify_stream_output(video_text, expected_frames)
    audio_summary = audio_live.classify_pcm_output(audio_text)
    return {
        "video": video_summary,
        "audio": audio_summary,
        "video_pass": bool(video_summary.get("pass")),
        "audio_pass": audio_live.pcm_output_pass(audio_summary),
        "corun_smoke_pass": bool(video_summary.get("pass")) and audio_live.pcm_output_pass(audio_summary),
    }


def render_report(result: dict[str, Any]) -> str:
    fixtures = result.get("fixtures") or {}
    video_fixture = fixtures.get("video") or {}
    audio_fixture = fixtures.get("audio") or {}
    install = result.get("runtime_install") or {}
    av = result.get("av_summary") or {}
    video_summary = av.get("video") or {}
    audio_summary = av.get("audio") or {}
    installed = install.get("installed", []) if isinstance(install.get("installed"), list) else []
    installed_lines = [
        f"- `{item.get('name')}` -> `{item.get('remote')}` ok=`{int(bool(item.get('ok')))}`"
        for item in installed
    ] or ["- none"]
    audio_lines = [f"- `{key}`: `{int(bool(value))}`" for key, value in sorted(audio_summary.items())]
    return "\n".join([
        "# Native Init V2882 A/V PCM+Video Co-run Live Handoff",
        "",
        "## Summary",
        "",
        f"- Cycle: `{RUN_ID}`",
        "- Track: active Video playback pipeline on existing KMS display.",
        f"- Decision: `{result.get('decision')}`",
        f"- Result: `{'PASS' if result.get('pass') else 'FAIL'}`",
        f"- Candidate: `{CANDIDATE_TAG}` / `{CANDIDATE_VERSION}`",
        f"- Candidate SHA256: `{CANDIDATE_SHA256}`",
        f"- Rollback attempted: `{int(bool(result.get('rollback_attempted')))}`",
        f"- Rollback health: version_ok=`{int(bool(result.get('rollback_version_ok')))}` selftest_fail0=`{int(bool(result.get('rollback_selftest_fail0')))}`",
        "",
        "## Scope",
        "",
        "- This is an A/V co-run smoke test: audio PCM-file playback and video page-flip streaming run in the same boot/runtime bundle.",
        "- It is **not** an exact A/V sync proof. It reduces integration risk before adding a native sync loop.",
        "- The default video fixture stays at six full-resolution frames, matching the V2879-proven transfer envelope.",
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
        f"- Co-run smoke pass: `{int(bool(av.get('corun_smoke_pass')))}`",
        "",
        "## Audio Markers",
        "",
        *(audio_lines or ["- No audio marker summary recorded."]),
        "",
        "## Safety",
        "",
        "- Flash path: `workspace/public/src/scripts/revalidation/native_init_flash.py`.",
        "- Only the boot partition is flashed, then rolled back to `v2321`.",
        "- Runtime payloads stay under `/cache/a90-runtime/pkg/av/v2882`; generated fixture bytes stay private.",
        "- Before staging, stale V2882 runtime payloads are removed to avoid partial-transfer cache exhaustion.",
        "- Audio amplitude and duration remain within source-enforced profile caps.",
        "- Video uses the existing KMS dumb-buffer page-flip path only.",
        "- No Venus, KGSL, raw DSI, panel init, backlight, PMIC, PWM, regulator, GPIO, or GDSC path is used.",
        "",
    ])


def live_run(args: argparse.Namespace, state: dict[str, Any]) -> dict[str, Any]:
    patch_child_module_paths()
    out_dir = ROOT / "workspace/private/runs/av" / f"v2882-av-pcm-video-corun-{now_slug()}"
    out_dir.mkdir(parents=True, exist_ok=True)
    steps: list[dict[str, Any]] = []
    result: dict[str, Any] = {
        "run_id": RUN_ID,
        "decision": "v2882-av-corun-live-started",
        "pass": False,
        "out_dir": rel(out_dir),
        "preflight": state,
        "steps": steps,
    }
    candidate_flash_attempted = False
    candidate_flash_ok = False
    try:
        if not preflight_ok(state):
            result["decision"] = "v2882-av-corun-preflight-failed-no-flash"
            return result
        fixtures = generate_fixtures(args, out_dir, steps)
        result["fixtures"] = fixtures
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
            "flash-v2880-av-corun",
            flash_command(CANDIDATE_IMAGE, CANDIDATE_VERSION, CANDIDATE_SHA256, from_native=True),
            timeout=args.flash_timeout,
        )
        candidate_flash_ok = flash.get("rc") == 0
        version = base.run_serial_step(out_dir, steps, "candidate-version", ["version"], timeout=90.0, retry_unsafe=True)
        status = base.run_serial_step(out_dir, steps, "candidate-status", ["status"], timeout=90.0, retry_unsafe=True)
        selftest = base.run_serial_step(out_dir, steps, "candidate-selftest", ["selftest", "verbose"], timeout=120.0, retry_unsafe=True)
        video_status = base.run_serial_step(out_dir, steps, "candidate-video-status", ["video", "status"], timeout=90.0, retry_unsafe=True)
        audio_status = base.run_serial_step(out_dir, steps, "candidate-audio-status", ["audio", "status"], timeout=90.0, retry_unsafe=True)
        result["candidate_version_ok"] = CANDIDATE_VERSION in stdout_of(version)
        result["candidate_status_stdout_path"] = status.get("stdout_path")
        result["candidate_selftest_fail0"] = selftest_step_ok(selftest)
        result["candidate_video_status_ok"] = "video.status.next_stream=" in stdout_of(video_status)
        result["candidate_audio_status_ok"] = "audio.status.version=" in stdout_of(audio_status)
        if not (
            result["candidate_version_ok"]
            and result["candidate_selftest_fail0"]
            and result["candidate_video_status_ok"]
            and result["candidate_audio_status_ok"]
        ):
            result["decision"] = "v2882-av-corun-candidate-health-failed-before-run"
            raise RuntimeError("candidate health/audio/video status failed before A/V run")

        result["runtime_install"] = install_fixtures(args, out_dir, steps, fixtures)
        if not result["runtime_install"].get("remote_audio_sha_match"):
            result["decision"] = "v2882-av-corun-audio-transfer-sha-mismatch"
            raise RuntimeError("remote audio fixture SHA mismatch")

        base.run_serial_step(out_dir, steps, "candidate-hide-menu-before-av", ["hide"], timeout=45.0, allow_error=True, retry_unsafe=True)
        audio_command = [
            "audio",
            "play",
            PROFILE,
            "--mode",
            "listen",
            "--duration-ms",
            str(args.duration_ms),
            "--amplitude-milli",
            str(args.amplitude_milli),
            "--manifest",
            BUNDLED_REMOTE_MANIFEST,
            "--pcm-file",
            REMOTE_AUDIO_PCM,
            "--execute",
        ]
        audio_step = base.run_serial_step(
            out_dir,
            steps,
            "candidate-av-audio-pcm-execute",
            audio_command,
            timeout=120.0,
            retry_unsafe=False,
            allow_error=True,
        )
        audio_execute_text = stdout_of(audio_step)
        result["audio_execute_stdout_path"] = audio_step.get("stdout_path")
        result["audio_execute_elapsed_sec"] = audio_step.get("elapsed_sec")
        if audio_step.get("rc") != 0 or "audio.play.worker.started=1" not in audio_execute_text:
            result["decision"] = "v2882-av-corun-audio-start-failed-before-video"
            raise RuntimeError("audio PCM-file worker did not start")

        video_step = base.run_serial_step(
            out_dir,
            steps,
            "candidate-av-video-stream-pageflip",
            [
                "video",
                "stream",
                "--manifest",
                REMOTE_VIDEO_MANIFEST,
                "--video-only",
                "--frames",
                str(args.frames),
                "--present",
                "pageflip",
            ],
            timeout=args.stream_timeout,
            retry_unsafe=False,
            allow_error=True,
        )
        video_text = stdout_of(video_step)
        result["video_stream_stdout_path"] = video_step.get("stdout_path")
        result["video_stream_elapsed_sec"] = video_step.get("elapsed_sec")

        worker = audio_live.wait_for_worker_done(out_dir, steps, args.play_timeout)
        result["audio_worker_done"] = bool(worker.get("done"))
        result["audio_worker_attempts"] = worker.get("attempts")
        result["audio_worker_status_stdout_path"] = worker.get("stdout_path")
        log_step = base.run_serial_step(
            out_dir,
            steps,
            "candidate-av-audio-worker-log",
            ["run", "/bin/busybox", "cat", REMOTE_PLAY_LOG],
            timeout=45.0,
            retry_unsafe=True,
            allow_error=True,
        )
        audio_log_text = stdout_of(log_step)
        result["audio_worker_log_stdout_path"] = log_step.get("stdout_path")
        audio_text = "\n".join([audio_execute_text, str(worker.get("text") or ""), audio_log_text])
        result["av_summary"] = classify_av_result(video_text, audio_text, args.frames)
        if video_step.get("rc") != 0 or not result["av_summary"].get("corun_smoke_pass"):
            result["decision"] = "v2882-av-corun-marker-failed-before-rollback"
            raise RuntimeError("A/V co-run did not emit required pass markers")
        after = base.run_serial_step(
            out_dir,
            steps,
            "candidate-selftest-after-av-corun",
            ["selftest", "verbose"],
            timeout=120.0,
            retry_unsafe=True,
        )
        result["candidate_selftest_after_av_fail0"] = selftest_step_ok(after)
        if not result["candidate_selftest_after_av_fail0"]:
            result["decision"] = "v2882-av-corun-post-selftest-failed"
            raise RuntimeError("candidate post-A/V selftest did not report fail=0")
        result["decision"] = "v2882-av-corun-live-pass-before-rollback"
        result["pass"] = True
    except Exception as exc:
        result.setdefault("decision", "v2882-av-corun-live-blocked")
        if result["decision"] == "v2882-av-corun-live-started":
            result["decision"] = "v2882-av-corun-live-blocked"
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


def dry_run_payload(args: argparse.Namespace, state: dict[str, Any]) -> dict[str, Any]:
    return {
        "decision": "v2882-av-corun-live-dry-run" if preflight_ok(state) else "v2882-av-corun-live-blocked",
        "ok": preflight_ok(state),
        "preflight": state,
        "commands": {
            "verify_current": flash_command(ROLLBACK_IMAGE, ROLLBACK_VERSION, ROLLBACK_SHA256, from_native=False) + ["--verify-only"],
            "flash_candidate": flash_command(CANDIDATE_IMAGE, CANDIDATE_VERSION, CANDIDATE_SHA256, from_native=True),
            "remote_mkdir": ["run", "/bin/toybox", "mkdir", "-p", REMOTE_VIDEO_DIR, REMOTE_AUDIO_DIR],
            "audio_execute": [
                "audio",
                "play",
                PROFILE,
                "--mode",
                "listen",
                "--duration-ms",
                str(args.duration_ms),
                "--amplitude-milli",
                str(args.amplitude_milli),
                "--manifest",
                BUNDLED_REMOTE_MANIFEST,
                "--pcm-file",
                REMOTE_AUDIO_PCM,
                "--execute",
            ],
            "video_stream": ["video", "stream", "--manifest", REMOTE_VIDEO_MANIFEST, "--video-only", "--frames", str(args.frames), "--present", "pageflip"],
            "audio_status": ["audio", "play-status"],
            "rollback": flash_command(ROLLBACK_IMAGE, ROLLBACK_VERSION, ROLLBACK_SHA256, from_native=True),
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--run-live", action="store_true")
    parser.add_argument("--bridge-host", default="127.0.0.1")
    parser.add_argument("--bridge-port", type=int, default=54321)
    parser.add_argument("--device-ip", default="192.168.7.2")
    parser.add_argument("--host-ip", default="192.168.7.1")
    parser.add_argument("--host-prefix", type=int, default=24)
    parser.add_argument("--tcp-port", type=int, default=2325)
    parser.add_argument("--command-timeout", type=float, default=60.0)
    parser.add_argument("--tcp-timeout", type=float, default=30.0)
    parser.add_argument("--device-toolbox", default=tiny_live.DEFAULT_DEVICE_TOOLBOX)
    parser.add_argument("--flash-timeout", type=float, default=900.0)
    parser.add_argument("--transfer-port", type=int, default=18421)
    parser.add_argument("--transfer-delay", type=float, default=0.05)
    parser.add_argument("--transfer-timeout", type=float, default=240.0)
    parser.add_argument("--repair-host-ncm", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--ncm-setup-timeout", type=float, default=120.0)
    parser.add_argument("--ncm-interface-timeout", type=float, default=20.0)
    parser.add_argument("--ncm-setup-sudo", default="sudo -n")
    parser.add_argument("--inventory-transport", choices=("auto", "tcpctl", "serial"), default="auto")
    parser.add_argument("--play-timeout", type=float, default=180.0)
    parser.add_argument("--stream-timeout", type=float, default=120.0)
    parser.add_argument("--duration-ms", type=int, default=3000)
    parser.add_argument("--amplitude-milli", type=int, default=80)
    parser.add_argument("--frequency-hz", type=int, default=440)
    parser.add_argument("--width", type=int, default=1080)
    parser.add_argument("--height", type=int, default=2400)
    parser.add_argument("--stride", type=int, default=4352)
    parser.add_argument("--frames", type=int, default=6)
    parser.add_argument("--fps-num", type=int, default=3)
    parser.add_argument("--fps-den", type=int, default=1)
    parser.add_argument("--pattern", choices=("bars", "checker", "pulse"), default="checker")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    patch_child_module_paths()
    state = preflight_state(args)
    if args.dry_run:
        print(json.dumps(dry_run_payload(args, state), ensure_ascii=False, indent=2, sort_keys=True))
        return 0 if preflight_ok(state) else 2
    result = live_run(args, state)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result.get("decision") == "v2882-av-corun-live-pass-before-rollback" and result.get("rollback_selftest_fail0") else 1


if __name__ == "__main__":
    raise SystemExit(main())
