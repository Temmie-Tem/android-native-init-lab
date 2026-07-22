#!/usr/bin/env python3
"""Reopen and verify one exact P2.34 candidate identity and kernel patch."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import sys
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import s22plus_fyg8_p234_candidate_intent as intent  # noqa: E402


SCHEMA = "s22plus_fyg8_p234_candidate_contract_v1"
VERDICT = "PASS_P234_CANDIDATE_CONTRACT_HOST_ONLY"
TARGET = intent.TARGET
DEFAULT_SOURCE = intent.DEFAULT_SOURCE
DEFAULT_INTENT = intent.DEFAULT_OUT / "candidate-intent.json"
DEFAULT_PATCH = intent.DEFAULT_OUT / "candidate.patch"


class ContractError(ValueError):
    pass


def stable_read(path: Path, label: str, maximum: int = 4 * 1024 * 1024) -> bytes:
    flags = os.O_RDONLY | os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags)
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or not 1 <= before.st_size <= maximum:
            raise ContractError(f"{label} is not a bounded regular file")
        chunks: list[bytes] = []
        remaining = before.st_size
        while remaining:
            chunk = os.read(descriptor, min(remaining, 1024 * 1024))
            if not chunk:
                raise ContractError(f"{label} read was short")
            chunks.append(chunk)
            remaining -= len(chunk)
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    current = os.lstat(path)
    identity_fields = ("st_dev", "st_ino", "st_size", "st_mtime_ns", "st_ctime_ns")
    if any(
        getattr(before, name) != getattr(after, name)
        or getattr(after, name) != getattr(current, name)
        for name in identity_fields
    ):
        raise ContractError(f"{label} changed while reading")
    return b"".join(chunks)


def _exact(value: Any, keys: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        raise ContractError(f"{label} shape mismatch")
    return value


def verify(
    root: Path,
    source: Path,
    intent_path: Path,
    patch_path: Path,
) -> dict[str, Any]:
    intent_bytes = stable_read(intent_path, "P2.34 candidate intent")
    patch = stable_read(patch_path, "P2.34 candidate patch")
    try:
        value = json.loads(intent_bytes.decode("ascii"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ContractError("candidate intent is not valid ASCII JSON") from exc
    if not isinstance(value, dict):
        raise ContractError("candidate intent root is not an object")
    for name, expected in {
        "schema": intent.SCHEMA,
        "target": TARGET,
        "verdict": intent.VERDICT,
        "profile": intent.PROFILE,
        "profile_number": intent.PROFILE_NUMBER,
    }.items():
        if value.get(name) != expected:
            raise ContractError(f"candidate intent identity mismatch: {name}")

    preimage = value.get("identity_preimage")
    if not isinstance(preimage, dict):
        raise ContractError("candidate identity preimage is missing")
    nonce_text = preimage.get("nonce")
    if not isinstance(nonce_text, str):
        raise ContractError("candidate nonce is missing")
    try:
        nonce = intent.parse_nonce(nonce_text)
    except intent.IntentError as exc:
        raise ContractError(str(exc)) from exc
    _source_data, source_rows = intent.source_receipts(root)
    expected_preimage = intent.identity_preimage(nonce, source_rows)
    if preimage != expected_preimage:
        raise ContractError("candidate identity preimage does not bind current sources")
    preimage_sha256 = hashlib.sha256(intent.canonical(preimage)).hexdigest()
    if value.get("identity_preimage_sha256") != preimage_sha256:
        raise ContractError("candidate identity preimage digest mismatch")
    run_id = intent.derive_run_id(preimage)
    if value.get("run_id") != run_id.hex():
        raise ContractError("candidate run ID derivation mismatch")
    unsat = intent.decoder.model.unsat_record(intent.PROFILE, run_id)
    unsat_tag = unsat[len(intent.decoder.model.UNSAT_FAMILY) :]
    if (
        value.get("unsat_record_hex") != unsat.hex()
        or value.get("unsat_tag_hex") != unsat_tag.hex()
    ):
        raise ContractError("candidate UNSAT derivation mismatch")

    expected_patch = intent.build_patch(
        _source_data["base_patch"], run_id, unsat_tag
    )
    if patch != expected_patch:
        raise ContractError("candidate patch differs from exact regeneration")
    patch_audit = intent.audit_patch(source, patch, run_id, unsat_tag)
    expected_patch_row = {**intent.receipt(patch), **patch_audit}
    if value.get("patch") != expected_patch_row:
        raise ContractError("candidate patch audit receipt mismatch")
    reachable = intent.p233.validate_reachable_records({intent.PROFILE: run_id})
    if value.get("reachable_record_contract") != reachable:
        raise ContractError("candidate reachable-record contract mismatch")
    safety = _exact(
        value.get("safety"),
        {
            "host_only",
            "kernel_built",
            "image_built",
            "candidate_created",
            "manifest_created",
            "device_contact",
            "device_write",
            "odin_invoked",
            "live_authorized",
        },
        "candidate intent safety",
    )
    if safety["host_only"] is not True or any(
        safety[name] is not False for name in safety if name != "host_only"
    ):
        raise ContractError("candidate intent safety boundary changed")
    return {
        "schema": SCHEMA,
        "target": TARGET,
        "verdict": VERDICT,
        "profile": intent.PROFILE,
        "profile_number": intent.PROFILE_NUMBER,
        "run_id": run_id.hex(),
        "unsat_record_hex": unsat.hex(),
        "unsat_tag_hex": unsat_tag.hex(),
        "decoder_id": intent.decoder.DECODER_ID,
        "decoder_policy_id": intent.decoder.POLICY_ID,
        "intent": intent.receipt(intent_bytes),
        "patch": expected_patch_row,
        "base_files": patch_audit["base_files"],
        "patched_files": patch_audit["patched_files"],
        "config_lines": patch_audit["config_lines"],
        "reachable_record_contract": reachable,
        "verified": True,
        "safety": {
            "host_only": True,
            "device_contact": False,
            "device_write": False,
            "odin_invoked": False,
            "live_authorized": False,
        },
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--intent", type=Path, default=DEFAULT_INTENT)
    parser.add_argument("--patch", type=Path, default=DEFAULT_PATCH)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    try:
        args = parse_args(argv)
        root = intent.repo_root()
        result = verify(
            root,
            intent.resolve(root, args.source),
            intent.resolve(root, args.intent),
            intent.resolve(root, args.patch),
        )
    except (
        ContractError,
        intent.IntentError,
        intent.p233.CheckError,
        intent.decoder.model.DesignError,
        OSError,
    ) as exc:
        print(json.dumps({"schema": SCHEMA, "verdict": "FAIL_CLOSED", "error": str(exc)}))
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
