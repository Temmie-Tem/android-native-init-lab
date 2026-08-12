#!/usr/bin/env python3
"""Decode P3.17 Max77705 envelope-v3 retained by Carrier-v2."""

from __future__ import annotations

import hashlib
import json
from typing import Any

import s22plus_fyg8_p317_max77705_telemetry as telemetry
import s22plus_fyg8_p312_telemetry_decoder as json_support
import s22plus_fyg8_p310_carrier_model as model
import s22plus_fyg8_p310_source_contract as source_contract
import s22plus_fyg8_p315_telemetry_decoder as inherited


SCHEMA = "s22plus_fyg8_p317_max77705_telemetry_decoder_v3"
DECODER_ID = "s22plus_fyg8_p317_max77705_carrier_v2_envelope_v3"
OVERLAY_CONTRACT_ID = "s22plus-fyg8-p317-executability-max77705-envelope-v3"
PARENT_SOURCE_CONTRACT_ID = source_contract.CONTRACT_ID
PROFILE = inherited.PROFILE
POLICY_PREIMAGE = (
    "S22PLUS_FYG8_P317_MAX77705_TELEMETRY_DECODER_V3|carrier=S22E1L2-192|"
    "pair=106,107|a=0xda3|b=0x6701-0x673f|envelope=MXD3-128|"
    "binding=compact-0-1-many-3bytes|exec=policy-provider-pre-post-link-wait-6bytes|"
    "poll=unchanged-76bytes|eagain=6-observable-row-reverse-map|"
    "negative=claim-busy-c-policy-to-result-policy-io-format-empty-preimage|"
    "precondition=0x670a-0x670e|contradiction=0x670f"
)
POLICY_SHA256 = hashlib.sha256(POLICY_PREIMAGE.encode("ascii")).hexdigest()
POLICY_ID = POLICY_SHA256[:32]


class DecodeError(ValueError):
    pass


def _json_safe(value: Any) -> Any:
    return json_support._json_safe(value)  # noqa: SLF001


def _attach(record: dict[str, Any], raw: bytes, run_id: bytes) -> dict[str, Any]:
    generations = {row.get("generation") for row in record.get("valid_slots", ())}
    expected = {
        telemetry.inherited.fixed_spec.ATTR_ORDINAL + 1,
        telemetry.inherited.fixed_spec.SUMMARY_ORDINAL + 1,
    }
    if generations != expected:
        return record
    try:
        decoded = telemetry.decode_carrier_record(raw, run_id=run_id)
    except (telemetry.TelemetryError, model.DesignError) as exc:
        raise DecodeError(str(exc)) from exc
    record["max77705"] = decoded
    return record


def decode_record(
    record: bytes,
    *,
    expected_profile: str = PROFILE,
    expected_run_id: bytes | None = None,
) -> dict[str, Any]:
    try:
        decoded = model.decode_record(
            record,
            expected_profile=expected_profile,
            expected_run_id=expected_run_id,
        )
    except model.DesignError as exc:
        raise DecodeError(str(exc)) from exc
    if expected_run_id is not None:
        decoded = _attach(decoded, record, expected_run_id)
    return _json_safe(decoded)


def classify_clean_baseline(
    payload: bytes, *, expected_profile: str, expected_run_id: bytes
) -> dict[str, Any]:
    return inherited.classify_clean_baseline(
        payload,
        expected_profile=expected_profile,
        expected_run_id=expected_run_id,
    )


def classify_observation(
    payload: bytes, *, expected_profile: str, expected_run_id: bytes
) -> dict[str, Any]:
    try:
        result = model.classify_observation(
            payload,
            expected_profile=expected_profile,
            expected_run_id=expected_run_id,
        )
    except model.DesignError as exc:
        raise DecodeError(str(exc)) from exc
    complete = 0
    no_proof = 0
    for row in result.get("records", ()):
        start = int(row["observer_offset"])
        raw = payload[start : start + model.LONG_RECORD_SIZE]
        _attach(row, raw, expected_run_id)
        decoded = row.get("max77705")
        if decoded is None:
            continue
        if decoded["mux_class"] is not None and decoded["causal_result_allowed"]:
            complete += 1
        else:
            no_proof += 1
    result["telemetry_count"] = complete
    result["contradiction_count"] = no_proof
    result["max77705_result_count"] = complete + no_proof
    if not result["integrity_issue"]:
        if complete and no_proof:
            result["classification"] = "MAX77705_RESULT_MULTIPLICITY"
            result["accepted"] = False
        elif complete == 1:
            result["classification"] = "MAX77705_DIAGNOSTIC_RESULT"
            result["accepted"] = True
        elif no_proof == 1:
            terminal = next(
                row["max77705"]["terminal_classification"]
                for row in result["records"]
                if row.get("max77705") is not None
            )
            result["classification"] = terminal
            result["accepted"] = False
        elif complete + no_proof > 1:
            result["classification"] = "MAX77705_RESULT_MULTIPLICITY"
            result["accepted"] = False
    return _json_safe(result)


def validate() -> dict[str, Any]:
    value = telemetry.validate()
    initialized = model.initialize_record(PROFILE, model.model_run_id(PROFILE))
    decoded = decode_record(
        initialized,
        expected_profile=PROFILE,
        expected_run_id=model.model_run_id(PROFILE),
    )
    json.dumps(decoded, sort_keys=True, allow_nan=False)
    return {
        "schema": SCHEMA,
        "decoder_id": DECODER_ID,
        "policy_id": POLICY_ID,
        "telemetry": value,
        "initialized_record_json_safe": True,
        "verified": True,
    }


if __name__ == "__main__":
    print(json.dumps(validate(), sort_keys=True))
