#!/usr/bin/env python3
"""Decode the exact P3.18 early EUD-cache failure over Carrier-v2.

The frozen live decoder correctly validates the Carrier-v2 byte ABI, but it
uses the P3.08 semantic table.  That table does not admit the P3.07 EUD-cache
failure at the intermediate generation where the P3.18 module-plan drift
actually published it.  This H0-only successor keeps the byte ABI unchanged
and admits only that one source-proved intermediate tuple.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterator

import s22plus_fyg8_p308_telemetry_spec as inherited
import s22plus_fyg8_p310_carrier_model as carrier


SCHEMA = "s22plus_fyg8_p318_postlive_eud_carrier_model_v2"
FAILURE_GENERATION = 47
FAILURE_STAGE = 0x66
FAILURE_ITEM_INDEX = 38
FAILURE_DETAIL = 0x6010


class _P318PostLiveSemantics:
    PROFILE = inherited.PROFILE
    TERMINAL_POSITION = inherited.TERMINAL_POSITION
    SpecError = inherited.SpecError

    @staticmethod
    def validate_slot(
        *,
        generation: int,
        stage: int,
        outcome: int,
        item_index: int,
        detail: int,
    ) -> None:
        exact_failure = (
            generation == FAILURE_GENERATION
            and stage == FAILURE_STAGE
            and outcome == carrier.OUTCOME_FAILURE
            and item_index == FAILURE_ITEM_INDEX
            and detail == FAILURE_DETAIL
        )
        if exact_failure:
            return
        inherited.validate_slot(
            generation=generation,
            stage=stage,
            outcome=outcome,
            item_index=item_index,
            detail=detail,
        )


SEMANTICS = _P318PostLiveSemantics()

for _name in (
    "TARGET",
    "LONG_FAMILY",
    "UNSAT_FAMILY",
    "LEGACY_FAMILIES",
    "ALL_FAMILIES",
    "FORMAT_VERSION",
    "REQUEST_VERSION_V2",
    "REQUEST_VERSION_V3",
    "LONG_RECORD_SIZE",
    "LONG_HEADER_SIZE",
    "SLOT_SIZE",
    "SLOT_COUNT",
    "SLOT_PAYLOAD_SIZE",
    "REQUEST_PAYLOAD_SIZE",
    "UNSAT_SIZE",
    "RUN_ID_SIZE",
    "PAYLOAD_NONE",
    "PAYLOAD_RAW_EXCERPT",
    "OUTCOME_PROGRESS",
    "OUTCOME_SUCCESS",
    "OUTCOME_FAILURE",
    "PROFILE_NUMBERS",
    "PROFILE_BY_NUMBER",
    "HEADER_STRUCT",
    "SLOT_BODY_STRUCT",
    "Request",
    "Slot",
    "DesignError",
    "crc32",
    "model_run_id",
):
    if hasattr(carrier, _name):
        globals()[_name] = getattr(carrier, _name)


@contextmanager
def _postlive_semantics() -> Iterator[None]:
    previous = carrier.spec
    carrier.spec = SEMANTICS
    try:
        yield
    finally:
        carrier.spec = previous


def _call(name: str, *args: Any, **kwargs: Any) -> Any:
    with _postlive_semantics():
        return getattr(carrier, name)(*args, **kwargs)


def unsat_record(*args: Any, **kwargs: Any) -> bytes:
    return _call("unsat_record", *args, **kwargs)


def encode_request(*args: Any, **kwargs: Any) -> bytes:
    return _call("encode_request", *args, **kwargs)


def decode_request(*args: Any, **kwargs: Any):  # noqa: ANN201
    return _call("decode_request", *args, **kwargs)


def initialize_record(*args: Any, **kwargs: Any) -> bytes:
    return _call("initialize_record", *args, **kwargs)


def decode_record(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return _call("decode_record", *args, **kwargs)


def apply_request(*args: Any, **kwargs: Any) -> bytes:
    return _call("apply_request", *args, **kwargs)


def classify_clean_baseline(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return _call("classify_clean_baseline", *args, **kwargs)


def classify_observation(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return _call("classify_observation", *args, **kwargs)
