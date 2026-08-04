#!/usr/bin/env python3
"""P3.01 userspace-only DWC3 device-event subtype telemetry contract."""

from __future__ import annotations

from dataclasses import asdict
from functools import lru_cache
import hashlib
import json
from typing import Any

import s22plus_fyg8_p300_telemetry_spec as base


SCHEMA = "s22plus_fyg8_p301_device_event_subtype_telemetry_spec_v1"
PROFILE = base.PROFILE

OUTCOME_PROGRESS = base.OUTCOME_PROGRESS
OUTCOME_SUCCESS = base.OUTCOME_SUCCESS
OUTCOME_FAILURE = base.OUTCOME_FAILURE

EVENT_LINK_ORDINAL = base.EVENT_LINK_ORDINAL
FINAL_STATE_ORDINAL = base.FINAL_STATE_ORDINAL
EVENT_LINK_GENERATION = EVENT_LINK_ORDINAL + 1
FINAL_STATE_GENERATION = FINAL_STATE_ORDINAL + 1

INGRESS_CLASSES = base.INGRESS_CLASSES
DEVICE_OTHER_ONLY_CLASS = INGRESS_CLASSES.index("DEVICE_OTHER_ONLY")
INGRESS_LINK_DETAIL_BASE = base.INGRESS_LINK_DETAIL_BASE
INGRESS_LINK_VALUE_COUNT = base.INGRESS_LINK_VALUE_COUNT

KNOWN_OTHER_EVENT_TYPES = (
    (0, "DISCONNECT"),
    (4, "WAKEUP"),
    (6, "SUSPEND"),
    (9, "ERRATIC_ERROR"),
    (10, "CMD_CMPL"),
    (11, "OVERFLOW"),
)
KNOWN_OTHER_TYPE_COUNT = len(KNOWN_OTHER_EVENT_TYPES)
KNOWN_OTHER_MASK_MAX = (1 << KNOWN_OTHER_TYPE_COUNT) - 1

SUBTYPE_DETAIL_BASE = 0x4001
SUBTYPE_MASK_COUNT = KNOWN_OTHER_MASK_MAX
SUBTYPE_INFO_COUNT = 16
SUBTYPE_BUCKET_COUNT = 4
SUBTYPE_VALUE_COUNT = (
    SUBTYPE_MASK_COUNT * SUBTYPE_INFO_COUNT * SUBTYPE_BUCKET_COUNT
)
SUBTYPE_DETAIL_MAX = SUBTYPE_DETAIL_BASE + SUBTYPE_VALUE_COUNT - 1
UNKNOWN_SUBTYPE_DETAIL = 0x4FC1

FINAL_DRIFT_DETAIL_BASE = 0x5001
FINAL_DRIFT_VALUE_COUNT = base.FINAL_STATE_VALUE_COUNT
FINAL_DRIFT_DETAIL_MAX = FINAL_DRIFT_DETAIL_BASE + FINAL_DRIFT_VALUE_COUNT - 1
EXPECTED_FINAL_STATE_DETAIL = base.encode_final_state(
    base.STATE_NOT_ATTACHED,
    base.SPEED_UNKNOWN,
    1,
    0,
)
EXPECTED_FINAL_STATE_INDEX = (
    EXPECTED_FINAL_STATE_DETAIL - base.FINAL_STATE_DETAIL_BASE
)

DETAIL_SUBTYPE_EMPTY_MASK = 0x6001
DETAIL_SUBTYPE_EMPTY_COUNT = 0x6002
DETAIL_SUBTYPE_INFO_MISSING = 0x6003
DETAIL_SUBTYPE_MASK_RANGE = 0x6004
DETAIL_FINAL_MISMATCH_BASE = 0x6005
DETAIL_FINAL_MISMATCH_COUNT = base.FIXED_MISMATCH_VALUE_COUNT
DETAIL_STATE_SPEED_CONTRADICTION = (
    DETAIL_FINAL_MISMATCH_BASE + DETAIL_FINAL_MISMATCH_COUNT
)
DETAIL_CONNECT_SPEED_CONTRADICTION = DETAIL_STATE_SPEED_CONTRADICTION + 1
DETAIL_TERMINAL_DOMAIN_CONTRADICTION = DETAIL_CONNECT_SPEED_CONTRADICTION + 1
DETAIL_CHECKPOINT_ORDINAL_CONTRADICTION = (
    DETAIL_TERMINAL_DOMAIN_CONTRADICTION + 1
)

