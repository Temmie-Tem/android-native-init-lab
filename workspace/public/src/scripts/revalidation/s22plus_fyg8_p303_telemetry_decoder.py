#!/usr/bin/env python3
"""Decode P3.03 two-slot HS-PHY clock and kmsg telemetry."""

from __future__ import annotations

import hashlib
from typing import Any

import s22plus_fyg8_p301_telemetry_decoder as inherited
import s22plus_fyg8_p301_telemetry_model as model
import s22plus_fyg8_p303_stock_log_baseline as stock_log_baseline
import s22plus_fyg8_p303_telemetry_spec as spec


SCHEMA = "s22plus_fyg8_p303_hsphy_telemetry_decoder_v1"
DECODER_ID = "s22plus_fyg8_p303_two_slot_hsphy_silent_failure_v1"
PROFILE = spec.PROFILE
POLICY_PREIMAGE = (
    "S22PLUS_FYG8_P303_HSPHY_TELEMETRY_DECODER_V1|"
    "a=ordinal105-progress-clock-d00-da2|"
    "b=ordinal106-failure-kmsg-4001-4800|"
    "missed-ne-zero|stock-baseline=external-bound-d0|"
    f"sot={spec.descriptor_sha256()}"
)
POLICY_SHA256 = hashlib.sha256(POLICY_PREIMAGE.encode("ascii")).hexdigest()
POLICY_ID = POLICY_SHA256[:32]
DecodeError = model.DesignError


def compare_stock_baseline(candidate_detail: int, baseline: dict[str, Any]) -> dict[str, Any]:
    if (
        baseline.get("schema") != stock_log_baseline.SCHEMA
        or baseline.get("parser_id") != stock_log_baseline.PARSER_ID
        or baseline.get("valid") is not True
        or baseline.get("normal_path_seen") is not True
    ):
        raise DecodeError("P3.03 stock HS-PHY log baseline is invalid")
    candidate = spec.decode_log(candidate_detail)
    stock = {
        "first_offset": int(baseline["first_readback_failure_offset"]),
        "count_bucket": int(baseline["readback_count_bucket"]),
        "reset_mask": int(baseline["reset_failure_mask"]),
    }
    if stock != spec.decode_log(int(baseline["candidate_domain_detail"])):
        raise DecodeError("P3.03 stock baseline summary is internally inconsistent")
    candidate_has_failure = bool(candidate["count_bucket"] or candidate["reset_mask"])
    if not candidate_has_failure:
        classification = "CANDIDATE_LOGGED_PATHS_CLEAN"
        attributable = False
    elif candidate == stock:
        classification = "CANDIDATE_SIGNATURE_PRESENT_IN_WORKING_STOCK"
        attributable = False
    else:
        classification = "CANDIDATE_SIGNATURE_DIFFERS_FROM_WORKING_STOCK"
        attributable = True
    return {
        "classification": classification,
        "candidate": candidate,
        "stock": stock,
        "candidate_failure_attributable": attributable,
        "clock_prepare_enable_domain_separate": True,
    }


def _clock_state_name(state: int) -> str:
    if state == 0:
        return "success"
    bucket = (state - 1) % spec.CLOCK_ERRNO_BUCKETS
    kind = "prepare-failed" if state <= spec.CLOCK_ERRNO_BUCKETS else "enable-failed"
    return f"{kind}-errno-bucket-{bucket}"


def decode_detail(
    value: int,
    *,
    outcome: int | None = None,
    generation: int | None = None,
) -> dict[str, Any]:
    if generation in {None, spec.CLOCK_ORDINAL + 1}:
        try:
            clock = spec.decode_clock(value)
        except ValueError:
            pass
        else:
            telemetry: dict[str, Any] = {
                "kind": "hsphy-clock-return",
                "callsite_probe_armed": True,
                "clock_path_reached": clock["branch"] != "missed",
                **clock,
            }
            if clock["branch"] != "missed":
                telemetry["ref_src_state_name"] = _clock_state_name(
                    int(clock["ref_src_state"])
                )
                telemetry["ref_state_name"] = _clock_state_name(
                    int(clock["ref_state"])
                )
            return {
                "detail_kind": "hsphy-clock-return",
                "detail_name": (
                    "hsphy-clock-path-missed"
                    if clock["branch"] == "missed"
                    else "hsphy-clock-returns"
                ),
                "telemetry": telemetry,
            }
    if generation in {None, spec.LOG_ORDINAL + 1}:
        try:
            log = spec.decode_log(value)
        except ValueError:
            pass
        else:
            return {
                "detail_kind": "hsphy-kmsg-summary",
                "detail_name": "hsphy-kmsg-complete",
                "telemetry": {
                    "kind": "hsphy-kmsg-summary",
                    "kmsg_complete": True,
                    "normal_path_seen": True,
                    **log,
                },
            }
    if value in spec.CONTRADICTION_DETAIL_NAMES:
        return {
            "detail_kind": "p303-observer-contradiction",
            "detail_name": spec.CONTRADICTION_DETAIL_NAMES[value],
            "telemetry": {"kind": "p303-observer-contradiction"},
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
        if row["generation"] == spec.CLOCK_ORDINAL + 1
        and row["outcome"] == spec.OUTCOME_PROGRESS
        and spec.CLOCK_DETAIL_BASE <= row["detail"] <= spec.CLOCK_DETAIL_MAX
    ]
    b = [
        row for row in result["slot_semantics"]
        if row["generation"] == spec.LOG_ORDINAL + 1
        and row["outcome"] == spec.OUTCOME_FAILURE
        and spec.LOG_DETAIL_BASE <= row["detail"] <= spec.LOG_DETAIL_MAX
    ]
    if len(a) == 1 and len(b) == 1:
        result["p303_pair"] = {
            "a": a[0],
            "b": b[0],
            "adjacent_generations": True,
            "stock_log_baseline_required_for_failure_attribution": True,
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
    for record in result.get("records", ()):
        _with_semantics(record)
        if "p303_pair" in record:
            pairs += 1
        if record["active"]["detail"] in spec.CONTRADICTION_DETAIL_NAMES:
            contradictions += 1
    result["telemetry_count"] = pairs
    result["contradiction_count"] = contradictions
    if not result["integrity_issue"]:
        if contradictions:
            result["classification"] = "P303_TELEMETRY_CONTRADICTION"
            result["accepted"] = False
        elif pairs:
            result["classification"] = "P303_TELEMETRY_ONE_OR_MORE_BOOTS"
            result["accepted"] = True
    return result
