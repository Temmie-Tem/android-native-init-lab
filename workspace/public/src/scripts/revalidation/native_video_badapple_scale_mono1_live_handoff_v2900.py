#!/usr/bin/env python3
"""V2900 live handoff for V2897 Bad Apple-scale mono1 video streams.

This reuses the V2893 stream runner mechanics with the V2897 mono1-capable
candidate image. The purpose is to prove the raised stream frame ceiling by
running a 6501-frame full-resolution 1bpp stream, matching Bad Apple-scale frame
counts. The first run may populate the SD SHA cache; later runs can reuse it.
"""

from __future__ import annotations

import native_video_gray8_stream_live_handoff_v2893 as video_live

video_live.RUN_ID = "V2900"
video_live.BUILD_TAG = "v2900-video-badapple-scale-mono1-live"
video_live.REPORT_TITLE = "Native Init V2900 Video Bad Apple Scale Mono1 Live Validation"
video_live.DECISION_PREFIX = "v2900-video-badapple-scale-mono1"
video_live.CANDIDATE_IMAGE = (
    video_live.ROOT / "workspace/private/inputs/boot_images/boot_linux_v2897_video_long_mono1_stream.img"
)
video_live.CANDIDATE_VERSION = "0.10.33"
video_live.CANDIDATE_TAG = "v2897-video-long-mono1-stream"
video_live.CANDIDATE_SHA256 = "1d93aa70bf01f9785ab63656cd45d456ec7e180f7510934fbe280082bb31ba32"
video_live.REPORT_PATH = (
    video_live.ROOT / "docs/reports/NATIVE_INIT_V2900_VIDEO_BADAPPLE_SCALE_MONO1_LIVE_2026-06-20.md"
)
video_live.REMOTE_DIR = "/mnt/sdext/a90/runtime/video/v2900"
video_live.REMOTE_MANIFEST = f"{video_live.REMOTE_DIR}/manifest.json"
video_live.REMOTE_STREAM = f"{video_live.REMOTE_DIR}/frames.a90vstr"


def main() -> int:
    args = video_live.parse_args()
    args.stream_format = "mono1"
    args.stride = (args.width + 7) // 8
    if args.frames == 30:
        args.frames = 6501
    args.transfer_timeout = max(args.transfer_timeout, 2400.0)
    args.stream_timeout = max(args.stream_timeout, 540.0)
    args.chunk_large_streams = True
    args.stream_chunk_bytes = min(args.stream_chunk_bytes, video_live.DEFAULT_STREAM_CHUNK_BYTES)
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
