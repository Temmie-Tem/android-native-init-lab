#!/usr/bin/env python3
"""V2813 live validation for the V2812 audio-core 0.10.0 candidate."""

from __future__ import annotations

import native_audio_late_manifest_wait_live_handoff_v2808 as runner

runner.CYCLE = "V2813"
runner.REPORT_PATH = (
    runner.ROOT / "docs/reports/NATIVE_INIT_V2813_AUDIO_CORE_PROMOTION_CANDIDATE_LIVE_2026-06-19.md"
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
