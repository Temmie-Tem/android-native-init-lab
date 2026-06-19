#!/usr/bin/env python3
"""V2860 live validation for V2859 latest audio changelog/status markers."""

from __future__ import annotations

import native_audio_status_selftest_live_handoff_v2819 as runner

CYCLE = "V2860"
BUILD_MANIFEST = runner.ROOT / "workspace/private/builds/native-init/v2859-audio-changelog-latest-refresh/manifest.json"
CANDIDATE_IMAGE = runner.ROOT / "workspace/private/inputs/boot_images/boot_linux_v2859_audio_changelog_latest_refresh.img"
CANDIDATE_VERSION = "0.10.19"
CANDIDATE_TAG = "v2859-audio-changelog-latest-refresh"
REPORT_PATH = runner.ROOT / "docs/reports/NATIVE_INIT_V2860_AUDIO_CHANGELOG_LATEST_REFRESH_LIVE_2026-06-19.md"
SCREENAPP_COMMAND = ["screenapp", "about-changelog"]
REQUIRED_PRODUCTIZATION_AUDIO_STATUS_MARKERS = [
    "audio.status.productization.version=1",
    "audio.status.productization.latest_run=V2860",
    "audio.status.productization.latest_version=0.10.19",
    "audio.status.productization.latest_tag=v2859-audio-changelog-latest-refresh",
    "audio.status.feature.chime=1",
    "audio.status.feature.chime.validation_run=V2855",
    "audio.status.feature.boot_chime=1",
    "audio.status.feature.boot_chime.enabled=1",
    "audio.status.feature.boot_chime.best_effort=1",
    "audio.status.feature.boot_chime.blocks_boot=0",
    "audio.status.feature.boot_chime.validation_run=V2846",
    "audio.status.feature.stop_execute=1",
    "audio.status.feature.stop_execute.scope=core-route-reset",
    "audio.status.feature.stop_execute.validation_run=V2856",
    "audio.status.feature.changelog=1",
    "audio.status.feature.changelog.validation_run=V2860",
    "audio.status.feature.changelog.screenapp_count=2",
]
REQUIRED_AUDIO_STATUS_MARKERS = [
    *runner.REQUIRED_AUDIO_STATUS_MARKERS,
    *REQUIRED_PRODUCTIZATION_AUDIO_STATUS_MARKERS,
]
REQUIRED_SCREENAPP_MARKERS = [
    "screenapp.app=about-changelog",
    "screenapp.safety=display-only-explicit",
    "screenapp.title=ABOUT / CHANGELOG",
    "screenapp.valid=1",
    "screenapp.rc=0",
    "screenapp.presented=1",
]
EXTRA_MARKER_STEPS = [
    {
        "name": "candidate-screenapp-audio-status",
        "command": ["screenapp", "audio-status"],
        "markers": [
            "screenapp.app=audio-status",
            "screenapp.safety=display-only-explicit",
            "screenapp.title=AUDIO STATUS",
            "screenapp.valid=1",
            "screenapp.rc=0",
            "screenapp.presented=1",
        ],
        "timeout": 120.0,
    },
]


