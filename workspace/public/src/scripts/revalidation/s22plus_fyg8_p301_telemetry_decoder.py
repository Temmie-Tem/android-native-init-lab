#!/usr/bin/env python3
"""Decode ordinal-aware P3.01 DWC3 subtype telemetry."""

from __future__ import annotations

import hashlib
from typing import Any

import s22plus_fyg8_p300_telemetry_decoder as inherited
import s22plus_fyg8_p301_telemetry_model as model
import s22plus_fyg8_p301_telemetry_spec as spec


SCHEMA = "s22plus_fyg8_p301_device_event_subtype_telemetry_decoder_v1"
DECODER_ID = "s22plus_fyg8_p301_two_slot_device_event_subtype_v1"
PROFILE = spec.PROFILE
POSITION_SEQUENCE = spec.POSITION_SEQUENCE
TERMINAL_POSITION = spec.TERMINAL_POSITION
POLICY_PREIMAGE = (
    "S22PLUS_FYG8_P301_DEVICE_EVENT_SUBTYPE_TELEMETRY_DECODER_V1|"
    "layout=S22E1L1-45-ab-crc32|"
    "a=ordinal105-progress-d00-daf|"
    "b=ordinal106-failure-wide-band|"
    "unknown-subtype=4fc1|"
    f"sot={spec.descriptor_sha256()}|model={model.SCHEMA}"
)
POLICY_SHA256 = hashlib.sha256(POLICY_PREIMAGE.encode("ascii")).hexdigest()
POLICY_ID = POLICY_SHA256[:32]
DecodeError = model.DesignError


def _subtype_telemetry(value: int) -> dict[str, Any]:
    mask, first_info, count_bucket = spec.decode_subtype(value)
    return {
        "kind": "device-event-subtype",
        "probe_armed": True,
        "gadget_start_rc": 0,
        "ingress_class": spec.DEVICE_OTHER_ONLY_CLASS,
        "ingress_class_name": "DEVICE_OTHER_ONLY",
        "event_type_mask": mask,
        "event_type_names": list(spec.known_event_names(mask)),
        "first_event_info": first_info,
        "count_bucket": count_bucket,
        "count_bucket_name": ("1", "2-3", "4-7", "8+")[count_bucket],
        "unknown_subtype_seen": False,
        "implied_final_state": spec.decode_final_drift(
            spec.FINAL_DRIFT_DETAIL_BASE + spec.EXPECTED_FINAL_STATE_INDEX
        ),
    }


def decode_detail(
    value: int,
    *,
    outcome: int | None = None,
    generation: int | None = None,
) -> dict[str, Any]:
    final_context = generation in {None, spec.FINAL_STATE_GENERATION}
    contradiction_context = generation in {
        None,
        spec.EVENT_LINK_GENERATION,
        spec.FINAL_STATE_GENERATION,
    }
    if final_context:
        try:
            telemetry = _subtype_telemetry(value)
        except ValueError:
            pass
        else:
            return {
                "detail_kind": spec.detail_kind(value),
                "detail_name": spec.detail_name(value),
                "telemetry": telemetry,
            }
        if value == spec.UNKNOWN_SUBTYPE_DETAIL:
            return {
                "detail_kind": spec.detail_kind(value),
                "detail_name": spec.detail_name(value),
                "telemetry": {
                    "kind": "device-event-unknown-subtype",
                    "probe_armed": True,
                    "gadget_start_rc": 0,
                    "ingress_class": spec.DEVICE_OTHER_ONLY_CLASS,
                    "ingress_class_name": "DEVICE_OTHER_ONLY",
                    "unknown_subtype_seen": True,
                    "known_mask_not_claimed": True,
                    "implied_final_state": spec.decode_final_drift(
                        spec.FINAL_DRIFT_DETAIL_BASE
                        + spec.EXPECTED_FINAL_STATE_INDEX
                    ),
                },
            }
        try:
            state = spec.decode_final_drift(value)
        except ValueError:
            pass
        else:
            return {
                "detail_kind": spec.detail_kind(value),
                "detail_name": spec.detail_name(value),
                "telemetry": {
                    "kind": "final-state-drift",
                    "subtype_claimed": False,
                    "state_index": value - spec.FINAL_DRIFT_DETAIL_BASE,
                    "final_state": state,
                },
            }
    if contradiction_context and value in spec.CONTRADICTION_DETAIL_NAMES:
        return {
            "detail_kind": spec.detail_kind(value),
            "detail_name": spec.detail_name(value),
            "telemetry": {
                "kind": "p301-telemetry-contradiction",
                "subtype_claimed": False,
            },
        }
    return inherited.decode_detail(value, outcome=outcome)


def _with_semantics(result: dict[str, Any]) -> dict[str, Any]:
    result["slot_semantics"] = [
        {
            "slot_id": slot["slot_id"],
            "generation": slot["generation"],
            "stage": slot["stage"],
            "outcome": slot["outcome"],
            "item_index": slot["item_index"],
            "detail": slot["detail"],
            "position_name": (
                "entry"
                if slot["generation"] == 0
                else spec.position_for_generation(slot["generation"]).name
            ),
            **decode_detail(
                slot["detail"],
                outcome=slot["outcome"],
                generation=slot["generation"],
            ),
        }
        for slot in result["valid_slots"]
    ]
    active = result["active"]
    result["active_semantics"] = {
        "position_name": (
            "entry"
            if active["generation"] == 0
            else spec.position_for_generation(active["generation"]).name
        ),
        **decode_detail(
            active["detail"],
            outcome=active["outcome"],
            generation=active["generation"],
        ),
    }
    a_slots = [
        slot
        for slot in result["slot_semantics"]
        if slot["generation"] == spec.EVENT_LINK_GENERATION
        and slot["outcome"] == spec.OUTCOME_PROGRESS
    ]
    b_slots = [
        slot
        for slot in result["slot_semantics"]
        if slot["generation"] == spec.FINAL_STATE_GENERATION
        and slot["outcome"] == spec.OUTCOME_FAILURE
    ]
    if len(a_slots) == 1 and len(b_slots) == 1:
        result["p301_pair"] = {
            "a": a_slots[0],
            "b": b_slots[0],
            "adjacent_generations": True,
            "a_ordinal_105_progress": True,
            "b_ordinal_106_failure": True,
        }
    return result


def decode_record(
    record: bytes,
    *,
    expected_profile: str = PROFILE,
    expected_run_id: bytes | None = None,
) -> dict[str, Any]:
    return _with_semantics(
        model.decode_record(
            record,
            expected_profile=expected_profile,
            expected_run_id=expected_run_id,
        )
    )


def classify_clean_baseline(
    payload: bytes,
    *,
    expected_profile: str,
    expected_run_id: bytes,
) -> dict[str, Any]:
    return model.classify_clean_baseline(
        payload,
        expected_profile=expected_profile,
        expected_run_id=expected_run_id,
    )


def classify_observation(
    payload: bytes,
    *,
    expected_profile: str,
    expected_run_id: bytes,
) -> dict[str, Any]:
    result = model.classify_observation(
        payload,
        expected_profile=expected_profile,
        expected_run_id=expected_run_id,
    )
    for record in result.get("records", ()):
        _with_semantics(record)
    return result
