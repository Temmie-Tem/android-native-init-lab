#!/usr/bin/env python3
"""P3.01 retained-record model with ordinal-aware wide-band semantics."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

import s22plus_fyg8_p290_latest_stage_model as base
import s22plus_fyg8_p292_repair_spec as repair
import s22plus_fyg8_p301_telemetry_spec as spec


SCHEMA = "s22plus_fyg8_p301_device_event_subtype_telemetry_model_v1"
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
model_run_id = base.model_run_id
unsat_record = base.unsat_record


def _validate_position_semantics(
    profile: str,
    generation: int,
    stage: int,
    outcome: int,
    item_index: int,
    detail: int,
) -> None:
    if profile != PROFILE:
        raise DesignError(f"unsupported P3.01 profile: {profile}")
    ordinal = generation - 1
    p301_wide_semantics = (
        ordinal == spec.FINAL_STATE_ORDINAL
        or (
            ordinal == spec.EVENT_LINK_ORDINAL
            and detail in spec.CONTRADICTION_DETAIL_NAMES
        )
    )
    if not p301_wide_semantics and repair.is_publication_error_detail(
        outcome, detail
    ):
        position = spec.position_for_generation(generation)
        if (stage, item_index) != position.pair:
            raise DesignError(
                "P3.01 publication-error record is at the wrong position"
            )
        return
    try:
        spec.validate_slot(
            generation=generation,
            stage=stage,
            outcome=outcome,
            item_index=item_index,
            detail=detail,
        )
    except spec.SpecError as exc:
        raise DesignError(str(exc)) from exc


@contextmanager
def base_context() -> Iterator[None]:
    with base.base_context():
        inherited = base.base
        replacements = {
            "SCHEMA": SCHEMA,
            "spec": spec,
            "PROFILE_POSITION_SEQUENCES": {PROFILE: spec.POSITION_SEQUENCE},
            "PROFILE_TERMINAL_POSITIONS": {PROFILE: spec.TERMINAL_POSITION},
            "PROFILE_TERMINALS": {PROFILE: spec.TERMINAL_STAGE},
            "_validate_position_semantics": _validate_position_semantics,
        }
        previous = {name: getattr(inherited, name) for name in replacements}
        for name, value in replacements.items():
            setattr(inherited, name, value)
        try:
            yield
        finally:
            for name, value in previous.items():
                setattr(inherited, name, value)


def _call(name: str, *args, **kwargs):  # noqa: ANN002, ANN003, ANN202
    with base_context():
        return getattr(base.base, name)(*args, **kwargs)


def encode_request(*args, **kwargs):  # noqa: ANN002, ANN003, ANN201
    return _call("encode_request", *args, **kwargs)


def decode_request(data: bytes) -> Request:
    return _call("decode_request", data)


def initialize_record(profile: str, run_id: bytes) -> bytes:
    return _call("initialize_record", profile, run_id)


def decode_record(*args, **kwargs):  # noqa: ANN002, ANN003, ANN201
    return _call("decode_record", *args, **kwargs)


def apply_request(record: bytes, request_data: bytes) -> bytes:
    return _call("apply_request", record, request_data)


def classify_clean_baseline(*args, **kwargs):  # noqa: ANN002, ANN003, ANN201
    return _call("classify_clean_baseline", *args, **kwargs)


def classify_observation(*args, **kwargs):  # noqa: ANN002, ANN003, ANN201
    return _call("classify_observation", *args, **kwargs)
