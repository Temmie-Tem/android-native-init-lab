#!/usr/bin/env python3
"""V2894 live handoff for gray8 SD-card video fixture cache hits.

This reuses the V2893 gray8 video stream runner against the same V2892 candidate
image, but records a distinct V2894 report and run directory. The purpose is to
prove that a pre-staged SHA-addressed SD-card fixture can be reused without a
fresh host-to-device frame upload.
"""

from __future__ import annotations

import native_video_gray8_stream_live_handoff_v2893 as v2893

v2893.RUN_ID = "V2894"
v2893.BUILD_TAG = "v2894-video-gray8-cache-hit-live"
v2893.REPORT_TITLE = "Native Init V2894 Video Gray8 SD Cache-Hit Live Validation"
v2893.DECISION_PREFIX = "v2894-video-gray8-cache-hit"
v2893.REPORT_PATH = (
    v2893.ROOT / "docs/reports/NATIVE_INIT_V2894_VIDEO_GRAY8_CACHE_HIT_LIVE_2026-06-19.md"
)
v2893.REMOTE_DIR = "/mnt/sdext/a90/runtime/video/v2894"
v2893.REMOTE_MANIFEST = f"{v2893.REMOTE_DIR}/manifest.json"
v2893.REMOTE_STREAM = f"{v2893.REMOTE_DIR}/frames.a90vstr"


def main() -> int:
    return v2893.main()


if __name__ == "__main__":
    raise SystemExit(main())
