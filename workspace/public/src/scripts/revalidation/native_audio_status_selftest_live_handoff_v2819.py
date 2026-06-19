#!/usr/bin/env python3
"""V2819 live validation for the V2818 audio status/selftest observability image.

This flashes the V2818 0.10.1 image, verifies only read-only serial surfaces
(`audio status` and `selftest verbose`), then rolls back to V2321.
"""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from _workspace_bootstrap import repo_root
import native_audio_speaker_descriptor_api_device_validation_handoff_v2788 as base

ROOT = repo_root()
CYCLE = "V2819"
BUILD_MANIFEST = ROOT / "workspace/private/builds/native-init/v2818-audio-status-selftest/manifest.json"
CANDIDATE_IMAGE = ROOT / "workspace/private/inputs/boot_images/boot_linux_v2818_audio_status_selftest.img"
CANDIDATE_VERSION = "0.10.1"
CANDIDATE_TAG = "v2818-audio-status-selftest"
REPORT_PATH = ROOT / "docs/reports/NATIVE_INIT_V2819_AUDIO_STATUS_SELFTEST_LIVE_2026-06-19.md"
ROLLBACK_VERSION = base.ROLLBACK_VERSION
ROLLBACK_IMAGE = base.ROLLBACK_IMAGE
ROLLBACK_SHA256 = base.ROLLBACK_SHA256
REQUIRED_AUDIO_STATUS_MARKERS = [
    "audio.status.core.promoted=1",
    "audio.status.core.promotion_run=V2815",
    "audio.status.core.version=0.10.0",
    "audio.status.core.build_tag=v2812-audio-core-promotion-candidate",
    "audio.status.core.validation_run=V2814",
    "audio.status.core.native_play_gate=closed",
    "audio.status.profile.id=internal-speaker-safe",
    "audio.status.profile.app_type=69941",
    "audio.status.profile.acdb_id=15",
    "audio.status.profile.sample_rate=48000",
    "audio.status.profile.bit_width=16",
    "audio.status.profile.route_control_count=13",
    "audio.status.profile.speaker_count=6",
    "audio.status.safety.amplitude_cap_milli=200",
    "audio.status.safety.smart_amp_boost_write_allowed=0",
    "audio.status.safety.wsa_speaker_protection_verified=0",
]
REQUIRED_SELFTEST_MARKERS = [
    "PASS      audio",
    "core=0.10.0",
    "profile=internal-speaker-safe",
    "route=13",
    "speakers=6",
    "cap=200",
    "boost=blocked",
    "sp=unverified",
]
SCREENAPP_COMMAND: list[str] | None = None
REQUIRED_SCREENAPP_MARKERS: list[str] = []
EXTRA_MARKER_STEPS: list[dict[str, Any]] = []
MARKER_RETRY_LIMIT = 2
MARKER_RETRY_DELAY_SEC = 0.5


def rel(path: Path) -> str:
    return base.rel(path)


def now_slug() -> str:
    return datetime.now(timezone.utc).astimezone().strftime("%Y%m%d-%H%M%S")


def write_json(path: Path, payload: Any) -> None:
    base.write_json(path, payload)


def decision_prefix() -> str:
    return CYCLE.lower()


def preflight_state() -> dict[str, Any]:
    manifest = base.read_json(BUILD_MANIFEST)
    candidate_expected_sha = str(manifest.get("boot_sha256") or "")
    return {
        "cycle": CYCLE,
        "build_manifest": rel(BUILD_MANIFEST),
        "build_manifest_exists": BUILD_MANIFEST.exists(),
        "build_manifest_decision": manifest.get("decision"),
        "candidate": base.file_state(CANDIDATE_IMAGE, candidate_expected_sha),
        "rollback": base.file_state(ROLLBACK_IMAGE, ROLLBACK_SHA256),
        "fallback_v2237": base.file_state(base.FALLBACK_V2237_IMAGE, base.FALLBACK_V2237_SHA256),
        "fallback_v48": base.file_state(base.FALLBACK_V48_IMAGE),
        "flash_helper": base.file_state(base.FLASH),
        "a90ctl": base.file_state(base.A90CTL),
        "candidate_expect_version": CANDIDATE_VERSION,
        "candidate_expect_tag": CANDIDATE_TAG,
        "rollback_expect_version": ROLLBACK_VERSION,
        "live_scope": [
            "boot partition only",
            f"flash {CANDIDATE_TAG} through native_init_flash.py",
            "run read-only version/status/selftest/audio status",
            "optionally run display-only screenapp validation when configured",
            "do not run ADSP boot, route apply/reset, ACDB SET, PCM open, mixer write, or playback",
            "rollback to v2321",
        ],
    }


