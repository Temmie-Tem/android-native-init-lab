#!/usr/bin/env python3
"""Decode P3.06 two-slot DWC3 MSM IPC state-machine telemetry."""

from __future__ import annotations

import hashlib
from typing import Any

import s22plus_fyg8_p301_telemetry_decoder as inherited
import s22plus_fyg8_p301_telemetry_model as model
import s22plus_fyg8_p306_ipc_spec as spec


SCHEMA = "s22plus_fyg8_p306_ipc_telemetry_decoder_v1"
DECODER_ID = "s22plus_fyg8_p306_two_slot_dwc3_msm_ipc_v1"
PROFILE = spec.PROFILE
POLICY_PREIMAGE = (
    "S22PLUS_FYG8_P306_IPC_TELEMETRY_DECODER_V1|"
    "a=ordinal105-progress-d01-d80|"
    "b=ordinal106-failure-4001-4800|"
    "contradiction=6001-6006|"
    "chain=mode-qrw-bsv-inputs-start-peripheral"
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
    if generation in {None, spec.CHAIN_ORDINAL + 1}:
        try:
            chain = spec.decode_chain(value)
        except ValueError:
            pass
        else:
            return {
                "detail_kind": "dwc3-msm-ipc-chain",
                "detail_name": "dwc3-msm-ipc-marker-mask",
                "telemetry": {"kind": "dwc3-msm-ipc-chain", **chain},
            }
    if generation in {None, spec.SUMMARY_ORDINAL + 1}:
        try:
            summary = spec.decode_summary(value)
        except ValueError:
            pass
        else:
            return {
                "detail_kind": "dwc3-msm-ipc-summary",
                "detail_name": "dwc3-msm-ipc-summary-complete",
                "telemetry": {
                    "kind": "dwc3-msm-ipc-summary",
                    "ipc_log_complete": True,
                    **summary,
                },
            }
    contradiction_names = {
        spec.DETAIL_MOUNT_FAILED: "debugfs-mount-failed",
        spec.DETAIL_PATH_UNAVAILABLE: "ipc-log-path-unavailable",
        spec.DETAIL_READ_FAILED: "ipc-log-read-failed",
        spec.DETAIL_FORMAT_CONTRADICTION: "ipc-log-format-contradiction",
        spec.DETAIL_CLEANUP_FAILED: "ipc-log-cleanup-failed",
        spec.DETAIL_LIFECYCLE_CONTRADICTION: "ipc-log-lifecycle-contradiction",
    }
    if value in contradiction_names:
        return {
            "detail_kind": "p306-observer-contradiction",
            "detail_name": contradiction_names[value],
            "telemetry": {"kind": "p306-observer-contradiction"},
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
        if row["generation"] == spec.CHAIN_ORDINAL + 1
        and row["outcome"] == spec.OUTCOME_PROGRESS
        and spec.CHAIN_DETAIL_BASE <= row["detail"] <= spec.CHAIN_DETAIL_MAX
    ]
    b = [
        row for row in result["slot_semantics"]
        if row["generation"] == spec.SUMMARY_ORDINAL + 1
        and row["outcome"] == spec.OUTCOME_FAILURE
        and spec.SUMMARY_DETAIL_BASE <= row["detail"] <= spec.SUMMARY_DETAIL_MAX
    ]
    if len(a) == 1 and len(b) == 1:
        result["p306_pair"] = {
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
        spec.DETAIL_MOUNT_FAILED,
        spec.DETAIL_PATH_UNAVAILABLE,
        spec.DETAIL_READ_FAILED,
        spec.DETAIL_FORMAT_CONTRADICTION,
        spec.DETAIL_CLEANUP_FAILED,
        spec.DETAIL_LIFECYCLE_CONTRADICTION,
    }
    for record in result.get("records", ()):
        _with_semantics(record)
        if "p306_pair" in record:
            pairs += 1
        if record["active"]["detail"] in contradiction_values:
            contradictions += 1
    result["telemetry_count"] = pairs
    result["contradiction_count"] = contradictions
    if not result["integrity_issue"]:
        if contradictions:
            result["classification"] = "P306_TELEMETRY_CONTRADICTION"
            result["accepted"] = False
        elif pairs:
            result["classification"] = "P306_TELEMETRY_ONE_OR_MORE_BOOTS"
            result["accepted"] = True
    return result
