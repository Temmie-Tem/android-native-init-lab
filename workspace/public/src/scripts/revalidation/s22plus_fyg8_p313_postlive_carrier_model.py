#!/usr/bin/env python3
"""Decode P3.13 Carrier-v2 records without rewriting its frozen live closure.

P3.13 reused the P3.12 Carrier-v2 model.  That model correctly validates the
byte ABI, but its semantic authority predates P3.13's 0x6701..0x673f
contradiction family.  This post-live model keeps the byte ABI unchanged and
adds only the missing P3.13 semantic authority for retained H0 analysis.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterator

import s22plus_fyg8_p310_carrier_model as carrier
import s22plus_fyg8_p312_telemetry_spec as inherited
import s22plus_fyg8_p313_telemetry_spec as p313


SCHEMA = "s22plus_fyg8_p313_postlive_carrier_model_v1"


class _P313PostLiveSemantics:
    PROFILE = p313.PROFILE
    TERMINAL_POSITION = p313.TERMINAL_POSITION
    SpecError = p313.SpecError

    @staticmethod
    def validate_slot(
        *,
        generation: int,
        stage: int,
        outcome: int,
        item_index: int,
        detail: int,
    ) -> None:
        position = p313.position_for_generation(generation)
        if (stage, item_index) != position.pair:
            raise p313.SpecError("P3.13 post-live carrier position differs")
        if detail in p313.CONTRADICTION_DETAIL_NAMES:
            if outcome != p313.OUTCOME_FAILURE:
                raise p313.SpecError("P3.13 contradiction outcome differs")
            return
        if generation in {p313.ATTR_ORDINAL + 1, p313.SUMMARY_ORDINAL + 1}:
            p313.validate_slot(
                generation=generation,
                stage=stage,
                outcome=outcome,
                item_index=item_index,
                detail=detail,
            )
            return
        inherited.validate_slot(
            generation=generation,
            stage=stage,
            outcome=outcome,
            item_index=item_index,
            detail=detail,
        )


SEMANTICS = _P313PostLiveSemantics()

for _name in (
    "TARGET", "LONG_FAMILY", "UNSAT_FAMILY", "LEGACY_FAMILIES", "ALL_FAMILIES",
    "FORMAT_VERSION", "REQUEST_VERSION_V2", "REQUEST_VERSION_V3",
    "LONG_RECORD_SIZE", "LONG_HEADER_SIZE", "SLOT_SIZE", "SLOT_COUNT",
    "SLOT_PAYLOAD_SIZE", "REQUEST_PAYLOAD_SIZE", "UNSAT_SIZE", "RUN_ID_SIZE",
    "PAYLOAD_NONE", "PAYLOAD_RAW_EXCERPT", "OUTCOME_PROGRESS", "OUTCOME_SUCCESS",
    "OUTCOME_FAILURE", "PROFILE_NUMBERS", "PROFILE_BY_NUMBER", "HEADER_STRUCT",
    "SLOT_BODY_STRUCT", "Request", "Slot", "DesignError", "crc32", "model_run_id",
):
    if hasattr(carrier, _name):
        globals()[_name] = getattr(carrier, _name)


@contextmanager
def _p313_postlive_semantics() -> Iterator[None]:
    previous = carrier.spec
    carrier.spec = SEMANTICS
    try:
        yield
    finally:
        carrier.spec = previous


def _call(name: str, *args: Any, **kwargs: Any) -> Any:
    with _p313_postlive_semantics():
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
