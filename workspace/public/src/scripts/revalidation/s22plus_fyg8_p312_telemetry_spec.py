#!/usr/bin/env python3
"""P3.12 early-clock telemetry over the fixed Carrier-v2 ABI."""

from __future__ import annotations

import s22plus_fyg8_p308_telemetry_spec as carrier_spec
import s22plus_fyg8_p311_telemetry_spec as inherited


PROFILE = inherited.PROFILE
ATTR_ORDINAL = inherited.ATTR_ORDINAL
SUMMARY_ORDINAL = inherited.SUMMARY_ORDINAL
EARLY_EVENT_COUNT = inherited.EARLY_EVENT_COUNT
CALLSITE_EVENT_BASE = inherited.CALLSITE_EVENT_BASE
CALLSITE_COUNT = inherited.CALLSITE_COUNT
RECORD_CAPACITY = inherited.RECORD_CAPACITY
DOMAIN_PROBE = inherited.DOMAIN_PROBE
DOMAIN_SET_SUSPEND = inherited.DOMAIN_SET_SUSPEND
DOMAIN_INIT = inherited.DOMAIN_INIT
DOMAIN_NONE = inherited.DOMAIN_NONE
DOMAIN_COUNT = inherited.DOMAIN_COUNT
REACH_PROBE = inherited.REACH_PROBE
REACH_INIT = inherited.REACH_INIT
REACH_SET_SUSPEND_ZERO = inherited.REACH_SET_SUSPEND_ZERO
REACH_MASK_COUNT = inherited.REACH_MASK_COUNT
MULTI_PATH_COUNT = inherited.MULTI_PATH_COUNT
QSCRATCH_STATE_COUNT = inherited.QSCRATCH_STATE_COUNT
CLOCK_STATE_COUNT = inherited.CLOCK_STATE_COUNT
CLOCK_PAIR_COUNT = inherited.CLOCK_PAIR_COUNT
FIRST_DETAIL_BASE = inherited.FIRST_DETAIL_BASE
FIRST_DETAIL_NO_CLOCK_PATH = inherited.FIRST_DETAIL_NO_CLOCK_PATH
FIRST_DETAIL_MAX = inherited.FIRST_DETAIL_MAX
SUMMARY_DETAIL_BASE = inherited.SUMMARY_DETAIL_BASE
SUMMARY_VALUE_COUNT = inherited.SUMMARY_VALUE_COUNT
SUMMARY_DETAIL_MAX = inherited.SUMMARY_DETAIL_MAX
DETAIL_EARLY_TRACE_CONTROL_UNAVAILABLE = inherited.DETAIL_EARLY_TRACE_CONTROL_UNAVAILABLE
DETAIL_EARLY_TRACE_REGISTRATION_UNAVAILABLE = inherited.DETAIL_EARLY_TRACE_REGISTRATION_UNAVAILABLE
DETAIL_EARLY_TRACE_CLEANUP_UNVERIFIED = inherited.DETAIL_EARLY_TRACE_CLEANUP_UNVERIFIED
DETAIL_EARLY_TRACE_SNAPSHOT_READ_FAILED = inherited.DETAIL_EARLY_TRACE_SNAPSHOT_READ_FAILED
DETAIL_EARLY_PROFILE_RECORD_MISMATCH = inherited.DETAIL_EARLY_PROFILE_RECORD_MISMATCH
DETAIL_EARLY_RECORD_FORMAT_CONTRADICTION = inherited.DETAIL_EARLY_RECORD_FORMAT_CONTRADICTION
DETAIL_EARLY_CALLER_PAIR_CONTRADICTION = inherited.DETAIL_EARLY_CALLER_PAIR_CONTRADICTION
DETAIL_EARLY_CALLSITE_FLOW_CONTRADICTION = inherited.DETAIL_EARLY_CALLSITE_FLOW_CONTRADICTION
DETAIL_EARLY_CALLSITE_RETURN_CONTRADICTION = inherited.DETAIL_EARLY_CALLSITE_RETURN_CONTRADICTION
DETAIL_EARLY_CFG_AHB_CONTRADICTION = inherited.DETAIL_EARLY_CFG_AHB_CONTRADICTION
DETAIL_EARLY_DOMAIN_CONTRADICTION = inherited.DETAIL_EARLY_DOMAIN_CONTRADICTION
DETAIL_EARLY_TRACE_RING_LOSS = inherited.DETAIL_EARLY_TRACE_RING_LOSS
CONTRADICTION_DETAIL_NAMES = inherited.CONTRADICTION_DETAIL_NAMES
Event = inherited.Event
EARLY_EVENTS = inherited.EARLY_EVENTS
EVENT_INDEX = inherited.EVENT_INDEX
POSITIONS = carrier_spec.POSITIONS
TERMINAL_POSITION = carrier_spec.TERMINAL_POSITION
SpecError = carrier_spec.SpecError

encode_first = inherited.encode_first
decode_first = inherited.decode_first
encode_summary = inherited.encode_summary
decode_summary = inherited.decode_summary
first_outputs = inherited.first_outputs
summary_outputs = inherited.summary_outputs
position_for_generation = carrier_spec.position_for_generation


def validate_slot(
    *, generation: int, stage: int, outcome: int, item_index: int, detail: int
) -> None:
    """Validate Carrier-v2 positions with the P3.12/P3.11 detail families."""

    position = carrier_spec.position_for_generation(generation)
    if (stage, item_index) != position.pair:
        raise SpecError("P3.12 carrier position differs")
    if detail in CONTRADICTION_DETAIL_NAMES:
        if outcome != carrier_spec.OUTCOME_FAILURE:
            raise SpecError("P3.12 contradiction outcome differs")
        return
    carrier_spec.validate_slot(
        generation=generation,
        stage=stage,
        outcome=outcome,
        item_index=item_index,
        detail=detail,
    )


def validate() -> dict[str, object]:
    result = inherited.validate()
    if FIRST_DETAIL_MAX > 0xDAF or SUMMARY_DETAIL_MAX > 0x4FFF:
        raise ValueError("P3.12 fixed Image bands differ")
    for detail in first_outputs():
        validate_slot(
            generation=ATTR_ORDINAL + 1,
            stage=position_for_generation(ATTR_ORDINAL + 1).stage,
            outcome=carrier_spec.OUTCOME_PROGRESS,
            item_index=position_for_generation(ATTR_ORDINAL + 1).item_index,
            detail=detail,
        )
    for detail in (*summary_outputs(), *CONTRADICTION_DETAIL_NAMES):
        validate_slot(
            generation=SUMMARY_ORDINAL + 1,
            stage=position_for_generation(SUMMARY_ORDINAL + 1).stage,
            outcome=carrier_spec.OUTCOME_FAILURE,
            item_index=position_for_generation(SUMMARY_ORDINAL + 1).item_index,
            detail=detail,
        )
    return {
        **result,
        "schema": "s22plus_fyg8_p312_telemetry_spec_v1",
        "carrier_v2_slot_contract": True,
        "profile_hits_may_exceed_records_outside_recording_window": True,
        "verified": True,
    }


if __name__ == "__main__":
    import json

    print(json.dumps(validate(), sort_keys=True))
