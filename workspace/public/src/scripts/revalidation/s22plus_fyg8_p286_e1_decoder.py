#!/usr/bin/env python3
"""Decode P2.86 bounded-restart details and generated final tuples."""

from __future__ import annotations

import hashlib
from typing import Any

import s22plus_fyg8_p252_e1_decoder as p252
import s22plus_fyg8_p286_contract_spec as spec


SCHEMA = "s22plus_fyg8_p286_e3_decoder_v1"
DECODER_ID = "s22plus_fyg8_p286_parent_tail_bounded_restart_v1"
PROFILE = spec.PROFILE
STAGE_SEQUENCE = spec.STAGE_SEQUENCE
TERMINAL_STAGE = spec.TERMINAL_STAGE
WARNING_VALUES = frozenset(
    (0xB01, 0xB02, 0xB03, 0xC01, 0xC02, 0xC03, 0xC46)
)
POLICY_PREIMAGE = (
    "S22PLUS_FYG8_P286_E3_DECODER_V1|"
    "layout=S22E1L1-45-ab-crc32|"
    "unsat=S22E1U1-24|"
    "baseline=all-related-families-absent|"
    "accept=one-or-more-p286-terminal-success|"
    "reject=foreign,malformed,partial,unknown-detail|zero=ambiguous|"
    "detail=001-7ff-errno,800-8ff-regression,900-9ff-read-error,"
    f"exact={','.join(f'{value:03x}' for value in spec.DETAIL_VALUES)},"
    f"tuple={spec.TUPLE_BASE:03x}-{spec.TUPLE_MAX:03x}|"
    "stable-pair=changing-canonical-c4b|"
    f"stages={','.join(f'{stage:02x}' for stage in STAGE_SEQUENCE)}|"
    f"spec={spec.SCHEMA}|model={p252.model.SCHEMA}"
)
POLICY_SHA256 = hashlib.sha256(POLICY_PREIMAGE.encode("ascii")).hexdigest()
POLICY_ID = POLICY_SHA256[:32]

model = p252.model
DecodeError = p252.DecodeError


def encode_slot(
    header: bytes,
    *,
    generation: int,
    stage: int,
    outcome: int,
    item_index: int,
    detail: int,
) -> bytes:
    return p252.encode_slot(
        header,
        generation=generation,
        stage=stage,
        outcome=outcome,
        item_index=item_index,
        detail=detail,
        _contract_spec=spec,
    )


def decode_detail(value: int) -> dict[str, Any]:
    result: dict[str, Any] = {
        "detail": value,
        "detail_kind": spec.detail_kind(value),
        "detail_name": spec.detail_name(value),
        "final_tuple": None,
    }
    if spec.TUPLE_BASE <= value <= spec.TUPLE_MAX:
        decoded = spec.decode_tuple(value)
        result["final_tuple"] = {
            "repair_index": int(decoded.repair),
            "repair": decoded.repair.name.lower().replace("_", "-"),
            "bind_index": int(decoded.bind),
            "bind": decoded.bind.name.lower().replace("_", "-"),
            "state_index": decoded.state_index,
            "state": decoded.state,
            "speed_index": decoded.speed_index,
            "speed": decoded.speed,
            "outcome": decoded.outcome,
        }
    return result


def _with_p286_semantics(result: dict[str, Any]) -> dict[str, Any]:
    warnings = [
        slot
        for slot in result["valid_slots"]
        if slot["outcome"] == model.OUTCOME_PROGRESS
        and slot["detail"] in WARNING_VALUES
    ]
    result["progress_warnings"] = [
        {
            "stage": slot["stage"],
            **decode_detail(slot["detail"]),
        }
        for slot in sorted(warnings, key=lambda value: value["generation"])
    ]
    result["progress_warning"] = (
        result["progress_warnings"][0]
        if result["progress_warnings"]
        else None
    )
    result["slot_semantics"] = [
        {
            "slot_id": slot["slot_id"],
            "generation": slot["generation"],
            "stage": slot["stage"],
            **decode_detail(slot["detail"]),
        }
        for slot in result["valid_slots"]
    ]
    result["active_semantics"] = decode_detail(result["active"]["detail"])
    return result


def decode_record(
    record: bytes,
    *,
    expected_profile: str = PROFILE,
    expected_run_id: bytes | None = None,
) -> dict[str, Any]:
    result = p252.decode_record(
        record,
        expected_profile=expected_profile,
        expected_run_id=expected_run_id,
        _contract_spec=spec,
    )
    return _with_p286_semantics(result)


def classify_clean_baseline(
    payload: bytes, *, expected_profile: str, expected_run_id: bytes
) -> dict[str, Any]:
    return p252.classify_clean_baseline(
        payload,
        expected_profile=expected_profile,
        expected_run_id=expected_run_id,
        _contract_spec=spec,
    )


def classify_observation(
    payload: bytes, *, expected_profile: str, expected_run_id: bytes
) -> dict[str, Any]:
    result = p252.classify_observation(
        payload,
        expected_profile=expected_profile,
        expected_run_id=expected_run_id,
        _contract_spec=spec,
    )
    for record in result.get("records", ()):
        _with_p286_semantics(record)
    return result
