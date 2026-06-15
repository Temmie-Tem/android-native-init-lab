#!/usr/bin/env python3
"""V2426 exact-gated rerun of the hardened thread-set ACDB capture.

This is a thin identity wrapper around the V2424 live runner after V2425 added
ADB staging waits. It preserves the same V2423 hybrid observer semantics while
recording the next live attempt under a new V-iteration identity.
"""

from __future__ import annotations

import json

import native_audio_acdb_threadset_clone_follow_live_handoff_v2424 as base


RUN_ID = "V2426"
BUILD_TAG = "v2426-audio-acdb-threadset-clone-follow-live-rerun"

base.RUN_ID = RUN_ID
base.BUILD_TAG = BUILD_TAG


def dry_run(args):
    payload = base.dry_run(args)
    payload.update({
        "run_id": RUN_ID,
        "build_tag": BUILD_TAG,
        "decision": "v2426-acdb-threadset-clone-follow-capture-live-dry-run",
        "live_runner": base.rel(base.ROOT / "workspace/public/src/scripts/revalidation/native_audio_acdb_threadset_clone_follow_live_handoff_v2426.py"),
        "base_runner": base.rel(base.ROOT / "workspace/public/src/scripts/revalidation/native_audio_acdb_threadset_clone_follow_live_handoff_v2424.py"),
        "inherits_v2425_stage_adb_waits": True,
    })
    return payload


def main() -> int:
    args = base.parse_args()
    if args.run_live:
        try:
            payload = base.run_live(args)
        except RuntimeError as error:
            payload = {
                "run_id": RUN_ID,
                "build_tag": BUILD_TAG,
                "decision": "v2426-acdb-threadset-clone-follow-capture-live-refused",
                "ok": False,
                "rolled_back": False,
                "reason": str(error),
            }
            print(json.dumps(payload, indent=2, sort_keys=True))
            return 1
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0 if payload.get("ok") and payload.get("rolled_back") else 1

    payload = dry_run(args)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
