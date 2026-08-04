#!/usr/bin/env python3
"""Bind P3.01 userspace to the exact already-qualified P3.00 Image contract."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import stat
from typing import Any, Mapping

import s22plus_fyg8_p300_candidate_contract as parent_contract
import s22plus_fyg8_p301_telemetry_decoder as decoder
import s22plus_fyg8_p301_telemetry_generator as generator
import s22plus_fyg8_p301_telemetry_spec as spec


SCHEMA = "s22plus_fyg8_p301_userspace_overlay_contract_v1"
CONTRACT_ID = "s22plus-fyg8-p301-device-event-subtype-userspace-overlay-v1"
INTENT_SCHEMA = "s22plus_fyg8_p301_userspace_overlay_intent_v1"
INTENT_VERDICT = "PASS_P301_USERSPACE_OVERLAY_INTENT_HOST_ONLY"
CONTRACT_VERDICT = "PASS_P301_USERSPACE_OVERLAY_CONTRACT_HOST_ONLY"
USERSPACE_VERDICT = "PASS_P301_USERSPACE_TWO_BUILD_REPRO_HOST_ONLY"
TARGET = parent_contract.TARGET
PROFILE = spec.PROFILE
PARENT_SOURCE_CONTRACT_ID = "s22plus-fyg8-p300-event-ingress-irq-attribution-v1"
PARENT_INTENT = parent_contract.DEFAULT_INTENT
PARENT_PATCH = parent_contract.DEFAULT_PATCH
PARENT_SOURCE = parent_contract.DEFAULT_SOURCE
PARENT_IMAGE = Path(
    "workspace/private/outputs/s22plus_fyg8_p300/"
    "full-lto-e324abae-v1/artifacts-a/Image"
)
PARENT_REPRO_RESULT = Path(
    "workspace/private/outputs/s22plus_fyg8_p300/"
    "full-lto-e324abae-v1/postbuild-repro-check-fresh.json"
)
EXPECTED_IMAGE = {
    "size": 41490944,
    "sha256": "01457240881b432f725b0f2d795813c38ef7cca4365633f9b0fc7c3a62744a3f",
}
DEFAULT_OUT = Path("workspace/private/outputs/s22plus_fyg8_p301_r1/intent")
DEFAULT_INTENT = DEFAULT_OUT / "overlay-intent.json"
DEFAULT_MATERIALIZED = DEFAULT_OUT / "materialized-sources"

PREFIX = Path("workspace/public/src/scripts/revalidation")
SOURCE_PATHS = {
    "p301_telemetry_spec": PREFIX / "s22plus_fyg8_p301_telemetry_spec.py",
    "p301_telemetry_transform": PREFIX / "s22plus_fyg8_p301_telemetry_transform.py",
    "p301_telemetry_generator": PREFIX / "s22plus_fyg8_p301_telemetry_generator.py",
    "p301_overlay_contract": PREFIX / "s22plus_fyg8_p301_overlay_contract.py",
    "p301_overlay_intent": PREFIX / "s22plus_fyg8_p301_overlay_intent.py",
    "p301_candidate_contract": PREFIX / "s22plus_fyg8_p301_candidate_contract.py",
    "p301_userspace_build": PREFIX / "s22plus_fyg8_p301_userspace_build.py",
    "p301_boot_only_packager": PREFIX / "s22plus_fyg8_p301_boot_only_packager.py",
    "p301_candidate_builder": PREFIX / "build_s22plus_fyg8_p301_candidate.py",
}
SOURCE_KEYS = frozenset(SOURCE_PATHS)


class OverlayContractError(ValueError):
    pass


def _receipt(data: bytes) -> dict[str, Any]:
    return {"size": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def _canonical(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            indent=2,
            ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
        + b"\n"
    )


def _read_regular(path: Path, label: str, maximum: int = 32 * 1024 * 1024) -> bytes:
    try:
        metadata = path.lstat()
    except FileNotFoundError as exc:
        raise OverlayContractError(f"{label} is missing") from exc
    if path.is_symlink() or not stat.S_ISREG(metadata.st_mode):
        raise OverlayContractError(f"{label} is indirect or not regular")
    if metadata.st_size <= 0 or metadata.st_size > maximum:
        raise OverlayContractError(f"{label} size is invalid")
    data = path.read_bytes()
    after = path.stat()
    if (
        len(data) != metadata.st_size
        or after.st_dev != metadata.st_dev
        or after.st_ino != metadata.st_ino
        or after.st_size != metadata.st_size
        or after.st_mtime_ns != metadata.st_mtime_ns
    ):
        raise OverlayContractError(f"{label} changed while reading")
    return data


def source_bytes(root: Path) -> dict[str, bytes]:
    result = {
        key: _read_regular(root / path, f"P3.01 SOURCE_KEY {key}")
        for key, path in sorted(SOURCE_PATHS.items())
    }
    if set(result) != SOURCE_KEYS:
        raise OverlayContractError("P3.01 SOURCE_KEYS differ")
    return result


def source_receipts(root: Path) -> dict[str, dict[str, Any]]:
    return {key: _receipt(value) for key, value in source_bytes(root).items()}


def verify_parent(root: Path) -> dict[str, Any]:
    try:
        value = parent_contract.verify(
            root,
            root / PARENT_SOURCE,
            root / PARENT_INTENT,
            root / PARENT_PATCH,
        )
    except (parent_contract.ContractError, OSError) as exc:
        raise OverlayContractError(str(exc)) from exc
    if (
        value.get("source_contract_id") != PARENT_SOURCE_CONTRACT_ID
        or value.get("profile") != PROFILE
        or value.get("verified") is not True
    ):
        raise OverlayContractError("P3.01 parent P3.00 contract differs")
    image = _read_regular(root / PARENT_IMAGE, "P3.01 fixed P3.00 Image", 64 * 1024 * 1024)
    if _receipt(image) != EXPECTED_IMAGE:
        raise OverlayContractError("P3.01 fixed P3.00 Image receipt differs")
    return value


def generated_bytes(root: Path, parent: Mapping[str, Any]) -> dict[str, bytes]:
    return generator.generate_bytes(
        root,
        run_id=bytes.fromhex(str(parent["run_id"])),
        unsat_tag=bytes.fromhex(str(parent["unsat_tag_hex"])),
        profile=str(parent["profile"]),
    )


def create_intent_value(root: Path) -> dict[str, Any]:
    parent = verify_parent(root)
    generated = generated_bytes(root, parent)
    value = {
        "schema": INTENT_SCHEMA,
        "verdict": INTENT_VERDICT,
        "contract_id": CONTRACT_ID,
        "target": TARGET,
        "profile": PROFILE,
        "run_id": parent["run_id"],
        "unsat_tag_hex": parent["unsat_tag_hex"],
        "parent_source_contract_id": PARENT_SOURCE_CONTRACT_ID,
        "parent_candidate_contract": parent,
        "parent_intent": {
            "path": PARENT_INTENT.as_posix(),
            **_receipt(_read_regular(root / PARENT_INTENT, "P3.01 parent intent")),
        },
        "fixed_image": {"path": PARENT_IMAGE.as_posix(), **EXPECTED_IMAGE},
        "source_keys": sorted(SOURCE_KEYS),
        "source_receipts": source_receipts(root),
        "generated_artifacts": {
            key: _receipt(data) for key, data in sorted(generated.items())
        },
        "telemetry": {
            "schema": spec.SCHEMA,
            "descriptor_sha256": spec.descriptor_sha256(),
            "decoder_id": decoder.DECODER_ID,
            "decoder_policy_id": decoder.POLICY_ID,
            "a_ordinal": 105,
            "a_outcome": spec.OUTCOME_PROGRESS,
            "unknown_subtype_detail": spec.UNKNOWN_SUBTYPE_DETAIL,
        },
        "safety": {
            "host_only": True,
            "fixed_kernel_image": True,
            "kernel_rebuild": False,
            "full_lto_ab": False,
            "device_contact": False,
            "live_authorized": False,
        },
    }
    value["intent_sha256"] = hashlib.sha256(_canonical(value)).hexdigest()
    return value


def verify_intent(root: Path, intent_path: Path) -> dict[str, Any]:
    payload = _read_regular(intent_path, "P3.01 overlay intent")
    try:
        value = json.loads(payload.decode("ascii"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise OverlayContractError("P3.01 overlay intent is not ASCII JSON") from exc
    if not isinstance(value, dict):
        raise OverlayContractError("P3.01 overlay intent root differs")
    expected = create_intent_value(root)
    if value != expected:
        raise OverlayContractError("P3.01 overlay intent content differs")
    generated = generated_bytes(root, value["parent_candidate_contract"])
    for key, relative in generator.artifact_paths().items():
        actual = _read_regular(
            intent_path.parent / relative,
            f"P3.01 materialized {key}",
            4 * 1024 * 1024,
        )
        if actual != generated[key]:
            raise OverlayContractError(f"P3.01 materialized source differs: {key}")
    return {
        "schema": SCHEMA,
        "verdict": CONTRACT_VERDICT,
        "contract_id": CONTRACT_ID,
        "target": TARGET,
        "profile": PROFILE,
        "profile_number": value["parent_candidate_contract"]["profile_number"],
        "run_id": value["run_id"],
        "unsat_tag_hex": value["unsat_tag_hex"],
        "source_contract_id": PARENT_SOURCE_CONTRACT_ID,
        "userspace_overlay_contract_id": CONTRACT_ID,
        "parent_candidate_contract": value["parent_candidate_contract"],
        "overlay_intent": _receipt(payload),
        "overlay_intent_sha256": value["intent_sha256"],
        "source_receipts": value["source_receipts"],
        "generated_artifacts": value["generated_artifacts"],
        "fixed_image": value["fixed_image"],
        "telemetry": value["telemetry"],
        "verified": True,
        "safety": value["safety"],
    }
