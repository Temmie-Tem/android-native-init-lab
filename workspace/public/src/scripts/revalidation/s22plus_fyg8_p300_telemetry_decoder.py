#!/usr/bin/env python3
"""Decode P3.00 retained event-ingress and IRQ telemetry."""

from __future__ import annotations

import hashlib
from typing import Any

import s22plus_fyg8_p298_telemetry_decoder as inherited
import s22plus_fyg8_p300_telemetry_model as model
import s22plus_fyg8_p300_telemetry_spec as spec


SCHEMA = "s22plus_fyg8_p300_event_ingress_irq_telemetry_decoder_v1"
DECODER_ID = "s22plus_fyg8_p300_two_slot_event_ingress_irq_telemetry_v1"
PROFILE = spec.PROFILE
POSITION_SEQUENCE = spec.POSITION_SEQUENCE
TERMINAL_POSITION = spec.TERMINAL_POSITION
POLICY_PREIMAGE = (
    "S22PLUS_FYG8_P300_EVENT_INGRESS_IRQ_TELEMETRY_DECODER_V1|"
    "layout=S22E1L1-45-ab-crc32|"
    "position=ordered-stage-item-pairs|"
    "control=P2.96-historical-no-probe|"
    "success-family=probe-armed-start-rc0-stream-ring-trigger-clean|"
    f"sot={spec.descriptor_sha256()}|model={model.SCHEMA}"
)
POLICY_SHA256 = hashlib.sha256(POLICY_PREIMAGE.encode("ascii")).hexdigest()
POLICY_ID = POLICY_SHA256[:32]
DecodeError = model.DesignError


def decode_detail(value: int, *, outcome: int | None = None) -> dict[str, Any]:
    common = {
        "detail_kind": spec.detail_kind(value),
        "detail_name": spec.detail_name(value),
    }
    if value in spec.FAILURE_DETAIL_NAMES:
        return {
            **common,
            "telemetry": {
                "kind": "event-ingress-irq-observer-failure",
                "probe_success_family": False,
            },
        }
    try:
        ingress_class, link_state = spec.decode_ingress_link(value)
    except ValueError:
        pass
    else:
        name = spec.INGRESS_CLASSES[ingress_class]
        return {
            **common,
            "telemetry": {
                "kind": "event-ingress-irq-link",
                "probe_armed": True,
                "gadget_start_rc": 0,
                "ep_enable_hit_count": 2,
                "streaming_trace_verified": True,
                "ring_loss_zero": True,
                "kretprobe_nmissed_zero": True,
                "trigger_contract_verified": True,
                "trace_cleanup_verified": True,
                "ingress_class": ingress_class,
                "ingress_class_name": name,
                "reset_seen": name in {
                    "RESET_NO_CONNECT_DONE",
                    "RESET_AND_CONNECT_DONE",
                },
                "connect_done_seen": name in {
                    "CONNECT_DONE_NO_RESET",
                    "RESET_AND_CONNECT_DONE",
                },
                "link_state": link_state,
            },
        }
    inherited_result = inherited.decode_detail(value, outcome=outcome)
    return {**inherited_result, **common}


def _with_semantics(result: dict[str, Any]) -> dict[str, Any]:
    result["slot_semantics"] = [
        {
            "slot_id": slot["slot_id"],
            "generation": slot["generation"],
            "stage": slot["stage"],
            "item_index": slot["item_index"],
            "position_name": (
                "entry"
                if slot["generation"] == 0
                else spec.position_for_generation(slot["generation"]).name
            ),
            **decode_detail(slot["detail"], outcome=slot["outcome"]),
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
        **decode_detail(active["detail"], outcome=active["outcome"]),
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
