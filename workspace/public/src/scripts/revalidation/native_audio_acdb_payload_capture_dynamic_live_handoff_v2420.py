#!/usr/bin/env python3
"""V2420 exact-gated dynamic-M0 Android msm_audio_cal payload capture.

This runner reuses the V2416 Android handoff/rollback machinery after V2419
made the observer dynamic-task-aware. It keeps the same AUD-5D safety boundary:
Android/Magisk-root measurement only, no native calibration ioctl, no native
speaker write, no persistent Magisk module, rollback to V2321.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

import native_audio_acdb_android_measurement_planner_v2396 as v2396
import native_audio_acdb_payload_capture_live_handoff_v2416 as v2416
import native_audio_acdb_payload_capture_planner_v2415 as v2415


RUN_ID = "V2420"
BUILD_TAG = "v2420-audio-acdb-dynamic-m0-live"
ROOT = v2415.ROOT
APPROVAL_PHRASE = v2416.APPROVAL_PHRASE
DEFAULT_OUT_BASE = ROOT / "workspace/private/runs/audio"


def rel(path: Path | str) -> str:
    return v2415.rel(path)


def default_live_out_dir() -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return DEFAULT_OUT_BASE / f"v2420-acdb-dynamic-m0-capture-{stamp}"


def rewrite_payload_identity(payload: dict[str, Any]) -> dict[str, Any]:
    payload["run_id"] = RUN_ID
    payload["build_tag"] = BUILD_TAG
    decision = str(payload.get("decision", ""))
    if decision.startswith("v2416-acdb-payload-capture-"):
        payload["decision"] = decision.replace("v2416-acdb-payload-capture-", "v2420-acdb-dynamic-m0-capture-", 1)
    elif decision.startswith("v2416-"):
        payload["decision"] = decision.replace("v2416-", "v2420-", 1)
    payload["dynamic_m0_task_watcher"] = True
    payload["magisk_module_escalation"] = "clone-following-m0-before-m1-temporary-boot-module"
    payload["v2419_observer_fix"] = {
        "task_polling": "poll /proc/<pid>/task/* during capture window",
        "late_tid_attach": True,
        "dedupe_file": "seen-tids.txt",
        "helper_lifetime": "remaining capture window per newly observed TID",
        "bounded_ptrace_waits": "waitpid(WNOHANG) timeout and stop/timed_out JSONL events",
    }
    return payload


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def dry_run(args: argparse.Namespace) -> dict[str, Any]:
    payload = v2416.dry_run(args)
    payload.update({
        "run_id": RUN_ID,
        "build_tag": BUILD_TAG,
        "decision": "v2420-acdb-dynamic-m0-capture-live-dry-run",
        "live_runner": rel(ROOT / "workspace/public/src/scripts/revalidation/native_audio_acdb_payload_capture_dynamic_live_handoff_v2420.py"),
        "approval_phrase_required_for_live": APPROVAL_PHRASE,
        "dynamic_m0_task_watcher": True,
        "magisk_module_escalation": "clone-following-m0-before-m1-temporary-boot-module",
    })
    return payload


def run_live(args: argparse.Namespace) -> dict[str, Any]:
    if args.out_dir is None:
        args.out_dir = default_live_out_dir()
    payload = v2416.run_live(args)
    payload = rewrite_payload_identity(payload)
    out_dir = Path(payload["out_dir"])
    if not out_dir.is_absolute():
        out_dir = ROOT / out_dir
    write_json(out_dir / "result.json", payload)
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="emit the V2420 live plan; no device action")
    mode.add_argument("--run-live", action="store_true", help="run exact-gated V2420 dynamic-M0 capture")
    parser.add_argument("--materialize-capture-helper", action="store_true", help="compile private AArch64 observer for dry-run readiness")
    parser.add_argument("--helper-out-dir", type=Path, default=v2415.DEFAULT_HELPER_OUT_DIR)
    parser.add_argument("--cc", default=v2415.DEFAULT_CC)
    parser.add_argument("--stimulus-apk", type=Path, default=v2396.DEFAULT_STIMULUS_APK)
    parser.add_argument("--adb", default="adb")
    parser.add_argument("--serial")
    parser.add_argument("--android-timeout", type=float, default=420.0)
    parser.add_argument("--adb-command-timeout", type=float, default=120.0)
    parser.add_argument("--flash-timeout", type=float, default=900.0)
    parser.add_argument("--duration-ms", type=int, default=v2396.DEFAULT_DURATION_MS)
    parser.add_argument("--sample-rate", type=int, default=v2396.DEFAULT_SAMPLE_RATE)
    parser.add_argument("--amplitude", type=float, default=v2396.DEFAULT_AMPLITUDE)
    parser.add_argument("--active-delay-sec", type=float, default=0.75)
    parser.add_argument("--post-delay-sec", type=float, default=1.0)
    parser.add_argument("--capture-duration-sec", type=int, default=v2415.DEFAULT_DURATION_SEC)
    parser.add_argument("--capture-warmup-sec", type=float, default=v2416.DEFAULT_CAPTURE_WARMUP_SEC)
    parser.add_argument("--max-bytes", type=int, default=v2415.DEFAULT_MAX_BYTES)
    parser.add_argument("--from-native", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--approval")
    parser.add_argument("--out-dir", type=Path, help="private live output directory")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.run_live:
        try:
            payload = run_live(args)
        except RuntimeError as error:
            payload = {
                "run_id": RUN_ID,
                "build_tag": BUILD_TAG,
                "decision": "v2420-acdb-dynamic-m0-capture-live-refused",
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
