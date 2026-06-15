#!/usr/bin/env python3
"""V2548 host-only gate for the real ACDB topology replay payload.

This unit promotes the V2547 private capture into a stable private replay input
and emits a public-safe manifest proving the payload length/SHA/non-zero checks
and replay policies.  It does not touch a device and does not issue native
/dev/msm_audio_cal ioctls.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[5]
RUN_ID = "V2548"
BUILD_TAG = "v2548-audio-acdb-real-payload-gate"
EXPECTED_PAYLOAD_LEN = 4916
EXPECTED_PAYLOAD_SHA256 = "7c5d45efa40944bc23dcc83af9f0046249499bb13d1a03c3470c287127992b89"
ZERO_4916_SHA256 = "9af4895ee511379e7a2d0620ea158c535f88c853de6df2eb2cd32f0cb4a2cb8c"
EXPECTED_CAL_TYPE = 39
EXPECTED_BUFFER_NUMBER = 0
DEFAULT_SOURCE_PAYLOAD = (
    ROOT
    / "workspace/private/runs/audio/v2490-acdb-ownprocess-get-20260616-080716/ownget-device-artifacts/acdbtap/acdbtap-00000003-cmd-00013296-len-00001334.bin"
)
DEFAULT_STABLE_PAYLOAD = (
    ROOT
    / "workspace/private/inputs/audio/acdb_replay/payloads/core_custom_topologies_v2547.bin"
)
DEFAULT_BUILD_ROOT = ROOT / "workspace/private/builds/audio" / BUILD_TAG
DEFAULT_MANIFEST = DEFAULT_BUILD_ROOT / "manifest.json"
REPLAY_SCAFFOLD_SOURCE = "workspace/public/src/native-init/helpers/a90_acdb_replay_scaffold_v2474.c"
REPLAY_SCAFFOLD_PLANNER = "workspace/public/src/scripts/revalidation/native_audio_acdb_replay_scaffold_v2474.py"


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def is_all_zero(path: Path) -> bool:
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            if any(chunk):
                return False
    return True


def payload_state(path: Path, *, expected_sha256: str = EXPECTED_PAYLOAD_SHA256) -> dict[str, Any]:
    state: dict[str, Any] = {
        "path": rel(path),
        "exists": path.exists(),
        "expected_size": EXPECTED_PAYLOAD_LEN,
        "expected_sha256": expected_sha256,
        "zero_sha256": ZERO_4916_SHA256,
        "private_only": True,
        "committable": False,
    }
    if not path.exists():
        return state | {
            "ok": False,
            "reason": "missing",
        }
    if not path.is_file():
        return state | {
            "ok": False,
            "reason": "not-file",
        }
    size = path.stat().st_size
    digest = sha256_file(path)
    all_zero = is_all_zero(path)
    checks = {
        "size_ok": size == EXPECTED_PAYLOAD_LEN,
        "sha256_ok": digest == expected_sha256,
        "nonzero_ok": not all_zero,
        "zero_hash_rejected": digest != ZERO_4916_SHA256,
    }
    return state | {
        "ok": all(checks.values()),
        "reason": "ok" if all(checks.values()) else "payload-validation-failed",
        "size": size,
        "sha256": digest,
        "mode": oct(path.stat().st_mode & 0o777),
        "all_zero": all_zero,
        "checks": checks,
    }


def stage_payload(source: Path, target: Path, *, expected_sha256: str = EXPECTED_PAYLOAD_SHA256) -> dict[str, Any]:
    before = payload_state(source, expected_sha256=expected_sha256)
    if not before["ok"]:
        return {
            "ok": False,
            "source": before,
            "target": payload_state(target, expected_sha256=expected_sha256),
            "reason": "source-payload-invalid",
        }
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)
    target.chmod(0o600)
    after = payload_state(target, expected_sha256=expected_sha256)
    return {
        "ok": after["ok"],
        "source": before,
        "target": after,
        "reason": "ok" if after["ok"] else "target-payload-invalid",
    }


def replay_policy_state(stable_payload: dict[str, Any]) -> dict[str, Any]:
    payload_ready = bool(stable_payload.get("ok"))
    return {
        "cal_type": EXPECTED_CAL_TYPE,
        "buffer_number": EXPECTED_BUFFER_NUMBER,
        "payload_len": EXPECTED_PAYLOAD_LEN,
        "payload_sha256": EXPECTED_PAYLOAD_SHA256,
        "payload_ready": payload_ready,
        "mem_handle_policy": {
            "android_mem_handle_37_is_not_reused": True,
            "native_mem_handle": "fresh native dma-buf fd allocated in the replay process",
            "fd_lifetime": "keep dma-buf fd and /dev/msm_audio_cal fd open across the bounded PCM probe",
        },
        "cleanup_policy": [
            "AUDIO_DEALLOCATE_CALIBRATION for cal_type 39, buffer 0, same native dma-buf fd",
            "close /dev/msm_audio_cal after deallocate/result capture",
            "munmap and close dma-buf fd",
            "close /dev/ion fd",
        ],
        "native_set_live_ran": False,
        "safe_to_run_live_set_from_this_unit": False,
        "next_gate": "build and run a separate exact-gated native replay runner that consumes this pinned private payload",
    }


def source_state() -> dict[str, Any]:
    scaffold_source = ROOT / REPLAY_SCAFFOLD_SOURCE
    scaffold_planner = ROOT / REPLAY_SCAFFOLD_PLANNER
    report = ROOT / "docs/reports/NATIVE_INIT_V2547_AUDIO_ACDB_INDIRECT_TOPOLOGY_CAPTURE_2026-06-16.md"
    return {
        "v2547_report": {
            "path": rel(report),
            "exists": report.exists(),
            "mentions_payload_sha": report.exists() and EXPECTED_PAYLOAD_SHA256 in report.read_text(encoding="utf-8", errors="replace"),
        },
        "replay_scaffold_source": {
            "path": REPLAY_SCAFFOLD_SOURCE,
            "exists": scaffold_source.exists(),
        },
        "replay_scaffold_planner": {
            "path": REPLAY_SCAFFOLD_PLANNER,
            "exists": scaffold_planner.exists(),
        },
    }


def manifest(args: argparse.Namespace) -> dict[str, Any]:
    started = time.monotonic()
    stage: dict[str, Any] | None = None
    if args.stage_payload:
        stage = stage_payload(
            args.source_payload_path,
            args.stable_payload_path,
            expected_sha256=args.expected_payload_sha256,
        )
    source = payload_state(args.source_payload_path, expected_sha256=args.expected_payload_sha256)
    stable = payload_state(args.stable_payload_path, expected_sha256=args.expected_payload_sha256)
    policy = replay_policy_state(stable)
    payload: dict[str, Any] = {
        "decision": "v2548-acdb-real-payload-gate-host-only",
        "run_id": RUN_ID,
        "build_tag": BUILD_TAG,
        "created_at": now_iso(),
        "elapsed_sec": round(time.monotonic() - started, 3),
        "ok": stable["ok"] if args.require_stable_payload else source["ok"],
        "host_only": True,
        "device_action": "none",
        "flash_action": "none",
        "native_calibration_ioctls": "none",
        "speaker_or_pcm_action": "none",
        "source_state": source_state(),
        "capture_payload_source": source,
        "stable_replay_payload": stable,
        "stage_payload": stage or {"requested": False},
        "replay_policy": policy,
        "boundaries": {
            "raw_bytes_private_only": True,
            "no_raw_payload_committed": True,
            "no_dev_msm_audio_cal_open": True,
            "no_audio_set_calibration": True,
            "no_mixer_write": True,
            "no_pcm_playback": True,
            "live_replay_requires_separate_unit": True,
        },
        "manifest_path": rel(args.manifest_path),
    }
    args.manifest_path.parent.mkdir(parents=True, exist_ok=True)
    args.manifest_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return payload


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="emit the host-only gate manifest")
    parser.add_argument("--stage-payload", action="store_true", help="copy the V2547 payload to the stable private replay input path")
    parser.add_argument("--require-stable-payload", action="store_true", help="overall ok requires the stable private replay input to validate")
    parser.add_argument("--source-payload-path", type=Path, default=DEFAULT_SOURCE_PAYLOAD)
    parser.add_argument("--stable-payload-path", type=Path, default=DEFAULT_STABLE_PAYLOAD)
    parser.add_argument("--expected-payload-sha256", default=EXPECTED_PAYLOAD_SHA256)
    parser.add_argument("--manifest-path", type=Path, default=DEFAULT_MANIFEST)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if not args.dry_run and not args.stage_payload:
        args.dry_run = True
    payload = manifest(args)
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
