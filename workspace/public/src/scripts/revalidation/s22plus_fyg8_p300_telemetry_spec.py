#!/usr/bin/env python3
"""P3.00 event-ingress and IRQ-attribution telemetry contract."""

from __future__ import annotations

from dataclasses import asdict
from functools import lru_cache
import hashlib
import json
from typing import Any

import s22plus_fyg8_p298_telemetry_spec as base


SCHEMA = "s22plus_fyg8_p300_event_ingress_irq_telemetry_spec_v1"
PROFILE = base.PROFILE

OUTCOME_PROGRESS = base.OUTCOME_PROGRESS
OUTCOME_SUCCESS = base.OUTCOME_SUCCESS
OUTCOME_FAILURE = base.OUTCOME_FAILURE

BIND_ORDINAL = base.BIND_ORDINAL
FINAL_SAMPLING_ORDINAL = base.FINAL_SAMPLING_ORDINAL
EVENT_LINK_ORDINAL = base.EVENT_LINK_ORDINAL
INGRESS_LINK_ORDINAL = EVENT_LINK_ORDINAL
FINAL_STATE_ORDINAL = base.FINAL_STATE_ORDINAL
LINK_STATE_ORDINAL = EVENT_LINK_ORDINAL

INGRESS_CLASSES = (
    "NO_TOP_COUNT_ZERO",
    "NO_TOP_COUNT_NONZERO",
    "TOP_NONE_ONLY",
    "HANDLED_NO_WAKE",
    "WAKE_NO_THREAD",
    "THREAD_EMPTY_PASS",
    "THREAD_NONDEVICE_ONLY",
    "DEVICE_OTHER_ONLY",
    "RESET_NO_CONNECT_DONE",
    "CONNECT_DONE_NO_RESET",
    "RESET_AND_CONNECT_DONE",
)
INGRESS_CLASS_COUNT = len(INGRESS_CLASSES)
INGRESS_LINK_DETAIL_BASE = 0xD00
INGRESS_LINK_VALUE_COUNT = INGRESS_CLASS_COUNT * 16
EVENT_LINK_DETAIL_BASE = INGRESS_LINK_DETAIL_BASE
EVENT_LINK_VALUE_COUNT = INGRESS_LINK_VALUE_COUNT
LINK_STATE_DETAIL_BASE = INGRESS_LINK_DETAIL_BASE
LINK_STATE_VALUE_COUNT = INGRESS_LINK_VALUE_COUNT

FINAL_STATE_DETAIL_BASE = base.FINAL_STATE_DETAIL_BASE
FINAL_STATE_VALUE_COUNT = base.FINAL_STATE_VALUE_COUNT
FIXED_MISMATCH_DETAIL_BASE = base.FIXED_MISMATCH_DETAIL_BASE
FIXED_MISMATCH_VALUE_COUNT = base.FIXED_MISMATCH_VALUE_COUNT
STATE_SPEED_CONTRADICTION_DETAIL = base.STATE_SPEED_CONTRADICTION_DETAIL
CONNECT_SPEED_CONTRADICTION_DETAIL = base.CONNECT_SPEED_CONTRADICTION_DETAIL

DETAIL_TRIGGER_SETUP_OR_READBACK = 0xF73
DETAIL_TRIGGER_STATE_CONTRADICTION = 0xF74
DETAIL_TRACE_STREAM_READ_FAILED = 0xF75
DETAIL_TRACE_STREAM_LINE_MALFORMED = 0xF76
DETAIL_TRACE_RING_LOSS = 0xF77
DETAIL_EVENT_CONFIG_CONTRADICTION = 0xF78
DETAIL_FOREIGN_POINTER_CONTRADICTION = 0xF79
DETAIL_IRQ_PAIRING_CONTRADICTION = 0xF7A
DETAIL_IRQ_RETURN_CONTRADICTION = 0xF7B
DETAIL_THREAD_SNAPSHOT_CONTRADICTION = 0xF7C
DETAIL_RAW_EVENT_CONTRADICTION = 0xF7D
DETAIL_PROFILE_RELATION_CONTRADICTION = 0xF7E
DETAIL_INGRESS_CLASSIFICATION_CONTRADICTION = 0xF7F

