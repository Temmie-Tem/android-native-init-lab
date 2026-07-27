#!/usr/bin/env python3
"""Decode P2.80 records and preserve progress-warning semantics."""

from __future__ import annotations

import hashlib
from typing import Any

import s22plus_fyg8_p252_e1_decoder as p252
import s22plus_fyg8_p280_contract_spec as spec


SCHEMA = "s22plus_fyg8_p280_e3_decoder_v1"
DECODER_ID = "s22plus_fyg8_p280_parent_pullup_discriminator_v1"
PROFILE = spec.PROFILE
STAGE_SEQUENCE = spec.STAGE_SEQUENCE
TERMINAL_STAGE = spec.TERMINAL_STAGE
WARNING_VALUES = frozenset((0xB01, 0xB02, 0xB03))
POLICY_PREIMAGE = (
    "S22PLUS_FYG8_P280_E3_DECODER_V1|"
    "layout=S22E1L1-45-ab-crc32|"
    "unsat=S22E1U1-24|"
    "baseline=all-related-families-absent|"
    "accept=one-or-more-p280-terminal-success|"
    "reject=foreign,malformed,partial,unknown-detail|zero=ambiguous|"
    "detail=001-7ff-errno,800-8ff-regression,900-9ff-read-error,"
    f"exact={','.join(f'{value:03x}' for value in spec.DETAIL_VALUES)}|"
    "warning-origin=unknown|"
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


def _with_warning(result: dict[str, Any]) -> dict[str, Any]:
    warnings = [
        slot
        for slot in result["valid_slots"]
        if slot["outcome"] == model.OUTCOME_PROGRESS
        and slot["detail"] in WARNING_VALUES
    ]
    warning_values = {slot["detail"] for slot in warnings}
    if len(warning_values) > 1:
        raise DecodeError("distinct P2.80 progress warnings are ambiguous")
    result["progress_warning"] = None
    if warnings:
        slot = min(warnings, key=lambda value: value["generation"])
        result["progress_warning"] = {
            "stage": slot["stage"],
            "detail": slot["detail"],
            "detail_kind": spec.detail_kind(slot["detail"]),
            "detail_name": spec.detail_name(slot["detail"]),
            "origin_phase": "unknown",
        }
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
    return _with_warning(result)


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
        _with_warning(record)
    return result
