#!/usr/bin/env python3
"""P3.13 post-bind resume-cycle retained telemetry contract."""

from __future__ import annotations

from functools import lru_cache
from itertools import product
from typing import Any

import s22plus_fyg8_p312_telemetry_spec as carrier


SCHEMA = "s22plus_fyg8_p313_telemetry_spec_v1"
PROFILE = carrier.PROFILE
ATTR_ORDINAL = carrier.ATTR_ORDINAL
SUMMARY_ORDINAL = carrier.SUMMARY_ORDINAL
OUTCOME_PROGRESS = carrier.carrier_spec.OUTCOME_PROGRESS
OUTCOME_FAILURE = carrier.carrier_spec.OUTCOME_FAILURE
POSITIONS = carrier.POSITIONS
TERMINAL_POSITION = carrier.TERMINAL_POSITION
position_for_generation = carrier.position_for_generation
SpecError = carrier.SpecError

ROLE_EVENT_COUNT = 5
DIRECT_EVENT_COUNT = 15
CYCLE_EVENT_COUNT = 25
RECORD_CAPACITY = 64
DIRECT_PREFIX_CAPACITY = 32
DIRECT_CLEAN_PREFIX = 10
DIRECT_DRIFT_PREFIX_MAX = 22
DIRECT_CONTRADICTION_PREFIX_MIN = 23
CYCLE_CLEAN_RECORDS = 37
CYCLE_DRIFT_RECORDS = 45
CYCLE_OVERFLOW_RECORDS = 65

UDC_STATES = (
    "not attached",
    "attached",
    "powered",
    "default",
    "addressed",
    "configured",
    "reconnecting",
    "unauthenticated",
    "suspended",
)
USB_SPEEDS = (
    "UNKNOWN",
    "low-speed",
    "full-speed",
    "high-speed",
    "wireless",
    "super-speed",
    "super-speed-plus",
)

A_DETAIL_BASE = 0xD00
A_CYCLE_STRIDE = len(UDC_STATES) * len(USB_SPEEDS)
A_VALUE_COUNT = 2 * A_CYCLE_STRIDE
A_DETAIL_MAX = A_DETAIL_BASE + A_VALUE_COUNT - 1

NORMAL_DETAIL_BASE = 0x4801
NORMAL_VALUE_COUNT = 1 << 10
NORMAL_DETAIL_MAX = NORMAL_DETAIL_BASE + NORMAL_VALUE_COUNT - 1
DIRECT_DETAIL_BASE = 0x4C01
DIRECT_LATE_SUCCESS = DIRECT_DETAIL_BASE
DIRECT_NONBASELINE_ACTIVITY = DIRECT_DETAIL_BASE + 1
DIRECT_DETAIL_MAX = DIRECT_NONBASELINE_ACTIVITY

CONTROLLER_DETAIL_BASE = 0x5001
CONTROLLER_SOURCE_COUNT = 10
ERRNO_BUCKET_COUNT = 8
CONTROLLER_VALUE_COUNT = CONTROLLER_SOURCE_COUNT * ERRNO_BUCKET_COUNT
CONTROLLER_DETAIL_MAX = CONTROLLER_DETAIL_BASE + CONTROLLER_VALUE_COUNT - 1
CONTROLLER_SOURCE_NAMES = (
    "stop-mode-write",
    "child-runtime-suspend",
    "stop-run-stop",
    "phy-power-off",
    "restart-mode-write",
    "child-runtime-resume",
    "phy-init",
    "phy-power-on",
    "gadget-start",
    "start-run-stop",
)
ERRNO_BUCKET_NAMES = (
    "ETIMEDOUT",
    "EBUSY",
    "EINVAL",
    "EAGAIN",
    "EIO",
    "ENODEV",
    "ENOMEM",
    "OTHER_NEG",
)

DRIFT_DETAIL_BASE = 0x5061
DRIFT_MASK_MAX = 0x1F
DRIFT_VALUE_COUNT = DRIFT_MASK_MAX
DRIFT_DETAIL_MAX = DRIFT_DETAIL_BASE + DRIFT_VALUE_COUNT - 1
DRIFT_PULLUP = 1 << 0
DRIFT_START_QSCRATCH = 1 << 1
DRIFT_OUTER_WORK = 1 << 2
DRIFT_RESUME_NESTING = 1 << 3
DRIFT_UDC_ROLE_DIRECT = 1 << 4

