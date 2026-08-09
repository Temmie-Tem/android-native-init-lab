#!/usr/bin/env python3
"""Recover committed P3.13 intermediate contradictions from retained bytes."""

from __future__ import annotations

from typing import Any

import s22plus_fyg8_p312_telemetry_decoder as inherited
import s22plus_fyg8_p313_postlive_carrier_model as model
import s22plus_fyg8_p313_telemetry_decoder as frozen
import s22plus_fyg8_p313_telemetry_spec as spec


SCHEMA = "s22plus_fyg8_p313_postlive_decoder_v1"
DECODER_ID = "s22plus_fyg8_p313_postlive_intermediate_contradiction_v1"


def decode_detail(
    value: int,
    *,
    outcome: int | None = None,
    generation: int | None = None,
) -> dict[str, Any]:
    if value in spec.CONTRADICTION_DETAIL_NAMES:
        return {
            "detail_kind": "p313-observer-contradiction",
            "detail_name": spec.CONTRADICTION_DETAIL_NAMES[value],
            "telemetry": {
                "kind": "observer-contradiction",
                "name": spec.CONTRADICTION_DETAIL_NAMES[value],
                "intermediate_generation": generation not in {
                    None,
                    spec.SUMMARY_ORDINAL + 1,
                },
            },
        }
    return frozen.decode_detail(value, outcome=outcome, generation=generation)


def _with_semantics(result: dict[str, Any]) -> dict[str, Any]:
    frozen._with_semantics(result)  # noqa: SLF001
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
    return result


def decode_record(
    record: bytes,
    *,
    expected_profile: str = spec.PROFILE,
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
    complete = 0
    contradictions = 0
    for record in result.get("records", ()):
        _with_semantics(record)
        active = record["active"]
        if (
            active["outcome"] == model.OUTCOME_FAILURE
            and active["detail"] in spec.CONTRADICTION_DETAIL_NAMES
        ):
            contradictions += 1
            continue
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
