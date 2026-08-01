#!/usr/bin/env python3
"""P2.96 built-in-only DWC3 value-telemetry single source of truth."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from functools import lru_cache
import hashlib
import json
from typing import Any

import s22plus_fyg8_p294_telemetry_spec as base


SCHEMA = "s22plus_fyg8_p296_builtin_dwc3_telemetry_spec_v1"
PROFILE = base.PROFILE

OUTCOME_PROGRESS = base.OUTCOME_PROGRESS
OUTCOME_SUCCESS = base.OUTCOME_SUCCESS
OUTCOME_FAILURE = base.OUTCOME_FAILURE

BIND_ORDINAL = base.BIND_ORDINAL
FINAL_SAMPLING_ORDINAL = base.FINAL_SAMPLING_ORDINAL
LINK_STATE_ORDINAL = base.LINK_STATE_ORDINAL
FINAL_STATE_ORDINAL = base.FINAL_STATE_ORDINAL

LINK_STATE_DETAIL_BASE = base.LINK_STATE_DETAIL_BASE
LINK_STATE_VALUE_COUNT = base.LINK_STATE_VALUE_COUNT
FINAL_STATE_DETAIL_BASE = base.FINAL_STATE_DETAIL_BASE
FINAL_STATE_VALUE_COUNT = base.FINAL_STATE_VALUE_COUNT
FIXED_MISMATCH_DETAIL_BASE = base.FIXED_MISMATCH_DETAIL_BASE
FIXED_MISMATCH_VALUE_COUNT = 7
STATE_SPEED_CONTRADICTION_DETAIL = base.STATE_SPEED_CONTRADICTION_DETAIL
CONNECT_SPEED_CONTRADICTION_DETAIL = base.CONNECT_SPEED_CONTRADICTION_DETAIL

FIXED_MISMATCH_RUN_STOP = 1 << 0
FIXED_MISMATCH_DEVCTRLHLT = 1 << 1
FIXED_MISMATCH_PRTCAP = 1 << 2
FIXED_MISMATCH_ALL = (
    FIXED_MISMATCH_RUN_STOP
    | FIXED_MISMATCH_DEVCTRLHLT
    | FIXED_MISMATCH_PRTCAP
)

UDC_STATES = base.UDC_STATES
USB_SPEEDS = base.USB_SPEEDS
STATE_NOT_ATTACHED = base.STATE_NOT_ATTACHED
STATE_CONFIGURED = base.STATE_CONFIGURED
SPEED_UNKNOWN = base.SPEED_UNKNOWN
SPEED_LOW = base.SPEED_LOW
SPEED_FULL = base.SPEED_FULL
SPEED_HIGH = base.SPEED_HIGH
ALLOWED_ENUMERATED_SPEEDS = base.ALLOWED_ENUMERATED_SPEEDS
DSTS_SPEED_BY_CANONICAL = base.DSTS_SPEED_BY_CANONICAL

Position = base.Position
SpecError = base.SpecError
TERMINAL_STAGE = base.TERMINAL_STAGE
POSITIONS = base.POSITIONS
POSITION_SEQUENCE = base.POSITION_SEQUENCE
TERMINAL_GENERATION = base.TERMINAL_GENERATION
TERMINAL_POSITION = base.TERMINAL_POSITION
GENERATION_BY_PAIR = base.GENERATION_BY_PAIR


@dataclass(frozen=True)
class Snapshot:
    link_state: int
    run_stop: int
    devctrlhlt: int
    coreidle: int
    prtcap: int
    susphy: int
    connect_speed: int
    udc_state: int
    udc_speed: int


@dataclass(frozen=True)
class Classification:
    detail: int
    outcome: int
    semantic: str


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")


encode_link_state = base.encode_link_state
decode_link_state = base.decode_link_state
state_speed_category = base.state_speed_category
decode_state_speed_category = base.decode_state_speed_category
encode_final_state = base.encode_final_state
decode_final_state = base.decode_final_state
expected_terminal_outcome = base.expected_terminal_outcome
position_for_generation = base.position_for_generation
generation_for_position = base.generation_for_position


def encode_fixed_mismatch(mask: int) -> int:
    if not 1 <= mask <= FIXED_MISMATCH_ALL:
        raise ValueError("P2.96 fixed-predicate mismatch mask is invalid")
    return FIXED_MISMATCH_DETAIL_BASE + mask - 1


def decode_fixed_mismatch(detail: int) -> int:
    mask = detail - FIXED_MISMATCH_DETAIL_BASE + 1
    if not 1 <= mask <= FIXED_MISMATCH_ALL:
        raise ValueError("P2.96 detail is not a mismatch mask")
    return mask


def classify(snapshot: Snapshot) -> Classification:
    for name, value, bound in (
        ("link_state", snapshot.link_state, 16),
        ("run_stop", snapshot.run_stop, 2),
        ("devctrlhlt", snapshot.devctrlhlt, 2),
        ("coreidle", snapshot.coreidle, 2),
        ("prtcap", snapshot.prtcap, 4),
        ("susphy", snapshot.susphy, 2),
        ("connect_speed", snapshot.connect_speed, 8),
        ("udc_state", snapshot.udc_state, len(UDC_STATES)),
        ("udc_speed", snapshot.udc_speed, len(USB_SPEEDS)),
    ):
        if not 0 <= value < bound:
            raise ValueError(f"P2.96 {name} is outside its raw domain")
    mismatch = 0
    if snapshot.run_stop != 1:
        mismatch |= FIXED_MISMATCH_RUN_STOP
    if snapshot.devctrlhlt != 0:
        mismatch |= FIXED_MISMATCH_DEVCTRLHLT
    if snapshot.prtcap != 2:
        mismatch |= FIXED_MISMATCH_PRTCAP
    if mismatch:
        return Classification(
            encode_fixed_mismatch(mismatch),
            OUTCOME_FAILURE,
            "fixed-digital-predicate-mismatch",
        )
    try:
        state_speed_category(snapshot.udc_state, snapshot.udc_speed)
    except ValueError:
        return Classification(
            STATE_SPEED_CONTRADICTION_DETAIL,
            OUTCOME_FAILURE,
            "udc-state-speed-contradiction",
        )
    if snapshot.udc_speed != SPEED_UNKNOWN:
        expected_speed = DSTS_SPEED_BY_CANONICAL.get(snapshot.udc_speed)
        if expected_speed is None or snapshot.connect_speed != expected_speed:
            return Classification(
                CONNECT_SPEED_CONTRADICTION_DETAIL,
                OUTCOME_FAILURE,
                "udc-dsts-speed-contradiction",
            )
    detail = encode_final_state(
        snapshot.udc_state,
        snapshot.udc_speed,
        snapshot.coreidle,
        snapshot.susphy,
    )
    return Classification(
        detail,
        expected_terminal_outcome(detail),
        "digital-control-state-nominal",
    )


def detail_name(detail: int) -> str:
    try:
        mask = decode_fixed_mismatch(detail)
    except ValueError:
        return base.detail_name(detail)
    return f"fixed-digital-predicate-mismatch-mask-0x{mask:x}"


def detail_kind(detail: int) -> str:
    if (
        FIXED_MISMATCH_DETAIL_BASE
        <= detail
        < FIXED_MISMATCH_DETAIL_BASE + FIXED_MISMATCH_VALUE_COUNT
    ):
        return "dwc3-fixed-predicate-mismatch"
    return base.detail_kind(detail)


@lru_cache(maxsize=1)
def exact_detail_rules() -> tuple[tuple[int, int, int], ...]:
    removed = range(
        FIXED_MISMATCH_DETAIL_BASE + FIXED_MISMATCH_VALUE_COUNT,
        base.FIXED_MISMATCH_DETAIL_BASE + base.FIXED_MISMATCH_VALUE_COUNT,
    )
    return tuple(
        row
        for row in base.exact_detail_rules()
        if not (row[0] == FINAL_STATE_ORDINAL and row[2] in removed)
    )


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
        raise SpecError(
            "slot generation does not match the P2.96 position pair"
        )
    if (generation - 1, outcome, detail) in _exact_rule_set():
        return
    if generation == TERMINAL_GENERATION and detail >= 0xC00:
        raise SpecError("P2.96 terminal detail is outside its declared route")
    base.validate_slot(
        generation=generation,
        stage=stage,
        outcome=outcome,
        item_index=item_index,
        detail=detail,
    )


def descriptor() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "profile": PROFILE,
        "positions": [asdict(position) for position in POSITIONS],
        "delivery": "boot-image-built-in-dwc3-only",
        "link_state": {
            "ordinal": LINK_STATE_ORDINAL,
            "detail_base": LINK_STATE_DETAIL_BASE,
            "value_count": LINK_STATE_VALUE_COUNT,
        },
        "final_state": {
            "ordinal": FINAL_STATE_ORDINAL,
            "detail_base": FINAL_STATE_DETAIL_BASE,
            "value_count": FINAL_STATE_VALUE_COUNT,
            "configured_high_success_count": 4,
        },
        "fixed_mismatch": {
            "detail_base": FIXED_MISMATCH_DETAIL_BASE,
            "value_count": FIXED_MISMATCH_VALUE_COUNT,
            "predicates": ["run_stop", "devctrlhlt", "prtcap"],
        },
        "contradiction_details": [
            STATE_SPEED_CONTRADICTION_DETAIL,
            CONNECT_SPEED_CONTRADICTION_DETAIL,
        ],
        "exact_detail_rules": [list(row) for row in exact_detail_rules()],
    }


def descriptor_sha256() -> str:
    return hashlib.sha256(_canonical(descriptor())).hexdigest()


def validate() -> dict[str, Any]:
    link_values = {encode_link_state(value) for value in range(16)}
    final_values = {
        encode_final_state(state, speed, coreidle, susphy)
        for state in range(len(UDC_STATES))
        for speed in range(len(USB_SPEEDS))
        if (state == STATE_NOT_ATTACHED and speed == SPEED_UNKNOWN)
        or (state != STATE_NOT_ATTACHED and speed in ALLOWED_ENUMERATED_SPEEDS)
        for coreidle in (0, 1)
        for susphy in (0, 1)
    }
    mismatch_values = {
        encode_fixed_mismatch(mask)
        for mask in range(1, FIXED_MISMATCH_ALL + 1)
    }
    if (
        len(POSITIONS) != 107
        or POSITION_SEQUENCE != base.POSITION_SEQUENCE
        or len(link_values) != 16
        or len(final_values) != 132
        or len(mismatch_values) != 7
        or len(exact_detail_rules()) != len(set(exact_detail_rules()))
        or len(exact_detail_rules()) != len(base.exact_detail_rules()) - 8
    ):
        raise ValueError("P2.96 built-in telemetry contract differs")
    return {
        "schema": SCHEMA,
        "descriptor_sha256": descriptor_sha256(),
        "position_count": len(POSITIONS),
        "link_state_value_count": len(link_values),
        "final_state_value_count": len(final_values),
        "fixed_mismatch_value_count": len(mismatch_values),
        "contradiction_value_count": 2,
        "exact_detail_rule_count": len(exact_detail_rules()),
        "external_module_symbol_count": 0,
        "verified": True,
    }


def __getattr__(name: str):
    return getattr(base, name)


validate()


if __name__ == "__main__":
    print(json.dumps(validate(), sort_keys=True))
