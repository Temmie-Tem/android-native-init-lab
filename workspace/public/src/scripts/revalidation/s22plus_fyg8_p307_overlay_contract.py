#!/usr/bin/env python3
"""Bind the P3.07 EUD and QSCRATCH observer overlay."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

import s22plus_fyg8_p305_overlay_contract as parent
import s22plus_fyg8_p307_generator as generator
import s22plus_fyg8_p307_qscratch_audit as qscratch_audit
import s22plus_fyg8_p307_telemetry_spec as telemetry


SCHEMA = "s22plus_fyg8_p307_userspace_overlay_contract_v1"
CONTRACT_ID = "s22plus-fyg8-p307-eud-qscratch-observer-v1"
INTENT_SCHEMA = "s22plus_fyg8_p307_userspace_overlay_intent_v1"
INTENT_VERDICT = "PASS_P307_USERSPACE_OVERLAY_INTENT_HOST_ONLY"
CONTRACT_VERDICT = "PASS_P307_USERSPACE_OVERLAY_CONTRACT_HOST_ONLY"
USERSPACE_VERDICT = "PASS_P307_USERSPACE_TWO_BUILD_REPRO_HOST_ONLY"
TARGET = parent.TARGET
PROFILE = parent.PROFILE
PARENT_OVERLAY_CONTRACT_ID = parent.CONTRACT_ID
PARENT_SOURCE_CONTRACT_ID = parent.PARENT_SOURCE_CONTRACT_ID
PARENT_INTENT = parent.DEFAULT_INTENT
PARENT_PATCH = parent.PARENT_PATCH
PARENT_SOURCE = parent.PARENT_SOURCE
PARENT_IMAGE = parent.PARENT_IMAGE
PARENT_REPRO_RESULT = parent.PARENT_REPRO_RESULT
EXPECTED_IMAGE = parent.EXPECTED_IMAGE
DEFAULT_OUT = Path("workspace/private/outputs/s22plus_fyg8_p307/intent")
DEFAULT_INTENT = DEFAULT_OUT / "overlay-intent.json"
DEFAULT_MATERIALIZED = DEFAULT_OUT / "materialized-sources"

PREFIX = Path("workspace/public/src/scripts/revalidation")
SOURCE_PATHS = {
    "p307_telemetry_spec": PREFIX / "s22plus_fyg8_p307_telemetry_spec.py",
    "p307_qscratch_audit": PREFIX / "s22plus_fyg8_p307_qscratch_audit.py",
    "p307_runtime_transform": PREFIX / "s22plus_fyg8_p307_runtime_transform.py",
    "p307_generator": PREFIX / "s22plus_fyg8_p307_generator.py",
    "p307_telemetry_decoder": PREFIX / "s22plus_fyg8_p307_telemetry_decoder.py",
    "p307_overlay_contract": PREFIX / "s22plus_fyg8_p307_overlay_contract.py",
    "p307_overlay_intent": PREFIX / "s22plus_fyg8_p307_overlay_intent.py",
    "p307_candidate_contract": PREFIX / "s22plus_fyg8_p307_candidate_contract.py",
    "p307_userspace_build": PREFIX / "s22plus_fyg8_p307_userspace_build.py",
    "p307_candidate_builder": PREFIX / "build_s22plus_fyg8_p307_candidate.py",
}
SOURCE_KEYS = frozenset(SOURCE_PATHS)
OverlayContractError = parent.OverlayContractError
_receipt = parent._receipt  # noqa: SLF001
_canonical = parent._canonical  # noqa: SLF001
_read_regular = parent._read_regular  # noqa: SLF001


def source_receipts(root: Path) -> dict[str, dict[str, Any]]:
    rows = {
        key: _receipt(_read_regular(root / path, f"P3.07 SOURCE_KEY {key}"))
        for key, path in sorted(SOURCE_PATHS.items())
    }
    if set(rows) != SOURCE_KEYS:
        raise OverlayContractError("P3.07 SOURCE_KEYS differ")
    return rows


def verify_parent(root: Path) -> dict[str, Any]:
    value = parent.verify_intent(root, root / PARENT_INTENT)
    if (
        value.get("userspace_overlay_contract_id") != PARENT_OVERLAY_CONTRACT_ID
        or value.get("source_contract_id") != PARENT_SOURCE_CONTRACT_ID
        or value.get("profile") != PROFILE
        or value.get("fixed_image", {}).get("sha256") != EXPECTED_IMAGE["sha256"]
        or value.get("verified") is not True
    ):
        raise OverlayContractError("P3.07 parent P3.05 contract differs")
    return value


def generated_bytes(root: Path, parent_contract: Mapping[str, Any]) -> dict[str, bytes]:
    return generator.generate_bytes(
        root,
        run_id=bytes.fromhex(str(parent_contract["run_id"])),
        unsat_tag=bytes.fromhex(str(parent_contract["unsat_tag_hex"])),
        profile=str(parent_contract["profile"]),
    )


def create_intent_value(root: Path) -> dict[str, Any]:
    parent_contract = verify_parent(root)
    generated = generated_bytes(root, parent_contract)
    qscratch = qscratch_audit.audit(
        root,
        Path(telemetry.DWC3_MODULE_PATH),
        "aarch64-linux-gnu-objdump",
        "readelf",
    )
    value = {
        "schema": INTENT_SCHEMA,
        "verdict": INTENT_VERDICT,
        "contract_id": CONTRACT_ID,
        "target": TARGET,
        "profile": PROFILE,
        "run_id": parent_contract["run_id"],
        "unsat_tag_hex": parent_contract["unsat_tag_hex"],
        "parent_overlay_contract_id": PARENT_OVERLAY_CONTRACT_ID,
        "parent_source_contract_id": PARENT_SOURCE_CONTRACT_ID,
        "parent_overlay_contract": parent_contract,
        "parent_overlay_intent": {
            "path": PARENT_INTENT.as_posix(),
            **_receipt(_read_regular(root / PARENT_INTENT, "P3.07 parent intent")),
        },
        "fixed_image": {"path": PARENT_IMAGE.as_posix(), **EXPECTED_IMAGE},
        "source_keys": sorted(SOURCE_KEYS),
        "source_receipts": source_receipts(root),
        "generated_artifacts": {
            key: _receipt(data) for key, data in sorted(generated.items())
        },
        "callsite_audit": parent_contract["callsite_audit"],
        "qscratch_audit": qscratch,
        "telemetry": telemetry.validate(),
        "module_delta": parent_contract["module_delta"],
        "folded_tail": parent_contract["folded_tail"],
        "observer": {
            "kmsg_opened_before_modules": True,
            "eud_cache_path": telemetry.EUD_CACHE_PATH,
            "eud_cache_read_after_module_index": telemetry.EUD_MODULE_INDEX,
            "eud_cache_read_count": 1,
            "ordered_first_init_attribution": True,
            "qscratch_module": telemetry.DWC3_MODULE_RUNTIME_NAME,
            "qscratch_symbol": telemetry.QSCRATCH_SYMBOL,
            "qscratch_offset": telemetry.QSCRATCH_PROBE_OFFSET,
            "qscratch_register": "w21",
            "kernel_changed": False,
            "module_plan_changed": False,
            "log_level_changed": False,
            "read_only": True,
            "verified": True,
        },
        "safety": {
            "host_only": True,
            "fixed_kernel_image": True,
            "kernel_rebuild": False,
            "full_lto_ab": False,
            "module_binaries_injected": 0,
            "stock_vendor_ramdisk_module_reused": True,
            "device_contact": False,
            "live_authorized": False,
        },
    }
    value["intent_sha256"] = hashlib.sha256(_canonical(value)).hexdigest()
    return value


def verify_intent(root: Path, intent_path: Path) -> dict[str, Any]:
    payload = _read_regular(intent_path, "P3.07 overlay intent")
    try:
        value = json.loads(payload.decode("ascii"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise OverlayContractError("P3.07 overlay intent is not ASCII JSON") from exc
    expected = create_intent_value(root)
    if value != expected:
        raise OverlayContractError("P3.07 overlay intent content differs")
    generated = generated_bytes(root, value["parent_overlay_contract"])
    for key, relative in generator.artifact_paths().items():
        actual = _read_regular(
            intent_path.parent / relative,
            f"P3.07 materialized {key}",
            4 * 1024 * 1024,
        )
        if actual != generated[key]:
            raise OverlayContractError(f"P3.07 materialized source differs: {key}")
    parent_contract = value["parent_overlay_contract"]
    return {
        "schema": SCHEMA,
        "verdict": CONTRACT_VERDICT,
        "contract_id": CONTRACT_ID,
        "target": TARGET,
        "profile": PROFILE,
        "profile_number": parent_contract["profile_number"],
        "run_id": value["run_id"],
        "unsat_tag_hex": value["unsat_tag_hex"],
        "source_contract_id": PARENT_SOURCE_CONTRACT_ID,
        "userspace_overlay_contract_id": CONTRACT_ID,
        "parent_overlay_contract_id": PARENT_OVERLAY_CONTRACT_ID,
        "parent_overlay_contract": parent_contract,
        "parent_candidate_contract": parent_contract["parent_candidate_contract"],
        "overlay_intent": _receipt(payload),
        "overlay_intent_sha256": value["intent_sha256"],
        "source_receipts": value["source_receipts"],
        "generated_artifacts": value["generated_artifacts"],
        "fixed_image": value["fixed_image"],
        "callsite_audit": value["callsite_audit"],
        "qscratch_audit": value["qscratch_audit"],
        "telemetry": value["telemetry"],
        "module_delta": value["module_delta"],
        "folded_tail": value["folded_tail"],
        "observer": value["observer"],
        "verified": True,
        "safety": value["safety"],
    }
