#!/usr/bin/env python3
"""Post-live P2.88 semantic rendering without changing the bound decoder."""

from __future__ import annotations

from typing import Any

import s22plus_fyg8_p288_e1_decoder as base
import s22plus_fyg8_p288_latest_stage_model as model


SCHEMA = "s22plus_fyg8_p288_postlive_e3_decoder_v2"
DECODER_ID = "s22plus_fyg8_p288_postlive_pair_semantics_v2"
BASE_DECODER_ID = base.DECODER_ID


def _zero_detail_semantics(outcome: int, detail: int) -> dict[str, str]:
    if detail != 0:
        return {}
    if outcome == model.OUTCOME_PROGRESS:
        return {
            "detail_kind": "progress",
            "detail_name": "progress-no-diagnostic-detail",
        }
    if outcome == model.OUTCOME_SUCCESS:
        return {
            "detail_kind": "success",
            "detail_name": "terminal-success",
        }
    return {}


def _repair_semantics(result: dict[str, Any]) -> dict[str, Any]:
    slots_by_generation = {
        slot["generation"]: slot for slot in result["valid_slots"]
    }
    for semantics in result["slot_semantics"]:
        slot = slots_by_generation[semantics["generation"]]
        semantics.update(
            _zero_detail_semantics(slot["outcome"], slot["detail"])
        )
    active = result["active"]
    result["active_semantics"].update(
        _zero_detail_semantics(active["outcome"], active["detail"])
    )
    result["semantic_renderer"] = {
        "schema": SCHEMA,
        "decoder_id": DECODER_ID,
        "base_decoder_id": BASE_DECODER_ID,
        "scope": "post-live-rendering-only",
    }
    return result


def decode_record(
    record: bytes,
    *,
    expected_profile: str = base.PROFILE,
    expected_run_id: bytes | None = None,
) -> dict[str, Any]:
    return _repair_semantics(
        base.decode_record(
            record,
            expected_profile=expected_profile,
            expected_run_id=expected_run_id,
        )
    )


def classify_clean_baseline(
    payload: bytes,
    *,
    expected_profile: str,
    expected_run_id: bytes,
) -> dict[str, Any]:
    return base.classify_clean_baseline(
        payload,
        expected_profile=expected_profile,
        expected_run_id=expected_run_id,
    )


def classify_observation(
    payload: bytes,
    *,
    expected_profile: str,
    expected_run_id: bytes,
) -> dict[str, Any]:
    result = base.classify_observation(
        payload,
        expected_profile=expected_profile,
        expected_run_id=expected_run_id,
    )
    for record in result.get("records", ()):
        _repair_semantics(record)
    return result
