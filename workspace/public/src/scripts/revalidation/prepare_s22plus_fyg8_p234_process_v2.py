#!/usr/bin/env python3
"""Promote one independently checked FYG8 E1 candidate into offline evidence."""

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
import s22plus_fyg8_p242_e2_stock_closure as e2_closure  # noqa: E402
import s22plus_fyg8_p245_e2_stock_closure as p245_e2_closure  # noqa: E402


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
    profile = (
        candidate_contract.get("profile")
        if isinstance(candidate_contract, dict)
        else None
    )
    source_contract_id = (
        candidate_contract.get("source_contract_id")
        if isinstance(candidate_contract, dict)
        else None
    )
    try:
        selected_decoder = evidence._latest_stage_decoder(
            source_contract_id, profile
        )
    except evidence.EvidenceError as exc:
        raise PromotionError(str(exc)) from exc
    if (
        not isinstance(candidate_contract, dict)
        or profile not in evidence.e1_latest_stage.model.PROFILE_NUMBERS
        or candidate_contract.get("decoder_id") != selected_decoder.DECODER_ID
        or candidate_contract.get("decoder_policy_id")
        != selected_decoder.POLICY_ID
        or candidate_contract.get("verified") is not True
    ):
        raise PromotionError("candidate contract is not supported-profile-bound")
    run_id = candidate_contract.get("run_id")
    if not isinstance(run_id, str) or evidence.HEX32_RE.fullmatch(run_id) is None:
        raise PromotionError("P2.34 candidate run ID is malformed")
    try:
        source_receipts = evidence.validate_candidate_source_preimage(
            candidate_contract, profile, run_id
        )
        _source_data, current_source_receipts = (
            static_checker.contract.intent.source_receipts(
                repo_root(),
                profile,
                candidate_contract.get("source_contract_id"),
            )
        )
    except (evidence.EvidenceError, static_checker.contract.intent.IntentError) as exc:
        raise PromotionError("candidate source preimage is invalid") from exc
    if source_receipts != current_source_receipts:
        raise PromotionError("candidate source preimage differs from current sources")
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
    if profile == "E1B":
        try:
            evidence.validate_e1b_stock_closure(
                module_closure=candidate.get("module_closure"),
                effective_rootfs=candidate.get("effective_rootfs"),
                stock_vendor_boot=candidate.get("stock_vendor_boot"),
                expected_init=exact_identity(userspace.get("init"), "candidate init"),
                expected_child=exact_identity(
                    userspace.get("child"), "candidate child"
                ),
            )
        except evidence.EvidenceError as exc:
            raise PromotionError(
                "E1B effective stock rootfs closure is incomplete"
            ) from exc
    elif profile == "E2":
        closure_api = (
            p245_e2_closure
            if candidate_contract.get("source_contract_id") is not None
            else evidence.e2_closure
        )
        try:
            module_closure = closure_api.validate_module_closure(
                candidate.get("module_closure")
            )
            closure_api.validate_effective_rootfs(
                candidate.get("effective_rootfs"),
                expected_init=exact_identity(userspace.get("init"), "candidate init"),
                expected_child=exact_identity(
                    userspace.get("child"), "candidate child"
                ),
                module_closure=module_closure,
            )
            stock_vendor_boot = exact_identity(
                candidate.get("stock_vendor_boot"), "stock vendor_boot"
            )
            if stock_vendor_boot != evidence.E1B_STOCK_VENDOR_BOOT:
                raise PromotionError("E2 stock vendor_boot identity mismatch")
        except (e2_closure.ClosureError, evidence.EvidenceError) as exc:
            raise PromotionError(
                "E2 effective stock rootfs closure is incomplete"
            ) from exc
    identities = {
        "ap": exact_identity(artifacts.get("ap_tar_md5"), "candidate AP"),
        "candidate_static": exact_identity(static_receipt, "candidate static result"),
        "image": exact_identity(build.get("image"), "candidate Image"),
        "boot_image": exact_identity(artifacts.get("boot_img"), "candidate boot"),
        "boot_img_lz4": exact_identity(
            artifacts.get("boot_img_lz4"), "candidate boot LZ4"
        ),
        "init": exact_identity(userspace.get("init"), "candidate init"),
        "child": exact_identity(userspace.get("child"), "candidate child"),
    }
    candidate_ap_identity = exact_identity(
        {name: ap_receipt.get(name) for name in ("size", "sha256")},
        "submitted candidate AP",
    )
    if identities["ap"] != candidate_ap_identity:
        raise PromotionError("P2.34 candidate AP changed after static verification")
    if profile == "E2" and ap_receipt.get("member") != {
        "name": "boot.img.lz4",
        **identities["boot_img_lz4"],
    }:
        raise PromotionError("E2 candidate AP boot member differs from static closure")
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
    candidate_ap_identity = exact_identity(
        {name: candidate_ap.get(name) for name in ("size", "sha256")},
        "submitted candidate AP",
    )
    run_id = candidate_contract["run_id"]
    profile = candidate_contract["profile"]
    source_contract_id = candidate_contract.get("source_contract_id")
    selected_decoder = evidence._latest_stage_decoder(
        source_contract_id, profile
    )
    model = selected_decoder.model
    run_manifest = {
        "schema": evidence.E1_LATEST_STAGE_RUN_MANIFEST_SCHEMA,
        "target": TARGET,
        "profile": profile,
        "run_id": run_id,
        "decoder": selected_decoder.DECODER_ID,
        "policy_id": selected_decoder.POLICY_ID,
        "records": {
            "long_family_hex": model.LONG_FAMILY.hex(),
            "unsat_family_hex": model.UNSAT_FAMILY.hex(),
            "terminal_stage": model.PROFILE_TERMINALS[profile],
        },
        "observation_contract": {
            "accepted_identity": f"{profile}_TERMINAL_SUCCESS_REACHED",
            "minimum_success_count": 1,
            "clean_baseline_required": True,
        },
        "candidate_ap": candidate_ap_identity,
        "candidate_static": static_receipt,
    }
    if source_contract_id is not None:
        run_manifest["source_contract_id"] = source_contract_id
    run_payload = canonical(run_manifest)
    static_result = {
        "schema": evidence.E1_LATEST_STAGE_STATIC_SCHEMA,
        "target": TARGET,
        "verdict": VERDICT,
        "profile": profile,
        "run_id": run_id,
        "decoder": selected_decoder.DECODER_ID,
        "policy_id": selected_decoder.POLICY_ID,
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
    if source_contract_id is not None:
        static_result["source_contract_id"] = source_contract_id
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
        ap_info, frame = boot_verify.parse_ap_tar_md5(ap_payload)
        if ap_info["member"]["name"] != "boot.img.lz4":
            raise PromotionError("P2.34 candidate AP is not boot-only")
        static_receipt = receipt(static_payload)
        ap_receipt = {
            **receipt(ap_payload),
            "member": {"name": "boot.img.lz4", **receipt(frame)},
        }
        run_payload, process_static = derive(
            static_result, static_receipt, ap_receipt
        )
        process_static_value = json.loads(process_static.decode("ascii"))
        if process_static_value.get("profile") == "E2":
            evidence.validate_e2_ap_payload(
                frame,
                {
                    **{
                        name: process_static_value["candidate"]["artifacts"][name]
                        for name in (
                            "boot_img_lz4",
                            "boot_image",
                            "image",
                            "init",
                            "child",
                        )
                    },
                    "run_id": process_static_value["run_id"],
                    "module_closure": static_result["candidate"]["module_closure"],
                    "effective_rootfs": static_result["candidate"][
                        "effective_rootfs"
                    ],
                    **(
                        {
                            "source_contract_id": process_static_value[
                                "source_contract_id"
                            ]
                        }
                        if process_static_value.get("source_contract_id")
                        is not None
                        else {}
                    ),
                },
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
        evidence.EvidenceError,
        static_checker.CheckError,
        boot_verify.BootVerifyError,
        OSError,
    ) as exc:
        print(f"P2.34 promotion error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
