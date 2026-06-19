#!/usr/bin/env python3
"""V2861 live validation for the V2859 latest read-only audio/about screen matrix."""

from __future__ import annotations

import native_audio_changelog_latest_refresh_live_handoff_v2860 as v2860
import native_audio_status_selftest_live_handoff_v2819 as runner

CYCLE = "V2861"
BUILD_MANIFEST = v2860.BUILD_MANIFEST
CANDIDATE_IMAGE = v2860.CANDIDATE_IMAGE
CANDIDATE_VERSION = v2860.CANDIDATE_VERSION
CANDIDATE_TAG = v2860.CANDIDATE_TAG
REPORT_PATH = runner.ROOT / "docs/reports/NATIVE_INIT_V2861_AUDIO_SCREEN_MATRIX_LATEST_LIVE_2026-06-19.md"
SCREENAPP_COMMAND = ["screenapp", "about-version"]
REQUIRED_AUDIO_STATUS_MARKERS = list(v2860.REQUIRED_AUDIO_STATUS_MARKERS)


def screen_markers(app: str, title: str) -> list[str]:
    return [
        f"screenapp.app={app}",
        "screenapp.safety=display-only-explicit",
        f"screenapp.title={title}",
        "screenapp.valid=1",
        "screenapp.rc=0",
        "screenapp.presented=1",
    ]


REQUIRED_SCREENAPP_MARKERS = screen_markers("about-version", "ABOUT / VERSION")
EXTRA_MARKER_STEPS = [
    {
        "name": "candidate-screenapp-about-changelog",
        "command": ["screenapp", "about-changelog"],
        "markers": screen_markers("about-changelog", "ABOUT / CHANGELOG"),
        "timeout": 120.0,
    },
    {
        "name": "candidate-screenapp-audio-status",
        "command": ["screenapp", "audio-status"],
        "markers": screen_markers("audio-status", "AUDIO STATUS"),
        "timeout": 120.0,
    },
    {
        "name": "candidate-screenapp-audio-profile",
        "command": ["screenapp", "audio-profile"],
        "markers": screen_markers("audio-profile", "AUDIO PROFILE"),
        "timeout": 120.0,
    },
    {
        "name": "candidate-screenapp-audio-stages",
        "command": ["screenapp", "audio-stages"],
        "markers": screen_markers("audio-stages", "AUDIO STAGES"),
        "timeout": 120.0,
    },
    {
        "name": "candidate-screenapp-audio-map",
        "command": ["screenapp", "audio-map"],
        "markers": screen_markers("audio-map", "AUDIO ROUTE MAP"),
        "timeout": 120.0,
    },
    {
        "name": "candidate-screenapp-audio-chime",
        "command": ["screenapp", "audio-chime"],
        "markers": screen_markers("audio-chime", "AUDIO CHIME"),
        "timeout": 120.0,
    },
]


def render_report(result: dict[str, object]) -> str:
    audio = result.get("audio_status_markers", {}) if isinstance(result.get("audio_status_markers"), dict) else {}
    selftest = result.get("selftest_markers", {}) if isinstance(result.get("selftest_markers"), dict) else {}
    screenapp = result.get("screenapp_markers", {}) if isinstance(result.get("screenapp_markers"), dict) else {}
    extra = result.get("extra_markers", {}) if isinstance(result.get("extra_markers"), dict) else {}
    matrix_rows = []
    for name in [step["name"] for step in EXTRA_MARKER_STEPS]:
        marker_state = extra.get(name, {}) if isinstance(extra.get(name), dict) else {}
        matrix_rows.append(
            f"- `{name}` marker pass: `{int(bool(marker_state.get('ok')))}` "
            f"({marker_state.get('count', 0)}/{marker_state.get('required', 0)})"
        )
    missing_rows = []
    for name in [step["name"] for step in EXTRA_MARKER_STEPS]:
        marker_state = extra.get(name, {}) if isinstance(extra.get(name), dict) else {}
        missing_rows.append(f"- `{name}`: `{marker_state.get('missing', [])}`")
    return "\n".join([
        "# Native Init V2861 Audio Screen Matrix Latest Live Validation",
        "",
        "## Summary",
        "",
        "- Cycle: `V2861`",
        "- Track: post-promotion audio Tier C display/read-only screen matrix.",
        f"- Decision: `{result.get('decision')}`",
        f"- Result directory: `{result.get('out_dir')}`",
        f"- Candidate image: `{runner.rel(CANDIDATE_IMAGE)}`",
        f"- Candidate SHA256: `{result.get('candidate_sha256')}`",
        f"- Candidate version/tag expected: `{CANDIDATE_VERSION}` / `{CANDIDATE_TAG}`",
        f"- Candidate version/tag observed OK: `{int(bool(result.get('candidate_version_ok')))}`",
        f"- `audio status` marker pass: `{int(bool(audio.get('ok')))}` ({audio.get('count', 0)}/{audio.get('required', 0)})",
        f"- `selftest verbose` audio marker pass: `{int(bool(selftest.get('ok')))}` ({selftest.get('count', 0)}/{selftest.get('required', 0)})",
        f"- `screenapp about-version` marker pass: `{int(bool(screenapp.get('ok')))}` ({screenapp.get('count', 0)}/{screenapp.get('required', 0)})",
        *matrix_rows,
        f"- Rollback attempted: `{int(bool(result.get('rollback_attempted')))}`",
        f"- Rollback recovery fallback used: `{int(bool(result.get('rollback_recovery_fallback_used')))}`",
        f"- Rollback health: version_ok=`{int(bool(result.get('rollback_version_ok')))}` selftest_fail0=`{int(bool(result.get('rollback_selftest_fail0')))}`",
        "",
        "## Finding",
        "",
        "- V2861 flashes the V2859 `0.10.19` candidate and validates the latest ABOUT/audio screen matrix on hardware.",
        "- The unit covers `about-version`, `about-changelog`, `audio-status`, `audio-profile`, `audio-stages`, `audio-map`, and `audio-chime` through display-only `screenapp` routes.",
        "- This validation intentionally performs no ADSP boot, `/dev/snd` materialization, route apply/reset, ACDB SET, PCM open, mixer write, speaker write, playback, chime, or stop-execute command.",
        "",
        "## Missing Markers",
        "",
        f"- `audio status`: `{audio.get('missing', [])}`",
        f"- `selftest verbose`: `{selftest.get('missing', [])}`",
        f"- `screenapp about-version`: `{screenapp.get('missing', [])}`",
        *missing_rows,
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
