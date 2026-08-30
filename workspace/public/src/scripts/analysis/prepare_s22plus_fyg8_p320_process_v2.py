#!/usr/bin/env python3
"""Promote the P3.20 H0 candidate-static result into offline evidence.

This step creates only private, immutable contract files.  It does not create
F1 approval, contact a device, invoke Odin, or transfer an artifact.
"""

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
import s22plus_fyg8_p320_process_v2_candidate_static as candidate_static  # noqa: E402
import s22plus_fyg8_p320_stock_candidate_build as candidate_build  # noqa: E402


SCHEMA = "s22plus_fyg8_p320_process_v2_promotion_v1"
VERDICT = "PASS_P320_PROCESS_V2_PROMOTION_HOST_ONLY"
DEFAULT_CANDIDATE_STATIC = candidate_static.DEFAULT_OUTPUT
DEFAULT_CANDIDATE_AP = candidate_build.DEFAULT_OUTPUT_ROOT / "candidate-a/odin4/AP.tar.md5"
DEFAULT_OUTPUT = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p320/"
    "process-v2-promotion-20260830-03"
)


class PromotionError(ValueError):
    pass


def canonical(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
    except (TypeError, ValueError, UnicodeError) as exc:
        raise PromotionError("P3.20 promotion value is not canonical JSON") from exc


def identity(payload: bytes) -> dict[str, Any]:
    return {"size": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}


def relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError as exc:
        raise PromotionError("P3.20 promotion path escaped the repository") from exc


def stable_bytes(
    path: Path,
    label: str,
    maximum: int,
    *,
    mode: int | None = None,
    nlink: int | None = None,
) -> bytes:
    direct = path.absolute()
    try:
        before = direct.lstat()
        resolved = direct.resolve(strict=True)
        with direct.open("rb") as stream:
            payload = stream.read(maximum + 1)
            inside = os.fstat(stream.fileno())
        after = direct.lstat()
    except OSError as exc:
        raise PromotionError(f"{label} is unavailable") from exc
    before_id = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
    if (
        direct != resolved
        or stat.S_ISLNK(before.st_mode)
        or not stat.S_ISREG(before.st_mode)
        or before.st_nlink != 1
        or before_id != (inside.st_dev, inside.st_ino, inside.st_size, inside.st_mtime_ns)
        or before_id != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
        or len(payload) != before.st_size
        or len(payload) > maximum
        or (mode is not None and stat.S_IMODE(before.st_mode) != mode)
        or (nlink is not None and before.st_nlink != nlink)
    ):
        raise PromotionError(f"{label} identity differs")
    return payload


def decode(payload: bytes, label: str) -> dict[str, Any]:
    try:
        value = json.loads(
            payload.decode("ascii"),
            object_pairs_hook=lambda pairs: _unique_pairs(pairs, label),
        )
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise PromotionError(f"{label} is not strict JSON") from exc
    if not isinstance(value, dict):
        raise PromotionError(f"{label} is not an object")
    return value


def _unique_pairs(pairs: list[tuple[str, Any]], label: str) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise PromotionError(f"{label} has a duplicate key")
        value[key] = item
    return value


def _payloads(
    static_value: dict[str, Any],
    static_payload: bytes,
    ap_receipt: dict[str, Any],
) -> dict[str, bytes]:
    candidate = static_value["candidate"]
    static_identity = identity(static_payload)
    candidate_ap = {name: ap_receipt[name] for name in ("size", "sha256")}
    records = {
        "long_family_hex": evidence.p320_stock_adapter.LONG_FAMILY.hex(),
        "unsat_family_hex": evidence.p320_stock_adapter.UNSAT_FAMILY.hex(),
        "terminal_stage": evidence.p320_stock_adapter.TERMINAL_STAGE,
    }
    run_manifest = {
        "schema": evidence.P320_RUN_MANIFEST_SCHEMA,
        "target": evidence.PID1_USERSPACE_TARGET,
        "profile": evidence.p320_stock_adapter.PROFILE,
        "run_id": evidence.P320_RUN_ID,
        "decoder": evidence.p320_stock_adapter.DECODER_ID,
        "policy_id": evidence.p320_stock_adapter.POLICY_ID,
        "records": records,
        "observation_contract": {
            "accepted_identity": "P320_STOCK_OBSERVER_V4_RETAINED",
            "minimum_success_count": 1,
            "clean_baseline_required": True,
            "runtime_values_preflighted": False,
            "complete_is_noncausal": True,
            "incomplete_result": "NO_PROOF_EXPERIMENT_PRECONDITION",
            "receipt_result": "NO_PROOF_OBSERVER",
        },
        "candidate_ap": candidate_ap,
        "candidate_static": static_identity,
        "source_contract_id": evidence.p320_stock_adapter.PARENT_SOURCE_CONTRACT_ID,
        "userspace_overlay_contract_id": evidence.P320_STOCK_OVERLAY_CONTRACT_ID,
    }
    run_payload = canonical(run_manifest)
    static_result = {
        "schema": evidence.P320_STATIC_RESULT_SCHEMA,
        "target": evidence.PID1_USERSPACE_TARGET,
        "verdict": evidence.P320_STATIC_RESULT_VERDICT,
        "profile": evidence.p320_stock_adapter.PROFILE,
        "run_id": evidence.P320_RUN_ID,
        "decoder": evidence.p320_stock_adapter.DECODER_ID,
        "policy_id": evidence.p320_stock_adapter.POLICY_ID,
        "source_contract_id": evidence.p320_stock_adapter.PARENT_SOURCE_CONTRACT_ID,
        "userspace_overlay_contract_id": evidence.P320_STOCK_OVERLAY_CONTRACT_ID,
        "run_binding": {
            "canonical_manifest_size": len(run_payload),
            "canonical_manifest_sha256": hashlib.sha256(run_payload).hexdigest(),
            "verified": True,
        },
        "candidate": {
            "artifacts": {
                "ap": candidate_ap,
                "candidate_static": static_identity,
                "boot_image": candidate["a"]["boot_img"],
                "boot_img_lz4": candidate["a"]["boot_img_lz4"],
                "image": static_value["builder_closure"]["inputs"]["fixed-Image"],
                "init": candidate["userspace"]["a"]["init"],
                "child": candidate["userspace"]["a"]["child"],
                "latch": static_value["builder_closure"]["module_bytes"][
                    "s22plus_dwc3_event_latch.ko"
                ],
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
    return {
        "candidate_static": static_payload,
        "run_manifest": canonical(run_manifest),
        "static_check": canonical(static_result),
    }


def acceptance(output: Path, payloads: dict[str, bytes]) -> dict[str, Any]:
    names = {
        "candidate_static": "candidate-static.json",
        "run_manifest": "run-manifest.json",
        "static_check": "static-check-result.json",
    }
    contract = {
        name: {"path": relative(output / filename), **identity(payloads[name])}
        for name, filename in names.items()
    }
    value = evidence.p320_stock_adapter.acceptance_fixture()
    value["contract"] = contract
    try:
        evidence.validate_acceptance(value)
    except evidence.EvidenceError as exc:
        raise PromotionError(str(exc)) from exc
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
        raise PromotionError("P3.20 promotion output already exists")
    output.mkdir(mode=0o700, parents=True)
    for name, filename in {
        "candidate_static": "candidate-static.json",
        "run_manifest": "run-manifest.json",
        "static_check": "static-check-result.json",
    }.items():
        path = output / filename
        descriptor = os.open(
            path,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
            0o400,
        )
        try:
            os.fchmod(descriptor, 0o400)
            payload = payloads[name]
            if os.write(descriptor, payload) != len(payload):
                raise PromotionError("P3.20 promotion write was short")
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    descriptor = os.open(output, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def build(
    candidate_static_path: Path = DEFAULT_CANDIDATE_STATIC,
    candidate_ap_path: Path = DEFAULT_CANDIDATE_AP,
    output: Path = DEFAULT_OUTPUT,
) -> tuple[dict[str, bytes], dict[str, Any]]:
    static_payload = stable_bytes(
        candidate_static_path,
        "P3.20 candidate-static",
        2 * 1024 * 1024,
        mode=0o400,
        nlink=1,
    )
    static_value = decode(static_payload, "P3.20 candidate-static")
    try:
        candidate_static.validate_result(static_value)
    except candidate_static.StaticContractError as exc:
        raise PromotionError(str(exc)) from exc
    ap_payload = stable_bytes(candidate_ap_path, "P3.20 candidate AP", 64 * 1024 * 1024)
    try:
        ap_info, frame = boot_verify.parse_ap_tar_md5(ap_payload)
    except boot_verify.BootVerifyError as exc:
        raise PromotionError("P3.20 candidate AP is invalid") from exc
    if ap_info["member"]["name"] != "boot.img.lz4":
        raise PromotionError("P3.20 candidate AP is not boot-only")
    ap_receipt = {
        **identity(ap_payload),
        "member": {"name": "boot.img.lz4", **identity(frame)},
    }
    expected = static_value["candidate"]["a"]["ap_tar_md5"]
    if {name: ap_receipt[name] for name in ("size", "sha256")} != expected:
        raise PromotionError("P3.20 candidate AP differs from candidate-static")
    payloads = _payloads(static_value, static_payload, ap_receipt)
    verification = verify(output, payloads, ap_receipt)
    try:
        evidence.validate_e2_ap_payload(frame, verification["ap_payload_closure"])
    except evidence.EvidenceError as exc:
        raise PromotionError(str(exc)) from exc
    return payloads, verification


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-static", type=Path, default=DEFAULT_CANDIDATE_STATIC)
    parser.add_argument("--candidate-ap", type=Path, default=DEFAULT_CANDIDATE_AP)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--audit-only", action="store_true")
    args = parser.parse_args(argv)
    paths = [
        path if path.is_absolute() else ROOT / path
        for path in (args.candidate_static, args.candidate_ap, args.out)
    ]
    try:
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
    except (OSError, PromotionError, RuntimeError) as exc:
        print(json.dumps({"schema": SCHEMA, "verdict": "FAIL_CLOSED", "error": str(exc)}, sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
