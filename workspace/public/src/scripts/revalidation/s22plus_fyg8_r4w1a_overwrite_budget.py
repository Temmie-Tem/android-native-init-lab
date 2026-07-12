#!/usr/bin/env python3
"""Measure the retained-log overwrite budget from pinned FYG8 boot captures."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any


SCHEMA = "s22plus_fyg8_r4w1a_overwrite_budget_v1"
RING_TOTAL_SIZE = 2_097_152
RING_HEADER_SIZE = 16
RING_PAYLOAD_SIZE = RING_TOTAL_SIZE - RING_HEADER_SIZE
SNAPSHOT_SIZE = RING_PAYLOAD_SIZE
TIMESTAMP_RE = re.compile(rb"\[\s*([0-9]+\.[0-9]{6})\]")

SOURCES = (
    (
        "o11_postrollback_stock",
        Path("workspace/private/runs/s22plus_o11_stock_first_stage_control_live_gate_20260709T193558Z/android_pstore/postrollback_o11_last_kmsg.bin"),
        "8db1b9211818f654b5c8f50151004dd3373a4c925b8c57aa19c210a8fa157787",
    ),
    (
        "v3437_candidate",
        Path("workspace/private/runs/s22plus_v3437_ramoops_20260710T230320Z/postrun/candidate-last_kmsg.bin"),
        "d6a7bc92b12a472f78ffb2567dae1cdea99dc703ffa0ca26849b154cb5a8c8ae",
    ),
    (
        "v3439_first_stock_boot",
        Path("workspace/private/runs/s22plus_v3439_ramoops_20260710T233555Z/postrun/first-stock-boot-last_kmsg.bin"),
        "4e706127ec6065c98b1ade492fa3bd6f62b8294209b8b9b737546386c78589a3",
    ),
)


class AnalysisError(ValueError):
    pass


def repo_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "GOAL.md").is_file() and (parent / "AGENTS.md").is_file():
            return parent
    raise AnalysisError("repository root not found")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def inspect_capture(root: Path, name: str, path: Path, expected_sha256: str) -> dict[str, Any]:
    resolved = (root / path).resolve()
    if resolved.is_symlink() or not resolved.is_file():
        raise AnalysisError(f"capture missing or not a direct regular file: {resolved}")
    payload = resolved.read_bytes()
    if len(payload) != SNAPSHOT_SIZE:
        raise AnalysisError(f"{name} size mismatch: {len(payload)} != {SNAPSHOT_SIZE}")
    actual = sha256_bytes(payload)
    if actual != expected_sha256:
        raise AnalysisError(f"{name} SHA256 mismatch: {actual}")
    timestamps = [float(match.group(1)) for match in TIMESTAMP_RE.finditer(payload)]
    if not timestamps:
        raise AnalysisError(f"{name} has no parseable kernel timestamps")
    return {
        "name": name,
        "path": str(path),
        "size": len(payload),
        "sha256": actual,
        "parsed_timestamp_count": len(timestamps),
        "oldest_timestamp_sec": min(timestamps),
        "latest_timestamp_sec": max(timestamps),
        "visible_span_sec": round(max(timestamps) - min(timestamps), 6),
        "prefix_loss_possible": True,
    }


def analyze() -> dict[str, Any]:
    root = repo_root()
    captures = [inspect_capture(root, *source) for source in SOURCES]
    return {
        "schema": SCHEMA,
        "target": "SM-S906N/g0q/S906NKSS7FYG8",
        "ring": {
            "total_size": RING_TOTAL_SIZE,
            "header_size": RING_HEADER_SIZE,
            "payload_size": RING_PAYLOAD_SIZE,
            "snapshot_size": SNAPSHOT_SIZE,
        },
        "captures": captures,
        "inference_limits": {
            "exact_bytes_written_since_witness": False,
            "exact_wrap_count_known": False,
            "oldest_visible_timestamp_is_boot_start": False,
            "full_android_boot_can_overwrite_early_marker": True,
            "rollback_absence_proves_init_rejection": False,
            "candidate_snapshot_oracle_independently_closed": False,
        },
        "a0_deliverable_pass": True,
        "a1_ready": False,
        "risk_verdict": "HIGH_RISK_UNRESOLVED",
        "verdict": "PASS_R4W1A_OVERWRITE_BUDGET_MEASURED_HOST_ONLY",
        "safety": {
            "host_only": True,
            "inputs_read_only": True,
            "device_contact": False,
            "flash": False,
            "live_authorized": False,
        },
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        report = analyze()
    except (AnalysisError, OSError) as exc:
        print(json.dumps({"schema": SCHEMA, "verdict": "FAIL_CLOSED", "error": str(exc)}, sort_keys=True))
        return 1
    encoded = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.out is not None:
        out = args.out if args.out.is_absolute() else repo_root() / args.out
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(encoded, encoding="ascii")
    print(encoded, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