def render_report(result: dict[str, object]) -> str:
    audio = result.get("audio_status_markers", {}) if isinstance(result.get("audio_status_markers"), dict) else {}
    selftest = result.get("selftest_markers", {}) if isinstance(result.get("selftest_markers"), dict) else {}
    screenapp = result.get("screenapp_markers", {}) if isinstance(result.get("screenapp_markers"), dict) else {}
    extra = result.get("extra_markers", {}) if isinstance(result.get("extra_markers"), dict) else {}
    audio_status_screen = extra.get("candidate-screenapp-audio-status", {}) if isinstance(extra.get("candidate-screenapp-audio-status"), dict) else {}
    return "\n".join([
        "# Native Init V2860 Audio Changelog Latest Refresh Live Validation",
        "",
        "## Summary",
        "",
        "- Cycle: `V2860`",
        "- Track: post-promotion audio Tier C changelog/productization observability.",
        f"- Decision: `{result.get('decision')}`",
        f"- Result directory: `{result.get('out_dir')}`",
        f"- Candidate image: `{runner.rel(CANDIDATE_IMAGE)}`",
        f"- Candidate SHA256: `{result.get('candidate_sha256')}`",
        f"- Candidate version/tag expected: `{CANDIDATE_VERSION}` / `{CANDIDATE_TAG}`",
        f"- Candidate version/tag observed OK: `{int(bool(result.get('candidate_version_ok')))}`",
        f"- `audio status` marker pass: `{int(bool(audio.get('ok')))}` ({audio.get('count', 0)}/{audio.get('required', 0)})",
        f"- `selftest verbose` audio marker pass: `{int(bool(selftest.get('ok')))}` ({selftest.get('count', 0)}/{selftest.get('required', 0)})",
        f"- `screenapp about-changelog` marker pass: `{int(bool(screenapp.get('ok')))}` ({screenapp.get('count', 0)}/{screenapp.get('required', 0)})",
        f"- `screenapp audio-status` marker pass: `{int(bool(audio_status_screen.get('ok')))}` ({audio_status_screen.get('count', 0)}/{audio_status_screen.get('required', 0)})",
        f"- Rollback attempted: `{int(bool(result.get('rollback_attempted')))}`",
        f"- Rollback recovery fallback used: `{int(bool(result.get('rollback_recovery_fallback_used')))}`",
        f"- Rollback health: version_ok=`{int(bool(result.get('rollback_version_ok')))}` selftest_fail0=`{int(bool(result.get('rollback_selftest_fail0')))}`",
        "",
        "## Finding",
        "",
        "- V2860 flashes the V2859 `0.10.19` changelog/latest-marker candidate and validates the ABOUT changelog screen route on hardware.",
        "- The unit revalidates `audio status` productization markers now pointing at the V2860 changelog refresh contract and the static `selftest verbose` audio row.",
        "- This validation intentionally performs no ADSP boot, `/dev/snd` materialization, route apply/reset, ACDB SET, PCM open, mixer write, speaker write, playback, chime, or stop-execute command.",
        "",
        "## Missing Markers",
        "",
        f"- `audio status`: `{audio.get('missing', [])}`",
        f"- `selftest verbose`: `{selftest.get('missing', [])}`",
        f"- `screenapp about-changelog`: `{screenapp.get('missing', [])}`",
        f"- `screenapp audio-status`: `{audio_status_screen.get('missing', [])}`",
        "",
        "## Safety",
        "",
        "- Flash path: `workspace/public/src/scripts/revalidation/native_init_flash.py`.",
        "- Only the boot partition is written.",
        "- No forbidden partitions are touched.",
        "- Public report contains metadata only; full serial transcripts stay under `workspace/private/runs/audio/`.",
        "",
    ])


def configure_runner() -> None:
    runner.CYCLE = CYCLE
    runner.BUILD_MANIFEST = BUILD_MANIFEST
    runner.CANDIDATE_IMAGE = CANDIDATE_IMAGE
    runner.CANDIDATE_VERSION = CANDIDATE_VERSION
    runner.CANDIDATE_TAG = CANDIDATE_TAG
    runner.REPORT_PATH = REPORT_PATH
    runner.SCREENAPP_COMMAND = list(SCREENAPP_COMMAND)
    runner.REQUIRED_AUDIO_STATUS_MARKERS = list(REQUIRED_AUDIO_STATUS_MARKERS)
    runner.REQUIRED_SCREENAPP_MARKERS = list(REQUIRED_SCREENAPP_MARKERS)
    runner.EXTRA_MARKER_STEPS = [dict(step) for step in EXTRA_MARKER_STEPS]
    runner.render_report = render_report


def main() -> int:
    configure_runner()
    return runner.main()


if __name__ == "__main__":
    raise SystemExit(main())
