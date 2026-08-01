#!/usr/bin/env python3
"""Decode P2.96 retained built-in DWC3 value telemetry."""

from __future__ import annotations

import hashlib
from typing import Any

import s22plus_fyg8_p294_telemetry_decoder as inherited
import s22plus_fyg8_p296_telemetry_model as model
import s22plus_fyg8_p296_telemetry_spec as spec


SCHEMA = "s22plus_fyg8_p296_builtin_dwc3_telemetry_decoder_v1"
DECODER_ID = "s22plus_fyg8_p296_two_slot_builtin_dwc3_telemetry_v1"
PROFILE = spec.PROFILE
POSITION_SEQUENCE = spec.POSITION_SEQUENCE
TERMINAL_POSITION = spec.TERMINAL_POSITION
POLICY_PREIMAGE = (
    "S22PLUS_FYG8_P296_BUILTIN_DWC3_TELEMETRY_DECODER_V1|"
    "layout=S22E1L1-45-ab-crc32|"
    "position=ordered-stage-item-pairs|"
    "delivery=boot-image-built-in-dwc3-only|"
    f"sot={spec.descriptor_sha256()}|model={model.SCHEMA}"
)
POLICY_SHA256 = hashlib.sha256(POLICY_PREIMAGE.encode("ascii")).hexdigest()
POLICY_ID = POLICY_SHA256[:32]
DecodeError = model.DesignError


def decode_detail(value: int, *, outcome: int | None = None) -> dict[str, Any]:
    result = inherited.decode_detail(value, outcome=outcome)
    try:
        mask = spec.decode_fixed_mismatch(value)
    except ValueError:
        return result
    result["detail_kind"] = spec.detail_kind(value)
    result["detail_name"] = spec.detail_name(value)
    result["telemetry"] = {
        "kind": "fixed-predicate-mismatch",
        "mask": mask,
        "run_stop": bool(mask & spec.FIXED_MISMATCH_RUN_STOP),
        "devctrlhlt": bool(mask & spec.FIXED_MISMATCH_DEVCTRLHLT),
        "prtcap": bool(mask & spec.FIXED_MISMATCH_PRTCAP),
    }
    return result


def _with_semantics(result: dict[str, Any]) -> dict[str, Any]:
    result["slot_semantics"] = [
        {
            "slot_id": slot["slot_id"],
            "generation": slot["generation"],
            "stage": slot["stage"],
            "item_index": slot["item_index"],
            "position_name": (
                "entry"
                if slot["generation"] == 0
                else spec.position_for_generation(slot["generation"]).name
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
            else spec.position_for_generation(active["generation"]).name
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
