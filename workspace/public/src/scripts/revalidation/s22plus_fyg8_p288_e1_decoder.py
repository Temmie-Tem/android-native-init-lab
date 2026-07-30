#!/usr/bin/env python3
"""Decode P2.88 pair-indexed attributable retained positions."""

from __future__ import annotations

import hashlib
from typing import Any

import s22plus_fyg8_p288_contract_spec as spec
import s22plus_fyg8_p288_latest_stage_model as model


SCHEMA = "s22plus_fyg8_p288_e3_decoder_v1"
DECODER_ID = "s22plus_fyg8_p288_pair_attributable_positions_v1"
PROFILE = spec.PROFILE
STAGE_SEQUENCE = spec.STAGE_SEQUENCE
POSITION_SEQUENCE = spec.POSITION_SEQUENCE
TERMINAL_STAGE = spec.TERMINAL_STAGE
TERMINAL_POSITION = spec.TERMINAL_POSITION
WARNING_VALUES = frozenset(
    (0xB01, 0xB02, 0xB03, 0xC01, 0xC02, 0xC03, 0xC46)
)
POLICY_PREIMAGE = (
    "S22PLUS_FYG8_P288_E3_DECODER_V1|"
    "layout=S22E1L1-45-ab-crc32|"
    "position=ordered-stage-item-pairs|"
    "baseline=all-related-families-absent|"
    "accept=one-or-more-p288-terminal-success|"
    "reject=foreign,malformed,partial,unknown-detail|zero=ambiguous|"
    f"positions={','.join(f'{stage:02x}:{item:02x}' for stage, item in POSITION_SEQUENCE)}|"
    f"exact={','.join(f'{value:03x}' for value in spec.DETAIL_VALUES)}|"
    f"spec={spec.SCHEMA}|model={model.SCHEMA}"
)
POLICY_SHA256 = hashlib.sha256(POLICY_PREIMAGE.encode("ascii")).hexdigest()
POLICY_ID = POLICY_SHA256[:32]

DecodeError = model.DesignError


def encode_slot(
    header: bytes,
    *,
    generation: int,
    stage: int,
    outcome: int,
    item_index: int,
    detail: int,
) -> bytes:
    return model._encode_slot(  # noqa: SLF001
        header,
        model.Slot(
            generation & 1,
            generation,
            stage,
            outcome,
            item_index,
            detail,
        ),
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
            "item_index": slot["item_index"],
            "position_name": (
                "entry"
                if slot["generation"] == 0
                else spec.position_for_generation(
                    slot["generation"]
                ).name
            ),
            **decode_detail(slot["detail"]),
        }
        for slot in result["valid_slots"]
    ]
    active = result["active"]
    result["active_semantics"] = {
        "position_name": (
            "entry"
            if active["generation"] == 0
            else spec.position_for_generation(active["generation"]).name
        ),
        **decode_detail(active["detail"]),
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
