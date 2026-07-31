#!/usr/bin/env python3
"""P2.94 two-slot DWC3 value-telemetry single source of truth."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from functools import lru_cache
import hashlib
import json
from typing import Any

import s22plus_fyg8_p282_contract_spec as legacy
import s22plus_fyg8_p290_contract_spec as base
import s22plus_fyg8_p292_repair_spec as repair


SCHEMA = "s22plus_fyg8_p294_value_telemetry_spec_v1"
PROFILE = repair.PROFILE

OUTCOME_PROGRESS = 0
OUTCOME_SUCCESS = 1
OUTCOME_FAILURE = 2

BIND_ORDINAL = 103
FINAL_SAMPLING_ORDINAL = 104
LINK_STATE_ORDINAL = 105
FINAL_STATE_ORDINAL = 106

LINK_STATE_DETAIL_BASE = 0xC60
LINK_STATE_VALUE_COUNT = 16
FINAL_STATE_DETAIL_BASE = 0xC70
FINAL_STATE_VALUE_COUNT = 132
FIXED_MISMATCH_DETAIL_BASE = 0xF40
FIXED_MISMATCH_VALUE_COUNT = 15
STATE_SPEED_CONTRADICTION_DETAIL = 0xF4F
CONNECT_SPEED_CONTRADICTION_DETAIL = 0xF50

FIXED_MISMATCH_RUN_STOP = 1 << 0
FIXED_MISMATCH_DEVCTRLHLT = 1 << 1
FIXED_MISMATCH_PRTCAP = 1 << 2
FIXED_MISMATCH_VBUS_VALID = 1 << 3
FIXED_MISMATCH_ALL = (
    FIXED_MISMATCH_RUN_STOP
    | FIXED_MISMATCH_DEVCTRLHLT
    | FIXED_MISMATCH_PRTCAP
    | FIXED_MISMATCH_VBUS_VALID
)

UDC_STATES = tuple(legacy.CANONICAL_UDC_STATES)
USB_SPEEDS = tuple(legacy.CANONICAL_SPEEDS)
STATE_NOT_ATTACHED = UDC_STATES.index("not attached")
STATE_CONFIGURED = UDC_STATES.index("configured")
SPEED_UNKNOWN = USB_SPEEDS.index("UNKNOWN")
SPEED_LOW = USB_SPEEDS.index("low-speed")
SPEED_FULL = USB_SPEEDS.index("full-speed")
SPEED_HIGH = USB_SPEEDS.index("high-speed")
ALLOWED_ENUMERATED_SPEEDS = (
    SPEED_UNKNOWN,
    SPEED_LOW,
    SPEED_FULL,
    SPEED_HIGH,
)
DSTS_SPEED_BY_CANONICAL = {
    SPEED_LOW: 2,
    SPEED_FULL: 1,
    SPEED_HIGH: 0,
}


@dataclass(frozen=True)
class Snapshot:
    link_state: int
    run_stop: int
    devctrlhlt: int
    coreidle: int
    prtcap: int
    susphy: int
    connect_speed: int
    vbus_valid: int
    udc_state: int
    udc_speed: int


@dataclass(frozen=True)
class Classification:
    detail: int
    outcome: int
    semantic: str


Position = base.Position
SpecError = base.SpecError
TERMINAL_STAGE = base.TERMINAL_STAGE
POSITIONS = (
    *base.POSITIONS[:LINK_STATE_ORDINAL],
    Position(
        "link_state_sampled",
        base.POSITIONS[LINK_STATE_ORDINAL].stage,
        base.POSITIONS[LINK_STATE_ORDINAL].item_index,
        base.POSITIONS[LINK_STATE_ORDINAL].kind,
    ),
    Position(
        "final_state",
        base.POSITIONS[FINAL_STATE_ORDINAL].stage,
        base.POSITIONS[FINAL_STATE_ORDINAL].item_index,
        base.POSITIONS[FINAL_STATE_ORDINAL].kind,
    ),
)
POSITION_SEQUENCE = tuple(position.pair for position in POSITIONS)
TERMINAL_GENERATION = len(POSITIONS)
TERMINAL_POSITION = POSITIONS[-1].pair
GENERATION_BY_PAIR = {
    position.pair: generation
    for generation, position in enumerate(POSITIONS, 1)
}


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")


def encode_link_state(link_state: int) -> int:
    if not 0 <= link_state < LINK_STATE_VALUE_COUNT:
        raise ValueError("P2.94 USBLNKST is outside the four-bit domain")
    return LINK_STATE_DETAIL_BASE + link_state


def decode_link_state(detail: int) -> int:
    value = detail - LINK_STATE_DETAIL_BASE
    if not 0 <= value < LINK_STATE_VALUE_COUNT:
        raise ValueError("P2.94 detail is not a USBLNKST value")
    return value


def state_speed_category(state: int, speed: int) -> int:
    if state == STATE_NOT_ATTACHED:
        if speed != SPEED_UNKNOWN:
            raise ValueError("not-attached requires UNKNOWN speed")
        return 0
    if not 1 <= state < len(UDC_STATES):
        raise ValueError("P2.94 UDC state is outside the canonical table")
    if speed not in ALLOWED_ENUMERATED_SPEEDS:
        raise ValueError("P2.94 enumerated state has an unsupported speed")
    return 1 + (state - 1) * len(ALLOWED_ENUMERATED_SPEEDS) + speed


def decode_state_speed_category(category: int) -> tuple[int, int]:
    if category == 0:
        return STATE_NOT_ATTACHED, SPEED_UNKNOWN
    if not 1 <= category < 33:
        raise ValueError("P2.94 state/speed category is outside the domain")
    offset = category - 1
    state = 1 + offset // len(ALLOWED_ENUMERATED_SPEEDS)
    speed = offset % len(ALLOWED_ENUMERATED_SPEEDS)
    return state, speed


def encode_final_state(
    state: int, speed: int, coreidle: int, susphy: int
) -> int:
    if coreidle not in (0, 1) or susphy not in (0, 1):
        raise ValueError("P2.94 sampled boolean is not one bit")
    category = state_speed_category(state, speed)
    index = ((category * 2 + coreidle) * 2) + susphy
    if not 0 <= index < FINAL_STATE_VALUE_COUNT:
        raise ValueError("P2.94 final-state index is outside the domain")
    return FINAL_STATE_DETAIL_BASE + index


def decode_final_state(detail: int) -> dict[str, int]:
    index = detail - FINAL_STATE_DETAIL_BASE
    if not 0 <= index < FINAL_STATE_VALUE_COUNT:
        raise ValueError("P2.94 detail is not a final-state value")
    susphy = index & 1
    coreidle = (index >> 1) & 1
    category = index >> 2
    state, speed = decode_state_speed_category(category)
    return {
        "state": state,
        "speed": speed,
        "coreidle": coreidle,
        "susphy": susphy,
    }


def encode_fixed_mismatch(mask: int) -> int:
    if not 1 <= mask <= FIXED_MISMATCH_ALL:
        raise ValueError("P2.94 fixed-predicate mismatch mask is invalid")
    return FIXED_MISMATCH_DETAIL_BASE + mask - 1


def decode_fixed_mismatch(detail: int) -> int:
    mask = detail - FIXED_MISMATCH_DETAIL_BASE + 1
    if not 1 <= mask <= FIXED_MISMATCH_ALL:
        raise ValueError("P2.94 detail is not a mismatch mask")
    return mask


def expected_terminal_outcome(detail: int) -> int:
    try:
        decoded = decode_final_state(detail)
    except ValueError:
        if (
            FIXED_MISMATCH_DETAIL_BASE
            <= detail
            < FIXED_MISMATCH_DETAIL_BASE + FIXED_MISMATCH_VALUE_COUNT
            or detail
            in (
                STATE_SPEED_CONTRADICTION_DETAIL,
                CONNECT_SPEED_CONTRADICTION_DETAIL,
            )
        ):
            return OUTCOME_FAILURE
        raise
    return (
        OUTCOME_SUCCESS
        if decoded["state"] == STATE_CONFIGURED
        and decoded["speed"] == SPEED_HIGH
        else OUTCOME_FAILURE
    )


def classify(snapshot: Snapshot) -> Classification:
    for name, value, bound in (
        ("link_state", snapshot.link_state, 16),
        ("run_stop", snapshot.run_stop, 2),
        ("devctrlhlt", snapshot.devctrlhlt, 2),
        ("coreidle", snapshot.coreidle, 2),
        ("prtcap", snapshot.prtcap, 4),
        ("susphy", snapshot.susphy, 2),
        ("connect_speed", snapshot.connect_speed, 8),
        ("vbus_valid", snapshot.vbus_valid, 2),
        ("udc_state", snapshot.udc_state, len(UDC_STATES)),
        ("udc_speed", snapshot.udc_speed, len(USB_SPEEDS)),
    ):
        if not 0 <= value < bound:
            raise ValueError(f"P2.94 {name} is outside its raw domain")
    mismatch = 0
    if snapshot.run_stop != 1:
        mismatch |= FIXED_MISMATCH_RUN_STOP
    if snapshot.devctrlhlt != 0:
        mismatch |= FIXED_MISMATCH_DEVCTRLHLT
    if snapshot.prtcap != 2:
        mismatch |= FIXED_MISMATCH_PRTCAP
    if snapshot.vbus_valid != 1:
        mismatch |= FIXED_MISMATCH_VBUS_VALID
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
        return f"usblnkst-{decode_link_state(detail)}"
    except ValueError:
        pass
    try:
        decoded = decode_final_state(detail)
    except ValueError:
        pass
    else:
        return (
            "digital-control-state-nominal-"
            f"{UDC_STATES[decoded['state']]}-"
            f"{USB_SPEEDS[decoded['speed']]}-"
            f"coreidle-{decoded['coreidle']}-susphy-{decoded['susphy']}"
        )
    try:
        mask = decode_fixed_mismatch(detail)
    except ValueError:
        pass
    else:
        return f"fixed-digital-predicate-mismatch-mask-0x{mask:x}"
    if detail == STATE_SPEED_CONTRADICTION_DETAIL:
        return "udc-state-speed-contradiction"
    if detail == CONNECT_SPEED_CONTRADICTION_DETAIL:
        return "udc-dsts-speed-contradiction"
    return base.detail_name(detail)


def detail_kind(detail: int) -> str:
    if LINK_STATE_DETAIL_BASE <= detail < LINK_STATE_DETAIL_BASE + 16:
        return "dwc3-link-state"
    if FINAL_STATE_DETAIL_BASE <= detail < FINAL_STATE_DETAIL_BASE + 132:
        return "dwc3-final-state"
    if (
        FIXED_MISMATCH_DETAIL_BASE
        <= detail
        < FIXED_MISMATCH_DETAIL_BASE + 15
    ):
        return "dwc3-fixed-predicate-mismatch"
    if detail in (
        STATE_SPEED_CONTRADICTION_DETAIL,
        CONNECT_SPEED_CONTRADICTION_DETAIL,
    ):
        return "dwc3-state-contradiction"
    return base.detail_kind(detail)


@lru_cache(maxsize=1)
def exact_detail_rules() -> tuple[tuple[int, int, int], ...]:
    rows = [
        row
        for row in base.exact_detail_rules()
        if row[0] < BIND_ORDINAL
        or (row[0] == BIND_ORDINAL and row[2] not in range(0xC41, 0xC47))
        or row[0] in (FINAL_SAMPLING_ORDINAL, LINK_STATE_ORDINAL)
        and row[2] in (0xC4B, 0xC5E)
    ]
    rows.extend((BIND_ORDINAL, OUTCOME_FAILURE, value) for value in range(0xC41, 0xC47))
    rows.extend(
        (LINK_STATE_ORDINAL, OUTCOME_PROGRESS, encode_link_state(value))
        for value in range(LINK_STATE_VALUE_COUNT)
    )
    for index in range(FINAL_STATE_VALUE_COUNT):
        detail = FINAL_STATE_DETAIL_BASE + index
        rows.append(
            (FINAL_STATE_ORDINAL, expected_terminal_outcome(detail), detail)
        )
    rows.extend(
        (FINAL_STATE_ORDINAL, OUTCOME_FAILURE, encode_fixed_mismatch(mask))
        for mask in range(1, FIXED_MISMATCH_ALL + 1)
    )
    rows.extend(
        (
            (FINAL_STATE_ORDINAL, OUTCOME_FAILURE, STATE_SPEED_CONTRADICTION_DETAIL),
            (FINAL_STATE_ORDINAL, OUTCOME_FAILURE, CONNECT_SPEED_CONTRADICTION_DETAIL),
        )
    )
    return tuple(sorted(set(rows)))


@lru_cache(maxsize=1)
def _exact_value_universe() -> frozenset[int]:
    return frozenset(
        row[2] for row in (*base.exact_detail_rules(), *exact_detail_rules())
    )


@lru_cache(maxsize=1)
def _exact_rule_set() -> frozenset[tuple[int, int, int]]:
    return frozenset(exact_detail_rules())


def position_for_generation(generation: int) -> Position:
    if (
        isinstance(generation, bool)
        or not isinstance(generation, int)
        or not 1 <= generation <= len(POSITIONS)
    ):
        raise SpecError("P2.94 generation is outside its position sequence")
    return POSITIONS[generation - 1]


def generation_for_position(stage: int, item_index: int) -> int:
    try:
        return GENERATION_BY_PAIR[(stage, item_index)]
    except KeyError as exc:
        raise SpecError(
            f"position (0x{stage:02x},{item_index}) is outside P2.94"
        ) from exc


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
            "slot generation does not match the P2.94 position pair"
        )
    ordinal = generation - 1
    if (ordinal, outcome, detail) in _exact_rule_set():
        return
    if detail in _exact_value_universe() or detail >= 0xC00:
        raise SpecError("P2.94 exact detail is outside its declared route")
    try:
        base.validate_slot(
            generation=generation,
            stage=stage,
            outcome=outcome,
            item_index=item_index,
            detail=detail,
        )
    except base.SpecError as exc:
        raise SpecError(str(exc)) from exc
    if generation == TERMINAL_GENERATION:
        raise SpecError("P2.94 terminal slot requires declared telemetry")


def descriptor() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "profile": PROFILE,
        "positions": [asdict(position) for position in POSITIONS],
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
    if (
        len(POSITIONS) != 107
        or POSITION_SEQUENCE != base.POSITION_SEQUENCE
        or TERMINAL_GENERATION != 107
        or TERMINAL_POSITION != base.TERMINAL_POSITION
        or len({position.pair for position in POSITIONS}) != len(POSITIONS)
    ):
        raise ValueError("P2.94 position ABI differs")
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
        encode_fixed_mismatch(mask) for mask in range(1, 16)
    }
    if (
        len(link_values) != 16
        or len(final_values) != 132
        or len(mismatch_values) != 15
        or link_values & final_values
        or (link_values | final_values) & mismatch_values
        or max(final_values) >= 0xD00
        or min(mismatch_values) <= 0xF36
        or len(exact_detail_rules()) != len(set(exact_detail_rules()))
    ):
        raise ValueError("P2.94 telemetry detail partition differs")
    return {
        "schema": SCHEMA,
        "descriptor_sha256": descriptor_sha256(),
        "position_count": len(POSITIONS),
        "normal_value_count": len(link_values) + len(final_values),
        "link_state_value_count": len(link_values),
        "final_state_value_count": len(final_values),
        "fixed_mismatch_value_count": len(mismatch_values),
        "contradiction_value_count": 2,
        "exact_detail_rule_count": len(exact_detail_rules()),
        "verified": True,
    }


def __getattr__(name: str):
    return getattr(base, name)


validate()


if __name__ == "__main__":
    print(json.dumps(validate(), sort_keys=True))
