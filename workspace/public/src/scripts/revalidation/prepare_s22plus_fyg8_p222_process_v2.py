#!/usr/bin/env python3
"""Promote the checked P2.21 candidate into Process v2 offline evidence."""

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

import device_action_f1_evidence_v2 as evidence  # noqa: E402
import s22plus_fyg8_p219_same_ring_contract as contract  # noqa: E402


SCHEMA = "s22plus_fyg8_p222_process_v2_promotion_v1"
P221_SCHEMA = "s22plus_fyg8_p221_candidate_static_checker_v1"
P221_VERDICT = "PASS_P221_INDEPENDENT_ARTIFACT_CLOSURE_HOST_ONLY"
P221_STATIC_SIZE = 8_477
P221_STATIC_SHA256 = (
    "982b48de2eda1d594d0ddededddc25bad2ac33127e2994bea6dce096df2fb6bd"
)
DEFAULT_P221_STATIC = Path(
    "workspace/private/outputs/s22plus_fyg8_p221_candidate/"
    "static-check-result.json"
)
DEFAULT_CANDIDATE_AP = Path(
    "workspace/private/outputs/s22plus_fyg8_p221_candidate/"
    "artifacts/odin4/AP.tar.md5"
)
DEFAULT_OUT = Path(
    "workspace/private/outputs/s22plus_fyg8_p222_process_v2"
)
CANDIDATE_AP = {
    "path": str(DEFAULT_CANDIDATE_AP),
    "size": 27_064_361,
    "sha256": "73e550d53bb0c2f4a8d69fd85829a1fe65e8e1af39069e9e749fe8e81956342e",
}


class PromotionError(ValueError):
    pass


def repo_root() -> Path:
    return Path(__file__).resolve().parents[5]


def resolve(root: Path, path: Path) -> Path:
    return path if path.is_absolute() else root / path


