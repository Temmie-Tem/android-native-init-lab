#!/usr/bin/env python3
"""Decode P3.15 Carrier-v2 telemetry without changing historical meanings."""

from __future__ import annotations

import hashlib
from typing import Any

import s22plus_fyg8_p312_telemetry_decoder as json_support
import s22plus_fyg8_p314_telemetry_decoder as inherited
import s22plus_fyg8_p315_carrier_model as model
import s22plus_fyg8_p315_telemetry_spec as spec


SCHEMA = "s22plus_fyg8_p315_telemetry_decoder_v1"
DECODER_ID = "s22plus_fyg8_p315_carrier_v2_live_profile_restart_v1"
PROFILE = spec.PROFILE
TERMINAL_POSITION = spec.TERMINAL_POSITION
POLICY_PREIMAGE = (
    "S22PLUS_FYG8_P315_TELEMETRY_DECODER_V1|carrier=S22E1L2-192|"
    "outputs=p314-identical|reserved=6721,6722,6723|"
    "legacy-6712=decode-only"
)
POLICY_SHA256 = hashlib.sha256(POLICY_PREIMAGE.encode("ascii")).hexdigest()
POLICY_ID = POLICY_SHA256[:32]
DecodeError = model.DesignError


def _validate_matrix_slot(slot: dict[str, Any]) -> None:
    generation = slot["generation"]
    outcome = slot["outcome"]
    detail = slot["detail"]
    if outcome == model.OUTCOME_PROGRESS and detail == 0:
        return
    if detail in spec.a_output_set():
        if outcome != model.OUTCOME_PROGRESS or not spec.matrix_expected_acceptance(
            family="a", generation=generation
        ):
            raise DecodeError("P3.15 A detail occupied an unauthorized position")
        return
    if detail in spec.matrix_b_value_set() and outcome != model.OUTCOME_FAILURE:
        raise DecodeError("P3.15 B detail used a non-failure outcome")


def decode_detail(
    value: int,
    *,
    outcome: int | None = None,
    generation: int | None = None,
) -> dict[str, Any]:
    if value in spec.P315_RESERVED_NAMES:
        if outcome not in {None, model.OUTCOME_FAILURE}:
            raise DecodeError("P3.15 reserved detail used a non-failure outcome")
        return {
            "detail_kind": "p315-observer-contradiction",
            "detail_name": spec.P315_RESERVED_NAMES[value],
            "telemetry": spec.decode_b(value),
        }
    return inherited.decode_detail(
        value, outcome=outcome, generation=generation
    )


def _with_semantics(result: dict[str, Any]) -> dict[str, Any]:
    for slot in result["valid_slots"]:
        _validate_matrix_slot(slot)
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
    result["p315_pair"] = {
        "kind": b_semantics["kind"],
        "a": {**a, **decode_detail(a["detail"], generation=a["generation"])},
        "b": {**b, **decode_detail(b["detail"], generation=b["generation"])},
        "adjacent_generations": True,
        "observer_complete": b_semantics["kind"] != "observer-contradiction",
        "cycle_attempted": a_semantics["cycle_attempted"] == 1,
        "cycle_causal_claim": b_semantics.get("cycle_causal_claim", True),
    }
    return result


def decode_record(
    record: bytes,
    *,
    expected_profile: str = PROFILE,
    expected_run_id: bytes | None = None,
) -> dict[str, Any]:
    return json_support._json_safe(  # noqa: SLF001
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
    return inherited.classify_clean_baseline(
        payload,
        expected_profile=expected_profile,
        expected_run_id=expected_run_id,
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
    pair_excess = 0
    for record in result.get("records", ()):
        _with_semantics(record)
        pair = record.get("p315_pair")
        active = record.get("active_semantics", {})
        if pair is not None and pair["kind"] == "source-normalized-pair-excess":
            pair_excess += 1
            contradictions += 1
        elif pair is not None and pair["observer_complete"]:
            complete += 1
        elif pair is not None:
            contradictions += 1
        elif active.get("outcome") == model.OUTCOME_FAILURE and (
            active.get("detail_kind") in {
                "p314-pair-excess",
                "p315-observer-contradiction",
            }
            or str(active.get("detail_kind", "")).endswith(
                "observer-contradiction"
            )
        ):
            if active.get("detail_kind") == "p314-pair-excess":
                pair_excess += 1
            contradictions += 1
    result["telemetry_count"] = complete
    result["contradiction_count"] = contradictions
    result["pair_excess_count"] = pair_excess
    if not result["integrity_issue"]:
        if contradictions:
            result["classification"] = "P315_OBSERVER_CONTRADICTION"
            result["accepted"] = False
        elif complete:
            result["classification"] = "P315_TELEMETRY_ONE_OR_MORE_BOOTS"
            result["accepted"] = True
    return json_support._json_safe(result)  # noqa: SLF001


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
