#!/usr/bin/env python3
"""V2836 live validation for the V2835 audio help surface image."""

from __future__ import annotations

import native_audio_status_selftest_live_handoff_v2819 as runner

CYCLE = "V2836"
BUILD_MANIFEST = runner.ROOT / "workspace/private/builds/native-init/v2835-audio-help-surface/manifest.json"
CANDIDATE_IMAGE = runner.ROOT / "workspace/private/inputs/boot_images/boot_linux_v2835_audio_help_surface.img"
CANDIDATE_VERSION = "0.10.9"
CANDIDATE_TAG = "v2835-audio-help-surface"
REPORT_PATH = runner.ROOT / "docs/reports/NATIVE_INIT_V2836_AUDIO_HELP_SURFACE_LIVE_2026-06-19.md"
HELP_USAGE = "audio [status|profiles|profile|speaker-map|stages|prereq|app-type|setcal|route|play|play-status|stop|adsp-status|snd-status]"
EXTRA_MARKER_STEPS = [
    {
        "name": "candidate-help",
        "command": ["help"],
        "markers": [HELP_USAGE],
        "timeout": 120.0,
    },
    {
        "name": "candidate-cmdmeta-verbose",
        "command": ["cmdmeta", "verbose"],
        "markers": [
            "name=audio group=android",
            f"usage={HELP_USAGE}",
        ],
        "timeout": 120.0,
    },
]


def render_report(result: dict[str, object]) -> str:
    audio = result.get("audio_status_markers", {}) if isinstance(result.get("audio_status_markers"), dict) else {}
    selftest = result.get("selftest_markers", {}) if isinstance(result.get("selftest_markers"), dict) else {}
    extra = result.get("extra_markers", {}) if isinstance(result.get("extra_markers"), dict) else {}
    help_markers = extra.get("candidate-help", {}) if isinstance(extra.get("candidate-help"), dict) else {}
    cmdmeta_markers = extra.get("candidate-cmdmeta-verbose", {}) if isinstance(extra.get("candidate-cmdmeta-verbose"), dict) else {}
    return "\n".join([
        "# Native Init V2836 Audio Help Surface Live Validation",
        "",
        "## Summary",
        "",
        "- Cycle: `V2836`",
        "- Track: post-promotion audio Tier C help/discoverability observability.",
        f"- Decision: `{result.get('decision')}`",
        f"- Result directory: `{result.get('out_dir')}`",
        f"- Candidate image: `{runner.rel(CANDIDATE_IMAGE)}`",
        f"- Candidate SHA256: `{result.get('candidate_sha256')}`",
        f"- Candidate version/tag expected: `{CANDIDATE_VERSION}` / `{CANDIDATE_TAG}`",
        f"- Candidate version/tag observed OK: `{int(bool(result.get('candidate_version_ok')))}`",
        f"- `audio status` marker pass: `{int(bool(audio.get('ok')))}` ({audio.get('count', 0)}/{audio.get('required', 0)})",
        f"- `selftest verbose` audio marker pass: `{int(bool(selftest.get('ok')))}` ({selftest.get('count', 0)}/{selftest.get('required', 0)})",
        f"- `help` audio usage marker pass: `{int(bool(help_markers.get('ok')))}` ({help_markers.get('count', 0)}/{help_markers.get('required', 0)})",
        f"- `cmdmeta verbose` audio usage marker pass: `{int(bool(cmdmeta_markers.get('ok')))}` ({cmdmeta_markers.get('count', 0)}/{cmdmeta_markers.get('required', 0)})",
        f"- Rollback attempted: `{int(bool(result.get('rollback_attempted')))}`",
        f"- Rollback recovery fallback used: `{int(bool(result.get('rollback_recovery_fallback_used')))}`",
        f"- Rollback health: version_ok=`{int(bool(result.get('rollback_version_ok')))}` selftest_fail0=`{int(bool(result.get('rollback_selftest_fail0')))}`",
        "",
        "## Finding",
        "",
        "- V2836 flashes the V2835 `0.10.9` help-surface candidate and validates that the image boots, preserves `audio status` and `selftest verbose` markers, and exposes the current audio subcommands in both `help` and `cmdmeta verbose`.",
        "- The validation is read-only: it performs no ADSP boot, `/dev/snd` materialization, route apply/reset, ACDB SET, PCM open, mixer write, speaker write, or playback.",
        "",
        "## Missing Markers",
        "",
        f"- `audio status`: `{audio.get('missing', [])}`",
        f"- `selftest verbose`: `{selftest.get('missing', [])}`",
        f"- `help`: `{help_markers.get('missing', [])}`",
        f"- `cmdmeta verbose`: `{cmdmeta_markers.get('missing', [])}`",
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
    runner.SCREENAPP_COMMAND = None
    runner.REQUIRED_SCREENAPP_MARKERS = []
    runner.EXTRA_MARKER_STEPS = [dict(step) for step in EXTRA_MARKER_STEPS]
    runner.render_report = render_report


def main() -> int:
    configure_runner()
    return runner.main()


if __name__ == "__main__":
    raise SystemExit(main())