CONTRADICTION_DETAIL_NAMES = {
    DETAIL_SUBTYPE_EMPTY_MASK: "device-other-subtype-empty-mask-contradiction",
    DETAIL_SUBTYPE_EMPTY_COUNT: "device-other-subtype-empty-count-contradiction",
    DETAIL_SUBTYPE_INFO_MISSING: "device-other-first-info-missing-contradiction",
    DETAIL_SUBTYPE_MASK_RANGE: "device-other-mask-range-contradiction",
    **{
        DETAIL_FINAL_MISMATCH_BASE + index: (
            f"final-digital-control-mismatch-{index + 1}"
        )
        for index in range(DETAIL_FINAL_MISMATCH_COUNT)
    },
    DETAIL_STATE_SPEED_CONTRADICTION: "final-state-speed-contradiction",
    DETAIL_CONNECT_SPEED_CONTRADICTION: "final-connect-speed-contradiction",
    DETAIL_TERMINAL_DOMAIN_CONTRADICTION: "final-detail-domain-contradiction",
    DETAIL_CHECKPOINT_ORDINAL_CONTRADICTION: "checkpoint-ordinal-contradiction",
}

Position = base.Position
SpecError = base.SpecError
Snapshot = base.Snapshot
Classification = base.Classification
POSITIONS = base.POSITIONS
POSITION_SEQUENCE = base.POSITION_SEQUENCE
TERMINAL_STAGE = base.TERMINAL_STAGE
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


def encode_subtype(mask: int, first_info: int, count_bucket: int) -> int:
    if not 1 <= mask <= KNOWN_OTHER_MASK_MAX:
        raise ValueError("P3.01 subtype mask must be nonzero and six-bit")
    if not 0 <= first_info < SUBTYPE_INFO_COUNT:
        raise ValueError("P3.01 first event-info nibble is invalid")
    if not 0 <= count_bucket < SUBTYPE_BUCKET_COUNT:
        raise ValueError("P3.01 event-count bucket is invalid")
    index = (
        ((mask - 1) * SUBTYPE_INFO_COUNT + first_info)
        * SUBTYPE_BUCKET_COUNT
        + count_bucket
    )
    return SUBTYPE_DETAIL_BASE + index


def decode_subtype(detail: int) -> tuple[int, int, int]:
    index = detail - SUBTYPE_DETAIL_BASE
    if not 0 <= index < SUBTYPE_VALUE_COUNT:
        raise ValueError("P3.01 detail is not a known-subtype value")
    mask_index, count_bucket = divmod(index, SUBTYPE_BUCKET_COUNT)
    mask_offset, first_info = divmod(mask_index, SUBTYPE_INFO_COUNT)
    return mask_offset + 1, first_info, count_bucket


def count_bucket_for_count(count: int) -> int:
    if count < 1:
        raise ValueError("P3.01 other-device count must be positive")
    if count == 1:
        return 0
    if count <= 3:
        return 1
    if count <= 7:
        return 2
    return 3


def encode_final_drift(state_index: int) -> int:
    if not 0 <= state_index < FINAL_DRIFT_VALUE_COUNT:
        raise ValueError("P3.01 final-state index is invalid")
    return FINAL_DRIFT_DETAIL_BASE + state_index


def decode_final_drift(detail: int) -> dict[str, int]:
    index = detail - FINAL_DRIFT_DETAIL_BASE
    if not 0 <= index < FINAL_DRIFT_VALUE_COUNT:
        raise ValueError("P3.01 detail is not a final-state value")
    return base.decode_final_state(base.FINAL_STATE_DETAIL_BASE + index)


def known_event_names(mask: int) -> tuple[str, ...]:
    if not 0 <= mask <= KNOWN_OTHER_MASK_MAX:
        raise ValueError("P3.01 subtype mask is invalid")
    return tuple(
        name
        for bit, (_event_type, name) in enumerate(KNOWN_OTHER_EVENT_TYPES)
        if mask & (1 << bit)
    )


def is_terminal_detail(detail: int) -> bool:
    return (
        SUBTYPE_DETAIL_BASE <= detail <= SUBTYPE_DETAIL_MAX
        or detail == UNKNOWN_SUBTYPE_DETAIL
        or FINAL_DRIFT_DETAIL_BASE <= detail <= FINAL_DRIFT_DETAIL_MAX
        or detail in CONTRADICTION_DETAIL_NAMES
    )


@lru_cache(maxsize=1)
def exact_detail_rules() -> tuple[tuple[int, int, int], ...]:
    """The fixed P3.00 Image rule table is intentionally unchanged."""
    return base.exact_detail_rules()


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
        raise SpecError("slot generation does not match the P3.01 position pair")
    ordinal = generation - 1
    if ordinal == FINAL_STATE_ORDINAL:
        if outcome != OUTCOME_FAILURE or not is_terminal_detail(detail):
            raise SpecError("P3.01 B must be a declared terminal failure detail")
        return
    if (
        ordinal == EVENT_LINK_ORDINAL
        and outcome == OUTCOME_FAILURE
        and detail in CONTRADICTION_DETAIL_NAMES
    ):
        return
    base.validate_slot(
        generation=generation,
        stage=stage,
        outcome=outcome,
        item_index=item_index,
        detail=detail,
    )