def preflight_ok(state: dict[str, Any]) -> bool:
    return bool(
        state.get("build_manifest_exists")
        and state.get("candidate", {}).get("sha256_ok")
        and state.get("rollback", {}).get("sha256_ok")
        and state.get("fallback_v2237", {}).get("sha256_ok")
        and state.get("fallback_v48", {}).get("exists")
        and state.get("flash_helper", {}).get("exists")
        and state.get("a90ctl", {}).get("exists")
    )


def text_of(step: dict[str, Any]) -> str:
    return base.stdout_of(step)


def markers_present(text: str, markers: list[str]) -> dict[str, Any]:
    missing = [marker for marker in markers if marker not in text]
    return {"ok": not missing, "missing": missing, "count": len(markers) - len(missing), "required": len(markers)}


def run_serial_marker_step(
    out_dir: Path,
    steps: list[dict[str, Any]],
    name: str,
    command: list[str],
    markers: list[str],
    *,
    timeout: float,
    pass_check: Any | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Run a read-only serial command and retry if marker collection is partial.

    Serial protocol noise can truncate the text transcript while the command
    itself succeeds. These commands are read-only/display-only validation
    surfaces, so a bounded re-read is safer than classifying a healthy boot as a
    device failure.
    """

    best_step: dict[str, Any] | None = None
    best_markers: dict[str, Any] | None = None
    best_score = (-1, -1)
    attempts: list[dict[str, Any]] = []
    for attempt in range(MARKER_RETRY_LIMIT + 1):
        step_name = name if attempt == 0 else f"{name}-marker-retry{attempt}"
        step = base.run_serial_step(
            out_dir,
            steps,
            step_name,
            command,
            timeout=timeout,
            retry_unsafe=True,
        )
        marker_state = markers_present(text_of(step), markers)
        pass_ok = bool(pass_check(step)) if pass_check is not None else bool(step.get("ok"))
        attempts.append({
            "step": step_name,
            "command_ok": bool(step.get("ok")),
            "pass_check_ok": pass_ok,
            "marker_count": marker_state["count"],
            "marker_required": marker_state["required"],
            "marker_ok": marker_state["ok"],
        })
        score = (int(pass_ok), int(marker_state["count"]))
        if score > best_score:
            best_step = step
            best_markers = marker_state
            best_score = score
        if pass_ok and marker_state["ok"]:
            break
        if attempt < MARKER_RETRY_LIMIT:
            time.sleep(MARKER_RETRY_DELAY_SEC)

    assert best_step is not None and best_markers is not None
    best_markers = dict(best_markers)
    best_markers["attempts"] = attempts
    best_markers["best_step"] = best_step.get("name")
    best_markers["pass_check_ok"] = bool(best_score[0])
    return best_step, best_markers


def render_report(result: dict[str, Any]) -> str:
    audio = result.get("audio_status_markers", {})
    selftest = result.get("selftest_markers", {})
    screenapp = result.get("screenapp_markers", {})
    return "\n".join([
        "# Native Init V2819 Audio Status/Selftest Live Validation",
        "",
        "## Summary",
        "",
        f"- Cycle: `{CYCLE}`",
        "- Track: post-promotion audio Tier C device observability.",
        f"- Decision: `{result.get('decision')}`",
        f"- Result directory: `{result.get('out_dir')}`",
        f"- Candidate image: `{rel(CANDIDATE_IMAGE)}`",
        f"- Candidate SHA256: `{result.get('candidate_sha256')}`",
        f"- Candidate version/tag expected: `{CANDIDATE_VERSION}` / `{CANDIDATE_TAG}`",
        f"- Candidate version/tag observed OK: `{int(bool(result.get('candidate_version_ok')))}`",
        f"- `audio status` marker pass: `{int(bool(audio.get('ok')))}` ({audio.get('count', 0)}/{audio.get('required', 0)})",
        f"- `selftest verbose` audio marker pass: `{int(bool(selftest.get('ok')))}` ({selftest.get('count', 0)}/{selftest.get('required', 0)})",
        f"- `screenapp` marker pass: `{int(bool(screenapp.get('ok', not REQUIRED_SCREENAPP_MARKERS)))}` ({screenapp.get('count', 0)}/{screenapp.get('required', 0)})",
        f"- Rollback attempted: `{int(bool(result.get('rollback_attempted')))}`",
        f"- Rollback recovery fallback used: `{int(bool(result.get('rollback_recovery_fallback_used')))}`",
        f"- Rollback health: version_ok=`{int(bool(result.get('rollback_version_ok')))}` selftest_fail0=`{int(bool(result.get('rollback_selftest_fail0')))}`",
        "",
        "## Finding",
        "",
        "- V2819 flashes the V2818 `0.10.1` audio observability image and validates the new read-only status/selftest surfaces on hardware.",
        "- Expected pass: `audio status` exposes the promoted `0.10.0` core metadata and safety fields, `selftest verbose` exposes the static audio row, and final rollback to `v2321` ends with `selftest fail=0`.",
        "- This validation intentionally performs no ADSP boot, `/dev/snd` materialization, route apply/reset, ACDB SET, PCM open, mixer write, speaker write, or playback.",
        "",
        "## Missing Markers",
        "",
        f"- `audio status`: `{audio.get('missing', [])}`",
        f"- `selftest verbose`: `{selftest.get('missing', [])}`",
        f"- `screenapp`: `{screenapp.get('missing', [])}`",
        "",
        "## Safety",
        "",
        "- Flash path: `workspace/public/src/scripts/revalidation/native_init_flash.py`.",
        "- Only the boot partition is written.",
        "- No forbidden partitions are touched.",
        "- Public report contains metadata only; full serial transcripts stay under `workspace/private/runs/audio/`.",
        "",
    ])


def live_run(args: argparse.Namespace, state: dict[str, Any]) -> dict[str, Any]:
    if not preflight_ok(state):
        raise SystemExit("refusing live run: preflight failed")

    candidate_sha = str(state["candidate"]["sha256"])
    out_dir = ROOT / f"workspace/private/runs/audio/{decision_prefix()}-audio-status-selftest-live-{now_slug()}"
    out_dir.mkdir(parents=True, exist_ok=False)
    write_json(out_dir / "preflight.json", state)
    steps: list[dict[str, Any]] = []
    result: dict[str, Any] = {
        "decision": f"{decision_prefix()}-audio-status-selftest-live-started",
        "out_dir": rel(out_dir),
        "candidate_sha256": candidate_sha,
        "steps": steps,
        "rollback_attempted": False,
        "rollback_recovery_fallback_used": False,
        "rollback_version_ok": False,
        "rollback_selftest_fail0": False,
    }

    candidate_flash_attempted = False
    candidate_flash_ok = False
    try:
        base.run_step(
            out_dir,
            steps,
            "preflight-current-v2321-verify",
            base.flash_command(ROLLBACK_IMAGE, ROLLBACK_VERSION, ROLLBACK_SHA256, from_native=False) + ["--verify-only"],
            timeout=args.flash_timeout,
        )
        current_selftest = base.run_serial_step(
            out_dir,
            steps,
            "preflight-current-selftest",
            ["selftest", "verbose"],
            timeout=120.0,
            retry_unsafe=True,
        )
        result["preflight_current_selftest_fail0"] = base.selftest_step_ok(current_selftest)
        if not result["preflight_current_selftest_fail0"]:
            raise RuntimeError("resident preflight selftest did not report fail=0")

        candidate_flash_attempted = True
        base.run_step(
            out_dir,
            steps,
            "flash-v2818-candidate",
            base.flash_command(CANDIDATE_IMAGE, CANDIDATE_VERSION, candidate_sha, from_native=True),
            timeout=args.flash_timeout,
        )
        candidate_flash_ok = True

        version = base.run_serial_step(out_dir, steps, "candidate-version", ["version"], timeout=90.0, retry_unsafe=True)
        version_text = text_of(version)
        result["candidate_version_ok"] = CANDIDATE_VERSION in version_text and CANDIDATE_TAG in version_text
        if not result["candidate_version_ok"]:
            raise RuntimeError("candidate version output did not contain expected version/tag")
        base.run_serial_step(out_dir, steps, "candidate-status", ["status"], timeout=90.0, retry_unsafe=True)
        candidate_selftest, selftest_markers = run_serial_marker_step(
            out_dir,
            steps,
            "candidate-selftest-verbose",
            ["selftest", "verbose"],
            timeout=120.0,
            markers=REQUIRED_SELFTEST_MARKERS,
            pass_check=base.selftest_step_ok,
        )
        result["candidate_selftest_fail0"] = bool(selftest_markers.get("pass_check_ok"))
        result["selftest_markers"] = selftest_markers
        if not result["candidate_selftest_fail0"]:
            raise RuntimeError("candidate selftest did not report fail=0")

        audio_status, audio_status_markers = run_serial_marker_step(
            out_dir,
            steps,
            "candidate-audio-status",
            ["audio", "status"],
            timeout=150.0,
            markers=REQUIRED_AUDIO_STATUS_MARKERS,
        )
        result["audio_status_markers"] = audio_status_markers
        if SCREENAPP_COMMAND is not None:
            base.run_serial_step(
                out_dir,
                steps,
                "candidate-screenapp-prehide",
                ["hide"],
                timeout=30.0,
                retry_unsafe=True,
                allow_error=True,
            )
            time.sleep(1.0)
            screenapp_status, screenapp_markers = run_serial_marker_step(
                out_dir,
                steps,
                "candidate-screenapp-status",
                list(SCREENAPP_COMMAND),
                timeout=120.0,
                markers=REQUIRED_SCREENAPP_MARKERS,
            )
            result["screenapp_markers"] = screenapp_markers
        else:
            result["screenapp_markers"] = {
                "ok": True,
                "missing": [],
                "count": 0,
                "required": 0,
            }
        extra_markers: dict[str, Any] = {}
        for extra in EXTRA_MARKER_STEPS:
            extra_name = str(extra["name"])
            _extra_step, marker_state = run_serial_marker_step(
                out_dir,
                steps,
                extra_name,
                [str(part) for part in extra["command"]],
                [str(marker) for marker in extra["markers"]],
                timeout=float(extra.get("timeout", 120.0)),
            )
            extra_markers[extra_name] = marker_state
        result["extra_markers"] = extra_markers

        if (
            result["audio_status_markers"].get("ok")
            and result["selftest_markers"].get("ok")
            and result["screenapp_markers"].get("ok")
            and all(marker_state.get("ok") for marker_state in result["extra_markers"].values())
        ):
            result["decision"] = f"{decision_prefix()}-audio-status-selftest-device-pass"
        else:
            result["decision"] = f"{decision_prefix()}-audio-status-selftest-marker-missing-before-rollback"
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
                result["rollback_version_ok"] = ROLLBACK_VERSION in text_of(rollback_version)
                result["rollback_selftest_fail0"] = base.selftest_step_ok(rollback_selftest)
        write_json(out_dir / "result.json", result)
        REPORT_PATH.write_text(render_report(result), encoding="utf-8")
    return result


def dry_run(state: dict[str, Any]) -> dict[str, Any]:
    candidate_sha = str(state["candidate"].get("sha256") or "")
    return {
        "decision": f"{decision_prefix()}-audio-status-selftest-live-dry-run",
        "preflight_ok": preflight_ok(state),
        "preflight": state,
        "commands": {
            "verify_current": base.flash_command(ROLLBACK_IMAGE, ROLLBACK_VERSION, ROLLBACK_SHA256, from_native=False) + ["--verify-only"],
            "flash_candidate": base.flash_command(CANDIDATE_IMAGE, CANDIDATE_VERSION, candidate_sha, from_native=True),
            "checks": [
                ["version"],
                ["status"],
                ["selftest", "verbose"],
                ["audio", "status"],
                *([["hide"]] if SCREENAPP_COMMAND is not None else []),
                *(list(SCREENAPP_COMMAND) for _ in [0] if SCREENAPP_COMMAND is not None),
                *([list(extra["command"]) for extra in EXTRA_MARKER_STEPS]),
            ],
            "rollback": base.flash_command(ROLLBACK_IMAGE, ROLLBACK_VERSION, ROLLBACK_SHA256, from_native=True),
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="perform flash + read-only validation + rollback")
    parser.add_argument("--flash-timeout", type=float, default=900.0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    state = preflight_state()
    if not args.live:
        print(json.dumps(dry_run(state), ensure_ascii=False, indent=2, sort_keys=True))
        return 0 if preflight_ok(state) else 1
    result = live_run(args, state)
    print(json.dumps({
        "decision": result.get("decision"),
        "out_dir": result.get("out_dir"),
        "rollback_version_ok": result.get("rollback_version_ok"),
        "rollback_selftest_fail0": result.get("rollback_selftest_fail0"),
    }, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if (
        result.get("decision") == f"{decision_prefix()}-audio-status-selftest-device-pass"
        and result.get("rollback_version_ok")
        and result.get("rollback_selftest_fail0")
    ) else 1


if __name__ == "__main__":
    raise SystemExit(main())
