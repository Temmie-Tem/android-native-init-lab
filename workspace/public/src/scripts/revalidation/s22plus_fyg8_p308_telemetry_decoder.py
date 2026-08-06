#!/usr/bin/env python3
"""Decode P3.08 normal and degraded two-slot telemetry."""

from __future__ import annotations

import hashlib
from typing import Any

import s22plus_fyg8_p303_telemetry_spec as p303
import s22plus_fyg8_p307_telemetry_decoder as inherited
import s22plus_fyg8_p307_telemetry_spec as p307
import s22plus_fyg8_p308_telemetry_model as model
import s22plus_fyg8_p308_telemetry_spec as spec


SCHEMA = "s22plus_fyg8_p308_telemetry_decoder_v1"
DECODER_ID = "s22plus_fyg8_p308_two_slot_loss_resistant_v1"
PROFILE = spec.PROFILE
POLICY_PREIMAGE = (
    "S22PLUS_FYG8_P308_TELEMETRY_DECODER_V1|"
    "normal=a-attr-d00-d95+b-summary-4001-4feb|"
    "degraded=a-clock-d00-da2+b-site-mask-qscratch-6100-673f|"
    "pair-context-disambiguates-d00-and-4fc1"
)
POLICY_SHA256 = hashlib.sha256(POLICY_PREIMAGE.encode("ascii")).hexdigest()
POLICY_ID = POLICY_SHA256[:32]
DecodeError = model.DesignError


def _normal_a(value: int) -> dict[str, Any]:
    return {
        "detail_kind": "p308-eud-kmsg-attribution",
        "detail_name": "eud-cache-init-dpdm-preclock",
        "telemetry": {
            "kind": "p308-eud-kmsg-attribution",
            **p307.decode_attribution(value),
        },
    }


def _degraded_a(value: int) -> dict[str, Any]:
    return {
        "detail_kind": "p308-degraded-clock-witness",
        "detail_name": "clock-result-before-parser-degradation",
        "telemetry": {
            "kind": "p308-degraded-clock-witness",
            "clock_detail": value,
            "clock": p303.decode_clock(value),
        },
    }


def decode_detail(
    value: int,
    *,
    outcome: int | None = None,
    generation: int | None = None,
) -> dict[str, Any]:
    if generation in {None, spec.SUMMARY_ORDINAL + 1}:
        try:
            summary = p307.decode_summary(value)
        except ValueError:
            pass
        else:
            return {
                "detail_kind": "p308-clock-qscratch-summary",
                "detail_name": "late-clock-and-qscratch-readback",
                "telemetry": {
                    "kind": "p308-clock-qscratch-summary",
                    **summary,
                },
            }
        try:
            degraded = spec.decode_degraded(value)
        except ValueError:
            pass
        else:
            return {
                "detail_kind": "p308-degraded-observer-contradiction",
                "detail_name": "parser-site-prefix-mask-and-qscratch",
                "telemetry": {
                    "kind": "p308-degraded-observer-contradiction",
                    **degraded,
                },
            }
    if generation in {None, spec.ATTR_ORDINAL + 1}:
        try:
            return _normal_a(value)
        except ValueError:
            pass
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
        and row["outcome"] == spec.OUTCOME_PROGRESS
    ]
    b_rows = [
        row for row in result["valid_slots"]
        if row["generation"] == spec.SUMMARY_ORDINAL + 1
        and row["outcome"] == spec.OUTCOME_FAILURE
    ]
    if len(a_rows) != 1 or len(b_rows) != 1:
        return result
    a = a_rows[0]
    b = b_rows[0]
    if (
        spec.ATTR_DETAIL_BASE <= a["detail"] <= spec.ATTR_DETAIL_MAX
        and spec.SUMMARY_DETAIL_BASE <= b["detail"] <= spec.SUMMARY_DETAIL_MAX
    ):
        result["p308_pair"] = {
            "kind": "normal",
            "a": {**a, **_normal_a(a["detail"])},
            "b": {**b, **decode_detail(
                b["detail"], outcome=b["outcome"], generation=b["generation"]
            )},
            "adjacent_generations": True,
            "observer_complete": True,
        }
    elif (
        spec.CLOCK_DETAIL_BASE <= a["detail"] <= spec.CLOCK_DETAIL_MAX
        and spec.DEGRADED_DETAIL_BASE <= b["detail"] <= spec.DEGRADED_DETAIL_MAX
    ):
        result["p308_pair"] = {
            "kind": "degraded",
            "a": {**a, **_degraded_a(a["detail"])},
            "b": {**b, **decode_detail(
                b["detail"], outcome=b["outcome"], generation=b["generation"]
            )},
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
    inherited_contradictions = 0
    contradiction_values = {
        *p303.CONTRADICTION_DETAIL_NAMES,
        *p307.CONTRADICTION_DETAIL_NAMES,
    }
    for record in result.get("records", ()):
        _with_semantics(record)
        pair = record.get("p308_pair")
        if pair is not None and pair["kind"] == "normal":
            normal += 1
        elif pair is not None and pair["kind"] == "degraded":
            degraded += 1
        if record["active"]["detail"] in contradiction_values:
            inherited_contradictions += 1
    result["telemetry_count"] = normal
    result["degraded_count"] = degraded
    result["contradiction_count"] = inherited_contradictions + degraded
    if not result["integrity_issue"]:
        if inherited_contradictions:
            result["classification"] = "P308_TELEMETRY_CONTRADICTION"
            result["accepted"] = False
        elif degraded:
            result["classification"] = "P308_DEGRADED_OBSERVER_CONTRADICTION"
            result["accepted"] = False
        elif normal:
            result["classification"] = "P308_TELEMETRY_ONE_OR_MORE_BOOTS"
            result["accepted"] = True
    return result
