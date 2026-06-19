#!/usr/bin/env python3
"""V2814 live retry for the V2812 audio-core candidate with marker-loss tolerance."""

from __future__ import annotations

import native_audio_late_manifest_wait_live_handoff_v2808 as runner

runner.CYCLE = "V2814"
runner.REPORT_PATH = (
    runner.ROOT
    / "docs/reports/NATIVE_INIT_V2814_AUDIO_CORE_PROMOTION_CANDIDATE_MARKER_LOSS_TOLERANT_LIVE_2026-06-19.md"
)
runner.BUILD_MANIFEST = (
    runner.ROOT / "workspace/private/builds/native-init/v2812-audio-core-promotion-candidate/manifest.json"
)
runner.CANDIDATE_IMAGE = (
    runner.ROOT / "workspace/private/inputs/boot_images/boot_linux_v2812_audio_core_promotion_candidate.img"
)
runner.CANDIDATE_VERSION = "0.10.0"
runner.CANDIDATE_TAG = "v2812-audio-core-promotion-candidate"
runner.configure_base_for_v2808()


if __name__ == "__main__":
    raise SystemExit(runner.main())
