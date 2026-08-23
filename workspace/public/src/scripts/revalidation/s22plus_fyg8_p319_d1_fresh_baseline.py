#!/usr/bin/env python3
"""P3.19 D1 successor contract and host-only rehearsal.

The live branch is intentionally review-pending.  It describes the exact
one-reboot action and its durable no-replay names, but H0 never creates the
approval arm or run directory.  The fresh-baseline normalizer binds this
source identity and accepts only a result carrying the corresponding binding,
so a P3.18 consumed run cannot be substituted.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[5]
SCRIPT = Path(__file__).resolve(strict=True)
REDUCER = ROOT / (
    "workspace/public/src/scripts/revalidation/"
    "s22plus_fyg8_p319_fresh_baseline_capability.py"
)
D0_RUNTIME = ROOT / (
    "workspace/public/src/scripts/revalidation/device_action_d0_v2.py"
)
PROFILE = ROOT / "workspace/public/src/device-action/profiles/s22plus_fyg8.json"
RUN_DIR = ROOT / (
    "workspace/private/runs/device-action-d1-p319-fresh-baseline/"
    "p319-fresh-baseline-1"
)
RUN_ARM = Path(str(RUN_DIR) + ".arm.json")
SCHEMA = "s22plus_fyg8_p319_d1_fresh_baseline_binding_v1"
RESULT_SCHEMA = "s22plus_fyg8_p319_d1_fresh_baseline_v1_result"
REVIEW_STATUS = "review-pending"
BASELINE_DESIGN_SCHEMA = "s22plus_fyg8_p319_fresh_baseline_design_v1"
BASELINE_DESIGN_ID = "s22plus-fyg8-p319-fresh-baseline-design-v1"
TARGET = {"model": "SM-S906N", "codename": "g0q", "build": "S906NKSS7FYG8"}


class D1FreshBaselineError(RuntimeError):
    pass


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("ascii") + b"\n"


def identity(payload: bytes) -> dict[str, Any]:
    return {"size": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}


def _relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path.resolve())


def _stable(path: Path, label: str) -> bytes:
    try:
        before = path.lstat()
        if stat.S_ISLNK(before.st_mode) or not stat.S_ISREG(before.st_mode):
            raise D1FreshBaselineError(f"{label} is not a direct regular file")
        with path.open("rb") as stream:
            payload = stream.read(4 * 1024 * 1024 + 1)
            inside = os.fstat(stream.fileno())
        after = path.lstat()
    except OSError as exc:
        raise D1FreshBaselineError(f"{label} unavailable") from exc
    def stat_tuple(item: os.stat_result) -> tuple[int, int, int, int, int]:
        return (item.st_dev, item.st_ino, item.st_size, item.st_mtime_ns, item.st_ctime_ns)

    if len(payload) != before.st_size or any(stat_tuple(item) != stat_tuple(before) for item in (inside, after)):
        raise D1FreshBaselineError(f"{label} changed while reading")
    return payload


def _source_identity(path: Path, label: str) -> dict[str, Any]:
    payload = _stable(path, label)
    return {"path": _relative(path), **identity(payload)}


def _baseline_design_identity() -> dict[str, Any]:
    return {
        "schema": BASELINE_DESIGN_SCHEMA,
        "design_id": BASELINE_DESIGN_ID,
        "target": TARGET,
        "profile": _source_identity(PROFILE, "S22+ target profile"),
        "reducer": _source_identity(REDUCER, "P3.19 baseline reducer"),
        "d1_source": _source_identity(SCRIPT, "P3.19 D1 design source"),
        "d0_runtime": _source_identity(D0_RUNTIME, "current D0 runtime"),
    }


def build_binding(candidate: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Return the exact P3.19 D1 binding without creating any durable state."""
    design = _baseline_design_identity()
    candidate = dict(candidate or {})
    return {
        "schema": SCHEMA,
        "action": "one exact attended normal Android reboot",
        "target": TARGET,
        "baseline_design": design,
        "candidate": candidate,
        "run_directory": {"path": _relative(RUN_DIR), "publication": "directory-no-replace-then-durable-start-no-replace"},
        "run_approval_arm": {"path": _relative(RUN_ARM), "publication": "file-no-replace-fsync-then-directory-fsync"},
        "command_count": 1,
        "candidate_transfer": False,
        "partition_payload": False,
        "odin": False,
        "download_transition": False,
        "f1_authorized": False,
        "review": {"status": REVIEW_STATUS, "verdict": None},
        "failure_rule": "park without replay or a second reboot command",
    }


class _HostFixture:
    def __init__(self) -> None:
        self.reboots = 0

    def reboot_once(self) -> None:
        if self.reboots:
            raise D1FreshBaselineError("fixture attempted a second reboot")
        self.reboots += 1


def self_test() -> dict[str, Any]:
    """Exercise the D1 schema rehearsal without a target."""
    binding = build_binding()
    transport = _HostFixture()
    transport.reboot_once()
    result = {
        "schema": RESULT_SCHEMA,
        "mode": "fixture-rehearsal",
        "target": TARGET,
        "baseline_design_id": binding["baseline_design"]["design_id"],
        "binding": binding,
        "reboot_count": transport.reboots,
        "candidate_transfer": False,
        "device_contact": False,
        "device_writes": False,
        "second_reboot_requested": False,
        "verdict": "PASS_P319_D1_FRESH_BASELINE_FIXTURE_H0",
    }
    if result["reboot_count"] != 1 or result["binding"]["review"]["status"] != REVIEW_STATUS:
        raise D1FreshBaselineError("D1 fixture closure differs")
    return result


def run_live(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
    """Explicit non-executable placeholder for a future reviewed D1 producer."""
    raise D1FreshBaselineError(
        "P3.19 D1 producer is H0 design-only; no device or acquisition implementation "
        "is present until self-binding, durable arm-before-contact, and independent review"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.self_test:
            print(json.dumps(self_test(), sort_keys=True))
            return 0
        parser.error("host-only mode requires --self-test")
    except D1FreshBaselineError as exc:
        print(f"P3.19 D1 successor blocked: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
