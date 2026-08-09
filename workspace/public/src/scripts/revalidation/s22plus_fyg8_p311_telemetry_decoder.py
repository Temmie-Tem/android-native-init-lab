#!/usr/bin/env python3
"""Decode the P3.11 early-clock and QSCRATCH retained pair."""

from __future__ import annotations

import hashlib
from typing import Any

import s22plus_fyg8_p308_telemetry_decoder as inherited
import s22plus_fyg8_p308_telemetry_spec as p308
import s22plus_fyg8_p311_telemetry_model as model
import s22plus_fyg8_p311_telemetry_spec as spec


SCHEMA = "s22plus_fyg8_p311_telemetry_decoder_v1"
DECODER_ID = "s22plus_fyg8_p311_early_hsphy_clock_v1"
PROFILE = spec.PROFILE
POLICY_PREIMAGE = (
    "S22PLUS_FYG8_P311_TELEMETRY_DECODER_V1|"
    "a=first-clock-pair-or-no-path-d00-d51|"
    "b=domain-multipath-reach-qscratch-4001-4640|"
    "degraded-b=p308-6100-673f"
)
POLICY_SHA256 = hashlib.sha256(POLICY_PREIMAGE.encode("ascii")).hexdigest()
POLICY_ID = POLICY_SHA256[:32]
DecodeError = model.DesignError


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
                "detail_kind": "p311-early-clock-summary",
                "detail_name": "domain-multipath-reach-and-qscratch",
                "telemetry": {"kind": "p311-early-clock-summary", **summary},
            }
    if generation in {None, spec.ATTR_ORDINAL + 1}:
        try:
            first = spec.decode_first(value)
        except ValueError:
            pass
        else:
            return {
                "detail_kind": "p311-first-clock-result",
                "detail_name": "first-actual-clock-path-result",
                "telemetry": first,
            }
    if value in spec.CONTRADICTION_DETAIL_NAMES:
        return {
            "detail_kind": "p311-observer-contradiction",
            "detail_name": spec.CONTRADICTION_DETAIL_NAMES[value],
            "telemetry": {"kind": "p311-observer-contradiction"},
        }
    return inherited.decode_detail(value, outcome=outcome, generation=generation)


def _with_semantics(result: dict[str, Any]) -> dict[str, Any]:
    result["slot_semantics"] = [
        {
            **slot,
            **decode_detail(
                slot["detail"],
                outcome=slot["outcome"],
                generation=slot["generation"],
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
        result["p311_pair"] = {
            "kind": "normal",
            "a": {
                **a,
                **decode_detail(a["detail"], generation=spec.ATTR_ORDINAL + 1),
            },
            "b": {
                **b,
                **decode_detail(b["detail"], generation=spec.SUMMARY_ORDINAL + 1),
            },
            "adjacent_generations": True,
            "observer_complete": True,
        }
    elif (
        spec.FIRST_DETAIL_BASE <= a["detail"] <= spec.FIRST_DETAIL_MAX
        and p308.DEGRADED_DETAIL_BASE <= b["detail"] <= p308.DEGRADED_DETAIL_MAX
    ):
        result["p311_pair"] = {
            "kind": "degraded",
            "a": {
                **a,
                **decode_detail(a["detail"], generation=spec.ATTR_ORDINAL + 1),
            },
            "b": {
                **b,
                **inherited.decode_detail(
                    b["detail"], generation=spec.SUMMARY_ORDINAL + 1
                ),
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
    return _with_semantics(
        model.decode_record(
            record,
            expected_profile=expected_profile,
            expected_run_id=expected_run_id,
        )
    )


def classify_clean_baseline(payload: bytes, *, expected_profile: str, expected_run_id: bytes):
    return model.classify_clean_baseline(
        payload, expected_profile=expected_profile, expected_run_id=expected_run_id
    )


def classify_observation(payload: bytes, *, expected_profile: str, expected_run_id: bytes):
    result = model.classify_observation(
        payload, expected_profile=expected_profile, expected_run_id=expected_run_id
    )
    normal = 0
    degraded = 0
    contradictions = 0
    for record in result.get("records", ()):
        _with_semantics(record)
        pair = record.get("p311_pair")
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
            result["classification"] = "P311_TELEMETRY_CONTRADICTION"
            result["accepted"] = False
        elif degraded:
            result["classification"] = "P311_DEGRADED_OBSERVER_CONTRADICTION"
            result["accepted"] = False
        elif normal:
            result["classification"] = "P311_TELEMETRY_ONE_OR_MORE_BOOTS"
            result["accepted"] = True
    return result
