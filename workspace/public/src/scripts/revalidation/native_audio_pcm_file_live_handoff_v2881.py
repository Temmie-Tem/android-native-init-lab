#!/usr/bin/env python3
"""V2881 live validation for V2880 bounded audio PCM-file playback.

This runner flashes the V2880 candidate, stages a private bounded raw S16LE
stereo fixture under /cache/a90-runtime, validates dry-run marker coverage, runs
`audio play ... --pcm-file ... --execute`, then rolls back to v2321 and verifies
selftest fail=0.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import struct
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from _workspace_bootstrap import repo_root
import native_audio_tinyalsa_inventory_live_handoff_v2349 as tiny_live
import native_audio_v2798_readiness_replay_live_handoff_v2801 as base

ROOT = repo_root()
RUN_ID = "V2881"
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
REPORT_PATH = ROOT / "docs/reports/NATIVE_INIT_V2881_AUDIO_PCM_FILE_LIVE_2026-06-19.md"
BUILD_MANIFEST = ROOT / "workspace/private/builds/native-init/v2880-audio-pcm-file/manifest.json"

PROFILE = "internal-speaker-safe"
BUNDLED_REMOTE_MANIFEST = "/a90/audio/manifests/audio-setcal-internal-speaker-safe.manifest"
REMOTE_DIR = "/cache/a90-runtime/pkg/audio/v2881"
REMOTE_PCM = f"{REMOTE_DIR}/tone.s16le"
REMOTE_PLAY_LOG = "/cache/a90-audio-play/worker.log"
SAMPLE_RATE = 48_000
CHANNELS = 2
BYTES_PER_SAMPLE = 2
SELFTEST_FAIL0_RE = re.compile(r"\bfail=0\b")


def rel(path: Path) -> str:
    return base.rel(path)


def now_slug() -> str:
    return datetime.now(timezone.utc).astimezone().strftime("%Y%m%d-%H%M%S")


def sha256_file(path: Path) -> str:
    return base.sha256_file(path)


def stdout_of(step: dict[str, Any]) -> str:
    return base.stdout_of(step)


def write_json(path: Path, payload: Any) -> None:
    base.write_json(path, payload)


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
    text = stdout_of(step)
    return bool(SELFTEST_FAIL0_RE.search(text)) or base.protocol_selftest_ok(step)


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
        "build_manifest": file_state(BUILD_MANIFEST),
        "profile": PROFILE,
        "remote_manifest": BUNDLED_REMOTE_MANIFEST,
        "remote_dir": REMOTE_DIR,
        "remote_pcm": REMOTE_PCM,
        "duration_ms": args.duration_ms,
        "amplitude_milli": args.amplitude_milli,
        "fixture_sample_rate": SAMPLE_RATE,
        "fixture_channels": CHANNELS,
        "hard_boundary": [
            "boot partition only via native_init_flash.py",
            "rollback to v2321 and verify selftest fail=0",
            "private generated PCM fixture not committed",
            "PCM file restricted to /cache/a90-runtime",
            "use bundled /a90/audio SET-cal manifest; no host ACDB deployment",
            "no PMIC/GPIO/GDSC/regulator/raw DSI/panel init/backlight changes",
        ],
    }


def preflight_ok(state: dict[str, Any]) -> bool:
    return bool(
        state["candidate"].get("sha256_ok")
        and state["rollback"].get("sha256_ok")
        and state["fallback_v2237"].get("sha256_ok")
        and state["fallback_v48"].get("exists")
        and state["flash_helper"].get("exists")
    )


def generate_pcm_fixture(args: argparse.Namespace, out_dir: Path) -> dict[str, Any]:
    fixture_dir = out_dir / "fixture"
    fixture_dir.mkdir(parents=True, exist_ok=True)
    path = fixture_dir / "tone.s16le"
    frames = SAMPLE_RATE * args.duration_ms // 1000
    peak = max(0, min(32767, 32767 * args.amplitude_milli // 1000))
    actual_peak = 0
    with path.open("wb") as handle:
        for frame in range(frames):
            sample = int(math.sin((2.0 * math.pi * args.frequency_hz * frame) / SAMPLE_RATE) * peak)
            actual_peak = max(actual_peak, abs(sample))
            packed = struct.pack("<h", sample)
            handle.write(packed * CHANNELS)
    return {
        "path": rel(path),
        "size": path.stat().st_size,
        "sha256": sha256_file(path),
        "sample_rate": SAMPLE_RATE,
        "channels": CHANNELS,
        "format": "s16le",
        "duration_ms": args.duration_ms,
        "frames": frames,
        "frequency_hz": args.frequency_hz,
        "amplitude_milli": args.amplitude_milli,
        "peak_abs_sample": actual_peak,
        "expected_bytes": frames * CHANNELS * BYTES_PER_SAMPLE,
    }


def install_fixture(args: argparse.Namespace,
                    out_dir: Path,
                    steps: list[dict[str, Any]],
                    fixture: dict[str, Any]) -> dict[str, Any]:
    readiness = tiny_live.probe_transfer_readiness(args, out_dir, steps)
    selected = str(readiness["selected_transport"])
    control_channel = "tcpctl" if selected == "tcpctl" else "bridge"
    local_path = ROOT / str(fixture["path"])
    base.run_serial_step(
        out_dir,
        steps,
        "candidate-create-remote-audio-dir",
        ["run", "/bin/toybox", "mkdir", "-p", REMOTE_DIR],
        timeout=45.0,
        retry_unsafe=True,
    )
    install = base.run_step(
        out_dir,
        steps,
        "install-audio-pcm-fixture",
        tiny_live.install_command(
            args,
            local_path,
            REMOTE_PCM,
            args.transfer_port,
            control_channel=control_channel,
        ),
        timeout=args.transfer_timeout + 60.0,
    )
    remote_sha = base.run_serial_step(
        out_dir,
        steps,
        "candidate-remote-pcm-sha256",
        ["run", "/bin/toybox", "sha256sum", REMOTE_PCM],
        timeout=45.0,
        retry_unsafe=True,
    )
    return {
        "transfer_readiness": readiness,
        "selected_transport": selected,
        "control_channel": control_channel,
        "install_stdout_path": install.get("stdout_path"),
        "remote_sha_stdout_path": remote_sha.get("stdout_path"),
        "remote_sha_match": fixture["sha256"] in stdout_of(remote_sha),
    }


def classify_pcm_output(text: str) -> dict[str, Any]:
    return {
        "pcm_source_selected": "audio.play.source=pcm-file" in text,
        "pcm_file_supported": "audio.play.pcm_file_supported=1" in text,
        "pcm_path_allowed": "audio.play.pcm_file.path_allowed=1" in text,
        "dry_run_ok": "audio.play.dry_run_ok=1" in text,
        "worker_started": "audio.play.worker.started=1" in text,
        "worker_done": "audio.play.worker.done=1 rc=0" in text,
        "worker_pcm_file": f"audio.play.worker.pcm_file={REMOTE_PCM}" in text,
        "integrated_pcm_file": f"audio.play.integrated.pcm_file={REMOTE_PCM}" in text,
        "execute_source_pcm": "audio.play.execute.source=pcm-file" in text,
        "execute_plan_source_pcm": "audio.play.execute.plan.source=pcm-file" in text,
        "execute_plan_waveform_file": "audio.play.execute.plan.waveform=s16le-stereo-bounded-file" in text,
        "pcm_file_validated": "audio.play.pcm_file.validated=1" in text,
        "pcm_file_amplitude_within_cap": "audio.play.pcm_file.amplitude_within_cap=1" in text,
        "pcm_write_attempted": "audio.play.execute.pcm_write_attempted=1" in text,
        "pcm_done": "audio.play.execute.done=1" in text,
        "listen_begin": "A90_LISTEN_WINDOW_BEGIN" in text,
        "listen_end": "A90_LISTEN_WINDOW_END" in text,
        "integrated_done": "audio.play.integrated.done=1 rc=0" in text,
        "route_apply_ok": "audio.play.integrated.route_apply.rc=0" in text,
        "route_reset_ok": "audio.play.integrated.route_reset.rc=0" in text,
        "setcal_all_set": "audio.setcal.execute.set_count=11" in text,
        "setcal_deallocated": "audio.setcal.execute.deallocated_count=4" in text,
        "safety_amplitude": "audio.play.safety.amplitude_within_cap=1" in text,
        "safety_duration": "audio.play.safety.duration_within_cap=1" in text,
    }


def pcm_output_pass(summary: dict[str, Any]) -> bool:
    required = [
        "pcm_source_selected",
        "pcm_file_supported",
        "pcm_path_allowed",
        "worker_started",
        "worker_done",
        "worker_pcm_file",
        "integrated_pcm_file",
        "execute_source_pcm",
        "execute_plan_source_pcm",
        "execute_plan_waveform_file",
        "pcm_file_validated",
        "pcm_file_amplitude_within_cap",
        "pcm_write_attempted",
        "pcm_done",
        "listen_begin",
        "listen_end",
        "integrated_done",
        "route_apply_ok",
        "route_reset_ok",
        "setcal_all_set",
        "setcal_deallocated",
        "safety_amplitude",
        "safety_duration",
    ]
    return all(bool(summary.get(key)) for key in required)


def wait_for_worker_done(out_dir: Path,
                         steps: list[dict[str, Any]],
                         timeout_sec: float,
                         interval_sec: float = 2.0) -> dict[str, Any]:
    deadline = time.time() + timeout_sec
    attempts = 0
    last_step: dict[str, Any] | None = None
    while time.time() < deadline:
        attempts += 1
        step = base.run_serial_step(
            out_dir,
            steps,
            f"candidate-audio-play-status-{attempts:02d}",
            ["audio", "play-status"],
            timeout=45.0,
            retry_unsafe=True,
            allow_error=True,
        )
        last_step = step
        text = stdout_of(step)
        if "audio.play.worker.done=1" in text:
            return {
                "done": True,
                "attempts": attempts,
                "stdout_path": step.get("stdout_path"),
                "text": text,
            }
        time.sleep(interval_sec)
    return {
        "done": False,
        "attempts": attempts,
        "stdout_path": last_step.get("stdout_path") if last_step else None,
        "text": stdout_of(last_step) if last_step else "",
    }


def render_report(result: dict[str, Any]) -> str:
    fixture = result.get("fixture") or {}
    install = result.get("fixture_install") or {}
    summary = result.get("pcm_summary") or {}
    summary_lines = [f"- `{key}`: `{int(bool(value))}`" for key, value in sorted(summary.items())]
    if not summary_lines:
        summary_lines = ["- No PCM marker summary recorded."]
    return "\n".join([
        "# Native Init V2881 Audio PCM-File Live Handoff",
        "",
        "## Summary",
        "",
        f"- Cycle: `{RUN_ID}`",
        "- Track: active Video playback pipeline; audio file-source validation for A/V bundles.",
        f"- Decision: `{result.get('decision')}`",
        f"- Result directory: `{result.get('out_dir')}`",
        f"- Candidate tag/version: `{CANDIDATE_TAG}` / `{CANDIDATE_VERSION}`",
        f"- Candidate image SHA256: `{CANDIDATE_SHA256}`",
        f"- Rollback attempted: `{int(bool(result.get('rollback_attempted')))}`",
        f"- Rollback recovery fallback used: `{int(bool(result.get('rollback_recovery_fallback_used')))}`",
        f"- Rollback health: version_ok=`{int(bool(result.get('rollback_version_ok')))}` selftest_fail0=`{int(bool(result.get('rollback_selftest_fail0')))}`",
        "",
        "## PCM Fixture",
        "",
        f"- Local private fixture: `{fixture.get('path')}`",
        f"- Remote fixture: `{REMOTE_PCM}`",
        f"- Format: `{fixture.get('sample_rate')} Hz`, `{fixture.get('channels')}` channels, `{fixture.get('format')}`",
        f"- Duration / amplitude: `{fixture.get('duration_ms')}` ms / `{fixture.get('amplitude_milli')}` milli",
        f"- Size / SHA256: `{fixture.get('size')}` / `{fixture.get('sha256')}`",
        f"- Peak absolute sample: `{fixture.get('peak_abs_sample')}`",
        f"- Transfer selected/control: `{install.get('selected_transport')}` / `{install.get('control_channel')}`",
        f"- Remote SHA matched: `{int(bool(install.get('remote_sha_match')))}`",
        "",
        "## Playback Evidence",
        "",
        f"- Dry-run stdout: `{result.get('dry_run_stdout_path')}`",
        f"- Execute stdout: `{result.get('execute_stdout_path')}`",
        f"- Worker status done/attempts: `{int(bool(result.get('worker_status_done')))}` / `{result.get('worker_status_attempts')}`",
        f"- Worker status stdout: `{result.get('worker_status_stdout_path')}`",
        f"- Worker log stdout: `{result.get('worker_log_stdout_path')}`",
        f"- PCM output pass: `{int(bool(result.get('pcm_output_pass')))}`",
        *summary_lines,
        "",
        "## Safety",
        "",
        "- Flash path: `workspace/public/src/scripts/revalidation/native_init_flash.py`.",
        "- Only the boot partition is flashed, then rolled back to `v2321`.",
        "- No host ACDB payload deployment is performed; V2880 uses the bundled `/a90/audio` SET-cal package.",
        "- The raw PCM fixture is generated under `workspace/private` and staged only under `/cache/a90-runtime`.",
        "- Native source validates regular file type, size, seekability, and peak amplitude before ALSA writes.",
        "- No Venus, GPU/KGSL, raw DSI, panel init, backlight, PMIC, PWM, regulator, GPIO, or GDSC path is used.",
        "",
    ])


def live_run(args: argparse.Namespace, state: dict[str, Any]) -> dict[str, Any]:
    out_dir = ROOT / "workspace/private/runs/audio" / f"v2881-audio-pcm-file-{now_slug()}"
    out_dir.mkdir(parents=True, exist_ok=True)
    steps: list[dict[str, Any]] = []
    result: dict[str, Any] = {
        "run_id": RUN_ID,
        "decision": "v2881-audio-pcm-file-live-started",
        "out_dir": rel(out_dir),
        "preflight": state,
        "candidate_sha256": CANDIDATE_SHA256,
        "steps": steps,
    }
    candidate_flash_attempted = False
    candidate_flash_ok = False

    try:
        if not preflight_ok(state):
            result["decision"] = "v2881-audio-pcm-file-preflight-failed-no-flash"
            return result
        fixture = generate_pcm_fixture(args, out_dir)
        result["fixture"] = fixture
        verify = base.run_step(
            out_dir,
            steps,
            "verify-current-v2321",
            flash_command(ROLLBACK_IMAGE, ROLLBACK_VERSION, ROLLBACK_SHA256, from_native=False) + ["--verify-only"],
            timeout=args.flash_timeout,
        )
        result["verify_current_stdout_path"] = verify.get("stdout_path")
        candidate_flash_attempted = True
        flash = base.run_step(
            out_dir,
            steps,
            "flash-v2880-audio-pcm-file",
            flash_command(CANDIDATE_IMAGE, CANDIDATE_VERSION, CANDIDATE_SHA256, from_native=True),
            timeout=args.flash_timeout,
        )
        candidate_flash_ok = flash.get("rc") == 0
        result["flash_candidate_stdout_path"] = flash.get("stdout_path")
        version = base.run_serial_step(out_dir, steps, "candidate-version", ["version"], timeout=90.0, retry_unsafe=True)
        status = base.run_serial_step(out_dir, steps, "candidate-status", ["status"], timeout=90.0, retry_unsafe=True)
        selftest = base.run_serial_step(out_dir, steps, "candidate-selftest", ["selftest", "verbose"], timeout=120.0, retry_unsafe=True)
        result["candidate_version_ok"] = CANDIDATE_VERSION in stdout_of(version)
        result["candidate_status_stdout_path"] = status.get("stdout_path")
        result["candidate_selftest_fail0"] = selftest_step_ok(selftest)
        if not result["candidate_version_ok"] or not result["candidate_selftest_fail0"]:
            result["decision"] = "v2881-audio-pcm-file-candidate-health-failed-before-play"
            raise RuntimeError("candidate health check failed before PCM-file playback")

        result["fixture_install"] = install_fixture(args, out_dir, steps, fixture)
        if not result["fixture_install"].get("remote_sha_match"):
            result["decision"] = "v2881-audio-pcm-file-transfer-sha-mismatch-before-play"
            raise RuntimeError("remote PCM fixture SHA mismatch")

        dry_command = [
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
            REMOTE_PCM,
            "--dry-run",
        ]
        dry = base.run_serial_step(
            out_dir,
            steps,
            "candidate-audio-pcm-file-dry-run",
            dry_command,
            timeout=90.0,
            retry_unsafe=True,
            allow_error=True,
        )
        dry_text = stdout_of(dry)
        result["dry_run_stdout_path"] = dry.get("stdout_path")
        result["dry_run_summary"] = classify_pcm_output(dry_text)
        if dry.get("rc") != 0 or not (
            result["dry_run_summary"].get("pcm_source_selected")
            and result["dry_run_summary"].get("pcm_path_allowed")
            and result["dry_run_summary"].get("dry_run_ok")
        ):
            result["decision"] = "v2881-audio-pcm-file-dry-run-failed-before-execute"
            raise RuntimeError("PCM-file dry-run did not confirm source/path safety markers")

        execute_command = dry_command[:-1] + ["--execute"]
        execute = base.run_serial_step(
            out_dir,
            steps,
            "candidate-audio-pcm-file-execute",
            execute_command,
            timeout=120.0,
            retry_unsafe=False,
            allow_error=True,
        )
        execute_text = stdout_of(execute)
        result["execute_stdout_path"] = execute.get("stdout_path")
        if execute.get("rc") != 0 or "audio.play.worker.started=1" not in execute_text:
            result["decision"] = "v2881-audio-pcm-file-start-failed-before-rollback"
            result["pcm_summary"] = classify_pcm_output("\n".join([dry_text, execute_text]))
            raise RuntimeError("PCM-file execute did not start worker")

        worker = wait_for_worker_done(out_dir, steps, args.play_timeout)
        result["worker_status_done"] = bool(worker.get("done"))
        result["worker_status_attempts"] = worker.get("attempts")
        result["worker_status_stdout_path"] = worker.get("stdout_path")
        log_step = base.run_serial_step(
            out_dir,
            steps,
            "candidate-audio-pcm-file-worker-log",
            ["run", "/bin/busybox", "cat", REMOTE_PLAY_LOG],
            timeout=45.0,
            retry_unsafe=True,
            allow_error=True,
        )
        log_text = stdout_of(log_step)
        result["worker_log_stdout_path"] = log_step.get("stdout_path")
        combined_text = "\n".join([dry_text, execute_text, str(worker.get("text") or ""), log_text])
        result["pcm_summary"] = classify_pcm_output(combined_text)
        result["pcm_output_pass"] = pcm_output_pass(result["pcm_summary"])
        result["candidate_selftest_after_play_fail0"] = selftest_step_ok(
            base.run_serial_step(
                out_dir,
                steps,
                "candidate-selftest-after-pcm-file-play",
                ["selftest", "verbose"],
                timeout=120.0,
                retry_unsafe=True,
            )
        )
        if not result["pcm_output_pass"] or not result["candidate_selftest_after_play_fail0"]:
            result["decision"] = "v2881-audio-pcm-file-worker-failed-before-rollback"
            raise RuntimeError("PCM-file worker did not emit all required pass markers")
        result["decision"] = "v2881-audio-pcm-file-live-pass-before-rollback"
    except Exception as exc:
        result.setdefault("decision", "v2881-audio-pcm-file-live-blocked")
        if result["decision"] == "v2881-audio-pcm-file-live-started":
            result["decision"] = "v2881-audio-pcm-file-live-blocked"
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
                rollback_version = base.run_serial_step(
                    out_dir,
                    steps,
                    "rollback-version",
                    ["version"],
                    timeout=90.0,
                    retry_unsafe=True,
                    allow_error=True,
                )
                rollback_selftest = base.run_serial_step(
                    out_dir,
                    steps,
                    "rollback-selftest",
                    ["selftest", "verbose"],
                    timeout=120.0,
                    retry_unsafe=True,
                    allow_error=True,
                )
                result["rollback_version_ok"] = ROLLBACK_VERSION in stdout_of(rollback_version)
                result["rollback_selftest_fail0"] = selftest_step_ok(rollback_selftest)
        write_json(out_dir / "result.json", result)
        REPORT_PATH.write_text(render_report(result), encoding="utf-8")
    return result


def dry_run_payload(args: argparse.Namespace, state: dict[str, Any]) -> dict[str, Any]:
    return {
        "decision": "v2881-audio-pcm-file-live-dry-run",
        "preflight_ok": preflight_ok(state),
        "preflight": state,
        "commands": {
            "verify_current": flash_command(ROLLBACK_IMAGE, ROLLBACK_VERSION, ROLLBACK_SHA256, from_native=False) + ["--verify-only"],
            "flash_candidate": flash_command(CANDIDATE_IMAGE, CANDIDATE_VERSION, CANDIDATE_SHA256, from_native=True),
            "remote_mkdir": ["run", "/bin/toybox", "mkdir", "-p", REMOTE_DIR],
            "install_pcm_fixture": f"tcpctl install {REMOTE_PCM}",
            "dry_run": [
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
                REMOTE_PCM,
                "--dry-run",
            ],
            "execute": [
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
                REMOTE_PCM,
                "--execute",
            ],
            "play_status": ["audio", "play-status"],
            "play_worker_log": ["run", "/bin/busybox", "cat", REMOTE_PLAY_LOG],
            "rollback": flash_command(ROLLBACK_IMAGE, ROLLBACK_VERSION, ROLLBACK_SHA256, from_native=True),
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true", help="verify local artifacts and print the live plan")
    mode.add_argument("--run-live", action="store_true", help="flash and run the bounded PCM-file playback validation")
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
    parser.add_argument("--transfer-port", type=int, default=18381)
    parser.add_argument("--transfer-delay", type=float, default=1.0)
    parser.add_argument("--transfer-timeout", type=float, default=120.0)
    parser.add_argument("--repair-host-ncm", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--ncm-setup-timeout", type=float, default=120.0)
    parser.add_argument("--ncm-interface-timeout", type=float, default=20.0)
    parser.add_argument("--ncm-setup-sudo", default="sudo -n")
    parser.add_argument("--inventory-transport", choices=("auto", "tcpctl", "serial"), default="auto")
    parser.add_argument("--play-timeout", type=float, default=150.0)
    parser.add_argument("--duration-ms", type=int, default=1000)
    parser.add_argument("--amplitude-milli", type=int, default=80)
    parser.add_argument("--frequency-hz", type=int, default=440)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    state = preflight_state(args)
    if args.dry_run:
        print(json.dumps(dry_run_payload(args, state), ensure_ascii=False, indent=2, sort_keys=True))
        return 0 if preflight_ok(state) else 2
    result = live_run(args, state)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result.get("decision") == "v2881-audio-pcm-file-live-pass-before-rollback" and result.get("rollback_selftest_fail0") else 1


if __name__ == "__main__":
    raise SystemExit(main())
