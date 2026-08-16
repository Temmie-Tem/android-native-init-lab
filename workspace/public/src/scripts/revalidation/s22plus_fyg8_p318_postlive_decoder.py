#!/usr/bin/env python3
"""Classify the retained P3.18 EUD-cache failure without device access."""

from __future__ import annotations

from typing import Any

import s22plus_fyg8_p318_postlive_carrier_model as model


SCHEMA = "s22plus_fyg8_p318_postlive_eud_decoder_v2"
DECODER_ID = "s22plus_fyg8_p318_postlive_eud_index_drift_v2"
CLASSIFICATION = "NO_PROOF_EXPERIMENT_PRECONDITION"
DETAIL_NAME = "eud-cache-read-before-explicit-eud-module-load"


def _json_safe(value: Any) -> Any:
    if isinstance(value, bytes):
        return {"encoding": "hex", "value": value.hex()}
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return value


def _is_exact_failure(slot: dict[str, Any]) -> bool:
    return (
        slot.get("generation") == model.FAILURE_GENERATION
        and slot.get("stage") == model.FAILURE_STAGE
        and slot.get("outcome") == model.OUTCOME_FAILURE
        and slot.get("item_index") == model.FAILURE_ITEM_INDEX
        and slot.get("detail") == model.FAILURE_DETAIL
        and slot.get("payload_kind") == model.PAYLOAD_NONE
        and slot.get("payload") in (b"", "")
    )


def _attach_semantics(record: dict[str, Any]) -> dict[str, Any]:
    if _is_exact_failure(record.get("active", {})):
        record["active_semantics"] = {
            **record["active"],
            "detail_name": DETAIL_NAME,
            "effective_proof": CLASSIFICATION,
            "max77705_diagnostic_reached": False,
            "explicit_eud_module_load_reached": False,
            "specific_eud_cache_failure_proved": True,
        }
    return record


def decode_record(
    record: bytes,
    *,
    expected_profile: str = "E2",
    expected_run_id: bytes | None = None,
) -> dict[str, Any]:
    decoded = model.decode_record(
        record,
        expected_profile=expected_profile,
        expected_run_id=expected_run_id,
    )
    return _json_safe(_attach_semantics(decoded))


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
    exact = 0
    for record in result.get("records", ()):
        _attach_semantics(record)
        exact += int(_is_exact_failure(record.get("active", {})))
    exact_shape = {
        "embedded_family_count": 0,
        "entry_count": 0,
        "exact_record_count": 1,
        "failure_count": 1,
        "fallback_record_count": 0,
        "family_count": 1,
        "foreign_count": 0,
        "long_record_count": 1,
        "minimum_candidate_boots": 1,
        "progress_count": 0,
        "success_count": 0,
        "unsat_count": 0,
    }
    if (
        result.get("integrity_issue")
        or result.get("integrity_issues") != []
        or result.get("residual_zero_meanings") != []
        or result.get("classification") != "E2_FAILURE_OBSERVED"
        or result.get("accepted") is not False
        or any(result.get(key) != value for key, value in exact_shape.items())
        or exact != 1
        or len(result.get("records", ())) != 1
    ):
        raise model.DesignError("P3.18 post-live observation lacks one exact clean failure")
    result["classification"] = CLASSIFICATION
    result["accepted"] = False
    result["telemetry_count"] = 0
    result["contradiction_count"] = 0
    result["precondition_failure_count"] = 1
    result["max77705_result_count"] = 0
    result["causal_result_allowed"] = False
    return _json_safe(result)
