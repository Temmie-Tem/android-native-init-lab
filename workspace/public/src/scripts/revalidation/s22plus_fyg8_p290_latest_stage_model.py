#!/usr/bin/env python3
"""P2.90 pair-aware retained model with the unchanged 45-byte wire ABI."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

import s22plus_fyg8_p288_latest_stage_model as base
import s22plus_fyg8_p290_contract_spec as spec


SCHEMA = "s22plus_fyg8_p290_latest_stage_position_model_v1"
PROFILE = spec.PROFILE

LONG_FAMILY = base.LONG_FAMILY
UNSAT_FAMILY = base.UNSAT_FAMILY
LEGACY_FAMILIES = base.LEGACY_FAMILIES
FORMAT_VERSION = base.FORMAT_VERSION
REQUEST_VERSION = base.REQUEST_VERSION
LONG_RECORD_SIZE = base.LONG_RECORD_SIZE
LONG_HEADER_SIZE = base.LONG_HEADER_SIZE
SLOT_SIZE = base.SLOT_SIZE
SLOT_COUNT = base.SLOT_COUNT
UNSAT_SIZE = base.UNSAT_SIZE
RUN_ID_SIZE = base.RUN_ID_SIZE
OUTCOME_PROGRESS = base.OUTCOME_PROGRESS
OUTCOME_SUCCESS = base.OUTCOME_SUCCESS
OUTCOME_FAILURE = base.OUTCOME_FAILURE
PROFILE_NUMBERS = base.PROFILE_NUMBERS
PROFILE_BY_NUMBER = base.PROFILE_BY_NUMBER
STAGES = base.STAGES
REQUEST_STRUCT = base.REQUEST_STRUCT
SLOT_BODY_STRUCT = base.SLOT_BODY_STRUCT
Request = base.Request
Slot = base.Slot
DesignError = base.DesignError
crc32 = base.crc32
_record_header = base._record_header
_slot_crc = base._slot_crc
_validate_record_families = base._validate_record_families
_edge_family_partial = base._edge_family_partial
_family_positions = base._family_positions
unsat_record = base.unsat_record
model_run_id = base.model_run_id

PROFILE_POSITION_SEQUENCES = {PROFILE: spec.POSITION_SEQUENCE}
PROFILE_TERMINAL_POSITIONS = {PROFILE: spec.TERMINAL_POSITION}
PROFILE_TERMINALS = {PROFILE: spec.TERMINAL_STAGE}
_CONTEXT = {
    "spec": spec,
    "SCHEMA": SCHEMA,
    "PROFILE": PROFILE,
    "PROFILE_POSITION_SEQUENCES": PROFILE_POSITION_SEQUENCES,
    "PROFILE_TERMINAL_POSITIONS": PROFILE_TERMINAL_POSITIONS,
    "PROFILE_TERMINALS": PROFILE_TERMINALS,
}


@contextmanager
def base_context() -> Iterator[None]:
    previous = {name: getattr(base, name) for name in _CONTEXT}
    for name, value in _CONTEXT.items():
        setattr(base, name, value)
    try:
        yield
    finally:
        for name, value in previous.items():
            setattr(base, name, value)


def _call(name: str, *args, **kwargs):  # noqa: ANN002, ANN003, ANN202
    with base_context():
        return getattr(base, name)(*args, **kwargs)


def _require_run_id(run_id: bytes) -> None:
    return _call("_require_run_id", run_id)


def _sequence(profile: str) -> tuple[tuple[int, int], ...]:
    return _call("_sequence", profile)


def generation_for_position(
    profile: str, stage: int, item_index: int
) -> int:
    return _call(
        "generation_for_position", profile, stage, item_index
    )


def _validate_position_semantics(
    profile: str,
    generation: int,
    stage: int,
    outcome: int,
    item_index: int,
    detail: int,
) -> None:
    return _call(
        "_validate_position_semantics",
        profile,
        generation,
        stage,
        outcome,
        item_index,
        detail,
    )


def encode_request(*args, **kwargs):  # noqa: ANN002, ANN003, ANN201
    return _call("encode_request", *args, **kwargs)


def decode_request(data: bytes) -> Request:
    return _call("decode_request", data)


def _encode_slot(header: bytes, slot: Slot) -> bytes:
    return _call("_encode_slot", header, slot)


def _decode_slot(*args, **kwargs):  # noqa: ANN002, ANN003, ANN202
    return _call("_decode_slot", *args, **kwargs)


def initialize_record(profile: str, run_id: bytes) -> bytes:
    return _call("initialize_record", profile, run_id)


def decode_record(*args, **kwargs):  # noqa: ANN002, ANN003, ANN201
    return _call("decode_record", *args, **kwargs)


def apply_request(record: bytes, request_data: bytes) -> bytes:
    return _call("apply_request", record, request_data)


def _classify(*args, **kwargs):  # noqa: ANN002, ANN003, ANN202
    return _call("_classify", *args, **kwargs)


def classify_clean_baseline(*args, **kwargs):  # noqa: ANN002, ANN003, ANN201
    return _call("classify_clean_baseline", *args, **kwargs)


def classify_observation(*args, **kwargs):  # noqa: ANN002, ANN003, ANN201
    return _call("classify_observation", *args, **kwargs)
