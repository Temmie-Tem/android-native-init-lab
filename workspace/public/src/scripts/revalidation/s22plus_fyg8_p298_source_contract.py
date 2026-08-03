#!/usr/bin/env python3
"""P2.98 source contract for gadget-start/event telemetry."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
from typing import Any

import s22plus_fyg8_p296_source_contract as inherited
import s22plus_fyg8_p298_identity_tiers as identity
import s22plus_fyg8_p298_telemetry_closure as closure
import s22plus_fyg8_p298_telemetry_decoder as decoder
import s22plus_fyg8_p298_telemetry_generator as generator
import s22plus_fyg8_p298_telemetry_spec as spec


CONTRACT_ID = "s22plus-fyg8-p298-gadget-start-event-attribution-v1"
PROFILE = spec.PROFILE
RUN_ID_DOMAIN = b"S22PLUS-FYG8-P298-GADGET-START-EVENT-RUN-ID-V1\0"
INTENT_SCHEMA = "s22plus_fyg8_p298_candidate_intent_v1"
PREIMAGE_SCHEMA = "s22plus_fyg8_p298_candidate_identity_preimage_v1"
INTENT_VERDICT = "PASS_P298_CANDIDATE_INTENT_HOST_ONLY"
CONTRACT_SCHEMA = "s22plus_fyg8_p298_candidate_contract_v1"
CONTRACT_VERDICT = "PASS_P298_CANDIDATE_CONTRACT_HOST_ONLY"
USERSPACE_VERDICT = "PASS_P298_E3_USERSPACE_TWO_BUILD_REPRO_HOST_ONLY"
IMPLEMENTATION_VERDICT = "PASS_P298_GADGET_START_EVENT_IMPLEMENTATION_HOST_ONLY"
SOURCE_CHECK_RUN_ID = identity.SOURCE_CHECK_RUN_ID
SOURCE_CHECK_UNSAT_TAG = identity.SOURCE_CHECK_UNSAT_TAG
MODULE_PLAN_COUNT = inherited.MODULE_PLAN_COUNT
SOURCE_KEYS = identity.TIER1_SOURCE_KEYS
STAGE_SEQUENCE = tuple(position.stage for position in spec.POSITIONS)
MATERIALIZED_FILENAMES = {
    key: path.name
    for key, path in generator.artifact_paths().items()
    if key != "candidate_patch"
}
TELEMETRY_REACHABLE_VARIANTS = (
    spec.EVENT_LINK_VALUE_COUNT
    + spec.FINAL_STATE_VALUE_COUNT
    + spec.FIXED_MISMATCH_VALUE_COUNT
    + 2
    + len(spec.FAILURE_DETAIL_NAMES)
)
PROBE_TARGET_SYMBOLS = (
    "__dwc3_gadget_start",
    "__dwc3_gadget_ep_enable",
    "dwc3_gadget_reset_interrupt",
    "dwc3_gadget_conndone_interrupt",
)
GADGET_START_CALLSITE_SYMBOLS = (
    "dwc3_gadget_pullup",
    "dwc3_gadget_resume",
)
REACHABLE_VARIANTS = inherited.REACHABLE_VARIANTS + TELEMETRY_REACHABLE_VARIANTS
LINKED_VALIDATOR_SYMBOLS = (
    *inherited.LINKED_VALIDATOR_SYMBOLS,
    *PROBE_TARGET_SYMBOLS,
    *GADGET_START_CALLSITE_SYMBOLS,
)
DRIVER_SOURCE_REFERENCE = inherited.DRIVER_SOURCE_REFERENCE
DRIVER_SOURCE_RECEIPTS = inherited.DRIVER_SOURCE_RECEIPTS


class SourceContractError(ValueError):
    pass


SourceContract = inherited.SourceContract
P298 = SourceContract(
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
        raise SourceContractError(
            f"unsupported source contract/profile: {contract_id!r}/{profile}"
        )
    return P298


def candidate_observer(run_id: bytes) -> dict[str, str]:
    return inherited.candidate_observer(run_id)


def source_bytes(root: Path) -> dict[str, bytes]:
    result = identity.tier1_materials(root)
    if set(result) != SOURCE_KEYS:
        raise SourceContractError("P2.98 source inventory changed")
    expected_patch = generator.generate_bytes(
        root,
        run_id=SOURCE_CHECK_RUN_ID,
        unsat_tag=SOURCE_CHECK_UNSAT_TAG,
        profile=PROFILE,
    )["candidate_patch"]
    if result["base_patch"] != expected_patch:
        raise SourceContractError(
            "P2.98 base patch is not the telemetry generator output"
        )
    return result


def source_receipts(root: Path) -> tuple[dict[str, bytes], dict[str, Any]]:
    data = source_bytes(root)
    return data, {name: receipt(value) for name, value in sorted(data.items())}


def generate(root: Path | None = None) -> dict[str, bytes]:
    repository = inherited.inherited.inherited.p290.p288.p243.repo_root() \
        if root is None else root
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
    source_result = closure.audit_driver_source(root)
    if source_result.get("verified") is not True:
        raise SourceContractError("P2.98 EP0 source closure differs")
    return {
        **result,
        "gadget_start_source": source_result,
        "probe_target_symbols": list(PROBE_TARGET_SYMBOLS),
        "verified": True,
    }


def _audit_userspace(
    root: Path,
    generated: dict[str, bytes],
    source: dict[str, bytes],
    directory: Path,
) -> dict[str, Any]:
    for key, filename in MATERIALIZED_FILENAMES.items():
        if key in {"checkpoint_client", "runtime_wrapper", "plan_header"}:
            continue
        (directory / filename).write_bytes(source[key])
    try:
        return inherited.checkpoint_base.p290.p288.p252._audit_userspace(  # noqa: SLF001
            inherited.checkpoint_base.p290.shared_input_root(root),
            generated,
            directory,
            materialized_filenames=MATERIALIZED_FILENAMES,
            source_check_run_id=SOURCE_CHECK_RUN_ID,
        )
    except inherited.checkpoint_base.p290.p288.p252.SourceContractError as exc:
        raise SourceContractError(str(exc)) from exc


def implementation_result(root: Path) -> dict[str, Any]:
    first = generate(root)
    second = generate(root)
    if first != second:
        raise SourceContractError("P2.98 generation is not deterministic")
    source = source_bytes(root)
    identity_result = identity.validate()
    telemetry = closure.run_closure(root)
    if telemetry.get("verdict") != closure.VERDICT:
        raise SourceContractError("P2.98 telemetry closure differs")
    with tempfile.TemporaryDirectory(prefix="s22-p298-") as temporary:
        directory = Path(temporary)
        patch = _audit_patch(root, first["patch"], directory)
        userspace = _audit_userspace(root, first, source, directory)
    return {
        "schema": "s22plus_fyg8_p298_implementation_v1",
        "verdict": IMPLEMENTATION_VERDICT,
        "contract_id": CONTRACT_ID,
        "source_key_count": len(SOURCE_KEYS),
        "generated": {name: receipt(data) for name, data in sorted(first.items())},
        "patch": patch,
        "linked_userspace": userspace,
        "telemetry_closure": telemetry,
        "identity": identity_result,
        "descriptor": {
            "position_count": len(spec.POSITIONS),
            "terminal_generation": spec.TERMINAL_GENERATION,
            "record_size": 45,
            "slot_count": 2,
            "bind_event_count": 12,
            "historical_no_probe_control": "P2.96",
        },
        "safety": {
            "host_only": True,
            "device_contact": False,
            "boot_image_packaging": False,
            "live_authorized": False,
        },
        "verified": True,
    }


def _prefix_record(run_id: bytes, ordinal: int) -> bytes:
    record = decoder.model.initialize_record(PROFILE, run_id)
    for index, position in enumerate(spec.POSITIONS[:ordinal]):
        detail = 0xC18 if index == 87 else 0xC40 if index == 103 else 0
        record = decoder.model.apply_request(
            record,
            decoder.model.encode_request(
                PROFILE,
                position.stage,
                run_id=run_id,
                outcome=decoder.model.OUTCOME_PROGRESS,
                item_index=position.item_index,
                detail=detail,
            ),
        )
    return record


def validate_reachable_records(run_id: bytes) -> dict[str, Any]:
    if len(run_id) != 16 or not any(run_id):
        raise SourceContractError("P2.98 reachable run ID is invalid")
    inherited_result = inherited.validate_reachable_records(run_id)
    checked = 0
    for ordinal, details in (
        (101, spec.BIND_SETUP_FAILURE_DETAILS),
        (103, spec.BIND_RESULT_FAILURE_DETAILS),
        (spec.EVENT_LINK_ORDINAL, spec.FINAL_TRACE_FAILURE_DETAILS),
    ):
        prefix = _prefix_record(run_id, ordinal)
        position = spec.POSITIONS[ordinal]
        for detail in details:
            candidate = decoder.model.apply_request(
                prefix,
                decoder.model.encode_request(
                    PROFILE,
                    position.stage,
                    run_id=run_id,
                    outcome=decoder.model.OUTCOME_FAILURE,
                    item_index=position.item_index,
                    detail=detail,
                ),
            )
            if decoder.decode_record(candidate, expected_run_id=run_id)["active"][
                "detail"
            ] != detail:
                raise SourceContractError("P2.98 observer failure route differs")
            checked += 1
    prefix = _prefix_record(run_id, spec.EVENT_LINK_ORDINAL)
    first_position = spec.POSITIONS[spec.EVENT_LINK_ORDINAL]
    terminal_position = spec.POSITIONS[spec.FINAL_STATE_ORDINAL]
    terminal_details = (
        *range(
            spec.FINAL_STATE_DETAIL_BASE,
            spec.FINAL_STATE_DETAIL_BASE + spec.FINAL_STATE_VALUE_COUNT,
        ),
        *range(
            spec.FIXED_MISMATCH_DETAIL_BASE,
            spec.FIXED_MISMATCH_DETAIL_BASE + spec.FIXED_MISMATCH_VALUE_COUNT,
        ),
        spec.STATE_SPEED_CONTRADICTION_DETAIL,
        spec.CONNECT_SPEED_CONTRADICTION_DETAIL,
    )
    first = None
    for detail in range(
        spec.EVENT_LINK_DETAIL_BASE,
        spec.EVENT_LINK_DETAIL_BASE + spec.EVENT_LINK_VALUE_COUNT,
    ):
        first = decoder.model.apply_request(
            prefix,
            decoder.model.encode_request(
                PROFILE,
                first_position.stage,
                run_id=run_id,
                outcome=decoder.model.OUTCOME_PROGRESS,
                item_index=first_position.item_index,
                detail=detail,
            ),
        )
        checked += 1
    if first is None:
        raise SourceContractError("P2.98 event/link family is empty")
    for detail in terminal_details:
        terminal = decoder.model.apply_request(
            first,
            decoder.model.encode_request(
                PROFILE,
                terminal_position.stage,
                run_id=run_id,
                outcome=spec.expected_terminal_outcome(detail),
                item_index=terminal_position.item_index,
                detail=detail,
            ),
        )
        if decoder.decode_record(terminal, expected_run_id=run_id)["active"][
            "detail"
        ] != detail:
            raise SourceContractError("P2.98 terminal route differs")
        checked += 1
    if checked != TELEMETRY_REACHABLE_VARIANTS:
        raise SourceContractError("P2.98 telemetry reachable count differs")
    return {
        **inherited_result,
        "reachable_slot_variants": REACHABLE_VARIANTS,
        "decoder_policy_id": decoder.POLICY_ID,
        "telemetry_reachable_variants": checked,
        "position_count": len(spec.POSITIONS),
        "terminal_generation": spec.TERMINAL_GENERATION,
        "verified": True,
    }


def linked_table_bytes() -> dict[str, bytes]:
    result = dict(inherited.checkpoint_base.linked_table_bytes())
    rules = bytearray()
    for ordinal, outcome, detail in spec.exact_detail_rules():
        rules.append(ordinal)
        rules.append(outcome)
        rules.extend(detail.to_bytes(2, "little"))
    result["s22_fyg8_p290_detail_rules"] = bytes(rules)
    return result


def audit_linked_tables(actual: dict[str, bytes]) -> dict[str, Any]:
    expected = linked_table_bytes()
    if actual != expected:
        raise SourceContractError("P2.98 linked descriptor tables differ")
    return {name: receipt(data) for name, data in sorted(actual.items())} | {
        "descriptor_bytes_verified": True,
        "position_pairs_verified": True,
        "exact_detail_whitelist_verified": True,
        "verified": True,
    }


if __name__ == "__main__":
    print(json.dumps(implementation_result(Path.cwd()), indent=2, sort_keys=True))
