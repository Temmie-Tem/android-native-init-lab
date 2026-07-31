#!/usr/bin/env python3
"""Prove exact P2.92 repair delta attribution and determinism."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import tempfile
from typing import Any, Callable

import s22plus_fyg8_p292_repair_generator as generator
import s22plus_fyg8_p292_repair_spec as spec
import s22plus_fyg8_p292_sot_zero_delta as zero


SCHEMA = "s22plus_fyg8_p292_repair_delta_result_v1"
VERDICT = "PASS_CHECKPOINT_REPAIR_DELTA_ATTRIBUTION"


class RepairDeltaError(ValueError):
    pass


Materializer = Callable[..., dict[str, Any]]


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _read_tree(tree: Path) -> dict[str, bytes]:
    expected = {
        relative.as_posix(): key
        for key, relative in generator.artifact_paths().items()
    }
    actual = {}
    for path in tree.rglob("*"):
        if path.is_symlink():
            raise RepairDeltaError("generated tree contains a symlink")
        if path.is_file():
            relative = path.relative_to(tree).as_posix()
            if relative not in expected:
                raise RepairDeltaError(
                    f"generated tree has extra file: {relative}"
                )
            if stat.S_IMODE(path.stat().st_mode) != 0o400:
                raise RepairDeltaError(
                    f"generated artifact mode differs: {relative}"
                )
            actual[expected[relative]] = path.read_bytes()
        elif not path.is_dir():
            raise RepairDeltaError("generated tree contains a special file")
    if set(actual) != set(generator.artifact_paths()):
        raise RepairDeltaError("generated tree artifact inventory differs")
    return actual


def _baseline_bytes(
    manifest: dict[str, Any], authority: dict[str, Any]
) -> dict[str, bytes]:
    baseline_root = authority["baseline_root"]
    return {
        row["key"]: (
            baseline_root / Path(row["path"])
        ).read_bytes()
        for row in manifest["artifacts"]
    }


def _delta_rows(
    baseline: dict[str, bytes],
    repaired: dict[str, bytes],
) -> tuple[set[str], dict[str, dict[str, Any]]]:
    changed = {
        key for key in baseline if baseline[key] != repaired[key]
    }
    rows = {
        key: {
            "baseline_size": len(baseline[key]),
            "baseline_sha256": _sha256(baseline[key]),
            "repaired_size": len(repaired[key]),
            "repaired_sha256": _sha256(repaired[key]),
            "changed": key in changed,
        }
        for key in sorted(baseline)
    }
    return changed, rows


def run_repair_delta(
    root: Path,
    *,
    materialize: Materializer = generator.materialize,
) -> dict[str, Any]:
    manifest = zero.load_manifest()
    authority = zero.verify_authority(root, manifest)
    baseline = _baseline_bytes(manifest, authority)
    if set(baseline) != set(generator.artifact_paths()):
        raise RepairDeltaError("baseline and generator inventories differ")

    with tempfile.TemporaryDirectory(
        prefix="s22-p292-repair-delta-"
    ) as temporary:
        base = Path(temporary)
        run_a = base / "run-a"
        materialize(
            root,
            run_a,
            run_id=bytes.fromhex(authority["run_id"]),
            unsat_tag=bytes.fromhex(authority["unsat_tag_hex"]),
            profile=authority["profile"],
        )
        run_a_bytes = _read_tree(run_a)
        changed_a, rows_a = _delta_rows(baseline, run_a_bytes)
        if changed_a != spec.REPAIR_ARTIFACT_KEYS:
            raise RepairDeltaError(
                f"run A repair delta differs: {sorted(changed_a)}"
            )

        run_b = base / "run-b"
        materialize(
            root,
            run_b,
            run_id=bytes.fromhex(authority["run_id"]),
            unsat_tag=bytes.fromhex(authority["unsat_tag_hex"]),
            profile=authority["profile"],
        )
        run_b_bytes = _read_tree(run_b)
        changed_b, rows_b = _delta_rows(baseline, run_b_bytes)
        if changed_b != spec.REPAIR_ARTIFACT_KEYS:
            raise RepairDeltaError(
                f"run B repair delta differs: {sorted(changed_b)}"
            )
        if run_a_bytes != run_b_bytes:
            raise RepairDeltaError("phase-2 run A/B bytes differ")

    unchanged = set(baseline) - spec.REPAIR_ARTIFACT_KEYS
    if any(rows_a[key]["changed"] for key in unchanged):
        raise RepairDeltaError("an undeclared artifact changed")
    return {
        "schema": SCHEMA,
        "verdict": VERDICT,
        "baseline": {
            "authority_intent_sha256": authority["intent_sha256"],
            "artifact_count": manifest["artifact_count"],
            "manifest_sha256": manifest["manifest_sha256"],
        },
        "sot": spec.validate(),
        "delta": {
            "declared_changed_keys": sorted(spec.REPAIR_ARTIFACT_KEYS),
            "actual_changed_keys": sorted(changed_a),
            "unchanged_key_count": len(unchanged),
            "run_a": rows_a,
            "run_b": rows_b,
            "run_a_b_determinism": True,
            "comparison_weakened": False,
            "undeclared_delta_count": 0,
        },
        "safety": {
            "host_only": True,
            "intent_created": False,
            "kernel_built": False,
            "image_built": False,
            "device_contact": False,
            "live_authorized": False,
        },
    }


def _durable_write(path: Path, data: bytes) -> None:
    if path.exists() or path.is_symlink():
        raise RepairDeltaError("repair-delta output already exists")
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    descriptor = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
        0o400,
    )
    try:
        offset = 0
        while offset < len(data):
            written = os.write(descriptor, data[offset:])
            if written <= 0:
                raise RepairDeltaError("short repair-delta result write")
            offset += written
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = zero.repo_root()
    try:
        result = run_repair_delta(root)
        if args.out is not None:
            output = args.out if args.out.is_absolute() else root / args.out
            _durable_write(
                output,
                json.dumps(
                    result, indent=2, sort_keys=True, allow_nan=False
                ).encode("ascii")
                + b"\n",
            )
    except (
        RepairDeltaError,
        generator.RepairGeneratorError,
        spec.RepairSpecError,
        OSError,
    ) as exc:
        print(
            json.dumps(
                {"schema": SCHEMA, "verdict": "FAIL_CLOSED", "error": str(exc)},
                sort_keys=True,
            )
        )
        return 1
    print(
        json.dumps(
            {
                "schema": result["schema"],
                "verdict": result["verdict"],
                "changed_keys": result["delta"]["actual_changed_keys"],
                "unchanged_key_count": result["delta"]["unchanged_key_count"],
                "run_a_b_determinism": result["delta"][
                    "run_a_b_determinism"
                ],
                "comparison_weakened": result["delta"][
                    "comparison_weakened"
                ],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