def receipt(data: bytes) -> dict[str, Any]:
    return {"size": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def canonical(value: dict[str, Any]) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("ascii")


def stable_read(path: Path, maximum: int) -> bytes:
    if path.is_symlink():
        raise PromotionError(f"indirect input refused: {path}")
    descriptor = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or not 1 <= before.st_size <= maximum:
            raise PromotionError(f"invalid regular input: {path}")
        chunks: list[bytes] = []
        remaining = before.st_size
        while remaining:
            chunk = os.read(descriptor, min(remaining, 1024 * 1024))
            if not chunk:
                raise PromotionError(f"short input read: {path}")
            chunks.append(chunk)
            remaining -= len(chunk)
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    current = os.lstat(path)
    identity = lambda item: (
        item.st_dev,
        item.st_ino,
        item.st_size,
        item.st_mtime_ns,
        item.st_ctime_ns,
    )
    if identity(before) != identity(after) or identity(after) != identity(current):
        raise PromotionError(f"input changed while reading: {path}")
    return b"".join(chunks)


def _exact(value: Any, keys: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        raise PromotionError(f"{label} shape mismatch")
    return value


def validate_p221(result: dict[str, Any], candidate_ap: dict[str, Any]) -> dict[str, Any]:
    if (
        result.get("schema") != P221_SCHEMA
        or result.get("target") != contract.TARGET
        or result.get("verdict") != P221_VERDICT
    ):
        raise PromotionError("P2.21 static result identity mismatch")
    safety = result.get("safety")
    if not isinstance(safety, dict) or any(
        safety.get(name) is not expected
        for name, expected in {
            "host_only": True,
            "device_contact": False,
            "device_write": False,
            "odin_invoked": False,
            "flash": False,
            "partition_write": False,
            "manifest_created": False,
            "live_authorized": False,
        }.items()
    ):
        raise PromotionError("P2.21 safety result mismatch")
    candidate = result.get("candidate")
    if not isinstance(candidate, dict) or candidate.get("verified") is not True:
        raise PromotionError("P2.21 candidate is not independently verified")
    if candidate.get("manifest_absent") is not True:
        raise PromotionError("P2.21 result already carries a manifest")
    artifacts = candidate.get("artifacts")
    if not isinstance(artifacts, dict):
        raise PromotionError("P2.21 artifact inventory missing")
    ap = artifacts.get("ap_tar_md5")
    if not isinstance(ap, dict) or any(
        ap.get(key) != candidate_ap[key] for key in ("size", "sha256")
    ):
        raise PromotionError("P2.21 candidate AP receipt mismatch")
    closure = candidate.get("extracted_artifact_closure")
    expected_keys = {
        "image",
        "vmlinux",
        "boot_image",
        "boot_kernel",
        "ap_members",
        "boot_only_ap",
        "verified",
    }
    _exact(closure, expected_keys, "P2.21 extracted closure")
    if (
        closure["ap_members"] != [{"name": "boot.img.lz4", "type": "regular"}]
        or closure["boot_only_ap"] is not True
        or closure["verified"] is not True
    ):
        raise PromotionError("P2.21 extracted closure is not boot-only")
    writer = candidate.get("writer_exclusion")
    if (
        not isinstance(writer, dict)
        or writer.get("verified") is not True
        or writer.get("direct_ring_writer_present") is not False
        or writer.get("sec_log_buf_loaded") is not False
    ):
        raise PromotionError("P2.21 ring-writer exclusion is not proven")
    return closure


def derive(
    p221: dict[str, Any], candidate_ap: dict[str, Any]
) -> tuple[bytes, bytes]:
    closure = validate_p221(p221, candidate_ap)
    records = {
        "entry_hex": contract.ENTRY_PROOF.hex(),
        "userspace_hex": contract.USERSPACE_PROOF.hex(),
        "unsat_hex": contract.UNSAT_PROOF.hex(),
    }
    run_manifest = {
        "schema": evidence.SAME_RING_RUN_MANIFEST_SCHEMA,
        "target": contract.TARGET,
        "profile": "P219",
        "contract_id": evidence.SAME_RING_CONTRACT_ID,
        "contract_sha256": contract.CONTRACT_SHA256,
        "records": records,
        "observation_contract": {
            "accepted_identity": "USERSPACE_CALLBACK_REACHED",
            "zero_classification": "ZERO_AMBIGUOUS",
            "entry_threshold": len(contract.ENTRY_PROOF),
            "unsat_threshold": len(contract.UNSAT_PROOF),
            "clean_baseline_required": True,
        },
        "candidate_ap": candidate_ap,
    }
    run_payload = canonical(run_manifest)
    run_receipt = receipt(run_payload)
    static_result = {
        "schema": evidence.SAME_RING_STATIC_SCHEMA,
        "target": contract.TARGET,
        "verdict": evidence.SAME_RING_STATIC_VERDICT,
        "contract_id": evidence.SAME_RING_CONTRACT_ID,
        "contract_sha256": contract.CONTRACT_SHA256,
        "records": records,
        "run_binding": {
            "canonical_manifest_size": len(run_payload),
            "canonical_manifest_sha256": run_receipt["sha256"],
            "verified": True,
        },
        "candidate": {
            "artifacts": {
                "ap": {key: candidate_ap[key] for key in ("size", "sha256")},
                "run_manifest": run_receipt,
                "image": {
                    key: closure["image"][key] for key in ("size", "sha256")
                },
                "vmlinux": {
                    key: closure["vmlinux"][key] for key in ("size", "sha256")
                },
                "boot_image": closure["boot_image"],
            },
            "record_verification": closure,
        },
        "safety": {
            "host_only": True,
            "device_contact": False,
            "device_write": False,
            "odin_invoked": False,
            "odin_transfer": False,
            "flash": False,
            "partition_write": False,
            "live_authorized": False,
        },
    }
    return run_payload, canonical(static_result)


def durable_create(path: Path, payload: bytes) -> None:
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o400
    )
    try:
        offset = 0
        while offset < len(payload):
            written = os.write(descriptor, payload[offset:])
            if written <= 0:
                raise PromotionError(f"short output write: {path}")
            offset += written
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--p221-static", type=Path, default=DEFAULT_P221_STATIC)
    parser.add_argument("--candidate-ap", type=Path, default=DEFAULT_CANDIDATE_AP)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    try:
        p221_payload = stable_read(resolve(root, args.p221_static), 1024 * 1024)
        if receipt(p221_payload) != {
            "size": P221_STATIC_SIZE,
            "sha256": P221_STATIC_SHA256,
        }:
            raise PromotionError("pinned P2.21 static result changed")
        p221 = json.loads(p221_payload.decode("ascii"))
        candidate_payload = stable_read(
            resolve(root, args.candidate_ap), CANDIDATE_AP["size"]
        )
        if receipt(candidate_payload) != {
            key: CANDIDATE_AP[key] for key in ("size", "sha256")
        }:
            raise PromotionError("pinned P2.21 candidate AP changed")
        run_payload, static_payload = derive(p221, CANDIDATE_AP)
        output = resolve(root, args.out)
        output.mkdir(mode=0o700, parents=True)
        durable_create(output / "run-manifest.json", run_payload)
        durable_create(output / "static-check-result.json", static_payload)
        directory = os.open(output, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
        print(
            json.dumps(
                {
                    "schema": SCHEMA,
                    "run_manifest": receipt(run_payload),
                    "static_check": receipt(static_payload),
                    "candidate_ap": {
                        key: CANDIDATE_AP[key] for key in ("size", "sha256")
                    },
                    "ready_manifest_created": False,
                    "device_contact": False,
                    "odin_invoked": False,
                    "flash": False,
                    "live_authorized": False,
                    "verdict": "PASS_P222_PROCESS_V2_OFFLINE_EVIDENCE_PROMOTION",
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    except (OSError, UnicodeError, json.JSONDecodeError, PromotionError) as exc:
        print(f"P2.22 promotion error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
