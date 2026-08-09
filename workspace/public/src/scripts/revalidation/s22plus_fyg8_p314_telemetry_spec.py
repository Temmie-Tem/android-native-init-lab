#!/usr/bin/env python3
"""P3.14 source-normalized cycle telemetry contract."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

import s22plus_fyg8_p313_successor_hazard_contract as hazard
import s22plus_fyg8_p313_telemetry_spec as inherited


SCHEMA = "s22plus_fyg8_p314_telemetry_spec_v1"
PROFILE = inherited.PROFILE
ATTR_ORDINAL = inherited.ATTR_ORDINAL
SUMMARY_ORDINAL = inherited.SUMMARY_ORDINAL
OUTCOME_PROGRESS = inherited.OUTCOME_PROGRESS
OUTCOME_FAILURE = inherited.OUTCOME_FAILURE
POSITIONS = inherited.POSITIONS
TERMINAL_POSITION = inherited.TERMINAL_POSITION
position_for_generation = inherited.position_for_generation
SpecError = inherited.SpecError

ROLE_EVENT_COUNT = inherited.ROLE_EVENT_COUNT
DIRECT_EVENT_COUNT = inherited.DIRECT_EVENT_COUNT
CYCLE_EVENT_COUNT = inherited.CYCLE_EVENT_COUNT
RECORD_CAPACITY = inherited.RECORD_CAPACITY
DIRECT_PREFIX_CAPACITY = inherited.DIRECT_PREFIX_CAPACITY
DIRECT_CLEAN_PREFIX = inherited.DIRECT_CLEAN_PREFIX
DIRECT_DRIFT_PREFIX_MAX = inherited.DIRECT_DRIFT_PREFIX_MAX
DIRECT_CONTRADICTION_PREFIX_MIN = inherited.DIRECT_CONTRADICTION_PREFIX_MIN
STOP_CLEAN_RECORDS = 14
FINAL_CLEAN_RECORDS = 41
FINAL_DRIFT_RECORDS = 49
CYCLE_OVERFLOW_RECORDS = 65

A_DETAIL_BASE = inherited.A_DETAIL_BASE
A_DETAIL_MAX = inherited.A_DETAIL_MAX
A_VALUE_COUNT = inherited.A_VALUE_COUNT
NORMAL_DETAIL_BASE = inherited.NORMAL_DETAIL_BASE
NORMAL_DETAIL_MAX = inherited.NORMAL_DETAIL_MAX
DIRECT_DETAIL_BASE = inherited.DIRECT_DETAIL_BASE
DIRECT_DETAIL_MAX = inherited.DIRECT_DETAIL_MAX
CONTROLLER_DETAIL_BASE = inherited.CONTROLLER_DETAIL_BASE
CONTROLLER_DETAIL_MAX = inherited.CONTROLLER_DETAIL_MAX
DRIFT_DETAIL_BASE = inherited.DRIFT_DETAIL_BASE
DRIFT_DETAIL_MAX = inherited.DRIFT_DETAIL_MAX
CONTRADICTION_DETAIL_BASE = inherited.CONTRADICTION_DETAIL_BASE
CONTRADICTION_DETAIL_MAX = inherited.CONTRADICTION_DETAIL_MAX
LEGACY_GENERIC_MULTIPLICITY_DETAIL = 0x6712
PAIR_MASK_DETAIL_BASE = hazard.PAIR_MASK_DETAIL_BASE
PAIR_MASK_DETAIL_MIN = hazard.PAIR_MASK_DETAIL_MIN
PAIR_MASK_DETAIL_MAX = hazard.PAIR_MASK_DETAIL_MAX
PAIR_MASK_VALUE_COUNT = hazard.PAIR_MASK_VALUE_COUNT

encode_a = inherited.encode_a
decode_a = inherited.decode_a
encode_normal = inherited.encode_normal
encode_direct = inherited.encode_direct
encode_controller = inherited.encode_controller
encode_drift = inherited.encode_drift


def encode_pair_mask(mask: int) -> int:
    return hazard.encode_pair_mask(mask)


def decode_pair_mask(detail: int) -> dict[str, Any]:
    names = hazard.decode_pair_mask(detail)
    return {
        "kind": "source-normalized-pair-excess",
        "pair_mask": detail - PAIR_MASK_DETAIL_BASE,
        "pairs": list(names),
        "cycle_causal_claim": False,
    }


def decode_b(detail: int) -> dict[str, Any]:
    if PAIR_MASK_DETAIL_MIN <= detail <= PAIR_MASK_DETAIL_MAX:
        return decode_pair_mask(detail)
    return inherited.decode_b(detail)


@lru_cache(maxsize=1)
def a_outputs() -> tuple[int, ...]:
    return inherited.a_outputs()


@lru_cache(maxsize=1)
def a_output_set() -> frozenset[int]:
    return frozenset(a_outputs())


@lru_cache(maxsize=1)
def b_outputs() -> tuple[int, ...]:
    values = set(inherited.b_outputs())
    values.remove(LEGACY_GENERIC_MULTIPLICITY_DETAIL)
    values.update(
        encode_pair_mask(mask) for mask in range(1, hazard.PAIR_MASK_MAX + 1)
    )
    return tuple(sorted(values))


@lru_cache(maxsize=1)
def matrix_b_values() -> tuple[int, ...]:
    return tuple(sorted({*b_outputs(), LEGACY_GENERIC_MULTIPLICITY_DETAIL}))


@lru_cache(maxsize=1)
def matrix_b_value_set() -> frozenset[int]:
    return frozenset(matrix_b_values())


def matrix_expected_acceptance(*, family: str, generation: int) -> bool:
    """Return the source-authorized position rule for one matrix family."""

    position_for_generation(generation)
    if family == "a":
        return generation == ATTR_ORDINAL + 1
    if family in {"b", "progress-zero"}:
        return True
    raise ValueError("P3.14 matrix family differs")


def matrix_cell_count() -> int:
    return (
        len(a_outputs()) + len(matrix_b_values()) + 1
    ) * len(POSITIONS)


def validate_slot(
    *, generation: int, stage: int, outcome: int, item_index: int, detail: int
) -> None:
    position = position_for_generation(generation)
    if (stage, item_index) != position.pair:
        raise SpecError("P3.14 carrier position differs")
    if outcome == OUTCOME_PROGRESS and detail == 0:
        return
    if (
        generation == ATTR_ORDINAL + 1
        and outcome == OUTCOME_PROGRESS
        and detail in a_output_set()
    ):
        return
    if outcome == OUTCOME_FAILURE and detail in matrix_b_value_set():
        return
    raise SpecError("P3.14 retained generation differs")


def validate() -> dict[str, Any]:
    a_values = a_outputs()
    b_values = b_outputs()
    matrix_values = matrix_b_values()
    if len(a_values) != 126:
        raise ValueError("P3.14 A extent differs")
    if len(b_values) != 2_222:
        raise ValueError("P3.14 B extent differs")
    if len(matrix_values) != 2_223:
        raise ValueError("P3.14 matrix B union differs")
    if matrix_cell_count() != 251_450:
        raise ValueError("P3.14 matrix cell count differs")
    if LEGACY_GENERIC_MULTIPLICITY_DETAIL in b_values:
        raise ValueError("P3.14 legacy multiplicity remained emit-capable")
    if LEGACY_GENERIC_MULTIPLICITY_DETAIL not in matrix_values:
        raise ValueError("P3.14 legacy decode-only detail disappeared")
    for detail in a_values:
        decode_a(detail)
    for detail in b_values:
        decode_b(detail)
    return {
        "schema": SCHEMA,
        "a_detail_range": [A_DETAIL_BASE, A_DETAIL_MAX],
        "a_output_count": len(a_values),
        "b_output_count": len(b_values),
        "matrix_b_value_count": len(matrix_values),
        "matrix_cell_count": matrix_cell_count(),
        "pair_mask_detail_range": [PAIR_MASK_DETAIL_MIN, PAIR_MASK_DETAIL_MAX],
        "pair_mask_output_count": PAIR_MASK_VALUE_COUNT,
        "legacy_0x6712_decode_only": True,
        "role_event_count": ROLE_EVENT_COUNT,
        "direct_event_count": DIRECT_EVENT_COUNT,
        "cycle_event_count": CYCLE_EVENT_COUNT,
        "record_capacity": RECORD_CAPACITY,
        "direct_prefix_capacity": DIRECT_PREFIX_CAPACITY,
        "cycle_record_contract": [
            STOP_CLEAN_RECORDS,
            FINAL_CLEAN_RECORDS,
            FINAL_DRIFT_RECORDS,
            CYCLE_OVERFLOW_RECORDS,
        ],
        "fixed_image_gate_compatible": True,
        "verified": True,
    }


if __name__ == "__main__":
    import json

    print(json.dumps(validate(), sort_keys=True))
