#!/usr/bin/env python3
"""Decode P2.92 exact-slot records, including publication errno failures."""

from __future__ import annotations

import hashlib
from typing import Any

import s22plus_fyg8_p290_contract_spec as positions
import s22plus_fyg8_p292_repair_model as model
import s22plus_fyg8_p292_repair_spec as repair


SCHEMA = "s22plus_fyg8_p292_exact_slot_decoder_v1"
DECODER_ID = "s22plus_fyg8_p292_exact_slot_and_publication_errno_v1"
PROFILE = positions.PROFILE
POSITION_SEQUENCE = positions.POSITION_SEQUENCE
TERMINAL_POSITION = positions.TERMINAL_POSITION
WARNING_VALUES = frozenset(
    (0xB01, 0xB02, 0xB03, 0xC01, 0xC02, 0xC03, 0xC46)
)
POLICY_PREIMAGE = (
    "S22PLUS_FYG8_P292_EXACT_SLOT_DECODER_V1|"
    "layout=S22E1L1-45-ab-crc32|"
    "position=ordered-stage-item-pairs|"
    "active-state=exact-committed-slot|"
    "publication-error=open-write-close-plus-exact-errno|"
    f"repair={repair.descriptor_sha256()}|model={model.SCHEMA}"
)
POLICY_SHA256 = hashlib.sha256(POLICY_PREIMAGE.encode("ascii")).hexdigest()
POLICY_ID = POLICY_SHA256[:32]
DecodeError = model.DesignError


def decode_detail(value: int, *, outcome: int | None = None) -> dict[str, Any]:
    result: dict[str, Any] = {
        "detail": value,
        "detail_kind": positions.detail_kind(value),
        "detail_name": positions.detail_name(value),
        "publication_error": None,
    }
    if outcome == model.OUTCOME_FAILURE:
        try:
            operation, error = repair.decode_publication_error(value)
        except repair.RepairSpecError:
            pass
        else:
            operation_name = next(
                item.name
                for item in repair.PUBLICATION_OPERATIONS
                if item.value == operation
            )
            result["detail_kind"] = "checkpoint-publication-error"
            result["detail_name"] = (
                f"checkpoint-publication-{operation_name}-errno-{-error}"
            )
            result["publication_error"] = {
                "operation": operation,
                "operation_name": operation_name,
                "errno": error,
            }
    return result


def _with_semantics(result: dict[str, Any]) -> dict[str, Any]:
    warnings = [
        slot
        for slot in result["valid_slots"]
        if slot["outcome"] == model.OUTCOME_PROGRESS
        and slot["detail"] in WARNING_VALUES
    ]
    result["progress_warnings"] = [
        {
            "stage": slot["stage"],
            "item_index": slot["item_index"],
            **decode_detail(slot["detail"], outcome=slot["outcome"]),
        }
        for slot in sorted(warnings, key=lambda value: value["generation"])
    ]
    result["slot_semantics"] = [
        {
            "slot_id": slot["slot_id"],
            "generation": slot["generation"],
            "stage": slot["stage"],
            "item_index": slot["item_index"],
            "position_name": (
                "entry"
                if slot["generation"] == 0
                else positions.position_for_generation(
                    slot["generation"]
                ).name
            ),
            **decode_detail(slot["detail"], outcome=slot["outcome"]),
        }
        for slot in result["valid_slots"]
    ]
    active = result["active"]
    result["active_semantics"] = {
        "position_name": (
            "entry"
            if active["generation"] == 0
            else positions.position_for_generation(active["generation"]).name
        ),
        **decode_detail(active["detail"], outcome=active["outcome"]),
    }
    return result


def decode_record(
    record: bytes,
    *,
    expected_profile: str = PROFILE,
    expected_run_id: bytes | None = None,
) -> dict[str, Any]:
    return _with_semantics(
        model.decode_record(
            record,
            expected_profile=expected_profile,
            expected_run_id=expected_run_id,
        )
    )


def classify_clean_baseline(
    payload: bytes,
    *,
    expected_profile: str,
    expected_run_id: bytes,
) -> dict[str, Any]:
    return model.classify_clean_baseline(
        payload,
        expected_profile=expected_profile,
        expected_run_id=expected_run_id,
    )


def classify_observation(
    payload: bytes,
    *,
    expected_profile: str,
    expected_run_id: bytes,
) -> dict[str, Any]:
    result = model.classify_observation(
        payload,
        expected_profile=expected_profile,
        expected_run_id=expected_run_id,
    )
    for record in result.get("records", ()):
        _with_semantics(record)
    return result
