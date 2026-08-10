#!/usr/bin/env python3
"""P3.15 telemetry semantics over the unchanged P3.14 value sets."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

import s22plus_fyg8_p314_telemetry_spec as inherited


SCHEMA = "s22plus_fyg8_p315_telemetry_spec_v1"
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
STOP_CLEAN_RECORDS = inherited.STOP_CLEAN_RECORDS
RESTART_CLEAN_RECORDS = 41
FINAL_CLEAN_RECORDS = inherited.FINAL_CLEAN_RECORDS
FINAL_DRIFT_RECORDS = inherited.FINAL_DRIFT_RECORDS
CYCLE_OVERFLOW_RECORDS = inherited.CYCLE_OVERFLOW_RECORDS

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
LEGACY_GENERIC_MULTIPLICITY_DETAIL = inherited.LEGACY_GENERIC_MULTIPLICITY_DETAIL
PAIR_MASK_DETAIL_BASE = inherited.PAIR_MASK_DETAIL_BASE
PAIR_MASK_DETAIL_MIN = inherited.PAIR_MASK_DETAIL_MIN
PAIR_MASK_DETAIL_MAX = inherited.PAIR_MASK_DETAIL_MAX
PAIR_MASK_VALUE_COUNT = inherited.PAIR_MASK_VALUE_COUNT

PROFILE_ONLY_NESTED_HIT_DETAIL = 0x6721
GADGET_START_ZERO_WITHOUT_RUN_ON_DETAIL = 0x6722
RUN_ON_PROVENANCE_CONTRADICTION_DETAIL = 0x6723
P315_RESERVED_NAMES = {
    PROFILE_ONLY_NESTED_HIT_DETAIL: "profile-only-nested-hit",
    GADGET_START_ZERO_WITHOUT_RUN_ON_DETAIL: (
        "gadget-start-zero-without-run-on"
    ),
    RUN_ON_PROVENANCE_CONTRADICTION_DETAIL: (
        "run-on-provenance-contradiction"
    ),
}

encode_a = inherited.encode_a
decode_a = inherited.decode_a
encode_normal = inherited.encode_normal
encode_direct = inherited.encode_direct
encode_controller = inherited.encode_controller
encode_drift = inherited.encode_drift
encode_pair_mask = inherited.encode_pair_mask
decode_pair_mask = inherited.decode_pair_mask


def decode_b(detail: int) -> dict[str, Any]:
    decoded = inherited.decode_b(detail)
    if detail in P315_RESERVED_NAMES:
        if decoded.get("kind") != "observer-contradiction":
            raise ValueError("P3.15 reserved contradiction domain differs")
        return {
            "kind": "observer-contradiction",
            "name": P315_RESERVED_NAMES[detail],
        }
    return decoded


@lru_cache(maxsize=1)
def a_outputs() -> tuple[int, ...]:
    return inherited.a_outputs()


@lru_cache(maxsize=1)
def a_output_set() -> frozenset[int]:
    return inherited.a_output_set()


@lru_cache(maxsize=1)
def b_outputs() -> tuple[int, ...]:
    return inherited.b_outputs()


@lru_cache(maxsize=1)
def matrix_b_values() -> tuple[int, ...]:
    return inherited.matrix_b_values()


@lru_cache(maxsize=1)
def matrix_b_value_set() -> frozenset[int]:
    return inherited.matrix_b_value_set()


matrix_expected_acceptance = inherited.matrix_expected_acceptance
matrix_cell_count = inherited.matrix_cell_count
validate_slot = inherited.validate_slot


def validate() -> dict[str, Any]:
    base = inherited.validate()
    for detail, name in P315_RESERVED_NAMES.items():
        decoded = decode_b(detail)
        if decoded != {"kind": "observer-contradiction", "name": name}:
            raise ValueError("P3.15 reserved detail semantics differ")
    if (
        len(a_outputs()) != 126
        or len(b_outputs()) != 2_222
        or len(matrix_b_values()) != 2_223
        or matrix_cell_count() != 251_450
    ):
        raise ValueError("P3.15 inherited output extent differs")
    return {
        **base,
        "schema": SCHEMA,
        "restart_clean_records": RESTART_CLEAN_RECORDS,
        "reserved_detail_names": {
            f"0x{detail:04x}": name
            for detail, name in sorted(P315_RESERVED_NAMES.items())
        },
        "inherited_output_sets_unchanged": True,
        "historical_p314_decoder_unchanged": True,
        "verified": True,
    }


if __name__ == "__main__":
    import json

    print(json.dumps(validate(), sort_keys=True))
