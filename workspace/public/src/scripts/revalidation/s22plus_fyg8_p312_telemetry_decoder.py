#!/usr/bin/env python3
"""Decode P3.12 early-clock telemetry from the Carrier-v2 retained record."""

from __future__ import annotations

import hashlib
from typing import Any

import s22plus_fyg8_p308_telemetry_decoder as inherited
import s22plus_fyg8_p308_telemetry_spec as p308
import s22plus_fyg8_p312_carrier_model as model
import s22plus_fyg8_p312_telemetry_spec as spec


SCHEMA = "s22plus_fyg8_p312_telemetry_decoder_v1"
DECODER_ID = "s22plus_fyg8_p312_carrier_v2_early_hsphy_clock_v1"
PROFILE = spec.PROFILE
TERMINAL_POSITION = spec.TERMINAL_POSITION
POLICY_PREIMAGE = (
    "S22PLUS_FYG8_P312_TELEMETRY_DECODER_V1|carrier=S22E1L2-192|"
    "a=first-clock-pair-or-no-path-d00-d51|"
    "b=domain-multipath-reach-qscratch-4001-4640|"
    "degraded-b=p308-6100-673f|profile=hits-ge-records"
)
POLICY_SHA256 = hashlib.sha256(POLICY_PREIMAGE.encode("ascii")).hexdigest()
POLICY_ID = POLICY_SHA256[:32]
DecodeError = model.DesignError


def _json_safe(value: Any) -> Any:
    if isinstance(value, bytes):
        return {"encoding": "hex", "value": value.hex()}
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    return value


def decode_detail(
    value: int,
    *,
    outcome: int | None = None,
    generation: int | None = None,
) -> dict[str, Any]:
    if generation in {None, spec.SUMMARY_ORDINAL + 1}:
        try:
            summary = spec.decode_summary(value)
        except ValueError:
            pass
        else:
            return {
                "detail_kind": "p312-early-clock-summary",
                "detail_name": "domain-multipath-reach-and-qscratch",
                "telemetry": {"kind": "p312-early-clock-summary", **summary},
            }
    if generation in {None, spec.ATTR_ORDINAL + 1}:
        try:
            first = spec.decode_first(value)
        except ValueError:
            pass
        else:
            return {
                "detail_kind": "p312-first-clock-result",
                "detail_name": "first-actual-clock-path-result",
                "telemetry": first,
            }
    if value in spec.CONTRADICTION_DETAIL_NAMES:
        return {
            "detail_kind": "p312-observer-contradiction",
            "detail_name": spec.CONTRADICTION_DETAIL_NAMES[value],
            "telemetry": {"kind": "p312-observer-contradiction"},
        }
    return inherited.decode_detail(value, outcome=outcome, generation=generation)


def _with_semantics(result: dict[str, Any]) -> dict[str, Any]:
    result["slot_semantics"] = [
        {
            **slot,
            **decode_detail(
                slot["detail"], outcome=slot["outcome"], generation=slot["generation"]
            ),
        }
        for slot in result["valid_slots"]
    ]
    result["active_semantics"] = {
        **result["active"],
        **decode_detail(
            result["active"]["detail"],
            outcome=result["active"]["outcome"],
            generation=result["active"]["generation"],
        ),
    }
    a_rows = [
        row for row in result["valid_slots"]
        if row["generation"] == spec.ATTR_ORDINAL + 1
        and row["outcome"] == model.OUTCOME_PROGRESS
    ]
    b_rows = [
        row for row in result["valid_slots"]
        if row["generation"] == spec.SUMMARY_ORDINAL + 1
        and row["outcome"] == model.OUTCOME_FAILURE
    ]
    if len(a_rows) != 1 or len(b_rows) != 1:
        return result
    a, b = a_rows[0], b_rows[0]
    if (
        spec.FIRST_DETAIL_BASE <= a["detail"] <= spec.FIRST_DETAIL_MAX
        and spec.SUMMARY_DETAIL_BASE <= b["detail"] <= spec.SUMMARY_DETAIL_MAX
    ):
        result["p312_pair"] = {
            "kind": "normal",
            "a": {**a, **decode_detail(a["detail"], generation=spec.ATTR_ORDINAL + 1)},
            "b": {**b, **decode_detail(b["detail"], generation=spec.SUMMARY_ORDINAL + 1)},
            "adjacent_generations": True,
            "observer_complete": True,
        }
    elif (
        spec.FIRST_DETAIL_BASE <= a["detail"] <= spec.FIRST_DETAIL_MAX
        and p308.DEGRADED_DETAIL_BASE <= b["detail"] <= p308.DEGRADED_DETAIL_MAX
    ):
        result["p312_pair"] = {
            "kind": "degraded",
            "a": {**a, **decode_detail(a["detail"], generation=spec.ATTR_ORDINAL + 1)},
            "b": {
                **b,
                **inherited.decode_detail(b["detail"], generation=spec.SUMMARY_ORDINAL + 1),
            },
            "adjacent_generations": True,
            "observer_complete": False,
            "evidence_bearing_observer_contradiction": True,
        }
    return result


def decode_record(
    record: bytes,
    *,
    expected_profile: str = PROFILE,
    expected_run_id: bytes | None = None,
) -> dict[str, Any]:
    return _json_safe(
        _with_semantics(
            model.decode_record(
                record,
                expected_profile=expected_profile,
                expected_run_id=expected_run_id,
            )
        )
    )


def classify_clean_baseline(
    payload: bytes, *, expected_profile: str, expected_run_id: bytes
) -> dict[str, Any]:
    return _json_safe(
        model.classify_clean_baseline(
            payload, expected_profile=expected_profile, expected_run_id=expected_run_id
        )
    )


def classify_observation(
    payload: bytes, *, expected_profile: str, expected_run_id: bytes
) -> dict[str, Any]:
    result = model.classify_observation(
        payload, expected_profile=expected_profile, expected_run_id=expected_run_id
    )
    normal = 0
    degraded = 0
    contradictions = 0
    for record in result.get("records", ()):
        _with_semantics(record)
        pair = record.get("p312_pair")
        if pair is not None and pair["kind"] == "normal":
            normal += 1
        elif pair is not None and pair["kind"] == "degraded":
            degraded += 1
        if record["active"]["detail"] in spec.CONTRADICTION_DETAIL_NAMES:
            contradictions += 1
    result["telemetry_count"] = normal
    result["degraded_count"] = degraded
    result["contradiction_count"] = contradictions + degraded
    if not result["integrity_issue"]:
        if contradictions:
            result["classification"] = "P312_TELEMETRY_CONTRADICTION"
            result["accepted"] = False
        elif degraded:
            result["classification"] = "P312_DEGRADED_OBSERVER_CONTRADICTION"
            result["accepted"] = False
        elif normal:
            result["classification"] = "P312_TELEMETRY_ONE_OR_MORE_BOOTS"
            result["accepted"] = True
    return _json_safe(result)
