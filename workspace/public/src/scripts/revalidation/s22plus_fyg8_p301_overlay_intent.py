#!/usr/bin/env python3
"""Materialize one P3.01 overlay intent without changing the P3.00 Image."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import s22plus_fyg8_p301_overlay_contract as contract
import s22plus_fyg8_p301_telemetry_generator as generator


SCHEMA = contract.INTENT_SCHEMA
VERDICT = contract.INTENT_VERDICT
DEFAULT_OUT = contract.DEFAULT_OUT


class IntentError(ValueError):
    pass


def create(root: Path, output: Path) -> dict:
    if output.exists() or output.is_symlink():
        raise IntentError(f"P3.01 overlay intent output exists: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    value = contract.create_intent_value(root)
    parent = value["parent_candidate_contract"]
    try:
        generator.materialize(
            root,
            output,
            run_id=bytes.fromhex(parent["run_id"]),
            unsat_tag=bytes.fromhex(parent["unsat_tag_hex"]),
            profile=parent["profile"],
        )
        payload = contract._canonical(value)  # noqa: SLF001
        descriptor = os.open(
            output / "overlay-intent.json",
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
            0o400,
        )
        try:
            if os.write(descriptor, payload) != len(payload):
                raise IntentError("short P3.01 overlay intent write")
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        directory = os.open(output, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    except Exception:
        raise
    contract.verify_intent(root, output / "overlay-intent.json")
    return value


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[5],
    )
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = args.repo_root.resolve()
    output = args.out if args.out.is_absolute() else root / args.out
    try:
        value = create(root, output)
    except (IntentError, contract.OverlayContractError, OSError) as exc:
        print(json.dumps({"schema": SCHEMA, "verdict": "FAIL_CLOSED", "error": str(exc)}))
        return 1
    print(
        json.dumps(
            {
                "schema": SCHEMA,
                "verdict": VERDICT,
                "run_id": value["run_id"],
                "intent_sha256": value["intent_sha256"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
