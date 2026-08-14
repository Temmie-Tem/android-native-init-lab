#!/usr/bin/env python3
"""Decode P3.18 Max77705 envelope-v4 retained by Carrier-v2."""

from __future__ import annotations

import hashlib
import json
from typing import Any

import s22plus_fyg8_p312_telemetry_decoder as json_support
import s22plus_fyg8_p310_carrier_model as model
import s22plus_fyg8_p310_source_contract as source_contract
import s22plus_fyg8_p315_telemetry_decoder as inherited
import s22plus_fyg8_p318_max77705_telemetry as telemetry
import s22plus_fyg8_p318_cdc_acm_endpoint_transition as transition


SCHEMA = "s22plus_fyg8_p318_max77705_telemetry_decoder_v4"
DECODER_ID = "s22plus_fyg8_p318_max77705_carrier_v2_envelope_v4"
OVERLAY_CONTRACT_ID = "s22plus-fyg8-p318-topology-timing-max77705-envelope-v4"
PARENT_SOURCE_CONTRACT_ID = source_contract.CONTRACT_ID
PROFILE = inherited.PROFILE
POLICY_PREIMAGE = (
    "S22PLUS_FYG8_P318_MAX77705_TELEMETRY_DECODER_V4|carrier=S22E1L2-192|"
    "pair=106,107|a=0xda3|b=0x6701-0x673f|envelope=MXD4-128|"
    "timing=install-exposure-pre-write-post1-post2-first-host-event|"
    "banner=outcome-error-count|poll=47-lossless-or-44-summary-plus-zero3|"
    "host=phase-bound-complete-receipt-required|claim-busy=empty-preimage"
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
        telemetry.p317.inherited.fixed_spec.ATTR_ORDINAL + 1,
        telemetry.p317.inherited.fixed_spec.SUMMARY_ORDINAL + 1,
    }
    if generations != expected:
        return record
    try:
        decoded = telemetry.decode_carrier_record(raw, run_id=run_id)
    except (telemetry.TelemetryV4Error, model.DesignError) as exc:
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
    pending = 0
    for row in result.get("records", ()):
        start = int(row["observer_offset"])
        raw = payload[start : start + model.LONG_RECORD_SIZE]
        _attach(row, raw, expected_run_id)
        decoded = row.get("max77705")
        if decoded is None:
            continue
        no_proof += 1
        if (
            decoded.get("mux_class") is not None
            and decoded.get("causal_pending_complete_host_receipt") is True
        ):
            pending += 1
    result["telemetry_count"] = complete
    result["contradiction_count"] = no_proof
    result["max77705_result_count"] = complete + no_proof
    result["p318_host_receipt_pending_count"] = pending
    if not result["integrity_issue"]:
        if no_proof == 1 and pending == 1:
            result["classification"] = "NO_PROOF_OBSERVER_HOST_RECEIPT_REQUIRED"
            result["accepted"] = False
        elif no_proof == 1:
            terminal = next(
                row["max77705"]["terminal_classification"]
                for row in result["records"]
                if row.get("max77705") is not None
            )
            result["classification"] = terminal
            result["accepted"] = False
        elif no_proof > 1:
            result["classification"] = "MAX77705_RESULT_MULTIPLICITY"
            result["accepted"] = False
    return _json_safe(result)


def correlate_candidate_receipt(
    classified: dict[str, Any],
    *,
    relationship: str,
    authority_state: str,
    observation_complete: bool,
) -> dict[str, Any]:
    if (
        relationship not in transition.TOPOLOGY_RELATIONSHIPS
        or authority_state not in transition.TOPOLOGY_AUTHORITIES
        or not isinstance(observation_complete, bool)
    ):
        raise DecodeError("P3.18 candidate topology receipt domain differs")
    result = dict(classified)
    records = [
        row for row in result.get("records", ())
        if isinstance(row, dict) and row.get("max77705") is not None
    ]
    if len(records) != 1 or result.get("integrity_issue"):
        raise DecodeError("P3.18 candidate correlation lacks one clean record")
    decoded = dict(records[0]["max77705"])
    if (
        decoded.get("mux_class") is None
        or decoded.get("causal_pending_complete_host_receipt") is not True
        or decoded.get("payload_overflow") is True
    ):
        decoded["candidate_topology_relationship"] = relationship
        decoded["candidate_topology_authority_state"] = authority_state
        decoded["host_correlation_proof_class"] = "NO_PROOF_OBSERVER"
        decoded["causal_result_allowed"] = False
        records[0]["max77705"] = decoded
        result["classification"] = decoded.get(
            "terminal_classification", "NO_PROOF_OBSERVER"
        )
        result["accepted"] = False
        result["telemetry_count"] = 0
        result["contradiction_count"] = 1
        return _json_safe(result)
    timing = decoded["timing"]
    correlated = transition.classify_candidate_evidence(
        relationship=relationship,
        authority_state=authority_state,
        observation_complete=observation_complete,
        causal_terminal_ready=bool(
            decoded.get("diagnostic_causal_prerequisites_ready")
        ),
        validity_mask=int(timing["valid_mask"]),
        host_event_kind=str(timing["first_host_event_kind"]),
        latch_install_delta_us=int(timing["latch_install_delta_us"]),
        gadget_exposure_delta_us=int(timing["gadget_exposure_delta_us"]),
    )
    proof_class = str(correlated["proof_class"])
    accepted = (
        correlated["timing"]["causal_timing_allowed"] is True
        and proof_class
        in {
            "RETAIN_EXPERIMENT_TERMINAL",
            "DEVICE_RESULT_HOST_SILENT",
            "DEVICE_RESULT_DWC3_HOST_EVENT_NO_ENDPOINT",
        }
    )
    decoded["candidate_topology_relationship"] = relationship
    decoded["candidate_topology_authority_state"] = authority_state
    decoded["candidate_topology_observation_complete"] = observation_complete
    decoded["host_timing_classification"] = correlated["timing"]["classification"]
    decoded["host_correlation_proof_class"] = proof_class
    decoded["host_correlation_effect"] = correlated["effect"]
    decoded["causal_result_allowed"] = accepted
    records[0]["max77705"] = decoded
    result["classification"] = proof_class
    result["accepted"] = accepted
    result["telemetry_count"] = 1 if accepted else 0
    result["contradiction_count"] = 0 if accepted else 1
    result["p318_host_receipt_pending_count"] = 0
    return _json_safe(result)


def validate() -> dict[str, Any]:
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
        "telemetry": {
            "schema": telemetry.SCHEMA,
            "envelope_size": telemetry.ENVELOPE_SIZE,
            "version": telemetry.ENVELOPE_VERSION,
            "lossless_capacity": telemetry.LOSSLESS_CAPACITY,
            "overflow_spare": telemetry.OVERFLOW_SPARE,
        },
        "host_receipt_required_before_causal_acceptance": True,
        "initialized_record_json_safe": True,
        "verified": True,
    }


if __name__ == "__main__":
    print(json.dumps(validate(), sort_keys=True))
