#!/usr/bin/env python3
"""Bind P3.14 semantics to the unchanged Carrier-v2 byte ABI."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterator

import s22plus_fyg8_p310_carrier_model as carrier
import s22plus_fyg8_p314_telemetry_spec as spec


SCHEMA = "s22plus_fyg8_p314_carrier_model_v1"

for _name in (
    "TARGET", "LONG_FAMILY", "UNSAT_FAMILY", "LEGACY_FAMILIES", "ALL_FAMILIES",
    "FORMAT_VERSION", "REQUEST_VERSION_V2", "REQUEST_VERSION_V3",
    "LONG_RECORD_SIZE", "LONG_HEADER_SIZE", "SLOT_SIZE", "SLOT_COUNT",
    "SLOT_PAYLOAD_SIZE", "REQUEST_PAYLOAD_SIZE", "UNSAT_SIZE", "RUN_ID_SIZE",
    "PAYLOAD_NONE", "PAYLOAD_RAW_EXCERPT", "OUTCOME_PROGRESS", "OUTCOME_SUCCESS",
    "OUTCOME_FAILURE", "PROFILE_NUMBERS", "PROFILE_BY_NUMBER", "REQUEST_STRUCT",
    "SLOT_BODY_STRUCT", "Request", "Slot", "DesignError", "crc32", "model_run_id",
):
    if hasattr(carrier, _name):
        globals()[_name] = getattr(carrier, _name)


@contextmanager
def _p314_semantics() -> Iterator[None]:
    previous = carrier.spec
    carrier.spec = spec
    try:
        yield
    finally:
        carrier.spec = previous


def _call(name: str, *args: Any, **kwargs: Any) -> Any:
    with _p314_semantics():
        return getattr(carrier, name)(*args, **kwargs)


def unsat_record(*args: Any, **kwargs: Any) -> bytes:
    return _call("unsat_record", *args, **kwargs)


def encode_request(*args: Any, **kwargs: Any) -> bytes:
    return _call("encode_request", *args, **kwargs)


def decode_request(*args: Any, **kwargs: Any) -> Any:
    return _call("decode_request", *args, **kwargs)


def initialize_record(*args: Any, **kwargs: Any) -> bytes:
    return _call("initialize_record", *args, **kwargs)


def decode_record(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return _call("decode_record", *args, **kwargs)


def apply_request(*args: Any, **kwargs: Any) -> bytes:
    if len(args) >= 2:
        request_data = args[1]
    else:
        request_data = kwargs.get("request_data")
    request = carrier.decode_request(request_data)
    if (
        request.outcome == carrier.OUTCOME_FAILURE
        and request.detail == spec.LEGACY_GENERIC_MULTIPLICITY_DETAIL
    ):
        raise carrier.DesignError("P3.14 legacy 0x6712 is decode-only")
    return _call("apply_request", *args, **kwargs)


def classify_clean_baseline(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return _call("classify_clean_baseline", *args, **kwargs)


def classify_observation(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return _call("classify_observation", *args, **kwargs)
