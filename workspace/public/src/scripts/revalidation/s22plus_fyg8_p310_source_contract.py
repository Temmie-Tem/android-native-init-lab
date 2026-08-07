#!/usr/bin/env python3
"""P3.10 source contract for Carrier v2 and corrected P3.08 telemetry."""

from __future__ import annotations

import hashlib
from pathlib import Path
import re
import tempfile
from typing import Any

import s22plus_fyg8_p300_source_contract as inherited
import s22plus_fyg8_p308_telemetry_spec as spec
import s22plus_fyg8_p310_carrier_model as carrier
import s22plus_fyg8_p310_generator as generator
import s22plus_fyg8_p310_identity_tiers as identity
import s22plus_fyg8_p310_telemetry_decoder as decoder


CONTRACT_ID = "s22plus-fyg8-p310-carrier-v2-hsphy-attribution-v1"
PROFILE = spec.PROFILE
RUN_ID_DOMAIN = b"S22PLUS-FYG8-P310-CARRIER-V2-HSPHY-RUN-ID-V1\0"
INTENT_SCHEMA = "s22plus_fyg8_p310_candidate_intent_v1"
PREIMAGE_SCHEMA = "s22plus_fyg8_p310_candidate_identity_preimage_v1"
INTENT_VERDICT = "PASS_P310_CANDIDATE_INTENT_HOST_ONLY"
CONTRACT_SCHEMA = "s22plus_fyg8_p310_candidate_contract_v1"
CONTRACT_VERDICT = "PASS_P310_CANDIDATE_CONTRACT_HOST_ONLY"
USERSPACE_VERDICT = "PASS_P310_E3_USERSPACE_TWO_BUILD_REPRO_HOST_ONLY"
IMPLEMENTATION_VERDICT = "PASS_P310_CARRIER_V2_IMPLEMENTATION_HOST_ONLY"
SOURCE_CHECK_RUN_ID = identity.SOURCE_CHECK_RUN_ID
SOURCE_CHECK_UNSAT_TAG = identity.SOURCE_CHECK_UNSAT_TAG
SOURCE_KEYS = identity.SOURCE_KEYS
STAGE_SEQUENCE = tuple(position.stage for position in spec.POSITIONS)
MATERIALIZED_FILENAMES = {
    key: path.name
    for key, path in generator.artifact_paths().items()
    if key != "candidate_patch"
}
TELEMETRY_REACHABLE_VARIANTS = (
    len(set(spec.attribution_outputs()) | set(spec.clock_outputs()))
    + len(tuple(spec.summary_outputs()))
    + len(tuple(spec.degraded_outputs()))
)
REACHABLE_VARIANTS = inherited.REACHABLE_VARIANTS + TELEMETRY_REACHABLE_VARIANTS
LINKED_VALIDATOR_SYMBOLS = inherited.LINKED_VALIDATOR_SYMBOLS
PROBE_TARGET_SYMBOLS = inherited.PROBE_TARGET_SYMBOLS
GADGET_START_CALLSITE_SYMBOLS = inherited.GADGET_START_CALLSITE_SYMBOLS
DRIVER_SOURCE_REFERENCE = inherited.DRIVER_SOURCE_REFERENCE
DRIVER_SOURCE_RECEIPTS = inherited.DRIVER_SOURCE_RECEIPTS
linked_table_bytes = inherited.linked_table_bytes


class SourceContractError(ValueError):
    pass


def _generated_module_plan_count() -> int:
    plan_header = generator.generate_bytes(
        inherited.inherited.inherited.inherited.inherited.p290.p288.p243.repo_root(),
        run_id=SOURCE_CHECK_RUN_ID,
        unsat_tag=SOURCE_CHECK_UNSAT_TAG,
        profile=PROFILE,
    )["plan_header"]
    names = tuple(
        match.decode("ascii")
        for match in re.findall(
            rb'^\s+\{"([^"]+\.ko)",', plan_header, re.MULTILINE
        )
    )
    if not names or len(names) != len(set(names)):
        raise SourceContractError("P3.10 generated module plan inventory differs")
    return len(names)


MODULE_PLAN_COUNT = _generated_module_plan_count()
SourceContract = inherited.SourceContract
P310 = SourceContract(
    contract_id=CONTRACT_ID,
    profile=PROFILE,
    run_id_domain=RUN_ID_DOMAIN,
    stage_sequence=STAGE_SEQUENCE,
    terminal_stage=spec.TERMINAL_STAGE,
    reachable_variants=REACHABLE_VARIANTS,
    source_keys=SOURCE_KEYS,
)