NEW_FAILURE_DETAIL_NAMES = {
    DETAIL_TRIGGER_SETUP_OR_READBACK: "connect-done-traceoff-trigger-setup-or-readback-failed",
    DETAIL_TRIGGER_STATE_CONTRADICTION: "connect-done-traceoff-trigger-state-contradiction",
    DETAIL_TRACE_STREAM_READ_FAILED: "bind-trace-stream-read-failed",
    DETAIL_TRACE_STREAM_LINE_MALFORMED: "bind-trace-stream-line-malformed",
    DETAIL_TRACE_RING_LOSS: "bind-trace-ring-overwrite-or-drop",
    DETAIL_EVENT_CONFIG_CONTRADICTION: "dwc3-event-config-contradiction",
    DETAIL_FOREIGN_POINTER_CONTRADICTION: "dwc3-foreign-pointer-contradiction",
    DETAIL_IRQ_PAIRING_CONTRADICTION: "dwc3-irq-pairing-order-contradiction",
    DETAIL_IRQ_RETURN_CONTRADICTION: "dwc3-irq-return-domain-contradiction",
    DETAIL_THREAD_SNAPSHOT_CONTRADICTION: "dwc3-thread-snapshot-contradiction",
    DETAIL_RAW_EVENT_CONTRADICTION: "dwc3-raw-event-contradiction",
    DETAIL_PROFILE_RELATION_CONTRADICTION: "bind-trace-profile-relation-contradiction",
    DETAIL_INGRESS_CLASSIFICATION_CONTRADICTION: "dwc3-ingress-classification-contradiction",
}
FAILURE_DETAIL_NAMES = {**base.FAILURE_DETAIL_NAMES, **NEW_FAILURE_DETAIL_NAMES}

BIND_SETUP_FAILURE_DETAILS = (
    *base.BIND_SETUP_FAILURE_DETAILS,
    DETAIL_TRIGGER_SETUP_OR_READBACK,
)
BIND_RESULT_FAILURE_DETAILS = (
    *base.BIND_RESULT_FAILURE_DETAILS,
    DETAIL_TRACE_STREAM_READ_FAILED,
    DETAIL_TRACE_STREAM_LINE_MALFORMED,
    DETAIL_EVENT_CONFIG_CONTRADICTION,
    DETAIL_FOREIGN_POINTER_CONTRADICTION,
    DETAIL_IRQ_PAIRING_CONTRADICTION,
    DETAIL_IRQ_RETURN_CONTRADICTION,
    DETAIL_THREAD_SNAPSHOT_CONTRADICTION,
    DETAIL_RAW_EVENT_CONTRADICTION,
)
FINAL_TRACE_FAILURE_DETAILS = (
    *base.FINAL_TRACE_FAILURE_DETAILS,
    *NEW_FAILURE_DETAIL_NAMES,
)

Position = base.Position
SpecError = base.SpecError
Snapshot = base.Snapshot
Classification = base.Classification
TERMINAL_STAGE = base.TERMINAL_STAGE
POSITIONS = base.POSITIONS
POSITION_SEQUENCE = base.POSITION_SEQUENCE
TERMINAL_GENERATION = base.TERMINAL_GENERATION
TERMINAL_POSITION = base.TERMINAL_POSITION
GENERATION_BY_PAIR = base.GENERATION_BY_PAIR
position_for_generation = base.position_for_generation
generation_for_position = base.generation_for_position


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")


def encode_ingress_link(ingress_class: int, link_state: int) -> int:
    if not 0 <= ingress_class < INGRESS_CLASS_COUNT:
        raise ValueError("P3.00 ingress class is invalid")
    if not 0 <= link_state < 16:
        raise ValueError("P3.00 link state is invalid")
    return INGRESS_LINK_DETAIL_BASE + ingress_class * 16 + link_state


def decode_ingress_link(detail: int) -> tuple[int, int]:
    index = detail - INGRESS_LINK_DETAIL_BASE
    if not 0 <= index < INGRESS_LINK_VALUE_COUNT:
        raise ValueError("P3.00 detail is not an ingress/link value")
    return divmod(index, 16)


encode_event_link = encode_ingress_link
decode_event_link = decode_ingress_link


def encode_link_state(link_state: int) -> int:
    return encode_ingress_link(0, link_state)


def decode_link_state(detail: int) -> int:
    ingress_class, link_state = decode_ingress_link(detail)
    if ingress_class != 0:
        raise ValueError("P3.00 detail includes a nonzero ingress class")
    return link_state


encode_final_state = base.encode_final_state
decode_final_state = base.decode_final_state
encode_fixed_mismatch = base.encode_fixed_mismatch
decode_fixed_mismatch = base.decode_fixed_mismatch
expected_terminal_outcome = base.expected_terminal_outcome
classify = base.classify
start_result_detail = base.start_result_detail


@lru_cache(maxsize=1)
def exact_detail_rules() -> tuple[tuple[int, int, int], ...]:
    inherited = (
        row
        for row in base.exact_detail_rules()
        if not (
            row[0] == EVENT_LINK_ORDINAL
            and base.EVENT_LINK_DETAIL_BASE
            <= row[2]
            < base.EVENT_LINK_DETAIL_BASE + base.EVENT_LINK_VALUE_COUNT
        )
    )
    additions = [
        *(
            (EVENT_LINK_ORDINAL, OUTCOME_PROGRESS, detail)
            for detail in range(
                INGRESS_LINK_DETAIL_BASE,
                INGRESS_LINK_DETAIL_BASE + INGRESS_LINK_VALUE_COUNT,
            )
        ),
        *(
            (101, OUTCOME_FAILURE, detail)
            for detail in BIND_SETUP_FAILURE_DETAILS
        ),
        *(
            (103, OUTCOME_FAILURE, detail)
            for detail in BIND_RESULT_FAILURE_DETAILS
        ),
        *(
            (EVENT_LINK_ORDINAL, OUTCOME_FAILURE, detail)
            for detail in FINAL_TRACE_FAILURE_DETAILS
        ),
    ]
    return tuple(sorted(set((*inherited, *additions))))


