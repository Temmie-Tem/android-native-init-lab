#!/usr/bin/env python3
"""V2852 live validation for V2851 audio changelog productization markers."""

from __future__ import annotations

import native_audio_status_productization_live_handoff_v2850 as v2850
import native_audio_status_selftest_live_handoff_v2819 as runner

CYCLE = "V2852"
BUILD_MANIFEST = runner.ROOT / "workspace/private/builds/native-init/v2851-audio-changelog-productization/manifest.json"
CANDIDATE_IMAGE = runner.ROOT / "workspace/private/inputs/boot_images/boot_linux_v2851_audio_changelog_productization.img"
CANDIDATE_VERSION = "0.10.16"
CANDIDATE_TAG = "v2851-audio-changelog-productization"
REPORT_PATH = runner.ROOT / "docs/reports/NATIVE_INIT_V2852_AUDIO_CHANGELOG_PRODUCTIZATION_LIVE_2026-06-19.md"
SCREENAPP_COMMAND = ["screenapp", "about-changelog"]
REQUIRED_AUDIO_STATUS_MARKERS = list(v2850.REQUIRED_AUDIO_STATUS_MARKERS)
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
        "name": "candidate-screenapp-about-version",
        "command": ["screenapp", "about-version"],
        "markers": [
            "screenapp.app=about-version",
            "screenapp.safety=display-only-explicit",
            "screenapp.title=ABOUT / VERSION",
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
    about_version = extra.get("candidate-screenapp-about-version", {}) if isinstance(extra.get("candidate-screenapp-about-version"), dict) else {}
    return "\n".join([
        "# Native Init V2852 Audio Changelog Productization Live Validation",
        "",
        "## Summary",
        "",
        "- Cycle: `V2852`",
        "- Track: post-promotion audio Tier C changelog/about observability.",
        f"- Decision: `{result.get('decision')}`",
        f"- Result directory: `{result.get('out_dir')}`",
        f"- Candidate image: `{runner.rel(CANDIDATE_IMAGE)}`",
        f"- Candidate SHA256: `{result.get('candidate_sha256')}`",
        f"- Candidate version/tag expected: `{CANDIDATE_VERSION}` / `{CANDIDATE_TAG}`",
        f"- Candidate version/tag observed OK: `{int(bool(result.get('candidate_version_ok')))}`",
        f"- `audio status` marker pass: `{int(bool(audio.get('ok')))}` ({audio.get('count', 0)}/{audio.get('required', 0)})",
        f"- `selftest verbose` audio marker pass: `{int(bool(selftest.get('ok')))}` ({selftest.get('count', 0)}/{selftest.get('required', 0)})",
        f"- `screenapp about-changelog` marker pass: `{int(bool(screenapp.get('ok')))}` ({screenapp.get('count', 0)}/{screenapp.get('required', 0)})",
        f"- `screenapp about-version` marker pass: `{int(bool(about_version.get('ok')))}` ({about_version.get('count', 0)}/{about_version.get('required', 0)})",
        f"- Rollback attempted: `{int(bool(result.get('rollback_attempted')))}`",
        f"- Rollback recovery fallback used: `{int(bool(result.get('rollback_recovery_fallback_used')))}`",
        f"- Rollback health: version_ok=`{int(bool(result.get('rollback_version_ok')))}` selftest_fail0=`{int(bool(result.get('rollback_selftest_fail0')))}`",
        "",
        "## Finding",
        "",
        "- V2852 flashes the V2851 `0.10.16` changelog-productization candidate and validates the direct ABOUT screenapp dispatch on hardware.",
        "- The unit revalidates unchanged `audio status` productization markers and the static `selftest verbose` audio row while proving `screenapp about-changelog` and `screenapp about-version` present display-only pages.",
        "- This validation intentionally performs no ADSP boot, `/dev/snd` materialization, route apply/reset, ACDB SET, PCM open, mixer write, speaker write, playback, chime, or stop-execute command.",
        "",
        "## Missing Markers",
        "",
        f"- `audio status`: `{audio.get('missing', [])}`",
        f"- `selftest verbose`: `{selftest.get('missing', [])}`",
        f"- `screenapp about-changelog`: `{screenapp.get('missing', [])}`",
        f"- `screenapp about-version`: `{about_version.get('missing', [])}`",
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