def receipt(data: bytes) -> dict[str, Any]:
    return {"size": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def require(contract_id: str | None, profile: str) -> SourceContract:
    if contract_id != CONTRACT_ID or profile != PROFILE:
        raise SourceContractError(f"unsupported source contract/profile: {contract_id!r}/{profile}")
    return P310


def candidate_observer(run_id: bytes) -> dict[str, str]:
    return inherited.candidate_observer(run_id)


def source_bytes(root: Path) -> dict[str, bytes]:
    result = identity.tier1_materials(root)
    if set(result) != SOURCE_KEYS:
        raise SourceContractError("P3.10 source inventory changed")
    expected = generator.generate_bytes(
        root,
        run_id=SOURCE_CHECK_RUN_ID,
        unsat_tag=SOURCE_CHECK_UNSAT_TAG,
        profile=PROFILE,
    )
    if result["base_patch"] != expected["candidate_patch"]:
        raise SourceContractError("P3.10 base patch is not the Carrier v2 generator output")
    return result


def source_receipts(root: Path) -> tuple[dict[str, bytes], dict[str, Any]]:
    data = source_bytes(root)
    return data, {name: receipt(value) for name, value in sorted(data.items())}


def audit_linked_tables(actual: dict[str, bytes]) -> dict[str, Any]:
    try:
        return inherited.audit_linked_tables(actual)
    except inherited.SourceContractError as exc:
        raise SourceContractError(str(exc)) from exc


def generate(root: Path | None = None) -> dict[str, bytes]:
    repository = inherited.inherited.inherited.inherited.inherited.p290.p288.p243.repo_root() if root is None else root
    source = source_bytes(repository)
    return {
        "plan": source["plan_header"],
        "runtime": source["runtime_wrapper"],
        "checkpoint": source["checkpoint_client"],
        "patch": source["base_patch"],
    }


def _audit_patch(root: Path, patch: bytes, directory: Path) -> dict[str, Any]:
    try:
        result = inherited._audit_patch(root, patch, directory)  # noqa: SLF001
    except inherited.SourceContractError as exc:
        raise SourceContractError(str(exc)) from exc
    for token in (
        b'S22E1L2|',
        b'S22_FYG8_E1_LONG_SIZE\t\t192U',
        b'S22_FYG8_E1_REQUEST_V3_SIZE\t100U',
        b'S22PLUS-FYG8-P310-HEADER-V2',
        b'S22PLUS-FYG8-P310-SLOT-V2',
    ):
        if patch.count(token) != 1:
            raise SourceContractError(f"P3.10 kernel ABI token differs: {token!r}")
    return {**result, "carrier": carrier.validate(), "verified": True}


def _audit_userspace(root: Path, generated: dict[str, bytes], source: dict[str, bytes], directory: Path) -> dict[str, Any]:
    try:
        return inherited._audit_userspace(root, generated, source, directory)  # noqa: SLF001
    except inherited.SourceContractError as exc:
        raise SourceContractError(str(exc)) from exc


def implementation_result(root: Path) -> dict[str, Any]:
    first = generate(root)
    second = generate(root)
    if first != second:
        raise SourceContractError("P3.10 generation is not deterministic")
    source = source_bytes(root)
    with tempfile.TemporaryDirectory(prefix="s22-p310-") as temporary:
        directory = Path(temporary)
        patch = _audit_patch(root, first["patch"], directory)
        userspace = _audit_userspace(root, first, source, directory)
    return {
        "schema": "s22plus_fyg8_p310_implementation_v1",
        "verdict": IMPLEMENTATION_VERDICT,
        "contract_id": CONTRACT_ID,
        "source_key_count": len(SOURCE_KEYS),
        "generated": {name: receipt(data) for name, data in sorted(first.items())},
        "patch": patch,
        "linked_userspace": userspace,
        "identity": identity.validate(),
        "carrier": carrier.validate(),
        "tracefs_descriptor_correction_inherited": True,
        "safety": {
            "host_only": True,
            "device_contact": False,
            "boot_image_packaging": False,
            "candidate_qualification_complete": False,
            "live_authorized": False,
        },
        "verified": True,
    }


def _prefix(run_id: bytes, ordinal: int) -> bytes:
    record = carrier.initialize_record(PROFILE, run_id)
    for index, position in enumerate(spec.POSITIONS[:ordinal]):
        detail = 0xC18 if index == 87 else 0xC40 if index == 103 else 0
        record = carrier.apply_request(
            record,
            carrier.encode_request(
                PROFILE,
                position.stage,
                run_id=run_id,
                outcome=carrier.OUTCOME_PROGRESS,
                item_index=position.item_index,
                detail=detail,
            ),
        )
    return record


def validate_reachable_records(run_id: bytes) -> dict[str, Any]:
    if len(run_id) != 16 or not any(run_id):
        raise SourceContractError("P3.10 reachable run ID is invalid")
    a_prefix = _prefix(run_id, spec.ATTR_ORDINAL)
    a_position = spec.POSITIONS[spec.ATTR_ORDINAL]
    a_values = sorted(set(spec.attribution_outputs()) | set(spec.clock_outputs()))
    checked = 0
    for detail in a_values:
        carrier.apply_request(
            a_prefix,
            carrier.encode_request(
                PROFILE,
                a_position.stage,
                run_id=run_id,
                outcome=carrier.OUTCOME_PROGRESS,
                item_index=a_position.item_index,
                detail=detail,
            ),
        )
        checked += 1
    representative_a = carrier.apply_request(
        a_prefix,
        carrier.encode_request(
            PROFILE,
            a_position.stage,
            run_id=run_id,
            outcome=carrier.OUTCOME_PROGRESS,
            item_index=a_position.item_index,
            detail=a_values[0],
        ),
    )
    b_position = spec.POSITIONS[spec.SUMMARY_ORDINAL]
    b_values = (*spec.summary_outputs(), *spec.degraded_outputs())
    for detail in b_values:
        candidate = carrier.apply_request(
            representative_a,
            carrier.encode_request(
                PROFILE,
                b_position.stage,
                run_id=run_id,
                outcome=carrier.OUTCOME_FAILURE,
                item_index=b_position.item_index,
                detail=detail,
            ),
        )
        if decoder.decode_record(candidate, expected_run_id=run_id)["active"]["detail"] != detail:
            raise SourceContractError("P3.10 reachable detail round trip differs")
        checked += 1
    if checked != TELEMETRY_REACHABLE_VARIANTS:
        raise SourceContractError("P3.10 reachable telemetry count differs")
    return {
        "schema": "s22plus_fyg8_p310_reachable_records_v1",
        "a_output_count": len(a_values),
        "b_output_count": len(b_values),
        "checked": checked,
        "reachable_slot_variants": REACHABLE_VARIANTS,
        "telemetry_reachable_variants": TELEMETRY_REACHABLE_VARIANTS,
        "request_v2_compatible": True,
        "carrier_v2": True,
        "verified": True,
    }
