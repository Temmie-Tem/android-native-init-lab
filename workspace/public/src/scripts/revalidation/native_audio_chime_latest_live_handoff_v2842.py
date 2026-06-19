#!/usr/bin/env python3
"""V2842 live validation for chime playback on the latest V2840 image.

V2841 validated the display-only `screenapp audio-chime` surface on the
`0.10.11` candidate. This wrapper reuses the proven V2839 chime playback
route, retargeted to the same latest V2840 image, to prove the manual chime
preset still reaches the native `audio play` worker after the screen/menu
surface landed. Boot autoplay remains disabled.
"""

from __future__ import annotations

import sys
from typing import Sequence

import native_audio_late_manifest_wait_live_handoff_v2808 as runner

CHIME_DEFAULT_AMPLITUDE_MILLI = 80
CHIME_DEFAULT_DURATION_MS = 1200

runner.CYCLE = "V2842"
runner.REPORT_PATH = (
    runner.ROOT
    / "docs/reports/NATIVE_INIT_V2842_AUDIO_CHIME_LATEST_LIVE_2026-06-19.md"
)
runner.BUILD_MANIFEST = (
    runner.ROOT / "workspace/private/builds/native-init/v2840-audio-chime-screen/manifest.json"
)
runner.CANDIDATE_IMAGE = (
    runner.ROOT / "workspace/private/inputs/boot_images/boot_linux_v2840_audio_chime_screen.img"
)
runner.CANDIDATE_VERSION = "0.10.11"
runner.CANDIDATE_TAG = "v2840-audio-chime-screen"
runner.REPORT_TRACK = "post-promotion audio 0.10.11 chime playback regression validation."
runner.configure_base_for_v2808()

_original_parse_args = runner.parse_args
_original_render_report = runner.render_report


def _argv_list(argv: list[str] | None) -> list[str]:
    return list(sys.argv[1:] if argv is None else argv)


def _has_option(argv: Sequence[str], name: str) -> bool:
    return name in argv or any(item.startswith(name + "=") for item in argv)


def parse_args(argv: list[str] | None = None):
    raw = _argv_list(argv)
    args = _original_parse_args(argv)
    if not _has_option(raw, "--amplitude-milli"):
        args.amplitude_milli = CHIME_DEFAULT_AMPLITUDE_MILLI
    if not _has_option(raw, "--duration-ms"):
        args.duration_ms = CHIME_DEFAULT_DURATION_MS
    return args


def chime_command(args) -> list[str]:
    return [
        "audio",
        "chime",
        "--duration-ms",
        str(args.duration_ms),
        "--amplitude-milli",
        str(args.amplitude_milli),
        "--execute",
    ]


def render_report(result: dict[str, object]) -> str:
    base_report = _original_render_report(result)
    chime_section = "\n".join([
        "## Latest Chime Playback Evidence",
        "",
        f"- Native command: `{result.get('play_command')}`",
        f"- Candidate image: `{runner.rel(runner.CANDIDATE_IMAGE)}`",
        f"- Candidate version/tag: `{runner.CANDIDATE_VERSION}` / `{runner.CANDIDATE_TAG}`",
        f"- Chime default amplitude milli: `{CHIME_DEFAULT_AMPLITUDE_MILLI}`",
        f"- Chime default duration ms: `{CHIME_DEFAULT_DURATION_MS}`",
        "- Boot autoplay: `disabled`.",
        "- This is a playback regression validation for the latest `0.10.11` chime-screen image; it does not enable boot-time audio.",
        "",
    ])
    return base_report + "\n" + chime_section


runner.parse_args = parse_args
runner.play_command = chime_command
runner.render_report = render_report


if __name__ == "__main__":
    raise SystemExit(runner.main())
