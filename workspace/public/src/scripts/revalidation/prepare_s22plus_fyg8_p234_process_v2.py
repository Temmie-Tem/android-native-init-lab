#!/usr/bin/env python3
"""Promote one independently checked P2.34 E1A candidate into offline evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import device_action_f1_evidence_v2 as evidence  # noqa: E402
import s22plus_boot_verify as boot_verify  # noqa: E402
import s22plus_fyg8_p234_candidate_static_checker as static_checker  # noqa: E402


SCHEMA = "s22plus_fyg8_p234_process_v2_promotion_v1"
VERDICT = evidence.E1_LATEST_STAGE_STATIC_VERDICT
TARGET = static_checker.TARGET
DEFAULT_STATIC = static_checker.DEFAULT_OUT
DEFAULT_CANDIDATE_AP = (
    static_checker.DEFAULT_CANDIDATE / "odin4/AP.tar.md5"
)
DEFAULT_OUT = Path("workspace/private/outputs/s22plus_fyg8_p234/process-v2")


class PromotionError(ValueError):
    pass


def repo_root() -> Path:
    return static_checker.repo_root()


def resolve(root: Path, value: Path) -> Path:
    return static_checker.resolve(root, value)


def receipt(data: bytes) -> dict[str, Any]:
    return {"size": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def canonical(value: dict[str, Any]) -> bytes:
    try:
        return json.dumps(
            value, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode("ascii")
    except (TypeError, ValueError, UnicodeError) as exc:
        raise PromotionError("P2.34 promotion value is not canonical ASCII JSON") from exc


def exact_identity(value: Any, label: str) -> dict[str, Any]:
    if (
        not isinstance(value, dict)
        or set(value) != {"size", "sha256"}
        or isinstance(value["size"], bool)
        or not isinstance(value["size"], int)
        or value["size"] <= 0
        or not isinstance(value["sha256"], str)
        or len(value["sha256"]) != 64
    ):
        raise PromotionError(f"{label} identity is malformed")
    try:
        bytes.fromhex(value["sha256"])
    except ValueError as exc:
        raise PromotionError(f"{label} digest is not hexadecimal") from exc
    return {"size": value["size"], "sha256": value["sha256"]}


def validate_static(
    result: dict[str, Any], static_receipt: dict[str, Any], ap_receipt: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    if (
        result.get("schema") != static_checker.SCHEMA
        or result.get("target") != TARGET
        or result.get("verdict") != static_checker.VERDICT
    ):
        raise PromotionError("P2.34 candidate static result identity mismatch")
    candidate_contract = result.get("candidate_contract")
    if (
        not isinstance(candidate_contract, dict)
        or candidate_contract.get("profile") != "E1A"
        or candidate_contract.get("decoder_id") != evidence.E1_LATEST_STAGE_DECODER
        or candidate_contract.get("decoder_policy_id")
        != evidence.e1_latest_stage.POLICY_ID
        or candidate_contract.get("verified") is not True
    ):
        raise PromotionError("P2.34 candidate contract is not E1A-bound")
    run_id = candidate_contract.get("run_id")
    if not isinstance(run_id, str) or evidence.HEX32_RE.fullmatch(run_id) is None:
        raise PromotionError("P2.34 candidate run ID is malformed")
    candidate = result.get("candidate")
    if (
        not isinstance(candidate, dict)
        or candidate.get("verified") is not True
        or candidate.get("boot_only_ap") is not True
        or candidate.get("independent_reconstruction") is not True
        or candidate.get("writer_exclusion_verified") is not True
        or candidate.get("two_package_builds_byte_identical") is not True
        or candidate.get("manifest_absent") is not True
    ):
        raise PromotionError("P2.34 candidate is not independently closed")
    build = result.get("build_repro")
    if (
        not isinstance(build, dict)
        or build.get("fresh_reverification") is not True
        or build.get("two_clean_builds_byte_identical") is not True
        or build.get("linked_audit_verified") is not True
    ):
        raise PromotionError("P2.34 clean-build closure is incomplete")
    artifacts = candidate.get("artifacts")
    userspace = candidate.get("userspace")
    if not isinstance(artifacts, dict) or not isinstance(userspace, dict):
        raise PromotionError("P2.34 candidate artifact closure is missing")
    identities = {
        "ap": exact_identity(artifacts.get("ap_tar_md5"), "candidate AP"),
        "candidate_static": exact_identity(static_receipt, "candidate static result"),
        "image": exact_identity(build.get("image"), "candidate Image"),
        "boot_image": exact_identity(artifacts.get("boot_img"), "candidate boot"),
        "init": exact_identity(userspace.get("init"), "candidate init"),
        "child": exact_identity(userspace.get("child"), "candidate child"),
    }
    if identities["ap"] != ap_receipt:
        raise PromotionError("P2.34 candidate AP changed after static verification")
    safety = result.get("safety")
    expected_safety = {
        "host_only": True,
        "device_contact": False,
        "device_write": False,
        "odin_invoked": False,
        "flash": False,
        "partition_write": False,
        "manifest_created": False,
        "live_authorized": False,
    }
    if safety != expected_safety:
        raise PromotionError("P2.34 candidate static safety contract mismatch")
    return candidate_contract, identities


def derive(
    static_result: dict[str, Any],
    static_receipt: dict[str, Any],
    candidate_ap: dict[str, Any],
) -> tuple[bytes, bytes]:
    candidate_contract, identities = validate_static(
        static_result, static_receipt, candidate_ap
    )
    run_id = candidate_contract["run_id"]
    profile = candidate_contract["profile"]
    model = evidence.e1_latest_stage.model
    run_manifest = {
        "schema": evidence.E1_LATEST_STAGE_RUN_MANIFEST_SCHEMA,
        "target": TARGET,
        "profile": profile,
        "run_id": run_id,
        "decoder": evidence.E1_LATEST_STAGE_DECODER,
        "policy_id": evidence.e1_latest_stage.POLICY_ID,
        "records": {
            "long_family_hex": model.LONG_FAMILY.hex(),
            "unsat_family_hex": model.UNSAT_FAMILY.hex(),
            "terminal_stage": model.PROFILE_TERMINALS[profile],
        },
        "observation_contract": {
            "accepted_identity": "E1A_TERMINAL_SUCCESS_REACHED",
            "minimum_success_count": 1,
            "clean_baseline_required": True,
        },
        "candidate_ap": candidate_ap,
        "candidate_static": static_receipt,
    }
    run_payload = canonical(run_manifest)
    static_result = {
        "schema": evidence.E1_LATEST_STAGE_STATIC_SCHEMA,
        "target": TARGET,
        "verdict": VERDICT,
        "profile": profile,
        "run_id": run_id,
        "decoder": evidence.E1_LATEST_STAGE_DECODER,
        "policy_id": evidence.e1_latest_stage.POLICY_ID,
        "run_binding": {
            "canonical_manifest_size": len(run_payload),
            "canonical_manifest_sha256": hashlib.sha256(run_payload).hexdigest(),
            "verified": True,
        },
        "candidate": {
            "artifacts": identities,
            "boot_only_ap": True,
            "two_clean_builds_byte_identical": True,
            "two_package_builds_byte_identical": True,
            "linked_audit_verified": True,
            "independent_reconstruction": True,
            "writer_exclusion_verified": True,
            "verified": True,
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
    parser.add_argument("--candidate-static", type=Path, default=DEFAULT_STATIC)
    parser.add_argument("--candidate-ap", type=Path, default=DEFAULT_CANDIDATE_AP)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    try:
        static_payload = static_checker.stable_read(
            resolve(root, args.candidate_static),
            "P2.34 candidate static result",
            16 * 1024 * 1024,
        )
        try:
            static_result = json.loads(static_payload.decode("ascii"))
        except (UnicodeError, json.JSONDecodeError) as exc:
            raise PromotionError("P2.34 candidate static result is not JSON") from exc
        if not isinstance(static_result, dict):
            raise PromotionError("P2.34 candidate static result is not an object")
        ap_payload = static_checker.stable_read(
            resolve(root, args.candidate_ap),
            "P2.34 candidate AP",
            static_checker.ARTIFACT_LIMITS["ap_tar_md5"],
        )
        ap_info, _frame = boot_verify.parse_ap_tar_md5(ap_payload)
        if ap_info["member"]["name"] != "boot.img.lz4":
            raise PromotionError("P2.34 candidate AP is not boot-only")
        static_receipt = receipt(static_payload)
        ap_receipt = receipt(ap_payload)
        run_payload, process_static = derive(
            static_result, static_receipt, ap_receipt
        )
        output = resolve(root, args.out)
        output.mkdir(mode=0o700, parents=True)
        durable_create(output / "run-manifest.json", run_payload)
        durable_create(output / "static-check-result.json", process_static)
        durable_create(output / "candidate-static.json", static_payload)
        descriptor = os.open(output, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        print(
            json.dumps(
                {
                    "schema": SCHEMA,
                    "verdict": VERDICT,
                    "candidate_ap": ap_receipt,
                    "candidate_static": static_receipt,
                    "candidate_static_payload": receipt(static_payload),
                    "run_manifest": receipt(run_payload),
                    "static_check": receipt(process_static),
                    "ready_manifest_created": False,
                    "device_contact": False,
                    "odin_invoked": False,
                    "flash": False,
                    "live_authorized": False,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    except (
        PromotionError,
        static_checker.CheckError,
        boot_verify.BootVerifyError,
        OSError,
    ) as exc:
        print(f"P2.34 promotion error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
