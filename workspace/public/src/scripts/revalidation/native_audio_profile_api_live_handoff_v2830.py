#!/usr/bin/env python3
"""V2830 live validation for the latest audio profile API surfaces.

This flashes the V2828 0.10.6 image, validates read-only native `audio`
profile/stage/speaker-map command surfaces, then rolls back to V2321.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from _workspace_bootstrap import repo_root
import native_audio_speaker_descriptor_api_device_validation_handoff_v2788 as base

ROOT = repo_root()
CYCLE = "V2830"
PROFILE = "internal-speaker-safe"
CANDIDATE_VERSION = "0.10.6"
CANDIDATE_TAG = "v2828-audio-route-map-safety"
BUILD_MANIFEST = ROOT / "workspace/private/builds/native-init/v2828-audio-route-map-safety/manifest.json"
CANDIDATE_IMAGE = ROOT / "workspace/private/inputs/boot_images/boot_linux_v2828_audio_route_map_safety.img"
REPORT_PATH = ROOT / "docs/reports/NATIVE_INIT_V2830_AUDIO_PROFILE_API_LIVE_2026-06-19.md"

ROLLBACK_IMAGE = base.ROLLBACK_IMAGE
ROLLBACK_VERSION = base.ROLLBACK_VERSION
ROLLBACK_SHA256 = base.ROLLBACK_SHA256

PROFILE_MARKERS = [
    "audio.profile.version=1",
    f"audio.profile.id={PROFILE}",
    "audio.profile.endpoint=internal-speaker",
    "audio.profile.speaker_map=SpkrLeft/SpkrRight WSA881x via WSA_CDC_DMA_RX",
    "audio.profile.card=0",
    "audio.profile.pcm_device=0",
    "audio.profile.channels=2",
    "audio.profile.sample_rate=48000",
    "audio.profile.bit_width=16",
    "audio.profile.app_type=69941",
    "audio.profile.acdb_id=15",
    "audio.profile.stream_control_width=2",
    "audio.profile.global_app_type_config=1 69941 48000 16",
    "audio.profile.stream_app_type_config=69941 15 48000 2",
    "audio.profile.acdb_set_order=39,20,20,13,9,11,12,15,23,16,21",
    "audio.profile.forbidden_cal_types=10,14,24",
    "audio.profile.probe_defaults.amplitude_milli=20 duration_ms=1000",
    "audio.profile.listen_defaults.amplitude_milli=150 duration_ms=8000",
    "audio.profile.safety.amplitude_cap_milli=200 duration_cap_ms=10000",
    "audio.profile.safety.no_smart_amp_gain_boost_changes=1",
    "audio.profile.read_only=1",
]

PROFILES_MARKERS = [
    "audio.profiles.version=1",
    "audio.profiles.count=1",
    f"audio.profiles.default={PROFILE}",
    f"audio.profiles.0.id={PROFILE} endpoint=internal-speaker card=0 pcm=0",
]

STAGES_MARKERS = [
    "audio.stages.version=1",
    f"audio.stages.profile={PROFILE}",
    "audio.stages.endpoint=internal-speaker",
    "audio.stages.count=14",
    "audio.stages.native_implemented.count=12",
    "audio.stages.runtime_write.count=8",
    "audio.stages.all_native_ready=0",
    "audio.stages.read_only=1",
    "audio.stages.3.id=write-global-app-type-config",
    f"audio.stages.3.command=audio app-type {PROFILE} --write",
    "audio.stages.7.id=replay-acdb-setcal-sequence",
    f"audio.stages.7.command=audio setcal {PROFILE} --manifest /cache/a90-runtime/pkg/manifests/audio-setcal-internal-speaker-safe.manifest --execute",
    "audio.stages.8.id=apply-core-speaker-route",
    f"audio.stages.8.command=audio route {PROFILE} --apply --layer core",
    "audio.stages.10.id=bounded-pcm-playback",
    f"audio.stages.10.command=audio play {PROFILE} --mode probe --execute",
    "audio.stages.13.id=rollback-v2321",
]

SPEAKER_MAP_MARKERS = [
    "audio.speaker_map.version=1",
    f"audio.speaker_map.profile={PROFILE}",
    "audio.speaker_map.read_only=1",
    "audio.speaker_map.route_write_attempted=0",
    "audio.speaker_map.playback_attempted=0",
    "audio.speaker_map.endpoint=internal-speaker",
    "audio.speaker_map.route_path=SLIMBUS_0_RX_to_WSA_CDC_DMA_RX",
    "audio.speaker_map.route_control.count=13",
    "audio.speaker_map.observer_control.count=8",
    "audio.speaker_map.speaker.count=6",
    "audio.speaker_map.safety.amplitude_cap_milli=200",
    "audio.speaker_map.safety.smart_amp_boost_write_allowed=0",
    "audio.speaker_map.safety.smart_amp_boost_blocked=1",
    "audio.speaker_map.speaker.1.id=SPKR_VI_1",
    "audio.speaker_map.speaker.2.id=SPKR_VI_2",
    "audio.speaker_map.speaker.4.id=SpkrLeft",
    "audio.speaker_map.speaker.4.safety=boost-write-blocked",
    "audio.speaker_map.speaker.5.id=SpkrRight",
    "audio.speaker_map.speaker.5.safety=boost-write-blocked",
]


def rel(path: Path) -> str:
    return base.rel(path)


def now_slug() -> str:
    return datetime.now(timezone.utc).astimezone().strftime("%Y%m%d-%H%M%S")


def decision_prefix() -> str:
    return CYCLE.lower()


def read_json(path: Path) -> dict[str, Any]:
    return base.read_json(path)


def write_json(path: Path, payload: Any) -> None:
    base.write_json(path, payload)


def text_of(step: dict[str, Any]) -> str:
    return base.stdout_of(step)


def markers_present(text: str, markers: list[str]) -> dict[str, Any]:
    missing = [marker for marker in markers if marker not in text]
    return {
        "ok": not missing,
        "missing": missing,
        "count": len(markers) - len(missing),
        "required": len(markers),
    }


def preflight_state() -> dict[str, Any]:
    manifest = read_json(BUILD_MANIFEST)
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
            "run read-only audio profiles/profile/stages/speaker-map commands",
            "do not run ADSP boot, /dev/snd materialization, route apply/reset, ACDB SET, PCM open, mixer write, speaker write, or playback",
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


def command_marker_sets() -> dict[str, list[str]]:
    return {
        "audio-profiles": PROFILES_MARKERS,
        "audio-profile": PROFILE_MARKERS,
        "audio-stages": STAGES_MARKERS,
        "audio-speaker-map": SPEAKER_MAP_MARKERS,
    }


def render_report(result: dict[str, Any]) -> str:
    checks = result.get("command_markers", {})
    check_lines = []
    for name in ["audio-profiles", "audio-profile", "audio-stages", "audio-speaker-map"]:
        marker = checks.get(name, {}) if isinstance(checks, dict) else {}
        check_lines.append(
            f"- `{name}` marker pass: `{int(bool(marker.get('ok')))}"
            f"` ({marker.get('count', 0)}/{marker.get('required', 0)})"
        )
    missing_lines = []
    for name in ["audio-profiles", "audio-profile", "audio-stages", "audio-speaker-map"]:
        marker = checks.get(name, {}) if isinstance(checks, dict) else {}
        missing_lines.append(f"- `{name}`: `{marker.get('missing', [])}`")

    return "\n".join([
        "# Native Init V2830 Audio Profile API Live Validation",
        "",
        "## Summary",
        "",
        f"- Cycle: `{CYCLE}`",
        "- Track: post-promotion audio Tier C read-only command API validation.",
        f"- Decision: `{result.get('decision')}`",
        f"- Result directory: `{result.get('out_dir')}`",
        f"- Candidate image: `{rel(CANDIDATE_IMAGE)}`",
        f"- Candidate SHA256: `{result.get('candidate_sha256')}`",
        f"- Candidate version/tag observed: `{int(bool(result.get('candidate_version_ok')))}`",
        *check_lines,
        f"- Rollback attempted: `{int(bool(result.get('rollback_attempted')))}`",
        f"- Rollback recovery fallback used: `{int(bool(result.get('rollback_recovery_fallback_used')))}`",
        f"- Rollback health: version_ok=`{int(bool(result.get('rollback_version_ok')))}` selftest_fail0=`{int(bool(result.get('rollback_selftest_fail0')))}`",
        "",
        "## Finding",
        "",
        "- V2830 flashes the latest `0.10.6` audio observability candidate and validates the read-only profile API on hardware.",
        "- The run proves the callable native API surfaces expose the canonical internal-speaker profile, stage contract, and per-speaker route map without issuing audio runtime writes.",
        "- This validation intentionally performs no ADSP boot, `/dev/snd` materialization, route apply/reset, ACDB SET, PCM open, mixer write, speaker write, or playback.",
        "",
        "## Missing Markers",
        "",
        *missing_lines,
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
    out_dir = ROOT / f"workspace/private/runs/audio/{decision_prefix()}-audio-profile-api-live-{now_slug()}"
    out_dir.mkdir(parents=True, exist_ok=False)
    write_json(out_dir / "preflight.json", state)
    steps: list[dict[str, Any]] = []
    result: dict[str, Any] = {
        "decision": f"{decision_prefix()}-audio-profile-api-live-started",
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
            "flash-v2828-candidate",
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
        candidate_selftest = base.run_serial_step(
            out_dir,
            steps,
            "candidate-selftest-verbose",
            ["selftest", "verbose"],
            timeout=120.0,
            retry_unsafe=True,
        )
        result["candidate_selftest_fail0"] = base.selftest_step_ok(candidate_selftest)
        if not result["candidate_selftest_fail0"]:
            raise RuntimeError("candidate selftest did not report fail=0")

        command_specs = [
            ("audio-profiles", ["audio", "profiles"]),
            ("audio-profile", ["audio", "profile", PROFILE]),
            ("audio-stages", ["audio", "stages", PROFILE]),
            ("audio-speaker-map", ["audio", "speaker-map", PROFILE]),
        ]
        command_markers: dict[str, Any] = {}
        for name, command in command_specs:
            step = base.run_serial_step(
                out_dir,
                steps,
                f"candidate-{name}",
                command,
                timeout=150.0,
                retry_unsafe=True,
            )
            command_markers[name] = markers_present(text_of(step), command_marker_sets()[name])
        result["command_markers"] = command_markers
        if all(marker.get("ok") for marker in command_markers.values()):
            result["decision"] = f"{decision_prefix()}-audio-profile-api-device-pass"
        else:
            result["decision"] = f"{decision_prefix()}-audio-profile-api-marker-missing-before-rollback"
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
        "decision": f"{decision_prefix()}-audio-profile-api-live-dry-run",
        "preflight_ok": preflight_ok(state),
        "preflight": state,
        "commands": {
            "verify_current": base.flash_command(ROLLBACK_IMAGE, ROLLBACK_VERSION, ROLLBACK_SHA256, from_native=False) + ["--verify-only"],
            "flash_candidate": base.flash_command(CANDIDATE_IMAGE, CANDIDATE_VERSION, candidate_sha, from_native=True),
            "checks": [
                ["version"],
                ["status"],
                ["selftest", "verbose"],
                ["audio", "profiles"],
                ["audio", "profile", PROFILE],
                ["audio", "stages", PROFILE],
                ["audio", "speaker-map", PROFILE],
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
        result.get("decision") == f"{decision_prefix()}-audio-profile-api-device-pass"
        and result.get("rollback_version_ok")
        and result.get("rollback_selftest_fail0")
    ) else 1


if __name__ == "__main__":
    raise SystemExit(main())
