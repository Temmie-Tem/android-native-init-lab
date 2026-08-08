#!/usr/bin/env python3
"""Decode P3.08 telemetry carried by the P3.10 Carrier v2 ABI."""

from __future__ import annotations

import hashlib
from typing import Any

import s22plus_fyg8_p303_telemetry_spec as p303
import s22plus_fyg8_p307_telemetry_spec as p307
import s22plus_fyg8_p308_telemetry_decoder as inherited
import s22plus_fyg8_p310_carrier_model as model


SCHEMA = "s22plus_fyg8_p310_telemetry_decoder_v1"
DECODER_ID = "s22plus_fyg8_p310_carrier_v2_p308_telemetry_v1"
PROFILE = p307.PROFILE
POLICY_PREIMAGE = (
    "S22PLUS_FYG8_P310_TELEMETRY_DECODER_V1|carrier=S22E1L2-192-ab-header-slot-crc|"
    "payload=64-byte-bounded-valid-span-exclusion|semantics=P308"
)
POLICY_SHA256 = hashlib.sha256(POLICY_PREIMAGE.encode("ascii")).hexdigest()
POLICY_ID = POLICY_SHA256[:32]
DecodeError = model.DesignError


def _json_safe(value: Any) -> Any:
    if isinstance(value, bytes):
        return {"encoding": "hex", "value": value.hex()}
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    return value


def decode_detail(*args, **kwargs):  # noqa: ANN002, ANN003, ANN201
    return inherited.decode_detail(*args, **kwargs)


def _decorate(record: dict[str, Any]) -> dict[str, Any]:
    # The P3.08 pair semantics are unchanged; only the retained carrier changed.
    return inherited._with_semantics(record)  # noqa: SLF001


def decode_record(
    record: bytes,
    *,
    expected_profile: str = PROFILE,
    expected_run_id: bytes | None = None,
) -> dict[str, Any]:
    return _decorate(
        model.decode_record(
            record,
            expected_profile=expected_profile,
            expected_run_id=expected_run_id,
        )
    )


def classify_clean_baseline(
    payload: bytes, *, expected_profile: str, expected_run_id: bytes
) -> dict[str, Any]:
    return model.classify_clean_baseline(
        payload,
        expected_profile=expected_profile,
        expected_run_id=expected_run_id,
    )


def classify_observation(
    payload: bytes, *, expected_profile: str, expected_run_id: bytes
) -> dict[str, Any]:
    result = model.classify_observation(
        payload,
        expected_profile=expected_profile,
        expected_run_id=expected_run_id,
    )
    normal = 0
    degraded = 0
    inherited_contradictions = 0
    contradiction_values = {
        *p303.CONTRADICTION_DETAIL_NAMES,
        *p307.CONTRADICTION_DETAIL_NAMES,
    }
    for record in result.get("records", ()):
        _decorate(record)
        pair = record.get("p308_pair")
        if pair is not None and pair["kind"] == "normal":
            normal += 1
        elif pair is not None and pair["kind"] == "degraded":
            degraded += 1
        if record["active"]["detail"] in contradiction_values:
            inherited_contradictions += 1
    result["telemetry_count"] = normal
    result["degraded_count"] = degraded
    result["contradiction_count"] = inherited_contradictions + degraded
    if not result["integrity_issue"]:
        if inherited_contradictions:
            result["classification"] = "P310_TELEMETRY_CONTRADICTION"
            result["accepted"] = False
        elif degraded:
            result["classification"] = "P310_DEGRADED_OBSERVER_CONTRADICTION"
            result["accepted"] = False
        elif normal:
            result["classification"] = "P310_TELEMETRY_ONE_OR_MORE_BOOTS"
            result["accepted"] = True
    return _json_safe(result)
