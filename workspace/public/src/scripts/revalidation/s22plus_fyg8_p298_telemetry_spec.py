#!/usr/bin/env python3
"""P2.98 gadget-start and downstream-event telemetry contract."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from functools import lru_cache
import hashlib
import json
from typing import Any

import s22plus_fyg8_p296_telemetry_spec as base


SCHEMA = "s22plus_fyg8_p298_gadget_start_event_telemetry_spec_v1"
PROFILE = base.PROFILE

OUTCOME_PROGRESS = base.OUTCOME_PROGRESS
OUTCOME_SUCCESS = base.OUTCOME_SUCCESS
OUTCOME_FAILURE = base.OUTCOME_FAILURE

BIND_ORDINAL = base.BIND_ORDINAL
FINAL_SAMPLING_ORDINAL = base.FINAL_SAMPLING_ORDINAL
EVENT_LINK_ORDINAL = base.LINK_STATE_ORDINAL
FINAL_STATE_ORDINAL = base.FINAL_STATE_ORDINAL
LINK_STATE_ORDINAL = EVENT_LINK_ORDINAL

EVENT_RESET = 1 << 0
EVENT_CONNECT_DONE = 1 << 1
EVENT_MASK_ALL = EVENT_RESET | EVENT_CONNECT_DONE
EVENT_MASK_COUNT = EVENT_MASK_ALL + 1
EVENT_LINK_DETAIL_BASE = 0xD00
EVENT_LINK_VALUE_COUNT = EVENT_MASK_COUNT * 16
LINK_STATE_DETAIL_BASE = EVENT_LINK_DETAIL_BASE
LINK_STATE_VALUE_COUNT = EVENT_LINK_VALUE_COUNT

FINAL_STATE_DETAIL_BASE = 0xE00
FINAL_STATE_VALUE_COUNT = base.FINAL_STATE_VALUE_COUNT
FIXED_MISMATCH_DETAIL_BASE = 0xF80
FIXED_MISMATCH_VALUE_COUNT = 7
STATE_SPEED_CONTRADICTION_DETAIL = 0xF8F
CONNECT_SPEED_CONTRADICTION_DETAIL = 0xF90

FIXED_MISMATCH_RUN_STOP = base.FIXED_MISMATCH_RUN_STOP
FIXED_MISMATCH_DEVCTRLHLT = base.FIXED_MISMATCH_DEVCTRLHLT
FIXED_MISMATCH_PRTCAP = base.FIXED_MISMATCH_PRTCAP
FIXED_MISMATCH_ALL = base.FIXED_MISMATCH_ALL

# Bind observer result contract. These details deliberately occupy distinct
# position families so an installed-but-unreached probe cannot collapse into a
# registration or readback failure.
DETAIL_BIND_TRACE_CONTROL_UNAVAILABLE = 0xF60
DETAIL_BIND_TRACE_REGISTRATION_UNAVAILABLE = 0xF61
DETAIL_BIND_TRACE_SETUP_CLEANUP_UNVERIFIED = 0xF62
DETAIL_BIND_TRACE_SNAPSHOT_READ_FAILED = 0xF63
DETAIL_GADGET_START_NOT_REACHED = 0xF64
DETAIL_GADGET_START_NO_RETURN = 0xF65
DETAIL_GADGET_START_POSITIVE_RC = 0xF66
DETAIL_EP_ENABLE_HIT_CONTRADICTION = 0xF67
DETAIL_EP0_OUT_EINVAL = 0xF68
DETAIL_EP0_OUT_EAGAIN = 0xF69
DETAIL_EP0_OUT_ETIMEDOUT = 0xF6A
DETAIL_EP0_IN_EINVAL = 0xF6B
DETAIL_EP0_IN_EAGAIN = 0xF6C
DETAIL_EP0_IN_ETIMEDOUT = 0xF6D
DETAIL_GADGET_START_NEGATIVE_RC_CONTRADICTION = 0xF6E
DETAIL_BIND_TRACE_SOURCE_CONTRADICTION = 0xF6F
DETAIL_FINAL_TRACE_READBACK_FAILED = 0xF70
DETAIL_FINAL_TRACE_CLEANUP_UNVERIFIED = 0xF71
DETAIL_FINAL_TRACE_PROFILE_MISMATCH = 0xF72

BIND_SETUP_FAILURE_DETAILS = (
    DETAIL_BIND_TRACE_CONTROL_UNAVAILABLE,
    DETAIL_BIND_TRACE_REGISTRATION_UNAVAILABLE,
    DETAIL_BIND_TRACE_SETUP_CLEANUP_UNVERIFIED,
)
BIND_RESULT_FAILURE_DETAILS = (
    DETAIL_BIND_TRACE_SNAPSHOT_READ_FAILED,
    DETAIL_GADGET_START_NOT_REACHED,
    DETAIL_GADGET_START_NO_RETURN,
    DETAIL_GADGET_START_POSITIVE_RC,
    DETAIL_EP_ENABLE_HIT_CONTRADICTION,
    DETAIL_EP0_OUT_EINVAL,
    DETAIL_EP0_OUT_EAGAIN,
    DETAIL_EP0_OUT_ETIMEDOUT,
    DETAIL_EP0_IN_EINVAL,
    DETAIL_EP0_IN_EAGAIN,
    DETAIL_EP0_IN_ETIMEDOUT,
    DETAIL_GADGET_START_NEGATIVE_RC_CONTRADICTION,
    DETAIL_BIND_TRACE_SOURCE_CONTRADICTION,
)
FINAL_TRACE_FAILURE_DETAILS = (
    DETAIL_FINAL_TRACE_READBACK_FAILED,
    DETAIL_FINAL_TRACE_CLEANUP_UNVERIFIED,
    DETAIL_FINAL_TRACE_PROFILE_MISMATCH,
)

FAILURE_DETAIL_NAMES = {
    DETAIL_BIND_TRACE_CONTROL_UNAVAILABLE: "bind-trace-control-unavailable",
    DETAIL_BIND_TRACE_REGISTRATION_UNAVAILABLE: "bind-trace-registration-unavailable",
    DETAIL_BIND_TRACE_SETUP_CLEANUP_UNVERIFIED: "bind-trace-setup-cleanup-unverified",
    DETAIL_BIND_TRACE_SNAPSHOT_READ_FAILED: "bind-trace-snapshot-read-failed",
    DETAIL_GADGET_START_NOT_REACHED: "gadget-start-not-reached",
    DETAIL_GADGET_START_NO_RETURN: "gadget-start-entered-no-return",
    DETAIL_GADGET_START_POSITIVE_RC: "gadget-start-positive-rc-contradiction",
    DETAIL_EP_ENABLE_HIT_CONTRADICTION: "ep0-enable-hit-count-contradiction",
    DETAIL_EP0_OUT_EINVAL: "ep0-out-enable-chain-einval",
    DETAIL_EP0_OUT_EAGAIN: "ep0-out-enable-chain-eagain",
    DETAIL_EP0_OUT_ETIMEDOUT: "ep0-out-enable-chain-etimedout",
    DETAIL_EP0_IN_EINVAL: "ep0-in-enable-chain-einval",
    DETAIL_EP0_IN_EAGAIN: "ep0-in-enable-chain-eagain",
    DETAIL_EP0_IN_ETIMEDOUT: "ep0-in-enable-chain-etimedout",
    DETAIL_GADGET_START_NEGATIVE_RC_CONTRADICTION: "gadget-start-negative-rc-domain-contradiction",
    DETAIL_BIND_TRACE_SOURCE_CONTRADICTION: "bind-trace-source-contradiction",
    DETAIL_FINAL_TRACE_READBACK_FAILED: "final-trace-readback-failed",
    DETAIL_FINAL_TRACE_CLEANUP_UNVERIFIED: "final-trace-cleanup-unverified",
    DETAIL_FINAL_TRACE_PROFILE_MISMATCH: "final-trace-profile-record-mismatch",
}


def start_result_detail(
    *,
    entered: bool,
    returned: bool,
    rc: int,
    ep_enable_hits: int,
) -> int:
    """Classify the bounded gadget-start result retained by the runtime."""
    if not entered:
        return DETAIL_GADGET_START_NOT_REACHED
    if not returned:
        return DETAIL_GADGET_START_NO_RETURN
    if rc > 0:
        return DETAIL_GADGET_START_POSITIVE_RC
    if rc == 0:
        return 0 if ep_enable_hits == 2 else DETAIL_EP_ENABLE_HIT_CONTRADICTION
    if ep_enable_hits not in (1, 2):
        return DETAIL_EP_ENABLE_HIT_CONTRADICTION
    domain = {
        (1, -22): DETAIL_EP0_OUT_EINVAL,
        (1, -11): DETAIL_EP0_OUT_EAGAIN,
        (1, -110): DETAIL_EP0_OUT_ETIMEDOUT,
        (2, -22): DETAIL_EP0_IN_EINVAL,
        (2, -11): DETAIL_EP0_IN_EAGAIN,
        (2, -110): DETAIL_EP0_IN_ETIMEDOUT,
    }
    return domain.get(
        (ep_enable_hits, rc),
        DETAIL_GADGET_START_NEGATIVE_RC_CONTRADICTION,
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
position_for_generation = base.position_for_generation
generation_for_position = base.generation_for_position
state_speed_category = base.state_speed_category
decode_state_speed_category = base.decode_state_speed_category


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


def encode_event_link(event_mask: int, link_state: int) -> int:
    if not 0 <= event_mask < EVENT_MASK_COUNT:
        raise ValueError("P2.98 downstream event mask is invalid")
    if not 0 <= link_state < 16:
        raise ValueError("P2.98 link state is invalid")
    return EVENT_LINK_DETAIL_BASE + event_mask * 16 + link_state


def decode_event_link(detail: int) -> tuple[int, int]:
    index = detail - EVENT_LINK_DETAIL_BASE
    if not 0 <= index < EVENT_LINK_VALUE_COUNT:
        raise ValueError("P2.98 detail is not an event/link value")
    return divmod(index, 16)


def encode_link_state(link_state: int) -> int:
    """Compatibility helper for the no-downstream-event member."""
    return encode_event_link(0, link_state)


def decode_link_state(detail: int) -> int:
    event_mask, link_state = decode_event_link(detail)
    if event_mask != 0:
        raise ValueError("P2.98 detail includes a downstream event")
    return link_state


def encode_final_state(
    state: int, speed: int, coreidle: int, susphy: int
) -> int:
    inherited = base.encode_final_state(state, speed, coreidle, susphy)
    return FINAL_STATE_DETAIL_BASE + inherited - base.FINAL_STATE_DETAIL_BASE


def decode_final_state(detail: int) -> dict[str, int]:
    index = detail - FINAL_STATE_DETAIL_BASE
    if not 0 <= index < FINAL_STATE_VALUE_COUNT:
        raise ValueError("P2.98 detail is not a final state")
    return base.decode_final_state(base.FINAL_STATE_DETAIL_BASE + index)


def encode_fixed_mismatch(mask: int) -> int:
    if not 1 <= mask <= FIXED_MISMATCH_ALL:
        raise ValueError("P2.98 fixed-predicate mismatch mask is invalid")
    return FIXED_MISMATCH_DETAIL_BASE + mask - 1


def decode_fixed_mismatch(detail: int) -> int:
    mask = detail - FIXED_MISMATCH_DETAIL_BASE + 1
    if not 1 <= mask <= FIXED_MISMATCH_ALL:
        raise ValueError("P2.98 detail is not a mismatch mask")
    return mask


def expected_terminal_outcome(detail: int) -> int:
    try:
        decoded = decode_final_state(detail)
    except ValueError:
        if (
            FIXED_MISMATCH_DETAIL_BASE
            <= detail
            < FIXED_MISMATCH_DETAIL_BASE + FIXED_MISMATCH_VALUE_COUNT
            or detail in {
                STATE_SPEED_CONTRADICTION_DETAIL,
                CONNECT_SPEED_CONTRADICTION_DETAIL,
            }
        ):
            return OUTCOME_FAILURE
        raise
    inherited = base.encode_final_state(
        decoded["state"],
        decoded["speed"],
        decoded["coreidle"],
        decoded["susphy"],
    )
    return base.expected_terminal_outcome(inherited)


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
            raise ValueError(f"P2.98 {name} is outside its raw domain")
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


_OLD_LINK_DETAILS = frozenset(
    range(base.LINK_STATE_DETAIL_BASE, base.LINK_STATE_DETAIL_BASE + 16)
)
_OLD_TERMINAL_DETAILS = frozenset(
    (
        *range(
            base.FINAL_STATE_DETAIL_BASE,
            base.FINAL_STATE_DETAIL_BASE + base.FINAL_STATE_VALUE_COUNT,
        ),
        *range(
            base.FIXED_MISMATCH_DETAIL_BASE,
            base.FIXED_MISMATCH_DETAIL_BASE
            + base.FIXED_MISMATCH_VALUE_COUNT,
        ),
        base.STATE_SPEED_CONTRADICTION_DETAIL,
        base.CONNECT_SPEED_CONTRADICTION_DETAIL,
    )
)


@lru_cache(maxsize=1)
def exact_detail_rules() -> tuple[tuple[int, int, int], ...]:
    inherited = (
        row
        for row in base.exact_detail_rules()
        if not (
            row[0] == EVENT_LINK_ORDINAL and row[2] in _OLD_LINK_DETAILS
        )
        and not (
            row[0] == FINAL_STATE_ORDINAL
            and row[2] in _OLD_TERMINAL_DETAILS
        )
    )
    additions = [
        *(
            (EVENT_LINK_ORDINAL, OUTCOME_PROGRESS, detail)
            for detail in range(
                EVENT_LINK_DETAIL_BASE,
                EVENT_LINK_DETAIL_BASE + EVENT_LINK_VALUE_COUNT,
            )
        ),
        *(
            (
                FINAL_STATE_ORDINAL,
                expected_terminal_outcome(detail),
                detail,
            )
            for detail in range(
                FINAL_STATE_DETAIL_BASE,
                FINAL_STATE_DETAIL_BASE + FINAL_STATE_VALUE_COUNT,
            )
        ),
        *(
            (FINAL_STATE_ORDINAL, OUTCOME_FAILURE, detail)
            for detail in range(
                FIXED_MISMATCH_DETAIL_BASE,
                FIXED_MISMATCH_DETAIL_BASE + FIXED_MISMATCH_VALUE_COUNT,
            )
        ),
        (
            FINAL_STATE_ORDINAL,
            OUTCOME_FAILURE,
            STATE_SPEED_CONTRADICTION_DETAIL,
        ),
        (
            FINAL_STATE_ORDINAL,
            OUTCOME_FAILURE,
            CONNECT_SPEED_CONTRADICTION_DETAIL,
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
    return tuple(sorted((*inherited, *additions)))


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
        raise SpecError("slot generation does not match the P2.98 position pair")
    ordinal = generation - 1
    if (ordinal, outcome, detail) in _exact_rule_set():
        return
    if (
        ordinal == EVENT_LINK_ORDINAL and detail in _OLD_LINK_DETAILS
    ) or (
        ordinal == FINAL_STATE_ORDINAL and detail in _OLD_TERMINAL_DETAILS
    ):
        raise SpecError("P2.98 rejects superseded P2.96 telemetry details")
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
        event_mask, link_state = decode_event_link(detail)
    except ValueError:
        pass
    else:
        return f"probe-ok-start-rc0-events-0x{event_mask:x}-link-{link_state}"
    try:
        decoded = decode_final_state(detail)
    except ValueError:
        pass
    else:
        return (
            "probe-ok-start-rc0-final-"
            f"{UDC_STATES[decoded['state']]}-{USB_SPEEDS[decoded['speed']]}-"
            f"coreidle-{decoded['coreidle']}-susphy-{decoded['susphy']}"
        )
    try:
        mask = decode_fixed_mismatch(detail)
    except ValueError:
        if detail == STATE_SPEED_CONTRADICTION_DETAIL:
            return "probe-ok-start-rc0-udc-state-speed-contradiction"
        if detail == CONNECT_SPEED_CONTRADICTION_DETAIL:
            return "probe-ok-start-rc0-udc-dsts-speed-contradiction"
        return base.detail_name(detail)
    return f"probe-ok-start-rc0-fixed-predicate-mismatch-mask-0x{mask:x}"


def detail_kind(detail: int) -> str:
    if detail in FAILURE_DETAIL_NAMES:
        return "gadget-start-observer-failure"
    if EVENT_LINK_DETAIL_BASE <= detail < EVENT_LINK_DETAIL_BASE + EVENT_LINK_VALUE_COUNT:
        return "gadget-start-event-link"
    if FINAL_STATE_DETAIL_BASE <= detail < FINAL_STATE_DETAIL_BASE + FINAL_STATE_VALUE_COUNT:
        return "gadget-start-final-state"
    if FIXED_MISMATCH_DETAIL_BASE <= detail < FIXED_MISMATCH_DETAIL_BASE + 7:
        return "gadget-start-fixed-predicate-mismatch"
    if detail in {STATE_SPEED_CONTRADICTION_DETAIL, CONNECT_SPEED_CONTRADICTION_DETAIL}:
        return "gadget-start-final-contradiction"
    return base.detail_kind(detail)


def descriptor() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "profile": PROFILE,
        "positions": [asdict(position) for position in POSITIONS],
        "delivery": "boot-image-built-in-dwc3-gadget-start-event-probes",
        "historical_control": "P2.96 no-probe behavioral baseline",
        "event_link": {
            "ordinal": EVENT_LINK_ORDINAL,
            "detail_base": EVENT_LINK_DETAIL_BASE,
            "value_count": EVENT_LINK_VALUE_COUNT,
            "event_bits": {"reset": EVENT_RESET, "connect_done": EVENT_CONNECT_DONE},
            "implies": [
                "probe_armed",
                "gadget_start_rc_zero",
                "ep_enable_hit_count_two",
                "trace_profile_exact",
                "trace_cleanup_verified",
            ],
        },
        "final_state": {
            "ordinal": FINAL_STATE_ORDINAL,
            "detail_base": FINAL_STATE_DETAIL_BASE,
            "value_count": FINAL_STATE_VALUE_COUNT,
            "configured_high_success_count": 4,
            "implies": ["probe_armed", "gadget_start_rc_zero"],
        },
        "fixed_mismatch": {
            "detail_base": FIXED_MISMATCH_DETAIL_BASE,
            "value_count": FIXED_MISMATCH_VALUE_COUNT,
            "predicates": ["run_stop", "devctrlhlt", "prtcap"],
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
    event_values = {
        encode_event_link(mask, link)
        for mask in range(EVENT_MASK_COUNT)
        for link in range(16)
    }
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
        encode_fixed_mismatch(mask) for mask in range(1, FIXED_MISMATCH_ALL + 1)
    }
    rules = exact_detail_rules()
    if (
        len(POSITIONS) != 107
        or POSITION_SEQUENCE != base.POSITION_SEQUENCE
        or len(event_values) != 64
        or len(final_values) != 132
        or len(mismatch_values) != 7
        or len(rules) != len(set(rules))
        or any(detail in _OLD_LINK_DETAILS for detail in event_values)
        or any(detail in _OLD_TERMINAL_DETAILS for detail in final_values)
    ):
        raise ValueError("P2.98 gadget-start telemetry contract differs")
    return {
        "schema": SCHEMA,
        "descriptor_sha256": descriptor_sha256(),
        "position_count": len(POSITIONS),
        "event_link_value_count": len(event_values),
        "final_state_value_count": len(final_values),
        "fixed_mismatch_value_count": len(mismatch_values),
        "observer_failure_value_count": len(FAILURE_DETAIL_NAMES),
        "exact_detail_rule_count": len(rules),
        "bind_event_count": 12,
        "verified": True,
    }


def __getattr__(name: str):
    return getattr(base, name)


validate()


if __name__ == "__main__":
    print(json.dumps(validate(), sort_keys=True))
