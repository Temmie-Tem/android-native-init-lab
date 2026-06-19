#!/usr/bin/env python3
"""V2896 live handoff for V2895 mono1 video streams.

This reuses the V2893 stream runner mechanics with the V2895 mono1-capable
candidate image. The purpose is to prove the B/W-friendly 1bpp stream format on
the existing KMS page-flip playback path.
"""

from __future__ import annotations

import native_video_gray8_stream_live_handoff_v2893 as video_live

video_live.RUN_ID = "V2896"
video_live.BUILD_TAG = "v2896-video-mono1-stream-live"
video_live.REPORT_TITLE = "Native Init V2896 Video Mono1 Stream Live Validation"
video_live.DECISION_PREFIX = "v2896-video-mono1-stream"
video_live.CANDIDATE_IMAGE = (
    video_live.ROOT / "workspace/private/inputs/boot_images/boot_linux_v2895_video_mono1_stream.img"
)
video_live.CANDIDATE_VERSION = "0.10.32"
video_live.CANDIDATE_TAG = "v2895-video-mono1-stream"
video_live.CANDIDATE_SHA256 = "9708a690ba3c552d1860bf29c8698de780cb5abfdc4557fc49213fb51f83c860"
video_live.REPORT_PATH = (
    video_live.ROOT / "docs/reports/NATIVE_INIT_V2896_VIDEO_MONO1_STREAM_LIVE_2026-06-19.md"
)
video_live.REMOTE_DIR = "/mnt/sdext/a90/runtime/video/v2896"
video_live.REMOTE_MANIFEST = f"{video_live.REMOTE_DIR}/manifest.json"
video_live.REMOTE_STREAM = f"{video_live.REMOTE_DIR}/frames.a90vstr"


def main() -> int:
    args = video_live.parse_args()
    args.stream_format = "mono1"
    args.stride = (args.width + 7) // 8
    out_dir = video_live.ROOT / f"workspace/private/runs/video/{video_live.BUILD_TAG}-{video_live.now_slug()}"
    out_dir.mkdir(parents=True, exist_ok=True)
    state = video_live.preflight_state(args)
    if not args.live:
        payload = video_live.dry_run_payload(args, state)
        video_live.write_json(out_dir / "dry_run.json", payload)
        print(video_live.json.dumps(payload, indent=2, sort_keys=True))
        return 0 if payload["ok"] else 1
    if not video_live.preflight_ok(state):
        payload = {
            "decision": f"{video_live.DECISION_PREFIX}-live-preflight-failed-no-flash",
            "pass": False,
            "preflight": state,
        }
        video_live.write_json(out_dir / "result.json", payload)
        video_live.REPORT_PATH.write_text(video_live.render_report(payload), encoding="utf-8")
        print(video_live.json.dumps({
            "decision": payload["decision"],
            "pass": False,
            "out_dir": video_live.rel(out_dir),
        }, indent=2, sort_keys=True))
        return 1
    result = video_live.run_live(args, out_dir, state)
    print(video_live.json.dumps({
        "decision": result.get("decision"),
        "pass": bool(result.get("pass")) and bool(result.get("rollback_version_ok")) and bool(result.get("rollback_selftest_fail0")),
        "out_dir": video_live.rel(out_dir),
        "rollback_version_ok": result.get("rollback_version_ok"),
        "rollback_selftest_fail0": result.get("rollback_selftest_fail0"),
    }, indent=2, sort_keys=True))
    return 0 if result.get("pass") and result.get("rollback_version_ok") and result.get("rollback_selftest_fail0") else 1


if __name__ == "__main__":
    raise SystemExit(main())
