#!/usr/bin/env python3
"""Promote the reviewed P3.19 candidate-static artifact into offline evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[5]
ANALYSIS = ROOT / "workspace/public/src/scripts/analysis"
REVALIDATION = ROOT / "workspace/public/src/scripts/revalidation"
for directory in (ANALYSIS, REVALIDATION):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))

import device_action_f1_evidence_v2 as evidence  # noqa: E402
import s22plus_boot_verify as boot_verify  # noqa: E402
import s22plus_fyg8_p319_process_v2_candidate_static as candidate_static  # noqa: E402


SCHEMA = "s22plus_fyg8_p319_process_v2_promotion_v1"
VERDICT = evidence.E1_LATEST_STAGE_STATIC_VERDICT
DEFAULT_CANDIDATE_STATIC = candidate_static.DEFAULT_OUTPUT
DEFAULT_CANDIDATE_AP = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p319/"
    "stock-witness-runtime-v1-20260821-55/candidate-a/odin4/AP.tar.md5"
)
DEFAULT_OUTPUT = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p319/"
    "process-v2-promotion-20260830-11"
)


class PromotionError(ValueError):
    pass


def canonical(value: Any) -> bytes:
    try:
        return json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
    except (TypeError, ValueError, UnicodeError) as exc:
        raise PromotionError("P3.19 promotion value is not canonical JSON") from exc


def identity(data: bytes) -> dict[str, Any]:
    return {"size": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError as exc:
        raise PromotionError("P3.19 promotion path is outside the repository") from exc


def stable_bytes(path: Path, label: str, maximum: int) -> bytes:
    try:
        before = path.lstat()
        if stat.S_ISLNK(before.st_mode) or not stat.S_ISREG(before.st_mode):
            raise PromotionError(f"{label} is not a direct regular file")
        if stat.S_IMODE(before.st_mode) != 0o400 or before.st_nlink != 1:
            raise PromotionError(f"{label} metadata differs")
        with path.open("rb") as stream:
            data = stream.read(maximum + 1)
            inside = os.fstat(stream.fileno())
        after = path.lstat()
    except OSError as exc:
        raise PromotionError(f"{label} is unavailable") from exc
    before_id = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
    if (
        before_id
        != (inside.st_dev, inside.st_ino, inside.st_size, inside.st_mtime_ns)
        or before_id
        != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
        or len(data) != before.st_size
        or len(data) > maximum
    ):
        raise PromotionError(f"{label} changed while reading")
    return data


def decode(data: bytes, label: str) -> dict[str, Any]:
    try:
        value = json.loads(data.decode("ascii"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise PromotionError(f"{label} is not JSON") from exc
    if not isinstance(value, dict):
        raise PromotionError(f"{label} is not an object")
    return value


def derive(
    static_value: dict[str, Any],
    static_receipt: dict[str, Any],
    ap_receipt: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    evidence._validate_p319_candidate_static(static_value)  # noqa: SLF001
    if (
        ap_receipt.get("size")
        != evidence.P319_EXACT_ARTIFACTS["ap_tar_md5"]["size"]
        or ap_receipt.get("sha256")
        != evidence.P319_EXACT_ARTIFACTS["ap_tar_md5"]["sha256"]
        or ap_receipt.get("member")
        != {
            "name": "boot.img.lz4",
            **evidence.P319_EXACT_ARTIFACTS["boot_img_lz4"],
        }
    ):
        raise PromotionError("P3.19 candidate AP differs from candidate-static")
    runtime_names = sorted(
        static_value["runtime_observation_contract"]["witnesses"]
    )
    run_manifest = {
        "schema": evidence.E1_LATEST_STAGE_RUN_MANIFEST_SCHEMA,
        "target": evidence.PID1_USERSPACE_TARGET,
        "profile": evidence.p319_stock_adapter.PROFILE,
        "run_id": evidence.P319_RUN_ID,
        "decoder": evidence.p319_stock_adapter.DECODER_ID,
        "policy_id": evidence.p319_stock_adapter.POLICY_ID,
        "records": {
            "long_family_hex": evidence.p319_stock_adapter.LONG_FAMILY.hex(),
            "unsat_family_hex": evidence.p319_stock_adapter.UNSAT_FAMILY.hex(),
            "terminal_stage": evidence.p319_stock_adapter.TERMINAL_STAGE,
        },
        "observation_contract": {
            "accepted_identity": "P319_STOCK_WITNESS_RETAINED",
            "minimum_success_count": 1,
            "clean_baseline_required": True,
            "runtime_witnesses_required": runtime_names,
            "runtime_values_preflighted": False,
            "complete_is_noncausal": True,
        },
        "candidate_ap": {
            name: ap_receipt[name] for name in ("size", "sha256")
        },
        "candidate_static": static_receipt,
        "source_contract_id": evidence.p319_stock_adapter.PARENT_SOURCE_CONTRACT_ID,
        "userspace_overlay_contract_id": evidence.P319_STOCK_OVERLAY_CONTRACT_ID,
    }
    run_payload = canonical(run_manifest)
    static_result = {
        "schema": evidence.E1_LATEST_STAGE_STATIC_SCHEMA,
        "target": evidence.PID1_USERSPACE_TARGET,
        "verdict": evidence.E1_LATEST_STAGE_STATIC_VERDICT,
        "profile": evidence.p319_stock_adapter.PROFILE,
        "run_id": evidence.P319_RUN_ID,
        "decoder": evidence.p319_stock_adapter.DECODER_ID,
        "policy_id": evidence.p319_stock_adapter.POLICY_ID,
        "source_contract_id": evidence.p319_stock_adapter.PARENT_SOURCE_CONTRACT_ID,
        "userspace_overlay_contract_id": evidence.P319_STOCK_OVERLAY_CONTRACT_ID,
        "run_binding": {
            "canonical_manifest_size": len(run_payload),
            "canonical_manifest_sha256": hashlib.sha256(run_payload).hexdigest(),
            "verified": True,
        },
        "candidate": {
            "artifacts": {
                "ap": evidence.P319_EXACT_ARTIFACTS["ap_tar_md5"],
                "candidate_static": static_receipt,
                "boot_image": evidence.P319_EXACT_ARTIFACTS["boot_img"],
                "boot_img_lz4": evidence.P319_EXACT_ARTIFACTS["boot_img_lz4"],
                "image": evidence.P319_EXACT_ARTIFACTS["image"],
                "init": evidence.P319_EXACT_ARTIFACTS["init"],
                "child": evidence.P319_EXACT_ARTIFACTS["child"],
                "latch": evidence.P319_EXACT_ARTIFACTS["latch"],
            },
            "boot_only_ap": True,
            "independent_static_contract": True,
            "complete_is_noncausal": True,
            "runtime_values_observed": False,
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
            "causal_result_allowed": False,
            "candidate_success": False,
        },
    }
    return run_manifest, static_result


def acceptance(
    output: Path,
    payloads: dict[str, bytes],
) -> dict[str, Any]:
    contract = {
        name: {
            "path": relative(output / filename),
            **identity(payloads[name]),
        }
        for name, filename in {
            "candidate_static": "candidate-static.json",
            "run_manifest": "run-manifest.json",
            "static_check": "static-check-result.json",
        }.items()
    }
    value = evidence.p319_stock_adapter.acceptance_fixture()
    value["contract"] = contract
    evidence.validate_acceptance(value)
    return value


def verify(
    output: Path,
    payloads: dict[str, bytes],
    ap_receipt: dict[str, Any],
) -> dict[str, Any]:
    receipts = {name: identity(payload) for name, payload in payloads.items()}
    try:
        return evidence.verify_offline_contract(
            acceptance(output, payloads),
            payloads=payloads,
            receipts=receipts,
            candidate_ap=ap_receipt,
        )
    except evidence.EvidenceError as exc:
        raise PromotionError(str(exc)) from exc


def publish(output: Path, payloads: dict[str, bytes]) -> None:
    if output.exists() or output.is_symlink():
        raise PromotionError("P3.19 promotion output already exists")
    output.mkdir(mode=0o700, parents=True)
    for name, filename in {
        "candidate_static": "candidate-static.json",
        "run_manifest": "run-manifest.json",
        "static_check": "static-check-result.json",
    }.items():
        path = output / filename
        descriptor = os.open(
            path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o400
        )
        try:
            os.fchmod(descriptor, 0o400)
            offset = 0
            while offset < len(payloads[name]):
                written = os.write(descriptor, payloads[name][offset:])
                if written <= 0:
                    raise PromotionError("P3.19 promotion write was short")
                offset += written
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    directory = os.open(output, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def build(
    candidate_static_path: Path = DEFAULT_CANDIDATE_STATIC,
    candidate_ap_path: Path = DEFAULT_CANDIDATE_AP,
    output: Path = DEFAULT_OUTPUT,
) -> tuple[dict[str, bytes], dict[str, Any]]:
    static_payload = stable_bytes(
        candidate_static_path, "P3.19 candidate-static", 2 * 1024 * 1024
    )
    static_value = decode(static_payload, "P3.19 candidate-static")
    static_receipt = identity(static_payload)
    ap_payload = stable_bytes(
        candidate_ap_path, "P3.19 candidate AP", 64 * 1024 * 1024
    )
    try:
        ap_info, frame = boot_verify.parse_ap_tar_md5(ap_payload)
    except boot_verify.BootVerifyError as exc:
        raise PromotionError("P3.19 candidate AP is invalid") from exc
    if ap_info["member"]["name"] != "boot.img.lz4":
        raise PromotionError("P3.19 candidate AP is not boot-only")
    ap_receipt = {
        **identity(ap_payload),
        "member": {"name": "boot.img.lz4", **identity(frame)},
    }
    run_manifest, static_result = derive(
        static_value, static_receipt, ap_receipt
    )
    payloads = {
        "candidate_static": static_payload,
        "run_manifest": canonical(run_manifest),
        "static_check": canonical(static_result),
    }
    verification = verify(output, payloads, ap_receipt)
    evidence.validate_e2_ap_payload(frame, verification["ap_payload_closure"])
    return payloads, verification


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-static", type=Path, default=DEFAULT_CANDIDATE_STATIC)
    parser.add_argument("--candidate-ap", type=Path, default=DEFAULT_CANDIDATE_AP)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--audit-only", action="store_true")
    args = parser.parse_args(argv)
    try:
        paths = [
            path if path.is_absolute() else ROOT / path
            for path in (args.candidate_static, args.candidate_ap, args.out)
        ]
        payloads, verification = build(paths[0], paths[1], paths[2])
        if not args.audit_only:
            publish(paths[2], payloads)
        print(
            json.dumps(
                {
                    "schema": SCHEMA,
                    "verdict": VERDICT,
                    "artifacts": {name: identity(data) for name, data in payloads.items()},
                    "offline_contract": verification,
                    "created": not args.audit_only,
                    "device_contact": False,
                    "ready_manifest_created": False,
                    "live_authorized": False,
                },
                sort_keys=True,
            )
        )
        return 0
    except (PromotionError, OSError) as exc:
        print(f"P3.19 promotion error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
