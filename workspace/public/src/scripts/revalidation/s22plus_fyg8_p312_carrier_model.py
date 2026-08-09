#!/usr/bin/env python3
"""Bind the P3.12 detail contract to the existing Carrier-v2 byte ABI."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterator

import s22plus_fyg8_p310_carrier_model as carrier
import s22plus_fyg8_p312_telemetry_spec as spec


SCHEMA = "s22plus_fyg8_p312_carrier_model_v1"

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
def _p312_semantics() -> Iterator[None]:
    previous = carrier.spec
    carrier.spec = spec
    try:
        yield
    finally:
        carrier.spec = previous


def _call(name: str, *args: Any, **kwargs: Any) -> Any:
    with _p312_semantics():
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


def simulate_initial_visibility(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return _call("simulate_initial_visibility", *args, **kwargs)


def validate() -> dict[str, Any]:
    previous = carrier.spec
    result = _call("validate")
    if carrier.spec is not previous:
        raise DesignError("P3.12 carrier semantics leaked into the parent module")
    if LONG_FAMILY != b"S22E1L2|" or UNSAT_FAMILY != b"S22E1U2|":
        raise DesignError("P3.12 did not select Carrier v2")
    return {
        **result,
        "schema": SCHEMA,
        "telemetry_schema": spec.validate()["schema"],
        "parent_semantics_restored": True,
        "verified": True,
    }


if __name__ == "__main__":
    import json

    print(json.dumps(validate(), sort_keys=True))