CONTRADICTION_DETAIL_BASE = 0x6701
CONTRADICTION_VALUE_COUNT = 63
CONTRADICTION_DETAIL_MAX = (
    CONTRADICTION_DETAIL_BASE + CONTRADICTION_VALUE_COUNT - 1
)
_NAMED_CONTRADICTIONS = (
    "trace-control-unavailable",
    "trace-registration-unavailable",
    "trace-cleanup-unverified",
    "trace-snapshot-read-failed",
    "profile-record-deficit",
    "trace-ring-loss",
    "record-format-contradiction",
    "role-qscratch-missing",
    "role-qscratch-duplicate",
    "role-qscratch-foreign-pid",
    "role-qscratch-order",
    "role-qscratch-value",
    "direct-prefix-multiplicity",
    "direct-trigger-state",
    "direct-stream-integrity",
    "direct-pointer-contradiction",
    "cycle-record-overflow",
    "cycle-event-multiplicity",
    "cycle-pairing-contradiction",
    "cycle-positive-return",
    "cycle-qscratch-contradiction",
    "cycle-snapshot-contradiction",
    "cycle-pointer-contradiction",
    "cycle-timeout-or-unreaped-helper",
    "cycle-readback-contradiction",
    "cycle-udc-binding-drift",
    "cycle-parent-pm-contradiction",
    "cycle-child-pm-contradiction",
    "cycle-resume-precondition-unproved",
    "cycle-final-state-unstable",
    "terminal-domain-contradiction",
    "checkpoint-position-contradiction",
)
CONTRADICTION_DETAIL_NAMES = {
    CONTRADICTION_DETAIL_BASE + index: (
        _NAMED_CONTRADICTIONS[index]
        if index < len(_NAMED_CONTRADICTIONS)
        else f"reserved-observer-contradiction-{index + 1:02d}"
    )
    for index in range(CONTRADICTION_VALUE_COUNT)
}


def encode_a(*, cycle_attempted: int, state_index: int, speed_index: int) -> int:
    if cycle_attempted not in (0, 1):
        raise ValueError("P3.13 cycle-attempted flag differs")
    if not 0 <= state_index < len(UDC_STATES):
        raise ValueError("P3.13 UDC state differs")
    if not 0 <= speed_index < len(USB_SPEEDS):
        raise ValueError("P3.13 USB speed differs")
    return (
        A_DETAIL_BASE
        + cycle_attempted * A_CYCLE_STRIDE
        + state_index * len(USB_SPEEDS)
        + speed_index
    )


def decode_a(detail: int) -> dict[str, Any]:
    index = detail - A_DETAIL_BASE
    if not 0 <= index < A_VALUE_COUNT:
        raise ValueError("P3.13 A detail differs")
    cycle_attempted, remainder = divmod(index, A_CYCLE_STRIDE)
    state_index, speed_index = divmod(remainder, len(USB_SPEEDS))
    return {
        "cycle_attempted": cycle_attempted,
        "state_index": state_index,
        "state": UDC_STATES[state_index],
        "speed_index": speed_index,
        "speed": USB_SPEEDS[speed_index],
    }


def encode_normal(delta_mask: int) -> int:
    if not 0 <= delta_mask < NORMAL_VALUE_COUNT:
        raise ValueError("P3.13 tuple delta differs")
    return NORMAL_DETAIL_BASE + delta_mask


def encode_direct(kind: str) -> int:
    values = {
        "late-success": DIRECT_LATE_SUCCESS,
        "nonbaseline-activity": DIRECT_NONBASELINE_ACTIVITY,
    }
    try:
        return values[kind]
    except KeyError as exc:
        raise ValueError("P3.13 direct branch differs") from exc


def encode_controller(source: int, errno_bucket: int) -> int:
    if not 0 <= source < CONTROLLER_SOURCE_COUNT:
        raise ValueError("P3.13 controller source differs")
    if not 0 <= errno_bucket < ERRNO_BUCKET_COUNT:
        raise ValueError("P3.13 errno bucket differs")
    return CONTROLLER_DETAIL_BASE + source * ERRNO_BUCKET_COUNT + errno_bucket


def encode_drift(mask: int) -> int:
    if not 1 <= mask <= DRIFT_MASK_MAX:
        raise ValueError("P3.13 drift mask differs")
    return DRIFT_DETAIL_BASE + mask - 1


def decode_b(detail: int) -> dict[str, Any]:
    if NORMAL_DETAIL_BASE <= detail <= NORMAL_DETAIL_MAX:
        return {"kind": "normal-cycle", "delta_mask": detail - NORMAL_DETAIL_BASE}
    if detail == DIRECT_LATE_SUCCESS:
        return {"kind": "direct-late-success"}
    if detail == DIRECT_NONBASELINE_ACTIVITY:
        return {"kind": "direct-nonbaseline-activity"}
    if CONTROLLER_DETAIL_BASE <= detail <= CONTROLLER_DETAIL_MAX:
        source, bucket = divmod(detail - CONTROLLER_DETAIL_BASE, ERRNO_BUCKET_COUNT)
        return {
            "kind": "controller-device-result",
            "source": source,
            "source_name": CONTROLLER_SOURCE_NAMES[source],
            "errno_bucket": bucket,
            "errno_bucket_name": ERRNO_BUCKET_NAMES[bucket],
        }
    if DRIFT_DETAIL_BASE <= detail <= DRIFT_DETAIL_MAX:
        return {"kind": "path-drift", "drift_mask": detail - DRIFT_DETAIL_BASE + 1}
    if detail in CONTRADICTION_DETAIL_NAMES:
        return {
            "kind": "observer-contradiction",
            "name": CONTRADICTION_DETAIL_NAMES[detail],
        }
    raise ValueError("P3.13 B detail differs")