@lru_cache(maxsize=1)
def _exact_rule_set() -> frozenset[tuple[int, int, int]]:
    return frozenset(exact_detail_rules())


def validate_slot(
    *,
    generation: int,
    stage: int,
    outcome: int,
    item_index: int,
    detail: int,
) -> None:
    position = position_for_generation(generation)
    if (stage, item_index) != position.pair:
        raise SpecError("slot generation does not match the P3.00 position pair")
    ordinal = generation - 1
    if (ordinal, outcome, detail) in _exact_rule_set():
        return
    base.validate_slot(
        generation=generation,
        stage=stage,
        outcome=outcome,
        item_index=item_index,
        detail=detail,
    )


def detail_name(detail: int) -> str:
    if detail in FAILURE_DETAIL_NAMES:
        return FAILURE_DETAIL_NAMES[detail]
    try:
        ingress_class, link_state = decode_ingress_link(detail)
    except ValueError:
        return base.detail_name(detail)
    return (
        "probe-ok-start-rc0-ingress-"
        f"{INGRESS_CLASSES[ingress_class].lower().replace('_', '-')}-"
        f"link-{link_state}"
    )


def detail_kind(detail: int) -> str:
    if detail in NEW_FAILURE_DETAIL_NAMES:
        return "event-ingress-irq-observer-failure"
    if INGRESS_LINK_DETAIL_BASE <= detail < INGRESS_LINK_DETAIL_BASE + INGRESS_LINK_VALUE_COUNT:
        return "event-ingress-irq-link"
    return base.detail_kind(detail)


def descriptor() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "profile": PROFILE,
        "positions": [asdict(position) for position in POSITIONS],
        "delivery": "boot-image-built-in-dwc3-event-ingress-irq-probes",
        "historical_control": "P2.96 no-probe behavioral baseline",
        "bind_event_count": 15,
        "irq_return_maxactive": 32,
        "ingress_link": {
            "ordinal": EVENT_LINK_ORDINAL,
            "detail_base": INGRESS_LINK_DETAIL_BASE,
            "value_count": INGRESS_LINK_VALUE_COUNT,
            "classes": list(INGRESS_CLASSES),
            "link_state_low_nibble": True,
            "connect_done_reset_presence_mandatory": True,
        },
        "integrity": {
            "streaming_bind_parser": True,
            "connect_done_post_trigger": "traceoff:1 if type == 2",
            "profile_before_filter_and_cutoff": True,
            "ring_loss_must_be_zero": True,
            "kretprobe_nmissed_must_be_zero": True,
            "single_controller": "dwc3@a600000",
        },
        "failure_details": {
            f"0x{detail:x}": name
            for detail, name in sorted(FAILURE_DETAIL_NAMES.items())
        },
        "exact_detail_rules": [list(row) for row in exact_detail_rules()],
    }


def descriptor_sha256() -> str:
    return hashlib.sha256(_canonical(descriptor())).hexdigest()


def validate() -> dict[str, Any]:
    ingress_values = {
        encode_ingress_link(ingress_class, link_state)
        for ingress_class in range(INGRESS_CLASS_COUNT)
        for link_state in range(16)
    }
    if (
        len(POSITIONS) != 107
        or POSITION_SEQUENCE != base.POSITION_SEQUENCE
        or INGRESS_CLASS_COUNT != 11
        or len(ingress_values) != 176
        or min(ingress_values) != 0xD00
        or max(ingress_values) != 0xDAF
        or max(ingress_values) >= FINAL_STATE_DETAIL_BASE
        or set(NEW_FAILURE_DETAIL_NAMES) != set(range(0xF73, 0xF80))
        or len(exact_detail_rules()) != len(set(exact_detail_rules()))
    ):
        raise ValueError("P3.00 event-ingress telemetry contract differs")
    return {
        "schema": SCHEMA,
        "descriptor_sha256": descriptor_sha256(),
        "position_count": len(POSITIONS),
        "ingress_class_count": INGRESS_CLASS_COUNT,
        "ingress_link_value_count": len(ingress_values),
        "final_state_value_count": FINAL_STATE_VALUE_COUNT,
        "observer_failure_value_count": len(FAILURE_DETAIL_NAMES),
        "new_observer_failure_value_count": len(NEW_FAILURE_DETAIL_NAMES),
        "exact_detail_rule_count": len(exact_detail_rules()),
        "bind_event_count": 15,
        "verified": True,
    }


def __getattr__(name: str):
    return getattr(base, name)


validate()


if __name__ == "__main__":
    print(json.dumps(validate(), sort_keys=True))
