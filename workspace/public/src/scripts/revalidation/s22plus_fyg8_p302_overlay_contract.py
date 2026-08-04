#!/usr/bin/env python3
"""Bind the inert P3.02-M0 carrier to the exact P3.01-r1 closure."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import stat
from typing import Any, Mapping

import s22plus_fyg8_p301_overlay_contract as parent_overlay
import s22plus_fyg8_p301_telemetry_decoder as decoder
import s22plus_fyg8_p301_telemetry_spec as spec
import s22plus_fyg8_p302_binary_carrier as binary_carrier
import s22plus_fyg8_p302_carrier_generator as generator


SCHEMA = "s22plus_fyg8_p302_userspace_overlay_contract_v1"
CONTRACT_ID = "s22plus-fyg8-p302-electrical-measurement-carrier-v1"
INTENT_SCHEMA = "s22plus_fyg8_p302_userspace_overlay_intent_v1"
INTENT_VERDICT = "PASS_P302_USERSPACE_OVERLAY_INTENT_HOST_ONLY"
CONTRACT_VERDICT = "PASS_P302_USERSPACE_OVERLAY_CONTRACT_HOST_ONLY"
USERSPACE_VERDICT = "PASS_P302_USERSPACE_TWO_BUILD_REPRO_HOST_ONLY"
TARGET = parent_overlay.TARGET
PROFILE = parent_overlay.PROFILE
PARENT_OVERLAY_CONTRACT_ID = parent_overlay.CONTRACT_ID
PARENT_SOURCE_CONTRACT_ID = parent_overlay.PARENT_SOURCE_CONTRACT_ID
PARENT_INTENT = parent_overlay.DEFAULT_INTENT
PARENT_PATCH = parent_overlay.PARENT_PATCH
PARENT_SOURCE = parent_overlay.PARENT_SOURCE
PARENT_IMAGE = parent_overlay.PARENT_IMAGE
PARENT_REPRO_RESULT = parent_overlay.PARENT_REPRO_RESULT
EXPECTED_IMAGE = parent_overlay.EXPECTED_IMAGE
DEFAULT_OUT = Path("workspace/private/outputs/s22plus_fyg8_p302/intent")
DEFAULT_INTENT = DEFAULT_OUT / "overlay-intent.json"
DEFAULT_MATERIALIZED = DEFAULT_OUT / "materialized-sources"

PREFIX = Path("workspace/public/src/scripts/revalidation")
SOURCE_PATHS = {
    "p302_binary_carrier": PREFIX / "s22plus_fyg8_p302_binary_carrier.py",
    "p302_carrier_generator": PREFIX / "s22plus_fyg8_p302_carrier_generator.py",
    "p302_overlay_contract": PREFIX / "s22plus_fyg8_p302_overlay_contract.py",
    "p302_overlay_intent": PREFIX / "s22plus_fyg8_p302_overlay_intent.py",
    "p302_candidate_contract": PREFIX / "s22plus_fyg8_p302_candidate_contract.py",
    "p302_userspace_build": PREFIX / "s22plus_fyg8_p302_userspace_build.py",
    "p302_boot_only_packager": PREFIX / "s22plus_fyg8_p302_boot_only_packager.py",
    "p302_candidate_builder": PREFIX / "build_s22plus_fyg8_p302_candidate.py",
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
        key: _read_regular(root / path, f"P3.02 SOURCE_KEY {key}")
        for key, path in sorted(SOURCE_PATHS.items())
    }
    if set(result) != SOURCE_KEYS:
        raise OverlayContractError("P3.02 SOURCE_KEYS differ")
    return result


def source_receipts(root: Path) -> dict[str, dict[str, Any]]:
    return {key: _receipt(value) for key, value in source_bytes(root).items()}


def verify_parent(root: Path) -> dict[str, Any]:
    try:
        value = parent_overlay.verify_intent(root, root / PARENT_INTENT)
    except (parent_overlay.OverlayContractError, OSError) as exc:
        raise OverlayContractError(str(exc)) from exc
    if (
        value.get("userspace_overlay_contract_id") != PARENT_OVERLAY_CONTRACT_ID
        or value.get("source_contract_id") != PARENT_SOURCE_CONTRACT_ID
        or value.get("profile") != PROFILE
        or value.get("fixed_image", {}).get("sha256") != EXPECTED_IMAGE["sha256"]
        or value.get("verified") is not True
    ):
        raise OverlayContractError("P3.02 parent P3.01-r1 contract differs")
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
        "parent_overlay_contract_id": PARENT_OVERLAY_CONTRACT_ID,
        "parent_source_contract_id": PARENT_SOURCE_CONTRACT_ID,
        "parent_overlay_contract": parent,
        "parent_overlay_intent": {
            "path": PARENT_INTENT.as_posix(),
            **_receipt(_read_regular(root / PARENT_INTENT, "P3.02 parent overlay intent")),
        },
        "fixed_image": {"path": PARENT_IMAGE.as_posix(), **EXPECTED_IMAGE},
        "source_keys": sorted(SOURCE_KEYS),
        "source_receipts": source_receipts(root),
        "generated_artifacts": {
            key: _receipt(data) for key, data in sorted(generated.items())
        },
        "carrier": {
            "id": binary_carrier.CARRIER_ID,
            "section": binary_carrier.SECTION,
            "execution_delta": "nonalloc_elf_identity_section_only",
            "p301_delta_keys": sorted(generator.P301_DELTA_KEYS),
        },
        "telemetry": parent["telemetry"],
        "safety": {
            "host_only": True,
            "fixed_kernel_image": True,
            "kernel_rebuild": False,
            "full_lto_ab": False,
            "module_binaries_injected": 0,
            "device_contact": False,
            "live_authorized": False,
        },
    }
    if (
        value["telemetry"].get("schema") != spec.SCHEMA
        or value["telemetry"].get("decoder_id") != decoder.DECODER_ID
        or value["telemetry"].get("decoder_policy_id") != decoder.POLICY_ID
    ):
        raise OverlayContractError("P3.02 inherited telemetry identity differs")
    value["intent_sha256"] = hashlib.sha256(_canonical(value)).hexdigest()
    return value


def verify_intent(root: Path, intent_path: Path) -> dict[str, Any]:
    payload = _read_regular(intent_path, "P3.02 overlay intent")
    try:
        value = json.loads(payload.decode("ascii"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise OverlayContractError("P3.02 overlay intent is not ASCII JSON") from exc
    if not isinstance(value, dict):
        raise OverlayContractError("P3.02 overlay intent root differs")
    expected = create_intent_value(root)
    if value != expected:
        raise OverlayContractError("P3.02 overlay intent content differs")
    generated = generated_bytes(root, value["parent_overlay_contract"])
    for key, relative in generator.artifact_paths().items():
        actual = _read_regular(
            intent_path.parent / relative,
            f"P3.02 materialized {key}",
            4 * 1024 * 1024,
        )
        if actual != generated[key]:
            raise OverlayContractError(f"P3.02 materialized source differs: {key}")
    parent_candidate = value["parent_overlay_contract"]["parent_candidate_contract"]
    return {
        "schema": SCHEMA,
        "verdict": CONTRACT_VERDICT,
        "contract_id": CONTRACT_ID,
        "target": TARGET,
        "profile": PROFILE,
        "profile_number": parent_candidate["profile_number"],
        "run_id": value["run_id"],
        "unsat_tag_hex": value["unsat_tag_hex"],
        "source_contract_id": PARENT_SOURCE_CONTRACT_ID,
        "userspace_overlay_contract_id": CONTRACT_ID,
        "parent_overlay_contract_id": PARENT_OVERLAY_CONTRACT_ID,
        "parent_overlay_contract": value["parent_overlay_contract"],
        "parent_candidate_contract": parent_candidate,
        "overlay_intent": _receipt(payload),
        "overlay_intent_sha256": value["intent_sha256"],
        "source_receipts": value["source_receipts"],
        "generated_artifacts": value["generated_artifacts"],
        "fixed_image": value["fixed_image"],
        "carrier": value["carrier"],
        "telemetry": value["telemetry"],
        "verified": True,
        "safety": value["safety"],
    }
