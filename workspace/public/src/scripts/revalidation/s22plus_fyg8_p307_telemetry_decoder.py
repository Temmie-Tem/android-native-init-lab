#!/usr/bin/env python3
"""Decode P3.07 two-slot EUD, clock, and QSCRATCH telemetry."""

from __future__ import annotations

import hashlib
from typing import Any

import s22plus_fyg8_p301_telemetry_model as model
import s22plus_fyg8_p303_telemetry_decoder as inherited
import s22plus_fyg8_p303_telemetry_spec as p303
import s22plus_fyg8_p307_telemetry_spec as spec


SCHEMA = "s22plus_fyg8_p307_telemetry_decoder_v1"
DECODER_ID = "s22plus_fyg8_p307_two_slot_eud_clock_qscratch_v1"
PROFILE = spec.PROFILE
POLICY_PREIMAGE = (
    "S22PLUS_FYG8_P307_TELEMETRY_DECODER_V1|"
    "a=ordinal105-progress-d00-d95|"
    "b=ordinal106-failure-4001-4feb|"
    "cache=probe-time-scm-synchronized|"
    "csr=later-nonsecure-direct|"
    "mismatch=no-causal-conclusion"
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
    if generation in {None, spec.ATTR_ORDINAL + 1}:
        try:
            attr = spec.decode_attribution(value)
        except ValueError:
            pass
        else:
            return {
                "detail_kind": "p307-eud-kmsg-attribution",
                "detail_name": "eud-cache-init-dpdm-preclock",
                "telemetry": {"kind": "p307-eud-kmsg-attribution", **attr},
            }
    if generation in {None, spec.SUMMARY_ORDINAL + 1}:
        try:
            summary = spec.decode_summary(value)
        except ValueError:
            pass
        else:
            return {
                "detail_kind": "p307-clock-qscratch-summary",
                "detail_name": "late-clock-and-qscratch-readback",
                "telemetry": {
                    "kind": "p307-clock-qscratch-summary",
                    **summary,
                },
            }
    contradiction_names = {
        **p303.CONTRADICTION_DETAIL_NAMES,
        **spec.CONTRADICTION_DETAIL_NAMES,
    }
    if value in contradiction_names:
        return {
            "detail_kind": "p307-observer-contradiction",
            "detail_name": contradiction_names[value],
            "telemetry": {"kind": "p307-observer-contradiction"},
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
    a = [
        row for row in result["slot_semantics"]
        if row["generation"] == spec.ATTR_ORDINAL + 1
        and row["outcome"] == spec.OUTCOME_PROGRESS
        and spec.ATTR_DETAIL_BASE <= row["detail"] <= spec.ATTR_DETAIL_MAX
    ]
    b = [
        row for row in result["slot_semantics"]
        if row["generation"] == spec.SUMMARY_ORDINAL + 1
        and row["outcome"] == spec.OUTCOME_FAILURE
        and spec.SUMMARY_DETAIL_BASE <= row["detail"] <= spec.SUMMARY_DETAIL_MAX
    ]
    if len(a) == 1 and len(b) == 1:
        result["p307_pair"] = {
            "a": a[0],
            "b": b[0],
            "adjacent_generations": True,
            "observer_complete": True,
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
    pairs = 0
    contradictions = 0
    contradiction_values = {
        *p303.CONTRADICTION_DETAIL_NAMES,
        *spec.CONTRADICTION_DETAIL_NAMES,
    }
    for record in result.get("records", ()):
        _with_semantics(record)
        if "p307_pair" in record:
            pairs += 1
        if record["active"]["detail"] in contradiction_values:
            contradictions += 1
    result["telemetry_count"] = pairs
    result["contradiction_count"] = contradictions
    if not result["integrity_issue"]:
        if contradictions:
            result["classification"] = "P307_TELEMETRY_CONTRADICTION"
            result["accepted"] = False
        elif pairs:
            result["classification"] = "P307_TELEMETRY_ONE_OR_MORE_BOOTS"
            result["accepted"] = True
    return result