def detail_name(detail: int) -> str:
    if detail == UNKNOWN_SUBTYPE_DETAIL:
        return "device-other-unknown-subtype-seen"
    if detail in CONTRADICTION_DETAIL_NAMES:
        return CONTRADICTION_DETAIL_NAMES[detail]
    try:
        mask, first_info, count_bucket = decode_subtype(detail)
    except ValueError:
        pass
    else:
        events = "+".join(name.lower().replace("_", "-") for name in known_event_names(mask))
        return (
            f"device-other-types-{events}-first-info-{first_info}-"
            f"count-bucket-{count_bucket}"
        )
    try:
        state = decode_final_drift(detail)
    except ValueError:
        return base.detail_name(detail)
    return (
        "final-state-index-"
        f"{detail - FINAL_DRIFT_DETAIL_BASE}-"
        f"state-{state['state']}-speed-{state['speed']}-"
        f"coreidle-{state['coreidle']}-susphy-{state['susphy']}"
    )


def detail_kind(detail: int) -> str:
    if SUBTYPE_DETAIL_BASE <= detail <= SUBTYPE_DETAIL_MAX:
        return "device-event-subtype"
    if detail == UNKNOWN_SUBTYPE_DETAIL:
        return "device-event-unknown-subtype"
    if FINAL_DRIFT_DETAIL_BASE <= detail <= FINAL_DRIFT_DETAIL_MAX:
        return "final-state-drift"
    if detail in CONTRADICTION_DETAIL_NAMES:
        return "p301-telemetry-contradiction"
    return base.detail_kind(detail)


def descriptor() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "profile": PROFILE,
        "positions": [asdict(position) for position in POSITIONS],
        "fixed_image": "P3.00 exact kernel Image and 15-probe descriptor",
        "a": {
            "ordinal": EVENT_LINK_ORDINAL,
            "generation_after_write": EVENT_LINK_GENERATION,
            "outcome": OUTCOME_PROGRESS,
            "detail_min": INGRESS_LINK_DETAIL_BASE,
            "detail_max": INGRESS_LINK_DETAIL_BASE + INGRESS_LINK_VALUE_COUNT - 1,
        },
        "b": {
            "ordinal": FINAL_STATE_ORDINAL,
            "generation_after_write": FINAL_STATE_GENERATION,
            "outcome": OUTCOME_FAILURE,
            "known_subtype_range": [SUBTYPE_DETAIL_BASE, SUBTYPE_DETAIL_MAX],
            "unknown_subtype_detail": UNKNOWN_SUBTYPE_DETAIL,
            "final_drift_range": [FINAL_DRIFT_DETAIL_BASE, FINAL_DRIFT_DETAIL_MAX],
            "contradiction_details": {
                f"0x{detail:x}": name
                for detail, name in sorted(CONTRADICTION_DETAIL_NAMES.items())
            },
        },
        "known_other_event_types": [
            {"type": event_type, "mask_bit": bit, "name": name}
            for bit, (event_type, name) in enumerate(KNOWN_OTHER_EVENT_TYPES)
        ],
        "expected_final_state_detail": EXPECTED_FINAL_STATE_DETAIL,
        "exact_detail_rules_sha256": hashlib.sha256(
            _canonical(exact_detail_rules())
        ).hexdigest(),
    }


def descriptor_sha256() -> str:
    return hashlib.sha256(_canonical(descriptor())).hexdigest()


def validate() -> dict[str, Any]:
    values = {
        encode_subtype(mask, info, bucket)
        for mask in range(1, KNOWN_OTHER_MASK_MAX + 1)
        for info in range(SUBTYPE_INFO_COUNT)
        for bucket in range(SUBTYPE_BUCKET_COUNT)
    }
    expected = base.decode_final_state(EXPECTED_FINAL_STATE_DETAIL)
    if (
        EVENT_LINK_ORDINAL != 105
        or FINAL_STATE_ORDINAL != 106
        or len(values) != 4032
        or min(values) != 0x4001
        or max(values) != 0x4FC0
        or UNKNOWN_SUBTYPE_DETAIL != 0x4FC1
        or FINAL_DRIFT_DETAIL_MAX != 0x5084
        or expected
        != {"state": 0, "speed": 0, "coreidle": 1, "susphy": 0}
        or len(exact_detail_rules()) != len(base.exact_detail_rules())
    ):
        raise ValueError("P3.01 fixed-Image telemetry contract differs")
    return {
        "schema": SCHEMA,
        "descriptor_sha256": descriptor_sha256(),
        "a_ordinal": EVENT_LINK_ORDINAL,
        "a_outcome": OUTCOME_PROGRESS,
        "known_subtype_value_count": len(values),
        "unknown_subtype_detail": UNKNOWN_SUBTYPE_DETAIL,
        "final_drift_value_count": FINAL_DRIFT_VALUE_COUNT,
        "contradiction_value_count": len(CONTRADICTION_DETAIL_NAMES),
        "fixed_image_exact_rule_count": len(exact_detail_rules()),
        "verified": True,
    }


def __getattr__(name: str):
    return getattr(base, name)


validate()


if __name__ == "__main__":
    print(json.dumps(validate(), sort_keys=True))
