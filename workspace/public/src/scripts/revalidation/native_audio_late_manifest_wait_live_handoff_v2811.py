#!/usr/bin/env python3
"""V2811 retry wrapper for late-manifest audio with shortened play command."""

from __future__ import annotations

import native_audio_late_manifest_wait_live_handoff_v2808 as runner

runner.CYCLE = "V2811"
runner.REPORT_PATH = (
    runner.ROOT / "docs/reports/NATIVE_INIT_V2811_AUDIO_LATE_MANIFEST_SHORT_PLAY_LIVE_2026-06-19.md"
)


if __name__ == "__main__":
    raise SystemExit(runner.main())
