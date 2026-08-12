#!/usr/bin/env python3
"""Materialize one immutable P3.17 userspace overlay intent."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import s22plus_fyg8_p317_generator as generator
import s22plus_fyg8_p317_overlay_contract as contract


SCHEMA = contract.INTENT_SCHEMA
VERDICT = contract.INTENT_VERDICT
DEFAULT_OUT = contract.DEFAULT_OUT


class IntentError(ValueError):
    pass


def create(root: Path, output: Path) -> dict:
    if output.exists() or output.is_symlink():
        raise IntentError(f"P3.17 overlay intent output exists: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    value = contract.create_intent_value(root)
    parent = value["parent_contract"]
    generator.materialize(
        root, output,
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
        offset = 0
        while offset < len(payload):
            written = os.write(descriptor, payload[offset:])
            if written <= 0:
                raise IntentError("short P3.17 overlay intent write")
            offset += written
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    contract.verify_intent(root, output / "overlay-intent.json")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[5])
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    root = args.repo_root.resolve()
    output = args.out if args.out.is_absolute() else root / args.out
    try:
        value = create(root, output)
    except (IntentError, contract.OverlayContractError, OSError, ValueError) as exc:
        print(json.dumps({"schema": SCHEMA, "verdict": "FAIL_CLOSED", "error": str(exc)}))
        return 1
    print(json.dumps({"schema": SCHEMA, "verdict": VERDICT, "run_id": value["run_id"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