@lru_cache(maxsize=1)
def a_outputs() -> tuple[int, ...]:
    return tuple(
        encode_a(cycle_attempted=cycle, state_index=state, speed_index=speed)
        for cycle, state, speed in product(
            range(2), range(len(UDC_STATES)), range(len(USB_SPEEDS))
        )
    )


@lru_cache(maxsize=1)
def b_outputs() -> tuple[int, ...]:
    values = {
        *(encode_normal(mask) for mask in range(NORMAL_VALUE_COUNT)),
        DIRECT_LATE_SUCCESS,
        DIRECT_NONBASELINE_ACTIVITY,
        *(encode_controller(source, bucket)
          for source in range(CONTROLLER_SOURCE_COUNT)
          for bucket in range(ERRNO_BUCKET_COUNT)),
        *(encode_drift(mask) for mask in range(1, DRIFT_MASK_MAX + 1)),
        *CONTRADICTION_DETAIL_NAMES,
    }
    return tuple(sorted(values))


def validate_slot(
    *, generation: int, stage: int, outcome: int, item_index: int, detail: int
) -> None:
    position = position_for_generation(generation)
    if (stage, item_index) != position.pair:
        raise SpecError("P3.13 carrier position differs")
    if generation == ATTR_ORDINAL + 1:
        if outcome != OUTCOME_PROGRESS or detail not in a_outputs():
            raise SpecError("P3.13 A slot differs")
        return
    if generation == SUMMARY_ORDINAL + 1:
        if outcome != OUTCOME_FAILURE or detail not in b_outputs():
            raise SpecError("P3.13 B slot differs")
        return
    raise SpecError("P3.13 retained generation differs")


def validate() -> dict[str, Any]:
    a_values = a_outputs()
    b_values = b_outputs()
    if len(a_values) != 126 or a_values[0] != 0xD00 or a_values[-1] != 0xD7D:
        raise ValueError("P3.13 A extent differs")
    if len(b_values) != 1200:
        raise ValueError("P3.13 B extent differs")
    for detail in a_values:
        decoded = decode_a(detail)
        if encode_a(
            cycle_attempted=decoded["cycle_attempted"],
            state_index=decoded["state_index"],
            speed_index=decoded["speed_index"],
        ) != detail:
            raise ValueError("P3.13 A round trip differs")
        position = position_for_generation(ATTR_ORDINAL + 1)
        validate_slot(
            generation=ATTR_ORDINAL + 1,
            stage=position.stage,
            outcome=OUTCOME_PROGRESS,
            item_index=position.item_index,
            detail=detail,
        )
    for detail in b_values:
        decode_b(detail)
        position = position_for_generation(SUMMARY_ORDINAL + 1)
        validate_slot(
            generation=SUMMARY_ORDINAL + 1,
            stage=position.stage,
            outcome=OUTCOME_FAILURE,
            item_index=position.item_index,
            detail=detail,
        )
    return {
        "schema": SCHEMA,
        "a_detail_range": [A_DETAIL_BASE, A_DETAIL_MAX],
        "a_output_count": len(a_values),
        "b_output_count": len(b_values),
        "normal_detail_range": [NORMAL_DETAIL_BASE, NORMAL_DETAIL_MAX],
        "direct_detail_range": [DIRECT_DETAIL_BASE, DIRECT_DETAIL_MAX],
        "controller_detail_range": [CONTROLLER_DETAIL_BASE, CONTROLLER_DETAIL_MAX],
        "drift_detail_range": [DRIFT_DETAIL_BASE, DRIFT_DETAIL_MAX],
        "contradiction_detail_range": [
            CONTRADICTION_DETAIL_BASE,
            CONTRADICTION_DETAIL_MAX,
        ],
        "role_event_count": ROLE_EVENT_COUNT,
        "direct_event_count": DIRECT_EVENT_COUNT,
        "cycle_event_count": CYCLE_EVENT_COUNT,
        "record_capacity": RECORD_CAPACITY,
        "direct_prefix_capacity": DIRECT_PREFIX_CAPACITY,
        "cycle_record_contract": [
            CYCLE_CLEAN_RECORDS,
            CYCLE_DRIFT_RECORDS,
            CYCLE_OVERFLOW_RECORDS,
        ],
        "fixed_image_gate_compatible": True,
        "verified": True,
    }


if __name__ == "__main__":
    import json

    print(json.dumps(validate(), sort_keys=True))
