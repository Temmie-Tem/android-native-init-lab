#!/usr/bin/env python3
"""V2827 live validation for the V2826 audio menu screen image."""

from __future__ import annotations

import native_audio_status_selftest_live_handoff_v2819 as runner

CYCLE = "V2827"
BUILD_MANIFEST = runner.ROOT / "workspace/private/builds/native-init/v2826-audio-menu-screens/manifest.json"
CANDIDATE_IMAGE = runner.ROOT / "workspace/private/inputs/boot_images/boot_linux_v2826_audio_menu_screens.img"
CANDIDATE_VERSION = "0.10.5"
CANDIDATE_TAG = "v2826-audio-menu-screens"
REPORT_PATH = runner.ROOT / "docs/reports/NATIVE_INIT_V2827_AUDIO_MENU_SCREENS_LIVE_2026-06-19.md"
SCREENAPP_COMMAND = ["screenapp", "audio-map"]
REQUIRED_SCREENAPP_MARKERS = [
    "screenapp.app=audio-map",
    "screenapp.safety=display-only-explicit",
    "screenapp.title=AUDIO ROUTE MAP",
    "screenapp.valid=1",
    "screenapp.rc=0",
    "screenapp.presented=1",
]


def render_report(result: dict[str, object]) -> str:
    audio = result.get("audio_status_markers", {}) if isinstance(result.get("audio_status_markers"), dict) else {}
    selftest = result.get("selftest_markers", {}) if isinstance(result.get("selftest_markers"), dict) else {}
    screenapp = result.get("screenapp_markers", {}) if isinstance(result.get("screenapp_markers"), dict) else {}
    return "\n".join([
        "# Native Init V2827 Audio Menu Screens Live Validation",
        "",
        "## Summary",
        "",
        "- Cycle: `V2827`",
        "- Track: post-promotion audio Tier C menu/screen observability.",
        f"- Decision: `{result.get('decision')}`",
        f"- Result directory: `{result.get('out_dir')}`",
        f"- Candidate image: `{runner.rel(CANDIDATE_IMAGE)}`",
        f"- Candidate SHA256: `{result.get('candidate_sha256')}`",
        f"- Candidate version/tag observed: `{int(bool(result.get('candidate_version_ok')))}`",
        f"- `audio status` marker pass: `{int(bool(audio.get('ok')))}` ({audio.get('count', 0)}/{audio.get('required', 0)})",
        f"- `selftest verbose` audio marker pass: `{int(bool(selftest.get('ok')))}` ({selftest.get('count', 0)}/{selftest.get('required', 0)})",
        f"- `screenapp audio-map` marker pass: `{int(bool(screenapp.get('ok')))}` ({screenapp.get('count', 0)}/{screenapp.get('required', 0)})",
        f"- Rollback attempted: `{int(bool(result.get('rollback_attempted')))}`",
        f"- Rollback recovery fallback used: `{int(bool(result.get('rollback_recovery_fallback_used')))}`",
        f"- Rollback health: version_ok=`{int(bool(result.get('rollback_version_ok')))}` selftest_fail0=`{int(bool(result.get('rollback_selftest_fail0')))}`",
        "",
        "## Finding",
        "",
        "- V2827 flashes the V2826 `0.10.5` APPS/AUDIO menu candidate and validates that the image boots, exposes `audio status`, and still renders the display-only audio route-map screen.",
        "- V2826 source tests cover the APPS/AUDIO touch-menu wiring (`AUDIO STATUS` and `ROUTE MAP` actions). This live run checks the candidate image and renderer on hardware after that menu surface was added.",
        "- The screenapp validation is intentionally display/KMS only; it performs no ADSP boot, `/dev/snd` materialization, route apply/reset, ACDB SET, PCM open, mixer write, speaker write, or playback.",
        "",
        "## Missing Markers",
        "",
        f"- `audio status`: `{audio.get('missing', [])}`",
        f"- `selftest verbose`: `{selftest.get('missing', [])}`",
        f"- `screenapp audio-map`: `{screenapp.get('missing', [])}`",
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
    runner.REQUIRED_SCREENAPP_MARKERS = list(REQUIRED_SCREENAPP_MARKERS)
    runner.render_report = render_report


def main() -> int:
    configure_runner()
    return runner.main()


if __name__ == "__main__":
    raise SystemExit(main())
