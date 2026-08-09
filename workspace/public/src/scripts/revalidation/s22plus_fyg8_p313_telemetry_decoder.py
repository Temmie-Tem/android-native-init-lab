#!/usr/bin/env python3
"""Decode P3.13 post-bind resume-cycle Carrier-v2 telemetry."""

from __future__ import annotations

import hashlib
from typing import Any

import s22plus_fyg8_p312_carrier_model as model
import s22plus_fyg8_p312_telemetry_decoder as inherited
import s22plus_fyg8_p313_telemetry_spec as spec


SCHEMA = "s22plus_fyg8_p313_telemetry_decoder_v1"
DECODER_ID = "s22plus_fyg8_p313_carrier_v2_post_bind_resume_cycle_v1"
PROFILE = spec.PROFILE
TERMINAL_POSITION = spec.TERMINAL_POSITION
POLICY_PREIMAGE = (
    "S22PLUS_FYG8_P313_TELEMETRY_DECODER_V1|carrier=S22E1L2-192|"
    "a=cycle-state-speed-d00-d7d|"
    "b=delta-4801-4c00,direct-4c01-4c02,controller-5001-5050,"
    "drift-5061-507f,contradiction-6701-673f"
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
            decoded = spec.decode_a(value)
        except ValueError:
            pass
        else:
            return {
                "detail_kind": "p313-cycle-state-speed",
                "detail_name": "cycle-attempt-state-and-speed",
                "telemetry": decoded,
            }
    if generation in {None, spec.SUMMARY_ORDINAL + 1}:
        try:
            decoded = spec.decode_b(value)
        except ValueError:
            pass
        else:
            return {
                "detail_kind": f"p313-{decoded['kind']}",
                "detail_name": decoded.get("name", decoded["kind"]),
                "telemetry": decoded,
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
        row
        for row in result["valid_slots"]
        if row["generation"] == spec.ATTR_ORDINAL + 1
        and row["outcome"] == model.OUTCOME_PROGRESS
    ]
    b_rows = [
        row
        for row in result["valid_slots"]
        if row["generation"] == spec.SUMMARY_ORDINAL + 1
        and row["outcome"] == model.OUTCOME_FAILURE
    ]
    if len(a_rows) != 1 or len(b_rows) != 1:
        return result
    a, b = a_rows[0], b_rows[0]
    try:
        a_semantics = spec.decode_a(a["detail"])
        b_semantics = spec.decode_b(b["detail"])
    except ValueError:
        return result
    result["p313_pair"] = {
        "kind": b_semantics["kind"],
        "a": {**a, **decode_detail(a["detail"], generation=a["generation"])},
        "b": {**b, **decode_detail(b["detail"], generation=b["generation"])},
        "adjacent_generations": True,
        "observer_complete": b_semantics["kind"] != "observer-contradiction",
        "cycle_attempted": a_semantics["cycle_attempted"] == 1,
    }
    return result


def decode_record(
    record: bytes,
    *,
    expected_profile: str = PROFILE,
    expected_run_id: bytes | None = None,
) -> dict[str, Any]:
    return inherited._json_safe(  # noqa: SLF001
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
    return inherited._json_safe(  # noqa: SLF001
        model.classify_clean_baseline(
            payload,
            expected_profile=expected_profile,
            expected_run_id=expected_run_id,
        )
    )


def classify_observation(
    payload: bytes, *, expected_profile: str, expected_run_id: bytes
) -> dict[str, Any]:
    result = model.classify_observation(
        payload,
        expected_profile=expected_profile,
        expected_run_id=expected_run_id,
    )
    complete = 0
    contradictions = 0
    for record in result.get("records", ()):
        _with_semantics(record)
        pair = record.get("p313_pair")
        if pair is None:
            continue
        if pair["observer_complete"]:
            complete += 1
        else:
            contradictions += 1
    result["telemetry_count"] = complete
    result["contradiction_count"] = contradictions
    if not result["integrity_issue"]:
        if contradictions:
            result["classification"] = "P313_OBSERVER_CONTRADICTION"
            result["accepted"] = False
        elif complete:
            result["classification"] = "P313_TELEMETRY_ONE_OR_MORE_BOOTS"
            result["accepted"] = True
    return inherited._json_safe(result)  # noqa: SLF001


if __name__ == "__main__":
    import json

    print(
        json.dumps(
            {
                "schema": SCHEMA,
                "decoder_id": DECODER_ID,
                "policy_id": POLICY_ID,
                "telemetry": spec.validate(),
            },
            sort_keys=True,
        )
    )
